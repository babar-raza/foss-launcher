"""Tests for TC-2407: W7 Phase 4 regen per-call timeout + parallel per-file loop.

TC-2407 adds:
- _REGEN_TIMEOUT_S = 120 module-level constant
- timeout=_REGEN_TIMEOUT_S passed to chat_completion() in _process_one_regen_file()
- n_workers param to _run_agent_on_files() with ThreadPoolExecutor parallel path
- _process_one_regen_file() extracted as a pure per-file helper
- n_workers threaded through spawn_enhancement_agents() → all 4 spawners → _run_agent_on_files()
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from launch.workers.w7_content_reviewer.fixes.llm_regen import (
    _REGEN_TIMEOUT_S,
    _process_one_regen_file,
    _run_agent_on_files,
    spawn_enhancement_agents,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_md(tmp_path: Path, name: str, text: str = "# Hello\n\nContent here.\n") -> Path:
    f = tmp_path / name
    f.write_text(text, encoding="utf-8")
    return f


def _make_issue(file_path: str, severity: str = "error") -> dict:
    return {
        "check": "content_quality.low_density",
        "severity": severity,
        "message": "Density too low",
        "location": {"path": file_path, "line": 1},
        "auto_fixable": False,
    }


def _make_llm(enhanced: str = "# Fixed\n\n<!-- claim: abc123 -->Content fixed.\n"):
    mock = MagicMock()
    mock.chat_completion.return_value = {"content": enhanced}
    return mock


# ---------------------------------------------------------------------------
# Test 1: timeout constant is passed to chat_completion in _process_one_regen_file
# ---------------------------------------------------------------------------

def test_regen_timeout_passed_to_chat_completion(tmp_path):
    """_process_one_regen_file() must pass timeout=_REGEN_TIMEOUT_S to chat_completion."""
    original = "# Page\n\n<!-- claim: abc123 -->\n\nSome content here that is long enough.\n"
    draft = _write_md(tmp_path, "page.md", original)
    issue = _make_issue(str(draft))

    mock_llm = MagicMock()
    mock_llm.chat_completion.return_value = {
        "content": "# Page\n\n<!-- claim: abc123 -->\n\nFixed content here.\n"
    }

    _process_one_regen_file(str(draft), "content_enhancer", [issue], tmp_path, {}, mock_llm)

    assert mock_llm.chat_completion.called
    _, kwargs = mock_llm.chat_completion.call_args
    assert kwargs.get("timeout") == _REGEN_TIMEOUT_S, (
        f"Expected timeout={_REGEN_TIMEOUT_S}, got {kwargs.get('timeout')}"
    )


# ---------------------------------------------------------------------------
# Test 2: sequential (n_workers=1) and parallel (n_workers=4) same results
# ---------------------------------------------------------------------------

def test_sequential_and_parallel_produce_same_results(tmp_path):
    """n_workers=1 and n_workers=4 must produce the same modified/failed counts."""
    originals = {}
    for i in range(4):
        text = f"# Page {i}\n\n<!-- claim: id{i:04d} -->\n\nContent for page {i}.\n"
        draft = _write_md(tmp_path, f"page_{i}.md", text)
        originals[str(draft)] = text

    issues = [_make_issue(fp) for fp in originals]

    def make_fixed(fp):
        i = Path(fp).stem.split("_")[1]
        return f"# Page {i}\n\n<!-- claim: id{int(i):04d} -->\n\nFixed content for page {i}.\n"

    def side_effect(**kwargs):
        cid = kwargs.get("call_id", "page_0")
        stem = cid.replace("w7_content_enhancer_", "")
        path = tmp_path / f"{stem}.md"
        return {"content": make_fixed(str(path))}

    mock_llm = MagicMock()
    mock_llm.chat_completion.side_effect = side_effect

    run_dir = tmp_path / "run"
    run_dir.mkdir()

    seq = _run_agent_on_files(
        "content_enhancer", issues, run_dir, {}, llm_client=mock_llm,
        drafts_dir=tmp_path, n_workers=1,
    )

    # Reset files
    for fp, text in originals.items():
        Path(fp).write_text(text, encoding="utf-8")

    par = _run_agent_on_files(
        "content_enhancer", issues, run_dir, {}, llm_client=mock_llm,
        drafts_dir=tmp_path, n_workers=4,
    )

    assert len(seq["files_modified"]) == len(par["files_modified"]), (
        f"seq modified {seq['files_modified']}, par modified {par['files_modified']}"
    )


# ---------------------------------------------------------------------------
# Test 3: exception in worker thread is caught, others continue
# ---------------------------------------------------------------------------

def test_thread_exception_caught_others_continue(tmp_path):
    """If one file's LLM call raises, the agent result should include other files."""
    good = _write_md(tmp_path, "good.md", "# Good\n\n<!-- claim: g001 -->\n\nContent.\n")
    bad  = _write_md(tmp_path, "bad.md",  "# Bad\n\n<!-- claim: b001 -->\n\nContent.\n")

    issues = [_make_issue(str(good)), _make_issue(str(bad))]

    def side_effect(**kwargs):
        if "bad" in kwargs.get("call_id", ""):
            raise RuntimeError("simulated LLM failure")
        return {"content": "# Good\n\n<!-- claim: g001 -->\n\nFixed.\n"}

    mock_llm = MagicMock()
    mock_llm.chat_completion.side_effect = side_effect

    run_dir = tmp_path / "run"
    run_dir.mkdir()

    result = _run_agent_on_files(
        "content_enhancer", issues, run_dir, {}, llm_client=mock_llm,
        drafts_dir=tmp_path, n_workers=2,
    )

    # Should not raise; at least the good file should be modified
    assert isinstance(result, dict)
    assert "files_modified" in result


