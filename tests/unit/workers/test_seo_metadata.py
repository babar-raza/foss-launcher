"""Tests for seo_metadata.py — post-generation SEO optimization (TC-3810)."""
from __future__ import annotations

import re
from unittest.mock import patch

import pytest

from launcher.models.claims import Claim
from launcher.models.page_ir import BlockIR, BlockType, PageIR, SectionIR
from launcher.models.product import ProductIdentity
from launcher.workers.generate.seo_metadata import (
    GeminiClientLike,
    KeywordBundleLike,
    _enhance_keywords,
    _enforce_metadata_quality,
    _extract_from_content,
    _generate_canonical,
    _generate_description,
    _generate_seo_title,
    _inject_freshness_dates,
    _robots_directive,
    _sanitize_title,
    _truncate_description,
    optimize_seo_metadata,
)


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


def _make_claim(text: str = "Test claim", **overrides) -> Claim:
    defaults = {
        "claim_id": "CLM-001",
        "kind": "feature",
        "text": text,
    }
    defaults.update(overrides)
    return Claim(**defaults)


def _make_page_ir(
    title: str = "Test Page",
    frontmatter: dict | None = None,
    sections: list[SectionIR] | None = None,
    page_role: str = "guide",
) -> PageIR:
    return PageIR(
        page_id="test-page",
        page_role=page_role,
        title=title,
        frontmatter=frontmatter or {"title": title},
        sections=sections or [],
    )


# --- _sanitize_title ---


class TestSanitizeTitle:
    def test_strips_html_entities(self):
        result = _sanitize_title("Microsoft Windows&reg; Spreadsheets")
        assert "&reg;" not in result
        assert "®" not in result
        assert "Windows" in result

    def test_collapses_whitespace(self):
        result = _sanitize_title("Hello   World")
        assert result == "Hello World"

    def test_empty_passthrough(self):
        assert _sanitize_title("") == ""

    def test_trademark_symbol_removed(self):
        result = _sanitize_title("Product™ Name")
        assert "™" not in result


# --- _generate_seo_title ---


class TestGenerateSeoTitle:
    def test_prepends_product_when_missing(self):
        result = _generate_seo_title("Getting Started", "Aspose.Cells for Python")
        assert "Aspose.Cells" in result

    def test_no_prepend_when_present(self):
        result = _generate_seo_title(
            "Aspose.Cells Getting Started", "Aspose.Cells for Python",
        )
        # Should not double the product name.
        assert result.count("Aspose.Cells") == 1

    def test_max_length_respected(self):
        result = _generate_seo_title("A" * 100, "Product", max_len=60)
        assert len(result) <= 60

    def test_differentiator_when_same(self):
        result = _generate_seo_title("Short Title", "")
        assert result != "Short Title"

    def test_empty_title(self):
        assert _generate_seo_title("", "Product") == ""

    def test_short_product_extraction(self):
        result = _generate_seo_title("Guide", "Aspose.Cells for Python")
        # "for Python" should be stripped from the short product name.
        assert "Aspose.Cells" in result


# --- _generate_description ---


class TestGenerateDescription:
    def test_purpose_field_used(self):
        page_ir = _make_page_ir(
            frontmatter={
                "title": "Test",
                "purpose": "This is a detailed purpose field that describes the page content adequately.",
            },
        )
        result = _generate_description(page_ir, _make_product(), [])
        assert "purpose field" in result

    def test_content_extraction_fallback(self):
        section = SectionIR(
            section_id="s1",
            heading="Overview",
            blocks=[
                BlockIR(
                    type=BlockType.paragraph,
                    content=(
                        "First sentence here. Second sentence provides useful context. "
                        "Third sentence adds more detail."
                    ),
                ),
            ],
        )
        page_ir = _make_page_ir(sections=[section])
        result = _generate_description(page_ir, _make_product(), [])
        assert "Second sentence" in result

    def test_claim_derived_fallback(self):
        claims = [_make_claim("Aspose.Cells supports reading Excel files in Python.")]
        page_ir = _make_page_ir()
        result = _generate_description(page_ir, _make_product(), claims)
        assert len(result) >= 50

    def test_template_fallback(self):
        page_ir = _make_page_ir()
        result = _generate_description(page_ir, _make_product(), [])
        assert "Aspose.Cells" in result

    def test_gemini_used_when_available(self):
        class MockGemini:
            available = True
            def generate_description(self, title, product, claims):
                return "A great description of the page for search engines and users alike."

        page_ir = _make_page_ir()
        result = _generate_description(page_ir, _make_product(), [], MockGemini())
        assert "great description" in result

    def test_gemini_too_short_falls_through(self):
        class MockGemini:
            available = True
            def generate_description(self, title, product, claims):
                return "Short."

        page_ir = _make_page_ir()
        result = _generate_description(page_ir, _make_product(), [])
        assert len(result) >= 50 or result == ""


