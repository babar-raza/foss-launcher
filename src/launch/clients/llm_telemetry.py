"""LLM telemetry context manager for automatic tracking of LLM API calls.

Binding contract:
- specs/16_local_telemetry_api.md (LLM Call Telemetry section)
- specs/11_state_and_events.md (LLM event types)
- specs/21_worker_contracts.md (Telemetry Requirements)

ALL telemetry operations MUST be non-fatal (hard requirement):
- Exceptions logged as warnings, NEVER raised
- Operations continue even if telemetry fails
- No raise statements in telemetry code paths
"""

from __future__ import annotations

import hashlib
import time
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from ..models.event import (
    Event,
    EVENT_LLM_CALL_STARTED,
    EVENT_LLM_CALL_FINISHED,
    EVENT_LLM_CALL_FAILED,
)
from ..state.event_log import append_event, generate_span_id
from ..util.logging import get_logger
from .telemetry import TelemetryClient, TelemetryError

logger = get_logger()


# Model pricing (as of 2026-02-07, per specs/16_local_telemetry_api.md)
MODEL_PRICING = {
    "claude-sonnet-4-5": {"input": 3.00, "output": 15.00},  # per MTok
    "claude-sonnet-4.5": {"input": 3.00, "output": 15.00},
    "claude-opus-4": {"input": 15.00, "output": 75.00},
    "claude-opus-4-6": {"input": 15.00, "output": 75.00},
    "claude-haiku-4-5": {"input": 0.80, "output": 4.00},
    "claude-haiku-4.5": {"input": 0.80, "output": 4.00},
    # Add OpenAI models if needed
    "gpt-4": {"input": 30.00, "output": 60.00},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
}


def calculate_api_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> float:
    """Calculate API cost in USD based on model pricing.

    Args:
        model: Model name (e.g., "claude-sonnet-4-5")
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens

    Returns:
        Cost in USD (0.0 if model pricing unknown)

    Spec reference: specs/16_local_telemetry_api.md (Cost Calculation section)
    """
    # Normalize model name for lookup
    model_key = model.lower().strip()

    if model_key not in MODEL_PRICING:
        # Unknown model, return 0 cost
        return 0.0

    pricing = MODEL_PRICING[model_key]
    input_cost = (input_tokens * pricing["input"]) / 1_000_000
    output_cost = (output_tokens * pricing["output"]) / 1_000_000

    return round(input_cost + output_cost, 6)


