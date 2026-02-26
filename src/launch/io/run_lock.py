"""
Run directory concurrency guard via PID lockfile (.launch.pid).

Prevents two pipeline processes from operating on the same run_dir simultaneously.
Uses atomic file creation (open 'x' mode = O_CREAT|O_EXCL) — works on both Windows
NTFS and POSIX without platform-specific fcntl/msvcrt code.

Stale locks (from crashed processes) are detected via a platform-safe PID liveness
check and reclaimed automatically, so a crash never permanently blocks future runs
on the same directory.
"""
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_LOCK_FILENAME = ".launch.pid"


class RunAlreadyActiveError(RuntimeError):
    """Raised when a run directory is already locked by a live process.

    Contains a human-readable message with the blocking PID, worker name,
    and the lock file path so the user knows exactly how to resolve it.
    """


class RunLock:
    """Context manager that exclusively locks a run directory via a PID file.

    Creates ``run_dir/.launch.pid`` on acquire (atomic, O_CREAT|O_EXCL).
    Deletes it on release — even if the body raises an exception.

    Stale lock handling: if a .launch.pid exists but the recorded PID is no
    longer alive (e.g. the previous process crashed), the stale file is
    removed and the lock is acquired fresh.

    Usage::

        with RunLock(run_dir, worker="W9"):
            execute_graph(...)
        # .launch.pid is deleted automatically

    Args:
        run_dir: Path to the run directory (e.g. ``runs/r_20260222T.../``).
        worker:  Human-readable label for the worker acquiring the lock
                 (used in error messages and the lock file content).
    """

    def __init__(self, run_dir: Path, *, worker: str = "unknown") -> None:
        self._lock_path = run_dir / _LOCK_FILENAME
        self._worker = worker

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def acquire(self) -> None:
        """Acquire the lock.  Raises RunAlreadyActiveError if another live
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
        # Ensure the directory exists (relevant when called before create_run_skeleton)
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
        """Release the lock (delete .launch.pid).  Safe to call even if the
        file was already removed."""
        try:
            self._lock_path.unlink()
            logger.debug("run_lock_released path=%s", self._lock_path)
        except FileNotFoundError:
            pass  # Already gone — fine

    # Context-manager protocol
    def __enter__(self) -> "RunLock":
        self.acquire()
        return self

    def __exit__(self, *_) -> None:
        self.release()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _handle_existing_lock(self) -> None:
        """Called when open('x') raises FileExistsError.

        Either raises RunAlreadyActiveError (if the locking process is alive)
        or reclaims the stale lock and retries once.
        """
        existing = self._read_lock()

        if existing is None:
            # Unreadable / corrupt lock file — treat as stale and overwrite.
            logger.warning(
                "run_lock_corrupt_replacing path=%s", self._lock_path
            )
            self._lock_path.unlink(missing_ok=True)
            self.acquire()  # Recursive retry (at most once — no more FileExistsError expected)
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

        # Process is dead → stale lock.  Reclaim and retry.
        logger.warning(
            "run_lock_stale_reclaimed stale_pid=%d stale_worker=%s path=%s",
            existing_pid,
            existing_worker,
            self._lock_path,
        )
        self._lock_path.unlink(missing_ok=True)
        # Retry: if two processes both detect a stale lock simultaneously,
        # only one will win the O_CREAT|O_EXCL race and the other will retry
        # again (and see a live lock this time → RunAlreadyActiveError).
        self.acquire()

    def _read_lock(self) -> Optional[dict]:
        """Read and parse the lock file.  Returns None on any error."""
        try:
            return json.loads(self._lock_path.read_text(encoding="utf-8"))
        except Exception:
            return None


# ---------------------------------------------------------------------------
# Module-level helper (used by RunLock and tests)
# ---------------------------------------------------------------------------


def _is_process_alive(pid: int) -> bool:
    """Return True if a process with the given PID currently exists.

    POSIX:
        Uses ``os.kill(pid, 0)`` (existence/permission probe).

    Windows:
        Uses ``OpenProcess + GetExitCodeProcess`` because ``os.kill(pid, 0)``
        maps to ``CTRL_C_EVENT`` on Windows and can interrupt the current
        console process group.
    """
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
    handle = ctypes.windll.kernel32.OpenProcess(desired_access, False, pid)
    if not handle:
        return False

    try:
        exit_code = ctypes.c_ulong()
        ok = ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))
        if not ok:
            return False
        return exit_code.value == STILL_ACTIVE
    finally:
        ctypes.windll.kernel32.CloseHandle(handle)
