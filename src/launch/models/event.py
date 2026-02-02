"""Event model for append-only event log.

Events power replay/resume per specs/11_state_and_events.md.

Spec references:
- specs/11_state_and_events.md (Event log fields and types)
- specs/schemas/event.schema.json (Schema definition)
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .base import BaseModel


class Event(BaseModel):
    """Represents a state transition or worker event.

    Events are written to runs/<run_id>/events.ndjson in append-only fashion.
    Each event validates against specs/schemas/event.schema.json.

    Spec reference: specs/11_state_and_events.md:62-73
    """

    def __init__(
        self,
        event_id: str,
        run_id: str,
        ts: str,
        type: str,
        payload: Dict[str, Any],
        trace_id: str,
        span_id: str,
        parent_span_id: Optional[str] = None,
        prev_hash: Optional[str] = None,
        event_hash: Optional[str] = None,
    ):
        """Initialize Event.

        Args:
            event_id: Unique event identifier
            run_id: Run identifier
            ts: ISO8601 timestamp with timezone
            type: Event type (e.g., RUN_CREATED, WORK_ITEM_STARTED)
            payload: Event payload dictionary
            trace_id: Trace ID for telemetry correlation (required)
            span_id: Span ID for telemetry correlation (required)
            parent_span_id: Parent span ID (optional)
            prev_hash: Hash of previous event (optional, for chain validation)
            event_hash: Hash of this event (optional, for chain validation)
        """
        self.event_id = event_id
        self.run_id = run_id
        self.ts = ts
        self.type = type
        self.payload = payload
        self.trace_id = trace_id
        self.span_id = span_id
        self.parent_span_id = parent_span_id
        self.prev_hash = prev_hash
        self.event_hash = event_hash

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary with stable field ordering.

        Field order matches schema definition for consistency.
        """
        result: Dict[str, Any] = {
            "event_id": self.event_id,
            "run_id": self.run_id,
            "ts": self.ts,
            "type": self.type,
            "payload": self.payload,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
        }

        # Optional fields included only if present
        if self.parent_span_id is not None:
            result["parent_span_id"] = self.parent_span_id
        if self.prev_hash is not None:
            result["prev_hash"] = self.prev_hash
        if self.event_hash is not None:
            result["event_hash"] = self.event_hash

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Event:
        """Deserialize from dictionary.

        Args:
            data: Dictionary matching event.schema.json

        Returns:
            Event instance
        """
        return cls(
            event_id=data["event_id"],
            run_id=data["run_id"],
            ts=data["ts"],
            type=data["type"],
            payload=data["payload"],
            trace_id=data["trace_id"],
            span_id=data["span_id"],
            parent_span_id=data.get("parent_span_id"),
            prev_hash=data.get("prev_hash"),
            event_hash=data.get("event_hash"),
        )


# Event type constants (binding per specs/11_state_and_events.md:75-89)
EVENT_RUN_CREATED = "RUN_CREATED"
EVENT_INPUTS_CLONED = "INPUTS_CLONED"
EVENT_ARTIFACT_WRITTEN = "ARTIFACT_WRITTEN"
EVENT_WORK_ITEM_QUEUED = "WORK_ITEM_QUEUED"
EVENT_WORK_ITEM_STARTED = "WORK_ITEM_STARTED"
EVENT_WORK_ITEM_FINISHED = "WORK_ITEM_FINISHED"
EVENT_GATE_RUN_STARTED = "GATE_RUN_STARTED"
EVENT_GATE_RUN_FINISHED = "GATE_RUN_FINISHED"
EVENT_ISSUE_OPENED = "ISSUE_OPENED"
EVENT_ISSUE_RESOLVED = "ISSUE_RESOLVED"
EVENT_RUN_STATE_CHANGED = "RUN_STATE_CHANGED"
EVENT_PR_OPENED = "PR_OPENED"
EVENT_RUN_COMPLETED = "RUN_COMPLETED"
EVENT_RUN_FAILED = "RUN_FAILED"

# LLM event types (binding per specs/11_state_and_events.md:91-94)
EVENT_LLM_CALL_STARTED = "LLM_CALL_STARTED"
EVENT_LLM_CALL_FINISHED = "LLM_CALL_FINISHED"
EVENT_LLM_CALL_FAILED = "LLM_CALL_FAILED"

# Taskcard event types (Layer 1 enforcement)
EVENT_TASKCARD_VALIDATED = "TASKCARD_VALIDATED"
