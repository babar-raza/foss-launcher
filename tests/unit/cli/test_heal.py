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
    _win_path,
    choose_worker,
    count_failed_gates,
    extract_worker_from_recommendation,
    is_stuck,
    run_heal_loop,
    write_heal_plan,
)


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
        """Max steps reached without convergence."""
        run_dir = _setup_run_dir(tmp_path, _truth_missing_report())
        call_count = 0

        def resume_side_effect(run_id, rd, rc, worker):
            nonlocal call_count
            call_count += 1
            # Each step reduces by 0 on even, and we alternate reports
            # to avoid stuck detection — use different reports each time
            if call_count % 2 == 1:
                _write_report(rd, _scaffold_report())  # 2 failures (changed from truth)
            else:
                _write_report(rd, _truth_missing_report())  # 1 failure (back to truth)
            return _mock_run_result(0)

        mock_resume.side_effect = resume_side_effect

        result = run_heal_loop("r_test", run_dir, {}, max_steps=2)

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
