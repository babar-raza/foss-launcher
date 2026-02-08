"""TC-412: Map evidence from claims to documentation and examples.

This module implements evidence mapping per specs/03_product_facts_and_evidence.md.
It enriches extracted claims with supporting evidence from discovered docs and examples.

Evidence mapping algorithm (binding):
1. Load extracted_claims.json from TC-411
2. Load discovered_docs.json and discovered_examples.json from TC-400
3. For each claim, find supporting evidence in docs/examples
4. Score evidence relevance using semantic similarity and keyword matching
5. Rank evidence by relevance score
6. Generate enriched evidence_map.json with claim→evidence mappings

Spec references:
- specs/03_product_facts_and_evidence.md (Evidence priority and structure)
- specs/04_claims_compiler_truth_lock.md (Claims structure)
- specs/21_worker_contracts.md:98-125 (W2 FactsBuilder contract)
- specs/10_determinism_and_caching.md (Stable ordering)

TC-412: W2.2 Map claims to evidence in docs and examples
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ...io.atomic import atomic_write_json
from ...io.run_layout import RunLayout
from ...util.logging import get_logger
from ._shared import STOPWORDS

logger = get_logger()

# Configurable file size limit (MB) - prevents memory issues with very large files
MAX_FILE_SIZE_MB = float(os.environ.get("W2_MAX_FILE_SIZE_MB", "5.0"))

# Evidence scoring weights (tuned heuristic from TC-412 optimization).
# Formula: score = (W_BASE * base) + (W_SIM * sim) + (W_KW * kw)
# where base=source_priority_score, similarity=Jaccard, keywords=keyword_match_ratio.
_SCORE_WEIGHT_BASE: float = 0.3       # 30% from source priority
_SCORE_WEIGHT_SIMILARITY: float = 0.4  # 40% from text similarity
_SCORE_WEIGHT_KEYWORDS: float = 0.3    # 30% from keyword matches


class EvidenceMappingError(Exception):
    """Raised when evidence mapping fails."""
    pass


class EvidenceValidationError(Exception):
    """Raised when evidence validation fails."""
    pass


def compute_text_similarity(text1: str, text2: str, _tokens2_cache=None) -> float:
    """Compute similarity between two text strings using fast Jaccard word-overlap.

    Uses set-based Jaccard for O(claims × docs) evidence mapping where speed
    matters. The TF-IDF embeddings module (``embeddings.py``) is available for
    higher-fidelity scoring in non-hot-path contexts.

    When ``_tokens2_cache`` is provided (from ``embeddings.precompute_token_cache``),
    the doc's token set is reused directly, avoiding repeated tokenization.

    Args:
        text1: First text string (typically short claim text)
        text2: Second text string (typically large document content)
        _tokens2_cache: Optional pre-tokenized (tokens_list, token_frozenset)
            for text2.

    Returns:
        Similarity score between 0.0 and 1.0
    """
    from .embeddings import tokenize

    tokens1 = tokenize(text1)
    if not tokens1:
        return 0.0

    if _tokens2_cache is not None:
        _, set2 = _tokens2_cache
    else:
        tokens2 = tokenize(text2)
        set2 = frozenset(tokens2)

    if not set2:
        return 0.0

    set1 = set(tokens1)
    intersection = set1 & set2
    if not intersection:
        return 0.0

    union = set1 | set2
    return len(intersection) / len(union)


def extract_keywords_from_claim(claim_text: str, claim_kind: str) -> List[str]:
    """Extract relevant keywords from claim for matching.

    Args:
        claim_text: Claim text
        claim_kind: Claim kind (feature, format, workflow, api, etc.)

    Returns:
        List of keywords
    """
    # Remove common stopwords (use shared constant from ._shared)
    stopwords = STOPWORDS

    # Extract words
    words = re.findall(r'\w+', claim_text.lower())

    # Filter stopwords and short words
    keywords = [w for w in words if w not in stopwords and len(w) > 2]

    # Add claim kind as a keyword
    keywords.append(claim_kind)

    return keywords


def score_evidence_relevance(
    claim: Dict[str, Any],
    evidence_text: str,
    evidence_path: str,
    _tokens_cache=None,
    _evidence_lower: Optional[str] = None,
) -> float:
    """Score relevance of evidence to claim.

    Per specs/03_product_facts_and_evidence.md:76-85 (Evidence priority):
    - Higher priority sources get higher base scores
    - Semantic similarity increases score
    - Direct keyword matches increase score

    Args:
        claim: Claim dictionary
        evidence_text: Evidence text content
        evidence_path: Path to evidence file (for source type detection)
        _tokens_cache: Optional pre-tokenized cache for evidence_text
        _evidence_lower: Optional pre-lowered evidence text

    Returns:
        Relevance score between 0.0 and 1.0
    """
    claim_text = claim['claim_text']
    claim_kind = claim['claim_kind']

    # Base score from source priority (already in claim)
    source_priority = claim.get('source_priority', 7)
    base_score = (8 - source_priority) / 7.0  # Invert priority to score (1→1.0, 7→~0.14)

    # Compute text similarity (with pre-tokenized cache for performance)
    similarity = compute_text_similarity(claim_text, evidence_text, _tokens2_cache=_tokens_cache)

    # Extract keywords and check for matches
    keywords = extract_keywords_from_claim(claim_text, claim_kind)
    evidence_lower = _evidence_lower if _evidence_lower is not None else evidence_text.lower()

    keyword_matches = sum(1 for kw in keywords if kw in evidence_lower)
    keyword_score = min(keyword_matches / len(keywords), 1.0) if keywords else 0.0

    # Combine scores (weighted average using module constants)
    final_score = (
        (_SCORE_WEIGHT_BASE * base_score)
        + (_SCORE_WEIGHT_SIMILARITY * similarity)
        + (_SCORE_WEIGHT_KEYWORDS * keyword_score)
    )

    return min(final_score, 1.0)


def _load_and_tokenize_files(
    files: List[Dict[str, Any]],
    repo_dir: Path,
    label: str = "file",
    emit_event=None,
) -> Dict[str, Tuple]:
    """Pre-load file contents, pre-tokenize for TF-IDF, pre-lower, and build word sets.

    Performance optimization: reads each file once, tokenizes once,
    lowercases once, builds word set once. Avoids O(claims × files) I/O,
    tokenization, and string lowering overhead.

    The word_set enables O(1) set-intersection pre-filtering instead of
    O(keywords × doc_length) substring scanning.

    Args:
        files: List of file dicts with 'path' key
        repo_dir: Repository root directory
        label: Label for log messages (used in event label)
        emit_event: Optional callback function(event_dict) for progress events

    Returns:
        Dictionary mapping path to (content_str, token_cache, content_lower, word_set) tuple.
    """
    from .embeddings import precompute_token_cache

    cache: Dict[str, Tuple] = {}
    total = len(files)
    for i, file_info in enumerate(files, 1):
        file_path = repo_dir / file_info['path']

        # Process file (may skip if not found, too large, or read error)
        if not file_path.exists():
            logger.warning(f"{label}_file_not_found", path=str(file_path))
        else:
            # Check file size before reading (TC-1050-T4: Memory safety)
            try:
                file_size_mb = file_path.stat().st_size / (1024 * 1024)
                if file_size_mb > MAX_FILE_SIZE_MB:
                    logger.warning(
                        f"{label}_too_large_skipped",
                        path=file_info['path'],
                        size_mb=round(file_size_mb, 2),
                        max_size_mb=MAX_FILE_SIZE_MB
                    )
                else:
                    # File size is acceptable, try to read and tokenize
                    try:
                        content = file_path.read_text(encoding='utf-8', errors='ignore')
                        token_cache = precompute_token_cache(content)
                        content_lower = content.lower()
                        # Pre-build word set for fast set-intersection pre-filtering
                        word_set = frozenset(
                            w for w in re.findall(r'\w+', content_lower)
                            if w not in STOPWORDS and len(w) >= 2
                        )
                        cache[file_info['path']] = (content, token_cache, content_lower, word_set)
                    except Exception as e:
                        logger.warning(f"{label}_read_error", path=str(file_path), error=str(e))
            except (OSError, FileNotFoundError) as e:
                logger.warning(f"{label}_stat_failed", path=file_info['path'], error=str(e))

        # Emit progress every 10 files or on completion (regardless of whether file was processed)
        if emit_event and (i % 10 == 0 or i == total):
            emit_event({
                "event_type": "WORK_PROGRESS",
                "label": f"{label}_tokenization",
                "progress": {"current": i, "total": total}
            })

    return cache


def find_supporting_evidence_in_docs(
    claim: Dict[str, Any],
    doc_files: List[Dict[str, Any]],
    repo_dir: Path,
    max_evidence_per_claim: int = 20,
    _content_cache: Optional[Dict[str, Tuple[str, Any, str]]] = None,
) -> List[Dict[str, Any]]:
    """Find supporting evidence for claim in documentation files.

    Args:
        claim: Claim dictionary
        doc_files: List of discovered documentation files
        repo_dir: Repository root directory
        max_evidence_per_claim: Maximum evidence items to return
        _content_cache: Pre-loaded (content, token_cache, content_lower) tuples

    Returns:
        List of evidence dictionaries sorted by relevance score
    """
    from .embeddings import tokenize

    evidence_items = []

    # --- Pre-compute claim-level data ONCE (not per doc) ---
    claim_text = claim['claim_text']
    claim_kind = claim['claim_kind']
    source_priority = claim.get('source_priority', 7)
    base_score = (8 - source_priority) / 7.0

    # Keywords for scoring (len > 2)
    keywords = extract_keywords_from_claim(claim_text, claim_kind)
    n_keywords = len(keywords)

    # Claim tokens for Jaccard similarity (computed once, reused per doc)
    claim_tokens = tokenize(claim_text)
    claim_token_set = set(claim_tokens) if claim_tokens else set()

    # Pre-filter uses lenient word set (>= 2 chars) for fast skip.
    prefilter_kws = frozenset(
        w for w in re.findall(r'\w+', claim_text.lower())
        if w not in STOPWORDS and len(w) >= 2
    ) | frozenset({claim_kind})

    for doc_file in doc_files:
        path_key = doc_file['path']

        # Use cached content + tokens + lowered + word_set if available
        if _content_cache is not None and path_key in _content_cache:
            cached = _content_cache[path_key]
            if len(cached) == 4:
                content, token_cache, content_lower, word_set = cached
            else:
                content, token_cache, content_lower = cached
                word_set = None
        else:
            doc_path = repo_dir / path_key
            if not doc_path.exists():
                continue
            try:
                content = doc_path.read_text(encoding='utf-8', errors='ignore')
            except Exception:
                continue
            token_cache = None
            content_lower = content.lower()
            word_set = None

        # Fast pre-filter: skip docs with zero keyword overlap.
        if word_set is not None and prefilter_kws:
            if not prefilter_kws & word_set:
                continue
        elif content_lower and prefilter_kws:
            if not any(kw in content_lower for kw in prefilter_kws):
                continue

        # --- Inline scoring (avoids per-doc re-tokenization) ---
        # Jaccard similarity using pre-computed claim tokens
        if claim_token_set and token_cache is not None:
            _, doc_token_set = token_cache
            intersection = claim_token_set & doc_token_set
            similarity = len(intersection) / len(claim_token_set | doc_token_set) if intersection else 0.0
        elif claim_token_set:
            doc_tokens = tokenize(content)
            doc_token_set = set(doc_tokens)
            intersection = claim_token_set & doc_token_set
            similarity = len(intersection) / len(claim_token_set | doc_token_set) if intersection else 0.0
        else:
            similarity = 0.0

        # Keyword matching: use word_set (O(1) per keyword) when available,
        # fall back to substring scan only when no word_set.
        if word_set is not None and n_keywords:
            kw_matches = sum(1 for kw in keywords if kw in word_set)
            kw_score = kw_matches / n_keywords
        elif n_keywords:
            ev_lower = content_lower if content_lower else content.lower()
            kw_matches = sum(1 for kw in keywords if kw in ev_lower)
            kw_score = kw_matches / n_keywords
        else:
            kw_score = 0.0

        # Combined score using module constants (same weights as score_evidence_relevance)
        relevance_score = (
            (_SCORE_WEIGHT_BASE * base_score)
            + (_SCORE_WEIGHT_SIMILARITY * similarity)
            + (_SCORE_WEIGHT_KEYWORDS * kw_score)
        )
        relevance_score = min(relevance_score, 1.0)

        # Only include if score exceeds threshold
        if relevance_score > 0.05:
            evidence_items.append({
                'path': path_key,
                'type': 'documentation',
                'relevance_score': relevance_score,
                'doc_type': doc_file.get('type', 'unknown'),
            })

    # Sort by relevance score (descending) and limit to max
    evidence_items.sort(key=lambda x: x['relevance_score'], reverse=True)

    return evidence_items[:max_evidence_per_claim]


def find_supporting_evidence_in_examples(
    claim: Dict[str, Any],
    example_files: List[Dict[str, Any]],
    repo_dir: Path,
    max_evidence_per_claim: int = 10,
    _content_cache: Optional[Dict[str, Tuple[str, Any, str]]] = None,
) -> List[Dict[str, Any]]:
    """Find supporting evidence for claim in example code files.

    Args:
        claim: Claim dictionary
        example_files: List of discovered example files
        repo_dir: Repository root directory
        max_evidence_per_claim: Maximum evidence items to return
        _content_cache: Pre-loaded (content, token_cache, content_lower) tuples

    Returns:
        List of evidence dictionaries sorted by relevance score
    """
    from .embeddings import tokenize

    evidence_items = []

    # --- Pre-compute claim-level data ONCE ---
    claim_text = claim['claim_text']
    claim_kind = claim['claim_kind']
    source_priority = claim.get('source_priority', 7)
    base_score = (8 - source_priority) / 7.0

    keywords = extract_keywords_from_claim(claim_text, claim_kind)
    n_keywords = len(keywords)

    claim_tokens = tokenize(claim_text)
    claim_token_set = set(claim_tokens) if claim_tokens else set()

    prefilter_kws = frozenset(
        w for w in re.findall(r'\w+', claim_text.lower())
        if w not in STOPWORDS and len(w) >= 2
    ) | frozenset({claim_kind})

    for example_file in example_files:
        path_key = example_file['path']

        # Use cached content + tokens + lowered + word_set if available
        if _content_cache is not None and path_key in _content_cache:
            cached = _content_cache[path_key]
            if len(cached) == 4:
                content, token_cache, content_lower, word_set = cached
            else:
                content, token_cache, content_lower = cached
                word_set = None
        else:
            example_path = repo_dir / path_key
            if not example_path.exists():
                continue
            try:
                content = example_path.read_text(encoding='utf-8', errors='ignore')
            except Exception:
                continue
            token_cache = None
            content_lower = content.lower()
            word_set = None

        # Fast pre-filter: skip examples with zero keyword overlap
        if word_set is not None and prefilter_kws:
            if not prefilter_kws & word_set:
                continue
        elif content_lower and prefilter_kws:
            if not any(kw in content_lower for kw in prefilter_kws):
                continue

        # --- Inline scoring (same formula as score_evidence_relevance) ---
        if claim_token_set and token_cache is not None:
            _, doc_token_set = token_cache
            intersection = claim_token_set & doc_token_set
            similarity = len(intersection) / len(claim_token_set | doc_token_set) if intersection else 0.0
        elif claim_token_set:
            doc_tokens = tokenize(content)
            doc_token_set = set(doc_tokens)
            intersection = claim_token_set & doc_token_set
            similarity = len(intersection) / len(claim_token_set | doc_token_set) if intersection else 0.0
        else:
            similarity = 0.0

        # Keyword matching: use word_set (O(1)) when available
        if word_set is not None and n_keywords:
            kw_matches = sum(1 for kw in keywords if kw in word_set)
            kw_score = kw_matches / n_keywords
        elif n_keywords:
            ev_lower = content_lower if content_lower else content.lower()
            kw_matches = sum(1 for kw in keywords if kw in ev_lower)
            kw_score = kw_matches / n_keywords
        else:
            kw_score = 0.0

        # Combined score using module constants (same weights as score_evidence_relevance)
        relevance_score = min(
            (_SCORE_WEIGHT_BASE * base_score)
            + (_SCORE_WEIGHT_SIMILARITY * similarity)
            + (_SCORE_WEIGHT_KEYWORDS * kw_score),
            1.0
        )

        if relevance_score > 0.1:
            evidence_items.append({
                'path': path_key,
                'type': 'example',
                'relevance_score': relevance_score,
                'language': example_file.get('language', 'unknown'),
            })

    # Sort by relevance score (descending) and limit to max
    evidence_items.sort(key=lambda x: x['relevance_score'], reverse=True)

    return evidence_items[:max_evidence_per_claim]


def enrich_claim_with_evidence(
    claim: Dict[str, Any],
    doc_files: List[Dict[str, Any]],
    example_files: List[Dict[str, Any]],
    repo_dir: Path,
    _doc_cache: Optional[Dict[str, str]] = None,
    _example_cache: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Enrich claim with supporting evidence from docs and examples.

    Args:
        claim: Claim dictionary
        doc_files: List of discovered documentation files
        example_files: List of discovered example files
        repo_dir: Repository root directory
        _doc_cache: Pre-loaded doc contents (performance optimization)
        _example_cache: Pre-loaded example contents (performance optimization)

    Returns:
        Enriched claim with evidence mappings
    """
    # Find supporting evidence
    doc_evidence = find_supporting_evidence_in_docs(
        claim, doc_files, repo_dir, _content_cache=_doc_cache,
    )
    example_evidence = find_supporting_evidence_in_examples(
        claim, example_files, repo_dir, _content_cache=_example_cache,
    )

    # Combine all evidence
    all_evidence = doc_evidence + example_evidence

    # Sort by relevance score (descending)
    all_evidence.sort(key=lambda x: x['relevance_score'], reverse=True)

    # Build enriched claim
    enriched_claim = claim.copy()
    enriched_claim['supporting_evidence'] = all_evidence
    enriched_claim['evidence_count'] = len(all_evidence)

    return enriched_claim


