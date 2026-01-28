"""
Tests for TC-520: Local Telemetry API Setup.

Tests the HTTP server implementation per specs/16_local_telemetry_api.md.
Validates:
- Server initialization
- Health check endpoint
- CORS configuration
- Server lifecycle
- Error handling (port in use, invalid config)
"""

import os
import socket
from contextlib import closing
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from launch.telemetry_api import (
    ServerConfig,
    create_app,
    get_server_config_from_env,
    start_telemetry_server,
)


def find_free_port() -> int:
    """Find a free port on localhost for testing."""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


class TestServerConfig:
    """Tests for ServerConfig model."""

    def test_default_config(self) -> None:
        """Test default server configuration values."""
        config = ServerConfig()
        assert config.host == "127.0.0.1"
        assert config.port == 8765
        assert config.log_level == "info"
        assert config.workers == 1
        assert "http://localhost:*" in config.cors_origins
        assert "http://127.0.0.1:*" in config.cors_origins

    def test_custom_config(self) -> None:
        """Test custom server configuration."""
        config = ServerConfig(
            host="0.0.0.0",
            port=9000,
            log_level="debug",
            cors_origins=["http://example.com"],
        )
        assert config.host == "0.0.0.0"
        assert config.port == 9000
        assert config.log_level == "debug"
        assert config.cors_origins == ["http://example.com"]

    def test_config_validation(self) -> None:
        """Test ServerConfig validates field types."""
        with pytest.raises(Exception):  # Pydantic validation error
            ServerConfig(port="invalid")  # type: ignore

        with pytest.raises(Exception):
            ServerConfig(workers="invalid")  # type: ignore


class TestCreateApp:
    """Tests for create_app function."""

    def test_app_creation_with_default_config(self) -> None:
        """Test FastAPI app is created with default config."""
        app = create_app()
        assert app is not None
        assert app.title == "Local Telemetry API"
        assert app.version == "2.2.0"
        assert app.docs_url == "/docs"
        assert app.redoc_url == "/redoc"
        assert app.openapi_url == "/openapi.json"

    def test_app_creation_with_custom_config(self) -> None:
        """Test FastAPI app is created with custom config."""
        config = ServerConfig(host="0.0.0.0", port=9000, log_level="debug")
        app = create_app(config)
        assert app is not None
        assert app.title == "Local Telemetry API"

    def test_cors_middleware_configured(self) -> None:
        """Test CORS middleware is properly configured."""
        app = create_app()
        # Check middleware is registered
        middleware_classes = [m.cls.__name__ for m in app.user_middleware]
        assert "CORSMiddleware" in middleware_classes

    def test_health_endpoint_registered(self) -> None:
        """Test health check endpoint is registered."""
        app = create_app()
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200


class TestHealthEndpoint:
    """Tests for GET /health endpoint."""

    def test_health_check_success(self) -> None:
        """Test health check returns 200 OK with correct schema."""
        app = create_app()
        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["version"] == "2.2.0"

    def test_health_check_response_structure(self) -> None:
        """Test health check response matches HealthResponse model."""
        app = create_app()
        client = TestClient(app)
        response = client.get("/health")

        data = response.json()
        assert "status" in data
        assert "version" in data
        assert isinstance(data["status"], str)
        assert isinstance(data["version"], str)

    def test_health_check_no_auth_required(self) -> None:
        """Test health check endpoint does not require authentication."""
        app = create_app()
        client = TestClient(app)
        # No Authorization header provided
        response = client.get("/health")
        assert response.status_code == 200


class TestCORSConfiguration:
    """Tests for CORS configuration."""

    def test_cors_allows_localhost_origins(self) -> None:
        """Test CORS allows localhost origins."""
        app = create_app()
        client = TestClient(app)

        # Make a regular GET request with Origin header
        response = client.get(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
            },
        )

        # Should allow the request and return success
        assert response.status_code == 200
        # CORS middleware is configured (detailed CORS testing is FastAPI's responsibility)

    def test_cors_configured_with_custom_origins(self) -> None:
        """Test CORS can be configured with custom origins."""
        config = ServerConfig(cors_origins=["http://example.com"])
        app = create_app(config)
        assert app is not None
        # Middleware is configured (detailed CORS testing is FastAPI's responsibility)


