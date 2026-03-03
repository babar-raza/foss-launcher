"""Unit tests for the launch heal self-driving healing iteration (TC-2950).

Tests the core healing loop: worker selection, stop conditions,
artifact writing, event emission, and mode behavior.
All tests are fast (no network, no LLM — resume is mocked).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

from launch.cli.heal import (
    HealResult,
    HealStep,
    _CHECKPOINT_CONTENT_DIRS,
    _HEAL_SAFETY_GATES,
    _WORKER_CHECKPOINT_SCOPES,
    _create_checkpoint,
    _win_path,
    choose_worker,
    count_failed_gates,
    extract_worker_from_recommendation,
    is_stuck,
    run_heal_loop,
    write_heal_plan,
)
from launch.orchestrator.graph import DRIVE_GOAL_DRAFT, DRIVE_GOAL_KEY, DRIVE_GOAL_VALIDATE


# ── Helpers (reuse patterns from test_triage.py) ─────────────────────────────


def _make_gate(name: str, ok: bool = True) -> Dict[str, Any]:
    return {"name": name, "ok": ok}


def _make_issue(
    gate: str,
    severity: str = "error",
    error_code: str = "",
    message: str = "test issue",
) -> Dict[str, Any]:
    issue: Dict[str, Any] = {
        "issue_id": f"{gate}_{severity}_{error_code or 'nocode'}",
        "gate": gate,
        "severity": severity,
        "message": message,
        "status": "OPEN",
    }
    if error_code:
        issue["error_code"] = error_code
    return issue


def _make_report(
    gates: List[Dict[str, Any]],
    issues: List[Dict[str, Any]],
    ok: bool | None = None,
) -> Dict[str, Any]:
    if ok is None:
        ok = all(g["ok"] for g in gates)
    return {
        "schema_version": "1.0",
        "ok": ok,
        "profile": "local",
        "gates": gates,
        "issues": issues,
    }


def _write_report(run_dir: Path, report: Dict[str, Any]) -> Path:
    artifacts = run_dir / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    report_path = artifacts / "validation_report.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")
    return report_path


def _all_pass_report() -> Dict[str, Any]:
    return _make_report(
        gates=[
            _make_gate("gate_1_schema_validation"),
            _make_gate("gate_5_cross_page_link_validity"),
        ],
        issues=[],
    )


def _truth_missing_report() -> Dict[str, Any]:
    return _make_report(
        gates=[
            _make_gate("gate_truth_layer_completeness", ok=False),
            _make_gate("gate_5_cross_page_link_validity"),
        ],
        issues=[
            _make_issue("gate_truth_layer_completeness", "error", "TRUTH_MISSING"),
        ],
    )


def _code_fence_report() -> Dict[str, Any]:
    return _make_report(
        gates=[
            _make_gate("gate_15b_code_fence_api", ok=False),
            _make_gate("gate_5_cross_page_link_validity"),
        ],
        issues=[
            _make_issue("gate_15b_code_fence_api", "error", "HALLUCINATED_API"),
        ],
    )


def _scaffold_report() -> Dict[str, Any]:
    return _make_report(
        gates=[
            _make_gate("gate_scaffold_leak", ok=False),
            _make_gate("gate_17_formatting_quality", ok=False),
        ],
        issues=[
            _make_issue("gate_scaffold_leak", "error", "SCAFFOLD_LEAK"),
            _make_issue("gate_17_formatting_quality", "error", "FQ-1"),
        ],
    )


def _link_report() -> Dict[str, Any]:
    return _make_report(
        gates=[
            _make_gate("gate_5_cross_page_link_validity", ok=False),
        ],
        issues=[
            _make_issue("gate_5_cross_page_link_validity", "error", "LINK_BROKEN"),
        ],
    )


def _multi_issue_report() -> Dict[str, Any]:
    return _make_report(
        gates=[
            _make_gate("gate_truth_layer_completeness", ok=False),
            _make_gate("gate_scaffold_leak", ok=False),
        ],
        issues=[
            _make_issue("gate_truth_layer_completeness", "error", "TRUTH_MISSING"),
            _make_issue("gate_scaffold_leak", "error", "SCAFFOLD_LEAK"),
        ],
    )


def _setup_run_dir(tmp_path: Path, report: Dict[str, Any] | None = None) -> Path:
    """Create a minimal run_dir structure."""
    run_dir = tmp_path / "runs" / "r_test"
    run_dir.mkdir(parents=True)
    (run_dir / "artifacts").mkdir()
    (run_dir / "events.ndjson").write_text("", encoding="utf-8")

    # Minimal run_config
    config = {"product_slug": "test-product", "github_ref": "main"}
    import yaml
    (run_dir / "run_config.yaml").write_text(yaml.dump(config), encoding="utf-8")

    if report is not None:
        _write_report(run_dir, report)
    return run_dir


# ── extract_worker_from_recommendation ────────────────────────────────────────


class TestExtractWorker:
    def test_extracts_w5(self) -> None:
        rec = {"command": "launch resume --run-dir /path --from-worker W5", "reason": "test"}
        assert extract_worker_from_recommendation(rec) == "W5"

    def test_extracts_w10(self) -> None:
        rec = {"command": "launch resume --run-dir /path --from-worker W10", "reason": "test"}
        assert extract_worker_from_recommendation(rec) == "W10"

    def test_extracts_w2(self) -> None:
        rec = {"command": "launch resume --run-dir /path --from-worker W2", "reason": "test"}
        assert extract_worker_from_recommendation(rec) == "W2"

    def test_empty_command(self) -> None:
        rec = {"command": "", "reason": "test"}
        assert extract_worker_from_recommendation(rec) == ""

    def test_missing_command_key(self) -> None:
        rec = {"reason": "test"}
        assert extract_worker_from_recommendation(rec) == ""


# ── count_failed_gates ────────────────────────────────────────────────────────


class TestCountFailedGates:
    def test_no_failures(self) -> None:
        report = _all_pass_report()
        assert count_failed_gates(report) == 0

    def test_one_failure(self) -> None:
        report = _truth_missing_report()
        assert count_failed_gates(report) == 1

    def test_two_failures(self) -> None:
        report = _multi_issue_report()
        assert count_failed_gates(report) == 2

    def test_empty_gates(self) -> None:
        assert count_failed_gates({"gates": []}) == 0


# ── choose_worker ─────────────────────────────────────────────────────────────


class TestChooseWorker:
    def test_strict_picks_first(self) -> None:
        recs = [
            {"command": "launch resume --run-dir /p --from-worker W2", "reason": "truth"},
            {"command": "launch resume --run-dir /p --from-worker W10", "reason": "scaffold"},
        ]
        result = choose_worker(recs, "strict", 3, [])
        assert result == ("W2", "truth")

    def test_aggressive_skips_tried_without_improvement(self) -> None:
        recs = [
            {"command": "launch resume --run-dir /p --from-worker W2", "reason": "truth"},
            {"command": "launch resume --run-dir /p --from-worker W10", "reason": "scaffold"},
        ]
        history = [HealStep(0, "W2", "truth", [], 3, 3)]
        result = choose_worker(recs, "aggressive", 3, history)
        assert result == ("W10", "scaffold")

    def test_strict_does_not_skip_tried(self) -> None:
        recs = [
            {"command": "launch resume --run-dir /p --from-worker W2", "reason": "truth"},
        ]
        history = [HealStep(0, "W2", "truth", [], 3, 3)]
        result = choose_worker(recs, "strict", 3, history)
        assert result == ("W2", "truth")

    def test_aggressive_all_tried_returns_none(self) -> None:
        recs = [
            {"command": "launch resume --run-dir /p --from-worker W2", "reason": "truth"},
        ]
        history = [HealStep(0, "W2", "truth", [], 3, 3)]
        result = choose_worker(recs, "aggressive", 3, history)
        assert result is None

    def test_empty_recommendations(self) -> None:
        assert choose_worker([], "strict", 3, []) is None


# ── is_stuck ──────────────────────────────────────────────────────────────────


class TestIsStuck:
    def test_no_history_not_stuck(self) -> None:
        assert not is_stuck([], "W2", "truth")

    def test_same_worker_no_improvement_is_stuck(self) -> None:
        history = [HealStep(0, "W2", "truth", [], 3, 3)]
        assert is_stuck(history, "W2", "truth")

    def test_same_worker_with_improvement_not_stuck(self) -> None:
        history = [HealStep(0, "W2", "truth", [], 3, 2)]
        assert not is_stuck(history, "W2", "truth")

    def test_different_worker_not_stuck(self) -> None:
        history = [HealStep(0, "W10", "scaffold", [], 3, 3)]
        assert not is_stuck(history, "W2", "truth")

    def test_regressed_outcome_excluded_from_stuck(self) -> None:
        """outcome='regressed' steps are skipped — not counted as tried-without-improvement."""
        step = HealStep(0, "W2", "truth", [], 3, 5, notes="regressed: 3 → 5", outcome="regressed")
        assert not is_stuck([step], "W2", "truth")

    def test_improved_outcome_excluded_from_stuck(self) -> None:
        """outcome='improved' steps are skipped — they represent real progress."""
        step = HealStep(0, "W2", "truth", [], 3, 3, notes="issues 5 → 3", outcome="improved")
        assert not is_stuck([step], "W2", "truth")


# ── run_heal_loop (integration with mocked resume) ───────────────────────────


def _mock_run_result(exit_code: int = 0) -> MagicMock:
    result = MagicMock()
    result.exit_code = exit_code
    result.final_state = "DONE" if exit_code == 0 else "FAILED"
    result.run_id = "r_test"
    return result


class TestRunHealLoop:
    """Integration tests for the main healing loop.

    All tests mock execute_run_from_node to avoid real pipeline execution.
    The mock's side_effect replaces validation_report.json after each call.
    """

    @patch("launch.orchestrator.run_loop.execute_run_from_node")
    def test_already_passing(self, mock_resume: MagicMock, tmp_path: Path) -> None:
        """All gates pass at start — should return immediately with 0 steps."""
        run_dir = _setup_run_dir(tmp_path, _all_pass_report())

        result = run_heal_loop("r_test", run_dir, {}, max_steps=5)

        assert result.stop_reason == "all_gates_pass"
        assert len(result.steps) == 0
        assert result.final_failed_gate_count == 0
        mock_resume.assert_not_called()

        # heal_plan.json must exist
        plan_path = run_dir / "artifacts" / "heal_plan.json"
        assert plan_path.exists()

    @patch("launch.orchestrator.run_loop.execute_run_from_node")
    def test_truth_missing_then_pass(self, mock_resume: MagicMock, tmp_path: Path) -> None:
        """Step 1: truth missing → picks W2. Resume fixes it → all pass."""
        run_dir = _setup_run_dir(tmp_path, _truth_missing_report())

        def resume_side_effect(run_id, rd, rc, worker):
            # After W2 resume, replace report with all-pass
            _write_report(rd, _all_pass_report())
            return _mock_run_result(0)

        mock_resume.side_effect = resume_side_effect

        result = run_heal_loop("r_test", run_dir, {}, max_steps=5)

        assert result.stop_reason == "all_gates_pass"
        assert len(result.steps) == 1
        assert result.steps[0].chosen_worker == "W2"
        assert result.steps[0].failed_gate_count_before == 1
        assert result.steps[0].failed_gate_count_after == 0
        assert result.final_failed_gate_count == 0

    @patch("launch.orchestrator.run_loop.execute_run_from_node")
    def test_code_fence_picks_w5(self, mock_resume: MagicMock, tmp_path: Path) -> None:
        """Code fence API issue → first recommendation is W5."""
        run_dir = _setup_run_dir(tmp_path, _code_fence_report())

        def resume_side_effect(run_id, rd, rc, worker):
            _write_report(rd, _all_pass_report())
            return _mock_run_result(0)

        mock_resume.side_effect = resume_side_effect

        result = run_heal_loop("r_test", run_dir, {}, max_steps=5)

        assert result.steps[0].chosen_worker == "W5"
        assert result.stop_reason == "all_gates_pass"

    @patch("launch.orchestrator.run_loop.execute_run_from_node")
    def test_scaffold_picks_w10(self, mock_resume: MagicMock, tmp_path: Path) -> None:
        """Scaffold leak + FQ issues → picks W10."""
        run_dir = _setup_run_dir(tmp_path, _scaffold_report())

        def resume_side_effect(run_id, rd, rc, worker):
            _write_report(rd, _all_pass_report())
            return _mock_run_result(0)

        mock_resume.side_effect = resume_side_effect

        result = run_heal_loop("r_test", run_dir, {}, max_steps=5)

        assert result.steps[0].chosen_worker == "W10"
        assert result.stop_reason == "all_gates_pass"

    @patch("launch.orchestrator.run_loop.execute_run_from_node")
    def test_links_picks_w8(self, mock_resume: MagicMock, tmp_path: Path) -> None:
        """Link issues → picks W8."""
        run_dir = _setup_run_dir(tmp_path, _link_report())

        def resume_side_effect(run_id, rd, rc, worker):
            _write_report(rd, _all_pass_report())
            return _mock_run_result(0)

        mock_resume.side_effect = resume_side_effect

        result = run_heal_loop("r_test", run_dir, {}, max_steps=5)

        assert result.steps[0].chosen_worker == "W8"
        assert result.stop_reason == "all_gates_pass"

    @patch("launch.orchestrator.run_loop.execute_run_from_node")
    def test_stuck_detection(self, mock_resume: MagicMock, tmp_path: Path) -> None:
        """Same (W10, reason) repeated with no gate improvement → stuck."""
        run_dir = _setup_run_dir(tmp_path, _scaffold_report())

        def resume_side_effect(run_id, rd, rc, worker):
            # Report unchanged (still 2 failures)
            _write_report(rd, _scaffold_report())
            return _mock_run_result(0)

        mock_resume.side_effect = resume_side_effect

        result = run_heal_loop("r_test", run_dir, {}, max_steps=5)

        assert result.stop_reason == "stuck"
        assert len(result.steps) == 1
        assert result.final_failed_gate_count == 2

    @patch("launch.orchestrator.run_loop.execute_run_from_node")
    def test_max_steps(self, mock_resume: MagicMock, tmp_path: Path) -> None:
        """Max steps reached without convergence.

        TC-3600: Uses multi-issue report (W2 + W10 recommendations) and
        aggressive mode so that both workers are tried before max_steps
        is reached.  Each step produces no change (same report).
        """
        run_dir = _setup_run_dir(tmp_path, _multi_issue_report())

        def resume_side_effect(run_id, rd, rc, worker):
            # Always write the same report — no change, no regression
            _write_report(rd, _multi_issue_report())
            return _mock_run_result(0)

        mock_resume.side_effect = resume_side_effect

        result = run_heal_loop("r_test", run_dir, {}, max_steps=2, mode="aggressive")

        assert result.stop_reason == "max_steps"
        assert len(result.steps) == 2

    @patch("launch.orchestrator.run_loop.execute_run_from_node")
    def test_dry_run(self, mock_resume: MagicMock, tmp_path: Path) -> None:
        """Dry-run records planned step but does NOT call execute_run_from_node."""
        run_dir = _setup_run_dir(tmp_path, _truth_missing_report())

        result = run_heal_loop("r_test", run_dir, {}, dry_run=True)

        assert result.stop_reason == "dry_run"
        assert len(result.steps) == 1
        assert result.steps[0].notes == "dry-run"
        assert result.steps[0].outcome == "skipped"
        assert result.steps[0].chosen_worker == "W2"
        mock_resume.assert_not_called()

    @patch("launch.orchestrator.run_loop.execute_run_from_node")
    def test_aggressive_mode_tries_alternative(self, mock_resume: MagicMock, tmp_path: Path) -> None:
        """Aggressive mode: if first rec doesn't help, tries next recommendation."""
        run_dir = _setup_run_dir(tmp_path, _multi_issue_report())
        call_count = 0

        def resume_side_effect(run_id, rd, rc, worker):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # W2 doesn't help (still 2 failures)
                _write_report(rd, _multi_issue_report())
            else:
                # W10 fixes everything
                _write_report(rd, _all_pass_report())
            return _mock_run_result(0)

        mock_resume.side_effect = resume_side_effect

        result = run_heal_loop("r_test", run_dir, {}, max_steps=5, mode="aggressive")

        assert len(result.steps) >= 2
        assert result.steps[0].chosen_worker == "W2"
        assert result.steps[1].chosen_worker == "W10"
        assert result.stop_reason == "all_gates_pass"

    @patch("launch.orchestrator.run_loop.execute_run_from_node")
    def test_heal_plan_json_written(self, mock_resume: MagicMock, tmp_path: Path) -> None:
        """heal_plan.json artifact has correct structure."""
        run_dir = _setup_run_dir(tmp_path, _truth_missing_report())

        def resume_side_effect(run_id, rd, rc, worker):
            _write_report(rd, _all_pass_report())
            return _mock_run_result(0)

        mock_resume.side_effect = resume_side_effect

        result = run_heal_loop("r_test", run_dir, {})

        plan_path = run_dir / "artifacts" / "heal_plan.json"
        assert plan_path.exists()

        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        assert plan["schema_version"] == "1.0"
        assert plan["run_id"] == "r_test"
        assert plan["mode"] == "strict"
        assert plan["stop_reason"] == "all_gates_pass"
        assert len(plan["steps"]) == 1
        assert plan["steps"][0]["chosen_worker"] == "W2"
        assert plan["final_failed_gate_count"] == 0
        assert plan["started_at_utc"]
        assert plan["finished_at_utc"]

    @patch("launch.orchestrator.run_loop.execute_run_from_node")
    def test_events_emitted(self, mock_resume: MagicMock, tmp_path: Path) -> None:
        """events.ndjson contains HEAL_STEP_STARTED, HEAL_STEP_COMPLETED, HEAL_STOPPED."""
        run_dir = _setup_run_dir(tmp_path, _truth_missing_report())

        def resume_side_effect(run_id, rd, rc, worker):
            _write_report(rd, _all_pass_report())
            return _mock_run_result(0)

        mock_resume.side_effect = resume_side_effect

        run_heal_loop("r_test", run_dir, {})

        events_text = (run_dir / "events.ndjson").read_text(encoding="utf-8")
        events = [json.loads(line) for line in events_text.strip().split("\n") if line.strip()]

        event_types = [e["type"] for e in events]
        assert "HEAL_STEP_STARTED" in event_types
        assert "HEAL_STEP_COMPLETED" in event_types
        assert "HEAL_STOPPED" in event_types

    @patch("launch.orchestrator.run_loop.execute_run_from_node")
    def test_no_validation_report_runs_w9_first(self, mock_resume: MagicMock, tmp_path: Path) -> None:
        """No validation_report.json at start → calls W9 first, then proceeds."""
        run_dir = _setup_run_dir(tmp_path, report=None)  # No report
        call_count = 0

        def resume_side_effect(run_id, rd, rc, worker):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # W9 produces a report with failures
                assert worker == "W9"
                _write_report(rd, _scaffold_report())
            else:
                # W10 fixes everything
                _write_report(rd, _all_pass_report())
            return _mock_run_result(0)

        mock_resume.side_effect = resume_side_effect

        result = run_heal_loop("r_test", run_dir, {})

        # First call should be W9 (to produce report), then W10 to fix
        assert call_count >= 2
        assert result.steps[0].chosen_worker == "W10"

    @patch("launch.orchestrator.run_loop.execute_run_from_node")
    def test_heal_skips_to_next_on_exit_code_2(
        self, mock_resume: MagicMock, tmp_path: Path
    ) -> None:
        """TC-3210: exit_code=2 on first worker → heal continues to next worker."""
        run_dir = _setup_run_dir(tmp_path, _multi_issue_report())
        call_count = 0

        def resume_side_effect(run_id, rd, rc, worker):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # W2 crashes (exit_code=2)
                raise RuntimeError("repo unavailable")
            else:
                # W10 fixes everything
                _write_report(rd, _all_pass_report())
                return _mock_run_result(0)

        mock_resume.side_effect = resume_side_effect

        result = run_heal_loop("r_test", run_dir, {}, max_steps=5, mode="strict")

        assert len(result.steps) >= 2
        assert result.steps[0].chosen_worker == "W2"
        assert result.steps[0].exit_code == 2
        assert result.steps[1].chosen_worker == "W10"
        assert result.stop_reason == "all_gates_pass"

    @patch("launch.orchestrator.run_loop.execute_run_from_node")
    def test_heal_stuck_when_all_recommendations_exit_code_2(
        self, mock_resume: MagicMock, tmp_path: Path
    ) -> None:
        """TC-3210: all recommendations crash (exit_code=2) → stuck."""
        run_dir = _setup_run_dir(tmp_path, _multi_issue_report())

        def resume_side_effect(run_id, rd, rc, worker):
            raise RuntimeError("worker crashed")

        mock_resume.side_effect = resume_side_effect

        result = run_heal_loop("r_test", run_dir, {}, max_steps=5, mode="strict")

        assert result.stop_reason == "stuck"
        assert all(s.exit_code == 2 for s in result.steps)
        assert result.final_failed_gate_count == 2

    @patch("launch.orchestrator.run_loop.execute_run_from_node")
    def test_heal_exit_code_2_does_not_block_other_workers(
        self, mock_resume: MagicMock, tmp_path: Path
    ) -> None:
        """TC-3210: W2 crash does not prevent W10 from running successfully."""
        run_dir = _setup_run_dir(tmp_path, _multi_issue_report())
        workers_called: list = []

        def resume_side_effect(run_id, rd, rc, worker):
            workers_called.append(worker)
            if worker == "W2":
                raise RuntimeError("no network")
            # W10 succeeds and reduces failures
            _write_report(rd, _make_report(
                gates=[
                    _make_gate("gate_truth_layer_completeness", ok=False),
                    _make_gate("gate_scaffold_leak"),
                ],
                issues=[
                    _make_issue("gate_truth_layer_completeness", "error", "TRUTH_MISSING"),
                ],
            ))
            return _mock_run_result(0)

        mock_resume.side_effect = resume_side_effect

        result = run_heal_loop("r_test", run_dir, {}, max_steps=5, mode="strict")

        assert "W2" in workers_called
        assert "W10" in workers_called
        # W10 reduced failures from 2 to 1
        w10_step = [s for s in result.steps if s.chosen_worker == "W10"][0]
        assert w10_step.failed_gate_count_after < w10_step.failed_gate_count_before


