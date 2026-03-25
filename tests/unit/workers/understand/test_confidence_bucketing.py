"""TC-5171: Production-grade tests for confidence histogram bucketing.

Verifies that every canonical confidence value defined in CONFIDENCE_BY_SOURCE
lands in a named bucket, and that "other" is reserved for genuinely unrecognized
values only.  Regression coverage for the 3d/dotnet case where 8 deterministic
claims silently bucketed to "other" after TC-FIX-02 changed deterministic
confidence from 0.5 to 0.65.
"""
from __future__ import annotations

import pytest

from launcher.models.claims import Claim
from launcher.workers.understand.extract._validation import CONFIDENCE_BY_SOURCE


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_histogram(confidences: list[float]) -> dict[str, int]:
    """Reproduce the exact bucketing logic from understand/worker.py."""
    _legacy: frozenset[str] = frozenset({"0.5"})
    _canonical = {str(round(v, 2)) for v in CONFIDENCE_BY_SOURCE.values()}
    hist: dict[str, int] = {k: 0 for k in sorted(_canonical | _legacy, reverse=True)}
    hist["other"] = 0
    for conf in confidences:
        key = str(round(conf, 2))
        if key in hist:
            hist[key] += 1
        else:
            hist["other"] += 1
    return hist


def _make_claim(source: str, confidence: float) -> Claim:
    return Claim(
        claim_id="test-claim",
        text="A test claim for bucketing verification.",
        kind="api",
        claim_source=source,
        confidence=confidence,
    )


# ---------------------------------------------------------------------------
# TC-5171-T01: each canonical source has a named bucket
# ---------------------------------------------------------------------------

class TestCanonicalSourcesBucketedCorrectly:
    """Every value in CONFIDENCE_BY_SOURCE must produce a named (non-'other') bucket."""

    @pytest.mark.parametrize("source,expected_conf", list(CONFIDENCE_BY_SOURCE.items()))
    def test_canonical_source_not_in_other(self, source: str, expected_conf: float) -> None:
        hist = _build_histogram([expected_conf])
        assert hist["other"] == 0, (
            f"Canonical source '{source}' with confidence={expected_conf} "
            f"was bucketed into 'other'. "
            f"Histogram: {hist}"
        )

    @pytest.mark.parametrize("source,expected_conf", list(CONFIDENCE_BY_SOURCE.items()))
    def test_canonical_source_in_named_bucket(self, source: str, expected_conf: float) -> None:
        expected_key = str(round(expected_conf, 2))
        hist = _build_histogram([expected_conf])
        assert hist.get(expected_key, -1) == 1, (
            f"Canonical source '{source}' with confidence={expected_conf} "
            f"should be in bucket '{expected_key}', got histogram: {hist}"
        )


# ---------------------------------------------------------------------------
# TC-5171-T02: deterministic claims go to "0.65" not "other"  (3d/dotnet regression)
# ---------------------------------------------------------------------------

class TestDeterministicConfidenceBucketing:
    """TC-FIX-02 raised deterministic confidence to 0.65; bucket must match."""

    def test_deterministic_confidence_value(self) -> None:
        assert CONFIDENCE_BY_SOURCE["deterministic"] == 0.65

    def test_deterministic_claim_bucketed_to_065(self) -> None:
        hist = _build_histogram([CONFIDENCE_BY_SOURCE["deterministic"]])
        assert hist.get("0.65", 0) == 1
        assert hist["other"] == 0

    def test_3d_dotnet_regression_8_deterministic_6_docstring(self) -> None:
        """Regression: before TC-5171, 8 deterministic claims landed in 'other'."""
        det_conf = CONFIDENCE_BY_SOURCE["deterministic"]
        doc_conf = CONFIDENCE_BY_SOURCE["docstring"]
        confs = [det_conf] * 8 + [doc_conf] * 6
        hist = _build_histogram(confs)
        assert hist.get("0.65", 0) == 8, f"Expected 8 in '0.65', got: {hist}"
        assert hist.get("1.0", 0) == 6, f"Expected 6 in '1.0', got: {hist}"
        assert hist["other"] == 0, f"Expected 0 in 'other', got: {hist}"


