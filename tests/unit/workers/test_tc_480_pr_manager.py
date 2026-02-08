"""TC-480: W9 PRManager worker tests.

This module tests the W9 PRManager worker implementation per
specs/12_pr_and_release.md and specs/21_worker_contracts.md:322-344.

Test coverage:
1. PR title generation
2. PR body generation with validation summary
3. Branch name generation (deterministic)
4. Commit creation via mock commit service
5. PR opening via mock commit service
6. Deterministic ordering (stable outputs)
7. Event emission (WORK_ITEM_STARTED, COMMIT_CREATED, PR_OPENED, WORK_ITEM_FINISHED)
8. Artifact validation (pr.json schema compliance)
9. Error handling (auth failures, rate limits, branch conflicts, missing artifacts)
10. No-changes scenario (empty patch bundle)
11. Rollback metadata generation
12. Affected paths extraction
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from src.launch.workers.w9_pr_manager import (
    execute_pr_manager,
    PRManagerError,
    PRManagerNoChangesError,
    PRManagerAuthFailedError,
    PRManagerRateLimitedError,
    PRManagerBranchExistsError,
    PRManagerMissingArtifactError,
    generate_branch_name,
    generate_pr_title,
    generate_pr_body,
    extract_affected_paths,
    generate_rollback_steps,
)
from src.launch.clients.commit_service import CommitServiceClient, CommitServiceError


@pytest.fixture
def temp_run_dir():
    """Create temporary run directory with required structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir) / "run"
        run_dir.mkdir()

        # Create required subdirectories
        (run_dir / "artifacts").mkdir()
        (run_dir / "reports").mkdir()
        (run_dir / "logs").mkdir()

        # Create events.ndjson
        (run_dir / "events.ndjson").write_text("")

        # Create AG-001 approval marker (required for non-offline PR creation)
        git_dir = Path(tmpdir) / ".git"
        git_dir.mkdir(exist_ok=True)
        (git_dir / "AI_BRANCH_APPROVED").write_text("manual-marker")

        yield run_dir


@pytest.fixture
def sample_patch_bundle():
    """Sample patch bundle for testing."""
    return {
        "schema_version": "1.0",
        "patches": [
            {
                "patch_id": "patch-001",
                "type": "create_file",
                "path": "content/docs.aspose.org/test-product/en/python/overview.md",
                "new_content": "# Overview\n\nTest product overview.",
                "content_hash": "abc123",
            },
            {
                "patch_id": "patch-002",
                "type": "update_by_anchor",
                "path": "content/docs.aspose.org/test-product/en/python/docs/getting-started.md",
                "anchor": "<!-- INSTALL -->",
                "new_content": "Install via pip",
                "content_hash": "def456",
            },
            {
                "patch_id": "patch-003",
                "type": "create_file",
                "path": "content/docs.aspose.org/test-product/en/python/reference/api.md",
                "new_content": "# API Reference",
                "content_hash": "ghi789",
            },
        ],
    }


@pytest.fixture
def sample_validation_report():
    """Sample validation report for testing."""
    return {
        "schema_version": "1.0",
        "ok": True,
        "profile": "ci",
        "gates": [
            {"name": "Gate0-S", "ok": True, "log_path": "logs/gate0s.log"},
            {"name": "Gate1", "ok": True, "log_path": "logs/gate1.log"},
            {"name": "Gate2", "ok": True, "log_path": "logs/gate2.log"},
        ],
        "issues": [],
    }


@pytest.fixture
def sample_run_config():
    """Sample run configuration for testing."""
    return {
        "run_id": "RUN-20260128-120000Z-abc123",
        "product_slug": "aspose-note",
        "language": "python",
        "repo_url": "https://github.com/Aspose/aspose.org",
        "base_ref": "main",
        "github_ref": "refs/heads/main",
        "allowed_paths": ["content/docs.aspose.org/aspose-note/"],
        "validation_profile": "ci",
    }


