from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

from .atomic import atomic_write_text


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


def create_run_skeleton(run_dir: Path) -> RunLayout:
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
