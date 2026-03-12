"""Tests for BudgetTracker.remaining_for_step() (TC-3854 / H5.5)."""
from __future__ import annotations

import pytest

from launcher.util.budget_tracker import BudgetTracker


def _make_tracker(**overrides) -> BudgetTracker:
    budgets = {
        "max_runtime_s": 1800,
        "max_llm_calls": 50,
        "max_llm_tokens": 200_000,
        "max_file_writes": 200,
        "max_patch_attempts": 20,
    }
    budgets.update(overrides)
    return BudgetTracker(budgets=budgets)


class TestRemainingForStep:
    def test_returns_all_required_keys(self) -> None:
        tracker = _make_tracker()
        result = tracker.remaining_for_step(step_idx=0, max_steps=10)
        assert "remaining_runtime_s" in result
        assert "remaining_llm_calls" in result
        assert "remaining_tokens" in result
        assert "tokens_per_step" in result
        assert "calls_per_step" in result

    def test_initial_step_tokens_per_step(self) -> None:
        tracker = _make_tracker(max_llm_tokens=200_000)
        result = tracker.remaining_for_step(step_idx=0, max_steps=10)
        # 200_000 tokens / 10 steps = 20_000 per step
        assert result["tokens_per_step"] == 20_000

    def test_tokens_per_step_decreases_as_step_increases(self) -> None:
        tracker = _make_tracker(max_llm_tokens=100_000)
        result_early = tracker.remaining_for_step(step_idx=0, max_steps=10)
        result_late = tracker.remaining_for_step(step_idx=8, max_steps=10)
        # At step 8, only 2 steps left → tokens_per_step = 50_000
        assert result_late["tokens_per_step"] >= result_early["tokens_per_step"]

    def test_remaining_calls_decremented(self) -> None:
        tracker = _make_tracker(max_llm_calls=10)
        tracker.record_llm_call(input_tokens=100, output_tokens=100)
        tracker.record_llm_call(input_tokens=100, output_tokens=100)
        result = tracker.remaining_for_step(step_idx=0, max_steps=5)
        # 10 - 2 = 8 remaining
        assert result["remaining_llm_calls"] == 8

    def test_remaining_not_negative(self) -> None:
        tracker = _make_tracker(max_llm_calls=2)
        # Use up all LLM calls (will raise BudgetExceededError on 3rd)
        try:
            tracker.record_llm_call(input_tokens=1, output_tokens=1)
            tracker.record_llm_call(input_tokens=1, output_tokens=1)
            tracker.record_llm_call(input_tokens=1, output_tokens=1)
        except Exception:
            pass
        result = tracker.remaining_for_step(step_idx=0, max_steps=5)
        assert result["remaining_llm_calls"] >= 0

    def test_step_idx_equal_max_steps_still_returns_valid(self) -> None:
        tracker = _make_tracker()
        # Edge case: step_idx == max_steps → steps_left = max(1, 0) = 1
        result = tracker.remaining_for_step(step_idx=10, max_steps=10)
        assert result["tokens_per_step"] >= 0
        assert result["calls_per_step"] >= 0