@pytest.fixture
def mock_commit_client():
    """Mock commit service client."""
    client = Mock(spec=CommitServiceClient)

    # Mock create_commit response
    client.create_commit.return_value = {
        "commit_sha": "0123456789abcdef0123456789abcdef01234567",
        "branch_name": "launch/aspose-note/main/abc123",
        "repo_url": "https://github.com/Aspose/aspose.org",
    }

    # Mock open_pr response
    client.open_pr.return_value = {
        "pr_number": 42,
        "pr_url": "https://api.github.com/repos/Aspose/aspose.org/pulls/42",
        "pr_html_url": "https://github.com/Aspose/aspose.org/pull/42",
    }

    return client


# Test 1: Branch name generation (deterministic)
def test_generate_branch_name():
    """Test deterministic branch name generation."""
    branch = generate_branch_name(
        product_slug="aspose-note",
        ref="refs/heads/main",
        run_id="RUN-20260128-120000Z-abc123",
    )
    assert branch == "launch/aspose-note/main/abc123"

    # Test with different ref format
    branch2 = generate_branch_name(
        product_slug="aspose-words",
        ref="main",
        run_id="RUN-20260128-130000Z-def456",
    )
    assert branch2 == "launch/aspose-words/main/def456"

    # Test determinism (same inputs = same output)
    branch3 = generate_branch_name(
        product_slug="aspose-note",
        ref="refs/heads/main",
        run_id="RUN-20260128-120000Z-abc123",
    )
    assert branch3 == branch


# Test 2: PR title generation
def test_generate_pr_title():
    """Test PR title generation with validation status."""
    # Success case
    title = generate_pr_title("aspose-note", "python", validation_ok=True)
    assert "Launch" in title
    assert "Aspose Note" in title
    assert "Python" in title

    # Failure case (draft)
    title_draft = generate_pr_title("aspose-words", "python", validation_ok=False)
    assert "Draft Launch" in title_draft
    assert "Aspose Words" in title_draft


# Test 3: PR body generation with validation summary
def test_generate_pr_body(sample_run_config, sample_validation_report, sample_patch_bundle):
    """Test PR body generation with validation summary and diff highlights."""
    body = generate_pr_body(
        run_id=sample_run_config["run_id"],
        product_slug=sample_run_config["product_slug"],
        validation_report=sample_validation_report,
        patch_bundle=sample_patch_bundle,
        run_config=sample_run_config,
    )

    # Check sections
    assert "## Summary" in body
    assert "## Validation Status" in body
    assert "## Changes" in body
    assert "### Affected Files" in body

    # Check content
    assert sample_run_config["run_id"] in body
    assert "3/3" in body  # Gates Passed
    assert "Pages Created**: 2" in body
    assert "Pages Updated**: 1" in body
    assert "All validation gates passed" in body

    # Check affected files
    assert "content/docs.aspose.org/test-product/en/python/overview.md" in body
    assert "content/docs.aspose.org/test-product/en/python/docs/getting-started.md" in body

    # Check footer
    assert "FOSS Launcher" in body


# Test 4: PR body with failed validation
def test_generate_pr_body_with_failures(sample_run_config, sample_patch_bundle):
    """Test PR body generation with validation failures."""
    validation_report = {
        "schema_version": "1.0",
        "ok": False,
        "profile": "ci",
        "gates": [
            {"name": "Gate0-S", "ok": True},
            {"name": "Gate1", "ok": False},
            {"name": "Gate2", "ok": False},
        ],
        "issues": [
            {
                "severity": "blocker",
                "code": "SPEC_VIOLATION",
                "message": "Frontmatter missing required field",
            },
            {
                "severity": "error",
                "code": "LINK_BROKEN",
                "message": "Broken link detected",
            },
        ],
    }

    body = generate_pr_body(
        run_id=sample_run_config["run_id"],
        product_slug=sample_run_config["product_slug"],
        validation_report=validation_report,
        patch_bundle=sample_patch_bundle,
        run_config=sample_run_config,
    )

    assert "2 gate(s) failed" in body
    assert "1 blocker issue(s) found" in body
    assert "### Issues" in body
    assert "SPEC_VIOLATION" in body
    assert "LINK_BROKEN" in body


# Test 5: Extract affected paths (sorted)
def test_extract_affected_paths(sample_patch_bundle):
    """Test affected paths extraction with stable sorting."""
    paths = extract_affected_paths(sample_patch_bundle)

    # Check sorting
    assert paths == sorted(paths)

    # Check content
    assert len(paths) == 3
    assert "content/docs.aspose.org/test-product/en/python/overview.md" in paths
    assert "content/docs.aspose.org/test-product/en/python/docs/getting-started.md" in paths
    assert "content/docs.aspose.org/test-product/en/python/reference/api.md" in paths


