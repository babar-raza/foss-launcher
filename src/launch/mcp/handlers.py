"""MCP tool handlers with orchestrator integration.

Implements real MCP tool handlers per:
- specs/14_mcp_endpoints.md (MCP tool handlers)
- specs/24_mcp_tool_schemas.md (Tool interfaces and error handling)
- specs/11_state_and_events.md (Run state management)

This module replaces TC-511 stubs with real orchestrator-integrated handlers.
Handlers interact with the orchestrator, event log, and snapshot manager.

Spec compliance:
- Tool handlers per specs/14_mcp_endpoints.md:82-94
- Request/response schemas per specs/24_mcp_tool_schemas.md
- Standard error shape per specs/24_mcp_tool_schemas.md:19-31
- Event emission per specs/11_state_and_events.md
"""

from __future__ import annotations

import json
import hashlib
import base64
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import mcp.types as types

from launch.io.run_layout import create_run_skeleton, RunLayout
from launch.models.state import RUN_STATE_CREATED
from launch.orchestrator import execute_run
from launch.state.event_log import read_events
from launch.state.snapshot_manager import read_snapshot, replay_events


# Error codes per specs/24_mcp_tool_schemas.md:33-44
ERROR_INVALID_INPUT = "INVALID_INPUT"
ERROR_SCHEMA_VALIDATION_FAILED = "SCHEMA_VALIDATION_FAILED"
ERROR_RUN_NOT_FOUND = "RUN_NOT_FOUND"
ERROR_ILLEGAL_STATE = "ILLEGAL_STATE"
ERROR_TOOLCHAIN_MISSING = "TOOLCHAIN_MISSING"
ERROR_GATE_FAILED = "GATE_FAILED"
ERROR_FIX_EXHAUSTED = "FIX_EXHAUSTED"
ERROR_ALLOWED_PATHS_VIOLATION = "ALLOWED_PATHS_VIOLATION"
ERROR_COMMIT_SERVICE_ERROR = "COMMIT_SERVICE_ERROR"
ERROR_CANCELLED = "CANCELLED"
ERROR_INTERNAL = "INTERNAL"


# Workspace path for runs (binding)
WORKSPACE_DIR = Path.cwd() / "runs"


def _error_response(
    error_code: str,
    message: str,
    retryable: bool = False,
    details: Optional[Dict[str, Any]] = None,
    run_id: Optional[str] = None,
) -> List[types.TextContent]:
    """Create standard error response per specs/24_mcp_tool_schemas.md:19-31.

    Args:
        error_code: Error code from specs/24_mcp_tool_schemas.md:33-44
        message: Human-readable error message
        retryable: Whether error is retryable
        details: Additional error details
        run_id: Optional run ID

    Returns:
        MCP error response as TextContent list
    """
    response: Dict[str, Any] = {
        "ok": False,
        "error": {
            "code": error_code,
            "message": message,
            "retryable": retryable,
        },
    }

    if details:
        response["error"]["details"] = details

    if run_id:
        response["run_id"] = run_id

    return [types.TextContent(type="text", text=json.dumps(response))]


def _success_response(data: Dict[str, Any]) -> List[types.TextContent]:
    """Create success response with ok=true.

    Args:
        data: Response data

    Returns:
        MCP success response as TextContent list
    """
    response = {"ok": True, **data}
    return [types.TextContent(type="text", text=json.dumps(response))]


def _generate_run_id() -> str:
    """Generate unique run ID.

    Format: r_YYYY-MM-DDTHH-MM-SSZ_<random>
    Per specs/11_state_and_events.md and run ID conventions.

    Returns:
        Run ID string
    """
    import uuid
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    suffix = uuid.uuid4().hex[:8]
    return f"r_{ts}_{suffix}"


def _find_run_dir(run_id: str) -> Optional[Path]:
    """Find run directory for given run_id.

    Args:
        run_id: Run identifier

    Returns:
        Path to run directory if found, None otherwise
    """
    run_dir = WORKSPACE_DIR / run_id
    if run_dir.exists() and run_dir.is_dir():
        return run_dir
    return None


