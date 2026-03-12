"""Run management endpoints for telemetry API."""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Path as PathParam

from .models import (
    CreateRunRequest,
    UpdateRunRequest,
    AssociateCommitRequest,
    RunResponse,
    ListRunsResponse,
    EventResponse,
)
from .database import TelemetryDatabase

_invalidate_metadata_cache = None


def set_cache_invalidator(invalidator_func):
    """Set the metadata cache invalidation function."""
    global _invalidate_metadata_cache
    _invalidate_metadata_cache = invalidator_func

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/runs", tags=["Runs"])

_db: Optional[TelemetryDatabase] = None


def init_database(db: TelemetryDatabase) -> None:
    """Initialize the database instance."""
    global _db
    _db = db


def get_db() -> TelemetryDatabase:
    """Get database instance."""
    if _db is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    return _db


@router.post("", response_model=RunResponse, status_code=201)
async def create_run(request: CreateRunRequest) -> RunResponse:
    """Create a new run record (POST /api/v1/runs)."""
    try:
        db = get_db()
        run_data = request.model_dump(exclude_none=False)
        result = db.create_run(run_data)

        if _invalidate_metadata_cache:
            _invalidate_metadata_cache()

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
    """List runs with filtering and pagination (GET /api/v1/runs)."""
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
    """Get run details by run_id (GET /api/v1/runs/{run_id})."""
    try:
        db = get_db()
        result = db.get_run_by_id(run_id)

        if result is None:
            raise HTTPException(
                status_code=404,
                detail=f"Run not found: {run_id}",
            )

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
    """Update run metadata (PATCH /api/v1/runs/{event_id})."""
    try:
        db = get_db()

        update_data = request.model_dump(exclude_none=True)

        if not update_data:
            result = db.get_run_by_event_id(event_id)
            if result is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"Run not found: {event_id}",
                )
            return RunResponse(**result)

        result = db.update_run(event_id, update_data)

        if result is None:
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
    """Stream events for a run (GET /api/v1/runs/{run_id}/events)."""
    try:
        db = get_db()

        run = db.get_run_by_id(run_id)
        if run is None:
            raise HTTPException(
                status_code=404,
                detail=f"Run not found: {run_id}",
            )

        events = db.get_events_for_run(run_id)

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
    """Associate commit with run (POST /api/v1/runs/{event_id}/associate-commit)."""
    try:
        db = get_db()

        if not (7 <= len(request.commit_hash) <= 40):
            raise HTTPException(
                status_code=400,
                detail="Invalid commit_hash: must be 7-40 characters",
            )

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
            raise HTTPException(
                status_code=404,
                detail=f"Run not found: {event_id}",
            )

        logger.info(
            f"commit_associated: event_id={event_id}, commit_hash={request.commit_hash}"
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
