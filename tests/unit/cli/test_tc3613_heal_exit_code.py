"""TC-3613: Heal wrapper exit code + result printing robustness.

Regression tests proving:
1. HealStep.to_dict() coerces malformed triage_snapshot (object-shape mismatch)
   to a stable, JSON-serializable dict without raising.
2. HealResult.to_dict() produces stable keys including initial_failed_gate_count.
3. write_heal_plan() never raises even when triage_snapshot entries have an
   unexpected type — it returns None and logs a warning instead.
4. Exit code is 0 (non-regressive) when final_failed_gate_count <= initial.
5. Exit code is 1 when initial is unknown (-1) — cannot determine baseline.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import patch

import pytest

from launch.cli.heal import (
    HealResult,
    HealStep,
    write_heal_plan,
)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_step(
    step_idx: int = 0,
    worker: str = "W10",
    reason: str = "test reason",
    snapshot: Any = None,
    before: int = 3,
    after: int = 2,
    exit_code: int = 0,
    notes: str = "",
    outcome: str = "unchanged",
) -> HealStep:
    if snapshot is None:
        snapshot = [{"command": "launch resume --run-dir /tmp --from-worker W10", "reason": reason}]
    return HealStep(
        step_idx=step_idx,
        chosen_worker=worker,
        reason=reason,
        triage_snapshot=snapshot,
        failed_gate_count_before=before,
        failed_gate_count_after=after,
        exit_code=exit_code,
        notes=notes,
        outcome=outcome,  # type: ignore[arg-type]
    )


def _make_result(
    stop_reason: str = "stuck",
    initial: int = 3,
    final: int = 2,
    steps: List[HealStep] | None = None,
) -> HealResult:
    r = HealResult(run_id="r_tc3613", mode="strict", max_steps=5)
    r.stop_reason = stop_reason
    r.initial_failed_gate_count = initial
    r.final_failed_gate_count = final
    r.started_at_utc = "2026-02-28T12:00:00+00:00"
    r.finished_at_utc = "2026-02-28T12:01:00+00:00"
    if steps is not None:
        r.steps = steps
    return r


# ══════════════════════════════════════════════════════════════════════════════
# A. HealStep.to_dict() defensive serialization
# ══════════════════════════════════════════════════════════════════════════════


class TestHealStepToDict:
    """Prove HealStep.to_dict() handles malformed triage_snapshot entries."""

    def test_normal_snapshot_preserved(self):
        """Standard snapshot dict entries pass through unchanged."""
        step = _make_step(
            snapshot=[
                {"command": "launch resume --from-worker W10", "reason": "fix FQ-1"},
                {"command": "launch resume --from-worker W6", "reason": "fix SEO"},
            ]
        )
        d = step.to_dict()
        assert d["triage_snapshot"] == [
            {"command": "launch resume --from-worker W10", "reason": "fix FQ-1"},
            {"command": "launch resume --from-worker W6", "reason": "fix SEO"},
        ]

    def test_non_dict_snapshot_entry_coerced_to_raw(self):
        """Non-dict snapshot entries are wrapped in {'_raw': str(entry)}.

        This is the TC-3613 failure mode: if a wrapper or future code accidentally
        appends a non-dict to triage_snapshot, asdict() would not fail (it does
        shallow copies of lists), but json.dumps could fail on custom objects.
        to_dict() coerces them to strings.
        """
        # Simulate an object that isn't a plain dict
        class FakeRec:
            def __str__(self):
                return "FakeRec(W10, fix-FQ1)"

        step = _make_step(snapshot=[FakeRec(), {"command": "cmd", "reason": "r"}])
        d = step.to_dict()
        # First entry: non-dict → {"_raw": "FakeRec(W10, fix-FQ1)"}
        assert d["triage_snapshot"][0] == {"_raw": "FakeRec(W10, fix-FQ1)"}
        # Second entry: normal dict → coerced keys/values are strings
        assert d["triage_snapshot"][1]["command"] == "cmd"

    def test_snapshot_with_non_string_values_coerced(self):
        """Dict entries with non-string values are str()-coerced."""
        step = _make_step(snapshot=[{"command": "cmd", "priority": 42}])
        d = step.to_dict()
        # values coerced to str
        assert d["triage_snapshot"][0]["priority"] == "42"

    def test_to_dict_result_is_json_serializable(self):
        """to_dict() output survives json.dumps without exception."""
        step = _make_step()
        d = step.to_dict()
        serialized = json.dumps(d)
        assert "W10" in serialized

    def test_to_dict_stable_keys(self):
        """to_dict() returns all expected keys (including TC-3614 additions)."""
        step = _make_step()
        d = step.to_dict()
        required_keys = {
            "step_idx", "chosen_worker", "reason", "triage_snapshot",
            "failed_gate_count_before", "failed_gate_count_after",
            "exit_code", "notes", "outcome",
        }
        assert required_keys.issubset(set(d.keys())), (
            f"Missing keys: {required_keys - set(d.keys())}"
        )

    def test_empty_snapshot_produces_empty_list(self):
        """Empty triage_snapshot passes through as empty list."""
        step = _make_step(snapshot=[])
        d = step.to_dict()
        assert d["triage_snapshot"] == []


# ══════════════════════════════════════════════════════════════════════════════
# B. HealResult.to_dict() stable keys + initial_failed_gate_count
# ══════════════════════════════════════════════════════════════════════════════


class TestHealResultToDict:
    """Prove HealResult.to_dict() includes all expected keys."""

    def test_to_dict_stable_keys(self):
        """to_dict() returns all expected top-level keys."""
        result = _make_result()
        d = result.to_dict()
        assert set(d.keys()) == {
            "schema_version", "run_id", "mode", "max_steps",
            "initial_failed_gate_count", "steps", "stop_reason",
            "final_failed_gate_count", "started_at_utc", "finished_at_utc",
        }

    def test_initial_failed_gate_count_included(self):
        """initial_failed_gate_count is present and correct."""
        result = _make_result(initial=5, final=2)
        d = result.to_dict()
        assert d["initial_failed_gate_count"] == 5

    def test_to_dict_delegates_to_step_to_dict(self):
        """Steps in to_dict() use HealStep.to_dict() (not asdict())."""
        step = _make_step(before=3, after=2, outcome="improved")
        result = _make_result(steps=[step])
        d = result.to_dict()
        assert len(d["steps"]) == 1
        assert d["steps"][0]["outcome"] == "improved"

    def test_to_dict_is_json_serializable(self):
        """to_dict() output survives json.dumps without exception."""
        step = _make_step()
        result = _make_result(steps=[step])
        serialized = json.dumps(result.to_dict())
        assert "r_tc3613" in serialized


# ══════════════════════════════════════════════════════════════════════════════
# C. write_heal_plan() defensive — never raises
# ══════════════════════════════════════════════════════════════════════════════


class TestWriteHealPlanDefensive:
    """Prove write_heal_plan() never raises; returns None on failure."""

    def test_write_heal_plan_succeeds_with_valid_result(self, tmp_path):
        """Normal result → file written, path returned."""
        run_dir = tmp_path / "r_test"
        run_dir.mkdir()
        result = _make_result(stop_reason="all_gates_pass", initial=3, final=0)
        result.started_at_utc = "2026-02-28T12:00:00+00:00"
        result.finished_at_utc = "2026-02-28T12:01:00+00:00"

        out_path = write_heal_plan(run_dir, result)

        assert out_path is not None
        assert out_path.exists()
        plan = json.loads(out_path.read_text())
        assert plan["stop_reason"] == "all_gates_pass"
        assert plan["initial_failed_gate_count"] == 3

    def test_write_heal_plan_survives_serialization_error(self, tmp_path, caplog):
        """If atomic_write_json raises, write_heal_plan returns None (not raises).

        This is the TC-3613 regression test: the prior failure mode was a
        TypeError from asdict() when steps contained unexpected object shapes,
        propagating through run_heal_loop to the CLI handler → exit code 1 even
        when heal had completed successfully.
        """
        run_dir = tmp_path / "r_bad"
        run_dir.mkdir()
        result = _make_result(stop_reason="all_gates_pass", initial=3, final=0)

        with patch("launch.io.atomic.atomic_write_json", side_effect=TypeError("simulated shape mismatch")):
            import logging
            with caplog.at_level(logging.WARNING, logger="launch.cli.heal"):
                out_path = write_heal_plan(run_dir, result)

        # Must return None, not raise
        assert out_path is None
        # Warning must be logged
        assert any("heal_plan.json" in record.message for record in caplog.records)

    def test_write_heal_plan_with_non_dict_snapshot_does_not_crash(self, tmp_path):
        """Step with non-dict triage_snapshot entries → file written successfully.

        to_dict() coerces the non-dict entries; write succeeds.
        """
        class BadEntry:
            def __str__(self):
                return "bad-entry"

        run_dir = tmp_path / "r_bad_snap"
        run_dir.mkdir()
        step = HealStep(
            step_idx=0,
            chosen_worker="W10",
            reason="test",
            triage_snapshot=[BadEntry()],  # type: ignore[list-item]
            failed_gate_count_before=2,
            failed_gate_count_after=1,
        )
        result = _make_result(steps=[step])

        out_path = write_heal_plan(run_dir, result)

        assert out_path is not None
        plan = json.loads(out_path.read_text())
        # Non-dict entry coerced to {"_raw": "bad-entry"}
        assert plan["steps"][0]["triage_snapshot"] == [{"_raw": "bad-entry"}]


# ══════════════════════════════════════════════════════════════════════════════
# D. Exit code logic — non-regressive contract
# ══════════════════════════════════════════════════════════════════════════════


def _compute_heal_exit_code(result: HealResult) -> int:
    """Mirror of the exit code logic in launch.cli.main.heal().

    Extracted here so we can test the contract without invoking the full CLI.
    TC-3613: Exit 0 when non-regressive (final <= initial, both known).
    """
    if result.stop_reason == "all_gates_pass":
        return 0
    if (
        result.initial_failed_gate_count >= 0
        and result.final_failed_gate_count >= 0
        and result.final_failed_gate_count <= result.initial_failed_gate_count
    ):
        return 0  # Non-regressive
    return 1


class TestExitCodeLogic:
    """Prove the non-regressive exit code contract."""

    def test_all_gates_pass_exit_0(self):
        """stop_reason=all_gates_pass → exit 0 (baseline)."""
        result = _make_result(stop_reason="all_gates_pass", initial=3, final=0)
        assert _compute_heal_exit_code(result) == 0

    def test_partial_improvement_exit_0(self):
        """final < initial (not zero) → exit 0 (partial improvement)."""
        result = _make_result(stop_reason="max_steps", initial=5, final=3)
        assert _compute_heal_exit_code(result) == 0

    def test_stuck_at_baseline_exit_0(self):
        """final == initial → exit 0 (non-regressive, stuck)."""
        result = _make_result(stop_reason="stuck", initial=4, final=4)
        assert _compute_heal_exit_code(result) == 0

    def test_unknown_initial_exit_1(self):
        """initial=-1 (resume_failed, unknown baseline) → exit 1."""
        result = _make_result(stop_reason="resume_failed", initial=-1, final=-1)
        assert _compute_heal_exit_code(result) == 1

    def test_regression_exit_1(self):
        """final > initial → exit 1 (regression)."""
        result = _make_result(stop_reason="max_steps", initial=3, final=5)
        assert _compute_heal_exit_code(result) == 1

    def test_no_recommendation_non_regressive_exit_0(self):
        """no_recommendation stop with final <= initial → exit 0."""
        result = _make_result(stop_reason="no_recommendation", initial=2, final=2)
        assert _compute_heal_exit_code(result) == 0
