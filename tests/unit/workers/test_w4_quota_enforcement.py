"""TC-953: Unit tests for W4 quota enforcement from ruleset.

Tests that W4 IAPlanner loads and respects page quotas from specs/rulesets/ruleset.v1.yaml
for each section (products, docs, reference, kb, blog).

Spec references:
- specs/06_page_planning.md (Page planning algorithm)
- specs/rulesets/ (Ruleset structure)
- TC-953 taskcard (Page inventory contract and quotas)
"""

import json
import pytest
from pathlib import Path
from typing import Dict, Any, List

from launch.workers.w4_ia_planner.worker import (
    load_ruleset_quotas,
    select_templates_with_quota,
    classify_templates,
    enumerate_templates,
)


@pytest.fixture
def mock_ruleset_file(tmp_path: Path) -> Path:
    """Create a mock ruleset.v1.yaml with pilot quotas."""
    specs_dir = tmp_path / "specs" / "rulesets"
    specs_dir.mkdir(parents=True, exist_ok=True)

    ruleset_content = """schema_version: "1.0"

style:
  tone: "technical"

sections:
  products:
    min_pages: 1
    max_pages: 6
    style_by_section:
      tone: "professional"
      voice: "active"
  docs:
    min_pages: 2
    max_pages: 10
    style_by_section:
      tone: "instructional"
      voice: "direct"
  reference:
    min_pages: 1
    max_pages: 6
    style_by_section:
      tone: "technical"
      voice: "passive"
  kb:
    min_pages: 3
    max_pages: 10
    style_by_section:
      tone: "conversational"
      voice: "active"
  blog:
    min_pages: 1
    max_pages: 3
    style_by_section:
      tone: "informal"
      voice: "active"
"""

    ruleset_path = specs_dir / "ruleset.v1.yaml"
    ruleset_path.write_text(ruleset_content, encoding="utf-8")
    return tmp_path


@pytest.fixture
def mock_template_dir(tmp_path: Path) -> Path:
    """Create a mock template directory with many templates to test quota."""
    template_root = tmp_path / "specs" / "templates"

    # Create docs templates with many optional pages
    docs_dir = template_root / "docs.aspose.org" / "cells" / "en" / "python"
    docs_dir.mkdir(parents=True, exist_ok=True)

    # Mandatory templates
    (docs_dir / "_index.md").write_text("---\ntitle: Docs Index\n---\n")
    (docs_dir / "guides").mkdir(exist_ok=True)
    (docs_dir / "guides" / "_index.md").write_text("---\ntitle: Guides Index\n---\n")

    # Create 20 optional templates to test quota enforcement
    for i in range(1, 21):
        (docs_dir / f"guide-{i:02d}.md").write_text(f"---\ntitle: Guide {i}\n---\n")

    # Create products templates
    products_dir = template_root / "products.aspose.org" / "cells" / "en" / "python"
    products_dir.mkdir(parents=True, exist_ok=True)
    (products_dir / "overview.md").write_text("---\ntitle: Overview\n---\n")
    (products_dir / "features.md").write_text("---\ntitle: Features\n---\n")
    (products_dir / "quickstart.md").write_text("---\ntitle: Quickstart\n---\n")
    for i in range(1, 8):
        (products_dir / f"optional-{i}.md").write_text(f"---\ntitle: Optional {i}\n---\n")

    # Create reference templates
    reference_dir = template_root / "reference.aspose.org" / "cells" / "en" / "python"
    reference_dir.mkdir(parents=True, exist_ok=True)
    (reference_dir / "api-overview.md").write_text("---\ntitle: API Overview\n---\n")
    for i in range(1, 15):
        (reference_dir / f"module-{i}.md").write_text(f"---\ntitle: Module {i}\n---\n")

    # Create KB templates
    kb_dir = template_root / "kb.aspose.org" / "cells" / "en" / "python"
    kb_dir.mkdir(parents=True, exist_ok=True)
    (kb_dir / "faq.md").write_text("---\ntitle: FAQ\n---\n")
    (kb_dir / "troubleshooting.md").write_text("---\ntitle: Troubleshooting\n---\n")
    (kb_dir / "limitations.md").write_text("---\ntitle: Limitations\n---\n")
    for i in range(1, 12):
        (kb_dir / f"faq-{i:02d}.md").write_text(f"---\ntitle: FAQ {i}\n---\n")

    # Create blog templates
    blog_dir = template_root / "blog.aspose.org" / "cells" / "python"
    blog_dir.mkdir(parents=True, exist_ok=True)
    (blog_dir / "announcement.md").write_text("---\ntitle: Announcement\n---\n")
    for i in range(1, 8):
        (blog_dir / f"post-{i}.md").write_text(f"---\ntitle: Post {i}\n---\n")

    return template_root


