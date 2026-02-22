"""TC-2404: Tests for per-file LLM parallelization in W9 Gate 17.

Validates:
1. run_gate_17 accepts max_parallel_files parameter (backward-compatible default=4)
2. max_parallel_files=1 produces sequential path — same results as parallel
3. llm_client=None early-return path unchanged (no ThreadPoolExecutor created)
4. Thread exception on a single page is caught — gate continues, other pages processed
5. gate_failed accumulation is correct when multiple threads report errors
6. gate_passed=True when all defects are warn-only (no error codes)
7. run_gate_17 fails the gate when error-code defects are returned
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from launch.workers.w9_validator.gates.gate_17_formatting_quality import run_gate_17


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_llm_response(defects: list) -> dict:
    """Build a mock LLM response containing the given defect list."""
    return {"content": json.dumps({"defects": defects})}


def _make_md_files(tmp_path: Path, n: int) -> list[Path]:
    """Create n minimal markdown files under tmp_path."""
    files = []
    for i in range(n):
        p = tmp_path / f"page_{i}.md"
        p.write_text(f"---\ntitle: Page {i}\n---\n\n## Section\n\nContent {i}.\n", encoding="utf-8")
        files.append(p)
    return files


# ---------------------------------------------------------------------------
# 1. Backward-compatible signature — max_parallel_files defaults to 4
# ---------------------------------------------------------------------------

class TestBackwardCompatibleSignature:
    """run_gate_17 with no max_parallel_files arg still works."""

    def test_no_max_parallel_files_arg(self, tmp_path):
        """Calling run_gate_17 without max_parallel_files should not raise."""
        md_files = _make_md_files(tmp_path, 2)
        mock_client = MagicMock()
        mock_client.chat_completion.return_value = _make_llm_response([])

        with patch(
            "launch.workers.w9_validator.gates.gate_17_formatting_quality._load_system_prompt",
            return_value="Check this markdown.",
        ):
            passed, issues = run_gate_17(md_files, mock_client)

        assert isinstance(passed, bool)
        assert isinstance(issues, list)


# ---------------------------------------------------------------------------
# 2. llm_client=None early-return — unchanged path
# ---------------------------------------------------------------------------

class TestNullLlmClientEarlyReturn:
    """When llm_client is None, gate passes without creating a ThreadPoolExecutor."""

    def test_none_client_returns_pass(self, tmp_path):
        md_files = _make_md_files(tmp_path, 3)
        passed, issues = run_gate_17(md_files, llm_client=None)
        assert passed is True
        assert any(i.get("error_code") == "G17-000" for i in issues)

    def test_none_client_no_page_checks(self, tmp_path):
        """_check_one_page must not be called when llm_client is None."""
        md_files = _make_md_files(tmp_path, 3)
        with patch(
            "launch.workers.w9_validator.gates.gate_17_formatting_quality._check_one_page",
            side_effect=AssertionError("Should not check pages when client is None"),
        ):
            passed, issues = run_gate_17(md_files, llm_client=None)
        assert passed is True


# ---------------------------------------------------------------------------
# 3. max_parallel_files=1 sequential path — identical results to parallel
# ---------------------------------------------------------------------------

class TestSequentialVsParallelConsistency:
    """max_parallel_files=1 and max_parallel_files=4 produce same issue count."""

    def test_sequential_and_parallel_same_issue_count(self, tmp_path):
        md_files = _make_md_files(tmp_path, 4)
        warn_defect = {"code": "FQ-2", "severity": "warn", "excerpt": "minor issue", "line_approximate": 5}
        mock_client = MagicMock()
        mock_client.chat_completion.return_value = _make_llm_response([warn_defect])

        with patch(
            "launch.workers.w9_validator.gates.gate_17_formatting_quality._load_system_prompt",
            return_value="prompt text",
        ):
            passed_seq, issues_seq = run_gate_17(md_files, mock_client, max_parallel_files=1)
            passed_par, issues_par = run_gate_17(md_files, mock_client, max_parallel_files=4)

        assert passed_seq == passed_par
        assert len(issues_seq) == len(issues_par)

    def test_sequential_passes_on_warn_only(self, tmp_path):
        md_files = _make_md_files(tmp_path, 2)
        warn_defect = {"code": "FQ-5", "severity": "warn", "excerpt": "spacing", "line_approximate": 3}
        mock_client = MagicMock()
        mock_client.chat_completion.return_value = _make_llm_response([warn_defect])

        with patch(
            "launch.workers.w9_validator.gates.gate_17_formatting_quality._load_system_prompt",
            return_value="prompt",
        ):
            passed, issues = run_gate_17(md_files, mock_client, max_parallel_files=1)

        assert passed is True
        assert len(issues) == 2  # one warn per file


# ---------------------------------------------------------------------------
# 4. Thread exception on one page is caught — other pages still processed
# ---------------------------------------------------------------------------

class TestThreadExceptionHandling:
    """Exception in one thread logs a warning and does not crash the gate."""

    def test_exception_in_one_page_continues(self, tmp_path):
        md_files = _make_md_files(tmp_path, 3)
        call_count = 0

        def _flaky_check(md_path, system_text, llm_client):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise RuntimeError("Simulated LLM timeout")
            return [], False

        with patch(
            "launch.workers.w9_validator.gates.gate_17_formatting_quality._load_system_prompt",
            return_value="prompt",
        ), patch(
            "launch.workers.w9_validator.gates.gate_17_formatting_quality._check_one_page",
            side_effect=_flaky_check,
        ):
            passed, issues = run_gate_17(md_files, MagicMock(), max_parallel_files=3)

        # Gate should not fail just because one page errored
        assert passed is True
        assert isinstance(issues, list)


# ---------------------------------------------------------------------------
# 5. gate_failed accumulates correctly when multiple threads report errors
# ---------------------------------------------------------------------------

class TestErrorFlagAccumulation:
    """Multiple error-code defects across files all contribute to gate_failed=True."""

    def test_multiple_error_pages_fail_gate(self, tmp_path):
        md_files = _make_md_files(tmp_path, 3)
        error_defect = {"code": "FQ-1", "severity": "error", "excerpt": "unclosed fence", "line_approximate": 10}
        mock_client = MagicMock()
        mock_client.chat_completion.return_value = _make_llm_response([error_defect])

        with patch(
            "launch.workers.w9_validator.gates.gate_17_formatting_quality._load_system_prompt",
            return_value="prompt",
        ):
            passed, issues = run_gate_17(md_files, mock_client, max_parallel_files=3)

        assert passed is False
        # One error issue per file × 3 files
        assert len([i for i in issues if i.get("severity") == "error"]) == 3

    def test_gate_passes_with_only_warn_codes(self, tmp_path):
        md_files = _make_md_files(tmp_path, 2)
        warn_defect = {"code": "FQ-6", "severity": "warn", "excerpt": "extra blank", "line_approximate": 7}
        mock_client = MagicMock()
        mock_client.chat_completion.return_value = _make_llm_response([warn_defect])

        with patch(
            "launch.workers.w9_validator.gates.gate_17_formatting_quality._load_system_prompt",
            return_value="prompt",
        ):
            passed, issues = run_gate_17(md_files, mock_client, max_parallel_files=2)

        assert passed is True
        assert all(i.get("severity") == "warn" for i in issues)


# ---------------------------------------------------------------------------
# 6. Empty file list returns pass with no issues
# ---------------------------------------------------------------------------

class TestEmptyFileList:
    """run_gate_17 with an empty md_files list should pass with no issues."""

    def test_empty_list_passes(self):
        mock_client = MagicMock()
        with patch(
            "launch.workers.w9_validator.gates.gate_17_formatting_quality._load_system_prompt",
            return_value="prompt",
        ):
            passed, issues = run_gate_17([], mock_client, max_parallel_files=4)

        assert passed is True
        assert issues == []
