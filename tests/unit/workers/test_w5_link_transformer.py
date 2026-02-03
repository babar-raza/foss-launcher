"""
Unit tests for W5 SectionWriter link transformer (TC-938 integration).

Tests the transform_cross_section_links() function that converts relative
cross-section links to absolute URLs during draft generation.

Per specs/06_page_planning.md, cross-section links must be absolute to work
correctly in the subdomain architecture (blog.aspose.org, docs.aspose.org, etc.).
"""

import pytest
from src.launch.workers.w5_section_writer.link_transformer import (
    transform_cross_section_links,
)


def test_transform_blog_to_docs_link():
    """Test blog → docs link transformed to absolute URL."""
    content = "See the [Getting Started Guide](../../docs/3d/python/getting-started/)."
    page_metadata = {
        "locale": "en",
        "family": "3d",
        "platform": "python",
    }

    result = transform_cross_section_links(
        markdown_content=content,
        current_section="blog",
        page_metadata=page_metadata,
    )

    # Should transform to absolute URL
    assert "https://docs.aspose.org/3d/python/getting-started/" in result
    assert "[Getting Started Guide]" in result
    # Should not contain relative path
    assert "../../docs/" not in result


def test_transform_docs_to_reference_link():
    """Test docs → reference link transformed to absolute URL."""
    content = "See the [API Reference](../../reference/cells/python/api/)."
    page_metadata = {
        "locale": "en",
        "family": "cells",
        "platform": "python",
    }

    result = transform_cross_section_links(
        markdown_content=content,
        current_section="docs",
        page_metadata=page_metadata,
    )

    # Should transform to absolute URL
    assert "https://reference.aspose.org/cells/python/api/" in result
    assert "[API Reference]" in result
    assert "../../reference/" not in result


def test_transform_kb_to_docs_link():
    """Test kb → docs link transformed to absolute URL."""
    content = "Follow the [installation tutorial](../../docs/cells/python/installation/)."
    page_metadata = {
        "locale": "en",
        "family": "cells",
        "platform": "python",
    }

    result = transform_cross_section_links(
        markdown_content=content,
        current_section="kb",
        page_metadata=page_metadata,
    )

    # Should transform to absolute URL
    assert "https://docs.aspose.org/cells/python/installation/" in result
    assert "[installation tutorial]" in result
    assert "../../docs/" not in result


def test_preserve_same_section_link():
    """Test same-section link remains relative."""
    content = "See the [Next Page](./next-page/)."
    page_metadata = {
        "locale": "en",
        "family": "cells",
        "platform": "python",
    }

    result = transform_cross_section_links(
        markdown_content=content,
        current_section="docs",
        page_metadata=page_metadata,
    )

    # Should remain unchanged (same section, no transformation)
    assert result == content
    assert "./next-page/" in result


def test_preserve_internal_anchor():
    """Test internal anchor remains unchanged."""
    content = "Jump to [Installation](#installation)."
    page_metadata = {
        "locale": "en",
        "family": "cells",
        "platform": "python",
    }

    result = transform_cross_section_links(
        markdown_content=content,
        current_section="docs",
        page_metadata=page_metadata,
    )

    # Should remain unchanged (internal anchor)
    assert result == content
    assert "#installation" in result


def test_preserve_external_link():
    """Test external link remains unchanged."""
    content = "Visit [Aspose](https://www.aspose.com/)."
    page_metadata = {
        "locale": "en",
        "family": "cells",
        "platform": "python",
    }

    result = transform_cross_section_links(
        markdown_content=content,
        current_section="docs",
        page_metadata=page_metadata,
    )

    # Should remain unchanged (external link)
    assert result == content
    assert "https://www.aspose.com/" in result


def test_transform_multiple_links():
    """Test multiple links in same content."""
    content = """
See the [Getting Started](../../docs/3d/python/getting-started/) guide.
Check the [API Reference](../../reference/3d/python/api/) for details.
Also see [Next Page](./next-page/) for more.
"""
    page_metadata = {
        "locale": "en",
        "family": "3d",
        "platform": "python",
    }

    result = transform_cross_section_links(
        markdown_content=content,
        current_section="blog",
        page_metadata=page_metadata,
    )

    # First link should be transformed (blog → docs)
    assert "https://docs.aspose.org/3d/python/getting-started/" in result
    # Second link should be transformed (blog → reference)
    assert "https://reference.aspose.org/3d/python/api/" in result
    # Third link should remain relative (same section-style relative link)
    assert "./next-page/" in result


