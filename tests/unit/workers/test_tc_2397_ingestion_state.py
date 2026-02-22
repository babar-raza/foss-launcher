"""Tests for TC-2397: IngestionStateManager."""
import pytest
from pathlib import Path
from launch.workers.w1_repo_scout.ingestion_state import IngestionStateManager


def test_needs_ingestion_new_file(tmp_path):
    """File not yet ingested → needs_ingestion returns True."""
    state_file = tmp_path / "state.json"
    manager = IngestionStateManager(state_file)
    test_file = tmp_path / "test.md"
    test_file.write_text("content")
    assert manager.needs_ingestion(test_file) is True


def test_mark_ingested_then_no_longer_needed(tmp_path):
    """After mark_ingested, needs_ingestion returns False for same content."""
    state_file = tmp_path / "state.json"
    manager = IngestionStateManager(state_file)
    test_file = tmp_path / "test.md"
    test_file.write_text("content")
    manager.mark_ingested(test_file)
    assert manager.needs_ingestion(test_file) is False


def test_needs_ingestion_after_content_change(tmp_path):
    """After file content changes, needs_ingestion returns True again."""
    state_file = tmp_path / "state.json"
    manager = IngestionStateManager(state_file)
    test_file = tmp_path / "test.md"
    test_file.write_text("original content")
    manager.mark_ingested(test_file)
    test_file.write_text("modified content")
    assert manager.needs_ingestion(test_file) is True


def test_state_persists_across_instances(tmp_path):
    """State is saved to disk and loaded by a new instance."""
    state_file = tmp_path / "state.json"
    test_file = tmp_path / "test.md"
    test_file.write_text("content")

    # First instance marks as ingested
    manager1 = IngestionStateManager(state_file)
    manager1.mark_ingested(test_file)

    # Second instance loads from disk — should not need ingestion
    manager2 = IngestionStateManager(state_file)
    assert manager2.needs_ingestion(test_file) is False


def test_clear_forces_full_reingest(tmp_path):
    """After clear(), all files need ingestion again."""
    state_file = tmp_path / "state.json"
    test_file = tmp_path / "test.md"
    test_file.write_text("content")

    manager = IngestionStateManager(state_file)
    manager.mark_ingested(test_file)
    assert manager.needs_ingestion(test_file) is False

    manager.clear()
    assert manager.needs_ingestion(test_file) is True


def test_get_changed_files(tmp_path):
    """get_changed_files returns only files that need re-ingestion."""
    state_file = tmp_path / "state.json"
    manager = IngestionStateManager(state_file)

    file_a = tmp_path / "a.md"
    file_a.write_text("content a")
    file_b = tmp_path / "b.md"
    file_b.write_text("content b")

    manager.mark_ingested(file_a)
    changed = manager.get_changed_files([file_a, file_b])
    assert file_a not in changed
    assert file_b in changed


def test_nonexistent_state_file_starts_empty(tmp_path):
    """IngestionStateManager with missing state file starts with empty state."""
    state_file = tmp_path / "nonexistent.json"
    manager = IngestionStateManager(state_file)
    assert manager._state == {}


def test_mark_ingested_many(tmp_path):
    """mark_ingested_many marks all files and persists once."""
    state_file = tmp_path / "state.json"
    manager = IngestionStateManager(state_file)

    files = []
    for i in range(5):
        f = tmp_path / f"file_{i}.md"
        f.write_text(f"content {i}")
        files.append(f)

    manager.mark_ingested_many(files)
    for f in files:
        assert manager.needs_ingestion(f) is False


def test_tracked_file_count(tmp_path):
    """tracked_file_count returns the number of tracked files."""
    state_file = tmp_path / "state.json"
    manager = IngestionStateManager(state_file)
    assert manager.tracked_file_count == 0

    f1 = tmp_path / "f1.md"
    f1.write_text("content 1")
    f2 = tmp_path / "f2.md"
    f2.write_text("content 2")

    manager.mark_ingested(f1)
    assert manager.tracked_file_count == 1

    manager.mark_ingested(f2)
    assert manager.tracked_file_count == 2

    manager.clear()
    assert manager.tracked_file_count == 0


def test_needs_ingestion_nonexistent_file(tmp_path):
    """needs_ingestion returns True for a file that doesn't exist on disk."""
    state_file = tmp_path / "state.json"
    manager = IngestionStateManager(state_file)
    missing_file = tmp_path / "does_not_exist.md"
    # File doesn't exist → OSError → treated as changed
    assert manager.needs_ingestion(missing_file) is True


def test_state_file_created_in_nested_directory(tmp_path):
    """State file is created even when parent directories don't exist yet."""
    state_file = tmp_path / "nested" / "dir" / "state.json"
    manager = IngestionStateManager(state_file)
    test_file = tmp_path / "test.md"
    test_file.write_text("content")
    manager.mark_ingested(test_file)
    assert state_file.exists()
    assert manager.needs_ingestion(test_file) is False
