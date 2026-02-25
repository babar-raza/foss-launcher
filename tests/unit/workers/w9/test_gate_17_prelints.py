"""Tests for gate_17_prelints (TC-2475).

Validates deterministic pre-lint detection for FQ-1/2/4/5/6 defect codes.
"""

from __future__ import annotations

import pytest
from pathlib import Path

from src.launch.workers.w9_validator.gates.gate_17_prelints import (
    lint_fq1_naked_code,
    lint_fq2_faq_concat,
    lint_fq4_double_heading,
    lint_fq5_keyword_colon,
    lint_fq6_claim_comment,
    run_deterministic_prelints,
)


class TestFQ1NakedCode:
    def test_fq1_naked_code_detected(self, tmp_path):
        """Code outside a fence should trigger G17-FQ-1."""
        md = tmp_path / "page.md"
        md.write_text("# Title\n\nimport os\n\nSome text.\n", encoding="utf-8")
        issues, has_errors = run_deterministic_prelints(md)
        fq1 = [i for i in issues if i["error_code"] == "G17-FQ-1"]
        assert len(fq1) >= 1
        assert has_errors is True
        assert "import os" in fq1[0]["message"]

    def test_fq1_code_inside_fence_clean(self, tmp_path):
        """Code inside a fence should NOT trigger FQ-1."""
        md = tmp_path / "clean.md"
        md.write_text(
            "# Title\n\n```python\nimport os\n```\n\nSome text.\n",
            encoding="utf-8",
        )
        issues, has_errors = run_deterministic_prelints(md)
        fq1 = [i for i in issues if i["error_code"] == "G17-FQ-1"]
        assert len(fq1) == 0


class TestFQ2FAQConcat:
    def test_fq2_faq_concat_detected(self, tmp_path):
        """Answer text immediately before ### Q: should trigger G17-FQ-2."""
        md = tmp_path / "faq.md"
        md.write_text(
            "# FAQ\n\nSome answer text.### Q: Next question?\n",
            encoding="utf-8",
        )
        issues = lint_fq2_faq_concat(md.read_text(encoding="utf-8"), md)
        assert len(issues) >= 1
        assert issues[0]["error_code"] == "G17-FQ-2"
        assert issues[0]["severity"] == "warn"


class TestFQ4DoubleHeading:
    def test_fq4_double_heading_detected(self, tmp_path):
        """Two headings on one line should trigger G17-FQ-4."""
        md = tmp_path / "double.md"
        md.write_text("## Title## Another\n\nBody text.\n", encoding="utf-8")
        issues, has_errors = run_deterministic_prelints(md)
        fq4 = [i for i in issues if i["error_code"] == "G17-FQ-4"]
        assert len(fq4) >= 1
        assert has_errors is True
        assert fq4[0]["severity"] == "error"


class TestFQ5KeywordColon:
    def test_fq5_keyword_colon_detected(self, tmp_path):
        """Colons inside frontmatter keywords should trigger G17-FQ-5."""
        md = tmp_path / "keywords.md"
        md.write_text(
            '---\ntitle: Test\nkeywords: ["deep:dive", "clean"]\n---\n\nBody.\n',
            encoding="utf-8",
        )
        issues = lint_fq5_keyword_colon(md.read_text(encoding="utf-8"), md)
        assert len(issues) >= 1
        assert issues[0]["error_code"] == "G17-FQ-5"
        assert issues[0]["severity"] == "warn"


class TestFQ6ClaimComment:
    def test_fq6_claim_comment_detected(self, tmp_path):
        """Claim comment markers in body should trigger G17-FQ-6."""
        md = tmp_path / "claims.md"
        md.write_text(
            "# Title\n\n<!-- claim: abc123 -->\n\nBody text.\n",
            encoding="utf-8",
        )
        issues = lint_fq6_claim_comment(md.read_text(encoding="utf-8"), md)
        assert len(issues) >= 1
        assert issues[0]["error_code"] == "G17-FQ-6"
        assert issues[0]["severity"] == "warn"

    def test_fq6_claim_in_fence_clean(self, tmp_path):
        """Claim comment inside a fence should NOT trigger FQ-6."""
        md = tmp_path / "fenced.md"
        md.write_text(
            "# Title\n\n```html\n<!-- claim: abc123 -->\n```\n\nBody.\n",
            encoding="utf-8",
        )
        issues = lint_fq6_claim_comment(md.read_text(encoding="utf-8"), md)
        assert len(issues) == 0


class TestCleanFile:
    def test_clean_file_no_issues(self, tmp_path):
        """A valid markdown file with code in fences should produce no issues."""
        md = tmp_path / "pristine.md"
        md.write_text(
            "---\ntitle: Clean Page\nkeywords: [\"python\", \"api\"]\n---\n\n"
            "# Getting Started\n\n"
            "This library helps you work with documents.\n\n"
            "```python\nimport aspose\nprint(aspose.version)\n```\n\n"
            "## Next Steps\n\n"
            "See the API reference for details.\n",
            encoding="utf-8",
        )
        issues, has_errors = run_deterministic_prelints(md)
        assert issues == []
        assert has_errors is False