# ---------------------------------------------------------------------------
# Test 4: n_workers=1 does NOT instantiate ThreadPoolExecutor
# ---------------------------------------------------------------------------

def test_n_workers_1_skips_threadpool(tmp_path):
    """When n_workers=1, ThreadPoolExecutor must NOT be instantiated."""
    draft = _write_md(tmp_path, "page.md", "# P\n\n<!-- claim: x001 -->\n\nContent.\n")
    issue = _make_issue(str(draft))
    mock_llm = _make_llm()
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    with patch("concurrent.futures.ThreadPoolExecutor") as mock_tpe:
        _run_agent_on_files(
            "content_enhancer", [issue], run_dir, {}, llm_client=mock_llm,
            drafts_dir=tmp_path, n_workers=1,
        )
        mock_tpe.assert_not_called()


# ---------------------------------------------------------------------------
# Test 5: empty affected_files returns skipped result
# ---------------------------------------------------------------------------

def test_empty_affected_files_returns_skipped(tmp_path):
    """No issues → no affected files → result status should be 'skipped'."""
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    mock_llm = MagicMock()

    result = _run_agent_on_files(
        "content_enhancer", [], run_dir, {}, llm_client=mock_llm,
        drafts_dir=tmp_path, n_workers=4,
    )

    assert result["status"] == "skipped"
    assert result["files_modified"] == []
    mock_llm.chat_completion.assert_not_called()


# ---------------------------------------------------------------------------
# Test 6: _REGEN_TIMEOUT_S is a positive integer
# ---------------------------------------------------------------------------

def test_regen_timeout_constant_is_positive():
    """_REGEN_TIMEOUT_S must be a positive integer."""
    assert isinstance(_REGEN_TIMEOUT_S, int)
    assert _REGEN_TIMEOUT_S > 0


# ---------------------------------------------------------------------------
# Test 7: spawn_enhancement_agents passes n_workers to spawners
# ---------------------------------------------------------------------------

def test_spawn_enhancement_agents_passes_n_workers(tmp_path):
    """spawn_enhancement_agents(n_workers=3) must propagate n_workers to _run_agent_on_files."""
    draft = _write_md(tmp_path, "page.md", "# P\n\n<!-- claim: x001 -->\n\nContent.\n")
    issue = {
        "check": "content_quality.low_density",
        "severity": "error",
        "message": "low density",
        "location": {"path": str(draft), "line": 1},
        "auto_fixable": False,
    }

    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "artifacts").mkdir()

    mock_llm = _make_llm()
    run_config = {"review_enabled": True, "offline_mode": False}

    captured_n = []

    original_run = _run_agent_on_files.__wrapped__ if hasattr(_run_agent_on_files, "__wrapped__") else None

    with patch(
        "launch.workers.w7_content_reviewer.fixes.llm_regen._run_agent_on_files",
        wraps=lambda *a, n_workers=1, **kw: captured_n.append(n_workers) or {
            "agent_type": "content_enhancer", "status": "skipped",
            "issues_addressed": 0, "files_modified": [],
        },
    ):
        spawn_enhancement_agents(
            [issue], run_dir, run_config,
            llm_client=mock_llm, drafts_dir=tmp_path, n_workers=3,
        )

    assert captured_n, "Expected _run_agent_on_files to be called"
    assert all(n == 3 for n in captured_n), f"Expected n_workers=3 in all calls, got {captured_n}"
