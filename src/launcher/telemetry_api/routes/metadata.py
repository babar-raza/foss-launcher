"""Metadata and metrics endpoints for telemetry API."""

import logging
import time
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .database import TelemetryDatabase

logger = logging.getLogger(__name__)

router = APIRouter()

_db: Optional[TelemetryDatabase] = None

_metadata_cache: Optional[Dict[str, Any]] = None
_metadata_cache_time: float = 0
METADATA_CACHE_TTL = 300  # 5 minutes


class MetadataResponse(BaseModel):
    """Response model for GET /api/v1/metadata."""

    agent_names: list[str] = Field(
        ..., description="Distinct agent names in the database"
    )
    job_types: list[str] = Field(..., description="Distinct job types in the database")
    counts: Dict[str, int] = Field(
        ..., description="Count of unique agent_names and job_types"
    )
    cache_hit: bool = Field(
        ..., description="True if result was served from cache"
    )


class MetricsResponse(BaseModel):
    """Response model for GET /metrics."""

    total_runs: int = Field(..., description="Total number of runs in the database")
    agents: Dict[str, int] = Field(..., description="Count of runs by agent name")
    recent_24h: int = Field(..., description="Number of runs in the last 24 hours")
    performance: Dict[str, str] = Field(..., description="Database performance info")


def init_database(db: TelemetryDatabase) -> None:
    """Initialize database connection for metadata endpoints."""
    global _db
    _db = db


def invalidate_metadata_cache() -> None:
    """Invalidate metadata cache (called when new runs are created)."""
    global _metadata_cache, _metadata_cache_time
    _metadata_cache = None
    _metadata_cache_time = 0


@router.get("/api/v1/metadata", response_model=MetadataResponse, tags=["Metadata"])
def get_metadata() -> MetadataResponse:
    """Get metadata about the telemetry database."""
    global _metadata_cache, _metadata_cache_time

    if _db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")

    current_time = time.time()
    cache_hit = False

    if _metadata_cache is not None and (current_time - _metadata_cache_time) < METADATA_CACHE_TTL:
        cache_hit = True
        metadata = _metadata_cache
    else:
        try:
            metadata = _db.get_metadata()
            _metadata_cache = metadata
            _metadata_cache_time = current_time
        except Exception as e:
            logger.error(f"Failed to query metadata: {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to query metadata: {str(e)}"
            )

    return MetadataResponse(
        agent_names=metadata["agent_names"],
        job_types=metadata["job_types"],
        counts=metadata["counts"],
        cache_hit=cache_hit,
    )


@router.get("/metrics", response_model=MetricsResponse, tags=["Metrics"])
def get_metrics() -> MetricsResponse:
    """Get system-level metrics."""
    if _db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")

    try:
        metrics = _db.get_metrics()
        return MetricsResponse(
            total_runs=metrics["total_runs"],
            agents=metrics["agents"],
            recent_24h=metrics["recent_24h"],
            performance=metrics["performance"],
        )
    except Exception as e:
        logger.error(f"Failed to query metrics: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to query metrics: {str(e)}"
        )
