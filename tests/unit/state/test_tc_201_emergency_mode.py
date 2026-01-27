"""Unit tests for TC-201: Emergency mode flag and policy plumbing.

Tests for:
- src/launch/state/emergency_mode.py
- src/launch/orchestrator/policy_enforcement.py
- src/launch/workers/_shared/policy_check.py

Spec references:
- plans/taskcards/TC-201_emergency_mode_manual_edits.md
- plans/policies/no_manual_content_edits.md
- specs/schemas/run_config.schema.json
- specs/schemas/validation_report.schema.json
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict

import pytest

# Import modules under test
from launch.state.emergency_mode import (
    is_emergency_mode_enabled,
    get_emergency_mode_config,
    validate_emergency_mode_preconditions,
    format_emergency_mode_warning,
)
from launch.orchestrator.policy_enforcement import (
    check_manual_edits_documentation,
    enforce_pr_requirements,
    create_policy_enforcement_report,
)
from launch.workers._shared.policy_check import (
    enumerate_changed_content_files,
    check_file_in_patch_index,
    find_unexplained_diffs,
    create_policy_violation_issue,
    validate_manual_edits_policy,
    update_validation_report_for_manual_edits,
)


# ============================================================================
# emergency_mode.py tests
# ============================================================================


def test_is_emergency_mode_enabled_default():
    """Test that emergency mode defaults to False when not specified."""
    run_config = {}
    assert is_emergency_mode_enabled(run_config) is False


def test_is_emergency_mode_enabled_explicit_false():
    """Test that emergency mode is False when explicitly set."""
    run_config = {"allow_manual_edits": False}
    assert is_emergency_mode_enabled(run_config) is False


def test_is_emergency_mode_enabled_explicit_true():
    """Test that emergency mode is True when explicitly enabled."""
    run_config = {"allow_manual_edits": True}
    assert is_emergency_mode_enabled(run_config) is True


def test_get_emergency_mode_config():
    """Test emergency mode config extraction."""
    run_config = {"allow_manual_edits": True}
    config = get_emergency_mode_config(run_config)
    assert config == {"allow_manual_edits": True}


def test_validate_emergency_mode_preconditions_not_enabled():
    """Test precondition validation when emergency mode not enabled."""
    run_config = {"allow_manual_edits": False}
    valid, errors = validate_emergency_mode_preconditions(run_config)
    assert valid is False
    assert len(errors) == 1
    assert "not enabled" in errors[0].lower()


def test_validate_emergency_mode_preconditions_no_validation_report():
    """Test precondition validation with emergency mode enabled, no validation report."""
    run_config = {"allow_manual_edits": True}
    valid, errors = validate_emergency_mode_preconditions(run_config)
    assert valid is True
    assert len(errors) == 0


def test_validate_emergency_mode_preconditions_validation_report_missing_manual_edits():
    """Test precondition validation when validation_report.manual_edits is False."""
    run_config = {"allow_manual_edits": True}
    validation_report = {"manual_edits": False}
    valid, errors = validate_emergency_mode_preconditions(run_config, validation_report)
    assert valid is False
    assert any("manual_edits must be true" in e for e in errors)


def test_validate_emergency_mode_preconditions_validation_report_no_files():
    """Test precondition validation when manual_edited_files is empty."""
    run_config = {"allow_manual_edits": True}
    validation_report = {"manual_edits": True, "manual_edited_files": []}
    valid, errors = validate_emergency_mode_preconditions(run_config, validation_report)
    assert valid is False
    assert any("enumerate all manually" in e for e in errors)


def test_validate_emergency_mode_preconditions_all_met():
    """Test precondition validation when all requirements are met."""
    run_config = {"allow_manual_edits": True}
    validation_report = {
        "manual_edits": True,
        "manual_edited_files": ["content/docs/page.md"]
    }
    valid, errors = validate_emergency_mode_preconditions(run_config, validation_report)
    assert valid is True
    assert len(errors) == 0


def test_format_emergency_mode_warning():
    """Test emergency mode warning formatting."""
    files = ["content/docs/a.md", "content/docs/b.md"]
    warning = format_emergency_mode_warning(files)
    assert "EMERGENCY MODE ACTIVE" in warning
    assert "2" in warning  # file count
    assert "content/docs/a.md" in warning
    assert "content/docs/b.md" in warning


# ============================================================================
# policy_enforcement.py tests
# ============================================================================


def test_check_manual_edits_documentation_no_emergency_mode():
    """Test that check passes when emergency mode not enabled."""
    run_config = {"allow_manual_edits": False}
    validation_report = {"manual_edits": False}
    ok, issues = check_manual_edits_documentation(run_config, validation_report)
    assert ok is True
    assert len(issues) == 0


def test_check_manual_edits_documentation_no_manual_edits():
    """Test that check passes when emergency mode enabled but no manual edits."""
    run_config = {"allow_manual_edits": True}
    validation_report = {"manual_edits": False}
    ok, issues = check_manual_edits_documentation(run_config, validation_report)
    assert ok is True
    assert len(issues) == 0


def test_check_manual_edits_documentation_files_not_enumerated():
    """Test that check fails when manual_edited_files is empty."""
    run_config = {"allow_manual_edits": True}
    validation_report = {"manual_edits": True, "manual_edited_files": []}
    ok, issues = check_manual_edits_documentation(run_config, validation_report)
    assert ok is False
    assert len(issues) == 1
    assert issues[0]["severity"] == "blocker"
    assert issues[0]["error_code"] == "MANUAL_EDITS_NOT_ENUMERATED"


def test_check_manual_edits_documentation_no_master_review():
    """Test that check fails when master review is missing."""
    run_config = {"allow_manual_edits": True}
    validation_report = {
        "manual_edits": True,
        "manual_edited_files": ["content/docs/page.md"]
    }
    ok, issues = check_manual_edits_documentation(run_config, validation_report, None)
    assert ok is False
    assert len(issues) == 1
    assert issues[0]["severity"] == "blocker"
    assert issues[0]["error_code"] == "MASTER_REVIEW_MISSING"


def test_check_manual_edits_documentation_no_manual_edits_section():
    """Test that check fails when master review lacks manual_edits section."""
    run_config = {"allow_manual_edits": True}
    validation_report = {
        "manual_edits": True,
        "manual_edited_files": ["content/docs/page.md"]
    }
    master_review = {"other_section": "data"}
    ok, issues = check_manual_edits_documentation(run_config, validation_report, master_review)
    assert ok is False
    assert len(issues) == 1
    assert issues[0]["error_code"] == "MASTER_REVIEW_NO_MANUAL_EDITS_SECTION"


def test_check_manual_edits_documentation_undocumented_files():
    """Test that check fails when some files are not documented."""
    run_config = {"allow_manual_edits": True}
    validation_report = {
        "manual_edits": True,
        "manual_edited_files": ["content/docs/a.md", "content/docs/b.md"]
    }
    master_review = {
        "manual_edits": {
            "files": ["content/docs/a.md"],  # Missing b.md
            "rationale": "Emergency fix needed for production issue."
        }
    }
    ok, issues = check_manual_edits_documentation(run_config, validation_report, master_review)
    assert ok is False
    assert len(issues) == 1
    assert issues[0]["error_code"] == "MANUAL_EDITS_UNDOCUMENTED_FILES"
    assert "content/docs/b.md" in str(issues[0]["message"])


def test_check_manual_edits_documentation_insufficient_rationale():
    """Test that check fails when rationale is too short."""
    run_config = {"allow_manual_edits": True}
    validation_report = {
        "manual_edits": True,
        "manual_edited_files": ["content/docs/page.md"]
    }
    master_review = {
        "manual_edits": {
            "files": ["content/docs/page.md"],
            "rationale": "Fix"  # Too short (< 20 chars)
        }
    }
    ok, issues = check_manual_edits_documentation(run_config, validation_report, master_review)
    assert ok is False
    assert len(issues) == 1
    assert issues[0]["error_code"] == "MASTER_REVIEW_INSUFFICIENT_RATIONALE"


def test_check_manual_edits_documentation_all_requirements_met():
    """Test that check passes when all documentation requirements are met."""
    run_config = {"allow_manual_edits": True}
    validation_report = {
        "manual_edits": True,
        "manual_edited_files": ["content/docs/page.md"]
    }
    master_review = {
        "manual_edits": {
            "files": ["content/docs/page.md"],
            "rationale": "Emergency fix needed to correct critical production error in documentation."
        }
    }
    ok, issues = check_manual_edits_documentation(run_config, validation_report, master_review)
    assert ok is True
    assert len(issues) == 0


def test_enforce_pr_requirements_no_pr_data():
    """Test that PR enforcement passes when no PR data provided."""
    run_config = {"allow_manual_edits": True}
    validation_report = {"manual_edits": True}
    ok, issues = enforce_pr_requirements(run_config, validation_report, None)
    assert ok is True
    assert len(issues) == 0


def test_enforce_pr_requirements_missing_emergency_notice():
    """Test that PR enforcement fails when emergency notice missing."""
    run_config = {"allow_manual_edits": True}
    validation_report = {
        "manual_edits": True,
        "manual_edited_files": ["content/docs/page.md"]
    }
    pr_data = {"body": "This PR adds documentation for feature X."}
    ok, issues = enforce_pr_requirements(run_config, validation_report, pr_data)
    assert ok is False
    assert len(issues) == 1
    assert issues[0]["error_code"] == "PR_MISSING_EMERGENCY_MODE_NOTICE"


def test_enforce_pr_requirements_with_emergency_notice():
    """Test that PR enforcement passes when emergency notice present."""
    run_config = {"allow_manual_edits": True}
    validation_report = {
        "manual_edits": True,
        "manual_edited_files": ["content/docs/page.md"]
    }
    pr_data = {
        "body": "This PR includes emergency mode changes. Manual edits were required."
    }
    ok, issues = enforce_pr_requirements(run_config, validation_report, pr_data)
    assert ok is True
    assert len(issues) == 0


def test_create_policy_enforcement_report():
    """Test comprehensive policy enforcement report creation."""
    run_config = {"allow_manual_edits": True}
    validation_report = {
        "manual_edits": True,
        "manual_edited_files": ["content/docs/page.md"]
    }
    master_review = {
        "manual_edits": {
            "files": ["content/docs/page.md"],
            "rationale": "Emergency fix for critical production error."
        }
    }
    pr_data = {"body": "Emergency mode active due to critical issue."}

    report = create_policy_enforcement_report(
        run_config, validation_report, master_review, pr_data
    )

    assert report["ok"] is True
    assert report["emergency_mode_enabled"] is True
    assert report["manual_edits_occurred"] is True
    assert report["checks"]["manual_edits_documentation"] is True
    assert report["checks"]["pr_requirements"] is True
    assert report["blocker_count"] == 0


# ============================================================================
# policy_check.py tests
# ============================================================================


@pytest.fixture
def temp_git_repo():
    """Create a temporary git repository for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # Initialize git repo
        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_path, check=True, capture_output=True
        )

        # Create initial content
        (repo_path / "page.md").write_text("# Initial content")
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=repo_path, check=True, capture_output=True
        )

        yield repo_path


