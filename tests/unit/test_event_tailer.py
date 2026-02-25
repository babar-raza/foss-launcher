"""Tests for launch.monitoring.event_tailer — EventTailer.

Validates real-time event tailing, rendering, and edge cases.
"""

from __future__ import annotations

import json
import textwrap
import threading
import time
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path

import pytest
from rich.console import Console

from launch.monitoring.event_tailer import EventTailer, _extract_worker_name


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_event(event_type: str, payload: dict, run_id: str = "test-run") -> str:
    """Create a single NDJSON event line."""
    event = {
        "event_id": f"evt-test-{event_type}",
        "run_id": run_id,
        "ts": datetime.now(timezone.utc).isoformat(),
        "type": event_type,
        "payload": payload,
        "trace_id": "trace-1",
        "span_id": "span-1",
    }
    return json.dumps(event, separators=(",", ":"), sort_keys=True)


def _append_line(path: Path, line: str) -> None:
    """Append a single NDJSON line to a file."""
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def _captured_console() -> tuple:
    """Create a Console that captures output to a StringIO buffer."""
    buf = StringIO()
    console = Console(file=buf, force_terminal=True, width=120)
    return console, buf


# ---------------------------------------------------------------------------
# Tests: _extract_worker_name
# ---------------------------------------------------------------------------

class TestExtractWorkerName:
    def test_standard_format(self):
        assert _extract_worker_name("run-123:W5.SectionWriter:1") == "W5.SectionWriter"

    def test_with_scope_key(self):
        assert _extract_worker_name("run-123:W5.SectionWriter:1:page-1") == "W5.SectionWriter"

    def test_no_colon(self):
        assert _extract_worker_name("just-a-string") == "just-a-string"

    def test_empty_string(self):
        assert _extract_worker_name("") == ""


# ---------------------------------------------------------------------------
# Tests: EventTailer._format_ts
# ---------------------------------------------------------------------------

class TestFormatTs:
    def test_iso_timestamp(self):
        assert EventTailer._format_ts("2026-02-25T12:50:15.123456+00:00") == "12:50:15"

    def test_iso_no_microseconds(self):
        assert EventTailer._format_ts("2026-02-25T08:30:00+00:00") == "08:30:00"

    def test_empty_string(self):
        assert EventTailer._format_ts("") == "??:??:??"

    def test_no_t_separator(self):
        result = EventTailer._format_ts("20260225")
        assert result == "20260225"  # Falls through to ts[:8]


# ---------------------------------------------------------------------------
# Tests: Event rendering
# ---------------------------------------------------------------------------

