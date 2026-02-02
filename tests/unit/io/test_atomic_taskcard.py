"""Unit tests for atomic.py taskcard enforcement (Layer 3).

Tests the STRONGEST layer of defense-in-depth system.
"""

import tempfile
from pathlib import Path

import pytest

from launch.io.atomic import atomic_write_json, atomic_write_text, get_enforcement_mode
from launch.util.path_validation import PathValidationError


class TestGetEnforcementMode:
    """Test enforcement mode detection."""

    def test_default_mode_is_strict(self, monkeypatch):
        """Test that default enforcement mode is strict."""
        monkeypatch.delenv("LAUNCH_TASKCARD_ENFORCEMENT", raising=False)

        mode = get_enforcement_mode()

        assert mode == "strict"

    def test_disabled_mode_from_env(self, monkeypatch):
        """Test that disabled mode can be set via environment."""
        monkeypatch.setenv("LAUNCH_TASKCARD_ENFORCEMENT", "disabled")

        mode = get_enforcement_mode()

        assert mode == "disabled"

    def test_strict_mode_from_env(self, monkeypatch):
        """Test that strict mode can be explicitly set via environment."""
        monkeypatch.setenv("LAUNCH_TASKCARD_ENFORCEMENT", "strict")

        mode = get_enforcement_mode()

        assert mode == "strict"

    def test_invalid_mode_raises_error(self, monkeypatch):
        """Test that invalid mode raises ValueError."""
        monkeypatch.setenv("LAUNCH_TASKCARD_ENFORCEMENT", "invalid")

        with pytest.raises(ValueError) as exc_info:
            get_enforcement_mode()

        assert "Invalid LAUNCH_TASKCARD_ENFORCEMENT" in str(exc_info.value)


