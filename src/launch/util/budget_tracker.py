"""Runtime budget tracking and enforcement (Guarantee F).

This module provides infrastructure for tracking resource usage and enforcing
budget limits. The orchestrator will integrate this when implemented.

Binding contract: specs/34_strict_compliance_guarantees.md (Guarantee F)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Any


class BudgetExceededError(Exception):
    """Raised when a budget limit is exceeded (Guarantee F)."""

    def __init__(self, message: str, budget_type: str):
        super().__init__(message)
        self.error_code = f"BUDGET_EXCEEDED_{budget_type.upper()}"
        self.budget_type = budget_type


@dataclass
class BudgetTracker:
    """Runtime budget tracking (Guarantee F).

    Usage (orchestrator integration point):
        tracker = BudgetTracker(run_config["budgets"])

        # Before LLM call:
        tracker.record_llm_call(input_tokens=100, output_tokens=200)

        # Before file write:
        tracker.record_file_write(path)

        # In main loop:
        tracker.check_runtime()

        # Get report:
        summary = tracker.get_summary()
    """

    budgets: Dict[str, Any]
    counters: Dict[str, int] = field(default_factory=dict)
    start_time: float = field(default_factory=time.time)

    def __post_init__(self):
        """Initialize counters."""
        required_fields = [
            "max_runtime_s", "max_llm_calls", "max_llm_tokens",
            "max_file_writes", "max_patch_attempts"
        ]
        for field_name in required_fields:
            if field_name not in self.budgets:
                raise ValueError(f"Missing required budget field: {field_name}")

        self.counters = {
            "llm_calls": 0,
            "llm_tokens": 0,
            "file_writes": 0,
            "patch_attempts": 0,
        }

    def record_llm_call(self, input_tokens: int, output_tokens: int) -> None:
        """Record LLM call and check budgets.

        Raises:
            BudgetExceededError: If budget exceeded
        """
        self.counters["llm_calls"] += 1
        self.counters["llm_tokens"] += input_tokens + output_tokens

        if self.counters["llm_calls"] > self.budgets["max_llm_calls"]:
            raise BudgetExceededError(
                f"LLM call budget exceeded: {self.counters['llm_calls']} > {self.budgets['max_llm_calls']}",
                budget_type="llm_calls"
            )

        if self.counters["llm_tokens"] > self.budgets["max_llm_tokens"]:
            raise BudgetExceededError(
                f"LLM token budget exceeded: {self.counters['llm_tokens']} > {self.budgets['max_llm_tokens']}",
                budget_type="llm_tokens"
            )

    def record_file_write(self, path: str) -> None:
        """Record file write and check budget."""
        self.counters["file_writes"] += 1

        if self.counters["file_writes"] > self.budgets["max_file_writes"]:
            raise BudgetExceededError(
                f"File write budget exceeded: {self.counters['file_writes']} > {self.budgets['max_file_writes']}",
                budget_type="file_writes"
            )

    def record_patch_attempt(self) -> None:
        """Record patch attempt and check budget."""
        self.counters["patch_attempts"] += 1

        if self.counters["patch_attempts"] > self.budgets["max_patch_attempts"]:
            raise BudgetExceededError(
                f"Patch attempt budget exceeded: {self.counters['patch_attempts']} > {self.budgets['max_patch_attempts']}",
                budget_type="patch_attempts"
            )

    def check_runtime(self) -> None:
        """Check if runtime budget exceeded."""
        elapsed = time.time() - self.start_time

        if elapsed > self.budgets["max_runtime_s"]:
            raise BudgetExceededError(
                f"Runtime budget exceeded: {elapsed:.1f}s > {self.budgets['max_runtime_s']}s",
                budget_type="runtime"
            )

    def get_summary(self) -> Dict[str, Any]:
        """Get current budget usage summary."""
        elapsed = time.time() - self.start_time
        return {
            "elapsed_s": elapsed,
            "counters": self.counters.copy(),
            "budgets": self.budgets.copy(),
            "utilization": {
                "runtime": f"{elapsed / self.budgets['max_runtime_s'] * 100:.1f}%",
                "llm_calls": f"{self.counters['llm_calls'] / self.budgets['max_llm_calls'] * 100:.1f}%",
                "llm_tokens": f"{self.counters['llm_tokens'] / self.budgets['max_llm_tokens'] * 100:.1f}%",
                "file_writes": f"{self.counters['file_writes'] / self.budgets['max_file_writes'] * 100:.1f}%",
            }
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serialize state for reporting."""
        return {
            "budgets": self.budgets,
            "counters": self.counters,
            "elapsed_s": time.time() - self.start_time,
            "start_time": self.start_time,
        }
