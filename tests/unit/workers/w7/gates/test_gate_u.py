"""Unit tests for Gate U: Taskcard Authorization (Layer 4).

Tests post-run audit of file modifications against taskcard allowed_paths.
"""

import json
import tempfile
from pathlib import Path

import pytest

from launch.workers.w7_validator.gates import gate_u_taskcard_authorization


class TestGateU:
    """Test Gate U: Taskcard Authorization."""

    def test_prod_run_without_taskcard_fails(self, tmp_path):
        """Test that production run without taskcard fails."""
        run_dir = tmp_path / "runs" / "test-run"
        run_dir.mkdir(parents=True)

        # Create run_config without taskcard
        run_config = {"validation_profile": "prod"}
        run_config_path = run_dir / "run_config.json"
        with run_config_path.open("w") as f:
            json.dump(run_config, f)

        # Execute gate
        gate_passed, issues = gate_u_taskcard_authorization.execute_gate(
            run_dir, "prod"
        )

        assert not gate_passed
        assert len(issues) == 1
        assert issues[0]["severity"] == "blocker"
        assert issues[0]["error_code"] == "GATE_U_TASKCARD_MISSING"
        assert "production" in issues[0]["message"].lower()

    def test_local_run_without_taskcard_passes(self, tmp_path):
        """Test that local run without taskcard passes."""
        run_dir = tmp_path / "runs" / "test-run"
        run_dir.mkdir(parents=True)

        # Create run_config without taskcard (local mode)
        run_config = {"validation_profile": "local"}
        run_config_path = run_dir / "run_config.json"
        with run_config_path.open("w") as f:
            json.dump(run_config, f)

        # Execute gate
        gate_passed, issues = gate_u_taskcard_authorization.execute_gate(
            run_dir, "local"
        )

        # Should pass (local mode doesn't require taskcard)
        assert gate_passed
        assert len(issues) == 0

    def test_run_with_invalid_taskcard_fails(self, tmp_path):
        """Test that run with nonexistent taskcard fails."""
        run_dir = tmp_path / "runs" / "test-run"
        run_dir.mkdir(parents=True)

        # Create run_config with nonexistent taskcard
        run_config = {"taskcard_id": "TC-9999", "validation_profile": "local"}
        run_config_path = run_dir / "run_config.json"
        with run_config_path.open("w") as f:
            json.dump(run_config, f)

        # Execute gate
        gate_passed, issues = gate_u_taskcard_authorization.execute_gate(
            run_dir, "local"
        )

        assert not gate_passed
        assert len(issues) == 1
        assert issues[0]["severity"] == "blocker"
        assert issues[0]["error_code"] == "GATE_U_TASKCARD_LOAD_FAILED"
        assert "TC-9999" in issues[0]["message"]

    def test_run_with_inactive_taskcard_fails(self, tmp_path):
        """Test that run with inactive taskcard (Draft) fails."""
        run_dir = tmp_path / "runs" / "test-run"
        run_dir.mkdir(parents=True)

        # Create taskcard with Draft status
        taskcards_dir = tmp_path / "plans" / "taskcards"
        taskcards_dir.mkdir(parents=True)

        taskcard_file = taskcards_dir / "TC-999_draft_test.md"
        taskcard_file.write_text(
            """---
id: TC-999
status: Draft
allowed_paths:
  - reports/**
---

# Draft taskcard
"""
        )

        # Create run_config
        run_config = {"taskcard_id": "TC-999", "validation_profile": "local"}
        run_config_path = run_dir / "run_config.json"
        with run_config_path.open("w") as f:
            json.dump(run_config, f)

        # Execute gate
        gate_passed, issues = gate_u_taskcard_authorization.execute_gate(
            run_dir, "local"
        )

        assert not gate_passed
        assert len(issues) == 1
        assert issues[0]["severity"] == "blocker"
        assert issues[0]["error_code"] == "GATE_U_TASKCARD_INACTIVE"
        assert "not active" in issues[0]["message"].lower()

    def test_run_with_valid_taskcard_no_modifications_passes(self, tmp_path):
        """Test that run with valid taskcard and no modifications passes."""
        run_dir = tmp_path / "runs" / "test-run"
        run_dir.mkdir(parents=True)

        # Create taskcard with In-Progress status
        taskcards_dir = tmp_path / "plans" / "taskcards"
        taskcards_dir.mkdir(parents=True)

        taskcard_file = taskcards_dir / "TC-999_test.md"
        taskcard_file.write_text(
            """---
id: TC-999
status: In-Progress
allowed_paths:
  - reports/**
---

# Test taskcard
"""
        )

        # Create run_config
        run_config = {"taskcard_id": "TC-999", "validation_profile": "local"}
        run_config_path = run_dir / "run_config.json"
        with run_config_path.open("w") as f:
            json.dump(run_config, f)

        # Create empty work/site directory (no git repo, so no modified files)
        site_dir = run_dir / "work" / "site"
        site_dir.mkdir(parents=True)

        # Execute gate
        gate_passed, issues = gate_u_taskcard_authorization.execute_gate(
            run_dir, "local"
        )

        # Should pass (no modifications)
        assert gate_passed
        assert len(issues) == 0

    def test_missing_run_config_passes(self, tmp_path):
        """Test that missing run_config.json passes (Gate 1 will catch)."""
        run_dir = tmp_path / "runs" / "test-run"
        run_dir.mkdir(parents=True)

        # No run_config.json created

        # Execute gate
        gate_passed, issues = gate_u_taskcard_authorization.execute_gate(
            run_dir, "local"
        )

        # Should pass (cannot validate without run_config)
        assert gate_passed
        assert len(issues) == 0


class TestGateUGetModifiedFiles:
    """Test get_modified_files_git helper."""

    def test_non_git_directory_returns_empty(self, tmp_path):
        """Test that non-git directory returns empty list."""
        site_dir = tmp_path / "site"
        site_dir.mkdir()

        modified = gate_u_taskcard_authorization.get_modified_files_git(site_dir)

        assert modified == []

    def test_nonexistent_directory_returns_empty(self, tmp_path):
        """Test that nonexistent directory returns empty list."""
        site_dir = tmp_path / "nonexistent"

        modified = gate_u_taskcard_authorization.get_modified_files_git(site_dir)

        assert modified == []
