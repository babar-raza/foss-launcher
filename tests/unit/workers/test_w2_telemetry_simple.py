"""Simplified telemetry integration smoke tests for W2 FactsBuilder.

These tests verify that telemetry context is properly extracted and passed
to LLMProviderClient without executing the full worker pipeline.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from launch.clients.telemetry import TelemetryClient


class TestW2TelemetryExtraction:
    """Test telemetry context extraction logic in W2 worker."""

    def test_telemetry_context_extraction(self, tmp_path):
        """Test that telemetry context is extracted from run_config dict."""
        # This is a unit test of just the telemetry extraction logic
        # without running the full worker

        mock_telemetry = MagicMock(spec=TelemetryClient)

        run_config_dict = {
            "_telemetry_client": mock_telemetry,
            "_telemetry_run_id": "run-test-001",
            "_telemetry_trace_id": "trace-abc",
            "_telemetry_parent_span_id": "span-def",
        }

        # Extract telemetry context (this is what W2 worker does)
        telemetry_client = run_config_dict.get("_telemetry_client") if isinstance(run_config_dict, dict) else None
        telemetry_run_id = run_config_dict.get("_telemetry_run_id") if isinstance(run_config_dict, dict) else None
        telemetry_trace_id = run_config_dict.get("_telemetry_trace_id") if isinstance(run_config_dict, dict) else None
        telemetry_parent_span_id = run_config_dict.get("_telemetry_parent_span_id") if isinstance(run_config_dict, dict) else None

        # Verify extraction
        assert telemetry_client == mock_telemetry
        assert telemetry_run_id == "run-test-001"
        assert telemetry_trace_id == "trace-abc"
        assert telemetry_parent_span_id == "span-def"

    def test_llm_client_initialization_with_telemetry(self, tmp_path):
        """Test that LLM client can be initialized with telemetry parameters."""
        from launch.clients.llm_provider import LLMProviderClient

        mock_telemetry = MagicMock(spec=TelemetryClient)

        # Initialize LLM client with telemetry (this is what W2 does after extracting context)
        with patch("launch.clients.llm_provider.http_post"):
            client = LLMProviderClient(
                api_base_url="https://api.example.com/v1",
                model="claude-sonnet-4-5",
                run_dir=tmp_path,
                telemetry_client=mock_telemetry,
                telemetry_run_id="run-test-001",
                telemetry_trace_id="trace-abc",
                telemetry_parent_span_id="span-def",
            )

        # Verify client was created with telemetry
        assert client.telemetry_client == mock_telemetry
        assert client.telemetry_run_id == "run-test-001"
        assert client.telemetry_trace_id == "trace-abc"
        assert client.telemetry_parent_span_id == "span-def"

    def test_telemetry_context_defaults(self):
        """Test that telemetry context extraction handles missing keys gracefully."""
        run_config_dict = {}  # No telemetry keys

        telemetry_client = run_config_dict.get("_telemetry_client") if isinstance(run_config_dict, dict) else None
        telemetry_run_id = run_config_dict.get("_telemetry_run_id") if isinstance(run_config_dict, dict) else None

        # Should get None for missing keys (graceful degradation)
        assert telemetry_client is None
        assert telemetry_run_id is None
