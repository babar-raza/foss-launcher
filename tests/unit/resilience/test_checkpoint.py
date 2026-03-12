"""Tests for checkpoint management."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from launcher.resilience.checkpoint import (
    Checkpoint,
    WorkerCheckpoint,
    backup_output_files,
    cleanup_old_checkpoints,
    create_checkpoint,
    get_latest_checkpoint,
    list_checkpoints,
    load_checkpoint,
    load_worker_checkpoint,
    restore_from_backup,
    restore_worker_checkpoint,
    write_worker_checkpoint,
)
from launcher.models.state import ArtifactIndexEntry, Snapshot, WorkItem
from launcher.state.snapshot_manager import write_snapshot


@pytest.fixture
def run_dir(tmp_path: Path) -> Path:
    d = tmp_path / "runs" / "r_test"
    d.mkdir(parents=True)
    return d


@pytest.fixture
def snapshot(run_dir: Path) -> Path:
    snapshot_data = {
        "run_id": "r_test",
        "run_state": "running",
        "completed_workers": ["Intake", "Understand"],
    }
    p = run_dir / "snapshot.json"
    p.write_text(json.dumps(snapshot_data), encoding="utf-8")
    return p


@pytest.fixture
def events(run_dir: Path) -> Path:
    p = run_dir / "events.ndjson"
    p.write_text('{"event":"a"}\n{"event":"b"}\n', encoding="utf-8")
    return p


class TestCreateCheckpoint:
    def test_creates_checkpoint(self, run_dir: Path, snapshot: Path, events: Path) -> None:
        cp = create_checkpoint(run_dir)
        assert isinstance(cp, Checkpoint)
        assert cp.run_id == "r_test"
        assert cp.run_state == "running"
        assert cp.completed_workers == ["Intake", "Understand"]
        assert cp.events_count == 2

    def test_checkpoint_dir_created(self, run_dir: Path, snapshot: Path) -> None:
        cp = create_checkpoint(run_dir)
        cp_dir = run_dir / "checkpoints" / cp.checkpoint_id
        assert cp_dir.exists()
        assert (cp_dir / "snapshot.json").exists()
        assert (cp_dir / "checkpoint.json").exists()

    def test_missing_snapshot_raises(self, run_dir: Path) -> None:
        with pytest.raises(FileNotFoundError, match="Snapshot not found"):
            create_checkpoint(run_dir)

    def test_no_events_file(self, run_dir: Path, snapshot: Path) -> None:
        cp = create_checkpoint(run_dir)
        assert cp.events_count == 0


class TestListCheckpoints:
    def test_empty(self, run_dir: Path) -> None:
        assert list_checkpoints(run_dir) == []

    def test_returns_sorted(self, run_dir: Path, snapshot: Path) -> None:
        cp1 = create_checkpoint(run_dir)
        cp2 = create_checkpoint(run_dir)
        cps = list_checkpoints(run_dir)
        assert len(cps) == 2
        assert cps[0].created_at <= cps[1].created_at


class TestGetLatestCheckpoint:
    def test_none_when_empty(self, run_dir: Path) -> None:
        assert get_latest_checkpoint(run_dir) is None

    def test_returns_latest(self, run_dir: Path, snapshot: Path) -> None:
        create_checkpoint(run_dir)
        cp2 = create_checkpoint(run_dir)
        latest = get_latest_checkpoint(run_dir)
        assert latest is not None
        assert latest.checkpoint_id == cp2.checkpoint_id


class TestLoadCheckpoint:
    def test_load_valid(self, run_dir: Path, snapshot: Path) -> None:
        cp = create_checkpoint(run_dir)
        loaded = load_checkpoint(run_dir, cp.checkpoint_id)
        assert loaded.run_id == cp.run_id

    def test_load_missing_raises(self, run_dir: Path) -> None:
        with pytest.raises(FileNotFoundError, match="not found"):
            load_checkpoint(run_dir, "nonexistent")


class TestCleanupOldCheckpoints:
    def test_no_cleanup_needed(self, run_dir: Path, snapshot: Path) -> None:
        create_checkpoint(run_dir)
        deleted = cleanup_old_checkpoints(run_dir, keep_last_n=5)
        assert deleted == 0

    def test_cleanup_removes_oldest(self, run_dir: Path, snapshot: Path) -> None:
        for _ in range(5):
            create_checkpoint(run_dir)
        assert len(list_checkpoints(run_dir)) == 5
        deleted = cleanup_old_checkpoints(run_dir, keep_last_n=2)
        assert deleted == 3
        assert len(list_checkpoints(run_dir)) == 2


class TestCheckpointWithPopulatedSnapshot:
    """SS-03: Verify checkpoint captures populated snapshots (not just {})."""

    def test_checkpoint_captures_populated_snapshot(self, run_dir: Path) -> None:
        """Checkpoint should contain the full Snapshot model data."""
        snap = Snapshot(
            run_id="r_test",
            run_state="RUNNING",
            artifacts_index={
                "bundle.json": ArtifactIndexEntry(
                    path="bundle.json", sha256="deadbeef", writer_worker="understand"
                )
            },
            work_items=[WorkItem(work_item_id="w1", worker="intake", status="finished")],
        )
        write_snapshot(run_dir / "snapshot.json", snap)

        cp = create_checkpoint(run_dir)
        assert cp.run_id == "r_test"
        assert cp.run_state == "RUNNING"

        # Verify the checkpoint's snapshot.json has real content
        cp_snap_path = run_dir / "checkpoints" / cp.checkpoint_id / "snapshot.json"
        cp_snap_data = json.loads(cp_snap_path.read_text(encoding="utf-8"))
        assert cp_snap_data["run_state"] == "RUNNING"
        assert "bundle.json" in cp_snap_data["artifacts_index"]
        assert cp_snap_data["artifacts_index"]["bundle.json"]["sha256"] == "deadbeef"
        assert len(cp_snap_data["work_items"]) == 1

    def test_load_checkpoint_preserves_snapshot_fields(self, run_dir: Path) -> None:
        """load_checkpoint metadata reflects snapshot state."""
        snap = Snapshot(run_id="r_test", run_state="COMPLETED")
        write_snapshot(run_dir / "snapshot.json", snap)

        cp = create_checkpoint(run_dir)
        loaded = load_checkpoint(run_dir, cp.checkpoint_id)
        assert loaded.run_id == "r_test"
        assert loaded.run_state == "COMPLETED"

    def test_checkpoint_empty_snapshot_still_works(self, run_dir: Path) -> None:
        """Even an empty Snapshot() should checkpoint without error."""
        snap = Snapshot()
        write_snapshot(run_dir / "snapshot.json", snap)

        cp = create_checkpoint(run_dir)
        assert cp.run_state == "CREATED"
        assert cp.run_id == ""


class TestWorkerCheckpoint:
    """Tests for write/load/restore worker checkpoint API (TC-3852a / H4.1)."""

    @pytest.fixture
    def run_dir(self, tmp_path: Path) -> Path:
        d = tmp_path / "run_wcp"
        d.mkdir()
        return d

    @pytest.fixture
    def artifact(self, run_dir: Path) -> Path:
        """A minimal artifact file inside run_dir."""
        p = run_dir / "bundle.json"
        p.write_text('{"worker": "understand", "status": "ok"}', encoding="utf-8")
        return p

    def test_write_creates_file(self, run_dir: Path, artifact: Path) -> None:
        """write_worker_checkpoint creates a JSON file in worker_checkpoints/."""
        cp = write_worker_checkpoint(run_dir=run_dir, worker="understand", artifact_path=artifact)
        cp_file = run_dir / "worker_checkpoints" / f"{cp.checkpoint_id}.json"
        assert cp_file.exists(), "Checkpoint JSON file must be created"

    def test_write_returns_checkpoint(self, run_dir: Path, artifact: Path) -> None:
        """Returned WorkerCheckpoint has all required fields populated."""
        cp = write_worker_checkpoint(run_dir=run_dir, worker="understand", artifact_path=artifact)
        assert isinstance(cp, WorkerCheckpoint)
        assert cp.worker == "understand"
        assert cp.run_id == run_dir.name
        assert cp.content_hash != ""
        assert cp.artifact_path != ""
        assert cp.created_at != ""

    def test_write_hash_is_sha256(self, run_dir: Path, artifact: Path) -> None:
        """content_hash is a 64-character lowercase hex SHA-256 digest."""
        cp = write_worker_checkpoint(run_dir=run_dir, worker="generate", artifact_path=artifact)
        assert len(cp.content_hash) == 64
        assert all(c in "0123456789abcdef" for c in cp.content_hash)
        # Verify hash matches file bytes
        expected = hashlib.sha256(artifact.read_bytes()).hexdigest()
        assert cp.content_hash == expected

    def test_load_valid(self, run_dir: Path, artifact: Path) -> None:
        """load_worker_checkpoint by ID returns the same WorkerCheckpoint."""
        cp = write_worker_checkpoint(run_dir=run_dir, worker="planner", artifact_path=artifact)
        loaded = load_worker_checkpoint(run_dir, cp.checkpoint_id)
        assert loaded is not None
        assert loaded.checkpoint_id == cp.checkpoint_id
        assert loaded.content_hash == cp.content_hash
        assert loaded.worker == cp.worker

    def test_load_missing_returns_none(self, run_dir: Path) -> None:
        """load_worker_checkpoint returns None for an unknown checkpoint ID."""
        result = load_worker_checkpoint(run_dir, "nonexistent_checkpoint_id")
        assert result is None

    def test_restore_intact(self, run_dir: Path, artifact: Path) -> None:
        """restore_worker_checkpoint returns True when artifact is unchanged."""
        cp = write_worker_checkpoint(run_dir=run_dir, worker="evaluate", artifact_path=artifact)
        assert restore_worker_checkpoint(run_dir, cp) is True

    def test_restore_tampered(self, run_dir: Path, artifact: Path) -> None:
        """restore_worker_checkpoint returns False after artifact bytes are modified."""
        cp = write_worker_checkpoint(run_dir=run_dir, worker="evaluate", artifact_path=artifact)
        # Tamper the artifact
        artifact.write_text('{"worker": "tampered"}', encoding="utf-8")
        assert restore_worker_checkpoint(run_dir, cp) is False

    def test_restore_missing_file(self, run_dir: Path, artifact: Path) -> None:
        """restore_worker_checkpoint returns False when artifact has been deleted."""
        cp = write_worker_checkpoint(run_dir=run_dir, worker="generate", artifact_path=artifact)
        artifact.unlink()
        assert restore_worker_checkpoint(run_dir, cp) is False


class TestBackupAndRestore:
    """V2SC-06: backup_output_files / restore_from_backup."""

    def test_backup_creates_bak_files(self, run_dir: Path) -> None:
        (run_dir / "heal_plan.json").write_text('{"steps":[]}', encoding="utf-8")
        created = backup_output_files(run_dir, ["heal_plan.json"])
        assert len(created) == 1
        assert (run_dir / "heal_plan.json.bak").exists()

    def test_backup_skips_missing_files(self, run_dir: Path) -> None:
        created = backup_output_files(run_dir, ["nonexistent_file.json"])
        assert created == []

    def test_restore_overwrites_original(self, run_dir: Path) -> None:
        original = run_dir / "heal_plan.json"
        original.write_text('{"steps":[]}', encoding="utf-8")
        backup_output_files(run_dir, ["heal_plan.json"])
        # Corrupt the original
        original.write_text('{"steps":"CORRUPT"}', encoding="utf-8")
        restored = restore_from_backup(run_dir, ["heal_plan.json"])
        assert len(restored) == 1
        assert original.read_text(encoding="utf-8") == '{"steps":[]}'

    def test_restore_removes_backup_after_restore(self, run_dir: Path) -> None:
        (run_dir / "heal_plan.json").write_text("{}", encoding="utf-8")
        backup_output_files(run_dir, ["heal_plan.json"])
        restore_from_backup(run_dir, ["heal_plan.json"])
        assert not (run_dir / "heal_plan.json.bak").exists()

    def test_restore_skips_missing_backup(self, run_dir: Path) -> None:
        restored = restore_from_backup(run_dir, ["no_backup_here.json"])
        assert restored == []

    def test_backup_missing_run_dir(self, tmp_path: Path) -> None:
        result = backup_output_files(tmp_path / "nonexistent", ["file.json"])
        assert result == []