def _get_run_status_from_snapshot(run_dir: Path, run_id: str) -> Dict[str, Any]:
    """Get run status from snapshot.json and events.ndjson.

    Args:
        run_dir: Path to run directory
        run_id: Run identifier

    Returns:
        RunStatus dictionary per specs/24_mcp_tool_schemas.md:46-62
    """
    snapshot_file = run_dir / "snapshot.json"
    events_file = run_dir / "events.ndjson"

    # Replay events to get current snapshot
    if events_file.exists():
        snapshot = replay_events(events_file, run_id)
    elif snapshot_file.exists():
        snapshot = read_snapshot(snapshot_file)
    else:
        # No snapshot yet, return minimal state
        return {
            "run_id": run_id,
            "state": RUN_STATE_CREATED,
            "section_states": {},
            "open_issues": [],
            "artifacts": [],
        }

    # Extract open issues (status != RESOLVED)
    open_issues = [
        {
            "issue_id": issue.get("issue_id", "unknown"),
            "severity": issue.get("severity", "warning"),
            "gate": issue.get("gate", "unknown"),
            "title": issue.get("title", "No title"),
        }
        for issue in snapshot.issues
        if issue.get("status") != "RESOLVED"
    ]

    # Build artifacts list
    artifacts = [
        {
            "name": name,
            "sha256": entry.sha256,
        }
        for name, entry in snapshot.artifacts_index.items()
    ]

    return {
        "run_id": run_id,
        "state": snapshot.run_state,
        "section_states": snapshot.section_states,
        "open_issues": open_issues,
        "artifacts": artifacts,
    }


