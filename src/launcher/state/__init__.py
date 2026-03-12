"""State management for launcher runs.

Provides:
- Event log management (append, read, validate chain)
- Snapshot persistence (write, read, replay) — deferred import

Spec references:
- specs/11_state_and_events.md (State and event model)
- specs/schemas/snapshot.schema.json (Snapshot schema)
- specs/schemas/event.schema.json (Event schema)
"""

from __future__ import annotations

from .event_log import (
    append_event,
    compute_event_hash,
    generate_event_id,
    generate_span_id,
    generate_trace_id,
    read_events,
    validate_event_chain,
)


def __getattr__(name: str):
    """Lazily import snapshot_manager symbols to avoid v1 dependency chain."""
    _SNAPSHOT_NAMES = {
        "apply_event_reducer",
        "create_initial_snapshot",
        "read_snapshot",
        "replay_events",
        "write_snapshot",
    }
    if name in _SNAPSHOT_NAMES:
        from . import snapshot_manager
        return getattr(snapshot_manager, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # Event log
    "append_event",
    "compute_event_hash",
    "generate_event_id",
    "generate_span_id",
    "generate_trace_id",
    "read_events",
    "validate_event_chain",
    # Snapshot (lazy)
    "apply_event_reducer",
    "create_initial_snapshot",
    "read_snapshot",
    "replay_events",
    "write_snapshot",
]