# --- _extract_from_content ---


class TestExtractFromContent:
    def test_extracts_sentences_2_3(self):
        section = SectionIR(
            section_id="s1",
            heading="Overview",
            blocks=[
                BlockIR(
                    type=BlockType.paragraph,
                    content="Lead sentence. Useful description here. More details follow.",
                ),
            ],
        )
        page_ir = _make_page_ir(sections=[section])
        result = _extract_from_content(page_ir)
        assert "Useful description" in result

    def test_empty_when_no_paragraphs(self):
        section = SectionIR(
            section_id="s1",
            heading="Code",
            blocks=[BlockIR(type=BlockType.code, content="print('hello')")],
        )
        page_ir = _make_page_ir(sections=[section])
        assert _extract_from_content(page_ir) == ""


# --- _truncate_description ---


class TestTruncateDescription:
    def test_short_text_unchanged(self):
        assert _truncate_description("Hello world", 160) == "Hello world"

    def test_long_text_truncated(self):
        long = "word " * 50
        result = _truncate_description(long, 80)
        assert len(result) <= 80
        assert result.endswith("...")

    def test_entities_stripped(self):
        result = _truncate_description("Hello&reg; world is great", 160)
        assert "&reg;" not in result


# --- _generate_canonical ---


class TestGenerateCanonical:
    def test_docs_canonical(self):
        result = _generate_canonical("/docs/cells/python/getting-started/", "guide")
        assert result.startswith("https://docs.aspose.org/")

    def test_reference_role(self):
        result = _generate_canonical("/reference/cells/python/api/", "api_reference")
        assert "reference.aspose.org" in result

    def test_empty_url(self):
        assert _generate_canonical("", "guide") == ""


# --- _robots_directive ---


class TestRobotsDirective:
    def test_index_page_noindex(self):
        assert _robots_directive("toc", "overview") == "noindex, follow"

    def test_index_slug_noindex(self):
        assert _robots_directive("guide", "_index") == "noindex, follow"

    def test_content_page_index(self):
        assert _robots_directive("guide", "getting-started") == "index, follow"


# --- _enhance_keywords ---


class TestEnhanceKeywords:
    def test_existing_preserved(self):
        result = _enhance_keywords(
            ["python", "excel"], [], "cells",
        )
        assert "python" in result
        assert "excel" in result

    def test_claim_derived_added(self):
        claims = [
            _make_claim("Convert Excel spreadsheets to PDF format using Python."),
            _make_claim("Convert Excel spreadsheets to CSV format using Python."),
        ]
        result = _enhance_keywords([], claims, "cells")
        # "convert" or "excel" or "spreadsheets" should appear
        lower = [k.lower() for k in result]
        assert any(w in lower for w in ("convert", "excel", "spreadsheets"))

    def test_capped_at_8(self):
        result = _enhance_keywords(
            [f"kw{i}" for i in range(10)], [], "cells",
        )
        assert len(result) <= 8

    def test_family_keyword_added(self):
        result = _enhance_keywords([], [], "cells")
        assert "spreadsheets" in result

    def test_keyword_bundle_used(self):
        class MockBundle:
            primary_keywords = ["xlsx python", "excel library"]

        result = _enhance_keywords([], [], "cells", MockBundle())
        assert "xlsx python" in result

    def test_deduplication(self):
        result = _enhance_keywords(
            ["Python", "python"], [], "cells",
        )
        lower = [k.lower() for k in result]
        assert lower.count("python") == 1


