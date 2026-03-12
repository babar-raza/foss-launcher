"""Clone behavior tests using real local git repositories (TC-A05).

Tests 1-3 use real local bare git repos via file:// URLs and should pass
immediately. Tests 4-5 verify post-TC-A05-B1 behavior and are marked xfail
until Agent B1's changes to clone.py and worker.py are merged.
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from launcher.workers.intake.clone import (
    _CLONE_SHA_MARKER,
    check_remote_sha,
    clone_repo_cached,
)
from launcher.workers.intake.worker import IntakeWorker
from launcher.models.intake import IntakeBundle


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

        with patch("launcher.workers.intake.clone.check_remote_sha", return_value=new_sha), \
             patch("launcher.workers.intake.clone.subprocess.run", side_effect=fake_clone_subprocess):
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
            "launcher.workers.intake.clone.subprocess.run",
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
