"""Clone behavior tests using real local git repositories (TC-A05).

Tests 1-3 use real local bare git repos via file:// URLs and should pass
immediately. Tests 4-5 verify post-TC-A05-B1 behavior and are marked xfail
until Agent B1's changes to clone.py and worker.py are merged.
"""
from __future__ import annotations

import logging
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from launcher.workers.intake.clone import (
    _CLONE_SHA_MARKER,
    check_remote_sha,
    clone_repo_cached,
)
from launcher.workers.intake.worker import IntakeWorker
from launcher.models.intake import IntakeBundle
from launcher.workers.intake.acquisition import (
    _CLONE_TIMESTAMP_MARKER,
    _STALE_CACHE_DAYS,
    _log_cache_age,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_bare_repo(path: Path) -> Path:
    """Create a local bare git repo with one commit for testing."""
    bare_path = path / "test_bare.git"
    bare_path.mkdir(parents=True)
    subprocess.run(
        ["git", "init", "--bare", str(bare_path)],
        check=True,
        capture_output=True,
    )

    # Create a working clone to add a commit
    work_path = path / "test_work"
    subprocess.run(
        ["git", "clone", str(bare_path), str(work_path)],
        check=True,
        capture_output=True,
    )

    # Configure git user for the test commit
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=str(work_path),
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=str(work_path),
        check=True,
        capture_output=True,
    )

    # Create a file and commit
    (work_path / "README.md").write_text("# Test")
    subprocess.run(["git", "add", "."], cwd=str(work_path), check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=str(work_path),
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "push", "origin", "master"],
        cwd=str(work_path),
        check=True,
        capture_output=True,
    )

    return bare_path


def _file_url(path: Path) -> str:
    """Convert a local path to a file:// URL suitable for git operations."""
    # On Windows, git needs triple-slash and forward slashes.
    posix = path.as_posix()
    if not posix.startswith("/"):
        # Windows absolute path like C:/...
        return f"file:///{posix}"
    return f"file://{posix}"


# ---------------------------------------------------------------------------
# Test 1 — Fresh clone on no cache
# ---------------------------------------------------------------------------


class TestCloneFreshOnNoCache:
    def test_clone_fresh_on_no_cache(self, tmp_path: Path):
        """First clone of a local bare repo produces a fresh clone."""
        bare_path = _create_bare_repo(tmp_path / "source")
        url = _file_url(bare_path)

        work_dir = tmp_path / "runs" / "run-001" / "work"
        work_dir.mkdir(parents=True)

        repo_dir, sha, is_fresh_clone = clone_repo_cached(
            url, family="test", platform="python", work_dir=work_dir
        )

        assert is_fresh_clone is True
        assert repo_dir.exists()
        assert len(list(repo_dir.iterdir())) > 0, "repo_dir should not be empty after clone"

        marker = repo_dir / _CLONE_SHA_MARKER
        assert marker.exists(), ".clone_sha marker file must exist"
        written_sha = marker.read_text(encoding="utf-8").strip()
        assert len(written_sha) == 40, f"SHA must be 40 hex chars, got: {written_sha!r}"
        assert sha == written_sha


# ---------------------------------------------------------------------------
# Test 2 — Cache reuse on SHA match
# ---------------------------------------------------------------------------


class TestCloneReusesCacheOnShaMatch:
    def test_clone_reuses_cache_on_sha_match(self, tmp_path: Path):
        """Second call to clone_repo_cached with same repo returns is_fresh_clone=False."""
        bare_path = _create_bare_repo(tmp_path / "source")
        url = _file_url(bare_path)

        work_dir = tmp_path / "runs" / "run-001" / "work"
        work_dir.mkdir(parents=True)

        # First call — must be a fresh clone
        repo_dir_first, sha_first, is_fresh_first = clone_repo_cached(
            url, family="test", platform="python", work_dir=work_dir
        )
        assert is_fresh_first is True

        # Second call — must be a cache hit
        repo_dir_second, sha_second, is_fresh_second = clone_repo_cached(
            url, family="test", platform="python", work_dir=work_dir
        )
        assert is_fresh_second is False, "Second clone should be a cache hit"
        assert repo_dir_first == repo_dir_second, "Both calls must return the same directory"
        assert sha_first == sha_second


