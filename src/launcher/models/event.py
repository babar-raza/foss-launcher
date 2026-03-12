from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import ConfigDict, Field, model_validator

from .base import LauncherBaseModel


class EventType(str, Enum):
    """Pipeline event types emitted during a run."""

    run_created = "run_created"
    run_state_changed = "run_state_changed"
    worker_started = "worker_started"
    worker_completed = "worker_completed"
    checkpoint_written = "checkpoint_written"
    llm_call_started = "llm_call_started"
    llm_call_completed = "llm_call_completed"
    llm_call_failed = "llm_call_failed"
    gate_executed = "gate_executed"
    re_run_triggered = "re_run_triggered"
    artifact_written = "artifact_written"
    gate_run_finished = "gate_run_finished"
    issue_opened = "issue_opened"
    issue_resolved = "issue_resolved"
    work_item_queued = "work_item_queued"
    work_item_started = "work_item_started"
    work_item_finished = "work_item_finished"
    run_failed = "run_failed"
    intake_scan_complete = "intake_scan_complete"
    intake_onboard_complete = "intake_onboard_complete"
    HEAL_SESSION_STARTED = "heal_session_started"
    HEAL_STEP_STARTED = "heal_step_started"
    HEAL_STEP_COMPLETED = "heal_step_completed"
    HEAL_SESSION_COMPLETED = "heal_session_completed"


# String constants for backwards compat with v1-style imports
EVENT_LLM_CALL_STARTED = "llm_call_started"
EVENT_LLM_CALL_FINISHED = "llm_call_completed"
EVENT_LLM_CALL_FAILED = "llm_call_failed"
EVENT_RUN_CREATED = "run_created"
EVENT_RUN_STATE_CHANGED = "run_state_changed"
EVENT_ARTIFACT_WRITTEN = "artifact_written"
EVENT_GATE_RUN_FINISHED = "gate_run_finished"
EVENT_ISSUE_OPENED = "issue_opened"
EVENT_ISSUE_RESOLVED = "issue_resolved"
EVENT_WORK_ITEM_QUEUED = "work_item_queued"
EVENT_WORK_ITEM_STARTED = "work_item_started"
EVENT_WORK_ITEM_FINISHED = "work_item_finished"


class Event(LauncherBaseModel):
    """A single pipeline event, appended to events.ndjson."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    event_id: str = ""
    event_type: str = ""
    run_id: str = ""
    timestamp: str = ""
    worker: str = ""
    data: Dict[str, Any] = Field(default_factory=dict)
    event_hash: Optional[str] = None
    prev_hash: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def _normalize_aliases(cls, values: Any) -> Any:
        """Accept legacy field names from llm_telemetry and v1-style callers."""
        if not isinstance(values, dict):
            return values
        # ts → timestamp
        if "ts" in values and "timestamp" not in values:
            values["timestamp"] = values.pop("ts")
        # type → event_type
        if "type" in values and "event_type" not in values:
            values["event_type"] = values.pop("type")
        # payload → data
        if "payload" in values and "data" not in values:
            values["data"] = values.pop("payload")
        return values

    # -- Compat properties used by snapshot_manager and event_log ---------------

    @property
    def type(self) -> str:
        """Alias for event_type (used by snapshot_manager reducers)."""
        return str(self.event_type)

    @property
    def payload(self) -> Dict[str, Any]:
        """Alias for data (used by snapshot_manager reducers)."""
        return self.data

    @property
    def ts(self) -> str:
        """Alias for timestamp (used by snapshot_manager reducers)."""
        return str(self.timestamp)

    def to_dict(self) -> Dict[str, Any]:
        result = self.model_dump(mode="json")
        # Remove None optional fields for clean ndjson
        return {k: v for k, v in result.items() if v is not None}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        return cls.model_validate(data)
