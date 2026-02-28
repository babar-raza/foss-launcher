"""Tests for ENGINE_VERSION drift detection (SR-04 / TC-3250 healing).

Covers:
- First-run lockfile creation
- Lock-current (no drift) returns 0
- Source drift without version bump returns 1
- ENGINE_VERSION bump regenerates lockfile (returns 0)
- --check mode blocks lockfile regeneration
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest


def _setup_fake_repo(tmp_path: Path) -> dict:
    """Create a minimal fake repo with provenance.py + W2 source file.

    Returns dict with paths needed by check_drift().
    """
    provenance_dir = tmp_path / "src" / "launch" / "provenance"
    provenance_dir.mkdir(parents=True)
    prov_module = provenance_dir / "provenance.py"
    prov_module.write_text(
        'ENGINE_VERSION = "1.0.0"\n', encoding="utf-8"
    )

    w2_dir = tmp_path / "src" / "launch" / "workers" / "w2_facts_builder"
    w2_dir.mkdir(parents=True)
    (w2_dir / "worker.py").write_text("# w2 worker\n", encoding="utf-8")

    lockfile = provenance_dir / ".engine_version_lock.json"

    return {
        "repo_root": tmp_path,
        "provenance_module": prov_module,
        "lockfile": lockfile,
        "patterns": ["src/launch/workers/w2_facts_builder/**/*.py"],
        "w2_worker": w2_dir / "worker.py",
    }


class TestFirstRun:
    def test_creates_lockfile(self, tmp_path: Path) -> None:
        """First run with no lockfile creates one and returns 0."""
        from tools.check_engine_version_drift import check_drift

        env = _setup_fake_repo(tmp_path)
        rc = check_drift(
            repo_root=env["repo_root"],
            provenance_module=env["provenance_module"],
            lockfile=env["lockfile"],
            patterns=env["patterns"],
        )
        assert rc == 0
        assert env["lockfile"].is_file()
        lock = json.loads(env["lockfile"].read_text(encoding="utf-8"))
        assert lock["engine_version"] == "1.0.0"
        assert len(lock["source_fingerprint"]) == 64  # SHA-256 hex

    def test_first_run_check_only_fails(self, tmp_path: Path) -> None:
        """First run with --check and no lockfile returns 1."""
        from tools.check_engine_version_drift import check_drift

        env = _setup_fake_repo(tmp_path)
        rc = check_drift(
            repo_root=env["repo_root"],
            provenance_module=env["provenance_module"],
            lockfile=env["lockfile"],
            patterns=env["patterns"],
            check_only=True,
        )
        assert rc == 1
        assert not env["lockfile"].is_file()


class TestLockCurrent:
    def test_no_drift_returns_zero(self, tmp_path: Path) -> None:
        """When nothing changed, returns 0."""
        from tools.check_engine_version_drift import check_drift

        env = _setup_fake_repo(tmp_path)
        # First run: create lock
        check_drift(
            repo_root=env["repo_root"],
            provenance_module=env["provenance_module"],
            lockfile=env["lockfile"],
            patterns=env["patterns"],
        )
        # Second run: no changes
        rc = check_drift(
            repo_root=env["repo_root"],
            provenance_module=env["provenance_module"],
            lockfile=env["lockfile"],
            patterns=env["patterns"],
        )
        assert rc == 0


class TestSourceDrift:
    def test_drift_detected(self, tmp_path: Path) -> None:
        """Source change without ENGINE_VERSION bump returns 1."""
        from tools.check_engine_version_drift import check_drift

        env = _setup_fake_repo(tmp_path)
        # Create lock
        check_drift(
            repo_root=env["repo_root"],
            provenance_module=env["provenance_module"],
            lockfile=env["lockfile"],
            patterns=env["patterns"],
        )
        # Modify W2 source
        env["w2_worker"].write_text(
            "# w2 worker\n# modified\n", encoding="utf-8"
        )
        # Check: should detect drift
        rc = check_drift(
            repo_root=env["repo_root"],
            provenance_module=env["provenance_module"],
            lockfile=env["lockfile"],
            patterns=env["patterns"],
        )
        assert rc == 1

    def test_drift_detected_check_only(self, tmp_path: Path) -> None:
        """--check mode also returns 1 on drift."""
        from tools.check_engine_version_drift import check_drift

        env = _setup_fake_repo(tmp_path)
        check_drift(
            repo_root=env["repo_root"],
            provenance_module=env["provenance_module"],
            lockfile=env["lockfile"],
            patterns=env["patterns"],
        )
        env["w2_worker"].write_text("# changed\n", encoding="utf-8")
        rc = check_drift(
            repo_root=env["repo_root"],
            provenance_module=env["provenance_module"],
            lockfile=env["lockfile"],
            patterns=env["patterns"],
            check_only=True,
        )
        assert rc == 1


class TestVersionBump:
    def test_bump_regenerates_lockfile(self, tmp_path: Path) -> None:
        """ENGINE_VERSION bump + source change → regenerate lock, return 0."""
        from tools.check_engine_version_drift import check_drift

        env = _setup_fake_repo(tmp_path)
        check_drift(
            repo_root=env["repo_root"],
            provenance_module=env["provenance_module"],
            lockfile=env["lockfile"],
            patterns=env["patterns"],
        )
        old_lock = json.loads(env["lockfile"].read_text(encoding="utf-8"))

        # Change source AND bump version
        env["w2_worker"].write_text("# v2 worker\n", encoding="utf-8")
        env["provenance_module"].write_text(
            'ENGINE_VERSION = "1.1.0"\n', encoding="utf-8"
        )

        rc = check_drift(
            repo_root=env["repo_root"],
            provenance_module=env["provenance_module"],
            lockfile=env["lockfile"],
            patterns=env["patterns"],
        )
        assert rc == 0
        new_lock = json.loads(env["lockfile"].read_text(encoding="utf-8"))
        assert new_lock["engine_version"] == "1.1.0"
        assert new_lock["source_fingerprint"] != old_lock["source_fingerprint"]

    def test_bump_check_only_returns_zero(self, tmp_path: Path) -> None:
        """--check with bumped ENGINE_VERSION returns 0 (but no regen)."""
        from tools.check_engine_version_drift import check_drift

        env = _setup_fake_repo(tmp_path)
        check_drift(
            repo_root=env["repo_root"],
            provenance_module=env["provenance_module"],
            lockfile=env["lockfile"],
            patterns=env["patterns"],
        )
        env["w2_worker"].write_text("# changed\n", encoding="utf-8")
        env["provenance_module"].write_text(
            'ENGINE_VERSION = "2.0.0"\n', encoding="utf-8"
        )

        rc = check_drift(
            repo_root=env["repo_root"],
            provenance_module=env["provenance_module"],
            lockfile=env["lockfile"],
            patterns=env["patterns"],
            check_only=True,
        )
        assert rc == 0
        # Lockfile NOT updated in check-only mode
        lock = json.loads(env["lockfile"].read_text(encoding="utf-8"))
        assert lock["engine_version"] == "1.0.0"  # still old
