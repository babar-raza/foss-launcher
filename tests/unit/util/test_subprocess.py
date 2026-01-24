"""Tests for secure subprocess wrapper (Guarantee J)."""

import pytest
from pathlib import Path
import tempfile

from launch.util.subprocess import (
    SubprocessSecurityError,
    run,
    check_output,
    Popen,
    _is_under_work_repo,
)


class TestIsUnderWorkRepo:
    """Tests for _is_under_work_repo helper function."""

    def test_none_cwd_returns_false(self):
        """None cwd should return False."""
        assert _is_under_work_repo(None) is False

    def test_cwd_under_work_repo_pattern(self):
        """Path containing /work/repo/ should be detected."""
        assert _is_under_work_repo("/path/to/runs/123/work/repo/subdir") is True

    def test_cwd_under_work_repo_windows(self):
        """Windows path containing \\work\\repo\\ should be detected."""
        assert _is_under_work_repo("C:\\runs\\123\\work\\repo\\subdir") is True

    def test_cwd_not_under_work_repo(self):
        """Path not containing work/repo should return False."""
        assert _is_under_work_repo("/path/to/some/other/dir") is False

    def test_cwd_with_run_dir_exact(self, tmp_path):
        """Test with explicit run_dir - exact work/repo path."""
        run_dir = tmp_path / "runs" / "123"
        work_repo = run_dir / "work" / "repo"
        work_repo.mkdir(parents=True, exist_ok=True)

        assert _is_under_work_repo(work_repo, run_dir) is True

    def test_cwd_with_run_dir_subdirectory(self, tmp_path):
        """Test with explicit run_dir - subdirectory under work/repo."""
        run_dir = tmp_path / "runs" / "123"
        work_repo = run_dir / "work" / "repo" / "subdir" / "deep"
        work_repo.mkdir(parents=True, exist_ok=True)

        assert _is_under_work_repo(work_repo, run_dir) is True

    def test_cwd_with_run_dir_sibling(self, tmp_path):
        """Test with explicit run_dir - sibling directory (not under work/repo)."""
        run_dir = tmp_path / "runs" / "123"
        artifacts = run_dir / "artifacts"
        artifacts.mkdir(parents=True, exist_ok=True)

        assert _is_under_work_repo(artifacts, run_dir) is False


class TestSubprocessRun:
    """Tests for secure subprocess.run wrapper."""

    def test_run_with_no_cwd_succeeds(self):
        """subprocess.run with no cwd should succeed."""
        result = run(["python", "--version"], capture_output=True)
        assert result.returncode == 0

    def test_run_with_safe_cwd_succeeds(self, tmp_path):
        """subprocess.run with safe cwd should succeed."""
        safe_dir = tmp_path / "safe"
        safe_dir.mkdir()

        result = run(["python", "--version"], cwd=safe_dir, capture_output=True)
        assert result.returncode == 0

    def test_run_with_untrusted_cwd_raises(self, tmp_path):
        """subprocess.run with cwd under work/repo should raise."""
        untrusted_dir = tmp_path / "runs" / "123" / "work" / "repo"
        untrusted_dir.mkdir(parents=True, exist_ok=True)

        with pytest.raises(SubprocessSecurityError) as exc_info:
            run(["python", "--version"], cwd=untrusted_dir)

        assert exc_info.value.error_code == "SECURITY_UNTRUSTED_EXECUTION"
        assert "work/repo" in str(exc_info.value)

    def test_run_with_untrusted_cwd_and_run_dir_raises(self, tmp_path):
        """subprocess.run with explicit run_dir validation should raise."""
        run_dir = tmp_path / "runs" / "123"
        untrusted_dir = run_dir / "work" / "repo" / "subdir"
        untrusted_dir.mkdir(parents=True, exist_ok=True)

        with pytest.raises(SubprocessSecurityError) as exc_info:
            run(["python", "--version"], cwd=untrusted_dir, run_dir=run_dir)

        assert exc_info.value.error_code == "SECURITY_UNTRUSTED_EXECUTION"

    def test_run_with_artifacts_dir_succeeds(self, tmp_path):
        """subprocess.run with cwd under artifacts/ should succeed (not work/repo)."""
        run_dir = tmp_path / "runs" / "123"
        artifacts_dir = run_dir / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        result = run(["python", "--version"], cwd=artifacts_dir, run_dir=run_dir, capture_output=True)
        assert result.returncode == 0


