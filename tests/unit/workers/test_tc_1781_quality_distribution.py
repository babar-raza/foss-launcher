"""Tests for TC-1731, TC-1740-1743, TC-1750-1752: W2 Quality, W4 Distribution, W7 Fixes.

Covers:
- TC-1731: _is_implementation_detail filter
- TC-1743: inject_see_also_section (W6)
- TC-1752: per-page scoring + publication readiness
"""

from __future__ import annotations

import pytest
from typing import Any, Dict, List


# ---------------------------------------------------------------------------
# TC-1731: Implementation Detail Filter
# ---------------------------------------------------------------------------

class TestIsImplementationDetail:
    """Tests for _is_implementation_detail()."""

    def test_return_statement_with_class(self):
        from launch.workers.w2_facts_builder.extract_claims import _is_implementation_detail
        # Two matches: return X() + isinstance or similar
        text = "return isinstance(obj, MyClass) and return SomeClass()"
        assert _is_implementation_detail(text)

    def test_dunder_methods(self):
        from launch.workers.w2_facts_builder.extract_claims import _is_implementation_detail
        text = "The __init__ method calls self._validate_input to setup"
        assert _is_implementation_detail(text)

    def test_private_method_with_super(self):
        from launch.workers.w2_facts_builder.extract_claims import _is_implementation_detail
        text = "The _prepare_data() function calls super().__init__() internally"
        assert _is_implementation_detail(text)

    def test_user_facing_feature_not_flagged(self):
        from launch.workers.w2_facts_builder.extract_claims import _is_implementation_detail
        text = "Supports loading and saving 3D models in OBJ and STL formats"
        assert not _is_implementation_detail(text)

    def test_api_usage_not_flagged(self):
        from launch.workers.w2_facts_builder.extract_claims import _is_implementation_detail
        text = "The Scene class provides methods for creating and manipulating 3D scenes"
        assert not _is_implementation_detail(text)

    def test_single_pattern_match_not_flagged(self):
        from launch.workers.w2_facts_builder.extract_claims import _is_implementation_detail
        # Only one match (isinstance) - threshold is 2
        text = "Uses isinstance to check input types for type safety"
        assert not _is_implementation_detail(text)

    def test_raise_with_private_access(self):
        from launch.workers.w2_facts_builder.extract_claims import _is_implementation_detail
        text = "raise TypeError if self._internal_state is invalid"
        assert _is_implementation_detail(text)


# ---------------------------------------------------------------------------
# TC-1743: W6 See Also Injection
# ---------------------------------------------------------------------------

class TestInjectSeeAlsoSection:
    """Tests for inject_see_also_section()."""

    def test_injects_see_also_with_related_pages(self):
        from launch.workers.w8_linker_and_patcher.worker import inject_see_also_section

        content = "# Guide\n\nSome content here."
        related = [{"slug": "tutorial", "section": "docs", "overlap_score": 0.5}]
        all_pages = [{"slug": "tutorial", "title": "Tutorial", "url_path": "/docs/tutorial/", "section": "docs"}]

        result = inject_see_also_section(content, related, all_pages)
        assert "## See Also" in result
        # TC-2103: Links are now absolute
        assert "[Tutorial](https://docs.aspose.org/docs/tutorial/)" in result

    def test_idempotent_no_duplicate(self):
        from launch.workers.w8_linker_and_patcher.worker import inject_see_also_section

        content = "# Guide\n\nSome content.\n\n## See Also\n\n- [Existing](/link/)\n"
        related = [{"slug": "tutorial", "section": "docs"}]
        all_pages = [{"slug": "tutorial", "title": "Tutorial", "url_path": "/docs/tutorial/"}]

        result = inject_see_also_section(content, related, all_pages)
        # Should not add duplicate See Also
        assert result.count("## See Also") == 1

    def test_empty_related_pages_no_change(self):
        from launch.workers.w8_linker_and_patcher.worker import inject_see_also_section

        content = "# Guide\n\nContent."
        result = inject_see_also_section(content, [], [])
        assert result == content
        assert "## See Also" not in result

    def test_fallback_title_from_slug(self):
        from launch.workers.w8_linker_and_patcher.worker import inject_see_also_section

        content = "# Guide\n\nContent."
        related = [{"slug": "getting-started"}]
        # No matching page in all_pages — title derived from slug
        all_pages = []

        result = inject_see_also_section(content, related, all_pages)
        assert "## See Also" in result
        assert "Getting Started" in result  # Title derived from slug

    def test_page_without_url_no_link(self):
        from launch.workers.w8_linker_and_patcher.worker import inject_see_also_section

        content = "# Guide\n\nContent."
        related = [{"slug": "api-ref"}]
        all_pages = [{"slug": "api-ref", "title": "API Reference"}]  # no url_path

        result = inject_see_also_section(content, related, all_pages)
        assert "## See Also" in result
        assert "API Reference" in result
        assert "]()" not in result  # No empty link


# ---------------------------------------------------------------------------
# TC-1752: Per-Page Scoring + Publication Readiness
# ---------------------------------------------------------------------------

