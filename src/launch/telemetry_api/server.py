"""
Local Telemetry API HTTP Server (TC-520).

Implements a FastAPI HTTP server for telemetry access per specs/16_local_telemetry_api.md.
Server listens on localhost:8765 (configurable) with CORS enabled for localhost development.

This module provides the server architecture only. Full endpoint implementation
will be added in subsequent taskcards as referenced in the spec.
"""

import logging
import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from .routes.database import TelemetryDatabase
from .routes import runs

# Configure logger
logger = logging.getLogger(__name__)


class ServerConfig(BaseModel):
    """Configuration for the telemetry API server."""

    host: str = "127.0.0.1"
    port: int = 8765
    log_level: str = "info"
    cors_origins: list[str] = ["http://localhost:*", "http://127.0.0.1:*"]
    workers: int = 1  # Single worker for SQLite (as per spec note)
    db_path: str = "./telemetry.db"  # SQLite database path


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    version: str


def create_app(config: Optional[ServerConfig] = None) -> FastAPI:
    """
    Create and configure the FastAPI application.

    Args:
        config: Optional server configuration. If not provided, uses defaults.

    Returns:
        Configured FastAPI application instance.
    """
    if config is None:
        config = ServerConfig()

    app = FastAPI(
        title="Local Telemetry API",
        description="HTTP API for telemetry access and accountability",
        version="2.2.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Configure CORS for localhost development
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
    logger.info(f"Database initialized at: {db_path}")

    # Register routers
    app.include_router(runs.router)
    logger.info("Run endpoints registered")

    # Health check endpoint (GET /health)
    @app.get("/health", response_model=HealthResponse, tags=["System"])
    def health_check() -> HealthResponse:
        """
        Health check endpoint.

        Returns service status and version. This endpoint is always available
        and does not require authentication.
        """
        return HealthResponse(status="ok", version="2.2.0")

    logger.info("Telemetry API application created (version 2.2.0)")
    return app


def start_telemetry_server(
    host: str = "127.0.0.1",
    port: int = 8765,
    log_level: str = "info",
    reload: bool = False,
) -> None:
    """
    Start the telemetry HTTP server.

    This is the main entry point for launching the telemetry API server.
    Server listens on localhost by default (configurable via host/port).

    Args:
        host: Host address to bind to (default: 127.0.0.1)
        port: Port to bind to (default: 8765)
        log_level: Logging level (default: info)
        reload: Enable auto-reload for development (default: False)

    Raises:
        OSError: If the port is already in use
        RuntimeError: If server configuration is invalid

    Example:
        >>> from launch.telemetry_api import start_telemetry_server
        >>> start_telemetry_server(host="127.0.0.1", port=8765)
    """
    # Validate configuration
    if not 1 <= port <= 65535:
        raise ValueError(f"Invalid port number: {port}. Must be between 1 and 65535.")

    if log_level not in ["critical", "error", "warning", "info", "debug"]:
        raise ValueError(
            f"Invalid log level: {log_level}. Must be one of: critical, error, warning, info, debug."
        )

    # Configure logging
    logging.basicConfig(
        level=log_level.upper(),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logger.info(f"Starting Local Telemetry API server on {host}:{port}")
    logger.info(f"Log level: {log_level}")
    logger.info("Health check available at: GET /health")
    logger.info(f"API documentation: http://{host}:{port}/docs")

    # Create server configuration
    config = ServerConfig(
        host=host,
        port=port,
        log_level=log_level,
    )

    try:
        # Run the server using uvicorn
        uvicorn.run(
            "launch.telemetry_api.server:create_app",
            host=config.host,
            port=config.port,
            log_level=config.log_level,
            reload=reload,
            factory=True,  # Use factory pattern to create app
            workers=config.workers,
        )
    except OSError as e:
        if "address already in use" in str(e).lower():
            logger.error(f"Port {port} is already in use. Please choose a different port.")
            raise OSError(f"Port {port} is already in use") from e
        raise
    except Exception as e:
        logger.error(f"Failed to start telemetry server: {e}")
        raise RuntimeError(f"Failed to start telemetry server: {e}") from e


def get_server_config_from_env() -> ServerConfig:
    """
    Load server configuration from environment variables.

    Environment variables:
        TELEMETRY_API_HOST: Host address (default: 127.0.0.1)
        TELEMETRY_API_PORT: Port number (default: 8765)
        TELEMETRY_LOG_LEVEL: Log level (default: info)
        TELEMETRY_DB_PATH: Database path (default: ./telemetry.db)

    Returns:
        ServerConfig with values from environment or defaults.
    """
    host = os.getenv("TELEMETRY_API_HOST", "127.0.0.1")
    port = int(os.getenv("TELEMETRY_API_PORT", "8765"))
    log_level = os.getenv("TELEMETRY_LOG_LEVEL", "info")
    db_path = os.getenv("TELEMETRY_DB_PATH", "./telemetry.db")

    return ServerConfig(host=host, port=port, log_level=log_level, db_path=db_path)


# CLI entry point (if run directly)
if __name__ == "__main__":
    config = get_server_config_from_env()
    start_telemetry_server(
        host=config.host,
        port=config.port,
        log_level=config.log_level,
    )
