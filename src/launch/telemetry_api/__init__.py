"""
Local Telemetry API package (TC-520).

This package implements the HTTP server for local telemetry access
per specs/16_local_telemetry_api.md.

Main entry point:
    start_telemetry_server() - Start the telemetry HTTP server

Configuration utilities:
    ServerConfig - Server configuration model
    get_server_config_from_env() - Load config from environment
    create_app() - Create FastAPI application instance
"""

from launch.telemetry_api.server import (
    ServerConfig,
    create_app,
    get_server_config_from_env,
    start_telemetry_server,
)

__all__ = [
    "start_telemetry_server",
    "ServerConfig",
    "create_app",
    "get_server_config_from_env",
]
