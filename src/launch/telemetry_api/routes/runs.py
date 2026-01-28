"""Run management endpoints for telemetry API (TC-521).

Binding contract: specs/16_local_telemetry_api.md (Local Telemetry API)

Implements:
- POST /api/v1/runs - Create new run record
- GET /api/v1/runs - List runs with filtering/pagination
- GET /api/v1/runs/{run_id} - Get run details
- PATCH /api/v1/runs/{run_id} - Update run metadata
- GET /api/v1/runs/{run_id}/events - Stream events for run
- POST /api/v1/runs/{event_id}/associate-commit - Associate commit with run
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Path as PathParam
from fastapi.responses import JSONResponse

from .models import (
    CreateRunRequest,
    UpdateRunRequest,
    AssociateCommitRequest,
    RunResponse,
    ListRunsResponse,
    EventResponse,
    ErrorResponse,
)
from .database import TelemetryDatabase

logger = logging.getLogger(__name__)

# Router instance (will be registered in server.py)
router = APIRouter(prefix="/api/v1/runs", tags=["Runs"])

# Global database instance (will be initialized in server.py)
_db: Optional[TelemetryDatabase] = None


def init_database(db: TelemetryDatabase) -> None:
    """Initialize the database instance.

    Args:
        db: TelemetryDatabase instance
    """
    global _db
    _db = db


def get_db() -> TelemetryDatabase:
    """Get database instance.

    Returns:
        TelemetryDatabase instance

    Raises:
        RuntimeError: If database not initialized
    """
    if _db is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    return _db


@router.post("", response_model=RunResponse, status_code=201)
async def create_run(request: CreateRunRequest) -> RunResponse:
    """Create a new run record (POST /api/v1/runs).

    This endpoint creates a new telemetry run with idempotent semantics.
    If a run with the same event_id already exists, returns the existing run.

    Args:
        request: CreateRunRequest with run details

    Returns:
        RunResponse with created/existing run data

    Raises:
        HTTPException: 500 on database error
    """
    try:
        db = get_db()
        run_data = request.model_dump(exclude_none=False)
        result = db.create_run(run_data)

        logger.info(
            f"run_created: event_id={request.event_id}, run_id={request.run_id}, job_type={request.job_type}"
        )

        return RunResponse(**result)

    except Exception as e:
        logger.error(f"create_run_failed: {e} (event_id={request.event_id})")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create run: {str(e)}",
        )


@router.get("", response_model=ListRunsResponse)
async def list_runs(
    limit: int = Query(100, ge=1, le=1000, description="Max results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    status: Optional[str] = Query(None, description="Filter by status"),
    job_type: Optional[str] = Query(None, description="Filter by job_type"),
    parent_run_id: Optional[str] = Query(None, description="Filter by parent_run_id"),
    product: Optional[str] = Query(None, description="Filter by product"),
) -> ListRunsResponse:
    """List runs with filtering and pagination (GET /api/v1/runs).

    Supports filtering by status, job_type, parent_run_id, and product.
    Results are paginated using limit/offset and ordered by start_time DESC.

    Args:
        limit: Max results to return (1-1000, default 100)
        offset: Number of results to skip (default 0)
        status: Optional status filter
        job_type: Optional job_type filter
        parent_run_id: Optional parent_run_id filter
        product: Optional product filter

    Returns:
        ListRunsResponse with runs array and pagination metadata

    Raises:
        HTTPException: 500 on database error
    """
    try:
        db = get_db()
        runs, total = db.list_runs(
            limit=limit,
            offset=offset,
            status=status,
            job_type=job_type,
            parent_run_id=parent_run_id,
            product=product,
        )

        logger.info(
            f"runs_listed: total={total}, limit={limit}, offset={offset}, status={status}, job_type={job_type}"
        )

        return ListRunsResponse(
            runs=[RunResponse(**run) for run in runs],
            total=total,
            limit=limit,
            offset=offset,
        )

    except Exception as e:
        logger.error(f"list_runs_failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list runs: {str(e)}",
        )


@router.get("/{run_id}", response_model=RunResponse)
async def get_run(
    run_id: str = PathParam(..., description="Run identifier"),
) -> RunResponse:
    """Get run details by run_id (GET /api/v1/runs/{run_id}).

    Returns the most recent run record for the given run_id.

    Args:
        run_id: Run identifier

    Returns:
        RunResponse with run details

    Raises:
        HTTPException: 404 if run not found, 500 on database error
    """
    try:
        db = get_db()
        result = db.get_run_by_id(run_id)

        if result is None:
            logger.warning(f"run_not_found: run_id={run_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Run not found: {run_id}",
            )

        logger.info(f"run_retrieved: run_id={run_id}")
        return RunResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_run_failed: {e} (run_id={run_id})")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get run: {str(e)}",
        )


@router.patch("/{event_id}", response_model=RunResponse)
async def update_run(
    event_id: str = PathParam(..., description="Event identifier"),
    request: UpdateRunRequest = ...,
) -> RunResponse:
    """Update run metadata (PATCH /api/v1/runs/{event_id}).

    Updates the run record identified by event_id with the provided fields.
    Only fields present in the request are updated.

    Args:
        event_id: Event identifier
        request: UpdateRunRequest with fields to update

    Returns:
        RunResponse with updated run data

    Raises:
        HTTPException: 404 if run not found, 400 for invalid input, 500 on database error
    """
    try:
        db = get_db()

        # Build update data (exclude None values)
        update_data = request.model_dump(exclude_none=True)

        if not update_data:
            # No fields to update
            result = db.get_run_by_event_id(event_id)
            if result is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"Run not found: {event_id}",
                )
            return RunResponse(**result)

        result = db.update_run(event_id, update_data)

        if result is None:
            logger.warning(f"run_not_found_for_update: event_id={event_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Run not found: {event_id}",
            )

        logger.info(f"run_updated: event_id={event_id}, updated_fields={list(update_data.keys())}")
        return RunResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"update_run_failed: {e} (event_id={event_id})")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update run: {str(e)}",
        )


@router.get("/{run_id}/events", response_model=list[EventResponse])
async def get_run_events(
    run_id: str = PathParam(..., description="Run identifier"),
) -> list[EventResponse]:
    """Stream events for a run (GET /api/v1/runs/{run_id}/events).

    Returns all events associated with the given run_id, ordered by timestamp.

    Args:
        run_id: Run identifier

    Returns:
        List of EventResponse objects

    Raises:
        HTTPException: 404 if run not found, 500 on database error
    """
    try:
        db = get_db()

        # Check if run exists
        run = db.get_run_by_id(run_id)
        if run is None:
            logger.warning(f"run_not_found_for_events: run_id={run_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Run not found: {run_id}",
            )

        # Get events
        events = db.get_events_for_run(run_id)

        logger.info(f"events_retrieved: run_id={run_id}, event_count={len(events)}")
        return [EventResponse(**event) for event in events]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_events_failed: {e} (run_id={run_id})")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get events: {str(e)}",
        )


@router.post("/{event_id}/associate-commit", response_model=RunResponse)
async def associate_commit(
    event_id: str = PathParam(..., description="Event identifier"),
    request: AssociateCommitRequest = ...,
) -> RunResponse:
    """Associate commit with run (POST /api/v1/runs/{event_id}/associate-commit).

    Associates a git commit with the run identified by event_id.

    Args:
        event_id: Event identifier
        request: AssociateCommitRequest with commit details

    Returns:
        RunResponse with updated run data

    Raises:
        HTTPException: 404 if run not found, 400 for invalid commit hash, 500 on database error
    """
    try:
        db = get_db()

        # Validate commit_hash length (7-40 chars)
        if not (7 <= len(request.commit_hash) <= 40):
            raise HTTPException(
                status_code=400,
                detail="Invalid commit_hash: must be 7-40 characters",
            )

        # Validate commit_source
        if request.commit_source not in ["manual", "llm", "ci"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid commit_source: must be one of: manual, llm, ci",
            )

        result = db.associate_commit(
            event_id=event_id,
            commit_hash=request.commit_hash,
            commit_source=request.commit_source,
            commit_author=request.commit_author,
            commit_timestamp=request.commit_timestamp,
        )

        if result is None:
            logger.warning(f"run_not_found_for_commit: event_id={event_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Run not found: {event_id}",
            )

        logger.info(
            f"commit_associated: event_id={event_id}, commit_hash={request.commit_hash}, commit_source={request.commit_source}"
        )

        return RunResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"associate_commit_failed: {e} (event_id={event_id})")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to associate commit: {str(e)}",
        )
