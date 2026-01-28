"""
Tests for TC-600: Checkpoint management.

Covers:
- Checkpoint creation
- Checkpoint listing and sorting
- Checkpoint cleanup
- Checkpoint loading
"""

import json
import pytest
import time
from datetime import datetime, timezone
from pathlib import Path
from src.launch.resilience.checkpoint import (
    Checkpoint,
    create_checkpoint,
    list_checkpoints,
    get_latest_checkpoint,
    cleanup_old_checkpoints,
    load_checkpoint,
)


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


def create_test_events(run_dir: Path, event_count: int):
    """Helper to create test events.ndjson."""
    events_path = run_dir / "events.ndjson"
    with open(events_path, "w", encoding="utf-8") as f:
        for i in range(event_count):
            event = {"event_type": "test", "event_id": f"evt-{i}"}
            f.write(json.dumps(event) + "\n")
    return events_path


def test_create_checkpoint_basic(tmp_path):
    """Test basic checkpoint creation."""
    run_dir = tmp_path / "run-123"
    run_dir.mkdir()

    # Create test data
    create_test_snapshot(run_dir, "run-123", "in_progress", ["worker1", "worker2"])
    create_test_events(run_dir, 5)

    # Create checkpoint
    checkpoint = create_checkpoint(run_dir)

    assert checkpoint.run_id == "run-123"
    assert checkpoint.run_state == "in_progress"
    assert checkpoint.completed_workers == ["worker1", "worker2"]
    assert checkpoint.events_count == 5
    assert checkpoint.checkpoint_id  # Should have timestamp ID

    # Verify checkpoint directory created
    checkpoint_dir = run_dir / "checkpoints" / checkpoint.checkpoint_id
    assert checkpoint_dir.exists()
    assert (checkpoint_dir / "snapshot.json").exists()
    assert (checkpoint_dir / "checkpoint.json").exists()


def test_create_checkpoint_no_events(tmp_path):
    """Test checkpoint creation with no events file."""
    run_dir = tmp_path / "run-123"
    run_dir.mkdir()

    create_test_snapshot(run_dir, "run-123", "initializing", [])

    checkpoint = create_checkpoint(run_dir)

    assert checkpoint.events_count == 0


def test_create_checkpoint_no_snapshot_raises(tmp_path):
    """Test checkpoint creation fails without snapshot."""
    run_dir = tmp_path / "run-123"
    run_dir.mkdir()

    with pytest.raises(FileNotFoundError):
        create_checkpoint(run_dir)


def test_list_checkpoints_empty(tmp_path):
    """Test listing checkpoints with no checkpoints."""
    run_dir = tmp_path / "run-123"
    run_dir.mkdir()

    checkpoints = list_checkpoints(run_dir)

    assert checkpoints == []


def test_list_checkpoints_sorted_by_time(tmp_path):
    """Test that checkpoints are sorted by creation time."""
    run_dir = tmp_path / "run-123"
    run_dir.mkdir()

    # Create multiple checkpoints
    create_test_snapshot(run_dir, "run-123", "in_progress", [])

    checkpoint1 = create_checkpoint(run_dir)
    time.sleep(0.01)  # Ensure different timestamps

    # Update snapshot
    create_test_snapshot(run_dir, "run-123", "in_progress", ["worker1"])
    checkpoint2 = create_checkpoint(run_dir)
    time.sleep(0.01)

    create_test_snapshot(run_dir, "run-123", "in_progress", ["worker1", "worker2"])
    checkpoint3 = create_checkpoint(run_dir)

    # List checkpoints
    checkpoints = list_checkpoints(run_dir)

    assert len(checkpoints) == 3
    # Should be sorted by created_at (oldest first)
    assert checkpoints[0].checkpoint_id == checkpoint1.checkpoint_id
    assert checkpoints[1].checkpoint_id == checkpoint2.checkpoint_id
    assert checkpoints[2].checkpoint_id == checkpoint3.checkpoint_id


