"""Run directory skeleton for v2 pipeline.

Layout: runs/<run_id>/
    understanding_bundle.json
    content_bundle/
    evaluation/
        pages/{content_path_or_slug}.eval.json
        evaluation_summary.json
    evaluation_report.json
    publish_bundle.json
    events.ndjson
    snapshot.json
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from .atomic import atomic_write_text

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RunLayout:
    run_dir: Path

    # -- Bundle files ----------------------------------------------------------

    @property
    def understanding_bundle(self) -> Path:
        return self.run_dir / "understanding_bundle.json"

    @property
    def content_bundle_dir(self) -> Path:
        return self.run_dir / "content_bundle"

    @property
    def evaluation_dir(self) -> Path:
        return self.run_dir / "evaluation"

    @property
    def evaluation_report(self) -> Path:
        return self.run_dir / "evaluation_report.json"

    @property
    def publish_bundle(self) -> Path:
        return self.run_dir / "publish_bundle.json"

    # -- Infrastructure files --------------------------------------------------

    @property
    def events_file(self) -> Path:
        return self.run_dir / "events.ndjson"

    @property
    def snapshot_file(self) -> Path:
        return self.run_dir / "snapshot.json"

    # -- Helpers ---------------------------------------------------------------

    def load_json(self, path: Path) -> Dict[str, Any]:
        """Load and parse a JSON file inside this run directory."""
        return json.loads(path.read_text(encoding="utf-8"))

    def load_previous_artifact(
        self, name: str, previous_run_path: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Load a JSON artifact from a previous run directory.

        Args:
            name: Artifact filename.
            previous_run_path: Path to previous run directory.
                If None, returns None.

        Returns:
            Parsed JSON dict, or None if not found/invalid.
        """
        if not previous_run_path:
            return None

        prev_path = Path(previous_run_path) / name
        if not prev_path.exists():
            logger.debug("[RunLayout] Previous artifact not found: %s", prev_path)
            return None

        try:
            return json.loads(prev_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(
                "[RunLayout] Failed to load previous artifact %s: %s", name, e
            )
            return None


def _validate_run_dir(run_dir: Path) -> Path:
    """Ensure run_dir is inside a 'runs/' parent."""
    resolved = run_dir.resolve()
    if resolved.parent.name != "runs":
        raise ValueError(
            f"run_dir must be inside a 'runs/' directory, got: {resolved}"
        )
    return resolved


def create_run_skeleton(run_dir: Path) -> RunLayout:
    """Create the v2 run directory skeleton and return a RunLayout."""
    run_dir = _validate_run_dir(run_dir)
    layout = RunLayout(run_dir=run_dir)

    run_dir.mkdir(parents=True, exist_ok=True)

    # Infrastructure files
    atomic_write_text(layout.events_file, "")
    atomic_write_text(layout.snapshot_file, "{}\n")

    # Content bundle directory
    layout.content_bundle_dir.mkdir(parents=True, exist_ok=True)

    return layout


def required_paths(run_dir: Path) -> List[Path]:
    """Return the paths that must exist after create_run_skeleton."""
    return [
        run_dir / "events.ndjson",
        run_dir / "snapshot.json",
        run_dir / "content_bundle",
    ]


def discover_latest_run(
    runs_root: Path, family: str, platform: str
) -> Optional[Path]:
    """Find the most recent run directory for a family+platform.

    Scans subdirectories of *runs_root*, reads ``run_config.json`` from each,
    and returns the newest match (by directory mtime) or ``None``.
    """
    if not runs_root.is_dir():
        return None

    candidates: List[tuple[float, Path]] = []
    for entry in runs_root.iterdir():
        if not entry.is_dir():
            continue
        config_file = entry / "run_config.json"
        if not config_file.exists():
            continue
        try:
            raw = json.loads(config_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            logger.debug("Skipping unreadable run_config.json in %s", entry.name)
            continue
        if raw.get("family") == family and raw.get("platform") == platform:
            candidates.append((entry.stat().st_mtime, entry))

    if not candidates:
        return None

    candidates.sort(key=lambda t: t[0], reverse=True)
    return candidates[0][1]
