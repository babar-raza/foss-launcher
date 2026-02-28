"""Tests for G17-FQ-8: Adjacent same-language fence detection (TC-2892).

Validates that the FQ-8 prelint correctly detects adjacent code fences
with the same language tag separated only by blank lines or HTML comments,
and does NOT fire when prose or headings intervene.
"""

from __future__ import annotations

import pytest
from pathlib import Path

from src.launch.workers.w9_validator.gates.gate_17_prelints import (
    lint_fq8_adjacent_fences,
    run_deterministic_prelints,
)
from src.launch.workers._shared.prelint_fq import detect_adjacent_same_lang_fences


class TestFQ8AdjacentFences:
    """G17-FQ-8: Adjacent same-language fence detection (TC-2892)."""

    def test_adjacent_python_fences_detected(self, tmp_path):
        """Two python fences separated by blank line triggers FQ-8."""
        md = tmp_path / "adj.md"
        md.write_text(
            "# Title\n\n```python\nx = 1\n```\n\n```python\ny = 2\n```\n",
            encoding="utf-8",
        )
        issues = lint_fq8_adjacent_fences(md.read_text(encoding="utf-8"), md)
        assert len(issues) == 1
        assert issues[0]["error_code"] == "G17-FQ-8"
        assert issues[0]["severity"] == "error"
        assert "python" in issues[0]["message"]

    def test_different_languages_clean(self, tmp_path):
        """Python + bash fences should NOT trigger FQ-8."""
        md = tmp_path / "diff.md"
        md.write_text(
            "```python\nx = 1\n```\n\n```bash\npip install foo\n```\n",
            encoding="utf-8",
        )
        issues = lint_fq8_adjacent_fences(md.read_text(encoding="utf-8"), md)
        assert len(issues) == 0

    def test_prose_between_fences_clean(self, tmp_path):
        """Same-language fences separated by prose should NOT trigger FQ-8."""
        md = tmp_path / "prose.md"
        md.write_text(
            "```python\nx = 1\n```\n\nThis explains the next block.\n\n```python\ny = 2\n```\n",
            encoding="utf-8",
        )
        issues = lint_fq8_adjacent_fences(md.read_text(encoding="utf-8"), md)
        assert len(issues) == 0

    def test_heading_between_fences_clean(self, tmp_path):
        """Same-language fences separated by heading should NOT trigger FQ-8."""
        md = tmp_path / "heading.md"
        md.write_text(
            "```python\nx = 1\n```\n\n## Next Section\n\n```python\ny = 2\n```\n",
            encoding="utf-8",
        )
        issues = lint_fq8_adjacent_fences(md.read_text(encoding="utf-8"), md)
        assert len(issues) == 0

    def test_claim_marker_only_triggers(self, tmp_path):
        """HTML claim marker between same-lang fences still triggers (is comment)."""
        md = tmp_path / "claim.md"
        md.write_text(
            "```python\nx = 1\n```\n<!-- claim: abc -->\n```python\ny = 2\n```\n",
            encoding="utf-8",
        )
        issues = lint_fq8_adjacent_fences(md.read_text(encoding="utf-8"), md)
        assert len(issues) == 1
        assert issues[0]["error_code"] == "G17-FQ-8"

    def test_empty_lang_matches(self, tmp_path):
        """Empty-lang fence adjacent to python fence triggers FQ-8."""
        md = tmp_path / "empty.md"
        md.write_text(
            "```python\nx = 1\n```\n\n```\ny = 2\n```\n",
            encoding="utf-8",
        )
        issues = lint_fq8_adjacent_fences(md.read_text(encoding="utf-8"), md)
        assert len(issues) == 1

    def test_integrated_in_run_deterministic(self, tmp_path):
        """FQ-8 is included in run_deterministic_prelints."""
        md = tmp_path / "integrated.md"
        md.write_text(
            "# Title\n\n```python\nx = 1\n```\n\n```python\ny = 2\n```\n",
            encoding="utf-8",
        )
        issues, has_errors = run_deterministic_prelints(md)
        fq8 = [i for i in issues if i["error_code"] == "G17-FQ-8"]
        assert len(fq8) == 1
        # FQ-8 is error (promoted from warn after TC-2892 bake-in), so has_errors is True
        assert has_errors is True

    def test_single_block_clean(self, tmp_path):
        """A single well-formed code block produces no FQ-8."""
        md = tmp_path / "clean.md"
        md.write_text(
            "# Title\n\n```python\nimport os\nprint('hello')\n```\n",
            encoding="utf-8",
        )
        issues = lint_fq8_adjacent_fences(md.read_text(encoding="utf-8"), md)
        assert len(issues) == 0

    def test_multiple_adjacent_pairs_detected(self, tmp_path):
        """Multiple adjacent pairs each produce their own FQ-8 issue."""
        md = tmp_path / "multi.md"
        md.write_text(
            "```python\na = 1\n```\n\n```python\nb = 2\n```\n\n"
            "Some prose text here.\n\n"
            "```bash\necho hi\n```\n\n```bash\necho bye\n```\n",
            encoding="utf-8",
        )
        issues = lint_fq8_adjacent_fences(md.read_text(encoding="utf-8"), md)
        assert len(issues) == 2
        langs = [i["message"] for i in issues]
        assert any("python" in m for m in langs)
        assert any("bash" in m for m in langs)

    def test_directly_adjacent_no_gap(self, tmp_path):
        """Two fences with zero lines between them triggers FQ-8."""
        md = tmp_path / "nospace.md"
        md.write_text(
            "```python\nx = 1\n```\n```python\ny = 2\n```\n",
            encoding="utf-8",
        )
        issues = lint_fq8_adjacent_fences(md.read_text(encoding="utf-8"), md)
        assert len(issues) == 1

    def test_fq8_severity_is_error(self, tmp_path):
        """TC-2892: FQ-8 severity must be error (promoted from warn after bake-in)."""
        md = tmp_path / "sev.md"
        md.write_text(
            "```python\nx = 1\n```\n\n```python\ny = 2\n```\n",
            encoding="utf-8",
        )
        issues = lint_fq8_adjacent_fences(md.read_text(encoding="utf-8"), md)
        assert len(issues) == 1
        assert issues[0]["severity"] == "error", (
            "FQ-8 must be error severity (TC-2892 promotion)"
        )


class TestSharedDetectionFunction:
    """TC-3500: Verify shared detect_adjacent_same_lang_fences() function."""

    def test_shared_detect_returns_correct_tuples(self):
        """Shared function returns (close_lineno, open_lineno, lang) tuples."""
        content = "# Title\n\n```python\nx = 1\n```\n\n```python\ny = 2\n```\n"
        detections = detect_adjacent_same_lang_fences(content)
        assert len(detections) == 1
        close_line, open_line, lang = detections[0]
        assert isinstance(close_line, int)
        assert isinstance(open_line, int)
        assert lang == "python"
        assert open_line > close_line

    def test_gate_17_uses_shared_detection(self, tmp_path):
        """Gate 17 still produces same results after refactor to shared module."""
        content = "```python\na = 1\n```\n\n```python\nb = 2\n```\n"
        md = tmp_path / "shared.md"
        md.write_text(content, encoding="utf-8")

        # Gate 17 result
        gate_issues = lint_fq8_adjacent_fences(content, md)
        # Shared result
        shared_detections = detect_adjacent_same_lang_fences(content)

        # Both should find exactly 1 detection
        assert len(gate_issues) == 1
        assert len(shared_detections) == 1
        # Gate issue should reference same line numbers as shared detection
        close_line, open_line, lang = shared_detections[0]
        assert gate_issues[0]["location"]["line"] == open_line
