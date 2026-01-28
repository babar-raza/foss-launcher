"""Pydantic models for telemetry API run endpoints.

Binding contract: specs/16_local_telemetry_api.md (Local Telemetry API)
"""

from typing import Any, Dict, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class CreateRunRequest(BaseModel):
    """Request model for POST /api/v1/runs."""

    event_id: str = Field(..., description="UUIDv4 idempotency key")
    run_id: str = Field(..., description="Stable run identifier")
    agent_name: str = Field(..., description="Agent name (e.g., launch.orchestrator)")
    job_type: str = Field(
        ...,
        description="Job type (launch, orchestrator_node, worker, gate, llm_call, commit_service)",
    )
    start_time: str = Field(..., description="ISO8601 timestamp with timezone")
    status: str = Field(
        default="running",
        description="Status (running, success, failure, partial, timeout, cancelled)",
    )
    parent_run_id: Optional[str] = Field(None, description="Parent run_id for child runs")
    product: Optional[str] = Field(None, description="Product slug")
    product_family: Optional[str] = Field(None, description="Product family")
    platform: Optional[str] = Field(None, description="Platform")
    subdomain: Optional[str] = Field(None, description="Subdomain")
    website_section: Optional[str] = Field(None, description="Website section")
    item_name: Optional[str] = Field(None, description="Item name")
    git_repo: Optional[str] = Field(None, description="Git repo URL")
    git_branch: Optional[str] = Field(None, description="Git branch")
    metrics_json: Optional[Dict[str, Any]] = Field(None, description="Metrics (counters, timings)")
    context_json: Optional[Dict[str, Any]] = Field(
        None, description="Context (trace_id, span_id, hashes)"
    )


class UpdateRunRequest(BaseModel):
    """Request model for PATCH /api/v1/runs/{run_id}."""

    status: Optional[str] = Field(None, description="Status update")
    end_time: Optional[str] = Field(None, description="ISO8601 end timestamp")
    duration_ms: Optional[int] = Field(None, description="Duration in milliseconds")
    items_discovered: Optional[int] = Field(None, description="Items discovered count")
    items_succeeded: Optional[int] = Field(None, description="Items succeeded count")
    items_failed: Optional[int] = Field(None, description="Items failed count")
    items_skipped: Optional[int] = Field(None, description="Items skipped count")
    output_summary: Optional[str] = Field(None, description="Output summary")
    error_summary: Optional[str] = Field(None, description="Error summary")
    metrics_json: Optional[Dict[str, Any]] = Field(None, description="Metrics update")
    context_json: Optional[Dict[str, Any]] = Field(None, description="Context update")


class AssociateCommitRequest(BaseModel):
    """Request model for POST /api/v1/runs/{event_id}/associate-commit."""

    commit_hash: str = Field(..., description="Git commit SHA (7-40 chars)")
    commit_source: str = Field(..., description="Source (manual, llm, ci)")
    commit_author: Optional[str] = Field(None, description="Commit author")
    commit_timestamp: Optional[str] = Field(None, description="ISO8601 commit timestamp")


class RunResponse(BaseModel):
    """Response model for run operations."""

    event_id: str
    run_id: str
    agent_name: str
    job_type: str
    start_time: str
    status: str
    parent_run_id: Optional[str] = None
    product: Optional[str] = None
    product_family: Optional[str] = None
    platform: Optional[str] = None
    subdomain: Optional[str] = None
    website_section: Optional[str] = None
    item_name: Optional[str] = None
    git_repo: Optional[str] = None
    git_branch: Optional[str] = None
    end_time: Optional[str] = None
    duration_ms: Optional[int] = None
    items_discovered: Optional[int] = None
    items_succeeded: Optional[int] = None
    items_failed: Optional[int] = None
    items_skipped: Optional[int] = None
    output_summary: Optional[str] = None
    error_summary: Optional[str] = None
    metrics_json: Optional[Dict[str, Any]] = None
    context_json: Optional[Dict[str, Any]] = None
    commit_hash: Optional[str] = None
    commit_source: Optional[str] = None
    commit_author: Optional[str] = None
    commit_timestamp: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ListRunsResponse(BaseModel):
    """Response model for GET /api/v1/runs (list runs)."""

    runs: list[RunResponse]
    total: int
    limit: int
    offset: int


class EventResponse(BaseModel):
    """Response model for run events (GET /api/v1/runs/{run_id}/events)."""

    event_id: str
    run_id: str
    ts: str
    type: str
    payload: Dict[str, Any]
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    parent_span_id: Optional[str] = None


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str
    details: Optional[Dict[str, Any]] = None
