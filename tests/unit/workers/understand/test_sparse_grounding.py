"""Tests for BBN-02: sparse-fact graceful degradation in _filter_weak_evidence.

When bounded-description mode is active but the extraction database has fewer than
_SPARSE_FACTS_THRESHOLD api_facts, unbound LLM claims should receive
confidence=0.55 (llm_sparse_grounding) instead of 0.35 (llm_fallback).
This prevents near-total claim collapse on lean repos.
"""
from __future__ import annotations

from launcher.models.claims import Claim, EvidenceAnchor
from launcher.workers.understand.extract._validation import (
    _CONFIDENCE_BY_SOURCE,
    _SPARSE_FACTS_THRESHOLD,
    _filter_weak_evidence,
)

# TC-4225 drop threshold — claims below this are discarded
_TC4225_THRESHOLD = 0.5


def _make_llm_claim(claim_id: str, text: str, snippet: str = "") -> Claim:
    """Build a minimal LLM claim with one evidence anchor."""
    evidence = [EvidenceAnchor(snippet=snippet, source_file="src/foo.py")] if snippet else []
    return Claim(
        claim_id=claim_id,
        text=text,
        kind="feature",
        confidence=0.75,
        claim_source="llm",
        tier_relevance="all",
        evidence=evidence,
    )


class TestSparseFactsThreshold:
    """_SPARSE_FACTS_THRESHOLD must be a positive integer."""

    def test_threshold_is_positive_integer(self):
        assert isinstance(_SPARSE_FACTS_THRESHOLD, int)
        assert _SPARSE_FACTS_THRESHOLD > 0

    def test_sparse_grounding_confidence_in_confidence_by_source(self):
        """llm_sparse_grounding must be registered in _CONFIDENCE_BY_SOURCE."""
        assert "llm_sparse_grounding" in _CONFIDENCE_BY_SOURCE

    def test_sparse_grounding_above_tc4225_threshold(self):
        """llm_sparse_grounding confidence must be > TC-4225 drop threshold."""
        assert _CONFIDENCE_BY_SOURCE["llm_sparse_grounding"] > _TC4225_THRESHOLD

    def test_sparse_grounding_below_llm(self):
        """llm_sparse_grounding confidence must be below standard llm confidence."""
        assert _CONFIDENCE_BY_SOURCE["llm_sparse_grounding"] < _CONFIDENCE_BY_SOURCE["llm"]


class TestFilterWeakEvidenceSparseMode:
    """BBN-02: sparse_facts=True raises floor for unbound LLM claims."""

    def test_irrelevant_evidence_elevated_when_sparse(self):
        """In sparse mode, unbound LLM claims get confidence=0.55 (not 0.35)."""
        claim = _make_llm_claim("CLM-S1", "CsvHandler supports delimiters", snippet="unrelated text here")
        result = _filter_weak_evidence([claim], sparse_facts=True)
        assert len(result) == 1, "Claim should survive in sparse mode"
        assert result[0].confidence == 0.55, (
            f"Expected 0.55 (llm_sparse_grounding), got {result[0].confidence}"
        )
        assert result[0].claim_source == "llm_sparse_grounding"

    def test_irrelevant_evidence_downgraded_when_not_sparse(self):
        """Without sparse mode, unbound LLM claims still drop to 0.35."""
        claim = _make_llm_claim("CLM-S2", "CsvHandler supports delimiters", snippet="unrelated text here")
        result = _filter_weak_evidence([claim], sparse_facts=False)
        assert len(result) == 1
        assert result[0].confidence == 0.35, (
            f"Expected 0.35 (llm_fallback), got {result[0].confidence}"
        )

    def test_relevant_evidence_unchanged_in_sparse_mode(self):
        """In sparse mode, claims with relevant evidence keep their original confidence."""
        claim = _make_llm_claim(
            "CLM-S3",
            "CsvHandler supports custom delimiters",
            snippet="csvhandler supports custom delimiters",
        )
        result = _filter_weak_evidence([claim], sparse_facts=True)
        assert len(result) == 1
        assert result[0].confidence == 0.75, "Relevant evidence claim should be unchanged"
        assert result[0].claim_source == "llm"

    def test_empty_evidence_still_rejected_in_sparse_mode(self):
        """In sparse mode, LLM claims with zero evidence are still rejected."""
        claim = Claim(
            claim_id="CLM-S4",
            text="Workbook supports password protection",
            kind="feature",
            confidence=0.75,
            claim_source="llm",
            tier_relevance="all",
            evidence=[],
        )
        result = _filter_weak_evidence([claim], sparse_facts=True)
        assert len(result) == 0, "Empty-evidence LLM claims are rejected even in sparse mode"

    def test_deterministic_claim_unchanged_in_sparse_mode(self):
        """Deterministic claims are exempt regardless of sparse_facts."""
        claim = Claim(
            claim_id="CLM-S5",
            text="Raises NotImplementedError for XLS",
            kind="limitation",
            confidence=0.65,
            claim_source="deterministic",
            tier_relevance="all",
            evidence=[],
        )
        result = _filter_weak_evidence([claim], sparse_facts=True)
        assert len(result) == 1
        assert result[0].confidence == 0.65
        assert result[0].claim_source == "deterministic"

    def test_sparse_grounding_confidence_above_tc4225_threshold(self):
        """Claims elevated to llm_sparse_grounding must survive TC-4225 filter (>= 0.5)."""
        claim = _make_llm_claim("CLM-S6", "Workbook exports to xlsx", snippet="unrelated content")
        result = _filter_weak_evidence([claim], sparse_facts=True)
        assert result, "Claim must survive in sparse mode"
        assert result[0].confidence >= _TC4225_THRESHOLD, (
            f"llm_sparse_grounding confidence {result[0].confidence} must be >= TC-4225 threshold {_TC4225_THRESHOLD}"
        )

    def test_default_behavior_unchanged(self):
        """sparse_facts defaults to False — existing behavior is preserved."""
        claim = _make_llm_claim("CLM-S7", "CsvHandler supports delimiters", snippet="unrelated text here")
        result_default = _filter_weak_evidence([claim])
        result_explicit = _filter_weak_evidence([claim], sparse_facts=False)
        assert len(result_default) == len(result_explicit)
        assert result_default[0].confidence == result_explicit[0].confidence == 0.35
