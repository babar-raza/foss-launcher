"""Tests for skeleton variant registry and resolution (TC-3799)."""
from __future__ import annotations

import pytest

from launcher.shared.page_skeletons import (
    PAGE_ROLE_SKELETONS,
    SKELETON_VARIANTS,
    SLUG_TOPIC_PATTERNS,
    TOPIC_CATEGORY_MAP,
    SkeletonSection,
    resolve_skeleton,
    resolve_topic_tag,
)


# ---------------------------------------------------------------------------
# resolve_topic_tag
# ---------------------------------------------------------------------------


class TestResolveTopicTag:
    """Tests for resolve_topic_tag()."""

    def test_from_topic_category_load_file(self) -> None:
        assert resolve_topic_tag("howto_article", topic_category="load_file") == "load_file"

    def test_from_topic_category_save_file(self) -> None:
        assert resolve_topic_tag("howto_article", topic_category="save_file") == "save_file"

    def test_from_topic_category_convert_formats(self) -> None:
        assert resolve_topic_tag("howto_article", topic_category="convert_formats") == "convert_formats"

    def test_from_topic_category_troubleshoot(self) -> None:
        assert resolve_topic_tag("howto_article", topic_category="troubleshoot") == "troubleshoot"

    def test_from_topic_category_optimize(self) -> None:
        assert resolve_topic_tag("howto_article", topic_category="optimize_performance") == "optimize_performance"

    def test_from_slug_installation(self) -> None:
        assert resolve_topic_tag("workflow_page", slug="installation") == "install"

    def test_from_slug_getting_started(self) -> None:
        assert resolve_topic_tag("workflow_page", slug="getting-started") == "getting_started"

    def test_from_slug_spreadsheet_operations(self) -> None:
        assert resolve_topic_tag("workflow_page", slug="spreadsheet-operations") == "data_operations"

    def test_from_slug_formula_calculation(self) -> None:
        assert resolve_topic_tag("workflow_page", slug="formula-calculation") == "computation"

    def test_from_slug_document_conversion(self) -> None:
        assert resolve_topic_tag("workflow_page", slug="document-conversion") == "convert_formats"

    def test_from_slug_notebook_manipulation(self) -> None:
        assert resolve_topic_tag("workflow_page", slug="notebook-manipulation") == "data_operations"

    def test_from_slug_rendering(self) -> None:
        assert resolve_topic_tag("workflow_page", slug="rendering") == "computation"

    def test_default_fallback_unknown_slug(self) -> None:
        assert resolve_topic_tag("workflow_page", slug="something-unusual") == "default"

    def test_default_fallback_no_signals(self) -> None:
        assert resolve_topic_tag("workflow_page") == "default"

    def test_default_fallback_unknown_topic_category(self) -> None:
        assert resolve_topic_tag("howto_article", topic_category="unknown_topic") == "default"

    def test_topic_category_takes_priority_over_slug(self) -> None:
        """topic_category should win even if slug also matches."""
        result = resolve_topic_tag(
            "howto_article",
            topic_category="troubleshoot",
            slug="installation",
        )
        assert result == "troubleshoot"

    def test_case_insensitive_slug(self) -> None:
        assert resolve_topic_tag("workflow_page", slug="Installation") == "install"

    def test_uninstall_does_not_match_install(self) -> None:
        """Segment-boundary matching prevents 'uninstall' matching 'install'."""
        assert resolve_topic_tag("workflow_page", slug="uninstall") == "default"

    def test_server_side_rendering_does_not_match_rendering(self) -> None:
        """Segment-boundary matching prevents false overmatch."""
        assert resolve_topic_tag("workflow_page", slug="server-side-rendering") == "computation"

    def test_getting_started_variant_exists(self) -> None:
        result = resolve_skeleton("workflow_page", "getting_started")
        headings = [s.heading for s in result]
        assert "First Steps" in headings
        assert "Next Steps" in headings


# ---------------------------------------------------------------------------
# resolve_skeleton
# ---------------------------------------------------------------------------