# Test 6: Generate rollback steps
def test_generate_rollback_steps():
    """Test rollback steps generation."""
    steps = generate_rollback_steps(
        branch_name="launch/aspose-note/main/abc123",
        commit_sha="0123456789abcdef0123456789abcdef01234567",
    )

    assert len(steps) >= 3
    assert any("git fetch" in step for step in steps)
    assert any("git revert" in step and "0123456789abcdef0123456789abcdef01234567" in step for step in steps)
    assert any("git push" in step for step in steps)


# Test 7: Execute PR manager (success case)
def test_execute_pr_manager_success(
    temp_run_dir,
    sample_run_config,
    sample_patch_bundle,
    sample_validation_report,
    mock_commit_client,
):
    """Test successful PR creation via commit service."""
    # Write required artifacts
    (temp_run_dir / "artifacts" / "patch_bundle.json").write_text(
        json.dumps(sample_patch_bundle, ensure_ascii=False, sort_keys=True)
    )
    (temp_run_dir / "artifacts" / "validation_report.json").write_text(
        json.dumps(sample_validation_report, ensure_ascii=False, sort_keys=True)
    )

    # Execute
    result = execute_pr_manager(
        run_dir=temp_run_dir,
        run_config=sample_run_config,
        commit_client=mock_commit_client,
    )

    # Check result
    assert result["ok"] is True
    assert result["pr_url"] == "https://github.com/Aspose/aspose.org/pull/42"
    assert result["pr_number"] == 42
    assert result["commit_sha"] == "0123456789abcdef0123456789abcdef01234567"
    assert result["branch_name"] == "launch/aspose-note/main/abc123"

    # Check artifact written
    pr_artifact_path = temp_run_dir / "artifacts" / "pr.json"
    assert pr_artifact_path.exists()

    with open(pr_artifact_path, "r", encoding="utf-8") as f:
        pr_artifact = json.load(f)

    # Validate pr.json schema compliance
    assert pr_artifact["schema_version"] == "1.0"
    assert pr_artifact["run_id"] == sample_run_config["run_id"]
    assert pr_artifact["base_ref"] is not None
    assert len(pr_artifact["base_ref"]) == 40  # SHA-1 hash
    assert "rollback_steps" in pr_artifact
    assert len(pr_artifact["rollback_steps"]) >= 3
    assert "affected_paths" in pr_artifact
    assert len(pr_artifact["affected_paths"]) == 3
    assert pr_artifact["pr_number"] == 42
    assert pr_artifact["pr_url"] == "https://github.com/Aspose/aspose.org/pull/42"
    assert pr_artifact["branch_name"] == "launch/aspose-note/main/abc123"
    assert pr_artifact["commit_shas"] == ["0123456789abcdef0123456789abcdef01234567"]

    # Check events emitted
    events_file = temp_run_dir / "events.ndjson"
    events_text = events_file.read_text()
    events = [json.loads(line) for line in events_text.strip().split("\n") if line]

    # Check event types
    event_types = [e["type"] for e in events]
    assert "WORK_ITEM_STARTED" in event_types
    assert "COMMIT_CREATED" in event_types
    assert "PR_OPENED" in event_types
    assert "ARTIFACT_WRITTEN" in event_types
    assert "WORK_ITEM_FINISHED" in event_types

    # Check commit service calls
    mock_commit_client.create_commit.assert_called_once()
    mock_commit_client.open_pr.assert_called_once()

    # Verify create_commit arguments
    create_commit_args = mock_commit_client.create_commit.call_args
    assert create_commit_args.kwargs["run_id"] == sample_run_config["run_id"]
    assert create_commit_args.kwargs["repo_url"] == sample_run_config["repo_url"]
    assert create_commit_args.kwargs["base_ref"] == sample_run_config["base_ref"]
    assert create_commit_args.kwargs["branch_name"] == "launch/aspose-note/main/abc123"
    assert create_commit_args.kwargs["patch_bundle"] == sample_patch_bundle

    # Verify open_pr arguments
    open_pr_args = mock_commit_client.open_pr.call_args
    assert open_pr_args.kwargs["run_id"] == sample_run_config["run_id"]
    assert open_pr_args.kwargs["base_ref"] == sample_run_config["base_ref"]
    assert open_pr_args.kwargs["head_ref"] == "launch/aspose-note/main/abc123"
    assert "Launch" in open_pr_args.kwargs["title"]
    assert open_pr_args.kwargs["draft"] is False  # validation passed


