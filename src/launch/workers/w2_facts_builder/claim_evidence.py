"""TC-3230: Claim-level evidence chunk mapping for hallucination prevention.

Links each claim to its top-K most relevant source chunks from
source_chunks.json, providing deterministic grounding excerpts
that W5 can inject per-claim instead of per-query TF-IDF retrieval.

Scoring reuses the same 30/40/30 weighted formula from map_evidence.py:
  score = 0.3 * base_priority + 0.4 * jaccard_similarity + 0.3 * keyword_match

Spec references:
- specs/03_product_facts_and_evidence.md (Evidence priority and structure)
- specs/04_claims_compiler_truth_lock.md (Claims structure)
- specs/schemas/claim_evidence_chunks.schema.json
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .map_evidence import (
    _SCORE_WEIGHT_BASE,
    _SCORE_WEIGHT_KEYWORDS,
    _SCORE_WEIGHT_SIMILARITY,
    extract_keywords_from_claim,
)

# Hard caps per spec
TOP_K_CHUNKS_PER_CLAIM = 3
MAX_EXCERPT_CHARS = 500
_MIN_SCORE_DEFAULT = 0.05


def classify_evidence_type(file_path: str) -> str:
    """Classify a file path into an evidence type.

    Returns one of: 'readme', 'manifest', 'code_docstring', 'doc'.
    """
    lower = file_path.lower()
    if "readme" in lower:
        return "readme"
    for manifest in ("setup.py", "pyproject.toml", "setup.cfg", "package.json",
                     "go.mod", "cargo.toml"):
        if lower.endswith(manifest):
            return "manifest"
    if lower.endswith((".py", ".pyi")):
        return "code_docstring"
    return "doc"


def _truncate_excerpt(text: str, max_chars: int = MAX_EXCERPT_CHARS) -> str:
    """Truncate text to *max_chars* at a word boundary."""
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars].rsplit(" ", 1)[0]
    if not truncated:
        truncated = text[:max_chars]
    return truncated + "..."


def score_claim_chunk_relevance(
    claim_text: str,
    claim_kind: str,
    chunk_text: str,
    source_priority: int = 7,
) -> float:
    """Score relevance of a source chunk to a claim.

    Uses the identical 30/40/30 weighted formula from
    ``map_evidence.score_evidence_relevance``:

        score = 0.3 * base + 0.4 * jaccard + 0.3 * keyword_ratio

    Args:
        claim_text: The normalised claim text.
        claim_kind: The claim kind (feature, format, api, ...).
        chunk_text: Source chunk text content.
        source_priority: 1-7 evidence priority (lower = higher quality).

    Returns:
        Score in [0.0, 1.0].
    """
    from .embeddings import tokenize

    # Base score from source priority (1 → 1.0, 7 → ~0.14)
    base_score = (8 - source_priority) / 7.0

    # Jaccard similarity
    tokens_claim = tokenize(claim_text)
    tokens_chunk = tokenize(chunk_text)
    if tokens_claim and tokens_chunk:
        set_claim = set(tokens_claim)
        set_chunk = set(tokens_chunk)
        intersection = set_claim & set_chunk
        similarity = len(intersection) / len(set_claim | set_chunk) if intersection else 0.0
    else:
        similarity = 0.0

    # Keyword matching
    keywords = extract_keywords_from_claim(claim_text, claim_kind)
    if keywords:
        chunk_lower = chunk_text.lower()
        kw_matches = sum(1 for kw in keywords if kw in chunk_lower)
        kw_score = min(kw_matches / len(keywords), 1.0)
    else:
        kw_score = 0.0

    return min(
        _SCORE_WEIGHT_BASE * base_score
        + _SCORE_WEIGHT_SIMILARITY * similarity
        + _SCORE_WEIGHT_KEYWORDS * kw_score,
        1.0,
    )


# ---------------------------------------------------------------------------
# Internal dataclasses (NOT in src/launch/models — TC-250 single-writer)
# ---------------------------------------------------------------------------

@dataclass
class ChunkEvidence:
    """A single chunk matched to a claim."""

    chunk_id: str
    file_path: str
    heading_context: str
    excerpt: str
    score: float
    evidence_type: str
    line_range: Optional[Tuple[int, int]] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "chunk_id": self.chunk_id,
            "evidence_type": self.evidence_type,
            "excerpt": self.excerpt,
            "file_path": self.file_path,
            "heading_context": self.heading_context,
            "score": round(self.score, 4),
        }
        if self.line_range is not None:
            d["line_range"] = list(self.line_range)
        return d


@dataclass
class ClaimEvidenceEntry:
    """Evidence chunks for a single claim."""

    claim_id: str
    evidence_chunks: List[ChunkEvidence] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "evidence_chunks": [c.to_dict() for c in self.evidence_chunks],
        }


# ---------------------------------------------------------------------------
# Main builder
# ---------------------------------------------------------------------------

def build_claim_evidence_chunks(
    claims: List[Dict[str, Any]],
    chunks: List[Dict[str, Any]],
    *,
    top_k: int = TOP_K_CHUNKS_PER_CLAIM,
    max_excerpt_chars: int = MAX_EXCERPT_CHARS,
    min_score: float = _MIN_SCORE_DEFAULT,
) -> Dict[str, Any]:
    """Build the ``claim_evidence_chunks.json`` artifact.

    For each claim, finds top-K most relevant source chunks using the
    same scoring formula as ``map_evidence.py``.

    Args:
        claims: List of claim dicts (from evidence_map or extracted_claims).
        chunks: List of chunk dicts (from source_chunks.json).
        top_k: Maximum evidence chunks per claim.
        max_excerpt_chars: Maximum excerpt character length.
        min_score: Minimum relevance score threshold.

    Returns:
        Artifact dict with ``schema_version``, ``entries``, ``metadata``.
    """
    if not chunks:
        return {
            "schema_version": "1.0",
            "entries": [],
            "metadata": {
                "total_claims": len(claims),
                "claims_with_chunks": 0,
                "avg_chunks_per_claim": 0.0,
            },
        }

    # Pre-tokenize chunks for fast keyword pre-filter
    from .embeddings import tokenize
    from ._shared import STOPWORDS

    chunk_word_sets: Dict[str, frozenset] = {}
    for chunk in chunks:
        cid = chunk.get("chunk_id", "")
        text = chunk.get("text", "")
        words = frozenset(
            w for w in re.findall(r"\w+", text.lower())
            if w not in STOPWORDS and len(w) >= 2
        )
        chunk_word_sets[cid] = words

    entries: List[Dict[str, Any]] = []
    claims_with_chunks = 0

    for claim in claims:
        claim_id = claim.get("claim_id", "")
        claim_text = claim.get("claim_text", "")
        claim_kind = claim.get("claim_kind", "feature")
        source_priority = claim.get("source_priority", 7)

        if not claim_text:
            entries.append({"claim_id": claim_id, "evidence_chunks": []})
            continue

        # Pre-filter keywords for fast skip
        prefilter_kws = frozenset(
            w for w in re.findall(r"\w+", claim_text.lower())
            if w not in STOPWORDS and len(w) >= 2
        ) | frozenset({claim_kind})

        scored: List[Tuple[float, Dict[str, Any]]] = []
        for chunk in chunks:
            cid = chunk.get("chunk_id", "")
            # Fast pre-filter: skip chunks with zero keyword overlap
            if prefilter_kws and cid in chunk_word_sets:
                if not prefilter_kws & chunk_word_sets[cid]:
                    continue

            score = score_claim_chunk_relevance(
                claim_text, claim_kind,
                chunk.get("text", ""),
                source_priority,
            )
            if score >= min_score:
                scored.append((score, chunk))

        # Sort by score desc, then chunk_id for determinism
        scored.sort(key=lambda x: (-x[0], x[1].get("chunk_id", "")))
        top_chunks = scored[:top_k]

        evidence_list: List[Dict[str, Any]] = []
        for score, chunk in top_chunks:
            excerpt = _truncate_excerpt(chunk.get("text", ""), max_excerpt_chars)
            ce = ChunkEvidence(
                chunk_id=chunk.get("chunk_id", ""),
                file_path=chunk.get("file_path", ""),
                heading_context=chunk.get("heading_context", ""),
                excerpt=excerpt,
                score=score,
                evidence_type=classify_evidence_type(chunk.get("file_path", "")),
            )
            evidence_list.append(ce.to_dict())

        if evidence_list:
            claims_with_chunks += 1

        entries.append({
            "claim_id": claim_id,
            "evidence_chunks": evidence_list,
        })

    # Sort deterministically by claim_id
    entries.sort(key=lambda e: e["claim_id"])

    total_chunks = sum(len(e["evidence_chunks"]) for e in entries)
    avg_chunks = total_chunks / max(len(entries), 1)

    return {
        "schema_version": "1.0",
        "entries": entries,
        "metadata": {
            "avg_chunks_per_claim": round(avg_chunks, 2),
            "claims_with_chunks": claims_with_chunks,
            "total_claims": len(claims),
        },
    }


def enrich_evidence_map_with_chunks(
    evidence_map: Dict[str, Any],
    claim_evidence_chunks: Dict[str, Any],
) -> Dict[str, Any]:
    """Add ``evidence_chunks`` references to evidence_map claims.

    Backward-compatible: adds optional ``evidence_chunks: [{chunk_id, score}]``
    to each claim. Claims without matches get no field added.

    Args:
        evidence_map: The existing evidence_map.json dict.
        claim_evidence_chunks: The claim_evidence_chunks artifact dict.

    Returns:
        The mutated evidence_map dict (same reference).
    """
    chunks_by_claim: Dict[str, List[Dict[str, Any]]] = {}
    for entry in claim_evidence_chunks.get("entries", []):
        cid = entry.get("claim_id", "")
        chunk_refs = [
            {"chunk_id": c["chunk_id"], "score": c["score"]}
            for c in entry.get("evidence_chunks", [])
        ]
        if chunk_refs:
            chunks_by_claim[cid] = chunk_refs

    for claim in evidence_map.get("claims", []):
        cid = claim.get("claim_id", "")
        if cid in chunks_by_claim:
            claim["evidence_chunks"] = chunks_by_claim[cid]

    return evidence_map
