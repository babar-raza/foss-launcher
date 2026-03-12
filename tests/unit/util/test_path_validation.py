"""Tests for path validation utilities."""

from __future__ import annotations

from pathlib import Path

import pytest

from launcher.util.path_validation import (
    PathValidationError,
    is_path_in_boundary,
    validate_no_path_traversal,
    validate_path_in_boundary,
    validate_path_matches_patterns,
    validate_run_dir_under_runs,
)


class TestValidatePathInBoundary:
    def test_path_inside_boundary(self, tmp_path: Path) -> None:
        boundary = tmp_path / "allowed"
        boundary.mkdir()
        target = boundary / "file.txt"
        target.touch()
        result = validate_path_in_boundary(target, boundary)
        assert result.is_relative_to(boundary.resolve())

    def test_path_outside_boundary(self, tmp_path: Path) -> None:
        boundary = tmp_path / "allowed"
        boundary.mkdir()
        outside = tmp_path / "forbidden" / "file.txt"
        with pytest.raises(PathValidationError, match="escapes boundary"):
            validate_path_in_boundary(outside, boundary)


class TestIsPathInBoundary:
    def test_inside(self, tmp_path: Path) -> None:
        b = tmp_path / "dir"
        b.mkdir()
        assert is_path_in_boundary(b / "f.txt", b) is True

    def test_outside(self, tmp_path: Path) -> None:
        b = tmp_path / "dir"
        b.mkdir()
        assert is_path_in_boundary(tmp_path / "other.txt", b) is False


class TestValidateNoPathTraversal:
    def test_clean_path(self) -> None:
        validate_no_path_traversal("src/launcher/io/atomic.py")

    def test_traversal_detected(self) -> None:
        with pytest.raises(PathValidationError, match="parent directory traversal"):
            validate_no_path_traversal("src/../etc/passwd")

    def test_suspicious_tilde(self) -> None:
        with pytest.raises(PathValidationError, match="suspicious pattern"):
            validate_no_path_traversal("~/secret")


class TestValidateRunDirUnderRuns:
    def test_valid_run_dir(self, tmp_path: Path) -> None:
        runs_dir = tmp_path / "runs"
        runs_dir.mkdir()
        run_dir = runs_dir / "r_test"
        run_dir.mkdir()
        result = validate_run_dir_under_runs(run_dir)
        assert result == run_dir.resolve()

    def test_invalid_run_dir(self, tmp_path: Path) -> None:
        bad = tmp_path / "not_runs" / "r_test"
        bad.mkdir(parents=True)
        with pytest.raises(PathValidationError, match="outside the required 'runs/' directory"):
            validate_run_dir_under_runs(bad)


class TestValidatePathMatchesPatterns:
    def test_exact_match(self, tmp_path: Path) -> None:
        assert validate_path_matches_patterns(
            "pyproject.toml", ["pyproject.toml"], repo_root=tmp_path
        )

    def test_recursive_glob(self, tmp_path: Path) -> None:
        assert validate_path_matches_patterns(
            "src/launcher/io/atomic.py", ["src/launcher/**"], repo_root=tmp_path
        )

    def test_no_match(self, tmp_path: Path) -> None:
        assert not validate_path_matches_patterns(
            "evil.py", ["src/**"], repo_root=tmp_path
        )