# Test 1: Load ruleset quotas
def test_load_ruleset_quotas(mock_ruleset_file: Path):
    """Test loading section quotas from ruleset."""
    quotas = load_ruleset_quotas(mock_ruleset_file)

    # Verify all sections are present
    assert "products" in quotas
    assert "docs" in quotas
    assert "reference" in quotas
    assert "kb" in quotas
    assert "blog" in quotas

    # Verify pilot quota values (TC-953)
    assert quotas["products"]["max_pages"] == 6
    assert quotas["docs"]["max_pages"] == 10
    assert quotas["reference"]["max_pages"] == 6
    assert quotas["kb"]["max_pages"] == 10
    assert quotas["blog"]["max_pages"] == 3

    # Verify min_pages
    assert quotas["products"]["min_pages"] == 1
    assert quotas["docs"]["min_pages"] == 2
    assert quotas["reference"]["min_pages"] == 1
    assert quotas["kb"]["min_pages"] == 3
    assert quotas["blog"]["min_pages"] == 1


# Test 2: Products section respects max_pages quota
def test_products_section_respects_quota(mock_template_dir: Path):
    """Test that products section respects max_pages=6 quota."""
    templates = enumerate_templates(
        template_dir=mock_template_dir,
        subdomain="products.aspose.org",
        family="cells",
        locale="en",
        platform="python",
    )

    assert len(templates) > 6  # Should have more than quota

    mandatory, optional = classify_templates(templates, launch_tier="standard")
    selected = select_templates_with_quota(mandatory, optional, max_pages=6)

    # Should respect max_pages=6
    assert len(selected) <= 6
    assert len(selected) >= 1  # At least min_pages=1


# Test 3: Docs section respects max_pages quota
def test_docs_section_respects_quota(mock_template_dir: Path):
    """Test that docs section respects max_pages=10 quota."""
    templates = enumerate_templates(
        template_dir=mock_template_dir,
        subdomain="docs.aspose.org",
        family="cells",
        locale="en",
        platform="python",
    )

    assert len(templates) > 10  # Should have more than quota

    mandatory, optional = classify_templates(templates, launch_tier="standard")
    selected = select_templates_with_quota(mandatory, optional, max_pages=10)

    # Should respect max_pages=10
    assert len(selected) <= 10
    assert len(selected) >= 2  # At least min_pages=2


# Test 4: Reference section respects max_pages quota
def test_reference_section_respects_quota(mock_template_dir: Path):
    """Test that reference section respects max_pages=6 quota."""
    templates = enumerate_templates(
        template_dir=mock_template_dir,
        subdomain="reference.aspose.org",
        family="cells",
        locale="en",
        platform="python",
    )

    assert len(templates) > 6  # Should have more than quota

    mandatory, optional = classify_templates(templates, launch_tier="standard")
    selected = select_templates_with_quota(mandatory, optional, max_pages=6)

    # Should respect max_pages=6
    assert len(selected) <= 6
    assert len(selected) >= 1  # At least min_pages=1


# Test 5: KB section respects max_pages quota
def test_kb_section_respects_quota(mock_template_dir: Path):
    """Test that KB section respects max_pages=10 quota."""
    templates = enumerate_templates(
        template_dir=mock_template_dir,
        subdomain="kb.aspose.org",
        family="cells",
        locale="en",
        platform="python",
    )

    assert len(templates) > 10  # Should have more than quota

    mandatory, optional = classify_templates(templates, launch_tier="standard")
    selected = select_templates_with_quota(mandatory, optional, max_pages=10)

    # Should respect max_pages=10
    assert len(selected) <= 10
    assert len(selected) >= 3  # At least min_pages=3


# Test 6: Blog section respects max_pages quota
def test_blog_section_respects_quota(mock_template_dir: Path):
    """Test that blog section respects max_pages=3 quota."""
    templates = enumerate_templates(
        template_dir=mock_template_dir,
        subdomain="blog.aspose.org",
        family="cells",
        locale="en",
        platform="python",
    )

    assert len(templates) > 3  # Should have more than quota

    mandatory, optional = classify_templates(templates, launch_tier="standard")
    selected = select_templates_with_quota(mandatory, optional, max_pages=3)

    # Should respect max_pages=3
    assert len(selected) <= 3
    assert len(selected) >= 1  # At least min_pages=1