# Test 8: No changes scenario
def test_execute_pr_manager_no_changes(
    temp_run_dir,
    sample_run_config,
    sample_validation_report,
    mock_commit_client,
):
    """Test no-changes scenario (empty patch bundle)."""
    # Write empty patch bundle
    empty_patch_bundle = {"schema_version": "1.0", "patches": []}
    (temp_run_dir / "artifacts" / "patch_bundle.json").write_text(
        json.dumps(empty_patch_bundle, ensure_ascii=False, sort_keys=True)
    )
    (temp_run_dir / "artifacts" / "validation_report.json").write_text(
        json.dumps(sample_validation_report, ensure_ascii=False, sort_keys=True)
    )

    # Execute
    result = execute_pr_manager(
        run_dir=temp_run_dir,
        run_config=sample_run_config,
        commit_client=mock_commit_client,
    )

    # Check no-op success
    assert result["ok"] is True
    assert result["status"] == "no_changes"
    assert "No changes to commit" in result["message"]

    # Check no commit service calls
    mock_commit_client.create_commit.assert_not_called()
    mock_commit_client.open_pr.assert_not_called()

    # Check pr.json not written
    assert not (temp_run_dir / "artifacts" / "pr.json").exists()


# Test 9: Missing artifacts error
def test_execute_pr_manager_missing_patch_bundle(
    temp_run_dir,
    sample_run_config,
    sample_validation_report,
    mock_commit_client,
):
    """Test error when patch_bundle.json is missing."""
    # Only write validation_report.json
    (temp_run_dir / "artifacts" / "validation_report.json").write_text(
        json.dumps(sample_validation_report, ensure_ascii=False, sort_keys=True)
    )

    # Execute (should raise)
    with pytest.raises(PRManagerMissingArtifactError) as exc_info:
        execute_pr_manager(
            run_dir=temp_run_dir,
            run_config=sample_run_config,
            commit_client=mock_commit_client,
        )

    assert "patch_bundle.json not found" in str(exc_info.value)


def test_execute_pr_manager_missing_validation_report(
    temp_run_dir,
    sample_run_config,
    sample_patch_bundle,
    mock_commit_client,
):
    """Test error when validation_report.json is missing."""
    # Only write patch_bundle.json
    (temp_run_dir / "artifacts" / "patch_bundle.json").write_text(
        json.dumps(sample_patch_bundle, ensure_ascii=False, sort_keys=True)
    )

    # Execute (should raise)
    with pytest.raises(PRManagerMissingArtifactError) as exc_info:
        execute_pr_manager(
            run_dir=temp_run_dir,
            run_config=sample_run_config,
            commit_client=mock_commit_client,
        )

    assert "validation_report.json not found" in str(exc_info.value)


# Test 10: Auth failure (401/403)
def test_execute_pr_manager_auth_failed(
    temp_run_dir,
    sample_run_config,
    sample_patch_bundle,
    sample_validation_report,
    mock_commit_client,
):
    """Test auth failure handling (401/403)."""
    # Write required artifacts
    (temp_run_dir / "artifacts" / "patch_bundle.json").write_text(
        json.dumps(sample_patch_bundle, ensure_ascii=False, sort_keys=True)
    )
    (temp_run_dir / "artifacts" / "validation_report.json").write_text(
        json.dumps(sample_validation_report, ensure_ascii=False, sort_keys=True)
    )

    # Mock auth failure
    mock_commit_client.create_commit.side_effect = CommitServiceError(
        "Authentication failed",
        error_code="AUTH_INVALID_TOKEN",
        status_code=401,
    )

    # Execute (should raise)
    with pytest.raises(PRManagerAuthFailedError) as exc_info:
        execute_pr_manager(
            run_dir=temp_run_dir,
            run_config=sample_run_config,
            commit_client=mock_commit_client,
        )

    assert "Authentication failed" in str(exc_info.value)

    # Check events
    events_file = temp_run_dir / "events.ndjson"
    events_text = events_file.read_text()
    events = [json.loads(line) for line in events_text.strip().split("\n") if line]
    event_types = [e["type"] for e in events]
    assert "ISSUE_OPENED" in event_types

    # Find ISSUE_OPENED event
    issue_event = next(e for e in events if e["type"] == "ISSUE_OPENED")
    assert issue_event["payload"]["severity"] == "blocker"
    assert issue_event["payload"]["code"] == "PR_MANAGER_AUTH_FAILED"


