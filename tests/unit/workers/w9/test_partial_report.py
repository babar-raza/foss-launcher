"""Tests for partial report marking during heal fast inner-loop (TC-3641).

W9 ``execute_validator()`` must annotate reports with ``partial: True`` and
``gate_filter`` when the runner skipped gates via ``_heal_gate_filter``.

Spec: specs/50_healing_cost_reduction.md §5.5.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest


def _setup_run_dir(tmp_path: Path) -> Path:
    """Create a minimal run_dir for W9."""
    run_dir = tmp_path / "runs" / "r_test"
    run_dir.mkdir(parents=True)
    (run_dir / "artifacts").mkdir()
    (run_dir / "work" / "site" / "content").mkdir(parents=True)
    (run_dir / "events.ndjson").write_text("", encoding="utf-8")
    return run_dir


def _mock_run_gates_partial(run_dir: Path, run_config: Dict, profile: str):
    """Simulate run_gates returning some skipped gates."""
    return (
        [
            {"name": "gate_1_schema_validation", "ok": True},
            {"name": "gate_truth_layer_completeness", "ok": True, "skipped": True},
            {"name": "gate_4_frontmatter_required_fields", "ok": False},
        ],
        [
            {
                "issue_id": "g4_err",
                "gate": "gate_4_frontmatter_required_fields",
                "severity": "error",
                "message": "missing field",
                "status": "OPEN",
            }
        ],
    )


def _mock_run_gates_full(run_dir: Path, run_config: Dict, profile: str):
    """Simulate run_gates with no skipped gates (full run)."""
    return (
        [
            {"name": "gate_1_schema_validation", "ok": True},
            {"name": "gate_truth_layer_completeness", "ok": True},
        ],
        [],
    )


class TestPartialReport:
    """Tests for partial report annotation by W9 (TC-3641)."""

    @patch("launch.workers.w9_validator.worker.emit_quality_feedback")
    @patch("launch.workers.w9_validator.worker.emit_event")
    @patch("launch.validation_engine.runner.run_gates")
    def test_partial_flag_set(
        self, mock_rg: MagicMock, mock_emit: MagicMock, mock_qf: MagicMock, tmp_path: Path
    ) -> None:
        """Report has ``partial: True`` + ``gate_filter`` list when gates skipped."""
        run_dir = _setup_run_dir(tmp_path)
        mock_rg.side_effect = _mock_run_gates_partial

        from launch.workers.w9_validator.worker import execute_validator

        report = execute_validator(run_dir, {"validation_profile": "local"})

        assert report.get("partial") is True
        assert "gate_filter" in report
        # gate_filter should list only non-skipped gates
        assert "gate_truth_layer_completeness" not in report["gate_filter"]
        assert "gate_1_schema_validation" in report["gate_filter"]

    @patch("launch.workers.w9_validator.worker.emit_quality_feedback")
    @patch("launch.workers.w9_validator.worker.emit_event")
    @patch("launch.validation_engine.runner.run_gates")
    def test_partial_flag_absent_full_run(
        self, mock_rg: MagicMock, mock_emit: MagicMock, mock_qf: MagicMock, tmp_path: Path
    ) -> None:
        """No ``partial`` key on full run (no skipped gates)."""
        run_dir = _setup_run_dir(tmp_path)
        mock_rg.side_effect = _mock_run_gates_full

        from launch.workers.w9_validator.worker import execute_validator

        report = execute_validator(run_dir, {"validation_profile": "local"})

        assert "partial" not in report
        assert "gate_filter" not in report

    @patch("launch.workers.w9_validator.worker.emit_quality_feedback")
    @patch("launch.workers.w9_validator.worker.emit_event")
    @patch("launch.validation_engine.runner.run_gates")
    def test_gate_filter_matches_executed(
        self, mock_rg: MagicMock, mock_emit: MagicMock, mock_qf: MagicMock, tmp_path: Path
    ) -> None:
        """``gate_filter`` exactly equals the set of non-skipped gate IDs."""
        run_dir = _setup_run_dir(tmp_path)
        mock_rg.side_effect = _mock_run_gates_partial

        from launch.workers.w9_validator.worker import execute_validator

        report = execute_validator(run_dir, {"validation_profile": "local"})

        executed_ids = {
            g["name"]
            for g in report["gates"]
            if not g.get("skipped")
        }
        assert set(report["gate_filter"]) == executed_ids
