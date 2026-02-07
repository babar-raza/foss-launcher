"""Unit tests for LLM telemetry context manager.

Test coverage:
- Context manager success path
- Context manager failure path
- Graceful degradation (telemetry failures don't crash)
- Event emission
- Cost calculation
- Hard warning requirement (no raises)
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from launch.clients.llm_telemetry import (
    LLMTelemetryContext,
    calculate_api_cost,
)
from launch.clients.telemetry import TelemetryClient, TelemetryError
from launch.models.event import EVENT_LLM_CALL_STARTED, EVENT_LLM_CALL_FINISHED, EVENT_LLM_CALL_FAILED


class TestCalculateApiCost:
    """Test API cost calculation."""

    def test_claude_sonnet_cost(self):
        """Test cost calculation for Claude Sonnet 4.5."""
        # Claude Sonnet 4.5: $3.00/MTok input, $15.00/MTok output
        # 1500 input, 3000 output
        # cost = (1500 * 3.00 + 3000 * 15.00) / 1_000_000
        #      = (4500 + 45000) / 1_000_000
        #      = 0.0495
        cost = calculate_api_cost("claude-sonnet-4-5", 1500, 3000)
        assert cost == pytest.approx(0.0495, abs=0.0001)

    def test_claude_opus_cost(self):
        """Test cost calculation for Claude Opus 4."""
        # Claude Opus 4: $15.00/MTok input, $75.00/MTok output
        # 1000 input, 2000 output
        # cost = (1000 * 15.00 + 2000 * 75.00) / 1_000_000
        #      = (15000 + 150000) / 1_000_000
        #      = 0.165
        cost = calculate_api_cost("claude-opus-4", 1000, 2000)
        assert cost == pytest.approx(0.165, abs=0.0001)

    def test_claude_haiku_cost(self):
        """Test cost calculation for Claude Haiku 4.5."""
        # Claude Haiku 4.5: $0.80/MTok input, $4.00/MTok output
        # 5000 input, 10000 output
        # cost = (5000 * 0.80 + 10000 * 4.00) / 1_000_000
        #      = (4000 + 40000) / 1_000_000
        #      = 0.044
        cost = calculate_api_cost("claude-haiku-4-5", 5000, 10000)
        assert cost == pytest.approx(0.044, abs=0.0001)

    def test_unknown_model_returns_zero(self):
        """Test that unknown models return 0 cost."""
        cost = calculate_api_cost("unknown-model-xyz", 1000, 2000)
        assert cost == 0.0

    def test_zero_tokens_returns_zero(self):
        """Test that zero tokens return 0 cost."""
        cost = calculate_api_cost("claude-sonnet-4-5", 0, 0)
        assert cost == 0.0


class TestLLMTelemetryContextSuccess:
    """Test successful LLM telemetry tracking."""

    def test_context_manager_success_with_telemetry_client(self, tmp_path):
        """Test context manager with telemetry client - success path."""
        # Setup
        mock_client = MagicMock(spec=TelemetryClient)
        mock_client.create_run.return_value = True
        mock_client.update_run.return_value = True

        events_file = tmp_path / "events.ndjson"

        # Execute
        with LLMTelemetryContext(
            telemetry_client=mock_client,
            event_log_path=events_file,
            call_id="test_call",
            run_id="run-001",
            trace_id="trace-abc",
            parent_span_id="span-def",
            model="claude-sonnet-4-5",
            temperature=0.0,
            max_tokens=4096,
            prompt_hash="prompt123",
            evidence_path="evidence/llm_calls/test_call.json",
        ) as ctx:
            # Simulate LLM response with usage
            ctx.record_usage({
                "input_tokens": 1500,
                "output_tokens": 3000,
                "total_tokens": 4500,
                "prompt_tokens": 1500,
                "completion_tokens": 3000,
                "finish_reason": "stop",
                "output_hash": "output123",
            })

        # Verify telemetry client calls
        assert mock_client.create_run.called
        create_call = mock_client.create_run.call_args
        assert create_call[1]["run_id"] == "run-001-llm-test_call"
        assert create_call[1]["agent_name"].startswith("launch.llm.")
        assert create_call[1]["job_type"] == "llm_call"
        assert create_call[1]["parent_run_id"] == "run-001"
        assert create_call[1]["status"] == "running"

        # Verify context_json
        context_json = create_call[1]["context_json"]
        assert context_json["trace_id"] == "trace-abc"
        assert context_json["parent_span_id"] == "span-def"
        assert context_json["call_id"] == "test_call"
        assert context_json["model"] == "claude-sonnet-4-5"
        assert context_json["temperature"] == 0.0
        assert context_json["max_tokens"] == 4096
        assert context_json["prompt_hash"] == "prompt123"
        assert context_json["evidence_path"] == "evidence/llm_calls/test_call.json"

        # Verify update_run called
        assert mock_client.update_run.called
        update_call = mock_client.update_run.call_args
        assert update_call[1]["status"] == "success"
        assert update_call[1]["duration_ms"] >= 0

        # Verify metrics_json
        metrics = update_call[1]["metrics_json"]
        assert metrics["input_tokens"] == 1500
        assert metrics["output_tokens"] == 3000
        assert metrics["total_tokens"] == 4500
        assert metrics["finish_reason"] == "stop"
        assert "api_cost_usd" in metrics
        assert metrics["api_cost_usd"] > 0

        # Verify events emitted
        assert events_file.exists()
        with events_file.open("r") as f:
            events = [json.loads(line) for line in f if line.strip()]

        assert len(events) == 2
        assert events[0]["type"] == EVENT_LLM_CALL_STARTED
        assert events[0]["payload"]["call_id"] == "test_call"
        assert events[0]["payload"]["model"] == "claude-sonnet-4-5"
        assert events[0]["trace_id"] == "trace-abc"

        assert events[1]["type"] == EVENT_LLM_CALL_FINISHED
        assert events[1]["payload"]["call_id"] == "test_call"
        assert events[1]["payload"]["latency_ms"] >= 0
        assert events[1]["payload"]["token_usage"]["total_tokens"] == 4500

    def test_context_manager_without_telemetry_client(self, tmp_path):
        """Test context manager without telemetry client (events only)."""
        events_file = tmp_path / "events.ndjson"

        with LLMTelemetryContext(
            telemetry_client=None,  # No telemetry client
            event_log_path=events_file,
            call_id="test_call",
            run_id="run-001",
            trace_id="trace-abc",
            parent_span_id="span-def",
            model="claude-sonnet-4-5",
        ) as ctx:
            ctx.record_usage({
                "input_tokens": 100,
                "output_tokens": 200,
                "total_tokens": 300,
                "finish_reason": "stop",
            })

        # Verify events still emitted
        assert events_file.exists()
        with events_file.open("r") as f:
            events = [json.loads(line) for line in f if line.strip()]

        assert len(events) == 2
        assert events[0]["type"] == EVENT_LLM_CALL_STARTED
        assert events[1]["type"] == EVENT_LLM_CALL_FINISHED

    def test_context_manager_without_event_log(self, tmp_path):
        """Test context manager without event log (telemetry only)."""
        mock_client = MagicMock(spec=TelemetryClient)

        with LLMTelemetryContext(
            telemetry_client=mock_client,
            event_log_path=None,  # No event log
            call_id="test_call",
            run_id="run-001",
            trace_id="trace-abc",
            parent_span_id="span-def",
            model="claude-sonnet-4-5",
        ) as ctx:
            ctx.record_usage({
                "input_tokens": 100,
                "output_tokens": 200,
                "total_tokens": 300,
                "finish_reason": "stop",
            })

        # Verify telemetry still called
        assert mock_client.create_run.called
        assert mock_client.update_run.called

    def test_context_manager_with_no_telemetry_or_events(self):
        """Test context manager with no telemetry or events (graceful no-op)."""
        # Should not crash
        with LLMTelemetryContext(
            telemetry_client=None,
            event_log_path=None,
            call_id="test_call",
            run_id="run-001",
            trace_id="trace-abc",
            parent_span_id="span-def",
            model="claude-sonnet-4-5",
        ) as ctx:
            ctx.record_usage({
                "input_tokens": 100,
                "output_tokens": 200,
                "total_tokens": 300,
                "finish_reason": "stop",
            })

        # No crashes = success


class TestLLMTelemetryContextFailure:
    """Test LLM telemetry tracking with failures."""

    def test_context_manager_with_llm_exception(self, tmp_path):
        """Test context manager when LLM call raises exception."""
        mock_client = MagicMock(spec=TelemetryClient)
        events_file = tmp_path / "events.ndjson"

        # Simulate LLM failure
        with pytest.raises(ValueError, match="LLM API error"):
            with LLMTelemetryContext(
                telemetry_client=mock_client,
                event_log_path=events_file,
                call_id="test_call",
                run_id="run-001",
                trace_id="trace-abc",
                parent_span_id="span-def",
                model="claude-sonnet-4-5",
            ):
                raise ValueError("LLM API error")

        # Verify failure telemetry
        update_call = mock_client.update_run.call_args
        assert update_call[1]["status"] == "failure"
        assert "LLM API error" in update_call[1]["error_summary"]

        # Verify failure event emitted
        with events_file.open("r") as f:
            events = [json.loads(line) for line in f if line.strip()]

        assert len(events) == 2
        assert events[0]["type"] == EVENT_LLM_CALL_STARTED
        assert events[1]["type"] == EVENT_LLM_CALL_FAILED
        assert events[1]["payload"]["error_class"] == "ValueError"
        assert events[1]["payload"]["error_summary"] == "LLM API error"
        assert events[1]["payload"]["retryable"] is False  # ValueError not retryable


class TestLLMTelemetryGracefulDegradation:
    """Test graceful degradation when telemetry fails."""

    def test_create_run_telemetry_error_does_not_crash(self, tmp_path):
        """Test that TelemetryError in create_run doesn't crash LLM call."""
        mock_client = MagicMock(spec=TelemetryClient)
        mock_client.create_run.side_effect = TelemetryError("API unavailable")

        events_file = tmp_path / "events.ndjson"

        # Should NOT crash
        with LLMTelemetryContext(
            telemetry_client=mock_client,
            event_log_path=events_file,
            call_id="test_call",
            run_id="run-001",
            trace_id="trace-abc",
            parent_span_id="span-def",
            model="claude-sonnet-4-5",
        ) as ctx:
            ctx.record_usage({
                "input_tokens": 100,
                "output_tokens": 200,
                "total_tokens": 300,
                "finish_reason": "stop",
            })

        # Verify events still emitted (event log independent of telemetry)
        assert events_file.exists()

    def test_update_run_telemetry_error_does_not_crash(self, tmp_path):
        """Test that TelemetryError in update_run doesn't crash LLM call."""
        mock_client = MagicMock(spec=TelemetryClient)
        mock_client.update_run.side_effect = TelemetryError("API unavailable")

        events_file = tmp_path / "events.ndjson"

        # Should NOT crash
        with LLMTelemetryContext(
            telemetry_client=mock_client,
            event_log_path=events_file,
            call_id="test_call",
            run_id="run-001",
            trace_id="trace-abc",
            parent_span_id="span-def",
            model="claude-sonnet-4-5",
        ) as ctx:
            ctx.record_usage({
                "input_tokens": 100,
                "output_tokens": 200,
                "total_tokens": 300,
                "finish_reason": "stop",
            })

        # Success - no crash

    def test_event_emission_failure_does_not_crash(self, tmp_path):
        """Test that event emission failure doesn't crash LLM call."""
        mock_client = MagicMock(spec=TelemetryClient)

        # Use invalid path to cause event emission failure
        events_file = Path("/invalid/path/events.ndjson")

        # Should NOT crash
        with LLMTelemetryContext(
            telemetry_client=mock_client,
            event_log_path=events_file,
            call_id="test_call",
            run_id="run-001",
            trace_id="trace-abc",
            parent_span_id="span-def",
            model="claude-sonnet-4-5",
        ) as ctx:
            ctx.record_usage({
                "input_tokens": 100,
                "output_tokens": 200,
                "total_tokens": 300,
                "finish_reason": "stop",
            })

        # Verify telemetry still called (independent of events)
        assert mock_client.create_run.called
        assert mock_client.update_run.called

    def test_generic_exception_in_create_run_does_not_crash(self, tmp_path):
        """Test that generic Exception in create_run doesn't crash."""
        mock_client = MagicMock(spec=TelemetryClient)
        mock_client.create_run.side_effect = RuntimeError("Unexpected error")

        events_file = tmp_path / "events.ndjson"

        # Should NOT crash
        with LLMTelemetryContext(
            telemetry_client=mock_client,
            event_log_path=events_file,
            call_id="test_call",
            run_id="run-001",
            trace_id="trace-abc",
            parent_span_id="span-def",
            model="claude-sonnet-4-5",
        ) as ctx:
            ctx.record_usage({
                "input_tokens": 100,
                "output_tokens": 200,
                "total_tokens": 300,
                "finish_reason": "stop",
            })

        # Success - no crash

    def test_hard_warning_requirement_no_raises(self, tmp_path):
        """Test HARD REQUIREMENT: telemetry NEVER raises exceptions."""
        mock_client = MagicMock(spec=TelemetryClient)
        # Simulate all possible failures
        mock_client.create_run.side_effect = Exception("Catastrophic failure")
        mock_client.update_run.side_effect = Exception("Catastrophic failure")

        # Use invalid event path
        events_file = Path("/invalid/events.ndjson")

        # Should STILL NOT crash
        with LLMTelemetryContext(
            telemetry_client=mock_client,
            event_log_path=events_file,
            call_id="test_call",
            run_id="run-001",
            trace_id="trace-abc",
            parent_span_id="span-def",
            model="claude-sonnet-4-5",
        ) as ctx:
            ctx.record_usage({
                "input_tokens": 100,
                "output_tokens": 200,
                "total_tokens": 300,
                "finish_reason": "stop",
            })

        # SUCCESS: No raises, operation completed