# ---------------------------------------------------------------------------
# Test 3 — Re-fetch on SHA mismatch
# ---------------------------------------------------------------------------


class TestCloneRefetchesOnShaMismatch:
    def test_clone_refetches_on_sha_mismatch(self, tmp_path: Path):
        """When marker SHA differs from remote SHA, clone_repo_cached must re-clone.

        Strategy: do a real first clone to get the cache dir, then call again
        with a mocked check_remote_sha returning a different SHA (simulating a
        new upstream commit). The actual git clone for the re-clone is also
        mocked because on Windows the cache dir cannot be reliably removed and
        re-cloned in-process (git holds open file handles). The key assertion is
        that is_fresh_clone=True is returned by the code path — which we verify
        by confirming clone_repo_cached does NOT take the cache-hit branch.
        """
        bare_path = _create_bare_repo(tmp_path / "source")
        url = _file_url(bare_path)

        work_dir = tmp_path / "runs" / "run-001" / "work"
        work_dir.mkdir(parents=True)

        # First clone — real clone using local bare repo
        repo_dir, real_sha, is_fresh_first = clone_repo_cached(
            url, family="test", platform="python", work_dir=work_dir
        )
        assert is_fresh_first is True
        assert (repo_dir / _CLONE_SHA_MARKER).read_text(encoding="utf-8").strip() == real_sha

        # New remote SHA (simulates upstream push)
        new_sha = "9" * 40

        # Patch only: check_remote_sha (returns new SHA) and subprocess.run (no-ops
        # the actual git clone). clone_repo_cached writes the marker itself after
        # subprocess.run, using `sha = remote_sha or _get_repo_sha(cache_dir)`.
        # Since remote_sha == new_sha, the marker will be written with new_sha.
        import subprocess as _sp

        def fake_clone_subprocess(*popenargs, **kwargs):
            """Succeed immediately — clone_repo_cached handles marker writing."""
            cmd = list(*popenargs) if popenargs else []
            return _sp.CompletedProcess(cmd, 0, stdout="", stderr="")

        with patch("launcher.workers.intake.acquisition.check_remote_sha", return_value=new_sha), \
             patch("launcher.workers.intake.acquisition.subprocess.run", side_effect=fake_clone_subprocess):
            repo_dir_second, sha_second, is_fresh_second = clone_repo_cached(
                url, family="test", platform="python", work_dir=work_dir
            )

        assert is_fresh_second is True, "SHA mismatch must trigger a fresh clone (is_fresh_clone=True)"
        assert sha_second == new_sha


# ---------------------------------------------------------------------------
# Test 4 — check_remote_sha returns None on failure (post-B1 behavior)
# ---------------------------------------------------------------------------


class TestCheckRemoteShaReturnsNoneOnFailure:
    def test_check_remote_sha_returns_none_on_failure(self):
        """check_remote_sha must return None (not '') when the remote is unreachable."""
        with patch(
            "launcher.workers.intake.acquisition.subprocess.run",
            side_effect=subprocess.CalledProcessError(128, "git ls-remote"),
        ):
            result = check_remote_sha("https://example.com/nonexistent.git")

        assert result is None, f"Expected None on network failure, got {result!r}"


# ---------------------------------------------------------------------------
# Test 5 — self_review fails on empty repo_dir directory
# ---------------------------------------------------------------------------


