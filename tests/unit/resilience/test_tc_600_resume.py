"""
Tests for TC-600: Run resume logic.

Covers:
- Resume from checkpoint
- Resume with no checkpoint
- Event replay
- Worker rerun determination
- Incomplete worker detection
"""

import json
import pytest
from pathlib import Path
from src.launch.resilience.resume import (
    ResumeResult,
    resume_run,
    replay_events,
    get_incomplete_workers,
)
from src.launch.resilience.checkpoint import create_checkpoint


def create_test_snapshot(run_dir: Path, run_id: str, run_state: str, completed_workers: list):
    """Helper to create test snapshot.json."""
    snapshot = {
        "run_id": run_id,
        "run_state": run_state,
        "completed_workers": completed_workers,
    }
    snapshot_path = run_dir / "snapshot.json"
    with open(snapshot_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2)
    return snapshot_path


def create_test_events(run_dir: Path, events: list):
    """Helper to create test events.ndjson with specific events."""
    events_path = run_dir / "events.ndjson"
    with open(events_path, "w", encoding="utf-8") as f:
        for event in events:
            f.write(json.dumps(event) + "\n")
    return events_path


def test_resume_run_no_checkpoint(tmp_path):
    """Test resume when no checkpoint exists (fresh start)."""
    run_dir = tmp_path / "run-123"
    run_dir.mkdir()

    target_workers = ["worker1", "worker2", "worker3"]
    result = resume_run(run_dir, target_workers)

    assert result.run_id == "unknown"
    assert result.resumed_from_state == "none"
    assert result.checkpoint_loaded == "none"
    assert result.workers_to_rerun == target_workers
    assert result.success is True


def test_resume_run_from_checkpoint(tmp_path):
    """Test successful resume from checkpoint."""
    run_dir = tmp_path / "run-123"
    run_dir.mkdir()

    # Create initial state
    create_test_snapshot(run_dir, "run-123", "in_progress", ["worker1", "worker2"])
    create_test_events(run_dir, [
        {"event_type": "worker_started", "worker": "worker1"},
        {"event_type": "worker_completed", "worker": "worker1"},
        {"event_type": "worker_started", "worker": "worker2"},
        {"event_type": "worker_completed", "worker": "worker2"},
    ])

    # Create checkpoint
    checkpoint = create_checkpoint(run_dir)

    # Resume
    target_workers = ["worker1", "worker2", "worker3", "worker4"]
    result = resume_run(run_dir, target_workers)

    assert result.run_id == "run-123"
    assert result.resumed_from_state == "in_progress"
    assert result.checkpoint_loaded == checkpoint.checkpoint_id
    assert set(result.workers_to_rerun) == {"worker3", "worker4"}
    assert result.success is True


def test_resume_run_all_workers_complete(tmp_path):
    """Test resume when all workers already complete."""
    run_dir = tmp_path / "run-123"
    run_dir.mkdir()

    create_test_snapshot(run_dir, "run-123", "completed", ["worker1", "worker2"])
    create_checkpoint(run_dir)

    target_workers = ["worker1", "worker2"]
    result = resume_run(run_dir, target_workers)

    assert result.workers_to_rerun == []
    assert result.success is True


def test_resume_run_partial_completion(tmp_path):
    """Test resume with partial worker completion."""
    run_dir = tmp_path / "run-123"
    run_dir.mkdir()

    # Only worker1 completed
    create_test_snapshot(run_dir, "run-123", "in_progress", ["worker1"])
    create_checkpoint(run_dir)

    target_workers = ["worker1", "worker2", "worker3"]
    result = resume_run(run_dir, target_workers)

    assert result.workers_to_rerun == ["worker2", "worker3"]


def test_resume_run_no_target_workers(tmp_path):
    """Test resume with no target workers specified."""
    run_dir = tmp_path / "run-123"
    run_dir.mkdir()

    create_test_snapshot(run_dir, "run-123", "in_progress", ["worker1"])
    create_checkpoint(run_dir)

    result = resume_run(run_dir, target_workers=None)

    assert result.workers_to_rerun == []
    assert result.success is True


