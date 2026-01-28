"""Snapshot persistence and replay for run state management.

Implements snapshot write/read and replay algorithm per specs/11_state_and_events.md.

Spec references:
- specs/11_state_and_events.md (Snapshot model and replay algorithm)
- specs/schemas/snapshot.schema.json (Snapshot schema)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from launch.io.atomic import atomic_write_text
from launch.models.event import (
    EVENT_ARTIFACT_WRITTEN,
    EVENT_GATE_RUN_FINISHED,
    EVENT_ISSUE_OPENED,
    EVENT_ISSUE_RESOLVED,
    EVENT_RUN_CREATED,
    EVENT_RUN_STATE_CHANGED,
    EVENT_WORK_ITEM_FINISHED,
    EVENT_WORK_ITEM_QUEUED,
    EVENT_WORK_ITEM_STARTED,
    Event,
)
from launch.models.state import (
    WORK_ITEM_STATUS_FINISHED,
    WORK_ITEM_STATUS_QUEUED,
    WORK_ITEM_STATUS_RUNNING,
    ArtifactIndexEntry,
    Snapshot,
    WorkItem,
)

from .event_log import read_events, validate_event_chain


SNAPSHOT_SCHEMA_VERSION = "1.0.0"


def write_snapshot(snapshot_file: Path, snapshot: Snapshot) -> None:
    """Write snapshot atomically to disk.

    Args:
        snapshot_file: Path to snapshot.json
        snapshot: Snapshot to write

    Spec reference: specs/11_state_and_events.md:100-111
    """
    snapshot_json = json.dumps(snapshot.to_dict(), indent=2, sort_keys=True)
    atomic_write_text(snapshot_file, snapshot_json + "\n")


def read_snapshot(snapshot_file: Path) -> Snapshot:
    """Read snapshot from disk.

    Args:
        snapshot_file: Path to snapshot.json

    Returns:
        Snapshot object

    Raises:
        FileNotFoundError: If snapshot file does not exist
    """
    with snapshot_file.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return Snapshot.from_dict(data)


def replay_events(events_file: Path, run_id: str) -> Snapshot:
    """Replay events to reconstruct snapshot.

    Implements the binding replay algorithm from specs/11_state_and_events.md:117-167.

    Args:
        events_file: Path to events.ndjson
        run_id: Run ID

    Returns:
        Reconstructed snapshot

    Spec reference: specs/11_state_and_events.md:117-143
    """
    # Step 1: Load Events
    events = read_events(events_file)

    # Step 2: Validate Chain (optional but recommended)
    try:
        validate_event_chain(events)
    except ValueError as e:
        # Log warning but continue (chain validation is optional)
        import sys
        print(f"WARNING: Event chain validation failed: {e}", file=sys.stderr)

    # Step 3: Apply Event Reducers
    # Initialize snapshot
    snapshot = Snapshot(
        schema_version=SNAPSHOT_SCHEMA_VERSION,
        run_id=run_id,
        run_state="CREATED",
        artifacts_index={},
        work_items=[],
        issues=[],
        section_states={},
    )

    # Reducer: apply events in order
    for event in events:
        snapshot = apply_event_reducer(snapshot, event)

    return snapshot


def apply_event_reducer(snapshot: Snapshot, event: Event) -> Snapshot:
    """Apply event to snapshot (reducer function).

    Args:
        snapshot: Current snapshot state
        event: Event to apply

    Returns:
        Updated snapshot

    Spec reference: specs/11_state_and_events.md:131-140
    """
    if event.type == EVENT_RUN_CREATED:
        # Initialize snapshot with run_id, timestamps
        # Already initialized, nothing to do
        pass

    elif event.type == EVENT_RUN_STATE_CHANGED:
        # Update snapshot.run_state = payload.new_state
        new_state = event.payload.get("new_state")
        if new_state:
            snapshot.run_state = new_state

    elif event.type == EVENT_ARTIFACT_WRITTEN:
        # Add to snapshot.artifacts_index with name, path, sha256, schema_id
        artifact_name = event.payload.get("name")
        if artifact_name:
            entry = ArtifactIndexEntry(
                path=event.payload.get("path", ""),
                sha256=event.payload.get("sha256", ""),
                schema_id=event.payload.get("schema_id", ""),
                writer_worker=event.payload.get("writer_worker", ""),
                ts=event.ts,
                event_id=event.event_id,
            )
            snapshot.artifacts_index[artifact_name] = entry

    elif event.type == EVENT_WORK_ITEM_QUEUED:
        # Add to snapshot.work_items with status=queued
        work_item = WorkItem(
            work_item_id=event.payload.get("work_item_id", ""),
            worker=event.payload.get("worker", ""),
            attempt=event.payload.get("attempt", 1),
            status=WORK_ITEM_STATUS_QUEUED,
            inputs=event.payload.get("inputs", []),
            outputs=event.payload.get("outputs", []),
            scope_key=event.payload.get("scope_key"),
        )
        snapshot.work_items.append(work_item)

    elif event.type == EVENT_WORK_ITEM_STARTED:
        # Update work_item status=running, started_at
        work_item_id = event.payload.get("work_item_id")
        for item in snapshot.work_items:
            if item.work_item_id == work_item_id:
                item.status = WORK_ITEM_STATUS_RUNNING
                item.started_at = event.ts
                break

    elif event.type == EVENT_WORK_ITEM_FINISHED:
        # Update work_item status=finished, finished_at
        work_item_id = event.payload.get("work_item_id")
        for item in snapshot.work_items:
            if item.work_item_id == work_item_id:
                item.status = WORK_ITEM_STATUS_FINISHED
                item.finished_at = event.ts
                break

    elif event.type == EVENT_ISSUE_OPENED:
        # Add to snapshot.issues with status=OPEN
        issue = event.payload.get("issue")
        if issue:
            snapshot.issues.append(issue)

    elif event.type == EVENT_ISSUE_RESOLVED:
        # Update issue status=RESOLVED, resolved_at
        issue_id = event.payload.get("issue_id")
        for issue in snapshot.issues:
            if issue.get("issue_id") == issue_id:
                issue["status"] = "RESOLVED"
                issue["resolved_at"] = event.ts
                break

    elif event.type == EVENT_GATE_RUN_FINISHED:
        # Update gate result in snapshot.gates (not currently in schema, skip)
        pass

    return snapshot


def create_initial_snapshot(run_id: str) -> Snapshot:
    """Create initial snapshot for a new run.

    Args:
        run_id: Run ID

    Returns:
        Initial snapshot with CREATED state
    """
    return Snapshot(
        schema_version=SNAPSHOT_SCHEMA_VERSION,
        run_id=run_id,
        run_state="CREATED",
        artifacts_index={},
        work_items=[],
        issues=[],
        section_states={},
    )
