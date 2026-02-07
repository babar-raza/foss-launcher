"""Integration tests for LLMProviderClient telemetry integration.

Test coverage:
- Backward compatibility (telemetry disabled)
- Telemetry enabled with successful API call
- Telemetry enabled with API failure
- Graceful degradation when telemetry fails
- Token usage recording
- Trace/span correlation
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from launch.clients.llm_provider import LLMProviderClient, LLMError
from launch.clients.telemetry import TelemetryClient


class TestLLMProviderBackwardCompatibility:
    """Test that LLMProviderClient still works without telemetry."""

    @patch("launch.clients.llm_provider.http_post")
    def test_chat_completion_without_telemetry(self, mock_http_post, tmp_path):
        """Test chat_completion works without telemetry parameters."""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "chatcmpl-123",
            "model": "claude-sonnet-4-5",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "Hello! How can I help you?",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30,
            },
        }
        mock_http_post.return_value = mock_response

        # Create client WITHOUT telemetry parameters
        client = LLMProviderClient(
            api_base_url="https://api.example.com/v1",
            model="claude-sonnet-4-5",
            run_dir=tmp_path,
            api_key="test_key",
        )

        # Make LLM call
        messages = [{"role": "user", "content": "Hello"}]
        result = client.chat_completion(messages, call_id="test_backward_compat")

        # Verify result
        assert result["content"] == "Hello! How can I help you?"
        assert result["model"] == "claude-sonnet-4-5"
        assert result["usage"]["total_tokens"] == 30
        assert "prompt_hash" in result
        assert "latency_ms" in result
        assert "evidence_path" in result

        # Verify evidence saved
        evidence_file = tmp_path / "evidence" / "llm_calls" / "test_backward_compat.json"
        assert evidence_file.exists()

    @patch("launch.clients.llm_provider.http_post")
    def test_telemetry_params_optional(self, mock_http_post, tmp_path):
        """Test that telemetry parameters are optional."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"index": 0, "message": {"content": "Test"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 10, "total_tokens": 15},
        }
        mock_http_post.return_value = mock_response

        # Create client with telemetry_client=None (explicitly disabled)
        client = LLMProviderClient(
            api_base_url="https://api.example.com/v1",
            model="claude-sonnet-4-5",
            run_dir=tmp_path,
            telemetry_client=None,
            telemetry_run_id=None,
            telemetry_trace_id=None,
            telemetry_parent_span_id=None,
        )

        messages = [{"role": "user", "content": "Test"}]
        result = client.chat_completion(messages)

        assert result["content"] == "Test"


