"""Tests for latest run state snapshot (TC-3660).

Covers:
- write_latest_state: meta.json, work_refs.json, artifacts/, drafts/
- hydrate_latest_state: compatibility check, symlink/artifact/draft hydration
- _create_dir_link: cross-platform directory link creation
- _try_reuse_existing_clone: idempotent clone guard
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from launch.state_store.latest_state import (
    _create_dir_link,
    hydrate_latest_state,
    write_latest_state,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def _make_run_config(
    repo_sha: str = "abc123def456abc123def456abc123def456abc1",
    family: str = "cells",
    platform: str = "python",
) -> dict:
    return {
        "family": family,
        "target_platform": platform,
        "product_slug": "aspose-cells-python",
        "github_ref": repo_sha,
        "ruleset_version": "ruleset.v1",
        "templates_version": "templates.v1",
    }


def _setup_run_dir(tmp_path: Path, run_name: str = "r_test_run") -> Path:
    """Create a minimal run directory with skeleton."""
    run_dir = tmp_path / "runs" / run_name
    run_dir.mkdir(parents=True)
    (run_dir / "work" / "repo").mkdir(parents=True)
    (run_dir / "work" / "site").mkdir(parents=True)
    (run_dir / "work" / "workflows").mkdir(parents=True)
    (run_dir / "artifacts").mkdir(parents=True)
    (run_dir / "drafts" / "products").mkdir(parents=True)
    (run_dir / "drafts" / "docs").mkdir(parents=True)
    return run_dir


def _setup_run_with_data(tmp_path: Path) -> Path:
    """Create a run directory with artifacts, drafts, and .git markers."""
    run_dir = _setup_run_dir(tmp_path)

    # Add .git marker to repo
    (run_dir / "work" / "repo" / ".git").mkdir()

    # Add artifacts
    _write_json(run_dir / "artifacts" / "repo_inventory.json", {"items": []})
    _write_json(run_dir / "artifacts" / "page_plan.json", {"pages": []})

    # Add drafts
    (run_dir / "drafts" / "products" / "landing.md").write_text(
        "# Landing\n", encoding="utf-8"
    )
    (run_dir / "drafts" / "docs" / "intro.md").write_text(
        "# Intro\n", encoding="utf-8"
    )

    # Add snapshot
    _write_json(run_dir / "snapshot.json", {"state": "DONE"})

    # Add validation report
    _write_json(
        run_dir / "artifacts" / "validation_report.json",
        {"gates": [{"name": "g1", "ok": True}, {"name": "g2", "ok": True}]},
    )

    return run_dir


# ---------------------------------------------------------------------------
# TestWriteLatestState
# ---------------------------------------------------------------------------


class TestWriteLatestState:
    def test_creates_latest_dir(self, tmp_path: Path) -> None:
        """write_latest_state creates latest/ with meta.json and work_refs.json."""
        run_dir = _setup_run_with_data(tmp_path)
        store_root = tmp_path / "store"
        store_key = Path("cells/python")
        rc = _make_run_config()

        write_latest_state(run_dir, rc, store_root, store_key)

        latest = store_root / store_key / "latest"
        assert (latest / "meta.json").is_file()
        assert (latest / "work_refs.json").is_file()

    def test_meta_json_fields(self, tmp_path: Path) -> None:
        """meta.json contains all required fields."""
        run_dir = _setup_run_with_data(tmp_path)
        store_root = tmp_path / "store"
        store_key = Path("cells/python")
        rc = _make_run_config()

        write_latest_state(run_dir, rc, store_root, store_key)

        meta = json.loads(
            (store_root / store_key / "latest" / "meta.json").read_text(encoding="utf-8")
        )
        assert meta["schema_version"] == "1.0"
        assert meta["run_id"] == run_dir.name
        assert meta["repo_sha"] == rc["github_ref"]
        assert meta["last_run_state"] == "DONE"
        assert meta["failed_gate_count"] == 0
        assert meta["drafts_count"] == 2
        assert len(meta["artifact_names"]) == 3  # repo_inventory, page_plan, validation_report
        assert "interpretation_sig" in meta
        assert "timestamp" in meta

    def test_work_refs_records_git_dirs(self, tmp_path: Path) -> None:
        """work_refs.json records paths for dirs with .git markers."""
        run_dir = _setup_run_with_data(tmp_path)
        store_root = tmp_path / "store"
        store_key = Path("cells/python")
        rc = _make_run_config()

        write_latest_state(run_dir, rc, store_root, store_key)

        refs = json.loads(
            (store_root / store_key / "latest" / "work_refs.json").read_text(
                encoding="utf-8"
            )
        )
        assert refs["repo"] is not None  # has .git
        assert refs["site"] is None  # no .git
        assert refs["workflows"] is None  # no .git

    def test_copies_artifacts(self, tmp_path: Path) -> None:
        """Artifacts are copied to latest/artifacts/."""
        run_dir = _setup_run_with_data(tmp_path)
        store_root = tmp_path / "store"
        store_key = Path("cells/python")
        rc = _make_run_config()

        write_latest_state(run_dir, rc, store_root, store_key)

        latest_artifacts = store_root / store_key / "latest" / "artifacts"
        assert (latest_artifacts / "repo_inventory.json").is_file()
        assert (latest_artifacts / "page_plan.json").is_file()

    def test_copies_drafts(self, tmp_path: Path) -> None:
        """Drafts are copied preserving subdirectory structure."""
        run_dir = _setup_run_with_data(tmp_path)
        store_root = tmp_path / "store"
        store_key = Path("cells/python")
        rc = _make_run_config()

        write_latest_state(run_dir, rc, store_root, store_key)

        latest_drafts = store_root / store_key / "latest" / "drafts"
        assert (latest_drafts / "products" / "landing.md").is_file()
        assert (latest_drafts / "docs" / "intro.md").is_file()

    def test_atomic_replaces_existing(self, tmp_path: Path) -> None:
        """Second write replaces the first atomically."""
        run_dir = _setup_run_with_data(tmp_path)
        store_root = tmp_path / "store"
        store_key = Path("cells/python")
        rc = _make_run_config()

        write_latest_state(run_dir, rc, store_root, store_key)

        # Add a new artifact and re-write
        _write_json(run_dir / "artifacts" / "extra.json", {"new": True})
        write_latest_state(run_dir, rc, store_root, store_key)

        latest_artifacts = store_root / store_key / "latest" / "artifacts"
        assert (latest_artifacts / "extra.json").is_file()

    def test_handles_missing_snapshot(self, tmp_path: Path) -> None:
        """write_latest_state works even if snapshot.json is absent."""
        run_dir = _setup_run_dir(tmp_path)
        store_root = tmp_path / "store"
        store_key = Path("cells/python")
        rc = _make_run_config()

        write_latest_state(run_dir, rc, store_root, store_key)

        meta = json.loads(
            (store_root / store_key / "latest" / "meta.json").read_text(encoding="utf-8")
        )
        assert meta["last_run_state"] == ""
        assert meta["failed_gate_count"] == -1


# ---------------------------------------------------------------------------
# TestHydrateLatestState
# ---------------------------------------------------------------------------


class TestHydrateLatestState:
    def test_returns_zero_no_snapshot(self, tmp_path: Path) -> None:
        """Returns 0 when no latest/ directory exists."""
        run_dir = _setup_run_dir(tmp_path)
        store_root = tmp_path / "store"
        store_key = Path("cells/python")
        rc = _make_run_config()

        count = hydrate_latest_state(run_dir, rc, store_root, store_key)
        assert count == 0

    def test_returns_zero_sha_mismatch(self, tmp_path: Path) -> None:
        """Returns 0 when repo SHA doesn't match."""
        run_dir_old = _setup_run_with_data(tmp_path)
        store_root = tmp_path / "store"
        store_key = Path("cells/python")
        rc_old = _make_run_config()

        write_latest_state(run_dir_old, rc_old, store_root, store_key)

        # New run with different SHA
        run_dir_new = _setup_run_dir(tmp_path, "r_new_run")
        rc_new = _make_run_config(repo_sha="deadbeefdeadbeefdeadbeefdeadbeefdeadbeef")

        count = hydrate_latest_state(run_dir_new, rc_new, store_root, store_key)
        assert count == 0

    def test_returns_zero_sig_mismatch(self, tmp_path: Path) -> None:
        """Returns 0 when interpretation signature doesn't match."""
        run_dir_old = _setup_run_with_data(tmp_path)
        store_root = tmp_path / "store"
        store_key = Path("cells/python")
        rc_old = _make_run_config()

        write_latest_state(run_dir_old, rc_old, store_root, store_key)

        # New run with different ruleset (changes sig)
        run_dir_new = _setup_run_dir(tmp_path, "r_new_run")
        rc_new = _make_run_config()
        rc_new["ruleset_version"] = "ruleset.v999"

        count = hydrate_latest_state(run_dir_new, rc_new, store_root, store_key)
        assert count == 0

    def test_hydrates_artifacts(self, tmp_path: Path) -> None:
        """Compatible snapshot hydrates artifacts into new run dir."""
        run_dir_old = _setup_run_with_data(tmp_path)
        store_root = tmp_path / "store"
        store_key = Path("cells/python")
        rc = _make_run_config()

        write_latest_state(run_dir_old, rc, store_root, store_key)

        # New run with same config
        run_dir_new = _setup_run_dir(tmp_path, "r_new_run")
        count = hydrate_latest_state(run_dir_new, rc, store_root, store_key)

        assert count > 0
        assert (run_dir_new / "artifacts" / "repo_inventory.json").is_file()
        assert (run_dir_new / "artifacts" / "page_plan.json").is_file()

    def test_hydrates_drafts(self, tmp_path: Path) -> None:
        """Compatible snapshot hydrates drafts into new run dir."""
        run_dir_old = _setup_run_with_data(tmp_path)
        store_root = tmp_path / "store"
        store_key = Path("cells/python")
        rc = _make_run_config()

        write_latest_state(run_dir_old, rc, store_root, store_key)

        # New run with same config
        run_dir_new = _setup_run_dir(tmp_path, "r_new_run")
        hydrate_latest_state(run_dir_new, rc, store_root, store_key)

        assert (run_dir_new / "drafts" / "products" / "landing.md").is_file()
        assert (run_dir_new / "drafts" / "docs" / "intro.md").is_file()

    def test_non_overwriting_artifacts(self, tmp_path: Path) -> None:
        """Hydration does NOT overwrite existing artifacts."""
        run_dir_old = _setup_run_with_data(tmp_path)
        store_root = tmp_path / "store"
        store_key = Path("cells/python")
        rc = _make_run_config()

        write_latest_state(run_dir_old, rc, store_root, store_key)

        # New run with an existing artifact
        run_dir_new = _setup_run_dir(tmp_path, "r_new_run")
        _write_json(
            run_dir_new / "artifacts" / "repo_inventory.json",
            {"existing": True},
        )

        hydrate_latest_state(run_dir_new, rc, store_root, store_key)

        # The existing artifact should NOT be overwritten
        data = json.loads(
            (run_dir_new / "artifacts" / "repo_inventory.json").read_text(
                encoding="utf-8"
            )
        )
        assert data["existing"] is True

    def test_non_overwriting_drafts(self, tmp_path: Path) -> None:
        """Hydration does NOT overwrite existing drafts."""
        run_dir_old = _setup_run_with_data(tmp_path)
        store_root = tmp_path / "store"
        store_key = Path("cells/python")
        rc = _make_run_config()

        write_latest_state(run_dir_old, rc, store_root, store_key)

        # New run with an existing draft
        run_dir_new = _setup_run_dir(tmp_path, "r_new_run")
        (run_dir_new / "drafts" / "products" / "landing.md").write_text(
            "# Existing\n", encoding="utf-8"
        )

        hydrate_latest_state(run_dir_new, rc, store_root, store_key)

        content = (run_dir_new / "drafts" / "products" / "landing.md").read_text(
            encoding="utf-8"
        )
        assert content == "# Existing\n"


