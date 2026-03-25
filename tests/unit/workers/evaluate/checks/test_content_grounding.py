"""Tests for check_content_grounding (TC-5154 / SR-01).

Verifies that prose assertions are cross-checked against assigned claims
and produce appropriate findings when ungrounded.
"""
from __future__ import annotations

import pytest

from launcher.workers.evaluate.checks.hallucination_rate import check_content_grounding


class TestContentGroundingEmptyInputs:
    """Early-return paths: empty content or empty claims."""

    def test_empty_content_returns_empty(self):
        assert check_content_grounding("", ["some claim"]) == []

    def test_none_like_content_returns_empty(self):
        assert check_content_grounding("", ["x"]) == []

    def test_empty_claim_texts_returns_empty(self):
        assert check_content_grounding("This supports CSV export.", []) == []


class TestContentGroundingNoAssertions:
    """Content with no trigger verbs should produce no findings."""

    def test_plain_prose_no_trigger_verbs(self):
        content = "The library is a Python package for spreadsheets."
        findings = check_content_grounding(content, ["spreadsheet operations"])
        assert findings == []

    def test_code_only_no_assertions(self):
        content = "```python\nimport aspose_cells_foss\n```"
        findings = check_content_grounding(content, ["import support"])
        assert findings == []


class TestContentGroundingGroundedAssertions:
    """Assertions with matching claims should produce no findings."""

    def test_grounded_assertion_no_findings(self):
        # Terms must match exactly (no stemming): "export" matches "export"
        content = "This library supports workbook export and formatting operations."
        claims = ["Supports workbook export and formatting with styling"]
        findings = check_content_grounding(content, claims, slug="test")
        assert findings == []

    def test_grounded_with_single_term_assertion(self):
        # Assertion with only 1 meaningful term — _GROUNDING_MIN_TERMS is 2,
        # but min(2, len(a_terms)) = min(2, 1) = 1, so 1 match suffices.
        content = "This library provides spreadsheets."
        claims = ["Handles spreadsheets and workbooks"]
        findings = check_content_grounding(content, claims, slug="test")
        assert findings == []


class TestContentGroundingUngrounded:
    """Assertions without matching claims should produce findings."""

    def test_single_ungrounded_medium_finding(self):
        # Rate must be <= 30% for MEDIUM: 1 ungrounded out of 4+ assertions
        content = (
            "This library supports workbook formatting operations. "
            "It provides workbook export features. "
            "It enables workbook styling capabilities. "
            "It offers quantum blockchain rendering."  # ungrounded
        )
        claims = ["Supports workbook formatting export styling operations"]
        findings = check_content_grounding(content, claims, slug="page1")
        medium = [f for f in findings if f.severity == "medium"]
        assert len(medium) >= 1
        assert medium[0].check == "content_grounding"
        assert medium[0].location == "page1"

    def test_slug_in_finding_location(self):
        # Single assertion, 100% ungrounded → HIGH
        content = "This library enables blockchain validation."
        claims = ["CSV export"]
        findings = check_content_grounding(content, claims, slug="my-slug")
        assert len(findings) >= 1
        assert findings[0].location == "my-slug"

    def test_medium_findings_capped_at_five(self):
        # 6 ungrounded assertions, rate < 30% would need many total assertions,
        # but if all are ungrounded (100% > 30%), we get HIGH instead.
        # So test with mix: 6 ungrounded + enough grounded to stay under 30%.
        grounded_claim = "Supports spreadsheet workbook operations management formatting styling"
        ungrounded_assertions = [
            "This library supports PDF rendering capabilities.",
            "It provides blockchain validation features.",
            "It enables quantum computing integration.",
            "It allows neural network training operations.",
            "It offers augmented reality processing.",
            "It includes holographic display generation.",
        ]
        grounded_assertions = [
            f"It supports spreadsheet operations {i}."
            for i in range(20)  # enough to keep rate < 30%
        ]
        content = "\n".join(ungrounded_assertions + grounded_assertions)
        findings = check_content_grounding(content, [grounded_claim], slug="test")
        medium_findings = [f for f in findings if f.severity == "medium"]
        assert len(medium_findings) <= 5


class TestContentGroundingHighSeverity:
    """When >30% of assertions are ungrounded, emit a single HIGH finding."""

    def test_high_severity_above_threshold(self):
        # All assertions ungrounded → 100% > 30% → HIGH
        content = (
            "This library supports PDF export. "
            "It provides 3D rendering. "
            "It enables blockchain validation. "
            "It offers quantum computing."
        )
        claims = ["Supports CSV file operations only"]
        findings = check_content_grounding(content, claims, slug="test")
        assert any(f.severity == "high" for f in findings)
        # HIGH finding should be a single summary, not per-assertion
        high_findings = [f for f in findings if f.severity == "high"]
        assert len(high_findings) == 1
        assert "content_grounding" == high_findings[0].check


class TestContentGroundingStripping:
    """Frontmatter and code blocks should be stripped before scanning."""

    def test_frontmatter_stripped(self):
        content = (
            "---\ntitle: Test\npage_role: docs\n---\n"
            "This library supports CSV export operations."
        )
        claims = ["Supports CSV export operations using Workbook"]
        findings = check_content_grounding(content, claims, slug="test")
        assert findings == []

    def test_code_blocks_stripped(self):
        # Assertion inside code block should not be extracted
        content = (
            "Some intro text.\n"
            "```python\n"
            "# This library supports PDF rendering\n"
            "import foo\n"
            "```\n"
        )
        claims = ["CSV operations only"]
        findings = check_content_grounding(content, claims, slug="test")
        # No assertions should be found in prose (only in code block)
        assert findings == []


class TestContentGroundingEdgeCases:
    """Boundary conditions and edge cases."""

    def test_assertion_with_only_stopwords_skipped(self):
        # "supports the use of this and that" — all terms are stop words or short
        content = "This library supports the use of it."
        claims = ["Something completely different with long terms"]
        findings = check_content_grounding(content, claims, slug="test")
        # The assertion "the use of it" has no meaningful terms → skipped
        assert findings == []

    def test_multiple_claims_any_match_grounds(self):
        content = "This library provides spreadsheet formatting operations."
        claims = [
            "Handles PDF rendering",
            "Provides spreadsheet formatting and styling operations",
        ]
        findings = check_content_grounding(content, claims, slug="test")
        assert findings == []
