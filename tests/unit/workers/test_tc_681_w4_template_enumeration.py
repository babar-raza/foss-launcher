"""Unit tests for TC-681: W4 Template-Driven Page Enumeration and Path Fixes.

Tests verify:
1. product_slug correctly uses run_config.family (not product_facts.product_slug)
2. subdomain is correctly mapped from section
3. output_path includes family segment (no double slashes)
4. paths conform to V1 layout: content/<subdomain>/<family>/<locale>/...
"""

import pytest
from pathlib import Path

from launch.workers.w4_ia_planner.worker import (
    get_subdomain_for_section,
    compute_output_path,
    compute_url_path,
)


class TestPathConstruction:
    """Test path construction functions for TC-681."""

    def test_get_subdomain_for_section(self):
        """Verify correct subdomain mapping for each section."""
        assert get_subdomain_for_section("products") == "products.aspose.org"
        assert get_subdomain_for_section("docs") == "docs.aspose.org"
        assert get_subdomain_for_section("reference") == "reference.aspose.org"
        assert get_subdomain_for_section("kb") == "kb.aspose.org"
        assert get_subdomain_for_section("blog") == "blog.aspose.org"

    def test_compute_output_path_includes_family(self):
        """Verify output_path includes family segment (TC-681 bug fix)."""
        path = compute_output_path(
            section="docs",
            slug="overview",
            product_slug="3d",  # This should be run_config.family
        )
        assert "3d" in path, "output_path must include family segment"
        assert "//" not in path, "output_path must not have double slashes"
        # TC-2000: No section subdirectory
        assert path == "content/docs.aspose.org/3d/en/overview.md"

    def test_compute_output_path_uses_correct_subdomain(self):
        """Verify output_path uses correct subdomain for each section."""
        products_path = compute_output_path("products", "overview", "3d")
        assert "products.aspose.org" in products_path

        docs_path = compute_output_path("docs", "getting-started", "3d")
        assert "docs.aspose.org" in docs_path

        kb_path = compute_output_path("kb", "faq", "3d")
        assert "kb.aspose.org" in kb_path

    def test_compute_output_path_no_double_slashes(self):
        """Verify no double slashes in any output paths."""
        sections = ["products", "docs", "reference", "kb", "blog"]
        for section in sections:
            path = compute_output_path(section, "test-page", "3d")
            assert "//" not in path, f"Section {section} has double slash in path: {path}"

    def test_compute_url_path_includes_family(self):
        """Verify URL path includes family segment."""
        url = compute_url_path("docs", "overview", product_slug="3d")
        assert "3d" in url, "url_path must include family"
        # Section is implicit in subdomain, NOT in URL path (specs/33_public_url_mapping.md)
        assert url == "/3d/overview/"

    def test_paths_conform_to_hugo_layout(self):
        """Verify paths follow Hugo layout: <subdomain>/<family>/<locale>/<slug>.md (no section subdir)."""
        path = compute_output_path("docs", "guide", "cells", locale="en")

        # TC-2000: Expected format: content/docs.aspose.org/cells/en/guide.md (no section subdir)
        parts = path.split("/")
        assert parts[0] == "content"
        assert parts[1] == "docs.aspose.org"  # subdomain
        assert parts[2] == "cells"  # family
        assert parts[3] == "en"  # locale
        assert parts[4] == "guide.md"  # slug.md (no section subdirectory)


class TestProductsLayout:
    """Test products section layout."""

    def test_products_path_family_first(self):
        """TC-2102: Verify products section uses family-first ordering (same as all non-blog sections)."""
        path = compute_output_path("products", "overview", "3d")
        # TC-2102: Products uses same {family}/{locale}/ as all non-blog sections
        assert path == "content/products.aspose.org/3d/en/overview.md"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
