"""Tests for claim-gated per_module page expansion (TC-3813)."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from launcher.models.claims import Claim
from launcher.models.plan import PlannedPage
from launcher.models.product import ApiSurface, ProductIdentity, RichnessResult, RichnessTier
from launcher.workers.planner.plan import (
    _build_class_claim_index,
    _class_name_to_slug,
    run_plan,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_product() -> ProductIdentity:
    return ProductIdentity(
        family="cells",
        platform="python",
        display_name="Aspose.Cells",
        canonical_import="aspose.cells",
        repo_url="https://github.com/aspose/cells-python",
    )


def _make_richness(tier: RichnessTier = RichnessTier.B) -> RichnessResult:
    return RichnessResult(tier=tier, score=15, reason="test")


def _make_claim(claim_id: str, text: str, kind: str = "api") -> Claim:
    return Claim(claim_id=claim_id, text=text, kind=kind)


def _make_api_surface(classes: list[str] | None = None) -> ApiSurface:
    return ApiSurface(
        public_classes=classes or [],
        import_allowlist=["aspose_cells"],
        confidence="high",
    )


def _pad_claims(claims: list[Claim], target: int = 200) -> list[Claim]:
    """Add filler claims so page budget pruning doesn't remove test-relevant pages."""
    for i in range(len(claims), target):
        claims.append(_make_claim(f"filler-{i}", f"Filler claim number {i}", kind="feature"))
    return claims


# ---------------------------------------------------------------------------
# _class_name_to_slug tests
# ---------------------------------------------------------------------------

class TestClassNameToSlug:
    """Test CamelCase → kebab-case slug conversion."""

    @pytest.mark.parametrize("cls_name, expected", [
        ("Workbook", "workbook"),
        ("WorksheetCollection", "worksheet-collection"),
        ("PDFDocument", "pdf-document"),
        ("HTMLParser", "html-parser"),
        ("XLSXReader", "xlsx-reader"),
        ("Cell", "cell"),
        ("oMath2Latex", "o-math2-latex"),
        ("CsvDocumentBackend", "csv-document-backend"),
    ])
    def test_camel_case_splitting(self, cls_name: str, expected: str) -> None:
        result = _class_name_to_slug(cls_name)
        assert result == expected

    def test_empty_name_fallback(self) -> None:
        result = _class_name_to_slug("")
        assert result.startswith("ref-")
        assert len(result) == 12  # "ref-" + 8 hex chars


# ---------------------------------------------------------------------------
# _build_class_claim_index tests
# ---------------------------------------------------------------------------

class TestBuildClassClaimIndex:
    """Test class-to-claims index construction."""

    def test_matches_class_in_claim_text(self) -> None:
        claims = [
            _make_claim("c1", "The Workbook class handles file loading"),
            _make_claim("c2", "Worksheet provides cell access"),
        ]
        classes = ["Workbook", "Worksheet", "Cell"]
        index = _build_class_claim_index(claims, classes)
        assert index["Workbook"] == ["c1"]
        assert index["Worksheet"] == ["c2"]
        # "cell" in "cell access" matches "Cell" case-insensitively (correct)
        assert index["Cell"] == ["c2"]

    def test_short_class_names_skipped(self) -> None:
        """Class names < 3 chars are skipped to avoid false positives."""
        claims = [_make_claim("c1", "The Pr class represents a paragraph run")]
        classes = ["Pr"]
        index = _build_class_claim_index(claims, classes)
        assert index["Pr"] == []

    def test_empty_claims(self) -> None:
        index = _build_class_claim_index([], ["Workbook"])
        assert index["Workbook"] == []

    def test_empty_classes(self) -> None:
        claims = [_make_claim("c1", "some text")]
        index = _build_class_claim_index(claims, [])
        assert index == {}

    def test_internal_claims_excluded(self) -> None:
        claim = Claim(claim_id="c1", text="Workbook internal detail", kind="api", visibility="internal")
        index = _build_class_claim_index([claim], ["Workbook"])
        assert index["Workbook"] == []

    def test_case_insensitive_lowercase(self) -> None:
        """Lowercase class name in claim text should still match."""
        claims = [_make_claim("c1", "the workbook class handles file loading")]
        index = _build_class_claim_index(claims, ["Workbook"])
        assert index["Workbook"] == ["c1"]

    def test_case_insensitive_uppercase(self) -> None:
        """UPPERCASE class name in claim text should still match."""
        claims = [_make_claim("c1", "WORKBOOK supports saving")]
        index = _build_class_claim_index(claims, ["Workbook"])
        assert index["Workbook"] == ["c1"]

    def test_only_eligible_kinds(self) -> None:
        """Only api, feature, example kinds are matched."""
        claims = [
            _make_claim("c1", "Workbook installs via pip", kind="install"),
            _make_claim("c2", "Workbook loads files", kind="api"),
        ]
        index = _build_class_claim_index(claims, ["Workbook"])
        assert index["Workbook"] == ["c2"]


