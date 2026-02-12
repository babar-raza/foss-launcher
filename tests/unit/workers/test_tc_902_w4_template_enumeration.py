"""TC-902: Unit tests for W4 template enumeration with quotas.

Tests the W4 IAPlanner template enumeration implementation that discovers
templates from the specs/templates/ hierarchy and applies quota logic.

Spec references:
- specs/06_page_planning.md (Page planning algorithm)
- specs/20_rulesets_and_templates_registry.md (Template resolution)
- specs/32_platform_aware_content_layout.md (V2 layout)
- TC-902 taskcard (Template enumeration with quotas)
"""

import json
import pytest
from pathlib import Path
from typing import Dict, Any, List

from launch.workers.w4_ia_planner.worker import (
    enumerate_templates,
    classify_templates,
    select_templates_with_quota,
    fill_template_placeholders,
    compute_output_path,
    compute_url_path,
)


@pytest.fixture
def mock_template_dir(tmp_path: Path) -> Path:
    """Create a mock template directory with V2 layout."""
    template_root = tmp_path / "specs" / "templates"

    # Create docs.aspose.org/cells/en/python/ templates
    docs_dir = template_root / "docs.aspose.org" / "cells" / "en" / "python"
    docs_dir.mkdir(parents=True, exist_ok=True)

    # Create mandatory templates (_index.md files)
    (docs_dir / "_index.md").write_text("---\ntitle: Docs Index\n---\n")

    # Create section directory with _index
    section_dir = docs_dir / "guides"
    section_dir.mkdir(parents=True, exist_ok=True)
    (section_dir / "_index.md").write_text("---\ntitle: Guides Index\n---\n")

    # Create optional templates with variants
    (docs_dir / "quickstart.variant-minimal.md").write_text("---\ntitle: Quickstart\n---\n")
    (docs_dir / "quickstart.variant-standard.md").write_text("---\ntitle: Quickstart Standard\n---\n")
    (docs_dir / "installation.md").write_text("---\ntitle: Installation\n---\n")
    (docs_dir / "advanced-guide.variant-rich.md").write_text("---\ntitle: Advanced Guide\n---\n")

    # Create more optional templates to test quota
    for i in range(1, 16):
        (docs_dir / f"guide-{i:02d}.md").write_text(f"---\ntitle: Guide {i}\n---\n")

    return template_root


@pytest.fixture
def mock_blog_template_dir(tmp_path: Path) -> Path:
    """Create a mock template directory for blog (non-locale structure)."""
    template_root = tmp_path / "specs" / "templates"

    # Blog uses: blog.aspose.org/<family>/<platform>/
    blog_dir = template_root / "blog.aspose.org" / "cells" / "python"
    blog_dir.mkdir(parents=True, exist_ok=True)

    # Create mandatory template
    (blog_dir / "_index.md").write_text("---\ntitle: Blog Index\n---\n")

    # Create optional templates
    (blog_dir / "announcement.variant-minimal.md").write_text("---\ntitle: Announcement\n---\n")
    (blog_dir / "showcase.variant-standard.md").write_text("---\ntitle: Showcase\n---\n")

    return template_root


# Test 1: Enumerate templates - V2 layout
def test_enumerate_templates_v2_layout(mock_template_dir: Path):
    """Test template enumeration with V2 platform-aware layout."""
    templates = enumerate_templates(
        template_dir=mock_template_dir,
        subdomain="docs.aspose.org",
        family="cells",
        locale="en",
        platform="python",
    )

    # Should find all templates
    assert len(templates) > 0

    # Check mandatory templates
    mandatory_count = sum(1 for t in templates if t["is_mandatory"])
    assert mandatory_count == 2  # _index.md and guides/_index.md

    # Check variant detection
    variant_templates = [t for t in templates if "variant" in t["filename"]]
    assert len(variant_templates) > 0

    # Check deterministic ordering
    paths = [t["template_path"] for t in templates]
    assert paths == sorted(paths)


# Test 2: Enumerate templates - blog layout
def test_enumerate_templates_blog_layout(mock_blog_template_dir: Path):
    """Test template enumeration for blog (non-locale structure)."""
    templates = enumerate_templates(
        template_dir=mock_blog_template_dir,
        subdomain="blog.aspose.org",
        family="cells",
        locale="en",  # Locale is ignored for blog
        platform="python",
    )

    assert len(templates) == 3  # _index + 2 optional
    assert sum(1 for t in templates if t["is_mandatory"]) == 1


