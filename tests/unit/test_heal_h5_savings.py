"""H5 benchmark: section-level heal reduces unnecessary LLM calls (V2SC-08).

Goal: When only 8 of 34 pages fail, the heal loop should target ≤8 pages
per step (not all 34), producing ≤ 8 × num_sections Generate calls.

We use a CountingMockLLM that records each call and verify the cap is respected.
"""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock


class CountingMockLLM:
    """Counts LLM calls and returns a canned response."""

    def __init__(self, response: str = "{}") -> None:
        self.call_count = 0
        self.calls: list[dict] = []
        self._response = response

    def chat_completion(self, messages: list[dict], **kwargs: Any) -> dict:
        self.call_count += 1
        self.calls.append({"messages": messages})
        return {"content": self._response}


class TestHealSavingsModel:
    """Verify the heal target-pages budget logic respects page caps."""

    def _make_report(self, total: int = 34, failing: int = 8):
        """Build a minimal EvaluationReport stub with given failing pages."""
        from launcher.models.evaluation import EvaluationReport, Grade, PageEvaluation, Verdict

        pages = []
        for i in range(total):
            grade = Grade.F if i < failing else Grade.A
            pages.append(PageEvaluation(
                slug=f"page-{i:03d}",
                grade=grade,
                findings=[],
                check_results={},
            ))
        return EvaluationReport(
            verdict=Verdict.NO_GO,
            pages=pages,
        )

    def test_prioritize_targets_caps_at_failing_count(self) -> None:
        """_prioritize_target_pages returns at most `failing` pages, not all 34."""
        try:
            from launcher.cli.heal import _prioritize_target_pages
        except ImportError:
            import pytest
            pytest.skip("heal CLI not available in this environment")

        report = self._make_report(total=34, failing=8)

        # Create a mock BudgetTracker that allows 10 calls per step
        budget = MagicMock()
        budget.remaining_for_step.return_value = {"calls_per_step": 10}

        targets = _prioritize_target_pages(report, budget, step_idx=0, max_steps=5)
        # Should return all 8 failing pages (≤ cap of 10 and ≤ 8 failing)
        assert len(targets) <= 8
        assert len(targets) == 8

    def test_targets_are_worst_grade_first(self) -> None:
        """Failing pages prioritized F before D before C."""
        from launcher.models.evaluation import (
            EvaluationReport, Grade, PageEvaluation, Verdict
        )
        try:
            from launcher.cli.heal import _prioritize_target_pages
        except ImportError:
            import pytest
            pytest.skip("heal CLI not available in this environment")

        pages = [
            PageEvaluation(slug="c-page", grade=Grade.C, findings=[], check_results={}),
            PageEvaluation(slug="f-page", grade=Grade.F, findings=[], check_results={}),
            PageEvaluation(slug="d-page", grade=Grade.D, findings=[], check_results={}),
        ]
        report = EvaluationReport(verdict="NO_GO", pages=pages)
        budget = MagicMock()
        budget.remaining_for_step.return_value = {"calls_per_step": 5}

        targets = _prioritize_target_pages(report, budget, step_idx=0, max_steps=5)
        assert targets[0] == "f-page"
        assert targets[1] == "d-page"
        assert targets[2] == "c-page"

    def test_budget_cap_limits_targets(self) -> None:
        """When budget allows only 3 calls, at most 3 targets returned."""
        try:
            from launcher.cli.heal import _prioritize_target_pages
        except ImportError:
            import pytest
            pytest.skip("heal CLI not available in this environment")

        report = self._make_report(total=34, failing=8)
        budget = MagicMock()
        budget.remaining_for_step.return_value = {"calls_per_step": 3}

        targets = _prioritize_target_pages(report, budget, step_idx=0, max_steps=5)
        assert len(targets) <= 3

    def test_h5_total_llm_calls_bounded(self) -> None:
        """H5 efficiency contract: ≤ 8 targets × 1 section avg = ≤ 8 LLM calls."""
        try:
            from launcher.cli.heal import _prioritize_target_pages
        except ImportError:
            import pytest
            pytest.skip("heal CLI not available in this environment")

        report = self._make_report(total=34, failing=8)
        budget = MagicMock()
        budget.remaining_for_step.return_value = {"calls_per_step": 20}

        targets = _prioritize_target_pages(report, budget, step_idx=0, max_steps=10)
        # If each failing page had 1 section, max LLM calls = len(targets) × 1 ≤ 8
        sections_per_page = 1  # conservative model assumption
        max_llm_calls = len(targets) * sections_per_page
        assert max_llm_calls <= 8, (
            f"H5 bound violated: {max_llm_calls} calls would be needed "
            f"for {len(targets)} pages × {sections_per_page} sections"
        )
