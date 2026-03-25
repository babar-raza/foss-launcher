"""TC-D-04: Tests for check_content_utility."""
from __future__ import annotations

import pytest

from launcher.workers.evaluate.checks.content_utility import check_content_utility


class TestContentUtility:

    def test_clean_content_passes(self):
        """Content without filler patterns should pass."""
        content = (
            "# Guide\n\n"
            "The Workbook class creates new spreadsheets.\n"
            "Use the save method to write to disk.\n"
            "Charts can be added using the Charts collection.\n"
        )
        findings = check_content_utility(content, "docs/guide")
        assert findings == []

    def test_consecutive_filler_lines_flagged(self):
        """≥3 consecutive lines with same filler prefix should flag MEDIUM."""
        content = (
            "# Features\n\n"
            "The library supports XLSX format for reading and writing.\n"
            "The library supports CSV format for data exchange.\n"
            "The library supports JSON format for web applications.\n"
            "The library supports PDF format for document export.\n"
        )
        findings = check_content_utility(content, "docs/features")
        assert len(findings) >= 1
        assert any(f.severity == "medium" and "copy-paste filler" in f.message.lower() for f in findings)

    def test_non_consecutive_filler_ok(self):
        """Filler lines that are not consecutive should pass."""
        content = (
            "# Features\n\n"
            "The library supports XLSX format.\n"
            "Users find this very helpful for their work.\n"
            "The library supports CSV format.\n"
            "Data scientists prefer this approach.\n"
            "The library supports JSON format.\n"
        )
        findings = check_content_utility(content, "docs/features")
        filler_findings = [f for f in findings if "copy-paste filler" in f.message.lower()]
        assert filler_findings == []

    def test_filler_in_code_blocks_ignored(self):
        """Filler patterns inside code blocks should not be flagged."""
        content = (
            "# Guide\n\n"
            "```python\n"
            "# The library supports XLSX format\n"
            "# The library supports CSV format\n"
            "# The library supports JSON format\n"
            "```\n"
        )
        findings = check_content_utility(content, "docs/guide")
        filler_findings = [f for f in findings if "copy-paste filler" in f.message.lower()]
        assert filler_findings == []

    def test_repetitive_bullets_flagged(self):
        """≥4 consecutive bullets with same prefix should flag MEDIUM."""
        content = (
            "# Features\n\n"
            "- Supports reading XLSX files\n"
            "- Supports reading CSV files\n"
            "- Supports reading JSON files\n"
            "- Supports reading PDF files\n"
            "- Supports reading XML files\n"
        )
        findings = check_content_utility(content, "docs/features")
        bullet_findings = [f for f in findings if "repetitive bullet" in f.message.lower()]
        assert len(bullet_findings) == 1

    def test_varied_bullets_ok(self):
        """Bullets with different prefixes should pass."""
        content = (
            "# Features\n\n"
            "- Read spreadsheet files efficiently\n"
            "- Write to multiple output formats\n"
            "- Create charts and visualizations\n"
            "- Manage formulas and calculations\n"
        )
        findings = check_content_utility(content, "docs/features")
        bullet_findings = [f for f in findings if "repetitive bullet" in f.message.lower()]
        assert bullet_findings == []

    def test_frontmatter_stripped(self):
        """Frontmatter should not trigger filler detection."""
        content = (
            "---\ntitle: Test\nkeywords: [a, b, c]\n---\n"
            "# Content\n\nNormal content here.\n"
        )
        findings = check_content_utility(content, "docs/test")
        assert findings == []
