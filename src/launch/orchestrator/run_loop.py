"""Orchestrator run loop for single-run execution.

Implements single-run execution flow with state persistence, event logging,
and worker invocation per specs/28_coordination_and_handoffs.md.

CRITICAL CONSTRAINT: Implements SINGLE-RUN path ONLY.
Batch execution is blocked by OQ-BATCH-001.

Spec references:
- specs/28_coordination_and_handoffs.md (Coordination model)
- specs/11_state_and_events.md (State transitions and events)
- specs/21_worker_contracts.md (Worker I/O contracts)
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from launch.io.run_layout import create_run_skeleton
from launch.models.event import EVENT_RUN_CREATED, EVENT_RUN_STATE_CHANGED, Event
from launch.models.state import RUN_STATE_CREATED, Snapshot
from launch.state.event_log import append_event, generate_event_id, generate_span_id, generate_trace_id
from launch.state.snapshot_manager import create_initial_snapshot, replay_events, write_snapshot

from .graph import OrchestratorState, build_orchestrator_graph


class RunResult:
    """Result of a run execution."""

    def __init__(
        self,
        run_id: str,
        final_state: str,
        exit_code: int,
        snapshot: Optional[Snapshot] = None,
    ):
        self.run_id = run_id
        self.final_state = final_state
        self.exit_code = exit_code
        self.snapshot = snapshot


def execute_run(
    run_id: str,
    run_dir: Path,
    run_config: Dict[str, Any],
) -> RunResult:
    """Execute a single run through the orchestrator graph.

    CRITICAL: This implements SINGLE-RUN execution only.
    Batch execution is blocked by OQ-BATCH-001 and must raise NotImplementedError.

    Args:
        run_id: Unique run identifier
        run_dir: Path to RUN_DIR (runs/<run_id>/)
        run_config: Validated run configuration

    Returns:
        RunResult with final state and exit code

    Spec references:
    - specs/28_coordination_and_handoffs.md:9-29 (control plane)
    - specs/11_state_and_events.md:14-29 (state model)
    """
    # Create run skeleton (RUN_DIR structure)
    create_run_skeleton(run_dir)

    # Initialize trace context
    trace_id = generate_trace_id()
    parent_span_id = generate_span_id()

    # Emit RUN_CREATED event
    run_created_event = Event(
        event_id=generate_event_id(),
        run_id=run_id,
        ts=datetime.now(timezone.utc).isoformat(),
        type=EVENT_RUN_CREATED,
        payload={
            "run_id": run_id,
            "run_config": run_config,
        },
        trace_id=trace_id,
        span_id=generate_span_id(),
        parent_span_id=parent_span_id,
    )
    append_event(run_dir / "events.ndjson", run_created_event)

    # Create initial snapshot
    snapshot = create_initial_snapshot(run_id)
    write_snapshot(run_dir / "snapshot.json", snapshot)

    # Build orchestrator graph
    graph = build_orchestrator_graph()
    compiled_graph = graph.compile()

    # Initialize graph state
    initial_state: OrchestratorState = {
        "run_id": run_id,
        "run_state": RUN_STATE_CREATED,
        "run_dir": str(run_dir),
        "run_config": run_config,
        "snapshot": snapshot.to_dict(),
        "issues": [],
        "fix_attempts": 0,
        "current_issue": None,
    }

    # Execute graph (streaming through states)
    final_state_dict: Optional[OrchestratorState] = None
    previous_run_state = RUN_STATE_CREATED  # Track previous state for correct old_state emission

    for state_update in compiled_graph.stream(initial_state):
        # state_update is a dict with node name as key
        for node_name, node_output in state_update.items():
            final_state_dict = node_output

            # Emit state change event if state changed
            new_run_state = node_output.get("run_state")
            if new_run_state and new_run_state != previous_run_state:
                state_change_event = Event(
                    event_id=generate_event_id(),
                    run_id=run_id,
                    ts=datetime.now(timezone.utc).isoformat(),
                    type=EVENT_RUN_STATE_CHANGED,
                    payload={
                        "old_state": previous_run_state,
                        "new_state": new_run_state,
                    },
                    trace_id=trace_id,
                    span_id=generate_span_id(),
                    parent_span_id=parent_span_id,
                )
                append_event(run_dir / "events.ndjson", state_change_event)

                # Update previous state tracker
                previous_run_state = new_run_state

                # Replay events to reconstruct snapshot (ensures snapshot = f(events))
                snapshot = replay_events(run_dir / "events.ndjson", run_id)
                write_snapshot(run_dir / "snapshot.json", snapshot)

    # Determine exit code
    final_run_state = final_state_dict["run_state"] if final_state_dict else RUN_STATE_CREATED
    exit_code = _determine_exit_code(final_run_state)

    return RunResult(
        run_id=run_id,
        final_state=final_run_state,
        exit_code=exit_code,
        snapshot=snapshot,
    )


def _determine_exit_code(final_state: str) -> int:
    """Determine exit code from final run state.

    Args:
        final_state: Final run state

    Returns:
        Exit code per specs/01_system_contract.md:146-151
    """
    if final_state == "DONE":
        return 0
    elif final_state == "FAILED":
        return 2
    elif final_state == "CANCELLED":
        return 1
    else:
        return 5  # Unexpected internal error


# BLOCKED: OQ-BATCH-001 (Batch execution semantics)
def execute_batch(batch_manifest: Dict[str, Any]) -> None:
    """Execute multiple runs with bounded concurrency.

    BLOCKED: OQ-BATCH-001 (Batch execution semantics)

    Args:
        batch_manifest: Batch configuration (shape undefined)

    Raises:
        NotImplementedError: Always (blocked by OQ-BATCH-001)

    Spec reference: OPEN_QUESTIONS.md:66-74
    """
    raise NotImplementedError(
        "Batch execution not implemented - blocked by OQ-BATCH-001. "
        "See OPEN_QUESTIONS.md for details on required batch execution semantics."
    )