# ---------------------------------------------------------------------------
# Integration: run_plan with per_module gating
# ---------------------------------------------------------------------------

class TestPerModuleGating:
    """Integration tests for claim-gated per_module expansion."""

    def test_no_per_module_when_zero_api_claims(self) -> None:
        """When no claims mention any class, no per_module pages are created."""
        claims = [
            _make_claim("c1", "Supports PDF export", kind="feature"),
            _make_claim("c2", "Install via pip", kind="install"),
        ]
        pages, _ = run_plan(
            _make_product(), _make_richness(), claims, [],
            api_surface=_make_api_surface(["Workbook", "Worksheet"]),
        )
        roles = {p.page_role for p in pages}
        assert "reference_object_page" not in roles

    def test_per_module_created_when_claims_exist(self) -> None:
        """When a class has >= 2 claims mentioning it, a per_module page is created."""
        claims = _pad_claims([
            _make_claim("c1", "The Workbook class loads spreadsheets", kind="api"),
            _make_claim("c2", "Workbook supports multiple formats", kind="feature"),
            _make_claim("c3", "Worksheet provides cell access", kind="api"),
        ])
        pages, _ = run_plan(
            _make_product(), _make_richness(), claims, [],
            api_surface=_make_api_surface(["Workbook", "Worksheet"]),
        )
        ref_pages = [p for p in pages if p.page_role == "reference_object_page"]
        assert len(ref_pages) == 1  # Only Workbook has >= 2 claims
        assert ref_pages[0].target_class == "Workbook"
        assert ref_pages[0].frontmatter.get("slug") == "workbook" or "workbook" in ref_pages[0].page_id

    def test_budget_caps_page_count(self) -> None:
        """Even with many viable classes, budget limits the count."""
        # Tier B → core → budget 2
        claims = [
            _make_claim(f"c{i}", f"The Class{i} does something", kind="api")
            for i in range(20)
        ] + [
            _make_claim(f"d{i}", f"Class{i} also supports features", kind="feature")
            for i in range(20)
        ]
        classes = [f"Class{i}" for i in range(20)]  # 20 classes, all with >= 2 claims
        pages, _ = run_plan(
            _make_product(), _make_richness(RichnessTier.B), claims, [],
            api_surface=_make_api_surface(classes),
        )
        ref_pages = [p for p in pages if p.page_role == "reference_object_page"]
        assert len(ref_pages) <= 2  # budget for core is 2

    def test_no_api_surface_skips_per_module(self) -> None:
        """When api_surface is None, no per_module pages are created."""
        claims = [_make_claim("c1", "Workbook loads files", kind="api")]
        pages, _ = run_plan(
            _make_product(), _make_richness(), claims, [],
            api_surface=None,
        )
        ref_pages = [p for p in pages if p.page_role == "reference_object_page"]
        assert len(ref_pages) == 0

    def test_api_reference_stays_default_when_no_subpages(self) -> None:
        """api_reference page keeps default skeleton when no per_module pages exist."""
        claims = [_make_claim("c1", "Generic feature", kind="feature")]
        pages, _ = run_plan(
            _make_product(), _make_richness(), claims, [],
            api_surface=_make_api_surface(["Workbook"]),
        )
        api_ref = [p for p in pages if p.page_role == "api_reference"]
        assert len(api_ref) == 1
        assert api_ref[0].skeleton_variant != "index"

    def test_api_reference_switches_to_index_when_subpages_exist(self) -> None:
        """api_reference page uses index skeleton when per_module pages are created."""
        claims = [
            _make_claim("c1", "The Workbook class loads spreadsheets", kind="api"),
            _make_claim("c2", "Workbook supports saving", kind="api"),
        ]
        pages, _ = run_plan(
            _make_product(), _make_richness(), claims, [],
            api_surface=_make_api_surface(["Workbook"]),
        )
        api_ref = [p for p in pages if p.page_role == "api_reference"]
        assert len(api_ref) == 1
        assert api_ref[0].skeleton_variant == "index"
        assert "Public API" in api_ref[0].skeleton

    def test_target_class_set_on_per_module_pages(self) -> None:
        """per_module pages have target_class populated."""
        claims = [
            _make_claim("c1", "The Workbook class loads spreadsheets", kind="api"),
            _make_claim("c2", "Workbook supports saving", kind="feature"),
        ]
        pages, _ = run_plan(
            _make_product(), _make_richness(), claims, [],
            api_surface=_make_api_surface(["Workbook"]),
        )
        ref_pages = [p for p in pages if p.page_role == "reference_object_page"]
        assert all(p.target_class != "" for p in ref_pages)

    def test_minimal_tier_skips_per_module(self) -> None:
        """Tier C (minimal) has budget 0, so no per_module pages regardless."""
        claims = [
            _make_claim("c1", "The Workbook class loads files", kind="api"),
            _make_claim("c2", "Workbook saves files", kind="api"),
        ]
        pages, _ = run_plan(
            _make_product(), _make_richness(RichnessTier.C), claims, [],
            api_surface=_make_api_surface(["Workbook"]),
        )
        ref_pages = [p for p in pages if p.page_role == "reference_object_page"]
        assert len(ref_pages) == 0

    def test_no_generic_fallback_slugs(self) -> None:
        """per_module pages must never have fallback slugs like 'per_module-spreadsheets-1'."""
        claims = [
            _make_claim("c1", "The Workbook class loads spreadsheets", kind="api"),
            _make_claim("c2", "Workbook supports formats", kind="feature"),
        ]
        pages, _ = run_plan(
            _make_product(), _make_richness(), claims, [],
            api_surface=_make_api_surface(["Workbook"]),
        )
        for page in pages:
            slug = page.frontmatter.get("slug", page.page_id)
            assert "per_module" not in slug, f"Generic fallback slug found: {slug}"

    def test_class_claims_prioritized_on_per_module_page(self) -> None:
        """Claims mentioning the target class should be assigned to its page."""
        claims = _pad_claims([
            _make_claim("c1", "The Workbook class loads spreadsheets", kind="api"),
            _make_claim("c2", "Workbook supports saving in multiple formats", kind="api"),
            _make_claim("c3", "Install the library via pip", kind="install"),
            _make_claim("c4", "Generic feature about file handling", kind="feature"),
            _make_claim("c5", "Another generic claim about performance", kind="feature"),
            _make_claim("c6", "Yet another claim about compatibility", kind="feature"),
        ])
        pages, assignment = run_plan(
            _make_product(), _make_richness(), claims, [],
            api_surface=_make_api_surface(["Workbook"]),
        )
        ref_pages = [p for p in pages if p.page_role == "reference_object_page"]
        assert len(ref_pages) == 1
        wb_page = ref_pages[0]
        # assigned_claims is a list of claim ID strings
        assigned_ids = wb_page.assigned_claims
        # At least one Workbook-mentioning claim must be assigned
        wb_claims_assigned = [cid for cid in ["c1", "c2"] if cid in assigned_ids]
        assert len(wb_claims_assigned) >= 1, \
            f"No Workbook-mentioning claims assigned, got: {assigned_ids}"

    def test_unrelated_claims_not_preferentially_assigned(self) -> None:
        """Claims NOT mentioning the target class should not be preferentially assigned."""
        claims = _pad_claims([
            _make_claim("c1", "The Workbook class loads spreadsheets", kind="api"),
            _make_claim("c2", "Workbook supports saving", kind="api"),
            _make_claim("c3", "Generic unrelated content about installation", kind="feature"),
            _make_claim("c4", "Another unrelated claim about licensing", kind="feature"),
        ])
        pages, assignment = run_plan(
            _make_product(), _make_richness(), claims, [],
            api_surface=_make_api_surface(["Workbook"]),
        )
        ref_pages = [p for p in pages if p.page_role == "reference_object_page"]
        assert len(ref_pages) == 1
        wb_page = ref_pages[0]
        assigned_ids = wb_page.assigned_claims
        # Workbook claims should appear before unrelated ones
        wb_indices = [assigned_ids.index(cid) for cid in ["c1", "c2"] if cid in assigned_ids]
        other_indices = [assigned_ids.index(cid) for cid in ["c3", "c4"] if cid in assigned_ids]
        if wb_indices and other_indices:
            assert max(wb_indices) < min(other_indices), \
                "Workbook claims should be ordered before unrelated claims"


