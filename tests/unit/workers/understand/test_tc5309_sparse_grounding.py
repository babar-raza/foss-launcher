"""TC-5309: Tests for removal of llm_sparse_grounding bypass in _validate_fact_binding().

After TC-5309, unbound LLM claims are DROPPED instead of being elevated to
llm_sparse_grounding (confidence=0.55). harvest_evidence_claims() provides
deterministic fallback coverage from ExtractionDatabase.
"""
from __future__ import annotations

import logging
import pytest

from launcher.workers.understand.extract._entry import _validate_fact_binding
from launcher.models.understanding import ExtractionDatabase, ApiFact, FormatFact


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_db(fact_id: str = "AF-test-001") -> ExtractionDatabase:
    return ExtractionDatabase(
        api_facts=[ApiFact(fact_id=fact_id, class_name="Workbook", member_name="save")]
    )


def _make_claim(
    claim_id: str = "CLM-001",
    source_fact_id: str = "",
    claim_source: str = "llm",
    confidence: float = 0.75,
) -> dict:
    return {
        "claim_id": claim_id,
        "text": f"Test claim {claim_id}",
        "confidence": confidence,
        "claim_source": claim_source,
        "evidence": [{"source_fact_id": source_fact_id, "source_file": "README.md"}],
    }


# ---------------------------------------------------------------------------
# TC-5309: Core drop behavior
# ---------------------------------------------------------------------------

class TestUnboundClaimDropped:

    def test_unbound_claim_is_dropped(self):
        """Unbound LLM claim (empty source_fact_id) must be dropped."""
        claims = [_make_claim(source_fact_id="")]
        result, stats = _validate_fact_binding(claims, _make_db(), bounded_mode_active=True)
        assert len(result) == 0, "TC-5309: unbound claim must be dropped"
        assert stats["unbound_claims_dropped"] == 1

    def test_hallucinated_fact_id_is_dropped(self):
        """Claim citing a fact_id not in ExtractionDatabase must be dropped."""
        claims = [_make_claim(source_fact_id="AF-HALLUCINATED-999")]
        result, stats = _validate_fact_binding(claims, _make_db(), bounded_mode_active=True)
        assert len(result) == 0, "TC-5309: claim with hallucinated fact_id must be dropped"
        assert stats["unbound_claims_dropped"] == 1

    def test_no_llm_sparse_grounding_in_output(self):
        """After TC-5309, no claim in output should have claim_source=llm_sparse_grounding."""
        claims = [
            _make_claim(claim_id="CLM-001", source_fact_id=""),
            _make_claim(claim_id="CLM-002", source_fact_id="AF-HALLUCINATED"),
        ]
        result, _ = _validate_fact_binding(claims, _make_db(), bounded_mode_active=True)
        assert result == [], "TC-5309: no llm_sparse_grounding claims in output"

    def test_bound_claim_is_kept(self):
        """Claim citing a valid fact_id must be kept unchanged."""
        claims = [_make_claim(source_fact_id="AF-test-001")]
        result, stats = _validate_fact_binding(claims, _make_db(), bounded_mode_active=True)
        assert len(result) == 1
        assert result[0]["confidence"] == 0.75
        assert result[0]["claim_source"] == "llm"
        assert stats["bound_claims"] == 1
        assert stats["unbound_claims_dropped"] == 0

    def test_mixed_bound_and_unbound(self):
        """Bound claims kept; unbound claims dropped."""
        claims = [
            _make_claim(claim_id="CLM-001", source_fact_id="AF-test-001"),  # bound
            _make_claim(claim_id="CLM-002", source_fact_id=""),              # unbound -> drop
            _make_claim(claim_id="CLM-003", source_fact_id="AF-test-001"),  # bound
        ]
        result, stats = _validate_fact_binding(claims, _make_db(), bounded_mode_active=True)
        assert len(result) == 2
        assert stats["bound_claims"] == 2
        assert stats["unbound_claims_dropped"] == 1
        returned_ids = {r["claim_id"] for r in result}
        assert "CLM-001" in returned_ids
        assert "CLM-003" in returned_ids
        assert "CLM-002" not in returned_ids


# ---------------------------------------------------------------------------
# Pre-verified claims still bypass binding check
# ---------------------------------------------------------------------------

