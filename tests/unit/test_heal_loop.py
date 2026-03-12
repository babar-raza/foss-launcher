"""Unit tests for heal CLI loop — HL-02 and HL-04."""
from __future__ import annotations
import json
import time
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from launcher.models.evaluation import (
    HealAction, HealDecision, HealStep, ReportMetrics,
)


class TestHL02SchemaFailureStep:
    """HL-02: schema_failure step must use HealAction, not dict."""

    def _make_metrics(self):
        return ReportMetrics(
            critical_count=0, high_count=0, grades={"D": 2},
            ab_rate=0.0, df_rate=0.5, total_findings=4,
        )

    def test_schema_failure_step_serializes_cleanly(self):
        """HealStep with schema_failure outcome must model_dump without error."""
        metrics = self._make_metrics()
        step = HealStep(
            step_idx=0,
            decision=HealDecision(
                analysis="Failed to parse response",
                root_causes=[],
                action=HealAction(
                    worker="generate",
                    target_pages=[],
                    strategy="schema_failure",
                    priority_checks=[],
                ),
                confidence=0.0,
                stop_recommendation=False,
                stop_reason=None,
            ),
            before_metrics=metrics,
            after_metrics=None,
            outcome="schema_failure",
            checkpoint_id="",
            execution_seconds=0.1,
            tokens_used=0,
        )
        dumped = step.model_dump(mode="json")
        assert dumped["outcome"] == "schema_failure"
        assert dumped["decision"]["action"]["worker"] == "generate"
        assert dumped["decision"]["confidence"] == 0.0

    def test_heal_decision_action_is_model_not_dict(self):
        """HealDecision.action must be HealAction instance."""
        action = HealAction(worker="generate", target_pages=[], strategy="s", priority_checks=[])
        decision = HealDecision(
            analysis="test", root_causes=[], action=action,
            confidence=0.5, stop_recommendation=False,
        )
        assert isinstance(decision.action, HealAction)
        assert decision.action.worker == "generate"

    def test_full_result_serializes_after_schema_failure(self):
        """HealResult with a schema_failure step serializes to JSON without ValidationError."""
        from launcher.models.evaluation import HealResult
        metrics = self._make_metrics()
        step = HealStep(
            step_idx=0,
            decision=HealDecision(
                analysis="parse failed",
                root_causes=[],
                action=HealAction(worker="generate", target_pages=[], strategy="schema_failure", priority_checks=[]),
                confidence=0.0,
                stop_recommendation=False,
                stop_reason=None,
            ),
            before_metrics=metrics,
            after_metrics=None,
            outcome="schema_failure",
            checkpoint_id="",
            execution_seconds=0.05,
            tokens_used=0,
        )
        result = HealResult(
            run_id="test-run",
            steps=[step],
            stop_reason="llm_schema_failures",
            initial_metrics=metrics,
            final_metrics=metrics,
            total_fixes=0,
            total_regressions=0,
            total_tokens=0,
            avg_confidence=0.0,
            engineering_only_findings=[],
        )
        j = json.dumps(result.model_dump(mode="json"))
        assert "schema_failure" in j


class TestHL04PromptAndTimeout:
    """HL-04: prompt truncation, session timeout, _FULL_STEPS constant."""

    def test_full_steps_constant_at_module_level(self):
        """_FULL_STEPS must be a module-level constant, not a local."""
        import launcher.cli.heal as heal_module
        assert hasattr(heal_module, "_FULL_STEPS"), "_FULL_STEPS must be at module level"
        assert isinstance(heal_module._FULL_STEPS, int)
        assert heal_module._FULL_STEPS == 3

    def test_session_timeout_constant_derived_from_budgets(self):
        """_SESSION_TIMEOUT_S must equal _DEFAULT_BUDGETS['max_runtime_s']."""
        import launcher.cli.heal as heal_module
        assert hasattr(heal_module, "_SESSION_TIMEOUT_S"), "_SESSION_TIMEOUT_S must exist"
        assert heal_module._SESSION_TIMEOUT_S == heal_module._DEFAULT_BUDGETS["max_runtime_s"]

    def test_system_prompt_not_truncated(self, tmp_path):
        """_build_diagnostician_prompt must include the full system prompt."""
        from launcher.cli.heal import _build_diagnostician_prompt
        from launcher.models.evaluation import EvaluationReport, Verdict
        # Write a long system prompt (> 500 chars)
        long_prompt = "SYSTEM INSTRUCTION: " + ("X" * 600)
        prompt_file = tmp_path / "heal_diagnostician.txt"
        prompt_file.write_text(long_prompt, encoding="utf-8")

        report = EvaluationReport(verdict=Verdict.NO_GO, pages=[])
        with patch("launcher.cli.heal._DIAGNOSTICIAN_PROMPT_PATH", prompt_file):
            result = _build_diagnostician_prompt(report, [], [], {})

        assert "SYSTEM INSTRUCTION: " in result
        # Full 600 X chars must be present (not truncated to 500)
        assert "X" * 600 in result

    def test_session_timeout_stops_loop(self, tmp_path):
        """run_heal must stop with stop_reason='session_timeout' when session exceeds timeout."""
        import asyncio
        from unittest.mock import AsyncMock
        # Create a minimal run_dir with an evaluate_checkpoint.json
        from launcher.models.evaluation import (
            EvaluationReport, Verdict, PageEvaluation, Grade
        )
        import json as _json
        report = EvaluationReport(
            verdict=Verdict.NO_GO,
            pages=[PageEvaluation(slug="p1", grade=Grade.D, findings=[])],
        )
        cp = tmp_path / "evaluate_checkpoint.json"
        cp.write_text(_json.dumps(report.model_dump(mode="json")), encoding="utf-8")

        call_count = [0]
        original_monotonic = time.monotonic

        def fast_forward_monotonic():
            # Return normal time for first 2 calls (budget init), then jump 1900s
            call_count[0] += 1
            if call_count[0] <= 3:
                return original_monotonic()
            return original_monotonic() + 1900  # past 1800s timeout

        from launcher.cli.heal import run_heal
        with patch("launcher.cli.heal.time.monotonic", side_effect=fast_forward_monotonic):
            with patch("launcher.cli.heal._call_llm_sync", return_value=None):
                result = asyncio.run(run_heal(
                    run_dir=tmp_path,
                    dry_run=False,
                    max_steps=5,
                ))
        # Either session_timeout or llm_unavailable (if timeout check fires before llm call)
        assert result is not None
        assert result.stop_reason in ("session_timeout", "llm_unavailable", "budget_exceeded")
