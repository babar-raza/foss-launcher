"""Tests for LLMProviderClient fallback endpoint behavior.

Verifies that when the primary LLM endpoint fails with transient errors,
the client falls back to a configured secondary endpoint (e.g., local Ollama).

Testing: mocked (no real HTTP calls)
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from launch.clients.llm_provider import (
    LLMError,
    LLMProviderClient,
    create_llm_client_from_config,
    _resolve_api_key,
)


def _make_success_response(content: str = "Hello world. This is a valid response.", model: str = "test-model") -> Mock:
    """Create a mock successful HTTP response.

    Default content is >= 50 chars and ends with punctuation so it passes
    the Layer 1 LLM response validator without triggering a retry.
    """
    # Pad short content to pass the L1 minimum-length check (50 chars).
    padded = content if len(content.rstrip()) >= 50 else content.rstrip() + (" " + content.rstrip()) * 10
    padded = padded[:200]  # reasonable cap
    response = Mock()
    response.status_code = 200
    response.json.return_value = {
        "choices": [
            {
                "index": 0,
                "message": {"content": padded},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30,
        },
    }
    return response


def _make_error_response(status_code: int, text: str = "error") -> Mock:
    """Create a mock error HTTP response."""
    response = Mock()
    response.status_code = status_code
    response.text = text
    return response


MESSAGES = [{"role": "user", "content": "test prompt"}]


class TestFallbackOnTransientFailure:
    """Verify fallback triggers on transient failures (connection, timeout, 5xx)."""

    @patch("launch.clients.llm_provider.http_post")
    def test_connection_error_triggers_fallback(self, mock_http_post, tmp_path):
        """When primary endpoint has connection error, fallback is used."""
        mock_http_post.side_effect = [
            ConnectionError("Connection refused"),
            _make_success_response("fallback response"),
        ]

        client = LLMProviderClient(
            api_base_url="https://primary.example.com/v1",
            model="primary-model",
            run_dir=tmp_path,
            fallback_api_base_url="http://127.0.0.1:11434/v1",
            fallback_model="fallback-model",
        )

        result = client.chat_completion(MESSAGES, call_id="test_conn_err")

        assert result["content"].startswith("fallback response")
        assert result["endpoint_used"] == "fallback"
        assert result["model"] == "fallback-model"
        assert mock_http_post.call_count == 2

    @patch("launch.clients.llm_provider.http_post")
    def test_timeout_error_triggers_fallback(self, mock_http_post, tmp_path):
        """When primary endpoint times out, fallback is used."""
        mock_http_post.side_effect = [
            TimeoutError("Request timed out"),
            _make_success_response("fallback ok"),
        ]

        client = LLMProviderClient(
            api_base_url="https://primary.example.com/v1",
            model="primary-model",
            run_dir=tmp_path,
            fallback_api_base_url="http://127.0.0.1:11434/v1",
            fallback_model="fallback-model",
        )

        result = client.chat_completion(MESSAGES, call_id="test_timeout")

        assert result["content"].startswith("fallback ok")
        assert result["endpoint_used"] == "fallback"

    @patch("launch.clients.llm_provider.http_post")
    def test_503_triggers_fallback(self, mock_http_post, tmp_path):
        """When primary returns 503, fallback is used."""
        mock_http_post.side_effect = [
            _make_error_response(503, "Service Unavailable"),
            _make_success_response("fallback 503"),
        ]

        client = LLMProviderClient(
            api_base_url="https://primary.example.com/v1",
            model="primary-model",
            run_dir=tmp_path,
            fallback_api_base_url="http://127.0.0.1:11434/v1",
            fallback_model="fallback-model",
        )

        # The _call_endpoint raises Exception on non-200, which classify_failure
        # will see "503" in the message and classify as transient
        result = client.chat_completion(MESSAGES, call_id="test_503")

        assert result["content"].startswith("fallback 503")
        assert result["endpoint_used"] == "fallback"


class TestNoFallbackOnPermanentFailure:
    """Verify fallback does NOT trigger on permanent failures."""

    @patch("launch.clients.llm_provider.http_post")
    def test_400_does_not_trigger_fallback(self, mock_http_post, tmp_path):
        """When primary returns 400 (bad request), no fallback - raise immediately."""
        mock_http_post.return_value = _make_error_response(400, "Bad Request: invalid model")

        client = LLMProviderClient(
            api_base_url="https://primary.example.com/v1",
            model="primary-model",
            run_dir=tmp_path,
            fallback_api_base_url="http://127.0.0.1:11434/v1",
            fallback_model="fallback-model",
        )

        with pytest.raises(LLMError, match="LLM API call failed"):
            client.chat_completion(MESSAGES, call_id="test_400")

        # Only one call made (no fallback attempt)
        assert mock_http_post.call_count == 1


class TestNoFallbackConfigured:
    """Verify behavior when no fallback is configured."""

    @patch("launch.clients.llm_provider.http_post")
    def test_no_fallback_raises_on_failure(self, mock_http_post, tmp_path):
        """When no fallback configured, original error propagates."""
        mock_http_post.side_effect = ConnectionError("Connection refused")

        client = LLMProviderClient(
            api_base_url="https://primary.example.com/v1",
            model="primary-model",
            run_dir=tmp_path,
            # No fallback configured
        )

        with pytest.raises(LLMError, match="LLM API call failed"):
            client.chat_completion(MESSAGES, call_id="test_no_fallback")

        assert mock_http_post.call_count == 1


class TestPrimarySuccess:
    """Verify primary endpoint used when it succeeds."""

    @patch("launch.clients.llm_provider.http_post")
    def test_primary_success_no_fallback_call(self, mock_http_post, tmp_path):
        """When primary succeeds, fallback is never called."""
        mock_http_post.return_value = _make_success_response("primary ok")

        client = LLMProviderClient(
            api_base_url="https://primary.example.com/v1",
            model="primary-model",
            run_dir=tmp_path,
            fallback_api_base_url="http://127.0.0.1:11434/v1",
            fallback_model="fallback-model",
        )

        result = client.chat_completion(MESSAGES, call_id="test_primary_ok")

        assert result["content"].startswith("primary ok")
        assert result["endpoint_used"] == "primary"
        assert result["model"] == "primary-model"
        assert mock_http_post.call_count == 1


class TestFallbackModelSwap:
    """Verify model name is swapped in the payload when using fallback."""

    @patch("launch.clients.llm_provider.http_post")
    def test_fallback_uses_fallback_model_in_payload(self, mock_http_post, tmp_path):
        """Fallback request payload uses the fallback model name."""
        mock_http_post.side_effect = [
            ConnectionError("Connection refused"),
            _make_success_response("fallback with correct model"),
        ]

        client = LLMProviderClient(
            api_base_url="https://primary.example.com/v1",
            model="remote-model",
            run_dir=tmp_path,
            fallback_api_base_url="http://127.0.0.1:11434/v1",
            fallback_model="local-model",
        )

        result = client.chat_completion(MESSAGES, call_id="test_model_swap")

        # Verify the second call used the fallback model
        second_call = mock_http_post.call_args_list[1]
        payload = json.loads(second_call[1]["data"])
        assert payload["model"] == "local-model"

        # Verify the second call URL points to fallback
        assert "127.0.0.1:11434" in second_call[0][0]

    @patch("launch.clients.llm_provider.http_post")
    def test_fallback_without_model_override_uses_primary_model(self, mock_http_post, tmp_path):
        """If no fallback_model set, primary model name is kept."""
        mock_http_post.side_effect = [
            ConnectionError("Connection refused"),
            _make_success_response("fallback same model"),
        ]

        client = LLMProviderClient(
            api_base_url="https://primary.example.com/v1",
            model="shared-model",
            run_dir=tmp_path,
            fallback_api_base_url="http://127.0.0.1:11434/v1",
            # No fallback_model set
        )

        result = client.chat_completion(MESSAGES, call_id="test_no_model_swap")

        second_call = mock_http_post.call_args_list[1]
        payload = json.loads(second_call[1]["data"])
        assert payload["model"] == "shared-model"


class TestFallbackEvidence:
    """Verify evidence captures fallback metadata."""

    @patch("launch.clients.llm_provider.http_post")
    def test_evidence_records_endpoint_used_primary(self, mock_http_post, tmp_path):
        """Evidence JSON includes endpoint_used='primary' on success."""
        mock_http_post.return_value = _make_success_response("ok")

        client = LLMProviderClient(
            api_base_url="https://primary.example.com/v1",
            model="test-model",
            run_dir=tmp_path,
        )

        result = client.chat_completion(MESSAGES, call_id="test_evidence_primary")

        evidence_file = tmp_path / "evidence" / "llm_calls" / "test_evidence_primary.json"
        assert evidence_file.exists()
        evidence = json.loads(evidence_file.read_text())
        assert evidence["endpoint_used"] == "primary"
        assert "fallback_reason" not in evidence

    @patch("launch.clients.llm_provider.http_post")
    def test_evidence_records_fallback_with_reason(self, mock_http_post, tmp_path):
        """Evidence JSON includes endpoint_used='fallback' and fallback_reason."""
        mock_http_post.side_effect = [
            ConnectionError("Primary down"),
            _make_success_response("fallback ok"),
        ]

        client = LLMProviderClient(
            api_base_url="https://primary.example.com/v1",
            model="test-model",
            run_dir=tmp_path,
            fallback_api_base_url="http://127.0.0.1:11434/v1",
            fallback_model="fallback-model",
        )

        result = client.chat_completion(MESSAGES, call_id="test_evidence_fallback")

        evidence_file = tmp_path / "evidence" / "llm_calls" / "test_evidence_fallback.json"
        assert evidence_file.exists()
        evidence = json.loads(evidence_file.read_text())
        assert evidence["endpoint_used"] == "fallback"
        assert "Primary down" in evidence["fallback_reason"]


class TestBothEndpointsFail:
    """Verify behavior when both primary and fallback fail."""

    @patch("launch.clients.llm_provider.http_post")
    def test_both_fail_raises_primary_error(self, mock_http_post, tmp_path):
        """When both endpoints fail, the primary error is raised."""
        mock_http_post.side_effect = [
            ConnectionError("Primary down"),
            ConnectionError("Fallback also down"),
        ]

        client = LLMProviderClient(
            api_base_url="https://primary.example.com/v1",
            model="test-model",
            run_dir=tmp_path,
            fallback_api_base_url="http://127.0.0.1:11434/v1",
            fallback_model="fallback-model",
        )

        with pytest.raises(LLMError, match="Primary down"):
            client.chat_completion(MESSAGES, call_id="test_both_fail")


class TestApiKeyResolution:
    """Verify API key resolution priority chain."""

    def test_resolve_from_config_env(self, monkeypatch):
        """Config-specified env var takes priority."""
        monkeypatch.setenv("litellm_key", "config-key")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-key")
        assert _resolve_api_key("litellm_key") == "config-key"

    def test_resolve_fallback_to_litellm_key(self, monkeypatch):
        """litellm_key is checked when config env var is empty."""
        monkeypatch.setenv("litellm_key", "litellm-key-value")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        assert _resolve_api_key("NONEXISTENT_VAR") == "litellm-key-value"

    def test_resolve_fallback_to_anthropic(self, monkeypatch):
        """ANTHROPIC_API_KEY used when litellm_key not set."""
        monkeypatch.delenv("litellm_key", raising=False)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-key")
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        assert _resolve_api_key(None) == "anthropic-key"

    def test_resolve_fallback_to_openai(self, monkeypatch):
        """OPENAI_API_KEY used as last resort."""
        monkeypatch.delenv("litellm_key", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
        assert _resolve_api_key(None) == "openai-key"

    def test_resolve_returns_none_when_no_keys(self, monkeypatch):
        """Returns None when no API keys are set."""
        monkeypatch.delenv("litellm_key", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        assert _resolve_api_key(None) is None


class TestCreateLLMClientFromConfig:
    """Verify factory function creates clients correctly."""

    def test_basic_config(self, tmp_path, monkeypatch):
        """Factory creates client from basic llm config."""
        monkeypatch.setenv("litellm_key", "test-key")

        config = {
            "llm": {
                "api_base_url": "https://llm.example.com/v1",
                "api_key_env": "litellm_key",
                "model": "test-model",
                "request_timeout_s": 300,
                "decoding": {
                    "temperature": 0.0,
                    "max_tokens": 4096,
                },
            }
        }

        client = create_llm_client_from_config(config, tmp_path)

        assert client is not None
        assert client.api_base_url == "https://llm.example.com/v1"
        assert client.model == "test-model"
        assert client.api_key == "test-key"
        assert client.temperature == 0.0
        assert client.max_tokens == 4096
        assert client.timeout == 300

    def test_config_with_fallback(self, tmp_path, monkeypatch):
        """Factory creates client with fallback from config."""
        monkeypatch.setenv("litellm_key", "remote-key")

        config = {
            "llm": {
                "api_base_url": "https://llm.example.com/v1",
                "api_key_env": "litellm_key",
                "model": "remote-model",
                "request_timeout_s": 300,
                "decoding": {"temperature": 0.0, "max_tokens": 6000},
                "fallback": {
                    "api_base_url": "http://127.0.0.1:11434/v1",
                    "model": "local-model",
                    "request_timeout_s": 300,
                },
            }
        }

        client = create_llm_client_from_config(config, tmp_path)

        assert client is not None
        assert client.api_base_url == "https://llm.example.com/v1"
        assert client.model == "remote-model"
        assert client.fallback_api_base_url == "http://127.0.0.1:11434/v1"
        assert client.fallback_model == "local-model"

    def test_missing_llm_config_returns_none(self, tmp_path):
        """Factory returns None when llm config is missing."""
        assert create_llm_client_from_config({}, tmp_path) is None
        assert create_llm_client_from_config({"llm": {}}, tmp_path) is None

    def test_telemetry_passthrough(self, tmp_path, monkeypatch):
        """Factory passes telemetry params to client."""
        monkeypatch.setenv("litellm_key", "key")
        mock_telem = MagicMock()

        config = {
            "llm": {
                "api_base_url": "https://llm.example.com/v1",
                "api_key_env": "litellm_key",
                "model": "test",
                "decoding": {"temperature": 0.0},
            }
        }

        client = create_llm_client_from_config(
            config,
            tmp_path,
            telemetry_client=mock_telem,
            telemetry_run_id="run-001",
            telemetry_trace_id="trace-abc",
            telemetry_parent_span_id="span-xyz",
        )

        assert client.telemetry_client is mock_telem
        assert client.telemetry_run_id == "run-001"
        assert client.telemetry_trace_id == "trace-abc"
        assert client.telemetry_parent_span_id == "span-xyz"
