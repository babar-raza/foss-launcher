"""Tests for W7 Gate 17: LLM Formatting Quality Verification.

TC-2361: W7 Gate 17 LLM formatting quality verification.

All tests mock the LLM client so no real API calls are made.
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

def _make_llm_client(response_dict: dict) -> MagicMock:
    """Build a mock LLM client that returns the given response dict."""
    client = MagicMock()
    client.chat_completion.return_value = {
        "content": json.dumps(response_dict),
    }
    return client


def _make_md_file(tmp_path: Path, name: str, content: str) -> Path:
    """Create a published markdown file and return its path."""
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Test 1: llm_client=None → gate passes with INFO issue
# ---------------------------------------------------------------------------

def test_gate_passes_when_llm_unavailable(tmp_path):
    """Gate 17 returns (True, [info_issue]) when llm_client is None."""
    md = _make_md_file(tmp_path, "page.md", "# Title\n\nContent.\n")
    gate_passed, issues = run_gate_17(md_files=[md], llm_client=None)

    assert gate_passed is True
    assert len(issues) == 1
    assert issues[0]["severity"] == "info"
    assert issues[0]["gate"] == "gate_17_formatting_quality"


# ---------------------------------------------------------------------------
# Test 2: FQ-3 TRUNCATED (error) → gate fails
# ---------------------------------------------------------------------------

def test_gate_fails_on_truncated_sentence(tmp_path):
    """FQ-3 error defect causes the gate to fail."""
    md = _make_md_file(tmp_path, "guide.md", "# Guide\n\n- Supports multiple file\n")

    llm = _make_llm_client({
        "defects": [
            {
                "code": "FQ-3",
                "line_approximate": 3,
                "excerpt": "- Supports multiple file",
                "severity": "error",
            }
        ],
        "fixed_content": None,
    })

    gate_passed, issues = run_gate_17(md_files=[md], llm_client=llm)

    assert gate_passed is False
    assert len(issues) == 1
    assert issues[0]["severity"] == "error"
    assert issues[0]["gate"] == "gate_17_formatting_quality"
    assert "FQ-3" in issues[0]["error_code"]


# ---------------------------------------------------------------------------
# Test 3: FQ-2 only (warn) → gate passes, issue recorded
# ---------------------------------------------------------------------------

def test_gate_passes_on_warn_only(tmp_path):
    """FQ-2 warn defect does not fail the gate but is recorded."""
    md = _make_md_file(tmp_path, "faq.md", "# FAQ\n\nAnswer.### Q: Next\n\nAnswer.\n")

    llm = _make_llm_client({
        "defects": [
            {
                "code": "FQ-2",
                "line_approximate": 3,
                "excerpt": "Answer.### Q: Next",
                "severity": "warn",
            }
        ],
        "fixed_content": None,
    })

    gate_passed, issues = run_gate_17(md_files=[md], llm_client=llm)

    assert gate_passed is True
    assert len(issues) == 1
    assert issues[0]["severity"] == "warn"


# ---------------------------------------------------------------------------
# Test 4: FQ-6 (warn) and FQ-1 (error) mixed → gate fails
# ---------------------------------------------------------------------------

def test_gate_fails_when_any_error_present(tmp_path):
    """Gate fails when at least one error-severity defect is present."""
    md = _make_md_file(
        tmp_path, "mixed.md",
        "---\nkeywords:\n  - dive:\n---\n\nworkbook.save()\n"
    )

    llm = _make_llm_client({
        "defects": [
            {"code": "FQ-6", "line_approximate": 10, "excerpt": "<!-- claim: abc -->", "severity": "warn"},
            {"code": "FQ-1", "line_approximate": 6, "excerpt": "workbook.save()", "severity": "error"},
        ],
        "fixed_content": None,
    })

    gate_passed, issues = run_gate_17(md_files=[md], llm_client=llm)

    assert gate_passed is False
    severities = {i["severity"] for i in issues}
    assert "error" in severities
    assert "warn" in severities


# ---------------------------------------------------------------------------
# Test 5: No defects → gate passes, empty issues
# ---------------------------------------------------------------------------

def test_gate_passes_with_no_defects(tmp_path):
    """When LLM finds no defects the gate passes with no issues."""
    md = _make_md_file(tmp_path, "clean.md", "# Clean\n\nNo issues here.\n")

    llm = _make_llm_client({"defects": [], "fixed_content": None})

    gate_passed, issues = run_gate_17(md_files=[md], llm_client=llm)

    assert gate_passed is True
    assert issues == []


# ---------------------------------------------------------------------------
# Test 6: JSON parse failure → page skipped, gate passes
# ---------------------------------------------------------------------------

def test_json_parse_failure_skips_page(tmp_path):
    """When LLM returns non-JSON the page is skipped and gate passes."""
    md = _make_md_file(tmp_path, "page.md", "# Title\n\nContent.\n")

    client = MagicMock()
    client.chat_completion.return_value = {"content": "Not JSON"}

    gate_passed, issues = run_gate_17(md_files=[md], llm_client=client)

    assert gate_passed is True
    assert issues == []


# ---------------------------------------------------------------------------
# Test 7: Empty file list → gate passes, no issues
# ---------------------------------------------------------------------------

def test_empty_file_list_passes(tmp_path):
    """Gate 17 passes with no issues when there are no files to scan."""
    llm = _make_llm_client({"defects": [], "fixed_content": None})

    gate_passed, issues = run_gate_17(md_files=[], llm_client=llm)

    assert gate_passed is True
    assert issues == []


# ---------------------------------------------------------------------------
# Test 8: Gate does NOT modify files (verification only)
# ---------------------------------------------------------------------------

def test_gate_does_not_modify_files(tmp_path):
    """Gate 17 is read-only — it must not write fixed_content to disk."""
    original = "# Guide\n\n- Supports multiple file\n"
    fixed = "# Guide\n\n- Supports multiple file formats.\n"
    md = _make_md_file(tmp_path, "guide.md", original)

    llm = _make_llm_client({
        "defects": [
            {"code": "FQ-3", "line_approximate": 3, "excerpt": "- Supports multiple file", "severity": "error"},
        ],
        "fixed_content": fixed,
    })

    run_gate_17(md_files=[md], llm_client=llm)

    # File must NOT have been modified — Gate 17 is verification only
    assert md.read_text(encoding="utf-8") == original
