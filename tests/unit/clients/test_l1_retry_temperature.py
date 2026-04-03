"""TC-L1-02 — Unit tests for temperature escalation in the L1 retry loop.

Verifies:
  1. Temperature bumps +0.1 per retry attempt (capped at 0.3).
  2. L1_EMPTY_RESPONSE is logged when the LLM returns an empty string.
  3. Temperature does not exceed 0.3 even when base is already high.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from launcher.clients.llm_provider import LLMProviderClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_provider(tmp_path: Path, temperature: float = 0.0) -> LLMProviderClient:
    return LLMProviderClient(
        api_base_url="http://test:8000/v1",
        model="test-model",
        run_dir=tmp_path,
        api_key="test-key",
        temperature=temperature,
    )


def _response(content: str) -> dict:
    return {
        "choices": [{"message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }


_VALID_JSON = json.dumps([{"type": "paragraph", "content": "Hello.", "claim_ids": []}])
_MESSAGES = [{"role": "user", "content": "Write something."}]


# ---------------------------------------------------------------------------
# SR-03-T1: temperature escalates on retries
# ---------------------------------------------------------------------------

def test_temperature_escalates_on_retry(tmp_path: Path) -> None:
    """Retry attempts must use T=0.1 and T=0.2 when base T=0.0."""
    provider = _make_provider(tmp_path, temperature=0.0)
    captured_payloads: list[dict] = []

    def fake_call_api(request_payload, timeout=None):
        captured_payloads.append(dict(request_payload))
        attempt = len(captured_payloads)
        if attempt < 3:
            return _response("")  # empty → L1 fail
        return _response(_VALID_JSON)

    with patch.object(provider, "_call_api", side_effect=fake_call_api):
        provider.chat_completion(_MESSAGES, task_type="generate")

    assert len(captured_payloads) == 3, f"Expected 3 calls, got {len(captured_payloads)}"
    assert captured_payloads[0]["temperature"] == 0.0, "First attempt must use base T=0.0"
    assert abs(captured_payloads[1]["temperature"] - 0.1) < 1e-9, (
        f"Second attempt must use T=0.1, got {captured_payloads[1]['temperature']}"
    )
    assert abs(captured_payloads[2]["temperature"] - 0.2) < 1e-9, (
        f"Third attempt must use T=0.2, got {captured_payloads[2]['temperature']}"
    )


# ---------------------------------------------------------------------------
# SR-03-T2: L1_EMPTY_RESPONSE is logged for empty responses
# ---------------------------------------------------------------------------

def test_l1_empty_response_logged(tmp_path: Path) -> None:
    """L1_EMPTY_RESPONSE must be emitted (via structlog) when LLM returns empty string."""
    import launcher.clients.llm_provider as _mod

    provider = _make_provider(tmp_path)
    logged_events: list[str] = []

    _orig_warning = _mod.logger.warning

    def _capture(event, *args, **kwargs):
        logged_events.append(str(event))
        return _orig_warning(event, *args, **kwargs)

    def fake_call_api(request_payload, timeout=None):
        return _response("")  # always empty

    with (
        patch.object(provider, "_call_api", side_effect=fake_call_api),
        patch.object(_mod.logger, "warning", side_effect=_capture),
    ):
        provider.chat_completion(_MESSAGES, task_type="generate")

    assert any("L1_EMPTY_RESPONSE" in e for e in logged_events), (
        f"Expected L1_EMPTY_RESPONSE in logged events. Got: {logged_events}"
    )


# ---------------------------------------------------------------------------
# SR-03-T3: temperature cap at 0.3
# ---------------------------------------------------------------------------

def test_temperature_capped_at_0_3(tmp_path: Path) -> None:
    """Even with base T=0.3, retries must not exceed 0.3."""
    provider = _make_provider(tmp_path, temperature=0.3)
    captured_payloads: list[dict] = []

    def fake_call_api(request_payload, timeout=None):
        captured_payloads.append(dict(request_payload))
        attempt = len(captured_payloads)
        if attempt < 3:
            return _response("")
        return _response(_VALID_JSON)

    with patch.object(provider, "_call_api", side_effect=fake_call_api):
        provider.chat_completion(_MESSAGES, task_type="generate")

    for i, payload in enumerate(captured_payloads):
        assert payload["temperature"] <= 0.3, (
            f"Attempt {i+1} temperature {payload['temperature']} exceeds cap 0.3"
        )
