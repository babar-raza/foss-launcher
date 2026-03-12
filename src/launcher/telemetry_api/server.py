"""
Local Telemetry API HTTP Server.

Implements a FastAPI HTTP server for telemetry access per specs/16_local_telemetry_api.md.
Server listens on localhost:8765 (configurable) with CORS enabled for localhost development.
"""

import logging
import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from launcher.provenance import ENGINE_VERSION

from .routes.database import TelemetryDatabase
from .routes import runs, batch, metadata

logger = logging.getLogger(__name__)

_API_VERSION = ENGINE_VERSION


class ServerConfig(BaseModel):
    """Configuration for the telemetry API server."""

    host: str = "127.0.0.1"
    port: int = 8765
    log_level: str = "info"
    cors_origins: list[str] = ["http://localhost:*", "http://127.0.0.1:*"]
    workers: int = 1  # Single worker for SQLite (as per spec note)
    db_path: str = "./telemetry.db"


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    version: str


def create_app(config: Optional[ServerConfig] = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    if config is None:
        config = ServerConfig()

    app = FastAPI(
        title="Local Telemetry API",
        description="HTTP API for telemetry access and accountability",
        version=_API_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Initialize database
    db_path = Path(config.db_path)
    db = TelemetryDatabase(db_path)
    runs.init_database(db)
    batch.init_database(db)
    metadata.init_database(db)
    logger.info(f"Database initialized at: {db_path}")

    # Set up cache invalidation for metadata endpoint
    runs.set_cache_invalidator(metadata.invalidate_metadata_cache)

    # Register routers
    app.include_router(runs.router)
    app.include_router(batch.router)
    app.include_router(metadata.router)

    @app.get("/health", response_model=HealthResponse, tags=["System"])
    def health_check() -> HealthResponse:
        """Health check endpoint."""
        return HealthResponse(status="ok", version=_API_VERSION)

    logger.info(f"Telemetry API application created (version {_API_VERSION})")
    return app


def start_telemetry_server(
    host: str = "127.0.0.1",
    port: int = 8765,
    log_level: str = "info",
    reload: bool = False,
) -> None:
    """Start the telemetry HTTP server."""
    if not 1 <= port <= 65535:
        raise ValueError(f"Invalid port number: {port}. Must be between 1 and 65535.")

    if log_level not in ["critical", "error", "warning", "info", "debug"]:
        raise ValueError(
            f"Invalid log level: {log_level}. Must be one of: critical, error, warning, info, debug."
        )

    logging.basicConfig(
        level=log_level.upper(),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logger.info(f"Starting Local Telemetry API server on {host}:{port}")

    config = ServerConfig(host=host, port=port, log_level=log_level)

    try:
        uvicorn.run(
            "launcher.telemetry_api.server:create_app",
            host=config.host,
            port=config.port,
            log_level=config.log_level,
            reload=reload,
            factory=True,
            workers=config.workers,
        )
    except OSError as e:
        if "address already in use" in str(e).lower():
            logger.error(f"Port {port} is already in use.")
            raise OSError(f"Port {port} is already in use") from e
        raise
    except Exception as e:
        logger.error(f"Failed to start telemetry server: {e}")
        raise RuntimeError(f"Failed to start telemetry server: {e}") from e


def get_server_config_from_env() -> ServerConfig:
    """Load server configuration from environment variables."""
    host = os.getenv("TELEMETRY_API_HOST", "127.0.0.1")
    port = int(os.getenv("TELEMETRY_API_PORT", "8765"))
    log_level = os.getenv("TELEMETRY_LOG_LEVEL", "info")
    db_path = os.getenv("TELEMETRY_DB_PATH", "./telemetry.db")

    return ServerConfig(host=host, port=port, log_level=log_level, db_path=db_path)


if __name__ == "__main__":
    config = get_server_config_from_env()
    start_telemetry_server(
        host=config.host,
        port=config.port,
        log_level=config.log_level,
    )
