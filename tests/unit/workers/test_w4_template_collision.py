"""HEAL-BUG2: Unit tests for W4 template collision de-duplication.

Tests the defensive de-duplication logic in classify_templates() that prevents
multiple _index.md variants from causing URL collisions.

Context:
- Phase 0 (HEAL-BUG4): Filtered obsolete blog templates with __LOCALE__
- Phase 2 (HEAL-BUG2): Defensive de-duplication in case variants still collide

Spec references:
- specs/06_page_planning.md (mandatory page policy)
- specs/07_section_templates.md (template structure)
- specs/33_public_url_mapping.md (URL path computation)
"""

import pytest
from typing import List, Dict, Any

from launch.workers.w4_ia_planner.worker import classify_templates


def test_classify_templates_deduplicates_index_pages():
    """Test that classify_templates de-duplicates index pages per section.

    When multiple _index.md variants exist for the same section, only the
    first one (alphabetically by template_path) should be selected.
    """
    templates = [
        {
            "section": "docs",
            "slug": "index",
            "template_path": "specs/templates/docs.aspose.org/cells/en/python/docs/_index.md",
            "filename": "_index.md",
            "variant": "default",
            "is_mandatory": True,
            "placeholders": [],
        },
        {
            "section": "docs",
            "slug": "index",
            "template_path": "specs/templates/docs.aspose.org/cells/en/python/docs/_index.variant-minimal.md",
            "filename": "_index.variant-minimal.md",
            "variant": "minimal",
            "is_mandatory": False,
            "placeholders": [],
        },
        {
            "section": "docs",
            "slug": "index",
            "template_path": "specs/templates/docs.aspose.org/cells/en/python/docs/_index.variant-standard.md",
            "filename": "_index.variant-standard.md",
            "variant": "standard",
            "is_mandatory": False,
            "placeholders": [],
        },
    ]

    mandatory, optional = classify_templates(templates, "standard")

    # Should only have one index page for docs section
    all_templates = mandatory + optional
    index_pages = [t for t in all_templates if t["slug"] == "index" and t["section"] == "docs"]
    assert len(index_pages) == 1, f"Expected 1 index page, found {len(index_pages)}"

    # Should be the first one alphabetically (_index.md comes before _index.variant-*.md)
    assert index_pages[0]["template_path"] == "specs/templates/docs.aspose.org/cells/en/python/docs/_index.md"


def test_classify_templates_alphabetical_selection():
    """Test that classify_templates selects the first variant alphabetically.

    When multiple index page variants exist, the one that comes first
    alphabetically by template_path should be selected.
    """
    templates = [
        {
            "section": "reference",
            "slug": "index",
            "template_path": "specs/templates/reference.aspose.org/cells/en/python/reference/_index.variant-weight.md",
            "filename": "_index.variant-weight.md",
            "variant": "weight",
            "is_mandatory": False,
            "placeholders": [],
        },
        {
            "section": "reference",
            "slug": "index",
            "template_path": "specs/templates/reference.aspose.org/cells/en/python/reference/_index.variant-sidebar.md",
            "filename": "_index.variant-sidebar.md",
            "variant": "sidebar",
            "is_mandatory": False,
            "placeholders": [],
        },
        {
            "section": "reference",
            "slug": "index",
            "template_path": "specs/templates/reference.aspose.org/cells/en/python/reference/_index.variant-minimal.md",
            "filename": "_index.variant-minimal.md",
            "variant": "minimal",
            "is_mandatory": False,
            "placeholders": [],
        },
    ]

    mandatory, optional = classify_templates(templates, "standard")

    # Should only have one index page
    all_templates = mandatory + optional
    index_pages = [t for t in all_templates if t["slug"] == "index"]
    assert len(index_pages) == 1

    # Should be minimal (alphabetically first: minimal < sidebar < weight)
    assert index_pages[0]["variant"] == "minimal"
    assert "_index.variant-minimal.md" in index_pages[0]["template_path"]


