"""Unit tests for W4 IAPlanner template discovery.

This module tests the enumerate_templates() function to ensure:
1. Blog templates with __LOCALE__ are filtered out (HEAL-BUG4)
2. Blog templates with correct __POST_SLUG__ structure are discovered
3. Non-blog sections (docs) correctly allow __LOCALE__ in templates

Spec references:
- specs/33_public_url_mapping.md:100 (blog uses filename-based i18n, no locale folder)
- specs/33_public_url_mapping.md:88-96 (blog structure)
- specs/07_section_templates.md (template requirements)
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from src.launch.workers.w4_ia_planner.worker import enumerate_templates


@pytest.fixture
def temp_template_dir():
    """Create temporary template directory with test templates."""
    with tempfile.TemporaryDirectory() as tmpdir:
        template_dir = Path(tmpdir)

        # Create blog templates with obsolete __LOCALE__ structure (should be filtered)
        # enumerate_templates searches blog at: blog.aspose.org/{family}/{platform}/
        # So we create templates under python/ that contain __LOCALE__ in their path
        obsolete_blog_path = (
            template_dir / "blog.aspose.org" / "cells" / "python" /
            "__LOCALE__" / "__POST_SLUG__" / "index.md"
        )
        obsolete_blog_path.parent.mkdir(parents=True, exist_ok=True)
        obsolete_blog_path.write_text(
            "---\ntitle: Obsolete Blog Template\n---\n\n# __TITLE__\n\n__CONTENT__"
        )

        # Create blog templates with correct __PLATFORM__ structure (should be discovered)
        # Blog templates at family/platform level with __POST_SLUG__
        correct_blog_path = (
            template_dir / "blog.aspose.org" / "cells" / "python" /
            "__POST_SLUG__" / "index.variant-standard.md"
        )
        correct_blog_path.parent.mkdir(parents=True, exist_ok=True)
        correct_blog_path.write_text(
            "---\ntitle: Correct Blog Template\n---\n\n# __TITLE__\n\n__CONTENT__"
        )

        # Create blog templates without platform (direct __POST_SLUG__) (should be discovered)
        # When platform doesn't exist, enumerate_templates falls back to family/ level
        direct_blog_path = (
            template_dir / "blog.aspose.org" / "cells" /
            "__POST_SLUG__" / "index.variant-minimal.md"
        )
        direct_blog_path.parent.mkdir(parents=True, exist_ok=True)
        direct_blog_path.write_text(
            "---\ntitle: Direct Blog Template\n---\n\n# __TITLE__\n\n__CONTENT__"
        )

        # Create docs templates with __LOCALE__ in a directory path (correct for docs)
        # TC-993: __LOCALE__ in a *directory component* is allowed for non-blog sections;
        # only __LOCALE__ in *filenames* is filtered by TC-967 placeholder filter.
        docs_locale_path = (
            template_dir / "docs.aspose.org" / "cells" / "__LOCALE__" /
            "python" / "locale-specific-guide.md"
        )
        docs_locale_path.parent.mkdir(parents=True, exist_ok=True)
        docs_locale_path.write_text(
            "---\ntitle: Docs Getting Started\n---\n\n# Getting Started\n\n__CONTENT__"
        )

        # Also create a normal docs template for baseline
        docs_normal_path = (
            template_dir / "docs.aspose.org" / "cells" / "en" /
            "python" / "getting-started.md"
        )
        docs_normal_path.parent.mkdir(parents=True, exist_ok=True)
        docs_normal_path.write_text(
            "---\ntitle: Docs Getting Started\n---\n\n# Getting Started\n\n__CONTENT__"
        )

        # Create README files (should be filtered for all sections)
        readme_blog = template_dir / "blog.aspose.org" / "cells" / "README.md"
        readme_blog.parent.mkdir(parents=True, exist_ok=True)
        readme_blog.write_text("# Blog Templates README")

        readme_docs = template_dir / "docs.aspose.org" / "cells" / "README.md"
        readme_docs.parent.mkdir(parents=True, exist_ok=True)
        readme_docs.write_text("# Docs Templates README")

        yield template_dir


def test_blog_templates_exclude_locale_folder(temp_template_dir):
    """Test that blog templates with __LOCALE__ folder are filtered out.

    Per specs/33_public_url_mapping.md:100, blog uses filename-based i18n
    (no locale folder). Templates with __LOCALE__ in path should be skipped.

    HEAL-BUG4: This test verifies the fix prevents obsolete template discovery.
    """
    templates = enumerate_templates(
        template_dir=temp_template_dir,
        subdomain="blog.aspose.org",
        family="cells",
        locale="en",
    )

    # Assert: No templates should contain __LOCALE__ in their path
    for template in templates:
        template_path = template["template_path"]
        assert "__LOCALE__" not in template_path, (
            f"Blog template should not contain __LOCALE__: {template_path}"
        )

    # Assert: At least some templates were discovered (not empty result)
    assert len(templates) > 0, "Should discover at least some blog templates"


def test_blog_templates_use_platform_structure(temp_template_dir):
    """Test that blog templates with correct __PLATFORM__/__POST_SLUG__ structure are discovered.

    Per specs/33_public_url_mapping.md:88-96, blog uses:
    - content/blog.aspose.org/<family>/<platform>/<slug>/index.md
    - Templates should mirror this with __PLATFORM__/__POST_SLUG__ placeholders
    """
    templates = enumerate_templates(
        template_dir=temp_template_dir,
        subdomain="blog.aspose.org",
        family="cells",
        locale="en",
    )

    # Assert: Should discover templates with __PLATFORM__ or __POST_SLUG__
    has_platform_template = any(
        "__PLATFORM__" in template["template_path"] for template in templates
    )
    has_post_slug_template = any(
        "__POST_SLUG__" in template["template_path"] for template in templates
    )

    assert has_platform_template or has_post_slug_template, (
        "Blog templates should contain __PLATFORM__ or __POST_SLUG__ placeholders"
    )

    # Assert: Verify we have the expected templates
    template_paths = [t["template_path"] for t in templates]

    # Should find the correct blog template (with __POST_SLUG__)
    # Note: The search path already includes concrete platform (python), so we won't see __PLATFORM__ placeholder
    correct_found = any(
        "blog.aspose.org" in p and "__POST_SLUG__" in p and "__LOCALE__" not in p
        for p in template_paths
    )
    assert correct_found, f"Should find blog template with correct __POST_SLUG__ structure. Found: {template_paths}"

    # Should NOT find the obsolete template
    obsolete_found = any(
        "__LOCALE__" in p for p in template_paths
    )
    assert not obsolete_found, "Should NOT find obsolete blog template with __LOCALE__"


def test_docs_templates_allow_locale_folder(temp_template_dir):
    """Test that the blog __LOCALE__ filter does NOT affect docs template discovery.

    Per specs/33_public_url_mapping.md:47-56, non-blog sections use concrete
    locale directories (e.g., en/). The blog __LOCALE__ filter only applies
    to blog.aspose.org subdomain and must not affect docs.

    This test ensures our blog filter doesn't over-filter other sections.
    """
    templates = enumerate_templates(
        template_dir=temp_template_dir,
        subdomain="docs.aspose.org",
        family="cells",
        locale="en",
    )

    # Assert: At least one template was discovered (blog filter didn't block docs)
    assert len(templates) > 0, "Should discover at least one docs template"

    # Verify the normal docs template was found
    template_paths = [t["template_path"] for t in templates]
    docs_found = any(
        "docs.aspose.org" in p and "getting-started" in p
        for p in template_paths
    )
    assert docs_found, "Should find normal docs template (blog filter must not affect docs)"


def test_readme_files_always_excluded(temp_template_dir):
    """Test that README.md files are excluded from template discovery for all sections.

    README files are documentation, not templates, and should never be enumerated.
    """
    # Test blog section
    blog_templates = enumerate_templates(
        template_dir=temp_template_dir,
        subdomain="blog.aspose.org",
        family="cells",
        locale="en",
    )

    for template in blog_templates:
        assert "README.md" not in template["template_path"], (
            f"README.md should be excluded: {template['template_path']}"
        )

    # Test docs section
    docs_templates = enumerate_templates(
        template_dir=temp_template_dir,
        subdomain="docs.aspose.org",
        family="cells",
        locale="en",
    )

    for template in docs_templates:
        assert "README.md" not in template["template_path"], (
            f"README.md should be excluded: {template['template_path']}"
        )


def test_empty_directory_returns_empty_list(temp_template_dir):
    """Test that enumerate_templates returns empty list for non-existent paths."""
    templates = enumerate_templates(
        template_dir=temp_template_dir,
        subdomain="nonexistent.aspose.org",
        family="nonexistent",
        locale="en",
    )

    assert templates == [], "Should return empty list for non-existent template paths"


def test_template_deterministic_ordering(temp_template_dir):
    """Test that enumerate_templates returns deterministically ordered results.

    Per specs/10_determinism_and_caching.md, template enumeration must be stable.
    Templates should be sorted by template_path.
    """
    templates_1 = enumerate_templates(
        template_dir=temp_template_dir,
        subdomain="blog.aspose.org",
        family="cells",
        locale="en",
    )

    templates_2 = enumerate_templates(
        template_dir=temp_template_dir,
        subdomain="blog.aspose.org",
        family="cells",
        locale="en",
    )

    # Assert: Same inputs produce identical results
    assert templates_1 == templates_2, "enumerate_templates should be deterministic"

    # Assert: Templates are sorted by template_path
    if len(templates_1) > 1:
        template_paths = [t["template_path"] for t in templates_1]
        sorted_paths = sorted(template_paths)
        assert template_paths == sorted_paths, "Templates should be sorted by template_path"
