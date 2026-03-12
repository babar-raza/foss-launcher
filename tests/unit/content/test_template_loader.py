"""Tests for the template_loader module — template parsing and frontmatter extraction.

SR-07: Ensures template files parse correctly and frontmatter placeholders
are stripped as expected.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from launcher.content.template_loader import (
    SECTION_SUBDOMAIN_MAP,
    extract_template_frontmatter,
    extract_template_sections,
    list_templates,
    load_template,
)

_PLACEHOLDER_RE = re.compile(r"__[A-Z0-9_]+__")

# Collect all (section, template_path) pairs for parametrized tests.
_ALL_TEMPLATES: list[tuple[str, Path]] = []
for _section in SECTION_SUBDOMAIN_MAP:
    for _path in list_templates(_section):
        _ALL_TEMPLATES.append((_section, _path))


class TestExtractTemplateSections:
    """Verify extract_template_sections on real template files."""

    @pytest.mark.parametrize(
        "section_and_path",
        _ALL_TEMPLATES,
        ids=[f"{s}:{p.name}" for s, p in _ALL_TEMPLATES],
    )
    def test_extract_template_sections_from_real_templates(
        self, section_and_path: tuple[str, Path],
    ) -> None:
        """Each content template in specs/templates/ should yield non-empty
        sections.  Pure-frontmatter templates (no markdown body) are allowed
        to return an empty list -- they are data-driven Hugo pages."""
        _section, path = section_and_path
        content = load_template(path)
        sections = extract_template_sections(content)
        # Check if this is a pure-frontmatter template (body is empty/whitespace
        # after stripping the YAML front matter delimiters).
        body = content
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                body = parts[2]
        has_body = body.strip() != ""
        if has_body:
            assert len(sections) > 0, (
                f"Template {path.name} has body content but produced no sections"
            )
        # Each returned section should have a non-empty heading
        for sec in sections:
            assert sec.heading, f"Empty heading in template {path.name}"


class TestExtractTemplateFrontmatter:
    """Verify frontmatter extraction strips all placeholders."""

    @pytest.mark.parametrize(
        "section_and_path",
        _ALL_TEMPLATES,
        ids=[f"{s}:{p.name}" for s, p in _ALL_TEMPLATES],
    )
    def test_extract_template_frontmatter_strips_all_placeholders(
        self, section_and_path: tuple[str, Path],
    ) -> None:
        """After extraction, no __UPPER_SNAKE__ values should remain."""
        _section, path = section_and_path
        content = load_template(path)
        fm, _required_keys = extract_template_frontmatter(content)
        for key, value in fm.items():
            if isinstance(value, str):
                assert not _PLACEHOLDER_RE.fullmatch(value), (
                    f"Placeholder value '{value}' for key '{key}' "
                    f"not stripped in template {path.name}"
                )
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str):
                        assert not _PLACEHOLDER_RE.fullmatch(item), (
                            f"Placeholder item '{item}' in key '{key}' "
                            f"not stripped in template {path.name}"
                        )


# ---------------------------------------------------------------------------
# TC-3827: two-tuple return contract for extract_template_frontmatter
# ---------------------------------------------------------------------------


class TestExtractTemplateFrontmatterTwoTuple:
    """extract_template_frontmatter returns (dict, frozenset) — TC-3827."""

    def test_placeholder_in_required_keys_not_in_dict(self) -> None:
        content = "---\ndescription: __DESCRIPTION__\n---\n## Body\n"
        fm, required_keys = extract_template_frontmatter(content)
        assert "description" not in fm
        assert "description" in required_keys

    def test_real_value_in_dict_not_in_required_keys(self) -> None:
        content = "---\nrobots: index, follow\n---\n## Body\n"
        fm, required_keys = extract_template_frontmatter(content)
        assert fm["robots"] == "index, follow"
        assert "robots" not in required_keys

    def test_no_overlap_between_dict_and_required_keys(self) -> None:
        content = (
            "---\n"
            "title: __TITLE__\n"
            "layout: reference-single\n"
            "seoTitle: __SEO_TITLE__\n"
            "type: topic\n"
            "---\n## Body\n"
        )
        fm, required_keys = extract_template_frontmatter(content)
        overlap = set(fm.keys()) & required_keys
        assert not overlap, f"Keys appear in both dict and required_keys: {overlap}"

    def test_mixed_template_separates_correctly(self) -> None:
        content = (
            "---\n"
            "layout: reference-single\n"
            "description: __DESCRIPTION__\n"
            "robots: index, follow\n"
            "keywords:\n  - __KW1__\n  - __KW2__\n"
            "---\n"
        )
        fm, required_keys = extract_template_frontmatter(content)
        assert fm == {"layout": "reference-single", "robots": "index, follow"}
        assert required_keys == frozenset({"description", "keywords"})

    def test_no_none_values_in_dict(self) -> None:
        content = "---\nlayout: reference-single\ntitle: __TITLE__\n---\n"
        fm, _required_keys = extract_template_frontmatter(content)
        assert all(v is not None for v in fm.values())

    def test_required_keys_is_frozenset(self) -> None:
        content = "---\ntitle: __TITLE__\n---\n"
        _fm, required_keys = extract_template_frontmatter(content)
        assert isinstance(required_keys, frozenset)

    def test_empty_content_returns_empty(self) -> None:
        fm, required_keys = extract_template_frontmatter("")
        assert fm == {}
        assert required_keys == frozenset()
