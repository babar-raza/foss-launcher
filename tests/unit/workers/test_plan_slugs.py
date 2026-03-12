"""Tests for evidence-aware slug/title generation (capability #5)."""
from __future__ import annotations

import pytest

from launcher.models.claims import Claim
from launcher.models.plan import PlannedPage
from launcher.models.product import ProductIdentity
from launcher.workers.planner.plan import (
    _dedup_and_validate_titles,
    _generate_evidence_aware_title,
    _generate_title,
    _refine_page_slugs,
    _title_from_slug,
    _validate_title,
)


def _make_claim(text: str, claim_id: str = "CLM-test-001") -> Claim:
    return Claim(claim_id=claim_id, text=text, kind="feature")


class TestGenerateTitle:
    def test_slug_to_title(self) -> None:
        assert _generate_title("how-to-open-a-file", "workflow_page") == "How to Open a File"

    def test_index_slug(self) -> None:
        assert _generate_title("_index", "landing") == "Overview"

    def test_toc_index(self) -> None:
        assert _generate_title("_index", "toc") == "Table of Contents"

    def test_small_words_lowercase(self) -> None:
        result = _generate_title("convert-to-pdf-format", "workflow_page")
        assert result == "Convert to Pdf Format"


class TestGenerateEvidenceAwareTitle:
    def test_falls_back_to_slug_title_no_claims(self) -> None:
        result = _generate_evidence_aware_title(
            "install-guide", "workflow_page", [], {},
        )
        assert result == _generate_title("install-guide", "workflow_page")

    def test_falls_back_for_index(self) -> None:
        claim = _make_claim("Some long claim text for testing purposes")
        result = _generate_evidence_aware_title(
            "_index", "landing", ["CLM-test-001"], {"CLM-test-001": claim},
        )
        assert result == "Overview"

    def test_uses_claim_text(self) -> None:
        claim = _make_claim(
            "The library supports converting spreadsheets to PDF format with high fidelity"
        )
        result = _generate_evidence_aware_title(
            "convert-pdf", "feature_showcase",
            ["CLM-test-001"], {"CLM-test-001": claim},
        )
        assert "library" in result.lower()
        assert "supports" in result.lower()

    def test_truncates_long_claims(self) -> None:
        claim = _make_claim("X" * 100)
        result = _generate_evidence_aware_title(
            "long-page", "feature_showcase",
            ["CLM-test-001"], {"CLM-test-001": claim},
        )
        assert len(result) <= 83  # 80 + "..."

    def test_falls_back_short_claim(self) -> None:
        claim = _make_claim("Short")
        result = _generate_evidence_aware_title(
            "some-page", "feature_showcase",
            ["CLM-test-001"], {"CLM-test-001": claim},
        )
        # Short claim (<15 chars) falls back to slug title
        assert result == _generate_title("some-page", "feature_showcase")

    def test_first_sentence_extraction(self) -> None:
        claim = _make_claim(
            "Supports PDF export. Also supports XLSX and CSV formats."
        )
        result = _generate_evidence_aware_title(
            "export", "feature_showcase",
            ["CLM-test-001"], {"CLM-test-001": claim},
        )
        assert "also" not in result.lower()
        assert "supports" in result.lower()

    def test_missing_claim_id_falls_back(self) -> None:
        result = _generate_evidence_aware_title(
            "some-page", "feature_showcase",
            ["CLM-nonexistent"], {},
        )
        assert result == _generate_title("some-page", "feature_showcase")

    def test_toc_role_ignores_claims(self) -> None:
        claim = _make_claim("Some claim text for the table of contents")
        result = _generate_evidence_aware_title(
            "toc", "toc",
            ["CLM-test-001"], {"CLM-test-001": claim},
        )
        assert result == _generate_title("toc", "toc")


# ------------------------------------------------------------------
# Gemini slug refinement (SEO-08)
# ------------------------------------------------------------------


def _make_product(**overrides) -> ProductIdentity:
    defaults = {
        "family": "cells",
        "platform": "python",
        "display_name": "Aspose.Cells for Python",
        "canonical_import": "aspose.cells",
        "repo_url": "https://github.com/aspose-cells/aspose-cells-python",
    }
    defaults.update(overrides)
    return ProductIdentity(**defaults)


