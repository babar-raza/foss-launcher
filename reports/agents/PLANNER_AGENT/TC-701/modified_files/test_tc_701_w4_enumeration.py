"""TC-701: Unit tests for W4 IAPlanner template-driven enumeration.

These tests verify:
1. Family-aware path construction with V2 layout
2. Blog special case (no locale in path)
3. Template-driven page enumeration (when implemented)
4. Quota enforcement (max_pages per section)
5. Mandatory vs optional page selection

Per specs/06_page_planning.md and specs/32_platform_aware_content_layout.md.
"""

import pytest
from typing import Dict, Any

from src.launch.workers.w4_ia_planner.worker import (
    compute_output_path,
    plan_pages_for_section,
)


# Default subdomain_roots configuration
DEFAULT_SUBDOMAIN_ROOTS = {
    "products": "content/products.aspose.org",
    "docs": "content/docs.aspose.org",
    "reference": "content/reference.aspose.org",
    "kb": "content/kb.aspose.org",
    "blog": "content/blog.aspose.org",
}


class TestComputeOutputPathWithFamily:
    """Tests for compute_output_path with family parameter."""

    def test_compute_output_path_includes_family(self):
        """Output path should include family segment."""
        path = compute_output_path(
            section="products",
            slug="overview",
            family="note",
            subdomain_roots=DEFAULT_SUBDOMAIN_ROOTS,
            platform="python",
            locale="en",
        )
        assert path == "content/products.aspose.org/note/en/python/overview.md"
        assert "note" in path
        assert "//" not in path

    def test_blog_path_no_locale(self):
        """Blog paths should NOT contain locale segment."""
        path = compute_output_path(
            section="blog",
            slug="announcement",
            family="note",
            subdomain_roots=DEFAULT_SUBDOMAIN_ROOTS,
            platform="python",
            locale="en",
        )
        assert path == "content/blog.aspose.org/note/python/announcement/index.md"
        assert "/en/" not in path
        assert "/note/" in path
        assert "/python/" in path

    def test_blog_uses_bundle_style(self):
        """Blog should use bundle-style paths with index.md."""
        path = compute_output_path(
            section="blog",
            slug="announcement",
            family="3d",
            subdomain_roots=DEFAULT_SUBDOMAIN_ROOTS,
            platform="java",
            locale="de",
        )
        # Blog ignores locale and uses bundle style
        assert path == "content/blog.aspose.org/3d/java/announcement/index.md"
        assert path.endswith("/index.md")
        assert "/de/" not in path

    def test_docs_path_with_family(self):
        """Docs section should include family in path."""
        path = compute_output_path(
            section="docs",
            slug="getting-started",
            family="3d",
            subdomain_roots=DEFAULT_SUBDOMAIN_ROOTS,
            platform="python",
            locale="en",
        )
        assert path == "content/docs.aspose.org/3d/en/python/getting-started.md"
        assert "/3d/" in path

    def test_reference_path_with_family(self):
        """Reference section should include family in path."""
        path = compute_output_path(
            section="reference",
            slug="api-overview",
            family="cells",
            subdomain_roots=DEFAULT_SUBDOMAIN_ROOTS,
            platform="typescript",
            locale="ja",
        )
        assert path == "content/reference.aspose.org/cells/ja/typescript/api-overview.md"
        assert "/cells/" in path
        assert "/ja/" in path

    def test_kb_path_with_family(self):
        """KB section should include family in path."""
        path = compute_output_path(
            section="kb",
            slug="faq",
            family="words",
            subdomain_roots=DEFAULT_SUBDOMAIN_ROOTS,
            platform="go",
            locale="zh",
        )
        assert path == "content/kb.aspose.org/words/zh/go/faq.md"
        assert "/words/" in path
        assert "/zh/" in path

    def test_no_double_slashes_any_section(self):
        """No section should produce double slashes."""
        for section in ["products", "docs", "reference", "kb", "blog"]:
            for family in ["note", "cells", "3d", "words"]:
                path = compute_output_path(
                    section=section,
                    slug="test-page",
                    family=family,
                    subdomain_roots=DEFAULT_SUBDOMAIN_ROOTS,
                    platform="python",
                    locale="en",
                )
                assert "//" not in path, f"Double slash in {section}/{family} path: {path}"

    def test_family_segment_always_present(self):
        """Family should always appear in paths."""
        for section in ["products", "docs", "reference", "kb", "blog"]:
            path = compute_output_path(
                section=section,
                slug="test-page",
                family="note",
                subdomain_roots=DEFAULT_SUBDOMAIN_ROOTS,
                platform="python",
                locale="en",
            )
            assert "/note/" in path, f"Family not in {section} path: {path}"


