"""TC-926: Unit tests for W4 IAPlanner compute_output_path fix.

Tests verify:
1. Blog posts use correct format (no locale, index.md)
2. Empty product_slug handled gracefully (no double slashes)
3. All sections generate correct paths per Hugo layout conventions
4. TC-2000: No section subdirectory in output paths
5. TC-2001: Products uses locale-first ordering
6. TC-2002: index/_index slugs become _index.md (branch bundle) for non-blog
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
    """TC-2000: Docs path should NOT include /docs/ section subdirectory."""
    result = compute_output_path(
        section="docs",
        slug="getting-started",
        product_slug="3d",
    )
    expected = "content/docs.aspose.org/3d/en/getting-started.md"
    assert result == expected
    assert "/docs/" not in result, "Section subdirectory should not appear in path"
    assert "//" not in result, "Path should not contain double slashes"


def test_compute_output_path_docs_empty_family():
    """Docs with empty family should not have double slash"""
    result = compute_output_path(
        section="docs",
        slug="getting-started",
        product_slug="",
    )
    # Should be content/docs.aspose.org/en/getting-started.md (no family segment, no section subdir)
    assert "//" not in result, "Path should not contain double slashes"
    assert result == "content/docs.aspose.org/en/getting-started.md"
    assert "/docs/" not in result, "Section subdirectory should not appear in path"


def test_compute_output_path_products_with_family():
    """Products path should use family-first: content/products.aspose.org/3d/en/overview.md"""
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
    """TC-2000: Reference path should NOT include /reference/ section subdirectory."""
    result = compute_output_path(
        section="reference",
        slug="api-overview",
        product_slug="3d",
    )
    expected = "content/reference.aspose.org/3d/en/api-overview.md"
    assert result == expected
    assert result.startswith("content/reference.aspose.org/")
    assert "/reference/" not in result, "Section subdirectory should not appear in path"
    assert "//" not in result, "Path should not contain double slashes"


def test_compute_output_path_kb_with_family():
    """TC-2000: KB path should NOT include /kb/ section subdirectory."""
    result = compute_output_path(
        section="kb",
        slug="faq",
        product_slug="3d",
    )
    expected = "content/kb.aspose.org/3d/en/faq.md"
    assert result == expected
    assert result.startswith("content/kb.aspose.org/")
    assert "/kb/" not in result, "Section subdirectory should not appear in path"
    assert "//" not in result, "Path should not contain double slashes"


def test_compute_output_path_kb_empty_family():
    """KB with empty family should not have double slash"""
    result = compute_output_path(
        section="kb",
        slug="faq",
        product_slug="",
    )
    assert "//" not in result, "Path should not contain double slashes"
    assert result == "content/kb.aspose.org/en/faq.md"
    assert "/kb/" not in result, "Section subdirectory should not appear in path"


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


# TC-2002: Hugo branch bundle tests

def test_compute_output_path_index_to_underscore_index():
    """TC-2002: Non-blog index pages should use _index.md (Hugo branch bundle)"""
    result = compute_output_path(section="docs", slug="index", product_slug="3d")
    assert result.endswith("/_index.md"), f"Expected _index.md but got: {result}"
    assert "/docs/" not in result


def test_compute_output_path_underscore_index_preserved():
    """TC-2002: Explicit _index slug should produce _index.md"""
    result = compute_output_path(section="docs", slug="_index", product_slug="3d")
    assert result.endswith("/_index.md")


def test_compute_output_path_blog_index_unchanged():
    """TC-2002: Blog index should remain index.md (leaf bundle)"""
    result = compute_output_path(section="blog", slug="announcement", product_slug="3d")
    assert result.endswith("/index.md"), "Blog should use index.md"


# V2 platform tests

def test_compute_output_path_products_v2_with_platform():
    """Products V2: family-first, locale, platform (same as other sections)"""
    result = compute_output_path(section="products", slug="overview", product_slug="3d", platform="python")
    assert result == "content/products.aspose.org/3d/en/python/overview.md"


def test_compute_output_path_docs_v2_with_platform():
    """TC-2000: Docs V2: family-first, locale, platform, no section subdir"""
    result = compute_output_path(section="docs", slug="getting-started", product_slug="3d", platform="python")
    assert result == "content/docs.aspose.org/3d/en/python/getting-started.md"
    assert "/docs/" not in result