def test_classify_templates_no_url_collision():
    """Test that de-duplication prevents URL collisions.

    After de-duplication, each section should have at most one index page,
    preventing multiple templates from generating the same URL path.
    """
    templates = [
        # docs section - multiple index variants
        {
            "section": "docs",
            "slug": "index",
            "template_path": "specs/templates/docs.aspose.org/cells/en/python/docs/_index.md",
            "filename": "_index.md",
            "variant": "default",
            "is_mandatory": True,
            "placeholders": [],
        },
        {
            "section": "docs",
            "slug": "index",
            "template_path": "specs/templates/docs.aspose.org/cells/en/python/docs/_index.variant-standard.md",
            "filename": "_index.variant-standard.md",
            "variant": "standard",
            "is_mandatory": False,
            "placeholders": [],
        },
        # kb section - multiple index variants
        {
            "section": "kb",
            "slug": "index",
            "template_path": "specs/templates/kb.aspose.org/cells/en/python/kb/_index.md",
            "filename": "_index.md",
            "variant": "default",
            "is_mandatory": True,
            "placeholders": [],
        },
        {
            "section": "kb",
            "slug": "index",
            "template_path": "specs/templates/kb.aspose.org/cells/en/python/kb/_index.variant-minimal.md",
            "filename": "_index.variant-minimal.md",
            "variant": "minimal",
            "is_mandatory": False,
            "placeholders": [],
        },
        # Non-index template (should not be affected)
        {
            "section": "docs",
            "slug": "getting-started",
            "template_path": "specs/templates/docs.aspose.org/cells/en/python/docs/getting-started.md",
            "filename": "getting-started.md",
            "variant": "default",
            "is_mandatory": True,
            "placeholders": [],
        },
    ]

    mandatory, optional = classify_templates(templates, "standard")

    all_templates = mandatory + optional

    # Each section should have at most one index page
    docs_index = [t for t in all_templates if t["section"] == "docs" and t["slug"] == "index"]
    kb_index = [t for t in all_templates if t["section"] == "kb" and t["slug"] == "index"]

    assert len(docs_index) == 1, "docs section should have exactly 1 index page"
    assert len(kb_index) == 1, "kb section should have exactly 1 index page"

    # Non-index templates should not be affected
    getting_started = [t for t in all_templates if t["slug"] == "getting-started"]
    assert len(getting_started) == 1, "Non-index templates should not be deduplicated"


def test_classify_templates_preserves_non_index_templates():
    """Test that de-duplication only affects index pages, not other templates.

    Non-index templates should be processed normally according to launch tier
    filtering, without any de-duplication.
    """
    templates = [
        # Index page (will be deduplicated)
        {
            "section": "docs",
            "slug": "index",
            "template_path": "specs/templates/docs/_index.md",
            "filename": "_index.md",
            "variant": "default",
            "is_mandatory": True,
            "placeholders": [],
        },
        {
            "section": "docs",
            "slug": "index",
            "template_path": "specs/templates/docs/_index.variant-standard.md",
            "filename": "_index.variant-standard.md",
            "variant": "standard",
            "is_mandatory": False,
            "placeholders": [],
        },
        # Non-index templates (should not be deduplicated)
        {
            "section": "docs",
            "slug": "getting-started",
            "template_path": "specs/templates/docs/getting-started.md",
            "filename": "getting-started.md",
            "variant": "default",
            "is_mandatory": True,
            "placeholders": [],
        },
        {
            "section": "docs",
            "slug": "api-reference",
            "template_path": "specs/templates/docs/api-reference.md",
            "filename": "api-reference.md",
            "variant": "default",
            "is_mandatory": False,
            "placeholders": [],
        },
        {
            "section": "docs",
            "slug": "troubleshooting",
            "template_path": "specs/templates/docs/troubleshooting.md",
            "filename": "troubleshooting.md",
            "variant": "standard",
            "is_mandatory": False,
            "placeholders": [],
        },
    ]

    mandatory, optional = classify_templates(templates, "standard")

    all_templates = mandatory + optional

    # Only 1 index page
    index_pages = [t for t in all_templates if t["slug"] == "index"]
    assert len(index_pages) == 1

    # All non-index mandatory templates should be present
    non_index_templates = [t for t in all_templates if t["slug"] != "index"]
    assert len(non_index_templates) == 3, "All non-index templates should be present"

    # Verify specific non-index templates
    assert any(t["slug"] == "getting-started" for t in non_index_templates)
    assert any(t["slug"] == "api-reference" for t in non_index_templates)
    assert any(t["slug"] == "troubleshooting" for t in non_index_templates)


