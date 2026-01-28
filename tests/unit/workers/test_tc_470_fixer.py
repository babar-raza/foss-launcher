"""Tests for TC-470: W8 Fixer worker implementation.

This module tests the W8 Fixer worker per specs/21_worker_contracts.md:290-320.

Test coverage:
- Fix generation (mock LLM responses)
- Fix application to artifacts
- Issue resolution tracking
- Max fix attempts enforcement
- Deterministic ordering
- Event emission
- Artifact validation
- Error handling (unfixable issues, LLM failures)

Spec references:
- specs/28_coordination_and_handoffs.md:71-84 (Fix loop policy)
- specs/21_worker_contracts.md:290-320 (W8 contract)
- specs/08_patch_engine.md (Patch strategies)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import pytest

from src.launch.workers.w8_fixer import (
    FixerError,
    FixerIssueNotFoundError,
    FixerUnfixableError,
    FixerNoOpError,
    FixerArtifactMissingError,
    execute_fixer,
)
from src.launch.workers.w8_fixer.worker import (
    select_issue_to_fix,
    fix_unresolved_token,
    fix_frontmatter_missing,
    fix_frontmatter_invalid_yaml,
    fix_consistency_mismatch,
    check_fix_produced_diff,
    compute_file_hash,
    parse_frontmatter,
    write_frontmatter,
)


# Fixtures
@pytest.fixture
def run_dir(tmp_path: Path) -> Path:
    """Create temporary run directory."""
    run_dir = tmp_path / "runs" / "test_run_001"
    run_dir.mkdir(parents=True)

    # Create required directories
    (run_dir / "artifacts").mkdir()
    (run_dir / "reports").mkdir()
    (run_dir / "work" / "site").mkdir(parents=True)

    # Create events.ndjson
    (run_dir / "events.ndjson").touch()

    return run_dir


@pytest.fixture
def validation_report_with_issues() -> Dict[str, Any]:
    """Validation report with multiple issues."""
    return {
        "schema_version": "1.0",
        "ok": False,
        "profile": "local",
        "gates": [
            {"name": "gate_1_schema_validation", "ok": False},
            {"name": "gate_11_template_token_lint", "ok": False},
        ],
        "issues": [
            {
                "issue_id": "template_token_test_1",
                "gate": "gate_11_template_token_lint",
                "severity": "blocker",
                "message": "Unresolved template token found: __PRODUCT_NAME__",
                "error_code": "GATE_TEMPLATE_TOKEN_UNRESOLVED",
                "location": {"path": "test_file.md", "line": 5},
                "status": "OPEN",
            },
            {
                "issue_id": "frontmatter_missing_test_1",
                "gate": "gate_1_schema_validation",
                "severity": "error",
                "message": "File missing frontmatter: test_file2.md",
                "error_code": "GATE_FRONTMATTER_MISSING",
                "location": {"path": "test_file2.md", "line": 1},
                "status": "OPEN",
            },
            {
                "issue_id": "consistency_test_1",
                "gate": "gate_10_consistency",
                "severity": "warn",
                "message": "repo_url mismatch in test_file3.md",
                "error_code": "GATE_CONSISTENCY_REPO_URL_MISMATCH",
                "location": {"path": "test_file3.md"},
                "status": "OPEN",
            },
        ],
    }


@pytest.fixture
def mock_llm_client():
    """Mock LLM client."""

    class MockLLMClient:
        def chat_completion(self, messages, **kwargs):
            return {
                "content": "Fixed content",
                "prompt_hash": "mock_hash",
                "model": "mock_model",
                "usage": {"total_tokens": 100},
                "latency_ms": 50,
                "evidence_path": "/mock/path",
            }

    return MockLLMClient()


# Tests for select_issue_to_fix
def test_select_issue_to_fix_blocker_first(validation_report_with_issues):
    """Test that blocker issues are selected before errors."""
    issue = select_issue_to_fix(validation_report_with_issues)

    assert issue is not None
    assert issue["issue_id"] == "template_token_test_1"
    assert issue["severity"] == "blocker"


def test_select_issue_to_fix_deterministic_ordering():
    """Test deterministic issue ordering."""
    report = {
        "ok": False,
        "issues": [
            {
                "issue_id": "error_2",
                "gate": "gate_b",
                "severity": "error",
                "location": {"path": "b.md", "line": 2},
                "status": "OPEN",
            },
            {
                "issue_id": "blocker_1",
                "gate": "gate_a",
                "severity": "blocker",
                "location": {"path": "a.md", "line": 1},
                "status": "OPEN",
            },
            {
                "issue_id": "error_1",
                "gate": "gate_a",
                "severity": "error",
                "location": {"path": "a.md", "line": 1},
                "status": "OPEN",
            },
        ],
    }

    issue = select_issue_to_fix(report)

    # Blocker should be selected first
    assert issue["issue_id"] == "blocker_1"
    assert issue["severity"] == "blocker"


def test_select_issue_to_fix_no_fixable_issues():
    """Test when no fixable issues exist."""
    report = {
        "ok": True,
        "issues": [
            {
                "issue_id": "info_1",
                "gate": "gate_a",
                "severity": "info",
                "status": "OPEN",
            },
            {
                "issue_id": "resolved_1",
                "gate": "gate_b",
                "severity": "blocker",
                "status": "RESOLVED",
            },
        ],
    }

    issue = select_issue_to_fix(report)

    assert issue is None


def test_select_issue_to_fix_specific_issue(validation_report_with_issues):
    """Test selecting a specific issue."""
    specific_issue = {"issue_id": "frontmatter_missing_test_1"}

    issue = select_issue_to_fix(validation_report_with_issues, specific_issue)

    assert issue is not None
    assert issue["issue_id"] == "frontmatter_missing_test_1"


def test_select_issue_to_fix_issue_not_found(validation_report_with_issues):
    """Test error when specific issue not found."""
    specific_issue = {"issue_id": "nonexistent_issue"}

    with pytest.raises(FixerIssueNotFoundError) as exc_info:
        select_issue_to_fix(validation_report_with_issues, specific_issue)

    assert "nonexistent_issue" in str(exc_info.value)


# Tests for fix_unresolved_token
def test_fix_unresolved_token_success(run_dir, mock_llm_client):
    """Test fixing unresolved template token."""
    # Create test file with token
    test_file = run_dir / "work" / "site" / "test.md"
    test_file.write_text(
        "Line 1\nLine 2\nLine 3\nLine 4\nThis is __PRODUCT_NAME__ line\nLine 6\n",
        encoding="utf-8",
    )

    issue = {
        "issue_id": "token_test",
        "message": "Unresolved template token found: __PRODUCT_NAME__",
        "location": {"path": str(test_file), "line": 5},
    }

    result = fix_unresolved_token(issue, run_dir, mock_llm_client)

    assert result["fixed"] is True
    assert str(test_file) in result["files_changed"]
    assert "Removed unresolved token" in result["diff_summary"]

    # Verify token was removed
    content = test_file.read_text(encoding="utf-8")
    assert "__PRODUCT_NAME__" not in content


def test_fix_unresolved_token_no_file_path(run_dir, mock_llm_client):
    """Test error when no file path in issue."""
    issue = {"issue_id": "token_test", "message": "Token issue", "location": {}}

    result = fix_unresolved_token(issue, run_dir, mock_llm_client)

    assert result["fixed"] is False
    assert "No file path" in result["error"]


def test_fix_unresolved_token_file_not_found(run_dir, mock_llm_client):
    """Test error when file not found."""
    issue = {
        "issue_id": "token_test",
        "message": "Token issue",
        "location": {"path": "/nonexistent/file.md", "line": 1},
    }

    result = fix_unresolved_token(issue, run_dir, mock_llm_client)

    assert result["fixed"] is False
    assert "File not found" in result["error"]


# Tests for fix_frontmatter_missing
def test_fix_frontmatter_missing_success(run_dir, mock_llm_client):
    """Test adding frontmatter to file."""
    test_file = run_dir / "work" / "site" / "test_page.md"
    test_file.write_text("# Test Page\n\nContent here.", encoding="utf-8")

    issue = {
        "issue_id": "frontmatter_test",
        "location": {"path": str(test_file), "line": 1},
    }

    result = fix_frontmatter_missing(issue, run_dir, mock_llm_client)

    assert result["fixed"] is True
    assert str(test_file) in result["files_changed"]

    # Verify frontmatter was added
    content = test_file.read_text(encoding="utf-8")
    assert content.startswith("---\n")
    assert "title:" in content
    assert "Test Page" in content


# Tests for fix_frontmatter_invalid_yaml
def test_fix_frontmatter_invalid_yaml_success(run_dir, mock_llm_client):
    """Test fixing invalid YAML frontmatter."""
    test_file = run_dir / "work" / "site" / "test.md"
    test_file.write_text(
        "---\ntitle: Missing quote\n  bad: indent\n---\n\nBody content.",
        encoding="utf-8",
    )

    issue = {
        "issue_id": "yaml_test",
        "location": {"path": str(test_file), "line": 1},
    }

    result = fix_frontmatter_invalid_yaml(issue, run_dir, mock_llm_client)

    assert result["fixed"] is True
    assert str(test_file) in result["files_changed"]

    # Verify frontmatter is valid
    content = test_file.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(content)
    assert frontmatter is not None
    assert "title" in frontmatter


# Tests for fix_consistency_mismatch
def test_fix_consistency_mismatch_repo_url(run_dir, mock_llm_client):
    """Test fixing repo_url consistency."""
    # Create product_facts.json
    product_facts = {
        "product_name": "Test Product",
        "repo_url": "https://github.com/correct/repo",
    }
    product_facts_path = run_dir / "artifacts" / "product_facts.json"
    product_facts_path.write_text(json.dumps(product_facts), encoding="utf-8")

    # Create test file with wrong repo_url
    test_file = run_dir / "work" / "site" / "test.md"
    test_file.write_text(
        "---\ntitle: Test\nrepo_url: https://github.com/wrong/repo\n---\n\nContent.",
        encoding="utf-8",
    )

    issue = {
        "issue_id": "consistency_test",
        "error_code": "GATE_CONSISTENCY_REPO_URL_MISMATCH",
        "location": {"path": str(test_file)},
    }

    result = fix_consistency_mismatch(issue, run_dir, mock_llm_client)

    assert result["fixed"] is True
    assert str(test_file) in result["files_changed"]

    # Verify repo_url was corrected
    content = test_file.read_text(encoding="utf-8")
    frontmatter, _ = parse_frontmatter(content)
    assert frontmatter["repo_url"] == "https://github.com/correct/repo"


def test_fix_consistency_mismatch_no_product_facts(run_dir, mock_llm_client):
    """Test error when product_facts.json missing."""
    test_file = run_dir / "work" / "site" / "test.md"
    test_file.write_text("---\ntitle: Test\n---\n\nContent.", encoding="utf-8")

    issue = {
        "issue_id": "consistency_test",
        "error_code": "GATE_CONSISTENCY_REPO_URL_MISMATCH",
        "location": {"path": str(test_file)},
    }

    result = fix_consistency_mismatch(issue, run_dir, mock_llm_client)

    assert result["fixed"] is False
    assert "product_facts.json not found" in result["error"]


# Tests for execute_fixer
def test_execute_fixer_success(run_dir, validation_report_with_issues, mock_llm_client):
    """Test full fixer execution."""
    # Create test file with token
    test_file = run_dir / "work" / "site" / "test_file.md"
    test_file.write_text(
        "Line 1\nLine 2\nLine 3\nLine 4\nThis is __PRODUCT_NAME__ line\nLine 6\n",
        encoding="utf-8",
    )

    # Update issue location to use absolute path
    validation_report_with_issues["issues"][0]["location"]["path"] = str(test_file)

    # Write validation report after updating path
    validation_report_path = run_dir / "artifacts" / "validation_report.json"
    validation_report_path.write_text(
        json.dumps(validation_report_with_issues), encoding="utf-8"
    )

    run_config = {"max_fix_attempts": 3}

    result = execute_fixer(run_dir, run_config, mock_llm_client)

    assert result["status"] == "resolved"
    assert result["issue_id"] == "template_token_test_1"
    assert len(result["files_changed"]) > 0

    # Verify events were emitted
    events_file = run_dir / "events.ndjson"
    events_content = events_file.read_text()
    assert "FIXER_STARTED" in events_content
    assert "FIXER_COMPLETED" in events_content
    assert "ISSUE_RESOLVED" in events_content

    # Verify fix report was created
    fix_report = run_dir / "reports" / "fix_template_token_test_1.md"
    assert fix_report.exists()


def test_execute_fixer_no_issues(run_dir, mock_llm_client):
    """Test fixer when no fixable issues exist."""
    validation_report = {
        "schema_version": "1.0",
        "ok": True,
        "profile": "local",
        "gates": [],
        "issues": [],
    }

    validation_report_path = run_dir / "artifacts" / "validation_report.json"
    validation_report_path.write_text(json.dumps(validation_report), encoding="utf-8")

    run_config = {}

    result = execute_fixer(run_dir, run_config, mock_llm_client)

    assert result["status"] == "resolved"
    assert result["issue_id"] is None
    assert result["files_changed"] == []


def test_execute_fixer_validation_report_missing(run_dir, mock_llm_client):
    """Test error when validation report missing."""
    run_config = {}

    with pytest.raises(FixerArtifactMissingError) as exc_info:
        execute_fixer(run_dir, run_config, mock_llm_client)

    assert "validation_report.json" in str(exc_info.value)


def test_execute_fixer_unfixable_issue(run_dir, mock_llm_client):
    """Test handling of unfixable issue."""
    validation_report = {
        "schema_version": "1.0",
        "ok": False,
        "profile": "local",
        "gates": [],
        "issues": [
            {
                "issue_id": "unfixable_test",
                "gate": "gate_unknown",
                "severity": "blocker",
                "message": "Unknown error",
                "error_code": "UNKNOWN_ERROR_CODE",
                "status": "OPEN",
            }
        ],
    }

    validation_report_path = run_dir / "artifacts" / "validation_report.json"
    validation_report_path.write_text(json.dumps(validation_report), encoding="utf-8")

    run_config = {}

    result = execute_fixer(run_dir, run_config, mock_llm_client)

    assert result["status"] == "unfixable"
    assert result["issue_id"] == "unfixable_test"
    assert "error_message" in result


def test_execute_fixer_no_diff_produced(run_dir, mock_llm_client):
    """Test error when fix produces no diff."""
    # Create a file that already has no token (so fix won't change it)
    test_file = run_dir / "work" / "site" / "no_diff.md"
    test_file.write_text("Line without any tokens\n", encoding="utf-8")

    # Create validation report with issue pointing to line that doesn't have token
    validation_report = {
        "schema_version": "1.0",
        "ok": False,
        "profile": "local",
        "gates": [],
        "issues": [
            {
                "issue_id": "token_test",
                "gate": "gate_11_template_token_lint",
                "severity": "blocker",
                "message": "Unresolved template token found: __TOKEN__",
                "error_code": "GATE_TEMPLATE_TOKEN_UNRESOLVED",
                "location": {"path": str(test_file), "line": 1},
                "status": "OPEN",
            }
        ],
    }

    validation_report_path = run_dir / "artifacts" / "validation_report.json"
    validation_report_path.write_text(json.dumps(validation_report), encoding="utf-8")

    run_config = {}

    # Fix will fail because line doesn't actually contain the token, resulting in no diff
    with pytest.raises(FixerNoOpError):
        execute_fixer(run_dir, run_config, mock_llm_client)


# Tests for utility functions
def test_compute_file_hash(tmp_path):
    """Test file hash computation."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content", encoding="utf-8")

    hash1 = compute_file_hash(test_file)
    hash2 = compute_file_hash(test_file)

    assert hash1 == hash2
    assert len(hash1) == 64  # SHA256 hex length


