"""Unit tests for dynamic LangGraph recursion_limit computation.

TC-2960: Prevents GraphRecursionError when max_fix_attempts > 6.
The default LangGraph recursion_limit (25) is insufficient for configs
with high max_fix_attempts or max_redraft_attempts values.

Spec reference: specs/28_coordination_and_handoffs.md (loop policy)
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from launch.orchestrator.run_loop import _compute_recursion_limit


# ---------------------------------------------------------------------------
# Test 1: Default config → floor of 50
# ---------------------------------------------------------------------------
class TestComputeRecursionLimitFormula:
    """Verify the formula and floor logic."""

    def test_defaults_returns_floor_50(self):
        """Default config (fix=3, redraft=1) computes 35, but floor is 50."""
        result = _compute_recursion_limit({})
        # 10 + 4*1 + 2*3 + 15 = 35, floor 50
        assert result == 50

    def test_explicit_defaults_returns_floor_50(self):
        """Explicit default values also return the floor."""
        result = _compute_recursion_limit(
            {"max_fix_attempts": 3, "max_redraft_attempts": 1}
        )
        assert result == 50

    # ---------------------------------------------------------------------------
    # Test 2: High fix attempts → exceeds actual worst case of 26
    # ---------------------------------------------------------------------------
    def test_high_fix_attempts_exceeds_worst_case(self):
        """3d pilot config (fix=8) must exceed the actual worst-case of 26 nodes."""
        result = _compute_recursion_limit({"max_fix_attempts": 8})
        # 10 + 4*1 + 2*8 + 15 = 45, floor 50
        assert result >= 26, f"Must exceed worst-case 26, got {result}"
        assert result == 50

    # ---------------------------------------------------------------------------
    # Test 3: fix=0 → still returns floor 50
    # ---------------------------------------------------------------------------
    def test_floor_enforced_with_zero_fix(self):
        """Even with fix=0 and redraft=0, the floor of 50 holds."""
        result = _compute_recursion_limit(
            {"max_fix_attempts": 0, "max_redraft_attempts": 0}
        )
        # 10 + 0 + 0 + 15 = 25, floor 50
        assert result == 50

    # ---------------------------------------------------------------------------
    # Test 4: Extreme config → exceeds theoretical worst case
    # ---------------------------------------------------------------------------
    def test_extreme_config_exceeds_worst_case(self):
        """fix=20, redraft=3 → computed must exceed theoretical 62."""
        result = _compute_recursion_limit(
            {"max_fix_attempts": 20, "max_redraft_attempts": 3}
        )
        worst_case = 10 + 4 * 3 + 2 * 20  # = 62
        assert result > worst_case, f"Must exceed {worst_case}, got {result}"
        # 10 + 12 + 40 + 15 = 77
        assert result == 77

    # ---------------------------------------------------------------------------
    # Test 5: Parametrized — all combos exceed theoretical worst case
    # ---------------------------------------------------------------------------
    @pytest.mark.parametrize(
        "max_fix,max_redraft",
        [
            (f, r)
            for f in range(0, 21, 4)  # 0, 4, 8, 12, 16, 20
            for r in range(0, 6)       # 0, 1, 2, 3, 4, 5
        ],
    )
    def test_always_exceeds_worst_case(self, max_fix: int, max_redraft: int):
        """For all valid (fix, redraft) combos, limit > worst-case node visits."""
        result = _compute_recursion_limit(
            {"max_fix_attempts": max_fix, "max_redraft_attempts": max_redraft}
        )
        worst_case = 10 + 4 * max_redraft + 2 * max_fix
        assert result > worst_case, (
            f"fix={max_fix}, redraft={max_redraft}: "
            f"limit {result} must exceed worst-case {worst_case}"
        )
        assert result >= 50, f"Floor 50 not enforced, got {result}"


# ---------------------------------------------------------------------------
# Test 6: Wiring — execute_run() passes recursion_limit to .stream()
# ---------------------------------------------------------------------------
_RUN_LOOP = "launch.orchestrator.run_loop"


class TestRecursionLimitWiring:
    """Verify both .stream() call sites pass the computed recursion_limit."""

    @patch(f"{_RUN_LOOP}.build_orchestrator_graph")
    @patch(f"{_RUN_LOOP}.append_event")
    @patch(f"{_RUN_LOOP}.write_snapshot")
    @patch(f"{_RUN_LOOP}.create_initial_snapshot")
    @patch(f"{_RUN_LOOP}.create_run_skeleton")
    def test_execute_run_passes_recursion_limit(
        self,
        mock_skeleton,
        mock_create_snap,
        mock_write_snap,
        mock_append_event,
        mock_build_graph,
    ):
        """execute_run() passes {'recursion_limit': N} to compiled_graph.stream()."""
        from pathlib import Path
        from launch.orchestrator.run_loop import execute_run

        # Snapshot mock — create_initial_snapshot returns an object with .to_dict()
        mock_snap = MagicMock()
        mock_snap.to_dict.return_value = {}
        mock_create_snap.return_value = mock_snap

        # Graph mock — .stream() yields nothing (empty run)
        mock_compiled = MagicMock()
        mock_compiled.stream.return_value = iter([])
        mock_graph = MagicMock()
        mock_graph.compile.return_value = mock_compiled
        mock_build_graph.return_value = mock_graph

        run_config = {"max_fix_attempts": 8, "max_redraft_attempts": 1}
        expected_limit = _compute_recursion_limit(run_config)

        try:
            execute_run("test_run", Path("/tmp/test_run"), run_config)
        except Exception:
            pass  # May fail post-stream — we only care about .stream() args

        # Verify .stream() was called with recursion_limit
        mock_compiled.stream.assert_called_once()
        call_args = mock_compiled.stream.call_args
        stream_config = call_args.args[1] if len(call_args.args) >= 2 else {}
        assert stream_config.get("recursion_limit") == expected_limit, (
            f"Expected recursion_limit={expected_limit}, got {stream_config}"
        )

    @patch(f"{_RUN_LOOP}.build_orchestrator_graph")
    @patch(f"{_RUN_LOOP}.append_event")
    def test_resume_passes_recursion_limit(self, mock_append_event, mock_build_graph, tmp_path):
        """_execute_run_from_node_locked() passes recursion_limit to .stream()."""
        from launch.orchestrator.run_loop import _execute_run_from_node_locked

        # Graph mock
        mock_compiled = MagicMock()
        mock_compiled.stream.return_value = iter([])
        mock_graph = MagicMock()
        mock_graph.compile.return_value = mock_compiled
        mock_build_graph.return_value = mock_graph

        run_config = {"max_fix_attempts": 12, "max_redraft_attempts": 2}
        expected_limit = _compute_recursion_limit(run_config)

        try:
            _execute_run_from_node_locked(
                run_id="test_run",
                run_dir=tmp_path,
                run_config=run_config,
                from_worker="W2",
                node_name="ingest",
                pre_run_state="cloned_inputs",
            )
        except Exception:
            pass

        mock_compiled.stream.assert_called_once()
        call_args = mock_compiled.stream.call_args
        stream_config = call_args.args[1] if len(call_args.args) >= 2 else {}
        assert stream_config.get("recursion_limit") == expected_limit, (
            f"Expected recursion_limit={expected_limit}, got {stream_config}"
        )
