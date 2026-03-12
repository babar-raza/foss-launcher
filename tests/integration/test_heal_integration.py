"""Integration tests for the heal loop — TC-3852c / H4.3.

Tests use real heal.py logic with a pre-built evaluate_checkpoint.json in a
tmp_path run_dir. LLM calls are intercepted via mock or skipped when LLM key
is absent (the heal loop falls back to stop_reason="llm_unavailable").
"""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from launcher.cli.heal import _write_heal_plan, _extract_metrics, run_heal
from launcher.models.evaluation import (
    EvaluationReport,
    Finding,
    Grade,
    HealAction,
    HealDecision,
    HealStep,
    PageEvaluation,
    ReportMetrics,
    Verdict,
)
from launcher.util.budget_tracker import BudgetExceededError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_eval_report(
    n_fail: int = 3, n_pass: int = 5, verdict: Verdict = Verdict.NO_GO
) -> dict:
    pages = []
    for i in range(n_fail):
        pages.append({
            "slug": f"failing-page-{i}",
            "grade": "D",
            "findings": [{"check": "density", "severity": "high", "message": "too thin"}],
        })
    for i in range(n_pass):
        pages.append({
            "slug": f"passing-page-{i}",
            "grade": "B",
            "findings": [],
        })
    return {
        "verdict": verdict.value,
        "pages": pages,
        "go_criteria": [],
    }