def test_compute_file_hash_nonexistent(tmp_path):
    """Test hash of nonexistent file."""
    hash_val = compute_file_hash(tmp_path / "nonexistent.txt")
    assert hash_val == ""


def test_parse_frontmatter_valid():
    """Test parsing valid frontmatter."""
    content = "---\ntitle: Test\ntype: docs\n---\nBody content."

    frontmatter, body = parse_frontmatter(content)

    assert frontmatter is not None
    assert frontmatter["title"] == "Test"
    assert frontmatter["type"] == "docs"
    assert body == "Body content."


def test_parse_frontmatter_no_frontmatter():
    """Test parsing content without frontmatter."""
    content = "Just body content."

    frontmatter, body = parse_frontmatter(content)

    assert frontmatter is None
    assert body == "Just body content."


def test_write_frontmatter():
    """Test writing frontmatter."""
    frontmatter = {"title": "Test", "type": "docs"}
    body = "\nBody content."

    result = write_frontmatter(frontmatter, body)

    assert result.startswith("---\n")
    assert "title: Test" in result
    assert "type: docs" in result
    assert result.endswith("---\n\nBody content.")


def test_check_fix_produced_diff(tmp_path):
    """Test checking if fix produced diff."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("original content", encoding="utf-8")

    original_hash = compute_file_hash(test_file)
    original_hashes = {str(test_file): original_hash}

    # Modify file
    test_file.write_text("modified content", encoding="utf-8")

    has_diff = check_fix_produced_diff([str(test_file)], tmp_path, original_hashes)

    assert has_diff is True


def test_check_fix_produced_diff_no_change(tmp_path):
    """Test checking when no diff produced."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("same content", encoding="utf-8")

    original_hash = compute_file_hash(test_file)
    original_hashes = {str(test_file): original_hash}

    # No change
    has_diff = check_fix_produced_diff([str(test_file)], tmp_path, original_hashes)

    assert has_diff is False


