"""Tests for TC-3617 B3: W10 sibling-issue batch fix.

Verifies that fix_formatting_defect() and fix_kb_howto_structure() collect
all sibling issues from validation_report.json and fix them in one pass.
"""
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from launch.workers.w10_fixer import worker as w10_worker
from launch.workers.w10_fixer.worker import (
    fix_formatting_defect,
    fix_kb_howto_structure,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_validation_report(run_dir, issues):
    """Write a minimal validation_report.json with given issues."""
    artifacts = run_dir / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    report = {
        "gates": [],
        "issues": issues,
        "generation_id": "test-gen-id",
        "content_hash": "test-hash",
    }
    (artifacts / "validation_report.json").write_text(
        json.dumps(report), encoding="utf-8",
    )


def _make_formatting_issue(error_code, file_path, line=1):
    """Build a formatting issue dict."""
    return {
        "issue_id": f"issue-{error_code}",
        "gate": "gate_17_formatting_quality",
        "error_code": error_code,
        "severity": "error",
        "message": f"Formatting defect {error_code}",
        "location": {"path": str(file_path), "line": line},
        "files": [str(file_path)],
    }


def _make_howto_issue(heading, file_path, slug="test-slug"):
    """Build a howto structure issue dict."""
    return {
        "issue_id": f"gate_kb_howto_structure_heading_order_{slug}",
        "gate": "gate_kb_howto_structure",
        "error_code": "GATE_KB_HOWTO_STRUCTURE_HEADING_ORDER",
        "severity": "error",
        "message": f"Heading '{heading}' missing in draft '{slug}'",
        "location": {"path": str(file_path), "line": 1},
        "files": [str(file_path)],
    }


# ---------------------------------------------------------------------------
# Tests: Formatting batch fix
# ---------------------------------------------------------------------------


class TestFormattingBatchFix:
    """TC-3617 B3: fix_formatting_defect batch tests."""

    def test_formatting_uses_one_llm_call_for_same_file_batch(self, tmp_path):
        """LLM path should fix all same-file formatting siblings in one call and one write."""
        run_dir = tmp_path / "run"
        run_dir.mkdir()

        file_path = run_dir / "test.md"
        file_path.write_text("## Heading1\n## Heading2\n\n```\ncode here\n```\n", encoding="utf-8")
        _write_validation_report(run_dir, [
            _make_formatting_issue("G17-FQ-4", file_path),
            _make_formatting_issue("G17-FQ-1", file_path),
        ])

        mock_llm = MagicMock()
        corrected = "## Heading1\n\n## Heading2\n\n```text\ncode here\n```\n"
        mock_llm.chat_completion.return_value = {"content": corrected}

        with patch(
            "launch.workers.w10_fixer.worker._write_text_atomic",
            wraps=w10_worker._write_text_atomic,
        ) as write_atomic:
            result = fix_formatting_defect(
                _make_formatting_issue("G17-FQ-4", file_path),
                run_dir,
                mock_llm,
            )

        assert result["fixed"] is True
        mock_llm.chat_completion.assert_called_once()
        assert write_atomic.call_count == 1
        assert file_path.read_text(encoding="utf-8") == corrected
        prompt = mock_llm.chat_completion.call_args.kwargs["messages"][0]["content"]
        assert "G17-FQ-4" in prompt
        assert "G17-FQ-1" in prompt

    def test_formatting_fixes_all_sibling_fq_codes(self, tmp_path):
        """Multiple FQ codes on same file should all be fixed in one call."""
        run_dir = tmp_path / "run"
        run_dir.mkdir()

        # Create a file with multiple formatting issues:
        # FQ-1: bare code block (no lang tag)
        # FQ-4: adjacent headings without blank line
        content = "## Heading1\n## Heading2\n\n```\ncode here\n```\n"
        file_path = run_dir / "test.md"
        file_path.write_text(content, encoding="utf-8")

        # Write validation_report with both issues
        _write_validation_report(run_dir, [
            _make_formatting_issue("G17-FQ-4", file_path),
            _make_formatting_issue("G17-FQ-1", file_path),
        ])

        # Call with FQ-4 as primary — should also fix FQ-1
        primary_issue = _make_formatting_issue("G17-FQ-4", file_path)
        result = fix_formatting_defect(primary_issue, run_dir, None)

        assert result["fixed"] is True
        fixed_content = file_path.read_text(encoding="utf-8")
        # FQ-4: blank line between headings
        assert "## Heading1\n\n## Heading2" in fixed_content
        # FQ-1: bare ``` → ```text
        assert "```text" in fixed_content

    def test_formatting_single_issue_when_report_missing(self, tmp_path):
        """No validation_report → graceful degradation, only primary issue."""
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        # No artifacts/validation_report.json

        content = "## Heading1\n## Heading2\n"
        file_path = run_dir / "test.md"
        file_path.write_text(content, encoding="utf-8")

        primary_issue = _make_formatting_issue("G17-FQ-4", file_path)
        result = fix_formatting_defect(primary_issue, run_dir, None)

        assert result["fixed"] is True
        fixed_content = file_path.read_text(encoding="utf-8")
        assert "## Heading1\n\n## Heading2" in fixed_content

    def test_batch_fix_ignores_other_files(self, tmp_path):
        """Sibling issues on different files should NOT be batched."""
        run_dir = tmp_path / "run"
        run_dir.mkdir()

        file_a = run_dir / "a.md"
        file_a.write_text("## H1\n## H2\n", encoding="utf-8")

        file_b = run_dir / "b.md"
        file_b.write_text("```\ncode\n```\n", encoding="utf-8")

        _write_validation_report(run_dir, [
            _make_formatting_issue("G17-FQ-4", file_a),
            _make_formatting_issue("G17-FQ-1", file_b),  # Different file
        ])

        # Fix FQ-4 on file_a — should NOT touch file_b
        primary_issue = _make_formatting_issue("G17-FQ-4", file_a)
        result = fix_formatting_defect(primary_issue, run_dir, None)

        assert result["fixed"] is True
        # file_b should be unchanged (bare ``` still there)
        b_content = file_b.read_text(encoding="utf-8")
        assert "```text" not in b_content


# ---------------------------------------------------------------------------
# Tests: Howto batch fix
# ---------------------------------------------------------------------------


class TestHowtoBatchFix:
    """TC-3617 B3: fix_kb_howto_structure batch tests."""

    def test_howto_uses_one_llm_call_for_same_file_batch(self, tmp_path):
        """LLM path should fix all same-file KB howto siblings in one call and one write."""
        run_dir = tmp_path / "run"
        (run_dir / "artifacts").mkdir(parents=True)
        kb_dir = run_dir / "drafts" / "kb"
        kb_dir.mkdir(parents=True)

        slug = "test-slug"
        file_path = kb_dir / f"{slug}.md"
        file_path.write_text("---\ntitle: Test\n---\n\n## Steps\n\n1. Do something.\n", encoding="utf-8")
        _write_validation_report(run_dir, [
            _make_howto_issue("Goal", file_path, slug),
            _make_howto_issue("Prerequisites", file_path, slug),
            _make_howto_issue("Code Example", file_path, slug),
        ])

        corrected = (
            "---\ntitle: Test\n---\n\n"
            "## Goal\n\nLearn how to accomplish this task step by step.\n\n"
            "## Prerequisites\n\n- Python 3.8+\n\n"
            "## Steps\n\n1. Do something.\n\n"
            "## Code Example\n\n```python\npass\n```\n"
        )
        mock_llm = MagicMock()
        mock_llm.chat_completion.return_value = {"content": corrected}

        with patch(
            "launch.workers.w10_fixer.worker._write_text_atomic",
            wraps=w10_worker._write_text_atomic,
        ) as write_atomic:
            result = fix_kb_howto_structure(
                _make_howto_issue("Goal", file_path, slug),
                run_dir,
                mock_llm,
            )

        assert result["fixed"] is True
        mock_llm.chat_completion.assert_called_once()
        assert write_atomic.call_count == 1
        assert file_path.read_text(encoding="utf-8") == corrected
        prompt = mock_llm.chat_completion.call_args.kwargs["messages"][0]["content"]
        assert "Heading 'Goal' missing" in prompt
        assert "Heading 'Prerequisites' missing" in prompt

    def test_howto_injects_all_missing_headings(self, tmp_path):
        """Multiple missing headings should all be injected in one call."""
        run_dir = tmp_path / "run"
        (run_dir / "artifacts").mkdir(parents=True)
        kb_dir = run_dir / "drafts" / "kb"
        kb_dir.mkdir(parents=True)

        # Create a KB file missing goal, prerequisites, and code example
        content = "---\ntitle: Test\n---\n\n## Steps\n\n1. Do something.\n\n## See Also\n\n- [Link](https://example.com)\n"
        slug = "test-slug"
        file_path = kb_dir / f"{slug}.md"
        file_path.write_text(content, encoding="utf-8")

        # Write validation_report with 3 missing heading issues
        _write_validation_report(run_dir, [
            _make_howto_issue("Goal", file_path, slug),
            _make_howto_issue("Prerequisites", file_path, slug),
            _make_howto_issue("Code Example", file_path, slug),
        ])

        # Call with "Goal" as primary
        primary_issue = _make_howto_issue("Goal", file_path, slug)
        result = fix_kb_howto_structure(primary_issue, run_dir, None)

        assert result["fixed"] is True
        fixed_content = file_path.read_text(encoding="utf-8")
        # All 3 missing headings should be injected
        assert "## Goal" in fixed_content
        assert "## Prerequisites" in fixed_content
        assert "## Code Example" in fixed_content

    def test_howto_single_heading_when_report_missing(self, tmp_path):
        """No validation_report → graceful degradation, only primary heading."""
        run_dir = tmp_path / "run"
        # No artifacts dir → no validation_report
        kb_dir = run_dir / "drafts" / "kb"
        kb_dir.mkdir(parents=True)

        content = "---\ntitle: Test\n---\n\n## Steps\n\n1. Do something.\n\n## See Also\n\n- [Link](https://example.com)\n"
        slug = "test-slug"
        file_path = kb_dir / f"{slug}.md"
        file_path.write_text(content, encoding="utf-8")

        primary_issue = _make_howto_issue("Goal", file_path, slug)
        result = fix_kb_howto_structure(primary_issue, run_dir, None)

        assert result["fixed"] is True
        fixed_content = file_path.read_text(encoding="utf-8")
        assert "## Goal" in fixed_content
        # Prerequisites NOT injected (not in primary issue, no report to discover it)
        assert "## Prerequisites" not in fixed_content
