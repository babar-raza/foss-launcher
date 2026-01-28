"""Integration tests for TC-300: Run loop execution.

Tests:
- Single-run execution (RUN_DIR creation, event log, snapshot persistence)
- Event replay and snapshot reconstruction
- Stop-the-line behavior
- Deterministic state transitions

Spec references:
- specs/11_state_and_events.md (Event log and replay)
- specs/28_coordination_and_handoffs.md (Run loop)
- specs/29_project_repo_structure.md (RUN_DIR layout)
"""

import json
import tempfile
from pathlib import Path

import pytest

from launch.orchestrator.run_loop import execute_run
from launch.state.event_log import read_events
from launch.state.snapshot_manager import read_snapshot, replay_events


@pytest.mark.integration
def test_execute_run_creates_run_dir():
    """Test that execute_run creates RUN_DIR with proper structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_id = "test_run_001"
        run_dir = Path(tmpdir) / "runs" / run_id
        run_config = {
            "product_slug": "test-product",
            "max_fix_attempts": 3,
        }

        # Execute run
        result = execute_run(run_id, run_dir, run_config)

        # Verify RUN_DIR exists
        assert run_dir.exists()

        # Verify required files exist
        assert (run_dir / "events.ndjson").exists()
        assert (run_dir / "snapshot.json").exists()
        assert (run_dir / "telemetry_outbox.jsonl").exists()

        # Verify required directories exist
        assert (run_dir / "work" / "repo").exists()
        assert (run_dir / "work" / "site").exists()
        assert (run_dir / "work" / "workflows").exists()
        assert (run_dir / "artifacts").exists()
        assert (run_dir / "drafts" / "products").exists()
        assert (run_dir / "drafts" / "docs").exists()
        assert (run_dir / "reports").exists()
        assert (run_dir / "logs").exists()


@pytest.mark.integration
def test_execute_run_emits_events():
    """Test that execute_run emits events to event log."""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_id = "test_run_002"
        run_dir = Path(tmpdir) / "runs" / run_id
        run_config = {"max_fix_attempts": 3}

        # Execute run
        result = execute_run(run_id, run_dir, run_config)

        # Read events
        events = read_events(run_dir / "events.ndjson")

        # Verify events exist
        assert len(events) > 0

        # Verify RUN_CREATED event exists
        run_created_events = [e for e in events if e.type == "RUN_CREATED"]
        assert len(run_created_events) == 1
        assert run_created_events[0].run_id == run_id

        # Verify RUN_STATE_CHANGED events exist
        state_change_events = [e for e in events if e.type == "RUN_STATE_CHANGED"]
        assert len(state_change_events) > 0


@pytest.mark.integration
def test_execute_run_writes_snapshot():
    """Test that execute_run writes snapshot after state transitions."""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_id = "test_run_003"
        run_dir = Path(tmpdir) / "runs" / run_id
        run_config = {"max_fix_attempts": 3}

        # Execute run
        result = execute_run(run_id, run_dir, run_config)

        # Read snapshot
        snapshot = read_snapshot(run_dir / "snapshot.json")

        # Verify snapshot structure
        assert snapshot.run_id == run_id
        assert snapshot.run_state in ["DONE", "FAILED"]
        assert snapshot.schema_version is not None


@pytest.mark.integration
def test_replay_events_reconstructs_snapshot():
    """Test that replay algorithm reconstructs snapshot from events."""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_id = "test_run_004"
        run_dir = Path(tmpdir) / "runs" / run_id
        run_config = {"max_fix_attempts": 3}

        # Execute run
        result = execute_run(run_id, run_dir, run_config)

        # Read original snapshot
        original_snapshot = read_snapshot(run_dir / "snapshot.json")

        # Replay events to reconstruct snapshot
        replayed_snapshot = replay_events(run_dir / "events.ndjson", run_id)

        # Verify replayed snapshot matches original
        assert replayed_snapshot.run_id == original_snapshot.run_id
        assert replayed_snapshot.run_state == original_snapshot.run_state


@pytest.mark.integration
def test_execute_run_returns_result():
    """Test that execute_run returns RunResult with correct exit code."""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_id = "test_run_005"
        run_dir = Path(tmpdir) / "runs" / run_id
        run_config = {"max_fix_attempts": 3}

        # Execute run
        result = execute_run(run_id, run_dir, run_config)

        # Verify result structure
        assert result.run_id == run_id
        assert result.final_state in ["DONE", "FAILED"]
        assert result.exit_code in [0, 2]
        assert result.snapshot is not None


@pytest.mark.integration
def test_deterministic_event_ordering():
    """Test that events are written in deterministic order."""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_id = "test_run_006"
        run_dir = Path(tmpdir) / "runs" / run_id
        run_config = {"max_fix_attempts": 3}

        # Execute run
        result = execute_run(run_id, run_dir, run_config)

        # Read events
        events = read_events(run_dir / "events.ndjson")

        # Verify events are in append order
        event_types = [e.type for e in events]

        # First event should be RUN_CREATED
        assert event_types[0] == "RUN_CREATED"

        # State changes should follow creation
        if "RUN_STATE_CHANGED" in event_types:
            first_state_change_idx = event_types.index("RUN_STATE_CHANGED")
            assert first_state_change_idx > 0


@pytest.mark.integration
def test_batch_execution_raises_not_implemented():
    """Test that batch execution raises NotImplementedError (blocked by OQ-BATCH-001)."""
    from launch.orchestrator.run_loop import execute_batch

    with pytest.raises(NotImplementedError, match="OQ-BATCH-001"):
        execute_batch({})