def test_resume_run_missing_snapshot_raises(tmp_path):
    """Test resume fails if checkpoint snapshot is missing."""
    run_dir = tmp_path / "run-123"
    run_dir.mkdir()

    # Create checkpoint with invalid snapshot path
    checkpoints_dir = run_dir / "checkpoints" / "20250128_120000"
    checkpoints_dir.mkdir(parents=True)

    checkpoint_data = {
        "checkpoint_id": "20250128_120000",
        "run_id": "run-123",
        "created_at": "2025-01-28T12:00:00+00:00",
        "run_state": "in_progress",
        "completed_workers": [],
        "snapshot_path": str(checkpoints_dir / "snapshot.json"),
        "events_count": 0
    }

    with open(checkpoints_dir / "checkpoint.json", "w", encoding="utf-8") as f:
        json.dump(checkpoint_data, f)

    # Don't create snapshot.json

    with pytest.raises(FileNotFoundError):
        resume_run(run_dir, ["worker1"])


def test_replay_events_no_events_file(tmp_path):
    """Test event replay with no events file."""
    run_dir = tmp_path / "run-123"
    run_dir.mkdir()

    count = replay_events(run_dir, from_count=0)

    assert count == 0


def test_replay_events_from_beginning(tmp_path):
    """Test replaying all events from beginning."""
    run_dir = tmp_path / "run-123"
    run_dir.mkdir()

    events = [
        {"event_type": "worker_started", "worker": "worker1"},
        {"event_type": "worker_completed", "worker": "worker1"},
        {"event_type": "worker_started", "worker": "worker2"},
    ]
    create_test_events(run_dir, events)

    count = replay_events(run_dir, from_count=0)

    assert count == 3


def test_replay_events_from_checkpoint(tmp_path):
    """Test replaying only new events after checkpoint."""
    run_dir = tmp_path / "run-123"
    run_dir.mkdir()

    events = [
        {"event_type": "worker_started", "worker": "worker1"},
        {"event_type": "worker_completed", "worker": "worker1"},
        {"event_type": "worker_started", "worker": "worker2"},
        {"event_type": "worker_completed", "worker": "worker2"},
        {"event_type": "worker_started", "worker": "worker3"},
    ]
    create_test_events(run_dir, events)

    # Checkpoint captured first 2 events
    count = replay_events(run_dir, from_count=2)

    assert count == 3  # Only events 3, 4, 5


def test_replay_events_invalid_json(tmp_path):
    """Test event replay handles invalid JSON gracefully."""
    run_dir = tmp_path / "run-123"
    run_dir.mkdir()

    events_path = run_dir / "events.ndjson"
    with open(events_path, "w", encoding="utf-8") as f:
        f.write('{"valid": "json"}\n')
        f.write('invalid json line\n')
        f.write('{"another": "valid"}\n')

    # Should skip invalid line but continue
    count = replay_events(run_dir, from_count=0)

    assert count == 2  # Only valid events counted


def test_get_incomplete_workers_no_checkpoint(tmp_path):
    """Test getting incomplete workers with no checkpoint."""
    run_dir = tmp_path / "run-123"
    run_dir.mkdir()

    all_workers = ["worker1", "worker2", "worker3"]
    incomplete = get_incomplete_workers(run_dir, all_workers)

    assert incomplete == all_workers


def test_get_incomplete_workers_partial_completion(tmp_path):
    """Test getting incomplete workers with partial completion."""
    run_dir = tmp_path / "run-123"
    run_dir.mkdir()

    create_test_snapshot(run_dir, "run-123", "in_progress", ["worker1", "worker2"])
    create_checkpoint(run_dir)

    all_workers = ["worker1", "worker2", "worker3", "worker4"]
    incomplete = get_incomplete_workers(run_dir, all_workers)

    assert incomplete == ["worker3", "worker4"]


def test_get_incomplete_workers_all_complete(tmp_path):
    """Test getting incomplete workers when all complete."""
    run_dir = tmp_path / "run-123"
    run_dir.mkdir()

    create_test_snapshot(run_dir, "run-123", "completed", ["worker1", "worker2"])
    create_checkpoint(run_dir)

    all_workers = ["worker1", "worker2"]
    incomplete = get_incomplete_workers(run_dir, all_workers)

    assert incomplete == []