def test_transform_docs_to_docs_link_not_transformed():
    """Test docs → docs link (same section) remains relative."""
    content = "See [Another Guide](../../docs/cells/python/another-guide/)."
    page_metadata = {
        "locale": "en",
        "family": "cells",
        "platform": "python",
    }

    result = transform_cross_section_links(
        markdown_content=content,
        current_section="docs",
        page_metadata=page_metadata,
    )

    # Should remain unchanged (docs → docs, same section)
    assert result == content
    assert "../../docs/" in result


def test_transform_section_index_link():
    """Test link to section index page (no slug)."""
    content = "Visit [Docs Home](../../docs/3d/python/)."
    page_metadata = {
        "locale": "en",
        "family": "3d",
        "platform": "python",
    }

    result = transform_cross_section_links(
        markdown_content=content,
        current_section="blog",
        page_metadata=page_metadata,
    )

    # Should transform to section index URL (no slug)
    assert "https://docs.aspose.org/3d/python/" in result
    assert "[Docs Home]" in result


def test_transform_with_subsections():
    """Test link with nested subsections."""
    content = "See [Advanced Guide](../../docs/cells/python/developer-guide/advanced/features/)."
    page_metadata = {
        "locale": "en",
        "family": "cells",
        "platform": "python",
    }

    result = transform_cross_section_links(
        markdown_content=content,
        current_section="blog",
        page_metadata=page_metadata,
    )

    # Should transform and preserve subsections in path
    assert "https://docs.aspose.org/cells/python/developer-guide/advanced/features/" in result
    assert "[Advanced Guide]" in result


def test_transform_malformed_link_keeps_original():
    """Test graceful handling of malformed link."""
    content = "See [Bad Link](../../docs/)."  # Too short, can't parse
    page_metadata = {
        "locale": "en",
        "family": "cells",
        "platform": "python",
    }

    result = transform_cross_section_links(
        markdown_content=content,
        current_section="blog",
        page_metadata=page_metadata,
    )

    # Should keep original (can't parse)
    # Warning logged but no exception
    assert "[Bad Link]" in result


def test_transform_products_to_docs_link():
    """Test products → docs link transformed to absolute URL."""
    content = "Read the [Documentation](../../docs/words/python/guide/)."
    page_metadata = {
        "locale": "en",
        "family": "words",
        "platform": "python",
    }

    result = transform_cross_section_links(
        markdown_content=content,
        current_section="products",
        page_metadata=page_metadata,
    )

    # Should transform to absolute URL
    assert "https://docs.aspose.org/words/python/guide/" in result
    assert "[Documentation]" in result


def test_transform_link_without_dots():
    """Test link without leading ../ (direct section reference)."""
    content = "See [Guide](docs/3d/python/getting-started/)."
    page_metadata = {
        "locale": "en",
        "family": "3d",
        "platform": "python",
    }

    result = transform_cross_section_links(
        markdown_content=content,
        current_section="blog",
        page_metadata=page_metadata,
    )

    # Should transform (detects docs/ pattern regardless of ../)
    assert "https://docs.aspose.org/3d/python/getting-started/" in result
    assert "[Guide]" in result


def test_no_links_returns_unchanged():
    """Test content with no links returns unchanged."""
    content = "This is plain text with no markdown links."
    page_metadata = {
        "locale": "en",
        "family": "cells",
        "platform": "python",
    }

    result = transform_cross_section_links(
        markdown_content=content,
        current_section="docs",
        page_metadata=page_metadata,
    )

    # Should remain unchanged
    assert result == content


def test_empty_content_returns_empty():
    """Test empty content returns empty."""
    content = ""
    page_metadata = {
        "locale": "en",
        "family": "cells",
        "platform": "python",
    }

    result = transform_cross_section_links(
        markdown_content=content,
        current_section="docs",
        page_metadata=page_metadata,
    )

    # Should remain empty
    assert result == ""
