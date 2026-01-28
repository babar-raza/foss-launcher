"""Event log management for append-only event sourcing.

Implements event append, read, and chain validation per specs/11_state_and_events.md.

Spec references:
- specs/11_state_and_events.md (Event log fields and required event types)
- specs/schemas/event.schema.json (Event schema)
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from launch.models.event import Event


def append_event(
    events_file: Path,
    event: Event,
) -> None:
    """Append event to NDJSON event log atomically.

    Args:
        events_file: Path to events.ndjson file
        event: Event to append

    Spec reference: specs/11_state_and_events.md:52-73
    """
    # Serialize event to single-line JSON
    event_json = json.dumps(event.to_dict(), separators=(",", ":"), sort_keys=True)

    # Append to file (newline-delimited JSON)
    with events_file.open("a", encoding="utf-8") as f:
        f.write(event_json + "\n")


def read_events(events_file: Path) -> List[Event]:
    """Read all events from NDJSON event log.

    Args:
        events_file: Path to events.ndjson file

    Returns:
        List of Event objects in append order

    Spec reference: specs/11_state_and_events.md:122-127
    """
    if not events_file.exists():
        return []

    events: List[Event] = []
    with events_file.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            event_data = json.loads(line)
            events.append(Event.from_dict(event_data))

    return events


def validate_event_chain(events: List[Event]) -> None:
    """Validate event chain integrity.

    Args:
        events: List of events in append order

    Raises:
        ValueError: If chain validation fails

    Spec reference: specs/11_state_and_events.md:126-130
    """
    prev_hash: Optional[str] = None

    for event in events:
        # Skip chain validation if hashes not present (optional feature)
        if event.event_hash is None or event.prev_hash is None:
            continue

        # Verify prev_hash matches previous event's event_hash
        if prev_hash is not None and event.prev_hash != prev_hash:
            raise ValueError(
                f"Event chain broken: event {event.event_id} has prev_hash={event.prev_hash} "
                f"but expected {prev_hash}"
            )

        # Verify event_hash
        computed_hash = compute_event_hash(
            event.event_id, event.ts, event.type, event.payload, event.prev_hash or ""
        )
        if event.event_hash != computed_hash:
            raise ValueError(
                f"Event hash mismatch: event {event.event_id} has event_hash={event.event_hash} "
                f"but computed {computed_hash}"
            )

        prev_hash = event.event_hash


def compute_event_hash(
    event_id: str,
    ts: str,
    event_type: str,
    payload: dict,
    prev_hash: str,
) -> str:
    """Compute event hash for chain validation.

    Args:
        event_id: Event ID
        ts: ISO8601 timestamp
        event_type: Event type
        payload: Event payload
        prev_hash: Previous event hash (or empty string for first event)

    Returns:
        SHA256 hash (hex string)

    Spec reference: specs/11_state_and_events.md:128
    """
    payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    data = f"{event_id}{ts}{event_type}{payload_json}{prev_hash}"
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def generate_event_id() -> str:
    """Generate unique event ID.

    Returns:
        Event ID (timestamp-based for ordering + random suffix for uniqueness)
    """
    import uuid
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    suffix = uuid.uuid4().hex[:8]
    return f"evt-{ts}-{suffix}"


def generate_trace_id() -> str:
    """Generate trace ID for telemetry correlation.

    Returns:
        Trace ID (UUID hex)
    """
    import uuid
    return uuid.uuid4().hex


def generate_span_id() -> str:
    """Generate span ID for telemetry correlation.

    Returns:
        Span ID (UUID hex)
    """
    import uuid
    return uuid.uuid4().hex