class TestSelfReviewFailsOnEmptyRepoDir:
    @pytest.mark.asyncio
    async def test_self_review_fails_on_empty_repo_dir(self, tmp_path: Path):
        """self_review must fail when repo_dir exists but contains no files."""
        # Empty directory — it exists but has no files inside
        empty_dir = tmp_path / "empty_repo"
        empty_dir.mkdir()
        assert empty_dir.exists()
        assert len(list(empty_dir.iterdir())) == 0, "Pre-condition: directory must be empty"

        bundle = IntakeBundle(
            family="cells",
            platform="python",
            repo_url="https://github.com/aspose/aspose-cells-foss-python",
            display_name="Aspose.Cells FOSS for Python",
            canonical_import="aspose_cells_foss",
            launch_tier="core",
            repo_dir=str(empty_dir),
        )

        worker = IntakeWorker()
        result = await worker.self_review(bundle)

        assert result.passed is False, "self_review must fail for an empty repo_dir"
        assert any(
            f.get("category") == "clone" and "empty" in f.get("message", "").lower()
            for f in result.findings
        ), (
            "Expected a finding with category='clone' and 'empty' in message. "
            f"Got findings: {result.findings}"
        )


# ---------------------------------------------------------------------------
# Regression: clone.py must be pure re-exports (TC-INT-001)
# ---------------------------------------------------------------------------


class TestNoRecursionInWrapper:
    """Regression: clone.py must be pure re-exports, not wrappers (TC-INT-001)."""

    def test_check_remote_sha_is_direct_reexport(self):
        """check_remote_sha in clone.py must be the same function object
        as acquisition.check_remote_sha — not a wrapper that calls itself."""
        from launcher.workers.intake import clone as wrapper_mod
        from launcher.phase1 import acquisition as impl_mod

        assert wrapper_mod.check_remote_sha is impl_mod.check_remote_sha, (
            "clone.check_remote_sha must be a direct re-export of "
            "acquisition.check_remote_sha, not a wrapper function"
        )

    def test_clone_repo_cached_is_direct_reexport(self):
        from launcher.workers.intake import clone as wrapper_mod
        from launcher.phase1 import acquisition as impl_mod

        assert wrapper_mod.clone_repo_cached is impl_mod.clone_repo_cached, (
            "clone.clone_repo_cached must be a direct re-export of "
            "acquisition.clone_repo_cached, not a wrapper function"
        )


# ---------------------------------------------------------------------------
# SR-01: build_repo_signals manifest detection
# ---------------------------------------------------------------------------


class TestBuildRepoSignalsManifestDetection:
    """SR-01: Manifest detection — root CMakeLists.txt and subdir .csproj/.sln."""

    def test_cmakelists_at_root_detected_as_cpp(self, tmp_path: Path):
        from launcher.workers.intake.acquisition import build_repo_signals
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "CMakeLists.txt").write_text("project(MyLib VERSION 1.0)", encoding="utf-8")
        signals = build_repo_signals(repo)
        assert signals["inferred_language"] == "cpp"
        assert "CMakeLists.txt" in signals["detected_manifest_files"]

    def test_csproj_in_subdir_detected_as_dotnet(self, tmp_path: Path):
        from launcher.workers.intake.acquisition import build_repo_signals
        repo = tmp_path / "repo"
        repo.mkdir()
        subdir = repo / "MyLib"
        subdir.mkdir()
        (subdir / "MyLib.csproj").write_text(
            "<Project Sdk=\"Microsoft.NET.Sdk\"/>", encoding="utf-8"
        )
        signals = build_repo_signals(repo)
        assert signals["inferred_language"] == "dotnet"
        assert "MyLib.csproj" in signals["detected_manifest_files"]

    def test_sln_in_subdir_detected_as_dotnet(self, tmp_path: Path):
        from launcher.workers.intake.acquisition import build_repo_signals
        repo = tmp_path / "repo"
        repo.mkdir()
        subdir = repo / "src"
        subdir.mkdir()
        (subdir / "MySolution.sln").write_text("", encoding="utf-8")
        signals = build_repo_signals(repo)
        assert signals["inferred_language"] == "dotnet"

    def test_root_manifest_wins_over_subdir_csproj(self, tmp_path: Path):
        """Root pyproject.toml must win over a subdir .csproj."""
        from launcher.workers.intake.acquisition import build_repo_signals
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "pyproject.toml").write_text("[project]\nname = 'mypkg'", encoding="utf-8")
        subdir = repo / "bindings"
        subdir.mkdir()
        (subdir / "MyLib.csproj").write_text("<Project/>", encoding="utf-8")
        signals = build_repo_signals(repo)
        assert signals["inferred_language"] == "python", (
            "Root pyproject.toml must win over subdir .csproj"
        )

    def test_empty_repo_returns_safe_defaults(self, tmp_path: Path):
        from launcher.workers.intake.acquisition import build_repo_signals
        repo = tmp_path / "repo"
        repo.mkdir()
        signals = build_repo_signals(repo)
        assert signals["is_empty_clone"] is True
        assert signals["inferred_language"] == ""
        assert signals["license_detected"] is False