def test_classify_templates_multiple_sections_independent():
    """Test that de-duplication is independent per section.

    Each section can have its own index page. De-duplication should only
    remove duplicates within the same section, not across sections.
    """
    templates = [
        # docs section
        {
            "section": "docs",
            "slug": "index",
            "template_path": "specs/templates/docs/_index.md",
            "filename": "_index.md",
            "variant": "default",
            "is_mandatory": True,
            "placeholders": [],
        },
        {
            "section": "docs",
            "slug": "index",
            "template_path": "specs/templates/docs/_index.variant-minimal.md",
            "filename": "_index.variant-minimal.md",
            "variant": "minimal",
            "is_mandatory": False,
            "placeholders": [],
        },
        # reference section
        {
            "section": "reference",
            "slug": "index",
            "template_path": "specs/templates/reference/_index.md",
            "filename": "_index.md",
            "variant": "default",
            "is_mandatory": True,
            "placeholders": [],
        },
        {
            "section": "reference",
            "slug": "index",
            "template_path": "specs/templates/reference/_index.variant-minimal.md",
            "filename": "_index.variant-minimal.md",
            "variant": "minimal",
            "is_mandatory": False,
            "placeholders": [],
        },
        # kb section
        {
            "section": "kb",
            "slug": "index",
            "template_path": "specs/templates/kb/_index.md",
            "filename": "_index.md",
            "variant": "default",
            "is_mandatory": True,
            "placeholders": [],
        },
    ]

    mandatory, optional = classify_templates(templates, "standard")

    all_templates = mandatory + optional

    # Should have exactly 3 index pages (one per section)
    index_pages = [t for t in all_templates if t["slug"] == "index"]
    assert len(index_pages) == 3, "Should have 1 index page per section"

    # Verify each section has exactly one index page
    docs_index = [t for t in index_pages if t["section"] == "docs"]
    reference_index = [t for t in index_pages if t["section"] == "reference"]
    kb_index = [t for t in index_pages if t["section"] == "kb"]

    assert len(docs_index) == 1
    assert len(reference_index) == 1
    assert len(kb_index) == 1


def test_classify_templates_empty_list():
    """Test that classify_templates handles empty template list."""
    templates = []

    mandatory, optional = classify_templates(templates, "standard")

    assert len(mandatory) == 0
    assert len(optional) == 0


def test_classify_templates_no_duplicates():
    """Test that classify_templates works correctly when no duplicates exist.

    When there are no duplicate index pages, all templates should be
    classified normally without any being skipped.
    """
    templates = [
        {
            "section": "docs",
            "slug": "index",
            "template_path": "specs/templates/docs/_index.md",
            "filename": "_index.md",
            "variant": "default",
            "is_mandatory": True,
            "placeholders": [],
        },
        {
            "section": "reference",
            "slug": "index",
            "template_path": "specs/templates/reference/_index.md",
            "filename": "_index.md",
            "variant": "default",
            "is_mandatory": True,
            "placeholders": [],
        },
        {
            "section": "docs",
            "slug": "getting-started",
            "template_path": "specs/templates/docs/getting-started.md",
            "filename": "getting-started.md",
            "variant": "default",
            "is_mandatory": True,
            "placeholders": [],
        },
    ]

    mandatory, optional = classify_templates(templates, "standard")

    all_templates = mandatory + optional

    # All 3 templates should be present (no duplicates to remove)
    assert len(all_templates) == 3

    # Both index pages should be present (different sections)
    index_pages = [t for t in all_templates if t["slug"] == "index"]
    assert len(index_pages) == 2


def test_classify_templates_launch_tier_filtering_with_deduplication():
    """Test that launch tier filtering works correctly with de-duplication.

    De-duplication should happen before launch tier filtering, ensuring that
    the selected index page is then subject to normal tier-based filtering.
    """
    templates = [
        # Multiple index variants (will be deduplicated)
        {
            "section": "docs",
            "slug": "index",
            "template_path": "specs/templates/docs/_index.variant-minimal.md",
            "filename": "_index.variant-minimal.md",
            "variant": "minimal",
            "is_mandatory": False,
            "placeholders": [],
        },
        {
            "section": "docs",
            "slug": "index",
            "template_path": "specs/templates/docs/_index.variant-rich.md",
            "filename": "_index.variant-rich.md",
            "variant": "rich",
            "is_mandatory": False,
            "placeholders": [],
        },
        {
            "section": "docs",
            "slug": "index",
            "template_path": "specs/templates/docs/_index.variant-standard.md",
            "filename": "_index.variant-standard.md",
            "variant": "standard",
            "is_mandatory": False,
            "placeholders": [],
        },
    ]

    # Test with minimal tier - should select minimal variant (alphabetically first)
    mandatory, optional = classify_templates(templates, "minimal")
    all_templates = mandatory + optional
    index_pages = [t for t in all_templates if t["slug"] == "index"]
    assert len(index_pages) == 1
    assert index_pages[0]["variant"] == "minimal"

    # Test with standard tier - should still select minimal variant (alphabetically first)
    mandatory, optional = classify_templates(templates, "standard")
    all_templates = mandatory + optional
    index_pages = [t for t in all_templates if t["slug"] == "index"]
    assert len(index_pages) == 1
    assert index_pages[0]["variant"] == "minimal"

    # Test with rich tier - should still select minimal variant (alphabetically first)
    mandatory, optional = classify_templates(templates, "rich")
    all_templates = mandatory + optional
    index_pages = [t for t in all_templates if t["slug"] == "index"]
    assert len(index_pages) == 1
    assert index_pages[0]["variant"] == "minimal"
