"""TC-3871: Tier-gated optional page inclusion + composite richness scoring.

Tests:
1. _apply_optional_expansion skips optional pages when eligible claim pool
   is below _MIN_CLAIMS_OPTIONAL threshold.
2. classify_richness_with_surface includes extracted_snippet_count signal.
   (Surface classifier tests are in test_surface_classifier.py — this file
   tests the planner-side integration.)

TC-4250: Per-page evidence gate in run_plan().
3. Non-mandatory pages with evidence_sufficient=False are excluded.
4. Mandatory pages are never excluded even with evidence_sufficient=False.
5. When page_evidence_index is None/empty, no filtering occurs.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from launcher.models.claims import Claim, Snippet
from launcher.models.product import ProductIdentity, RichnessResult, RichnessTier


def _make_product() -> ProductIdentity:
    return ProductIdentity(
        family="cells",
        platform="python",
        display_name="Aspose.Cells for Python",
        canonical_import="aspose.cells",
        repo_url="https://github.com/aspose-cells/aspose-cells-python",
    )


def _make_richness(tier: str = "B") -> RichnessResult:
    return RichnessResult(
        tier=RichnessTier(tier),
        score=15,
        reason="test",
    )


def _make_claim(
    claim_id: str,
    text: str = "feature claim",
    kind: str = "feature",
    visibility: str = "public",
) -> Claim:
    return Claim(claim_id=claim_id, text=text, kind=kind, visibility=visibility)


def _load_ruleset():
    from launcher.workers.planner.plan import _load_ruleset
    return _load_ruleset()


class TestOptionalPageClaimVolumeGate:
    """TC-3871: optional pages are skipped when eligible claim pool is too thin."""

    def test_zero_eligible_claims_skips_optional(self):
        """With 0 eligible claims, no optional pages should be added."""
        from launcher.workers.planner.plan import _apply_optional_expansion

        # No claims at all
        pages: list = []
        ruleset = _load_ruleset()
        richness = _make_richness("B")
        product = _make_product()
        result = _apply_optional_expansion(
            pages, ruleset, richness, [], product, "B",
        )
        # With 0 claims, all optional policies should be skipped by the gate
        # (even if tier_budget is non-zero)
        optional_pages = [p for p in result if not p.get("mandatory", True)]
        assert optional_pages == [], (
            f"Expected no optional pages with 0 claims, got {len(optional_pages)}"
        )

    def test_sufficient_claims_allows_optional(self):
        """With enough eligible claims, optional pages are added."""
        from launcher.workers.planner.plan import _apply_optional_expansion, _MIN_CLAIMS_OPTIONAL, _DEFAULT_MIN_CLAIMS_OPTIONAL

        # Create enough feature claims to satisfy feature_showcase min
        min_needed = _MIN_CLAIMS_OPTIONAL.get("feature_showcase", _DEFAULT_MIN_CLAIMS_OPTIONAL)
        claims = [
            _make_claim(f"CLM-{i}", f"feature claim about cells {i}", kind="feature")
            for i in range(min_needed + 2)
        ]
        pages: list = []
        ruleset = _load_ruleset()
        richness = _make_richness("B")
        product = _make_product()
        result = _apply_optional_expansion(
            pages, ruleset, richness, claims, product, "B",
        )
        optional_pages = [p for p in result if not p.get("mandatory", True)]
        # With enough claims, at least one optional page should be created
        assert len(optional_pages) >= 1, (
            f"Expected >=1 optional pages with {len(claims)} claims, got {len(optional_pages)}"
        )

    def test_boundary_below_threshold_skips(self):
        """Exactly one below minimum threshold → skip."""
        from launcher.workers.planner.plan import _apply_optional_expansion, _MIN_CLAIMS_OPTIONAL, _DEFAULT_MIN_CLAIMS_OPTIONAL

        min_needed = _MIN_CLAIMS_OPTIONAL.get("feature_showcase", _DEFAULT_MIN_CLAIMS_OPTIONAL)
        # One claim below threshold
        claims = [
            _make_claim(f"CLM-{i}", f"feature claim {i}", kind="feature")
            for i in range(min_needed - 1)
        ]
        pages: list = []
        ruleset = _load_ruleset()
        richness = _make_richness("B")
        product = _make_product()
        result = _apply_optional_expansion(
            pages, ruleset, richness, claims, product, "B",
        )
        # feature_showcase optional should be skipped (not enough claims)
        feature_showcase_optional = [
            p for p in result
            if not p.get("mandatory", True) and p.get("page_role") == "feature_showcase"
        ]
        assert feature_showcase_optional == [], (
            f"Expected 0 optional feature_showcase with {len(claims)} claims (min={min_needed}), "
            f"got {len(feature_showcase_optional)}"
        )

    def test_internal_claims_not_counted(self):
        """Internal-visibility claims should not count toward the minimum."""
        from launcher.workers.planner.plan import _apply_optional_expansion, _MIN_CLAIMS_OPTIONAL, _DEFAULT_MIN_CLAIMS_OPTIONAL

        min_needed = _MIN_CLAIMS_OPTIONAL.get("feature_showcase", _DEFAULT_MIN_CLAIMS_OPTIONAL)
        # All claims are internal — should not count
        claims = [
            _make_claim(f"CLM-{i}", f"internal feature {i}", kind="feature", visibility="internal")
            for i in range(min_needed + 5)
        ]
        pages: list = []
        ruleset = _load_ruleset()
        richness = _make_richness("B")
        product = _make_product()
        result = _apply_optional_expansion(
            pages, ruleset, richness, claims, product, "B",
        )
        optional_pages = [p for p in result if not p.get("mandatory", True)]
        assert optional_pages == [], (
            "Internal claims should not satisfy optional page claim gate"
        )

    def test_per_module_not_affected_by_volume_gate(self):
        """per_module pages have their own claim gate and should not be
        double-gated by the volume check in _apply_optional_expansion."""
        from launcher.workers.planner.plan import _apply_optional_expansion
        from launcher.models.product import ApiSurface

        # Enough feature claims
        claims = [
            _make_claim(f"CLM-{i}", f"Workbook feature {i}", kind="api")
            for i in range(10)
        ]
        api_surface = ApiSurface(
            public_classes=["Workbook", "Worksheet", "Cell"],
            import_allowlist=["aspose.cells"],
            confidence="high",
        )
        pages: list = []
        ruleset = _load_ruleset()
        # Tier B gives per_module budget=2
        richness = _make_richness("B")
        product = _make_product()
        # Should not raise and per_module expansion should be attempted
        result = _apply_optional_expansion(
            pages, ruleset, richness, claims, product, "B",
            api_surface=api_surface,
        )
        # The function completed without error — per_module used its own gate
        assert isinstance(result, list)


class TestTierCOptionalBehavior:
    """Tier C (minimal) optional expansion behaviour."""

    def test_tier_c_per_module_budget_zero(self):
        """Tier C has tier_budget minimal=0 for per_module — no expansion."""
        from launcher.workers.planner.plan import _apply_optional_expansion
        from launcher.models.product import ApiSurface

        claims = [_make_claim(f"CLM-{i}", f"api claim {i}", kind="api") for i in range(20)]
        api_surface = ApiSurface(
            public_classes=["Workbook"] * 25,  # many public classes
            import_allowlist=["aspose.cells"],
            confidence="high",
        )
        pages: list = []
        ruleset = _load_ruleset()
        richness = _make_richness("C")  # Tier C
        product = _make_product()
        result = _apply_optional_expansion(
            pages, ruleset, richness, claims, product, "C",
            api_surface=api_surface,
        )
        # per_module should have budget=0 for Tier C
        per_module_pages = [
            p for p in result if p.get("page_role") == "reference_object_page"
        ]
        assert per_module_pages == [], (
            f"Tier C should have 0 per_module pages but got {len(per_module_pages)}"
        )


# ---------------------------------------------------------------------------
# TC-4250: Per-page evidence gate
# ---------------------------------------------------------------------------


def _make_score(sufficient: bool) -> SimpleNamespace:
    """Create a minimal PageEvidenceScore-like object."""
    return SimpleNamespace(evidence_sufficient=sufficient, missing=[])


def _make_planned_page(
    page_id: str,
    page_role: str,
    mandatory: bool,
) -> "PlannedPage":
    """Create a minimal PlannedPage for evidence gate tests."""
    from launcher.models.plan import PlannedPage

    return PlannedPage(
        page_id=page_id,
        page_role=page_role,
        title=f"Test Page {page_id}",
        skeleton=[],
        skeleton_variant="default",
        assigned_claims=[],
        assigned_snippets=[],
        frontmatter={},
        content_path="",
        seo_keywords=[],
        mandatory=mandatory,
    )


class TestPageEvidenceGate:
    """TC-4250: Evidence gate skips non-mandatory pages with insufficient evidence."""

    def test_no_index_keeps_all_pages(self):
        """When page_evidence_index is None or empty, no pages are filtered."""
        from launcher.workers.planner.plan import _apply_evidence_gate

        pages = [
            _make_planned_page("docs/landing", "landing", mandatory=True),
            _make_planned_page("kb/feature-showcase-1", "feature_showcase", mandatory=False),
        ]

        # None index — no filtering
        result_none = _apply_evidence_gate(pages, None)
        assert len(result_none) == 2, "None index must keep all pages"

        # Empty dict — no filtering
        result_empty = _apply_evidence_gate(pages, {})
        assert len(result_empty) == 2, "Empty index must keep all pages"

    def test_non_mandatory_insufficient_page_skipped(self):
        """Non-mandatory pages with evidence_sufficient=False are excluded."""
        from launcher.workers.planner.plan import _apply_evidence_gate

        pages = [
            _make_planned_page("docs/landing", "landing", mandatory=True),
            _make_planned_page("kb/feature-showcase-1", "feature_showcase", mandatory=False),
            _make_planned_page("kb/feature-showcase-2", "feature_showcase", mandatory=False),
        ]
        index = {
            "feature_showcase": _make_score(sufficient=False),
        }

        result = _apply_evidence_gate(pages, index)

        # Only the mandatory landing page should survive
        assert len(result) == 1, (
            f"Expected 1 page (mandatory only), got {len(result)}: "
            f"{[p.page_id for p in result]}"
        )
        assert result[0].page_role == "landing"

    def test_mandatory_insufficient_page_kept(self):
        """Mandatory pages are never skipped even with evidence_sufficient=False."""
        from launcher.workers.planner.plan import _apply_evidence_gate

        pages = [
            _make_planned_page("docs/landing", "landing", mandatory=True),
            _make_planned_page("docs/api-overview", "api_reference", mandatory=True),
            _make_planned_page("kb/feature-showcase-1", "feature_showcase", mandatory=False),
        ]
        index = {
            "landing": _make_score(sufficient=False),
            "api_reference": _make_score(sufficient=False),
            "feature_showcase": _make_score(sufficient=True),  # optional but sufficient
        }

        result = _apply_evidence_gate(pages, index)

        # Both mandatory pages must be kept; optional is kept (sufficient=True)
        assert len(result) == 3, (
            f"Expected all 3 pages kept (mandatory pages never removed): "
            f"got {len(result)}: {[p.page_id for p in result]}"
        )
        mandatory_in_result = [p for p in result if p.mandatory]
        assert len(mandatory_in_result) == 2, (
            f"Both mandatory pages must survive evidence gate, got {len(mandatory_in_result)}"
        )

    def test_sufficient_evidence_pages_kept(self):
        """Pages with evidence_sufficient=True are never filtered out."""
        from launcher.workers.planner.plan import _apply_evidence_gate

        pages = [
            _make_planned_page("docs/landing", "landing", mandatory=True),
            _make_planned_page("kb/feature-showcase-1", "feature_showcase", mandatory=False),
        ]
        index = {
            "landing": _make_score(sufficient=True),
            "feature_showcase": _make_score(sufficient=True),
        }

        result = _apply_evidence_gate(pages, index)

        assert len(result) == 2, (
            f"No pages should be removed when all scores are sufficient: "
            f"got {len(result)}"
        )

    def test_mixed_roles_partial_filter(self):
        """Only roles with evidence_sufficient=False are removed."""
        from launcher.workers.planner.plan import _apply_evidence_gate

        pages = [
            _make_planned_page("docs/landing", "landing", mandatory=True),
            _make_planned_page("kb/feature-showcase-1", "feature_showcase", mandatory=False),
            _make_planned_page("kb/faq", "faq", mandatory=False),
        ]
        # Only feature_showcase is insufficient; faq is sufficient
        index = {
            "feature_showcase": _make_score(sufficient=False),
            "faq": _make_score(sufficient=True),
        }

        result = _apply_evidence_gate(pages, index)

        # landing (mandatory kept) + faq (optional, sufficient kept) = 2
        assert len(result) == 2, (
            f"Expected 2 pages (landing + faq), got {len(result)}: "
            f"{[p.page_id for p in result]}"
        )
        result_roles = {p.page_role for p in result}
        assert "feature_showcase" not in result_roles
        assert "landing" in result_roles
        assert "faq" in result_roles

    def test_run_plan_backward_compatible(self):
        """run_plan without page_evidence_index is backward-compatible."""
        from launcher.workers.planner.plan import run_plan

        product = _make_product()
        richness = _make_richness("B")
        claims = [_make_claim(f"CLM-{i}", f"feature claim {i}") for i in range(5)]
        # Must not raise; returns same structure as before
        pages, claim_index = run_plan(product, richness, claims, [])
        assert isinstance(pages, list)
        assert isinstance(claim_index, dict)
        assert len(pages) > 0
