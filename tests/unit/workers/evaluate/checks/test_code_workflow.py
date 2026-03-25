"""TC-D-04: Tests for check_code_completeness_workflow."""
from __future__ import annotations

import pytest

from launcher.workers.evaluate.checks.code_workflow import check_code_completeness_workflow


class TestCodeCompletenessWorkflow:

    def test_non_code_role_returns_empty(self):
        """Non-code roles should return no findings."""
        content = "# FAQ\nSome text without code."
        findings = check_code_completeness_workflow(content, "kb/faq", page_role="faq")
        assert findings == []

    def test_code_role_no_code_blocks_flags_high(self):
        """Code-required role with no code blocks should flag HIGH."""
        content = "---\ntitle: Guide\n---\n# Getting Started\nJust text, no code."
        findings = check_code_completeness_workflow(content, "docs/getting-started", page_role="getting_started")
        assert len(findings) == 1
        assert findings[0].severity == "high"
        assert "No code blocks" in findings[0].message

    def test_complete_code_block_passes(self):
        """Code block with ≥3 meaningful statements should pass."""
        content = (
            "# Guide\n\n"
            "```python\n"
            "from aspose.cells_foss import Workbook\n"
            "wb = Workbook()\n"
            "ws = wb.worksheets[0]\n"
            "ws.cells.get('A1').put_value('Hello')\n"
            "wb.save('output.xlsx')\n"
            "```\n"
        )
        findings = check_code_completeness_workflow(content, "docs/guide", page_role="howto_article")
        assert findings == []

    def test_stub_code_block_flags_medium(self):
        """Code block with only import + constructor should flag MEDIUM."""
        content = (
            "# Guide\n\n"
            "```python\n"
            "from aspose.cells_foss import Workbook\n"
            "wb = Workbook()\n"
            "```\n"
        )
        findings = check_code_completeness_workflow(content, "docs/guide", page_role="howto_article")
        assert len(findings) == 1
        assert findings[0].severity == "medium"
        assert "fewer than 3" in findings[0].message

    def test_empty_code_block_not_double_counted(self):
        """Empty code blocks are handled by check_empty_code_blocks, not this check."""
        content = (
            "# Guide\n\n"
            "```python\n"
            "\n"
            "```\n"
            "```python\n"
            "from aspose.cells_foss import Workbook\n"
            "wb = Workbook()\n"
            "ws = wb.worksheets[0]\n"
            "ws.cells.get('A1').put_value('Hello')\n"
            "wb.save('output.xlsx')\n"
            "```\n"
        )
        findings = check_code_completeness_workflow(content, "docs/guide", page_role="howto_article")
        # The empty block is skipped; the complete block passes
        assert findings == []

    def test_multiple_stub_blocks_counted(self):
        """Multiple stub blocks should be counted."""
        content = (
            "# Guide\n\n"
            "```python\n"
            "import aspose\n"
            "```\n\n"
            "```python\n"
            "from aspose.cells_foss import Workbook\n"
            "wb = Workbook()\n"
            "```\n"
        )
        findings = check_code_completeness_workflow(content, "docs/guide", page_role="howto_article")
        assert len(findings) == 1
        assert "2 code block(s)" in findings[0].message

    def test_comments_dont_count_as_statements(self):
        """Comment-only lines should not count as meaningful statements."""
        content = (
            "# Guide\n\n"
            "```python\n"
            "# Import the library\n"
            "from aspose.cells_foss import Workbook\n"
            "# Create a new workbook\n"
            "wb = Workbook()\n"
            "# That's it\n"
            "```\n"
        )
        findings = check_code_completeness_workflow(content, "docs/guide", page_role="howto_article")
        # Only 1 meaningful statement (wb = Workbook()), import doesn't count
        assert len(findings) == 1
        assert findings[0].severity == "medium"

    def test_frontmatter_stripped(self):
        """Frontmatter should not interfere with code block detection."""
        content = (
            "---\ntitle: Test\npage_role: howto_article\n---\n"
            "# Guide\n\n"
            "```python\n"
            "wb = Workbook()\n"
            "ws = wb.worksheets[0]\n"
            "ws.cells.get('A1').put_value('Hello')\n"
            "wb.save('output.xlsx')\n"
            "```\n"
        )
        findings = check_code_completeness_workflow(content, "docs/guide", page_role="howto_article")
        assert findings == []
