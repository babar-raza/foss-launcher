"""
Checkpoint management for run state persistence.

Provides:
- Checkpoint creation (snapshot + metadata)
- Checkpoint listing and loading
- Cleanup of old checkpoints (retention policy)

Spec: specs/11_state_and_events.md (state recovery)
"""

import json
import logging
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Checkpoint:
    """A saved checkpoint."""

    checkpoint_id: str
    run_id: str
    created_at: str  # ISO 8601
    run_state: str
    completed_workers: List[str]
    snapshot_path: str
    events_count: int


def create_checkpoint(run_dir: Path) -> Checkpoint:
    """
    Create a checkpoint from current run state.

    Saves:
    - snapshot.json -> checkpoints/<timestamp>/snapshot.json
    - Checkpoint metadata -> checkpoints/<timestamp>/checkpoint.json
    - Records events count from events.ndjson

    Args:
        run_dir: Run directory containing snapshot.json and events.ndjson

    Returns:
        Checkpoint metadata

    Raises:
        FileNotFoundError: If snapshot.json doesn't exist
    """
    snapshot_path = run_dir / "snapshot.json"
    events_path = run_dir / "events.ndjson"
    checkpoints_dir = run_dir / "checkpoints"

    if not snapshot_path.exists():
        raise FileNotFoundError(f"Snapshot not found at {snapshot_path}")

    # Load current snapshot
    with open(snapshot_path, "r", encoding="utf-8") as f:
        snapshot = json.load(f)

    run_id = snapshot.get("run_id", "unknown")
    run_state = snapshot.get("run_state", "unknown")
    completed_workers = snapshot.get("completed_workers", [])

    # Count events
    events_count = 0
    if events_path.exists():
        with open(events_path, "r", encoding="utf-8") as f:
            events_count = sum(1 for _ in f)

    # Create checkpoint directory with timestamp (including microseconds for uniqueness)
    now = datetime.now(timezone.utc)
    checkpoint_id = now.strftime("%Y%m%d_%H%M%S_%f")
    checkpoint_dir = checkpoints_dir / checkpoint_id
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    # Copy snapshot to checkpoint
    checkpoint_snapshot_path = checkpoint_dir / "snapshot.json"
    shutil.copy2(snapshot_path, checkpoint_snapshot_path)

    # Create checkpoint metadata
    checkpoint = Checkpoint(
        checkpoint_id=checkpoint_id,
        run_id=run_id,
        created_at=now.isoformat(),
        run_state=run_state,
        completed_workers=completed_workers,
        snapshot_path=str(checkpoint_snapshot_path),
        events_count=events_count,
    )

    # Save checkpoint metadata
    checkpoint_metadata_path = checkpoint_dir / "checkpoint.json"
    with open(checkpoint_metadata_path, "w", encoding="utf-8") as f:
        json.dump(asdict(checkpoint), f, indent=2)

    logger.info(
        f"Created checkpoint {checkpoint_id} for run {run_id} "
        f"(state={run_state}, workers={len(completed_workers)}, events={events_count})"
    )

    return checkpoint


def list_checkpoints(run_dir: Path) -> List[Checkpoint]:
    """
    List all checkpoints for a run, sorted by created_at (oldest first).

    Args:
        run_dir: Run directory containing checkpoints/

    Returns:
        List of Checkpoint objects sorted by creation time
    """
    checkpoints_dir = run_dir / "checkpoints"
    if not checkpoints_dir.exists():
        return []

    checkpoints = []
    for checkpoint_dir in checkpoints_dir.iterdir():
        if not checkpoint_dir.is_dir():
            continue

        metadata_path = checkpoint_dir / "checkpoint.json"
        if not metadata_path.exists():
            logger.warning(f"Checkpoint {checkpoint_dir.name} missing metadata")
            continue

        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                checkpoint = Checkpoint(**data)
                checkpoints.append(checkpoint)
        except Exception as e:
            logger.warning(f"Error loading checkpoint {checkpoint_dir.name}: {e}")
            continue

    # Sort by created_at (ISO 8601 strings sort correctly)
    checkpoints.sort(key=lambda c: c.created_at)

    return checkpoints


def get_latest_checkpoint(run_dir: Path) -> Optional[Checkpoint]:
    """
    Get the most recent checkpoint for a run.

    Args:
        run_dir: Run directory

    Returns:
        Latest Checkpoint or None if no checkpoints exist
    """
    checkpoints = list_checkpoints(run_dir)
    if not checkpoints:
        return None

    return checkpoints[-1]  # Last one is most recent


def cleanup_old_checkpoints(run_dir: Path, keep_last_n: int = 5) -> int:
    """
    Delete old checkpoints, keeping only the last N.

    Args:
        run_dir: Run directory
        keep_last_n: Number of recent checkpoints to retain

    Returns:
        Number of checkpoints deleted
    """
    checkpoints = list_checkpoints(run_dir)

    if len(checkpoints) <= keep_last_n:
        logger.debug(f"Only {len(checkpoints)} checkpoints exist, keeping all")
        return 0

    # Delete oldest checkpoints
    checkpoints_to_delete = checkpoints[:-keep_last_n]
    deleted_count = 0

    for checkpoint in checkpoints_to_delete:
        checkpoint_dir = run_dir / "checkpoints" / checkpoint.checkpoint_id
        if checkpoint_dir.exists():
            try:
                shutil.rmtree(checkpoint_dir)
                deleted_count += 1
                logger.info(f"Deleted old checkpoint {checkpoint.checkpoint_id}")
            except Exception as e:
                logger.warning(f"Error deleting checkpoint {checkpoint.checkpoint_id}: {e}")

    logger.info(f"Cleaned up {deleted_count} old checkpoints, kept {keep_last_n} most recent")
    return deleted_count


def load_checkpoint(run_dir: Path, checkpoint_id: str) -> Checkpoint:
    """
    Load a specific checkpoint by ID.

    Args:
        run_dir: Run directory
        checkpoint_id: Checkpoint ID to load

    Returns:
        Checkpoint object

    Raises:
        FileNotFoundError: If checkpoint doesn't exist
    """
    checkpoint_dir = run_dir / "checkpoints" / checkpoint_id
    metadata_path = checkpoint_dir / "checkpoint.json"

    if not metadata_path.exists():
        raise FileNotFoundError(f"Checkpoint {checkpoint_id} not found")

    with open(metadata_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        return Checkpoint(**data)
