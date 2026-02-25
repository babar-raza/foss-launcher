"""Tests for run directory concurrency guard (PID lockfile).

Validates:
- Lock file is created/deleted correctly
- Concurrent acquire raises RunAlreadyActiveError with live PID
- Stale lock (dead process) is reclaimed automatically
- Corrupt lock file (non-JSON) is treated as stale
- Context manager cleans up on normal exit and on exception
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from launch.io.run_lock import RunAlreadyActiveError, RunLock, _is_process_alive


# ---------------------------------------------------------------------------
# T1: acquire() creates .launch.pid with expected JSON fields
# ---------------------------------------------------------------------------


def test_acquire_creates_lock_file(tmp_path: Path) -> None:
    """acquire() writes .launch.pid with pid, worker, and acquired_at fields."""
    lock = RunLock(tmp_path, worker="W9")
    lock.acquire()
    try:
        lock_file = tmp_path / ".launch.pid"
        assert lock_file.exists()
        data = json.loads(lock_file.read_text(encoding="utf-8"))
        assert data["pid"] == os.getpid()
        assert data["worker"] == "W9"
        assert "acquired_at" in data
        assert data["acquired_at"].endswith("+00:00") or data["acquired_at"].endswith("Z")
    finally:
        lock.release()


# ---------------------------------------------------------------------------
# T2: second acquire while first held → RunAlreadyActiveError
# ---------------------------------------------------------------------------


def test_acquire_raises_when_live_process_holds_lock(tmp_path: Path) -> None:
    """Acquiring while a live process holds the lock raises RunAlreadyActiveError."""
    lock1 = RunLock(tmp_path, worker="W9")
    lock1.acquire()
    try:
        lock2 = RunLock(tmp_path, worker="W9")
        with pytest.raises(RunAlreadyActiveError) as exc_info:
            lock2.acquire()
        assert str(os.getpid()) in str(exc_info.value)
    finally:
        lock1.release()


# ---------------------------------------------------------------------------
# T3: stale lock (os.kill raises OSError) → warning + lock acquired
# ---------------------------------------------------------------------------


def test_stale_lock_is_reclaimed(tmp_path: Path) -> None:
    """A lock whose PID is dead is treated as stale and overwritten."""
    stale_pid = 999999  # Extremely unlikely to be alive
    lock_file = tmp_path / ".launch.pid"
    lock_file.write_text(
        json.dumps({"pid": stale_pid, "worker": "W7", "acquired_at": "2026-01-01T00:00:00+00:00"}),
        encoding="utf-8",
    )

    # Patch _is_process_alive to simulate dead process
    with patch("launch.io.run_lock._is_process_alive", return_value=False):
        lock = RunLock(tmp_path, worker="W9")
        lock.acquire()
        try:
            data = json.loads(lock_file.read_text(encoding="utf-8"))
            assert data["pid"] == os.getpid()  # Reclaimed by current process
            assert data["worker"] == "W9"
        finally:
            lock.release()


# ---------------------------------------------------------------------------
# T4: corrupt lock file (non-JSON) → treated as stale, overwritten
# ---------------------------------------------------------------------------


def test_corrupt_lock_file_is_overwritten(tmp_path: Path) -> None:
    """A non-JSON lock file is treated as stale and overwritten cleanly."""
    lock_file = tmp_path / ".launch.pid"
    lock_file.write_text("THIS IS NOT JSON !!!", encoding="utf-8")

    lock = RunLock(tmp_path, worker="W9")
    lock.acquire()
    try:
        data = json.loads(lock_file.read_text(encoding="utf-8"))
        assert data["pid"] == os.getpid()
    finally:
        lock.release()


# ---------------------------------------------------------------------------
# T5: context manager cleans up on normal exit
# ---------------------------------------------------------------------------


def test_context_manager_releases_on_normal_exit(tmp_path: Path) -> None:
    """__exit__ deletes .launch.pid after a successful body."""
    lock_file = tmp_path / ".launch.pid"

    with RunLock(tmp_path, worker="W9"):
        assert lock_file.exists()

    assert not lock_file.exists()


# ---------------------------------------------------------------------------
# T6: context manager cleans up even when body raises
# ---------------------------------------------------------------------------


def test_context_manager_releases_on_exception(tmp_path: Path) -> None:
    """__exit__ deletes .launch.pid even when the body raises an exception."""
    lock_file = tmp_path / ".launch.pid"

    with pytest.raises(RuntimeError):
        with RunLock(tmp_path, worker="W9"):
            assert lock_file.exists()
            raise RuntimeError("simulated failure")

    assert not lock_file.exists()