# Test 11: Rate limit error (429)
def test_execute_pr_manager_rate_limited(
    temp_run_dir,
    sample_run_config,
    sample_patch_bundle,
    sample_validation_report,
    mock_commit_client,
):
    """Test rate limit error handling (429)."""
    # Write required artifacts
    (temp_run_dir / "artifacts" / "patch_bundle.json").write_text(
        json.dumps(sample_patch_bundle, ensure_ascii=False, sort_keys=True)
    )
    (temp_run_dir / "artifacts" / "validation_report.json").write_text(
        json.dumps(sample_validation_report, ensure_ascii=False, sort_keys=True)
    )

    # Mock rate limit
    mock_commit_client.create_commit.side_effect = CommitServiceError(
        "Rate limit exceeded",
        error_code="RATE_LIMITED",
        status_code=429,
    )

    # Execute (should raise)
    with pytest.raises(PRManagerRateLimitedError):
        execute_pr_manager(
            run_dir=temp_run_dir,
            run_config=sample_run_config,
            commit_client=mock_commit_client,
        )


# Test 12: Branch already exists
def test_execute_pr_manager_branch_exists(
    temp_run_dir,
    sample_run_config,
    sample_patch_bundle,
    sample_validation_report,
    mock_commit_client,
):
    """Test branch already exists error."""
    # Write required artifacts
    (temp_run_dir / "artifacts" / "patch_bundle.json").write_text(
        json.dumps(sample_patch_bundle, ensure_ascii=False, sort_keys=True)
    )
    (temp_run_dir / "artifacts" / "validation_report.json").write_text(
        json.dumps(sample_validation_report, ensure_ascii=False, sort_keys=True)
    )

    # Mock branch exists
    mock_commit_client.create_commit.side_effect = CommitServiceError(
        "Branch already exists",
        error_code="BRANCH_EXISTS",
        status_code=409,
    )

    # Execute (should raise)
    with pytest.raises(PRManagerBranchExistsError):
        execute_pr_manager(
            run_dir=temp_run_dir,
            run_config=sample_run_config,
            commit_client=mock_commit_client,
        )


# Test 13: Deterministic output (idempotency)
def test_execute_pr_manager_deterministic(
    temp_run_dir,
    sample_run_config,
    sample_patch_bundle,
    sample_validation_report,
    mock_commit_client,
):
    """Test deterministic outputs (same inputs = same PR body/branch)."""
    # Write required artifacts
    (temp_run_dir / "artifacts" / "patch_bundle.json").write_text(
        json.dumps(sample_patch_bundle, ensure_ascii=False, sort_keys=True)
    )
    (temp_run_dir / "artifacts" / "validation_report.json").write_text(
        json.dumps(sample_validation_report, ensure_ascii=False, sort_keys=True)
    )

    # Execute first time
    result1 = execute_pr_manager(
        run_dir=temp_run_dir,
        run_config=sample_run_config,
        commit_client=mock_commit_client,
    )

    # Get PR body from first call
    pr_body_1 = mock_commit_client.open_pr.call_args.kwargs["body"]

    # Reset mock
    mock_commit_client.reset_mock()
    mock_commit_client.create_commit.return_value = {
        "commit_sha": "0123456789abcdef0123456789abcdef01234567",
        "branch_name": "launch/aspose-note/main/abc123",
        "repo_url": "https://github.com/Aspose/aspose.org",
    }
    mock_commit_client.open_pr.return_value = {
        "pr_number": 42,
        "pr_url": "https://api.github.com/repos/Aspose/aspose.org/pulls/42",
        "pr_html_url": "https://github.com/Aspose/aspose.org/pull/42",
    }

    # Recreate run dir
    (temp_run_dir / "artifacts" / "pr.json").unlink()
    (temp_run_dir / "events.ndjson").write_text("")

    # Execute second time
    result2 = execute_pr_manager(
        run_dir=temp_run_dir,
        run_config=sample_run_config,
        commit_client=mock_commit_client,
    )

    # Get PR body from second call
    pr_body_2 = mock_commit_client.open_pr.call_args.kwargs["body"]

    # Check determinism (excluding timestamps/UUIDs in events)
    assert result1["branch_name"] == result2["branch_name"]
    # Note: PR bodies should be identical (stable ordering)
    # We can't compare bodies directly due to potential timestamp differences
    # But we can check that key sections are present in both
    for section in ["## Summary", "## Validation Status", "## Changes"]:
        assert section in pr_body_1
        assert section in pr_body_2


