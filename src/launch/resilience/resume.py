"""
Run resume logic for recovering from failures.

Implements:
- Loading state from latest checkpoint
- Replaying events from checkpoint
- Determining which workers need re-execution
- Preserving run_id and continuity

Spec: specs/11_state_and_events.md (event sourcing, state recovery)
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from .checkpoint import get_latest_checkpoint

logger = logging.getLogger(__name__)


@dataclass
class ResumeResult:
    """Result of resuming a run."""

    run_id: str
    resumed_from_state: str
    checkpoint_loaded: str
    workers_to_rerun: List[str]
    success: bool


def resume_run(run_dir: Path, target_workers: Optional[List[str]] = None) -> ResumeResult:
    """
    Resume a run from the latest checkpoint.

    Process:
    1. Find latest checkpoint
    2. Load snapshot.json from checkpoint
    3. Replay events.ndjson from checkpoint position
    4. Determine which workers need re-execution
    5. Return resume result with workers to rerun

    Args:
        run_dir: Run directory containing checkpoints/
        target_workers: Optional list of all workers (to determine what needs rerun)

    Returns:
        ResumeResult with workers that need re-execution

    Raises:
        FileNotFoundError: If no checkpoint exists or run state invalid
    """
    # Find latest checkpoint
    checkpoint = get_latest_checkpoint(run_dir)

    if checkpoint is None:
        # No checkpoint - start fresh
        logger.info(f"No checkpoint found in {run_dir}, starting fresh run")
        return ResumeResult(
            run_id="unknown",
            resumed_from_state="none",
            checkpoint_loaded="none",
            workers_to_rerun=target_workers or [],
            success=True,
        )

    logger.info(
        f"Resuming from checkpoint {checkpoint.checkpoint_id} "
        f"(state={checkpoint.run_state}, completed={len(checkpoint.completed_workers)})"
    )

    # Load snapshot from checkpoint
    snapshot_path = Path(checkpoint.snapshot_path)
    if not snapshot_path.exists():
        raise FileNotFoundError(f"Checkpoint snapshot not found at {snapshot_path}")

    with open(snapshot_path, "r", encoding="utf-8") as f:
        snapshot = json.load(f)

    run_id = snapshot.get("run_id", checkpoint.run_id)
    run_state = snapshot.get("run_state", checkpoint.run_state)
    completed_workers = set(snapshot.get("completed_workers", checkpoint.completed_workers))

    # Determine which workers need re-execution
    if target_workers is None:
        # If no target workers specified, no workers to rerun
        workers_to_rerun = []
    else:
        # Rerun workers that are not completed
        workers_to_rerun = [w for w in target_workers if w not in completed_workers]

    # Replay events from checkpoint (for state validation)
    events_count = replay_events(run_dir, from_count=checkpoint.events_count)

    logger.info(
        f"Resumed run {run_id}: {len(completed_workers)} workers completed, "
        f"{len(workers_to_rerun)} workers to rerun, {events_count} new events since checkpoint"
    )

    return ResumeResult(
        run_id=run_id,
        resumed_from_state=run_state,
        checkpoint_loaded=checkpoint.checkpoint_id,
        workers_to_rerun=workers_to_rerun,
        success=True,
    )


def replay_events(run_dir: Path, from_count: int = 0) -> int:
    """
    Replay events from events.ndjson starting from a given position.

    This is primarily for state validation - in practice, the snapshot
    already contains the applied state, but replaying events can verify
    consistency or apply new events since the checkpoint.

    Args:
        run_dir: Run directory containing events.ndjson
        from_count: Number of events already processed in checkpoint

    Returns:
        Number of new events replayed (events after from_count)
    """
    events_path = run_dir / "events.ndjson"

    if not events_path.exists():
        logger.debug(f"No events file found at {events_path}")
        return 0

    new_events_count = 0
    current_line = 0

    with open(events_path, "r", encoding="utf-8") as f:
        for line in f:
            current_line += 1

            # Skip events already in checkpoint
            if current_line <= from_count:
                continue

            # Process new event (in practice, just validate JSON)
            try:
                event = json.loads(line)
                event_type = event.get("event_type", "unknown")
                logger.debug(f"Replayed event {current_line}: {event_type}")
                new_events_count += 1
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid event at line {current_line}: {e}")

    logger.info(f"Replayed {new_events_count} new events (total: {current_line})")
    return new_events_count


def get_incomplete_workers(
    run_dir: Path, all_workers: List[str]
) -> List[str]:
    """
    Get list of workers that have not completed successfully.

    Loads latest checkpoint and compares against expected workers.

    Args:
        run_dir: Run directory
        all_workers: List of all expected workers

    Returns:
        List of worker names that need execution
    """
    checkpoint = get_latest_checkpoint(run_dir)

    if checkpoint is None:
        # No checkpoint - all workers need execution
        return all_workers

    completed = set(checkpoint.completed_workers)
    incomplete = [w for w in all_workers if w not in completed]

    return incomplete
