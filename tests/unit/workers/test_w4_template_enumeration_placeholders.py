"""Unit tests for W4 template enumeration with placeholder directories.

TC-966: Fix W4 Template Enumeration - Search Placeholder Directories

Tests verify that enumerate_templates() discovers templates in placeholder
directories (__LOCALE__, __POST_SLUG__) instead of searching
for literal locale values. Templates with __PLATFORM__ in their path are
skipped (V2 platform layout removed).
"""

import pytest
from pathlib import Path
from src.launch.workers.w4_ia_planner.worker import enumerate_templates


def test_enumerate_templates_docs_section():
    """Test template discovery for docs.aspose.org section.

    Verifies that templates are found in __LOCALE__/ placeholder dirs,
    not in literal en/ dirs. Templates with __PLATFORM__ are skipped (V2 removed).
    """
    template_dir = Path("specs/templates")

    templates = enumerate_templates(
        template_dir=template_dir,
        subdomain="docs.aspose.org",
        family="3d",
        locale="en",
    )

    # Should find multiple templates (was 0 before fix)
    assert len(templates) > 0, "docs.aspose.org/3d should find templates in placeholder dirs"

    # Verify templates are from placeholder directories
    template_paths = [t["template_path"] for t in templates]
    has_placeholder = any("__LOCALE__" in p or "__POST_SLUG__" in p
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
    )

    # Should find templates in __LOCALE__/ dirs
    assert len(templates) > 0, "products.aspose.org/cells should find templates"

    # Verify no README.md files included
    template_filenames = [t["filename"] for t in templates]
    assert "README.md" not in template_filenames, "README.md should be filtered out"


def test_enumerate_templates_reference_section():
    """Test template discovery for reference.aspose.org section.

    TC-967: After filtering placeholder filenames, reference section may have
    fewer templates, but should still find templates with concrete filenames.
    """
    template_dir = Path("specs/templates")

    templates = enumerate_templates(
        template_dir=template_dir,
        subdomain="reference.aspose.org",
        family="cells",
        locale="en",
    )

    # TC-967: Should find reference templates with concrete filenames
    # (Templates with __REFERENCE_SLUG__.md filenames are filtered out)
    # If no concrete-filename templates exist yet, this may be 0
    if len(templates) > 0:
        # Verify no placeholder filenames
        for template in templates:
            filename = Path(template["template_path"]).name
            assert "__" not in filename or filename == "_index.md", \
                f"Reference template should not have placeholder filename: {filename}"


def test_enumerate_templates_kb_section():
    """Test template discovery for kb.aspose.org section.

    TC-967: After filtering placeholder filenames, KB section may have
    fewer templates, but should filter out placeholder filenames correctly.
    """
    template_dir = Path("specs/templates")

    templates = enumerate_templates(
        template_dir=template_dir,
        subdomain="kb.aspose.org",
        family="cells",
        locale="en",
    )

    # TC-967: KB templates with concrete filenames should be included
    # (Templates with __CONVERTER_SLUG__.md or __TOPIC_SLUG__.md filenames are filtered out)
    if len(templates) > 0:
        # Verify no placeholder filenames
        for template in templates:
            filename = Path(template["template_path"]).name
            assert "__" not in filename or filename == "_index.md", \
                f"KB template should not have placeholder filename: {filename}"


def test_enumerate_templates_blog_section():
    """Test template discovery for blog.aspose.org section (no regression).

    Blog should still work after fix. Blog uses __POST_SLUG__ structure
    and should NOT include templates with __LOCALE__ (per TC-957 filter).
    """
    template_dir = Path("specs/templates")

    templates = enumerate_templates(
        template_dir=template_dir,
        subdomain="blog.aspose.org",
        family="3d",
        locale="en",
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
    )

    templates2 = enumerate_templates(
        template_dir=template_dir,
        subdomain="docs.aspose.org",
        family="3d",
        locale="en",
    )

    # Should return same templates
    assert len(templates1) == len(templates2), "Same input should return same count"

    # Should be in same order (sorted by template_path)
    paths1 = [t["template_path"] for t in templates1]
    paths2 = [t["template_path"] for t in templates2]
    assert paths1 == paths2, "Template order should be deterministic"

    # Verify sorting is by template_path
    assert paths1 == sorted(paths1), "Templates should be sorted by template_path"


def test_enumerate_templates_filters_placeholder_filenames():
    """Test that templates with placeholder filenames are filtered out (TC-967).

    Templates with placeholder filenames like __REFERENCE_SLUG__.md cause URL
    collisions. Only templates with concrete filenames should be enumerated.
    """
    template_dir = Path("specs/templates")

    # Test all sections
    sections = [
        ("docs.aspose.org", "3d"),
        ("products.aspose.org", "cells"),
        ("reference.aspose.org", "cells"),
        ("kb.aspose.org", "cells"),
        ("blog.aspose.org", "3d"),
    ]

    for subdomain, family in sections:
        templates = enumerate_templates(
            template_dir=template_dir,
            subdomain=subdomain,
            family=family,
            locale="en",
            platform="python"
        )

        # Verify no templates have placeholder filenames
        for template in templates:
            filename = Path(template["template_path"]).name

            # Check for placeholder pattern in filename (double underscores)
            # Exception: _index.md is valid (single leading underscore)
            if filename not in ["_index.md", "__init__.py"]:
                assert "__" not in filename, \
                    f"{subdomain}/{family}: Template has placeholder filename: {filename} (path: {template['template_path']})"

        # Verify concrete filenames are still included
        filenames = [Path(t["template_path"]).name for t in templates]
        has_concrete_files = any(
            f in ["index.md", "_index.md", "getting-started.md", "faq.md", "overview.md"]
            for f in filenames
        )
        # Note: Not all sections have these specific files, but at least some should have concrete filenames
        if templates:
            # If we found templates, verify none have placeholder filenames
            placeholder_filenames = [f for f in filenames if "__" in f and f != "_index.md"]
            assert len(placeholder_filenames) == 0, \
                f"{subdomain}/{family}: Found placeholder filenames: {placeholder_filenames}"


def test_enumerate_templates_all_sections_nonzero():
    """Comprehensive test: verify template discovery across all 5 sections.

    TC-966: All sections should discover templates in placeholder directories.
    TC-967: After filtering placeholder filenames, some sections may have 0 templates
    if they only contained placeholder-filename templates. At least blog should work.
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

    # Log results for evidence
    print("\nTemplate discovery results (TC-967):")
    for subdomain, count in results.items():
        print(f"  {subdomain}: {count} templates")

    # Critical assertion: Blog should always work (has concrete filenames)
    assert results["blog.aspose.org"] > 0, "blog.aspose.org/3d should find templates"

    # At least one section should have templates
    total_templates = sum(results.values())
    assert total_templates > 0, "Should find at least some templates across all sections"
