"""MCP tool registration and handlers.

Implements tool registration per:
- specs/24_mcp_tool_schemas.md (Tool schemas and contracts)
- specs/14_mcp_endpoints.md:82-94 (Tool registration)

This module provides MCP tool handlers for the orchestrator operations.
Tools are registered with the MCP server in server.py.

Spec compliance:
- Tool names per specs/14_mcp_endpoints.md:82-94
- Request/response schemas per specs/24_mcp_tool_schemas.md
- Standard error shape per specs/24_mcp_tool_schemas.md:19-31
"""

from __future__ import annotations

from typing import Any, Dict, List

import mcp.types as types


# Tool schema definitions per specs/24_mcp_tool_schemas.md
# These define the MCP tool metadata (name, description, input schema)

def get_tool_schemas() -> List[types.Tool]:
    """Get all MCP tool schemas.

    Returns list of Tool objects with:
    - name: Tool identifier
    - description: Human-readable tool description
    - inputSchema: JSON Schema for tool arguments

    Spec references:
    - specs/14_mcp_endpoints.md:82-94 (Tool list)
    - specs/24_mcp_tool_schemas.md (Tool schemas)

    Returns:
        List of Tool schema definitions
    """
    return [
        # launch_start_run: Start a new documentation run
        types.Tool(
            name="launch_start_run",
            description="Start a new documentation run from a run_config. Returns run_id for tracking.",
            inputSchema={
                "type": "object",
                "properties": {
                    "run_config": {
                        "type": "object",
                        "description": "Run configuration validated against run_config.schema.json"
                    },
                    "idempotency_key": {
                        "type": "string",
                        "description": "Optional stable string for idempotent run creation"
                    }
                },
                "required": ["run_config"]
            }
        ),

        # launch_get_status: Query run status
        types.Tool(
            name="launch_get_status",
            description="Get current status and progress of a run. Returns state, section_states, open_issues, and artifacts.",
            inputSchema={
                "type": "object",
                "properties": {
                    "run_id": {
                        "type": "string",
                        "description": "Run identifier (format: r_YYYY-MM-DDTHH-MM-SSZ_xxxx)"
                    }
                },
                "required": ["run_id"]
            }
        ),

        # launch_list_runs: List all runs
        types.Tool(
            name="launch_list_runs",
            description="List all runs with optional filtering by product_slug or state.",
            inputSchema={
                "type": "object",
                "properties": {
                    "filter": {
                        "type": "object",
                        "description": "Optional filter criteria",
                        "properties": {
                            "product_slug": {
                                "type": "string",
                                "description": "Filter by product slug"
                            },
                            "state": {
                                "type": "string",
                                "description": "Filter by run state"
                            }
                        }
                    }
                },
                "required": []
            }
        ),

        # launch_get_artifact: Retrieve run artifact
        types.Tool(
            name="launch_get_artifact",
            description="Retrieve a specific artifact from a run by name (e.g., page_plan.json, validation_report.json).",
            inputSchema={
                "type": "object",
                "properties": {
                    "run_id": {
                        "type": "string",
                        "description": "Run identifier"
                    },
                    "artifact_name": {
                        "type": "string",
                        "description": "Name of artifact to retrieve (e.g., page_plan.json)"
                    }
                },
                "required": ["run_id", "artifact_name"]
            }
        ),

        # launch_validate: Run validation gates
        types.Tool(
            name="launch_validate",
            description="Run validation gates (W7) for the current worktree state. Returns validation_report.",
            inputSchema={
                "type": "object",
                "properties": {
                    "run_id": {
                        "type": "string",
                        "description": "Run identifier"
                    }
                },
                "required": ["run_id"]
            }
        ),

        # launch_cancel: Cancel a run
        types.Tool(
            name="launch_cancel",
            description="Cancel a running launch task. Returns cancelled status.",
            inputSchema={
                "type": "object",
                "properties": {
                    "run_id": {
                        "type": "string",
                        "description": "Run identifier to cancel"
                    }
                },
                "required": ["run_id"]
            }
        ),

        # launch_resume: Resume a paused run
        types.Tool(
            name="launch_resume",
            description="Resume a paused or partial run from snapshot. Continues until next stable boundary.",
            inputSchema={
                "type": "object",
                "properties": {
                    "run_id": {
                        "type": "string",
                        "description": "Run identifier to resume"
                    }
                },
                "required": ["run_id"]
            }
        ),

        # launch_fix_next: Apply fix to next issue
        types.Tool(
            name="launch_fix_next",
            description="Select next fixable issue deterministically and apply fix attempt (W8), then re-validate.",
            inputSchema={
                "type": "object",
                "properties": {
                    "run_id": {
                        "type": "string",
                        "description": "Run identifier"
                    }
                },
                "required": ["run_id"]
            }
        ),

        # launch_open_pr: Open pull request
        types.Tool(
            name="launch_open_pr",
            description="Open a pull request using the commit service. Requires run state READY_FOR_PR.",
            inputSchema={
                "type": "object",
                "properties": {
                    "run_id": {
                        "type": "string",
                        "description": "Run identifier"
                    }
                },
                "required": ["run_id"]
            }
        ),

        # launch_start_run_from_product_url: Quickstart from URL
        types.Tool(
            name="launch_start_run_from_product_url",
            description="Quickstart: Start a run by providing an Aspose product page URL. System derives run_config automatically.",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "Aspose product page URL (e.g., https://products.aspose.org/3d/en/python/)"
                    },
                    "idempotency_key": {
                        "type": "string",
                        "description": "Optional stable string for idempotent run creation"
                    }
                },
                "required": ["url"]
            }
        ),

        # launch_start_run_from_github_repo_url: Quickstart from GitHub
        types.Tool(
            name="launch_start_run_from_github_repo_url",
            description="Quickstart: Start a run from a GitHub repository URL. System infers product family and platform.",
            inputSchema={
                "type": "object",
                "properties": {
                    "github_repo_url": {
                        "type": "string",
                        "description": "GitHub repository URL (e.g., https://github.com/aspose-3d/Aspose.3D-for-Python-via-.NET)"
                    },
                    "idempotency_key": {
                        "type": "string",
                        "description": "Optional stable string for idempotent run creation"
                    }
                },
                "required": ["github_repo_url"]
            }
        ),

        # get_run_telemetry: Retrieve telemetry data
        types.Tool(
            name="get_run_telemetry",
            description="Retrieve telemetry data for a specific run via MCP protocol.",
            inputSchema={
                "type": "object",
                "properties": {
                    "run_id": {
                        "type": "string",
                        "description": "Run identifier (format: YYYYMMDD-HHMM)",
                        "pattern": "^[0-9]{8}-[0-9]{4}$"
                    }
                },
                "required": ["run_id"]
            }
        ),
    ]