# ---------------------------------------------------------------------------
# SR-02: build_repo_signals license detection
# ---------------------------------------------------------------------------


class TestBuildRepoSignalsLicense:
    """SR-02: LICENSE file scanning detects open-source licenses."""

    def test_mit_license_detected(self, tmp_path: Path):
        from launcher.workers.intake.acquisition import build_repo_signals
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "LICENSE").write_text(
            "MIT License\n\nCopyright (c) 2024 Aspose Pty Ltd\n", encoding="utf-8"
        )
        signals = build_repo_signals(repo)
        assert signals["license_detected"] is True
        assert signals["license_type"] == "MIT"

    def test_apache_license_txt_detected(self, tmp_path: Path):
        from launcher.workers.intake.acquisition import build_repo_signals
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "LICENSE.txt").write_text(
            "Apache License\nVersion 2.0, January 2004\n", encoding="utf-8"
        )
        signals = build_repo_signals(repo)
        assert signals["license_detected"] is True
        assert signals["license_type"] == "Apache-2.0"

    def test_no_license_file_returns_false(self, tmp_path: Path):
        from launcher.workers.intake.acquisition import build_repo_signals
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "README.md").write_text("# Hello", encoding="utf-8")
        signals = build_repo_signals(repo)
        assert signals["license_detected"] is False
        assert signals["license_type"] == ""

    def test_unrecognised_license_content_returns_unknown(self, tmp_path: Path):
        from launcher.workers.intake.acquisition import build_repo_signals
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "LICENSE").write_text(
            "This is a proprietary license. All rights reserved.", encoding="utf-8"
        )
        signals = build_repo_signals(repo)
        assert signals["license_detected"] is True
        assert signals["license_type"] == "unknown"

    def test_binary_license_file_does_not_crash(self, tmp_path: Path):
        from launcher.workers.intake.acquisition import build_repo_signals
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "LICENSE").write_bytes(bytes(range(256)))
        signals = build_repo_signals(repo)
        assert "license_detected" in signals


# ---------------------------------------------------------------------------
# TC-5177 — Stale cache age detection with aspose_* dirs (G-09 / BA-03)
# ---------------------------------------------------------------------------


