"""Tests for TC-2500 conformance gates in go_criteria.py."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from launcher.models.evaluation import (
    EvaluationReport,
    Finding,
    GoCriteria,
    Grade,
    PageEvaluation,
    QualitySummary,
    Verdict,
)
from launcher.workers.evaluate.go_criteria import evaluate_go_criteria


def _make_report(
    pages: list[PageEvaluation] | None = None,
) -> EvaluationReport:
    """Build a minimal EvaluationReport with given pages."""
    if pages is None:
        pages = []
    return EvaluationReport(
        verdict=Verdict.NO_GO,
        pages=pages,
        quality=QualitySummary(
            pages_by_grade={},
            avg_word_count=0.0,
            claim_coverage=1.0,
        ),
    )


def _make_page(
    slug: str = "test",
    grade: Grade = Grade.A,
    conformance_score: float | None = None,
    findings: list[Finding] | None = None,
) -> PageEvaluation:
    return PageEvaluation(
        slug=slug,
        content_path=f"/tmp/{slug}.md",
        grade=grade,
        findings=findings or [],
        check_results={},
        numeric_score=80.0,
        conformance_score=conformance_score,
    )


class TestConformanceGatesAutoPass:
    """When no pages have conformance scores, gates should auto-pass."""

    def test_no_conformance_scores_no_gate(self):
        pages = [_make_page("p1", Grade.A), _make_page("p2", Grade.B)]
        report = _make_report(pages)
        verdict, criteria = evaluate_go_criteria(report)
        # No conformance criteria should be present
        conf_criteria = [c for c in criteria if "conformance" in c.criterion.lower()]
        assert conf_criteria == []

    def test_none_conformance_scores_no_gate(self):
        pages = [_make_page("p1", Grade.A, conformance_score=None)]
        report = _make_report(pages)
        verdict, criteria = evaluate_go_criteria(report)
        conf_criteria = [c for c in criteria if "conformance" in c.criterion.lower()]
        assert conf_criteria == []


class TestMedianConformanceGate:
    """Median conformance score >= 0.50 gate."""

    def test_high_median_passes(self):
        pages = [
            _make_page("p1", Grade.A, conformance_score=0.80),
            _make_page("p2", Grade.A, conformance_score=0.70),
            _make_page("p3", Grade.B, conformance_score=0.60),
        ]
        report = _make_report(pages)
        _, criteria = evaluate_go_criteria(report)
        mc = [c for c in criteria if c.criterion == "Median conformance score"]
        assert len(mc) == 1
        assert mc[0].passed is True

    def test_low_median_fails(self):
        pages = [
            _make_page("p1", Grade.A, conformance_score=0.40),
            _make_page("p2", Grade.B, conformance_score=0.30),
            _make_page("p3", Grade.B, conformance_score=0.45),
        ]
        report = _make_report(pages)
        _, criteria = evaluate_go_criteria(report)
        mc = [c for c in criteria if c.criterion == "Median conformance score"]
        assert len(mc) == 1
        assert mc[0].passed is False

    def test_exact_threshold_passes(self):
        pages = [_make_page("p1", Grade.A, conformance_score=0.50)]
        report = _make_report(pages)
        _, criteria = evaluate_go_criteria(report)
        mc = [c for c in criteria if c.criterion == "Median conformance score"]
        assert len(mc) == 1
        assert mc[0].passed is True


class TestLowConformanceRateGate:
    """Low-conformance page rate <= 15% gate."""

    def test_no_low_conformance_passes(self):
        pages = [
            _make_page("p1", Grade.A, conformance_score=0.80),
            _make_page("p2", Grade.A, conformance_score=0.70),
        ]
        report = _make_report(pages)
        _, criteria = evaluate_go_criteria(report)
        lc = [c for c in criteria if c.criterion == "Low-conformance page rate"]
        assert len(lc) == 1
        assert lc[0].passed is True

    def test_high_low_conformance_fails(self):
        # 3 out of 5 pages below 0.35 → 60% > 15%
        pages = [
            _make_page("p1", Grade.A, conformance_score=0.10),
            _make_page("p2", Grade.D, conformance_score=0.20),
            _make_page("p3", Grade.D, conformance_score=0.30),
            _make_page("p4", Grade.B, conformance_score=0.80),
            _make_page("p5", Grade.B, conformance_score=0.70),
        ]
        report = _make_report(pages)
        _, criteria = evaluate_go_criteria(report)
        lc = [c for c in criteria if c.criterion == "Low-conformance page rate"]
        assert len(lc) == 1
        assert lc[0].passed is False


class TestConformanceRegressionGate:
    """Conformance regression gate: median must not drop > 10pp vs baseline."""

    def test_regression_within_threshold_passes(self, tmp_path: Path):
        baseline = {"ab_rate": 0.60, "df_rate": 0.20, "median_conformance": 0.70}
        baseline_path = tmp_path / "baseline.json"
        baseline_path.write_text(json.dumps(baseline), encoding="utf-8")

        pages = [
            _make_page("p1", Grade.A, conformance_score=0.65),
            _make_page("p2", Grade.A, conformance_score=0.60),
        ]
        report = _make_report(pages)
        _, criteria = evaluate_go_criteria(report, baseline_path=baseline_path)
        cg = [c for c in criteria if c.criterion == "Conformance regression gate"]
        assert len(cg) == 1
        # median = 0.625, baseline = 0.70 → delta = -7.5pp (within -10pp)
        assert cg[0].passed is True

    def test_regression_beyond_threshold_fails(self, tmp_path: Path):
        baseline = {"ab_rate": 0.60, "df_rate": 0.20, "median_conformance": 0.80}
        baseline_path = tmp_path / "baseline.json"
        baseline_path.write_text(json.dumps(baseline), encoding="utf-8")

        pages = [
            _make_page("p1", Grade.A, conformance_score=0.50),
            _make_page("p2", Grade.A, conformance_score=0.55),
        ]
        report = _make_report(pages)
        _, criteria = evaluate_go_criteria(report, baseline_path=baseline_path)
        cg = [c for c in criteria if c.criterion == "Conformance regression gate"]
        assert len(cg) == 1
        # median = 0.525, baseline = 0.80 → delta = -27.5pp (beyond -10pp)
        assert cg[0].passed is False