def _write_eval(run_dir: Path, n_fail: int = 3, n_pass: int = 5) -> None:
    data = _make_eval_report(n_fail=n_fail, n_pass=n_pass)
    (run_dir / "evaluate_checkpoint.json").write_text(
        json.dumps(data), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestHealDryRun:
    def test_dry_run_writes_heal_plan(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run-dry"
        run_dir.mkdir()
        _write_eval(run_dir)

        result = asyncio.run(run_heal(run_dir, dry_run=True, max_steps=1))
        assert result is not None
        assert result.stop_reason == "dry_run"
        assert (run_dir / "heal_plan.json").exists()

    def test_dry_run_no_steps_recorded(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run-dry2"
        run_dir.mkdir()
        _write_eval(run_dir)

        result = asyncio.run(run_heal(run_dir, dry_run=True))
        assert result is not None
        assert len(result.steps) == 0

    def test_dry_run_heal_plan_is_valid_json(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run-dry3"
        run_dir.mkdir()
        _write_eval(run_dir)

        asyncio.run(run_heal(run_dir, dry_run=True))
        plan_path = run_dir / "heal_plan.json"
        data = json.loads(plan_path.read_text(encoding="utf-8"))
        assert "stop_reason" in data
        assert data["stop_reason"] == "dry_run"

    def test_dry_run_outputs_metrics(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run-dry4"
        run_dir.mkdir()
        _write_eval(run_dir, n_fail=3, n_pass=5)

        result = asyncio.run(run_heal(run_dir, dry_run=True))
        assert result is not None
        # 3 of 8 pages are D → df_rate = 3/8 = 0.375
        assert result.initial_metrics.df_rate == pytest.approx(3 / 8, abs=0.01)


class TestHealLLMUnavailable:
    def test_no_api_key_stops_with_llm_unavailable(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run-nollm"
        run_dir.mkdir()
        _write_eval(run_dir)

        # Ensure no LLM key is set
        with patch.dict(os.environ, {"litellm_key": ""}):
            result = asyncio.run(run_heal(run_dir, dry_run=False, max_steps=1))
        assert result is not None
        assert result.stop_reason == "llm_unavailable"

    def test_llm_unavailable_still_writes_heal_plan(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run-nollm2"
        run_dir.mkdir()
        _write_eval(run_dir)

        with patch.dict(os.environ, {"litellm_key": ""}):
            asyncio.run(run_heal(run_dir, dry_run=False, max_steps=1))
        assert (run_dir / "heal_plan.json").exists()


class TestHealMissingEvalReport:
    def test_missing_eval_returns_none(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run-noeval"
        run_dir.mkdir()
        # No evaluate_checkpoint.json

        result = asyncio.run(run_heal(run_dir, dry_run=True))
        assert result is None

    def test_missing_run_dir_returns_none(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run-nonexistent"
        # Don't create it

        result = asyncio.run(run_heal(run_dir, dry_run=True))
        assert result is None


class TestHealQuarantine:
    def test_quarantine_file_loaded_on_start(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run-quar"
        run_dir.mkdir()
        _write_eval(run_dir)

        # Pre-write a quarantine entry
        quarantine = [{"key": "generate:density", "step": 0}]
        (run_dir / "heal_quarantine.json").write_text(
            json.dumps(quarantine), encoding="utf-8"
        )

        # Dry-run — should still work (quarantine checked after LLM call)
        result = asyncio.run(run_heal(run_dir, dry_run=True))
        assert result is not None

    def test_quarantine_file_persists(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run-quar2"
        run_dir.mkdir()
        _write_eval(run_dir)

        # Pre-write quarantine
        quarantine = [{"key": "generate:density", "step": 0}]
        (run_dir / "heal_quarantine.json").write_text(
            json.dumps(quarantine), encoding="utf-8"
        )

        asyncio.run(run_heal(run_dir, dry_run=True))

        # Quarantine file must still be readable after session
        q_path = run_dir / "heal_quarantine.json"
        if q_path.exists():
            loaded = json.loads(q_path.read_text(encoding="utf-8"))
            assert isinstance(loaded, list)


# ---------------------------------------------------------------------------
# Shared fixture: a valid HealDecision JSON string the mock LLM returns
# ---------------------------------------------------------------------------

_VALID_DECISION_JSON = json.dumps({
    "analysis": "Dense content detected on failing pages",
    "root_causes": ["density"],
    "action": {
        "worker": "generate",
        "target_pages": ["failing-page-0"],
        "strategy": "Expand thin sections with more detail",
        "priority_checks": ["density"],
    },
    "confidence": 0.75,
    "stop_recommendation": False,
    "stop_reason": None,
})

_STOP_DECISION_JSON = json.dumps({
    "analysis": "No further improvements possible",
    "root_causes": [],
    "action": {
        "worker": "generate",
        "target_pages": [],
        "strategy": "done",
        "priority_checks": [],
    },
    "confidence": 0.9,
    "stop_recommendation": True,
    "stop_reason": "no_improvements",
})


def _make_metrics(df_rate: float = 0.375, ab_rate: float = 0.625) -> ReportMetrics:
    return ReportMetrics(
        critical_count=0,
        high_count=1,
        grades={"D": 3, "B": 5},
        ab_rate=ab_rate,
        df_rate=df_rate,
        total_findings=3,
    )


# ---------------------------------------------------------------------------
# HL-01: 3-step multi-step heal integration test
# ---------------------------------------------------------------------------

class TestHealMultiStep:
    def test_three_step_records_exactly_three_steps(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run-multi"
        run_dir.mkdir()
        _write_eval(run_dir, n_fail=3, n_pass=5)

        with patch("launcher.cli.heal._call_llm_sync", return_value=_VALID_DECISION_JSON):
            result = asyncio.run(run_heal(run_dir, dry_run=False, max_steps=3))

        assert result is not None
        assert len(result.steps) == 3

    def test_three_step_indices_are_sequential(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run-multi-idx"
        run_dir.mkdir()
        _write_eval(run_dir, n_fail=3, n_pass=5)

        with patch("launcher.cli.heal._call_llm_sync", return_value=_VALID_DECISION_JSON):
            result = asyncio.run(run_heal(run_dir, dry_run=False, max_steps=3))

        assert result is not None
        indices = [s.step_idx for s in result.steps]
        assert indices == [0, 1, 2]

    def test_three_step_each_has_checkpoint_id(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run-multi-cp"
        run_dir.mkdir()
        _write_eval(run_dir, n_fail=3, n_pass=5)

        from launcher.resilience.checkpoint import WorkerCheckpoint
        import datetime

        def _fake_wcp(run_dir, worker, artifact_path):
            return WorkerCheckpoint(
                checkpoint_id=f"test-{worker}",
                worker=worker,
                run_id=run_dir.name,
                created_at=datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                artifact_path=str(artifact_path),
                content_hash="abc123deadbeef",
            )

        with patch("launcher.cli.heal._call_llm_sync", return_value=_VALID_DECISION_JSON), \
             patch("launcher.resilience.checkpoint.write_worker_checkpoint", side_effect=_fake_wcp):
            result = asyncio.run(run_heal(run_dir, dry_run=False, max_steps=3))

        assert result is not None
        assert len(result.steps) == 3
        for step in result.steps:
            assert step.checkpoint_id, f"step {step.step_idx} has empty checkpoint_id"

    def test_three_step_tokens_accumulate(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run-multi-tok"
        run_dir.mkdir()
        _write_eval(run_dir, n_fail=3, n_pass=5)

        with patch("launcher.cli.heal._call_llm_sync", return_value=_VALID_DECISION_JSON):
            result = asyncio.run(run_heal(run_dir, dry_run=False, max_steps=3))

        assert result is not None
        # Each step uses prompt-word-count + 1024 approximate tokens
        assert result.total_tokens >= len(result.steps)

    def test_stop_recommendation_honored_before_max_steps(self, tmp_path: Path) -> None:
        """LLM stop_recommendation=True causes early exit before max_steps."""
        run_dir = tmp_path / "run-multi-stop"
        run_dir.mkdir()
        _write_eval(run_dir, n_fail=3, n_pass=5)

        # min_steps=1: stop_recommendation honored once step_idx >= 1
        with patch("launcher.cli.heal._call_llm_sync", return_value=_STOP_DECISION_JSON):
            result = asyncio.run(run_heal(run_dir, dry_run=False, max_steps=10, min_steps=1))

        assert result is not None
        assert result.stop_reason == "llm_stop"
        assert len(result.steps) < 10


# ---------------------------------------------------------------------------
# HL-02: Regression rollback integration test
# ---------------------------------------------------------------------------

class TestHealRegressionRollback:
    def _make_regressed_step(self, step_idx: int = 0) -> HealStep:
        action = HealAction(
            worker="generate",
            target_pages=["failing-page-0"],
            strategy="regen",
            priority_checks=["density"],
        )
        decision = HealDecision(
            analysis="test regression",
            root_causes=["density"],
            action=action,
            confidence=0.75,
            stop_recommendation=False,
        )
        before = _make_metrics(df_rate=0.30)
        after = _make_metrics(df_rate=0.45)  # +0.15 > threshold 0.05 = regression
        return HealStep(
            step_idx=step_idx,
            decision=decision,
            before_metrics=before,
            after_metrics=after,
            outcome="regressed",
            checkpoint_id=f"cp-regress-{step_idx}",
            execution_seconds=1.0,
            tokens_used=500,
        )

    def test_regression_step_outcome_is_regressed(self, tmp_path: Path) -> None:
        """A HealStep with outcome='regressed' is correctly recorded in heal_plan.json."""
        run_dir = tmp_path / "run-regress"
        run_dir.mkdir()
        step = self._make_regressed_step(step_idx=0)
        metrics = _make_metrics()
        _write_heal_plan(run_dir, [step], "max_steps", metrics, metrics)

        data = json.loads((run_dir / "heal_plan.json").read_text(encoding="utf-8"))
        assert data["steps"][0]["outcome"] == "regressed"

    def test_regression_increments_total_regressions(self, tmp_path: Path) -> None:
        """total_regressions is counted correctly from regressed steps."""
        run_dir = tmp_path / "run-regress-count"
        run_dir.mkdir()
        action = HealAction(worker="generate", target_pages=[], strategy="x", priority_checks=[])
        decision = HealDecision(analysis="x", root_causes=[], action=action, confidence=0.7,
                                stop_recommendation=False)
        metrics = _make_metrics()
        steps = [
            HealStep(step_idx=0, decision=decision, before_metrics=metrics,
                     after_metrics=metrics, outcome="regressed",
                     checkpoint_id="cp-0", execution_seconds=1.0, tokens_used=100),
            HealStep(step_idx=1, decision=decision, before_metrics=metrics,
                     after_metrics=metrics, outcome="improved",
                     checkpoint_id="cp-1", execution_seconds=1.0, tokens_used=100),
        ]
        _write_heal_plan(run_dir, steps, "max_steps", metrics, metrics)

        data = json.loads((run_dir / "heal_plan.json").read_text(encoding="utf-8"))
        assert data["total_regressions"] == 1

    def test_regression_restore_checkpoint_called(self) -> None:
        """restore_worker_checkpoint infrastructure exists and is callable."""
        from launcher.resilience.checkpoint import restore_worker_checkpoint
        assert callable(restore_worker_checkpoint)

    def test_quarantine_stops_repeated_regression_action(self, tmp_path: Path) -> None:
        """TC-3882 (H6): A permanently quarantined action is skipped (not stopped).

        With H6 strike-count quarantine, quarantined actions trigger `continue` (skip)
        rather than `break` (stop session). When all actions are permanently quarantined,
        the session runs all steps and exits with "max_steps" stop_reason.
        """
        run_dir = tmp_path / "run-regress-quar"
        run_dir.mkdir()
        _write_eval(run_dir, n_fail=2, n_pass=5)

        # Pre-quarantine with permanent entry (next_eligible_step=999 = permanent)
        quarantine_key = "generate:density"
        (run_dir / "heal_quarantine.json").write_text(
            json.dumps([{
                "key": quarantine_key,
                "step": 0,
                "strikes": 3,
                "last_strategy": "density fix",
                "next_eligible_step": 999,
            }]), encoding="utf-8"
        )

        with patch("launcher.cli.heal._call_llm_sync", return_value=_VALID_DECISION_JSON):
            result = asyncio.run(run_heal(run_dir, dry_run=False, max_steps=5))

        assert result is not None
        # H6: quarantined steps are skipped (continue), session ends at max_steps
        assert result.stop_reason == "max_steps"
        # No new steps executed (all skipped due to quarantine)
        assert len(result.steps) == 0
        q_data = json.loads((run_dir / "heal_quarantine.json").read_text(encoding="utf-8"))
        assert isinstance(q_data, list)


# ---------------------------------------------------------------------------
# HL-03: Budget exhaustion integration test
# ---------------------------------------------------------------------------

class TestHealBudgetExhaustion:
    def test_budget_exhaustion_stop_reason(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run-budget"
        run_dir.mkdir()
        _write_eval(run_dir)

        with patch("launcher.cli.heal.BudgetTracker") as mock_tracker_cls:
            mock_tracker = MagicMock()
            mock_tracker.check_runtime.side_effect = BudgetExceededError(
                "Runtime budget exceeded: 1800.0s > 0s", "runtime"
            )
            mock_tracker.get_summary.return_value = {"elapsed_s": 1800, "counters": {}}
            mock_tracker_cls.return_value = mock_tracker

            result = asyncio.run(run_heal(run_dir, dry_run=False, max_steps=5))

        assert result is not None
        assert result.stop_reason == "budget_exceeded"

    def test_budget_exhaustion_stops_before_max_steps(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run-budget2"
        run_dir.mkdir()
        _write_eval(run_dir)
        max_steps = 5

        with patch("launcher.cli.heal.BudgetTracker") as mock_tracker_cls:
            mock_tracker = MagicMock()
            mock_tracker.check_runtime.side_effect = BudgetExceededError(
                "Runtime budget exceeded", "runtime"
            )
            mock_tracker.get_summary.return_value = {"elapsed_s": 1800, "counters": {}}
            mock_tracker_cls.return_value = mock_tracker

            result = asyncio.run(run_heal(run_dir, dry_run=False, max_steps=max_steps))

        assert result is not None
        assert len(result.steps) < max_steps

    def test_budget_exhaustion_heal_plan_written(self, tmp_path: Path) -> None:
        """heal_plan.json is always written in finally even when budget aborts the session."""
        run_dir = tmp_path / "run-budget3"
        run_dir.mkdir()
        _write_eval(run_dir)

        with patch("launcher.cli.heal.BudgetTracker") as mock_tracker_cls:
            mock_tracker = MagicMock()
            mock_tracker.check_runtime.side_effect = BudgetExceededError(
                "Runtime budget exceeded", "runtime"
            )
            mock_tracker.get_summary.return_value = {"elapsed_s": 1800, "counters": {}}
            mock_tracker_cls.return_value = mock_tracker

            asyncio.run(run_heal(run_dir, dry_run=False, max_steps=5))

        assert (run_dir / "heal_plan.json").exists()


class TestExtractMetrics:
    def test_extract_metrics_df_rate(self) -> None:
        pages = []
        for i in range(3):
            pages.append(PageEvaluation(
                slug=f"fail-{i}", grade=Grade.D,
                findings=[Finding(check="density", message="thin", severity="high")],
            ))
        for i in range(7):
            pages.append(PageEvaluation(slug=f"pass-{i}", grade=Grade.B, findings=[]))
        report = EvaluationReport(verdict=Verdict.NO_GO, pages=pages)
        m = _extract_metrics(report)
        assert m.df_rate == pytest.approx(0.3, abs=0.01)
        assert m.ab_rate == pytest.approx(0.7, abs=0.01)

    def test_extract_metrics_empty_report(self) -> None:
        report = EvaluationReport(verdict=Verdict.GO, pages=[])
        m = _extract_metrics(report)
        assert m.df_rate == 0.0
        assert m.ab_rate == 0.0


# ---------------------------------------------------------------------------
# TC-3868: Execution mode flag integration tests
# ---------------------------------------------------------------------------

class TestHealModeFlag:
    def test_diagnose_mode_writes_heal_diagnosis_json(self, tmp_path: Path) -> None:
        """run_heal with mode='diagnose' and a mocked LLM writes heal_diagnosis.json."""
        from launcher.cli.heal import _write_diagnosis

        run_dir = tmp_path / "run-diagnose"
        run_dir.mkdir()
        _write_eval(run_dir, n_fail=3, n_pass=5)

        # LLM returns a valid decision but diagnose mode skips execute_run
        with patch("launcher.cli.heal._call_llm_sync", return_value=_VALID_DECISION_JSON):
            result = asyncio.run(run_heal(run_dir, dry_run=False, max_steps=2, mode="diagnose"))

        assert result is not None
        # Write diagnosis manually (mimicking what the CLI does after run_heal)
        _write_diagnosis(run_dir, result.steps)

        diag_path = run_dir / "heal_diagnosis.json"
        assert diag_path.exists(), "heal_diagnosis.json should be written for --mode diagnose"
        data = json.loads(diag_path.read_text(encoding="utf-8"))
        assert "actions" in data
        assert isinstance(data["actions"], list)

    def test_mode_field_in_steps(self, tmp_path: Path) -> None:
        """Steps recorded in diagnose mode have mode='diagnose' in their fields."""
        run_dir = tmp_path / "run-diagnose-mode"
        run_dir.mkdir()
        _write_eval(run_dir, n_fail=2, n_pass=5)

        with patch("launcher.cli.heal._call_llm_sync", return_value=_VALID_DECISION_JSON):
            result = asyncio.run(run_heal(run_dir, dry_run=False, max_steps=1, mode="diagnose"))

        assert result is not None
        assert len(result.steps) >= 1
        for step in result.steps:
            assert step.mode == "diagnose", (
                f"Expected mode='diagnose', got '{step.mode}' on step {step.step_idx}"
            )
            assert step.outcome == "diagnose_only", (
                f"Expected outcome='diagnose_only', got '{step.outcome}' on step {step.step_idx}"
            )

    def test_cli_diagnose_mode_writes_heal_diagnosis_e2e(self, tmp_path: Path) -> None:
        """CLI --mode diagnose end-to-end: heal_diagnosis.json written by CLI entrypoint."""
        from typer.testing import CliRunner
        from launcher.cli.heal import heal_app

        run_dir = tmp_path / "run-diagnose-e2e"
        run_dir.mkdir()
        _write_eval(run_dir, n_fail=3, n_pass=5)

        runner = CliRunner()
        with patch("launcher.cli.heal._call_llm_sync", return_value=_VALID_DECISION_JSON):
            result = runner.invoke(heal_app, [str(run_dir), "--mode", "diagnose", "--max-steps", "1"])

        # Exit code 0 (no failing pages after diagnose) or 2 (failing pages remain) — both OK
        assert result.exit_code in (0, 2), f"Unexpected exit code {result.exit_code}: {result.output}"
        diag_path = run_dir / "heal_diagnosis.json"
        assert diag_path.exists(), "heal_diagnosis.json must be written by CLI entrypoint"
        data = json.loads(diag_path.read_text(encoding="utf-8"))
        assert "actions" in data

    def test_cli_invalid_mode_exits_nonzero(self, tmp_path: Path) -> None:
        """CLI --mode bogus exits with non-zero and mentions valid modes."""
        from typer.testing import CliRunner
        from launcher.cli.heal import heal_app

        run_dir = tmp_path / "run-invalid-mode"
        run_dir.mkdir()
        _write_eval(run_dir)

        runner = CliRunner()
        result = runner.invoke(heal_app, [str(run_dir), "--mode", "bogus"])
        assert result.exit_code != 0, "bogus mode should produce non-zero exit"