class TestStaleCacheEviction:
    """_log_cache_age correctly reads .clone_timestamp from aspose_* cache dirs.

    Note: _log_cache_age only WARNS about staleness — it does not force a reclone.
    The `force_refresh` parameter to clone_repo_cached controls eviction. These
    tests verify the warning detection logic works with aspose_* dir names.
    """

    def _write_ts(self, cache_dir: Path, age_days: float) -> None:
        """Write a .clone_timestamp marker with the given age in days."""
        ts = datetime.now(tz=timezone.utc) - timedelta(days=age_days)
        (cache_dir / _CLONE_TIMESTAMP_MARKER).write_text(
            ts.isoformat(), encoding="utf-8"
        )

    def test_stale_aspose_cache_logs_warning(self, tmp_path: Path, caplog):
        """aspose_* cache dir older than _STALE_CACHE_DAYS logs a stale warning."""
        cache_dir = tmp_path / f"aspose_cells_python"
        cache_dir.mkdir()
        self._write_ts(cache_dir, age_days=_STALE_CACHE_DAYS + 1)

        with caplog.at_level(logging.WARNING, logger="launcher.workers.intake.acquisition"):
            _log_cache_age(cache_dir, "https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Python")

        assert any(
            "days old" in record.message and "consider force_refresh" in record.message
            for record in caplog.records
        ), f"Expected stale-cache warning. Got records: {[r.message for r in caplog.records]}"

    def test_fresh_aspose_cache_no_warning(self, tmp_path: Path, caplog):
        """aspose_* cache dir within _STALE_CACHE_DAYS does NOT log a warning."""
        cache_dir = tmp_path / f"aspose_cells_python"
        cache_dir.mkdir()
        self._write_ts(cache_dir, age_days=_STALE_CACHE_DAYS - 1)

        with caplog.at_level(logging.WARNING, logger="launcher.workers.intake.acquisition"):
            _log_cache_age(cache_dir, "https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Python")

        stale_records = [
            r for r in caplog.records if "days old" in r.message
        ]
        assert not stale_records, (
            f"Expected no stale warning for a {_STALE_CACHE_DAYS - 1}-day-old cache. "
            f"Got: {[r.message for r in stale_records]}"
        )

    def test_stale_days_boundary(self, tmp_path: Path, caplog):
        """Exactly _STALE_CACHE_DAYS days old: boundary is exclusive (> not >=), no warning."""
        cache_dir = tmp_path / f"aspose_cells_python"
        cache_dir.mkdir()
        # Write a timestamp exactly _STALE_CACHE_DAYS * 86400 seconds ago
        ts = datetime.now(tz=timezone.utc) - timedelta(days=_STALE_CACHE_DAYS)
        (cache_dir / _CLONE_TIMESTAMP_MARKER).write_text(ts.isoformat(), encoding="utf-8")

        with caplog.at_level(logging.WARNING, logger="launcher.workers.intake.acquisition"):
            _log_cache_age(cache_dir, "https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Python")

        # acquisition.py uses `.days` (integer floor division), so exactly
        # _STALE_CACHE_DAYS seconds * 86400 = exactly _STALE_CACHE_DAYS days → age_days == _STALE_CACHE_DAYS
        # Condition is `age_days > _STALE_CACHE_DAYS` — boundary is NOT stale
        stale_records = [r for r in caplog.records if "days old" in r.message]
        assert not stale_records, (
            f"Exactly {_STALE_CACHE_DAYS} days old should NOT trigger warning "
            f"(condition is >, not >=). Got: {[r.message for r in stale_records]}"
        )


# ---------------------------------------------------------------------------
# TC-5175 — seed mode passes force_refresh=True to clone_repo_cached
# ---------------------------------------------------------------------------