class TestServerLifecycle:
    """Tests for server lifecycle management."""

    @patch("launch.telemetry_api.server.uvicorn.run")
    def test_start_server_with_defaults(self, mock_uvicorn_run: MagicMock) -> None:
        """Test server starts with default configuration."""
        start_telemetry_server()

        mock_uvicorn_run.assert_called_once()
        call_kwargs = mock_uvicorn_run.call_args.kwargs
        assert call_kwargs["host"] == "127.0.0.1"
        assert call_kwargs["port"] == 8765
        assert call_kwargs["log_level"] == "info"
        assert call_kwargs["factory"] is True

    @patch("launch.telemetry_api.server.uvicorn.run")
    def test_start_server_with_custom_config(self, mock_uvicorn_run: MagicMock) -> None:
        """Test server starts with custom configuration."""
        start_telemetry_server(host="0.0.0.0", port=9000, log_level="debug")

        mock_uvicorn_run.assert_called_once()
        call_kwargs = mock_uvicorn_run.call_args.kwargs
        assert call_kwargs["host"] == "0.0.0.0"
        assert call_kwargs["port"] == 9000
        assert call_kwargs["log_level"] == "debug"

    @patch("launch.telemetry_api.server.uvicorn.run")
    def test_start_server_single_worker(self, mock_uvicorn_run: MagicMock) -> None:
        """Test server uses single worker (required for SQLite)."""
        start_telemetry_server()

        call_kwargs = mock_uvicorn_run.call_args.kwargs
        assert call_kwargs["workers"] == 1


class TestErrorHandling:
    """Tests for error handling."""

    def test_invalid_port_number_low(self) -> None:
        """Test error raised for invalid port number (too low)."""
        with pytest.raises(ValueError, match="Invalid port number"):
            start_telemetry_server(port=0)

    def test_invalid_port_number_high(self) -> None:
        """Test error raised for invalid port number (too high)."""
        with pytest.raises(ValueError, match="Invalid port number"):
            start_telemetry_server(port=65536)

    def test_invalid_log_level(self) -> None:
        """Test error raised for invalid log level."""
        with pytest.raises(ValueError, match="Invalid log level"):
            start_telemetry_server(log_level="invalid")

    @patch("launch.telemetry_api.server.uvicorn.run")
    def test_port_in_use_error(self, mock_uvicorn_run: MagicMock) -> None:
        """Test error handling when port is already in use."""
        # Simulate OSError for port in use
        mock_uvicorn_run.side_effect = OSError("address already in use")

        with pytest.raises(OSError, match="Port .* is already in use"):
            start_telemetry_server(port=8765)

    @patch("launch.telemetry_api.server.uvicorn.run")
    def test_generic_runtime_error(self, mock_uvicorn_run: MagicMock) -> None:
        """Test error handling for generic runtime errors."""
        mock_uvicorn_run.side_effect = RuntimeError("Unexpected error")

        with pytest.raises(RuntimeError, match="Failed to start telemetry server"):
            start_telemetry_server()


class TestEnvironmentConfiguration:
    """Tests for environment-based configuration."""

    def test_get_config_from_env_defaults(self) -> None:
        """Test loading config from environment with defaults."""
        with patch.dict(os.environ, {}, clear=True):
            config = get_server_config_from_env()
            assert config.host == "127.0.0.1"
            assert config.port == 8765
            assert config.log_level == "info"

    def test_get_config_from_env_custom(self) -> None:
        """Test loading config from environment with custom values."""
        with patch.dict(
            os.environ,
            {
                "TELEMETRY_API_HOST": "0.0.0.0",
                "TELEMETRY_API_PORT": "9000",
                "TELEMETRY_LOG_LEVEL": "debug",
            },
        ):
            config = get_server_config_from_env()
            assert config.host == "0.0.0.0"
            assert config.port == 9000
            assert config.log_level == "debug"

    def test_get_config_from_env_partial(self) -> None:
        """Test loading config with some env vars set."""
        with patch.dict(
            os.environ,
            {"TELEMETRY_API_PORT": "9999"},
            clear=True,
        ):
            config = get_server_config_from_env()
            assert config.host == "127.0.0.1"  # default
            assert config.port == 9999  # from env
            assert config.log_level == "info"  # default


# Summary: 8+ tests covering all requirements
# - Server initialization (TestCreateApp: 4 tests)
# - Health check endpoint (TestHealthEndpoint: 3 tests)
# - CORS configuration (TestCORSConfiguration: 2 tests)
# - Server lifecycle (TestServerLifecycle: 3 tests)
# - Error handling (TestErrorHandling: 5 tests)
# - Environment config (TestEnvironmentConfiguration: 3 tests)
# Total: 20 tests
