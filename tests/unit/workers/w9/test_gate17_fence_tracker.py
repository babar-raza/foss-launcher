"""Tests for TC-3629: gate_17_prelints.py CommonMark fence tracker fix.

Verifies that:
1. A ```python opener inside an open fence does NOT close the fence
   (only bare ``` closes a fence per CommonMark spec).
2. Code lines inside ```python fences are NOT flagged as FQ-1.
3. Genuine code outside any fence IS still flagged.
4. FQ-4 double-heading inside a fence is NOT flagged.
"""

from pathlib import Path
from unittest.mock import MagicMock
from launch.workers.w9_validator.gates.gate_17_prelints import (
    lint_fq1_naked_code,
    lint_fq4_double_heading,
    lint_fq6_claim_comment,
    run_deterministic_prelints,
    _FENCE_CLOSER_RE,
)


# ---------------------------------------------------------------------------
# _FENCE_CLOSER_RE contract
# ---------------------------------------------------------------------------

class TestFenceCloserRe:
    """_FENCE_CLOSER_RE must match bare ``` only."""

    def test_bare_backticks_match(self):
        assert _FENCE_CLOSER_RE.match("```") is not None

    def test_bare_backticks_with_whitespace_match(self):
        assert _FENCE_CLOSER_RE.match("```  ") is not None

    def test_four_backticks_match(self):
        assert _FENCE_CLOSER_RE.match("````") is not None

    def test_python_tag_no_match(self):
        assert _FENCE_CLOSER_RE.match("```python") is None

    def test_bash_tag_no_match(self):
        assert _FENCE_CLOSER_RE.match("```bash") is None

    def test_text_tag_no_match(self):
        assert _FENCE_CLOSER_RE.match("```text") is None


# ---------------------------------------------------------------------------
# FQ-1: Fence-tracking false positives
# ---------------------------------------------------------------------------

class TestFq1FenceTracking:
    """lint_fq1_naked_code must not flag code inside ```python fences."""

    _PATH = Path("test_file.md")

    def test_import_inside_python_fence_not_flagged(self):
        """from X import Y inside ```python...``` must not trigger FQ-1."""
        content = (
            "Some prose.\n"
            "\n"
            "```python\n"
            "from asposecells import Workbook, BorderType\n"
            "wb = Workbook()\n"
            "```\n"
        )
        issues = lint_fq1_naked_code(content, self._PATH)
        assert not issues, f"False positive FQ-1: {issues}"

    def test_import_after_bare_opener_inside_fence(self):
        """Code after bare ``` opener + ```python inside must stay inside fence."""
        content = (
            "```\n"
            "prose inside fence\n"
            "```python\n"
            "from asposecells import Workbook\n"
            "```\n"
        )
        issues = lint_fq1_naked_code(content, self._PATH)
        assert not issues, f"False positive FQ-1 (tutorials.md pattern): {issues}"

    def test_python_fence_inside_bare_fence_not_closer(self):
        """```python inside an open ``` fence does NOT close it; code stays inside."""
        # This matches the tutorials.md bug: bare ``` at line 101, then ```python
        # at line 140, then from ... import at line 141 (inside the still-open fence)
        content = (
            "```\n"
            "```python\n"
            "from asposecells import Workbook, BorderType, BorderLineStyle\n"
            "wb = Workbook()\n"
            "```\n"
        )
        issues = lint_fq1_naked_code(content, self._PATH)
        fq1 = [i for i in issues if i["error_code"] == "G17-FQ-1"]
        assert not fq1, f"False positive: import inside fence flagged as FQ-1: {fq1}"

    def test_code_text_fence_inside_python_fence_not_closer(self):
        """```text inside ```python fence does NOT close it."""
        content = (
            "```python\n"
            "import os\n"
            "```text\n"
            "print('inside')\n"
            "```\n"
        )
        issues = lint_fq1_naked_code(content, self._PATH)
        fq1 = [i for i in issues if i["error_code"] == "G17-FQ-1"]
        assert not fq1, f"print() inside fence falsely flagged: {fq1}"

    def test_genuine_code_outside_fence_still_flagged(self):
        """import statement genuinely outside any fence IS flagged."""
        content = (
            "Some prose.\n"
            "\n"
            "from asposecells import Workbook\n"
            "\n"
            "```python\n"
            "wb = Workbook()\n"
            "```\n"
        )
        issues = lint_fq1_naked_code(content, self._PATH)
        fq1 = [i for i in issues if i["error_code"] == "G17-FQ-1"]
        assert len(fq1) == 1, f"Expected 1 FQ-1 issue, got: {fq1}"
        assert fq1[0]["location"]["line"] == 3

    def test_print_outside_fence_between_blocks_flagged(self):
        """print() between two closed fences IS flagged."""
        content = (
            "```python\n"
            "wb = Workbook()\n"
            "```\n"
            "\n"
            'print("outside")\n'
            "\n"
            "```python\n"
            "wb.save('out.xlsx')\n"
            "```\n"
        )
        issues = lint_fq1_naked_code(content, self._PATH)
        fq1 = [i for i in issues if i["error_code"] == "G17-FQ-1"]
        assert len(fq1) == 1, f"Expected print() to be flagged: {fq1}"
        assert fq1[0]["location"]["line"] == 5

    def test_multiple_info_string_fences_not_false_positives(self):
        """Multiple ```python ... ``` blocks must all work correctly."""
        content = (
            "```python\n"
            "import os\n"
            "```\n"
            "\n"
            "```python\n"
            "from pathlib import Path\n"
            "```\n"
        )
        issues = lint_fq1_naked_code(content, self._PATH)
        assert not issues, f"Unexpected FQ-1 in consecutive fences: {issues}"


# ---------------------------------------------------------------------------
# FQ-4: Heading inside fence not flagged
# ---------------------------------------------------------------------------

class TestFq4FenceTracking:
    """lint_fq4_double_heading must not flag headings inside fences."""

    _PATH = Path("test_file.md")

    def test_heading_inside_python_fence_not_flagged(self):
        """## Heading inside ```python fence must not trigger FQ-4."""
        content = (
            "```python\n"
            "## This looks like a heading but is Python comment-like\n"
            "import os\n"
            "```\n"
        )
        issues = lint_fq4_double_heading(content, self._PATH)
        assert not issues, f"Heading inside fence falsely flagged as FQ-4: {issues}"

    def test_fused_heading_outside_fence_flagged(self):
        """## Overview## Next heading on same line must be flagged as FQ-4."""
        # _DOUBLE_HEADING_RE requires two ## markers on the same line
        content = (
            "## Overview## See Also\n"
        )
        issues = lint_fq4_double_heading(content, self._PATH)
        fq4 = [i for i in issues if i["error_code"] == "G17-FQ-4"]
        assert fq4, "Expected FQ-4 for double heading but none found"


# ---------------------------------------------------------------------------
# FQ-6: Claim comment inside fence not flagged
# ---------------------------------------------------------------------------

class TestFq6FenceTracking:
    """lint_fq6_claim_comment must not flag claim comments inside fences."""

    _PATH = Path("test_file.md")

    def test_claim_comment_inside_python_fence_not_flagged(self):
        """<!-- claim: id --> inside ```python fence must not trigger FQ-6."""
        content = (
            "```python\n"
            "# <!-- claim: abc123 --> this is a code comment\n"
            "import os\n"
            "```\n"
        )
        issues = lint_fq6_claim_comment(content, self._PATH)
        assert not issues, f"Claim comment inside fence falsely flagged: {issues}"