def _make_page(slug: str, page_role: str = "workflow_page") -> PlannedPage:
    return PlannedPage(
        page_id=f"page-{slug}",
        page_role=page_role,
        title=slug.replace("-", " ").title(),
        skeleton=["overview", "steps"],
        skeleton_variant="standard",
        assigned_claims=["CLM-001"],
        assigned_snippets=[],
        frontmatter={"slug": slug, "title": slug.replace("-", " ").title()},
    )


class TestGeminiSlugRefinement:
    def test_refine_slugs_with_gemini(self) -> None:
        """Gemini-refined slugs are applied to pages."""
        class MockGemini:
            available = True
            def refine_slugs(self, slugs, family, platform):
                return [s.replace("how-to-", "") for s in slugs]

        pages = [_make_page("how-to-install"), _make_page("how-to-convert")]
        product = _make_product()
        result = _refine_page_slugs(pages, gemini_client=MockGemini(), product=product)
        slugs = [p.frontmatter["slug"] for p in result]
        assert "install" in slugs
        assert "convert" in slugs

    def test_refine_slugs_gemini_unavailable_falls_back(self) -> None:
        """Gemini with available=False uses algorithmic fallback."""
        class UnavailableGemini:
            available = False
            def refine_slugs(self, slugs, family, platform):
                raise AssertionError("Should not be called")

        pages = [_make_page("how-to-install")]
        result = _refine_page_slugs(pages, gemini_client=UnavailableGemini(), product=_make_product())
        # Should fall back to algorithmic (strip_leading_stop_words)
        assert len(result) == 1
        # The slug should be processed (algorithmic fallback strips stop words)
        assert result[0].frontmatter["slug"] in ("how-to-install", "install")

    def test_refine_slugs_gemini_error_falls_back(self) -> None:
        """Gemini raising exception falls back to algorithmic."""
        class CrashingGemini:
            available = True
            def refine_slugs(self, slugs, family, platform):
                raise RuntimeError("Gemini exploded")

        pages = [_make_page("how-to-install")]
        result = _refine_page_slugs(pages, gemini_client=CrashingGemini(), product=_make_product())
        assert len(result) == 1
        # Should still return valid pages (algorithmic fallback)
        assert result[0].frontmatter["slug"] in ("how-to-install", "install")


# ---------------------------------------------------------------------------
# TC-4218: title validation, slug-derived fallback, post-dedup
# ---------------------------------------------------------------------------


class TestTitleFromSlug:
    """Unit tests for _title_from_slug helper (TC-4218)."""

    def test_basic_slug(self) -> None:
        assert _title_from_slug("load-3d-models") == "Load 3D Models"

    def test_last_segment_of_path(self) -> None:
        assert _title_from_slug("docs/api/save-file") == "Save File"

    def test_strips_python_suffix(self) -> None:
        result = _title_from_slug("load-3d-models-python")
        assert "Python" not in result
        assert "Load" in result

    def test_underscores_replaced(self) -> None:
        result = _title_from_slug("convert_file_formats")
        assert "_" not in result
        assert "Convert" in result


class TestValidateTitle:
    """Unit tests for _validate_title helper (TC-4218)."""

    def test_trailing_colon_stripped(self) -> None:
        """TC-4218 requirement: trailing colon must be removed."""
        result = _validate_title("Foo bar:", slug="some-page")
        assert result == "Foo bar"

    def test_trailing_colon_with_spaces(self) -> None:
        result = _validate_title("Foo bar :  ", slug="some-page")
        assert result == "Foo bar"

    def test_demonstrating_fragment_replaced(self) -> None:
        """TC-4218 requirement: 'demonstrating' in title → slug-derived fallback."""
        result = _validate_title(
            "5 example files demonstrating:",
            slug="load-3d-models",
            product_name="Aspose.3D for Python",
        )
        assert "demonstrating" not in result.lower()
        # Should derive from slug
        assert "Load" in result or "3D" in result or "Models" in result

    def test_min_length_falls_back_to_slug(self) -> None:
        """TC-4218 requirement: title < 10 chars → slug-derived title."""
        result = _validate_title("Foo", slug="save-3d-scene-python", product_name="")
        # Slug-derived title should be longer
        assert len(result) >= 10

    def test_valid_title_unchanged(self) -> None:
        result = _validate_title("How to Load 3D Models with Python", slug="load-3d-models-python")
        assert result == "How to Load 3D Models with Python"


