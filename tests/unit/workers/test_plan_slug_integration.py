"""Tests for evidence-aware slug integration in the planner (TC-3781, TC-3824)."""
from __future__ import annotations

import pytest

from launcher.models.claims import Claim, Snippet
from launcher.models.plan import PlannedPage
from launcher.models.product import ProductIdentity, RichnessResult, RichnessTier
from launcher.models.understanding import ProductEvidence
from launcher.workers.planner.plan import (
    _apply_optional_expansion,
    _build_frontmatter,
    _derive_optional_slug,
    _disambiguate_slugs,
    _enumerate_mandatory_pages,
    _expand_slug,
    _load_ruleset,
    _policy_kind_to_role,
    _quality_check_slugs,
    _refine_page_slugs,
    _slug_fallback,
    run_plan,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_product(
    family: str = "cells",
    platform: str = "python",
    canonical_import: str | None = None,
    runtime_import: str = "",
) -> ProductIdentity:
    return ProductIdentity(
        display_name=f"Aspose.{family.title()} for {platform.title()}",
        family=family,
        platform=platform,
        canonical_import=canonical_import or f"aspose.{family}",
        runtime_import=runtime_import,
        repo_url=f"https://github.com/aspose-{family}/Aspose.{family.title()}-for-{platform.title()}",
    )


def _make_richness(tier: RichnessTier = RichnessTier.A) -> RichnessResult:
    return RichnessResult(tier=tier, score=30, reason="test")


def _make_evidence(**kwargs) -> ProductEvidence:
    return ProductEvidence(**kwargs)


def _make_claim(
    text: str, kind: str = "feature", claim_id: str = "CLM-001",
) -> Claim:
    return Claim(claim_id=claim_id, text=text, kind=kind)


# ---------------------------------------------------------------------------
# Tests: KB how-to evidence-aware slugs
# ---------------------------------------------------------------------------

class TestKBHowToSlugs:
    """KB how-to pages should get evidence-enriched slugs."""

    def test_convert_slug_with_conversion_pairs(self) -> None:
        """When product_evidence has conversion_pairs, the convert how-to
        slug should include source and target formats."""
        product = _make_product("cells")
        evidence = _make_evidence(
            conversion_pairs=[{"source": "XLSX", "target": "CSV"}],
            supported_formats=["XLSX", "CSV", "PDF"],
        )
        richness = _make_richness(RichnessTier.A)
        claims = [_make_claim("Convert spreadsheets", kind="format")]
        snippets: list[Snippet] = []

        pages, _ = run_plan(
            product, richness, claims, snippets,
            product_evidence=evidence,
        )

        # Find the convert how-to page
        convert_pages = [
            p for p in pages
            if "convert" in p.page_id.lower() and p.page_role == "howto_article"
        ]
        assert convert_pages, "Expected a convert how-to page"
        slug = convert_pages[0].page_id.split("/", 1)[-1]
        # Evidence-aware slug should contain format info
        assert "xlsx" in slug.lower() or "csv" in slug.lower() or "spreadsheets" in slug.lower(), (
            f"Expected evidence-enriched slug, got: {slug}"
        )

    def test_convert_slug_without_evidence_preserves_original(self) -> None:
        """Without product_evidence, slugs remain as-is (backward compat)."""
        product = _make_product("cells")
        richness = _make_richness(RichnessTier.A)
        claims = [_make_claim("Some feature", kind="feature")]
        snippets: list[Snippet] = []

        pages, _ = run_plan(product, richness, claims, snippets)

        convert_pages = [
            p for p in pages
            if "convert" in p.page_id.lower() and p.page_role == "howto_article"
        ]
        assert convert_pages
        slug = convert_pages[0].page_id.split("/", 1)[-1]
        assert slug == "how-to-convert-formats"

    def test_open_slug_with_evidence(self) -> None:
        """Open how-to should get family keyword in slug."""
        product = _make_product("pdf")
        evidence = _make_evidence(supported_formats=["PDF", "DOCX"])
        richness = _make_richness(RichnessTier.A)
        claims = [_make_claim("Open PDF files", kind="workflow")]
        snippets: list[Snippet] = []

        pages, _ = run_plan(
            product, richness, claims, snippets,
            product_evidence=evidence,
        )

        open_pages = [
            p for p in pages
            if "open" in p.page_id.lower() or "load" in p.page_id.lower()
        ]
        assert open_pages
        slug = open_pages[0].page_id.split("/", 1)[-1]
        # Should contain family keyword (pdf-files) or platform
        assert "pdf" in slug.lower(), f"Expected pdf in slug, got: {slug}"


# ---------------------------------------------------------------------------
# Tests: Blog evidence-aware slugs
# ---------------------------------------------------------------------------

class TestBlogSlugs:
    """Blog feature_blog pages should get workflow-derived slugs."""

    def test_blog_slug_with_workflow_evidence(self) -> None:
        """When product_evidence has workflows with conversion intent,
        the feature_blog slug should reflect the top workflow."""
        product = _make_product("cells")
        evidence = _make_evidence(
            workflows=[{
                "name": "convert-xlsx-to-csv",
                "title": "Convert XLSX to CSV",
                "tags": ["convert"],
            }],
        )
        richness = _make_richness(RichnessTier.A)
        claims = [_make_claim("Feature", kind="feature")]
        snippets: list[Snippet] = []

        pages, _ = run_plan(
            product, richness, claims, snippets,
            product_evidence=evidence,
        )

        blog_pages = [
            p for p in pages
            if p.page_role == "feature_blog"
        ]
        assert blog_pages
        slug = blog_pages[0].page_id.split("/", 1)[-1]
        # Should NOT be the generic "{family}-key-features"
        assert slug != "cells-key-features", (
            f"Expected evidence-enriched blog slug, got generic: {slug}"
        )

    def test_blog_slug_without_evidence_keeps_template(self) -> None:
        """Without evidence, blog slug remains template-based."""
        product = _make_product("cells")
        richness = _make_richness(RichnessTier.A)
        claims = [_make_claim("Feature", kind="feature")]
        snippets: list[Snippet] = []

        pages, _ = run_plan(product, richness, claims, snippets)

        blog_pages = [p for p in pages if p.page_role == "feature_blog"]
        assert blog_pages
        slug = blog_pages[0].page_id.split("/", 1)[-1]
        assert slug == "cells-key-features"


# ---------------------------------------------------------------------------
# Tests: Optional page slug derivation
# ---------------------------------------------------------------------------

class TestOptionalPageSlugs:
    """Optional pages should get claim-derived slugs, not generic ones."""

    def test_optional_slug_with_claims_and_evidence(self) -> None:
        """_derive_optional_slug should produce semantic slug from claims."""
        product = _make_product("cells")
        evidence = _make_evidence(supported_formats=["XLSX"])
        claims = [
            _make_claim(
                "The library provides chart rendering capabilities",
                kind="feature", claim_id="CLM-001",
            ),
        ]

        slug = _derive_optional_slug(
            "feature_showcase", 0, 3, product, evidence, claims,
        )
        assert slug != "feature_showcase-1", (
            f"Expected meaningful slug, got: {slug}"
        )
        assert "feature_showcase" not in slug or "spreadsheets" in slug

    def test_optional_slug_without_evidence_preserves_original(self) -> None:
        """Without evidence, original pattern preserved."""
        slug = _derive_optional_slug(
            "feature_showcase", 0, 3, None, None, [],
        )
        assert slug == "feature_showcase-1"

    def test_optional_slug_single_budget_no_index(self) -> None:
        """Single-budget optional page without evidence gets bare kind."""
        slug = _derive_optional_slug(
            "deep_dive", 0, 1, None, None, [],
        )
        assert slug == "deep_dive"

    def test_optional_slug_fallback_with_family_keyword(self) -> None:
        """When evidence exists but no relevant claims, falls back with
        family keyword instead of bare number."""
        product = _make_product("cells")
        evidence = _make_evidence()
        # No claims that match feature_showcase eligible kinds
        claims: list[Claim] = []

        slug = _derive_optional_slug(
            "feature_showcase", 0, 3, product, evidence, claims,
        )
        assert "spreadsheets" in slug, f"Expected family keyword in slug: {slug}"

    def test_no_feature_showcase_N_pattern_in_plan(self) -> None:
        """Full plan with evidence should not produce feature_showcase-N slugs."""
        product = _make_product("cells")
        evidence = _make_evidence(supported_formats=["XLSX", "CSV"])
        richness = _make_richness(RichnessTier.A)
        claims = [
            _make_claim(
                "Advanced chart rendering with multiple chart types",
                kind="feature", claim_id=f"CLM-{i:03d}",
            )
            for i in range(10)
        ]
        snippets: list[Snippet] = []

        pages, _ = run_plan(
            product, richness, claims, snippets,
            product_evidence=evidence,
        )

        for page in pages:
            slug = page.page_id.split("/", 1)[-1]
            assert not slug.endswith("-1") or "spreadsheets" in slug or "cells" in slug, (
                f"Unexpected generic slug pattern: {slug}"
            )


# ---------------------------------------------------------------------------
# Tests: Backward compatibility
# ---------------------------------------------------------------------------

class TestBackwardCompatibility:
    """Planner must work identically when product_evidence is None."""

    def test_run_plan_without_evidence(self) -> None:
        """run_plan with no product_evidence should produce valid plan."""
        product = _make_product("cells")
        richness = _make_richness(RichnessTier.B)
        claims = [
            _make_claim("Feature A", kind="feature", claim_id="CLM-001"),
            _make_claim("Feature B", kind="feature", claim_id="CLM-002"),
        ]
        snippets: list[Snippet] = []

        pages, index = run_plan(product, richness, claims, snippets)

        assert len(pages) > 0
        # All pages should have valid page_ids
        for page in pages:
            assert "/" in page.page_id
            assert page.page_role

    def test_run_plan_with_empty_evidence(self) -> None:
        """run_plan with empty ProductEvidence should produce valid plan."""
        product = _make_product("cells")
        evidence = _make_evidence()
        richness = _make_richness(RichnessTier.B)
        claims = [
            _make_claim("Feature A", kind="feature", claim_id="CLM-001"),
            _make_claim("Feature B", kind="feature", claim_id="CLM-002"),
        ]
        snippets: list[Snippet] = []

        pages, index = run_plan(
            product, richness, claims, snippets,
            product_evidence=evidence,
        )

        assert len(pages) > 0


# ---------------------------------------------------------------------------
# Tests: LLM refinement parameter acceptance
# ---------------------------------------------------------------------------

class TestLLMRefinement:
    """LLM refinement parameter is accepted but safe when None."""

    def test_llm_client_none_no_effect(self) -> None:
        """llm_client=None should not change plan output."""
        product = _make_product("cells")
        richness = _make_richness(RichnessTier.B)
        claims = [_make_claim("Feature", kind="feature")]
        snippets: list[Snippet] = []

        pages_no_llm, _ = run_plan(
            product, richness, claims, snippets, llm_client=None,
        )
        pages_default, _ = run_plan(
            product, richness, claims, snippets,
        )

        assert len(pages_no_llm) == len(pages_default)
        for a, b in zip(pages_no_llm, pages_default):
            assert a.page_id == b.page_id


# ---------------------------------------------------------------------------
# Tests: Permalink uniqueness with evidence-derived slugs
# ---------------------------------------------------------------------------

class TestPermalinkUniqueness:
    """Evidence-derived slugs must not create permalink collisions."""

    def test_no_duplicate_page_ids(self) -> None:
        """Plan should have unique page_ids even with evidence enrichment."""
        product = _make_product("cells")
        evidence = _make_evidence(
            conversion_pairs=[{"source": "XLSX", "target": "CSV"}],
            supported_formats=["XLSX", "CSV"],
        )
        richness = _make_richness(RichnessTier.A)
        claims = [
            _make_claim(f"Feature {i}", kind="feature", claim_id=f"CLM-{i:03d}")
            for i in range(20)
        ]
        snippets: list[Snippet] = []

        pages, _ = run_plan(
            product, richness, claims, snippets,
            product_evidence=evidence,
        )

        page_ids = [p.page_id for p in pages]
        assert len(page_ids) == len(set(page_ids)), (
            f"Duplicate page_ids found: {[pid for pid in page_ids if page_ids.count(pid) > 1]}"
        )


# ---------------------------------------------------------------------------
# Tests: SR-01 — Snippet-to-dict conversion for blog scoring
# ---------------------------------------------------------------------------

class TestSnippetConversion:
    """Blog scoring must work with pydantic Snippet objects (SR-01)."""

    def test_blog_slug_with_snippet_evidence(self) -> None:
        """Snippets (pydantic) should be converted to dicts for scoring."""
        product = _make_product("cells")
        evidence = _make_evidence(
            workflows=[{
                "name": "convert-xlsx-to-csv",
                "title": "Convert XLSX to CSV",
                "tags": ["convert"],
            }],
        )
        richness = _make_richness(RichnessTier.A)
        claims = [_make_claim("Convert spreadsheets", kind="format", claim_id="CLM-001")]
        snippets = [
            Snippet(
                code="import aspose.cells",
                language="python",
                claim_ids=["CLM-001"],
            ),
        ]

        # Should not raise TypeError from isinstance(snippet, dict) check
        pages, _ = run_plan(
            product, richness, claims, snippets,
            product_evidence=evidence,
        )
        assert len(pages) > 0

    def test_blog_scoring_uses_snippet_claim_ids(self) -> None:
        """Blog scoring should receive claim_ids from Snippet objects."""
        product = _make_product("cells")
        evidence = _make_evidence(
            workflows=[{
                "name": "convert-xlsx-to-csv",
                "title": "Convert XLSX to CSV",
                "tags": ["convert"],
                "claim_ids": ["CLM-001"],
            }],
        )
        richness = _make_richness(RichnessTier.A)
        claims = [_make_claim("Convert spreadsheets", kind="format", claim_id="CLM-001")]
        snippets = [
            Snippet(
                code="import aspose.cells",
                language="python",
                claim_ids=["CLM-001"],
            ),
        ]

        pages, _ = run_plan(
            product, richness, claims, snippets,
            product_evidence=evidence,
        )

        blog_pages = [p for p in pages if p.page_role == "feature_blog"]
        assert blog_pages, "Expected a feature_blog page"


# ---------------------------------------------------------------------------
# Tests: SR-02 — Slug safety validation
# ---------------------------------------------------------------------------

class TestSlugSafetyValidation:
    """Evidence-derived slugs must pass safety validation (SR-02)."""

    def test_unsafe_evidence_slug_rejected(self) -> None:
        """Slugs with doubled hyphens should be rejected, keeping original."""
        from launcher.shared.slug_engine import validate_slug_safety

        issues = validate_slug_safety("convert--xlsx--csv")
        assert len(issues) > 0, "Expected safety issues for doubled hyphens"

    def test_safe_evidence_slug_accepted(self) -> None:
        """Clean slugs should pass safety validation."""
        from launcher.shared.slug_engine import validate_slug_safety

        issues = validate_slug_safety("convert-xlsx-to-csv-python")
        assert issues == [], f"Unexpected safety issues: {issues}"


# ---------------------------------------------------------------------------
# Tests: SR-03 — Collision disambiguation
# ---------------------------------------------------------------------------

class TestCollisionDisambiguation:
    """Evidence-derived slugs must be disambiguated on collision (SR-03)."""

    def test_collision_disambiguation_appends_suffix(self) -> None:
        """Duplicate page_ids should get -2, -3 suffixes."""
        pages = [
            {"section": "kb", "page_id": "kb/how-to-convert", "slug": "how-to-convert",
             "page_role": "howto_article", "content_path": "kb/how-to-convert/index.md",
             "mandatory": True, "folder_index": False, "topic_category": "convert"},
            {"section": "kb", "page_id": "kb/how-to-convert", "slug": "how-to-convert",
             "page_role": "howto_article", "content_path": "kb/how-to-convert/index.md",
             "mandatory": True, "folder_index": False, "topic_category": "convert"},
        ]
        result = _disambiguate_slugs(pages)
        page_ids = [p["page_id"] for p in result]
        assert len(set(page_ids)) == 2, f"Expected unique page_ids, got: {page_ids}"
        assert result[0]["page_id"] == "kb/how-to-convert"
        assert result[1]["slug"] == "how-to-convert-2"

    def test_optional_pages_no_silent_drop(self) -> None:
        """Multiple optional pages with same slug get disambiguated, not dropped."""
        pages = [
            {"section": "docs", "page_id": "docs/chart-rendering", "slug": "chart-rendering",
             "page_role": "feature_showcase", "content_path": "docs/chart-rendering/index.md",
             "mandatory": False, "folder_index": False, "topic_category": None},
            {"section": "docs", "page_id": "docs/chart-rendering", "slug": "chart-rendering",
             "page_role": "feature_showcase", "content_path": "docs/chart-rendering/index.md",
             "mandatory": False, "folder_index": False, "topic_category": None},
            {"section": "docs", "page_id": "docs/chart-rendering", "slug": "chart-rendering",
             "page_role": "feature_showcase", "content_path": "docs/chart-rendering/index.md",
             "mandatory": False, "folder_index": False, "topic_category": None},
        ]
        result = _disambiguate_slugs(pages)
        assert len(result) == 3, "All 3 pages should be preserved"
        page_ids = [p["page_id"] for p in result]
        assert len(set(page_ids)) == 3, f"Expected 3 unique page_ids: {page_ids}"
        assert result[1]["slug"] == "chart-rendering-2"
        assert result[2]["slug"] == "chart-rendering-3"


# ---------------------------------------------------------------------------
# Tests: SR-06 — LLM refinement code path
# ---------------------------------------------------------------------------

class _MockLLMClient:
    """Mock LLM client for testing _refine_page_slugs via run_plan."""

    def __init__(self, response: str) -> None:
        self._response = response

    def chat_completion(self, messages: list[dict], temperature: float = 0.0) -> str:
        return self._response


class TestLLMRefinementCodePath:
    """Exercise _refine_page_slugs through run_plan with mock LLM (SR-06)."""

    def test_llm_refinement_updates_frontmatter_slug(self) -> None:
        """Valid LLM output should update frontmatter slug fields."""
        product = _make_product("cells")
        richness = _make_richness(RichnessTier.B)
        claims = [_make_claim("Feature A", kind="feature", claim_id="CLM-001")]
        snippets: list[Snippet] = []

        # First, get baseline slugs without LLM
        pages_base, _ = run_plan(product, richness, claims, snippets)
        # Collect non-toc, non-_index slugs
        base_slugs = [
            p.frontmatter.get("slug", "")
            for p in pages_base
            if p.page_role != "toc" and p.frontmatter.get("slug") != "_index"
        ]
        base_slugs = [s for s in base_slugs if s]

        if not base_slugs:
            pytest.skip("No refinable slugs in plan")

        # Mock returns cleaned versions (just first 3 words of each slug)
        refined = ["-".join(s.split("-")[:3]) or s for s in base_slugs]
        mock = _MockLLMClient("\n".join(refined))

        pages_llm, _ = run_plan(
            product, richness, claims, snippets, llm_client=mock,
        )

        # At least one slug should differ (LLM refined it)
        llm_slugs = [
            p.frontmatter.get("slug", "")
            for p in pages_llm
            if p.page_role != "toc" and p.frontmatter.get("slug") != "_index"
        ]
        llm_slugs = [s for s in llm_slugs if s]
        assert len(llm_slugs) == len(base_slugs)

    def test_llm_refinement_fallback_on_wrong_count(self) -> None:
        """When LLM returns wrong number of lines, original slugs preserved."""
        product = _make_product("cells")
        richness = _make_richness(RichnessTier.B)
        claims = [_make_claim("Feature", kind="feature")]
        snippets: list[Snippet] = []

        # Mock returns only 1 line regardless of input count
        mock = _MockLLMClient("single-slug-only")

        pages_llm, _ = run_plan(
            product, richness, claims, snippets, llm_client=mock,
        )
        pages_base, _ = run_plan(product, richness, claims, snippets)

        # Should fall back to algorithmic — same page count, slugs based on
        # strip_leading_stop_words fallback
        assert len(pages_llm) == len(pages_base)

    def test_llm_refinement_rejects_unsafe_slug(self) -> None:
        """LLM-returned slugs with special chars should be rejected."""
        product = _make_product("cells")
        richness = _make_richness(RichnessTier.B)
        claims = [_make_claim("Feature", kind="feature")]
        snippets: list[Snippet] = []

        pages_base, _ = run_plan(product, richness, claims, snippets)
        base_slugs = [
            p.frontmatter.get("slug", "")
            for p in pages_base
            if p.page_role != "toc" and p.frontmatter.get("slug") != "_index"
        ]
        base_slugs = [s for s in base_slugs if s]

        if not base_slugs:
            pytest.skip("No refinable slugs in plan")

        # Mock returns invalid slugs (with brackets, quotes)
        bad_slugs = [f"[{s}]" for s in base_slugs]
        mock = _MockLLMClient("\n".join(bad_slugs))

        pages_llm, _ = run_plan(
            product, richness, claims, snippets, llm_client=mock,
        )

        # Invalid slugs should be rejected — originals or algorithmic fallback kept
        llm_slugs = [
            p.frontmatter.get("slug", "")
            for p in pages_llm
            if p.page_role != "toc" and p.frontmatter.get("slug") != "_index"
        ]
        llm_slugs = [s for s in llm_slugs if s]
        for slug in llm_slugs:
            assert "[" not in slug and "]" not in slug, f"Unsafe slug leaked: {slug}"


# ---------------------------------------------------------------------------
# Tests: TC-3782 — HTML entity / trademark cleanup
# ---------------------------------------------------------------------------

class TestHTMLEntityCleanup:
    """Claims with HTML entities should produce clean slugs (TC-3782)."""

    def test_claim_with_html_entities_produces_clean_slug(self) -> None:
        """Claim text with &reg; should not leak 'reg' into slugs."""
        product = _make_product("cells")
        evidence = _make_evidence(supported_formats=["XLSX", "CSV"])
        richness = _make_richness(RichnessTier.A)
        claims = [
            _make_claim(
                "Print Microsoft Excel&reg; files to printers",
                kind="feature", claim_id="CLM-001",
            ),
            _make_claim(
                "Convert Excel&reg; spreadsheets to PDF",
                kind="feature", claim_id="CLM-002",
            ),
        ]
        snippets: list[Snippet] = []

        pages, _ = run_plan(
            product, richness, claims, snippets,
            product_evidence=evidence,
        )

        for page in pages:
            slug = page.page_id.split("/", 1)[-1]
            parts = slug.split("-")
            assert "reg" not in parts, (
                f"HTML entity 'reg' leaked into slug: {slug}"
            )


# ---------------------------------------------------------------------------
# Tests: TC-3800 — _refine_page_slugs safety validation
# ---------------------------------------------------------------------------

class TestRefinePageSlugsSafety:
    """LLM-refined slugs must pass validate_slug_safety (TC-3800, SR-14)."""

    def _make_pages_with_slugs(self, slugs: list[str]) -> list:
        from launcher.models.plan import PlannedPage
        return [
            PlannedPage(
                page_id=f"kb/{slug}",
                page_role="feature_showcase",
                title=slug.replace("-", " ").title(),
                frontmatter={"slug": slug, "url": f"/kb/{slug}/"},
                content_path=f"kb/{slug}",
            )
            for slug in slugs
        ]

    def test_entity_artifact_slug_rejected(self) -> None:
        """LLM-refined slug with entity remnant (excelreg) must be rejected."""
        pages = self._make_pages_with_slugs([
            "print-microsoft-excel-files",
            "convert-xlsx-to-csv",
        ])
        mock = _MockLLMClient("print-microsoft-excelreg-files\nconvert-xlsx-to-csv")
        result = _refine_page_slugs(pages, mock)

        # First slug should be preserved (LLM version rejected)
        assert result[0].frontmatter["slug"] == "print-microsoft-excel-files"
        # Second slug is unchanged (same as original)
        assert result[1].frontmatter["slug"] == "convert-xlsx-to-csv"

    def test_windowsreg_artifact_slug_rejected(self) -> None:
        """LLM-refined slug with 'windowsreg' entity remnant must be rejected."""
        pages = self._make_pages_with_slugs(["microsoft-windows-desktop"])
        mock = _MockLLMClient("microsoft-windowsreg-desktop")
        result = _refine_page_slugs(pages, mock)
        assert result[0].frontmatter["slug"] == "microsoft-windows-desktop"

    def test_safe_refined_slug_accepted(self) -> None:
        """Clean LLM-refined slug should be accepted and applied."""
        pages = self._make_pages_with_slugs(["convert-xlsx-to-csv-format"])
        mock = _MockLLMClient("convert-xlsx-csv")
        result = _refine_page_slugs(pages, mock)
        assert result[0].frontmatter["slug"] == "convert-xlsx-csv"

    @pytest.mark.parametrize("artifact,original", [
        ("microsoft-exceltrade-files", "microsoft-excel-files"),
        ("microsoft-windowscopy-desktop", "microsoft-windows-desktop"),
        ("aspose-cellsreg-library", "aspose-cells-library"),
    ])
    def test_entity_variants_rejected(self, artifact: str, original: str) -> None:
        """All entity remnant variants (reg/trade/copy) must be rejected."""
        pages = self._make_pages_with_slugs([original])
        mock = _MockLLMClient(artifact)
        result = _refine_page_slugs(pages, mock)
        assert result[0].frontmatter["slug"] == original

    def test_e2e_entity_artifact_rejected_through_run_plan(self) -> None:
        """Entity artifact slug rejected end-to-end through run_plan()."""
        product = _make_product("cells")
        richness = _make_richness(RichnessTier.B)
        claims = [_make_claim("Feature A", kind="feature", claim_id="CLM-001")]
        snippets: list[Snippet] = []

        # Get baseline slugs
        pages_base, _ = run_plan(product, richness, claims, snippets)
        base_slugs = [
            p.frontmatter.get("slug", "")
            for p in pages_base
            if p.page_role != "toc" and p.frontmatter.get("slug") != "_index"
        ]
        base_slugs = [s for s in base_slugs if s]
        if not base_slugs:
            pytest.skip("No refinable slugs in plan")

        # LLM returns entity-artifact versions of every slug
        bad_slugs = [s + "reg" if not s.endswith("reg") else s for s in base_slugs]
        mock = _MockLLMClient("\n".join(bad_slugs))
        pages_llm, _ = run_plan(
            product, richness, claims, snippets, llm_client=mock,
        )

        # No slug should contain a fused entity artifact
        from launcher.shared.slug_engine import _ENTITY_ARTIFACT_RE
        for page in pages_llm:
            slug = page.frontmatter.get("slug", "")
            assert not _ENTITY_ARTIFACT_RE.search(slug), (
                f"Entity artifact leaked through run_plan: {slug}"
            )

    def test_url_preserved_on_rejection(self) -> None:
        """URL field must remain unchanged when refined slug is rejected."""
        pages = self._make_pages_with_slugs(["print-microsoft-excel-files"])
        original_url = pages[0].frontmatter["url"]
        mock = _MockLLMClient("print-microsoft-excelreg-files")
        result = _refine_page_slugs(pages, mock)
        assert result[0].frontmatter["url"] == original_url

    def test_all_slugs_unsafe_all_preserved(self) -> None:
        """When ALL refined slugs are unsafe, all originals must be kept."""
        originals = [
            "microsoft-excel-files",
            "microsoft-windows-desktop",
            "aspose-cells-library",
        ]
        pages = self._make_pages_with_slugs(originals)
        # Every slug gets an entity artifact appended
        bad = [s + "reg" for s in originals]
        mock = _MockLLMClient("\n".join(bad))
        result = _refine_page_slugs(pages, mock)
        for i, orig in enumerate(originals):
            assert result[i].frontmatter["slug"] == orig, (
                f"Page {i} slug changed from {orig} to {result[i].frontmatter['slug']}"
            )


# ---------------------------------------------------------------------------
# SR-01 + SR-05: Quality gate integration tests (TC-3820 healing)
# ---------------------------------------------------------------------------


class TestQualityCheckSlugs:
    """Integration tests for _quality_check_slugs and _slug_fallback."""

    def _make_page(
        self, slug: str, section: str = "blog", page_role: str = "feature_blog",
        topic_category: str | None = None,
    ) -> dict:
        return {
            "section": section,
            "page_id": f"{section}/{slug}",
            "page_role": page_role,
            "slug": slug,
            "content_path": f"{section}/{slug}",
            "mandatory": True,
            "topic_category": topic_category,
        }

    def test_good_slug_unchanged(self) -> None:
        """A valid slug must pass through untouched."""
        product = _make_product("cells")
        pages = [self._make_page("cells-key-features")]
        result = _quality_check_slugs(pages, product)
        assert result[0]["slug"] == "cells-key-features"

    def test_bad_slug_replaced(self) -> None:
        """A garbled slug must be replaced."""
        product = _make_product("cells")
        pages = [self._make_page("microsoft-windows-windows-desktop-spreadsheets")]
        result = _quality_check_slugs(pages, product)
        assert result[0]["slug"] != "microsoft-windows-windows-desktop-spreadsheets"
        assert "windows" not in result[0]["slug"]

    def test_index_slug_exempt(self) -> None:
        """_index slugs must not be quality-checked."""
        product = _make_product("cells")
        pages = [self._make_page("_index", page_role="toc")]
        result = _quality_check_slugs(pages, product)
        assert result[0]["slug"] == "_index"

    def test_collision_resolved_by_re_disambiguation(self) -> None:
        """SR-01: Two bad slugs mapping to the same fallback get disambiguated."""
        product = _make_product("cells")
        pages = [
            self._make_page("microsoft-windows-windows-desktop-spreadsheets"),
            self._make_page("microsoft-linux-linux-server-spreadsheets"),
        ]
        # Quality gate replaces both → likely same fallback
        pages = _quality_check_slugs(pages, product)
        # Re-disambiguate (as pipeline does)
        pages = _disambiguate_slugs(pages)
        page_ids = [p["page_id"] for p in pages]
        assert len(set(page_ids)) == len(page_ids), f"Collision! page_ids={page_ids}"

    def test_slug_fallback_per_role(self) -> None:
        """_slug_fallback returns distinct patterns per page_role."""
        fb_blog = _slug_fallback("feature_blog", "blog", "spreadsheets", "python")
        fb_announce = _slug_fallback("blog_announcement", "blog", "spreadsheets", "python")
        fb_kb = _slug_fallback("howto_article", "kb", "spreadsheets", "python")
        assert fb_blog != fb_announce
        assert fb_blog != fb_kb

    def test_sentence_fragment_slug_replaced(self) -> None:
        """A sentence-fragment slug must be replaced."""
        product = _make_product("cells")
        pages = [self._make_page(
            "this-repository-provides-a-python-spreadsheets",
            section="docs", page_role="workflow_page",
        )]
        result = _quality_check_slugs(pages, product)
        slug = result[0]["slug"]
        assert slug != "this-repository-provides-a-python-spreadsheets"

    def test_topic_category_used_for_recovery(self) -> None:
        """SR-02: Recovery uses topic_category, not title derived from bad slug."""
        product = _make_product("cells")
        pages = [self._make_page(
            "microsoft-windows-windows-desktop-spreadsheets",
            section="kb", page_role="howto_article",
            topic_category="convert spreadsheet files to PDF",
        )]
        result = _quality_check_slugs(pages, product)
        slug = result[0]["slug"]
        # Should attempt extract_slug_core("convert spreadsheet files to PDF")
        # which finds verb "convert" → "convert-spreadsheet-spreadsheets" or similar
        assert "windows" not in slug


# ---------------------------------------------------------------------------
# TC-3824: _build_frontmatter must always set robots
# ---------------------------------------------------------------------------

def _make_planned_page(
    page_id: str = "cells/python/overview",
    page_role: str = "overview",
    title: str = "Overview",
    slug: str = "overview",
    content_path: str = "cells/python/overview",
) -> PlannedPage:
    """Minimal PlannedPage for _build_frontmatter tests."""
    return PlannedPage(
        page_id=page_id,
        page_role=page_role,
        title=title,
        content_path=content_path,
    )


class TestBuildFrontmatterRobots:
    """TC-3824: _build_frontmatter must set robots on every page."""

    def test_robots_present_on_regular_page(self) -> None:
        product = _make_product("cells", "python")
        page = _make_planned_page(page_role="how_to", title="Convert Files")
        result = _build_frontmatter([page], product)
        assert len(result) == 1
        fm = result[0].frontmatter
        assert "robots" in fm
        assert fm["robots"]  # non-empty string

    def test_robots_index_follow_for_content_page(self) -> None:
        product = _make_product("cells", "python")
        page = _make_planned_page(page_role="api_reference", title="API Reference")
        result = _build_frontmatter([page], product)
        assert result[0].frontmatter["robots"] == "index, follow"

    def test_robots_noindex_for_index_slug(self) -> None:
        product = _make_product("cells", "python")
        page = _make_planned_page(
            page_id="cells/python/_index",
            page_role="toc",
            title="Python Cells",
            slug="_index",
            content_path="cells/python/_index",
        )
        result = _build_frontmatter([page], product)
        assert result[0].frontmatter["robots"] == "noindex, follow"

    def test_robots_noindex_for_toc_role(self) -> None:
        product = _make_product("cells", "python")
        page = _make_planned_page(page_role="toc", title="Table of Contents")
        result = _build_frontmatter([page], product)
        assert result[0].frontmatter["robots"] == "noindex, follow"

    def test_no_none_values_in_frontmatter(self) -> None:
        """_build_frontmatter must never produce None values (TC-3824 invariant)."""
        product = _make_product("cells", "python")
        pages = [
            _make_planned_page(page_role="how_to", title="How To"),
            _make_planned_page(page_id="cells/python/_index", page_role="toc",
                               title="Index", content_path="cells/python/_index"),
        ]
        results = _build_frontmatter(pages, product)
        for planned in results:
            null_keys = [k for k, v in planned.frontmatter.items() if v is None]
            assert null_keys == [], (
                f"Page {planned.page_id} has None values: {null_keys}"
            )

    def test_all_ir_renderer_required_keys_present(self) -> None:
        """Frontmatter produced by _build_frontmatter must satisfy ir_renderer contract."""
        from launcher.shared.ir_renderer import _REQUIRED_FM_KEYS
        product = _make_product("cells", "python")
        page = _make_planned_page(page_role="tutorial", title="Tutorial")
        result = _build_frontmatter([page], product)
        fm = result[0].frontmatter
        missing = _REQUIRED_FM_KEYS - fm.keys()
        assert missing == frozenset(), f"Missing required keys: {missing}"

    def test_python_frontmatter_uses_runtime_import_when_available(self) -> None:
        """TC-4254: frontmatter canonical_import stores the code-facing Python import."""
        product = _make_product(
            family="3d",
            platform="python",
            canonical_import="aspose_3d_foss",
            runtime_import="aspose.threed",
        )
        page = _make_planned_page(page_id="3d/python/getting-started", content_path="3d/python/getting-started")
        result = _build_frontmatter([page], product)
        assert result[0].frontmatter["canonical_import"] == "aspose.threed"

    def test_non_python_frontmatter_keeps_canonical_import(self) -> None:
        """TC-4254: non-Python platforms keep canonical_import semantics unchanged."""
        product = _make_product(
            family="cells",
            platform="java",
            canonical_import="com.aspose.cells",
            runtime_import="",
        )
        page = _make_planned_page(page_id="cells/java/overview", content_path="cells/java/overview")
        result = _build_frontmatter([page], product)
        assert result[0].frontmatter["canonical_import"] == "com.aspose.cells"


class TestBuildFrontmatterRobotsDict:
    """SR-04: _ROBOTS_BY_ROLE dict — unknown roles safe default, all known roles covered."""

    def test_unknown_role_gets_safe_default(self) -> None:
        """A role not in _ROBOTS_BY_ROLE must receive 'noindex, nofollow'."""
        from launcher.workers.planner.plan import _ROBOTS_SAFE_DEFAULT
        product = _make_product("cells", "python")
        page = _make_planned_page(page_role="unknown_future_role", title="New Page")
        result = _build_frontmatter([page], product)
        assert result[0].frontmatter["robots"] == _ROBOTS_SAFE_DEFAULT
        assert result[0].frontmatter["robots"] == "noindex, nofollow"

    def test_misspelled_role_gets_safe_default(self) -> None:
        """A misspelled role name must NOT become indexable."""
        product = _make_product("cells", "python")
        page = _make_planned_page(page_role="feature_showkase", title="Typo Role")
        result = _build_frontmatter([page], product)
        assert result[0].frontmatter["robots"] == "noindex, nofollow"

    @pytest.mark.parametrize("page_role", [
        "landing",
        "workflow_page",
        "api_reference",
        "faq",
        "troubleshooting",
        "feature_showcase",
        "howto_article",
        "blog_announcement",
        "feature_blog",
        "reference_object_page",
    ])
    def test_known_indexable_roles_get_index_follow(self, page_role: str) -> None:
        """Every known content role must produce a non-empty, valid robots string."""
        product = _make_product("cells", "python")
        page = _make_planned_page(page_role=page_role, title="Content Page")
        result = _build_frontmatter([page], product)
        robots = result[0].frontmatter["robots"]
        assert robots == "index, follow", (
            f"Expected 'index, follow' for role={page_role!r}, got {robots!r}"
        )

    def test_toc_role_noindex_follow(self) -> None:
        """toc is structural — noindex but crawlable."""
        product = _make_product("cells", "python")
        page = _make_planned_page(page_role="toc", title="Contents")
        result = _build_frontmatter([page], product)
        assert result[0].frontmatter["robots"] == "noindex, follow"

    def test_robots_dict_covers_all_ruleset_roles(self) -> None:
        """Every page_role in specs/rulesets/ruleset.yaml must be in _ROBOTS_BY_ROLE."""
        from launcher.workers.planner.plan import _ROBOTS_BY_ROLE
        # Roles from ruleset.yaml (ground truth for the pipeline)
        ruleset_roles = {
            "landing", "toc", "workflow_page", "api_reference", "faq",
            "troubleshooting", "feature_showcase", "howto_article",
            "blog_announcement", "feature_blog",
        }
        missing = ruleset_roles - set(_ROBOTS_BY_ROLE.keys())
        assert not missing, (
            f"Roles in ruleset.yaml not covered by _ROBOTS_BY_ROLE: {missing}. "
            "Add them to the dict in plan.py."
        )