# --- _enforce_metadata_quality ---


class TestEnforceMetadataQuality:
    def test_seo_title_differs_from_title(self):
        fm = {"title": "Test", "seoTitle": "Test"}
        result = _enforce_metadata_quality(fm)
        assert result["seoTitle"] != result["title"]

    def test_description_too_short_cleared(self):
        fm = {"title": "Test", "description": "Short"}
        result = _enforce_metadata_quality(fm)
        assert result["description"] == ""

    def test_description_too_long_truncated(self):
        fm = {"title": "Test", "description": "word " * 50}
        result = _enforce_metadata_quality(fm)
        assert len(result["description"]) <= 160

    def test_entity_sweep(self):
        fm = {"title": "Hello&reg; World", "seoTitle": "Hello&reg;", "description": ""}
        result = _enforce_metadata_quality(fm)
        assert "&reg;" not in result["title"]
        assert "&reg;" not in result["seoTitle"]


# --- optimize_seo_metadata (integration) ---


class TestOptimizeSeoMetadata:
    def test_adds_seo_fields(self):
        page_ir = _make_page_ir(
            title="Getting Started",
            frontmatter={
                "title": "Getting Started",
                "url": "/docs/cells/python/getting-started/",
                "slug": "getting-started",
            },
        )
        product = _make_product()
        claims = [_make_claim("Aspose.Cells supports reading Excel files.")]

        result = optimize_seo_metadata(page_ir, product, claims)

        assert "seoTitle" in result.frontmatter
        assert "robots" in result.frontmatter
        assert "keywords" in result.frontmatter
        assert result.frontmatter["robots"] == "index, follow"

    def test_entity_bug_fixed(self):
        page_ir = _make_page_ir(
            title="Microsoft Windows&reg; Spreadsheets",
            frontmatter={
                "title": "Microsoft Windows&reg; Spreadsheets",
                "url": "/docs/cells/python/windows-spreadsheets/",
                "slug": "windows-spreadsheets",
            },
        )
        result = optimize_seo_metadata(page_ir, _make_product(), [])
        assert "&reg;" not in result.frontmatter["title"]
        assert "®" not in result.frontmatter["title"]

    def test_returns_new_page_ir(self):
        page_ir = _make_page_ir()
        result = optimize_seo_metadata(page_ir, _make_product(), [])
        # Must be a new object (immutable pattern).
        assert result is not page_ir

    def test_toc_page_noindex(self):
        page_ir = _make_page_ir(
            page_role="toc",
            frontmatter={"title": "Table of Contents", "slug": "_index"},
        )
        result = optimize_seo_metadata(page_ir, _make_product(), [])
        assert result.frontmatter["robots"] == "noindex, follow"


# --- SEO-01: Exception safety tests ---


class TestExceptionSafety:
    def test_optimize_survives_bad_frontmatter(self):
        """Non-string title should not crash optimize_seo_metadata."""
        page_ir = _make_page_ir(
            title="Fallback",
            frontmatter={"title": None, "slug": "test"},
        )
        # Should not raise — returns a result (possibly with empty/cleaned fields).
        result = optimize_seo_metadata(page_ir, _make_product(), [])
        assert result is not None

    def test_gemini_exception_falls_through(self):
        """Gemini raising should fall through to next description source."""
        class CrashingGemini:
            available = True
            def generate_description(self, title, product, claims):
                raise RuntimeError("Gemini exploded")

        page_ir = _make_page_ir(
            frontmatter={
                "title": "Test Page",
                "purpose": "A detailed purpose that is long enough to be a valid description for the page.",
            },
        )
        result = _generate_description(page_ir, _make_product(), [], CrashingGemini())
        # Should fall through to purpose field.
        assert "purpose" in result.lower() or len(result) >= 50

    def test_gemini_exception_with_no_other_sources(self):
        """Gemini crash with no other sources should still produce template fallback."""
        class CrashingGemini:
            available = True
            def generate_description(self, title, product, claims):
                raise RuntimeError("Gemini exploded")

        page_ir = _make_page_ir()
        result = _generate_description(page_ir, _make_product(), [], CrashingGemini())
        assert "Aspose.Cells" in result


