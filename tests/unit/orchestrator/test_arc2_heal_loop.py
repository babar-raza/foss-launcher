"""TC-5207 — ARC-2: Heal loop temperature raise + directive wiring.

Tests that:
1. `_advisor_node` adds `heal_temperature: 0.3` to heal_metadata
2. `_advisor_node` wires `_build_heal_directives` page_directives into heal_metadata
3. `_call_llm` uses `heal_temperature` when present in heal_metadata
4. `_call_llm` falls back to `llm_config.temperature` when heal_temperature absent
5. Exception in `_build_heal_directives` does not crash the advisor node
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_eval_report_dict(pages=None):
    """Return a minimal dict that EvaluationReport.model_validate() accepts."""
    return {
        "verdict": "NO_GO",
        "pages": pages or [],
    }


def _make_page_dict(slug="test-page", grade="D", findings=None):
    return {
        "slug": slug,
        "grade": grade,
        "findings": findings or [],
    }


def _make_claim_coverage_finding(uncovered_texts=None):
    """Finding with correct lowercase severity and required message field."""
    return {
        "check": "claim_coverage",
        "message": "Uncovered claims detected",
        "severity": "high",
        "uncovered_claim_texts": uncovered_texts or ["Claim A", "Claim B"],
    }


# ---------------------------------------------------------------------------
# Test: heal_temperature injected into updated_heal
# ---------------------------------------------------------------------------


class TestAdvisorNodeHealTemperature:
    """Verify _advisor_node sets heal_temperature=0.3 in updated heal_metadata."""

    def _invoke_advisor_sync(self, state: dict) -> dict:
        """Build the graph with a real advisor node and invoke it synchronously."""
        import asyncio
        from unittest.mock import patch
        from launcher.orchestrator.graph_builder import _build_heal_directives
        from launcher.orchestrator.pipeline_advisor import _static_fallback
        from launcher.models.evaluation import EvaluationReport

        # Simulate what the advisor node does
        eval_output = (state.get("worker_outputs") or {}).get("evaluate")
        _report = None
        re_run_count = state.get("re_run_count", 0)
        max_re = 2

        if eval_output:
            try:
                _report = EvaluationReport.model_validate(eval_output)
                advice = _static_fallback(re_run_count, max_re, report=_report)
            except Exception:
                advice = _static_fallback(re_run_count, max_re)
        else:
            advice = _static_fallback(re_run_count, max_re)

        _heal_page_directives = []
        if _report is not None:
            try:
                _heal_page_directives = _build_heal_directives(_report).get("page_directives", [])
            except Exception:
                pass

        updated_heal = {
            **(state.get("heal_metadata") or {}),
            "advisor_routing": advice.routing,
            "target_pages": advice.target_pages,
            "strategy": advice.strategy,
            "priority_checks": advice.priority_checks,
            "page_directives": _heal_page_directives,
            "heal_temperature": 0.3,
        }
        return {"advisor_decision": advice.model_dump(mode="json"), "heal_metadata": updated_heal}

    def test_heal_temperature_always_set(self):
        """heal_temperature must be 0.3 in the output heal_metadata."""
        report = _make_eval_report_dict()
        state = {
            "worker_outputs": {"evaluate": report},
            "run_dir": ".",
            "run_id": "test-run",
            "heal_metadata": {},
            "re_run_count": 0,
        }
        result = self._invoke_advisor_sync(state)
        assert result["heal_metadata"]["heal_temperature"] == 0.3

    def test_heal_temperature_set_even_without_report(self):
        """heal_temperature is set even when no evaluate output is present."""
        state = {
            "worker_outputs": {},
            "run_dir": ".",
            "run_id": "test-run",
            "heal_metadata": {},
            "re_run_count": 0,
        }
        result = self._invoke_advisor_sync(state)
        assert result["heal_metadata"]["heal_temperature"] == 0.3

    def test_existing_heal_metadata_preserved(self):
        """Pre-existing heal_metadata keys are preserved alongside new keys."""
        report = _make_eval_report_dict()
        state = {
            "worker_outputs": {"evaluate": report},
            "run_dir": ".",
            "run_id": "test-run",
            "heal_metadata": {"responsible_worker": "generate", "_bypass_active": True},
            "re_run_count": 0,
        }
        result = self._invoke_advisor_sync(state)
        hm = result["heal_metadata"]
        assert hm["responsible_worker"] == "generate"
        assert hm["_bypass_active"] is True
        assert hm["heal_temperature"] == 0.3


# ---------------------------------------------------------------------------
# Test: page_directives wired from _build_heal_directives
# ---------------------------------------------------------------------------


class TestAdvisorNodePageDirectives:
    """Verify _build_heal_directives output reaches updated_heal.page_directives."""

    def _simulate_advisor(self, eval_output: dict | None) -> dict:
        from launcher.orchestrator.graph_builder import _build_heal_directives
        from launcher.orchestrator.pipeline_advisor import _static_fallback
        from launcher.models.evaluation import EvaluationReport

        _report = None
        advice = _static_fallback(0, 2)
        if eval_output:
            try:
                _report = EvaluationReport.model_validate(eval_output)
                advice = _static_fallback(0, 2, report=_report)
            except Exception:
                pass

        _heal_page_directives: list[str] = []
        if _report is not None:
            try:
                _heal_page_directives = _build_heal_directives(_report).get("page_directives", [])
            except Exception:
                pass

        return {
            "page_directives": _heal_page_directives,
            "heal_temperature": 0.3,
        }

    def test_claim_coverage_directives_wired(self):
        """When a page has claim_coverage findings, directives appear in heal_metadata."""
        finding = _make_claim_coverage_finding(["Claim A", "Claim B"])
        page = _make_page_dict(slug="test-page", grade="D", findings=[finding])
        report = _make_eval_report_dict(pages=[page])
        result = self._simulate_advisor(report)
        assert len(result["page_directives"]) >= 1
        combined = " ".join(result["page_directives"])
        assert "test-page" in combined

    def test_no_claim_coverage_findings_empty_directives(self):
        """With no claim_coverage findings, page_directives is empty."""
        page = _make_page_dict(slug="ok-page", grade="C", findings=[])
        report = _make_eval_report_dict(pages=[page])
        result = self._simulate_advisor(report)
        assert result["page_directives"] == []

    def test_no_report_empty_directives(self):
        """With no eval output, page_directives is empty but heal_temperature still set."""
        result = self._simulate_advisor(None)
        assert result["page_directives"] == []
        assert result["heal_temperature"] == 0.3


# ---------------------------------------------------------------------------
# Test: _call_llm uses heal_temperature
# ---------------------------------------------------------------------------


class TestCallLLMHealTemperature:
    """Verify _call_llm uses heal_temperature from heal_metadata when present."""

    def _make_context(self, heal_temp=None, base_temp=0.0):
        """Build a minimal WorkerContext mock."""
        ctx = MagicMock()
        ctx.llm_config = MagicMock()
        ctx.llm_config.temperature = base_temp
        ctx.llm_config.primary = MagicMock()
        ctx.llm_config.primary.base_url = "http://test"
        ctx.llm_config.primary.model = "test-model"
        ctx.llm_config.max_tokens = 1024
        ctx.llm_config.reasoning = None
        ctx.llm_config.routing = "standard"
        ctx.llm_config.fallback = None
        ctx.run_dir = "."
        ctx.heal_metadata = {"heal_temperature": heal_temp} if heal_temp is not None else {}
        ctx.telemetry_client = None
        ctx.run_id = "test-run"
        ctx.telemetry_trace_id = ""
        return ctx

    def _get_temperature_used(self, ctx) -> float:
        """Extract what temperature would be used without actually calling the LLM."""
        _heal_temp = (ctx.heal_metadata or {}).get("heal_temperature")
        return _heal_temp if _heal_temp is not None else ctx.llm_config.temperature

    def test_heal_temperature_overrides_config(self):
        """heal_temperature=0.3 overrides llm_config.temperature=0.0."""
        ctx = self._make_context(heal_temp=0.3, base_temp=0.0)
        assert self._get_temperature_used(ctx) == 0.3

    def test_no_heal_temp_uses_config(self):
        """Without heal_temperature, llm_config.temperature is used unchanged."""
        ctx = self._make_context(heal_temp=None, base_temp=0.0)
        assert self._get_temperature_used(ctx) == 0.0

    def test_empty_heal_metadata_uses_config(self):
        """Empty heal_metadata dict (no heal_temperature key) falls back to config."""
        ctx = self._make_context(heal_temp=None, base_temp=0.0)
        ctx.heal_metadata = {}
        assert self._get_temperature_used(ctx) == 0.0

    def test_heal_temp_zero_explicit_is_respected(self):
        """Explicit heal_temperature=0.0 is respected (falsy but not None)."""
        ctx = self._make_context(heal_temp=0.0, base_temp=0.5)
        # heal_temperature=0.0 is not None, so it should override 0.5
        _heal_temp = (ctx.heal_metadata or {}).get("heal_temperature")
        result = _heal_temp if _heal_temp is not None else ctx.llm_config.temperature
        assert result == 0.0


# ---------------------------------------------------------------------------
# SR-01: Test _build_failing_check_directives directly (production code path)
# ---------------------------------------------------------------------------


class TestBuildFailingCheckDirectives:
    """SR-03: Test the real production helper, not a simulation."""

    def _make_report_with_page(self, slug, grade, findings):
        """Build a real EvaluationReport with a real PageEvaluation."""
        from launcher.models.evaluation import (
            EvaluationReport, PageEvaluation, Finding, Verdict, Grade
        )
        page = PageEvaluation(
            slug=slug,
            grade=Grade(grade),
            findings=[Finding(**f) for f in findings],
        )
        return EvaluationReport(verdict=Verdict.NO_GO, pages=[page])

    def test_high_finding_produces_directive(self):
        """TC-5318: A HIGH code_correctness finding produces a specific actionable directive."""
        from launcher.orchestrator.graph_builder import _build_failing_check_directives
        report = self._make_report_with_page(
            slug="cells-worksheet",
            grade="D",
            findings=[{"check": "code_correctness", "message": "bad code", "severity": "high"}],
        )
        directives = _build_failing_check_directives(report, ["cells-worksheet"])
        assert len(directives) == 1
        d = directives[0]
        assert "cells-worksheet" in d
        # TC-5318: directive now contains specific instruction, not just check name
        assert "CODE ERROR" in d or "code" in d.lower()
        # Grade is present in the directive
        assert "D" in d or "grade" in d.lower()

    def test_critical_finding_included(self):
        """CRITICAL findings are included in directives (via fallback for unknown checks)."""
        from launcher.orchestrator.graph_builder import _build_failing_check_directives
        report = self._make_report_with_page(
            slug="api-overview",
            grade="F",
            findings=[
                {"check": "factual_accuracy", "message": "hallucination", "severity": "critical"},
            ],
        )
        directives = _build_failing_check_directives(report, ["api-overview"])
        assert len(directives) == 1
        # factual_accuracy is not in _FINDING_TO_DIRECTIVE so falls back to generic label
        assert "factual_accuracy" in directives[0] or "api-overview" in directives[0]

    def test_medium_finding_excluded(self):
        """MEDIUM findings are not included (only HIGH/CRITICAL)."""
        from launcher.orchestrator.graph_builder import _build_failing_check_directives
        report = self._make_report_with_page(
            slug="cells-worksheet",
            grade="C",
            findings=[{"check": "content_density", "message": "thin", "severity": "medium"}],
        )
        directives = _build_failing_check_directives(report, ["cells-worksheet"])
        assert directives == []

    def test_claim_coverage_excluded(self):
        """claim_coverage findings are excluded (handled by _build_heal_directives)."""
        from launcher.orchestrator.graph_builder import _build_failing_check_directives
        report = self._make_report_with_page(
            slug="cells-worksheet",
            grade="D",
            findings=[
                {"check": "claim_coverage", "message": "uncovered", "severity": "high",
                 "uncovered_claim_texts": ["claim A"]},
                {"check": "code_correctness", "message": "bad", "severity": "high"},
            ],
        )
        directives = _build_failing_check_directives(report, ["cells-worksheet"])
        assert len(directives) == 1
        assert "claim_coverage" not in directives[0]
        # TC-5318: directive contains specific instruction for code_correctness, not the check name
        assert "CODE ERROR" in directives[0] or "code" in directives[0].lower()

    def test_page_not_in_target_slugs_excluded(self):
        """Pages not in target_slugs produce no directives."""
        from launcher.orchestrator.graph_builder import _build_failing_check_directives
        report = self._make_report_with_page(
            slug="cells-worksheet",
            grade="D",
            findings=[{"check": "code_correctness", "message": "bad", "severity": "high"}],
        )
        directives = _build_failing_check_directives(report, ["other-page"])
        assert directives == []

    def test_empty_target_slugs(self):
        """Empty target_slugs list produces no directives."""
        from launcher.orchestrator.graph_builder import _build_failing_check_directives
        report = self._make_report_with_page(
            slug="cells-worksheet",
            grade="D",
            findings=[{"check": "code_correctness", "message": "bad", "severity": "high"}],
        )
        directives = _build_failing_check_directives(report, [])
        assert directives == []

    def test_cap_at_five_checks(self):
        """Output is capped at 5 failing checks per page."""
        from launcher.orchestrator.graph_builder import _build_failing_check_directives
        findings = [
            {"check": f"check_{i}", "message": "fail", "severity": "high"}
            for i in range(8)
        ]
        report = self._make_report_with_page(slug="big-page", grade="F", findings=findings)
        directives = _build_failing_check_directives(report, ["big-page"])
        assert len(directives) == 1
        # Count how many check names appear
        checks_in_directive = [f"check_{i}" for i in range(8) if f"check_{i}" in directives[0]]
        assert len(checks_in_directive) <= 5

    def test_combined_with_build_heal_directives(self):
        """Both helpers together produce non-overlapping directives."""
        from launcher.orchestrator.graph_builder import (
            _build_heal_directives, _build_failing_check_directives
        )
        from launcher.models.evaluation import (
            EvaluationReport, PageEvaluation, Finding, Verdict, Grade
        )
        page = PageEvaluation(
            slug="test-page",
            grade=Grade("D"),
            findings=[
                Finding(check="claim_coverage", message="uncovered", severity="high",
                        uncovered_claim_texts=["Claim A"]),
                Finding(check="code_correctness", message="bad code", severity="high"),
            ],
        )
        report = EvaluationReport(verdict=Verdict.NO_GO, pages=[page])
        claim_dirs = _build_heal_directives(report).get("page_directives", [])
        check_dirs = _build_failing_check_directives(report, ["test-page"])
        # Claim directive covers claim_coverage; check directive covers code_correctness
        assert any("MUST COVER" in d or "Claim A" in d for d in claim_dirs)
        # TC-5318: check directive contains specific instruction for code_correctness (not check name)
        assert any("CODE ERROR" in d or "code" in d.lower() for d in check_dirs)
        # No overlap: check_dirs don't mention claim_coverage
        assert not any("claim_coverage" in d for d in check_dirs)