def test_enumerate_changed_content_files_no_changes(temp_git_repo):
    """Test enumeration returns empty list when no changes."""
    changed = enumerate_changed_content_files(temp_git_repo)
    assert changed == []


def test_enumerate_changed_content_files_with_changes(temp_git_repo):
    """Test enumeration detects changed markdown files."""
    # Modify existing file
    (temp_git_repo / "page.md").write_text("# Updated content")

    # Add new file
    (temp_git_repo / "new.md").write_text("# New page")
    subprocess.run(["git", "add", "."], cwd=temp_git_repo, check=True, capture_output=True)

    changed = enumerate_changed_content_files(temp_git_repo)
    assert len(changed) == 2
    assert "new.md" in changed
    assert "page.md" in changed


def test_enumerate_changed_content_files_filters_non_content(temp_git_repo):
    """Test enumeration filters out non-content files."""
    (temp_git_repo / "page.md").write_text("# Updated")
    (temp_git_repo / "script.py").write_text("print('hello')")
    subprocess.run(["git", "add", "."], cwd=temp_git_repo, check=True, capture_output=True)

    changed = enumerate_changed_content_files(temp_git_repo)
    assert changed == ["page.md"]
    assert "script.py" not in changed


def test_enumerate_changed_content_files_deterministic(temp_git_repo):
    """Test that enumeration is deterministic (sorted)."""
    files = ["z.md", "a.md", "m.md"]
    for f in files:
        (temp_git_repo / f).write_text(f"# {f}")
    subprocess.run(["git", "add", "."], cwd=temp_git_repo, check=True, capture_output=True)

    changed = enumerate_changed_content_files(temp_git_repo)
    assert changed == sorted(files)


