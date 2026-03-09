"""TC-3918: Unit tests for pipeline advisor — no live LLM calls."""
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from launcher.models.evaluation import PipelineAdvice
from launcher.orchestrator.pipeline_advisor import (
    _parse_advice,
    _static_fallback,
    call_pipeline_advisor,
)


# ---------------------------------------------------------------------------
# PipelineAdvice model validation
# ---------------------------------------------------------------------------

def test_valid_routing_publish_roundtrips():
    advice = PipelineAdvice(
        routing="publish",
        analysis="No critical findings.",
        confidence=0.9,
        target_pages=["intro"],
        strategy="",
        priority_checks=[],
        stop_reason=None,
    )
    dumped = advice.model_dump()
    recovered = PipelineAdvice.model_validate(dumped)
    assert recovered.routing == "publish"
    assert recovered.confidence == 0.9


def test_invalid_routing_raises():
    with pytest.raises(ValidationError):
        PipelineAdvice(
            routing="heal_upstream",  # not in Literal
            analysis="x",
            confidence=0.8,
        )


def test_confidence_out_of_range_raises():
    with pytest.raises(ValidationError):
        PipelineAdvice(
            routing="stop",
            analysis="x",
            confidence=1.5,  # > 1.0
        )


# ---------------------------------------------------------------------------
# _parse_advice
# ---------------------------------------------------------------------------

def test_parse_advice_low_confidence_returns_none():
    import json
    data = {
        "routing": "heal_generate",
        "analysis": "low confidence test",
        "confidence": 0.5,  # below 0.6
        "target_pages": [],
        "strategy": "",
        "priority_checks": [],
        "stop_reason": None,
    }
    result = _parse_advice(json.dumps(data))
    assert result is None


def test_parse_advice_strips_json_fences():
    import json
    data = {
        "routing": "heal_generate",
        "analysis": "fence stripping test",
        "confidence": 0.8,
        "target_pages": [],
        "strategy": "",
        "priority_checks": [],
        "stop_reason": None,
    }
    fenced = f"```json\n{json.dumps(data)}\n```"
    result = _parse_advice(fenced)
    assert result is not None
    assert result.routing == "heal_generate"


# ---------------------------------------------------------------------------
# _static_fallback
# ---------------------------------------------------------------------------

def test_static_fallback_below_ceiling():
    result = _static_fallback(0, 2)
    assert result.routing == "heal_generate"


def test_static_fallback_at_ceiling():
    result = _static_fallback(2, 2)
    assert result.routing == "stop"


# ---------------------------------------------------------------------------
# call_pipeline_advisor — LLM unavailable
# ---------------------------------------------------------------------------

def test_call_advisor_llm_unavailable(tmp_path):
    from unittest.mock import MagicMock
    # Build a minimal mock EvaluationReport
    mock_report = MagicMock()
    mock_report.model_dump.return_value = {
        "verdict": "NO_GO",
        "critical_count": 1,
        "high_count": 2,
        "pages_reviewed": 5,
        "ab_rate": 0.2,
        "df_rate": 0.6,
        "findings": [],
    }

    with patch(
        "launcher.orchestrator.pipeline_advisor._call_llm",
        return_value=None,
    ):
        result = call_pipeline_advisor(mock_report, 0, 2, tmp_path)

    assert isinstance(result, PipelineAdvice)
    assert result.routing == "heal_generate"
