"""Tests for the phase group executor (TC-2500).

Validates:
- PHASE_GROUPS mapping completeness and correctness
- Single phase execution via execute_phase_group()
- Phase range execution via execute_phase_range()
- Error propagation (worker failure, invalid phase IDs)
- Boundary event emission (PHASE_STARTED / PHASE_COMPLETED)
- Fail-fast behaviour in range execution

All tests mock ``execute_run_from_node()`` — no actual pipeline execution.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from launch.orchestrator.phase_executor import (
    EVENT_PHASE_COMPLETED,
    EVENT_PHASE_STARTED,
    PHASE_GROUPS,
    PhaseResult,
    _PHASE_ORDER,
    execute_phase_group,
    execute_phase_range,
)
from launch.orchestrator.run_loop import RESUME_NODE_MAP, RunResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_run_result(exit_code: int = 0, final_state: str = "DONE") -> RunResult:
    """Create a minimal RunResult for mocking."""
    return RunResult(
        run_id="r_test",
        final_state=final_state,
        exit_code=exit_code,
    )


def _make_run_config() -> Dict[str, Any]:
    """Return a minimal run config dict for tests."""
    return {"product_slug": "test-product", "offline_mode": True}


# ---------------------------------------------------------------------------
# T1: PHASE_GROUPS mapping is complete — covers all 11 workers, no gaps
# ---------------------------------------------------------------------------


class TestPhaseGroupsMapping:
    """Verify PHASE_GROUPS constant correctness."""

    def test_all_six_phases_present(self) -> None:
        """PHASE_GROUPS contains exactly P1 through P6."""
        assert set(PHASE_GROUPS.keys()) == {"P1", "P2", "P3", "P4", "P5", "P6"}

    def test_all_workers_covered(self) -> None:
        """Every worker W1-W11 appears in exactly one phase group."""
        all_workers = []
        for workers in PHASE_GROUPS.values():
            all_workers.extend(workers)

        expected = [f"W{i}" for i in range(1, 12)]
        assert sorted(all_workers) == sorted(expected)

    def test_no_duplicate_workers(self) -> None:
        """No worker alias appears in more than one phase group."""
        all_workers = []
        for workers in PHASE_GROUPS.values():
            all_workers.extend(workers)
        assert len(all_workers) == len(set(all_workers))

    def test_workers_match_resume_node_map(self) -> None:
        """Every worker in PHASE_GROUPS is a valid key in RESUME_NODE_MAP."""
        for phase_id, workers in PHASE_GROUPS.items():
            for w in workers:
                assert w in RESUME_NODE_MAP, (
                    f"Worker '{w}' in phase '{phase_id}' not found in RESUME_NODE_MAP"
                )

    def test_phase_order_matches_keys(self) -> None:
        """_PHASE_ORDER contains exactly the same keys as PHASE_GROUPS."""
        assert set(_PHASE_ORDER) == set(PHASE_GROUPS.keys())
        assert _PHASE_ORDER == ["P1", "P2", "P3", "P4", "P5", "P6"]

    def test_specific_phase_assignments(self) -> None:
        """Verify each phase maps to the correct workers per the taskcard."""
        assert PHASE_GROUPS["P1"] == ("W1", "W2")
        assert PHASE_GROUPS["P2"] == ("W3", "W4")
        assert PHASE_GROUPS["P3"] == ("W5", "W6")
        assert PHASE_GROUPS["P4"] == ("W7", "W8")
        assert PHASE_GROUPS["P5"] == ("W9", "W10")
        assert PHASE_GROUPS["P6"] == ("W11",)


# ---------------------------------------------------------------------------
# T2: execute_phase_group — happy path
# ---------------------------------------------------------------------------


class TestExecutePhaseGroup:
    """Verify execute_phase_group() delegates correctly."""

    @patch("launch.orchestrator.phase_executor.execute_run_from_node")
    @patch("launch.orchestrator.phase_executor.append_event")
    def test_calls_execute_run_from_node_with_first_worker(
        self, mock_append: MagicMock, mock_exec: MagicMock, tmp_path: Path
    ) -> None:
        """execute_phase_group('P1') calls execute_run_from_node with 'W1'."""
        mock_exec.return_value = _make_run_result()
        run_dir = tmp_path / "runs" / "r_test"
        run_dir.mkdir(parents=True)

        result = execute_phase_group("r_test", run_dir, _make_run_config(), "P1")

        mock_exec.assert_called_once_with(
            run_id="r_test",
            run_dir=run_dir,
            run_config=_make_run_config(),
            from_worker="W1",
        )
        assert result.ok is True
        assert result.phase_id == "P1"
        assert result.workers == ["W1", "W2"]
        assert result.error is None

    @patch("launch.orchestrator.phase_executor.execute_run_from_node")
    @patch("launch.orchestrator.phase_executor.append_event")
    def test_p3_starts_from_w5(
        self, mock_append: MagicMock, mock_exec: MagicMock, tmp_path: Path
    ) -> None:
        """execute_phase_group('P3') calls execute_run_from_node with 'W5'."""
        mock_exec.return_value = _make_run_result()
        run_dir = tmp_path / "runs" / "r_test"
        run_dir.mkdir(parents=True)

        result = execute_phase_group("r_test", run_dir, _make_run_config(), "P3")

        mock_exec.assert_called_once_with(
            run_id="r_test",
            run_dir=run_dir,
            run_config=_make_run_config(),
            from_worker="W5",
        )
        assert result.ok is True
        assert result.workers == ["W5", "W6"]

    @patch("launch.orchestrator.phase_executor.execute_run_from_node")
    @patch("launch.orchestrator.phase_executor.append_event")
    def test_p6_starts_from_w11(
        self, mock_append: MagicMock, mock_exec: MagicMock, tmp_path: Path
    ) -> None:
        """execute_phase_group('P6') calls execute_run_from_node with 'W11'."""
        mock_exec.return_value = _make_run_result()
        run_dir = tmp_path / "runs" / "r_test"
        run_dir.mkdir(parents=True)

        result = execute_phase_group("r_test", run_dir, _make_run_config(), "P6")

        mock_exec.assert_called_once_with(
            run_id="r_test",
            run_dir=run_dir,
            run_config=_make_run_config(),
            from_worker="W11",
        )
        assert result.ok is True
        assert result.workers == ["W11"]


# ---------------------------------------------------------------------------
# T3: execute_phase_group — error propagation
# ---------------------------------------------------------------------------


class TestPhaseGroupErrorPropagation:
    """Verify failures are captured in PhaseResult."""

    @patch("launch.orchestrator.phase_executor.execute_run_from_node")
    @patch("launch.orchestrator.phase_executor.append_event")
    def test_nonzero_exit_code_sets_ok_false(
        self, mock_append: MagicMock, mock_exec: MagicMock, tmp_path: Path
    ) -> None:
        """A non-zero exit code from the run results in ok=False."""
        mock_exec.return_value = _make_run_result(exit_code=2, final_state="FAILED")
        run_dir = tmp_path / "runs" / "r_test"
        run_dir.mkdir(parents=True)

        result = execute_phase_group("r_test", run_dir, _make_run_config(), "P1")

        assert result.ok is False
        assert "exit_code=2" in result.error
        assert "FAILED" in result.error

    @patch("launch.orchestrator.phase_executor.execute_run_from_node")
    @patch("launch.orchestrator.phase_executor.append_event")
    def test_exception_sets_ok_false(
        self, mock_append: MagicMock, mock_exec: MagicMock, tmp_path: Path
    ) -> None:
        """An exception from execute_run_from_node is captured in PhaseResult."""
        mock_exec.side_effect = ValueError("Missing artifact: product_facts.json")
        run_dir = tmp_path / "runs" / "r_test"
        run_dir.mkdir(parents=True)

        result = execute_phase_group("r_test", run_dir, _make_run_config(), "P5")

        assert result.ok is False
        assert "ValueError" in result.error
        assert "product_facts.json" in result.error

    def test_invalid_phase_id_raises_value_error(self, tmp_path: Path) -> None:
        """An unknown phase_id raises ValueError with valid phase list."""
        with pytest.raises(ValueError, match="Unknown phase_id 'PX'"):
            execute_phase_group("r_test", tmp_path, {}, "PX")

    def test_invalid_phase_id_lists_valid_phases(self, tmp_path: Path) -> None:
        """The ValueError message contains all valid phase identifiers."""
        with pytest.raises(ValueError) as exc_info:
            execute_phase_group("r_test", tmp_path, {}, "BOGUS")
        for pid in _PHASE_ORDER:
            assert pid in str(exc_info.value)


# ---------------------------------------------------------------------------
# T4: Boundary event emission
# ---------------------------------------------------------------------------


class TestPhaseEventEmission:
    """Verify PHASE_STARTED and PHASE_COMPLETED events are emitted."""

    @patch("launch.orchestrator.phase_executor.execute_run_from_node")
    @patch("launch.orchestrator.phase_executor.append_event")
    def test_started_and_completed_events_emitted(
        self, mock_append: MagicMock, mock_exec: MagicMock, tmp_path: Path
    ) -> None:
        """Both PHASE_STARTED and PHASE_COMPLETED events are appended."""
        mock_exec.return_value = _make_run_result()
        run_dir = tmp_path / "runs" / "r_test"
        run_dir.mkdir(parents=True)

        execute_phase_group("r_test", run_dir, _make_run_config(), "P2")

        assert mock_append.call_count == 2

        # First call: PHASE_STARTED
        first_event = mock_append.call_args_list[0][0][1]  # positional arg [1]
        assert first_event.type == EVENT_PHASE_STARTED
        assert first_event.payload["phase_id"] == "P2"
        assert first_event.payload["workers"] == ["W3", "W4"]
        assert first_event.payload["entry_worker"] == "W3"

        # Second call: PHASE_COMPLETED
        second_event = mock_append.call_args_list[1][0][1]
        assert second_event.type == EVENT_PHASE_COMPLETED
        assert second_event.payload["phase_id"] == "P2"
        assert second_event.payload["ok"] is True
        assert second_event.payload["error"] is None

    @patch("launch.orchestrator.phase_executor.execute_run_from_node")
    @patch("launch.orchestrator.phase_executor.append_event")
    def test_completed_event_records_failure(
        self, mock_append: MagicMock, mock_exec: MagicMock, tmp_path: Path
    ) -> None:
        """PHASE_COMPLETED event payload contains ok=False when phase fails."""
        mock_exec.side_effect = RuntimeError("kaboom")
        run_dir = tmp_path / "runs" / "r_test"
        run_dir.mkdir(parents=True)

        execute_phase_group("r_test", run_dir, _make_run_config(), "P4")

        second_event = mock_append.call_args_list[1][0][1]
        assert second_event.type == EVENT_PHASE_COMPLETED
        assert second_event.payload["ok"] is False
        assert "kaboom" in second_event.payload["error"]


# ---------------------------------------------------------------------------
# T5: PhaseResult dataclass
# ---------------------------------------------------------------------------


class TestPhaseResult:
    """Verify PhaseResult is JSON-serialisable."""

    def test_to_dict_roundtrip(self) -> None:
        """to_dict() returns a plain dict that json.dumps can serialise."""
        pr = PhaseResult(
            phase_id="P3",
            workers=["W5", "W6"],
            ok=True,
            error=None,
            started_at_utc="2026-02-25T10:00:00+00:00",
            finished_at_utc="2026-02-25T10:05:00+00:00",
        )
        d = pr.to_dict()
        assert isinstance(d, dict)
        # Must be JSON-serialisable
        serialised = json.dumps(d)
        assert '"phase_id": "P3"' in serialised

    def test_to_dict_with_error(self) -> None:
        """to_dict() correctly includes error string."""
        pr = PhaseResult(phase_id="P1", workers=["W1", "W2"], ok=False, error="boom")
        d = pr.to_dict()
        assert d["ok"] is False
        assert d["error"] == "boom"


# ---------------------------------------------------------------------------
# T6: execute_phase_range — happy path
# ---------------------------------------------------------------------------


class TestExecutePhaseRange:
    """Verify execute_phase_range() iterates phases sequentially."""

    @patch("launch.orchestrator.phase_executor.execute_run_from_node")
    @patch("launch.orchestrator.phase_executor.append_event")
    def test_range_p1_to_p3_executes_three_phases(
        self, mock_append: MagicMock, mock_exec: MagicMock, tmp_path: Path
    ) -> None:
        """P1 through P3 yields three PhaseResult objects."""
        mock_exec.return_value = _make_run_result()
        run_dir = tmp_path / "runs" / "r_test"
        run_dir.mkdir(parents=True)

        results = execute_phase_range(
            "r_test", run_dir, _make_run_config(), "P1", "P3"
        )

        assert len(results) == 3
        assert [r.phase_id for r in results] == ["P1", "P2", "P3"]
        assert all(r.ok for r in results)

    @patch("launch.orchestrator.phase_executor.execute_run_from_node")
    @patch("launch.orchestrator.phase_executor.append_event")
    def test_single_phase_range(
        self, mock_append: MagicMock, mock_exec: MagicMock, tmp_path: Path
    ) -> None:
        """start_phase == end_phase executes exactly one phase."""
        mock_exec.return_value = _make_run_result()
        run_dir = tmp_path / "runs" / "r_test"
        run_dir.mkdir(parents=True)

        results = execute_phase_range(
            "r_test", run_dir, _make_run_config(), "P4", "P4"
        )

        assert len(results) == 1
        assert results[0].phase_id == "P4"

    @patch("launch.orchestrator.phase_executor.execute_run_from_node")
    @patch("launch.orchestrator.phase_executor.append_event")
    def test_full_range_p1_to_p6(
        self, mock_append: MagicMock, mock_exec: MagicMock, tmp_path: Path
    ) -> None:
        """Full P1-P6 range executes all six phases."""
        mock_exec.return_value = _make_run_result()
        run_dir = tmp_path / "runs" / "r_test"
        run_dir.mkdir(parents=True)

        results = execute_phase_range(
            "r_test", run_dir, _make_run_config(), "P1", "P6"
        )

        assert len(results) == 6
        assert [r.phase_id for r in results] == _PHASE_ORDER


# ---------------------------------------------------------------------------
# T7: execute_phase_range — fail-fast
# ---------------------------------------------------------------------------


class TestPhaseRangeFailFast:
    """Verify range execution stops on the first phase failure."""

    @patch("launch.orchestrator.phase_executor.execute_run_from_node")
    @patch("launch.orchestrator.phase_executor.append_event")
    def test_stops_on_first_failure(
        self, mock_append: MagicMock, mock_exec: MagicMock, tmp_path: Path
    ) -> None:
        """If P2 fails, P3 is never executed."""
        call_count = 0

        def _side_effect(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                # P2 fails
                return _make_run_result(exit_code=2, final_state="FAILED")
            return _make_run_result()

        mock_exec.side_effect = _side_effect
        run_dir = tmp_path / "runs" / "r_test"
        run_dir.mkdir(parents=True)

        results = execute_phase_range(
            "r_test", run_dir, _make_run_config(), "P1", "P3"
        )

        assert len(results) == 2  # P1 ok, P2 failed, P3 never executed
        assert results[0].ok is True
        assert results[1].ok is False

    @patch("launch.orchestrator.phase_executor.execute_run_from_node")
    @patch("launch.orchestrator.phase_executor.append_event")
    def test_stops_on_exception(
        self, mock_append: MagicMock, mock_exec: MagicMock, tmp_path: Path
    ) -> None:
        """If a phase raises an exception, subsequent phases are skipped."""
        call_count = 0

        def _side_effect(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("W1 crashed")
            return _make_run_result()

        mock_exec.side_effect = _side_effect
        run_dir = tmp_path / "runs" / "r_test"
        run_dir.mkdir(parents=True)

        results = execute_phase_range(
            "r_test", run_dir, _make_run_config(), "P1", "P3"
        )

        assert len(results) == 1
        assert results[0].ok is False
        assert "W1 crashed" in results[0].error


# ---------------------------------------------------------------------------
# T8: execute_phase_range — validation errors
# ---------------------------------------------------------------------------


class TestPhaseRangeValidation:
    """Verify input validation for phase range parameters."""

    def test_invalid_start_phase_raises(self, tmp_path: Path) -> None:
        """Unknown start_phase raises ValueError."""
        with pytest.raises(ValueError, match="Unknown phase_id 'PX'"):
            execute_phase_range("r_test", tmp_path, {}, "PX", "P3")

    def test_invalid_end_phase_raises(self, tmp_path: Path) -> None:
        """Unknown end_phase raises ValueError."""
        with pytest.raises(ValueError, match="Unknown phase_id 'P99'"):
            execute_phase_range("r_test", tmp_path, {}, "P1", "P99")

    def test_reversed_range_raises(self, tmp_path: Path) -> None:
        """end_phase before start_phase raises ValueError."""
        with pytest.raises(ValueError, match="precedes"):
            execute_phase_range("r_test", tmp_path, {}, "P5", "P2")


# ---------------------------------------------------------------------------
# T9: Timing fields are populated
# ---------------------------------------------------------------------------


class TestPhaseResultTiming:
    """Verify started_at_utc and finished_at_utc are populated."""

    @patch("launch.orchestrator.phase_executor.execute_run_from_node")
    @patch("launch.orchestrator.phase_executor.append_event")
    def test_timestamps_are_iso_utc(
        self, mock_append: MagicMock, mock_exec: MagicMock, tmp_path: Path
    ) -> None:
        """Both timestamp fields are non-empty ISO strings."""
        mock_exec.return_value = _make_run_result()
        run_dir = tmp_path / "runs" / "r_test"
        run_dir.mkdir(parents=True)

        result = execute_phase_group("r_test", run_dir, _make_run_config(), "P1")

        assert result.started_at_utc != ""
        assert result.finished_at_utc != ""
        # Basic ISO format check: contains 'T' separator
        assert "T" in result.started_at_utc
        assert "T" in result.finished_at_utc

    @patch("launch.orchestrator.phase_executor.execute_run_from_node")
    @patch("launch.orchestrator.phase_executor.append_event")
    def test_finished_at_is_after_started_at(
        self, mock_append: MagicMock, mock_exec: MagicMock, tmp_path: Path
    ) -> None:
        """finished_at_utc >= started_at_utc (string comparison, ISO format)."""
        mock_exec.return_value = _make_run_result()
        run_dir = tmp_path / "runs" / "r_test"
        run_dir.mkdir(parents=True)

        result = execute_phase_group("r_test", run_dir, _make_run_config(), "P1")

        assert result.finished_at_utc >= result.started_at_utc
