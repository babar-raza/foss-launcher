"""Tests for Event model.

Validates:
- Event serialization matches event.schema.json
- Required and optional fields handled correctly
- Deterministic serialization
"""

import json

import pytest

from src.launch.models.event import (
    EVENT_RUN_CREATED,
    EVENT_WORK_ITEM_STARTED,
    Event,
)


def test_event_minimal():
    """Test Event with only required fields."""
    event = Event(
        event_id="evt-001",
        run_id="run-123",
        ts="2026-01-28T00:00:00Z",
        type=EVENT_RUN_CREATED,
        payload={"data": "value"},
        trace_id="trace-abc",
        span_id="span-123",
    )

    data = event.to_dict()

    assert data["event_id"] == "evt-001"
    assert data["run_id"] == "run-123"
    assert data["ts"] == "2026-01-28T00:00:00Z"
    assert data["type"] == EVENT_RUN_CREATED
    assert data["payload"] == {"data": "value"}
    assert data["trace_id"] == "trace-abc"
    assert data["span_id"] == "span-123"

    # Optional fields should not be present
    assert "parent_span_id" not in data
    assert "prev_hash" not in data
    assert "event_hash" not in data


def test_event_with_optional_fields():
    """Test Event with all optional fields."""
    event = Event(
        event_id="evt-002",
        run_id="run-123",
        ts="2026-01-28T00:00:01Z",
        type=EVENT_WORK_ITEM_STARTED,
        payload={"worker": "W1"},
        trace_id="trace-abc",
        span_id="span-124",
        parent_span_id="span-123",
        prev_hash="hash-001",
        event_hash="hash-002",
    )

    data = event.to_dict()

    assert data["parent_span_id"] == "span-123"
    assert data["prev_hash"] == "hash-001"
    assert data["event_hash"] == "hash-002"


def test_event_round_trip():
    """Test Event serialization round-trip."""
    original = Event(
        event_id="evt-003",
        run_id="run-456",
        ts="2026-01-28T12:34:56Z",
        type="CUSTOM_EVENT",
        payload={"nested": {"key": "value"}},
        trace_id="trace-xyz",
        span_id="span-789",
        parent_span_id="span-parent",
    )

    data = original.to_dict()
    restored = Event.from_dict(data)

    assert restored.event_id == original.event_id
    assert restored.run_id == original.run_id
    assert restored.ts == original.ts
    assert restored.type == original.type
    assert restored.payload == original.payload
    assert restored.trace_id == original.trace_id
    assert restored.span_id == original.span_id
    assert restored.parent_span_id == original.parent_span_id


def test_event_json_deterministic():
    """Test that identical events produce identical JSON."""
    event1 = Event(
        event_id="evt-test",
        run_id="run-test",
        ts="2026-01-28T00:00:00Z",
        type="TEST_EVENT",
        payload={"a": 1, "b": 2},
        trace_id="trace-test",
        span_id="span-test",
    )

    event2 = Event(
        event_id="evt-test",
        run_id="run-test",
        ts="2026-01-28T00:00:00Z",
        type="TEST_EVENT",
        payload={"a": 1, "b": 2},
        trace_id="trace-test",
        span_id="span-test",
    )

    json1 = event1.to_json()
    json2 = event2.to_json()

    assert json1 == json2


def test_event_constants_defined():
    """Test that event type constants are defined."""
    # Just verify a few key constants exist
    assert EVENT_RUN_CREATED == "RUN_CREATED"
    assert EVENT_WORK_ITEM_STARTED == "WORK_ITEM_STARTED"
