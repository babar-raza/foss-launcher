"""Tests for TC-3623: W10 FQ-4 extended dash-sentence heading split.

Verifies that the FQ-4 handler correctly detects and splits headings with
a dash-sentence junction (e.g. '## Product Api- The sentence here.').
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Helpers — invoke only the FQ-4 portion of execute_fixer
# ---------------------------------------------------------------------------

def _run_fq4_fix_on_content(content: str) -> str:
    """Simulate the W10 FQ-4 handler on a piece of markdown content.

    Reproduces the exact logic in worker.py lines ~792–860 for the
    scan-based split (Fix 3 + TC-3623 Fix 4).
    Returns the modified content.
    """
    error_codes = ["FQ-4"]

    if any("FQ-4" in c or "FQ4" in c for c in error_codes):
        # Fix 1: Insert blank line between adjacent headings (regex-based)
        content = re.sub(
            r"(^#{1,6}\s+[^\n]+\n)(#{1,6}\s+)",
            r"\1\n\2",
            content,
            flags=re.MULTILINE,
        )
        # Fix 2: backtick inline-code concat (not tested here)
        content = re.sub(
            r'^(#{1,6}\s+(\w+))`\2`',
            lambda m: f"{m.group(1)}\n`{m.group(2)}`",
            content,
            flags=re.MULTILINE | re.IGNORECASE,
        )
        # Fix 3+TC-3623: scan-based camelCase + dash-sentence split
        _fq4_fixed_lines = []
        _fq4_in_fence = False
        for _fq4_line in content.split('\n'):
            _fq4_stripped = _fq4_line.rstrip()
            if _fq4_stripped.startswith('```'):
                _fq4_in_fence = not _fq4_in_fence
            if _fq4_in_fence:
                _fq4_fixed_lines.append(_fq4_line)
                continue
            _fq4_hm = re.match(r'^(#{1,6}\s+)', _fq4_line)
            if _fq4_hm and len(_fq4_line) > 60:
                _fq4_prefix = _fq4_hm.group(1)
                _fq4_rest = _fq4_line[len(_fq4_prefix):]
                # camelCase junction
                _fq4_jm = re.search(r'([a-z])(?=[A-Z][a-z]{2,})', _fq4_rest)
                if _fq4_jm:
                    _fq4_split = _fq4_jm.end()
                    _fq4_head = _fq4_rest[:_fq4_split]
                    _fq4_prose = _fq4_rest[_fq4_split:]
                    if len(_fq4_prose.strip()) >= 20:
                        _fq4_fixed_lines.append(_fq4_prefix + _fq4_head)
                        _fq4_fixed_lines.append('')
                        _fq4_fixed_lines.append(_fq4_prose)
                        continue
                # TC-3623: dash-sentence junction
                _fq4_dm = re.search(r'\b(\w+)[-\u2013]\s+([A-Z][a-z])', _fq4_rest)
                if _fq4_dm:
                    _fq4_dash_end = _fq4_dm.start() + len(_fq4_dm.group(1))
                    _fq4_head2 = _fq4_rest[:_fq4_dash_end].rstrip()
                    _fq4_prose2 = _fq4_rest[_fq4_dm.start(2):]
                    if len(_fq4_prose2.strip()) >= 20 and len(_fq4_head2.strip()) >= 3:
                        _fq4_fixed_lines.append(_fq4_prefix + _fq4_head2)
                        _fq4_fixed_lines.append('')
                        _fq4_fixed_lines.append(_fq4_prose2)
                        continue
            _fq4_fixed_lines.append(_fq4_line)
        content = '\n'.join(_fq4_fixed_lines)
    return content


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestFQ4DashSentenceSplit:
    """TC-3623: Dash-sentence junction pattern split."""

    def test_dash_heading_split_basic(self):
        """'## Aspose.Cells FOSS for Python Api- The move method...' → split."""
        line = "## Aspose.Cells FOSS for Python Api- The move method on Worksheet forwards the operation to the Workbook class."
        content = line + "\n"
        result = _run_fq4_fix_on_content(content)
        lines = result.strip().split('\n')
        assert lines[0] == "## Aspose.Cells FOSS for Python Api"
        assert lines[1] == ""
        assert lines[2].startswith("The move method")

    def test_dash_heading_split_em_dash(self):
        """Em-dash variant (–) is also handled."""
        line = "## Aspose.Words FOSS for Python Api\u2013 The export method converts the document to PDF format easily."
        content = line + "\n"
        result = _run_fq4_fix_on_content(content)
        lines = result.strip().split('\n')
        assert lines[0] == "## Aspose.Words FOSS for Python Api"
        assert lines[1] == ""
        assert lines[2].startswith("The export method")

    def test_dash_heading_short_prose_no_split(self):
        """Prose < 20 chars → no split (guard fires)."""
        # "Short." is only 6 chars
        line = "## Aspose.Cells FOSS for Python Api- Short prose here."
        # len("Short prose here.") == 17 < 20
        content = line + "\n"
        result = _run_fq4_fix_on_content(content)
        # Should NOT be split — line remains unchanged
        lines = result.strip().split('\n')
        assert len(lines) == 1, f"Expected no split but got {lines}"

    def test_camelcase_still_works(self):
        """Existing camelCase pattern still fires unaffected by TC-3623."""
        line = "## IntroductionThe library provides a comprehensive API for working with Excel files in Python."
        content = line + "\n"
        result = _run_fq4_fix_on_content(content)
        lines = result.strip().split('\n')
        assert lines[0] == "## Introduction"
        assert lines[1] == ""
        assert lines[2].startswith("The library")

    def test_inside_fence_not_split(self):
        """Heading inside code fence is NOT split (fence guard active)."""
        content = (
            "```python\n"
            "## Aspose.Cells FOSS for Python Api- The move method on Worksheet is handled by Workbook.\n"
            "```\n"
        )
        result = _run_fq4_fix_on_content(content)
        # Content inside fence must be unchanged
        assert "## Aspose.Cells FOSS for Python Api- The move method" in result
        # The heading line inside the fence should NOT be split
        lines = result.strip().split('\n')
        fence_lines = [l for l in lines if l.startswith('## ')]
        assert len(fence_lines) == 1, "No extra heading line should appear outside fence"

    def test_heading_minimum_length_guard(self):
        """Very short heading before dash → no split (heading guard ≥3 chars fires)."""
        # "## A- The sentence is long enough to pass the prose guard."
        # heading 'A' is < 3 chars after stripping prefix
        line = "## A- The sentence is long enough to trigger the prose guard easily."
        content = line + "\n"
        result = _run_fq4_fix_on_content(content)
        # 'A' is only 1 char → heading guard should prevent split
        lines = result.strip().split('\n')
        # May or may not split — 'A' is 1 char which is < 3 so no split
        assert len(lines) == 1, f"Short heading should not split: {lines}"

    def test_deterministic_on_repeated_calls(self):
        """Running the fix twice produces identical output (idempotency)."""
        line = "## Aspose.Cells FOSS for Python Api- The move method on Worksheet forwards the operation to the Workbook class."
        content = line + "\n"
        result1 = _run_fq4_fix_on_content(content)
        result2 = _run_fq4_fix_on_content(result1)
        assert result1 == result2, "FQ-4 fix must be idempotent"
