"""Tests for budget tracker (Guarantee F)."""

import time
import pytest
from launch.util.budget_tracker import BudgetTracker, BudgetExceededError


class TestBudgetTrackerInit:
    """Test budget tracker initialization."""

    def test_init_with_valid_budgets(self):
        """Test initialization with valid budgets."""
        budgets = {
            "max_runtime_s": 100,
            "max_llm_calls": 10,
            "max_llm_tokens": 1000,
            "max_file_writes": 50,
            "max_patch_attempts": 5,
        }
        tracker = BudgetTracker(budgets)
        assert tracker.budgets == budgets
        assert tracker.counters["llm_calls"] == 0
        assert tracker.counters["llm_tokens"] == 0

    def test_init_missing_required_field(self):
        """Test initialization fails with missing required field."""
        budgets = {
            "max_runtime_s": 100,
            # Missing other required fields
        }
        with pytest.raises(ValueError, match="Missing required budget field"):
            BudgetTracker(budgets)


class TestLLMCallBudget:
    """Test LLM call budget tracking."""

    def test_record_llm_call_under_budget(self):
        """Test recording LLM call within budget."""
        budgets = {
            "max_runtime_s": 100,
            "max_llm_calls": 10,
            "max_llm_tokens": 1000,
            "max_file_writes": 50,
            "max_patch_attempts": 5,
        }
        tracker = BudgetTracker(budgets)

        tracker.record_llm_call(input_tokens=50, output_tokens=100)

        assert tracker.counters["llm_calls"] == 1
        assert tracker.counters["llm_tokens"] == 150

    def test_record_llm_call_exceeds_call_budget(self):
        """Test that exceeding call budget raises error."""
        budgets = {
            "max_runtime_s": 100,
            "max_llm_calls": 2,
            "max_llm_tokens": 10000,
            "max_file_writes": 50,
            "max_patch_attempts": 5,
        }
        tracker = BudgetTracker(budgets)

        tracker.record_llm_call(100, 200)  # 1st call
        tracker.record_llm_call(100, 200)  # 2nd call

        with pytest.raises(BudgetExceededError) as exc_info:
            tracker.record_llm_call(100, 200)  # 3rd call - exceeds

        assert exc_info.value.error_code == "BUDGET_EXCEEDED_LLM_CALLS"
        assert exc_info.value.budget_type == "llm_calls"

    def test_record_llm_call_exceeds_token_budget(self):
        """Test that exceeding token budget raises error."""
        budgets = {
            "max_runtime_s": 100,
            "max_llm_calls": 100,
            "max_llm_tokens": 500,
            "max_file_writes": 50,
            "max_patch_attempts": 5,
        }
        tracker = BudgetTracker(budgets)

        tracker.record_llm_call(200, 200)  # 400 tokens

        with pytest.raises(BudgetExceededError) as exc_info:
            tracker.record_llm_call(200, 200)  # 800 total - exceeds

        assert exc_info.value.error_code == "BUDGET_EXCEEDED_LLM_TOKENS"


class TestFileWriteBudget:
    """Test file write budget tracking."""

    def test_record_file_write_under_budget(self):
        """Test recording file writes within budget."""
        budgets = {
            "max_runtime_s": 100,
            "max_llm_calls": 10,
            "max_llm_tokens": 1000,
            "max_file_writes": 5,
            "max_patch_attempts": 5,
        }
        tracker = BudgetTracker(budgets)

        for i in range(5):
            tracker.record_file_write(f"/path/to/file{i}.txt")

        assert tracker.counters["file_writes"] == 5

    def test_record_file_write_exceeds_budget(self):
        """Test that exceeding file write budget raises error."""
        budgets = {
            "max_runtime_s": 100,
            "max_llm_calls": 10,
            "max_llm_tokens": 1000,
            "max_file_writes": 2,
            "max_patch_attempts": 5,
        }
        tracker = BudgetTracker(budgets)

        tracker.record_file_write("/path/1.txt")
        tracker.record_file_write("/path/2.txt")

        with pytest.raises(BudgetExceededError) as exc_info:
            tracker.record_file_write("/path/3.txt")

        assert exc_info.value.error_code == "BUDGET_EXCEEDED_FILE_WRITES"


class TestRuntimeBudget:
    """Test runtime budget tracking."""

    def test_check_runtime_under_budget(self):
        """Test runtime check within budget."""
        budgets = {
            "max_runtime_s": 10,
            "max_llm_calls": 10,
            "max_llm_tokens": 1000,
            "max_file_writes": 50,
            "max_patch_attempts": 5,
        }
        tracker = BudgetTracker(budgets)

        # Should not raise
        tracker.check_runtime()

    def test_check_runtime_exceeds_budget(self):
        """Test that exceeding runtime budget raises error."""
        budgets = {
            "max_runtime_s": 1,  # 1 second
            "max_llm_calls": 10,
            "max_llm_tokens": 1000,
            "max_file_writes": 50,
            "max_patch_attempts": 5,
        }
        tracker = BudgetTracker(budgets)

        # Manually set start time to past
        tracker.start_time = time.time() - 2

        with pytest.raises(BudgetExceededError) as exc_info:
            tracker.check_runtime()

        assert exc_info.value.error_code == "BUDGET_EXCEEDED_RUNTIME"


class TestPatchAttemptBudget:
    """Test patch attempt budget tracking."""

    def test_record_patch_attempt_under_budget(self):
        """Test recording patch attempts within budget."""
        budgets = {
            "max_runtime_s": 100,
            "max_llm_calls": 10,
            "max_llm_tokens": 1000,
            "max_file_writes": 50,
            "max_patch_attempts": 3,
        }
        tracker = BudgetTracker(budgets)

        tracker.record_patch_attempt()
        tracker.record_patch_attempt()

        assert tracker.counters["patch_attempts"] == 2

    def test_record_patch_attempt_exceeds_budget(self):
        """Test that exceeding patch attempt budget raises error."""
        budgets = {
            "max_runtime_s": 100,
            "max_llm_calls": 10,
            "max_llm_tokens": 1000,
            "max_file_writes": 50,
            "max_patch_attempts": 2,
        }
        tracker = BudgetTracker(budgets)

        tracker.record_patch_attempt()
        tracker.record_patch_attempt()

        with pytest.raises(BudgetExceededError) as exc_info:
            tracker.record_patch_attempt()

        assert exc_info.value.error_code == "BUDGET_EXCEEDED_PATCH_ATTEMPTS"


class TestBudgetSummary:
    """Test budget summary and serialization."""

    def test_get_summary(self):
        """Test getting budget summary."""
        budgets = {
            "max_runtime_s": 100,
            "max_llm_calls": 10,
            "max_llm_tokens": 1000,
            "max_file_writes": 50,
            "max_patch_attempts": 5,
        }
        tracker = BudgetTracker(budgets)

        tracker.record_llm_call(100, 200)
        tracker.record_file_write("/path.txt")

        summary = tracker.get_summary()

        assert "elapsed_s" in summary
        assert summary["counters"]["llm_calls"] == 1
        assert summary["counters"]["llm_tokens"] == 300
        assert summary["counters"]["file_writes"] == 1
        assert "utilization" in summary

    def test_to_dict(self):
        """Test serialization to dict."""
        budgets = {
            "max_runtime_s": 100,
            "max_llm_calls": 10,
            "max_llm_tokens": 1000,
            "max_file_writes": 50,
            "max_patch_attempts": 5,
        }
        tracker = BudgetTracker(budgets)

        state = tracker.to_dict()

        assert state["budgets"] == budgets
        assert "counters" in state
        assert "elapsed_s" in state
        assert "start_time" in state
