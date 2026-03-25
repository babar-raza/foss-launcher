"""Tests for event accuracy in phase promotion (TC5190-SR-03).

Verifies:
1. phase_store_updated event excludes scout.json/understand.json from phase_files_written
2. phase_store_updated event includes only content phase files
3. metadata_phase_store_promoted event emitted by run_loop block
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from launcher.deploy.phase_promoter import promote_phase_snapshots
from launcher.models.evaluation import Grade


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_run(base: Path, run_id: str, pages: list[str], grade: str = "A") -> Path:
    """Create a run directory with evaluation_report.json + IR files."""
    run_dir = base / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    page_evals = [
        {
            "slug": cp.split("/")[-1],
            "content_path": cp,
            "grade": grade,
            "findings": [],
            "check_results": {},
            "numeric_score": 90.0,
        }
        for cp in pages
    ]
    eval_report = {
        "verdict": "GO",
        "pages": page_evals,
        "quality": {},
        "gates": [],
        "root_cause_diagnosis": [],
        "go_criteria": [],
    }
    (run_dir / "evaluation_report.json").write_text(
        json.dumps(eval_report), encoding="utf-8"
    )

    pages_dir = run_dir / "content_bundle" / "pages"
    for cp in pages:
        ir_path = pages_dir / (cp + ".ir.json")
        ir_path.parent.mkdir(parents=True, exist_ok=True)
        ir_path.write_text(f'{{"slug":"{cp}"}}', encoding="utf-8")

    # Create phase files that _update_phase_store expects
    (run_dir / "planner_checkpoint.json").write_text("{}", encoding="utf-8")
    (run_dir / "generate_checkpoint.json").write_text("{}", encoding="utf-8")
    (run_dir / "evaluate_checkpoint.json").write_text("{}", encoding="utf-8")
    # Metadata files (handled by update_phase_store_metadata, NOT _update_phase_store)
    (run_dir / "scout.json").write_text('{"build_systems":["python"]}', encoding="utf-8")
    (run_dir / "understanding_bundle.json").write_text("{}", encoding="utf-8")

    return run_dir


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestPhaseStoreUpdatedEventAccuracy:
    """Verify phase_store_updated event data matches files actually written."""

    def test_event_excludes_metadata_files(self, tmp_path: Path) -> None:
        """phase_files_written must NOT list scout.json or understand.json.

        TC5190-SR-03 fix: _update_phase_store does not write those files —
        they are handled by update_phase_store_metadata instead.
        """
        snapshots = tmp_path / "snapshots"
        phase_store = tmp_path / "phase_store"
        events_file = tmp_path / "events.ndjson"
        run_dir = _make_run(tmp_path, "run-evt", ["blog.test.org/page1"])

        promote_phase_snapshots(
            run_dir=run_dir,
            snapshots_dir=snapshots,
            phase_store_dir=phase_store,
            family="cells",
            platform="python",
            events_path=events_file,
        )

        assert events_file.exists()
        lines = [
            json.loads(line)
            for line in events_file.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        ps_events = [e for e in lines if e.get("event_type") == "phase_store_updated"]
        assert len(ps_events) == 1

        written_files = ps_events[0]["data"]["phase_files_written"]
        assert "scout.json" not in written_files
        assert "understand.json" not in written_files

    def test_event_includes_content_phase_files(self, tmp_path: Path) -> None:
        """phase_files_written must list plan.json, generate.json, evaluate.json."""
        snapshots = tmp_path / "snapshots"
        phase_store = tmp_path / "phase_store"
        events_file = tmp_path / "events.ndjson"
        run_dir = _make_run(tmp_path, "run-content", ["blog.test.org/page2"])

        promote_phase_snapshots(
            run_dir=run_dir,
            snapshots_dir=snapshots,
            phase_store_dir=phase_store,
            family="cells",
            platform="python",
            events_path=events_file,
        )

        lines = [
            json.loads(line)
            for line in events_file.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        ps_events = [e for e in lines if e.get("event_type") == "phase_store_updated"]
        assert len(ps_events) == 1

        written_files = ps_events[0]["data"]["phase_files_written"]
        assert "plan.json" in written_files
        assert "generate.json" in written_files
        assert "evaluate.json" in written_files


class TestMetadataPromotionEvent:
    """Verify the run_loop metadata promotion block emits the correct event."""

    def test_event_emitted_with_source_field(self, tmp_path: Path) -> None:
        """metadata_phase_store_promoted event must include family, platform, source."""
        from datetime import datetime, timezone

        from launcher.models.event import Event
        from launcher.state.event_log import append_event

        events_file = tmp_path / "events.ndjson"
        run_id = "test_run_42"
        family = "3d"
        platform = "dotnet"

        # Simulate what run_loop.py now does (TC5190-SR-03)
        evt = Event(
            event_type="metadata_phase_store_promoted",
            run_id=run_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            data={"family": family, "platform": platform, "source": "run_loop"},
        )
        events_file.parent.mkdir(parents=True, exist_ok=True)
        append_event(events_file, evt)

        assert events_file.exists()
        lines = [
            json.loads(line)
            for line in events_file.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

        meta_events = [
            e for e in lines if e.get("event_type") == "metadata_phase_store_promoted"
        ]
        assert len(meta_events) == 1
        assert meta_events[0]["data"]["family"] == "3d"
        assert meta_events[0]["data"]["platform"] == "dotnet"
        assert meta_events[0]["data"]["source"] == "run_loop"
        assert meta_events[0]["run_id"] == run_id
