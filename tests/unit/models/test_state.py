"""Tests for State models (Snapshot, WorkItem, ArtifactIndexEntry).

Validates:
- Snapshot serialization matches snapshot.schema.json
- WorkItem and ArtifactIndexEntry nested serialization
- State constants defined correctly
"""

import pytest

from src.launch.models.state import (
    RUN_STATE_CREATED,
    RUN_STATE_DONE,
    SECTION_STATE_DRAFTED,
    WORK_ITEM_STATUS_FINISHED,
    WORK_ITEM_STATUS_QUEUED,
    ArtifactIndexEntry,
    Snapshot,
    WorkItem,
)


def test_artifact_index_entry_minimal():
    """Test ArtifactIndexEntry with only required fields."""
    entry = ArtifactIndexEntry(
        path="artifacts/test.json",
        sha256="a" * 64,
        schema_id="test.schema.json",
        writer_worker="W1",
    )

    data = entry.to_dict()

    assert data["path"] == "artifacts/test.json"
    assert data["sha256"] == "a" * 64
    assert data["schema_id"] == "test.schema.json"
    assert data["writer_worker"] == "W1"
    assert "ts" not in data
    assert "event_id" not in data


def test_artifact_index_entry_with_optional():
    """Test ArtifactIndexEntry with optional fields."""
    entry = ArtifactIndexEntry(
        path="artifacts/test.json",
        sha256="b" * 64,
        schema_id="test.schema.json",
        writer_worker="W2",
        ts="2026-01-28T00:00:00Z",
        event_id="evt-123",
    )

    data = entry.to_dict()
    assert data["ts"] == "2026-01-28T00:00:00Z"
    assert data["event_id"] == "evt-123"


def test_work_item_minimal():
    """Test WorkItem with only required fields."""
    item = WorkItem(
        work_item_id="wi-001",
        worker="W1",
        attempt=1,
        status=WORK_ITEM_STATUS_QUEUED,
        inputs=["input1.json"],
        outputs=["output1.json"],
    )

    data = item.to_dict()

    assert data["work_item_id"] == "wi-001"
    assert data["worker"] == "W1"
    assert data["attempt"] == 1
    assert data["status"] == WORK_ITEM_STATUS_QUEUED
    assert data["inputs"] == ["input1.json"]
    assert data["outputs"] == ["output1.json"]
    assert "scope_key" not in data
    assert "started_at" not in data
    assert "finished_at" not in data
    assert "error" not in data


def test_work_item_with_timestamps():
    """Test WorkItem with timestamps and error."""
    item = WorkItem(
        work_item_id="wi-002",
        worker="W2",
        attempt=2,
        status=WORK_ITEM_STATUS_FINISHED,
        inputs=["input.json"],
        outputs=["output.json"],
        scope_key="section_1",
        started_at="2026-01-28T10:00:00Z",
        finished_at="2026-01-28T10:05:00Z",
    )

    data = item.to_dict()
    assert data["scope_key"] == "section_1"
    assert data["started_at"] == "2026-01-28T10:00:00Z"
    assert data["finished_at"] == "2026-01-28T10:05:00Z"


def test_work_item_round_trip():
    """Test WorkItem serialization round-trip."""
    original = WorkItem(
        work_item_id="wi-003",
        worker="W3",
        attempt=1,
        status="running",
        inputs=["a.json", "b.json"],
        outputs=["c.json"],
        scope_key="test",
    )

    data = original.to_dict()
    restored = WorkItem.from_dict(data)

    assert restored.work_item_id == original.work_item_id
    assert restored.worker == original.worker
    assert restored.inputs == original.inputs
    assert restored.outputs == original.outputs


def test_snapshot_minimal():
    """Test Snapshot with minimal data."""
    snapshot = Snapshot(
        schema_version="v1.0",
        run_id="run-123",
        run_state=RUN_STATE_CREATED,
        artifacts_index={},
        work_items=[],
        issues=[],
    )

    data = snapshot.to_dict()

    assert data["schema_version"] == "v1.0"
    assert data["run_id"] == "run-123"
    assert data["run_state"] == RUN_STATE_CREATED
    assert data["artifacts_index"] == {}
    assert data["work_items"] == []
    assert data["issues"] == []
    assert data["section_states"] == {}


def test_snapshot_with_artifacts_and_work_items():
    """Test Snapshot with artifacts and work items."""
    entry = ArtifactIndexEntry(
        path="artifacts/facts.json",
        sha256="c" * 64,
        schema_id="product_facts.schema.json",
        writer_worker="W2",
    )

    item = WorkItem(
        work_item_id="wi-001",
        worker="W1",
        attempt=1,
        status="finished",
        inputs=["run_config.json"],
        outputs=["facts.json"],
    )

    snapshot = Snapshot(
        schema_version="v1.0",
        run_id="run-456",
        run_state=RUN_STATE_DONE,
        artifacts_index={"facts": entry},
        work_items=[item],
        issues=[],
        section_states={"products": SECTION_STATE_DRAFTED},
    )

    data = snapshot.to_dict()

    assert "facts" in data["artifacts_index"]
    assert len(data["work_items"]) == 1
    assert data["section_states"]["products"] == SECTION_STATE_DRAFTED


def test_snapshot_round_trip():
    """Test Snapshot complete serialization round-trip."""
    entry1 = ArtifactIndexEntry("path1.json", "d" * 64, "schema1", "W1")
    entry2 = ArtifactIndexEntry("path2.json", "e" * 64, "schema2", "W2")

    item1 = WorkItem("wi-1", "W1", 1, "finished", ["in1"], ["out1"])
    item2 = WorkItem("wi-2", "W2", 1, "queued", ["in2"], ["out2"])

    original = Snapshot(
        schema_version="v1.0",
        run_id="run-789",
        run_state="PLAN_READY",
        artifacts_index={"art1": entry1, "art2": entry2},
        work_items=[item1, item2],
        issues=[{"issue_id": "i1", "gate": "G1", "severity": "warn", "message": "test", "status": "OPEN"}],
        section_states={"docs": "DRAFTED"},
    )

    data = original.to_dict()
    restored = Snapshot.from_dict(data)

    assert restored.schema_version == original.schema_version
    assert restored.run_id == original.run_id
    assert restored.run_state == original.run_state
    assert len(restored.artifacts_index) == 2
    assert len(restored.work_items) == 2
    assert len(restored.issues) == 1
    assert restored.section_states == {"docs": "DRAFTED"}


def test_state_constants():
    """Test that state constants are defined."""
    assert RUN_STATE_CREATED == "CREATED"
    assert RUN_STATE_DONE == "DONE"
    assert SECTION_STATE_DRAFTED == "DRAFTED"
    assert WORK_ITEM_STATUS_QUEUED == "queued"
    assert WORK_ITEM_STATUS_FINISHED == "finished"
