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
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ...io.atomic import atomic_write_json
from ...io.run_layout import RunLayout
from ...util.logging import get_logger

logger = get_logger()


class EvidenceMappingError(Exception):
    """Raised when evidence mapping fails."""
    pass


class EvidenceValidationError(Exception):
    """Raised when evidence validation fails."""
    pass


def compute_text_similarity(text1: str, text2: str) -> float:
    """Compute simple similarity score between two text strings.

    Uses keyword overlap and length normalization as a heuristic.
    For production, this would use embedding-based semantic similarity via LLM.

    Args:
        text1: First text string
        text2: Second text string

    Returns:
        Similarity score between 0.0 and 1.0
    """
    # Normalize texts
    words1 = set(re.findall(r'\w+', text1.lower()))
    words2 = set(re.findall(r'\w+', text2.lower()))

    if not words1 or not words2:
        return 0.0

    # Compute Jaccard similarity
    intersection = words1 & words2
    union = words1 | words2

    return len(intersection) / len(union) if union else 0.0


def extract_keywords_from_claim(claim_text: str, claim_kind: str) -> List[str]:
    """Extract relevant keywords from claim for matching.

    Args:
        claim_text: Claim text
        claim_kind: Claim kind (feature, format, workflow, api, etc.)

    Returns:
        List of keywords
    """
    # Remove common stopwords
    stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                 'of', 'with', 'by', 'from', 'as', 'is', 'are', 'was', 'were', 'be',
                 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this',
                 'that', 'these', 'those', 'it', 'its'}

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

    Returns:
        Relevance score between 0.0 and 1.0
    """
    claim_text = claim['claim_text']
    claim_kind = claim['claim_kind']

    # Base score from source priority (already in claim)
    source_priority = claim.get('source_priority', 7)
    base_score = (8 - source_priority) / 7.0  # Invert priority to score (1→1.0, 7→~0.14)

    # Compute text similarity
    similarity = compute_text_similarity(claim_text, evidence_text)

    # Extract keywords and check for matches
    keywords = extract_keywords_from_claim(claim_text, claim_kind)
    evidence_lower = evidence_text.lower()

    keyword_matches = sum(1 for kw in keywords if kw in evidence_lower)
    keyword_score = min(keyword_matches / len(keywords), 1.0) if keywords else 0.0

    # Combine scores (weighted average)
    # 30% base (source priority), 40% similarity, 30% keyword matches
    final_score = (0.3 * base_score) + (0.4 * similarity) + (0.3 * keyword_score)

    return min(final_score, 1.0)


def find_supporting_evidence_in_docs(
    claim: Dict[str, Any],
    doc_files: List[Dict[str, Any]],
    repo_dir: Path,
    max_evidence_per_claim: int = 5,
) -> List[Dict[str, Any]]:
    """Find supporting evidence for claim in documentation files.

    Args:
        claim: Claim dictionary
        doc_files: List of discovered documentation files
        repo_dir: Repository root directory
        max_evidence_per_claim: Maximum evidence items to return

    Returns:
        List of evidence dictionaries sorted by relevance score
    """
    evidence_items = []

    for doc_file in doc_files:
        doc_path = repo_dir / doc_file['path']

        if not doc_path.exists():
            logger.warning("doc_file_not_found", path=str(doc_path))
            continue

        try:
            content = doc_path.read_text(encoding='utf-8', errors='ignore')
        except Exception as e:
            logger.warning("doc_read_error", path=str(doc_path), error=str(e))
            continue

        # Score relevance
        relevance_score = score_evidence_relevance(claim, content, str(doc_path))

        # Only include if score exceeds threshold
        if relevance_score > 0.2:  # Minimum relevance threshold
            evidence_items.append({
                'path': doc_file['path'],
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
    max_evidence_per_claim: int = 3,
) -> List[Dict[str, Any]]:
    """Find supporting evidence for claim in example code files.

    Args:
        claim: Claim dictionary
        example_files: List of discovered example files
        repo_dir: Repository root directory
        max_evidence_per_claim: Maximum evidence items to return

    Returns:
        List of evidence dictionaries sorted by relevance score
    """
    evidence_items = []

    for example_file in example_files:
        example_path = repo_dir / example_file['path']

        if not example_path.exists():
            logger.warning("example_file_not_found", path=str(example_path))
            continue

        try:
            content = example_path.read_text(encoding='utf-8', errors='ignore')
        except Exception as e:
            logger.warning("example_read_error", path=str(example_path), error=str(e))
            continue

        # Score relevance
        relevance_score = score_evidence_relevance(claim, content, str(example_path))

        # Only include if score exceeds threshold
        if relevance_score > 0.25:  # Slightly higher threshold for examples
            evidence_items.append({
                'path': example_file['path'],
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
) -> Dict[str, Any]:
    """Enrich claim with supporting evidence from docs and examples.

    Args:
        claim: Claim dictionary
        doc_files: List of discovered documentation files
        example_files: List of discovered example files
        repo_dir: Repository root directory

    Returns:
        Enriched claim with evidence mappings
    """
    # Find supporting evidence
    doc_evidence = find_supporting_evidence_in_docs(claim, doc_files, repo_dir)
    example_evidence = find_supporting_evidence_in_examples(claim, example_files, repo_dir)

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

    # Enrich each claim with supporting evidence
    enriched_claims = []
    for claim in claims:
        try:
            enriched_claim = enrich_claim_with_evidence(
                claim,
                doc_files,
                example_files,
                repo_dir,
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
