"""Tests for runtime budget tracking."""

from __future__ import annotations

import time

import pytest

from launcher.util.budget_tracker import BudgetExceededError, BudgetTracker


@pytest.fixture
def budgets():
    return {
        "max_runtime_s": 300,
        "max_llm_calls": 10,
        "max_llm_tokens": 50000,
        "max_file_writes": 100,
        "max_patch_attempts": 5,
    }


class TestBudgetTracker:
    def test_init(self, budgets) -> None:
        tracker = BudgetTracker(budgets=budgets)
        assert tracker.counters["llm_calls"] == 0

    def test_missing_field_raises(self) -> None:
        with pytest.raises(ValueError, match="Missing required budget field"):
            BudgetTracker(budgets={"max_runtime_s": 100})

    def test_record_llm_call(self, budgets) -> None:
        tracker = BudgetTracker(budgets=budgets)
        tracker.record_llm_call(input_tokens=100, output_tokens=200)
        assert tracker.counters["llm_calls"] == 1
        assert tracker.counters["llm_tokens"] == 300

    def test_llm_calls_budget_exceeded(self, budgets) -> None:
        budgets["max_llm_calls"] = 2
        tracker = BudgetTracker(budgets=budgets)
        tracker.record_llm_call(100, 100)
        tracker.record_llm_call(100, 100)
        with pytest.raises(BudgetExceededError, match="LLM call budget exceeded"):
            tracker.record_llm_call(100, 100)

    def test_llm_tokens_budget_exceeded(self, budgets) -> None:
        budgets["max_llm_tokens"] = 500
        tracker = BudgetTracker(budgets=budgets)
        with pytest.raises(BudgetExceededError, match="LLM token budget exceeded"):
            tracker.record_llm_call(300, 300)

    def test_file_write_budget(self, budgets) -> None:
        budgets["max_file_writes"] = 2
        tracker = BudgetTracker(budgets=budgets)
        tracker.record_file_write("a.txt")
        tracker.record_file_write("b.txt")
        with pytest.raises(BudgetExceededError, match="File write budget exceeded"):
            tracker.record_file_write("c.txt")

    def test_patch_budget(self, budgets) -> None:
        budgets["max_patch_attempts"] = 1
        tracker = BudgetTracker(budgets=budgets)
        tracker.record_patch_attempt()
        with pytest.raises(BudgetExceededError, match="Patch attempt budget exceeded"):
            tracker.record_patch_attempt()

    def test_runtime_budget(self, budgets) -> None:
        budgets["max_runtime_s"] = 0  # Expired immediately
        tracker = BudgetTracker(budgets=budgets)
        tracker.start_time = time.time() - 1  # 1 second ago
        with pytest.raises(BudgetExceededError, match="Runtime budget exceeded"):
            tracker.check_runtime()

    def test_get_summary(self, budgets) -> None:
        tracker = BudgetTracker(budgets=budgets)
        tracker.record_llm_call(100, 200)
        summary = tracker.get_summary()
        assert "elapsed_s" in summary
        assert summary["counters"]["llm_calls"] == 1

    def test_to_dict(self, budgets) -> None:
        tracker = BudgetTracker(budgets=budgets)
        d = tracker.to_dict()
        assert "budgets" in d
        assert "counters" in d
        assert "elapsed_s" in d

    def test_budget_exceeded_error_attrs(self) -> None:
        err = BudgetExceededError("test", budget_type="llm_calls")
        assert err.budget_type == "llm_calls"
        assert "BUDGET_EXCEEDED" in err.error_code