# ---------------------------------------------------------------------------
# PM-05: skeleton_variant scoping + structural audit
# ---------------------------------------------------------------------------

class TestSkeletonVariantScoping:
    """Verify skeleton_variant preservation is scoped to registered variants."""

    def test_skeleton_variant_not_overridden_for_non_api_reference(self) -> None:
        """A non-api_reference page should use normal topic_tag resolution,
        even if skeleton_variant were somehow pre-set to an unregistered value."""
        claims = [
            _make_claim("c1", "The Workbook class loads spreadsheets", kind="api"),
            _make_claim("c2", "Workbook supports saving", kind="api"),
        ]
        pages, _ = run_plan(
            _make_product(), _make_richness(), claims, [],
            api_surface=_make_api_surface(["Workbook"]),
        )
        # All non-api_reference pages should have a valid skeleton_variant
        for page in pages:
            if page.page_role != "api_reference":
                assert page.skeleton_variant != "index" or page.page_role == "api_reference", \
                    f"Page {page.page_id} ({page.page_role}) unexpectedly has variant 'index'"

    def test_all_planned_page_constructions_include_target_class(self) -> None:
        """Every PlannedPage() construction in plan.py must include target_class=."""
        plan_py = Path(__file__).resolve().parent.parent / "src" / "launcher" / "workers" / "planner" / "plan.py"
        source = plan_py.read_text(encoding="utf-8")
        lines = source.splitlines()
        # Find lines containing "PlannedPage(" and extract the block until balanced parens
        construction_starts = []
        for i, line in enumerate(lines):
            if "PlannedPage(" in line and "import" not in line:
                construction_starts.append(i)
        assert len(construction_starts) >= 3, \
            f"Expected >=3 PlannedPage constructions, found {len(construction_starts)}"
        for start_line in construction_starts:
            # Collect lines until paren depth returns to 0
            block = ""
            depth = 0
            for j in range(start_line, min(start_line + 30, len(lines))):
                block += lines[j] + "\n"
                depth += lines[j].count("(") - lines[j].count(")")
                if depth <= 0:
                    break
            assert "target_class=" in block, \
                f"PlannedPage at line {start_line + 1} missing target_class="


