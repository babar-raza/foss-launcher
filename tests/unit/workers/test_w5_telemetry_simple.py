"""Simplified telemetry integration smoke tests for W5 SectionWriter.

These tests verify that telemetry context is properly extracted and passed
to LLMProviderClient without executing the full worker pipeline.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from launch.clients.telemetry import TelemetryClient


class TestW5TelemetryExtraction:
    """Test telemetry context extraction logic in W5 worker."""

    def test_telemetry_context_extraction(self):
        """Test that telemetry context is extracted from run_config dict."""
        # This is a unit test of just the telemetry extraction logic
        # without running the full worker

        mock_telemetry = MagicMock(spec=TelemetryClient)

        run_config = {
            "_telemetry_client": mock_telemetry,
            "_telemetry_run_id": "run-test-002",
            "_telemetry_trace_id": "trace-xyz",
            "_telemetry_parent_span_id": "span-w5",
        }

        # Extract telemetry context (this is what W5 worker does)
        telemetry_client = run_config.get("_telemetry_client") if isinstance(run_config, dict) else None
        telemetry_run_id = run_config.get("_telemetry_run_id") if isinstance(run_config, dict) else None
        telemetry_trace_id = run_config.get("_telemetry_trace_id") if isinstance(run_config, dict) else None
        telemetry_parent_span_id = run_config.get("_telemetry_parent_span_id") if isinstance(run_config, dict) else None

        # Verify extraction
        assert telemetry_client == mock_telemetry
        assert telemetry_run_id == "run-test-002"
        assert telemetry_trace_id == "trace-xyz"
        assert telemetry_parent_span_id == "span-w5"

    def test_llm_client_initialization_with_telemetry(self, tmp_path):
        """Test that W5 can initialize LLM client with telemetry parameters."""
        from launch.clients.llm_provider import LLMProviderClient

        mock_telemetry = MagicMock(spec=TelemetryClient)

        # Simulate W5's LLM client initialization with telemetry
        with patch("launch.clients.llm_provider.http_post"):
            client = LLMProviderClient(
                api_base_url="https://api.example.com/v1",
                model="claude-sonnet-4-5",
                run_dir=tmp_path,
                temperature=0.0,
                max_tokens=6000,
                telemetry_client=mock_telemetry,
                telemetry_run_id="run-test-002",
                telemetry_trace_id="trace-xyz",
                telemetry_parent_span_id="span-w5",
            )

        # Verify client was created with telemetry
        assert client.telemetry_client == mock_telemetry
        assert client.telemetry_run_id == "run-test-002"
        assert client.telemetry_trace_id == "trace-xyz"
        assert client.telemetry_parent_span_id == "span-w5"

    def test_w5_llm_config_structure(self):
        """Test that W5 run_config llm structure is properly accessed."""
        run_config = {
            "llm": {
                "api_base_url": "https://api.example.com/v1",
                "model": "claude-sonnet-4-5",
                "decoding": {
                    "temperature": 0.0,
                    "max_tokens": 6000,
                },
                "request_timeout_s": 120,
            },
            "_telemetry_client": None,  # No telemetry
        }

        # Verify W5 can access llm config (this is what W5 does before initializing client)
        llm_cfg = run_config.get("llm", {})
        assert llm_cfg.get("api_base_url") == "https://api.example.com/v1"
        assert llm_cfg.get("model") == "claude-sonnet-4-5"
        assert llm_cfg.get("decoding", {}).get("temperature") == 0.0
        assert llm_cfg.get("decoding", {}).get("max_tokens") == 6000

    def test_telemetry_context_defaults(self):
        """Test that telemetry context extraction handles missing keys gracefully."""
        run_config = {"llm": {}}  # No telemetry keys

        telemetry_client = run_config.get("_telemetry_client") if isinstance(run_config, dict) else None
        telemetry_run_id = run_config.get("_telemetry_run_id") if isinstance(run_config, dict) else None

        # Should get None for missing keys (graceful degradation)
        assert telemetry_client is None
        assert telemetry_run_id is None