def test_resume_result_dataclass_structure():
    """Test ResumeResult dataclass structure."""
    result = ResumeResult(
        run_id="run-123",
        resumed_from_state="in_progress",
        checkpoint_loaded="20250128_120000",
        workers_to_rerun=["worker2", "worker3"],
        success=True
    )

    assert result.run_id == "run-123"
    assert result.resumed_from_state == "in_progress"
    assert result.checkpoint_loaded == "20250128_120000"
    assert len(result.workers_to_rerun) == 2
    assert result.success is True


def test_resume_run_preserves_run_id(tmp_path):
    """Test that resume preserves original run_id."""
    run_dir = tmp_path / "run-original-123"
    run_dir.mkdir()

    original_run_id = "run-original-123"
    create_test_snapshot(run_dir, original_run_id, "in_progress", ["worker1"])
    create_checkpoint(run_dir)

    result = resume_run(run_dir, ["worker1", "worker2"])

    assert result.run_id == original_run_id


def test_resume_run_worker_order_preserved(tmp_path):
    """Test that resume preserves worker order for rerun."""
    run_dir = tmp_path / "run-123"
    run_dir.mkdir()

    create_test_snapshot(run_dir, "run-123", "in_progress", ["worker2"])
    create_checkpoint(run_dir)

    # Workers in specific order
    target_workers = ["worker1", "worker2", "worker3", "worker4"]
    result = resume_run(run_dir, target_workers)

    # Should maintain order, just exclude completed worker2
    assert result.workers_to_rerun == ["worker1", "worker3", "worker4"]


def test_replay_events_counts_correctly(tmp_path):
    """Test that event replay counts match actual events."""
    run_dir = tmp_path / "run-123"
    run_dir.mkdir()

    # Create exactly 10 events
    events = [{"event_type": f"event_{i}"} for i in range(10)]
    create_test_events(run_dir, events)

    # Replay all
    count = replay_events(run_dir, from_count=0)
    assert count == 10

    # Replay from middle
    count = replay_events(run_dir, from_count=5)
    assert count == 5


def test_resume_run_with_complex_snapshot(tmp_path):
    """Test resume with complex snapshot containing extra fields."""
    run_dir = tmp_path / "run-123"
    run_dir.mkdir()

    snapshot_data = {
        "run_id": "run-123",
        "run_state": "in_progress",
        "completed_workers": ["worker1"],
        "extra_data": {
            "artifacts": ["artifact1.json"],
            "metadata": {"version": "1.0"}
        }
    }

    snapshot_path = run_dir / "snapshot.json"
    with open(snapshot_path, "w", encoding="utf-8") as f:
        json.dump(snapshot_data, f)

    create_checkpoint(run_dir)

    result = resume_run(run_dir, ["worker1", "worker2"])

    assert result.run_id == "run-123"
    assert result.workers_to_rerun == ["worker2"]


def test_get_incomplete_workers_duplicate_workers(tmp_path):
    """Test get_incomplete_workers handles duplicate workers correctly."""
    run_dir = tmp_path / "run-123"
    run_dir.mkdir()

    create_test_snapshot(run_dir, "run-123", "in_progress", ["worker1", "worker1"])
    create_checkpoint(run_dir)

    # Target has duplicates too
    all_workers = ["worker1", "worker1", "worker2"]
    incomplete = get_incomplete_workers(run_dir, all_workers)

    # Should filter out both instances of worker1
    assert incomplete == ["worker2"]


def test_resume_run_empty_completed_workers(tmp_path):
    """Test resume with empty completed workers list."""
    run_dir = tmp_path / "run-123"
    run_dir.mkdir()

    create_test_snapshot(run_dir, "run-123", "initializing", [])
    create_checkpoint(run_dir)

    target_workers = ["worker1", "worker2"]
    result = resume_run(run_dir, target_workers)

    assert result.workers_to_rerun == target_workers