class TestSubprocessCheckOutput:
    """Tests for secure subprocess.check_output wrapper."""

    def test_check_output_with_no_cwd_succeeds(self):
        """subprocess.check_output with no cwd should succeed."""
        output = check_output(["python", "--version"])
        assert b"Python" in output

    def test_check_output_with_safe_cwd_succeeds(self, tmp_path):
        """subprocess.check_output with safe cwd should succeed."""
        safe_dir = tmp_path / "safe"
        safe_dir.mkdir()

        output = check_output(["python", "--version"], cwd=safe_dir)
        assert b"Python" in output

    def test_check_output_with_untrusted_cwd_raises(self, tmp_path):
        """subprocess.check_output with cwd under work/repo should raise."""
        untrusted_dir = tmp_path / "runs" / "123" / "work" / "repo"
        untrusted_dir.mkdir(parents=True, exist_ok=True)

        with pytest.raises(SubprocessSecurityError) as exc_info:
            check_output(["python", "--version"], cwd=untrusted_dir)

        assert exc_info.value.error_code == "SECURITY_UNTRUSTED_EXECUTION"


class TestSubprocessPopen:
    """Tests for secure subprocess.Popen wrapper."""

    def test_popen_with_no_cwd_succeeds(self):
        """subprocess.Popen with no cwd should succeed."""
        proc = Popen(["python", "--version"], stdout=-1, stderr=-1)
        stdout, stderr = proc.communicate()
        assert proc.returncode == 0

    def test_popen_with_safe_cwd_succeeds(self, tmp_path):
        """subprocess.Popen with safe cwd should succeed."""
        safe_dir = tmp_path / "safe"
        safe_dir.mkdir()

        proc = Popen(["python", "--version"], cwd=safe_dir, stdout=-1, stderr=-1)
        stdout, stderr = proc.communicate()
        assert proc.returncode == 0

    def test_popen_with_untrusted_cwd_raises(self, tmp_path):
        """subprocess.Popen with cwd under work/repo should raise."""
        untrusted_dir = tmp_path / "runs" / "123" / "work" / "repo"
        untrusted_dir.mkdir(parents=True, exist_ok=True)

        with pytest.raises(SubprocessSecurityError) as exc_info:
            Popen(["python", "--version"], cwd=untrusted_dir)

        assert exc_info.value.error_code == "SECURITY_UNTRUSTED_EXECUTION"


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_work_repo_in_safe_path_component(self, tmp_path):
        """Path containing 'work_repo' as part of directory name should be safe."""
        safe_dir = tmp_path / "my_work_repo_backup"
        safe_dir.mkdir()

        result = run(["python", "--version"], cwd=safe_dir, capture_output=True)
        assert result.returncode == 0

    def test_repo_work_reversed(self, tmp_path):
        """Path with repo/work (reversed) should be safe."""
        safe_dir = tmp_path / "repo" / "work"
        safe_dir.mkdir(parents=True, exist_ok=True)

        result = run(["python", "--version"], cwd=safe_dir, capture_output=True)
        assert result.returncode == 0

    def test_path_object_as_cwd(self, tmp_path):
        """Path object should work for cwd parameter."""
        untrusted_dir = tmp_path / "runs" / "123" / "work" / "repo"
        untrusted_dir.mkdir(parents=True, exist_ok=True)

        with pytest.raises(SubprocessSecurityError):
            run(["python", "--version"], cwd=untrusted_dir)

    def test_string_path_as_cwd(self, tmp_path):
        """String path should work for cwd parameter."""
        untrusted_dir = tmp_path / "runs" / "123" / "work" / "repo"
        untrusted_dir.mkdir(parents=True, exist_ok=True)

        with pytest.raises(SubprocessSecurityError):
            run(["python", "--version"], cwd=str(untrusted_dir))