class LLMTelemetryContext:
    """Context manager for automatic LLM call telemetry tracking.

    Usage:
        with LLMTelemetryContext(
            telemetry_client=client,
            event_log_path=events_file,
            call_id="section_writer_my-page",
            run_id="run-001",
            trace_id="abc123",
            parent_span_id="def456",
            model="claude-sonnet-4-5",
        ) as telemetry:
            # Make LLM API call
            result = llm_api_call()

            # Record token usage
            telemetry.record_usage(result["usage"])

    Features:
    - Automatically creates telemetry run on __enter__
    - Automatically updates telemetry run on __exit__
    - Emits LLM_CALL_STARTED/FINISHED/FAILED events
    - Calculates API costs
    - Graceful degradation (NEVER crashes on telemetry failures)

    Spec reference: specs/16_local_telemetry_api.md (LLM Call Telemetry)
    """

    def __init__(
        self,
        telemetry_client: Optional[TelemetryClient],
        event_log_path: Optional[Path],
        call_id: str,
        run_id: str,
        trace_id: str,
        parent_span_id: str,
        model: str,
        temperature: float = 0.0,
        max_tokens: int = 4096,
        prompt_hash: Optional[str] = None,
        evidence_path: Optional[str] = None,
    ):
        """Initialize LLM telemetry context.

        Args:
            telemetry_client: Optional TelemetryClient (None = no telemetry API tracking)
            event_log_path: Optional path to events.ndjson (None = no event emission)
            call_id: Stable call identifier (used in run_id and evidence naming)
            run_id: Parent run_id for hierarchical tracking
            trace_id: Trace ID for correlation
            parent_span_id: Parent span ID for hierarchical tracking
            model: Model name (e.g., "claude-sonnet-4-5")
            temperature: Sampling temperature (default: 0.0)
            max_tokens: Maximum tokens to generate (default: 4096)
            prompt_hash: Optional SHA256 hash of prompt
            evidence_path: Optional path to evidence file (relative to run_dir)
        """
        self.telemetry_client = telemetry_client
        self.event_log_path = event_log_path
        self.call_id = call_id
        self.run_id = run_id
        self.trace_id = trace_id
        self.parent_span_id = parent_span_id
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.prompt_hash = prompt_hash or ""
        self.evidence_path = evidence_path

        # Generate span ID for this LLM call
        self.span_id = generate_span_id()

        # Generate event ID for telemetry run (idempotency key)
        self.event_id = str(uuid.uuid4())

        # Track timing
        self.start_time_ts = None
        self.start_time_iso = None
        self.end_time_iso = None
        self.duration_ms = None

        # Track token usage (populated by record_usage())
        self.usage: Optional[Dict[str, Any]] = None

        # Track error (populated in __exit__ on exception)
        self.error: Optional[Exception] = None

    def __enter__(self) -> LLMTelemetryContext:
        """Start telemetry tracking.

        Creates telemetry run and emits LLM_CALL_STARTED event.
        ALL exceptions are caught and logged (graceful degradation).

        Returns:
            Self for context manager protocol
        """
        self.start_time_ts = time.time()
        self.start_time_iso = datetime.now(timezone.utc).isoformat()

        # Build telemetry run_id: {parent_run_id}-llm-{call_id}
        telemetry_run_id = f"{self.run_id}-llm-{self.call_id}"

        # Create telemetry run (POST /api/v1/runs)
        if self.telemetry_client:
            try:
                context_json = {
                    "trace_id": self.trace_id,
                    "span_id": self.span_id,
                    "parent_span_id": self.parent_span_id,
                    "call_id": self.call_id,
                    "model": self.model,
                    "temperature": self.temperature,
                    "max_tokens": self.max_tokens,
                    "prompt_hash": self.prompt_hash,
                }

                if self.evidence_path:
                    context_json["evidence_path"] = self.evidence_path

                self.telemetry_client.create_run(
                    run_id=telemetry_run_id,
                    agent_name=f"launch.llm.{self.call_id[:30]}",  # Truncate for readability
                    job_type="llm_call",
                    start_time=self.start_time_iso,
                    event_id=self.event_id,
                    parent_run_id=self.run_id,
                    status="running",
                    context_json=context_json,
                )
            except TelemetryError as e:
                # HARD WARNING: Log but NEVER raise
                logger.warning(
                    "llm_telemetry_create_run_failed",
                    call_id=self.call_id,
                    error=str(e),
                )
            except Exception as e:
                # HARD WARNING: Log but NEVER raise
                logger.warning(
                    "llm_telemetry_create_run_unexpected_error",
                    call_id=self.call_id,
                    error=str(e),
                )

        # Emit LLM_CALL_STARTED event
        if self.event_log_path:
            try:
                event = Event(
                    event_id=str(uuid.uuid4()),
                    run_id=self.run_id,
                    ts=self.start_time_iso,
                    type=EVENT_LLM_CALL_STARTED,
                    payload={
                        "call_id": self.call_id,
                        "model": self.model,
                        "provider_base_url": "",  # Populated by caller if needed
                        "prompt_hash": self.prompt_hash,
                        "temperature": self.temperature,
                        "max_tokens": self.max_tokens,
                    },
                    trace_id=self.trace_id,
                    span_id=self.span_id,
                    parent_span_id=self.parent_span_id,
                )

                # Ensure parent directory exists
                self.event_log_path.parent.mkdir(parents=True, exist_ok=True)

                append_event(self.event_log_path, event)
            except Exception as e:
                # HARD WARNING: Log but NEVER raise
                logger.warning(
                    "llm_telemetry_event_emission_failed",
                    event_type="LLM_CALL_STARTED",
                    call_id=self.call_id,
                    error=str(e),
                )

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Complete telemetry tracking.

        Updates telemetry run and emits LLM_CALL_FINISHED or LLM_CALL_FAILED event.
        ALL exceptions are caught and logged (graceful degradation).

        Args:
            exc_type: Exception type (if exception occurred)
            exc_val: Exception value (if exception occurred)
            exc_tb: Exception traceback (if exception occurred)

        Returns:
            False (do not suppress exceptions from user code)
        """
        self.end_time_iso = datetime.now(timezone.utc).isoformat()
        self.duration_ms = int((time.time() - self.start_time_ts) * 1000)

        # Determine success/failure
        success = exc_type is None

        # Update telemetry run (PATCH /api/v1/runs/{event_id})
        if self.telemetry_client:
            try:
                if success and self.usage:
                    # Success: report metrics
                    metrics_json = {
                        "input_tokens": self.usage.get("input_tokens", 0),
                        "output_tokens": self.usage.get("output_tokens", 0),
                        "prompt_tokens": self.usage.get("prompt_tokens", 0),
                        "completion_tokens": self.usage.get("completion_tokens", 0),
                        "total_tokens": self.usage.get("total_tokens", 0),
                        "finish_reason": self.usage.get("finish_reason", "stop"),
                    }

                    # Calculate cost
                    input_tokens = self.usage.get("input_tokens", 0)
                    output_tokens = self.usage.get("output_tokens", 0)
                    cost_usd = calculate_api_cost(self.model, input_tokens, output_tokens)
                    if cost_usd > 0:
                        metrics_json["api_cost_usd"] = cost_usd

                    self.telemetry_client.update_run(
                        event_id=self.event_id,
                        status="success",
                        end_time=self.end_time_iso,
                        duration_ms=self.duration_ms,
                        metrics_json=metrics_json,
                    )
                else:
                    # Failure: report error
                    error_summary = str(exc_val) if exc_val else "Unknown error"
                    error_details = "".join(traceback.format_exception(exc_type, exc_val, exc_tb)) if exc_tb else ""

                    self.telemetry_client.update_run(
                        event_id=self.event_id,
                        status="failure",
                        end_time=self.end_time_iso,
                        duration_ms=self.duration_ms,
                        error_summary=error_summary[:500],  # Truncate for summary
                    )
            except TelemetryError as e:
                # HARD WARNING: Log but NEVER raise
                logger.warning(
                    "llm_telemetry_update_run_failed",
                    call_id=self.call_id,
                    error=str(e),
                )
            except Exception as e:
                # HARD WARNING: Log but NEVER raise
                logger.warning(
                    "llm_telemetry_update_run_unexpected_error",
                    call_id=self.call_id,
                    error=str(e),
                )

        # Emit LLM_CALL_FINISHED or LLM_CALL_FAILED event
        if self.event_log_path:
            try:
                if success and self.usage:
                    # Success event
                    event = Event(
                        event_id=str(uuid.uuid4()),
                        run_id=self.run_id,
                        ts=self.end_time_iso,
                        type=EVENT_LLM_CALL_FINISHED,
                        payload={
                            "call_id": self.call_id,
                            "latency_ms": self.duration_ms,
                            "token_usage": {
                                "input_tokens": self.usage.get("input_tokens", 0),
                                "output_tokens": self.usage.get("output_tokens", 0),
                                "total_tokens": self.usage.get("total_tokens", 0),
                            },
                            "finish_reason": self.usage.get("finish_reason", "stop"),
                            "output_hash": self.usage.get("output_hash", ""),
                            "api_cost_usd": calculate_api_cost(
                                self.model,
                                self.usage.get("input_tokens", 0),
                                self.usage.get("output_tokens", 0),
                            ),
                        },
                        trace_id=self.trace_id,
                        span_id=self.span_id,
                        parent_span_id=self.parent_span_id,
                    )
                else:
                    # Failure event
                    error_class = exc_type.__name__ if exc_type else "UnknownError"
                    error_summary = str(exc_val) if exc_val else "Unknown error"
                    error_details = "".join(traceback.format_exception(exc_type, exc_val, exc_tb)) if exc_tb else ""

                    # Determine if error is retryable (network/timeout errors)
                    retryable = error_class in ["HTTPError", "TimeoutError", "ConnectionError", "RequestException"]

                    event = Event(
                        event_id=str(uuid.uuid4()),
                        run_id=self.run_id,
                        ts=self.end_time_iso,
                        type=EVENT_LLM_CALL_FAILED,
                        payload={
                            "call_id": self.call_id,
                            "latency_ms": self.duration_ms,
                            "error_class": error_class,
                            "error_summary": error_summary[:500],  # Truncate
                            "retryable": retryable,
                            "error_details": error_details[:5000],  # Truncate
                        },
                        trace_id=self.trace_id,
                        span_id=self.span_id,
                        parent_span_id=self.parent_span_id,
                    )

                append_event(self.event_log_path, event)
            except Exception as e:
                # HARD WARNING: Log but NEVER raise
                logger.warning(
                    "llm_telemetry_event_emission_failed",
                    event_type="LLM_CALL_FINISHED" if success else "LLM_CALL_FAILED",
                    call_id=self.call_id,
                    error=str(e),
                )

        # Return False to not suppress user exceptions
        return False

    def record_usage(self, usage: Dict[str, Any]) -> None:
        """Record token usage from LLM response.

        Call this method after receiving LLM response to record token counts.

        Args:
            usage: Usage dictionary from LLM response, containing:
                - input_tokens: int
                - output_tokens: int
                - total_tokens: int
                - finish_reason: str (optional)
                - output_hash: str (optional, SHA256 of output)

        Spec reference: specs/16_local_telemetry_api.md (metrics_json Structure)
        """
        self.usage = usage
