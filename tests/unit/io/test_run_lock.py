"""Tests for run directory concurrency guard (PID lockfile)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from launcher.io.run_lock import RunAlreadyActiveError, RunLock, _is_process_alive


class TestRunLock:
    def test_acquire_creates_lock(self, tmp_path: Path) -> None:
        lock = RunLock(tmp_path, worker="test")
        lock.acquire()
        lock_file = tmp_path / ".launcher.pid"
        assert lock_file.exists()
        data = json.loads(lock_file.read_text(encoding="utf-8"))
        assert data["pid"] == os.getpid()
        assert data["worker"] == "test"
        lock.release()

    def test_release_removes_lock(self, tmp_path: Path) -> None:
        lock = RunLock(tmp_path, worker="test")
        lock.acquire()
        lock.release()
        assert not (tmp_path / ".launcher.pid").exists()

    def test_context_manager(self, tmp_path: Path) -> None:
        with RunLock(tmp_path, worker="ctx"):
            assert (tmp_path / ".launcher.pid").exists()
        assert not (tmp_path / ".launcher.pid").exists()

    def test_context_manager_cleanup_on_exception(self, tmp_path: Path) -> None:
        with pytest.raises(RuntimeError):
            with RunLock(tmp_path, worker="err"):
                raise RuntimeError("boom")
        assert not (tmp_path / ".launcher.pid").exists()

    def test_concurrent_acquire_raises(self, tmp_path: Path) -> None:
        lock1 = RunLock(tmp_path, worker="first")
        lock1.acquire()
        try:
            lock2 = RunLock(tmp_path, worker="second")
            with pytest.raises(RunAlreadyActiveError, match="already active"):
                lock2.acquire()
        finally:
            lock1.release()

    def test_stale_lock_reclaimed(self, tmp_path: Path) -> None:
        """Stale lock from dead process is reclaimed."""
        lock_file = tmp_path / ".launcher.pid"
        lock_file.write_text(
            json.dumps({"pid": 99999999, "worker": "dead", "acquired_at": "2024-01-01T00:00:00Z"}),
            encoding="utf-8",
        )

        with patch("launcher.io.run_lock._is_process_alive", return_value=False):
            lock = RunLock(tmp_path, worker="new")
            lock.acquire()
            data = json.loads(lock_file.read_text(encoding="utf-8"))
            assert data["worker"] == "new"
            lock.release()

    def test_corrupt_lock_replaced(self, tmp_path: Path) -> None:
        lock_file = tmp_path / ".launcher.pid"
        lock_file.write_text("not json at all", encoding="utf-8")

        lock = RunLock(tmp_path, worker="recovery")
        lock.acquire()
        data = json.loads(lock_file.read_text(encoding="utf-8"))
        assert data["worker"] == "recovery"
        lock.release()

    def test_release_idempotent(self, tmp_path: Path) -> None:
        lock = RunLock(tmp_path, worker="test")
        lock.acquire()
        lock.release()
        lock.release()  # Should not raise


class TestIsProcessAlive:
    def test_current_process_alive(self) -> None:
        assert _is_process_alive(os.getpid()) is True

    def test_invalid_pid_not_alive(self) -> None:
        assert _is_process_alive(-1) is False
        assert _is_process_alive(0) is False