class TestResolveSkeleton:
    """Tests for resolve_skeleton()."""

    def test_variant_found_install(self) -> None:
        result = resolve_skeleton("workflow_page", "install")
        headings = [s.heading for s in result]
        assert "System Requirements" in headings
        assert "Installation" in headings
        assert "Verify Installation" in headings

    def test_variant_found_data_operations(self) -> None:
        result = resolve_skeleton("workflow_page", "data_operations")
        headings = [s.heading for s in result]
        assert "Working with Data" in headings

    def test_variant_found_computation(self) -> None:
        result = resolve_skeleton("workflow_page", "computation")
        headings = [s.heading for s in result]
        assert "Core Concepts" in headings
        assert "Implementation" in headings

    def test_variant_found_howto_load_file(self) -> None:
        result = resolve_skeleton("howto_article", "load_file")
        headings = [s.heading for s in result]
        assert "Loading the File" in headings
        assert "Supported Formats" in headings

    def test_variant_found_howto_troubleshoot(self) -> None:
        result = resolve_skeleton("howto_article", "troubleshoot")
        headings = [s.heading for s in result]
        assert "Symptoms" in headings
        assert "Root Cause" in headings

    def test_variant_found_howto_optimize(self) -> None:
        result = resolve_skeleton("howto_article", "optimize_performance")
        headings = [s.heading for s in result]
        assert "Optimization Steps" in headings
        assert "Benchmarks" in headings

    def test_fallback_to_default(self) -> None:
        """Unknown variant tag should return PAGE_ROLE_SKELETONS default."""
        result = resolve_skeleton("workflow_page", "nonexistent_variant")
        default = PAGE_ROLE_SKELETONS["workflow_page"]
        assert [s.heading for s in result] == [s.heading for s in default]

    def test_default_tag_returns_default(self) -> None:
        result = resolve_skeleton("workflow_page", "default")
        default = PAGE_ROLE_SKELETONS["workflow_page"]
        assert [s.heading for s in result] == [s.heading for s in default]

    def test_unknown_role_returns_generic(self) -> None:
        result = resolve_skeleton("completely_unknown_role", "default")
        assert len(result) == 1
        assert result[0].heading == "Content"

    def test_empty_variant_falls_back_to_default(self) -> None:
        """Empty variant list should fall back to default, not return []."""
        key = ("workflow_page", "_test_empty")
        SKELETON_VARIANTS[key] = []
        try:
            result = resolve_skeleton("workflow_page", "_test_empty")
            default = PAGE_ROLE_SKELETONS["workflow_page"]
            assert [s.heading for s in result] == [s.heading for s in default]
        finally:
            del SKELETON_VARIANTS[key]

    def test_all_variants_differ_from_default(self) -> None:
        """Every variant must have different headings than its role's default."""
        for (role, tag), variant_skeleton in SKELETON_VARIANTS.items():
            default_skeleton = PAGE_ROLE_SKELETONS.get(role, [])
            variant_headings = [s.heading for s in variant_skeleton]
            default_headings = [s.heading for s in default_skeleton]
            assert variant_headings != default_headings, (
                f"Variant ({role}, {tag}) has identical headings to default"
            )

    def test_all_variants_have_nonempty_hints(self) -> None:
        """Every SkeletonSection in variants must have a non-empty content_hint."""
        for (role, tag), skeleton in SKELETON_VARIANTS.items():
            for section in skeleton:
                assert section.content_hint, (
                    f"Empty content_hint in ({role}, {tag}) section '{section.heading}'"
                )

    def test_all_variants_end_with_see_also(self) -> None:
        """Every variant should end with a See Also section."""
        for (role, tag), skeleton in SKELETON_VARIANTS.items():
            assert skeleton[-1].heading == "See Also", (
                f"Variant ({role}, {tag}) does not end with See Also"
            )

    def test_page_role_skeletons_unchanged(self) -> None:
        """PAGE_ROLE_SKELETONS must still have exactly 17 roles."""
        assert len(PAGE_ROLE_SKELETONS) == 17
        expected_roles = {
            "landing", "toc", "comprehensive_guide", "workflow_page",
            "feature_showcase", "troubleshooting", "api_reference",
            "reference_object_page", "faq", "best_practices", "tutorial",
            "howto_article", "blog_announcement", "blog", "feature_blog",
            "format_conversion", "performance_guide",
        }
        assert set(PAGE_ROLE_SKELETONS.keys()) == expected_roles