# ── write_heal_plan ───────────────────────────────────────────────────────────


class TestWriteHealPlan:
    def test_writes_valid_json(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "runs" / "r_test"
        (run_dir / "artifacts").mkdir(parents=True)

        result = HealResult(
            run_id="r_test",
            mode="strict",
            max_steps=5,
            steps=[
                HealStep(0, "W2", "truth missing", [{"command": "x", "reason": "y"}], 3, 1, 0, ""),
            ],
            stop_reason="all_gates_pass",
            final_failed_gate_count=0,
            started_at_utc="2026-02-27T00:00:00+00:00",
            finished_at_utc="2026-02-27T00:01:00+00:00",
        )

        path = write_heal_plan(run_dir, result)
        assert path.exists()

        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["schema_version"] == "1.0"
        assert data["stop_reason"] == "all_gates_pass"
        assert len(data["steps"]) == 1


# ── TC-3570: _win_path() Windows MAX_PATH helper ──────────────────────────────


class TestCheckpointMaxPath:
    """Tests for _win_path() Windows long-path helper (TC-3570)."""

    def test_win_path_adds_prefix_on_win32(self, tmp_path: Path) -> None:
        """_win_path() adds \\?\\ prefix on Windows to bypass MAX_PATH."""
        with patch("launch.cli.heal.sys.platform", "win32"):
            result = _win_path(tmp_path)
        result_str = str(result)
        assert result_str.startswith("\\\\?\\"), (
            f"Expected \\\\?\\ prefix on win32, got: {result_str}"
        )

    def test_win_path_noop_on_non_windows(self, tmp_path: Path) -> None:
        """_win_path() is a no-op on Linux/macOS."""
        with patch("launch.cli.heal.sys.platform", "linux"):
            result = _win_path(tmp_path)
        assert result == tmp_path

    def test_win_path_idempotent(self, tmp_path: Path) -> None:
        """_win_path() called twice on the same path returns the same result."""
        with patch("launch.cli.heal.sys.platform", "win32"):
            first = _win_path(tmp_path)
            second = _win_path(first)
        assert str(first) == str(second)

    def test_win_path_unc_prefix(self) -> None:
        """UNC paths get \\\\?\\UNC\\ prefix on win32 (Windows-only)."""
        import sys as _sys
        if _sys.platform != "win32":
            pytest.skip("UNC path semantics only meaningful on Windows")
        unc_path = Path("\\\\server\\share\\deep\\nested\\directory")
        result = _win_path(unc_path)
        assert str(result).startswith("\\\\?\\UNC\\")

    def test_win_path_already_prefixed_not_double_prefixed(self, tmp_path: Path) -> None:
        """A path already starting with \\?\\ is NOT double-prefixed."""
        with patch("launch.cli.heal.sys.platform", "win32"):
            prefixed = _win_path(tmp_path)
            double = _win_path(prefixed)
        prefix_count = str(double).count("\\\\?\\")
        assert prefix_count == 1, f"Expected exactly one \\\\?\\ prefix, got: {double}"


# ── TC-3600: ReportMetrics and convergence-aware progress ──────────────────


class TestReportMetrics:
    """Tests for compute_report_metrics, is_improvement, is_regression."""

    def test_compute_metrics_basic(self) -> None:
        from launch.cli.heal import ReportMetrics, compute_report_metrics

        report = _make_report(
            gates=[
                _make_gate("gate_4", ok=False),
                _make_gate("gate_17", ok=False),
                _make_gate("gate_20", ok=True),
            ],
            issues=[
                _make_issue("gate_4", "error", "G4-001"),
                _make_issue("gate_4", "error", "G4-002"),
                _make_issue("gate_17", "error", "FQ-1"),
                _make_issue("gate_20", "warn", "G20-008"),
            ],
        )
        m = compute_report_metrics(report)
        assert m.failed_gate_count == 2
        assert m.failed_gate_ids == frozenset({"gate_4", "gate_17"})
        assert m.open_critical_issue_count == 3  # 3 errors
        assert m.open_total_issue_count == 4  # 3 errors + 1 warn

    def test_compute_metrics_empty(self) -> None:
        from launch.cli.heal import compute_report_metrics

        report = _make_report(gates=[], issues=[])
        m = compute_report_metrics(report)
        assert m.failed_gate_count == 0
        assert m.open_total_issue_count == 0

    def test_is_improvement_gate_count_dropped(self) -> None:
        from launch.cli.heal import ReportMetrics, is_improvement

        before = ReportMetrics(
            failed_gate_ids=frozenset({"g1", "g2"}),
            failed_gate_count=2,
            open_critical_issue_count=5,
            open_total_issue_count=8,
        )
        after = ReportMetrics(
            failed_gate_ids=frozenset({"g1"}),
            failed_gate_count=1,
            open_critical_issue_count=3,
            open_total_issue_count=5,
        )
        assert is_improvement(before, after) is True

    def test_is_improvement_issue_count_dropped_gate_count_same(self) -> None:
        """Gate count unchanged but issue count dropped — should be improvement."""
        from launch.cli.heal import ReportMetrics, is_improvement

        before = ReportMetrics(
            failed_gate_ids=frozenset({"g1", "g2"}),
            failed_gate_count=2,
            open_critical_issue_count=5,
            open_total_issue_count=8,
        )
        after = ReportMetrics(
            failed_gate_ids=frozenset({"g1", "g2"}),
            failed_gate_count=2,
            open_critical_issue_count=4,
            open_total_issue_count=7,
        )
        assert is_improvement(before, after) is True

    def test_is_improvement_total_issues_dropped_critical_same(self) -> None:
        """Total issues dropped but critical count unchanged — still improvement."""
        from launch.cli.heal import ReportMetrics, is_improvement

        before = ReportMetrics(
            failed_gate_ids=frozenset({"g1"}),
            failed_gate_count=1,
            open_critical_issue_count=2,
            open_total_issue_count=10,
        )
        after = ReportMetrics(
            failed_gate_ids=frozenset({"g1"}),
            failed_gate_count=1,
            open_critical_issue_count=2,
            open_total_issue_count=8,
        )
        assert is_improvement(before, after) is True

    def test_no_improvement_when_nothing_changed(self) -> None:
        from launch.cli.heal import ReportMetrics, is_improvement

        m = ReportMetrics(
            failed_gate_ids=frozenset({"g1"}),
            failed_gate_count=1,
            open_critical_issue_count=3,
            open_total_issue_count=5,
        )
        assert is_improvement(m, m) is False

    def test_not_improvement_when_new_gates_appear(self) -> None:
        """Gate set swap: one fixed, one new — not an improvement."""
        from launch.cli.heal import ReportMetrics, is_improvement

        before = ReportMetrics(
            failed_gate_ids=frozenset({"g1", "g2"}),
            failed_gate_count=2,
            open_critical_issue_count=4,
            open_total_issue_count=6,
        )
        after = ReportMetrics(
            failed_gate_ids=frozenset({"g1", "g3"}),  # g2 fixed, g3 new
            failed_gate_count=2,
            open_critical_issue_count=4,
            open_total_issue_count=6,
        )
        assert is_improvement(before, after) is False

    def test_is_regression_gate_count_increased(self) -> None:
        from launch.cli.heal import ReportMetrics, is_regression

        before = ReportMetrics(
            failed_gate_ids=frozenset({"g1"}),
            failed_gate_count=1,
            open_critical_issue_count=2,
            open_total_issue_count=4,
        )
        after = ReportMetrics(
            failed_gate_ids=frozenset({"g1", "g2"}),
            failed_gate_count=2,
            open_critical_issue_count=3,
            open_total_issue_count=5,
        )
        assert is_regression(before, after) is True

    def test_is_regression_new_gates_appeared(self) -> None:
        """Gate count same but new gate appeared (swap) — regression."""
        from launch.cli.heal import ReportMetrics, is_regression

        before = ReportMetrics(
            failed_gate_ids=frozenset({"g1", "g2"}),
            failed_gate_count=2,
            open_critical_issue_count=4,
            open_total_issue_count=6,
        )
        after = ReportMetrics(
            failed_gate_ids=frozenset({"g1", "g3"}),  # g3 is new
            failed_gate_count=2,
            open_critical_issue_count=4,
            open_total_issue_count=6,
        )
        assert is_regression(before, after) is True

    def test_is_regression_critical_count_increased(self) -> None:
        from launch.cli.heal import ReportMetrics, is_regression

        before = ReportMetrics(
            failed_gate_ids=frozenset({"g1"}),
            failed_gate_count=1,
            open_critical_issue_count=2,
            open_total_issue_count=4,
        )
        after = ReportMetrics(
            failed_gate_ids=frozenset({"g1"}),
            failed_gate_count=1,
            open_critical_issue_count=3,
            open_total_issue_count=5,
        )
        assert is_regression(before, after) is True

    def test_not_regression_when_issues_drop(self) -> None:
        from launch.cli.heal import ReportMetrics, is_regression

        before = ReportMetrics(
            failed_gate_ids=frozenset({"g1"}),
            failed_gate_count=1,
            open_critical_issue_count=5,
            open_total_issue_count=8,
        )
        after = ReportMetrics(
            failed_gate_ids=frozenset({"g1"}),
            failed_gate_count=1,
            open_critical_issue_count=4,
            open_total_issue_count=7,
        )
        assert is_regression(before, after) is False


class TestHealLoopMetricsProgress:
    """Integration test: heal loop detects issue-count-drop as progress."""

    @patch("launch.orchestrator.run_loop.execute_run_from_node")
    def test_issue_count_drop_treated_as_improvement(
        self, mock_resume: MagicMock, tmp_path: Path
    ) -> None:
        """When gate count stays 2 but issues drop 4→3, heal should record improvement."""
        run_dir = tmp_path / "run"
        run_dir.mkdir()

        # Initial report: 2 failing gates, 4 issues
        initial_report = _make_report(
            gates=[
                _make_gate("gate_4", ok=False),
                _make_gate("gate_17", ok=False),
                _make_gate("gate_20", ok=True),
            ],
            issues=[
                _make_issue("gate_4", "error", "G4-001"),
                _make_issue("gate_4", "error", "G4-002"),
                _make_issue("gate_17", "error", "FQ-1"),
                _make_issue("gate_17", "error", "FQ-3"),
            ],
        )
        _write_report(run_dir, initial_report)

        call_count = {"n": 0}

        def mock_execute(run_id, rd, rc, worker):
            call_count["n"] += 1
            # After fix: still 2 failing gates but only 3 issues (one FQ-3 fixed)
            fixed_report = _make_report(
                gates=[
                    _make_gate("gate_4", ok=False),
                    _make_gate("gate_17", ok=False),
                    _make_gate("gate_20", ok=True),
                ],
                issues=[
                    _make_issue("gate_4", "error", "G4-001"),
                    _make_issue("gate_4", "error", "G4-002"),
                    _make_issue("gate_17", "error", "FQ-1"),
                ],
            )
            _write_report(rd, fixed_report)
            result = MagicMock()
            result.exit_code = 0
            return result

        mock_resume.side_effect = mock_execute

        with (
            patch("launch.cli.triage.recommend_action", return_value=[
                {"command": f"launch resume --run-dir {run_dir} --from-worker W10",
                 "reason": "formatting issues"},
            ]),
            patch("launch.cli.triage.load_validation_report", side_effect=lambda rd: json.loads(
                (rd / "artifacts" / "validation_report.json").read_text()
            )),
        ):
            result = run_heal_loop(
                run_id="test_metrics",
                run_dir=run_dir,
                run_config={},
                max_steps=2,
                mode="strict",
            )

        # Step should show gate count unchanged (2→2) but heal should NOT be stuck
        assert len(result.steps) >= 1
        step = result.steps[0]
        assert step.failed_gate_count_before == 2
        assert step.failed_gate_count_after == 2
        # The step should be marked as improved (issue count dropped), not regressed
        assert step.outcome == "improved"
        assert "regressed" not in step.notes


# ── TC-3614: Step metrics persisted in heal_plan.json ─────────────────────────


class TestStepMetricsPersisted:
    """TC-3614: before_metrics / after_metrics and recommendation_id in heal_plan.json."""

    def test_metrics_to_dict_converts_report_metrics(self) -> None:
        """_metrics_to_dict converts a ReportMetrics snapshot to a serializable dict."""
        from launch.cli.heal import ReportMetrics, _metrics_to_dict

        m = ReportMetrics(
            failed_gate_ids=frozenset({"gate_17", "gate_4"}),
            failed_gate_count=2,
            open_critical_issue_count=3,
            open_total_issue_count=5,
        )
        d = _metrics_to_dict(m)
        assert d is not None
        assert d["failed_gate_count"] == 2
        assert sorted(d["failed_gate_ids"]) == ["gate_17", "gate_4"]
        assert d["open_critical_issue_count"] == 3
        assert d["open_total_issue_count"] == 5

    def test_metrics_to_dict_returns_none_for_none(self) -> None:
        """_metrics_to_dict(None) returns None — step had no snapshot."""
        from launch.cli.heal import _metrics_to_dict

        assert _metrics_to_dict(None) is None

    def test_heal_step_to_dict_includes_all_tc3614_fields(self) -> None:
        """HealStep.to_dict() serialises recommendation_id, before_metrics, after_metrics."""
        step = HealStep(
            step_idx=0,
            chosen_worker="W10",
            reason="scaffold leak",
            triage_snapshot=[],
            failed_gate_count_before=2,
            failed_gate_count_after=0,
            exit_code=0,
            notes="",
            recommendation_id="triage:_match_scaffold_or_fmt->W10",
            before_metrics={
                "failed_gate_count": 2,
                "failed_gate_ids": ["gate_17", "gate_scaffold_leak"],
                "open_critical_issue_count": 2,
                "open_total_issue_count": 2,
            },
            after_metrics={
                "failed_gate_count": 0,
                "failed_gate_ids": [],
                "open_critical_issue_count": 0,
                "open_total_issue_count": 0,
            },
        )
        d = step.to_dict()
        assert d["recommendation_id"] == "triage:_match_scaffold_or_fmt->W10"
        assert d["before_metrics"]["failed_gate_count"] == 2
        assert d["after_metrics"]["failed_gate_count"] == 0

    @patch("launch.orchestrator.run_loop.execute_run_from_node")
    def test_heal_plan_json_has_before_after_metrics(
        self, mock_resume: MagicMock, tmp_path: Path
    ) -> None:
        """heal_plan.json step includes non-None before_metrics and after_metrics."""
        run_dir = _setup_run_dir(tmp_path, _truth_missing_report())

        def resume_side_effect(run_id, rd, rc, worker):
            _write_report(rd, _all_pass_report())
            return _mock_run_result(0)

        mock_resume.side_effect = resume_side_effect

        run_heal_loop("r_test", run_dir, {}, max_steps=5)

        plan = json.loads(
            (run_dir / "artifacts" / "heal_plan.json").read_text(encoding="utf-8")
        )
        assert len(plan["steps"]) == 1
        step = plan["steps"][0]

        bm = step["before_metrics"]
        assert bm is not None, "before_metrics must be present after a real step"
        assert bm["failed_gate_count"] == 1
        assert bm["open_total_issue_count"] == 1
        assert "open_critical_issue_count" in bm
        assert "failed_gate_ids" in bm

        am = step["after_metrics"]
        assert am is not None, "after_metrics must be present after a successful step"
        assert am["failed_gate_count"] == 0
        assert am["open_total_issue_count"] == 0

    @patch("launch.orchestrator.run_loop.execute_run_from_node")
    def test_heal_plan_json_metrics_show_issue_count_drop(
        self, mock_resume: MagicMock, tmp_path: Path
    ) -> None:
        """E2E: gate count flat but issue count dropped → heal_plan.json records the drop.

        TC-3614 auditability: "progress without gate flip" must be visible in
        heal_plan.json before_metrics/after_metrics, not only in logs.
        """
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        (run_dir / "events.ndjson").write_text("", encoding="utf-8")

        # Initial: 2 failing gates, 4 issues (all critical errors)
        initial_report = _make_report(
            gates=[
                _make_gate("gate_4", ok=False),
                _make_gate("gate_17", ok=False),
                _make_gate("gate_20", ok=True),
            ],
            issues=[
                _make_issue("gate_4", "error", "G4-001"),
                _make_issue("gate_4", "error", "G4-002"),
                _make_issue("gate_17", "error", "FQ-1"),
                _make_issue("gate_17", "error", "FQ-3"),
            ],
        )
        _write_report(run_dir, initial_report)

        def mock_execute(run_id, rd, rc, worker):
            # After fix: still 2 failing gates but only 3 issues (FQ-3 resolved)
            fixed_report = _make_report(
                gates=[
                    _make_gate("gate_4", ok=False),
                    _make_gate("gate_17", ok=False),
                    _make_gate("gate_20", ok=True),
                ],
                issues=[
                    _make_issue("gate_4", "error", "G4-001"),
                    _make_issue("gate_4", "error", "G4-002"),
                    _make_issue("gate_17", "error", "FQ-1"),
                ],
            )
            _write_report(rd, fixed_report)
            r = MagicMock()
            r.exit_code = 0
            return r

        mock_resume.side_effect = mock_execute

        with (
            patch("launch.cli.triage.recommend_action", return_value=[
                {
                    "command": f"launch resume --run-dir {run_dir} --from-worker W10",
                    "reason": "formatting issues",
                    "id": "triage:_match_scaffold_or_fmt->W10",
                },
            ]),
            patch("launch.cli.triage.load_validation_report", side_effect=lambda rd: json.loads(
                (rd / "artifacts" / "validation_report.json").read_text()
            )),
        ):
            run_heal_loop(
                run_id="test_metrics_e2e",
                run_dir=run_dir,
                run_config={},
                max_steps=2,
                mode="strict",
            )

        plan = json.loads(
            (run_dir / "artifacts" / "heal_plan.json").read_text(encoding="utf-8")
        )
        assert len(plan["steps"]) >= 1
        step = plan["steps"][0]

        bm = step["before_metrics"]
        am = step["after_metrics"]
        assert bm is not None
        assert am is not None

        # Gate count must be flat (2 → 2); issue count must drop (4 → 3)
        assert bm["failed_gate_count"] == 2
        assert am["failed_gate_count"] == 2
        assert bm["open_total_issue_count"] == 4
        assert am["open_total_issue_count"] == 3
        assert am["open_total_issue_count"] < bm["open_total_issue_count"]

    @patch("launch.orchestrator.run_loop.execute_run_from_node")
    def test_recommendation_id_in_heal_plan_json(
        self, mock_resume: MagicMock, tmp_path: Path
    ) -> None:
        """TC-3614: recommendation_id is written to heal_plan.json steps."""
        run_dir = _setup_run_dir(tmp_path, _scaffold_report())

        def resume_side_effect(run_id, rd, rc, worker):
            _write_report(rd, _all_pass_report())
            return _mock_run_result(0)

        mock_resume.side_effect = resume_side_effect

        # Use real recommend_action — scaffold report produces W10 with stable id
        run_heal_loop("r_test", run_dir, {}, max_steps=5)

        plan = json.loads(
            (run_dir / "artifacts" / "heal_plan.json").read_text(encoding="utf-8")
        )
        assert len(plan["steps"]) >= 1
        step = plan["steps"][0]

        assert "recommendation_id" in step
        rec_id = step["recommendation_id"]
        # Must be a real stable id, not the fallback
        assert rec_id.startswith("triage:"), (
            f"recommendation_id should start with 'triage:', got: {rec_id!r}"
        )
        assert "->W10" in rec_id, (
            f"recommendation_id should map to W10 for scaffold issues, got: {rec_id!r}"
        )


# ── TC-3620: Disk-truth contract ──────────────────────────────────────────────


class TestDiskTruthWinsOnException:
    """TC-3620 OBS-1: exception path reads disk before recording step outcome.

    The heal loop must consult validation_report.json on disk even when
    execute_run_from_node() raises an exception.  A worker may write a green
    report before crashing, and the loop must detect this as success.
    """

    @patch("launch.orchestrator.run_loop.execute_run_from_node")
    def test_exception_but_disk_green_stops_as_all_gates_pass(
        self, mock_resume: MagicMock, tmp_path: Path
    ) -> None:
        """Worker writes green report then raises — loop must stop as all_gates_pass.

        Expected:
         - stop_reason == 'all_gates_pass'
         - final_failed_gate_count == 0
         - step.failed_gate_count_after == 0
         - step.outcome == 'improved'
        """
        run_dir = _setup_run_dir(tmp_path, _truth_missing_report())

        def side_effect(run_id: str, rd: Path, rc: dict, worker: str) -> None:
            # Write green report to disk, then raise — simulates a worker that
            # successfully finished its work but crashed during cleanup.
            _write_report(rd, _all_pass_report())
            raise RuntimeError("simulated crash after writing green report")

        mock_resume.side_effect = side_effect

        result = run_heal_loop("r_test", run_dir, {}, max_steps=5)

        assert result.stop_reason == "all_gates_pass"
        assert result.final_failed_gate_count == 0
        assert len(result.steps) == 1
        assert result.steps[0].failed_gate_count_after == 0
        assert result.steps[0].outcome == "improved"

    @patch("launch.orchestrator.run_loop.execute_run_from_node")
    def test_exception_no_disk_improvement_continues_and_heals(
        self, mock_resume: MagicMock, tmp_path: Path
    ) -> None:
        """First recommended worker (W2) crashes without updating disk;
        second recommended worker (W10) succeeds and heals everything.

        Uses a multi-issue report so W2 AND W10 are both recommended.
        In strict mode, after W2 crashes (exit_code=2) it is excluded by
        _had_execution_error(), so the loop moves on to W10.
        The loop must converge to all_gates_pass on the W10 step.
        """
        run_dir = _setup_run_dir(tmp_path, _multi_issue_report())
        call_count = [0]

        def side_effect(run_id: str, rd: Path, rc: dict, worker: str) -> MagicMock:
            call_count[0] += 1
            if worker == "W2":
                # W2 crashes without touching disk
                raise RuntimeError("transient crash, disk unchanged")
            # W10 (or any other worker) succeeds and writes green report.
            _write_report(rd, _all_pass_report())
            return _mock_run_result(0)

        mock_resume.side_effect = side_effect

        result = run_heal_loop("r_test", run_dir, {}, max_steps=5, mode="strict")

        assert result.stop_reason == "all_gates_pass"
        assert result.final_failed_gate_count == 0
        assert call_count[0] >= 2  # W2 crash + at least one successful call


class TestTopOfIterationDiskSync:
    """TC-3620 OBS-5: top-of-iteration disk sync exits all_gates_pass before stuck.

    When the exception-path continues (disk not yet green) but disk becomes
    green before the next iteration, the top-of-loop sync must detect this and
    break before executing (and before stuck detection fires).
    """

    @patch("launch.cli.heal._sync_from_disk")
    @patch("launch.orchestrator.run_loop.execute_run_from_node")
    def test_top_of_loop_detects_green_before_stuck(
        self, mock_resume: MagicMock, mock_sync: MagicMock, tmp_path: Path
    ) -> None:
        """Exception on iteration 0 leaves disk failing; disk becomes green
        between iterations.  Top-of-loop sync on iteration 1 exits before
        calling execute again, preventing a spurious 'stuck' report.
        """
        from launch.cli.heal import ReportMetrics, compute_report_metrics

        run_dir = _setup_run_dir(tmp_path, _truth_missing_report())

        fail_rep = _truth_missing_report()
        pass_rep = _all_pass_report()
        fail_m = compute_report_metrics(fail_rep)
        pass_m = compute_report_metrics(pass_rep)

        # _sync_from_disk calls in order:
        #   call 1 (exception-path) — still failing (handler continues loop)
        #   call 2 (top of iteration 1) — green (exits before execute)
        #   call 3 (finalization) — green (corrects final_failed_gate_count)
        #   call 4+ (defensive spare) — green (guards against future extra sync points)
        mock_sync.side_effect = [
            (fail_rep, 1, fail_m),  # exception path read
            (pass_rep, 0, pass_m),  # top-of-loop iteration 1
            (pass_rep, 0, pass_m),  # finalization sync
            (pass_rep, 0, pass_m),  # defensive: 4th call if a new sync point is added
        ]

        def execute_side(run_id: str, rd: Path, rc: dict, worker: str) -> None:
            raise RuntimeError("crash, disk not updated by worker")

        mock_resume.side_effect = execute_side

        result = run_heal_loop("r_test", run_dir, {}, max_steps=5)

        assert result.stop_reason == "all_gates_pass"
        assert result.final_failed_gate_count == 0
        # execute was called exactly once — top-of-loop sync exited before call 2
        assert mock_resume.call_count == 1


class TestDriveGoalValidateInjection:
    """TC-3633: heal always injects _drive_goal='validate' into run_config copy.

    The orchestrator must execute a single pass (chosen worker → W9 → stop)
    during heal. Injecting _drive_goal='validate' causes decide_after_validation()
    to return 'stop' immediately, preventing the internal fix sub-loop and PR routing.

    Replaces TC-3620 OBS-2 (previously used 'draft'; now 'validate' for stronger
    single-pass guarantee — draft still allowed the fix loop when issues were present).
    """

    @patch("launch.orchestrator.run_loop.execute_run_from_node")
    def test_drive_goal_validate_injected(
        self, mock_resume: MagicMock, tmp_path: Path
    ) -> None:
        """run_config passed to execute_run_from_node must have _drive_goal='validate'."""
        run_dir = _setup_run_dir(tmp_path, _truth_missing_report())
        captured_configs: list = []

        def side_effect(run_id: str, rd: Path, rc: dict, worker: str) -> MagicMock:
            captured_configs.append(dict(rc))
            _write_report(rd, _all_pass_report())
            return _mock_run_result(0)

        mock_resume.side_effect = side_effect

        run_heal_loop("r_test", run_dir, {}, max_steps=5)

        assert len(captured_configs) >= 1
        assert captured_configs[0].get(DRIVE_GOAL_KEY) == DRIVE_GOAL_VALIDATE, (
            f"Expected {DRIVE_GOAL_KEY}={DRIVE_GOAL_VALIDATE!r} in config, got: {captured_configs[0]}"
        )

    @patch("launch.orchestrator.run_loop.execute_run_from_node")
    def test_original_run_config_not_mutated(
        self, mock_resume: MagicMock, tmp_path: Path
    ) -> None:
        """The caller's run_config dict must NOT be mutated by the heal loop."""
        run_dir = _setup_run_dir(tmp_path, _truth_missing_report())
        original_config: dict = {"product_slug": "test-prod", "some_key": "some_val"}

        def side_effect(run_id: str, rd: Path, rc: dict, worker: str) -> MagicMock:
            _write_report(rd, _all_pass_report())
            return _mock_run_result(0)

        mock_resume.side_effect = side_effect

        run_heal_loop("r_test", run_dir, original_config, max_steps=5)

        assert DRIVE_GOAL_KEY not in original_config, (
            "heal loop must not mutate the caller's run_config dict"
        )
        assert original_config == {"product_slug": "test-prod", "some_key": "some_val"}


# ── TC-3620 SR-01: _restore_missing_from_checkpoint unit tests ─────────────────


class TestRestoreMissingFromCheckpoint:
    """TC-3620 SR-01: _restore_missing_from_checkpoint only-missing semantics.

    The helper must restore absent artifacts from checkpoint but NEVER
    overwrite existing files (disk truth contract).
    """

    def test_missing_artifact_is_restored(self, tmp_path: Path) -> None:
        """A file absent from run_dir is copied from checkpoint."""
        from launch.cli.heal import _restore_missing_from_checkpoint

        run_dir = tmp_path / "run"
        checkpoint = tmp_path / "ckpt"
        (checkpoint / "artifacts").mkdir(parents=True)
        sentinel = checkpoint / "artifacts" / "patch_bundle.json"
        sentinel.write_text('{"restored": true}', encoding="utf-8")

        restored = _restore_missing_from_checkpoint(
            run_dir, checkpoint, rel_paths=["artifacts/patch_bundle.json"]
        )

        assert "artifacts/patch_bundle.json" in restored
        assert (run_dir / "artifacts" / "patch_bundle.json").read_text() == '{"restored": true}'

    def test_existing_artifact_is_not_overwritten(self, tmp_path: Path) -> None:
        """A file already present in run_dir must NOT be overwritten (disk truth wins)."""
        from launch.cli.heal import _restore_missing_from_checkpoint

        run_dir = tmp_path / "run"
        checkpoint = tmp_path / "ckpt"
        (run_dir / "artifacts").mkdir(parents=True)
        (checkpoint / "artifacts").mkdir(parents=True)

        live_file = run_dir / "artifacts" / "patch_bundle.json"
        live_file.write_text('{"live": true}', encoding="utf-8")
        ckpt_file = checkpoint / "artifacts" / "patch_bundle.json"
        ckpt_file.write_text('{"stale": true}', encoding="utf-8")

        restored = _restore_missing_from_checkpoint(
            run_dir, checkpoint, rel_paths=["artifacts/patch_bundle.json"]
        )

        assert restored == [], "existing file must not be restored"
        assert live_file.read_text() == '{"live": true}', "live file must not be overwritten"

    def test_missing_from_both_returns_empty(self, tmp_path: Path) -> None:
        """Artifact absent from both run_dir and checkpoint — returns empty list."""
        from launch.cli.heal import _restore_missing_from_checkpoint

        run_dir = tmp_path / "run"
        checkpoint = tmp_path / "ckpt"
        run_dir.mkdir()
        checkpoint.mkdir()

        restored = _restore_missing_from_checkpoint(
            run_dir, checkpoint, rel_paths=["artifacts/patch_bundle.json"]
        )

        assert restored == []


# ── TC-3633: Checkpoint scope map tests ───────────────────────────────────────


class TestCheckpointScopes:
    """TC-3633: _WORKER_CHECKPOINT_SCOPES defines per-worker checkpoint content dirs.

    Verifies the scope map is correctly defined and that _create_checkpoint()
    respects the content_dirs parameter.
    """

    def test_w2_scope_is_empty_list(self) -> None:
        """W2 only touches artifacts/ — content dirs scope must be []."""
        assert _WORKER_CHECKPOINT_SCOPES.get("W2") == []

    def test_w10_scope_includes_site_content(self) -> None:
        """W10 patches site content — scope must include work/site/content."""
        scope = _WORKER_CHECKPOINT_SCOPES.get("W10")
        assert scope is not None
        assert "work/site/content" in scope

    def test_w9_scope_is_none_skip_checkpoint(self) -> None:
        """W9 is read-only (writes only validation_report.json in artifacts/).
        Its scope must be None so the heal loop skips checkpoint creation.
        """
        assert _WORKER_CHECKPOINT_SCOPES.get("W9") is None

    def test_unknown_worker_defaults_to_full_scope(self) -> None:
        """Workers absent from the map default to _CHECKPOINT_CONTENT_DIRS (full scope)."""
        scope = _WORKER_CHECKPOINT_SCOPES.get("W99", _CHECKPOINT_CONTENT_DIRS)
        assert scope == _CHECKPOINT_CONTENT_DIRS

    def test_create_checkpoint_with_empty_scope_skips_content_dirs(
        self, tmp_path: Path
    ) -> None:
        """content_dirs=[] causes _create_checkpoint to snapshot only artifacts/."""
        run_dir = tmp_path / "run"
        (run_dir / "artifacts").mkdir(parents=True)
        (run_dir / "artifacts" / "sentinel.json").write_text("{}", encoding="utf-8")
        # Create content dir that should NOT be checkpointed
        (run_dir / "work" / "site" / "content").mkdir(parents=True)
        (run_dir / "work" / "site" / "content" / "page.md").write_text("# page", encoding="utf-8")

        ckpt = _create_checkpoint(run_dir, step_idx=0, content_dirs=[])

        assert ckpt is not None
        assert (ckpt / "artifacts" / "sentinel.json").exists(), "artifacts must be checkpointed"
        assert not (ckpt / "work").exists(), "content dir must NOT be in scoped checkpoint"

    def test_create_checkpoint_with_none_falls_back_to_full_scope(
        self, tmp_path: Path
    ) -> None:
        """content_dirs=None falls back to _CHECKPOINT_CONTENT_DIRS (backward compat)."""
        run_dir = tmp_path / "run"
        (run_dir / "artifacts").mkdir(parents=True)
        (run_dir / "drafts").mkdir(parents=True)
        (run_dir / "drafts" / "draft.md").write_text("# draft", encoding="utf-8")

        ckpt = _create_checkpoint(run_dir, step_idx=0, content_dirs=None)

        assert ckpt is not None
        assert (ckpt / "drafts" / "draft.md").exists(), "drafts must be in full-scope checkpoint"


# ── TC-3633: HealStep timing telemetry tests ──────────────────────────────────


class TestHealStepTiming:
    """TC-3633: HealStep exposes checkpoint/execution/restore timing fields."""

    def test_timing_fields_default_to_zero(self) -> None:
        """New HealStep has all timing fields defaulting to 0.0."""
        step = HealStep(
            step_idx=0,
            chosen_worker="W10",
            reason="test",
            triage_snapshot=[],
            failed_gate_count_before=3,
        )
        assert step.checkpoint_seconds == 0.0
        assert step.execution_seconds == 0.0
        assert step.restore_seconds == 0.0

    def test_timing_fields_in_to_dict(self) -> None:
        """checkpoint_seconds, execution_seconds, restore_seconds appear in to_dict()."""
        step = HealStep(
            step_idx=0,
            chosen_worker="W10",
            reason="test",
            triage_snapshot=[],
            failed_gate_count_before=3,
            checkpoint_seconds=0.042,
            execution_seconds=12.7,
            restore_seconds=0.0,
        )
        d = step.to_dict()
        assert "checkpoint_seconds" in d, "checkpoint_seconds must be in to_dict()"
        assert "execution_seconds" in d, "execution_seconds must be in to_dict()"
        assert "restore_seconds" in d, "restore_seconds must be in to_dict()"
        assert d["checkpoint_seconds"] == pytest.approx(0.042)
        assert d["execution_seconds"] == pytest.approx(12.7)
        assert d["restore_seconds"] == 0.0


# ═══════════════════════════════════════════════════════════════════════
# TC-3641: Selective Gate Execution (Fast Inner-Loop Validation)
# ═══════════════════════════════════════════════════════════════════════


class TestSelectiveGateExecution:
    """Tests for heal loop gate filter injection and partial-zero handling.

    Spec: specs/50_healing_cost_reduction.md §5.
    """

    @patch("launch.orchestrator.run_loop.execute_run_from_node")
    def test_heal_injects_gate_filter(
        self, mock_resume: MagicMock, tmp_path: Path
    ) -> None:
        """``_heal_gate_filter`` is injected into the run_config passed to execute_run_from_node."""
        run_dir = _setup_run_dir(tmp_path, _truth_missing_report())

        captured_rc: List[Dict] = []

        def resume_side_effect(run_id, rd, rc, worker):
            captured_rc.append(dict(rc))
            _write_report(rd, _all_pass_report())
            return _mock_run_result(0)

        mock_resume.side_effect = resume_side_effect

        run_heal_loop("r_test", run_dir, {}, max_steps=1)

        assert len(captured_rc) >= 1
        rc = captured_rc[0]
        assert "_heal_gate_filter" in rc
        filter_list = rc["_heal_gate_filter"]
        # Must contain the failed gate
        assert "gate_truth_layer_completeness" in filter_list

    @patch("launch.orchestrator.run_loop.execute_run_from_node")
    def test_safety_gates_always_included(
        self, mock_resume: MagicMock, tmp_path: Path
    ) -> None:
        """All 7 safety gates are in the filter regardless of which gates failed."""
        # Use a report where only gate_5 fails — NOT a safety gate
        report = _make_report(
            gates=[_make_gate("gate_5_cross_page_link_validity", ok=False)],
            issues=[_make_issue("gate_5_cross_page_link_validity", "error", "LINK_BROKEN")],
        )
        run_dir = _setup_run_dir(tmp_path, report)

        captured_rc: List[Dict] = []

        def resume_side_effect(run_id, rd, rc, worker):
            captured_rc.append(dict(rc))
            _write_report(rd, _all_pass_report())
            return _mock_run_result(0)

        mock_resume.side_effect = resume_side_effect

        run_heal_loop("r_test", run_dir, {}, max_steps=1)

        rc = captured_rc[0]
        filter_set = set(rc["_heal_gate_filter"])
        for safety_gate in _HEAL_SAFETY_GATES:
            assert safety_gate in filter_set, f"Safety gate {safety_gate} missing from filter"

    @patch("launch.orchestrator.run_loop.execute_run_from_node")
    def test_fast_validation_false_disables(
        self, mock_resume: MagicMock, tmp_path: Path
    ) -> None:
        """No filter when ``heal_fast_validation=false``."""
        run_dir = _setup_run_dir(tmp_path, _truth_missing_report())

        captured_rc: List[Dict] = []

        def resume_side_effect(run_id, rd, rc, worker):
            captured_rc.append(dict(rc))
            _write_report(rd, _all_pass_report())
            return _mock_run_result(0)

        mock_resume.side_effect = resume_side_effect

        run_heal_loop(
            "r_test", run_dir, {"heal_fast_validation": False}, max_steps=1
        )

        rc = captured_rc[0]
        assert "_heal_gate_filter" not in rc

    @patch("launch.orchestrator.run_loop.execute_run_from_node")
    def test_partial_zero_triggers_final_full(
        self, mock_resume: MagicMock, tmp_path: Path
    ) -> None:
        """Partial green triggers a final full W9 validation call."""
        run_dir = _setup_run_dir(tmp_path, _truth_missing_report())
        call_count = [0]

        def resume_side_effect(run_id, rd, rc, worker):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call: worker fixes the issue; report is partial-green
                report = _all_pass_report()
                report["partial"] = True
                report["gate_filter"] = ["gate_truth_layer_completeness"]
                _write_report(rd, report)
            else:
                # Second call: final full validation — also green
                _write_report(rd, _all_pass_report())
            return _mock_run_result(0)

        mock_resume.side_effect = resume_side_effect

        result = run_heal_loop("r_test", run_dir, {}, max_steps=5)

        assert result.stop_reason == "all_gates_pass"
        # At least 2 calls: one for the step, one for final full validation
        assert call_count[0] >= 2

    @patch("launch.orchestrator.run_loop.execute_run_from_node")
    def test_final_full_finds_regression(
        self, mock_resume: MagicMock, tmp_path: Path
    ) -> None:
        """Final full run reveals failures → NOT ``all_gates_pass``."""
        run_dir = _setup_run_dir(tmp_path, _truth_missing_report())
        call_count = [0]

        def resume_side_effect(run_id, rd, rc, worker):
            call_count[0] += 1
            if call_count[0] == 1:
                report = _all_pass_report()
                report["partial"] = True
                report["gate_filter"] = ["gate_truth_layer_completeness"]
                _write_report(rd, report)
            else:
                # Final full validation finds a new failure
                _write_report(rd, _truth_missing_report())
            return _mock_run_result(0)

        mock_resume.side_effect = resume_side_effect

        result = run_heal_loop("r_test", run_dir, {}, max_steps=5)

        assert result.stop_reason != "all_gates_pass"
        assert result.final_failed_gate_count > 0

    @patch("launch.orchestrator.run_loop.execute_run_from_node")
    def test_final_full_confirms_green(
        self, mock_resume: MagicMock, tmp_path: Path
    ) -> None:
        """Final full run also 0 → ``all_gates_pass``."""
        run_dir = _setup_run_dir(tmp_path, _truth_missing_report())
        call_count = [0]

        def resume_side_effect(run_id, rd, rc, worker):
            call_count[0] += 1
            if call_count[0] == 1:
                report = _all_pass_report()
                report["partial"] = True
                report["gate_filter"] = ["gate_truth_layer_completeness"]
                _write_report(rd, report)
            else:
                _write_report(rd, _all_pass_report())
            return _mock_run_result(0)

        mock_resume.side_effect = resume_side_effect

        result = run_heal_loop("r_test", run_dir, {}, max_steps=5)

        assert result.stop_reason == "all_gates_pass"
        assert result.final_failed_gate_count == 0

    @patch("launch.orchestrator.run_loop.execute_run_from_node")
    def test_disk_sync_defers_partial_green(
        self, mock_resume: MagicMock, tmp_path: Path
    ) -> None:
        """Top-of-iteration partial green does not immediately declare all_gates_pass."""
        # Write a partial-green report directly on disk before the loop starts
        report = _all_pass_report()
        report["partial"] = True
        report["gate_filter"] = ["gate_1_schema_validation"]
        run_dir = _setup_run_dir(tmp_path, report)

        # The heal loop should see 0 failed but partial → NOT immediately break as all_gates_pass
        # Instead it triggers final full validation
        def resume_side_effect(run_id, rd, rc, worker):
            # Final full validation: truly green
            _write_report(rd, _all_pass_report())
            return _mock_run_result(0)

        mock_resume.side_effect = resume_side_effect

        result = run_heal_loop("r_test", run_dir, {}, max_steps=5)

        # After final full validation confirms green
        assert result.stop_reason == "all_gates_pass"

    @patch("launch.orchestrator.run_loop.execute_run_from_node")
    def test_metrics_comparison_with_partial(
        self, mock_resume: MagicMock, tmp_path: Path
    ) -> None:
        """``is_improvement``/``is_regression`` work unchanged with partial reports."""
        # Start with 2 failing gates
        run_dir = _setup_run_dir(tmp_path, _multi_issue_report())

        def resume_side_effect(run_id, rd, rc, worker):
            # Improve to 1 failing gate (partial report)
            report = _make_report(
                gates=[
                    _make_gate("gate_truth_layer_completeness"),
                    _make_gate("gate_scaffold_leak", ok=False),
                ],
                issues=[_make_issue("gate_scaffold_leak", "error", "SCAFFOLD_LEAK")],
            )
            report["partial"] = True
            report["gate_filter"] = [
                "gate_truth_layer_completeness",
                "gate_scaffold_leak",
            ]
            _write_report(rd, report)
            return _mock_run_result(0)

        mock_resume.side_effect = resume_side_effect

        result = run_heal_loop("r_test", run_dir, {}, max_steps=1)

        # Should detect improvement (2 → 1 failed)
        assert len(result.steps) >= 1
        assert result.steps[0].outcome == "improved"


# ═══════════════════════════════════════════════════════════════════════════
# TC-3641 gap TM-03: Progressive Narrowing + Resume Fallback
# ═══════════════════════════════════════════════════════════════════════════


class TestProgressiveNarrowing:
    """Verify that the gate filter narrows across multiple heal iterations.

    Spec: specs/50_healing_cost_reduction.md §5.2.
    """

    @patch("launch.orchestrator.run_loop.execute_run_from_node")
    def test_progressive_narrowing_across_iterations(
        self, mock_resume: MagicMock, tmp_path: Path
    ) -> None:
        """Filter shrinks after gate fix: iter1 has 2 failed + safety, iter2 has 1 + safety."""
        # Start: 2 failing gates
        run_dir = _setup_run_dir(tmp_path, _multi_issue_report())

        captured_filters: List[List[str]] = []
        call_count = [0]

        def resume_side_effect(run_id, rd, rc, worker):
            call_count[0] += 1
            captured_filters.append(list(rc.get("_heal_gate_filter", [])))

            if call_count[0] == 1:
                # Iter 1: fix gate_truth_layer_completeness, leave gate_scaffold_leak
                report = _make_report(
                    gates=[
                        _make_gate("gate_truth_layer_completeness"),
                        _make_gate("gate_scaffold_leak", ok=False),
                    ],
                    issues=[_make_issue("gate_scaffold_leak", "error", "SCAFFOLD_LEAK")],
                )
                _write_report(rd, report)
            elif call_count[0] == 2:
                # Iter 2: fix gate_scaffold_leak too → all pass (non-partial)
                _write_report(rd, _all_pass_report())
            else:
                _write_report(rd, _all_pass_report())
            return _mock_run_result(0)

        mock_resume.side_effect = resume_side_effect

        run_heal_loop("r_test", run_dir, {}, max_steps=5)

        # Must have captured at least 2 filters
        assert len(captured_filters) >= 2
        filter_1 = set(captured_filters[0])
        filter_2 = set(captured_filters[1])

        # Iter 1 filter: both failed gates + safety
        assert "gate_truth_layer_completeness" in filter_1
        assert "gate_scaffold_leak" in filter_1

        # Iter 2 filter: only gate_scaffold_leak + safety (gate_truth passed)
        assert "gate_scaffold_leak" in filter_2
        assert "gate_truth_layer_completeness" not in filter_2 or \
            "gate_truth_layer_completeness" in _HEAL_SAFETY_GATES

        # Filter 2 is a subset of (or equal to) filter 1 (narrowed)
        assert filter_2 <= filter_1

    @patch("launch.orchestrator.run_loop.execute_run_from_node")
    def test_progressive_narrowing_safety_gates_always_present(
        self, mock_resume: MagicMock, tmp_path: Path
    ) -> None:
        """Safety gates remain in filter even when no failed gate is a safety gate."""
        # Only gate_scaffold_leak fails (not a safety gate)
        report = _make_report(
            gates=[_make_gate("gate_scaffold_leak", ok=False)],
            issues=[_make_issue("gate_scaffold_leak", "error", "SCAFFOLD_LEAK")],
        )
        run_dir = _setup_run_dir(tmp_path, report)

        captured_filters: List[List[str]] = []

        def resume_side_effect(run_id, rd, rc, worker):
            captured_filters.append(list(rc.get("_heal_gate_filter", [])))
            _write_report(rd, _all_pass_report())
            return _mock_run_result(0)

        mock_resume.side_effect = resume_side_effect

        run_heal_loop("r_test", run_dir, {}, max_steps=1)

        assert len(captured_filters) >= 1
        filter_set = set(captured_filters[0])
        for safety_gate in _HEAL_SAFETY_GATES:
            assert safety_gate in filter_set


class TestResumeWithoutFilter:
    """Verify that run_gates works correctly without ``_heal_gate_filter``.

    This simulates ``launch resume --from-worker W9`` where the persisted
    run_config has no transient key.  All gates must execute; no skipped entries.

    Spec: specs/50_healing_cost_reduction.md §5.8.
    """

    @patch("launch.validation_engine.registry_loader.load_registry")
    @patch("launch.validation_engine.adapters.ADAPTER_DISPATCH", new_callable=dict)
    @patch("launch.validation_engine.context.GateContext")
    def test_resume_without_filter_runs_all_gates(
        self, mock_ctx_cls: MagicMock, mock_dispatch: dict, mock_load: MagicMock
    ) -> None:
        """No ``_heal_gate_filter`` in run_config → all gates executed, zero skipped."""
        from launch.validation_engine.runner import run_gates
        from launch.validation_engine.gate_types import GateDefinition, RunnerType

        g1 = GateDefinition(
            gate_id="gate_a", display_name="gate_a", order=1,
            module="m", callable_name="c",
            runner_type=RunnerType.EXECUTE_GATE,
        )
        g2 = GateDefinition(
            gate_id="gate_b", display_name="gate_b", order=2,
            module="m", callable_name="c",
            runner_type=RunnerType.EXECUTE_GATE,
        )
        mock_load.return_value = [g1, g2]

        def adapter(gdef, ctx):
            return True, []

        mock_dispatch[RunnerType.EXECUTE_GATE] = adapter
        mock_ctx_cls.return_value = MagicMock(artifact_block_skip=False)

        # Simulate resume: run_config has NO _heal_gate_filter
        results, issues = run_gates(
            Path("/fake"), {"product_slug": "test"}, "local"
        )

        assert len(results) == 2
        assert not any(r.get("skipped") for r in results)
        assert all(r["ok"] for r in results)

    @patch("launch.validation_engine.registry_loader.load_registry")
    @patch("launch.validation_engine.adapters.ADAPTER_DISPATCH", new_callable=dict)
    @patch("launch.validation_engine.context.GateContext")
    def test_resume_without_filter_no_partial_flag(
        self, mock_ctx_cls: MagicMock, mock_dispatch: dict, mock_load: MagicMock
    ) -> None:
        """Without filter, W9 report should NOT have ``partial`` key."""
        from launch.validation_engine.runner import run_gates
        from launch.validation_engine.gate_types import GateDefinition, RunnerType

        g1 = GateDefinition(
            gate_id="gate_a", display_name="gate_a", order=1,
            module="m", callable_name="c",
            runner_type=RunnerType.EXECUTE_GATE,
        )
        mock_load.return_value = [g1]

        def adapter(gdef, ctx):
            return True, []

        mock_dispatch[RunnerType.EXECUTE_GATE] = adapter
        mock_ctx_cls.return_value = MagicMock(artifact_block_skip=False)

        results, issues = run_gates(
            Path("/fake"), {}, "local"
        )

        # No skipped gates → W9 would NOT set partial flag
        assert not any(r.get("skipped") for r in results)