# ---------------------------------------------------------------------------
# TC-5171-T03: sparse grounding claims go to "0.55" not "other"
# ---------------------------------------------------------------------------

class TestSparseGroundingConfidenceBucketing:
    """BBN-02 added llm_sparse_grounding at 0.55; bucket must match."""

    def test_sparse_grounding_confidence_value(self) -> None:
        assert CONFIDENCE_BY_SOURCE["llm_sparse_grounding"] == 0.55

    def test_sparse_grounding_claim_bucketed_to_055(self) -> None:
        hist = _build_histogram([CONFIDENCE_BY_SOURCE["llm_sparse_grounding"]])
        assert hist.get("0.55", 0) == 1
        assert hist["other"] == 0


# ---------------------------------------------------------------------------
# TC-5171-T04: "other" bucket is reserved for genuinely unrecognized values
# ---------------------------------------------------------------------------

class TestOtherBucketReservedForUnknown:
    """'other' must ONLY capture values outside the canonical + legacy set."""

    @pytest.mark.parametrize("bad_conf", [0.42, 0.48, 0.80, 0.99, 0.01])
    def test_non_canonical_goes_to_other(self, bad_conf: float) -> None:
        hist = _build_histogram([bad_conf])
        assert hist["other"] == 1, (
            f"Non-canonical confidence={bad_conf} should have gone to 'other', got: {hist}"
        )

    def test_zero_other_for_all_canonical_sources(self) -> None:
        """One claim per canonical source → 'other' must be zero."""
        confs = list(CONFIDENCE_BY_SOURCE.values())
        hist = _build_histogram(confs)
        assert hist["other"] == 0, (
            f"All-canonical claim set produced 'other'>0: {hist}"
        )


# ---------------------------------------------------------------------------
# TC-5171-T05: histogram keys include all canonical values and "other"
# ---------------------------------------------------------------------------

class TestHistogramKeyCompleteness:
    """Keys of _conf_dist must cover every CONFIDENCE_BY_SOURCE value + 'other'."""

    def test_histogram_contains_all_canonical_keys(self) -> None:
        hist = _build_histogram([])
        for conf in CONFIDENCE_BY_SOURCE.values():
            key = str(round(conf, 2))
            assert key in hist, (
                f"Canonical confidence key '{key}' missing from histogram keys: {set(hist)}"
            )

    def test_histogram_contains_other_key(self) -> None:
        hist = _build_histogram([])
        assert "other" in hist

    def test_histogram_contains_legacy_05_key(self) -> None:
        """'0.5' is a legacy bucket for pre-TC-FIX-02 backward compat."""
        hist = _build_histogram([])
        assert "0.5" in hist


# ---------------------------------------------------------------------------
# TC-5171-T06: float representation stability
# ---------------------------------------------------------------------------

class TestFloatRepresentationStability:
    """Bucketing must be stable regardless of Python float representation edge cases."""

    def test_065_rounds_to_string_065(self) -> None:
        assert str(round(0.65, 2)) == "0.65"

    def test_055_rounds_to_string_055(self) -> None:
        assert str(round(0.55, 2)) == "0.55"

    def test_same_confidence_same_bucket_across_reruns(self) -> None:
        """Deterministic: identical confidence values must always produce identical histogram."""
        confs = [0.65, 0.65, 0.75, 1.0, 0.55]
        hist1 = _build_histogram(confs)
        hist2 = _build_histogram(confs)
        assert hist1 == hist2


# ---------------------------------------------------------------------------
# TC-5171-T07: Claim model accepts llm_sparse_grounding as claim_source
# ---------------------------------------------------------------------------

