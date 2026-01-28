"""Test suite for security validation gate (TC-590).

Tests:
1. Security gate integration
2. Report generation (security_report.json)
3. Issue creation for detected secrets
4. Allowlist handling
5. Pass/fail determination
6. Multiple findings aggregation
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from launch.validators.security_gate import run_security_gate, validate_security


class TestRunSecurityGate:
    """Test security gate execution."""

    def test_run_security_gate_clean_directory(self, tmp_path: Path) -> None:
        """Test security gate on clean directory."""
        # Create clean files
        (tmp_path / "clean.txt").write_text("This is clean", encoding="utf-8")

        report = run_security_gate(tmp_path)

        assert report["passed"] is True
        assert report["secrets_found"] == 0
        assert len(report["findings"]) == 0
        assert "schema_version" in report
        assert "scan_timestamp" in report

    def test_run_security_gate_with_secret(self, tmp_path: Path) -> None:
        """Test security gate with a secret."""
        # Create file with secret
        (tmp_path / "config.txt").write_text("AWS_KEY=AKIAIOSFODNN7EXAMPLE", encoding="utf-8")

        report = run_security_gate(tmp_path)

        assert report["passed"] is False
        assert report["secrets_found"] > 0
        assert len(report["findings"]) > 0

        # Check finding structure
        finding = report["findings"][0]
        assert "file_path" in finding
        assert "secrets" in finding
        assert len(finding["secrets"]) > 0

        secret = finding["secrets"][0]
        assert "secret_type" in secret
        assert "line_number" in secret
        assert "context" in secret
        assert "confidence" in secret

    def test_run_security_gate_multiple_secrets(self, tmp_path: Path) -> None:
        """Test security gate with multiple secrets."""
        # Create files with secrets
        (tmp_path / "aws.txt").write_text("KEY=AKIAIOSFODNN7EXAMPLE", encoding="utf-8")
        (tmp_path / "github.txt").write_text("TOKEN=ghp_1234567890abcdefghijklmnopqrstuvwxyz", encoding="utf-8")

        report = run_security_gate(tmp_path)

        assert report["passed"] is False
        assert report["secrets_found"] >= 2
        assert len(report["findings"]) >= 2

    def test_run_security_gate_with_allowlist(self, tmp_path: Path) -> None:
        """Test security gate with allowlist."""
        # Create test file with secret (should be allowlisted)
        (tmp_path / "test_secrets.py").write_text("password=test123", encoding="utf-8")

        report = run_security_gate(tmp_path, allowlist=["test_secrets.py"])

        # Should pass because file is allowlisted
        assert report["passed"] is True
        assert report["secrets_found"] == 0

    def test_run_security_gate_report_structure(self, tmp_path: Path) -> None:
        """Test that report has correct structure."""
        (tmp_path / "clean.txt").write_text("Clean", encoding="utf-8")

        report = run_security_gate(tmp_path)

        # Check schema
        assert "schema_version" in report
        assert report["schema_version"] == "1.0"
        assert "scan_timestamp" in report
        assert "files_scanned" in report
        assert "secrets_found" in report
        assert "passed" in report
        assert "findings" in report

        assert isinstance(report["findings"], list)


class TestValidateSecurity:
    """Test validate_security function."""

    def test_validate_security_clean(self, tmp_path: Path) -> None:
        """Test validation with clean directory."""
        # Setup
        (tmp_path / "artifacts").mkdir()
        (tmp_path / "clean.txt").write_text("Clean", encoding="utf-8")

        passed, issues = validate_security(tmp_path)

        assert passed is True
        assert len(issues) == 0

        # Check that report was written
        report_path = tmp_path / "artifacts" / "security_report.json"
        assert report_path.exists()

        with open(report_path, "r", encoding="utf-8") as f:
            report = json.load(f)

        assert report["passed"] is True

    def test_validate_security_with_secret(self, tmp_path: Path) -> None:
        """Test validation with secret detected."""
        # Setup
        (tmp_path / "artifacts").mkdir()
        (tmp_path / "config.txt").write_text("AWS_KEY=AKIAIOSFODNN7EXAMPLE", encoding="utf-8")

        passed, issues = validate_security(tmp_path)

        assert passed is False
        assert len(issues) > 0

        # Check issue structure
        issue = issues[0]
        assert issue["gate"] == "security"
        assert issue["severity"] == "blocker"
        assert issue["error_code"] == "SECURITY_SECRET_DETECTED"
        assert "issue_id" in issue
        assert "message" in issue
        assert "files" in issue
        assert "suggested_fix" in issue

    def test_validate_security_multiple_secrets(self, tmp_path: Path) -> None:
        """Test validation with multiple secrets."""
        # Setup
        (tmp_path / "artifacts").mkdir()
        (tmp_path / "aws.txt").write_text("KEY=AKIAIOSFODNN7EXAMPLE", encoding="utf-8")
        (tmp_path / "github.txt").write_text("TOKEN=ghp_1234567890abcdefghijklmnopqrstuvwxyz", encoding="utf-8")

        passed, issues = validate_security(tmp_path)

        assert passed is False
        assert len(issues) >= 2

        # Each finding should have unique issue_id
        issue_ids = [issue["issue_id"] for issue in issues]
        assert len(issue_ids) == len(set(issue_ids))

    def test_validate_security_creates_artifacts_dir(self, tmp_path: Path) -> None:
        """Test that validation creates artifacts directory if missing."""
        # Don't create artifacts dir
        (tmp_path / "clean.txt").write_text("Clean", encoding="utf-8")

        passed, issues = validate_security(tmp_path)

        # Should create artifacts dir and write report
        assert (tmp_path / "artifacts").exists()
        assert (tmp_path / "artifacts" / "security_report.json").exists()

    def test_validate_security_report_json_format(self, tmp_path: Path) -> None:
        """Test that security report is valid JSON."""
        # Setup
        (tmp_path / "artifacts").mkdir()
        (tmp_path / "config.txt").write_text("password=Secret123456", encoding="utf-8")

        validate_security(tmp_path)

        report_path = tmp_path / "artifacts" / "security_report.json"
        with open(report_path, "r", encoding="utf-8") as f:
            report = json.load(f)

        # Should be valid JSON with expected structure
        assert isinstance(report, dict)
        assert "findings" in report
        assert isinstance(report["findings"], list)


class TestSecurityGateIntegration:
    """Integration tests for security gate."""

    def test_security_gate_realistic_project(self, tmp_path: Path) -> None:
        """Test security gate on realistic project structure."""
        # Create structure
        artifacts = tmp_path / "artifacts"
        artifacts.mkdir()

        src = tmp_path / "src"
        src.mkdir()
        (src / "code.py").write_text("# Clean code\nprint('hello')", encoding="utf-8")

        config = tmp_path / "config"
        config.mkdir()
        (config / "settings.py").write_text(
            "API_KEY = 'abc123def456ghi789jkl012mno345pqr678'",
            encoding="utf-8",
        )

        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "test_secrets.py").write_text(
            "# Test file\ntest_password = 'test123'",
            encoding="utf-8",
        )

        # Run with allowlist
        passed, issues = validate_security(tmp_path, allowlist=["test_secrets.py"])

        # Should fail due to API key in config
        assert passed is False
        assert len(issues) > 0

        # Check that test file was not flagged
        flagged_files = [issue["files"][0] for issue in issues]
        assert not any("test_secrets.py" in f for f in flagged_files)

    def test_security_gate_excludes_git_dir(self, tmp_path: Path) -> None:
        """Test that .git directory is excluded."""
        # Create .git dir with "secrets"
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "config").write_text("password=secret", encoding="utf-8")

        # Create artifacts
        (tmp_path / "artifacts").mkdir()

        passed, issues = validate_security(tmp_path)

        # Should pass (no secrets found because .git excluded)
        assert passed is True

    def test_security_gate_binary_files_skipped(self, tmp_path: Path) -> None:
        """Test that binary files are skipped."""
        # Create binary file with "secret-like" bytes
        (tmp_path / "test.bin").write_bytes(b"\x00AKIA1234567890ABCDEF\x00")
        (tmp_path / "artifacts").mkdir()

        passed, issues = validate_security(tmp_path)

        # Should pass (binary files skipped)
        assert passed is True

    def test_security_gate_nested_secrets(self, tmp_path: Path) -> None:
        """Test detection of secrets in nested directories."""
        # Create nested structure
        deep_dir = tmp_path / "a" / "b" / "c"
        deep_dir.mkdir(parents=True)
        (deep_dir / "secret.txt").write_text("TOKEN=ghp_1234567890abcdefghijklmnopqrstuvwxyz", encoding="utf-8")

        (tmp_path / "artifacts").mkdir()

        passed, issues = validate_security(tmp_path)

        assert passed is False
        assert len(issues) > 0

    def test_security_gate_deterministic(self, tmp_path: Path) -> None:
        """Test that security gate produces deterministic results."""
        # Create test files
        (tmp_path / "file1.txt").write_text("KEY=AKIAIOSFODNN7EXAMPLE", encoding="utf-8")
        (tmp_path / "file2.txt").write_text("password=Secret123456", encoding="utf-8")
        (tmp_path / "artifacts").mkdir()

        # Run twice
        report1 = run_security_gate(tmp_path)
        report2 = run_security_gate(tmp_path)

        # Results should be identical (except timestamps)
        assert report1["passed"] == report2["passed"]
        assert report1["secrets_found"] == report2["secrets_found"]
        assert len(report1["findings"]) == len(report2["findings"])
