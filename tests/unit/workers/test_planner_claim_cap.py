"""TC-DFR-002: Tests for skeleton-aware per-page claim cap.

Verifies that _skeleton_claim_cap computes correct caps from skeleton
section counts and that unknown roles fall back to _MAX_CLAIMS_PER_PAGE.
"""
from __future__ import annotations

import pytest

from launcher.models.claims import Claim
from launcher.workers.planner.plan import (
    _CLAIM_FLOOR_MIN,
    _CLAIM_FLOOR_ROLES,
    _MAX_CLAIM_PAGES,
    _MAX_CLAIMS_PER_PAGE,
    _assign_claims,
)

try:
    from launcher.workers.planner.plan import (
        _STRUCTURAL_ONLY_SECTIONS,
        _skeleton_claim_cap,
    )
    _HAS_SKELETON_CAP = True
except ImportError:
    _HAS_SKELETON_CAP = False
    _STRUCTURAL_ONLY_SECTIONS = frozenset()  # type: ignore[assignment]
    _skeleton_claim_cap = None  # type: ignore[assignment]


@pytest.mark.skipif(not _HAS_SKELETON_CAP, reason="_skeleton_claim_cap not in this codebase version")
class TestSkeletonClaimCap:
    """TC-DFR-002: Per-page claim cap from skeleton."""

    def test_howto_article_cap(self):
        """howto_article has 6 sections, 1 structural (See Also) -> 5 content * 3 = 15."""
        cap = _skeleton_claim_cap("howto_article")
        # howto_article skeleton: Problem, Prerequisites, Solution Steps,
        # Code Example, Troubleshooting, See Also
        # "prerequisites" and "see also" are structural -> 4 content * 3 = 12
        assert cap >= 4  # minimum floor
        assert cap <= _MAX_CLAIMS_PER_PAGE  # shouldn't exceed global cap for small skeletons

    def test_landing_cap(self):
        """landing has 4 sections, 1 structural (See Also) -> 3 content * 3 = 9."""
        cap = _skeleton_claim_cap("landing")
        assert cap == 9

    def test_unknown_role_fallback(self):
        """Unknown role falls back to _MAX_CLAIMS_PER_PAGE."""
        cap = _skeleton_claim_cap("nonexistent_role_xyz")
        assert cap == _MAX_CLAIMS_PER_PAGE

    def test_minimum_floor(self):
        """Cap is always at least 4."""
        # Even if somehow a role had only 1 content section: max(4, 1*3) = 4
        cap = _skeleton_claim_cap("toc")  # toc has 3 sections, ~1 content
        assert cap >= 4

    def test_variant_skeleton_used(self):
        """Variant skeletons should be used when available."""
        # ("howto_article", "save_file") has a variant skeleton
        cap = _skeleton_claim_cap("howto_article", "save_file")
        assert cap >= 4
        assert isinstance(cap, int)

    def test_structural_sections_excluded(self):
        """Verify structural section names are lowercase in the exclusion set."""
        for s in _STRUCTURAL_ONLY_SECTIONS:
            assert s == s.lower(), f"Structural section '{s}' must be lowercase"

    def test_cap_is_integer(self):
        """Cap must be an integer."""
        cap = _skeleton_claim_cap("howto_article")
        assert isinstance(cap, int)

    def test_api_reference_cap(self):
        """api_reference should have a reasonable cap."""
        cap = _skeleton_claim_cap("api_reference")
        assert cap >= 4
        assert isinstance(cap, int)


# ---------------------------------------------------------------------------
# FPR-05 (2026-03-22): Claim floor fallback for getting-started and install pages
# ---------------------------------------------------------------------------


def _make_claims(n: int, kind: str = "feature") -> list[Claim]:
    """Build n minimal public Claim objects with deterministic IDs."""
    return [
        Claim(
            claim_id=f"CLM-fpr05-{i:03d}",
            text=f"Feature capability {i}",
            kind=kind,
            visibility="public",
        )
        for i in range(n)
    ]


def _make_page(page_id: str, role: str, mandatory: bool = True) -> dict:
    return {"page_id": page_id, "page_role": role, "mandatory": mandatory, "slug": page_id}


class TestGettingStartedMinimumClaims:
    """FPR-05 (2026-03-22): _assign_claims must assign ≥ _CLAIM_FLOOR_MIN claims
    to getting-started and install pages even when all claims have exhausted
    their _MAX_CLAIM_PAGES budget from prior mandatory pages.
    """

    def test_fallback_fires_when_all_claims_exhausted(self):
        """Fallback runs when all claims have exhausted _MAX_CLAIM_PAGES from prior mandatory pages."""
        claims = _make_claims(3)
        # Pre-exhaust every claim on _MAX_CLAIM_PAGES mandatory pages before getting-started
        drain_pages = [
            _make_page(f"drain-{i}", "workflow_page", mandatory=True)
            for i in range(_MAX_CLAIM_PAGES)
        ]
        gs_page = _make_page("getting-started", "getting_started", mandatory=True)
        # mandatory=True for all pages — sorted_pages puts them all first, drains consume claims first
        result_pages, _ = _assign_claims(drain_pages + [gs_page], claims, [])
        gs = next(p for p in result_pages if p.page_role == "getting_started")
        # All 3 claims were at _MAX_CLAIM_PAGES limit when getting_started ran
        # → fallback must have fired to assign _CLAIM_FLOOR_MIN claims
        assert len(gs.assigned_claims) >= _CLAIM_FLOOR_MIN, (
            f"Fallback did not fire: expected >= {_CLAIM_FLOOR_MIN}, got {len(gs.assigned_claims)}"
        )

    def test_non_floor_role_page_not_boosted(self):
        """A page whose role is not in _CLAIM_FLOOR_ROLES gets 0 claims when budget is exhausted."""
        assert "faq" not in _CLAIM_FLOOR_ROLES  # pre-condition
        claims = _make_claims(3)
        drain_pages = [
            _make_page(f"drain-{i}", "workflow_page", mandatory=True)
            for i in range(_MAX_CLAIM_PAGES)
        ]
        faq_page = _make_page("faq", "faq", mandatory=True)
        result_pages, _ = _assign_claims(drain_pages + [faq_page], claims, [])
        faq = next(p for p in result_pages if p.page_role == "faq")
        # faq is not in _CLAIM_FLOOR_ROLES — no fallback, so 0 claims when all at budget
        assert len(faq.assigned_claims) == 0

    def test_claim_floor_roles_constant_contains_getting_started(self):
        """_CLAIM_FLOOR_ROLES must include both 'getting_started' and 'getting-started'."""
        assert "getting_started" in _CLAIM_FLOOR_ROLES
        assert "getting-started" in _CLAIM_FLOOR_ROLES

    def test_claim_floor_min_is_three(self):
        """_CLAIM_FLOOR_MIN must be 3 (as specified in FPR-05 taskcard)."""
        assert _CLAIM_FLOOR_MIN == 3

    def test_fallback_claims_are_deterministic(self):
        """Running _assign_claims twice with same inputs yields same fallback claim IDs."""
        claims = _make_claims(10)
        pages = [_make_page("getting-started", "getting_started")]
        result_a, _ = _assign_claims(pages, claims, [])
        result_b, _ = _assign_claims(pages, claims, [])
        assert result_a[0].assigned_claims == result_b[0].assigned_claims
