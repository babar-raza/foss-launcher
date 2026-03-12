"""Unit tests for the heal CLI (TC-3851)."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

import os
from unittest.mock import patch

from launcher.cli.heal import (
    _build_diagnostician_prompt,
    _compress_heal_step,
    _execute_worker_rerun,
    _extract_metrics,
    _is_improved,
    _parse_heal_decision,
    _save_rollback_snapshot,
    _write_diagnosis,
    run_heal,
)
from launcher.models.evaluation import (
    EvaluationReport,
    Grade,
    HealAction,
    HealDecision,
    HealStep,
    PageEvaluation,
    ReportMetrics,
    Verdict,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _minimal_eval_report_dict(grade: str = "D") -> dict:
    """Return a minimal valid EvaluationReport dict."""
    return {
        "verdict": "NO_GO",
        "pages": [
            {
                "slug": "page-1",
                "grade": grade,
                "findings": [
                    {"check": "density", "message": "too short", "severity": "high", "location": "page-1"}
                ],
                "check_results": {},
            }
        ],
        "quality": {"pages_by_grade": {grade: 1}, "avg_word_count": 0.0, "claim_coverage": 0.0},
        "gates": [],
        "root_cause_diagnosis": [],
        "go_criteria": [],
    }


def _write_eval_checkpoint(run_dir: Path, grade: str = "D") -> None:
    """Write a minimal evaluate_checkpoint.json to run_dir."""
    cp = _minimal_eval_report_dict(grade)
    (run_dir / "evaluate_checkpoint.json").write_text(json.dumps(cp), encoding="utf-8")


def _minimal_heal_decision_dict(confidence: float = 0.8) -> dict:
    """Return a minimal valid HealDecision dict."""
    return {
        "analysis": "Page is too short.",
        "root_causes": ["content_too_short"],
        "action": {
            "worker": "generate",
            "target_pages": ["page-1"],
            "strategy": "Add more detail to each section.",
            "priority_checks": ["density"],
        },
        "confidence": confidence,
        "stop_recommendation": False,
        "stop_reason": None,
    }


# ---------------------------------------------------------------------------
# Test 1: _extract_metrics returns correct df_rate and ab_rate
# ---------------------------------------------------------------------------

def test_extract_metrics_df_rate():
    """_extract_metrics returns correct df_rate and ab_rate for a D-grade page."""
    data = _minimal_eval_report_dict("D")
    report = EvaluationReport.model_validate(data)
    metrics = _extract_metrics(report)
    assert metrics.df_rate == pytest.approx(1.0)
    assert metrics.ab_rate == pytest.approx(0.0)
    assert metrics.grades == {"D": 1}
    assert metrics.high_count == 1
    assert metrics.total_findings == 1


# ---------------------------------------------------------------------------
# Test 2: _extract_metrics on empty-pages report → rates = 0.0
# ---------------------------------------------------------------------------

def test_extract_metrics_empty_report():
    """_extract_metrics on a report with no pages produces zero rates."""
    data = {
        "verdict": "GO",
        "pages": [],
        "quality": {},
        "gates": [],
        "root_cause_diagnosis": [],
        "go_criteria": [],
    }
    report = EvaluationReport.model_validate(data)
    metrics = _extract_metrics(report)
    assert metrics.df_rate == pytest.approx(0.0)
    assert metrics.ab_rate == pytest.approx(0.0)
    assert metrics.total_findings == 0


# ---------------------------------------------------------------------------
# Test 3: _is_improved returns True when after.df_rate < before.df_rate
# ---------------------------------------------------------------------------

def test_is_improved_df_rate_decrease():
    """_is_improved returns True when df_rate decreases sufficiently."""
    before = ReportMetrics(
        critical_count=0, high_count=0,
        grades={"D": 5, "A": 5},
        ab_rate=0.5, df_rate=0.5, total_findings=5,
    )
    after = ReportMetrics(
        critical_count=0, high_count=0,
        grades={"D": 2, "A": 8},
        ab_rate=0.8, df_rate=0.2, total_findings=2,
    )
    assert _is_improved(before, after, threshold=0.0) is True


# ---------------------------------------------------------------------------
# Test 4: _parse_heal_decision parses valid JSON when confidence >= threshold
# ---------------------------------------------------------------------------

def test_parse_heal_decision_valid_json():
    """_parse_heal_decision returns HealDecision when confidence meets threshold."""
    raw = json.dumps(_minimal_heal_decision_dict(confidence=0.8))
    decision = _parse_heal_decision(raw, min_confidence=0.6)
    assert decision is not None
    assert decision.confidence == pytest.approx(0.8)
    assert decision.action.worker == "generate"
    assert decision.action.strategy == "Add more detail to each section."


# ---------------------------------------------------------------------------
# Test 5: _parse_heal_decision returns None when confidence < threshold
# ---------------------------------------------------------------------------

def test_parse_heal_decision_below_threshold():
    """_parse_heal_decision returns None when confidence is below the threshold."""
    raw = json.dumps(_minimal_heal_decision_dict(confidence=0.4))
    decision = _parse_heal_decision(raw, min_confidence=0.9)
    assert decision is None


# ---------------------------------------------------------------------------
# Test 6: _parse_heal_decision returns None for non-JSON input
# ---------------------------------------------------------------------------

def test_parse_heal_decision_invalid_json():
    """_parse_heal_decision returns None for non-JSON input."""
    decision = _parse_heal_decision("not valid json at all", min_confidence=0.6)
    assert decision is None


# ---------------------------------------------------------------------------
# Test 7: run_heal dry-run creates heal_plan.json and returns HealResult
# ---------------------------------------------------------------------------

def test_run_heal_dry_run_creates_plan(tmp_path: Path):
    """run_heal in dry-run mode writes heal_plan.json and returns HealResult."""
    _write_eval_checkpoint(tmp_path)

    result = asyncio.run(run_heal(tmp_path, dry_run=True))

    assert result is not None
    assert result.stop_reason == "dry_run"
    plan_file = tmp_path / "heal_plan.json"
    assert plan_file.exists(), "heal_plan.json should be written in finally block"
    plan = json.loads(plan_file.read_text(encoding="utf-8"))
    assert plan["stop_reason"] == "dry_run"
    assert plan["run_id"] == tmp_path.name


# ---------------------------------------------------------------------------
# Test 8: run_heal dry-run output contains "DRY RUN"
# ---------------------------------------------------------------------------

def test_run_heal_dry_run_output_contains_dry_run(tmp_path: Path, capsys):
    """run_heal dry-run prints 'DRY RUN' to stdout."""
    _write_eval_checkpoint(tmp_path)

    asyncio.run(run_heal(tmp_path, dry_run=True))

    captured = capsys.readouterr()
    assert "DRY RUN" in captured.out


# ---------------------------------------------------------------------------
# Test 9: run_heal returns None when run_dir does not exist
# ---------------------------------------------------------------------------

def test_run_heal_missing_run_dir(tmp_path: Path):
    """run_heal returns None when run_dir does not exist."""
    missing = tmp_path / "nonexistent"
    result = asyncio.run(run_heal(missing, dry_run=True))
    assert result is None


# ---------------------------------------------------------------------------
# Test 10: run_heal returns None when evaluate_checkpoint.json is missing
# ---------------------------------------------------------------------------

def test_run_heal_missing_eval_checkpoint(tmp_path: Path):
    """run_heal returns None when evaluate_checkpoint.json is absent."""
    # tmp_path is a real directory but has no evaluate_checkpoint.json
    result = asyncio.run(run_heal(tmp_path, dry_run=True))
    assert result is None


# ---------------------------------------------------------------------------
# Test 11: _parse_heal_decision strips markdown code fences
# ---------------------------------------------------------------------------

def test_parse_heal_decision_strips_code_fences():
    """_parse_heal_decision correctly strips ```json code fences."""
    inner = json.dumps(_minimal_heal_decision_dict(confidence=0.75))
    fenced = f"```json\n{inner}\n```"
    decision = _parse_heal_decision(fenced, min_confidence=0.6)
    assert decision is not None
    assert decision.confidence == pytest.approx(0.75)


# ---------------------------------------------------------------------------
# TC-3855: Rolling compression tests
# ---------------------------------------------------------------------------

def _make_heal_step(step_idx: int, outcome: str = "unchanged") -> HealStep:
    metrics = ReportMetrics(
        critical_count=0, high_count=1,
        grades={"D": 3, "B": 5}, ab_rate=0.5, df_rate=0.3, total_findings=5,
    )
    decision = HealDecision(
        analysis="Content density is low.",
        root_causes=["thin_content"],
        action=HealAction(
            worker="generate",
            target_pages=["page-1"],
            strategy="Regenerate thin sections.",
            priority_checks=["density"],
        ),
        confidence=0.75,
        stop_recommendation=False,
    )
    return HealStep(
        step_idx=step_idx,
        decision=decision,
        before_metrics=metrics,
        after_metrics=metrics,
        outcome=outcome,
        checkpoint_id=f"cp-{step_idx}",
        execution_seconds=1.5,
        tokens_used=500,
    )


def _make_report_with_n_failing(n: int) -> EvaluationReport:
    pages = []
    for i in range(n):
        pages.append(PageEvaluation(
            slug=f"fail-{i}", grade=Grade.D,
            findings=[],
        ))
    for i in range(20 - n):
        pages.append(PageEvaluation(slug=f"pass-{i}", grade=Grade.B, findings=[]))
    return EvaluationReport(verdict=Verdict.NO_GO, pages=pages)


def test_compress_heal_step_format():
    """_compress_heal_step returns a compact single-line summary."""
    step = _make_heal_step(5, outcome="improved")
    compressed = _compress_heal_step(step)
    assert "step=5" in compressed
    assert "worker=generate" in compressed
    assert "outcome=improved" in compressed
    assert "\n" not in compressed


def test_prompt_length_under_6000_with_10_steps_and_20_failing():
    """_build_diagnostician_prompt stays < 6000 chars with 10 steps + 20 failing pages."""
    report = _make_report_with_n_failing(20)
    history = [_make_heal_step(i) for i in range(10)]
    prompt = _build_diagnostician_prompt(report, history, [], {"elapsed_s": 45.0, "counters": {}})
    assert len(prompt) < 6_000, f"Prompt too long: {len(prompt)} chars"


def test_prompt_recent_steps_in_full():
    """_build_diagnostician_prompt includes RECENT label for last 3 steps."""
    report = _make_report_with_n_failing(5)
    history = [_make_heal_step(i) for i in range(6)]
    prompt = _build_diagnostician_prompt(report, history, [], {})
    assert "RECENT" in prompt


def test_prompt_compressed_earlier_steps():
    """_build_diagnostician_prompt includes EARLIER (compressed) for steps beyond last 3."""
    report = _make_report_with_n_failing(3)
    history = [_make_heal_step(i) for i in range(6)]
    prompt = _build_diagnostician_prompt(report, history, [], {})
    assert "EARLIER" in prompt


def test_prompt_no_compression_with_few_steps():
    """With 3 or fewer steps, no EARLIER compression label appears."""
    report = _make_report_with_n_failing(2)
    history = [_make_heal_step(i) for i in range(3)]
    prompt = _build_diagnostician_prompt(report, history, [], {})
    assert "EARLIER" not in prompt


# ---------------------------------------------------------------------------
# HO-03: FOSS_LAUNCHER_LLM_CACHE env var wired in heal session
# ---------------------------------------------------------------------------

def test_heal_sets_llm_cache_env_var(tmp_path: Path) -> None:
    """FOSS_LAUNCHER_LLM_CACHE is set to '1' during the heal session."""
    _write_eval_checkpoint(tmp_path)
    captured: list[str | None] = []

    original_build = _build_diagnostician_prompt

    def _capture(*args, **kwargs):
        captured.append(os.environ.get("FOSS_LAUNCHER_LLM_CACHE"))
        return original_build(*args, **kwargs)

    # Ensure the var is not set before the test
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("FOSS_LAUNCHER_LLM_CACHE", None)
        with patch("launcher.cli.heal._build_diagnostician_prompt", side_effect=_capture):
            asyncio.run(run_heal(tmp_path, dry_run=True))

    assert captured, "_build_diagnostician_prompt must have been called"
    assert captured[0] == "1", f"Expected '1', got {captured[0]!r}"


def test_heal_restores_cache_env_on_exit(tmp_path: Path) -> None:
    """FOSS_LAUNCHER_LLM_CACHE is restored to its prior value after the session ends."""
    _write_eval_checkpoint(tmp_path)

    with patch.dict(os.environ, {"FOSS_LAUNCHER_LLM_CACHE": "0"}, clear=False):
        asyncio.run(run_heal(tmp_path, dry_run=True))
        assert os.environ.get("FOSS_LAUNCHER_LLM_CACHE") == "0", (
            "Prior value '0' should be restored after heal session"
        )


def test_cache_env_not_set_when_heal_not_active() -> None:
    """Outside of a heal session, FOSS_LAUNCHER_LLM_CACHE is not set by the library."""
    from launcher.clients.llm_cache import cache_enabled

    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("FOSS_LAUNCHER_LLM_CACHE", None)
        assert not cache_enabled(), (
            "cache_enabled() must return False when env var is absent"
        )


# ---------------------------------------------------------------------------
# HO-04: Adaptive F→D→C page prioritization in heal
# ---------------------------------------------------------------------------

def _make_eval_report_with_grades(grade_map: dict[str, str]) -> EvaluationReport:
    """Build a minimal EvaluationReport with pages at specific grades.

    grade_map: {slug → grade_letter}
    """
    pages = [
        PageEvaluation(slug=slug, grade=Grade(letter), findings=[])
        for slug, letter in grade_map.items()
    ]
    return EvaluationReport(verdict=Verdict.NO_GO, pages=pages)


def _make_budget(max_llm_calls: int = 100) -> object:
    """Build a real BudgetTracker with generous limits."""
    from launcher.util.budget_tracker import BudgetTracker
    return BudgetTracker(budgets={
        "max_tokens": 1_000_000,
        "max_runtime_s": 3600,
        "max_llm_calls": max_llm_calls,
        "max_llm_tokens": 1_000_000,
        "max_file_writes": 1000,
        "max_patch_attempts": 100,
    })


def test_prioritization_orders_f_before_d_before_c() -> None:
    """F-grade pages appear before D and C in prioritized target list."""
    from launcher.cli.heal import _prioritize_target_pages

    report = _make_eval_report_with_grades({
        "page-c": "C",
        "page-f": "F",
        "page-d": "D",
    })
    budget = _make_budget(max_llm_calls=100)
    result = _prioritize_target_pages(report, budget, step_idx=0, max_steps=5)

    assert result[0] == "page-f", f"F-page should come first, got {result}"
    assert result[1] == "page-d", f"D-page should come second, got {result}"
    assert result[2] == "page-c", f"C-page should come third, got {result}"


def test_prioritization_respects_budget_cap() -> None:
    """At most calls_per_step pages are returned (capped by budget)."""
    from launcher.cli.heal import _prioritize_target_pages

    # 10 pages, but budget only allows 2 calls across remaining 5 steps → cap=1 per step
    grade_map = {f"page-{i}": "D" for i in range(10)}
    report = _make_eval_report_with_grades(grade_map)
    budget = _make_budget(max_llm_calls=5)  # 5 calls / 5 steps remaining = 1 per step

    result = _prioritize_target_pages(report, budget, step_idx=0, max_steps=5)
    # calls_per_step = 5 // 5 = 1; cap = max(1, 1) = 1
    assert len(result) <= max(1, 1)


def test_prioritization_empty_fails_no_crash() -> None:
    """No failing pages → empty target list; function does not raise."""
    from launcher.cli.heal import _prioritize_target_pages

    report = _make_eval_report_with_grades({"page-a": "A", "page-b": "B"})
    budget = _make_budget()
    result = _prioritize_target_pages(report, budget, step_idx=0, max_steps=5)
    assert isinstance(result, list)
    assert len(result) == 0


def test_prioritization_deterministic() -> None:
    """Same input → same output regardless of dict iteration order."""
    from launcher.cli.heal import _prioritize_target_pages

    grade_map = {"page-z": "D", "page-a": "F", "page-m": "C"}
    report1 = _make_eval_report_with_grades(grade_map)
    report2 = _make_eval_report_with_grades(grade_map)
    budget = _make_budget()

    result1 = _prioritize_target_pages(report1, budget, step_idx=0, max_steps=5)
    result2 = _prioritize_target_pages(report2, budget, step_idx=0, max_steps=5)
    assert result1 == result2


# ---------------------------------------------------------------------------
# TC-3868: Execution mode tests
# ---------------------------------------------------------------------------

def _make_budget_with_remaining(remaining_runtime_s: float = 600.0) -> object:
    """Build a BudgetTracker whose remaining_for_step returns the given runtime."""
    from unittest.mock import MagicMock
    budget = MagicMock()
    budget.remaining_for_step.return_value = {"remaining_runtime_s": remaining_runtime_s, "calls_per_step": 5}
    budget.record_llm_call = MagicMock()
    budget.check_runtime = MagicMock()
    budget.get_summary = MagicMock(return_value={"elapsed_s": 0, "counters": {}})
    return budget


def _make_sample_metrics() -> ReportMetrics:
    return ReportMetrics(
        critical_count=0,
        high_count=1,
        grades={"D": 3, "B": 5},
        ab_rate=0.625,
        df_rate=0.375,
        total_findings=3,
    )


class TestHealModes:
    """TC-3868: tests for the three execution modes."""

    def test_diagnose_mode_returns_diagnose_only(self, tmp_path: Path) -> None:
        """_execute_worker_rerun with mode='diagnose' returns (None, 'diagnose_only', None)."""
        budget = _make_budget_with_remaining(600)
        metrics = _make_sample_metrics()

        result = asyncio.run(_execute_worker_rerun(
            run_dir=tmp_path,
            worker="generate",
            step_idx=0,
            max_steps=5,
            budget=budget,
            mode="diagnose",
            checkpoint_id="",
            current_metrics=metrics,
        ))

        after_m, outcome, fallback, executed_mode = result
        assert after_m is None
        assert outcome == "diagnose_only"
        assert fallback is None
        assert executed_mode == "diagnose"

    def test_budget_exceeded_returns_budget_exceeded(self, tmp_path: Path) -> None:
        """_execute_worker_rerun returns 'budget_exceeded' when remaining_runtime_s < 60."""
        budget = _make_budget_with_remaining(remaining_runtime_s=0.0)
        metrics = _make_sample_metrics()

        result = asyncio.run(_execute_worker_rerun(
            run_dir=tmp_path,
            worker="generate",
            step_idx=0,
            max_steps=5,
            budget=budget,
            mode="worker",
            checkpoint_id="",
            current_metrics=metrics,
        ))

        after_m, outcome, fallback, executed_mode = result
        assert outcome == "budget_exceeded"
        assert after_m == metrics
        assert executed_mode == "worker"

    def test_save_rollback_creates_file(self, tmp_path: Path) -> None:
        """_save_rollback_snapshot writes heal_rollback_{step_idx}.json."""
        metrics = _make_sample_metrics()
        _save_rollback_snapshot(tmp_path, 0, metrics)

        snapshot = tmp_path / "heal_rollback_0.json"
        assert snapshot.exists(), "heal_rollback_0.json should exist after _save_rollback_snapshot"
        data = json.loads(snapshot.read_text(encoding="utf-8"))
        assert data["df_rate"] == pytest.approx(0.375)

    def test_write_diagnosis_creates_file(self, tmp_path: Path) -> None:
        """_write_diagnosis writes heal_diagnosis.json with 'actions' key."""
        steps = [_make_heal_step(i) for i in range(3)]
        _write_diagnosis(tmp_path, steps)

        diag = tmp_path / "heal_diagnosis.json"
        assert diag.exists(), "heal_diagnosis.json should exist after _write_diagnosis"
        data = json.loads(diag.read_text(encoding="utf-8"))
        assert "actions" in data
        assert isinstance(data["actions"], list)
        assert data["total_steps"] == 3

    def test_run_heal_diagnose_mode_writes_plan(self, tmp_path: Path) -> None:
        """run_heal with mode='diagnose' returns a result and writes heal_plan.json."""
        _write_eval_checkpoint(tmp_path)

        with patch("launcher.cli.heal._call_llm_sync", return_value=json.dumps({
            "analysis": "Content is thin.",
            "root_causes": ["thin_content"],
            "action": {
                "worker": "generate",
                "target_pages": ["page-1"],
                "strategy": "Expand thin sections.",
                "priority_checks": ["density"],
            },
            "confidence": 0.8,
            "stop_recommendation": True,
            "stop_reason": "diagnose_only",
        })):
            result = asyncio.run(run_heal(tmp_path, dry_run=False, max_steps=1, mode="diagnose"))

        assert result is not None
        assert (tmp_path / "heal_plan.json").exists()

    def test_current_metrics_advances_across_steps(self, tmp_path: Path) -> None:
        """current_metrics rolls forward: step[i+1].before_metrics == step[i].after_metrics."""
        _write_eval_checkpoint(tmp_path)

        step_call_count = 0
        df_rates = [0.8, 0.6, 0.4]

        async def _mock_rerun(**kwargs):
            nonlocal step_call_count
            m = ReportMetrics(
                critical_count=0, high_count=0,
                grades={"D": 1}, ab_rate=1.0 - df_rates[step_call_count],
                df_rate=df_rates[step_call_count], total_findings=1,
            )
            step_call_count += 1
            return (m, "improved", None, "worker")

        decision_json = json.dumps({
            "analysis": "thin", "root_causes": ["density"],
            "action": {"worker": "generate", "target_pages": ["page-1"],
                       "strategy": "expand", "priority_checks": ["density"]},
            "confidence": 0.8, "stop_recommendation": False, "stop_reason": None,
        })

        with patch("launcher.cli.heal._call_llm_sync", return_value=decision_json), \
             patch("launcher.cli.heal._execute_worker_rerun", side_effect=_mock_rerun):
            result = asyncio.run(run_heal(tmp_path, dry_run=False, max_steps=3, mode="worker"))

        assert result is not None
        assert len(result.steps) == 3
        # step 1's before_metrics must equal step 0's after_metrics
        assert result.steps[1].before_metrics.df_rate == pytest.approx(0.8)
        assert result.steps[2].before_metrics.df_rate == pytest.approx(0.6)
        assert result.final_metrics.df_rate == pytest.approx(0.4)

    def test_diagnose_mode_metrics_do_not_advance(self, tmp_path: Path) -> None:
        """In diagnose mode, current_metrics must NOT advance (after_metrics is None)."""
        _write_eval_checkpoint(tmp_path)

        decision_json = json.dumps({
            "analysis": "thin", "root_causes": ["density"],
            "action": {"worker": "generate", "target_pages": ["page-1"],
                       "strategy": "expand", "priority_checks": ["density"]},
            "confidence": 0.8, "stop_recommendation": False, "stop_reason": None,
        })

        with patch("launcher.cli.heal._call_llm_sync", return_value=decision_json):
            result = asyncio.run(run_heal(tmp_path, dry_run=False, max_steps=2, mode="diagnose"))

        assert result is not None
        assert len(result.steps) == 2
        initial_df = result.initial_metrics.df_rate
        for step in result.steps:
            assert step.before_metrics.df_rate == pytest.approx(initial_df), (
                f"step {step.step_idx} before_metrics should equal initial in diagnose mode"
            )

    def test_worker_falls_back_to_full_on_invalid_checkpoint(self, tmp_path: Path) -> None:
        """_execute_worker_rerun returns executed_mode='full' when checkpoint is invalid."""
        import yaml
        # Write a minimal run_config.yaml so _load_run_config succeeds
        minimal_config = {
            "family": "test-family",
            "platform": "python",
            "repo_url": "https://github.com/test/repo",
            "output": {"run_dir": str(tmp_path)},
        }
        (tmp_path / "run_config.yaml").write_text(yaml.dump(minimal_config), encoding="utf-8")

        budget = _make_budget_with_remaining(600)
        metrics = _make_sample_metrics()

        from unittest.mock import AsyncMock
        mock_execute = AsyncMock(return_value=None)
        with patch("launcher.resilience.checkpoint.load_worker_checkpoint", return_value=None), \
             patch("launcher.orchestrator.run_loop.execute_run", mock_execute):
            result = asyncio.run(_execute_worker_rerun(
                run_dir=tmp_path,
                worker="generate",
                step_idx=0,
                max_steps=5,
                budget=budget,
                mode="worker",
                checkpoint_id="test-cp-123",
                current_metrics=metrics,
            ))

        after_m, outcome, fallback_reason, executed_mode = result
        assert fallback_reason == "checkpoint_invalid"
        assert executed_mode == "full"

    def test_worker_mode_no_fallback_when_checkpoint_valid(self, tmp_path: Path) -> None:
        """_execute_worker_rerun uses actual_mode='worker' when checkpoint validates OK."""
        from unittest.mock import AsyncMock, MagicMock
        import yaml
        minimal_config = {
            "family": "test-family",
            "platform": "python",
            "repo_url": "https://github.com/test/repo",
            "output": {"run_dir": str(tmp_path)},
        }
        (tmp_path / "run_config.yaml").write_text(yaml.dump(minimal_config), encoding="utf-8")

        budget = _make_budget_with_remaining(600)
        metrics = _make_sample_metrics()

        fake_cp = MagicMock()
        fake_cp.checkpoint_id = "test-cp-valid"

        with patch("launcher.resilience.checkpoint.load_worker_checkpoint", return_value=fake_cp), \
             patch("launcher.resilience.checkpoint.restore_worker_checkpoint", return_value=True), \
             patch("launcher.orchestrator.run_loop.execute_run", new_callable=AsyncMock, return_value=None):
            result = asyncio.run(_execute_worker_rerun(
                run_dir=tmp_path,
                worker="generate",
                step_idx=0,
                max_steps=5,
                budget=budget,
                mode="worker",
                checkpoint_id="test-cp-valid",
                current_metrics=metrics,
            ))

        after_m, outcome, fallback_reason, executed_mode = result
        assert fallback_reason is None
        assert executed_mode == "worker"
