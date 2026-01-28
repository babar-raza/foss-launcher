"""Event log redaction for events.ndjson.

Binding contract: specs/11_state_and_events.md (event redaction)

Provides:
1. Event log redaction (NDJSON format)
2. Recursive payload redaction
3. Structure preservation (event_id, timestamp, event_type)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .redactor import redact_value
from .secret_detector import detect_secrets


def redact_events_log(input_path: Path, output_path: Path) -> int:
    """Redact secrets from events.ndjson log file.

    Args:
        input_path: Path to input events.ndjson
        output_path: Path to output redacted events.ndjson

    Returns:
        Number of events processed
    """
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    count = 0
    redacted_events: list[str] = []

    # Read and process each event
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            try:
                event = json.loads(line)

                # Redact the event recursively
                redacted_event = redact_value(event, detect_secrets)

                # Write back as JSON line
                redacted_events.append(json.dumps(redacted_event, sort_keys=True))
                count += 1

            except json.JSONDecodeError:
                # Skip malformed lines
                continue

    # Write all redacted events atomically
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for event_line in redacted_events:
            f.write(event_line + "\n")

    return count


def redact_event_payload(event: dict[str, Any]) -> dict[str, Any]:
    """Redact secrets from a single event payload.

    Preserves structure: event_id, timestamp, event_type are not redacted.
    Only payload fields are redacted.

    Args:
        event: Event dictionary

    Returns:
        Redacted event dictionary
    """
    # Don't redact metadata fields
    metadata_fields = {"event_id", "timestamp", "event_type"}

    redacted = {}
    for key, value in event.items():
        if key in metadata_fields:
            redacted[key] = value
        else:
            redacted[key] = redact_value(value, detect_secrets)

    return redacted
