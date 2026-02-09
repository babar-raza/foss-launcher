"""TC-926: Unit tests for W4 IAPlanner compute_output_path fix.

Tests verify:
1. Blog posts use correct format (no locale, index.md)
2. Empty product_slug handled gracefully (no double slashes)
3. All sections generate correct paths per specs/18_site_repo_layout.md
"""

from src.launch.workers.w4_ia_planner.worker import compute_output_path


def test_compute_output_path_blog_with_family():
    """Blog path should be: content/blog.aspose.org/3d/announcement/index.md"""
    result = compute_output_path(
        section="blog",
        slug="announcement",
        product_slug="3d",
    )
    assert result == "content/blog.aspose.org/3d/announcement/index.md"
    assert "//" not in result, "Path should not contain double slashes"


def test_compute_output_path_blog_empty_family():
    """Blog with empty family should still work (no double slash)"""
    result = compute_output_path(
        section="blog",
        slug="announcement",
        product_slug="",
    )
    # Should be content/blog.aspose.org/announcement/index.md (no family segment)
    assert result == "content/blog.aspose.org/announcement/index.md"
    assert "//" not in result, "Path should not contain double slashes"


def test_compute_output_path_blog_no_locale():
    """Blog paths should NOT include locale segment"""
    result = compute_output_path(
        section="blog",
        slug="announcement",
        product_slug="3d",
        locale="en"
    )
    # Even with locale specified, blog should not include /en/ in path
    assert "/en/" not in result, "Blog paths should not include locale"
    assert result.endswith("/index.md"), "Blog posts should use index.md"


def test_compute_output_path_docs_with_family():
    """Docs path should be: content/docs.aspose.org/3d/en/docs/getting-started.md"""
    result = compute_output_path(
        section="docs",
        slug="getting-started",
        product_slug="3d",
    )
    expected = "content/docs.aspose.org/3d/en/docs/getting-started.md"
    assert result == expected
    assert "//" not in result, "Path should not contain double slashes"


def test_compute_output_path_docs_empty_family():
    """Docs with empty family should not have double slash"""
    result = compute_output_path(
        section="docs",
        slug="getting-started",
        product_slug="",
    )
    # Should be content/docs.aspose.org/en/docs/getting-started.md (no family segment)
    assert "//" not in result, "Path should not contain double slashes"
    assert result == "content/docs.aspose.org/en/docs/getting-started.md"


def test_compute_output_path_products_with_family():
    """Products path should be: content/products.aspose.org/3d/en/overview.md"""
    result = compute_output_path(
        section="products",
        slug="overview",
        product_slug="3d",
    )
    expected = "content/products.aspose.org/3d/en/overview.md"
    assert result == expected
    assert "//" not in result, "Path should not contain double slashes"


def test_compute_output_path_products_empty_family():
    """Products with empty family should not have double slash"""
    result = compute_output_path(
        section="products",
        slug="overview",
        product_slug="",
    )
    # Should be content/products.aspose.org/en/overview.md (no family segment, no double slash)
    assert "//" not in result, "Path should not contain double slashes"
    assert result == "content/products.aspose.org/en/overview.md"


def test_compute_output_path_reference_with_family():
    """Reference path should use reference.aspose.org subdomain"""
    result = compute_output_path(
        section="reference",
        slug="api-overview",
        product_slug="3d",
    )
    expected = "content/reference.aspose.org/3d/en/reference/api-overview.md"
    assert result == expected
    assert result.startswith("content/reference.aspose.org/")
    assert "//" not in result, "Path should not contain double slashes"


def test_compute_output_path_kb_with_family():
    """KB path should use kb.aspose.org subdomain"""
    result = compute_output_path(
        section="kb",
        slug="faq",
        product_slug="3d",
    )
    expected = "content/kb.aspose.org/3d/en/kb/faq.md"
    assert result == expected
    assert result.startswith("content/kb.aspose.org/")
    assert "//" not in result, "Path should not contain double slashes"


def test_compute_output_path_kb_empty_family():
    """KB with empty family should not have double slash"""
    result = compute_output_path(
        section="kb",
        slug="faq",
        product_slug="",
    )
    assert "//" not in result, "Path should not contain double slashes"
    assert result == "content/kb.aspose.org/en/kb/faq.md"


def test_compute_output_path_subdomain_auto_determined():
    """Subdomain should be auto-determined from section if not provided"""
    result_docs = compute_output_path(
        section="docs",
        slug="test",
        product_slug="3d",
        subdomain=None  # Let it auto-determine
    )
    assert "docs.aspose.org" in result_docs

    result_blog = compute_output_path(
        section="blog",
        slug="test",
        product_slug="3d",
        subdomain=None  # Let it auto-determine
    )
    assert "blog.aspose.org" in result_blog


def test_compute_output_path_whitespace_product_slug():
    """Product slug with only whitespace should be treated as empty"""
    result = compute_output_path(
        section="docs",
        slug="test",
        product_slug="   ",  # Whitespace only
    )
    # Should not include the whitespace as a path segment
    assert "//" not in result, "Path should not contain double slashes"
    assert "/   /" not in result, "Path should not include whitespace segment"
