"""Tests for TC-3530: Gate17 FQ-7b demotion correctness.

Verifies:
- _ERROR_CODES does NOT contain "FQ-7" (TC-3530 fix)
- FQ-7 from LLM Phase 2 (_check_one_page) -> always warn, gate passes
- FQ-7a from Phase 1 prelints -> error, gate fails
- Various co-occurrence scenarios (FQ-7 + FQ-1, etc.)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

from src.launch.workers.w9_validator.gates.gate_17_formatting_quality import (
    _ERROR_CODES,
    _check_one_page,
    run_gate_17,
)


# ── _ERROR_CODES set tests ─────────────────────────────────────────────────────


class TestErrorCodesSet:
    """TC-3530: verify that _ERROR_CODES no longer contains 'FQ-7'."""

    def test_fq7_not_in_error_codes(self):
        """FQ-7 must NOT be in _ERROR_CODES.

        FQ-7b is always demoted by _check_one_page(). FQ-7a (prelint)
        is handled by run_deterministic_prelints() which has its own
        _ERROR_CODES set containing 'G17-FQ-7a'. Including raw 'FQ-7'
        here is dead/misleading code that TC-3530 removes.
        """
        assert "FQ-7" not in _ERROR_CODES, (
            "FQ-7 must not be in _ERROR_CODES. FQ-7b is always warn (LLM Phase 2). "
            "FQ-7a (prelint) returns has_errors directly — it does not go through _ERROR_CODES."
        )

    def test_fq1_in_error_codes(self):
        """FQ-1 (naked code) must remain a gate-failing error code."""
        assert "FQ-1" in _ERROR_CODES

    def test_fq3_in_error_codes(self):
        """FQ-3 (truncated content) must remain a gate-failing error code."""
        assert "FQ-3" in _ERROR_CODES

    def test_fq4_in_error_codes(self):
        """FQ-4 (double heading) must remain a gate-failing error code."""
        assert "FQ-4" in _ERROR_CODES

    def test_error_codes_exact_set(self):
        """_ERROR_CODES must contain exactly FQ-1, FQ-3, FQ-4 (no FQ-7)."""
        assert _ERROR_CODES == frozenset({"FQ-1", "FQ-3", "FQ-4"})


# ── _check_one_page FQ-7 demotion ─────────────────────────────────────────────


class TestCheckOnePageFQ7Demotion:
    """FQ-7 from LLM Phase 2 must always be demoted to warn."""

    @staticmethod
    def _make_llm_response(defects: List[Dict]) -> Dict:
        return {"content": json.dumps({"defects": defects})}

    def test_fq7_from_llm_always_warn(self, tmp_path):
        """LLM returns FQ-7 with severity=error -> gate still passes (demoted to warn)."""
        md_file = tmp_path / "page.md"
        md_file.write_text("# Title\n\nContent.\n", encoding="utf-8")

        llm_client = MagicMock()
        llm_client.chat_completion.return_value = self._make_llm_response([
            {"code": "FQ-7", "severity": "error", "excerpt": "Bad flow.", "line_approximate": 5}
        ])

        issues, has_errors = _check_one_page(md_file, "system prompt", llm_client)

        assert not has_errors, "FQ-7b must NOT set has_errors"
        fq7_issues = [i for i in issues if "FQ-7" in i.get("error_code", "")]
        assert len(fq7_issues) == 1
        assert fq7_issues[0]["severity"] == "warn", (
            f"FQ-7b severity must be warn, got {fq7_issues[0]['severity']}"
        )

    def test_fq7_gate_still_passes_when_only_fq7_issues(self, tmp_path):
        """Gate17 passes when only FQ-7b issues exist (all warn)."""
        md_file = tmp_path / "page.md"
        md_file.write_text("# Title\n\nContent.\n", encoding="utf-8")

        llm_client = MagicMock()
        llm_client.chat_completion.return_value = self._make_llm_response([
            {"code": "FQ-7", "severity": "error", "excerpt": "Narrative issues.", "line_approximate": 3}
        ])

        with patch(
            "src.launch.workers.w9_validator.gates.gate_17_formatting_quality.run_deterministic_prelints"
        ) as mock_prelint:
            mock_prelint.return_value = ([], False)  # Phase 1: no issues
            gate_passed, issues = run_gate_17([md_file], llm_client)

        assert gate_passed, "Gate17 must pass when only FQ-7b issues exist"
        fq7_issues = [i for i in issues if "FQ-7" in i.get("error_code", "")]
        for issue in fq7_issues:
            assert issue["severity"] == "warn"

    def test_fq7_with_retries_exhausted_returns_no_errors(self, tmp_path):
        """When LLM JSON parse fails on all retries, no errors are returned."""
        md_file = tmp_path / "page.md"
        md_file.write_text("# Title\n\nContent.\n", encoding="utf-8")

        llm_client = MagicMock()
        # Return invalid JSON on all attempts
        llm_client.chat_completion.return_value = {"content": "NOT VALID JSON {{{"}

        issues, has_errors = _check_one_page(md_file, "system prompt", llm_client)

        # When parse fails, returns empty with no errors (parsed=None path)
        assert not has_errors
        assert issues == []

    def test_fq1_from_llm_causes_gate_failure(self, tmp_path):
        """FQ-1 from LLM must still cause gate failure (not demoted like FQ-7)."""
        md_file = tmp_path / "page.md"
        md_file.write_text("# Title\n\nContent.\n", encoding="utf-8")

        llm_client = MagicMock()
        llm_client.chat_completion.return_value = self._make_llm_response([
            {"code": "FQ-1", "severity": "error", "excerpt": "Code outside fence.", "line_approximate": 2}
        ])

        issues, has_errors = _check_one_page(md_file, "system prompt", llm_client)

        assert has_errors, "FQ-1 must set has_errors"
        fq1_issues = [i for i in issues if "FQ-1" in i.get("error_code", "")]
        assert len(fq1_issues) == 1
        assert fq1_issues[0]["severity"] == "error"

    def test_fq7_and_fq1_together_gate_fails_but_fq7_still_warn(self, tmp_path):
        """When page has FQ-1 + FQ-7, gate fails (FQ-1) but FQ-7 issue is still warn."""
        md_file = tmp_path / "page.md"
        md_file.write_text("# Title\n\nContent.\n", encoding="utf-8")

        llm_client = MagicMock()
        llm_client.chat_completion.return_value = self._make_llm_response([
            {"code": "FQ-1", "severity": "error", "excerpt": "import os", "line_approximate": 2},
            {"code": "FQ-7", "severity": "error", "excerpt": "Bad narrative.", "line_approximate": 5},
        ])

        issues, has_errors = _check_one_page(md_file, "system prompt", llm_client)

        assert has_errors  # FQ-1 causes this
        fq7_issues = [i for i in issues if "FQ-7" in i.get("error_code", "")]
        for issue in fq7_issues:
            assert issue["severity"] == "warn", (
                "FQ-7b must be warn even when co-occurring with FQ-1"
            )


# ── G17-FQ-7 vs G17-FQ-7a error codes ────────────────────────────────────────


class TestFQ7aVsFQ7bErrorCodes:
    """Ensure FQ-7a and FQ-7b use distinct error codes.

    FQ-7a from prelints: error_code = "G17-FQ-7a"
    FQ-7b from LLM Phase 2: error_code = "G17-FQ-7"

    These must be distinct so that the dedup logic (prelint_keys) works correctly:
    Phase 2 FQ-7 and Phase 1 FQ-7a are different codes and will NOT accidentally
    deduplicate each other.
    """

    def test_fq7b_issue_has_g17_fq7_error_code(self, tmp_path):
        """Phase 2 FQ-7 issues get error_code 'G17-FQ-7'."""
        md_file = tmp_path / "page.md"
        md_file.write_text("# Title\n\nContent.\n", encoding="utf-8")

        llm_client = MagicMock()
        llm_client.chat_completion.return_value = {
            "content": json.dumps({"defects": [
                {"code": "FQ-7", "severity": "warn", "excerpt": "Flow.", "line_approximate": 1}
            ]})
        }

        issues, has_errors = _check_one_page(md_file, "system prompt", llm_client)

        fq7_issues = [i for i in issues if i.get("error_code") == "G17-FQ-7"]
        assert len(fq7_issues) == 1
        assert fq7_issues[0]["severity"] == "warn"
        assert not has_errors

    def test_fq7a_from_prelints_has_g17_fq7a_error_code(self, tmp_path):
        """Phase 1 FQ-7a issues get error_code 'G17-FQ-7a' (not 'G17-FQ-7')."""
        from src.launch.workers.w9_validator.gates.gate_17_prelints import (
            lint_fq7a_heading_hierarchy,
        )

        # H1 -> H3 skip triggers FQ-7a
        content = "# Title\n\n### Skipped\n\nText.\n"
        md_file = tmp_path / "page.md"
        md_file.write_text(content, encoding="utf-8")

        issues = lint_fq7a_heading_hierarchy(content, md_file)

        assert len(issues) >= 1
        for issue in issues:
            assert issue["error_code"] == "G17-FQ-7a", (
                f"FQ-7a prelint must use 'G17-FQ-7a', got '{issue['error_code']}'"
            )
            # FQ-7a is error severity (gate-failing)
            assert issue["severity"] == "error"

    def test_fq7a_and_fq7b_codes_are_distinct(self):
        """Confirm FQ-7a and FQ-7b error_code strings are not equal (no dedup collision)."""
        fq7a_code = "G17-FQ-7a"
        fq7b_code = "G17-FQ-7"
        assert fq7a_code != fq7b_code, (
            "FQ-7a and FQ-7b error codes must be distinct to prevent dedup collision"
        )
