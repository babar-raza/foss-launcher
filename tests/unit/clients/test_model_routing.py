"""Tests for task-type model routing in LLMProviderClient."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from launcher.clients.llm_provider import LLMProviderClient, create_llm_client_from_config
from launcher.models.run_config import ModelRouting


@pytest.fixture()
def tmp_run_dir(tmp_path: Path) -> Path:
    d = tmp_path / "run"
    d.mkdir()
    return d


def _make_client(
    tmp_run_dir: Path,
    reasoning_model: str | None = None,
    routing: ModelRouting | None = None,
) -> LLMProviderClient:
    return LLMProviderClient(
        api_base_url="http://localhost:9999/v1",
        model="primary-model",
        run_dir=tmp_run_dir,
        reasoning_model=reasoning_model,
        routing=routing,
    )


class TestResolveModel:
    def test_no_task_type_returns_primary(self, tmp_run_dir: Path) -> None:
        client = _make_client(tmp_run_dir, reasoning_model="reasoning-model", routing=ModelRouting())
        assert client.resolve_model(None) == "primary-model"

    def test_no_reasoning_model_returns_primary(self, tmp_run_dir: Path) -> None:
        client = _make_client(tmp_run_dir, reasoning_model=None, routing=ModelRouting())
        assert client.resolve_model("review") == "primary-model"

    def test_no_routing_returns_primary(self, tmp_run_dir: Path) -> None:
        client = _make_client(tmp_run_dir, reasoning_model="reasoning-model", routing=None)
        assert client.resolve_model("review") == "primary-model"

    def test_extract_routes_to_standard(self, tmp_run_dir: Path) -> None:
        routing = ModelRouting(extract="standard", generate="standard", review="reasoning")
        client = _make_client(tmp_run_dir, reasoning_model="reasoning-model", routing=routing)
        assert client.resolve_model("extract") == "primary-model"

    def test_generate_routes_to_standard(self, tmp_run_dir: Path) -> None:
        routing = ModelRouting(extract="standard", generate="standard", review="reasoning")
        client = _make_client(tmp_run_dir, reasoning_model="reasoning-model", routing=routing)
        assert client.resolve_model("generate") == "primary-model"

    def test_review_routes_to_reasoning(self, tmp_run_dir: Path) -> None:
        routing = ModelRouting(extract="standard", generate="standard", review="reasoning")
        client = _make_client(tmp_run_dir, reasoning_model="reasoning-model", routing=routing)
        assert client.resolve_model("review") == "reasoning-model"

    def test_unknown_task_type_returns_primary(self, tmp_run_dir: Path) -> None:
        routing = ModelRouting()
        client = _make_client(tmp_run_dir, reasoning_model="reasoning-model", routing=routing)
        assert client.resolve_model("unknown_task") == "primary-model"

    def test_all_reasoning_routing(self, tmp_run_dir: Path) -> None:
        routing = ModelRouting(extract="reasoning", generate="reasoning", review="reasoning")
        client = _make_client(tmp_run_dir, reasoning_model="reasoning-model", routing=routing)
        assert client.resolve_model("extract") == "reasoning-model"
        assert client.resolve_model("generate") == "reasoning-model"
        assert client.resolve_model("review") == "reasoning-model"

    def test_default_routing_values(self, tmp_run_dir: Path) -> None:
        """Default ModelRouting: extract=standard, generate=standard, review=reasoning."""
        routing = ModelRouting()
        client = _make_client(tmp_run_dir, reasoning_model="reasoning-model", routing=routing)
        assert client.resolve_model("extract") == "primary-model"
        assert client.resolve_model("generate") == "primary-model"
        assert client.resolve_model("review") == "reasoning-model"


# ---------------------------------------------------------------------------
# SR-08: Evidence data integrity
# ---------------------------------------------------------------------------

_FAKE_RESPONSE = {
    "choices": [{"message": {"content": "hello"}, "finish_reason": "stop"}],
    "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
}


class TestEvidenceIntegrity:
    """SR-08: Evidence JSON must record actual_model and task_type."""

    def test_evidence_contains_routed_model(self, tmp_run_dir: Path) -> None:
        """When routing selects reasoning model, evidence 'model' must match."""
        routing = ModelRouting(review="reasoning")
        client = _make_client(tmp_run_dir, reasoning_model="reasoning-model", routing=routing)

        with patch.object(client, "_call_api", return_value=_FAKE_RESPONSE):
            result = client.chat_completion(
                [{"role": "user", "content": "test"}],
                call_id="ev-routed",
                task_type="review",
            )

        evidence_file = client.evidence_dir / "ev-routed.json"
        evidence = json.loads(evidence_file.read_text(encoding="utf-8"))
        assert evidence["model"] == "reasoning-model"

    def test_evidence_contains_primary_model_when_not_routed(self, tmp_run_dir: Path) -> None:
        """Without routing, evidence 'model' must be the primary model."""
        client = _make_client(tmp_run_dir)

        with patch.object(client, "_call_api", return_value=_FAKE_RESPONSE):
            result = client.chat_completion(
                [{"role": "user", "content": "test"}],
                call_id="ev-primary",
            )

        evidence_file = client.evidence_dir / "ev-primary.json"
        evidence = json.loads(evidence_file.read_text(encoding="utf-8"))
        assert evidence["model"] == "primary-model"

    def test_evidence_contains_task_type(self, tmp_run_dir: Path) -> None:
        """When task_type is passed, it must appear in the evidence JSON."""
        routing = ModelRouting(review="reasoning")
        client = _make_client(tmp_run_dir, reasoning_model="reasoning-model", routing=routing)

        with patch.object(client, "_call_api", return_value=_FAKE_RESPONSE):
            client.chat_completion(
                [{"role": "user", "content": "test"}],
                call_id="ev-tasktype",
                task_type="review",
            )

        evidence_file = client.evidence_dir / "ev-tasktype.json"
        evidence = json.loads(evidence_file.read_text(encoding="utf-8"))
        assert evidence["task_type"] == "review"

    def test_evidence_omits_task_type_when_none(self, tmp_run_dir: Path) -> None:
        """When task_type is not passed, it must not appear in evidence."""
        client = _make_client(tmp_run_dir)

        with patch.object(client, "_call_api", return_value=_FAKE_RESPONSE):
            client.chat_completion(
                [{"role": "user", "content": "test"}],
                call_id="ev-no-tt",
            )

        evidence_file = client.evidence_dir / "ev-no-tt.json"
        evidence = json.loads(evidence_file.read_text(encoding="utf-8"))
        assert "task_type" not in evidence


# ---------------------------------------------------------------------------
# SR-09: Routing observability (log line)
# ---------------------------------------------------------------------------

class TestRoutingObservability:
    """SR-09: Log line must appear when routing changes the model.

    The project uses structlog which writes to stdout, so we use capsys.
    """

    def test_log_emitted_when_model_routed(self, tmp_run_dir: Path, capsys) -> None:
        routing = ModelRouting(review="reasoning")
        client = _make_client(tmp_run_dir, reasoning_model="reasoning-model", routing=routing)

        with patch.object(client, "_call_api", return_value=_FAKE_RESPONSE):
            client.chat_completion(
                [{"role": "user", "content": "x"}],
                call_id="log-routed",
                task_type="review",
            )

        captured = capsys.readouterr().out
        assert "model_routing_decision" in captured
        assert "reasoning-model" in captured
        assert "routing_config" in captured

    def test_routing_log_shows_primary_default_when_model_unchanged(self, tmp_run_dir: Path, capsys) -> None:
        routing = ModelRouting(extract="standard")
        client = _make_client(tmp_run_dir, reasoning_model="reasoning-model", routing=routing)

        with patch.object(client, "_call_api", return_value=_FAKE_RESPONSE):
            client.chat_completion(
                [{"role": "user", "content": "x"}],
                call_id="log-std",
                task_type="extract",
            )

        captured = capsys.readouterr().out
        assert "model_routing_decision" in captured
        assert "primary_default" in captured

    def test_no_routing_log_when_no_task_type(self, tmp_run_dir: Path, capsys) -> None:
        routing = ModelRouting(review="reasoning")
        client = _make_client(tmp_run_dir, reasoning_model="reasoning-model", routing=routing)

        with patch.object(client, "_call_api", return_value=_FAKE_RESPONSE):
            client.chat_completion(
                [{"role": "user", "content": "x"}],
                call_id="log-none",
            )

        captured = capsys.readouterr().out
        assert "model_routing" not in captured


# ---------------------------------------------------------------------------
# SR-10: Factory + payload + edge case tests
# ---------------------------------------------------------------------------

class TestFactoryRouting:
    """SR-10: create_llm_client_from_config with routing."""

    def test_factory_with_routing_config(self, tmp_run_dir: Path) -> None:
        cfg = {
            "llm": {
                "primary": {"base_url": "http://x/v1", "model": "qwen3-next"},
                "reasoning": {"model": "recommended"},
                "routing": {"extract": "standard", "review": "reasoning"},
            }
        }
        client = create_llm_client_from_config(cfg, tmp_run_dir)
        assert client is not None
        assert client._reasoning_model == "recommended"
        assert client._routing.review == "reasoning"
        assert client._routing.extract == "standard"

    def test_factory_default_routing_when_reasoning_only(self, tmp_run_dir: Path) -> None:
        """Config has reasoning block but no routing → default ModelRouting applied."""
        cfg = {
            "llm": {
                "primary": {"base_url": "http://x/v1", "model": "qwen3-next"},
                "reasoning": {"model": "recommended"},
            }
        }
        client = create_llm_client_from_config(cfg, tmp_run_dir)
        assert client is not None
        assert client._reasoning_model == "recommended"
        assert client._routing is not None
        assert client._routing.review == "reasoning"  # default
        assert client._routing.extract == "standard"  # default

    def test_factory_no_routing_no_reasoning(self, tmp_run_dir: Path) -> None:
        """Config with neither routing nor reasoning → both None."""
        cfg = {
            "llm": {
                "primary": {"base_url": "http://x/v1", "model": "qwen3-next"},
            }
        }
        client = create_llm_client_from_config(cfg, tmp_run_dir)
        assert client is not None
        assert client._reasoning_model is None
        assert client._routing is None


class TestPayloadModel:
    """SR-10: Verify the resolved model ends up in the HTTP request payload."""

    def test_review_payload_uses_reasoning_model(self, tmp_run_dir: Path) -> None:
        routing = ModelRouting(review="reasoning")
        client = _make_client(tmp_run_dir, reasoning_model="reasoning-model", routing=routing)

        captured_payload = {}

        def mock_call_api(payload, timeout=None):
            captured_payload.update(payload)
            return _FAKE_RESPONSE

        with patch.object(client, "_call_api", side_effect=mock_call_api):
            client.chat_completion(
                [{"role": "user", "content": "test"}],
                call_id="payload-review",
                task_type="review",
            )

        assert captured_payload["model"] == "reasoning-model"

    def test_extract_payload_uses_primary_model(self, tmp_run_dir: Path) -> None:
        routing = ModelRouting(extract="standard")
        client = _make_client(tmp_run_dir, reasoning_model="reasoning-model", routing=routing)

        captured_payload = {}

        def mock_call_api(payload, timeout=None):
            captured_payload.update(payload)
            return _FAKE_RESPONSE

        with patch.object(client, "_call_api", side_effect=mock_call_api):
            client.chat_completion(
                [{"role": "user", "content": "test"}],
                call_id="payload-extract",
                task_type="extract",
            )

        assert captured_payload["model"] == "primary-model"


# ---------------------------------------------------------------------------
# SR-11: Code quality — warning for misconfigured routing
# ---------------------------------------------------------------------------

class TestRoutingMisconfigWarning:
    """SR-11: Warning when routing→reasoning but reasoning_model is None."""

    def test_warning_when_reasoning_model_missing(self, tmp_run_dir: Path, capsys) -> None:
        """Routing says review→reasoning but no reasoning_model — must warn and use primary."""
        routing = ModelRouting(review="reasoning")
        client = _make_client(tmp_run_dir, reasoning_model=None, routing=routing)

        result = client.resolve_model("review")
        assert result == "primary-model"

        captured = capsys.readouterr().out
        assert "routing_misconfigured" in captured
        assert "review" in captured

    def test_no_warning_when_properly_configured(self, tmp_run_dir: Path, capsys) -> None:
        """Routing says review→reasoning with reasoning_model set — no warning."""
        routing = ModelRouting(review="reasoning")
        client = _make_client(tmp_run_dir, reasoning_model="reasoning-model", routing=routing)

        result = client.resolve_model("review")
        assert result == "reasoning-model"

        captured = capsys.readouterr().out
        assert "routing_misconfigured" not in captured

    def test_no_warning_for_standard_routing(self, tmp_run_dir: Path, capsys) -> None:
        """Routing says extract→standard — no warning even without reasoning_model."""
        routing = ModelRouting(extract="standard")
        client = _make_client(tmp_run_dir, reasoning_model=None, routing=routing)

        result = client.resolve_model("extract")
        assert result == "primary-model"

        captured = capsys.readouterr().out
        assert "routing_misconfigured" not in captured


class TestTaskTypeContentTypeMap:
    """TC-4224: _TASK_TYPE_CONTENT_TYPE must include 'advisor' → 'json_object'."""

    def test_advisor_maps_to_json_object(self):
        from launcher.clients.llm_provider import _TASK_TYPE_CONTENT_TYPE
        assert _TASK_TYPE_CONTENT_TYPE.get("advisor") == "json_object"

    def test_generate_maps_to_json_array(self):
        from launcher.clients.llm_provider import _TASK_TYPE_CONTENT_TYPE
        assert _TASK_TYPE_CONTENT_TYPE.get("generate") == "json_array"

    def test_review_maps_to_json_object(self):
        from launcher.clients.llm_provider import _TASK_TYPE_CONTENT_TYPE
        assert _TASK_TYPE_CONTENT_TYPE.get("review") == "json_object"

    def test_unknown_task_type_absent_from_map(self):
        from launcher.clients.llm_provider import _TASK_TYPE_CONTENT_TYPE
        assert "unknown_type" not in _TASK_TYPE_CONTENT_TYPE