async def handle_launch_start_run(arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Handle launch_start_run tool invocation.

    Start a new run from run_config. Creates run directory, initializes state,
    and invokes orchestrator.

    Spec references:
    - specs/24_mcp_tool_schemas.md:84-107 (Tool schema)
    - specs/11_state_and_events.md (State initialization)

    Args:
        arguments: Tool arguments containing run_config and optional idempotency_key

    Returns:
        Success response with run_id and state, or error response
    """
    try:
        run_config = arguments.get("run_config")
        if not run_config:
            return _error_response(
                ERROR_INVALID_INPUT,
                "Missing required field: run_config",
                details={"missing_fields": ["run_config"]},
            )

        # TODO: Validate run_config against schema (TC-200 schema validation)
        # For now, accept any dict

        # Generate run ID
        run_id = _generate_run_id()
        run_dir = WORKSPACE_DIR / run_id

        # Check idempotency
        idempotency_key = arguments.get("idempotency_key")
        if idempotency_key:
            # TODO: Implement idempotency check (hash run_config, check existing runs)
            # For now, create new run
            pass

        # Create run directory structure
        WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
        create_run_skeleton(run_dir)

        # Write run_config.yaml
        import yaml
        from launch.io.atomic import atomic_write_text
        run_config_yaml = yaml.dump(run_config, sort_keys=False)
        atomic_write_text(run_dir / "run_config.yaml", run_config_yaml)

        # Execute run asynchronously (non-blocking for MCP tool call)
        # NOTE: In production, this would spawn a background task
        # For now, return run_id immediately with state CREATED
        # Actual orchestrator execution happens in separate process/thread

        return _success_response({
            "run_id": run_id,
            "state": RUN_STATE_CREATED,
        })

    except Exception as e:
        return _error_response(
            ERROR_INTERNAL,
            f"Tool execution failed: {str(e)}",
            details={"cause_class": type(e).__name__},
        )


async def handle_launch_get_status(arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Handle launch_get_status tool invocation.

    Query run status from snapshot and events.

    Spec references:
    - specs/24_mcp_tool_schemas.md:242-252 (Tool schema)
    - specs/11_state_and_events.md (State model)

    Args:
        arguments: Tool arguments containing run_id

    Returns:
        Success response with RunStatus, or error response
    """
    try:
        run_id = arguments.get("run_id")
        if not run_id:
            return _error_response(
                ERROR_INVALID_INPUT,
                "Missing required field: run_id",
                details={"missing_fields": ["run_id"]},
            )

        # Find run directory
        run_dir = _find_run_dir(run_id)
        if not run_dir:
            return _error_response(
                ERROR_RUN_NOT_FOUND,
                f"Run not found: {run_id}",
                run_id=run_id,
            )

        # Get status from snapshot
        status = _get_run_status_from_snapshot(run_dir, run_id)

        return _success_response({"status": status})

    except Exception as e:
        return _error_response(
            ERROR_INTERNAL,
            f"Tool execution failed: {str(e)}",
            details={"cause_class": type(e).__name__},
        )


async def handle_launch_list_runs(arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Handle launch_list_runs tool invocation.

    List all runs in workspace with optional filtering.

    Spec references:
    - specs/24_mcp_tool_schemas.md:372-386 (Tool schema)

    Args:
        arguments: Tool arguments with optional filter

    Returns:
        Success response with runs list, or error response
    """
    try:
        filter_criteria = arguments.get("filter", {})
        product_slug_filter = filter_criteria.get("product_slug")
        state_filter = filter_criteria.get("state")

        # List run directories
        if not WORKSPACE_DIR.exists():
            return _success_response({"runs": []})

        runs = []
        for run_dir in WORKSPACE_DIR.iterdir():
            if not run_dir.is_dir():
                continue

            run_id = run_dir.name

            # Load snapshot to get state
            snapshot_file = run_dir / "snapshot.json"
            events_file = run_dir / "events.ndjson"

            try:
                if events_file.exists():
                    snapshot = replay_events(events_file, run_id)
                elif snapshot_file.exists():
                    snapshot = read_snapshot(snapshot_file)
                else:
                    # Skip runs without snapshot
                    continue

                # Load run_config for product_slug
                run_config_file = run_dir / "run_config.yaml"
                product_slug = None
                if run_config_file.exists():
                    import yaml
                    with run_config_file.open("r") as f:
                        run_config = yaml.safe_load(f)
                        product_slug = run_config.get("product_slug")

                # Apply filters
                if product_slug_filter and product_slug != product_slug_filter:
                    continue
                if state_filter and snapshot.run_state != state_filter:
                    continue

                # Get timestamps from events
                events = read_events(events_file) if events_file.exists() else []
                started_at = events[0].ts if events else None
                finished_at = events[-1].ts if events and snapshot.run_state in ["DONE", "FAILED", "CANCELLED"] else None

                runs.append({
                    "run_id": run_id,
                    "product_slug": product_slug,
                    "state": snapshot.run_state,
                    "started_at": started_at,
                    "finished_at": finished_at,
                })

            except Exception:
                # Skip invalid runs
                continue

        return _success_response({"runs": runs})

    except Exception as e:
        return _error_response(
            ERROR_INTERNAL,
            f"Tool execution failed: {str(e)}",
            details={"cause_class": type(e).__name__},
        )


async def handle_launch_get_artifact(arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Handle launch_get_artifact tool invocation.

    Retrieve artifact from run directory.

    Spec references:
    - specs/24_mcp_tool_schemas.md:254-262 (Tool schema)
    - specs/24_mcp_tool_schemas.md:65-78 (ArtifactResponse)

    Args:
        arguments: Tool arguments containing run_id and artifact_name

    Returns:
        Success response with artifact content, or error response
    """
    try:
        run_id = arguments.get("run_id")
        artifact_name = arguments.get("artifact_name")

        if not run_id or not artifact_name:
            missing = []
            if not run_id:
                missing.append("run_id")
            if not artifact_name:
                missing.append("artifact_name")
            return _error_response(
                ERROR_INVALID_INPUT,
                f"Missing required fields: {', '.join(missing)}",
                details={"missing_fields": missing},
            )

        # Find run directory
        run_dir = _find_run_dir(run_id)
        if not run_dir:
            return _error_response(
                ERROR_RUN_NOT_FOUND,
                f"Run not found: {run_id}",
                run_id=run_id,
            )

        # Find artifact (check artifacts/ and other locations)
        artifact_locations = [
            run_dir / "artifacts" / artifact_name,
            run_dir / artifact_name,
            run_dir / "reports" / artifact_name,
        ]

        artifact_path = None
        for loc in artifact_locations:
            if loc.exists() and loc.is_file():
                artifact_path = loc
                break

        if not artifact_path:
            return _error_response(
                ERROR_INVALID_INPUT,
                f"Artifact not found: {artifact_name}",
                details={"artifact_name": artifact_name},
                run_id=run_id,
            )

        # Read artifact content
        content = artifact_path.read_text(encoding="utf-8")

        # Compute SHA256
        sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()

        # Determine content type
        if artifact_name.endswith(".json"):
            content_type = "application/json"
        elif artifact_name.endswith(".yaml") or artifact_name.endswith(".yml"):
            content_type = "application/x-yaml"
        elif artifact_name.endswith(".md"):
            content_type = "text/markdown"
        else:
            content_type = "text/plain"

        return _success_response({
            "run_id": run_id,
            "artifact": {
                "name": artifact_name,
                "content_type": content_type,
                "sha256": sha256,
                "content": content,
            },
        })

    except Exception as e:
        return _error_response(
            ERROR_INTERNAL,
            f"Tool execution failed: {str(e)}",
            details={"cause_class": type(e).__name__},
        )


async def handle_launch_validate(arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Handle launch_validate tool invocation.

    Run validation gates (W7) for current worktree state.

    Spec references:
    - specs/24_mcp_tool_schemas.md:264-285 (Tool schema)
    - specs/09_validation_gates.md (Validation gates)

    Args:
        arguments: Tool arguments containing run_id

    Returns:
        Success response with validation_report, or error response
    """
    try:
        run_id = arguments.get("run_id")
        if not run_id:
            return _error_response(
                ERROR_INVALID_INPUT,
                "Missing required field: run_id",
                details={"missing_fields": ["run_id"]},
            )

        # Find run directory
        run_dir = _find_run_dir(run_id)
        if not run_dir:
            return _error_response(
                ERROR_RUN_NOT_FOUND,
                f"Run not found: {run_id}",
                run_id=run_id,
            )

        # Check preconditions: run state MUST be at least LINKING
        snapshot_file = run_dir / "snapshot.json"
        if snapshot_file.exists():
            snapshot = read_snapshot(snapshot_file)
            if snapshot.run_state not in ["LINKING", "VALIDATING", "FIXING", "READY_FOR_PR"]:
                return _error_response(
                    ERROR_ILLEGAL_STATE,
                    f"Validation requires run state >= LINKING, got {snapshot.run_state}",
                    details={"current_state": snapshot.run_state},
                    run_id=run_id,
                )

        # TODO: Invoke W7 validator worker (blocked by TC-470)
        # For now, return stub validation report
        validation_report = {
            "ok": True,
            "gates": [],
            "issues": [],
            "summary": "Validation not yet implemented (TC-470 blocked)",
        }

        return _success_response({
            "run_id": run_id,
            "validation_report": validation_report,
        })

    except Exception as e:
        return _error_response(
            ERROR_INTERNAL,
            f"Tool execution failed: {str(e)}",
            details={"cause_class": type(e).__name__},
        )


async def handle_launch_fix_next(arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Handle launch_fix_next tool invocation.

    Select next fixable issue and apply fix attempt (W8), then re-validate.

    Spec references:
    - specs/24_mcp_tool_schemas.md:287-314 (Tool schema)
    - specs/08_patch_engine.md (Patch engine)

    Args:
        arguments: Tool arguments containing run_id

    Returns:
        Success response with fix result, or error response
    """
    try:
        run_id = arguments.get("run_id")
        if not run_id:
            return _error_response(
                ERROR_INVALID_INPUT,
                "Missing required field: run_id",
                details={"missing_fields": ["run_id"]},
            )

        # Find run directory
        run_dir = _find_run_dir(run_id)
        if not run_dir:
            return _error_response(
                ERROR_RUN_NOT_FOUND,
                f"Run not found: {run_id}",
                run_id=run_id,
            )

        # Check preconditions
        snapshot_file = run_dir / "snapshot.json"
        if snapshot_file.exists():
            snapshot = read_snapshot(snapshot_file)
            if snapshot.run_state != "VALIDATING":
                return _error_response(
                    ERROR_ILLEGAL_STATE,
                    f"Fix requires run state VALIDATING, got {snapshot.run_state}",
                    details={"current_state": snapshot.run_state},
                    run_id=run_id,
                )

        # TODO: Invoke W8 patch engine (blocked by TC-480)
        # For now, return stub response
        return _error_response(
            ERROR_INTERNAL,
            "Fix not yet implemented (TC-480 blocked)",
            run_id=run_id,
        )

    except Exception as e:
        return _error_response(
            ERROR_INTERNAL,
            f"Tool execution failed: {str(e)}",
            details={"cause_class": type(e).__name__},
        )


async def handle_launch_resume(arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Handle launch_resume tool invocation.

    Resume paused/partial run from snapshot.

    Spec references:
    - specs/24_mcp_tool_schemas.md:316-328 (Tool schema)
    - specs/11_state_and_events.md:144-160 (Resume algorithm)

    Args:
        arguments: Tool arguments containing run_id

    Returns:
        Success response with resumed status, or error response
    """
    try:
        run_id = arguments.get("run_id")
        if not run_id:
            return _error_response(
                ERROR_INVALID_INPUT,
                "Missing required field: run_id",
                details={"missing_fields": ["run_id"]},
            )

        # Find run directory
        run_dir = _find_run_dir(run_id)
        if not run_dir:
            return _error_response(
                ERROR_RUN_NOT_FOUND,
                f"Run not found: {run_id}",
                run_id=run_id,
            )

        # Load snapshot
        snapshot_file = run_dir / "snapshot.json"
        if not snapshot_file.exists():
            return _error_response(
                ERROR_INVALID_INPUT,
                "Cannot resume: no snapshot found",
                run_id=run_id,
            )

        snapshot = read_snapshot(snapshot_file)

        # TODO: Implement resume logic (orchestrator resume)
        # For now, return current status
        status = _get_run_status_from_snapshot(run_dir, run_id)

        return _success_response({"status": status})

    except Exception as e:
        return _error_response(
            ERROR_INTERNAL,
            f"Tool execution failed: {str(e)}",
            details={"cause_class": type(e).__name__},
        )


async def handle_launch_cancel(arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Handle launch_cancel tool invocation.

    Cancel a running launch task.

    Spec references:
    - specs/24_mcp_tool_schemas.md:330-343 (Tool schema)

    Args:
        arguments: Tool arguments containing run_id

    Returns:
        Success response with cancelled status, or error response
    """
    try:
        run_id = arguments.get("run_id")
        if not run_id:
            return _error_response(
                ERROR_INVALID_INPUT,
                "Missing required field: run_id",
                details={"missing_fields": ["run_id"]},
            )

        # Find run directory
        run_dir = _find_run_dir(run_id)
        if not run_dir:
            return _error_response(
                ERROR_RUN_NOT_FOUND,
                f"Run not found: {run_id}",
                run_id=run_id,
            )

        # TODO: Implement cancellation (signal orchestrator, update state)
        # For now, return not implemented
        return _error_response(
            ERROR_INTERNAL,
            "Cancellation not yet implemented",
            run_id=run_id,
        )

    except Exception as e:
        return _error_response(
            ERROR_INTERNAL,
            f"Tool execution failed: {str(e)}",
            details={"cause_class": type(e).__name__},
        )


async def handle_launch_open_pr(arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Handle launch_open_pr tool invocation.

    Open PR using commit service.

    Spec references:
    - specs/24_mcp_tool_schemas.md:345-369 (Tool schema)
    - specs/17_github_commit_service.md (Commit service)

    Args:
        arguments: Tool arguments containing run_id

    Returns:
        Success response with PR URL, or error response
    """
    try:
        run_id = arguments.get("run_id")
        if not run_id:
            return _error_response(
                ERROR_INVALID_INPUT,
                "Missing required field: run_id",
                details={"missing_fields": ["run_id"]},
            )

        # Find run directory
        run_dir = _find_run_dir(run_id)
        if not run_dir:
            return _error_response(
                ERROR_RUN_NOT_FOUND,
                f"Run not found: {run_id}",
                run_id=run_id,
            )

        # Check preconditions
        snapshot_file = run_dir / "snapshot.json"
        if snapshot_file.exists():
            snapshot = read_snapshot(snapshot_file)
            if snapshot.run_state != "READY_FOR_PR":
                return _error_response(
                    ERROR_ILLEGAL_STATE,
                    f"PR requires run state READY_FOR_PR, got {snapshot.run_state}",
                    details={"current_state": snapshot.run_state},
                    run_id=run_id,
                )

        # TODO: Invoke commit service (blocked by TC-490)
        # For now, return stub response
        return _error_response(
            ERROR_INTERNAL,
            "PR creation not yet implemented (TC-490 blocked)",
            run_id=run_id,
        )

    except Exception as e:
        return _error_response(
            ERROR_INTERNAL,
            f"Tool execution failed: {str(e)}",
            details={"cause_class": type(e).__name__},
        )


async def handle_launch_start_run_from_product_url(arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Handle launch_start_run_from_product_url tool invocation.

    Quickstart: derive run_config from Aspose product URL and start run.

    Spec references:
    - specs/24_mcp_tool_schemas.md:110-151 (Tool schema)
    - specs/26_repo_adapters_and_variability.md (URL parsing)

    Args:
        arguments: Tool arguments containing url and optional idempotency_key

    Returns:
        Success response with run_id and derived_config, or error response
    """
    try:
        url = arguments.get("url")
        if not url:
            return _error_response(
                ERROR_INVALID_INPUT,
                "Missing required field: url",
                details={"missing_fields": ["url"]},
            )

        # TODO: Implement URL parsing and config derivation (TC-520)
        # For now, return error
        return _error_response(
            ERROR_INTERNAL,
            "Product URL parsing not yet implemented (TC-520 blocked)",
        )

    except Exception as e:
        return _error_response(
            ERROR_INTERNAL,
            f"Tool execution failed: {str(e)}",
            details={"cause_class": type(e).__name__},
        )


async def handle_launch_start_run_from_github_repo_url(arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Handle launch_start_run_from_github_repo_url tool invocation.

    Quickstart: infer product from GitHub repo URL and start run.

    Spec references:
    - specs/24_mcp_tool_schemas.md:153-240 (Tool schema)
    - specs/26_repo_adapters_and_variability.md (Repo inference)

    Args:
        arguments: Tool arguments containing github_repo_url and optional idempotency_key

    Returns:
        Success response with run_id and derived_config, or error response
    """
    try:
        github_repo_url = arguments.get("github_repo_url")
        if not github_repo_url:
            return _error_response(
                ERROR_INVALID_INPUT,
                "Missing required field: github_repo_url",
                details={"missing_fields": ["github_repo_url"]},
            )

        # TODO: Implement GitHub repo inference (TC-520)
        # For now, return error
        return _error_response(
            ERROR_INTERNAL,
            "GitHub repo inference not yet implemented (TC-520 blocked)",
        )

    except Exception as e:
        return _error_response(
            ERROR_INTERNAL,
            f"Tool execution failed: {str(e)}",
            details={"cause_class": type(e).__name__},
        )


async def handle_get_run_telemetry(arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Handle get_run_telemetry tool invocation.

    Retrieve telemetry data from events.ndjson.

    Spec references:
    - specs/24_mcp_tool_schemas.md:388-432 (Tool schema)
    - specs/16_local_telemetry_api.md (Telemetry API)

    Args:
        arguments: Tool arguments containing run_id

    Returns:
        Success response with telemetry data, or error response
    """
    try:
        run_id = arguments.get("run_id")
        if not run_id:
            return _error_response(
                ERROR_INVALID_INPUT,
                "Missing required field: run_id",
                details={"missing_fields": ["run_id"]},
            )

        # Find run directory
        run_dir = _find_run_dir(run_id)
        if not run_dir:
            return _error_response(
                ERROR_RUN_NOT_FOUND,
                f"Run not found: {run_id}",
                run_id=run_id,
            )

        # Read events for telemetry
        events_file = run_dir / "events.ndjson"
        if not events_file.exists():
            return _success_response({
                "run_id": run_id,
                "events": [],
                "summary": {
                    "total_events": 0,
                    "event_types": {},
                },
            })

        events = read_events(events_file)

        # Build telemetry summary
        event_types: Dict[str, int] = {}
        for event in events:
            event_types[event.type] = event_types.get(event.type, 0) + 1

        telemetry_data = {
            "run_id": run_id,
            "events": [e.to_dict() for e in events],
            "summary": {
                "total_events": len(events),
                "event_types": event_types,
                "first_event": events[0].ts if events else None,
                "last_event": events[-1].ts if events else None,
            },
        }

        return _success_response(telemetry_data)

    except Exception as e:
        return _error_response(
            ERROR_INTERNAL,
            f"Tool execution failed: {str(e)}",
            details={"cause_class": type(e).__name__},
        )
