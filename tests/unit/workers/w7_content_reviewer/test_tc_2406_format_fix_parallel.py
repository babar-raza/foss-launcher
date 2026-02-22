"""Tests for TC-2406: W7 Phase 0 format fix per-call timeout + parallel loop.

TC-2406 adds:
- _FORMAT_FIX_TIMEOUT_S = 120 module-level constant
- timeout=_FORMAT_FIX_TIMEOUT_S passed to chat_completion() in _process_one_page()
- n_workers param to run_llm_format_fix() with ThreadPoolExecutor parallel path
- n_workers=n_workers wired from worker.py call site
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from launch.workers.w7_content_reviewer.fixes.llm_format_fix import (
    _FORMAT_FIX_TIMEOUT_S,
    _process_one_page,
    run_llm_format_fix,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_llm_response(defects=None, fixed_content=None):
    """Return a mock LLM response with JSON payload."""
    payload = {
        "defects": defects or [],
        "fixed_content": fixed_content,
    }
    mock = MagicMock()
    mock.chat_completion.return_value = {"content": json.dumps(payload)}
    return mock


def _write_md(tmp_path: Path, name: str, text: str = "# Hello\n\nContent here.\n") -> Path:
    f = tmp_path / name
    f.write_text(text, encoding="utf-8")
    return f


# ---------------------------------------------------------------------------
# Test 1: timeout constant is passed to chat_completion
# ---------------------------------------------------------------------------

def test_timeout_constant_passed_to_chat_completion(tmp_path):
    """_process_one_page() must pass timeout=_FORMAT_FIX_TIMEOUT_S to chat_completion."""
    draft = _write_md(tmp_path, "page.md")
    mock_llm = MagicMock()
    mock_llm.chat_completion.return_value = {
        "content": json.dumps({"defects": [], "fixed_content": None})
    }
    system_text = "You are a formatter."

    _process_one_page(draft, system_text, mock_llm)

    assert mock_llm.chat_completion.called
    _, kwargs = mock_llm.chat_completion.call_args
    assert kwargs.get("timeout") == _FORMAT_FIX_TIMEOUT_S, (
        f"Expected timeout={_FORMAT_FIX_TIMEOUT_S}, got timeout={kwargs.get('timeout')}"
    )


# ---------------------------------------------------------------------------
# Test 2: sequential (n_workers=1) and parallel (n_workers=4) same results
# ---------------------------------------------------------------------------

def test_sequential_and_parallel_produce_same_results(tmp_path):
    """n_workers=1 and n_workers=4 must produce the same issue/fix sets."""
    pages = [_write_md(tmp_path, f"page_{i}.md", f"# Page {i}\n\nContent.\n") for i in range(4)]

    defect = {"code": "FQ-3", "severity": "error", "excerpt": "truncated", "line_approximate": 5}
    fixed = "# Page\n\nFixed content.\n"

    mock_llm = MagicMock()
    mock_llm.chat_completion.return_value = {
        "content": json.dumps({"defects": [defect], "fixed_content": fixed})
    }

    with patch("launch.workers.w7_content_reviewer.fixes.llm_format_fix._load_system_prompt",
               return_value="sys"):
        seq_issues, seq_fixes = run_llm_format_fix(tmp_path, mock_llm, n_workers=1)

    # Reset file contents (parallel path will also write them)
    for i, p in enumerate(pages):
        p.write_text(f"# Page {i}\n\nContent.\n", encoding="utf-8")

    with patch("launch.workers.w7_content_reviewer.fixes.llm_format_fix._load_system_prompt",
               return_value="sys"):
        par_issues, par_fixes = run_llm_format_fix(tmp_path, mock_llm, n_workers=4)

    # Issue counts must match (order may differ in parallel)
    assert len(seq_issues) == len(par_issues), (
        f"seq={len(seq_issues)} issues, par={len(par_issues)} issues"
    )
    assert len(seq_fixes) == len(par_fixes), (
        f"seq={len(seq_fixes)} fixes, par={len(par_fixes)} fixes"
    )


# ---------------------------------------------------------------------------
# Test 3: exception in worker thread is caught, others continue
# ---------------------------------------------------------------------------

def test_exception_in_worker_thread_is_caught(tmp_path):
    """If one page raises, run_llm_format_fix should complete and process the rest."""
    good1 = _write_md(tmp_path, "aaa_good1.md")
    bad   = _write_md(tmp_path, "bbb_bad.md")
    good2 = _write_md(tmp_path, "ccc_good2.md")

    call_count = [0]

    def side_effect(**kwargs):
        call_count[0] += 1
        if "bbb_bad" in kwargs.get("call_id", ""):
            raise RuntimeError("simulated LLM failure")
        return {"content": json.dumps({"defects": [], "fixed_content": None})}

    mock_llm = MagicMock()
    mock_llm.chat_completion.side_effect = side_effect

    with patch("launch.workers.w7_content_reviewer.fixes.llm_format_fix._load_system_prompt",
               return_value="sys"):
        issues, fixes = run_llm_format_fix(tmp_path, mock_llm, n_workers=3)

    # Should complete without raising; bad page yields empty issues/fix
    assert isinstance(issues, list)
    assert isinstance(fixes, list)


# ---------------------------------------------------------------------------
# Test 4: n_workers=1 does NOT instantiate ThreadPoolExecutor
# ---------------------------------------------------------------------------

def test_n_workers_1_skips_threadpool(tmp_path):
    """When n_workers=1, ThreadPoolExecutor must NOT be used."""
    _write_md(tmp_path, "page.md")
    mock_llm = _make_llm_response()

    tpe_path = "launch.workers.w7_content_reviewer.fixes.llm_format_fix.ThreadPoolExecutor"
    with patch("launch.workers.w7_content_reviewer.fixes.llm_format_fix._load_system_prompt",
               return_value="sys"):
        # ThreadPoolExecutor is imported inside the else-branch; patch via the module
        with patch("concurrent.futures.ThreadPoolExecutor") as mock_tpe:
            run_llm_format_fix(tmp_path, mock_llm, n_workers=1)
            mock_tpe.assert_not_called()


# ---------------------------------------------------------------------------
# Test 5: empty drafts directory returns empty lists
# ---------------------------------------------------------------------------

def test_empty_drafts_dir_returns_empty_lists(tmp_path):
    """An empty drafts directory must return ([], []) without error."""
    mock_llm = MagicMock()
    with patch("launch.workers.w7_content_reviewer.fixes.llm_format_fix._load_system_prompt",
               return_value="sys"):
        issues, fixes = run_llm_format_fix(tmp_path, mock_llm, n_workers=4)

    assert issues == []
    assert fixes == []
    mock_llm.chat_completion.assert_not_called()


# ---------------------------------------------------------------------------
# Test 6: llm_client=None skips Phase 0 entirely
# ---------------------------------------------------------------------------

def test_none_llm_client_returns_empty(tmp_path):
    """run_llm_format_fix(llm_client=None) must return ([], []) immediately."""
    _write_md(tmp_path, "page.md")
    issues, fixes = run_llm_format_fix(tmp_path, None, n_workers=4)
    assert issues == []
    assert fixes == []


# ---------------------------------------------------------------------------
# Test 7: _FORMAT_FIX_TIMEOUT_S is a positive integer
# ---------------------------------------------------------------------------

def test_format_fix_timeout_constant_is_positive():
    """_FORMAT_FIX_TIMEOUT_S must be a positive integer (not None, not 0)."""
    assert isinstance(_FORMAT_FIX_TIMEOUT_S, int)
    assert _FORMAT_FIX_TIMEOUT_S > 0


# ---------------------------------------------------------------------------
# A1: Frontmatter validation — reject LLM output that drops closing ---
# ---------------------------------------------------------------------------

from launch.workers.w7_content_reviewer.fixes.llm_format_fix import (
    _FM_MARKER,
    _needs_format_fix,
)


_GOOD_FM = (
    "---\ntitle: \"Test\"\nlayout: docs\nmachine_readable:\n"
    "  product_name: \"P\"\n---\n\n## Body\n\nContent here.\n"
)

_BAD_FM = (
    "---\ntitle: \"Test\"\nlayout: docs\nmachine_readable:\n"
    " product_name: \"P\"\n keywords: [a, b]\n\n## Body\n\nContent here.\n"
)


def test_frontmatter_validation_rejects_corrupt_fix(tmp_path):
    """LLM output that drops the closing --- must be rejected (file unchanged)."""
    draft = tmp_path / "page.md"
    draft.write_text(_GOOD_FM, encoding="utf-8")

    # LLM returns fixed_content WITHOUT closing ---
    mock_llm = MagicMock()
    mock_llm.chat_completion.return_value = {
        "content": json.dumps({"defects": [{"code": "FQ-4", "severity": "error",
                                             "excerpt": "heading", "line_approximate": 1}],
                                "fixed_content": _BAD_FM})
    }

    _process_one_page(draft, "sys", mock_llm)

    # Original content must be preserved (fix rejected)
    assert draft.read_text(encoding="utf-8") == _GOOD_FM


def test_frontmatter_validation_accepts_clean_fix(tmp_path):
    """LLM output that preserves both --- markers must be written to disk."""
    draft = tmp_path / "page.md"
    original = _GOOD_FM
    draft.write_text(original, encoding="utf-8")

    fixed = (
        "---\ntitle: \"Test\"\nlayout: docs\nmachine_readable:\n"
        "  product_name: \"P\"\n---\n\n## Body\n\nBetter content.\n"
    )
    assert fixed.strip() != original.strip()  # sanity: LLM made a change

    mock_llm = MagicMock()
    mock_llm.chat_completion.return_value = {
        "content": json.dumps({"defects": [], "fixed_content": fixed})
    }

    _process_one_page(draft, "sys", mock_llm)

    # Fixed content should be written
    assert draft.read_text(encoding="utf-8") == fixed


# ---------------------------------------------------------------------------
# B1: _needs_format_fix heuristic
# ---------------------------------------------------------------------------

def test_needs_format_fix_clean_page():
    """A well-formed deterministic-fallback page should return False."""
    content = (
        "---\ntitle: \"Test\"\nlayout: docs\n---\n\n"
        "## Getting Started\n\n"
        "This is a well-formed paragraph with enough words to pass the word count "
        "threshold. It describes the product features clearly and concisely. "
        "The library supports multiple formats and provides efficient workflows. "
        "Developers can use it for enterprise and prototype applications.\n\n"
        "## Key Features\n\n"
        "- Feature one works correctly.\n"
        "- Feature two is fully supported.\n"
    )
    assert _needs_format_fix(content) is False


def test_needs_format_fix_naked_code():
    """A page with indented code outside fences should return True."""
    content = (
        "---\ntitle: \"Test\"\nlayout: docs\n---\n\n"
        "## Example\n\n"
        "    import aspose3d  # naked code outside a fence\n"
        "    scene = aspose3d.Scene()\n\n"
        "Some text here to pass word count. " * 5 + "\n"
    )
    assert _needs_format_fix(content) is True


def test_needs_format_fix_double_heading():
    """A page with heading+paragraph on one line should return True."""
    content = (
        "---\ntitle: \"Test\"\nlayout: docs\n---\n\n"
        "## Getting StartedThis is a very long text that was concatenated "
        "Onto the heading line which is a formatting defect detected by FQ-4.\n\n"
        "Some text here to pass word count. " * 5 + "\n"
    )
    assert _needs_format_fix(content) is True


def test_needs_format_fix_short_body():
    """A page with very short body (< 50 words) should return True."""
    content = "---\ntitle: \"Test\"\n---\n\n## Title\n\nShort.\n"
    assert _needs_format_fix(content) is True


def test_needs_format_fix_skips_clean_page_in_process(tmp_path):
    """_process_one_page should return ([], None) for a clean page without LLM call."""
    content = (
        "---\ntitle: \"Test\"\nlayout: docs\n---\n\n"
        "## Getting Started\n\n"
        "This is a well-formed paragraph with enough words to pass. " * 5 + "\n\n"
        "## Features\n\n"
        "- Feature one works correctly.\n"
        "- Feature two is fully supported.\n"
    )
    draft = tmp_path / "clean.md"
    draft.write_text(content, encoding="utf-8")

    mock_llm = MagicMock()
    issues, fix = _process_one_page(draft, "sys", mock_llm)

    assert issues == []
    assert fix is None
    mock_llm.chat_completion.assert_not_called()
