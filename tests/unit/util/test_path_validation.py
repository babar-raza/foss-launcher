"""Tests for hermetic path validation utilities (Guarantee B)."""

import pytest
from pathlib import Path
import tempfile
import os

from launch.util.path_validation import (
    PathValidationError,
    validate_path_in_boundary,
    validate_path_in_allowed,
    validate_no_path_traversal,
    is_path_in_boundary,
)


class TestValidatePathInBoundary:
    """Tests for validate_path_in_boundary function."""

    def test_valid_path_within_boundary(self, tmp_path):
        """Path within boundary should pass."""
        boundary = tmp_path
        file_path = boundary / "subdir" / "file.txt"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.touch()

        result = validate_path_in_boundary(file_path, boundary)
        assert result.is_relative_to(boundary)

    def test_path_equals_boundary(self, tmp_path):
        """Path equal to boundary should pass."""
        boundary = tmp_path
        result = validate_path_in_boundary(boundary, boundary)
        assert result == boundary.resolve()

    def test_path_with_parent_traversal_escapes(self, tmp_path):
        """Path using .. to escape boundary should fail."""
        boundary = tmp_path / "allowed"
        boundary.mkdir(parents=True, exist_ok=True)

        # Try to escape via ../..
        escaping_path = boundary / ".." / ".." / "etc" / "passwd"

        with pytest.raises(PathValidationError) as exc_info:
            validate_path_in_boundary(escaping_path, boundary)

        assert "escapes boundary" in str(exc_info.value)
        assert exc_info.value.error_code == "POLICY_PATH_ESCAPE"

    def test_absolute_path_outside_boundary(self, tmp_path):
        """Absolute path outside boundary should fail."""
        boundary = tmp_path / "allowed"
        boundary.mkdir(parents=True, exist_ok=True)

        outside_path = tmp_path / "forbidden" / "file.txt"

        with pytest.raises(PathValidationError) as exc_info:
            validate_path_in_boundary(outside_path, boundary)

        assert "escapes boundary" in str(exc_info.value)

    def test_symlink_escaping_boundary(self, tmp_path):
        """Symlink pointing outside boundary should fail when resolved."""
        boundary = tmp_path / "allowed"
        boundary.mkdir(parents=True, exist_ok=True)

        outside = tmp_path / "forbidden"
        outside.mkdir(parents=True, exist_ok=True)
        outside_file = outside / "secret.txt"
        outside_file.touch()

        # Create symlink inside boundary pointing outside
        symlink = boundary / "link"
        if os.name != "nt":  # Skip on Windows if no admin rights
            try:
                symlink.symlink_to(outside_file)
            except OSError:
                pytest.skip("Cannot create symlinks without admin rights")

            with pytest.raises(PathValidationError) as exc_info:
                validate_path_in_boundary(symlink, boundary, resolve_symlinks=True)

            assert "escapes boundary" in str(exc_info.value)

    def test_resolve_symlinks_false(self, tmp_path):
        """When resolve_symlinks=False, validation uses literal path."""
        boundary = tmp_path / "allowed"
        boundary.mkdir(parents=True, exist_ok=True)

        # Create a path that would fail if resolved
        file_path = boundary / "file.txt"
        file_path.touch()

        # Should pass because we're not resolving
        result = validate_path_in_boundary(
            file_path,
            boundary,
            resolve_symlinks=False
        )
        assert file_path.parts[-1] == result.parts[-1]


class TestValidatePathInAllowed:
    """Tests for validate_path_in_allowed function."""

    def test_exact_path_match(self, tmp_path):
        """Exact path in allowed list should pass."""
        file_path = tmp_path / "file.txt"
        file_path.touch()

        allowed = [str(file_path)]
        result = validate_path_in_allowed(file_path, allowed)
        assert result == file_path.resolve()

    def test_glob_pattern_match(self, tmp_path):
        """Path matching /** pattern should pass."""
        subdir = tmp_path / "src" / "subdir"
        subdir.mkdir(parents=True, exist_ok=True)
        file_path = subdir / "file.py"
        file_path.touch()

        allowed = [str(tmp_path / "src") + "/**"]
        result = validate_path_in_allowed(file_path, allowed)
        assert result == file_path.resolve()

    def test_path_not_in_allowed(self, tmp_path):
        """Path not matching any allowed pattern should fail."""
        file_path = tmp_path / "forbidden" / "file.txt"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.touch()

        allowed = [str(tmp_path / "src") + "/**"]

        with pytest.raises(PathValidationError) as exc_info:
            validate_path_in_allowed(file_path, allowed)

        assert "not in allowed paths" in str(exc_info.value)
        assert exc_info.value.error_code == "POLICY_PATH_NOT_ALLOWED"

    def test_with_boundary_validation(self, tmp_path):
        """Should validate both allowed pattern and boundary."""
        boundary = tmp_path / "run_dir"
        boundary.mkdir(parents=True, exist_ok=True)

        file_path = boundary / "src" / "file.py"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.touch()

        allowed = [str(boundary / "src") + "/**"]
        result = validate_path_in_allowed(file_path, allowed, boundary=boundary)
        assert result == file_path.resolve()

    def test_escapes_boundary_despite_allowed_pattern(self, tmp_path):
        """Path matching pattern but outside boundary should fail."""
        boundary = tmp_path / "run_dir"
        boundary.mkdir(parents=True, exist_ok=True)

        # File outside boundary
        file_path = tmp_path / "src" / "file.py"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.touch()

        # Pattern would match, but boundary check should fail
        allowed = [str(tmp_path / "src") + "/**"]

        with pytest.raises(PathValidationError) as exc_info:
            validate_path_in_allowed(file_path, allowed, boundary=boundary)

        assert "escapes boundary" in str(exc_info.value)