class TestPreVerifiedClaimsBypass:

    def test_docstring_claim_not_dropped(self):
        """Docstring claims bypass binding check -- always kept."""
        claims = [_make_claim(claim_source="docstring", source_fact_id="")]
        result, stats = _validate_fact_binding(claims, _make_db(), bounded_mode_active=True)
        assert len(result) == 1
        assert stats["pre_verified_skipped"] == 1
        assert stats["unbound_claims_dropped"] == 0

    def test_llm_fallback_claim_not_dropped(self):
        """llm_fallback claims bypass binding check -- already at fallback level."""
        claims = [_make_claim(claim_source="llm_fallback", source_fact_id="")]
        result, stats = _validate_fact_binding(claims, _make_db(), bounded_mode_active=True)
        assert len(result) == 1
        assert stats["pre_verified_skipped"] == 1

    def test_deterministic_fallback_claim_not_dropped(self):
        """deterministic_fallback claims bypass binding check."""
        claims = [_make_claim(claim_source="deterministic_fallback", source_fact_id="")]
        result, stats = _validate_fact_binding(claims, _make_db(), bounded_mode_active=True)
        assert len(result) == 1
        assert stats["pre_verified_skipped"] == 1


# ---------------------------------------------------------------------------
# TC-5309: Citation rate WARNING
# ---------------------------------------------------------------------------

class TestCitationRateWarning:

    def test_low_citation_rate_emits_warning(self, caplog):
        """When < 50% claims are cited, a TC-5309 WARNING is emitted."""
        claims = [
            _make_claim(claim_id="CLM-001", source_fact_id=""),              # unbound
            _make_claim(claim_id="CLM-002", source_fact_id=""),              # unbound
            _make_claim(claim_id="CLM-003", source_fact_id="AF-test-001"),  # bound (1/3 = 33%)
        ]
        with caplog.at_level(logging.WARNING, logger="launcher.workers.understand.extract._entry"):
            _validate_fact_binding(claims, _make_db(), bounded_mode_active=True)
        warning_records = [
            r for r in caplog.records
            if r.levelno == logging.WARNING and "TC-5309" in r.message
        ]
        assert warning_records, "TC-5309: low citation rate must emit WARNING"
        assert "low_citation_rate" in warning_records[0].message

    def test_high_citation_rate_no_warning(self, caplog):
        """When >= 50% claims are cited, no TC-5309 WARNING is emitted."""
        claims = [
            _make_claim(claim_id="CLM-001", source_fact_id="AF-test-001"),  # bound
            _make_claim(claim_id="CLM-002", source_fact_id="AF-test-001"),  # bound
            _make_claim(claim_id="CLM-003", source_fact_id=""),              # unbound (2/3 = 67%)
        ]
        with caplog.at_level(logging.WARNING, logger="launcher.workers.understand.extract._entry"):
            _validate_fact_binding(claims, _make_db(), bounded_mode_active=True)
        tc5309_warnings = [
            r for r in caplog.records
            if r.levelno == logging.WARNING and "TC-5309" in r.message
        ]
        assert not tc5309_warnings, "TC-5309: 67% citation rate must NOT emit WARNING"

    def test_all_unbound_emits_warning(self, caplog):
        """All claims unbound -> 0% citation rate -> WARNING."""
        claims = [
            _make_claim(claim_id=f"CLM-{i:03d}", source_fact_id="")
            for i in range(5)
        ]
        with caplog.at_level(logging.WARNING, logger="launcher.workers.understand.extract._entry"):
            _validate_fact_binding(claims, _make_db(), bounded_mode_active=True)
        assert any("TC-5309" in r.message for r in caplog.records if r.levelno == logging.WARNING)

    def test_empty_claims_no_warning(self, caplog):
        """No eligible claims -> no citation rate warning (avoid division by zero)."""
        claims = []
        with caplog.at_level(logging.WARNING, logger="launcher.workers.understand.extract._entry"):
            _validate_fact_binding(claims, _make_db(), bounded_mode_active=True)
        assert not any(
            "TC-5309" in r.message for r in caplog.records if r.levelno == logging.WARNING
        )


# ---------------------------------------------------------------------------
# TC-5309: Stats dict has correct keys
# ---------------------------------------------------------------------------

class TestStatsDict:

    def test_stats_has_unbound_claims_dropped_key(self):
        """Stats dict must have 'unbound_claims_dropped' (not 'unbound_claims_elevated_sparse')."""
        claims = [_make_claim(source_fact_id="")]
        _, stats = _validate_fact_binding(claims, _make_db(), bounded_mode_active=True)
        assert "unbound_claims_dropped" in stats
        assert "unbound_claims_elevated_sparse" not in stats, (
            "TC-5309: old key must not be present"
        )

    def test_stats_shows_dropped_count(self):
        claims = [
            _make_claim(claim_id="CLM-001", source_fact_id=""),
            _make_claim(claim_id="CLM-002", source_fact_id=""),
        ]
        _, stats = _validate_fact_binding(claims, _make_db(), bounded_mode_active=True)
        assert stats["unbound_claims_dropped"] == 2

    def test_original_dict_not_mutated(self):
        """The input claim dict must not be mutated even when dropped."""
        original = _make_claim(source_fact_id="", confidence=0.75)
        _validate_fact_binding([original], _make_db(), bounded_mode_active=True)
        assert original["confidence"] == 0.75
        assert original.get("claim_source") == "llm"
