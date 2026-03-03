"""TC-3617: Tests for Gate — Review Report Required.

Covers:
- review_report.json present with PASS → gate passes (all profiles)
- review_report.json missing → error in ci, blocker in prod, info in local
- review_report.json with non-PASS status → error in ci, blocker in prod, info in local
- Corrupt JSON → error in ci
- review_enabled: False → gate no-ops (always passes, no issues)
"""

from __future__ import annotations

import json
import pytest
from pathlib import Path

from src.launch.workers.w9_validator.gates.gate_review_report_required import (
    execute_gate,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_review_report(run_dir: Path, data: dict) -> None:
    """Write review_report.json to artifacts/."""
    arts = run_dir / "artifacts"
    arts.mkdir(parents=True, exist_ok=True)
    (arts / "review_report.json").write_text(
        json.dumps(data), encoding="utf-8",
    )


def _passing_report() -> dict:
    return {"overall_status": "PASS", "pages_reviewed": 5, "pages_passed": 5}


# ---------------------------------------------------------------------------
# Report present with PASS
# ---------------------------------------------------------------------------

class TestPassingReport:
    """Gate passes when review_report.json exists and overall_status==PASS."""

    def test_pass_when_report_exists_and_passes(self, tmp_path: Path) -> None:
        _write_review_report(tmp_path, _passing_report())
        passed, issues = execute_gate(tmp_path, {}, "ci")
        assert passed is True
        assert issues == []

    def test_pass_when_overall_status_pass_local(self, tmp_path: Path) -> None:
        _write_review_report(tmp_path, _passing_report())
        passed, issues = execute_gate(tmp_path, {}, "local")
        assert passed is True
        assert issues == []


# ---------------------------------------------------------------------------
# Report missing
# ---------------------------------------------------------------------------

class TestReportMissing:
    """Gate behavior when review_report.json is absent."""

    def test_fail_when_report_missing_ci(self, tmp_path: Path) -> None:
        (tmp_path / "artifacts").mkdir(parents=True, exist_ok=True)
        passed, issues = execute_gate(tmp_path, {}, "ci")
        assert passed is False
        assert len(issues) == 1
        assert issues[0]["severity"] == "error"
        assert issues[0]["error_code"] == "REVIEW_REPORT_MISSING"

    def test_fail_when_report_missing_prod(self, tmp_path: Path) -> None:
        (tmp_path / "artifacts").mkdir(parents=True, exist_ok=True)
        passed, issues = execute_gate(tmp_path, {}, "prod")
        assert passed is False
        assert len(issues) == 1
        assert issues[0]["severity"] == "blocker"
        assert issues[0]["error_code"] == "REVIEW_REPORT_MISSING"

    def test_info_when_report_missing_local(self, tmp_path: Path) -> None:
        (tmp_path / "artifacts").mkdir(parents=True, exist_ok=True)
        passed, issues = execute_gate(tmp_path, {}, "local")
        assert passed is True  # info severity does not fail gate
        assert len(issues) == 1
        assert issues[0]["severity"] == "info"
        assert issues[0]["error_code"] == "REVIEW_REPORT_MISSING"


# ---------------------------------------------------------------------------
# Report present with non-PASS status
# ---------------------------------------------------------------------------

class TestNonPassStatus:
    """Gate fails when overall_status is not PASS in ci/prod."""

    def test_fail_when_overall_status_needs_changes(self, tmp_path: Path) -> None:
        _write_review_report(tmp_path, {
            "overall_status": "NEEDS_CHANGES",
            "pages_reviewed": 5,
            "pages_failed": 2,
        })
        passed, issues = execute_gate(tmp_path, {}, "ci")
        assert passed is False
        assert len(issues) == 1
        assert issues[0]["severity"] == "error"
        assert issues[0]["error_code"] == "REVIEW_NOT_PASS"
        assert "NEEDS_CHANGES" in issues[0]["message"]

    def test_fail_when_overall_status_reject(self, tmp_path: Path) -> None:
        _write_review_report(tmp_path, {
            "overall_status": "REJECT",
            "pages_reviewed": 5,
            "pages_failed": 5,
        })
        passed, issues = execute_gate(tmp_path, {}, "prod")
        assert passed is False
        assert len(issues) == 1
        assert issues[0]["severity"] == "blocker"
        assert issues[0]["error_code"] == "REVIEW_NOT_PASS"


# ---------------------------------------------------------------------------
# Corrupt report
# ---------------------------------------------------------------------------

class TestCorruptReport:
    """Gate fails when review_report.json is invalid JSON."""

    def test_fail_when_report_corrupt(self, tmp_path: Path) -> None:
        arts = tmp_path / "artifacts"
        arts.mkdir(parents=True, exist_ok=True)
        (arts / "review_report.json").write_text(
            "{{not valid json", encoding="utf-8",
        )
        passed, issues = execute_gate(tmp_path, {}, "ci")
        assert passed is False
        assert len(issues) == 1
        assert issues[0]["severity"] == "error"
        assert issues[0]["error_code"] == "REVIEW_REPORT_MISSING"


# ---------------------------------------------------------------------------
# review_enabled: False — gate no-op (SR-01 regression guard)
# ---------------------------------------------------------------------------

class TestReviewDisabled:
    """When review_enabled is False, gate is a no-op regardless of artifact state."""

    def test_noop_when_review_disabled_report_missing(self, tmp_path: Path) -> None:
        """No artifact + review_enabled=False → gate passes with 0 issues."""
        run_config = {"review_enabled": False}
        passed, issues = execute_gate(tmp_path, run_config, "ci")
        assert passed is True
        assert issues == []

    def test_noop_when_review_disabled_report_failing(self, tmp_path: Path) -> None:
        """Non-PASS report + review_enabled=False → gate passes with 0 issues."""
        _write_review_report(tmp_path, {"overall_status": "REJECT"})
        run_config = {"review_enabled": False}
        passed, issues = execute_gate(tmp_path, run_config, "prod")
        assert passed is True
        assert issues == []