# ---------------------------------------------------------------------------
# TestCreateDirLink
# ---------------------------------------------------------------------------


class TestCreateDirLink:
    def test_symlink_success(self, tmp_path: Path) -> None:
        """_create_dir_link creates a working directory link."""
        target = tmp_path / "target"
        target.mkdir()
        (target / "file.txt").write_text("hello", encoding="utf-8")

        link = tmp_path / "link"
        result = _create_dir_link(target, link)

        if result:
            # Link was created — verify it works
            assert (link / "file.txt").read_text(encoding="utf-8") == "hello"
        else:
            # Platform doesn't support symlinks/junctions without privileges
            pytest.skip("symlink/junction creation not available")

    def test_link_to_nonexistent_target(self, tmp_path: Path) -> None:
        """_create_dir_link behavior with nonexistent target is platform-dependent.

        On Windows, junctions succeed even for nonexistent targets.
        On Linux, symlinks succeed but the link is dangling.
        """
        target = tmp_path / "nonexistent"
        link = tmp_path / "link"
        result = _create_dir_link(target, link)
        # On both platforms, the call may succeed (dangling link/junction)
        # so we just verify it returns a bool without crashing
        assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# TestTryReuseExistingClone
# ---------------------------------------------------------------------------


class TestTryReuseExistingClone:
    def test_no_git_returns_none(self, tmp_path: Path) -> None:
        """Returns None when .git directory is absent."""
        from launch.workers.w1_repo_scout.clone import _try_reuse_existing_clone

        target = tmp_path / "repo"
        target.mkdir()

        result = _try_reuse_existing_clone(
            target, "abc123def456abc123def456abc123def456abc1", "product"
        )
        assert result is None

    def test_matching_sha_returns_resolved(self, tmp_path: Path) -> None:
        """Returns ResolvedRepo when .git exists and SHA matches."""
        from launch.workers.w1_repo_scout.clone import _try_reuse_existing_clone

        target = tmp_path / "repo"
        target.mkdir()
        (target / ".git").mkdir()

        sha = "abc123def456abc123def456abc123def456abc1"

        with patch("subprocess.run") as mock_run:
            # First call: git rev-parse HEAD
            mock_run.return_value.stdout = sha + "\n"
            mock_run.return_value.returncode = 0

            result = _try_reuse_existing_clone(target, sha, "product")

        assert result is not None
        assert result.resolved_sha == sha

    def test_reuse_populates_repo_url(self, tmp_path: Path) -> None:
        """SR-03: repo_url param is passed through to ResolvedRepo."""
        from launch.workers.w1_repo_scout.clone import _try_reuse_existing_clone

        target = tmp_path / "repo"
        target.mkdir()
        (target / ".git").mkdir()

        sha = "abc123def456abc123def456abc123def456abc1"
        url = "https://github.com/example/repo"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value.stdout = sha + "\n"
            mock_run.return_value.returncode = 0

            result = _try_reuse_existing_clone(
                target, sha, "product", repo_url=url,
            )

        assert result is not None
        assert result.repo_url == url

    def test_mismatched_sha_removes_dir(self, tmp_path: Path) -> None:
        """Removes stale clone and returns None on SHA mismatch."""
        from launch.workers.w1_repo_scout.clone import _try_reuse_existing_clone

        target = tmp_path / "repo"
        target.mkdir()
        (target / ".git").mkdir()
        (target / "somefile.txt").write_text("data", encoding="utf-8")

        expected_sha = "abc123def456abc123def456abc123def456abc1"
        actual_sha = "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value.stdout = actual_sha + "\n"
            mock_run.return_value.returncode = 0

            result = _try_reuse_existing_clone(target, expected_sha, "product")

        assert result is None
        # Directory was removed and recreated empty
        assert target.is_dir()
        assert not (target / "somefile.txt").exists()

    def test_non_sha_ref_reclones(self, tmp_path: Path) -> None:
        """Non-SHA refs (branch names) always trigger re-clone."""
        from launch.workers.w1_repo_scout.clone import _try_reuse_existing_clone

        target = tmp_path / "repo"
        target.mkdir()
        (target / ".git").mkdir()

        result = _try_reuse_existing_clone(target, "main", "product")

        assert result is None

    def test_git_error_removes_dir(self, tmp_path: Path) -> None:
        """Git errors cause removal and return None."""
        from launch.workers.w1_repo_scout.clone import _try_reuse_existing_clone

        target = tmp_path / "repo"
        target.mkdir()
        (target / ".git").mkdir()

        sha = "abc123def456abc123def456abc123def456abc1"

        with patch("subprocess.run", side_effect=FileNotFoundError("git not found")):
            result = _try_reuse_existing_clone(target, sha, "product")

        assert result is None


