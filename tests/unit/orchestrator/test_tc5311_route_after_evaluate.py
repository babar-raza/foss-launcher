"""TC-5311: Tests for route_after_evaluate() deterministic routing function.

Full scope: heal_understand is implemented.
extraction_quality HIGH findings on first re-run → heal_understand.
On subsequent re-runs, falls through to heal_generate or stop.
"""
import logging
import pytest
from unittest.mock import MagicMock

from launcher.models.evaluation import Grade


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_report(pages=None):
    """Create a minimal mock EvaluationReport."""
    report = MagicMock()
    report.pages = pages if pages is not None else []
    return report


def _make_page(slug="test", grade=Grade.C, findings=None):
    """Create a minimal mock PageEvaluation."""
    page = MagicMock()
    page.slug = slug
    page.grade = grade
    page.findings = findings or []
    return page


def _make_finding(check="some_check", severity="medium", location="test"):
    f = MagicMock()
    f.check = check
    f.severity = severity
    f.location = location
    return f


# ---------------------------------------------------------------------------
# TestRouteAfterEvaluate — core deterministic routing rules
# ---------------------------------------------------------------------------

class TestRouteAfterEvaluate:

    def setup_method(self):
        from launcher.orchestrator.pipeline_advisor import route_after_evaluate
        self.route = route_after_evaluate

    # Rule 1: Budget exhausted → stop

    def test_stop_when_rerun_equals_max(self):
        report = _make_report([_make_page()])
        advice = self.route(report, re_run_count=2, max_re_runs=2)
        assert advice.routing == "stop"
        assert "exhausted" in advice.stop_reason.lower()
        assert advice.confidence == 1.0

    def test_stop_when_rerun_exceeds_max(self):
        report = _make_report([_make_page()])
        advice = self.route(report, re_run_count=5, max_re_runs=2)
        assert advice.routing == "stop"

    def test_stop_budget_exhausted_reports_counts(self):
        report = _make_report([_make_page()])
        advice = self.route(report, re_run_count=3, max_re_runs=3)
        assert "3/3" in advice.analysis

    # Rule 2: extraction_quality HIGH on first re-run → heal_understand

    def test_extraction_high_routes_heal_understand(self):
        """TC-5311: extraction_quality HIGH on first re-run must route heal_understand."""
        finding = _make_finding(check="extraction_quality", severity="high")
        page = _make_page(grade=Grade.D, findings=[finding])
        report = _make_report([page])
        advice = self.route(report, re_run_count=0, max_re_runs=2)
        assert advice.routing == "heal_understand", (
            "extraction_quality HIGH on first re-run must route heal_understand"
        )

    def test_extraction_high_emits_info_log(self, caplog):
        """TC-5311: extraction_quality HIGH must emit an INFO log when routing heal_understand."""
        finding = _make_finding(check="extraction_quality", severity="high")
        page = _make_page(grade=Grade.D, findings=[finding])
        report = _make_report([page])
        with caplog.at_level(logging.INFO, logger="launcher.orchestrator.pipeline_advisor"):
            self.route(report, re_run_count=0, max_re_runs=2)
        assert any(
            "TC-5311" in r.message and "extraction_quality" in r.message
            for r in caplog.records
        ), "Expected TC-5311 extraction_quality INFO log"

    def test_extraction_high_multiple_findings_routes_heal_understand(self):
        """Multiple HIGH extraction_quality findings still → heal_understand on first run."""
        findings = [_make_finding(check="extraction_quality", severity="high") for _ in range(4)]
        page = _make_page(grade=Grade.F, findings=findings)
        report = _make_report([page])
        advice = self.route(report, re_run_count=0, max_re_runs=2)
        assert advice.routing == "heal_understand"

    def test_extraction_high_second_rerun_routes_heal_generate(self):
        """On second re-run (re_run_count=1), extraction HIGH falls through to heal_generate."""
        finding = _make_finding(check="extraction_quality", severity="high")
        page = _make_page(grade=Grade.D, findings=[finding])
        report = _make_report([page])
        advice = self.route(report, re_run_count=1, max_re_runs=2)
        assert advice.routing == "heal_generate", (
            "On second re-run, extraction HIGH should fall through to heal_generate, not loop"
        )

    def test_extraction_medium_does_not_route_heal_understand(self):
        """Only HIGH extraction_quality triggers heal_understand; medium falls through."""
        finding = _make_finding(check="extraction_quality", severity="medium")
        page = _make_page(grade=Grade.D, findings=[finding])
        report = _make_report([page])
        advice = self.route(report, re_run_count=0, max_re_runs=2)
        assert advice.routing == "heal_generate", (
            "Medium extraction_quality must NOT trigger heal_understand"
        )

    def test_heal_understand_analysis_mentions_extraction(self):
        """heal_understand advice must describe the extraction quality issue."""
        finding = _make_finding(check="extraction_quality", severity="high")
        page = _make_page(grade=Grade.D, findings=[finding])
        report = _make_report([page])
        advice = self.route(report, re_run_count=0, max_re_runs=2)
        assert advice.routing == "heal_understand"
        assert "extraction_quality" in advice.analysis or "extraction" in advice.analysis.lower()

    # Rule 3: CRITICAL finding rate > 50% → stop

    def test_stop_when_critical_rate_exceeds_50_percent(self):
        critical_finding = _make_finding(check="safety", severity="critical")
        pages = [
            _make_page(slug=f"page{i}", grade=Grade.F, findings=[critical_finding])
            for i in range(6)
        ] + [_make_page(slug="ok", grade=Grade.B)]  # 6/7 = 85.7%
        report = _make_report(pages)
        advice = self.route(report, re_run_count=0, max_re_runs=2)
        assert advice.routing == "stop"
        assert "CRITICAL" in advice.stop_reason

    def test_stop_when_critical_rate_exactly_at_threshold(self):
        """Exactly 50% should NOT stop (rule is > 50%, not >= 50%)."""
        critical_finding = _make_finding(check="safety", severity="critical")
        pages = [
            _make_page(slug="bad", grade=Grade.F, findings=[critical_finding]),
            _make_page(slug="ok", grade=Grade.B),
        ]  # 1/2 = 50% — not > 50%
        report = _make_report(pages)
        advice = self.route(report, re_run_count=0, max_re_runs=2)
        assert advice.routing == "heal_generate"

    def test_heal_generate_when_critical_rate_below_50_percent(self):
        critical_finding = _make_finding(check="safety", severity="critical")
        pages = [
            _make_page(slug="bad", grade=Grade.F, findings=[critical_finding]),
            _make_page(slug="ok1", grade=Grade.B),
            _make_page(slug="ok2", grade=Grade.B),
        ]  # 1/3 = 33%
        report = _make_report(pages)
        advice = self.route(report, re_run_count=0, max_re_runs=2)
        assert advice.routing == "heal_generate"

    def test_stop_critical_analysis_includes_page_counts(self):
        critical_finding = _make_finding(check="safety", severity="critical")
        pages = [
            _make_page(slug=f"bad{i}", grade=Grade.F, findings=[critical_finding])
            for i in range(4)
        ] + [_make_page(slug="ok", grade=Grade.B)]  # 4/5 = 80%
        report = _make_report(pages)
        advice = self.route(report, re_run_count=0, max_re_runs=2)
        assert advice.routing == "stop"
        assert "4" in advice.analysis and "5" in advice.analysis

    # Rule 4: Default → heal_generate

    def test_heal_generate_basic(self):
        report = _make_report([_make_page(grade=Grade.C)])
        advice = self.route(report, re_run_count=0, max_re_runs=2)
        assert advice.routing == "heal_generate"

    def test_heal_generate_with_budget_remaining(self):
        report = _make_report([_make_page(grade=Grade.D)])
        advice = self.route(report, re_run_count=1, max_re_runs=2)
        assert advice.routing == "heal_generate"

    def test_failing_pages_in_target_pages(self):
        pages = [
            _make_page(slug="bad_page", grade=Grade.D),
            _make_page(slug="good_page", grade=Grade.A),
        ]
        report = _make_report(pages)
        advice = self.route(report, re_run_count=0, max_re_runs=2)
        assert advice.routing == "heal_generate"
        assert "bad_page" in advice.target_pages
        assert "good_page" not in advice.target_pages

    def test_b_grade_pages_excluded_from_target_pages(self):
        pages = [
            _make_page(slug="c_page", grade=Grade.C),
            _make_page(slug="b_page", grade=Grade.B),
            _make_page(slug="f_page", grade=Grade.F),
        ]
        report = _make_report(pages)
        advice = self.route(report, re_run_count=0, max_re_runs=2)
        assert sorted(advice.target_pages) == ["c_page", "f_page"]

    def test_target_pages_sorted(self):
        pages = [
            _make_page(slug="zzz", grade=Grade.C),
            _make_page(slug="aaa", grade=Grade.D),
            _make_page(slug="mmm", grade=Grade.F),
        ]
        report = _make_report(pages)
        advice = self.route(report, re_run_count=0, max_re_runs=2)
        assert advice.target_pages == sorted(advice.target_pages)

    def test_empty_pages_returns_heal_generate(self):
        report = _make_report([])
        advice = self.route(report, re_run_count=0, max_re_runs=2)
        assert advice.routing == "heal_generate"
        assert advice.target_pages == []

    def test_all_a_grade_pages_empty_target(self):
        pages = [
            _make_page(slug=f"page{i}", grade=Grade.A)
            for i in range(5)
        ]
        report = _make_report(pages)
        advice = self.route(report, re_run_count=0, max_re_runs=2)
        assert advice.routing == "heal_generate"
        assert advice.target_pages == []

    # Confidence is always 1.0 for deterministic decisions

    def test_confidence_is_1_for_stop(self):
        report = _make_report([_make_page()])
        advice = self.route(report, re_run_count=2, max_re_runs=2)
        assert advice.confidence == 1.0

    def test_confidence_is_1_for_heal_generate(self):
        report = _make_report([_make_page(grade=Grade.C)])
        advice = self.route(report, re_run_count=0, max_re_runs=2)
        assert advice.confidence == 1.0

    def test_confidence_is_1_for_critical_stop(self):
        critical_finding = _make_finding(severity="critical")
        pages = [_make_page(grade=Grade.F, findings=[critical_finding]) for _ in range(3)]
        report = _make_report(pages)
        advice = self.route(report, re_run_count=0, max_re_runs=2)
        assert advice.confidence == 1.0

    # Rule priority order: budget > extraction_quality(high+first-run) > critical > default

    def test_budget_exhausted_takes_priority_over_extraction_high(self):
        """Budget rule (1) beats extraction_quality rule (2) — stop even with HIGH findings."""
        finding = _make_finding(check="extraction_quality", severity="high")
        page = _make_page(grade=Grade.F, findings=[finding])
        report = _make_report([page])
        advice = self.route(report, re_run_count=2, max_re_runs=2)
        assert advice.routing == "stop"
        assert "exhausted" in advice.stop_reason.lower()

    def test_budget_exhausted_takes_priority_over_critical_rate(self):
        """Budget rule (1) beats critical-rate rule (3)."""
        critical_finding = _make_finding(severity="critical")
        pages = [_make_page(grade=Grade.F, findings=[critical_finding]) for _ in range(3)]
        report = _make_report(pages)
        advice = self.route(report, re_run_count=3, max_re_runs=3)
        assert advice.routing == "stop"
        assert "exhausted" in advice.stop_reason.lower()
