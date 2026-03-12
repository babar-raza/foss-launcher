"""Tests for TC-HO-07: keyword per_page flow verification."""
from __future__ import annotations

import pytest

from launcher.models.claims import Claim
from launcher.models.plan import PlannedPage
from launcher.models.product import ProductIdentity
from launcher.shared.page_skeletons import SkeletonSection


def _make_product() -> ProductIdentity:
    return ProductIdentity(
        family="cells", platform="python",
        display_name="Aspose.Cells", canonical_import="aspose_cells_foss",
        repo_url="https://example.com",
    )


def _make_page(seo_keywords: list[str] | None = None) -> PlannedPage:
    return PlannedPage(
        page_id="test-page",
        page_role="feature_overview",
        title="Excel Automation",
        assigned_claims=["CLM-001"],
        seo_keywords=seo_keywords or [],
    )


def _make_section() -> SkeletonSection:
    return SkeletonSection(heading="Overview", level=2, required=True, content_hint="desc", min_words=30, max_words=300)


def _make_claim() -> Claim:
    return Claim(
        claim_id="CLM-001",
        text="Supports Excel operations.",
        kind="api",
        evidence=[],
    )


class TestSeoKeywordsInPrompt:
    """Verify seo_keywords from PlannedPage appear in section prompt output."""

    def test_seo_keywords_appear_in_prompt(self):
        from launcher.workers.generate.section_prompt import build_section_prompt
        page = _make_page(seo_keywords=["excel automation", "spreadsheet python"])
        result = build_section_prompt(
            _make_section(), 0, 1, page, _make_product(), [_make_claim()], [],
        )
        assert "excel automation" in result
        assert "spreadsheet python" in result

    def test_empty_seo_keywords_shows_fallback(self):
        from launcher.workers.generate.section_prompt import build_section_prompt
        page = _make_page(seo_keywords=[])
        result = build_section_prompt(
            _make_section(), 0, 1, page, _make_product(), [_make_claim()], [],
        )
        assert "No specific SEO keywords" in result

    def test_none_seo_keywords_shows_fallback(self):
        from launcher.workers.generate.section_prompt import build_section_prompt
        page = _make_page(seo_keywords=None)
        result = build_section_prompt(
            _make_section(), 0, 1, page, _make_product(), [_make_claim()], [],
        )
        assert "No specific SEO keywords" in result

    def test_seo_keywords_capped_at_eight(self):
        from launcher.workers.generate.section_prompt import build_section_prompt
        keywords = [f"keyword-{i}" for i in range(15)]
        page = _make_page(seo_keywords=keywords)
        result = build_section_prompt(
            _make_section(), 0, 1, page, _make_product(), [_make_claim()], [],
        )
        # keyword-7 should be in (index 7, 8th keyword)
        assert "keyword-7" in result
        # keyword-8 (9th) should NOT be included since we cap at 8
        assert "keyword-8" not in result


class TestPlannerKeywordPerPage:
    """Verify planner correctly reads per_page from keyword bundle."""

    def test_generate_seo_keywords_uses_per_page(self):
        """Regression test: _generate_seo_keywords copies per_page[slug] to seo_keywords.

        Signature: _generate_seo_keywords(title, product_name, slug='', keyword_bundle=None)
        """
        from launcher.workers.planner.plan import _generate_seo_keywords
        from launcher.shared.keyword_research import KeywordResearchBundle

        kb = KeywordResearchBundle(
            per_page={"convert-fbx-to-gltf": ["fbx to gltf", "3d conversion python"]}
        )
        result = _generate_seo_keywords(
            "Convert FBX to GLTF", "Aspose.3D",
            slug="convert-fbx-to-gltf", keyword_bundle=kb,
        )
        assert "fbx to gltf" in result or "3d conversion python" in result

    def test_generate_seo_keywords_missing_slug_returns_list(self):
        """When per_page has no entry for slug, returns a list (may be empty or fallback)."""
        from launcher.workers.planner.plan import _generate_seo_keywords
        from launcher.shared.keyword_research import KeywordResearchBundle

        kb = KeywordResearchBundle(per_page={})
        result = _generate_seo_keywords(
            "Overview Page", "Aspose.Note",
            slug="unknown-page", keyword_bundle=kb,
        )
        assert isinstance(result, list)