# ---------------------------------------------------------------------------
# TestRoundTrip
# ---------------------------------------------------------------------------


class TestRoundTrip:
    def test_write_then_hydrate_roundtrip(self, tmp_path: Path) -> None:
        """Full round-trip: write snapshot, hydrate into fresh run."""
        run_dir_old = _setup_run_with_data(tmp_path)
        store_root = tmp_path / "store"
        store_key = Path("cells/python")
        rc = _make_run_config()

        write_latest_state(run_dir_old, rc, store_root, store_key)

        # Fresh run
        run_dir_new = _setup_run_dir(tmp_path, "r_fresh")
        count = hydrate_latest_state(run_dir_new, rc, store_root, store_key)

        # Should have hydrated artifacts + drafts
        assert count >= 4  # 3 artifacts + 2 drafts (minus validation_report already counted)
        assert (run_dir_new / "artifacts" / "repo_inventory.json").is_file()
        assert (run_dir_new / "drafts" / "products" / "landing.md").is_file()


# ---------------------------------------------------------------------------
# TestWriteMetrics (SR-02)
# ---------------------------------------------------------------------------


class TestWriteMetrics:
    """SR-02 / GAP-02: Structured counter logs from write_latest_state()."""

    def test_write_emits_metrics_log(self, tmp_path: Path, caplog) -> None:
        """write_latest_state emits a structured write_metrics log line."""
        run_dir = _setup_run_with_data(tmp_path)
        store_root = tmp_path / "store"
        store_key = Path("cells/python")
        rc = _make_run_config()

        with caplog.at_level(logging.INFO, logger="launch.state_store.latest_state"):
            write_latest_state(run_dir, rc, store_root, store_key)

        metrics_lines = [r for r in caplog.records if "write_metrics" in r.message]
        assert len(metrics_lines) == 1
        msg = metrics_lines[0].message
        # _setup_run_with_data creates 3 JSON artifacts + 2 MD drafts + 1 work ref (repo)
        assert "artifacts=3" in msg
        assert "drafts=2" in msg
        assert "work_refs=1" in msg
        assert "duration_seconds=" in msg

    def test_write_empty_run_emits_zero_counters(self, tmp_path: Path, caplog) -> None:
        """write_latest_state with empty run dir emits zero counters."""
        run_dir = _setup_run_dir(tmp_path)  # no artifacts, no drafts
        store_root = tmp_path / "store"
        store_key = Path("cells/python")
        rc = _make_run_config()

        with caplog.at_level(logging.INFO, logger="launch.state_store.latest_state"):
            write_latest_state(run_dir, rc, store_root, store_key)

        metrics_lines = [r for r in caplog.records if "write_metrics" in r.message]
        assert len(metrics_lines) == 1
        msg = metrics_lines[0].message
        assert "artifacts=0" in msg
        assert "drafts=0" in msg
        assert "work_refs=0" in msg


