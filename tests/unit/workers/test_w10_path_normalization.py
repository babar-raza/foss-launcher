"""TC-3240: W10 Fixer relative path resolution tests.

Root cause: normalize_report() (TC-935) converts absolute paths in
validation_report.json to relative (run_dir-relative) paths for determinism.
W10 fix functions then do ``Path(relative_path).exists()`` which resolves
against CWD instead of run_dir, causing "File not found" on every fix attempt.

Fix: ``_normalize_issue_paths(issue, run_dir)`` resolves relative paths
against run_dir before any fix function sees them.

Spec references:
- specs/21_worker_contracts.md:290-320 (W10 contract)
- specs/28_coordination_and_handoffs.md:71-84 (Fix loop policy)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import pytest

from src.launch.workers.w10_fixer.worker import (
    _normalize_issue_paths,
    _strip_rundir_overlap,
    fix_formatting_defect,
    fix_unresolved_token,
    StaleValidationReportError,
)
from src.launch.workers.w10_fixer import execute_fixer


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def run_dir(tmp_path: Path) -> Path:
    """Create a temporary run directory with standard structure."""
    rd = tmp_path / "runs" / "test_run"
    rd.mkdir(parents=True)
    (rd / "artifacts").mkdir()
    (rd / "reports").mkdir()
    (rd / "events.ndjson").touch()
    (rd / "work" / "site" / "content").mkdir(parents=True)
    return rd


# ---------------------------------------------------------------------------
# Class 1: Unit tests for _normalize_issue_paths
# ---------------------------------------------------------------------------

class TestNormalizeIssuePaths:
    """Unit tests for the _normalize_issue_paths helper."""

    def test_relative_path_resolved(self, tmp_path: Path):
        """Relative location.path is resolved to absolute using run_dir."""
        issue: Dict[str, Any] = {
            "location": {"path": "work/site/content/page.md", "line": 5},
        }
        _normalize_issue_paths(issue, tmp_path)
        assert issue["location"]["path"] == str(tmp_path / "work/site/content/page.md")

    def test_absolute_path_unchanged(self, tmp_path: Path):
        """Absolute location.path is left as-is."""
        abs_path = str(tmp_path / "work" / "site" / "page.md")
        issue: Dict[str, Any] = {
            "location": {"path": abs_path, "line": 1},
        }
        _normalize_issue_paths(issue, tmp_path)
        assert issue["location"]["path"] == abs_path

    def test_forward_slash_relative_path(self, tmp_path: Path):
        """Forward-slash relative path (as produced by normalize_report) resolves correctly."""
        issue: Dict[str, Any] = {
            "location": {
                "path": "work/site/content/blog.aspose.org/3d/python/quick-start/index.md",
                "line": 28,
            },
        }
        _normalize_issue_paths(issue, tmp_path)
        expected = str(
            tmp_path / "work/site/content/blog.aspose.org/3d/python/quick-start/index.md"
        )
        assert issue["location"]["path"] == expected

    def test_no_location_key_safe(self, tmp_path: Path):
        """Issue without location key does not raise."""
        issue: Dict[str, Any] = {"issue_id": "test", "severity": "error"}
        _normalize_issue_paths(issue, tmp_path)  # should not raise

    def test_location_not_dict_safe(self, tmp_path: Path):
        """Issue with non-dict location does not raise."""
        issue: Dict[str, Any] = {"location": "some/path"}
        _normalize_issue_paths(issue, tmp_path)  # should not raise

    def test_no_path_in_location_safe(self, tmp_path: Path):
        """Issue with location dict but no path key does not raise."""
        issue: Dict[str, Any] = {"location": {"line": 5}}
        _normalize_issue_paths(issue, tmp_path)
        assert issue["location"] == {"line": 5}

    def test_files_list_resolved(self, tmp_path: Path):
        """Relative paths in files list are resolved."""
        issue: Dict[str, Any] = {
            "files": [
                "work/site/content/a.md",
                "work/site/content/b.md",
            ],
        }
        _normalize_issue_paths(issue, tmp_path)
        assert issue["files"][0] == str(tmp_path / "work/site/content/a.md")
        assert issue["files"][1] == str(tmp_path / "work/site/content/b.md")

    def test_files_list_mixed_relative_absolute(self, tmp_path: Path):
        """Only relative paths in files list are resolved; absolute paths stay."""
        abs_path = str(tmp_path / "work" / "site" / "abs.md")
        issue: Dict[str, Any] = {
            "files": [
                "work/site/content/rel.md",
                abs_path,
            ],
        }
        _normalize_issue_paths(issue, tmp_path)
        assert issue["files"][0] == str(tmp_path / "work/site/content/rel.md")
        assert issue["files"][1] == abs_path

    def test_files_list_missing_safe(self, tmp_path: Path):
        """Issue without files key does not raise."""
        issue: Dict[str, Any] = {"issue_id": "test"}
        _normalize_issue_paths(issue, tmp_path)  # should not raise

    def test_idempotent(self, tmp_path: Path):
        """Calling _normalize_issue_paths twice produces the same result."""
        issue: Dict[str, Any] = {
            "location": {"path": "work/site/content/page.md", "line": 1},
            "files": ["work/site/content/a.md"],
        }
        _normalize_issue_paths(issue, tmp_path)
        first_location = issue["location"]["path"]
        first_file = issue["files"][0]

        _normalize_issue_paths(issue, tmp_path)
        assert issue["location"]["path"] == first_location
        assert issue["files"][0] == first_file

    def test_rundir_prefixed_relative_path_no_duplication(self, tmp_path: Path):
        """Relative path already containing run_dir tail must NOT be doubled.

        Bug: validation_report stores ``runs/test_run/work/site/content/page.md``
        (relative but starts with run_dir tail).  Naive join produces
        ``.../runs/test_run/runs/test_run/work/site/...`` — wrong.
        """
        run_dir = tmp_path / "runs" / "test_run"
        run_dir.mkdir(parents=True)
        issue: Dict[str, Any] = {
            "location": {
                "path": "runs/test_run/work/site/content/page.md",
                "line": 10,
            },
        }
        _normalize_issue_paths(issue, run_dir)
        expected = str(run_dir / "work" / "site" / "content" / "page.md")
        assert issue["location"]["path"] == expected

    def test_rundir_prefixed_files_no_duplication(self, tmp_path: Path):
        """files[] entries with run_dir tail prefix must not be doubled."""
        run_dir = tmp_path / "runs" / "test_run"
        run_dir.mkdir(parents=True)
        issue: Dict[str, Any] = {
            "files": [
                "runs/test_run/work/site/content/a.md",
                "runs/test_run/work/site/content/b.md",
            ],
        }
        _normalize_issue_paths(issue, run_dir)
        assert issue["files"][0] == str(run_dir / "work" / "site" / "content" / "a.md")
        assert issue["files"][1] == str(run_dir / "work" / "site" / "content" / "b.md")

    def test_rundir_prefixed_idempotent(self, tmp_path: Path):
        """Calling twice on a run_dir-prefixed relative path is safe."""
        run_dir = tmp_path / "runs" / "test_run"
        run_dir.mkdir(parents=True)
        issue: Dict[str, Any] = {
            "location": {"path": "runs/test_run/work/site/content/page.md", "line": 1},
            "files": ["runs/test_run/work/site/content/a.md"],
        }
        _normalize_issue_paths(issue, run_dir)
        first_loc = issue["location"]["path"]
        first_file = issue["files"][0]
        _normalize_issue_paths(issue, run_dir)
        assert issue["location"]["path"] == first_loc
        assert issue["files"][0] == first_file


# ---------------------------------------------------------------------------
# Class 1b: Unit tests for _strip_rundir_overlap
# ---------------------------------------------------------------------------

class TestStripRundirOverlap:
    """Direct unit tests for the _strip_rundir_overlap helper."""

    def test_no_overlap(self, tmp_path: Path):
        """Path with no common suffix/prefix is returned unchanged."""
        run_dir = tmp_path / "runs" / "test_run"
        rel = Path("work/site/content/page.md")
        assert _strip_rundir_overlap(rel, run_dir) == rel

    def test_full_tail_overlap(self, tmp_path: Path):
        """Relative path starting with full run_dir tail is stripped."""
        run_dir = tmp_path / "runs" / "test_run"
        rel = Path("runs/test_run/work/site/content/page.md")
        assert _strip_rundir_overlap(rel, run_dir) == Path("work/site/content/page.md")

    def test_partial_tail_overlap(self, tmp_path: Path):
        """Only the last component of run_dir matches first of rel."""
        run_dir = tmp_path / "runs" / "test_run"
        rel = Path("test_run/work/site/content/page.md")
        assert _strip_rundir_overlap(rel, run_dir) == Path("work/site/content/page.md")

    def test_deeper_run_dir(self, tmp_path: Path):
        """Overlap works for deeper run_dir hierarchies."""
        run_dir = tmp_path / "data" / "runs" / "pilot_001" / "run_42"
        rel = Path("runs/pilot_001/run_42/artifacts/report.json")
        assert _strip_rundir_overlap(rel, run_dir) == Path("artifacts/report.json")


# ---------------------------------------------------------------------------
# Class 2: Integration tests for execute_fixer with relative paths
# ---------------------------------------------------------------------------

class TestExecuteFixerPathResolution:
    """Integration tests: execute_fixer correctly resolves relative paths."""

    def _make_validation_report(
        self,
        issues: list,
        ok: bool = False,
    ) -> Dict[str, Any]:
        return {
            "schema_version": "1.0",
            "ok": ok,
            "profile": "local",
            "gates": [{"name": "gate_17_formatting_quality", "ok": not issues}],
            "issues": issues,
        }

    def test_relative_path_formatting_fix_fq4(self, run_dir: Path):
        """FQ-4 fix succeeds when validation_report has relative path."""
        # Create file with adjacent headings (FQ-4 issue)
        content_dir = run_dir / "work" / "site" / "content"
        page = content_dir / "test-page.md"
        page.write_text("---\ntitle: Test\n---\n## Heading One\n## Heading Two\nBody text.\n")

        # Relative path as stored by normalize_report
        rel_path = "work/site/content/test-page.md"
        report = self._make_validation_report([
            {
                "issue_id": "gate17_fq4_test_page_4",
                "gate": "gate_17_formatting_quality",
                "severity": "error",
                "error_code": "G17-FQ-4",
                "message": "Adjacent headings without blank line at line 4",
                "location": {"path": rel_path, "line": 4},
                "status": "OPEN",
            },
        ])
        (run_dir / "artifacts" / "validation_report.json").write_text(
            json.dumps(report), encoding="utf-8"
        )

        result = execute_fixer(run_dir=run_dir, run_config={}, llm_client=None)

        # Fix should succeed (not "File not found")
        assert result["status"] != "unfixable" or "File not found" not in result.get("error_message", "")

    def test_absolute_path_still_works(self, run_dir: Path):
        """Backward compat: absolute paths in issues still work."""
        content_dir = run_dir / "work" / "site" / "content"
        page = content_dir / "abs-test.md"
        page.write_text("---\ntitle: Test\n---\n## H1\n## H2\nText.\n")

        abs_path = str(page)
        report = self._make_validation_report([
            {
                "issue_id": "gate17_fq4_abs_test_4",
                "gate": "gate_17_formatting_quality",
                "severity": "error",
                "error_code": "G17-FQ-4",
                "message": "Adjacent headings at line 4",
                "location": {"path": abs_path, "line": 4},
                "status": "OPEN",
            },
        ])
        (run_dir / "artifacts" / "validation_report.json").write_text(
            json.dumps(report), encoding="utf-8"
        )

        result = execute_fixer(run_dir=run_dir, run_config={}, llm_client=None)

        assert result["status"] != "unfixable" or "File not found" not in result.get("error_message", "")

    def test_truly_missing_file_raises_stale_error(self, run_dir: Path):
        """File that doesn't exist after resolution raises StaleValidationReportError (TC-3450).

        Previously returned status="unfixable"; now the stale path guard fires first and
        raises StaleValidationReportError so the orchestrator can re-run W9.
        """
        report = self._make_validation_report([
            {
                "issue_id": "gate17_fq4_ghost_1",
                "gate": "gate_17_formatting_quality",
                "severity": "error",
                "error_code": "G17-FQ-4",
                "message": "Formatting issue",
                "location": {"path": "work/site/content/nonexistent.md", "line": 1},
                "status": "OPEN",
            },
        ])
        (run_dir / "artifacts" / "validation_report.json").write_text(
            json.dumps(report), encoding="utf-8"
        )

        with pytest.raises(StaleValidationReportError) as exc_info:
            execute_fixer(run_dir=run_dir, run_config={}, llm_client=None)

        # Error should mention the issue_id and the resolved absolute path
        error_msg = str(exc_info.value)
        assert "gate17_fq4_ghost_1" in error_msg
        assert "nonexistent.md" in error_msg

    def test_fix_unresolved_token_with_relative_path(self, run_dir: Path):
        """fix_unresolved_token works after _normalize_issue_paths resolves path."""
        page = run_dir / "work" / "site" / "content" / "token-test.md"
        page.write_text("Line 1\nLine 2\n__PRODUCT_NAME__ here\nLine 4\n")

        issue: Dict[str, Any] = {
            "issue_id": "token_rel",
            "message": "Unresolved template token found: __PRODUCT_NAME__",
            "location": {"path": "work/site/content/token-test.md", "line": 3},
        }

        # Before normalization: Path is relative, fix would fail
        _normalize_issue_paths(issue, run_dir)

        result = fix_unresolved_token(issue, run_dir, None)
        assert result["fixed"] is True
        assert "__PRODUCT_NAME__" not in page.read_text(encoding="utf-8")

    def test_fix_formatting_defect_with_relative_path(self, run_dir: Path):
        """fix_formatting_defect works after _normalize_issue_paths resolves path."""
        page = run_dir / "work" / "site" / "content" / "fmt-test.md"
        page.write_text("---\ntitle: Fmt\n---\n## H1\n## H2\nBody.\n")

        issue: Dict[str, Any] = {
            "issue_id": "fq4_rel",
            "gate": "gate_17_formatting_quality",
            "severity": "error",
            "error_code": "G17-FQ-4",
            "message": "Adjacent headings",
            "location": {"path": "work/site/content/fmt-test.md", "line": 4},
            "status": "OPEN",
        }

        _normalize_issue_paths(issue, run_dir)

        result = fix_formatting_defect(issue, run_dir, None)
        assert result["fixed"] is True
        content = page.read_text(encoding="utf-8")
        # FQ-4 fix inserts blank line between adjacent headings
        assert "## H1\n\n## H2" in content


# ---------------------------------------------------------------------------
# Class 3: TC-3450 — Stale path guard
# ---------------------------------------------------------------------------

class TestStalePathGuard:
    """TC-3450: Stale path guard in execute_fixer().

    When issue.location.path does not exist after resolution, execute_fixer()
    must raise StaleValidationReportError and emit FIXER_STALE_PATH_DETECTED
    instead of returning status='unfixable'.
    """

    def _make_validation_report(self, issues: list) -> Dict[str, Any]:
        return {
            "schema_version": "1.0",
            "ok": False,
            "profile": "local",
            "gates": [{"name": "gate_17_formatting_quality", "ok": False}],
            "issues": issues,
        }

    def _write_report(self, run_dir: Path, issues: list) -> None:
        report = self._make_validation_report(issues)
        (run_dir / "artifacts" / "validation_report.json").write_text(
            json.dumps(report), encoding="utf-8"
        )

    def _make_fq4_issue(self, rel_path: str) -> Dict[str, Any]:
        return {
            "issue_id": "tc3450_stale_path_001",
            "gate": "gate_17_formatting_quality",
            "severity": "error",
            "error_code": "G17-FQ-4",
            "message": "Adjacent headings",
            "location": {"path": rel_path, "line": 4},
            "status": "OPEN",
        }

    def test_stale_path_raises_stale_validation_report_error(self, run_dir: Path):
        """Missing location.path → StaleValidationReportError raised (not unfixable)."""
        self._write_report(run_dir, [self._make_fq4_issue("work/site/content/ghost.md")])

        with pytest.raises(StaleValidationReportError):
            execute_fixer(run_dir=run_dir, run_config={}, llm_client=None)

    def test_stale_path_error_message_contains_path_and_issue_id(self, run_dir: Path):
        """StaleValidationReportError message includes issue_id and resolved path."""
        self._write_report(run_dir, [self._make_fq4_issue("work/site/content/ghost-page.md")])

        with pytest.raises(StaleValidationReportError) as exc_info:
            execute_fixer(run_dir=run_dir, run_config={}, llm_client=None)

        error_msg = str(exc_info.value)
        assert "tc3450_stale_path_001" in error_msg, f"issue_id missing from: {error_msg}"
        assert "ghost-page.md" in error_msg, f"path missing from: {error_msg}"

    def test_existing_path_guard_passes_no_exception(self, run_dir: Path):
        """Existing location.path → stale-path guard passes; fix proceeds normally."""
        page = run_dir / "work" / "site" / "content" / "real-page.md"
        page.write_text("---\ntitle: Real\n---\n## H1\n## H2\nText.\n")

        self._write_report(run_dir, [self._make_fq4_issue("work/site/content/real-page.md")])

        # Must NOT raise StaleValidationReportError; guard is a no-op for existing files
        try:
            execute_fixer(run_dir=run_dir, run_config={}, llm_client=None)
        except StaleValidationReportError:
            pytest.fail("StaleValidationReportError raised for an existing location.path")

    def test_no_location_path_guard_skipped(self, run_dir: Path):
        """Issue without location.path → stale-path guard skipped silently."""
        # Scaffold issue: has no location.path, only a message
        issue = {
            "issue_id": "tc3450_no_loc_001",
            "gate": "gate_scaffold_leak",
            "severity": "error",
            "error_code": "SCAFFOLD_LLM_META",
            "message": "LLM meta-commentary detected",
            "status": "OPEN",
        }
        self._write_report(run_dir, [issue])

        # Guard must NOT fire for issues without location.path
        try:
            execute_fixer(run_dir=run_dir, run_config={}, llm_client=None)
        except StaleValidationReportError:
            pytest.fail("StaleValidationReportError raised for issue without location.path")
