from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from .atomic import atomic_write_text
from ..util.path_validation import validate_run_dir_under_runs

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RunLayout:
    run_dir: Path

    @property
    def artifacts_dir(self) -> Path:
        return self.run_dir / "artifacts"

    @property
    def logs_dir(self) -> Path:
        return self.run_dir / "logs"

    @property
    def reports_dir(self) -> Path:
        return self.run_dir / "reports"

    @property
    def drafts_dir(self) -> Path:
        return self.run_dir / "drafts"

    @property
    def work_dir(self) -> Path:
        return self.run_dir / "work"

    # -- TC-1760: Incremental update support -----------------------------------

    def load_previous_artifact(
        self, name: str, previous_run_path: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Load a JSON artifact from a previous run directory.

        TC-1760: Enables incremental updates by loading artifacts from a
        prior run for comparison (SHA matching, claim merging, page preservation).

        Args:
            name: Artifact filename (e.g., "product_facts.json")
            previous_run_path: Path to previous run directory.
                              If None, returns None.

        Returns:
            Parsed JSON dict, or None if not found/invalid.
        """
        if not previous_run_path:
            return None

        prev_path = Path(previous_run_path) / "artifacts" / name
        if not prev_path.exists():
            logger.debug(f"[RunLayout] Previous artifact not found: {prev_path}")
            return None

        try:
            return json.loads(prev_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"[RunLayout] Failed to load previous artifact {name}: {e}")
            return None

    def load_previous_drafts(
        self, previous_run_path: Optional[str] = None
    ) -> Dict[str, str]:
        """Load all draft file contents from a previous run.

        TC-1760: For draft reuse in incremental mode -- preserved pages
        can skip W5 generation by copying from previous run.

        Args:
            previous_run_path: Path to previous run directory.

        Returns:
            Dict mapping relative path (from drafts/) to content string.
        """
        if not previous_run_path:
            return {}

        prev_drafts = Path(previous_run_path) / "drafts"
        if not prev_drafts.exists():
            return {}

        result: Dict[str, str] = {}
        for md_file in prev_drafts.rglob("*.md"):
            try:
                rel_path = str(md_file.relative_to(prev_drafts))
                result[rel_path] = md_file.read_text(encoding="utf-8")
            except (OSError, ValueError):
                continue

        return result


def create_run_skeleton(run_dir: Path) -> RunLayout:
    run_dir = validate_run_dir_under_runs(run_dir)
    layout = RunLayout(run_dir=run_dir)
    # Required top-level files
    run_dir.mkdir(parents=True, exist_ok=True)
    atomic_write_text(run_dir / "events.ndjson", "")
    atomic_write_text(run_dir / "snapshot.json", "{}\n")
    atomic_write_text(run_dir / "telemetry_outbox.jsonl", "")

    # Required dirs
    (layout.work_dir / "repo").mkdir(parents=True, exist_ok=True)
    (layout.work_dir / "site").mkdir(parents=True, exist_ok=True)
    (layout.work_dir / "workflows").mkdir(parents=True, exist_ok=True)

    layout.artifacts_dir.mkdir(parents=True, exist_ok=True)
    layout.logs_dir.mkdir(parents=True, exist_ok=True)
    layout.reports_dir.mkdir(parents=True, exist_ok=True)

    # Draft section dirs
    for section in ["products", "docs", "reference", "kb", "blog"]:
        (layout.drafts_dir / section).mkdir(parents=True, exist_ok=True)

    return layout


def required_paths(run_dir: Path) -> List[Path]:
    """Return the required paths defined by specs/29_project_repo_structure.md."""
    return [
        run_dir / "run_config.yaml",
        run_dir / "events.ndjson",
        run_dir / "snapshot.json",
        run_dir / "telemetry_outbox.jsonl",
        run_dir / "work" / "repo",
        run_dir / "work" / "site",
        run_dir / "work" / "workflows",
        run_dir / "artifacts",
        run_dir / "drafts" / "products",
        run_dir / "drafts" / "docs",
        run_dir / "drafts" / "reference",
        run_dir / "drafts" / "kb",
        run_dir / "drafts" / "blog",
        run_dir / "reports",
        run_dir / "logs",
    ]
