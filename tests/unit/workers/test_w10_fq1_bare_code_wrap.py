"""Tests for TC-3626: W10 FQ-1 bare code block wrapper.

Verifies that _wrap_bare_code_blocks() correctly wraps Python code
that appears outside code fences in ``` python ... ``` fences.
"""

import pytest
from launch.workers.w10_fixer.worker import _wrap_bare_code_blocks


class TestSingleBareImport:
    """Single bare import statement gets wrapped."""

    def test_single_import_wrapped(self):
        content = "Some prose.\n\nfrom aspose.cells import Workbook\n\nMore prose."
        result = _wrap_bare_code_blocks(content, {3})
        assert "```python\nfrom aspose.cells import Workbook\n```" in result

    def test_single_print_wrapped(self):
        content = "Some prose.\n\nprint('Hello, World!')\n\nMore prose."
        result = _wrap_bare_code_blocks(content, {3})
        assert "```python\nprint('Hello, World!')\n```" in result

    def test_prose_preserved(self):
        content = "Before\n\nfrom aspose import X\n\nAfter"
        result = _wrap_bare_code_blocks(content, {3})
        assert "Before" in result
        assert "After" in result


class TestForwardExtension:
    """Forward context extension includes subsequent assignment and method-call lines."""

    def test_forward_extension_includes_assignment(self):
        content = "Prose.\n\nfrom aspose.cells import Workbook\nwb = Workbook()\n\nProse."
        result = _wrap_bare_code_blocks(content, {3})
        assert "```python\nfrom aspose.cells import Workbook\nwb = Workbook()\n```" in result

    def test_forward_extension_includes_method_call(self):
        content = "Prose.\n\nfrom aspose.cells import Workbook\nwb.save('output.xlsx')\n\nProse."
        result = _wrap_bare_code_blocks(content, {3})
        assert "```python\nfrom aspose.cells import Workbook\nwb.save('output.xlsx')\n```" in result

    def test_forward_stops_at_fence(self):
        content = "Prose.\n\nfrom aspose import X\n```python\nalready_in_fence()\n```\n"
        result = _wrap_bare_code_blocks(content, {3})
        # Should wrap just the import, not eat the existing fence
        assert "```python\nfrom aspose import X\n```" in result
        assert result.count("```python") == 2  # new wrapper + existing fence

    def test_forward_stops_at_prose(self):
        content = "Prose.\n\nfrom aspose import X\nThis is prose text.\n\nEnd."
        result = _wrap_bare_code_blocks(content, {3})
        # Only the import is wrapped, not the prose line
        assert "```python\nfrom aspose import X\n```" in result
        assert "This is prose text." in result


class TestBackwardExtension:
    """Backward context extension includes preceding assignment/method-call lines."""

    def test_backward_extension_from_print(self):
        content = "Prose.\n\nwb = Workbook()\nwb.save('out.xlsx')\nprint('Done!')\n\nEnd."
        result = _wrap_bare_code_blocks(content, {5})  # print is line 5
        # Should include all three code lines
        fence_block = "```python\nwb = Workbook()\nwb.save('out.xlsx')\nprint('Done!')\n```"
        assert fence_block in result

    def test_backward_stops_at_heading(self):
        content = "## Heading\n\nprint('code')\n\nEnd."
        result = _wrap_bare_code_blocks(content, {3})
        assert "## Heading" in result
        assert "```python\nprint('code')\n```" in result

    def test_backward_stops_at_prose_paragraph(self):
        content = "This is prose text.\nprint('code')\n\nEnd."
        result = _wrap_bare_code_blocks(content, {2})
        assert "This is prose text." in result
        assert "```python\nprint('code')\n```" in result


class TestIdempotence:
    """Lines already inside fences are not double-wrapped."""

    def test_already_in_fence_skipped(self):
        content = "Prose.\n\n```python\nfrom aspose import X\n```\n\nEnd."
        result = _wrap_bare_code_blocks(content, {4})  # line 4 is inside fence
        # Should be unchanged — only 1 fence pair
        assert result.count("```python") == 1
        assert result == content

    def test_no_bare_lines_unchanged(self):
        content = "Prose.\n\n```python\nwb = Workbook()\n```\n"
        result = _wrap_bare_code_blocks(content, set())
        assert result == content


class TestTwoSeparateBlocks:
    """Two separate code groups each get their own fence."""

    def test_two_imports_separate_fences(self):
        content = (
            "Section A.\n\n"
            "from aspose.cells import Workbook\n\n"
            "Between sections.\n\n"
            "from aspose.cells import Worksheet\n\n"
            "End."
        )
        result = _wrap_bare_code_blocks(content, {3, 7})
        assert result.count("```python") == 2
        assert "```python\nfrom aspose.cells import Workbook\n```" in result
        assert "```python\nfrom aspose.cells import Worksheet\n```" in result
        assert "Between sections." in result

    def test_two_blocks_in_troubleshooting_pattern(self):
        """Simulates the troubleshooting.md pattern with two separate code blocks."""
        content = (
            "Prose intro.\n\n"
            "from asposecells import Workbook\n"
            "ws = wb.worksheets[0]\n"
            "print('Conditional format persisted successfully.')\n\n"
            "Section break.\n\n"
            "from asposecells import Workbook\n"
            "result = wb.cells['A1'].value\n\n"
            "End."
        )
        # FQ-1 detects lines 3 and 9 (import statements — line 8 is blank)
        result = _wrap_bare_code_blocks(content, {3, 9})
        assert result.count("```python") == 2
        assert "Section break." in result


class TestBlankLineHandling:
    """Blank lines within a code block are kept inside the fence."""

    def test_blank_line_between_code_included(self):
        content = "Prose.\n\nfrom aspose import X\n\nwb = Workbook()\n\nEnd."
        result = _wrap_bare_code_blocks(content, {3})
        # The blank line between import and assignment should stay inside the fence
        assert "```python\nfrom aspose import X\n\nwb = Workbook()\n```" in result


class TestFrontmatterProtection:
    """Frontmatter YAML is never wrapped."""

    def test_frontmatter_not_wrapped(self):
        content = (
            "---\n"
            "title: Test\n"
            "layout: docs\n"
            "---\n\n"
            "from aspose import X\n\n"
            "End."
        )
        result = _wrap_bare_code_blocks(content, {6})
        # Frontmatter intact
        assert "---\ntitle: Test\nlayout: docs\n---" in result
        # Code wrapped
        assert "```python\nfrom aspose import X\n```" in result