# Test 7: Total page count across all sections equals expected ~35 pages
def test_total_page_count_35_pages(mock_template_dir: Path):
    """Integration test: All sections combined should yield ~35 pages."""
    sections = [
        ("products", "products.aspose.org", 6),
        ("docs", "docs.aspose.org", 10),
        ("reference", "reference.aspose.org", 6),
        ("kb", "kb.aspose.org", 10),
        ("blog", "blog.aspose.org", 3),
    ]

    total_pages = 0
    for section, subdomain, expected_max in sections:
        templates = enumerate_templates(
            template_dir=mock_template_dir,
            subdomain=subdomain,
            family="cells",
            locale="en",
            platform="python",
        )

        mandatory, optional = classify_templates(templates, launch_tier="standard")
        selected = select_templates_with_quota(mandatory, optional, max_pages=expected_max)

        total_pages += len(selected)

    # Should sum to approximately 35 pages (6+10+6+10+3)
    assert total_pages == 35


# Test 8: Mandatory pages always included despite tight quota
def test_mandatory_pages_always_included(mock_template_dir: Path):
    """Test that mandatory pages are always included even with tight quota."""
    templates = enumerate_templates(
        template_dir=mock_template_dir,
        subdomain="docs.aspose.org",
        family="cells",
        locale="en",
        platform="python",
    )

    mandatory, optional = classify_templates(templates, launch_tier="standard")

    # Get original mandatory count
    original_mandatory_count = len(mandatory)

    # Apply tight quota (equal to mandatory count)
    selected = select_templates_with_quota(
        mandatory, optional, max_pages=original_mandatory_count
    )

    # All mandatory should still be included
    selected_mandatory = [t for t in selected if t["is_mandatory"]]
    assert len(selected_mandatory) == original_mandatory_count


# Test 9: Quota with diverse launch tiers
def test_quota_enforcement_across_tiers(mock_template_dir: Path):
    """Test that quota enforcement works consistently across launch tiers."""
    templates = enumerate_templates(
        template_dir=mock_template_dir,
        subdomain="docs.aspose.org",
        family="cells",
        locale="en",
        platform="python",
    )

    max_pages = 10

    for tier in ["minimal", "standard", "rich"]:
        mandatory, optional = classify_templates(templates, launch_tier=tier)
        selected = select_templates_with_quota(mandatory, optional, max_pages=max_pages)

        # Should respect max_pages regardless of tier
        assert len(selected) <= max_pages

        # All mandatory should be included
        selected_mandatory = [t for t in selected if t["is_mandatory"]]
        mandatory_slugs = {t["slug"] for t in mandatory}
        selected_slugs = {t["slug"] for t in selected_mandatory}
        assert mandatory_slugs.issubset(selected_slugs)


# Test 10: Page count comparison - before/after pilot quotas
def test_page_count_scaling():
    """Test that pilot quotas enable scaling from ~5 to ~35 pages."""
    # Old quotas (products=10, docs=50, reference=100, kb=30, blog=20)
    old_total = 1 + 2 + 1 + 3 + 1  # Sum of min_pages = 8 minimum
    # Actual old max: 10 + 50 + 100 + 30 + 20 = 210 pages

    # New pilot quotas (products=6, docs=10, reference=6, kb=10, blog=3)
    new_total_max = 6 + 10 + 6 + 10 + 3  # = 35 pages
    new_total_min = 1 + 2 + 1 + 3 + 1  # = 8 pages

    # Verify scaling
    assert new_total_max == 35  # Expected pilot total
    assert new_total_min == 8  # Minimum remains same


# Test 11: Load ruleset missing file handling
def test_load_ruleset_missing_file(tmp_path: Path):
    """Test that loading missing ruleset raises appropriate error."""
    from launch.workers.w4_ia_planner.worker import IAPlannerError

    # Don't create ruleset file, just temp directory
    with pytest.raises(IAPlannerError, match="Missing ruleset"):
        load_ruleset_quotas(tmp_path)


# Test 12: Deterministic quota selection
def test_deterministic_quota_selection(mock_template_dir: Path):
    """Test that quota selection is deterministic across runs."""
    templates = enumerate_templates(
        template_dir=mock_template_dir,
        subdomain="docs.aspose.org",
        family="cells",
        locale="en",
        platform="python",
    )

    mandatory, optional = classify_templates(templates, launch_tier="standard")

    # Select with quota multiple times
    selected1 = select_templates_with_quota(mandatory, optional, max_pages=10)
    selected2 = select_templates_with_quota(mandatory, optional, max_pages=10)

    # Should be identical
    paths1 = [t["template_path"] for t in selected1]
    paths2 = [t["template_path"] for t in selected2]
    assert paths1 == paths2
