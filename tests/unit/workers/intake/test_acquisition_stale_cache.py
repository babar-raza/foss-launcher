"""Regression tests for TC-5300 stale-cache fallback in clone_repo_cached().

Verifies that when a fresh clone fails:
- If a stale cache existed, it is restored and returned (is_fresh=False)
- If no stale cache existed, the original exception is re-raised

Also verifies that on successful fresh clone, any stale backup is cleaned up.
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from launcher.workers.intake.acquisition import (
    _CLONE_SHA_MARKER,
    _CLONE_URL_MARKER,
    clone_repo_cached,
)


def _make_fake_cache(cache_dir: Path, sha: str, url: str) -> None:
    """Create a minimal fake cache directory with marker files."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / _CLONE_SHA_MARKER).write_text(sha, encoding="utf-8")
    (cache_dir / _CLONE_URL_MARKER).write_text(url, encoding="utf-8")
    (cache_dir / "README.md").write_text("fake repo", encoding="utf-8")


# ---------------------------------------------------------------------------
# Helpers that patch network calls
# ---------------------------------------------------------------------------

_FAKE_URL = "https://github.com/test-org/test-repo"
_FAKE_SHA_OLD = "aabbccdd" * 5  # 40 hex chars
_FAKE_SHA_NEW = "11223344" * 5


def _check_remote_sha_new(_url: str) -> str:
    return _FAKE_SHA_NEW


def _check_remote_sha_none(_url: str) -> str | None:
    return None


# ---------------------------------------------------------------------------
# Test 1: Clone failure with stale cache → falls back to stale cache
# ---------------------------------------------------------------------------


def test_clone_failure_with_stale_cache_falls_back(tmp_path: Path) -> None:
    """When fresh clone fails and stale cache exists, stale cache is returned."""
    # Build a fake existing cache (old SHA, so will try refresh)
    work_dir = tmp_path / "runs" / "test_run"
    work_dir.mkdir(parents=True)
    cache_dir = tmp_path / ".clone_cache" / "test-org" / "test" / "test" / "python"
    _make_fake_cache(cache_dir, _FAKE_SHA_OLD, _FAKE_URL)

    def _fake_get_cache_dir(*args, **kwargs):
        return cache_dir

    with (
        patch(
            "launcher.workers.intake.acquisition.check_remote_sha",
            side_effect=_check_remote_sha_new,
        ),
        patch(
            "launcher.workers.intake.acquisition._get_cache_dir",
            side_effect=_fake_get_cache_dir,
        ),
        patch(
            "launcher.workers.intake.acquisition._check_url_collision",
        ),
        patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "git")),
    ):
        result_dir, result_sha, is_fresh = clone_repo_cached(
            repo_url=_FAKE_URL,
            family="test",
            platform="python",
            work_dir=work_dir,
        )

    assert result_dir == cache_dir
    assert result_sha == _FAKE_SHA_OLD
    assert is_fresh is False
    # Stale cache must be restored
    assert cache_dir.exists()
    assert (cache_dir / _CLONE_SHA_MARKER).read_text(encoding="utf-8").strip() == _FAKE_SHA_OLD
    # Stale backup must be cleaned up on return path (it was renamed to cache_dir)
    stale_backup = cache_dir.parent / (cache_dir.name + "_stale")
    assert not stale_backup.exists()


# ---------------------------------------------------------------------------
# Test 2: Clone failure without stale cache → re-raises exception
# ---------------------------------------------------------------------------


def test_clone_failure_without_stale_cache_reraises(tmp_path: Path) -> None:
    """When fresh clone fails and no stale cache exists, the exception is re-raised."""
    work_dir = tmp_path / "runs" / "test_run"
    work_dir.mkdir(parents=True)
    cache_dir = tmp_path / ".clone_cache" / "test-org" / "test" / "test" / "python"
    # No cache pre-exists

    def _fake_get_cache_dir(*args, **kwargs):
        return cache_dir

    with (
        patch(
            "launcher.workers.intake.acquisition.check_remote_sha",
            side_effect=_check_remote_sha_new,
        ),
        patch(
            "launcher.workers.intake.acquisition._get_cache_dir",
            side_effect=_fake_get_cache_dir,
        ),
        patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "git")),
    ):
        with pytest.raises(subprocess.CalledProcessError):
            clone_repo_cached(
                repo_url=_FAKE_URL,
                family="test",
                platform="python",
                work_dir=work_dir,
            )