class TestClaimModelAcceptsAllSources:
    """Claim.claim_source Literal must include 'llm_sparse_grounding'."""

    def test_llm_sparse_grounding_valid_claim_source(self) -> None:
        """Should not raise ValidationError."""
        claim = _make_claim("llm_sparse_grounding", 0.55)
        assert claim.claim_source == "llm_sparse_grounding"
        assert claim.confidence == 0.55

    def test_llm_corroborated_valid_claim_source(self) -> None:
        """TC-UND-210: llm_corroborated must be a valid claim_source."""
        claim = _make_claim("llm_corroborated", 0.85)
        assert claim.claim_source == "llm_corroborated"
        assert claim.confidence == 0.85


# ---------------------------------------------------------------------------
# TC-UND-210: promote_corroborated_claims
# ---------------------------------------------------------------------------


def _make_claim_with_text(
    claim_source: str,
    confidence: float,
    text: str,
    evidence_source_file: str = "",
) -> Claim:
    from launcher.models.claims import EvidenceAnchor
    ev = [EvidenceAnchor(source_file=evidence_source_file)] if evidence_source_file else []
    return Claim(
        claim_id=f"c-{claim_source}-{text[:8].replace(' ', '_')}",
        text=text,
        kind="api",
        confidence=confidence,
        claim_source=claim_source,
        evidence=ev,
    )


class TestCorroboratedPromotion:
    """TC-UND-210: promote_corroborated_claims promotes correctly and leaves others unchanged."""

    def test_llm_with_docstring_backing_promoted(self) -> None:
        """LLM claim mentioning a docstring-backed class → claim_source=llm_corroborated, confidence=0.85."""
        from launcher.workers.understand.extract._linking import promote_corroborated_claims

        docstring_claim = _make_claim_with_text(
            "docstring", 1.0,
            "Workbook: Represents a spreadsheet workbook.",
            evidence_source_file="docstring:Workbook",
        )
        llm_claim = _make_claim_with_text(
            "llm", 0.75,
            "Workbook supports saving to multiple file formats.",
        )
        result, promoted = promote_corroborated_claims([docstring_claim, llm_claim])

        assert promoted == 1
        llm_result = next(c for c in result if c.claim_id == llm_claim.claim_id)
        assert llm_result.claim_source == "llm_corroborated"
        assert llm_result.confidence == 0.85

    def test_llm_without_docstring_backing_unchanged(self) -> None:
        """LLM claim mentioning a class NOT backed by docstring → unchanged."""
        from launcher.workers.understand.extract._linking import promote_corroborated_claims

        llm_claim = _make_claim_with_text(
            "llm", 0.75,
            "Worksheet can be used to manipulate rows and columns.",
        )
        result, promoted = promote_corroborated_claims([llm_claim])

        assert promoted == 0
        assert result[0].claim_source == "llm"
        assert result[0].confidence == 0.75

    def test_docstring_claim_unchanged(self) -> None:
        """Docstring claims must never be modified by the promotion pass."""
        from launcher.workers.understand.extract._linking import promote_corroborated_claims

        docstring_claim = _make_claim_with_text(
            "docstring", 1.0,
            "Workbook: the main entry point.",
            evidence_source_file="docstring:Workbook",
        )
        result, promoted = promote_corroborated_claims([docstring_claim])

        assert promoted == 0
        assert result[0].claim_source == "docstring"
        assert result[0].confidence == 1.0

    def test_empty_claims_ok(self) -> None:
        """Empty input → empty output, 0 promoted."""
        from launcher.workers.understand.extract._linking import promote_corroborated_claims

        result, promoted = promote_corroborated_claims([])
        assert result == []
        assert promoted == 0

    def test_all_caps_acronym_not_promoted(self) -> None:
        """FPRPS-01: All-caps acronyms (CSV, JSON, XLSX) must NOT trigger promotion."""
        from launcher.workers.understand.extract._linking import promote_corroborated_claims

        docstring_claim = _make_claim_with_text(
            "docstring", 1.0,
            "CSV: Comma-separated values format.",
            evidence_source_file="docstring:CSV",
        )
        llm_claim = _make_claim_with_text(
            "llm", 0.75,
            "Supports CSV export for spreadsheet data.",
        )
        result, promoted = promote_corroborated_claims([docstring_claim, llm_claim])

        assert promoted == 0
        llm_result = next(c for c in result if c.claim_id == llm_claim.claim_id)
        assert llm_result.claim_source == "llm"

    def test_true_pascal_case_promoted(self) -> None:
        """FPRPS-01: True PascalCase names (Workbook, SaveFormat) must trigger promotion."""
        from launcher.workers.understand.extract._linking import promote_corroborated_claims

        docstring_claim = _make_claim_with_text(
            "docstring", 1.0,
            "Workbook: Represents a spreadsheet workbook.",
            evidence_source_file="docstring:Workbook",
        )
        llm_claim = _make_claim_with_text(
            "llm", 0.75,
            "The Workbook class supports loading spreadsheets.",
        )
        result, promoted = promote_corroborated_claims([docstring_claim, llm_claim])

        assert promoted == 1
        llm_result = next(c for c in result if c.claim_id == llm_claim.claim_id)
        assert llm_result.claim_source == "llm_corroborated"


