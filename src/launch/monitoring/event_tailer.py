"""Real-time event tailer for pipeline monitoring.

Polls ``events.ndjson`` and renders structured Rich console output for each
event type.  Designed to run in a background daemon thread alongside
in-process pipeline execution.

Usage::

    from launch.monitoring.event_tailer import EventTailer
    from rich.console import Console

    tailer = EventTailer(run_dir / "events.ndjson", Console())
    tailer.start()
    # ... execute pipeline ...
    tailer.stop()
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Dict, Optional

from rich.console import Console


class EventTailer:
    """Tail ``events.ndjson`` and render real-time progress via Rich.

    The tailer reads new lines from the event log using a seek/tell approach
    that is safe on Windows NTFS (no file locking conflicts with writers).
    Only complete lines (ending with ``\\n``) are processed — partial writes
    from concurrent appenders are silently skipped until complete.

    Parameters
    ----------
    events_path:
        Path to the ``events.ndjson`` file to tail.
    console:
        Rich Console instance for output.
    verbose:
        If True, display LLM call events (normally suppressed).
    poll_interval:
        Seconds between file polls (default 0.5).
    """

    def __init__(
        self,
        events_path: Path,
        console: Console,
        verbose: bool = False,
        poll_interval: float = 0.5,
    ) -> None:
        self._events_path = events_path
        self._console = console
        self._verbose = verbose
        self._poll_interval = poll_interval
        self._stop = threading.Event()
        self._last_pos: int = 0
        self._thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> threading.Thread:
        """Start tailing in a background daemon thread.

        Returns the thread object (caller can ``join()`` if desired).
        """
        self._stop.clear()
        t = threading.Thread(target=self._tail_loop, daemon=True, name="event-tailer")
        t.start()
        self._thread = t
        return t

    def stop(self) -> None:
        """Signal the tailer to stop and wait for the thread to exit."""
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    def replay_existing(self) -> None:
        """Read and display all existing events (catch-up display).

        Useful for ``launch monitor`` on an already-running or completed run.
        After replay, ``start()`` will continue from where replay left off.
        """
        self._read_new_events()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _tail_loop(self) -> None:
        """Poll events.ndjson for new lines and process them."""
        while not self._stop.is_set():
            self._read_new_events()
            self._stop.wait(timeout=self._poll_interval)
        # Final read to catch events written during stop signal
        self._read_new_events()

    def _read_new_events(self) -> None:
        """Read new complete lines from events.ndjson since last position."""
        if not self._events_path.exists():
            return

        try:
            with open(self._events_path, "r", encoding="utf-8") as f:
                f.seek(self._last_pos)
                data = f.read()
                if not data:
                    return

                # Only process complete lines (ending with \n).
                # If the last chunk doesn't end with \n, it's a partial write.
                if data.endswith("\n"):
                    lines = data.split("\n")
                    # Last element after split on trailing \n is empty string
                    lines = [ln for ln in lines if ln.strip()]
                    self._last_pos = f.tell()
                else:
                    # Partial write — process all complete lines, leave partial
                    parts = data.rsplit("\n", 1)
                    if len(parts) == 2:
                        complete, _partial = parts
                        lines = [ln for ln in complete.split("\n") if ln.strip()]
                        # Advance position past the complete lines + their newlines
                        self._last_pos += len(complete.encode("utf-8")) + 1  # +1 for \n
                    else:
                        # No newline at all — entirely partial
                        return

                for line in lines:
                    try:
                        event = json.loads(line)
                        self._process_event(event)
                    except json.JSONDecodeError:
                        pass  # Skip malformed lines
        except (OSError, PermissionError):
            pass  # File temporarily locked or inaccessible

    def _process_event(self, event: Dict[str, Any]) -> None:
        """Route an event to the appropriate display handler."""
        etype = event.get("type", "")
        payload = event.get("payload", {})
        ts = self._format_ts(event.get("ts", ""))

        if etype == "PHASE_STARTED":
            phase_id = payload.get("phase_id", "?")
            workers = payload.get("workers", [])
            self._console.print()
            self._console.rule(f"Phase {phase_id}: {', '.join(workers)}")

        elif etype == "PHASE_COMPLETED":
            phase_id = payload.get("phase_id", "?")
            ok = payload.get("ok", True)
            status = "[green]PASS[/green]" if ok else "[red]FAIL[/red]"
            self._console.print(f"  [{ts}] Phase {phase_id}: {status}")

        elif etype == "WORK_ITEM_STARTED":
            worker = payload.get("worker", payload.get("work_item_id", "?"))
            self._console.print(f"  [{ts}] [bold blue]STARTED[/bold blue]  {worker}")

        elif etype == "WORK_ITEM_FINISHED":
            wid = payload.get("work_item_id", "?")
            success = payload.get("success", True)
            worker = _extract_worker_name(wid)
            status = "[green]OK[/green]" if success else "[red]FAIL[/red]"
            err = payload.get("error")
            suffix = ""
            if err and not success:
                suffix = f" — {err.get('message', '')}"
            self._console.print(f"  [{ts}] {status}       {worker}{suffix}")

        elif etype == "ARTIFACT_WRITTEN":
            name = payload.get("name", payload.get("artifact", "?"))
            self._console.print(f"  [{ts}] [dim]ARTIFACT[/dim] {name}")

        elif etype == "RUN_STATE_CHANGED":
            old = payload.get("old_state", "?")
            new = payload.get("new_state", "?")
            self._console.print(
                f"  [{ts}] [yellow]STATE[/yellow]    {old} \u2192 {new}"
            )

        elif etype == "GATE_RUN_FINISHED":
            gate = payload.get("gate_id", payload.get("gate", "?"))
            passed = payload.get("passed", payload.get("ok", True))
            status = "[green]PASS[/green]" if passed else "[red]FAIL[/red]"
            self._console.print(f"  [{ts}] [dim]GATE[/dim]     {gate}: {status}")

        elif etype == "RUN_COMPLETED":
            self._console.print(f"\n  [{ts}] [bold green]RUN COMPLETED[/bold green]")

        elif etype == "RUN_FAILED":
            reason = payload.get("reason", payload.get("error", ""))
            self._console.print(
                f"\n  [{ts}] [bold red]RUN FAILED[/bold red]"
                + (f" — {reason}" if reason else "")
            )

        elif etype in ("LLM_CALL_STARTED", "LLM_CALL_FINISHED", "LLM_CALL_FAILED"):
            if self._verbose:
                self._render_llm_event(etype, payload, ts)

        elif etype == "RUN_CREATED":
            run_id = event.get("run_id", "?")
            self._console.print(f"  [{ts}] [blue]RUN CREATED[/blue] {run_id}")

        elif etype == "RUN_RESUMED":
            run_id = event.get("run_id", "?")
            self._console.print(f"  [{ts}] [blue]RUN RESUMED[/blue] {run_id}")

        # Silently ignore other event types

    def _render_llm_event(
        self, etype: str, payload: Dict[str, Any], ts: str
    ) -> None:
        """Render LLM call events (only shown in verbose mode)."""
        if etype == "LLM_CALL_STARTED":
            worker = payload.get("worker", "?")
            self._console.print(f"  [{ts}] [dim cyan]LLM[/dim cyan]      {worker}")
        elif etype == "LLM_CALL_FINISHED":
            duration = payload.get("duration_s", payload.get("elapsed_s", "?"))
            self._console.print(
                f"  [{ts}] [dim cyan]LLM done[/dim cyan] ({duration}s)"
            )
        elif etype == "LLM_CALL_FAILED":
            error = payload.get("error", "?")
            self._console.print(
                f"  [{ts}] [dim red]LLM FAIL[/dim red] {error}"
            )

    @staticmethod
    def _format_ts(ts: str) -> str:
        """Extract ``HH:MM:SS`` from an ISO-8601 timestamp."""
        if not ts:
            return "??:??:??"
        # ISO format: 2026-02-25T12:50:15.123456+00:00
        try:
            if "T" in ts:
                time_part = ts.split("T")[1]
                return time_part[:8]  # HH:MM:SS
        except (IndexError, ValueError):
            pass
        return ts[:8]


def _extract_worker_name(work_item_id: str) -> str:
    """Extract the human-readable worker name from a work_item_id.

    Work item IDs have the form ``{run_id}:{worker}:{attempt}[:{scope_key}]``.
    """
    parts = work_item_id.split(":")
    if len(parts) >= 2:
        return parts[1]
    return work_item_id
