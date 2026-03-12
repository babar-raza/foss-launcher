"""SR-01: Verify snapshot is preserved on resume, written on fresh run."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from launcher.io.run_layout import create_run_skeleton


SENTINEL_SNAPSHOT = '{"status": "previous_run_snapshot"}\n'


def _setup_existing_run(runs_root: Path, run_id: str, family: str, platform: str) -> Path:
    """Create a run dir with skeleton + config + sentinel snapshot."""
    run_dir = runs_root / run_id
    layout = create_run_skeleton(run_dir)
    # Write run_config.json so discover_latest_run can find it
    (run_dir / "run_config.json").write_text(
        json.dumps({"family": family, "platform": platform}), encoding="utf-8"
    )
    # Overwrite snapshot with a sentinel we can verify later
    layout.snapshot_file.write_text(SENTINEL_SNAPSHOT, encoding="utf-8")
    return run_dir


class TestResumeSnapshotPreservation:
    """Snapshot must NOT be overwritten when resuming into existing run dir."""

    def test_resume_preserves_snapshot(self, tmp_path: Path, minimal_run_config) -> None:
        """On resume, the existing snapshot.json must be untouched."""
        from launcher.orchestrator.run_loop import execute_run

        runs = tmp_path / "runs"
        runs.mkdir()
        run_dir = _setup_existing_run(runs, "prev_run", "cells", "python")

        # Write a fake checkpoint so _build_resume_state finds something
        (run_dir / "intake_checkpoint.json").write_text('{"family":"cells"}', encoding="utf-8")

        # execute_run will fail at graph execution (no real workers), but
        # snapshot should already be preserved before that point.
        # We catch the expected failure.
        try:
            import asyncio
            asyncio.run(execute_run(
                minimal_run_config,
                resume_from="understand",
                runs_root=runs,
                workers={},  # empty → NO_GO return
            ))
        except Exception:
            pass

        # The sentinel snapshot should be untouched
        content = (run_dir / "snapshot.json").read_text(encoding="utf-8")
        assert content == SENTINEL_SNAPSHOT, (
            f"Snapshot was overwritten on resume! Got: {content!r}"
        )

    def test_fresh_run_writes_snapshot(self, tmp_path: Path, minimal_run_config) -> None:
        """On a fresh run (no resume), snapshot.json must be written."""
        from launcher.orchestrator.run_loop import execute_run
        import asyncio

        runs = tmp_path / "runs"
        runs.mkdir()

        result = asyncio.run(execute_run(
            minimal_run_config,
            runs_root=runs,
            workers={},  # empty → NO_GO return
        ))

        run_dir = Path(result.run_dir)
        snap = json.loads((run_dir / "snapshot.json").read_text(encoding="utf-8"))
        # Fresh snapshot should have a run_id field
        assert "run_id" in snap
