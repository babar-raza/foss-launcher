"""Tests for W7 Phase 0 LLM formatting review and fix.

TC-2360: W7 Phase 0 LLM formatting review and fix.

All tests mock the LLM client so no real API calls are made.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from launch.workers.w7_content_reviewer.fixes.llm_format_fix import (
    run_llm_format_fix,
    _process_one_page,
)
from launch.workers.w7_content_reviewer.scoring import calculate_scores


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


def _make_draft(tmp_path: Path, name: str, content: str) -> Path:
    """Create a draft markdown file and return its path."""
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Test 1: llm_client=None → graceful skip
# ---------------------------------------------------------------------------

def test_llm_unavailable_skips_gracefully(tmp_path):
    """run_llm_format_fix returns ([], []) when llm_client is None."""
    draft = _make_draft(tmp_path, "page.md", "# Hello\n\nContent.\n")
    issues, fixes = run_llm_format_fix(drafts_dir=tmp_path, llm_client=None)
    assert issues == []
    assert fixes == []
    # File must not be modified
    assert draft.read_text(encoding="utf-8") == "# Hello\n\nContent.\n"


# ---------------------------------------------------------------------------
# Test 2: FQ-2 FAQ concat detected and fixed
# ---------------------------------------------------------------------------

def test_fq2_faq_concat_detected_and_fixed(tmp_path):
    """FQ-2 warn defect: issue recorded, draft file updated with fixed_content."""
    original = "---\ntitle: FAQ\n---\n\n### Q: How?\n\nAnswer.### Q: Why?\n\nBecause.\n"
    fixed = "---\ntitle: FAQ\n---\n\n### Q: How?\n\nAnswer.\n\n### Q: Why?\n\nBecause.\n"
    draft = _make_draft(tmp_path, "faq.md", original)

    llm = _make_llm_client({
        "defects": [
            {
                "code": "FQ-2",
                "line_approximate": 7,
                "excerpt": "Answer.### Q: Why?",
                "severity": "warn",
            }
        ],
        "fixed_content": fixed,
    })

    issues, fix_results = run_llm_format_fix(drafts_dir=tmp_path, llm_client=llm)

    assert len(issues) == 1
    assert issues[0]["check"] == "formatting_quality.faq_concat"
    assert issues[0]["severity"] == "warn"

    assert len(fix_results) == 1
    assert fix_results[0]["success"] is True

    # File on disk must now contain the fixed content
    assert draft.read_text(encoding="utf-8") == fixed


# ---------------------------------------------------------------------------
# Test 3: FQ-5 keyword colon detected and fixed
# ---------------------------------------------------------------------------

def test_fq5_keyword_colon_detected_and_fixed(tmp_path):
    """FQ-5 warn defect: keyword colon reported with warn severity."""
    original = "---\ntitle: Blog\nkeywords:\n  - dive:\n  - excel\n---\n\nContent.\n"
    fixed = "---\ntitle: Blog\nkeywords:\n  - dive\n  - excel\n---\n\nContent.\n"
    draft = _make_draft(tmp_path, "blog.md", original)

    llm = _make_llm_client({
        "defects": [
            {
                "code": "FQ-5",
                "line_approximate": 4,
                "excerpt": "  - dive:",
                "severity": "warn",
            }
        ],
        "fixed_content": fixed,
    })

    issues, fix_results = run_llm_format_fix(drafts_dir=tmp_path, llm_client=llm)

    assert len(issues) == 1
    assert issues[0]["check"] == "formatting_quality.keyword_colon"
    assert issues[0]["severity"] == "warn"
    assert fix_results[0]["success"] is True
    assert draft.read_text(encoding="utf-8") == fixed


# ---------------------------------------------------------------------------
# Test 4: No defects → empty results, file unchanged
# ---------------------------------------------------------------------------

def test_no_defects_returns_empty(tmp_path):
    """When LLM finds no defects, issues and fix_results are empty, file unchanged."""
    content = "---\ntitle: Guide\n---\n\nClean content with no defects.\n"
    draft = _make_draft(tmp_path, "guide.md", content)

    llm = _make_llm_client({"defects": [], "fixed_content": None})

    issues, fix_results = run_llm_format_fix(drafts_dir=tmp_path, llm_client=llm)

    assert issues == []
    assert fix_results == []
    assert draft.read_text(encoding="utf-8") == content


# ---------------------------------------------------------------------------
# Test 5: JSON parse failure → skip page gracefully
# ---------------------------------------------------------------------------

def test_json_parse_failure_skips_page(tmp_path):
    """When LLM returns non-JSON, the page is skipped without raising."""
    draft = _make_draft(tmp_path, "page.md", "# Title\n\nContent.\n")

    client = MagicMock()
    client.chat_completion.return_value = {"content": "Not valid JSON at all"}

    issues, fix_results = run_llm_format_fix(drafts_dir=tmp_path, llm_client=client)

    assert issues == []
    assert fix_results == []


# ---------------------------------------------------------------------------
# Test 6: FQ-1 error defect — issue has severity=error
# ---------------------------------------------------------------------------

def test_fq1_error_defect_has_error_severity(tmp_path):
    """FQ-1 (NAKED_CODE) defects are reported with severity=error."""
    draft = _make_draft(tmp_path, "tutorial.md", "# Tutorial\n\nworkbook.save()\n")

    llm = _make_llm_client({
        "defects": [
            {
                "code": "FQ-1",
                "line_approximate": 3,
                "excerpt": "workbook.save()",
                "severity": "error",
            }
        ],
        "fixed_content": "# Tutorial\n\n```python\nworkbook.save()\n```\n",
    })

    issues, _ = run_llm_format_fix(drafts_dir=tmp_path, llm_client=llm)

    assert len(issues) == 1
    assert issues[0]["check"] == "formatting_quality.naked_code"
    assert issues[0]["severity"] == "error"


# ---------------------------------------------------------------------------
# Test 7: formatting_quality issues reduce content_quality score in scoring.py
# ---------------------------------------------------------------------------

def test_scoring_maps_fq_to_content_quality():
    """formatting_quality.* issues lower the content_quality score."""
    issues = [
        {
            "check": "formatting_quality.naked_code",
            "severity": "error",
            "location": {"path": "page.md", "line": 3},
            "auto_fixable": True,
        }
    ]
    scores = calculate_scores(issues, num_pages=1)

    # An error in content_quality dimension must produce score < 5
    assert "content_quality" in scores
    assert scores["content_quality"] < 5

    # Other dimensions must be unaffected (score 5 with no issues)
    assert scores["technical_accuracy"] == 5
    assert scores["usability"] == 5


# ---------------------------------------------------------------------------
# Test 8: LLM call failure → page skipped, no exception
# ---------------------------------------------------------------------------

def test_llm_call_failure_skips_page(tmp_path):
    """When the LLM call raises, the page is skipped without raising."""
    draft = _make_draft(tmp_path, "page.md", "# Title\n\nContent.\n")

    client = MagicMock()
    client.chat_completion.side_effect = RuntimeError("Connection timeout")

    issues, fix_results = run_llm_format_fix(drafts_dir=tmp_path, llm_client=client)

    assert issues == []
    assert fix_results == []
