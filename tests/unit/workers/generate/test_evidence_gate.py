"""TC-5156: Tests for the pre-generation evidence adequacy gate."""
from __future__ import annotations

import pytest

from launcher.models.claims import Claim, EvidenceAnchor
from launcher.models.plan import PlannedPage
from launcher.workers.generate.worker import _check_evidence_adequacy


def _make_claim(claim_id: str, kind: str = "feature") -> Claim:
    return Claim(claim_id=claim_id, text=f"Claim {claim_id}", kind=kind)


def _make_planned_page(
    page_role: str = "howto_article",
    assigned_claims: list[str] | None = None,
    assigned_snippets: list[int] | None = None,
    evidence_score: float = 1.0,
    evidence_sufficient: bool = True,
    evidence_missing: list[str] | None = None,
) -> PlannedPage:
    return PlannedPage(
        page_id=f"test-{page_role}",
        page_role=page_role,
        title=f"Test {page_role}",
        assigned_claims=assigned_claims or [],
        assigned_snippets=assigned_snippets or [],
        evidence_score=evidence_score,
        evidence_sufficient=evidence_sufficient,
        evidence_missing=evidence_missing or [],
    )


class TestEvidenceAdequacyGateSkips:
    """Test cases where the gate should REJECT the page."""

    def test_skips_howto_with_zero_snippets(self):
        """howto_article requires min 2 snippets."""
        page = _make_planned_page(
            page_role="howto_article",
            assigned_claims=[f"c{i}" for i in range(6)],
            assigned_snippets=[],  # 0 snippets
            evidence_score=0.8,
        )
        claims_by_id = {f"c{i}": _make_claim(f"c{i}") for i in range(6)}
        ok, reason = _check_evidence_adequacy(page, claims_by_id)
        assert not ok
        assert "snippets=0" in reason

    def test_skips_howto_with_one_snippet(self):
        """howto_article requires min 2 snippets."""
        page = _make_planned_page(
            page_role="howto_article",
            assigned_claims=[f"c{i}" for i in range(6)],
            assigned_snippets=[1],  # only 1
            evidence_score=0.8,
        )
        claims_by_id = {f"c{i}": _make_claim(f"c{i}") for i in range(6)}
        ok, reason = _check_evidence_adequacy(page, claims_by_id)
        assert not ok
        assert "snippets=1" in reason

    def test_skips_when_evidence_sufficient_false(self):
        page = _make_planned_page(
            page_role="reference_object_page",
            assigned_claims=[f"c{i}" for i in range(10)],
            assigned_snippets=[1, 2, 3],
            evidence_score=0.9,
            evidence_sufficient=False,
            evidence_missing=["no_docstrings"],
        )
        claims_by_id = {f"c{i}": _make_claim(f"c{i}") for i in range(10)}
        ok, reason = _check_evidence_adequacy(page, claims_by_id)
        assert not ok
        assert "evidence_sufficient=False" in reason
        assert "no_docstrings" in reason

    def test_skips_low_evidence_score(self):
        page = _make_planned_page(
            page_role="howto_article",
            assigned_claims=[f"c{i}" for i in range(6)],
            assigned_snippets=[1, 2, 3],
            evidence_score=0.1,  # below 0.6 threshold
        )
        claims_by_id = {f"c{i}": _make_claim(f"c{i}") for i in range(6)}
        ok, reason = _check_evidence_adequacy(page, claims_by_id)
        assert not ok
        assert "evidence_score=" in reason

    def test_skips_too_few_claims(self):
        """howto_article requires min 5 claims."""
        page = _make_planned_page(
            page_role="howto_article",
            assigned_claims=["c1", "c2"],  # only 2, need 5
            assigned_snippets=[1, 2, 3],
            evidence_score=0.8,
        )
        claims_by_id = {"c1": _make_claim("c1"), "c2": _make_claim("c2")}
        ok, reason = _check_evidence_adequacy(page, claims_by_id)
        assert not ok
        assert "claims=2" in reason

    def test_skips_faq_without_limitation_claims(self):
        """FAQ pages need 3+ limitation/troubleshoot claims."""
        page = _make_planned_page(
            page_role="faq",
            assigned_claims=[f"c{i}" for i in range(5)],
            assigned_snippets=[],
            evidence_score=0.8,
        )
        # All feature claims, no limitation
        claims_by_id = {f"c{i}": _make_claim(f"c{i}", kind="feature") for i in range(5)}
        ok, reason = _check_evidence_adequacy(page, claims_by_id)
        assert not ok
        assert "faq_limitation_claims=0" in reason

    def test_skips_faq_with_insufficient_limitation_claims(self):
        page = _make_planned_page(
            page_role="faq",
            assigned_claims=["c0", "c1", "c2", "c3", "c4"],
            assigned_snippets=[],
            evidence_score=0.8,
        )
        claims_by_id = {
            "c0": _make_claim("c0", kind="limitation"),
            "c1": _make_claim("c1", kind="limitation"),
            "c2": _make_claim("c2", kind="feature"),
            "c3": _make_claim("c3", kind="feature"),
            "c4": _make_claim("c4", kind="feature"),
        }
        ok, reason = _check_evidence_adequacy(page, claims_by_id)
        assert not ok
        assert "faq_limitation_claims=2" in reason

    def test_skips_blog_announcement_with_zero_snippets(self):
        """blog_announcement requires min 1 snippet."""
        page = _make_planned_page(
            page_role="blog_announcement",
            assigned_claims=[f"c{i}" for i in range(6)],
            assigned_snippets=[],
            evidence_score=0.8,
        )
        claims_by_id = {f"c{i}": _make_claim(f"c{i}") for i in range(6)}
        ok, reason = _check_evidence_adequacy(page, claims_by_id)
        assert not ok
        assert "snippets=0" in reason