class TestEventRendering:
    def test_work_item_started(self, tmp_path):
        events_path = tmp_path / "events.ndjson"
        _append_line(events_path, _make_event(
            "WORK_ITEM_STARTED",
            {"worker": "W1.RepoScout", "work_item_id": "run:W1.RepoScout:1"},
        ))

        console, buf = _captured_console()
        tailer = EventTailer(events_path, console)
        tailer.replay_existing()

        output = buf.getvalue()
        assert "STARTED" in output
        assert "W1.RepoScout" in output

    def test_work_item_finished_success(self, tmp_path):
        events_path = tmp_path / "events.ndjson"
        _append_line(events_path, _make_event(
            "WORK_ITEM_FINISHED",
            {"work_item_id": "run:W2.FactsBuilder:1", "success": True},
        ))

        console, buf = _captured_console()
        tailer = EventTailer(events_path, console)
        tailer.replay_existing()

        output = buf.getvalue()
        assert "OK" in output
        assert "W2.FactsBuilder" in output

    def test_work_item_finished_failure(self, tmp_path):
        events_path = tmp_path / "events.ndjson"
        _append_line(events_path, _make_event(
            "WORK_ITEM_FINISHED",
            {
                "work_item_id": "run:W5.SectionWriter:1",
                "success": False,
                "error": {"type": "ValueError", "message": "bad input"},
            },
        ))

        console, buf = _captured_console()
        tailer = EventTailer(events_path, console)
        tailer.replay_existing()

        output = buf.getvalue()
        assert "FAIL" in output
        assert "W5.SectionWriter" in output
        assert "bad input" in output

    def test_artifact_written(self, tmp_path):
        events_path = tmp_path / "events.ndjson"
        _append_line(events_path, _make_event(
            "ARTIFACT_WRITTEN",
            {"name": "product_facts.json"},
        ))

        console, buf = _captured_console()
        tailer = EventTailer(events_path, console)
        tailer.replay_existing()

        output = buf.getvalue()
        assert "ARTIFACT" in output
        assert "product_facts.json" in output

    def test_run_state_changed(self, tmp_path):
        events_path = tmp_path / "events.ndjson"
        _append_line(events_path, _make_event(
            "RUN_STATE_CHANGED",
            {"old_state": "CLONED_INPUTS", "new_state": "INGESTED"},
        ))

        console, buf = _captured_console()
        tailer = EventTailer(events_path, console)
        tailer.replay_existing()

        output = buf.getvalue()
        assert "STATE" in output
        assert "CLONED_INPUTS" in output
        assert "INGESTED" in output

    def test_phase_started_renders_rule(self, tmp_path):
        events_path = tmp_path / "events.ndjson"
        _append_line(events_path, _make_event(
            "PHASE_STARTED",
            {"phase_id": "P1", "workers": ["W1", "W2"]},
        ))

        console, buf = _captured_console()
        tailer = EventTailer(events_path, console)
        tailer.replay_existing()

        output = buf.getvalue()
        assert "Phase P1" in output
        assert "W1" in output
        assert "W2" in output

    def test_phase_completed_pass(self, tmp_path):
        events_path = tmp_path / "events.ndjson"
        _append_line(events_path, _make_event(
            "PHASE_COMPLETED",
            {"phase_id": "P2", "ok": True},
        ))

        console, buf = _captured_console()
        tailer = EventTailer(events_path, console)
        tailer.replay_existing()

        output = buf.getvalue()
        assert "Phase P2" in output
        assert "PASS" in output

    def test_phase_completed_fail(self, tmp_path):
        events_path = tmp_path / "events.ndjson"
        _append_line(events_path, _make_event(
            "PHASE_COMPLETED",
            {"phase_id": "P3", "ok": False},
        ))

        console, buf = _captured_console()
        tailer = EventTailer(events_path, console)
        tailer.replay_existing()

        output = buf.getvalue()
        assert "Phase P3" in output
        assert "FAIL" in output

    def test_gate_run_finished(self, tmp_path):
        events_path = tmp_path / "events.ndjson"
        _append_line(events_path, _make_event(
            "GATE_RUN_FINISHED",
            {"gate_id": "gate_1_schema_validation", "passed": True},
        ))

        console, buf = _captured_console()
        tailer = EventTailer(events_path, console)
        tailer.replay_existing()

        output = buf.getvalue()
        assert "GATE" in output
        assert "gate_1_schema_validation" in output

    def test_run_completed(self, tmp_path):
        events_path = tmp_path / "events.ndjson"
        _append_line(events_path, _make_event("RUN_COMPLETED", {}))

        console, buf = _captured_console()
        tailer = EventTailer(events_path, console)
        tailer.replay_existing()

        output = buf.getvalue()
        assert "RUN COMPLETED" in output

    def test_run_failed(self, tmp_path):
        events_path = tmp_path / "events.ndjson"
        _append_line(events_path, _make_event(
            "RUN_FAILED",
            {"reason": "W9 validation failed"},
        ))

        console, buf = _captured_console()
        tailer = EventTailer(events_path, console)
        tailer.replay_existing()

        output = buf.getvalue()
        assert "RUN FAILED" in output
        assert "W9 validation failed" in output

    def test_run_created(self, tmp_path):
        events_path = tmp_path / "events.ndjson"
        _append_line(events_path, _make_event("RUN_CREATED", {}, run_id="r_20260225T120000Z"))

        console, buf = _captured_console()
        tailer = EventTailer(events_path, console)
        tailer.replay_existing()

        output = buf.getvalue()
        assert "RUN CREATED" in output
        assert "r_20260225T120000Z" in output


# ---------------------------------------------------------------------------
# Tests: LLM events (verbose control)
# ---------------------------------------------------------------------------

class TestLLMEventVerbose:
    def test_llm_events_hidden_by_default(self, tmp_path):
        events_path = tmp_path / "events.ndjson"
        _append_line(events_path, _make_event(
            "LLM_CALL_STARTED", {"worker": "W5.SectionWriter"},
        ))
        _append_line(events_path, _make_event(
            "LLM_CALL_FINISHED", {"duration_s": 3.2},
        ))

        console, buf = _captured_console()
        tailer = EventTailer(events_path, console, verbose=False)
        tailer.replay_existing()

        output = buf.getvalue()
        assert "LLM" not in output

    def test_llm_events_shown_in_verbose(self, tmp_path):
        events_path = tmp_path / "events.ndjson"
        _append_line(events_path, _make_event(
            "LLM_CALL_STARTED", {"worker": "W5.SectionWriter"},
        ))
        _append_line(events_path, _make_event(
            "LLM_CALL_FINISHED", {"duration_s": 3.2},
        ))
        _append_line(events_path, _make_event(
            "LLM_CALL_FAILED", {"error": "timeout"},
        ))

        console, buf = _captured_console()
        tailer = EventTailer(events_path, console, verbose=True)
        tailer.replay_existing()

        output = buf.getvalue()
        assert "LLM" in output
        assert "W5.SectionWriter" in output
        # Check "LLM done" and "LLM FAIL" (ANSI codes may split numbers)
        assert "LLM done" in output
        assert "timeout" in output