# Tool handler implementations
# Real implementations from handlers.py (TC-512)
# Replaces TC-511 stubs with orchestrator-integrated handlers

from .handlers import (
    handle_launch_start_run,
    handle_launch_get_status,
    handle_launch_list_runs,
    handle_launch_get_artifact,
    handle_launch_validate,
    handle_launch_cancel,
    handle_launch_resume,
    handle_launch_fix_next,
    handle_launch_open_pr,
    handle_launch_start_run_from_product_url,
    handle_launch_start_run_from_github_repo_url,
    handle_get_run_telemetry,
)


# Tool handler registry mapping tool names to handler functions
TOOL_HANDLERS = {
    "launch_start_run": handle_launch_start_run,
    "launch_get_status": handle_launch_get_status,
    "launch_list_runs": handle_launch_list_runs,
    "launch_get_artifact": handle_launch_get_artifact,
    "launch_validate": handle_launch_validate,
    "launch_cancel": handle_launch_cancel,
    "launch_resume": handle_launch_resume,
    "launch_fix_next": handle_launch_fix_next,
    "launch_open_pr": handle_launch_open_pr,
    "launch_start_run_from_product_url": handle_launch_start_run_from_product_url,
    "launch_start_run_from_github_repo_url": handle_launch_start_run_from_github_repo_url,
    "get_run_telemetry": handle_get_run_telemetry,
}