class TestEvidenceAdequacyGatePasses:
    """Test cases where the gate should ACCEPT the page."""

    def test_passes_reference_page_with_claims_no_snippets(self):
        """reference_object_page has min_snippets=0."""
        page = _make_planned_page(
            page_role="reference_object_page",
            assigned_claims=[f"c{i}" for i in range(10)],
            assigned_snippets=[],
            evidence_score=0.8,
        )
        claims_by_id = {f"c{i}": _make_claim(f"c{i}") for i in range(10)}
        ok, reason = _check_evidence_adequacy(page, claims_by_id)
        assert ok
        assert reason == ""

    def test_passes_howto_with_sufficient_evidence(self):
        page = _make_planned_page(
            page_role="howto_article",
            assigned_claims=[f"c{i}" for i in range(6)],
            assigned_snippets=[1, 2, 3],
            evidence_score=0.8,
        )
        claims_by_id = {f"c{i}": _make_claim(f"c{i}") for i in range(6)}
        ok, reason = _check_evidence_adequacy(page, claims_by_id)
        assert ok
        assert reason == ""

    def test_passes_faq_with_enough_limitation_claims(self):
        page = _make_planned_page(
            page_role="faq",
            assigned_claims=["c0", "c1", "c2", "c3", "c4"],
            assigned_snippets=[],
            evidence_score=0.8,
        )
        claims_by_id = {
            "c0": _make_claim("c0", kind="limitation"),
            "c1": _make_claim("c1", kind="troubleshoot"),
            "c2": _make_claim("c2", kind="limitation"),
            "c3": _make_claim("c3", kind="feature"),
            "c4": _make_claim("c4", kind="feature"),
        }
        ok, reason = _check_evidence_adequacy(page, claims_by_id)
        assert ok

    def test_passes_installation_with_minimal_evidence(self):
        """installation has low thresholds: 2 claims, 1 snippet, 0.3 score."""
        page = _make_planned_page(
            page_role="installation",
            assigned_claims=["c1", "c2"],
            assigned_snippets=[1],
            evidence_score=0.5,
        )
        claims_by_id = {"c1": _make_claim("c1"), "c2": _make_claim("c2")}
        ok, reason = _check_evidence_adequacy(page, claims_by_id)
        assert ok

    def test_passes_unknown_role_with_defaults(self):
        """Unknown roles use defaults: 2 claims, 0 snippets, 0.3 score."""
        page = _make_planned_page(
            page_role="some_unknown_role",
            assigned_claims=["c1", "c2", "c3"],
            assigned_snippets=[],
            evidence_score=0.5,
        )
        claims_by_id = {f"c{i}": _make_claim(f"c{i}") for i in range(1, 4)}
        ok, reason = _check_evidence_adequacy(page, claims_by_id)
        assert ok


class TestEvidenceAdequacyGateEdgeCases:
    """Edge cases and boundary conditions."""

    def test_exact_threshold_passes(self):
        """Evidence score exactly at threshold should pass."""
        page = _make_planned_page(
            page_role="howto_article",
            assigned_claims=[f"c{i}" for i in range(5)],
            assigned_snippets=[1, 2],
            evidence_score=0.6,  # exactly at threshold
        )
        claims_by_id = {f"c{i}": _make_claim(f"c{i}") for i in range(5)}
        ok, _ = _check_evidence_adequacy(page, claims_by_id)
        # >= threshold should pass
        assert ok

    def test_just_below_threshold_fails(self):
        page = _make_planned_page(
            page_role="howto_article",
            assigned_claims=[f"c{i}" for i in range(5)],
            assigned_snippets=[1, 2],
            evidence_score=0.599,
        )
        claims_by_id = {f"c{i}": _make_claim(f"c{i}") for i in range(5)}
        ok, _ = _check_evidence_adequacy(page, claims_by_id)
        assert not ok

    def test_faq_with_missing_claim_ids_in_lookup(self):
        """Claims referenced in assigned_claims but missing from claims_by_id should not crash."""
        page = _make_planned_page(
            page_role="faq",
            assigned_claims=["c_missing1", "c_missing2", "c_exists"],
            assigned_snippets=[],
            evidence_score=0.8,
        )
        claims_by_id = {"c_exists": _make_claim("c_exists", kind="limitation")}
        ok, reason = _check_evidence_adequacy(page, claims_by_id)
        assert not ok
        assert "faq_limitation_claims=1" in reason

    def test_first_failing_dimension_reported(self):
        """When multiple dimensions fail, the first one detected is reported."""
        page = _make_planned_page(
            page_role="howto_article",
            assigned_claims=[],
            assigned_snippets=[],
            evidence_score=0.0,
            evidence_sufficient=False,
            evidence_missing=["no_claims"],
        )
        ok, reason = _check_evidence_adequacy(page, {})
        assert not ok
        # evidence_sufficient is checked first
        assert "evidence_sufficient=False" in reason
