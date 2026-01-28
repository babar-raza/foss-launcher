"""Test suite for file scanning (TC-590).

Tests:
1. Binary file detection
2. Allowlist checking (exact name, path patterns, globs)
3. Single file scanning
4. Directory scanning (recursive and non-recursive)
5. Scan result aggregation
6. Filtering results with secrets
7. Excluding directories (.git, node_modules)
8. Error handling (missing files, encoding issues)
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from launch.security.file_scanner import (
    ScanResult,
    is_binary_file,
    is_allowlisted,
    scan_file,
    scan_directory,
    filter_results_with_secrets,
    count_total_secrets,
)


class TestBinaryFileDetection:
    """Test binary file detection."""

    def test_is_binary_text_file(self, tmp_path: Path) -> None:
        """Test that text files are not detected as binary."""
        text_file = tmp_path / "test.txt"
        text_file.write_text("This is a text file", encoding="utf-8")

        assert not is_binary_file(text_file)

    def test_is_binary_actual_binary(self, tmp_path: Path) -> None:
        """Test that binary files are detected."""
        binary_file = tmp_path / "test.bin"
        binary_file.write_bytes(b"\x00\x01\x02\x03")

        assert is_binary_file(binary_file)

    def test_is_binary_nonexistent_file(self, tmp_path: Path) -> None:
        """Test that nonexistent files are treated as binary."""
        nonexistent = tmp_path / "nonexistent.txt"

        assert is_binary_file(nonexistent)


class TestAllowlistChecking:
    """Test allowlist checking."""

    def test_is_allowlisted_exact_name(self) -> None:
        """Test exact filename match."""
        path = Path("tests/test_secrets.py")
        allowlist = ["test_secrets.py"]

        assert is_allowlisted(path, allowlist)

    def test_is_allowlisted_path_pattern(self) -> None:
        """Test path pattern match."""
        path = Path("tests/fixtures/secrets.txt")
        allowlist = ["fixtures"]

        assert is_allowlisted(path, allowlist)

    def test_is_allowlisted_glob_pattern(self) -> None:
        """Test glob-style pattern match."""
        path = Path("tests/test_data/secrets.txt")
        allowlist = ["test_data/*"]

        assert is_allowlisted(path, allowlist)

    def test_is_allowlisted_not_in_list(self) -> None:
        """Test that non-allowlisted paths return False."""
        path = Path("src/code.py")
        allowlist = ["test_secrets.py"]

        assert not is_allowlisted(path, allowlist)

    def test_is_allowlisted_empty_list(self) -> None:
        """Test that empty allowlist returns False."""
        path = Path("src/code.py")
        allowlist = []

        assert not is_allowlisted(path, allowlist)

    def test_is_allowlisted_none(self) -> None:
        """Test that None allowlist returns False."""
        path = Path("src/code.py")

        assert not is_allowlisted(path, None)


class TestScanResult:
    """Test ScanResult dataclass."""

    def test_scan_result_creation(self) -> None:
        """Test creating a ScanResult."""
        result = ScanResult(file_path="test.py")

        assert result.file_path == "test.py"
        assert result.secrets_found == []
        assert result.scan_timestamp != ""
        assert not result.is_binary
        assert not result.is_allowlisted
        assert result.error is None

    def test_scan_result_with_timestamp(self) -> None:
        """Test that timestamp is auto-generated."""
        result = ScanResult(file_path="test.py")

        # Should have ISO 8601 format
        assert "T" in result.scan_timestamp
        assert result.scan_timestamp.endswith("Z") or "+" in result.scan_timestamp


class TestScanFile:
    """Test single file scanning."""

    def test_scan_file_no_secrets(self, tmp_path: Path) -> None:
        """Test scanning a file with no secrets."""
        test_file = tmp_path / "clean.txt"
        test_file.write_text("This is clean text", encoding="utf-8")

        result = scan_file(test_file)

        assert result.file_path == str(test_file)
        assert len(result.secrets_found) == 0
        assert not result.is_binary
        assert not result.is_allowlisted

    def test_scan_file_with_secret(self, tmp_path: Path) -> None:
        """Test scanning a file with a secret."""
        test_file = tmp_path / "config.txt"
        test_file.write_text("AWS_KEY=AKIAIOSFODNN7EXAMPLE", encoding="utf-8")

        result = scan_file(test_file)

        assert result.file_path == str(test_file)
        assert len(result.secrets_found) > 0
        assert result.secrets_found[0].secret_type == "aws_access_key_id"

    def test_scan_file_binary(self, tmp_path: Path) -> None:
        """Test scanning a binary file."""
        binary_file = tmp_path / "test.bin"
        binary_file.write_bytes(b"\x00\x01\x02\x03")

        result = scan_file(binary_file)

        assert result.is_binary
        assert len(result.secrets_found) == 0

    def test_scan_file_allowlisted(self, tmp_path: Path) -> None:
        """Test scanning an allowlisted file."""
        test_file = tmp_path / "test_secrets.py"
        test_file.write_text("password=secret", encoding="utf-8")

        result = scan_file(test_file, allowlist=["test_secrets.py"])

        assert result.is_allowlisted
        assert len(result.secrets_found) == 0  # Not scanned

    def test_scan_file_encoding_error(self, tmp_path: Path) -> None:
        """Test scanning a file with encoding issues."""
        bad_file = tmp_path / "bad_encoding.txt"
        # Write invalid UTF-8
        bad_file.write_bytes(b"\xff\xfe Invalid UTF-8")

        result = scan_file(bad_file)

        # Should be treated as binary
        assert result.is_binary


class TestScanDirectory:
    """Test directory scanning."""

    def test_scan_directory_empty(self, tmp_path: Path) -> None:
        """Test scanning an empty directory."""
        results = scan_directory(tmp_path)

        assert results == []

    def test_scan_directory_with_files(self, tmp_path: Path) -> None:
        """Test scanning a directory with files."""
        # Create test files
        (tmp_path / "clean.txt").write_text("Clean text", encoding="utf-8")
        (tmp_path / "config.txt").write_text("AWS_KEY=AKIAIOSFODNN7EXAMPLE", encoding="utf-8")

        results = scan_directory(tmp_path, recursive=False)

        assert len(results) == 2
        # Should be sorted by file path
        assert results[0].file_path < results[1].file_path

    def test_scan_directory_recursive(self, tmp_path: Path) -> None:
        """Test recursive directory scanning."""
        # Create nested structure
        (tmp_path / "file1.txt").write_text("Clean", encoding="utf-8")
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "file2.txt").write_text("Clean", encoding="utf-8")

        results = scan_directory(tmp_path, recursive=True)

        assert len(results) == 2

    def test_scan_directory_non_recursive(self, tmp_path: Path) -> None:
        """Test non-recursive directory scanning."""
        # Create nested structure
        (tmp_path / "file1.txt").write_text("Clean", encoding="utf-8")
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "file2.txt").write_text("Clean", encoding="utf-8")

        results = scan_directory(tmp_path, recursive=False)

        # Should only scan top level
        assert len(results) == 1

    def test_scan_directory_exclude_dirs(self, tmp_path: Path) -> None:
        """Test excluding directories."""
        # Create structure with .git
        (tmp_path / "file.txt").write_text("Clean", encoding="utf-8")
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "config").write_text("git config", encoding="utf-8")

        results = scan_directory(tmp_path, recursive=True)

        # .git should be excluded by default
        assert len(results) == 1
        assert ".git" not in results[0].file_path

    def test_scan_directory_custom_exclude(self, tmp_path: Path) -> None:
        """Test custom exclude directories."""
        # Create structure
        (tmp_path / "file.txt").write_text("Clean", encoding="utf-8")
        custom_dir = tmp_path / "custom_exclude"
        custom_dir.mkdir()
        (custom_dir / "file.txt").write_text("Clean", encoding="utf-8")

        results = scan_directory(tmp_path, recursive=True, exclude_dirs={"custom_exclude"})

        assert len(results) == 1

    def test_scan_directory_nonexistent(self, tmp_path: Path) -> None:
        """Test scanning a nonexistent directory."""
        nonexistent = tmp_path / "nonexistent"

        results = scan_directory(nonexistent)

        assert results == []


class TestFilterResults:
    """Test filtering scan results."""

    def test_filter_results_with_secrets(self) -> None:
        """Test filtering to only results with secrets."""
        from launch.security.secret_detector import SecretMatch

        results = [
            ScanResult(file_path="clean.txt", secrets_found=[]),
            ScanResult(
                file_path="secret.txt",
                secrets_found=[
                    SecretMatch(
                        secret_type="api_key",
                        value="test",
                        start_pos=0,
                        end_pos=4,
                        line_number=1,
                        context="***",
                        confidence=0.8,
                    )
                ],
            ),
        ]

        filtered = filter_results_with_secrets(results)

        assert len(filtered) == 1
        assert filtered[0].file_path == "secret.txt"

    def test_filter_results_excludes_allowlisted(self) -> None:
        """Test that allowlisted files are excluded from filtered results."""
        from launch.security.secret_detector import SecretMatch

        results = [
            ScanResult(
                file_path="test_secrets.py",
                secrets_found=[
                    SecretMatch(
                        secret_type="api_key",
                        value="test",
                        start_pos=0,
                        end_pos=4,
                        line_number=1,
                        context="***",
                        confidence=0.8,
                    )
                ],
                is_allowlisted=True,
            ),
        ]

        filtered = filter_results_with_secrets(results)

        assert len(filtered) == 0


class TestCountSecrets:
    """Test counting secrets."""

    def test_count_total_secrets(self) -> None:
        """Test counting total secrets across results."""
        from launch.security.secret_detector import SecretMatch

        results = [
            ScanResult(file_path="clean.txt", secrets_found=[]),
            ScanResult(
                file_path="secret1.txt",
                secrets_found=[
                    SecretMatch(
                        secret_type="api_key",
                        value="test1",
                        start_pos=0,
                        end_pos=5,
                        line_number=1,
                        context="***",
                        confidence=0.8,
                    )
                ],
            ),
            ScanResult(
                file_path="secret2.txt",
                secrets_found=[
                    SecretMatch(
                        secret_type="password",
                        value="test2",
                        start_pos=0,
                        end_pos=5,
                        line_number=1,
                        context="***",
                        confidence=0.8,
                    ),
                    SecretMatch(
                        secret_type="api_key",
                        value="test3",
                        start_pos=10,
                        end_pos=15,
                        line_number=2,
                        context="***",
                        confidence=0.8,
                    ),
                ],
            ),
        ]

        count = count_total_secrets(results)

        assert count == 3

    def test_count_total_secrets_excludes_allowlisted(self) -> None:
        """Test that allowlisted secrets are not counted."""
        from launch.security.secret_detector import SecretMatch

        results = [
            ScanResult(
                file_path="test_secrets.py",
                secrets_found=[
                    SecretMatch(
                        secret_type="api_key",
                        value="test",
                        start_pos=0,
                        end_pos=4,
                        line_number=1,
                        context="***",
                        confidence=0.8,
                    )
                ],
                is_allowlisted=True,
            ),
        ]

        count = count_total_secrets(results)

        assert count == 0


class TestScanIntegration:
    """Integration tests for file scanning."""

    def test_scan_project_structure(self, tmp_path: Path) -> None:
        """Test scanning a realistic project structure."""
        # Create structure
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "code.py").write_text("# Clean code", encoding="utf-8")

        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "settings.py").write_text(
            "API_KEY=abc123def456ghi789jkl012mno345pqr678", encoding="utf-8"
        )

        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_secrets.py").write_text("password=test", encoding="utf-8")

        # Scan with allowlist
        results = scan_directory(tmp_path, allowlist=["test_secrets.py"], recursive=True)

        # Should find secret in config but not in test_secrets
        results_with_secrets = filter_results_with_secrets(results)
        assert len(results_with_secrets) >= 1

        # test_secrets.py should be allowlisted
        test_file_results = [r for r in results if "test_secrets.py" in r.file_path]
        assert len(test_file_results) == 1
        assert test_file_results[0].is_allowlisted
