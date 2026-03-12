"""Tests for secure subprocess wrapper."""

from __future__ import annotations

from pathlib import Path

import pytest

from launcher.util.subprocess import SubprocessSecurityError, run, check_output


class TestSubprocessSecurity:
    def test_allowed_cwd(self, tmp_path: Path) -> None:
        result = run(["echo", "hello"], cwd=tmp_path, capture_output=True, text=True)
        assert result.returncode == 0

    def test_blocked_work_repo_with_run_dir(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "runs" / "r_test"
        work_repo = run_dir / "work" / "repo"
        work_repo.mkdir(parents=True)
        with pytest.raises(SubprocessSecurityError, match="untrusted repo directory"):
            run(["echo", "hello"], cwd=work_repo, run_dir=run_dir)

    def test_blocked_work_repo_pattern(self, tmp_path: Path) -> None:
        fake_repo = tmp_path / "work" / "repo" / "subdir"
        fake_repo.mkdir(parents=True)
        with pytest.raises(SubprocessSecurityError):
            run(["echo", "hello"], cwd=fake_repo)

    def test_none_cwd_allowed(self) -> None:
        result = run(["echo", "ok"], capture_output=True, text=True)
        assert result.returncode == 0

    def test_check_output_blocked(self, tmp_path: Path) -> None:
        work_repo = tmp_path / "work" / "repo"
        work_repo.mkdir(parents=True)
        with pytest.raises(SubprocessSecurityError):
            check_output(["echo", "hello"], cwd=work_repo)

    def test_error_code(self) -> None:
        err = SubprocessSecurityError("test", error_code="SECURITY_TEST")
        assert err.error_code == "SECURITY_TEST"