# Test 3: Enumerate templates - empty directory
def test_enumerate_templates_empty_directory(tmp_path: Path):
    """Test template enumeration with no templates."""
    template_root = tmp_path / "specs" / "templates"
    template_root.mkdir(parents=True, exist_ok=True)

    templates = enumerate_templates(
        template_dir=template_root,
        subdomain="docs.aspose.org",
        family="nonexistent",
        locale="en",
        platform="python",
    )

    assert len(templates) == 0


# Test 4: Classify templates - minimal tier
def test_classify_templates_minimal_tier(mock_template_dir: Path):
    """Test template classification for minimal launch tier."""
    templates = enumerate_templates(
        template_dir=mock_template_dir,
        subdomain="docs.aspose.org",
        family="cells",
        locale="en",
        platform="python",
    )

    mandatory, optional = classify_templates(templates, launch_tier="minimal")

    # All _index.md should be mandatory
    assert all(t["is_mandatory"] for t in mandatory)

    # Optional should include minimal variants
    minimal_variants = [t for t in optional if t["variant"] == "minimal"]
    assert len(minimal_variants) > 0


# Test 5: Classify templates - standard tier
def test_classify_templates_standard_tier(mock_template_dir: Path):
    """Test template classification for standard launch tier."""
    templates = enumerate_templates(
        template_dir=mock_template_dir,
        subdomain="docs.aspose.org",
        family="cells",
        locale="en",
        platform="python",
    )

    mandatory, optional = classify_templates(templates, launch_tier="standard")

    # Should include standard variants
    standard_variants = [t for t in optional if t["variant"] == "standard"]
    assert len(standard_variants) > 0


# Test 6: Classify templates - rich tier
def test_classify_templates_rich_tier(mock_template_dir: Path):
    """Test template classification for rich launch tier."""
    templates = enumerate_templates(
        template_dir=mock_template_dir,
        subdomain="docs.aspose.org",
        family="cells",
        locale="en",
        platform="python",
    )

    mandatory, optional = classify_templates(templates, launch_tier="rich")

    # Should include rich variants
    rich_variants = [t for t in optional if t["variant"] == "rich"]
    assert len(rich_variants) > 0


# Test 7: Select templates with quota - normal case
def test_select_templates_with_quota_normal(mock_template_dir: Path):
    """Test template selection with quota (normal case)."""
    templates = enumerate_templates(
        template_dir=mock_template_dir,
        subdomain="docs.aspose.org",
        family="cells",
        locale="en",
        platform="python",
    )

    mandatory, optional = classify_templates(templates, launch_tier="standard")

    # Select with quota of 10
    selected = select_templates_with_quota(
        mandatory=mandatory,
        optional=optional,
        max_pages=10,
    )

    # Should have exactly 10 templates (or all if fewer available)
    assert len(selected) <= 10

    # All mandatory templates must be included
    mandatory_in_selected = [t for t in selected if t["is_mandatory"]]
    assert len(mandatory_in_selected) == len(mandatory)


# Test 8: Select templates with quota - quota exceeded by mandatory
def test_select_templates_with_quota_exceeded(mock_template_dir: Path):
    """Test template selection when mandatory templates exceed quota."""
    templates = enumerate_templates(
        template_dir=mock_template_dir,
        subdomain="docs.aspose.org",
        family="cells",
        locale="en",
        platform="python",
    )

    mandatory, optional = classify_templates(templates, launch_tier="standard")

    # Set quota lower than mandatory count
    selected = select_templates_with_quota(
        mandatory=mandatory,
        optional=optional,
        max_pages=1,  # Less than mandatory count
    )

    # All mandatory templates should still be included
    assert len(selected) >= len(mandatory)
    mandatory_in_selected = [t for t in selected if t["is_mandatory"]]
    assert len(mandatory_in_selected) == len(mandatory)


# Test 9: Select templates with quota - zero optional
def test_select_templates_with_quota_zero_optional(mock_template_dir: Path):
    """Test template selection when quota allows no optional templates."""
    templates = enumerate_templates(
        template_dir=mock_template_dir,
        subdomain="docs.aspose.org",
        family="cells",
        locale="en",
        platform="python",
    )

    mandatory, optional = classify_templates(templates, launch_tier="standard")

    # Set quota equal to mandatory count
    selected = select_templates_with_quota(
        mandatory=mandatory,
        optional=optional,
        max_pages=len(mandatory),
    )

    # Should have exactly mandatory templates
    assert len(selected) == len(mandatory)


