"""Batch upload endpoints for telemetry API."""

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .models import CreateRunRequest, RunResponse
from .database import TelemetryDatabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/runs", tags=["Batch"])

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


class BatchRunRequest(BaseModel):
    """Request model for batch run creation."""

    runs: List[CreateRunRequest] = Field(
        ...,
        description="List of runs to create",
        min_length=1,
    )


class BatchRunResponse(BaseModel):
    """Response model for batch run creation."""

    runs: List[RunResponse] = Field(..., description="Created/existing runs")
    total: int = Field(..., description="Total number of runs processed")
    created: int = Field(..., description="Number of runs created")
    existing: int = Field(..., description="Number of existing runs (idempotent)")
    failed: int = Field(..., description="Number of failed runs")
    errors: List[dict] = Field(default_factory=list, description="List of errors for failed runs")


@router.post("/batch", response_model=BatchRunResponse, status_code=201)
async def batch_upload(request: BatchRunRequest) -> BatchRunResponse:
    """Upload multiple runs in a single request (POST /api/v1/runs/batch)."""
    if not request.runs:
        raise HTTPException(
            status_code=400,
            detail="Batch request must contain at least one run",
        )

    if len(request.runs) > 1000:
        raise HTTPException(
            status_code=400,
            detail="Batch size exceeds maximum limit of 1000 runs",
        )

    try:
        db = get_db()

        results: List[RunResponse] = []
        created_count = 0
        existing_count = 0
        failed_count = 0
        errors = []

        for idx, run_request in enumerate(request.runs):
            try:
                existing_run = db.get_run_by_event_id(run_request.event_id)

                run_data = run_request.model_dump(exclude_none=False)
                result = db.create_run(run_data)

                if existing_run:
                    existing_count += 1
                else:
                    created_count += 1

                results.append(RunResponse(**result))

            except Exception as e:
                failed_count += 1
                errors.append({
                    "index": idx,
                    "event_id": run_request.event_id,
                    "run_id": run_request.run_id,
                    "error": str(e),
                })
                logger.error(
                    f"batch_run_failed: index={idx}, event_id={run_request.event_id}, error={e}"
                )

        if failed_count > 0:
            raise HTTPException(
                status_code=500,
                detail={
                    "message": f"Batch upload failed for {failed_count} run(s)",
                    "total": len(request.runs),
                    "created": created_count,
                    "existing": existing_count,
                    "failed": failed_count,
                    "errors": errors,
                },
            )

        return BatchRunResponse(
            runs=results,
            total=len(request.runs),
            created=created_count,
            existing=existing_count,
            failed=failed_count,
            errors=errors,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"batch_upload_failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process batch upload: {str(e)}",
        )


@router.post("/batch-transactional", response_model=BatchRunResponse, status_code=201)
async def batch_upload_transactional(request: BatchRunRequest) -> BatchRunResponse:
    """Upload multiple runs with strict transactional semantics."""
    if not request.runs:
        raise HTTPException(
            status_code=400,
            detail="Batch request must contain at least one run",
        )

    if len(request.runs) > 1000:
        raise HTTPException(
            status_code=400,
            detail="Batch size exceeds maximum limit of 1000 runs",
        )

    try:
        db = get_db()
        run_data_list = [r.model_dump(exclude_none=False) for r in request.runs]

        results, created_count, existing_count = db.batch_create_runs(
            run_data_list, transactional=True
        )

        return BatchRunResponse(
            runs=[RunResponse(**r) for r in results],
            total=len(request.runs),
            created=created_count,
            existing=existing_count,
            failed=0,
            errors=[],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"batch_upload_transactional_failed: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Batch transaction failed (rolled back): {str(e)}",
        )