# ---------------------------------------------------------------------------
# TestHydrateMetrics (SR-02)
# ---------------------------------------------------------------------------


class TestHydrateMetrics:
    """SR-02 / GAP-02: Structured counter logs from hydrate_latest_state()."""

    def test_hydrate_emits_metrics_log(self, tmp_path: Path, caplog) -> None:
        """hydrate_latest_state emits a structured hydrate_metrics log line."""
        run_dir_old = _setup_run_with_data(tmp_path)
        store_root = tmp_path / "store"
        store_key = Path("cells/python")
        rc = _make_run_config()

        write_latest_state(run_dir_old, rc, store_root, store_key)

        run_dir_new = _setup_run_dir(tmp_path, "r_new_run")
        with caplog.at_level(logging.INFO, logger="launch.state_store.latest_state"):
            hydrate_latest_state(run_dir_new, rc, store_root, store_key)

        metrics_lines = [r for r in caplog.records if "hydrate_metrics" in r.message]
        assert len(metrics_lines) == 1
        msg = metrics_lines[0].message
        assert "artifacts=" in msg
        assert "drafts=" in msg
        assert "links_created=" in msg
        assert "links_failed=" in msg
        assert "duration_seconds=" in msg

    def test_hydrate_skip_no_meta_emits_reason(self, tmp_path: Path, caplog) -> None:
        """hydrate_latest_state emits skip reason when no meta.json exists."""
        run_dir = _setup_run_dir(tmp_path)
        store_root = tmp_path / "store"
        store_key = Path("cells/python")
        rc = _make_run_config()

        with caplog.at_level(logging.INFO, logger="launch.state_store.latest_state"):
            hydrate_latest_state(run_dir, rc, store_root, store_key)

        skip_lines = [r for r in caplog.records if "hydrate_skip" in r.message]
        assert len(skip_lines) == 1
        assert "reason=no_meta" in skip_lines[0].message

    def test_hydrate_skip_incompatible_emits_reason(self, tmp_path: Path, caplog) -> None:
        """hydrate_latest_state emits skip reason on SHA/sig mismatch."""
        run_dir_old = _setup_run_with_data(tmp_path)
        store_root = tmp_path / "store"
        store_key = Path("cells/python")
        rc_old = _make_run_config()

        write_latest_state(run_dir_old, rc_old, store_root, store_key)

        run_dir_new = _setup_run_dir(tmp_path, "r_new_run")
        rc_new = _make_run_config(repo_sha="deadbeefdeadbeefdeadbeefdeadbeefdeadbeef")

        with caplog.at_level(logging.INFO, logger="launch.state_store.latest_state"):
            hydrate_latest_state(run_dir_new, rc_new, store_root, store_key)

        skip_lines = [r for r in caplog.records if "hydrate_skip" in r.message]
        assert len(skip_lines) == 1
        assert "reason=incompatible" in skip_lines[0].message
