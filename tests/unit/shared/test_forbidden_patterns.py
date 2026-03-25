"""Tests for shared.forbidden_patterns — TC-5152."""
from __future__ import annotations

import pytest

from launcher.shared.forbidden_patterns import (
    FORBIDDEN_PATTERNS,
    scan_forbidden,
    strip_forbidden,
)


class TestScanForbidden:
    """scan_forbidden detects all registered forbidden patterns."""

    def test_clean_content_returns_empty(self):
        result = scan_forbidden("This is perfectly clean content with no issues.")
        assert result == []

    def test_identifier_omitted(self):
        content = "Use the [identifier omitted] class to process data."
        result = scan_forbidden(content)
        assert len(result) == 1
        assert result[0][0] == "hallucinated_identifier"
        assert result[0][1] == "critical"
        assert result[0][3] == 1  # count

    def test_multiple_identifier_omitted(self):
        content = "Use [identifier omitted] and [identifier omitted] classes."
        result = scan_forbidden(content)
        cats = [r[0] for r in result]
        assert "hallucinated_identifier" in cats
        # Should report count=2
        for r in result:
            if r[0] == "hallucinated_identifier":
                assert r[3] == 2

    def test_source_comment(self):
        content = "Some text\n# source: snippet_042\nMore text"
        result = scan_forbidden(content)
        cats = [r[0] for r in result]
        assert "internal_metadata" in cats

    def test_bare_claim_id(self):
        content = "CLM-cells-dc36dc: This is a claim about cells."
        result = scan_forbidden(content)
        cats = [r[0] for r in result]
        assert "claim_id_leak" in cats

    def test_claim_citation_bracket(self):
        content = "Supports CSV export [CLM-cells-abc123]."
        result = scan_forbidden(content)
        cats = [r[0] for r in result]
        assert "claim_id_leak" in cats

    def test_content_to_be_generated(self):
        content = "## Overview\n\n[Content to be generated]"
        result = scan_forbidden(content)
        cats = [r[0] for r in result]
        assert "template_placeholder" in cats

    def test_sentence_count_instruction(self):
        content = "Write 2-3 sentences about the feature."
        result = scan_forbidden(content)
        cats = [r[0] for r in result]
        assert "template_placeholder" in cats

    def test_placeholder_url(self):
        content = "See the docs at docs.example.com/api for more."
        result = scan_forbidden(content)
        cats = [r[0] for r in result]
        assert "placeholder_url" in cats

    def test_placeholder_link(self):
        content = "For details, see (link-to-getting-started)."
        result = scan_forbidden(content)
        cats = [r[0] for r in result]
        assert "placeholder_link" in cats

    def test_multiple_pattern_types(self):
        content = (
            "Use [identifier omitted] to load.\n"
            "CLM-cells-abc123: supports CSV.\n"
            "[Content to be generated]\n"
        )
        result = scan_forbidden(content)
        cats = {r[0] for r in result}
        assert "hallucinated_identifier" in cats
        assert "claim_id_leak" in cats
        assert "template_placeholder" in cats


class TestStripForbidden:
    """strip_forbidden removes all forbidden patterns."""

    def test_strips_identifier_omitted(self):
        content = "Use the [identifier omitted] class."
        result = strip_forbidden(content)
        assert "[identifier omitted]" not in result
        assert "Use the  class." in result

    def test_strips_claim_id(self):
        content = "CLM-cells-dc36dc: This is content."
        result = strip_forbidden(content)
        assert "CLM-cells-dc36dc:" not in result
        assert "This is content." in result

    def test_strips_source_comment_line(self):
        content = "line1\n# source: snippet_001\nline2\n"
        result = strip_forbidden(content)
        assert "source: snippet_001" not in result
        assert "line1" in result
        assert "line2" in result

    def test_strips_content_placeholder(self):
        content = "## Section\n\n[Content to be generated]\n"
        result = strip_forbidden(content)
        assert "[Content to be generated]" not in result

    def test_preserves_clean_content(self):
        content = "This is clean content with no forbidden patterns.\n\nIt has multiple paragraphs."
        result = strip_forbidden(content)
        assert result == content

    def test_all_patterns_have_regex(self):
        """Every registered pattern has a compiled regex."""
        for pat in FORBIDDEN_PATTERNS:
            assert pat.regex is not None
            assert pat.category
            assert pat.severity in ("critical", "high", "medium", "low")


class TestSR05NewPatterns:
    """SR-05: Tests for the two patterns added in TC-5154."""

    def test_confidence_percentage_detected(self):
        content = "This claim has 75% confidence that CSV export works."
        result = scan_forbidden(content)
        cats = [r[0] for r in result]
        assert "llm_reasoning_leak" in cats

    def test_confidence_percentage_zero(self):
        content = "There is 0% confidence in this assertion."
        result = scan_forbidden(content)
        cats = [r[0] for r in result]
        assert "llm_reasoning_leak" in cats

    def test_high_confidence_no_number_not_matched(self):
        """'high confidence' without a number% should NOT match."""
        content = "We have high confidence in this feature."
        result = scan_forbidden(content)
        cats = [r[0] for r in result]
        assert "llm_reasoning_leak" not in cats

    def test_what_this_library_provides_detected(self):
        content = "## What this library provides\n\nSome content here."
        result = scan_forbidden(content)
        cats = [r[0] for r in result]
        assert "template_placeholder" in cats

    def test_what_this_library_provides_case_insensitive(self):
        content = "what This Library Provides features for spreadsheets."
        result = scan_forbidden(content)
        cats = [r[0] for r in result]
        assert "template_placeholder" in cats

    def test_strip_confidence_percentage(self):
        content = "Feature has 90% confidence rating."
        result = strip_forbidden(content)
        assert "90% confidence" not in result

    def test_strip_what_this_library_provides(self):
        content = "## What this library provides\n\nContent."
        result = strip_forbidden(content)
        assert "What this library provides" not in result