class TestCalculatePerPageScores:
    """Tests for calculate_per_page_scores()."""

    def test_scores_each_page_independently(self):
        from launch.workers.w7_content_reviewer.scoring import calculate_per_page_scores

        issues = [
            {"check": "content_quality.density", "severity": "warn",
             "location": {"path": "docs/guide.md"}, "message": "Low density"},
            {"check": "content_quality.density", "severity": "warn",
             "location": {"path": "docs/guide.md"}, "message": "Low density 2"},
            {"check": "technical_accuracy.api_ref", "severity": "error",
             "location": {"path": "kb/faq.md"}, "message": "Unknown API"},
        ]

        scores = calculate_per_page_scores(issues)
        assert "docs/guide.md" in scores
        assert "kb/faq.md" in scores
        # Each page scored independently
        assert scores["docs/guide.md"]["content_quality"] <= 5
        assert scores["kb/faq.md"]["technical_accuracy"] <= 5

    def test_empty_issues_returns_empty(self):
        from launch.workers.w7_content_reviewer.scoring import calculate_per_page_scores

        scores = calculate_per_page_scores([])
        assert scores == {}

    def test_single_page_all_dimensions(self):
        from launch.workers.w7_content_reviewer.scoring import calculate_per_page_scores

        issues = [
            {"check": "content_quality.density", "severity": "warn",
             "location": {"path": "page.md"}, "message": "Issue"},
            {"check": "usability.navigation", "severity": "warn",
             "location": {"path": "page.md"}, "message": "Issue"},
        ]

        scores = calculate_per_page_scores(issues)
        assert len(scores) == 1
        page_scores = scores["page.md"]
        assert "content_quality" in page_scores
        assert "technical_accuracy" in page_scores
        assert "usability" in page_scores


class TestCheckPublicationReadiness:
    """Tests for check_publication_readiness()."""

    def test_ready_when_all_pages_pass(self):
        from launch.workers.w7_content_reviewer.scoring import check_publication_readiness

        per_page = {
            "page1.md": {"content_quality": 5, "technical_accuracy": 5, "usability": 4},
            "page2.md": {"content_quality": 4, "technical_accuracy": 4, "usability": 5},
        }

        result = check_publication_readiness(per_page)
        assert result["ready"] is True
        assert result["total_pages"] == 2
        assert result["passing_pages"] == 2
        assert result["actual_pass_rate"] == 1.0

    def test_not_ready_when_too_many_fail(self):
        from launch.workers.w7_content_reviewer.scoring import check_publication_readiness

        per_page = {
            "page1.md": {"content_quality": 5, "technical_accuracy": 5, "usability": 5},
            "page2.md": {"content_quality": 2, "technical_accuracy": 3, "usability": 2},
            "page3.md": {"content_quality": 1, "technical_accuracy": 2, "usability": 1},
        }

        result = check_publication_readiness(per_page, threshold=4, pass_rate=0.8)
        assert result["ready"] is False
        assert result["passing_pages"] == 1
        assert len(result["failing_pages"]) == 2

    def test_empty_pages_is_ready(self):
        from launch.workers.w7_content_reviewer.scoring import check_publication_readiness

        result = check_publication_readiness({})
        assert result["ready"] is True
        assert result["total_pages"] == 0

    def test_failing_pages_have_details(self):
        from launch.workers.w7_content_reviewer.scoring import check_publication_readiness

        per_page = {
            "bad.md": {"content_quality": 3, "technical_accuracy": 5, "usability": 5},
        }

        result = check_publication_readiness(per_page, threshold=4)
        assert result["ready"] is False
        assert len(result["failing_pages"]) == 1
        failing = result["failing_pages"][0]
        assert failing["path"] == "bad.md"
        assert "content_quality" in failing["failing_dimensions"]

    def test_custom_threshold_and_pass_rate(self):
        from launch.workers.w7_content_reviewer.scoring import check_publication_readiness

        per_page = {
            "p1.md": {"content_quality": 3, "technical_accuracy": 3, "usability": 3},
            "p2.md": {"content_quality": 3, "technical_accuracy": 3, "usability": 3},
            "p3.md": {"content_quality": 3, "technical_accuracy": 3, "usability": 3},
        }

        # With threshold=3, all pages pass
        result = check_publication_readiness(per_page, threshold=3, pass_rate=0.5)
        assert result["ready"] is True

    def test_pass_rate_boundary(self):
        from launch.workers.w7_content_reviewer.scoring import check_publication_readiness

        per_page = {
            "p1.md": {"content_quality": 5, "technical_accuracy": 5, "usability": 5},
            "p2.md": {"content_quality": 5, "technical_accuracy": 5, "usability": 5},
            "p3.md": {"content_quality": 5, "technical_accuracy": 5, "usability": 5},
            "p4.md": {"content_quality": 5, "technical_accuracy": 5, "usability": 5},
            "p5.md": {"content_quality": 2, "technical_accuracy": 2, "usability": 2},
        }

        # 4/5 = 0.8 = exactly at pass_rate
        result = check_publication_readiness(per_page, threshold=4, pass_rate=0.8)
        assert result["ready"] is True
        assert result["actual_pass_rate"] == 0.8
