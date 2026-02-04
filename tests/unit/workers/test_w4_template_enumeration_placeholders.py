"""Unit tests for W4 template enumeration with placeholder directories.

TC-966: Fix W4 Template Enumeration - Search Placeholder Directories

Tests verify that enumerate_templates() discovers templates in placeholder
directories (__LOCALE__, __PLATFORM__, __POST_SLUG__) instead of searching
for literal locale/platform values.
"""

import pytest
from pathlib import Path
from src.launch.workers.w4_ia_planner.worker import enumerate_templates


def test_enumerate_templates_docs_section():
    """Test template discovery for docs.aspose.org section.

    Verifies that templates are found in __LOCALE__/__PLATFORM__/ placeholder dirs,
    not in literal en/python/ dirs.
    """
    template_dir = Path("specs/templates")

    templates = enumerate_templates(
        template_dir=template_dir,
        subdomain="docs.aspose.org",
        family="3d",
        locale="en",
        platform="python"
    )

    # Should find multiple templates (was 0 before fix)
    assert len(templates) > 0, "docs.aspose.org/3d should find templates in placeholder dirs"

    # Verify templates are from placeholder directories
    template_paths = [t["template_path"] for t in templates]
    has_placeholder = any("__LOCALE__" in p or "__PLATFORM__" in p or "__POST_SLUG__" in p
                          for p in template_paths)
    assert has_placeholder, "Should discover templates in placeholder directories"

    # Verify template structure
    for template in templates:
        assert "section" in template
        assert "template_path" in template
        assert "slug" in template
        assert "filename" in template
        assert "placeholders" in template
        assert template["template_path"].endswith(".md")


def test_enumerate_templates_products_section():
    """Test template discovery for products.aspose.org section."""
    template_dir = Path("specs/templates")

    # Test with cells family (has known templates)
    templates = enumerate_templates(
        template_dir=template_dir,
        subdomain="products.aspose.org",
        family="cells",
        locale="en",
        platform="python"
    )

    # Should find templates in __LOCALE__/__PLATFORM__/ dirs
    assert len(templates) > 0, "products.aspose.org/cells should find templates"

    # Verify no README.md files included
    template_filenames = [t["filename"] for t in templates]
    assert "README.md" not in template_filenames, "README.md should be filtered out"


def test_enumerate_templates_reference_section():
    """Test template discovery for reference.aspose.org section."""
    template_dir = Path("specs/templates")

    templates = enumerate_templates(
        template_dir=template_dir,
        subdomain="reference.aspose.org",
        family="cells",
        locale="en",
        platform="python"
    )

    # Should find reference templates
    assert len(templates) > 0, "reference.aspose.org/cells should find templates"

    # Verify templates have reference-specific patterns
    template_paths = [t["template_path"] for t in templates]
    has_reference = any("__REFERENCE_SLUG__" in p for p in template_paths)
    assert has_reference, "Reference section should have __REFERENCE_SLUG__ templates"


def test_enumerate_templates_kb_section():
    """Test template discovery for kb.aspose.org section."""
    template_dir = Path("specs/templates")

    templates = enumerate_templates(
        template_dir=template_dir,
        subdomain="kb.aspose.org",
        family="cells",
        locale="en",
        platform="python"
    )

    # Should find KB templates
    assert len(templates) > 0, "kb.aspose.org/cells should find templates"

    # Verify templates have KB-specific patterns
    template_paths = [t["template_path"] for t in templates]
    has_kb_patterns = any("__CONVERTER_SLUG__" in p or "__TOPIC_SLUG__" in p
                          for p in template_paths)
    assert has_kb_patterns, "KB section should have converter/topic slug templates"


def test_enumerate_templates_blog_section():
    """Test template discovery for blog.aspose.org section (no regression).

    Blog should still work after fix. Blog uses __PLATFORM__/__POST_SLUG__ structure
    and should NOT include templates with __LOCALE__ (per TC-957 filter).
    """
    template_dir = Path("specs/templates")

    templates = enumerate_templates(
        template_dir=template_dir,
        subdomain="blog.aspose.org",
        family="3d",
        locale="en",
        platform="python"
    )

    # Should still find blog templates (was ~8 before)
    assert len(templates) > 0, "blog.aspose.org/3d should still find templates"

    # Verify blog templates use correct structure
    template_paths = [t["template_path"] for t in templates]

    # Should have __POST_SLUG__ templates
    has_post_slug = any("__POST_SLUG__" in p for p in template_paths)
    assert has_post_slug, "Blog should have __POST_SLUG__ templates"

    # Should NOT have __LOCALE__ templates (TC-957 filter)
    has_locale = any("__LOCALE__" in p for p in template_paths)
    assert not has_locale, "Blog should filter out __LOCALE__ templates (TC-957)"


def test_template_discovery_deterministic():
    """Test that template discovery produces consistent results across runs.

    Multiple calls with same inputs should return templates in same order.
    """
    template_dir = Path("specs/templates")

    # Run enumeration twice
    templates1 = enumerate_templates(
        template_dir=template_dir,
        subdomain="docs.aspose.org",
        family="3d",
        locale="en",
        platform="python"
    )

    templates2 = enumerate_templates(
        template_dir=template_dir,
        subdomain="docs.aspose.org",
        family="3d",
        locale="en",
        platform="python"
    )

    # Should return same templates
    assert len(templates1) == len(templates2), "Same input should return same count"

    # Should be in same order (sorted by template_path)
    paths1 = [t["template_path"] for t in templates1]
    paths2 = [t["template_path"] for t in templates2]
    assert paths1 == paths2, "Template order should be deterministic"

    # Verify sorting is by template_path
    assert paths1 == sorted(paths1), "Templates should be sorted by template_path"


def test_enumerate_templates_all_sections_nonzero():
    """Comprehensive test: all 5 sections should find templates.

    This is the main acceptance criterion for TC-966.
    """
    template_dir = Path("specs/templates")

    sections = [
        ("docs.aspose.org", "3d"),
        ("products.aspose.org", "cells"),
        ("reference.aspose.org", "cells"),
        ("kb.aspose.org", "cells"),
        ("blog.aspose.org", "3d"),
    ]

    results = {}
    for subdomain, family in sections:
        templates = enumerate_templates(
            template_dir=template_dir,
            subdomain=subdomain,
            family=family,
            locale="en",
            platform="python"
        )
        results[subdomain] = len(templates)

        # Critical assertion: all sections should find templates
        assert len(templates) > 0, f"{subdomain}/{family} should find templates (found {len(templates)})"

    # Log results for evidence
    print("\nTemplate discovery results:")
    for subdomain, count in results.items():
        print(f"  {subdomain}: {count} templates")