def test_check_file_in_patch_index_exists():
    """Test checking if file exists in patch index."""
    patch_index = {
        "files": {
            "content/docs/page.md": {"patch_id": "p1"}
        }
    }
    assert check_file_in_patch_index("content/docs/page.md", patch_index) is True


def test_check_file_in_patch_index_not_exists():
    """Test checking if file does not exist in patch index."""
    patch_index = {"files": {}}
    assert check_file_in_patch_index("content/docs/page.md", patch_index) is False


def test_find_unexplained_diffs():
    """Test finding files without patch records."""
    changed_files = ["a.md", "b.md", "c.md"]
    patch_index = {
        "files": {
            "a.md": {"patch_id": "p1"},
            "c.md": {"patch_id": "p2"}
        }
    }
    unexplained = find_unexplained_diffs(changed_files, patch_index)
    assert unexplained == ["b.md"]


def test_create_policy_violation_issue_default_mode():
    """Test creating blocker issue in default mode."""
    files = ["page.md"]
    issue = create_policy_violation_issue(files, allow_manual_edits=False)
    assert issue["severity"] == "blocker"
    assert issue["error_code"] == "POLICY_MANUAL_EDITS_FORBIDDEN"
    assert "forbidden" in issue["message"].lower()


def test_create_policy_violation_issue_emergency_mode():
    """Test creating warning issue in emergency mode."""
    files = ["page.md"]
    issue = create_policy_violation_issue(files, allow_manual_edits=True)
    assert issue["severity"] == "warn"
    assert issue["error_code"] == "MANUAL_EDITS_DETECTED"