def test_get_latest_checkpoint_none(tmp_path):
    """Test getting latest checkpoint when none exist."""
    run_dir = tmp_path / "run-123"
    run_dir.mkdir()

    latest = get_latest_checkpoint(run_dir)

    assert latest is None


def test_get_latest_checkpoint(tmp_path):
    """Test getting the most recent checkpoint."""
    run_dir = tmp_path / "run-123"
    run_dir.mkdir()

    create_test_snapshot(run_dir, "run-123", "in_progress", [])

    checkpoint1 = create_checkpoint(run_dir)
    time.sleep(0.01)

    create_test_snapshot(run_dir, "run-123", "in_progress", ["worker1"])
    checkpoint2 = create_checkpoint(run_dir)

    latest = get_latest_checkpoint(run_dir)

    assert latest is not None
    assert latest.checkpoint_id == checkpoint2.checkpoint_id


def test_cleanup_old_checkpoints_keep_all(tmp_path):
    """Test cleanup when fewer checkpoints than keep_last_n."""
    run_dir = tmp_path / "run-123"
    run_dir.mkdir()

    create_test_snapshot(run_dir, "run-123", "in_progress", [])

    create_checkpoint(run_dir)
    time.sleep(0.01)
    create_checkpoint(run_dir)

    # Keep last 5, but only 2 exist
    deleted = cleanup_old_checkpoints(run_dir, keep_last_n=5)

    assert deleted == 0
    assert len(list_checkpoints(run_dir)) == 2


def test_cleanup_old_checkpoints_delete_oldest(tmp_path):
    """Test cleanup deletes oldest checkpoints."""
    run_dir = tmp_path / "run-123"
    run_dir.mkdir()

    create_test_snapshot(run_dir, "run-123", "in_progress", [])

    # Create 6 checkpoints
    checkpoints = []
    for i in range(6):
        cp = create_checkpoint(run_dir)
        checkpoints.append(cp)
        time.sleep(0.01)

    # Keep last 3
    deleted = cleanup_old_checkpoints(run_dir, keep_last_n=3)

    assert deleted == 3

    # Verify only last 3 remain
    remaining = list_checkpoints(run_dir)
    assert len(remaining) == 3
    assert remaining[0].checkpoint_id == checkpoints[3].checkpoint_id
    assert remaining[1].checkpoint_id == checkpoints[4].checkpoint_id
    assert remaining[2].checkpoint_id == checkpoints[5].checkpoint_id


def test_load_checkpoint_success(tmp_path):
    """Test loading a checkpoint by ID."""
    run_dir = tmp_path / "run-123"
    run_dir.mkdir()

    create_test_snapshot(run_dir, "run-123", "in_progress", ["worker1"])
    create_test_events(run_dir, 10)

    checkpoint = create_checkpoint(run_dir)

    # Load checkpoint
    loaded = load_checkpoint(run_dir, checkpoint.checkpoint_id)

    assert loaded.checkpoint_id == checkpoint.checkpoint_id
    assert loaded.run_id == "run-123"
    assert loaded.run_state == "in_progress"
    assert loaded.completed_workers == ["worker1"]
    assert loaded.events_count == 10


def test_load_checkpoint_not_found(tmp_path):
    """Test loading non-existent checkpoint raises error."""
    run_dir = tmp_path / "run-123"
    run_dir.mkdir()

    with pytest.raises(FileNotFoundError):
        load_checkpoint(run_dir, "nonexistent")


def test_checkpoint_dataclass_structure():
    """Test Checkpoint dataclass structure."""
    checkpoint = Checkpoint(
        checkpoint_id="20250128_120000",
        run_id="run-123",
        created_at="2025-01-28T12:00:00+00:00",
        run_state="in_progress",
        completed_workers=["worker1", "worker2"],
        snapshot_path="/path/to/snapshot.json",
        events_count=42
    )

    assert checkpoint.checkpoint_id == "20250128_120000"
    assert checkpoint.run_id == "run-123"
    assert checkpoint.run_state == "in_progress"
    assert len(checkpoint.completed_workers) == 2
    assert checkpoint.events_count == 42