# ---------------------------------------------------------------------------
# PM-06: slug collision robustness
# ---------------------------------------------------------------------------

class TestSlugCollisionRobustness:
    """Tests for slug fallback uniqueness and collision handling."""

    def test_slug_collision_two_same_name_classes(self) -> None:
        """Two classes producing the same slug get unique page_ids after disambiguation."""
        # Cell and CELL both produce "cell" via CamelCase splitting
        claims = []
        for i in range(4):
            claims.append(_make_claim(f"c{i}", f"The Cell class does thing {i}", kind="api"))
            claims.append(_make_claim(f"d{i}", f"The CELL class does thing {i}", kind="api"))
        pages, _ = run_plan(
            _make_product(), _make_richness(), claims, [],
            api_surface=_make_api_surface(["Cell", "CELL"]),
        )
        ref_pages = [p for p in pages if p.page_role == "reference_object_page"]
        if len(ref_pages) >= 2:
            page_ids = [p.page_id for p in ref_pages]
            assert len(set(page_ids)) == len(page_ids), \
                f"Duplicate page_ids found: {page_ids}"

    def test_slug_fallback_is_unique_per_class(self) -> None:
        """Two different empty-ish class names produce different fallback slugs."""
        slug_a = _class_name_to_slug("")
        slug_b = _class_name_to_slug(" ")
        # Both are fallbacks but should differ since input differs
        assert slug_a.startswith("ref-")
        assert slug_b.startswith("ref-")
        assert slug_a != slug_b, "Different class names must produce different fallback slugs"

    def test_deterministic_fallback(self) -> None:
        """Fallback slug is deterministic (same input → same output)."""
        slug1 = _class_name_to_slug("")
        slug2 = _class_name_to_slug("")
        assert slug1 == slug2