def test_validate_manual_edits_policy_no_changes(temp_git_repo):
    """Test policy validation passes when no changes."""
    run_config = {"allow_manual_edits": False}
    patch_index = {"files": {}}

    ok, manual_files, issues = validate_manual_edits_policy(
        temp_git_repo, run_config, patch_index
    )
    assert ok is True
    assert manual_files == []
    assert issues == []


def test_validate_manual_edits_policy_explained_changes(temp_git_repo):
    """Test policy validation passes when all changes are explained."""
    (temp_git_repo / "page.md").write_text("# Updated")
    subprocess.run(["git", "add", "."], cwd=temp_git_repo, check=True, capture_output=True)

    run_config = {"allow_manual_edits": False}
    patch_index = {"files": {"page.md": {"patch_id": "p1"}}}

    ok, manual_files, issues = validate_manual_edits_policy(
        temp_git_repo, run_config, patch_index
    )
    assert ok is True
    assert manual_files == []
    assert issues == []


def test_validate_manual_edits_policy_unexplained_default_mode(temp_git_repo):
    """Test policy validation fails for unexplained changes in default mode."""
    (temp_git_repo / "page.md").write_text("# Updated")
    subprocess.run(["git", "add", "."], cwd=temp_git_repo, check=True, capture_output=True)

    run_config = {"allow_manual_edits": False}
    patch_index = {"files": {}}

    ok, manual_files, issues = validate_manual_edits_policy(
        temp_git_repo, run_config, patch_index
    )
    assert ok is False
    assert manual_files == []
    assert len(issues) == 1
    assert issues[0]["severity"] == "blocker"