# ---------------------------------------------------------------------------
# Tests: Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_missing_file_no_crash(self, tmp_path):
        events_path = tmp_path / "nonexistent" / "events.ndjson"
        console, buf = _captured_console()
        tailer = EventTailer(events_path, console)
        # Should not raise
        tailer.replay_existing()
        assert buf.getvalue() == ""

    def test_empty_file(self, tmp_path):
        events_path = tmp_path / "events.ndjson"
        events_path.write_text("", encoding="utf-8")

        console, buf = _captured_console()
        tailer = EventTailer(events_path, console)
        tailer.replay_existing()
        assert buf.getvalue() == ""

    def test_malformed_json_lines_skipped(self, tmp_path):
        events_path = tmp_path / "events.ndjson"
        events_path.write_text(
            "not-json\n"
            + _make_event("RUN_CREATED", {}) + "\n"
            + "{broken json\n",
            encoding="utf-8",
        )

        console, buf = _captured_console()
        tailer = EventTailer(events_path, console)
        tailer.replay_existing()

        output = buf.getvalue()
        assert "RUN CREATED" in output

    def test_unknown_event_type_ignored(self, tmp_path):
        events_path = tmp_path / "events.ndjson"
        _append_line(events_path, _make_event("CUSTOM_UNKNOWN_EVENT", {"data": "test"}))

        console, buf = _captured_console()
        tailer = EventTailer(events_path, console)
        tailer.replay_existing()
        # Should not crash; output may be empty since unknown types are silently ignored
        # Just verify no exception was raised

    def test_multiple_events_ordered(self, tmp_path):
        events_path = tmp_path / "events.ndjson"
        _append_line(events_path, _make_event(
            "WORK_ITEM_STARTED", {"worker": "W1.RepoScout"},
        ))
        _append_line(events_path, _make_event(
            "ARTIFACT_WRITTEN", {"name": "repo_inventory.json"},
        ))
        _append_line(events_path, _make_event(
            "WORK_ITEM_FINISHED", {"work_item_id": "run:W1.RepoScout:1", "success": True},
        ))

        console, buf = _captured_console()
        tailer = EventTailer(events_path, console)
        tailer.replay_existing()

        output = buf.getvalue()
        # All three events should appear in order
        started_pos = output.find("STARTED")
        artifact_pos = output.find("ARTIFACT")
        ok_pos = output.find("OK")
        assert started_pos < artifact_pos < ok_pos


# ---------------------------------------------------------------------------
# Tests: Background thread behavior
# ---------------------------------------------------------------------------

class TestBackgroundThread:
    def test_start_stop_lifecycle(self, tmp_path):
        events_path = tmp_path / "events.ndjson"
        events_path.write_text("", encoding="utf-8")

        console, buf = _captured_console()
        tailer = EventTailer(events_path, console, poll_interval=0.1)

        thread = tailer.start()
        assert thread.is_alive()

        tailer.stop()
        assert not thread.is_alive()

    def test_picks_up_new_events_while_tailing(self, tmp_path):
        events_path = tmp_path / "events.ndjson"
        events_path.write_text("", encoding="utf-8")

        console, buf = _captured_console()
        tailer = EventTailer(events_path, console, poll_interval=0.1)
        tailer.start()

        # Write an event after tailer has started
        time.sleep(0.2)
        _append_line(events_path, _make_event(
            "WORK_ITEM_STARTED", {"worker": "W4.IAPlanner"},
        ))
        time.sleep(0.3)

        tailer.stop()
        output = buf.getvalue()
        assert "W4.IAPlanner" in output

    def test_file_appears_after_start(self, tmp_path):
        events_path = tmp_path / "events.ndjson"
        # File does not exist yet

        console, buf = _captured_console()
        tailer = EventTailer(events_path, console, poll_interval=0.1)
        tailer.start()

        # Create file and write event after tailer started
        time.sleep(0.2)
        _append_line(events_path, _make_event(
            "RUN_CREATED", {}, run_id="late-start-run",
        ))
        time.sleep(0.3)

        tailer.stop()
        output = buf.getvalue()
        assert "RUN CREATED" in output

    def test_replay_then_tail(self, tmp_path):
        events_path = tmp_path / "events.ndjson"
        _append_line(events_path, _make_event(
            "WORK_ITEM_STARTED", {"worker": "W1.RepoScout"},
        ))

        console, buf = _captured_console()
        tailer = EventTailer(events_path, console, poll_interval=0.1)

        # Replay existing
        tailer.replay_existing()
        assert "W1.RepoScout" in buf.getvalue()

        # Start tailing
        tailer.start()
        time.sleep(0.2)

        # Write new event
        _append_line(events_path, _make_event(
            "WORK_ITEM_STARTED", {"worker": "W2.FactsBuilder"},
        ))
        time.sleep(0.3)

        tailer.stop()
        output = buf.getvalue()
        # Both events should be in output
        assert "W1.RepoScout" in output
        assert "W2.FactsBuilder" in output
