"""Snapshot manifest — provenance ledger for promoted IR files.

Tracks the best-grade PageIR per content_path across all runs.
Mirrors deploy/manifest.json but for snapshots/ IR store.

Path invariant: snapshots_dir / (content_path + ".ir.json") — always.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict

from pydantic import Field

from launcher.io.atomic import atomic_write_json
from launcher.models.base import LauncherBaseModel
from launcher.models.evaluation import Grade

logger = logging.getLogger(__name__)


class SnapshotIREntry(LauncherBaseModel):
    """Record of one promoted IR file in the snapshots/ directory."""

    content_path: str
    snapshot_file: str   # relative path from snapshots_dir root
    source_run_id: str
    grade: Grade
    sha256: str
    promoted_at: str


class SnapshotManifest(LauncherBaseModel, frozen=False):
    """Manifest tracking all promoted IR files in snapshots/.

    majority_run_id / majority_run_ir_count track which single run
    contributed the most IR slots — that run's phase JSONs are written
    to phase_store/.
    """

    schema_version: str = "1.0"
    pages: Dict[str, SnapshotIREntry] = Field(default_factory=dict)
    majority_run_id: str = ""
    majority_run_ir_count: int = 0
    run_ir_counts: Dict[str, int] = Field(default_factory=dict)
    last_promotion: str = ""
    promotion_count: int = 0


def load_snapshot_manifest(path: Path) -> SnapshotManifest:
    """Load snapshot manifest from disk, or return empty manifest if missing/corrupt."""
    if not path.exists():
        return SnapshotManifest()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return SnapshotManifest.model_validate(raw)
    except Exception:
        logger.warning(
            "Corrupt snapshot manifest at %s — starting fresh", path, exc_info=True
        )
        backup = path.with_suffix(".json.bak")
        try:
            path.rename(backup)
            logger.info("Backed up corrupt snapshot manifest to %s", backup)
        except OSError:
            pass
        return SnapshotManifest()


def save_snapshot_manifest(path: Path, manifest: SnapshotManifest) -> None:
    """Atomically write snapshot manifest to disk."""
    data = manifest.model_dump(mode="json")
    _schema = Path(__file__).resolve().parents[3] / "specs" / "schemas" / "snapshot_manifest.schema.json"
    atomic_write_json(
        path,
        data,
        validate_boundary=path.parent,
        schema_path=str(_schema) if _schema.exists() else None,
    )