class TestPlanPagesForSectionWithFamily:
    """Tests for plan_pages_for_section with family parameter."""

    @pytest.fixture
    def minimal_product_facts(self) -> Dict[str, Any]:
        """Minimal product facts for testing."""
        return {
            "product_name": "Aspose.3D for Python",
            "product_slug": "",  # Empty to test family override
            "claims": [],
            "workflows": [],
            "api_surface_summary": {},
        }

    @pytest.fixture
    def minimal_snippet_catalog(self) -> Dict[str, Any]:
        """Minimal snippet catalog for testing."""
        return {
            "snippets": [],
        }

    def test_products_section_uses_family_3d(
        self, minimal_product_facts, minimal_snippet_catalog
    ):
        """Products section should use family=3d in paths."""
        pages = plan_pages_for_section(
            section="products",
            launch_tier="minimal",
            product_facts=minimal_product_facts,
            snippet_catalog=minimal_snippet_catalog,
            family="3d",
            subdomain_roots=DEFAULT_SUBDOMAIN_ROOTS,
            platform="python",
            locale="en",
        )
        assert len(pages) >= 1
        assert pages[0]["output_path"] == "content/products.aspose.org/3d/en/python/overview.md"
        assert "/3d/" in pages[0]["output_path"]

    def test_docs_section_uses_family_3d(
        self, minimal_product_facts, minimal_snippet_catalog
    ):
        """Docs section should use family=3d in paths."""
        pages = plan_pages_for_section(
            section="docs",
            launch_tier="minimal",
            product_facts=minimal_product_facts,
            snippet_catalog=minimal_snippet_catalog,
            family="3d",
            subdomain_roots=DEFAULT_SUBDOMAIN_ROOTS,
            platform="python",
            locale="en",
        )
        assert len(pages) >= 1
        assert pages[0]["output_path"] == "content/docs.aspose.org/3d/en/python/getting-started.md"
        assert "/3d/" in pages[0]["output_path"]

    def test_reference_section_uses_family_3d(
        self, minimal_product_facts, minimal_snippet_catalog
    ):
        """Reference section should use family=3d in paths."""
        pages = plan_pages_for_section(
            section="reference",
            launch_tier="minimal",
            product_facts=minimal_product_facts,
            snippet_catalog=minimal_snippet_catalog,
            family="3d",
            subdomain_roots=DEFAULT_SUBDOMAIN_ROOTS,
            platform="python",
            locale="en",
        )
        assert len(pages) >= 1
        assert pages[0]["output_path"] == "content/reference.aspose.org/3d/en/python/api-overview.md"
        assert "/3d/" in pages[0]["output_path"]

    def test_kb_section_uses_family_3d(
        self, minimal_product_facts, minimal_snippet_catalog
    ):
        """KB section should use family=3d in paths."""
        pages = plan_pages_for_section(
            section="kb",
            launch_tier="minimal",
            product_facts=minimal_product_facts,
            snippet_catalog=minimal_snippet_catalog,
            family="3d",
            subdomain_roots=DEFAULT_SUBDOMAIN_ROOTS,
            platform="python",
            locale="en",
        )
        assert len(pages) >= 1
        assert pages[0]["output_path"] == "content/kb.aspose.org/3d/en/python/faq.md"
        assert "/3d/" in pages[0]["output_path"]

    def test_blog_section_uses_family_3d_no_locale(
        self, minimal_product_facts, minimal_snippet_catalog
    ):
        """Blog section should use family=3d WITHOUT locale in paths."""
        pages = plan_pages_for_section(
            section="blog",
            launch_tier="minimal",
            product_facts=minimal_product_facts,
            snippet_catalog=minimal_snippet_catalog,
            family="3d",
            subdomain_roots=DEFAULT_SUBDOMAIN_ROOTS,
            platform="python",
            locale="en",
        )
        assert len(pages) >= 1
        assert pages[0]["output_path"] == "content/blog.aspose.org/3d/python/announcement/index.md"
        assert "/3d/" in pages[0]["output_path"]
        assert "/en/" not in pages[0]["output_path"]

    def test_all_sections_include_family_in_seo(
        self, minimal_product_facts, minimal_snippet_catalog
    ):
        """All sections should include family in seo_keywords."""
        for section in ["products", "docs", "reference", "kb", "blog"]:
            pages = plan_pages_for_section(
                section=section,
                launch_tier="minimal",
                product_facts=minimal_product_facts,
                snippet_catalog=minimal_snippet_catalog,
                family="3d",
                subdomain_roots=DEFAULT_SUBDOMAIN_ROOTS,
                platform="python",
                locale="en",
            )
            assert len(pages) >= 1
            assert "3d" in pages[0]["seo_keywords"], f"Family not in {section} seo_keywords"

    def test_different_families_produce_different_paths(
        self, minimal_product_facts, minimal_snippet_catalog
    ):
        """Different families should produce different paths."""
        families = ["3d", "note", "cells", "words"]
        paths_by_family = {}

        for family in families:
            pages = plan_pages_for_section(
                section="products",
                launch_tier="minimal",
                product_facts=minimal_product_facts,
                snippet_catalog=minimal_snippet_catalog,
                family=family,
                subdomain_roots=DEFAULT_SUBDOMAIN_ROOTS,
                platform="python",
                locale="en",
            )
            paths_by_family[family] = pages[0]["output_path"]

        # All paths should be unique
        assert len(set(paths_by_family.values())) == len(families)

        # Each path should contain its family
        for family, path in paths_by_family.items():
            assert f"/{family}/" in path


