"""Tests for run_manifest.json — creation, content, and resume preservation."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest


class TestRunManifest:
    def test_manifest_created_on_fresh_run(self, tmp_path: Path, minimal_run_config) -> None:
        from launcher.orchestrator.run_loop import execute_run

        runs = tmp_path / "runs"
        runs.mkdir()

        result = asyncio.run(execute_run(
            minimal_run_config,
            workers={},
            runs_root=runs,
            source_config_path="configs/test.yaml",
        ))

        run_dir = Path(result.run_dir)
        manifest_path = run_dir / "run_manifest.json"
        assert manifest_path.exists(), "run_manifest.json should be created on fresh run"

    def test_manifest_content_matches_config(self, tmp_path: Path, minimal_run_config) -> None:
        from launcher.orchestrator.run_loop import execute_run

        runs = tmp_path / "runs"
        runs.mkdir()

        result = asyncio.run(execute_run(
            minimal_run_config,
            workers={},
            runs_root=runs,
            source_config_path="configs/test.yaml",
        ))

        run_dir = Path(result.run_dir)
        manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))

        assert manifest["family"] == "cells"
        assert manifest["platform"] == "python"
        assert manifest["run_id"] == run_dir.name
        assert "created_utc" in manifest
        assert manifest["config_path"] == "configs/test.yaml"

    def test_manifest_preserved_on_resume(self, tmp_path: Path, minimal_run_config) -> None:
        """Resumed runs must NOT overwrite the original manifest."""
        from launcher.orchestrator.run_loop import execute_run
        from launcher.io.run_layout import create_run_skeleton

        runs = tmp_path / "runs"
        runs.mkdir()

        # Create a fake previous run with a manifest
        run_dir = runs / "260101_000000_cells_python_aa00"
        create_run_skeleton(run_dir)
        (run_dir / "run_config.json").write_text(
            json.dumps({"family": "cells", "platform": "python"}),
            encoding="utf-8",
        )
        original_manifest = {
            "run_id": "260101_000000_cells_python_aa00",
            "family": "cells",
            "platform": "python",
            "created_utc": "2026-01-01T00:00:00+00:00",
            "config_path": "configs/original.yaml",
        }
        (run_dir / "run_manifest.json").write_text(
            json.dumps(original_manifest, indent=2),
            encoding="utf-8",
        )

        # Resume into same run
        result = asyncio.run(execute_run(
            minimal_run_config,
            run_id="260101_000000_cells_python_aa00",
            resume_from="intake",
            workers={},
            runs_root=runs,
            source_config_path="configs/new.yaml",
        ))

        # Manifest must still have original created_utc and config_path
        manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
        assert manifest["created_utc"] == "2026-01-01T00:00:00+00:00"
        assert manifest["config_path"] == "configs/original.yaml"

    def test_manifest_has_required_keys(self, tmp_path: Path, minimal_run_config) -> None:
        from launcher.orchestrator.run_loop import execute_run

        runs = tmp_path / "runs"
        runs.mkdir()

        result = asyncio.run(execute_run(
            minimal_run_config,
            workers={},
            runs_root=runs,
        ))

        run_dir = Path(result.run_dir)
        manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))

        required_keys = {"run_id", "family", "platform", "created_utc", "config_path"}
        assert set(manifest.keys()) == required_keys
