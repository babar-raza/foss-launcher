"""Run directory concurrency guard via PID lockfile (.launcher.pid).

Prevents two pipeline processes from operating on the same run_dir simultaneously.
Uses atomic file creation (open 'x' mode = O_CREAT|O_EXCL) -- works on both Windows
NTFS and POSIX without platform-specific fcntl/msvcrt code.

Stale locks (from crashed processes) are detected via a platform-safe PID liveness
check and reclaimed automatically, so a crash never permanently blocks future runs
on the same directory.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_LOCK_FILENAME = ".launcher.pid"


class RunAlreadyActiveError(RuntimeError):
    """Raised when a run directory is already locked by a live process."""


class RunLock:
    """Context manager that exclusively locks a run directory via a PID file.

    Creates ``run_dir/.launcher.pid`` on acquire (atomic, O_CREAT|O_EXCL).
    Deletes it on release -- even if the body raises an exception.

    Usage::

        with RunLock(run_dir, worker="Intake"):
            run_pipeline(...)
        # .launcher.pid is deleted automatically
    """

    def __init__(self, run_dir: Path, *, worker: str = "unknown") -> None:
        self._lock_path = run_dir / _LOCK_FILENAME
        self._worker = worker

    def acquire(self) -> None:
        """Acquire the lock. Raises RunAlreadyActiveError if another live
        process holds it."""
        pid = os.getpid()
        content = json.dumps(
            {
                "pid": pid,
                "worker": self._worker,
                "acquired_at": datetime.now(timezone.utc).isoformat(),
            },
            indent=2,
        )
        self._lock_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self._lock_path, "x", encoding="utf-8") as f:
                f.write(content)
            logger.debug(
                "run_lock_acquired pid=%d worker=%s path=%s",
                pid,
                self._worker,
                self._lock_path,
            )
        except FileExistsError:
            self._handle_existing_lock()

    def release(self) -> None:
        """Release the lock (delete .launcher.pid). Safe to call even if the
        file was already removed."""
        try:
            self._lock_path.unlink()
            logger.debug("run_lock_released path=%s", self._lock_path)
        except FileNotFoundError:
            pass

    def __enter__(self) -> RunLock:
        self.acquire()
        return self

    def __exit__(self, *_: object) -> None:
        self.release()

    # -- Internal helpers ------------------------------------------------------

    def _handle_existing_lock(self) -> None:
        existing = self._read_lock()

        if existing is None:
            logger.warning(
                "run_lock_corrupt_replacing path=%s", self._lock_path
            )
            self._lock_path.unlink(missing_ok=True)
            self.acquire()
            return

        existing_pid: int = existing.get("pid", -1)
        existing_worker: str = existing.get("worker", "?")
        acquired_at: str = existing.get("acquired_at", "?")

        if _is_process_alive(existing_pid):
            raise RunAlreadyActiveError(
                f"Run directory is already active "
                f"(PID {existing_pid}, worker '{existing_worker}', "
                f"since {acquired_at}).\n"
                f"Wait for it to complete, or delete {self._lock_path} "
                f"if PID {existing_pid} is no longer running."
            )

        logger.warning(
            "run_lock_stale_reclaimed stale_pid=%d stale_worker=%s path=%s",
            existing_pid,
            existing_worker,
            self._lock_path,
        )
        self._lock_path.unlink(missing_ok=True)
        self.acquire()

    def _read_lock(self) -> Optional[dict]:
        try:
            return json.loads(self._lock_path.read_text(encoding="utf-8"))
        except Exception:
            return None


def _is_process_alive(pid: int) -> bool:
    """Return True if a process with the given PID currently exists."""
    if pid <= 0:
        return False

    if os.name == "nt":
        return _is_process_alive_windows(pid)

    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _is_process_alive_windows(pid: int) -> bool:
    """Windows process liveness check without signals."""
    import ctypes

    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    SYNCHRONIZE = 0x00100000
    STILL_ACTIVE = 259

    desired_access = PROCESS_QUERY_LIMITED_INFORMATION | SYNCHRONIZE
    handle = ctypes.windll.kernel32.OpenProcess(desired_access, False, pid)  # type: ignore[union-attr]
    if not handle:
        return False

    try:
        exit_code = ctypes.c_ulong()
        ok = ctypes.windll.kernel32.GetExitCodeProcess(  # type: ignore[union-attr]
            handle, ctypes.byref(exit_code)
        )
        if not ok:
            return False
        return exit_code.value == STILL_ACTIVE
    finally:
        ctypes.windll.kernel32.CloseHandle(handle)  # type: ignore[union-attr]