def validate_evidence_map_structure(evidence_map: Dict[str, Any]) -> None:
    """Validate evidence map structure against schema.

    Per specs/schemas/evidence_map.schema.json.

    Args:
        evidence_map: Evidence map dictionary

    Raises:
        EvidenceValidationError: If structure is invalid
    """
    required_fields = ['schema_version', 'repo_url', 'repo_sha', 'claims']

    for field in required_fields:
        if field not in evidence_map:
            raise EvidenceValidationError(f"Missing required field: {field}")

    # Validate claims array
    if not isinstance(evidence_map['claims'], list):
        raise EvidenceValidationError("claims must be a list")

    # Validate each claim
    for claim in evidence_map['claims']:
        claim_required = ['claim_id', 'claim_text', 'claim_kind', 'truth_status', 'citations']
        for field in claim_required:
            if field not in claim:
                raise EvidenceValidationError(
                    f"Claim {claim.get('claim_id', 'unknown')} missing required field: {field}"
                )


def sort_claims_deterministically(claims: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Sort claims deterministically by claim_id.

    Per specs/10_determinism_and_caching.md:39-46:
    Claims must be sorted by claim_id lexicographically.

    Args:
        claims: List of claims

    Returns:
        Sorted list of claims
    """
    return sorted(claims, key=lambda c: c['claim_id'])


def map_evidence(
    repo_dir: Path,
    run_dir: Path,
    llm_client: Optional[Any] = None,
) -> Dict[str, Any]:
    """Map evidence from claims to documentation and examples.

    This is the main entry point for TC-412 evidence mapping.

    Per specs/21_worker_contracts.md:98-125 (W2 FactsBuilder contract):
    - Reads extracted_claims.json from TC-411
    - Reads discovered_docs.json and discovered_examples.json from TC-400
    - Maps each claim to supporting evidence (doc snippets, code examples)
    - Scores evidence relevance
    - Writes evidence_map.json artifact

    Args:
        repo_dir: Repository directory path
        run_dir: Run directory path
        llm_client: Optional LLM client (for semantic similarity)

    Returns:
        Evidence map dictionary with:
        {
            "schema_version": "1.0.0",
            "repo_url": str,
            "repo_sha": str,
            "claims": List[Dict] (with supporting_evidence added),
            "metadata": {
                "total_claims": int,
                "claims_with_evidence": int,
                "average_evidence_per_claim": float
            }
        }

    Raises:
        EvidenceMappingError: If evidence mapping fails
        FileNotFoundError: If required artifacts are missing

    Spec references:
    - specs/21_worker_contracts.md:98-125 (W2 FactsBuilder contract)
    - specs/03_product_facts_and_evidence.md (Evidence priority)
    - specs/04_claims_compiler_truth_lock.md (Claims structure)
    """
    run_layout = RunLayout(run_dir=run_dir)

    # Load extracted_claims.json from TC-411
    extracted_claims_path = run_layout.artifacts_dir / "extracted_claims.json"
    if not extracted_claims_path.exists():
        raise FileNotFoundError(
            f"extracted_claims.json not found: {extracted_claims_path}"
        )

    with open(extracted_claims_path, 'r', encoding='utf-8') as f:
        extracted_claims = json.load(f)

    # Load discovered_docs.json from TC-400
    discovered_docs_path = run_layout.artifacts_dir / "discovered_docs.json"
    if not discovered_docs_path.exists():
        raise FileNotFoundError(
            f"discovered_docs.json not found: {discovered_docs_path}"
        )

    with open(discovered_docs_path, 'r', encoding='utf-8') as f:
        discovered_docs = json.load(f)

    # Load discovered_examples.json from TC-400
    discovered_examples_path = run_layout.artifacts_dir / "discovered_examples.json"
    if not discovered_examples_path.exists():
        raise FileNotFoundError(
            f"discovered_examples.json not found: {discovered_examples_path}"
        )

    with open(discovered_examples_path, 'r', encoding='utf-8') as f:
        discovered_examples = json.load(f)

    # Extract metadata
    repo_url = extracted_claims.get('repo_url', '')
    repo_sha = extracted_claims.get('repo_sha', '')
    claims = extracted_claims.get('claims', [])

    # Get doc and example files
    doc_files = discovered_docs.get('doc_entrypoint_details', [])
    example_files = discovered_examples.get('example_file_details', [])

    logger.info(
        "evidence_mapping_started",
        total_claims=len(claims),
        total_docs=len(doc_files),
        total_examples=len(example_files),
    )

    # Pre-load + pre-tokenize all docs/examples once (avoids O(claims×docs) I/O and tokenization)
    doc_cache = _load_and_tokenize_files(
        doc_files,
        repo_dir,
        label="doc",
        emit_event=lambda e: logger.info("doc_tokenization_progress", **e)
    )
    example_cache = _load_and_tokenize_files(
        example_files,
        repo_dir,
        label="example",
        emit_event=lambda e: logger.info("example_tokenization_progress", **e)
    )

    # Enrich each claim with supporting evidence
    enriched_claims = []
    total_claims = len(claims)
    for idx, claim in enumerate(claims, 1):
        # Log progress every 500 claims
        if idx % 500 == 0 or idx == total_claims:
            logger.info(
                "evidence_mapping_progress",
                processed=idx,
                total=total_claims,
                percent=round(100 * idx / total_claims, 1),
            )

        try:
            enriched_claim = enrich_claim_with_evidence(
                claim,
                doc_files,
                example_files,
                repo_dir,
                _doc_cache=doc_cache,
                _example_cache=example_cache,
            )
            enriched_claims.append(enriched_claim)
        except Exception as e:
            logger.warning(
                "claim_evidence_mapping_failed",
                claim_id=claim.get('claim_id'),
                error=str(e),
            )
            # Include claim without evidence enrichment
            enriched_claims.append(claim)

    # Sort deterministically
    enriched_claims = sort_claims_deterministically(enriched_claims)

    # Compute metadata
    claims_with_evidence = sum(
        1 for c in enriched_claims if c.get('evidence_count', 0) > 0
    )
    total_evidence = sum(c.get('evidence_count', 0) for c in enriched_claims)
    avg_evidence = total_evidence / len(enriched_claims) if enriched_claims else 0.0

    # Build evidence map
    evidence_map = {
        'schema_version': '1.0.0',
        'repo_url': repo_url,
        'repo_sha': repo_sha,
        'claims': enriched_claims,
        'contradictions': [],  # Contradiction detection not implemented in TC-412
        'metadata': {
            'total_claims': len(enriched_claims),
            'claims_with_evidence': claims_with_evidence,
            'average_evidence_per_claim': round(avg_evidence, 2),
            'total_supporting_evidence': total_evidence,
        },
    }

    # Validate structure
    try:
        validate_evidence_map_structure(evidence_map)
    except EvidenceValidationError as e:
        logger.error("evidence_map_validation_failed", error=str(e))
        raise

    # Write artifact
    output_path = run_layout.artifacts_dir / "evidence_map.json"
    atomic_write_json(output_path, evidence_map)

    logger.info(
        "evidence_map_generated",
        total_claims=len(enriched_claims),
        claims_with_evidence=claims_with_evidence,
        average_evidence_per_claim=avg_evidence,
        output_path=str(output_path),
    )

    return evidence_map