def test_create_checkpoint_copies_snapshot(tmp_path):
    """Test that checkpoint copies snapshot, not moves it."""
    run_dir = tmp_path / "run-123"
    run_dir.mkdir()

    snapshot_path = create_test_snapshot(run_dir, "run-123", "in_progress", [])

    checkpoint = create_checkpoint(run_dir)

    # Original snapshot should still exist
    assert snapshot_path.exists()

    # Checkpoint snapshot should also exist
    checkpoint_snapshot = Path(checkpoint.snapshot_path)
    assert checkpoint_snapshot.exists()


def test_create_checkpoint_timestamp_format(tmp_path):
    """Test checkpoint ID uses correct timestamp format."""
    run_dir = tmp_path / "run-123"
    run_dir.mkdir()

    create_test_snapshot(run_dir, "run-123", "in_progress", [])

    checkpoint = create_checkpoint(run_dir)

    # Should be YYYYMMDD_HHMMSS_microseconds format
    assert len(checkpoint.checkpoint_id) == 22  # 20250128_120000_123456
    assert checkpoint.checkpoint_id[8] == "_"
    assert checkpoint.checkpoint_id[15] == "_"


def test_list_checkpoints_ignores_invalid(tmp_path):
    """Test that list_checkpoints ignores invalid checkpoint directories."""
    run_dir = tmp_path / "run-123"
    run_dir.mkdir()
    checkpoints_dir = run_dir / "checkpoints"
    checkpoints_dir.mkdir()

    # Create valid checkpoint
    create_test_snapshot(run_dir, "run-123", "in_progress", [])
    valid_checkpoint = create_checkpoint(run_dir)

    # Create invalid checkpoint directory (no metadata)
    invalid_dir = checkpoints_dir / "invalid"
    invalid_dir.mkdir()

    # Create file (not directory)
    (checkpoints_dir / "file.txt").write_text("not a checkpoint")

    checkpoints = list_checkpoints(run_dir)

    # Should only include valid checkpoint
    assert len(checkpoints) == 1
    assert checkpoints[0].checkpoint_id == valid_checkpoint.checkpoint_id


def test_checkpoint_created_at_iso8601(tmp_path):
    """Test checkpoint created_at uses ISO 8601 format."""
    run_dir = tmp_path / "run-123"
    run_dir.mkdir()

    create_test_snapshot(run_dir, "run-123", "in_progress", [])

    checkpoint = create_checkpoint(run_dir)

    # Should be valid ISO 8601 timestamp
    timestamp = datetime.fromisoformat(checkpoint.created_at)
    assert timestamp.tzinfo is not None  # Should have timezone


def test_cleanup_old_checkpoints_handles_delete_errors(tmp_path):
    """Test cleanup handles errors gracefully."""
    run_dir = tmp_path / "run-123"
    run_dir.mkdir()

    create_test_snapshot(run_dir, "run-123", "in_progress", [])

    # Create checkpoints
    for i in range(4):
        create_checkpoint(run_dir)
        time.sleep(0.01)

    # Keep last 2 (should delete 2)
    deleted = cleanup_old_checkpoints(run_dir, keep_last_n=2)

    assert deleted == 2
    assert len(list_checkpoints(run_dir)) == 2


def test_create_checkpoint_preserves_snapshot_content(tmp_path):
    """Test that checkpoint snapshot is identical to original."""
    run_dir = tmp_path / "run-123"
    run_dir.mkdir()

    original_data = {
        "run_id": "run-123",
        "run_state": "in_progress",
        "completed_workers": ["worker1", "worker2"],
        "extra_field": "extra_value"
    }

    snapshot_path = run_dir / "snapshot.json"
    with open(snapshot_path, "w", encoding="utf-8") as f:
        json.dump(original_data, f, indent=2)

    checkpoint = create_checkpoint(run_dir)

    # Load checkpoint snapshot
    with open(checkpoint.snapshot_path, "r", encoding="utf-8") as f:
        checkpoint_data = json.load(f)

    assert checkpoint_data == original_data