def test_deterministic_event_emission(run_dir, mock_llm_client):
    """Test that events are emitted deterministically."""
    # Create validation report
    validation_report = {
        "schema_version": "1.0",
        "ok": False,
        "profile": "local",
        "gates": [],
        "issues": [
            {
                "issue_id": "test_issue",
                "gate": "gate_11_template_token_lint",
                "severity": "blocker",
                "message": "Unresolved template token found: __TEST__",
                "error_code": "GATE_TEMPLATE_TOKEN_UNRESOLVED",
                "status": "OPEN",
            }
        ],
    }

    # Create test file
    test_file = run_dir / "work" / "site" / "test.md"
    test_file.write_text("Line 1\nLine with __TEST__ token\n", encoding="utf-8")
    validation_report["issues"][0]["location"] = {"path": str(test_file), "line": 2}

    validation_report_path = run_dir / "artifacts" / "validation_report.json"
    validation_report_path.write_text(json.dumps(validation_report), encoding="utf-8")

    run_config = {}

    # Run fixer
    execute_fixer(run_dir, run_config, mock_llm_client)

    # Verify events
    events_file = run_dir / "events.ndjson"
    events = []
    for line in events_file.read_text().splitlines():
        if line.strip():
            events.append(json.loads(line))

    # Check event types
    event_types = [e["type"] for e in events]
    assert "FIXER_STARTED" in event_types
    assert "ISSUE_RESOLVED" in event_types
    assert "FIXER_COMPLETED" in event_types

    # Check all events have required fields
    for event in events:
        assert "event_id" in event
        assert "run_id" in event
        assert "ts" in event
        assert "type" in event
        assert "trace_id" in event
        assert "span_id" in event