# Test 10: Select templates with quota - deterministic ordering
def test_select_templates_with_quota_deterministic(mock_template_dir: Path):
    """Test that template selection is deterministic."""
    templates = enumerate_templates(
        template_dir=mock_template_dir,
        subdomain="docs.aspose.org",
        family="cells",
        locale="en",
        platform="python",
    )

    mandatory, optional = classify_templates(templates, launch_tier="standard")

    # Select multiple times
    selected1 = select_templates_with_quota(mandatory, optional, max_pages=10)
    selected2 = select_templates_with_quota(mandatory, optional, max_pages=10)

    # Results should be identical
    paths1 = [t["template_path"] for t in selected1]
    paths2 = [t["template_path"] for t in selected2]
    assert paths1 == paths2


# Test 11: Fill template placeholders - docs section
def test_fill_template_placeholders_docs(monkeypatch):
    """Test placeholder filling for docs section."""
    monkeypatch.setattr(
        "launch.workers.w4_ia_planner.worker.extract_title_from_template",
        lambda path: "__TITLE__",
    )
    template = {
        "template_path": "/path/to/template.md",
        "slug": "getting-started",
        "variant": "standard",
        "is_mandatory": False,
    }

    page_spec = fill_template_placeholders(
        template=template,
        section="docs",
        product_slug="cells",
        locale="en",
        platform="python",
        subdomain="docs.aspose.org",
    )

    # Verify page spec structure
    assert page_spec["section"] == "docs"
    assert page_spec["slug"] == "getting-started"
    assert page_spec["template_variant"] == "standard"
    assert page_spec["template_path"] == "/path/to/template.md"

    # Verify paths
    assert "cells" in page_spec["output_path"]
    # Section is implicit in subdomain, NOT in URL path (specs/33_public_url_mapping.md)
    assert "/cells/python/getting-started/" in page_spec["url_path"]


# Test 12: Fill template placeholders - products section
def test_fill_template_placeholders_products(monkeypatch):
    """Test placeholder filling for products section."""
    monkeypatch.setattr(
        "launch.workers.w4_ia_planner.worker.extract_title_from_template",
        lambda path: "__TITLE__",
    )
    template = {
        "template_path": "/path/to/overview.md",
        "slug": "overview",
        "variant": "minimal",
        "is_mandatory": True,
    }

    page_spec = fill_template_placeholders(
        template=template,
        section="products",
        product_slug="cells",
        locale="en",
        platform="python",
        subdomain="products.aspose.org",
    )

    assert page_spec["section"] == "products"
    assert page_spec["slug"] == "overview"
    assert "/cells/python/overview/" in page_spec["url_path"]


# Test 13: Fill template placeholders - blog section
def test_fill_template_placeholders_blog(monkeypatch):
    """Test placeholder filling for blog section."""
    monkeypatch.setattr(
        "launch.workers.w4_ia_planner.worker.extract_title_from_template",
        lambda path: "__TITLE__",
    )
    template = {
        "template_path": "/path/to/announcement.md",
        "slug": "announcement",
        "variant": "standard",
        "is_mandatory": False,
    }

    page_spec = fill_template_placeholders(
        template=template,
        section="blog",
        product_slug="cells",
        locale="en",
        platform="python",
        subdomain="blog.aspose.org",
    )

    assert page_spec["section"] == "blog"
    assert page_spec["slug"] == "announcement"


# Test 14: Compute output path - V2 docs
def test_compute_output_path_v2_docs():
    """Test output path computation for V2 docs section."""
    path = compute_output_path(
        section="docs",
        slug="getting-started",
        product_slug="cells",
        subdomain="docs.aspose.org",
        platform="python",
        locale="en",
    )

    assert path == "content/docs.aspose.org/cells/en/python/docs/getting-started.md"


# Test 15: Compute output path - V2 products
def test_compute_output_path_v2_products():
    """Test output path computation for V2 products section."""
    path = compute_output_path(
        section="products",
        slug="overview",
        product_slug="cells",
        subdomain="products.aspose.org",
        platform="python",
        locale="en",
    )

    assert path == "content/products.aspose.org/cells/en/python/overview.md"


# Test 16: Compute URL path - products section
def test_compute_url_path_products():
    """Test URL path computation for products section."""
    url = compute_url_path(
        section="products",
        slug="overview",
        product_slug="cells",
        platform="python",
        locale="en",
    )

    assert url == "/cells/python/overview/"


# Test 17: Compute URL path - docs section
def test_compute_url_path_docs():
    """Test URL path computation for docs section."""
    url = compute_url_path(
        section="docs",
        slug="getting-started",
        product_slug="cells",
        platform="python",
        locale="en",
    )

    # Section is implicit in subdomain, NOT in URL path (specs/33_public_url_mapping.md)
    # V2: Platform comes after family
    assert url == "/cells/python/getting-started/"


