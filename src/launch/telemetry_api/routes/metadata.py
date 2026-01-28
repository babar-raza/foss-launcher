"""Metadata and metrics endpoints for telemetry API (TC-523).

Binding contract: specs/16_local_telemetry_api.md, docs/reference/local-telemetry.md

Implements:
- GET /api/v1/metadata - Returns distinct agent names and job types
- GET /metrics - Returns system-level metrics (Prometheus-style)
"""

import logging
import time
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .database import TelemetryDatabase

# Configure logger
logger = logging.getLogger(__name__)

# Router for metadata endpoints
router = APIRouter()

# Database instance (initialized by server)
_db: Optional[TelemetryDatabase] = None

# Simple in-memory cache for metadata (5 minute TTL as per spec)
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
        ..., description="True if result was served from cache, false if freshly queried"
    )


class MetricsResponse(BaseModel):
    """Response model for GET /metrics."""

    total_runs: int = Field(..., description="Total number of runs in the database")
    agents: Dict[str, int] = Field(..., description="Count of runs by agent name")
    recent_24h: int = Field(..., description="Number of runs in the last 24 hours")
    performance: Dict[str, str] = Field(..., description="Database performance info")


def init_database(db: TelemetryDatabase) -> None:
    """Initialize database connection for metadata endpoints.

    Args:
        db: TelemetryDatabase instance
    """
    global _db
    _db = db
    logger.info("Metadata endpoints database initialized")


def invalidate_metadata_cache() -> None:
    """Invalidate metadata cache (called when new runs are created)."""
    global _metadata_cache, _metadata_cache_time
    _metadata_cache = None
    _metadata_cache_time = 0
    logger.debug("Metadata cache invalidated")


@router.get("/api/v1/metadata", response_model=MetadataResponse, tags=["Metadata"])
def get_metadata() -> MetadataResponse:
    """
    Get metadata about the telemetry database.

    Returns distinct agent names and job types seen in the database.
    Results are cached for 5 minutes to improve performance on large datasets.
    Cache is automatically invalidated when new runs are created.

    Returns:
        MetadataResponse with agent_names, job_types, counts, and cache_hit flag

    Raises:
        HTTPException: 500 if database query fails
    """
    global _metadata_cache, _metadata_cache_time

    if _db is None:
        logger.error("Database not initialized for metadata endpoint")
        raise HTTPException(status_code=500, detail="Database not initialized")

    # Check cache
    current_time = time.time()
    cache_hit = False

    if _metadata_cache is not None and (current_time - _metadata_cache_time) < METADATA_CACHE_TTL:
        logger.debug("Metadata cache hit")
        cache_hit = True
        metadata = _metadata_cache
    else:
        # Query database
        logger.debug("Metadata cache miss, querying database")
        try:
            metadata = _db.get_metadata()
            # Update cache
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
    """
    Get system-level metrics.

    Returns aggregated metrics including:
    - Total number of runs
    - Count of runs by agent name
    - Number of runs in the last 24 hours
    - Database performance information

    This endpoint is suitable for monitoring and Prometheus-style scraping.

    Returns:
        MetricsResponse with system metrics

    Raises:
        HTTPException: 500 if database query fails
    """
    if _db is None:
        logger.error("Database not initialized for metrics endpoint")
        raise HTTPException(status_code=500, detail="Database not initialized")

    try:
        metrics = _db.get_metrics()
        logger.debug(f"Metrics retrieved: {metrics['total_runs']} total runs")
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
