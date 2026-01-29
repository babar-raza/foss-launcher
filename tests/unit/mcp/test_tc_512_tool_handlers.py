"""Tests for TC-512 MCP tool handlers.

Tests MCP tool handler implementations with orchestrator integration per:
- specs/14_mcp_endpoints.md (Tool handlers)
- specs/24_mcp_tool_schemas.md (Tool schemas and error handling)
- specs/11_state_and_events.md (Run state management)

Test coverage:
- 12 tool handlers (1 test per tool minimum)
- Error handling (run not found, invalid state transitions)
- Artifact fetching
- Telemetry retrieval
- State management

Spec compliance:
- Standard error shape per specs/24_mcp_tool_schemas.md:19-31
- Tool request/response schemas per specs/24_mcp_tool_schemas.md
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from launch.mcp import handlers
from launch.models.event import EVENT_RUN_CREATED, EVENT_RUN_STATE_CHANGED, Event
from launch.models.state import RUN_STATE_CREATED, RUN_STATE_VALIDATING, Snapshot
from launch.state.event_log import append_event, generate_event_id, generate_span_id, generate_trace_id
from launch.state.snapshot_manager import write_snapshot, create_initial_snapshot


@pytest.fixture
def temp_workspace(tmp_path):
    """Create temporary workspace for tests."""
    workspace = tmp_path / "runs"
    workspace.mkdir()
    # Monkey-patch WORKSPACE_DIR
    original_workspace = handlers.WORKSPACE_DIR
    handlers.WORKSPACE_DIR = workspace
    yield workspace
    handlers.WORKSPACE_DIR = original_workspace


@pytest.fixture
def sample_run(temp_workspace):
    """Create a sample run directory with snapshot and events."""
    run_id = "r_2026-01-28T10-00-00Z_test1234"
    run_dir = temp_workspace / run_id
    run_dir.mkdir()

    # Create run structure
    (run_dir / "artifacts").mkdir()
    (run_dir / "events.ndjson").touch()
    (run_dir / "snapshot.json").touch()
    (run_dir / "run_config.yaml").touch()

    # Create initial snapshot
    snapshot = create_initial_snapshot(run_id)
    write_snapshot(run_dir / "snapshot.json", snapshot)

    # Create RUN_CREATED event
    trace_id = generate_trace_id()
    event = Event(
        event_id=generate_event_id(),
        run_id=run_id,
        ts="2026-01-28T10:00:00Z",
        type=EVENT_RUN_CREATED,
        payload={"run_id": run_id, "run_config": {}},
        trace_id=trace_id,
        span_id=generate_span_id(),
    )
    append_event(run_dir / "events.ndjson", event)

    # Write sample run_config
    import yaml
    run_config = {"product_slug": "3d", "platform": "python"}
    (run_dir / "run_config.yaml").write_text(yaml.dump(run_config))

    return {
        "run_id": run_id,
        "run_dir": run_dir,
        "snapshot": snapshot,
    }


@pytest.mark.asyncio
async def test_handle_launch_start_run_success(temp_workspace):
    """Test launch_start_run creates run successfully."""
    arguments = {
        "run_config": {
            "product_slug": "3d",
            "platform": "python",
            "locale": "en",
        }
    }

    result = await handlers.handle_launch_start_run(arguments)

    assert len(result) == 1
    response = json.loads(result[0].text)

    assert response["ok"] is True
    assert "run_id" in response
    assert response["state"] == RUN_STATE_CREATED

    # Verify run directory was created
    run_id = response["run_id"]
    run_dir = temp_workspace / run_id
    assert run_dir.exists()
    assert (run_dir / "events.ndjson").exists()
    assert (run_dir / "snapshot.json").exists()
    assert (run_dir / "run_config.yaml").exists()


@pytest.mark.asyncio
async def test_handle_launch_start_run_missing_config(temp_workspace):
    """Test launch_start_run with missing run_config."""
    arguments = {}

    result = await handlers.handle_launch_start_run(arguments)

    assert len(result) == 1
    response = json.loads(result[0].text)

    assert response["ok"] is False
    assert response["error"]["code"] == handlers.ERROR_INVALID_INPUT
    assert "run_config" in response["error"]["message"]


@pytest.mark.asyncio
async def test_handle_launch_get_status_success(temp_workspace, sample_run):
    """Test launch_get_status returns run status."""
    arguments = {"run_id": sample_run["run_id"]}

    result = await handlers.handle_launch_get_status(arguments)

    assert len(result) == 1
    response = json.loads(result[0].text)

    assert response["ok"] is True
    assert "status" in response
    status = response["status"]
    assert status["run_id"] == sample_run["run_id"]
    assert status["state"] == RUN_STATE_CREATED
    assert "section_states" in status
    assert "open_issues" in status
    assert "artifacts" in status


@pytest.mark.asyncio
async def test_handle_launch_get_status_run_not_found(temp_workspace):
    """Test launch_get_status with non-existent run."""
    arguments = {"run_id": "r_nonexistent_12345678"}

    result = await handlers.handle_launch_get_status(arguments)

    assert len(result) == 1
    response = json.loads(result[0].text)

    assert response["ok"] is False
    assert response["error"]["code"] == handlers.ERROR_RUN_NOT_FOUND
    assert "run_id" in response


@pytest.mark.asyncio
async def test_handle_launch_list_runs_empty(temp_workspace):
    """Test launch_list_runs with no runs."""
    arguments = {}

    result = await handlers.handle_launch_list_runs(arguments)

    assert len(result) == 1
    response = json.loads(result[0].text)

    assert response["ok"] is True
    assert "runs" in response
    assert response["runs"] == []


@pytest.mark.asyncio
async def test_handle_launch_list_runs_with_runs(temp_workspace, sample_run):
    """Test launch_list_runs returns run list."""
    arguments = {}

    result = await handlers.handle_launch_list_runs(arguments)

    assert len(result) == 1
    response = json.loads(result[0].text)

    assert response["ok"] is True
    assert "runs" in response
    assert len(response["runs"]) == 1

    run = response["runs"][0]
    assert run["run_id"] == sample_run["run_id"]
    assert run["product_slug"] == "3d"
    assert run["state"] == RUN_STATE_CREATED


@pytest.mark.asyncio
async def test_handle_launch_list_runs_with_filter(temp_workspace, sample_run):
    """Test launch_list_runs with product_slug filter."""
    arguments = {
        "filter": {
            "product_slug": "cells",  # Different from sample_run
        }
    }

    result = await handlers.handle_launch_list_runs(arguments)

    assert len(result) == 1
    response = json.loads(result[0].text)

    assert response["ok"] is True
    assert "runs" in response
    assert len(response["runs"]) == 0  # Filtered out


@pytest.mark.asyncio
async def test_handle_launch_get_artifact_success(temp_workspace, sample_run):
    """Test launch_get_artifact retrieves artifact."""
    # Create sample artifact
    artifact_name = "page_plan.json"
    artifact_content = {"pages": [{"slug": "home"}]}
    artifact_path = sample_run["run_dir"] / "artifacts" / artifact_name
    artifact_path.write_text(json.dumps(artifact_content))

    arguments = {
        "run_id": sample_run["run_id"],
        "artifact_name": artifact_name,
    }

    result = await handlers.handle_launch_get_artifact(arguments)

    assert len(result) == 1
    response = json.loads(result[0].text)

    assert response["ok"] is True
    assert "artifact" in response
    artifact = response["artifact"]
    assert artifact["name"] == artifact_name
    assert artifact["content_type"] == "application/json"
    assert "sha256" in artifact
    assert json.loads(artifact["content"]) == artifact_content


@pytest.mark.asyncio
async def test_handle_launch_get_artifact_not_found(temp_workspace, sample_run):
    """Test launch_get_artifact with non-existent artifact."""
    arguments = {
        "run_id": sample_run["run_id"],
        "artifact_name": "nonexistent.json",
    }

    result = await handlers.handle_launch_get_artifact(arguments)

    assert len(result) == 1
    response = json.loads(result[0].text)

    assert response["ok"] is False
    assert response["error"]["code"] == handlers.ERROR_INVALID_INPUT
    assert "not found" in response["error"]["message"].lower()


@pytest.mark.asyncio
async def test_handle_launch_validate_success(temp_workspace, sample_run):
    """Test launch_validate executes validation."""
    # Update snapshot to VALIDATING state
    snapshot = sample_run["snapshot"]
    snapshot.run_state = RUN_STATE_VALIDATING
    write_snapshot(sample_run["run_dir"] / "snapshot.json", snapshot)

    arguments = {"run_id": sample_run["run_id"]}

    result = await handlers.handle_launch_validate(arguments)

    assert len(result) == 1
    response = json.loads(result[0].text)

    assert response["ok"] is True
    assert "validation_report" in response


@pytest.mark.asyncio
async def test_handle_launch_validate_illegal_state(temp_workspace, sample_run):
    """Test launch_validate with illegal state."""
    # Keep snapshot in CREATED state (requires >= LINKING)
    arguments = {"run_id": sample_run["run_id"]}

    result = await handlers.handle_launch_validate(arguments)

    assert len(result) == 1
    response = json.loads(result[0].text)

    assert response["ok"] is False
    assert response["error"]["code"] == handlers.ERROR_ILLEGAL_STATE


@pytest.mark.asyncio
async def test_handle_launch_fix_next_illegal_state(temp_workspace, sample_run):
    """Test launch_fix_next with wrong state."""
    # Snapshot is CREATED, requires VALIDATING
    arguments = {"run_id": sample_run["run_id"]}

    result = await handlers.handle_launch_fix_next(arguments)

    assert len(result) == 1
    response = json.loads(result[0].text)

    assert response["ok"] is False
    assert response["error"]["code"] == handlers.ERROR_ILLEGAL_STATE


@pytest.mark.asyncio
async def test_handle_launch_resume_success(temp_workspace, sample_run):
    """Test launch_resume loads snapshot."""
    arguments = {"run_id": sample_run["run_id"]}

    result = await handlers.handle_launch_resume(arguments)

    assert len(result) == 1
    response = json.loads(result[0].text)

    assert response["ok"] is True
    assert "status" in response


@pytest.mark.asyncio
async def test_handle_launch_cancel_run_not_found(temp_workspace):
    """Test launch_cancel with non-existent run."""
    arguments = {"run_id": "r_nonexistent_12345678"}

    result = await handlers.handle_launch_cancel(arguments)

    assert len(result) == 1
    response = json.loads(result[0].text)

    assert response["ok"] is False
    assert response["error"]["code"] == handlers.ERROR_RUN_NOT_FOUND


@pytest.mark.asyncio
async def test_handle_launch_open_pr_illegal_state(temp_workspace, sample_run):
    """Test launch_open_pr with wrong state."""
    # Snapshot is CREATED, requires READY_FOR_PR
    arguments = {"run_id": sample_run["run_id"]}

    result = await handlers.handle_launch_open_pr(arguments)

    assert len(result) == 1
    response = json.loads(result[0].text)

    assert response["ok"] is False
    assert response["error"]["code"] == handlers.ERROR_ILLEGAL_STATE


@pytest.mark.asyncio
async def test_handle_launch_start_run_from_product_url_not_implemented(temp_workspace):
    """Test launch_start_run_from_product_url not yet implemented."""
    arguments = {"url": "https://products.aspose.org/3d/en/python/"}

    result = await handlers.handle_launch_start_run_from_product_url(arguments)

    assert len(result) == 1
    response = json.loads(result[0].text)

    assert response["ok"] is False
    assert response["error"]["code"] == handlers.ERROR_INTERNAL


@pytest.mark.asyncio
async def test_handle_launch_start_run_from_github_repo_url_not_implemented(temp_workspace):
    """Test launch_start_run_from_github_repo_url not yet implemented."""
    arguments = {"github_repo_url": "https://github.com/aspose-3d/Aspose.3D-for-Python-via-.NET"}

    result = await handlers.handle_launch_start_run_from_github_repo_url(arguments)

    assert len(result) == 1
    response = json.loads(result[0].text)

    assert response["ok"] is False
    assert response["error"]["code"] == handlers.ERROR_INTERNAL


@pytest.mark.asyncio
async def test_handle_get_run_telemetry_success(temp_workspace, sample_run):
    """Test get_run_telemetry retrieves events."""
    arguments = {"run_id": sample_run["run_id"]}

    result = await handlers.handle_get_run_telemetry(arguments)

    assert len(result) == 1
    response = json.loads(result[0].text)

    assert response["ok"] is True
    assert "events" in response
    assert "summary" in response
    assert response["summary"]["total_events"] >= 1  # At least RUN_CREATED


@pytest.mark.asyncio
async def test_handle_get_run_telemetry_run_not_found(temp_workspace):
    """Test get_run_telemetry with non-existent run."""
    arguments = {"run_id": "r_nonexistent_12345678"}

    result = await handlers.handle_get_run_telemetry(arguments)

    assert len(result) == 1
    response = json.loads(result[0].text)

    assert response["ok"] is False
    assert response["error"]["code"] == handlers.ERROR_RUN_NOT_FOUND


@pytest.mark.asyncio
async def test_error_response_format():
    """Test _error_response follows standard error shape."""
    result = handlers._error_response(
        error_code="TEST_ERROR",
        message="Test error message",
        retryable=True,
        details={"field": "value"},
        run_id="r_test_12345678",
    )

    assert len(result) == 1
    response = json.loads(result[0].text)

    assert response["ok"] is False
    assert response["run_id"] == "r_test_12345678"
    assert response["error"]["code"] == "TEST_ERROR"
    assert response["error"]["message"] == "Test error message"
    assert response["error"]["retryable"] is True
    assert response["error"]["details"]["field"] == "value"


@pytest.mark.asyncio
async def test_success_response_format():
    """Test _success_response includes ok=true."""
    result = handlers._success_response({
        "run_id": "r_test_12345678",
        "state": "CREATED",
    })

    assert len(result) == 1
    response = json.loads(result[0].text)

    assert response["ok"] is True
    assert response["run_id"] == "r_test_12345678"
    assert response["state"] == "CREATED"


def test_generate_run_id_format():
    """Test run ID format matches specs."""
    run_id = handlers._generate_run_id()

    assert run_id.startswith("r_")
    assert "T" in run_id  # ISO8601 timestamp
    assert "Z" in run_id  # UTC timezone
    assert len(run_id.split("_")) == 3  # r_, timestamp, random


@pytest.mark.asyncio
async def test_handle_launch_get_artifact_markdown_content_type(temp_workspace, sample_run):
    """Test launch_get_artifact returns correct content_type for markdown."""
    artifact_name = "README.md"
    artifact_content = "# Test\n\nSome content"
    artifact_path = sample_run["run_dir"] / "artifacts" / artifact_name
    artifact_path.write_text(artifact_content)

    arguments = {
        "run_id": sample_run["run_id"],
        "artifact_name": artifact_name,
    }

    result = await handlers.handle_launch_get_artifact(arguments)

    assert len(result) == 1
    response = json.loads(result[0].text)

    assert response["ok"] is True
    artifact = response["artifact"]
    assert artifact["content_type"] == "text/markdown"


@pytest.mark.asyncio
async def test_handle_launch_list_runs_state_filter(temp_workspace, sample_run):
    """Test launch_list_runs with state filter."""
    arguments = {
        "filter": {
            "state": "DONE",  # Different from CREATED
        }
    }

    result = await handlers.handle_launch_list_runs(arguments)

    assert len(result) == 1
    response = json.loads(result[0].text)

    assert response["ok"] is True
    assert len(response["runs"]) == 0  # Filtered out


@pytest.mark.asyncio
async def test_handle_launch_get_status_with_issues(temp_workspace, sample_run):
    """Test launch_get_status includes open issues."""
    # Add ISSUE_OPENED events to event log
    from launch.models.event import EVENT_ISSUE_OPENED

    trace_id = generate_trace_id()

    # Issue 1: OPEN
    event1 = Event(
        event_id=generate_event_id(),
        run_id=sample_run["run_id"],
        ts="2026-01-28T10:01:00Z",
        type=EVENT_ISSUE_OPENED,
        payload={
            "issue": {
                "issue_id": "iss_001",
                "severity": "blocker",
                "gate": "TruthLock",
                "title": "Missing citation",
                "status": "OPEN",
            }
        },
        trace_id=trace_id,
        span_id=generate_span_id(),
    )
    append_event(sample_run["run_dir"] / "events.ndjson", event1)

    # Issue 2: will be RESOLVED
    event2 = Event(
        event_id=generate_event_id(),
        run_id=sample_run["run_id"],
        ts="2026-01-28T10:02:00Z",
        type=EVENT_ISSUE_OPENED,
        payload={
            "issue": {
                "issue_id": "iss_002",
                "severity": "warning",
                "gate": "LinkCheck",
                "title": "Broken link",
                "status": "OPEN",
            }
        },
        trace_id=trace_id,
        span_id=generate_span_id(),
    )
    append_event(sample_run["run_dir"] / "events.ndjson", event2)

    # Resolve issue 2
    from launch.models.event import EVENT_ISSUE_RESOLVED
    event3 = Event(
        event_id=generate_event_id(),
        run_id=sample_run["run_id"],
        ts="2026-01-28T10:03:00Z",
        type=EVENT_ISSUE_RESOLVED,
        payload={"issue_id": "iss_002"},
        trace_id=trace_id,
        span_id=generate_span_id(),
    )
    append_event(sample_run["run_dir"] / "events.ndjson", event3)

    arguments = {"run_id": sample_run["run_id"]}

    result = await handlers.handle_launch_get_status(arguments)

    assert len(result) == 1
    response = json.loads(result[0].text)

    assert response["ok"] is True
    status = response["status"]
    assert len(status["open_issues"]) == 1  # Only OPEN issue
    assert status["open_issues"][0]["issue_id"] == "iss_001"