# Test 18: Compute URL path - reference section
def test_compute_url_path_reference():
    """Test URL path computation for reference section."""
    url = compute_url_path(
        section="reference",
        slug="api-overview",
        product_slug="cells",
        platform="python",
        locale="en",
    )

    # Section is implicit in subdomain, NOT in URL path (specs/33_public_url_mapping.md)
    # V2: Platform comes after family
    assert url == "/cells/python/api-overview/"


# Test 19: Integration test - quota enforcement with 20 optional + 3 mandatory
def test_integration_quota_enforcement(mock_template_dir: Path):
    """Integration test: 20 optional + 3 mandatory, max_pages=10."""
    templates = enumerate_templates(
        template_dir=mock_template_dir,
        subdomain="docs.aspose.org",
        family="cells",
        locale="en",
        platform="python",
    )

    mandatory, optional = classify_templates(templates, launch_tier="standard")

    # Ensure we have at least the expected counts
    # HEAL-BUG2 dedup: guides/_index.md and root _index.md both normalize to
    # slug="index", so classify_templates keeps only the first per section
    assert len(mandatory) >= 1  # At least root _index.md
    assert len(optional) >= 15  # guide-01 through guide-15 + others

    # Apply quota of 10
    selected = select_templates_with_quota(
        mandatory=mandatory,
        optional=optional,
        max_pages=10,
    )

    # Verify quota enforcement
    assert len(mandatory) <= len(selected) <= 10 or len(selected) == len(mandatory)

    # All mandatory must be included
    mandatory_slugs = {t["slug"] for t in mandatory}
    selected_slugs = {t["slug"] for t in selected}
    assert mandatory_slugs.issubset(selected_slugs)


# Test 20: Integration test - deterministic page planning
def test_integration_deterministic_planning(mock_template_dir: Path):
    """Integration test: Verify deterministic page planning."""
    # Run enumeration twice
    templates1 = enumerate_templates(
        template_dir=mock_template_dir,
        subdomain="docs.aspose.org",
        family="cells",
        locale="en",
        platform="python",
    )

    templates2 = enumerate_templates(
        template_dir=mock_template_dir,
        subdomain="docs.aspose.org",
        family="cells",
        locale="en",
        platform="python",
    )

    # Results should be identical
    assert len(templates1) == len(templates2)

    paths1 = [t["template_path"] for t in templates1]
    paths2 = [t["template_path"] for t in templates2]
    assert paths1 == paths2


# Test 21: Integration test - V2 path generation for all sections
def test_integration_v2_paths_all_sections(monkeypatch):
    """Integration test: Verify V2 path generation for all sections."""
    monkeypatch.setattr(
        "launch.workers.w4_ia_planner.worker.extract_title_from_template",
        lambda path: "__TITLE__",
    )
    sections = ["products", "docs", "reference", "kb", "blog"]

    for section in sections:
        template = {
            "template_path": f"/path/{section}.md",
            "slug": f"{section}-page",
            "variant": "standard",
            "is_mandatory": False,
        }

        page_spec = fill_template_placeholders(
            template=template,
            section=section,
            product_slug="cells",
            locale="en",
            platform="python",
            subdomain=f"{section}.aspose.org" if section != "products" else "products.aspose.org",
        )

        # Verify paths are correctly formatted
        assert "cells" in page_spec["output_path"]
        assert page_spec["url_path"].startswith("/")
        assert page_spec["url_path"].endswith("/")


# Test 22: TC-902 Blog paths must include family segment
def test_compute_output_path_blog_includes_family():
    """Test that blog paths include /<family>/ segment (TC-902 fix)."""
    # Test with family="3d"
    path_3d = compute_output_path(
        section="blog",
        slug="announcement",
        product_slug="3d",
        subdomain="blog.aspose.org",
        platform="python",
        locale="en",
    )

    # Must include family and platform segments: content/blog.aspose.org/3d/python/announcement/index.md
    assert path_3d == "content/blog.aspose.org/3d/python/announcement/index.md"
    assert "/3d/" in path_3d
    assert "/python/" in path_3d
    assert path_3d.startswith("content/blog.aspose.org/3d/")

    # Test with family="note"
    path_note = compute_output_path(
        section="blog",
        slug="announcement",
        product_slug="note",
        subdomain="blog.aspose.org",
        platform="python",
        locale="en",
    )

    assert path_note == "content/blog.aspose.org/note/python/announcement/index.md"
    assert "/note/" in path_note
    assert "/python/" in path_note
    assert path_note.startswith("content/blog.aspose.org/note/")

    # Verify no double slashes
    assert "//" not in path_3d
    assert "//" not in path_note
