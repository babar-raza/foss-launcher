"""Tests for snapshot persistence, replay, and event reducers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from launcher.models.event import (
    EVENT_ARTIFACT_WRITTEN,
    EVENT_ISSUE_OPENED,
    EVENT_ISSUE_RESOLVED,
    EVENT_RUN_CREATED,
    EVENT_RUN_STATE_CHANGED,
    EVENT_WORK_ITEM_FINISHED,
    EVENT_WORK_ITEM_QUEUED,
    EVENT_WORK_ITEM_STARTED,
    Event,
)
from launcher.models.state import (
    WORK_ITEM_STATUS_FINISHED,
    WORK_ITEM_STATUS_QUEUED,
    WORK_ITEM_STATUS_RUNNING,
    ArtifactIndexEntry,
    Snapshot,
    WorkItem,
)
from launcher.state.snapshot_manager import (
    apply_event_reducer,
    create_initial_snapshot,
    read_snapshot,
    replay_events,
    write_snapshot,
)


# ---------------------------------------------------------------------------
# Model construction tests
# ---------------------------------------------------------------------------


class TestSnapshotModel:
    def test_default_construction(self):
        s = Snapshot()
        assert s.run_state == "CREATED"
        assert s.schema_version == "1.0.0"
        assert s.artifacts_index == {}
        assert s.work_items == []
        assert s.issues == []
        assert s.section_states == {}

    def test_to_dict_round_trip(self):
        s = Snapshot(run_id="r_test", run_state="RUNNING")
        d = s.to_dict()
        s2 = Snapshot.from_dict(d)
        assert s2.run_id == "r_test"
        assert s2.run_state == "RUNNING"
        assert s2.to_dict() == d

    def test_from_dict_empty(self):
        s = Snapshot.from_dict({})
        assert s.run_state == "CREATED"
        assert s.run_id == ""

    def test_mutable(self):
        s = Snapshot()
        s.run_state = "RUNNING"
        assert s.run_state == "RUNNING"


class TestWorkItemModel:
    def test_default_status(self):
        w = WorkItem()
        assert w.status == WORK_ITEM_STATUS_QUEUED

    def test_mutable(self):
        w = WorkItem(work_item_id="w1")
        w.status = WORK_ITEM_STATUS_RUNNING
        assert w.status == WORK_ITEM_STATUS_RUNNING


class TestArtifactIndexEntryModel:
    def test_all_fields(self):
        e = ArtifactIndexEntry(
            path="a.json",
            sha256="abc123",
            schema_id="schema.json",
            writer_worker="understand",
            ts="2026-03-07T00:00:00Z",
            event_id="evt-1",
        )
        d = e.model_dump(mode="json")
        assert d["path"] == "a.json"
        assert d["sha256"] == "abc123"
        assert d["writer_worker"] == "understand"
        assert d["ts"] == "2026-03-07T00:00:00Z"
        assert d["event_id"] == "evt-1"


# ---------------------------------------------------------------------------
# Event alias normalization tests
# ---------------------------------------------------------------------------


class TestEventAliases:
    def test_legacy_aliases(self):
        """Event(ts=, type=, payload=) maps to timestamp, event_type, data."""
        e = Event(
            event_id="e1",
            run_id="r1",
            ts="2026-01-01T00:00:00Z",
            type="run_created",
            payload={"key": "val"},
        )
        assert e.timestamp == "2026-01-01T00:00:00Z"
        assert e.event_type == "run_created"
        assert e.data == {"key": "val"}

    def test_canonical_fields_no_double_map(self):
        """Direct field names work without alias interference."""
        e = Event(
            event_id="e2",
            run_id="r1",
            timestamp="2026-01-01T00:00:00Z",
            event_type="worker_started",
            data={"w": "intake"},
        )
        assert e.timestamp == "2026-01-01T00:00:00Z"
        assert e.event_type == "worker_started"
        assert e.data == {"w": "intake"}

    def test_compat_properties(self):
        """Properties type, payload, ts read back correctly."""
        e = Event(event_type="gate_executed", timestamp="T1", data={"g": 1})
        assert e.type == "gate_executed"
        assert e.payload == {"g": 1}
        assert e.ts == "T1"

    def test_from_dict_artifact_store_format(self):
        """Parse a dict shaped like ArtifactStore.emit_event() output."""
        raw = {
            "event_id": "uuid-1",
            "event_type": "worker_started",
            "run_id": "r_abc",
            "timestamp": "2026-03-07T00:00:00+00:00",
            "worker": "understand",
            "data": {"phase": "A_scout"},
        }
        e = Event.from_dict(raw)
        assert e.event_id == "uuid-1"
        assert e.event_type == "worker_started"
        assert e.data["phase"] == "A_scout"

    def test_to_dict_no_none_fields(self):
        """to_dict strips None optional fields."""
        e = Event(event_id="e1", event_type="run_created", run_id="r1", timestamp="T")
        d = e.to_dict()
        assert "event_hash" not in d
        assert "prev_hash" not in d


# ---------------------------------------------------------------------------
# Snapshot manager function tests
# ---------------------------------------------------------------------------


class TestCreateInitialSnapshot:
    def test_creates_with_run_id(self):
        s = create_initial_snapshot("r_test_123")
        assert s.run_id == "r_test_123"
        assert s.run_state == "CREATED"
        assert s.artifacts_index == {}
        assert s.work_items == []


class TestWriteReadSnapshot:
    def test_round_trip(self, tmp_path: Path):
        snap = Snapshot(
            run_id="r_rt",
            run_state="RUNNING",
            artifacts_index={
                "bundle.json": ArtifactIndexEntry(path="bundle.json", sha256="abc")
            },
            work_items=[WorkItem(work_item_id="w1", worker="intake")],
        )
        f = tmp_path / "snapshot.json"
        write_snapshot(f, snap)
        loaded = read_snapshot(f)
        assert loaded.run_id == "r_rt"
        assert loaded.run_state == "RUNNING"
        assert "bundle.json" in loaded.artifacts_index
        assert loaded.artifacts_index["bundle.json"].sha256 == "abc"
        assert len(loaded.work_items) == 1
        assert loaded.work_items[0].work_item_id == "w1"

    def test_read_missing_raises(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            read_snapshot(tmp_path / "nonexistent.json")


# ---------------------------------------------------------------------------
# Event reducer tests
# ---------------------------------------------------------------------------


class TestApplyEventReducer:
    def _make_event(self, event_type: str, data: dict) -> Event:
        return Event(
            event_id="evt-1",
            event_type=event_type,
            run_id="r_test",
            timestamp="2026-03-07T00:00:00Z",
            data=data,
        )

    def test_run_created(self):
        snap = create_initial_snapshot("r_test")
        event = self._make_event(EVENT_RUN_CREATED, {"run_id": "r_test"})
        result = apply_event_reducer(snap, event)
        assert result.run_state == "CREATED"  # unchanged

    def test_run_state_changed(self):
        snap = create_initial_snapshot("r_test")
        event = self._make_event(EVENT_RUN_STATE_CHANGED, {"new_state": "RUNNING"})
        result = apply_event_reducer(snap, event)
        assert result.run_state == "RUNNING"

    def test_artifact_written(self):
        snap = create_initial_snapshot("r_test")
        event = self._make_event(
            EVENT_ARTIFACT_WRITTEN,
            {"name": "bundle.json", "path": "bundle.json", "sha256": "abc123"},
        )
        result = apply_event_reducer(snap, event)
        assert "bundle.json" in result.artifacts_index
        assert result.artifacts_index["bundle.json"].sha256 == "abc123"

    def test_artifact_written_no_name_logs_warning(self):
        snap = create_initial_snapshot("r_test")
        event = self._make_event(EVENT_ARTIFACT_WRITTEN, {"sha256": "abc"})
        result = apply_event_reducer(snap, event)
        assert len(result.artifacts_index) == 0  # skipped

    def test_work_item_queued(self):
        snap = create_initial_snapshot("r_test")
        event = self._make_event(
            EVENT_WORK_ITEM_QUEUED,
            {"work_item_id": "wi-1", "worker": "understand", "attempt": 1},
        )
        result = apply_event_reducer(snap, event)
        assert len(result.work_items) == 1
        assert result.work_items[0].status == WORK_ITEM_STATUS_QUEUED

    def test_work_item_started(self):
        snap = create_initial_snapshot("r_test")
        snap.work_items.append(WorkItem(work_item_id="wi-1", worker="understand"))
        event = self._make_event(
            EVENT_WORK_ITEM_STARTED, {"work_item_id": "wi-1"}
        )
        result = apply_event_reducer(snap, event)
        assert result.work_items[0].status == WORK_ITEM_STATUS_RUNNING

    def test_work_item_finished(self):
        snap = create_initial_snapshot("r_test")
        snap.work_items.append(
            WorkItem(work_item_id="wi-1", worker="understand", status=WORK_ITEM_STATUS_RUNNING)
        )
        event = self._make_event(
            EVENT_WORK_ITEM_FINISHED, {"work_item_id": "wi-1"}
        )
        result = apply_event_reducer(snap, event)
        assert result.work_items[0].status == WORK_ITEM_STATUS_FINISHED

    def test_issue_opened(self):
        snap = create_initial_snapshot("r_test")
        event = self._make_event(
            EVENT_ISSUE_OPENED,
            {"issue": {"issue_id": "ISS-1", "severity": "error", "message": "bad"}},
        )
        result = apply_event_reducer(snap, event)
        assert len(result.issues) == 1
        assert result.issues[0]["issue_id"] == "ISS-1"

    def test_issue_resolved(self):
        snap = create_initial_snapshot("r_test")
        snap.issues.append({"issue_id": "ISS-1", "status": "OPEN"})
        event = self._make_event(
            EVENT_ISSUE_RESOLVED, {"issue_id": "ISS-1"}
        )
        result = apply_event_reducer(snap, event)
        assert result.issues[0]["status"] == "RESOLVED"


# ---------------------------------------------------------------------------
# Replay tests
# ---------------------------------------------------------------------------


class TestReplayEvents:
    def test_replay_produces_populated_snapshot(self, tmp_path: Path):
        events_file = tmp_path / "events.ndjson"
        events = [
            {
                "event_id": "e1",
                "event_type": "run_created",
                "run_id": "r_replay",
                "timestamp": "2026-03-07T00:00:00Z",
                "worker": "",
                "data": {"run_id": "r_replay"},
            },
            {
                "event_id": "e2",
                "event_type": "run_state_changed",
                "run_id": "r_replay",
                "timestamp": "2026-03-07T00:00:01Z",
                "worker": "",
                "data": {"new_state": "RUNNING"},
            },
            {
                "event_id": "e3",
                "event_type": "artifact_written",
                "run_id": "r_replay",
                "timestamp": "2026-03-07T00:00:02Z",
                "worker": "understand",
                "data": {
                    "name": "understanding_bundle.json",
                    "path": "understanding_bundle.json",
                    "sha256": "deadbeef",
                },
            },
        ]
        with events_file.open("w", encoding="utf-8") as f:
            for evt in events:
                f.write(json.dumps(evt, sort_keys=True) + "\n")

        snap = replay_events(events_file, "r_replay")
        assert snap.run_state == "RUNNING"
        assert "understanding_bundle.json" in snap.artifacts_index
        assert snap.artifacts_index["understanding_bundle.json"].sha256 == "deadbeef"

    def test_replay_empty_events(self, tmp_path: Path):
        events_file = tmp_path / "events.ndjson"
        events_file.write_text("", encoding="utf-8")
        snap = replay_events(events_file, "r_empty")
        assert snap.run_state == "CREATED"
        assert snap.artifacts_index == {}
