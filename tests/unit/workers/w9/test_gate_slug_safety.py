"""TC-2841: Tests for gate_slug_safety.

Covers:
- Clean slugs pass
- Repr-leaked slugs fail (brackets, quotes, commas)
- Doubled separators fail
- Empty path segments fail
- Profile-based severity
"""

from __future__ import annotations

import json
import pytest
from pathlib import Path

from src.launch.workers.w9_validator.gates.gate_slug_safety import (
    execute_gate,
    _check_slug,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_page_plan(run_dir: Path, pages: list) -> None:
    arts = run_dir / "artifacts"
    arts.mkdir(parents=True, exist_ok=True)
    (arts / "page_plan.json").write_text(
        json.dumps({"pages": pages}), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# _check_slug
# ---------------------------------------------------------------------------

class TestCheckSlug:

    def test_clean_slug_passes(self):
        issues = []
        _check_slug("open-stl-file-python", "content/kb/open-stl-file-python/index.md", "ci", issues)
        assert len(issues) == 0

    def test_repr_leaked_slug_fails(self):
        issues = []
        _check_slug("convert-['pdf']-to-['doc']", "", "ci", issues)
        assert len(issues) >= 1
        assert issues[0]["error_code"] == "SLUG_REPR_TOKEN"

    def test_doubled_separator_fails(self):
        issues = []
        _check_slug("convert--pdf-to-doc", "", "ci", issues)
        assert len(issues) >= 1
        assert issues[0]["error_code"] == "SLUG_DOUBLED_SEPARATOR"

    def test_empty_segment_in_path_fails(self):
        issues = []
        _check_slug("convert", "content//kb/convert/index.md", "ci", issues)
        assert len(issues) >= 1
        assert issues[0]["error_code"] == "SLUG_EMPTY_SEGMENT"

    def test_prod_severity_is_blocker(self):
        issues = []
        _check_slug("bad['slug']", "", "prod", issues)
        assert issues[0]["severity"] == "blocker"

    def test_local_severity_is_warn(self):
        issues = []
        _check_slug("bad['slug']", "", "local", issues)
        assert issues[0]["severity"] == "warn"

    def test_empty_slug_skipped(self):
        issues = []
        _check_slug("", "", "ci", issues)
        assert len(issues) == 0


# ---------------------------------------------------------------------------
# execute_gate (integration)
# ---------------------------------------------------------------------------

class TestExecuteGate:

    def test_clean_plan_passes(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_page_plan(run_dir, [
            {"slug": "open-stl-file-python", "output_path": "content/kb/open-stl-file-python/index.md"},
            {"slug": "convert-pdf-to-docx", "output_path": "content/kb/convert-pdf-to-docx/index.md"},
        ])
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is True

    def test_repr_leaked_plan_fails(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_page_plan(run_dir, [
            {"slug": "convert-['pdf']-to-['doc']", "output_path": "content/kb/bad/index.md"},
        ])
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is False

    def test_no_plan_passes(self, tmp_path):
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is True

    def test_empty_segment_in_filesystem(self, tmp_path):
        """Detect empty segments in actual generated file paths."""
        run_dir = tmp_path / "run"
        content_dir = run_dir / "work" / "site" / "content" / "docs"
        content_dir.mkdir(parents=True)
        # We can't create a path with // on filesystem, but we can test the plan
        _write_page_plan(run_dir, [
            {"slug": "test", "output_path": "content//kb/test/index.md"},
        ])
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is False