class TestHowtoArticleSlugDerivedFallback:
    """TC-4218: howto_article without topic_category must derive title from slug."""

    def test_no_topic_category_derives_from_slug(self) -> None:
        """When topic_category is absent, howto_article uses slug-derived title."""
        result = _generate_evidence_aware_title(
            "load-3d-models-python",
            "howto_article",
            [],
            {},
            product_name="Aspose.3D for Python",
            topic_category="",  # no topic
        )
        # Must start with "How to" and NOT contain description fragments
        assert result.startswith("How to")
        assert "demonstrating" not in result.lower()
        assert ":" not in result.rstrip()

    def test_description_fragment_never_used_as_title(self) -> None:
        """Claim text with 'demonstrating' must not become the page title."""
        from launcher.models.claims import Claim
        claim = _make_claim("5 example files demonstrating the API surface")
        result = _generate_evidence_aware_title(
            "api-examples-python",
            "howto_article",
            ["CLM-test-001"],
            {"CLM-test-001": claim},
            product_name="Aspose.3D for Python",
            topic_category="",
        )
        # howto_article with no topic → slug-derived; claim text should not override
        assert result.startswith("How to")
        assert "demonstrating" not in result.lower()


class TestTitleDeduplication:
    """TC-4218: _dedup_and_validate_titles removes collisions."""

    def _make_planned_page(
        self,
        page_id: str,
        title: str,
        page_role: str = "howto_article",
    ) -> PlannedPage:
        return PlannedPage(
            page_id=page_id,
            page_role=page_role,
            title=title,
            skeleton=["overview"],
            skeleton_variant="default",
            assigned_claims=["CLM-001"],
            assigned_snippets=[],
            frontmatter={},
        )

    def test_dedup_adds_suffix_when_titles_collide(self) -> None:
        """Two pages sharing a title get unique titles via slug-derived suffix."""
        page_a = self._make_planned_page(
            "3d/load-3d-models",
            "How to Load 3D Models with Aspose.3D",
        )
        page_b = self._make_planned_page(
            "3d/save-3d-models",
            "How to Load 3D Models with Aspose.3D",  # deliberate collision
        )
        result = _dedup_and_validate_titles(
            [page_a, page_b], product_name="Aspose.3D for Python"
        )
        titles = [p.title for p in result]
        assert len(set(titles)) == 2, f"Titles are still not unique: {titles}"
        # Both titles should contain the original base
        for title in titles:
            assert "Load 3D Models" in title or "\u2014" in title

    def test_no_collision_titles_unchanged(self) -> None:
        """Pages with unique titles are not modified by the dedup pass."""
        page_a = self._make_planned_page("3d/load", "How to Load Files with Aspose.3D")
        page_b = self._make_planned_page("3d/save", "How to Save Files with Aspose.3D")
        result = _dedup_and_validate_titles(
            [page_a, page_b], product_name="Aspose.3D for Python"
        )
        assert result[0].title == "How to Load Files with Aspose.3D"
        assert result[1].title == "How to Save Files with Aspose.3D"

    def test_validate_trailing_colon_in_dedup_pass(self) -> None:
        """Trailing colon in a title is cleaned during the validation pass."""
        page = self._make_planned_page("3d/examples", "Example Files:")
        result = _dedup_and_validate_titles([page], product_name="Aspose.3D")
        assert not result[0].title.endswith(":")

    def test_three_way_collision_all_unique_after_dedup(self) -> None:
        """Three pages sharing a title all get unique titles after dedup."""
        pages = [
            self._make_planned_page("3d/bounding-boxes", "Bounding Boxes And Transformations"),
            self._make_planned_page("3d/transform-meshes", "Bounding Boxes And Transformations"),
            self._make_planned_page("3d/matrix-ops", "Bounding Boxes And Transformations"),
        ]
        result = _dedup_and_validate_titles(pages, product_name="Aspose.3D for Python")
        titles = [p.title for p in result]
        assert len(set(titles)) == 3, f"Not all titles unique after dedup: {titles}"