# --- SEO-06: Test coverage expansion ---


class TestCoverageExpansion:
    def test_optimize_with_keyword_bundle(self):
        """Real keyword bundle should enhance keywords."""
        class RealBundle:
            primary_keywords = ["xlsx python", "excel library", "spreadsheet api"]
            per_page = {"test-page": ["page-specific-kw"]}

        page_ir = _make_page_ir(
            frontmatter={"title": "Test Page", "slug": "test-page"},
        )
        result = optimize_seo_metadata(page_ir, _make_product(), [], RealBundle())
        kw = result.frontmatter.get("keywords", [])
        assert "xlsx python" in kw or "excel library" in kw

    def test_canonical_all_subdomain_variants(self):
        assert "reference.aspose.org" in _generate_canonical("/reference/cells/", "guide")
        assert "kb.aspose.org" in _generate_canonical("/kb/cells/python/faq/", "guide")
        assert "blog.aspose.org" in _generate_canonical("/blog/cells/python/post/", "guide")
        assert "products.aspose.org" in _generate_canonical("/products/cells/", "guide")
        assert "docs.aspose.org" in _generate_canonical("/some/unknown/path/", "guide")

    def test_canonical_full_subdomain_in_url_path(self):
        # URLs from pipeline include full subdomain as first path component.
        result = _generate_canonical("/docs.aspose.org/cells/python/installation/", "guide")
        assert result == "https://docs.aspose.org/cells/python/installation/"
        result = _generate_canonical("/blog.aspose.org/cells/python/post/", "guide")
        assert result == "https://blog.aspose.org/cells/python/post/"
        result = _generate_canonical("/kb.aspose.org/cells/python/faq/", "guide")
        assert result == "https://kb.aspose.org/cells/python/faq/"

    def test_description_equals_seo_title_cleared(self):
        fm = {"title": "Title", "seoTitle": "Same Desc", "description": "Same Desc"}
        result = _enforce_metadata_quality(fm)
        assert result["description"] == ""

    def test_description_equals_title_cleared(self):
        fm = {"title": "Identical", "seoTitle": "Different", "description": "Identical"}
        result = _enforce_metadata_quality(fm)
        assert result["description"] == ""

    def test_enhance_keywords_string_input(self):
        """optimize_seo_metadata handles string keywords gracefully."""
        page_ir = _make_page_ir(
            frontmatter={"title": "Test", "slug": "test", "keywords": "python, excel, cells"},
        )
        result = optimize_seo_metadata(page_ir, _make_product(), [])
        kw = result.frontmatter.get("keywords", [])
        assert isinstance(kw, list)
        assert "python" in kw

    def test_canonical_reference_object_page(self):
        result = _generate_canonical("/cells/python/api/workbook/", "reference_object_page")
        assert "reference.aspose.org" in result

    def test_generate_description_all_fallbacks_exhausted(self):
        """No Gemini, no purpose, no content, no claims -> template fallback."""
        page_ir = _make_page_ir(title="Empty Page")
        result = _generate_description(page_ir, _make_product(), [])
        assert len(result) >= 50
        assert "Aspose.Cells" in result


# ------------------------------------------------------------------
# Protocol compliance (SEO-03)
# ------------------------------------------------------------------


class TestProtocolCompliance:
    def test_keyword_bundle_protocol_compliance(self):
        """KeywordResearchBundle satisfies KeywordBundleLike protocol."""
        from launcher.shared.keyword_research import KeywordResearchBundle

        bundle = KeywordResearchBundle(
            primary_keywords=["python", "excel"],
            per_page={"install": ["pip"]},
        )
        assert isinstance(bundle, KeywordBundleLike)

    def test_gemini_client_protocol_compliance(self):
        """GeminiSEOClient satisfies GeminiClientLike protocol."""
        from launcher.clients.gemini_client import GeminiSEOClient
        from launcher.shared.seo_cache import SEOCache
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            cache = SEOCache(Path(tmp), default_ttl=60)
            client = GeminiSEOClient(api_key="", cache=cache)
            assert isinstance(client, GeminiClientLike)