# ---------------------------------------------------------------------------
# FPRPS-03: _SOURCE_PRIORITY dedup regression tests
# ---------------------------------------------------------------------------


class TestSourcePriorityDedup:
    """FPRPS-03: Verify _SOURCE_PRIORITY ordering ensures high-priority claims survive dedup."""

    def test_dedup_prefers_llm_corroborated_over_llm(self) -> None:
        """When two near-duplicate claims exist (llm vs llm_corroborated), dedup keeps llm_corroborated."""
        from launcher.workers.understand.extract._validation import (
            _SOURCE_PRIORITY,
            _deduplicate_claims,
        )

        shared_text = "The Workbook class provides methods to load and save spreadsheet files"
        llm_claim = Claim(
            claim_id="CLM-test-llm",
            text=shared_text,
            kind="api",
            claim_source="llm",
            confidence=CONFIDENCE_BY_SOURCE["llm"],
        )
        corroborated_claim = Claim(
            claim_id="CLM-test-corr",
            text=shared_text,
            kind="api",
            claim_source="llm_corroborated",
            confidence=CONFIDENCE_BY_SOURCE["llm_corroborated"],
        )
        # Sort exactly as _validate_and_normalize_claims does (confidence DESC, source priority, text)
        both = [llm_claim, corroborated_claim]
        both.sort(key=lambda c: (
            -c.confidence,
            _SOURCE_PRIORITY.get(c.claim_source, 99),
            c.text,
        ))
        result = _deduplicate_claims(both)

        assert len(result) == 1
        assert result[0].claim_source == "llm_corroborated"

    def test_dedup_prefers_docstring_over_llm_corroborated(self) -> None:
        """When two near-duplicate claims exist (docstring vs llm_corroborated), dedup keeps docstring."""
        from launcher.workers.understand.extract._validation import (
            _SOURCE_PRIORITY,
            _deduplicate_claims,
        )

        shared_text = "Workbook represents a spreadsheet workbook and is the main entry point"
        docstring_claim = Claim(
            claim_id="CLM-test-doc",
            text=shared_text,
            kind="api",
            claim_source="docstring",
            confidence=CONFIDENCE_BY_SOURCE["docstring"],
        )
        corroborated_claim = Claim(
            claim_id="CLM-test-corr2",
            text=shared_text,
            kind="api",
            claim_source="llm_corroborated",
            confidence=CONFIDENCE_BY_SOURCE["llm_corroborated"],
        )
        both = [corroborated_claim, docstring_claim]
        both.sort(key=lambda c: (
            -c.confidence,
            _SOURCE_PRIORITY.get(c.claim_source, 99),
            c.text,
        ))
        result = _deduplicate_claims(both)

        assert len(result) == 1
        assert result[0].claim_source == "docstring"
