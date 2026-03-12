"""Tests for run_layout — discover_latest_run and create_run_skeleton."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from launcher.io.run_layout import (
    RunLayout,
    create_run_skeleton,
    discover_latest_run,
)


# ---------------------------------------------------------------------------
# discover_latest_run
# ---------------------------------------------------------------------------


def _make_run_dir(
    runs_root: Path, name: str, family: str, platform: str
) -> Path:
    """Create a fake run directory with run_config.json."""
    d = runs_root / name
    d.mkdir(parents=True)
    config = {"family": family, "platform": platform}
    (d / "run_config.json").write_text(json.dumps(config), encoding="utf-8")
    return d


class TestDiscoverLatestRun:
    def test_returns_none_for_nonexistent_root(self, tmp_path: Path) -> None:
        result = discover_latest_run(tmp_path / "nope", "fam", "plat")
        assert result is None

    def test_returns_none_for_empty_dir(self, tmp_path: Path) -> None:
        runs = tmp_path / "runs"
        runs.mkdir()
        result = discover_latest_run(runs, "fam", "plat")
        assert result is None

    def test_finds_matching_run(self, tmp_path: Path) -> None:
        runs = tmp_path / "runs"
        runs.mkdir()
        _make_run_dir(runs, "run_a", "cells", "python")
        _make_run_dir(runs, "run_b", "note", "python")

        result = discover_latest_run(runs, "cells", "python")
        assert result is not None
        assert result.name == "run_a"

    def test_returns_newest_by_mtime(self, tmp_path: Path) -> None:
        import os
        runs = tmp_path / "runs"
        runs.mkdir()
        old = _make_run_dir(runs, "run_old", "cells", "python")
        new = _make_run_dir(runs, "run_new", "cells", "python")
        # Set deterministic mtimes (no sleep needed)
        os.utime(old, (1000.0, 1000.0))
        os.utime(new, (2000.0, 2000.0))

        result = discover_latest_run(runs, "cells", "python")
        assert result is not None
        assert result.name == "run_new"

    def test_filters_by_platform(self, tmp_path: Path) -> None:
        runs = tmp_path / "runs"
        runs.mkdir()
        _make_run_dir(runs, "run_java", "cells", "java")

        result = discover_latest_run(runs, "cells", "python")
        assert result is None

    def test_skips_dirs_without_config(self, tmp_path: Path) -> None:
        runs = tmp_path / "runs"
        runs.mkdir()
        (runs / "orphan").mkdir()  # No run_config.json

        result = discover_latest_run(runs, "cells", "python")
        assert result is None

    def test_skips_corrupted_config(self, tmp_path: Path) -> None:
        runs = tmp_path / "runs"
        runs.mkdir()
        bad = runs / "bad_run"
        bad.mkdir()
        (bad / "run_config.json").write_text("NOT JSON", encoding="utf-8")

        # Should not crash, just return None
        result = discover_latest_run(runs, "cells", "python")
        assert result is None


# ---------------------------------------------------------------------------
# create_run_skeleton
# ---------------------------------------------------------------------------


class TestCreateRunSkeleton:
    def test_creates_expected_structure(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "runs" / "test_run"
        layout = create_run_skeleton(run_dir)

        assert isinstance(layout, RunLayout)
        assert layout.events_file.exists()
        assert layout.snapshot_file.exists()
        assert layout.content_bundle_dir.is_dir()

    def test_existing_dir_does_not_fail(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "runs" / "test_run"
        run_dir.mkdir(parents=True)
        # Should not raise
        layout = create_run_skeleton(run_dir)
        assert layout.run_dir.exists()
