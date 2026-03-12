"""Tests for HealDecision, HealStep, HealResult models (TC-3852b / H4.2)."""
from __future__ import annotations

import json

import pytest

from launcher.models.evaluation import (
    Grade,
    HealAction,
    HealDecision,
    HealResult,
    HealStep,
    ReportMetrics,
    Verdict,
)


def _make_metrics(ab: float = 0.5, df: float = 0.3) -> ReportMetrics:
    return ReportMetrics(
        critical_count=1,
        high_count=2,
        grades={"A": 5, "D": 3},
        ab_rate=ab,
        df_rate=df,
        total_findings=10,
    )


def _make_action(**kwargs) -> HealAction:
    defaults = {
        "worker": "generate",
        "target_pages": ["page-1"],
        "strategy": "Improve content density",
        "priority_checks": ["density"],
    }
    defaults.update(kwargs)
    return HealAction(**defaults)


def _make_decision(**kwargs) -> HealDecision:
    defaults = {
        "analysis": "Pages lack sufficient detail.",
        "root_causes": ["thin_content"],
        "action": _make_action(),
        "confidence": 0.8,
        "stop_recommendation": False,
    }
    defaults.update(kwargs)
    return HealDecision(**defaults)


class TestHealDecisionValidation:
    def test_valid_decision_parses(self) -> None:
        d = _make_decision()
        assert d.confidence == 0.8
        assert d.action.worker == "generate"
        assert d.stop_recommendation is False

    def test_confidence_range_accepted(self) -> None:
        for conf in (0.0, 0.5, 1.0):
            d = _make_decision(confidence=conf)
            assert d.confidence == conf

    def test_stop_reason_optional(self) -> None:
        d = _make_decision(stop_recommendation=True, stop_reason="converged")
        assert d.stop_reason == "converged"
        d2 = _make_decision()
        assert d2.stop_reason is None

    def test_serialization_roundtrip(self) -> None:
        d = _make_decision()
        data = d.model_dump(mode="json")
        d2 = HealDecision.model_validate(data)
        assert d2.confidence == d.confidence
        assert d2.action.worker == d.action.worker

    def test_json_string_roundtrip(self) -> None:
        d = _make_decision()
        json_str = json.dumps(d.model_dump(mode="json"))
        data = json.loads(json_str)
        d2 = HealDecision.model_validate(data)
        assert d2.analysis == d.analysis


class TestReportMetrics:
    def test_metrics_fields(self) -> None:
        m = _make_metrics()
        assert m.ab_rate == 0.5
        assert m.df_rate == 0.3
        assert m.critical_count == 1
        assert "A" in m.grades

    def test_zero_rates(self) -> None:
        m = _make_metrics(ab=0.0, df=0.0)
        assert m.ab_rate == 0.0
        assert m.df_rate == 0.0

    def test_serialization(self) -> None:
        m = _make_metrics()
        data = m.model_dump(mode="json")
        m2 = ReportMetrics.model_validate(data)
        assert m2.df_rate == m.df_rate


class TestHealResult:
    def test_heal_result_minimal(self) -> None:
        m = _make_metrics()
        r = HealResult(
            run_id="run-001",
            steps=[],
            stop_reason="dry_run",
            initial_metrics=m,
            final_metrics=m,
            total_fixes=0,
            total_regressions=0,
            total_tokens=0,
            avg_confidence=0.0,
            engineering_only_findings=[],
        )
        assert r.run_id == "run-001"
        assert r.total_fixes == 0
        assert r.stop_reason == "dry_run"

    def test_heal_result_serialization(self) -> None:
        m = _make_metrics()
        r = HealResult(
            run_id="run-002",
            steps=[],
            stop_reason="max_steps",
            initial_metrics=m,
            final_metrics=m,
            total_fixes=2,
            total_regressions=0,
            total_tokens=1500,
            avg_confidence=0.75,
            engineering_only_findings=[],
        )
        data = r.model_dump(mode="json")
        r2 = HealResult.model_validate(data)
        assert r2.total_tokens == 1500
        assert r2.avg_confidence == 0.75
