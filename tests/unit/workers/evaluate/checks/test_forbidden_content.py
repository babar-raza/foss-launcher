"""Tests for evaluate.checks.forbidden_content — TC-5152."""
from __future__ import annotations

import pytest

from launcher.workers.evaluate.checks.forbidden_content import check_forbidden_content


class TestCheckForbiddenContent:
    """check_forbidden_content produces correct findings."""

    def test_clean_content_no_findings(self):
        findings = check_forbidden_content("Clean page with no issues.", "test-slug")
        assert findings == []

    def test_identifier_omitted_critical(self):
        content = "Use [identifier omitted] to load files."
        findings = check_forbidden_content(content, "test-slug")
        assert len(findings) >= 1
        critical = [f for f in findings if f.severity == "critical"]
        assert len(critical) >= 1
        assert any("identifier" in f.message.lower() for f in critical)

    def test_claim_id_leak_critical(self):
        content = "CLM-cells-abc123: Supports CSV export."
        findings = check_forbidden_content(content, "test-slug")
        assert len(findings) >= 1
        assert any(f.severity == "critical" for f in findings)

    def test_content_placeholder_critical(self):
        content = "## Overview\n\n[Content to be generated]"
        findings = check_forbidden_content(content, "test-slug")
        assert len(findings) >= 1
        assert any(f.severity == "critical" for f in findings)

    def test_source_comment_high(self):
        content = "Code example:\n# source: snippet_005\nimport foo"
        findings = check_forbidden_content(content, "test-slug")
        assert len(findings) >= 1
        assert any(f.severity == "high" for f in findings)

    def test_finding_has_correct_check_name(self):
        content = "[identifier omitted]"
        findings = check_forbidden_content(content, "test-slug")
        assert all(f.check == "forbidden_content" for f in findings)

    def test_finding_has_correct_location(self):
        content = "[identifier omitted]"
        findings = check_forbidden_content(content, "my-page-slug")
        assert all(f.location == "my-page-slug" for f in findings)

    def test_count_in_message(self):
        content = "[identifier omitted] and [identifier omitted]"
        findings = check_forbidden_content(content, "test-slug")
        id_findings = [f for f in findings if "identifier" in f.message.lower()]
        assert len(id_findings) >= 1
        assert "2 occurrences" in id_findings[0].message

    def test_multiple_pattern_types(self):
        content = (
            "Use [identifier omitted].\n"
            "CLM-cells-abc123: claim.\n"
            "[Content to be generated]\n"
            "# source: snippet_001\n"
        )
        findings = check_forbidden_content(content, "test-slug")
        # Should have at least 4 findings (one per pattern type)
        assert len(findings) >= 4
