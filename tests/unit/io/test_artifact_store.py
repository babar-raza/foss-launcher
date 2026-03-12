"""Tests for ArtifactStore."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from launcher.io.artifact_store import ArtifactStore


@pytest.fixture
def store(tmp_path: Path) -> ArtifactStore:
    run_dir = tmp_path / "runs" / "test-run"
    run_dir.mkdir(parents=True)
    return ArtifactStore(run_dir=run_dir)


class TestLoadJson:
    def test_load_valid(self, store: ArtifactStore) -> None:
        data = {"key": "value"}
        fpath = store.file_path("test.json")
        fpath.write_text(json.dumps(data), encoding="utf-8")
        assert store.load_json("test.json", validate_schema=False) == data

    def test_load_missing_raises(self, store: ArtifactStore) -> None:
        with pytest.raises(FileNotFoundError, match="Required file not found"):
            store.load_json("nonexistent.json", validate_schema=False)

    def test_load_or_default_missing(self, store: ArtifactStore) -> None:
        result = store.load_json_or_default("missing.json", {"default": True}, validate_schema=False)
        assert result == {"default": True}

    def test_load_or_default_exists(self, store: ArtifactStore) -> None:
        fpath = store.file_path("exists.json")
        fpath.write_text('{"real": true}', encoding="utf-8")
        result = store.load_json_or_default("exists.json", {"default": True}, validate_schema=False)
        assert result == {"real": True}


class TestWriteJson:
    def test_write_basic(self, store: ArtifactStore) -> None:
        entry = store.write_json("output.json", {"result": "ok"})
        assert "path" in entry
        assert "sha256" in entry
        assert "size" in entry
        assert entry["path"] == "output.json"

        loaded = json.loads(store.file_path("output.json").read_text(encoding="utf-8"))
        assert loaded == {"result": "ok"}

    def test_write_deterministic(self, store: ArtifactStore) -> None:
        data = {"z": 1, "a": 2, "m": 3}
        e1 = store.write_json("d1.json", data)
        e2 = store.write_json("d2.json", data)
        assert e1["sha256"] == e2["sha256"]

    def test_write_creates_subdirs(self, store: ArtifactStore) -> None:
        entry = store.write_json("sub/dir/out.json", {"nested": True})
        assert store.file_path("sub/dir/out.json").exists()


class TestEmitEvent:
    def test_emit_creates_ndjson(self, store: ArtifactStore) -> None:
        store.emit_event("worker_started", {"worker": "Understand"}, worker="Understand")
        events_file = store.run_dir / "events.ndjson"
        assert events_file.exists()
        lines = events_file.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 1
        event = json.loads(lines[0])
        assert event["event_type"] == "worker_started"
        assert event["worker"] == "Understand"

    def test_emit_appends(self, store: ArtifactStore) -> None:
        store.emit_event("event_a", {})
        store.emit_event("event_b", {})
        events_file = store.run_dir / "events.ndjson"
        lines = events_file.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 2

    def test_emit_event_has_required_fields(self, store: ArtifactStore) -> None:
        store.emit_event("test_type", {"detail": "val"}, run_id="r_test")
        events_file = store.run_dir / "events.ndjson"
        event = json.loads(events_file.read_text(encoding="utf-8").strip())
        for field in ("event_id", "event_type", "run_id", "timestamp", "data"):
            assert field in event
        assert event["run_id"] == "r_test"


class TestExists:
    def test_exists_true(self, store: ArtifactStore) -> None:
        store.file_path("present.json").write_text("{}", encoding="utf-8")
        assert store.exists("present.json") is True

    def test_exists_false(self, store: ArtifactStore) -> None:
        assert store.exists("absent.json") is False


class TestFilePath:
    def test_file_path(self, store: ArtifactStore) -> None:
        p = store.file_path("some/artifact.json")
        assert p == store.run_dir / "some/artifact.json"