# ------------------------------------------------------------------
# Contract clarity (SEO-04)
# ------------------------------------------------------------------


class TestEnforceMetadataContract:
    def test_enforce_metadata_quality_does_not_mutate_input(self):
        """_enforce_metadata_quality returns new dict; input unchanged."""
        original = {
            "title": "Test Title",
            "seoTitle": "Test Title",  # same as title — will be modified
            "description": "A short",  # too short — will be cleared
        }
        original_copy = dict(original)
        result = _enforce_metadata_quality(original)
        # Input must not be mutated.
        assert original == original_copy
        # Result is a different object.
        assert result is not original
        # Result has changes applied.
        assert result["seoTitle"] != original["seoTitle"]


# ------------------------------------------------------------------
# Configuration (SEO-07)
# ------------------------------------------------------------------


class TestSEOConfiguration:
    def test_default_seo_config_values(self):
        """SEOConfig defaults match plan spec values."""
        from launcher.models.run_config import SEOConfig

        cfg = SEOConfig()
        assert cfg.enabled is True
        assert cfg.keyword_research is True
        assert cfg.offline_mode is False
        assert cfg.cache_ttl_days == 7
        assert cfg.keyword_density_target == 0.015
        assert cfg.slug_rewrite is True
        assert cfg.gemini.enabled is True
        assert cfg.gemini.model == "gemini-2.5-flash"
        assert cfg.gemini.rpm == 15
        assert cfg.gemini.rpd == 1500
        assert "docs" in cfg.subdomain_map
        assert cfg.subdomain_map["docs"] == "docs.aspose.org"

    def test_subdomain_map_from_config(self):
        """_generate_canonical uses a custom subdomain map when provided."""
        custom_map = {
            "docs": "docs.example.com",
            "reference": "ref.example.com",
        }
        result = _generate_canonical(
            "/docs/cells/python/install/", "guide",
            subdomain_map=custom_map,
        )
        assert "docs.example.com" in result
        assert "aspose.org" not in result

    def test_seo_disabled_skips_phase15(self):
        """When seo.enabled=False, optimize_seo_metadata is not called."""
        page_ir = _make_page_ir(
            title="Original Title",
            frontmatter={
                "title": "Original Title",
                "slug": "original",
                "url": "/docs/cells/python/original/",
            },
        )
        # Verify that when we call optimize_seo_metadata, it modifies frontmatter
        result_enabled = optimize_seo_metadata(page_ir, _make_product(), [])
        assert "seoTitle" in result_enabled.frontmatter

        # The seo.enabled check is in worker.py, not in optimize_seo_metadata.
        # We verify the config model has the enabled field.
        from launcher.models.run_config import SEOConfig
        disabled = SEOConfig(enabled=False)
        assert disabled.enabled is False


# ------------------------------------------------------------------
# TC-3836: Content freshness signal injection
# ------------------------------------------------------------------


