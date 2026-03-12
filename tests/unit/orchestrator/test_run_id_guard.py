"""SR-02: run_id without resume_from must raise ValueError."""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest


class TestRunIdRequiresResumeFrom:
    def test_run_id_without_resume_raises(self, tmp_path: Path, minimal_run_config) -> None:
        from launcher.orchestrator.run_loop import execute_run

        runs = tmp_path / "runs"
        runs.mkdir()

        with pytest.raises(ValueError, match="run_id requires resume_from"):
            asyncio.run(execute_run(
                minimal_run_config,
                run_id="some_explicit_id",
                resume_from="",
                runs_root=runs,
            ))

    def test_run_id_with_resume_does_not_raise(self, tmp_path: Path, minimal_run_config) -> None:
        """run_id + resume_from should NOT raise the guard error."""
        import json
        from launcher.orchestrator.run_loop import execute_run
        from launcher.io.run_layout import create_run_skeleton

        runs = tmp_path / "runs"
        runs.mkdir()
        run_dir = runs / "explicit_run"
        create_run_skeleton(run_dir)
        (run_dir / "run_config.json").write_text(
            json.dumps({"family": "cells", "platform": "python"}), encoding="utf-8"
        )

        # Should not raise ValueError — may fail later (no workers) but that's OK
        result = asyncio.run(execute_run(
            minimal_run_config,
            run_id="explicit_run",
            resume_from="intake",
            runs_root=runs,
            workers={},
        ))
        assert result is not None