# ---------------------------------------------------------------------------
# Test 3: Clone success → stale backup is cleaned up
# ---------------------------------------------------------------------------


def test_clone_success_removes_stale_backup(tmp_path: Path) -> None:
    """When fresh clone succeeds, any stale backup directory is removed."""
    work_dir = tmp_path / "runs" / "test_run"
    work_dir.mkdir(parents=True)
    cache_dir = tmp_path / ".clone_cache" / "test-org" / "test" / "test" / "python"
    _make_fake_cache(cache_dir, _FAKE_SHA_OLD, _FAKE_URL)

    def _fake_get_cache_dir(*args, **kwargs):
        return cache_dir

    def _fake_subprocess_run(cmd, **kwargs):
        # Simulate git clone by writing a fake marker into cache_dir
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / _CLONE_SHA_MARKER).write_text(_FAKE_SHA_NEW, encoding="utf-8")
        (cache_dir / _CLONE_URL_MARKER).write_text(_FAKE_URL, encoding="utf-8")
        result = MagicMock()
        result.returncode = 0
        return result

    def _fake_get_repo_sha(_dir: Path) -> str:
        return _FAKE_SHA_NEW

    with (
        patch(
            "launcher.workers.intake.acquisition.check_remote_sha",
            side_effect=_check_remote_sha_new,
        ),
        patch(
            "launcher.workers.intake.acquisition._get_cache_dir",
            side_effect=_fake_get_cache_dir,
        ),
        patch(
            "launcher.workers.intake.acquisition._check_url_collision",
        ),
        patch("subprocess.run", side_effect=_fake_subprocess_run),
        patch(
            "launcher.workers.intake.acquisition._get_repo_sha",
            side_effect=_fake_get_repo_sha,
        ),
        patch("launcher.workers.intake.acquisition._write_cache_timestamp"),
    ):
        result_dir, result_sha, is_fresh = clone_repo_cached(
            repo_url=_FAKE_URL,
            family="test",
            platform="python",
            work_dir=work_dir,
        )

    assert is_fresh is True
    # Stale backup must be gone
    stale_backup = cache_dir.parent / (cache_dir.name + "_stale")
    assert not stale_backup.exists()


# ---------------------------------------------------------------------------
# Test 4: Cache hit (SHA matches) → no clone attempted, returned directly
# ---------------------------------------------------------------------------


def test_cache_hit_returns_without_clone(tmp_path: Path) -> None:
    """When cached SHA matches remote SHA, clone is skipped entirely."""
    work_dir = tmp_path / "runs" / "test_run"
    work_dir.mkdir(parents=True)
    cache_dir = tmp_path / ".clone_cache" / "test-org" / "test" / "test" / "python"
    _make_fake_cache(cache_dir, _FAKE_SHA_NEW, _FAKE_URL)

    def _fake_get_cache_dir(*args, **kwargs):
        return cache_dir

    with (
        patch(
            "launcher.workers.intake.acquisition.check_remote_sha",
            side_effect=_check_remote_sha_new,
        ),
        patch(
            "launcher.workers.intake.acquisition._get_cache_dir",
            side_effect=_fake_get_cache_dir,
        ),
        patch(
            "launcher.workers.intake.acquisition._check_url_collision",
        ),
        patch("launcher.workers.intake.acquisition._log_cache_age"),
        patch("subprocess.run") as mock_run,
    ):
        result_dir, result_sha, is_fresh = clone_repo_cached(
            repo_url=_FAKE_URL,
            family="test",
            platform="python",
            work_dir=work_dir,
        )

    # subprocess.run must NOT have been called (cache hit)
    mock_run.assert_not_called()
    assert result_dir == cache_dir
    assert result_sha == _FAKE_SHA_NEW
    assert is_fresh is False