class TestV2LayoutCompliance:
    """Tests for V2 layout format compliance."""

    def test_v2_products_path_format(self):
        """Products paths should match V2 format: content/<subdomain>/<family>/<locale>/<platform>/<slug>.md"""
        path = compute_output_path(
            section="products",
            slug="overview",
            family="3d",
            subdomain_roots=DEFAULT_SUBDOMAIN_ROOTS,
            platform="python",
            locale="en",
        )
        # Expected: content/products.aspose.org/3d/en/python/overview.md
        parts = path.split("/")
        assert parts[0] == "content"
        assert parts[1] == "products.aspose.org"
        assert parts[2] == "3d"  # family
        assert parts[3] == "en"  # locale
        assert parts[4] == "python"  # platform
        assert parts[5] == "overview.md"  # slug

    def test_v2_docs_path_format(self):
        """Docs paths should match V2 format: content/<subdomain>/<family>/<locale>/<platform>/<slug>.md"""
        path = compute_output_path(
            section="docs",
            slug="getting-started",
            family="note",
            subdomain_roots=DEFAULT_SUBDOMAIN_ROOTS,
            platform="java",
            locale="de",
        )
        # Expected: content/docs.aspose.org/note/de/java/getting-started.md
        parts = path.split("/")
        assert parts[0] == "content"
        assert parts[1] == "docs.aspose.org"
        assert parts[2] == "note"  # family
        assert parts[3] == "de"  # locale
        assert parts[4] == "java"  # platform
        assert parts[5] == "getting-started.md"  # slug

    def test_v2_blog_path_format(self):
        """Blog paths should match V2 format: content/<subdomain>/<family>/<platform>/<slug>/index.md (NO LOCALE)"""
        path = compute_output_path(
            section="blog",
            slug="announcement",
            family="cells",
            subdomain_roots=DEFAULT_SUBDOMAIN_ROOTS,
            platform="typescript",
            locale="es",
        )
        # Expected: content/blog.aspose.org/cells/typescript/announcement/index.md
        parts = path.split("/")
        assert parts[0] == "content"
        assert parts[1] == "blog.aspose.org"
        assert parts[2] == "cells"  # family
        assert parts[3] == "typescript"  # platform (NO locale!)
        assert parts[4] == "announcement"  # slug
        assert parts[5] == "index.md"  # bundle-style


# TODO: Template enumeration tests (to be implemented in future TC)
# These tests will be added when template-driven enumeration is fully implemented:
#
# class TestTemplateEnumeration:
#     """Tests for template-driven page enumeration."""
#
#     def test_enumerate_templates_respects_max_pages(self):
#         """Template enumeration should respect max_pages quota."""
#         pass
#
#     def test_mandatory_pages_always_included(self):
#         """Mandatory pages should always be included even with low quota."""
#         pass
#
#     def test_deterministic_page_ordering(self):
#         """Page order should be deterministic (stable sort by slug)."""
#         pass
#
#     def test_variant_selection_by_launch_tier(self):
#         """Template variants should be selected based on launch_tier."""
#         pass
