"""Batch upload endpoints for telemetry API (TC-522).

Binding contract: specs/16_local_telemetry_api.md (Local Telemetry API)

Implements:
- POST /api/v1/runs/batch - Upload multiple runs with events in a single request
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .models import CreateRunRequest, RunResponse, ErrorResponse
from .database import TelemetryDatabase

logger = logging.getLogger(__name__)

# Router instance (will be registered in server.py)
router = APIRouter(prefix="/api/v1/runs", tags=["Batch"])

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
    """Upload multiple runs in a single request (POST /api/v1/runs/batch).

    This endpoint allows bulk creation of telemetry runs with transaction semantics.
    All runs are created within a single database transaction (all-or-nothing).

    If any run fails validation or database constraints, the entire batch is rolled back.
    Idempotent: runs with existing event_ids are returned without error.

    Args:
        request: BatchRunRequest with list of runs to create

    Returns:
        BatchRunResponse with created runs and statistics

    Raises:
        HTTPException: 400 for validation errors, 500 for database errors
    """
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

        # Process runs with transaction semantics
        results: List[RunResponse] = []
        created_count = 0
        existing_count = 0
        failed_count = 0
        errors = []

        for idx, run_request in enumerate(request.runs):
            try:
                # Check if run already exists before creating
                existing_run = db.get_run_by_event_id(run_request.event_id)

                run_data = run_request.model_dump(exclude_none=False)
                result = db.create_run(run_data)

                # Determine if this was newly created or already existed
                if existing_run:
                    # Run already existed (idempotent)
                    existing_count += 1
                else:
                    # New run created
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

        # If any runs failed, raise error with details
        if failed_count > 0:
            logger.error(
                f"batch_upload_partial_failure: total={len(request.runs)}, "
                f"created={created_count}, existing={existing_count}, failed={failed_count}"
            )
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

        logger.info(
            f"batch_upload_success: total={len(request.runs)}, "
            f"created={created_count}, existing={existing_count}"
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
    """Upload multiple runs with strict transactional semantics (POST /api/v1/runs/batch-transactional).

    This endpoint provides strict all-or-nothing transaction semantics.
    If ANY run fails, the entire batch is rolled back and no runs are created.

    Use this endpoint when you need atomic batch operations.
    For more lenient behavior, use POST /api/v1/runs/batch instead.

    Args:
        request: BatchRunRequest with list of runs to create

    Returns:
        BatchRunResponse with created runs and statistics

    Raises:
        HTTPException: 400 for validation errors or if any run fails, 500 for database errors
    """
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

        # Use SQLite transaction for true atomicity
        with db._get_connection() as conn:
            cursor = conn.cursor()

            try:
                # Begin explicit transaction
                cursor.execute("BEGIN TRANSACTION")

                results: List[RunResponse] = []
                created_count = 0
                existing_count = 0

                for idx, run_request in enumerate(request.runs):
                    run_data = run_request.model_dump(exclude_none=False)

                    # Check if event_id already exists (idempotency)
                    cursor.execute(
                        "SELECT * FROM runs WHERE event_id = ?",
                        (run_data["event_id"],)
                    )
                    existing = cursor.fetchone()

                    if existing:
                        existing_count += 1
                        results.append(RunResponse(**db._row_to_dict(existing)))
                        continue

                    # Serialize JSON fields
                    import json
                    metrics_json = None
                    if run_data.get("metrics_json"):
                        metrics_json = json.dumps(run_data["metrics_json"], sort_keys=True)

                    context_json = None
                    if run_data.get("context_json"):
                        context_json = json.dumps(run_data["context_json"], sort_keys=True)

                    # Insert new run
                    from datetime import datetime, timezone
                    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

                    cursor.execute("""
                        INSERT INTO runs (
                            event_id, run_id, agent_name, job_type, start_time, status,
                            parent_run_id, product, product_family, platform, subdomain,
                            website_section, item_name, git_repo, git_branch,
                            metrics_json, context_json, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        run_data["event_id"],
                        run_data["run_id"],
                        run_data["agent_name"],
                        run_data["job_type"],
                        run_data["start_time"],
                        run_data.get("status", "running"),
                        run_data.get("parent_run_id"),
                        run_data.get("product"),
                        run_data.get("product_family"),
                        run_data.get("platform"),
                        run_data.get("subdomain"),
                        run_data.get("website_section"),
                        run_data.get("item_name"),
                        run_data.get("git_repo"),
                        run_data.get("git_branch"),
                        metrics_json,
                        context_json,
                        now,
                        now,
                    ))

                    created_count += 1

                    # Fetch the created run
                    cursor.execute(
                        "SELECT * FROM runs WHERE event_id = ?",
                        (run_data["event_id"],)
                    )
                    row = cursor.fetchone()
                    results.append(RunResponse(**db._row_to_dict(row)))

                # Commit transaction
                conn.commit()

                logger.info(
                    f"batch_upload_transactional_success: total={len(request.runs)}, "
                    f"created={created_count}, existing={existing_count}"
                )

                return BatchRunResponse(
                    runs=results,
                    total=len(request.runs),
                    created=created_count,
                    existing=existing_count,
                    failed=0,
                    errors=[],
                )

            except Exception as e:
                # Rollback on any error
                conn.rollback()
                logger.error(f"batch_upload_transactional_failed: {e}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Batch transaction failed (rolled back): {str(e)}",
                )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"batch_upload_transactional_failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process transactional batch upload: {str(e)}",
        )