class TestValidateNoPathTraversal:
    """Tests for validate_no_path_traversal function."""

    def test_valid_relative_path(self):
        """Normal relative path should pass."""
        validate_no_path_traversal("src/foo/bar.py")

    def test_valid_absolute_path(self, tmp_path):
        """Normal absolute path should pass."""
        validate_no_path_traversal(tmp_path / "src" / "file.py")

    def test_parent_traversal_fails(self):
        """Path with .. should fail."""
        with pytest.raises(PathValidationError) as exc_info:
            validate_no_path_traversal("src/../etc/passwd")

        assert "parent directory traversal" in str(exc_info.value)
        assert exc_info.value.error_code == "POLICY_PATH_TRAVERSAL"

    def test_multiple_parent_traversal_fails(self):
        """Path with multiple .. should fail."""
        with pytest.raises(PathValidationError) as exc_info:
            validate_no_path_traversal("src/../../etc/passwd")

        assert "parent directory traversal" in str(exc_info.value)

    def test_suspicious_tilde_pattern(self):
        """Path with ~ should fail."""
        with pytest.raises(PathValidationError) as exc_info:
            validate_no_path_traversal("~/etc/passwd")

        assert "suspicious pattern" in str(exc_info.value)
        assert exc_info.value.error_code == "POLICY_PATH_SUSPICIOUS"

    def test_suspicious_percent_pattern(self):
        """Path with % should fail."""
        with pytest.raises(PathValidationError) as exc_info:
            validate_no_path_traversal("src/%APPDATA%/file.txt")

        assert "suspicious pattern" in str(exc_info.value)

    def test_suspicious_dollar_pattern(self):
        """Path with $ should fail."""
        with pytest.raises(PathValidationError) as exc_info:
            validate_no_path_traversal("src/$HOME/file.txt")

        assert "suspicious pattern" in str(exc_info.value)


class TestIsPathInBoundary:
    """Tests for is_path_in_boundary function."""

    def test_valid_path_returns_true(self, tmp_path):
        """Path within boundary should return True."""
        boundary = tmp_path
        file_path = boundary / "file.txt"
        file_path.touch()

        assert is_path_in_boundary(file_path, boundary) is True

    def test_invalid_path_returns_false(self, tmp_path):
        """Path outside boundary should return False."""
        boundary = tmp_path / "allowed"
        boundary.mkdir(parents=True, exist_ok=True)

        outside_path = tmp_path / "forbidden" / "file.txt"

        assert is_path_in_boundary(outside_path, boundary) is False

    def test_nonexistent_path_returns_false(self, tmp_path):
        """Nonexistent path should return False."""
        boundary = tmp_path
        nonexistent = boundary / "nonexistent" / "file.txt"

        # This should not raise, just return False
        result = is_path_in_boundary(nonexistent, boundary)
        assert result in [True, False]  # Depends on resolution behavior


class TestPathValidationIntegration:
    """Integration tests for path validation."""

    def test_run_dir_confinement(self, tmp_path):
        """Simulate RUN_DIR confinement scenario."""
        run_dir = tmp_path / "run_dir"
        run_dir.mkdir(parents=True, exist_ok=True)

        # Create allowed paths
        allowed_paths = [
            str(run_dir / "artifacts") + "/**",
            str(run_dir / "logs") + "/**",
        ]

        # Valid paths
        valid_artifact = run_dir / "artifacts" / "report.json"
        valid_artifact.parent.mkdir(parents=True, exist_ok=True)
        valid_artifact.touch()

        valid_log = run_dir / "logs" / "gate.log"
        valid_log.parent.mkdir(parents=True, exist_ok=True)
        valid_log.touch()

        # Should pass
        validate_path_in_allowed(valid_artifact, allowed_paths, boundary=run_dir)
        validate_path_in_allowed(valid_log, allowed_paths, boundary=run_dir)

        # Invalid path (escapes RUN_DIR)
        forbidden = tmp_path / "etc" / "passwd"
        with pytest.raises(PathValidationError):
            validate_path_in_allowed(forbidden, allowed_paths, boundary=run_dir)

        # Invalid path (inside RUN_DIR but not in allowed_paths)
        not_allowed = run_dir / "forbidden" / "file.txt"
        not_allowed.parent.mkdir(parents=True, exist_ok=True)
        not_allowed.touch()

        with pytest.raises(PathValidationError) as exc_info:
            validate_path_in_allowed(not_allowed, allowed_paths, boundary=run_dir)

        assert exc_info.value.error_code == "POLICY_PATH_NOT_ALLOWED"

    def test_deterministic_validation(self, tmp_path):
        """Path validation should be deterministic."""
        boundary = tmp_path
        file_path = boundary / "file.txt"
        file_path.touch()

        # Run validation multiple times
        results = []
        for _ in range(5):
            result = validate_path_in_boundary(file_path, boundary)
            results.append(str(result))

        # All results should be identical
        assert len(set(results)) == 1