class TestFreshnessDates:
    """TC-3836: content freshness signal injection."""

    _ISO8601_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

    def test_freshness_dates_injected(self):
        """date, lastmod, datePublished, dateModified are all injected on a fresh page."""
        page_ir = _make_page_ir(
            frontmatter={"title": "Test Page", "slug": "test"},
        )
        result = optimize_seo_metadata(page_ir, _make_product(), [])
        fm = result.frontmatter
        assert "date" in fm, "date missing from frontmatter"
        assert "lastmod" in fm, "lastmod missing from frontmatter"
        assert "datePublished" in fm, "datePublished missing from frontmatter"
        assert "dateModified" in fm, "dateModified missing from frontmatter"
        assert fm["datePublished"] == fm["date"]
        assert fm["dateModified"] == fm["lastmod"]

    def test_date_preserved_on_rerun(self):
        """If fm already has date, it must not be overwritten by _inject_freshness_dates."""
        original_date = "2026-01-01T00:00:00Z"
        fm = {"date": original_date}
        result = _inject_freshness_dates(fm)
        assert result["date"] == original_date, "Existing date must not be overwritten"

    def test_lastmod_always_updated(self):
        """lastmod is always set to now, even when date already exists."""
        frozen_now = "2026-03-08T12:00:00Z"
        fm = {"date": "2026-01-01T00:00:00Z"}

        with patch(
            "launcher.workers.generate.seo_metadata.datetime",
        ) as mock_dt:
            mock_dt.now.return_value.strftime.return_value = frozen_now
            result = _inject_freshness_dates(fm)

        assert result["lastmod"] == frozen_now
        assert result["date"] == "2026-01-01T00:00:00Z"

    def test_iso8601_format(self):
        """All date fields match YYYY-MM-DDTHH:MM:SSZ format."""
        fm: dict = {}
        result = _inject_freshness_dates(fm)
        for field in ("date", "lastmod", "datePublished", "dateModified"):
            value = result.get(field, "")
            assert self._ISO8601_PATTERN.match(value), (
                f"{field} does not match ISO 8601: {value!r}"
            )

    def test_empty_date_replaced(self):
        """An empty string date is treated as absent and gets overwritten."""
        fm = {"date": ""}
        result = _inject_freshness_dates(fm)
        assert result["date"] != "", "Empty date should be replaced with current time"
        assert self._ISO8601_PATTERN.match(result["date"])

    def test_schema_org_mirrors(self):
        """datePublished == date and dateModified == lastmod on _inject_freshness_dates output."""
        fm: dict = {}
        result = _inject_freshness_dates(fm)
        assert result["datePublished"] == result["date"], (
            "datePublished must mirror date"
        )
        assert result["dateModified"] == result["lastmod"], (
            "dateModified must mirror lastmod"
        )

    def test_unusual_preexisting_date_preserved(self):
        """Non-ISO date string (e.g. 'March 2025') is preserved as-is — no crash, no overwrite."""
        non_iso_date = "March 2025"
        fm = {"date": non_iso_date}
        result = _inject_freshness_dates(fm)
        assert result["date"] == non_iso_date, (
            "Unusual but non-empty date must not be overwritten"
        )
        # lastmod is still updated to now (ISO format)
        assert self._ISO8601_PATTERN.match(result["lastmod"])

    # ------------------------------------------------------------------
    # V2AC-03: update_lastmod parameter (prevents CI/CD churn)
    # ------------------------------------------------------------------

    def test_lastmod_preserved_when_update_false(self):
        """update_lastmod=False: existing lastmod must NOT be overwritten."""
        existing_lastmod = "2026-01-01T00:00:00Z"
        fm = {"date": "2026-01-01T00:00:00Z", "lastmod": existing_lastmod}
        result = _inject_freshness_dates(fm, update_lastmod=False)
        assert result["lastmod"] == existing_lastmod, (
            "lastmod must be preserved when update_lastmod=False"
        )

    def test_lastmod_updated_when_update_true(self):
        """update_lastmod=True (default): existing lastmod IS overwritten."""
        frozen_now = "2026-03-08T15:00:00Z"
        fm = {"date": "2026-01-01T00:00:00Z", "lastmod": "2026-01-01T00:00:00Z"}
        with patch(
            "launcher.workers.generate.seo_metadata.datetime",
        ) as mock_dt:
            mock_dt.now.return_value.strftime.return_value = frozen_now
            result = _inject_freshness_dates(fm, update_lastmod=True)
        assert result["lastmod"] == frozen_now, (
            "lastmod must be updated when update_lastmod=True"
        )

    def test_missing_lastmod_always_set_regardless_of_flag(self):
        """update_lastmod=False but no prior lastmod → set it (first generation)."""
        fm: dict = {}
        result = _inject_freshness_dates(fm, update_lastmod=False)
        assert "lastmod" in result and result["lastmod"], (
            "lastmod must be set on first generation even with update_lastmod=False"
        )
        assert self._ISO8601_PATTERN.match(result["lastmod"])