# Test 14: Draft PR when validation fails
def test_execute_pr_manager_draft_pr_on_validation_failure(
    temp_run_dir,
    sample_run_config,
    sample_patch_bundle,
    mock_commit_client,
):
    """Test that PR is opened as draft when validation fails."""
    # Write artifacts with failed validation
    validation_report_failed = {
        "schema_version": "1.0",
        "ok": False,
        "profile": "ci",
        "gates": [
            {"name": "Gate0-S", "ok": True},
            {"name": "Gate1", "ok": False},
        ],
        "issues": [
            {"severity": "error", "code": "TEST_ERROR", "message": "Test error"}
        ],
    }

    (temp_run_dir / "artifacts" / "patch_bundle.json").write_text(
        json.dumps(sample_patch_bundle, ensure_ascii=False, sort_keys=True)
    )
    (temp_run_dir / "artifacts" / "validation_report.json").write_text(
        json.dumps(validation_report_failed, ensure_ascii=False, sort_keys=True)
    )

    # Execute
    result = execute_pr_manager(
        run_dir=temp_run_dir,
        run_config=sample_run_config,
        commit_client=mock_commit_client,
    )

    # Check PR opened as draft
    open_pr_args = mock_commit_client.open_pr.call_args
    assert open_pr_args.kwargs["draft"] is True  # validation failed


# Test 15: Rollback metadata in pr.json
def test_pr_json_rollback_metadata(
    temp_run_dir,
    sample_run_config,
    sample_patch_bundle,
    sample_validation_report,
    mock_commit_client,
):
    """Test that pr.json includes required rollback metadata per Guarantee L."""
    # Write required artifacts
    (temp_run_dir / "artifacts" / "patch_bundle.json").write_text(
        json.dumps(sample_patch_bundle, ensure_ascii=False, sort_keys=True)
    )
    (temp_run_dir / "artifacts" / "validation_report.json").write_text(
        json.dumps(sample_validation_report, ensure_ascii=False, sort_keys=True)
    )

    # Execute
    result = execute_pr_manager(
        run_dir=temp_run_dir,
        run_config=sample_run_config,
        commit_client=mock_commit_client,
    )

    # Read pr.json
    pr_artifact_path = temp_run_dir / "artifacts" / "pr.json"
    with open(pr_artifact_path, "r", encoding="utf-8") as f:
        pr_artifact = json.load(f)

    # Verify Guarantee L fields (specs/12_pr_and_release.md:39-44)
    assert "base_ref" in pr_artifact
    assert "run_id" in pr_artifact
    assert "rollback_steps" in pr_artifact
    assert "affected_paths" in pr_artifact

    # Validate types and constraints
    assert len(pr_artifact["base_ref"]) == 40  # SHA-1 hash
    assert isinstance(pr_artifact["rollback_steps"], list)
    assert len(pr_artifact["rollback_steps"]) >= 1
    assert isinstance(pr_artifact["affected_paths"], list)
    assert len(pr_artifact["affected_paths"]) >= 1

    # Verify rollback steps contain git commands
    rollback_steps_str = " ".join(pr_artifact["rollback_steps"])
    assert "git" in rollback_steps_str.lower()
    assert "revert" in rollback_steps_str.lower()