class TestLLMProviderTelemetryEnabled:
    """Test LLMProviderClient with telemetry enabled."""

    @patch("launch.clients.llm_provider.http_post")
    def test_chat_completion_with_telemetry(self, mock_http_post, tmp_path):
        """Test chat_completion with telemetry client."""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "Telemetry test response"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 200,
                "total_tokens": 300,
            },
        }
        mock_http_post.return_value = mock_response

        # Create mock telemetry client
        mock_telemetry = MagicMock(spec=TelemetryClient)

        # Create client WITH telemetry
        client = LLMProviderClient(
            api_base_url="https://api.example.com/v1",
            model="claude-sonnet-4-5",
            run_dir=tmp_path,
            api_key="test_key",
            telemetry_client=mock_telemetry,
            telemetry_run_id="run-001",
            telemetry_trace_id="trace-abc",
            telemetry_parent_span_id="span-def",
        )

        # Make LLM call
        messages = [{"role": "user", "content": "Test with telemetry"}]
        result = client.chat_completion(messages, call_id="test_telemetry")

        # Verify LLM result
        assert result["content"] == "Telemetry test response"
        assert result["usage"]["total_tokens"] == 300

        # Verify telemetry client was called
        assert mock_telemetry.create_run.called, "Telemetry create_run should be called"
        assert mock_telemetry.update_run.called, "Telemetry update_run should be called"

        # Verify create_run parameters
        create_call = mock_telemetry.create_run.call_args
        assert create_call[1]["run_id"] == "run-001-llm-test_telemetry"
        assert create_call[1]["job_type"] == "llm_call"
        assert create_call[1]["parent_run_id"] == "run-001"
        assert create_call[1]["status"] == "running"

        # Verify context_json
        context_json = create_call[1]["context_json"]
        assert context_json["trace_id"] == "trace-abc"
        assert context_json["parent_span_id"] == "span-def"
        assert context_json["call_id"] == "test_telemetry"
        assert context_json["model"] == "claude-sonnet-4-5"
        assert context_json["temperature"] == 0.0
        assert context_json["max_tokens"] == 4096
        assert "prompt_hash" in context_json
        assert context_json["evidence_path"] == "evidence/llm_calls/test_telemetry.json"

        # Verify update_run parameters
        update_call = mock_telemetry.update_run.call_args
        assert update_call[1]["status"] == "success"
        assert update_call[1]["duration_ms"] >= 0

        # Verify metrics_json
        metrics = update_call[1]["metrics_json"]
        assert metrics["input_tokens"] == 100
        assert metrics["output_tokens"] == 200
        assert metrics["total_tokens"] == 300
        assert metrics["finish_reason"] == "stop"
        assert "api_cost_usd" in metrics
        assert metrics["api_cost_usd"] > 0  # Claude Sonnet has non-zero cost

    @patch("launch.clients.llm_provider.http_post")
    def test_chat_completion_with_telemetry_events(self, mock_http_post, tmp_path):
        """Test that telemetry events are emitted to events.ndjson."""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {"index": 0, "message": {"content": "Events test"}, "finish_reason": "stop"}
            ],
            "usage": {"prompt_tokens": 50, "completion_tokens": 100, "total_tokens": 150},
        }
        mock_http_post.return_value = mock_response

        mock_telemetry = MagicMock(spec=TelemetryClient)

        client = LLMProviderClient(
            api_base_url="https://api.example.com/v1",
            model="claude-sonnet-4-5",
            run_dir=tmp_path,
            telemetry_client=mock_telemetry,
            telemetry_run_id="run-002",
            telemetry_trace_id="trace-xyz",
        )

        messages = [{"role": "user", "content": "Test events"}]
        result = client.chat_completion(messages, call_id="test_events")

        # Verify events.ndjson exists and contains events
        events_file = tmp_path / "events.ndjson"
        assert events_file.exists(), "events.ndjson should be created"

        with events_file.open("r") as f:
            events = [json.loads(line) for line in f if line.strip()]

        assert len(events) == 2, "Should have LLM_CALL_STARTED and LLM_CALL_FINISHED"
        assert events[0]["type"] == "LLM_CALL_STARTED"
        assert events[1]["type"] == "LLM_CALL_FINISHED"

        # Verify event payloads
        started = events[0]
        assert started["payload"]["call_id"] == "test_events"
        assert started["payload"]["model"] == "claude-sonnet-4-5"
        assert started["trace_id"] == "trace-xyz"

        finished = events[1]
        assert finished["payload"]["call_id"] == "test_events"
        assert finished["payload"]["token_usage"]["total_tokens"] == 150
        assert finished["payload"]["latency_ms"] >= 0


