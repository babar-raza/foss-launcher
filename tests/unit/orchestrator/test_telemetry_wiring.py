"""Unit tests for orchestrator telemetry wiring (TC-3792)."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from launcher.models.run_config import (
    LLMConfig,
    LLMEndpoint,
    OutputConfig,
    RunConfig,
    TelemetryConfig,
)
from launcher.orchestrator.worker_contract import WorkerContext


class TestTelemetryConfig:
    def test_defaults(self):
        tc = TelemetryConfig()
        assert tc.endpoint_url == "http://127.0.0.1:8765"
        assert tc.auth_token_env == ""

    def test_custom(self):
        tc = TelemetryConfig(endpoint_url="http://custom:9999", auth_token_env="MY_TOKEN")
        assert tc.endpoint_url == "http://custom:9999"
        assert tc.auth_token_env == "MY_TOKEN"


class TestRunConfigTelemetry:
    def test_run_config_accepts_telemetry(self):
        rc = RunConfig(
            family="test",
            platform="python",
            repo_url="https://example.com",
            telemetry=TelemetryConfig(endpoint_url="http://localhost:8765"),
        )
        assert rc.telemetry is not None
        assert rc.telemetry.endpoint_url == "http://localhost:8765"

    def test_run_config_telemetry_optional(self):
        rc = RunConfig(
            family="test",
            platform="python",
            repo_url="https://example.com",
        )
        assert rc.telemetry is None

    def test_run_config_ignores_unknown_fields(self):
        """Existing configs with extra fields still parse (extra='ignore')."""
        rc = RunConfig(
            family="test",
            platform="python",
            repo_url="https://example.com",
            unknown_field="should_be_ignored",
        )
        assert rc.family == "test"


class TestWorkerContextTelemetry:
    def _make_config(self) -> RunConfig:
        return RunConfig(
            family="test",
            platform="python",
            repo_url="https://example.com",
        )

    def test_default_telemetry_is_none(self, tmp_path):
        ctx = WorkerContext(
            run_id="test-001",
            run_dir=tmp_path,
            config=self._make_config(),
        )
        assert ctx.telemetry_client is None
        assert ctx.telemetry_trace_id == ""

    def test_telemetry_client_passthrough(self, tmp_path):
        mock_client = MagicMock()
        ctx = WorkerContext(
            run_id="test-001",
            run_dir=tmp_path,
            config=self._make_config(),
            telemetry_client=mock_client,
            telemetry_trace_id="trace-abc123",
        )
        assert ctx.telemetry_client is mock_client
        assert ctx.telemetry_trace_id == "trace-abc123"

    def test_backward_compat_no_telemetry_args(self, tmp_path):
        """Existing code creating WorkerContext without telemetry args still works."""
        ctx = WorkerContext(
            run_id="test-001",
            run_dir=tmp_path,
            config=self._make_config(),
        )
        assert ctx.run_id == "test-001"
        assert ctx.store is not None
        assert ctx.log is not None