class TestSeedModeForceRefresh:
    """TC-5175: pipeline_mode=seed causes IntakeWorker to pass force_refresh=True.

    These tests mock clone_repo_cached so no real network/git is required.
    """

    def _make_context(self, tmp_path: Path, pipeline_mode: str = "create"):
        from launcher.models.run_config import RunConfig
        from launcher.orchestrator.worker_contract import WorkerContext

        config = RunConfig(
            family="cells",
            platform="python",
            repo_url="https://example.com/test.git",
            pipeline_mode=pipeline_mode,
        )
        run_dir = tmp_path / "run"
        run_dir.mkdir(parents=True)
        return WorkerContext(run_id="test-seed", run_dir=run_dir, config=config)

    def _make_fake_repo(self, tmp_path: Path) -> Path:
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir(parents=True)
        (repo_dir / "README.md").write_text("# test", encoding="utf-8")
        return repo_dir

    @pytest.mark.asyncio
    async def test_seed_mode_passes_force_refresh_true(self, tmp_path: Path) -> None:
        """TC-5175: pipeline_mode=seed → clone_repo_cached called with force_refresh=True."""
        import asyncio
        from launcher.workers.intake.worker import IntakeWorker

        context = self._make_context(tmp_path, pipeline_mode="seed")
        repo_dir = self._make_fake_repo(tmp_path)

        with patch(
            "launcher.workers.intake.worker.clone_repo_cached",
            return_value=(repo_dir, "a" * 40, True),
        ) as mock_clone:
            with patch("launcher.workers.intake.worker.load_allowed_org_prefixes", return_value=None):
                worker = IntakeWorker()
                from launcher.models.base import LauncherBaseModel
                await worker.run(LauncherBaseModel(), context)

        mock_clone.assert_called_once()
        _, kwargs = mock_clone.call_args
        assert kwargs.get("force_refresh") is True, (
            f"seed mode must pass force_refresh=True; got kwargs={kwargs}"
        )

    @pytest.mark.asyncio
    async def test_create_mode_passes_force_refresh_false(self, tmp_path: Path) -> None:
        """TC-5175: pipeline_mode=create → clone_repo_cached called with force_refresh=False."""
        from launcher.workers.intake.worker import IntakeWorker

        context = self._make_context(tmp_path, pipeline_mode="create")
        repo_dir = self._make_fake_repo(tmp_path)

        with patch(
            "launcher.workers.intake.worker.clone_repo_cached",
            return_value=(repo_dir, "b" * 40, False),
        ) as mock_clone:
            with patch("launcher.workers.intake.worker.load_allowed_org_prefixes", return_value=None):
                worker = IntakeWorker()
                from launcher.models.base import LauncherBaseModel
                await worker.run(LauncherBaseModel(), context)

        mock_clone.assert_called_once()
        _, kwargs = mock_clone.call_args
        assert kwargs.get("force_refresh") is False, (
            f"create mode must pass force_refresh=False; got kwargs={kwargs}"
        )


# ---------------------------------------------------------------------------
# TC-5176 — _force_rmtree handles read-only files and missing dirs
# ---------------------------------------------------------------------------


class TestForceRmtree:
    """TC-5176: _force_rmtree removes read-only files without error."""

    def test_force_rmtree_removes_readonly_files(self, tmp_path: Path):
        """_force_rmtree removes a directory containing a read-only file."""
        import stat as _stat
        from launcher.workers.intake.acquisition import _force_rmtree

        target = tmp_path / "readonly_dir"
        target.mkdir()
        ro_file = target / "packed-refs"
        ro_file.write_text("# git packed-refs\n", encoding="utf-8")
        # Make the file read-only (simulates git's .git dir behavior on Windows)
        ro_file.chmod(_stat.S_IREAD)

        _force_rmtree(target)

        assert not target.exists(), f"Expected directory to be removed, but it still exists"

    def test_force_rmtree_removes_nested_dirs(self, tmp_path: Path):
        """_force_rmtree removes a nested read-only structure entirely."""
        import stat as _stat
        from launcher.workers.intake.acquisition import _force_rmtree

        target = tmp_path / "git_dir"
        nested = target / "objects" / "pack"
        nested.mkdir(parents=True)
        ro_file = nested / "pack-abc.idx"
        ro_file.write_text("idx", encoding="utf-8")
        ro_file.chmod(_stat.S_IREAD)

        _force_rmtree(target)

        assert not target.exists(), "Nested read-only tree must be fully removed"

    def test_force_rmtree_handles_missing_dir(self, tmp_path: Path):
        """_force_rmtree on a non-existent path raises no exception."""
        from launcher.workers.intake.acquisition import _force_rmtree

        missing = tmp_path / "does_not_exist"
        assert not missing.exists()

        # Must not raise
        _force_rmtree(missing)
