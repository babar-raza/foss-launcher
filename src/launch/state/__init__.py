"""State management for launch runs.

Provides:
- Event log management (append, read, validate chain)
- Snapshot persistence (write, read, replay)
- Replay algorithm (event sourcing)

Spec references:
- specs/11_state_and_events.md (State and event model)
- specs/schemas/snapshot.schema.json (Snapshot schema)
- specs/schemas/event.schema.json (Event schema)
"""

from .event_log import (
    append_event,
    compute_event_hash,
    generate_event_id,
    generate_span_id,
    generate_trace_id,
    read_events,
    validate_event_chain,
)
from .snapshot_manager import (
    apply_event_reducer,
    create_initial_snapshot,
    read_snapshot,
    replay_events,
    write_snapshot,
)

__all__ = [
    # Event log
    "append_event",
    "read_events",
    "validate_event_chain",
    "compute_event_hash",
    "generate_event_id",
    "generate_trace_id",
    "generate_span_id",
    # Snapshot
    "write_snapshot",
    "read_snapshot",
    "replay_events",
    "apply_event_reducer",
    "create_initial_snapshot",
]
