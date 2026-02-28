"""Tests for guardrailed LLM planner (TC-3030)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from launch.autopilot.llm_planner import (
    PlannerSuggestion,
    _validate_suggestion,
    build_planner_context,
    plan_with_llm,
)


class TestValidateSuggestion:
    """Core guardrail logic tests."""

    def test_earlier_worker_accepted(self) -> None:
        raw = {"suggested_start_worker": "W1", "rationale": "Facts look thin"}
        result = _validate_suggestion(raw, baseline_start_worker="W5")
        assert result is not None
        assert result.suggested_start_worker == "W1"
        assert result.guardrail_applied is False

    def test_equal_worker_accepted(self) -> None:
        raw = {"suggested_start_worker": "W5", "rationale": "Agree with baseline"}
        result = _validate_suggestion(raw, baseline_start_worker="W5")
        assert result is not None
        assert result.suggested_start_worker == "W5"
        assert result.guardrail_applied is False

    def test_later_worker_rejected(self) -> None:
        """HARD CONSTRAINT: LLM cannot skip past baseline."""
        raw = {"suggested_start_worker": "W9", "rationale": "Skip to validation"}
        result = _validate_suggestion(raw, baseline_start_worker="W5")
        assert result is not None
        assert result.suggested_start_worker == "W5"  # Reverted to baseline
        assert result.guardrail_applied is True
        assert "REJECTED_LATER_THAN_BASELINE" in result.rationale

    def test_invalid_worker_returns_none(self) -> None:
        raw = {"suggested_start_worker": "W99"}
        result = _validate_suggestion(raw, baseline_start_worker="W5")
        assert result is None

    def test_missing_worker_returns_none(self) -> None:
        raw = {"rationale": "no worker specified"}
        result = _validate_suggestion(raw, baseline_start_worker="W5")
        assert result is None

    def test_toggles_propagated(self) -> None:
        raw = {
            "suggested_start_worker": "W1",
            "toggles": {"heal_mode": True, "regen_failed_only": True},
            "rationale": "Full rerun in heal mode",
        }
        result = _validate_suggestion(raw, baseline_start_worker="W5")
        assert result is not None
        assert result.toggles == {"heal_mode": True, "regen_failed_only": True}

    def test_non_dict_toggles_defaulted(self) -> None:
        raw = {"suggested_start_worker": "W1", "toggles": "invalid"}
        result = _validate_suggestion(raw, baseline_start_worker="W5")
        assert result is not None
        assert result.toggles == {}


class TestPlanWithLlm:
    """Integration tests with mocked LLM client."""

    def test_none_client_returns_none(self) -> None:
        result = plan_with_llm(None, "W5", "context")
        assert result is None

    def test_chat_client_valid_response(self) -> None:
        client = MagicMock()
        client.chat.return_value = '{"suggested_start_worker": "W3", "rationale": "rerun facts"}'
        result = plan_with_llm(client, "W5", "context")
        assert result is not None
        assert result.suggested_start_worker == "W3"

    def test_complete_client_valid_response(self) -> None:
        client = MagicMock(spec=[])  # No chat attr
        client.complete = MagicMock(return_value='{"suggested_start_worker": "W1"}')
        result = plan_with_llm(client, "W5", "context")
        assert result is not None
        assert result.suggested_start_worker == "W1"

    def test_invalid_json_returns_none(self) -> None:
        client = MagicMock()
        client.chat.return_value = "NOT JSON AT ALL"
        result = plan_with_llm(client, "W5", "context")
        assert result is None

    def test_markdown_fenced_json_parsed(self) -> None:
        client = MagicMock()
        client.chat.return_value = '```json\n{"suggested_start_worker": "W4", "rationale": "ok"}\n```'
        result = plan_with_llm(client, "W5", "context")
        assert result is not None
        assert result.suggested_start_worker == "W4"

    def test_client_exception_returns_none(self) -> None:
        client = MagicMock()
        client.chat.side_effect = ConnectionError("timeout")
        result = plan_with_llm(client, "W5", "context")
        assert result is None

    def test_later_than_baseline_guardrailed(self) -> None:
        client = MagicMock()
        client.chat.return_value = '{"suggested_start_worker": "W9"}'
        result = plan_with_llm(client, "W5", "context")
        assert result is not None
        assert result.suggested_start_worker == "W5"  # Guardrailed to baseline
        assert result.guardrail_applied is True


class TestBuildPlannerContext:
    def test_context_contains_baseline(self) -> None:
        ctx = build_planner_context("W5", "abc123def456", ["repo_inventory.json"])
        assert "W5" in ctx
        assert "abc123def456" in ctx

    def test_context_includes_validation(self) -> None:
        ctx = build_planner_context(
            "W10", "sha", [],
            validation_summary={"fixable_count": 3},
        )
        assert "fixable_count" in ctx