class TestLLMProviderTelemetryFailure:
    """Test graceful degradation when telemetry fails."""

    @patch("launch.clients.llm_provider.http_post")
    def test_llm_call_succeeds_when_telemetry_create_fails(self, mock_http_post, tmp_path):
        """Test that LLM call succeeds even if telemetry create_run fails."""
        # Mock successful LLM response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"index": 0, "message": {"content": "Success"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        }
        mock_http_post.return_value = mock_response

        # Mock telemetry client that fails on create_run
        mock_telemetry = MagicMock(spec=TelemetryClient)
        mock_telemetry.create_run.side_effect = Exception("Telemetry API unavailable")

        client = LLMProviderClient(
            api_base_url="https://api.example.com/v1",
            model="claude-sonnet-4-5",
            run_dir=tmp_path,
            telemetry_client=mock_telemetry,
            telemetry_run_id="run-003",
        )

        # Should NOT raise exception
        messages = [{"role": "user", "content": "Test"}]
        result = client.chat_completion(messages, call_id="test_telemetry_fail")

        # Verify LLM call succeeded
        assert result["content"] == "Success"
        assert result["usage"]["total_tokens"] == 30

    @patch("launch.clients.llm_provider.http_post")
    def test_llm_call_succeeds_when_telemetry_update_fails(self, mock_http_post, tmp_path):
        """Test that LLM call succeeds even if telemetry update_run fails."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"index": 0, "message": {"content": "Success"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        }
        mock_http_post.return_value = mock_response

        # Mock telemetry client that fails on update_run
        mock_telemetry = MagicMock(spec=TelemetryClient)
        mock_telemetry.update_run.side_effect = Exception("Update failed")

        client = LLMProviderClient(
            api_base_url="https://api.example.com/v1",
            model="claude-sonnet-4-5",
            run_dir=tmp_path,
            telemetry_client=mock_telemetry,
            telemetry_run_id="run-004",
        )

        # Should NOT raise exception
        messages = [{"role": "user", "content": "Test"}]
        result = client.chat_completion(messages)

        # Verify LLM call succeeded
        assert result["content"] == "Success"

    @patch("launch.clients.llm_provider.http_post")
    def test_llm_call_failure_tracked_in_telemetry(self, mock_http_post, tmp_path):
        """Test that LLM API failures are tracked in telemetry."""
        # Mock failed LLM response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_http_post.return_value = mock_response

        mock_telemetry = MagicMock(spec=TelemetryClient)

        client = LLMProviderClient(
            api_base_url="https://api.example.com/v1",
            model="claude-sonnet-4-5",
            run_dir=tmp_path,
            telemetry_client=mock_telemetry,
            telemetry_run_id="run-005",
        )

        messages = [{"role": "user", "content": "Test failure"}]

        # LLM call should raise LLMError
        with pytest.raises(LLMError):
            client.chat_completion(messages, call_id="test_llm_failure")

        # Verify telemetry update_run was called with failure status
        assert mock_telemetry.update_run.called
        update_call = mock_telemetry.update_run.call_args
        assert update_call[1]["status"] == "failure"
        assert "error_summary" in update_call[1]


class TestLLMProviderTelemetryTokenUsage:
    """Test token usage recording with different API response formats."""

    @patch("launch.clients.llm_provider.http_post")
    def test_openai_style_token_usage(self, mock_http_post, tmp_path):
        """Test token usage recording with OpenAI-style keys (prompt_tokens, completion_tokens)."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"index": 0, "message": {"content": "Test"}, "finish_reason": "stop"}],
            "usage": {
                "prompt_tokens": 150,
                "completion_tokens": 300,
                "total_tokens": 450,
            },
        }
        mock_http_post.return_value = mock_response

        mock_telemetry = MagicMock(spec=TelemetryClient)

        client = LLMProviderClient(
            api_base_url="https://api.example.com/v1",
            model="claude-sonnet-4-5",
            run_dir=tmp_path,
            telemetry_client=mock_telemetry,
            telemetry_run_id="run-006",
        )

        messages = [{"role": "user", "content": "Test"}]
        result = client.chat_completion(messages)

        # Verify telemetry recorded correct usage
        update_call = mock_telemetry.update_run.call_args
        metrics = update_call[1]["metrics_json"]
        assert metrics["input_tokens"] == 150
        assert metrics["output_tokens"] == 300
        assert metrics["total_tokens"] == 450

    @patch("launch.clients.llm_provider.http_post")
    def test_anthropic_style_token_usage(self, mock_http_post, tmp_path):
        """Test token usage recording with Anthropic-style keys (input_tokens, output_tokens)."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"index": 0, "message": {"content": "Test"}, "finish_reason": "stop"}],
            "usage": {
                "input_tokens": 200,
                "output_tokens": 400,
                "total_tokens": 600,
            },
        }
        mock_http_post.return_value = mock_response

        mock_telemetry = MagicMock(spec=TelemetryClient)

        client = LLMProviderClient(
            api_base_url="https://api.example.com/v1",
            model="claude-sonnet-4-5",
            run_dir=tmp_path,
            telemetry_client=mock_telemetry,
            telemetry_run_id="run-007",
        )

        messages = [{"role": "user", "content": "Test"}]
        result = client.chat_completion(messages)

        # Verify telemetry recorded correct usage
        update_call = mock_telemetry.update_run.call_args
        metrics = update_call[1]["metrics_json"]
        assert metrics["input_tokens"] == 200
        assert metrics["output_tokens"] == 400
        assert metrics["total_tokens"] == 600