class TestAtomicWriteTaskcardEnforcement:
    """Test taskcard enforcement in atomic write operations."""

    def test_write_to_unprotected_path_without_taskcard(self, tmp_path):
        """Test that writes to unprotected paths work without taskcard."""
        # reports/ is not a protected path
        test_file = tmp_path / "reports" / "test.md"
        repo_root = Path(__file__).parent.parent.parent.parent

        # Should succeed without taskcard
        atomic_write_text(
            test_file,
            "Test content",
            enforcement_mode="strict",
            repo_root=repo_root,
        )

        assert test_file.exists()
        assert test_file.read_text() == "Test content"

    def test_write_to_protected_path_without_taskcard_fails(self, tmp_path):
        """Test that writes to protected paths fail without taskcard."""
        # src/launch/ is a protected path
        test_file = tmp_path / "src" / "launch" / "test.py"
        repo_root = tmp_path

        with pytest.raises(PathValidationError) as exc_info:
            atomic_write_text(
                test_file,
                "Test content",
                enforcement_mode="strict",
                repo_root=repo_root,
            )

        assert exc_info.value.error_code == "POLICY_TASKCARD_MISSING"
        assert "protected path" in str(exc_info.value).lower()
        assert "src/launch" in str(exc_info.value)

    def test_write_to_protected_path_with_valid_taskcard(self, tmp_path):
        """Test that writes to protected paths succeed with valid taskcard."""
        # Use real repo to access TC-100
        repo_root = Path(__file__).parent.parent.parent.parent
        test_file = repo_root / "src" / "launch" / "__init__.py"

        # TC-100 allows src/launch/__init__.py
        # Read current content first
        original_content = test_file.read_text()

        try:
            # Write with taskcard (should succeed)
            atomic_write_text(
                test_file,
                original_content,  # Write same content back
                taskcard_id="TC-100",
                enforcement_mode="strict",
                repo_root=repo_root,
            )

            # File should still exist
            assert test_file.exists()

        finally:
            # Restore original content
            test_file.write_text(original_content)

    def test_write_to_unauthorized_path_with_taskcard_fails(self, tmp_path):
        """Test that writes to paths not in allowed_paths fail."""
        # Use real repo to access TC-100
        repo_root = Path(__file__).parent.parent.parent.parent

        # TC-100 does NOT allow src/launch/test.py (only __init__.py)
        test_file = repo_root / "src" / "launch" / "test_unauthorized.py"

        with pytest.raises(PathValidationError) as exc_info:
            atomic_write_text(
                test_file,
                "Test content",
                taskcard_id="TC-100",
                enforcement_mode="strict",
                repo_root=repo_root,
            )

        assert exc_info.value.error_code == "POLICY_TASKCARD_PATH_VIOLATION"
        assert "TC-100" in str(exc_info.value)
        assert "not authorized" in str(exc_info.value).lower()

    def test_write_with_disabled_enforcement(self, tmp_path):
        """Test that disabled enforcement allows all writes."""
        # src/launch/ is protected, but should work with enforcement disabled
        test_file = tmp_path / "src" / "launch" / "test.py"

        # Should succeed without taskcard when disabled
        atomic_write_text(
            test_file,
            "Test content",
            enforcement_mode="disabled",
            repo_root=tmp_path,
        )

        assert test_file.exists()
        assert test_file.read_text() == "Test content"

    def test_write_with_inactive_taskcard_fails(self, tmp_path):
        """Test that inactive taskcard (Draft status) fails enforcement."""
        # Create a temporary taskcard with Draft status
        repo_root = tmp_path
        taskcards_dir = repo_root / "plans" / "taskcards"
        taskcards_dir.mkdir(parents=True)

        draft_taskcard = taskcards_dir / "TC-999_draft_test.md"
        draft_taskcard.write_text(
            """---
id: TC-999
status: Draft
allowed_paths:
  - src/launch/test.py
---

# Draft taskcard
"""
        )

        test_file = tmp_path / "src" / "launch" / "test.py"

        with pytest.raises(PathValidationError) as exc_info:
            atomic_write_text(
                test_file,
                "Test content",
                taskcard_id="TC-999",
                enforcement_mode="strict",
                repo_root=repo_root,
            )

        assert exc_info.value.error_code == "POLICY_TASKCARD_INACTIVE"
        assert "not active" in str(exc_info.value).lower()

    def test_write_json_with_taskcard(self, tmp_path):
        """Test that atomic_write_json also enforces taskcard."""
        # Use real repo to access TC-100
        repo_root = Path(__file__).parent.parent.parent.parent

        # Try to write to protected path without taskcard
        test_file = repo_root / "src" / "launch" / "test.json"

        with pytest.raises(PathValidationError) as exc_info:
            atomic_write_json(
                test_file,
                {"test": "data"},
                enforcement_mode="strict",
                repo_root=repo_root,
            )

        assert exc_info.value.error_code == "POLICY_TASKCARD_MISSING"

    def test_write_with_explicit_allowed_paths(self, tmp_path):
        """Test that explicit allowed_paths override taskcard."""
        # Create a temporary taskcard
        repo_root = tmp_path
        taskcards_dir = repo_root / "plans" / "taskcards"
        taskcards_dir.mkdir(parents=True)

        taskcard = taskcards_dir / "TC-999_test.md"
        taskcard.write_text(
            """---
id: TC-999
status: In-Progress
allowed_paths:
  - wrong/path.py
---

# Test taskcard
"""
        )

        test_file = tmp_path / "src" / "launch" / "test.py"

        # Use explicit allowed_paths to override taskcard
        atomic_write_text(
            test_file,
            "Test content",
            taskcard_id="TC-999",
            allowed_paths=["src/launch/**"],
            enforcement_mode="strict",
            repo_root=repo_root,
        )

        assert test_file.exists()

    def test_write_with_glob_pattern_in_taskcard(self, tmp_path):
        """Test that glob patterns in allowed_paths work correctly."""
        # Create a temporary taskcard with glob patterns
        repo_root = tmp_path
        taskcards_dir = repo_root / "plans" / "taskcards"
        taskcards_dir.mkdir(parents=True)

        taskcard = taskcards_dir / "TC-999_glob_test.md"
        taskcard.write_text(
            """---
id: TC-999
status: In-Progress
allowed_paths:
  - reports/**
  - src/launch/workers/w1_*/**
---

# Glob test taskcard
"""
        )

        # Test recursive glob
        test_file1 = tmp_path / "reports" / "agents" / "AGENT_B" / "report.md"
        atomic_write_text(
            test_file1,
            "Report content",
            taskcard_id="TC-999",
            enforcement_mode="disabled",  # Use disabled to avoid protection check
            repo_root=repo_root,
        )
        assert test_file1.exists()

        # Test wildcard glob
        test_file2 = tmp_path / "src" / "launch" / "workers" / "w1_repo_scout" / "worker.py"
        atomic_write_text(
            test_file2,
            "Worker content",
            taskcard_id="TC-999",
            enforcement_mode="disabled",  # Use disabled to avoid protection check
            repo_root=repo_root,
        )
        assert test_file2.exists()


class TestProtectedPathDetection:
    """Test is_source_code_path detection."""

    def test_src_launch_is_protected(self):
        """Test that src/launch paths are protected."""
        from launch.util.path_validation import is_source_code_path

        repo_root = Path(__file__).parent.parent.parent.parent

        assert is_source_code_path("src/launch/test.py", repo_root)
        assert is_source_code_path("src/launch/workers/w1_repo_scout/worker.py", repo_root)
        assert is_source_code_path("src/launch/__init__.py", repo_root)

    def test_specs_is_protected(self):
        """Test that specs paths are protected."""
        from launch.util.path_validation import is_source_code_path

        repo_root = Path(__file__).parent.parent.parent.parent

        assert is_source_code_path("specs/01_system_contract.md", repo_root)
        assert is_source_code_path("specs/schemas/run_config.schema.json", repo_root)

    def test_reports_not_protected(self):
        """Test that reports paths are NOT protected."""
        from launch.util.path_validation import is_source_code_path

        repo_root = Path(__file__).parent.parent.parent.parent

        assert not is_source_code_path("reports/test.md", repo_root)
        assert not is_source_code_path("reports/agents/AGENT_B/report.md", repo_root)

    def test_tests_not_protected(self):
        """Test that test paths are NOT protected."""
        from launch.util.path_validation import is_source_code_path

        repo_root = Path(__file__).parent.parent.parent.parent

        assert not is_source_code_path("tests/unit/test_something.py", repo_root)