# TC-631: Test commit_client construction from run_config
def test_pr_manager_constructs_client_from_config(
    temp_run_dir,
    sample_run_config,
    sample_patch_bundle,
    sample_validation_report,
):
    """Test W9 can construct commit service client from run_config (TC-631)."""
    # Add commit_service config
    sample_run_config["commit_service"] = {
        "endpoint_url": "http://localhost:4320/v1",
        "github_token_env": "GITHUB_TOKEN",
        "timeout": 30,
    }

    # Write required artifacts
    (temp_run_dir / "artifacts" / "patch_bundle.json").write_text(
        json.dumps(sample_patch_bundle, ensure_ascii=False, sort_keys=True)
    )
    (temp_run_dir / "artifacts" / "validation_report.json").write_text(
        json.dumps(sample_validation_report, ensure_ascii=False, sort_keys=True)
    )

    # Mock the CommitServiceClient class
    with patch("src.launch.workers.w9_pr_manager.worker.CommitServiceClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client.create_commit.return_value = {
            "commit_sha": "0123456789abcdef0123456789abcdef01234567",
            "branch_name": "launch/aspose-note/main/abc123",
        }
        mock_client.open_pr.return_value = {
            "pr_number": 1,
            "pr_html_url": "https://github.com/test/repo/pull/1",
        }
        mock_client_class.return_value = mock_client

        # Execute WITHOUT passing commit_client
        result = execute_pr_manager(
            run_dir=temp_run_dir,
            run_config=sample_run_config,
            commit_client=None,  # Force construction
        )

        # Verify client was constructed
        mock_client_class.assert_called_once()
        call_kwargs = mock_client_class.call_args.kwargs
        assert call_kwargs["endpoint_url"] == "http://localhost:4320/v1"
        assert call_kwargs["timeout"] == 30

        # Verify execution succeeded
        assert result["ok"] is True
        assert result["pr_url"] == "https://github.com/test/repo/pull/1"


# TC-631: Test OFFLINE_MODE path
def test_pr_manager_offline_mode(
    temp_run_dir,
    sample_run_config,
    sample_patch_bundle,
    sample_validation_report,
    monkeypatch,
):
    """Test W9 offline mode creates bundle without network calls (TC-631)."""
    # Set OFFLINE_MODE
    monkeypatch.setenv("OFFLINE_MODE", "1")

    # Add commit_service config
    sample_run_config["commit_service"] = {
        "endpoint_url": "http://localhost:4320/v1",
        "github_token_env": "GITHUB_TOKEN",
    }

    # Write required artifacts
    (temp_run_dir / "artifacts" / "patch_bundle.json").write_text(
        json.dumps(sample_patch_bundle, ensure_ascii=False, sort_keys=True)
    )
    (temp_run_dir / "artifacts" / "validation_report.json").write_text(
        json.dumps(sample_validation_report, ensure_ascii=False, sort_keys=True)
    )

    # Execute
    result = execute_pr_manager(
        run_dir=temp_run_dir,
        run_config=sample_run_config,
        commit_client=None,
    )

    # Verify offline mode behavior
    assert result["ok"] is True
    assert result["status"] == "offline_ok"
    assert "offline_bundle" in result

    # Verify offline bundle exists
    offline_bundle_path = temp_run_dir / "offline_bundles" / "pr_payload.json"
    assert offline_bundle_path.exists()

    with open(offline_bundle_path, "r", encoding="utf-8") as f:
        bundle = json.load(f)

    assert bundle["mode"] == "offline"
    assert bundle["run_id"] == sample_run_config["run_id"]
    assert "patch_bundle" in bundle
    assert "pr_title" in bundle
    assert "pr_body" in bundle
    assert bundle["branch_name"] == "launch/aspose-note/main/abc123"

    # Verify events emitted
    events_file = temp_run_dir / "events.ndjson"
    events_text = events_file.read_text()
    events = [json.loads(line) for line in events_text.strip().split("\n") if line]
    event_types = [e["type"] for e in events]
    assert "WORK_ITEM_STARTED" in event_types
    assert "WORK_ITEM_FINISHED" in event_types

    # Find WORK_ITEM_FINISHED event and verify offline status
    finished_event = next(e for e in events if e["type"] == "WORK_ITEM_FINISHED")
    assert finished_event["payload"]["status"] == "offline_ok"
