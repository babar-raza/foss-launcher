"""Unit tests for page_skeletons.py (TC-3674).

Tests the deterministic skeleton template registry, rendering, and
post-generation validation.
"""

from __future__ import annotations

import pytest

from launch.workers.w5_section_writer.page_skeletons import (
    PAGE_ROLE_SKELETONS,
    SkeletonSection,
    _extract_h2_headings,
    get_required_headings,
    get_skeleton,
    render_skeleton_markdown,
    validate_against_skeleton,
)


# ── Registry coverage tests ──────────────────────────────────────────────


class TestSkeletonRegistry:
    """TC-3674: PAGE_ROLE_SKELETONS covers all 17 page roles."""

    ALL_PAGE_ROLES = [
        "landing", "toc", "comprehensive_guide", "workflow_page",
        "feature_showcase", "troubleshooting", "api_reference",
        "reference_object_page", "faq", "best_practices", "tutorial",
        "howto_article", "blog_announcement", "blog", "feature_blog",
        "format_conversion", "performance_guide",
    ]

    def test_all_17_roles_have_skeletons(self):
        for role in self.ALL_PAGE_ROLES:
            assert role in PAGE_ROLE_SKELETONS, (
                f"Page role '{role}' missing from PAGE_ROLE_SKELETONS"
            )

    def test_registry_has_exactly_17_entries(self):
        assert len(PAGE_ROLE_SKELETONS) == 17

    def test_all_values_are_non_empty_lists(self):
        for role, sections in PAGE_ROLE_SKELETONS.items():
            assert isinstance(sections, list), f"{role}: expected list"
            assert len(sections) > 0, f"{role}: empty skeleton"

    def test_all_sections_are_skeleton_section_tuples(self):
        for role, sections in PAGE_ROLE_SKELETONS.items():
            for section in sections:
                assert isinstance(section, SkeletonSection), (
                    f"{role}: not a SkeletonSection: {section}"
                )

    def test_all_sections_have_level_2(self):
        """All skeleton sections should be H2 level."""
        for role, sections in PAGE_ROLE_SKELETONS.items():
            for section in sections:
                assert section.level == 2, (
                    f"{role}/{section.heading}: level is {section.level}, expected 2"
                )

    def test_see_also_is_last_when_present(self):
        """If 'See Also' is in the skeleton, it must be the last section."""
        for role, sections in PAGE_ROLE_SKELETONS.items():
            see_also_indices = [
                i for i, s in enumerate(sections) if s.heading == "See Also"
            ]
            if see_also_indices:
                assert see_also_indices[-1] == len(sections) - 1, (
                    f"{role}: 'See Also' is not the last section"
                )


# ── get_skeleton tests ───────────────────────────────────────────────────


class TestGetSkeleton:
    """TC-3674: get_skeleton() returns correct skeletons."""

    def test_landing_returns_skeleton(self):
        skeleton = get_skeleton("landing")
        assert skeleton is not None
        headings = [s.heading for s in skeleton]
        assert "Overview" in headings
        assert "Key Features" in headings
        assert "Quick Start" in headings
        assert "See Also" in headings

    def test_unknown_role_returns_none(self):
        assert get_skeleton("nonexistent_role") is None

    def test_howto_article_has_goal(self):
        skeleton = get_skeleton("howto_article")
        assert skeleton is not None
        headings = [s.heading for s in skeleton]
        assert "Goal" in headings
        assert "Prerequisites" in headings
        assert "Steps" in headings


# ── get_required_headings tests ──────────────────────────────────────────


class TestGetRequiredHeadings:
    """TC-3674: get_required_headings() returns only required headings."""

    def test_landing_required_headings(self):
        required = get_required_headings("landing")
        assert "Overview" in required
        assert "Key Features" in required
        assert "Quick Start" in required
        assert "See Also" in required

    def test_comprehensive_guide_excludes_optional(self):
        required = get_required_headings("comprehensive_guide")
        # Advanced Usage and Troubleshooting are optional
        assert "Advanced Usage" not in required
        assert "Troubleshooting" not in required
        # But Introduction, Core Concepts, Implementation are required
        assert "Introduction" in required
        assert "Core Concepts" in required
        assert "Implementation" in required

    def test_unknown_role_returns_empty(self):
        assert get_required_headings("nonexistent_role") == []


# ── render_skeleton_markdown tests ───────────────────────────────────────


class TestRenderSkeletonMarkdown:
    """TC-3674: render_skeleton_markdown() produces correct output."""

    def test_output_contains_headings(self):
        skeleton = get_skeleton("landing")
        md = render_skeleton_markdown(skeleton)
        assert "## Overview" in md
        assert "## Key Features" in md
        assert "## Quick Start" in md
        assert "## See Also" in md

    def test_output_contains_fill_markers(self):
        skeleton = get_skeleton("landing")
        md = render_skeleton_markdown(skeleton)
        assert "<!-- FILL:" in md

    def test_output_marks_required_and_optional(self):
        skeleton = get_skeleton("comprehensive_guide")
        md = render_skeleton_markdown(skeleton)
        assert "(required)" in md
        assert "(optional)" in md

    def test_empty_skeleton_returns_empty(self):
        md = render_skeleton_markdown([])
        assert md == ""