def test_validate_manual_edits_policy_unexplained_emergency_mode(temp_git_repo):
    """Test policy validation records files in emergency mode."""
    (temp_git_repo / "page.md").write_text("# Updated")
    subprocess.run(["git", "add", "."], cwd=temp_git_repo, check=True, capture_output=True)

    run_config = {"allow_manual_edits": True}
    patch_index = {"files": {}}

    ok, manual_files, issues = validate_manual_edits_policy(
        temp_git_repo, run_config, patch_index
    )
    assert ok is True
    assert manual_files == ["page.md"]
    assert issues == []


def test_update_validation_report_for_manual_edits_with_files():
    """Test updating validation report when manual files exist."""
    validation_report = {"ok": True, "gates": [], "issues": []}
    manual_files = ["b.md", "a.md"]

    updated = update_validation_report_for_manual_edits(validation_report, manual_files)
    assert updated["manual_edits"] is True
    assert updated["manual_edited_files"] == ["a.md", "b.md"]  # Sorted


def test_update_validation_report_for_manual_edits_no_files():
    """Test updating validation report when no manual files."""
    validation_report = {"ok": True, "gates": [], "issues": []}
    manual_files = []

    updated = update_validation_report_for_manual_edits(validation_report, manual_files)
    assert updated["manual_edits"] is False
    assert updated["manual_edited_files"] == []


# ============================================================================
# Acceptance criteria tests
# ============================================================================


def test_acceptance_default_behavior_forbids_manual_edits(temp_git_repo):
    """ACCEPTANCE: Default behavior forbids manual edits and fails with policy BLOCKER."""
    # Setup: modify file without patch record
    (temp_git_repo / "page.md").write_text("# Manual edit")
    subprocess.run(["git", "add", "."], cwd=temp_git_repo, check=True, capture_output=True)

    # Validate with default config (allow_manual_edits=False)
    run_config = {"allow_manual_edits": False}
    patch_index = {"files": {}}

    ok, manual_files, issues = validate_manual_edits_policy(
        temp_git_repo, run_config, patch_index
    )

    # Assert: validation fails with blocker
    assert ok is False
    assert len(issues) == 1
    assert issues[0]["severity"] == "blocker"
    assert issues[0]["gate"] == "policy"


def test_acceptance_emergency_mode_records_files(temp_git_repo):
    """ACCEPTANCE: Emergency mode records manual_edits=true and enumerates files."""
    # Setup: modify files without patch records
    (temp_git_repo / "a.md").write_text("# Manual edit A")
    (temp_git_repo / "b.md").write_text("# Manual edit B")
    subprocess.run(["git", "add", "."], cwd=temp_git_repo, check=True, capture_output=True)

    # Validate with emergency mode enabled
    run_config = {"allow_manual_edits": True}
    patch_index = {"files": {}}

    ok, manual_files, issues = validate_manual_edits_policy(
        temp_git_repo, run_config, patch_index
    )

    # Assert: validation passes and records files
    assert ok is True
    assert len(manual_files) == 2
    assert "a.md" in manual_files
    assert "b.md" in manual_files
    assert issues == []

    # Update validation report
    validation_report = {"ok": True, "gates": [], "issues": []}
    updated = update_validation_report_for_manual_edits(validation_report, manual_files)

    assert updated["manual_edits"] is True
    assert len(updated["manual_edited_files"]) == 2


def test_acceptance_deterministic_enumeration(temp_git_repo):
    """ACCEPTANCE: File enumeration is deterministic (stable sort)."""
    # Add files in random order
    files = ["z.md", "a.md", "m.md", "b.md"]
    for f in files:
        (temp_git_repo / f).write_text(f"# {f}")
    subprocess.run(["git", "add", "."], cwd=temp_git_repo, check=True, capture_output=True)

    # Run enumeration multiple times
    result1 = enumerate_changed_content_files(temp_git_repo)
    result2 = enumerate_changed_content_files(temp_git_repo)

    # Assert: results are identical and sorted
    assert result1 == result2
    assert result1 == sorted(files)
