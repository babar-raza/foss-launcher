"""Deploy manifest — provenance ledger for promoted content."""

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


class DeployedPage(LauncherBaseModel):
    """Record of one promoted page in the deploy directory."""

    content_path: str
    deploy_file: str
    source_run_id: str
    grade: Grade
    sha256: str
    promoted_at: str


class DeployManifest(LauncherBaseModel, frozen=False):
    """Manifest tracking all promoted pages in deploy/."""

    schema_version: str = "1.0"
    pages: Dict[str, DeployedPage] = Field(default_factory=dict)
    last_promotion: str = ""
    promotion_count: int = 0


def load_manifest(path: Path) -> DeployManifest:
    """Load manifest from disk, or return empty manifest if missing/corrupt."""
    if not path.exists():
        return DeployManifest()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return DeployManifest.model_validate(raw)
    except Exception:
        logger.warning("Corrupt manifest at %s — starting fresh", path, exc_info=True)
        backup = path.with_suffix(".json.bak")
        try:
            path.rename(backup)
            logger.info("Backed up corrupt manifest to %s", backup)
        except OSError:
            pass
        return DeployManifest()


def save_manifest(path: Path, manifest: DeployManifest) -> None:
    """Atomically write manifest to disk."""
    data = manifest.model_dump(mode="json")
    atomic_write_json(path, data, validate_boundary=path.parent, schema_path="specs/schemas/deploy_manifest.schema.json")
