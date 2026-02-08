"""TC-1035: W9 PRManager edge case tests.

This module tests edge cases in the W9 PRManager worker that are
NOT covered by the existing test_tc_480_pr_manager.py:

1. Offline mode produces local validation report (via validation_profile=local)
2. Empty patch bundle (nothing to commit)
3. PR creation with missing mandatory fields in run_config
4. Approval gate with different authorization levels
5. Validation summary with mixed pass/fail gates
6. Branch name generation edge cases
7. PR body generation edge cases (empty issues, long affected paths)
8. Commit service generic error handling
9. Missing commit_service config

Spec references:
- specs/12_pr_and_release.md (PR creation workflow)
- specs/17_github_commit_service.md (Commit service integration)
- specs/21_worker_contracts.md:322-344 (W9 PRManager contract)
- specs/30_ai_agent_governance.md (AG-001 approval gate)
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.launch.clients.commit_service import CommitServiceClient, CommitServiceError
from src.launch.workers.w9_pr_manager import (
    PRManagerAuthFailedError,
    PRManagerBranchExistsError,
    PRManagerError,
    PRManagerMissingArtifactError,
    PRManagerNoChangesError,
    PRManagerRateLimitedError,
    execute_pr_manager,
    extract_affected_paths,
    generate_branch_name,
    generate_pr_body,
    generate_pr_title,
    generate_rollback_steps,
)


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
    """Standard patch bundle for testing."""
    return {
        "schema_version": "1.0",
        "patches": [
            {
                "patch_id": "p1",
                "type": "create_file",
                "path": "content/docs.aspose.org/product/en/python/page.md",
                "new_content": "# Page\n\nContent.",
                "content_hash": "abc123",
            },
        ],
    }


@pytest.fixture
def sample_validation_report():
    """Standard validation report for testing."""
    return {
        "schema_version": "1.0",
        "ok": True,
        "profile": "local",
        "gates": [
            {"name": "Gate0-S", "ok": True},
            {"name": "Gate1", "ok": True},
        ],
        "issues": [],
    }


@pytest.fixture
def sample_run_config():
    """Standard run configuration."""
    return {
        "run_id": "RUN-20260207-120000Z-test01",
        "product_slug": "test-product",
        "language": "python",
        "repo_url": "https://github.com/Test/repo",
        "base_ref": "main",
        "github_ref": "refs/heads/main",
        "allowed_paths": ["content/docs.aspose.org/test-product/"],
        "validation_profile": "ci",
    }


@pytest.fixture
def mock_commit_client():
    """Mock commit service client with standard responses."""
    client = Mock(spec=CommitServiceClient)
    client.create_commit.return_value = {
        "commit_sha": "abcdef1234567890abcdef1234567890abcdef12",
        "branch_name": "launch/test-product/main/test01",
        "repo_url": "https://github.com/Test/repo",
    }
    client.open_pr.return_value = {
        "pr_number": 99,
        "pr_url": "https://api.github.com/repos/Test/repo/pulls/99",
        "pr_html_url": "https://github.com/Test/repo/pull/99",
    }
    return client


# ---------------------------------------------------------------------------
# 1. Offline mode via validation_profile=local
# ---------------------------------------------------------------------------
def test_offline_mode_via_local_profile(
    temp_run_dir,
    sample_patch_bundle,
    sample_validation_report,
):
    """When validation_profile='local', offline mode is auto-enabled.
    No network calls should be made."""
    run_config = {
        "run_id": "RUN-20260207-120000Z-local1",
        "product_slug": "test-product",
        "language": "python",
        "repo_url": "https://github.com/Test/repo",
        "base_ref": "main",
        "github_ref": "refs/heads/main",
        "allowed_paths": [],
        "validation_profile": "local",  # This triggers offline mode
        "commit_service": {
            "endpoint_url": "http://localhost:4320/v1",
        },
    }

    (temp_run_dir / "artifacts" / "patch_bundle.json").write_text(
        json.dumps(sample_patch_bundle)
    )
    (temp_run_dir / "artifacts" / "validation_report.json").write_text(
        json.dumps(sample_validation_report)
    )

    result = execute_pr_manager(
        run_dir=temp_run_dir,
        run_config=run_config,
        commit_client=None,  # Should not be needed
    )

    assert result["ok"] is True
    assert result["status"] == "offline_ok"
    assert "offline_bundle" in result

    # Verify offline bundle content
    bundle_path = temp_run_dir / "offline_bundles" / "pr_payload.json"
    assert bundle_path.exists()

    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    assert bundle["mode"] == "offline"
    assert bundle["run_id"] == run_config["run_id"]
    assert "pr_body" in bundle


# ---------------------------------------------------------------------------
# 2. Empty patch bundle (edge case already tested but let's test events)
# ---------------------------------------------------------------------------
def test_empty_patch_bundle_emits_events(
    temp_run_dir,
    sample_validation_report,
    mock_commit_client,
):
    """Empty patch bundle should emit WORK_ITEM_STARTED and WORK_ITEM_FINISHED."""
    run_config = {
        "run_id": "RUN-20260207-120000Z-empty1",
        "product_slug": "test",
        "validation_profile": "ci",
    }

    empty_bundle = {"schema_version": "1.0", "patches": []}
    (temp_run_dir / "artifacts" / "patch_bundle.json").write_text(
        json.dumps(empty_bundle)
    )
    (temp_run_dir / "artifacts" / "validation_report.json").write_text(
        json.dumps(sample_validation_report)
    )

    result = execute_pr_manager(
        run_dir=temp_run_dir,
        run_config=run_config,
        commit_client=mock_commit_client,
    )

    assert result["ok"] is True
    assert result["status"] == "no_changes"

    # Verify events
    events_text = (temp_run_dir / "events.ndjson").read_text()
    events = [json.loads(line) for line in events_text.strip().split("\n") if line]
    event_types = [e["type"] for e in events]
    assert "WORK_ITEM_STARTED" in event_types
    assert "WORK_ITEM_FINISHED" in event_types

    # WORK_ITEM_FINISHED should have no_changes status
    finished = next(e for e in events if e["type"] == "WORK_ITEM_FINISHED")
    assert finished["payload"]["status"] == "no_changes"


# ---------------------------------------------------------------------------
# 3. Missing commit_service config
# ---------------------------------------------------------------------------
def test_missing_commit_service_config(
    temp_run_dir,
    sample_patch_bundle,
    sample_validation_report,
):
    """When commit_service config is missing from run_config,
    PRManagerError should be raised (non-offline mode)."""
    run_config = {
        "run_id": "RUN-20260207-120000Z-noconfig",
        "product_slug": "test",
        "validation_profile": "ci",
        # No commit_service key
    }

    (temp_run_dir / "artifacts" / "patch_bundle.json").write_text(
        json.dumps(sample_patch_bundle)
    )
    (temp_run_dir / "artifacts" / "validation_report.json").write_text(
        json.dumps(sample_validation_report)
    )

    with pytest.raises(PRManagerError, match="commit_service configuration missing"):
        execute_pr_manager(
            run_dir=temp_run_dir,
            run_config=run_config,
            commit_client=None,
        )


def test_missing_endpoint_url(
    temp_run_dir,
    sample_patch_bundle,
    sample_validation_report,
):
    """When commit_service.endpoint_url is missing, PRManagerError is raised."""
    run_config = {
        "run_id": "RUN-20260207-120000Z-nourl",
        "product_slug": "test",
        "validation_profile": "ci",
        "commit_service": {
            # No endpoint_url
            "github_token_env": "GITHUB_TOKEN",
        },
    }

    (temp_run_dir / "artifacts" / "patch_bundle.json").write_text(
        json.dumps(sample_patch_bundle)
    )
    (temp_run_dir / "artifacts" / "validation_report.json").write_text(
        json.dumps(sample_validation_report)
    )

    with pytest.raises(PRManagerError, match="endpoint_url missing"):
        execute_pr_manager(
            run_dir=temp_run_dir,
            run_config=run_config,
            commit_client=None,
        )


# ---------------------------------------------------------------------------
# 4. AG-001 approval gate missing (non-offline mode)
# ---------------------------------------------------------------------------
def test_ag001_approval_missing(
    temp_run_dir,
    sample_patch_bundle,
    sample_validation_report,
    mock_commit_client,
):
    """When AG-001 approval marker is absent, PRManagerError should be raised."""
    run_config = {
        "run_id": "RUN-20260207-120000Z-noapproval",
        "product_slug": "test",
        "validation_profile": "ci",
    }

    (temp_run_dir / "artifacts" / "patch_bundle.json").write_text(
        json.dumps(sample_patch_bundle)
    )
    (temp_run_dir / "artifacts" / "validation_report.json").write_text(
        json.dumps(sample_validation_report)
    )

    # Remove the approval marker
    approval_path = temp_run_dir.parent / ".git" / "AI_BRANCH_APPROVED"
    if approval_path.exists():
        approval_path.unlink()

    with pytest.raises(PRManagerError, match="AG-001 approval gate violation"):
        execute_pr_manager(
            run_dir=temp_run_dir,
            run_config=run_config,
            commit_client=mock_commit_client,
        )


# ---------------------------------------------------------------------------
# 5. Validation summary with mixed pass/fail gates
# ---------------------------------------------------------------------------
def test_pr_body_mixed_gates():
    """PR body should correctly reflect mixed pass/fail gate results."""
    validation_report = {
        "ok": False,
        "profile": "ci",
        "gates": [
            {"name": "Gate0-S", "ok": True},
            {"name": "Gate1", "ok": True},
            {"name": "Gate2", "ok": False},
            {"name": "Gate3", "ok": True},
            {"name": "Gate4", "ok": False},
            {"name": "Gate5", "ok": True},
        ],
        "issues": [
            {"severity": "blocker", "code": "CODE_A", "message": "Blocker A"},
            {"severity": "error", "code": "CODE_B", "message": "Error B"},
            {"severity": "warn", "code": "CODE_C", "message": "Warning C"},
        ],
    }
    patch_bundle = {"patches": [{"path": "a.md", "type": "create_file"}]}
    run_config = {}

    body = generate_pr_body(
        run_id="test-run",
        product_slug="test",
        validation_report=validation_report,
        patch_bundle=patch_bundle,
        run_config=run_config,
    )

    # Check gate counts
    assert "4/6" in body  # 4 passed out of 6
    assert "2 gate(s) failed" in body
    assert "1 blocker issue(s) found" in body

    # Check issues section
    assert "### Issues" in body
    assert "CODE_A" in body
    assert "CODE_B" in body
    assert "CODE_C" in body


def test_pr_body_all_gates_pass():
    """PR body should show success message when all gates pass."""
    validation_report = {
        "ok": True,
        "profile": "ci",
        "gates": [
            {"name": "Gate1", "ok": True},
            {"name": "Gate2", "ok": True},
        ],
        "issues": [],
    }
    patch_bundle = {"patches": []}

    body = generate_pr_body("run1", "product", validation_report, patch_bundle, {})

    assert "All validation gates passed" in body
    assert "### Issues" not in body


def test_pr_body_no_gates():
    """PR body should handle empty gates list gracefully."""
    validation_report = {
        "ok": True,
        "profile": "ci",
        "gates": [],
        "issues": [],
    }
    patch_bundle = {"patches": []}

    body = generate_pr_body("run1", "product", validation_report, patch_bundle, {})

    assert "0/0" in body  # 0 passed out of 0


# ---------------------------------------------------------------------------
# 6. Branch name generation edge cases
# ---------------------------------------------------------------------------
def test_branch_name_simple_ref():
    """Branch name with simple ref (no slashes)."""
    name = generate_branch_name("product", "main", "RUN-12345-abc")
    assert name == "launch/product/main/abc"


def test_branch_name_deep_ref():
    """Branch name with deeply nested ref."""
    name = generate_branch_name("product", "refs/heads/feature/deep", "RUN-x-abc123")
    assert name == "launch/product/deep/abc123"


def test_branch_name_no_dash_in_run_id():
    """Branch name with run_id that has no dashes."""
    name = generate_branch_name("product", "main", "RUNID123456")
    # No dash = use first 6 chars
    assert name == "launch/product/main/RUNID1"


def test_branch_name_deterministic():
    """Same inputs must produce same branch name (determinism)."""
    b1 = generate_branch_name("foo", "refs/heads/main", "RUN-2026-abc")
    b2 = generate_branch_name("foo", "refs/heads/main", "RUN-2026-abc")
    assert b1 == b2


# ---------------------------------------------------------------------------
# 7. PR title generation edge cases
# ---------------------------------------------------------------------------
def test_pr_title_with_complex_slug():
    """PR title with complex product slug should format correctly."""
    title = generate_pr_title("aspose-3d-for-python", "python", True)
    assert "Launch" in title
    assert "Python" in title
    assert "Aspose 3D For Python" in title


def test_pr_title_draft_on_failure():
    """PR title should say 'Draft Launch' when validation failed."""
    title = generate_pr_title("product", "java", False)
    assert "Draft Launch" in title
    assert "Java" in title


# ---------------------------------------------------------------------------
# 8. Extract affected paths edge cases
# ---------------------------------------------------------------------------
def test_extract_affected_paths_empty():
    """extract_affected_paths with no patches returns empty list."""
    assert extract_affected_paths({"patches": []}) == []


def test_extract_affected_paths_deduplication():
    """extract_affected_paths should deduplicate paths."""
    bundle = {
        "patches": [
            {"path": "content/a.md"},
            {"path": "content/b.md"},
            {"path": "content/a.md"},  # duplicate
        ]
    }
    paths = extract_affected_paths(bundle)
    assert paths == sorted(["content/a.md", "content/b.md"])


def test_extract_affected_paths_missing_path_key():
    """extract_affected_paths should skip patches without 'path' key."""
    bundle = {
        "patches": [
            {"path": "content/a.md"},
            {"type": "create_file"},  # no path key
            {"path": ""},  # empty path
        ]
    }
    paths = extract_affected_paths(bundle)
    assert paths == ["content/a.md"]


# ---------------------------------------------------------------------------
# 9. Rollback steps generation
# ---------------------------------------------------------------------------
def test_rollback_steps_content():
    """Rollback steps should contain git fetch, revert, and push."""
    steps = generate_rollback_steps("launch/product/main/abc", "sha123")

    assert any("git fetch" in s for s in steps)
    assert any("git revert" in s and "sha123" in s for s in steps)
    assert any("git push" in s for s in steps)
    assert len(steps) >= 3


# ---------------------------------------------------------------------------
# 10. Commit service generic error (500 server error)
# ---------------------------------------------------------------------------
def test_commit_service_generic_error(
    temp_run_dir,
    sample_patch_bundle,
    sample_validation_report,
    sample_run_config,
    mock_commit_client,
):
    """Generic commit service error (non-auth, non-rate-limit) should
    raise PRManagerError."""
    (temp_run_dir / "artifacts" / "patch_bundle.json").write_text(
        json.dumps(sample_patch_bundle)
    )
    (temp_run_dir / "artifacts" / "validation_report.json").write_text(
        json.dumps(sample_validation_report)
    )

    mock_commit_client.create_commit.side_effect = CommitServiceError(
        "Internal server error",
        error_code="INTERNAL_ERROR",
        status_code=500,
    )

    with pytest.raises(PRManagerError, match="Commit service error"):
        execute_pr_manager(
            run_dir=temp_run_dir,
            run_config=sample_run_config,
            commit_client=mock_commit_client,
        )


# ---------------------------------------------------------------------------
# 11. PR opened as draft when validation fails
# ---------------------------------------------------------------------------
def test_pr_draft_mode_on_failure(
    temp_run_dir,
    sample_patch_bundle,
    sample_run_config,
    mock_commit_client,
):
    """PR should open as draft when validation report shows ok=False."""
    failed_report = {
        "schema_version": "1.0",
        "ok": False,
        "profile": "ci",
        "gates": [
            {"name": "Gate1", "ok": True},
            {"name": "Gate2", "ok": False},
        ],
        "issues": [
            {"severity": "error", "code": "ERR1", "message": "Test error"},
        ],
    }

    (temp_run_dir / "artifacts" / "patch_bundle.json").write_text(
        json.dumps(sample_patch_bundle)
    )
    (temp_run_dir / "artifacts" / "validation_report.json").write_text(
        json.dumps(failed_report)
    )

    result = execute_pr_manager(
        run_dir=temp_run_dir,
        run_config=sample_run_config,
        commit_client=mock_commit_client,
    )

    # PR should be opened as draft
    open_pr_args = mock_commit_client.open_pr.call_args
    assert open_pr_args.kwargs["draft"] is True

    # Result should still be ok (PR was opened)
    assert result["ok"] is True


# ---------------------------------------------------------------------------
# 12. Validation summary in pr.json
# ---------------------------------------------------------------------------
def test_pr_json_validation_summary(
    temp_run_dir,
    sample_patch_bundle,
    sample_run_config,
    mock_commit_client,
):
    """pr.json should contain accurate validation_summary."""
    validation_report = {
        "schema_version": "1.0",
        "ok": False,
        "profile": "ci",
        "gates": [
            {"name": "Gate1", "ok": True},
            {"name": "Gate2", "ok": True},
            {"name": "Gate3", "ok": False},
        ],
        "issues": [],
    }

    (temp_run_dir / "artifacts" / "patch_bundle.json").write_text(
        json.dumps(sample_patch_bundle)
    )
    (temp_run_dir / "artifacts" / "validation_report.json").write_text(
        json.dumps(validation_report)
    )

    result = execute_pr_manager(
        run_dir=temp_run_dir,
        run_config=sample_run_config,
        commit_client=mock_commit_client,
    )

    # Read pr.json
    pr_json = json.loads(
        (temp_run_dir / "artifacts" / "pr.json").read_text(encoding="utf-8")
    )

    summary = pr_json["validation_summary"]
    assert summary["ok"] is False
    assert summary["profile"] == "ci"
    assert summary["gates_passed"] == 2
    assert summary["gates_failed"] == 1


# ---------------------------------------------------------------------------
# 13. PR body with many affected files (truncation test)
# ---------------------------------------------------------------------------
def test_pr_body_many_files_truncated():
    """PR body should truncate affected files list when >20."""
    patches = [
        {"path": f"content/docs/page_{i:03d}.md", "type": "create_file"}
        for i in range(30)
    ]
    patch_bundle = {"patches": patches}
    validation_report = {"ok": True, "profile": "ci", "gates": [], "issues": []}

    body = generate_pr_body("run1", "product", validation_report, patch_bundle, {})

    # Should show first 20 + "and X more files"
    assert "and 10 more files" in body


def test_pr_body_exactly_20_files():
    """PR body with exactly 20 files should show all without truncation."""
    patches = [
        {"path": f"content/docs/page_{i:03d}.md", "type": "create_file"}
        for i in range(20)
    ]
    patch_bundle = {"patches": patches}
    validation_report = {"ok": True, "profile": "ci", "gates": [], "issues": []}

    body = generate_pr_body("run1", "product", validation_report, patch_bundle, {})

    assert "more files" not in body


# ---------------------------------------------------------------------------
# 14. Both missing artifacts
# ---------------------------------------------------------------------------
def test_both_artifacts_missing(
    temp_run_dir,
    sample_run_config,
    mock_commit_client,
):
    """Both patch_bundle.json and validation_report.json missing should
    raise for the first one checked (patch_bundle)."""
    with pytest.raises(PRManagerMissingArtifactError, match="patch_bundle.json"):
        execute_pr_manager(
            run_dir=temp_run_dir,
            run_config=sample_run_config,
            commit_client=mock_commit_client,
        )


# ---------------------------------------------------------------------------
# 15. AG-001 approval marker with different content
# ---------------------------------------------------------------------------
def test_ag001_approval_interactive_dialog(
    temp_run_dir,
    sample_patch_bundle,
    sample_validation_report,
    sample_run_config,
    mock_commit_client,
):
    """AG-001 with interactive-dialog approval source should be passed to
    governance metadata."""
    # Update approval marker
    approval_path = temp_run_dir.parent / ".git" / "AI_BRANCH_APPROVED"
    approval_path.write_text("interactive-dialog")

    (temp_run_dir / "artifacts" / "patch_bundle.json").write_text(
        json.dumps(sample_patch_bundle)
    )
    (temp_run_dir / "artifacts" / "validation_report.json").write_text(
        json.dumps(sample_validation_report)
    )

    result = execute_pr_manager(
        run_dir=temp_run_dir,
        run_config=sample_run_config,
        commit_client=mock_commit_client,
    )

    assert result["ok"] is True

    # Verify governance metadata was passed to create_commit
    create_args = mock_commit_client.create_commit.call_args
    gov_metadata = create_args.kwargs.get("ai_governance_metadata")
    assert gov_metadata is not None
    assert gov_metadata["ag001_approval"]["approved"] is True
    assert gov_metadata["ag001_approval"]["approval_source"] == "interactive-dialog"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
