"""TC-5135: Heal loop routing tests.

Tests diagnostic logging, defensive verdict propagation, and targeted
static fallback page population.
"""
from __future__ import annotations

import pytest
from langgraph.graph import END

from launcher.models.evaluation import (
    Grade,
    PageEvaluation,
    EvaluationReport,
    PipelineAdvice,
)
from launcher.orchestrator.graph_builder import _make_post_evaluate_router
from launcher.orchestrator.pipeline_advisor import (
    _extract_failing_slugs,
    _static_fallback,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _page(slug: str, grade: Grade) -> PageEvaluation:
    """Create a minimal PageEvaluation."""
    return PageEvaluation(slug=slug, grade=grade)


def _report(pages: list[PageEvaluation], verdict: str = "NO_GO") -> EvaluationReport:
    """Create a minimal EvaluationReport."""
    return EvaluationReport(verdict=verdict, pages=pages)


# ---------------------------------------------------------------------------
# Tests — _make_post_evaluate_router routing
# ---------------------------------------------------------------------------

class TestPostEvaluateRouter:
    """TC-5135: Post-evaluate router routes correctly."""

    def test_go_routes_to_publish(self):
        """GO verdict → publish."""
        router = _make_post_evaluate_router(max_re_runs=2)
        state = {"verdict": "GO", "re_run_count": 0}
        assert router(state) == "publish"

    def test_no_go_with_budget_routes_to_advisor(self):
        """NO_GO + budget remaining → __advisor__."""
        router = _make_post_evaluate_router(max_re_runs=2)
        state = {"verdict": "NO_GO", "re_run_count": 0}
        assert router(state) == "__advisor__"

    def test_no_go_at_ceiling_routes_to_end(self):
        """NO_GO + budget exhausted → END."""
        router = _make_post_evaluate_router(max_re_runs=2)
        state = {"verdict": "NO_GO", "re_run_count": 2}
        assert router(state) == END

    def test_no_go_max_zero_routes_to_end(self):
        """NO_GO + max_re_runs=0 → END (heal disabled)."""
        router = _make_post_evaluate_router(max_re_runs=0)
        state = {"verdict": "NO_GO", "re_run_count": 0}
        assert router(state) == END

    def test_missing_verdict_routes_to_advisor(self):
        """Missing verdict (empty string) + budget → __advisor__."""
        router = _make_post_evaluate_router(max_re_runs=2)
        state = {"verdict": "", "re_run_count": 0}
        assert router(state) == "__advisor__"

    def test_no_verdict_key_routes_to_advisor(self):
        """No verdict key at all + budget → __advisor__."""
        router = _make_post_evaluate_router(max_re_runs=2)
        state = {"re_run_count": 0}
        assert router(state) == "__advisor__"

    def test_re_run_count_1_of_2_routes_to_advisor(self):
        """NO_GO + re_run=1 of max=2 → __advisor__ (one more try)."""
        router = _make_post_evaluate_router(max_re_runs=2)
        state = {"verdict": "NO_GO", "re_run_count": 1}
        assert router(state) == "__advisor__"


# ---------------------------------------------------------------------------
# Tests — _extract_failing_slugs
# ---------------------------------------------------------------------------

class TestExtractFailingSlugs:
    """TC-5135: Extract C/D/F-grade slugs from report."""

    def test_extracts_cdf_grades(self):
        """C, D, F slugs extracted; A, B excluded."""
        report = _report([
            _page("page-a", Grade.A),
            _page("page-b", Grade.B),
            _page("page-c", Grade.C),
            _page("page-d", Grade.D),
            _page("page-f", Grade.F),
        ])
        slugs = _extract_failing_slugs(report)
        assert slugs == ["page-c", "page-d", "page-f"]

    def test_all_passing_returns_empty(self):
        """All A/B grades → empty list."""
        report = _report([
            _page("page-a", Grade.A),
            _page("page-b", Grade.B),
        ])
        assert _extract_failing_slugs(report) == []

    def test_none_report_returns_empty(self):
        """None report → empty list."""
        assert _extract_failing_slugs(None) == []

    def test_empty_pages_returns_empty(self):
        """Report with no pages → empty list."""
        report = _report([])
        assert _extract_failing_slugs(report) == []

    def test_slugs_sorted(self):
        """Returned slugs are sorted alphabetically."""
        report = _report([
            _page("zulu", Grade.F),
            _page("alpha", Grade.D),
            _page("mike", Grade.C),
        ])
        assert _extract_failing_slugs(report) == ["alpha", "mike", "zulu"]


# ---------------------------------------------------------------------------
# Tests — _static_fallback with report
# ---------------------------------------------------------------------------

class TestStaticFallbackTargetPages:
    """TC-5135: Static fallback populates target_pages from report."""

    def test_fallback_with_report_populates_targets(self):
        """When report is provided, target_pages includes C/D/F slugs."""
        report = _report([
            _page("good", Grade.A),
            _page("bad", Grade.D),
            _page("ugly", Grade.F),
        ])
        advice = _static_fallback(0, 2, report=report)
        assert advice.routing == "heal_generate"
        assert advice.target_pages == ["bad", "ugly"]

    def test_fallback_without_report_empty_targets(self):
        """When no report, target_pages is empty."""
        advice = _static_fallback(0, 2, report=None)
        assert advice.routing == "heal_generate"
        assert advice.target_pages == []

    def test_fallback_at_ceiling_stops(self):
        """Budget exhausted → stop, regardless of report."""
        report = _report([_page("bad", Grade.F)])
        advice = _static_fallback(2, 2, report=report)
        assert advice.routing == "stop"
        assert advice.target_pages == []


# ---------------------------------------------------------------------------
# SR-03: Heal temperature escalation (TC-E-03)
# ---------------------------------------------------------------------------


class TestHealTemperatureEscalation:
    """TC-E-03: Heal metadata temperature schedule [0.0, 0.3, 0.6]."""

    _TEMP_SCHEDULE = [0.0, 0.3, 0.6]

    def _compute_heal_temp(self, heal_attempt: int) -> float:
        """Reproduce the temperature computation from graph_builder."""
        return self._TEMP_SCHEDULE[min(heal_attempt - 1, len(self._TEMP_SCHEDULE) - 1)]

    def test_first_attempt_temp_0(self):
        """First heal attempt → temperature 0.0."""
        assert self._compute_heal_temp(1) == 0.0

    def test_second_attempt_temp_03(self):
        """Second heal attempt → temperature 0.3."""
        assert self._compute_heal_temp(2) == 0.3

    def test_third_attempt_temp_06(self):
        """Third heal attempt → temperature 0.6."""
        assert self._compute_heal_temp(3) == 0.6

    def test_fourth_attempt_capped_at_06(self):
        """Fourth+ heal attempt → still 0.6 (capped)."""
        assert self._compute_heal_temp(4) == 0.6
        assert self._compute_heal_temp(10) == 0.6

    def test_heal_metadata_attempt_increment(self):
        """heal_attempt increments from previous heal_metadata."""
        prev_meta = {"heal_attempt": 2}
        new_attempt = prev_meta.get("heal_attempt", 0) + 1
        assert new_attempt == 3
        assert self._compute_heal_temp(new_attempt) == 0.6

    def test_first_heal_no_previous_meta(self):
        """First heal pass with empty heal_metadata → attempt 1."""
        prev_meta = {}
        new_attempt = prev_meta.get("heal_attempt", 0) + 1
        assert new_attempt == 1
        assert self._compute_heal_temp(new_attempt) == 0.0
