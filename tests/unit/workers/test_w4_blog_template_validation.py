"""TC-963: Unit tests for blog template validation.

This test module validates that all blog templates have the required
frontmatter fields to pass IAPlanner PagePlan validation.

Required fields per worker.py:817-823:
- section
- slug
- output_path
- url_path
- title
- purpose
- required_headings
- required_claim_ids
- required_snippet_tags
- cross_links

TC-963: Fix IAPlanner Blog Template Validation - Missing Title Field
"""

import pytest
import yaml
from pathlib import Path
from typing import List, Dict, Any


def get_blog_templates() -> List[Path]:
    """Discover all blog template files for 3d and note families.

    Returns:
        List of Path objects for blog template files
    """
    repo_root = Path(__file__).parent.parent.parent.parent
    template_dir = repo_root / "specs" / "templates" / "blog.aspose.org"

    templates = []

    # Find all .md files in 3d and note directories
    for family in ["3d", "note"]:
        family_dir = template_dir / family
        if family_dir.exists():
            for template_path in family_dir.rglob("*.md"):
                # Skip README files
                if template_path.name == "README.md":
                    continue
                templates.append(template_path)

    return templates


def extract_frontmatter(template_path: Path) -> Dict[str, Any]:
    """Extract YAML frontmatter from template file.

    Args:
        template_path: Path to template file

    Returns:
        Parsed frontmatter dictionary

    Raises:
        ValueError: If frontmatter is missing or malformed
    """
    content = template_path.read_text(encoding="utf-8")

    if not content.startswith("---"):
        raise ValueError(f"Template {template_path} has no frontmatter (must start with ---)")

    # Split on --- and take the second part (first is empty)
    parts = content.split("---", 2)
    if len(parts) < 3:
        raise ValueError(f"Template {template_path} has malformed frontmatter")

    frontmatter_text = parts[1]
    frontmatter = yaml.safe_load(frontmatter_text)

    if not frontmatter:
        raise ValueError(f"Template {template_path} has empty frontmatter")

    return frontmatter


def test_blog_templates_have_frontmatter():
    """Test 1: All blog templates have YAML frontmatter.

    Validates that every blog template starts with --- and has valid YAML.
    """
    templates = get_blog_templates()

    assert len(templates) > 0, "No blog templates found"

    for template_path in templates:
        content = template_path.read_text(encoding="utf-8")
        assert content.startswith("---"), \
            f"Template {template_path.relative_to(template_path.parent.parent.parent)} " \
            f"must start with --- (frontmatter delimiter)"


def test_blog_templates_have_title_field():
    """Test 2: All blog templates have 'title' field in frontmatter.

    This is the critical test for TC-963. IAPlanner validation requires
    the 'title' field at worker.py:818.
    """
    templates = get_blog_templates()

    assert len(templates) > 0, "No blog templates found"

    missing_title = []
    for template_path in templates:
        try:
            frontmatter = extract_frontmatter(template_path)
            if "title" not in frontmatter:
                missing_title.append(template_path)
        except ValueError as e:
            pytest.fail(f"Frontmatter parsing failed: {e}")

    if missing_title:
        relative_paths = [
            str(p.relative_to(p.parent.parent.parent)) for p in missing_title
        ]
        pytest.fail(
            f"Templates missing 'title' field in frontmatter:\n" +
            "\n".join(f"  - {p}" for p in relative_paths)
        )


def test_blog_templates_schema_compliant():
    """Test 3: Templates have all fields needed for PagePlan schema.

    While IAPlanner's fill_template_placeholders adds most fields,
    'title' must come from template frontmatter.

    Required fields per worker.py:817-823:
    - title (from template frontmatter)
    - section, slug, output_path, url_path (computed by IAPlanner)
    - purpose, required_headings, required_claim_ids, required_snippet_tags, cross_links (added by IAPlanner)
    """
    templates = get_blog_templates()

    assert len(templates) > 0, "No blog templates found"

    for template_path in templates:
        try:
            frontmatter = extract_frontmatter(template_path)

            # Title is the only field that MUST come from frontmatter
            assert "title" in frontmatter, \
                f"Template {template_path.relative_to(template_path.parent.parent.parent)} " \
                f"missing required 'title' field"

            # Title should be a string placeholder token
            title = frontmatter["title"]
            assert isinstance(title, str), \
                f"Template {template_path.relative_to(template_path.parent.parent.parent)} " \
                f"'title' must be a string, got {type(title)}"

        except ValueError as e:
            pytest.fail(f"Frontmatter parsing failed: {e}")


def test_template_deduplication_survivor_valid():
    """Test 4: Surviving template (alphabetically first) is valid.

    TC-959 deduplication selects the alphabetically first template by
    template_path when multiple _index variants exist for the same section.

    This test ensures the survivor has valid frontmatter with 'title' field.
    """
    templates = get_blog_templates()

    assert len(templates) > 0, "No blog templates found"

    # Group by section
    sections = {}
    for template_path in templates:
        # Extract section from path
        parts = template_path.relative_to(template_path.parent.parent).parts
        if len(parts) > 1:
            section = parts[0]
        else:
            section = "root"

        if section not in sections:
            sections[section] = []
        sections[section].append(template_path)

    # For each section with multiple templates, find alphabetically first
    for section, section_templates in sections.items():
        if len(section_templates) > 1:
            # Sort by template_path (same as IAPlanner)
            sorted_templates = sorted(section_templates, key=lambda p: str(p))
            survivor = sorted_templates[0]

            # Validate survivor has title field
            try:
                frontmatter = extract_frontmatter(survivor)
                assert "title" in frontmatter, \
                    f"Deduplication survivor for section '{section}' " \
                    f"({survivor.relative_to(survivor.parent.parent.parent)}) " \
                    f"missing 'title' field"
            except ValueError as e:
                pytest.fail(
                    f"Deduplication survivor for section '{section}' has invalid frontmatter: {e}"
                )