# ── _extract_h2_headings tests ───────────────────────────────────────────


class TestExtractH2Headings:
    """TC-3674: _extract_h2_headings() correctly parses markdown."""

    def test_simple_h2(self):
        content = "## Overview\n\nSome text.\n\n## See Also\n\nLinks."
        headings = _extract_h2_headings(content)
        assert headings == ["Overview", "See Also"]

    def test_h3_not_included(self):
        content = "## Overview\n\n### Sub-section\n\n## See Also"
        headings = _extract_h2_headings(content)
        assert headings == ["Overview", "See Also"]

    def test_headings_inside_fences_ignored(self):
        content = "## Real\n\n```\n## Fake\n```\n\n## Also Real"
        headings = _extract_h2_headings(content)
        assert headings == ["Real", "Also Real"]

    def test_empty_content(self):
        assert _extract_h2_headings("") == []

    def test_no_headings(self):
        assert _extract_h2_headings("Just a paragraph.") == []


# ── validate_against_skeleton tests ──────────────────────────────────────


class TestValidateAgainstSkeleton:
    """TC-3674: validate_against_skeleton() catches structural issues."""

    def test_valid_landing_page_passes(self):
        content = (
            "## Overview\n\nProduct intro.\n\n"
            "## Key Features\n\nFeature list.\n\n"
            "## Quick Start\n\nCode example.\n\n"
            "## See Also\n\n- Link 1\n"
        )
        skeleton = get_skeleton("landing")
        issues = validate_against_skeleton(content, skeleton)
        assert issues == []

    def test_missing_required_section_detected(self):
        content = (
            "## Overview\n\nProduct intro.\n\n"
            "## See Also\n\n- Link 1\n"
        )
        skeleton = get_skeleton("landing")
        issues = validate_against_skeleton(content, skeleton)
        error_msgs = [i["message"] for i in issues if i["type"] == "error"]
        assert any("Key Features" in msg for msg in error_msgs)
        assert any("Quick Start" in msg for msg in error_msgs)

    def test_see_also_not_last_detected(self):
        content = (
            "## Overview\n\nProduct intro.\n\n"
            "## Key Features\n\nFeatures.\n\n"
            "## See Also\n\n- Links\n\n"
            "## Quick Start\n\nCode example.\n"
        )
        skeleton = get_skeleton("landing")
        issues = validate_against_skeleton(content, skeleton)
        error_msgs = [i["message"] for i in issues if i["type"] == "error"]
        assert any("See Also" in msg and "last" in msg for msg in error_msgs)

    def test_duplicate_h2_detected(self):
        content = (
            "## Overview\n\nFirst.\n\n"
            "## Key Features\n\nFeatures.\n\n"
            "## Quick Start\n\nCode.\n\n"
            "## Overview\n\nDuplicate!\n\n"
            "## See Also\n\n- Links\n"
        )
        skeleton = get_skeleton("landing")
        issues = validate_against_skeleton(content, skeleton)
        error_msgs = [i["message"] for i in issues if i["type"] == "error"]
        assert any("Duplicate" in msg and "overview" in msg for msg in error_msgs)

    def test_case_insensitive_heading_match(self):
        content = (
            "## overview\n\nIntro.\n\n"
            "## key features\n\nFeatures.\n\n"
            "## quick start\n\nCode.\n\n"
            "## see also\n\n- Links\n"
        )
        skeleton = get_skeleton("landing")
        issues = validate_against_skeleton(content, skeleton)
        # Should pass — headings match case-insensitively
        missing = [i for i in issues if "Missing required" in i["message"]]
        assert missing == []

    def test_optional_sections_not_required(self):
        """Missing optional sections should not produce errors."""
        content = (
            "## Introduction\n\nIntro.\n\n"
            "## Core Concepts\n\nConcepts.\n\n"
            "## Implementation\n\nSteps.\n\n"
            "## See Also\n\n- Links\n"
        )
        skeleton = get_skeleton("comprehensive_guide")
        issues = validate_against_skeleton(content, skeleton)
        # Advanced Usage and Troubleshooting are optional — no error
        missing = [i for i in issues if "Missing required" in i["message"]]
        assert missing == []

    def test_empty_content_fails_all_required(self):
        skeleton = get_skeleton("landing")
        issues = validate_against_skeleton("", skeleton)
        required_count = sum(1 for s in skeleton if s.required)
        missing_count = sum(1 for i in issues if "Missing required" in i["message"])
        assert missing_count == required_count

    def test_howto_article_valid(self):
        content = (
            "## Goal\n\nLearn something.\n\n"
            "## Prerequisites\n\nPython 3.8+\n\n"
            "## Steps\n\n1. Step one.\n\n"
            "## Code Example\n\n```python\npass\n```\n\n"
            "## See Also\n\n- Link\n"
        )
        skeleton = get_skeleton("howto_article")
        issues = validate_against_skeleton(content, skeleton)
        errors = [i for i in issues if i["type"] == "error"]
        assert errors == []
