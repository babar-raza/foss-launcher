from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from launcher.models.base import LauncherBaseModel


# -- Work-item status constants ------------------------------------------------

WORK_ITEM_STATUS_QUEUED = "queued"
WORK_ITEM_STATUS_RUNNING = "running"
WORK_ITEM_STATUS_FINISHED = "finished"


# -- Worker status enum --------------------------------------------------------


class WorkerStatus(str, Enum):
    """Lifecycle status of a worker."""

    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    skipped = "skipped"


class WorkerState(LauncherBaseModel):
    """Runtime state of a single worker."""

    worker: str
    status: WorkerStatus = WorkerStatus.pending
    started_at: datetime | None = None
    completed_at: datetime | None = None
    checkpoint_path: str = ""
    error: str = ""


class PipelineState(LauncherBaseModel):
    """Runtime state of the entire pipeline."""

    run_id: str
    workers: list[WorkerState] = Field(default_factory=list)
    current_worker: str = ""
    re_run_count: int = 0
    max_re_runs: int = 2
    resume_from: str = ""


# -- Snapshot models -----------------------------------------------------------


class ArtifactIndexEntry(LauncherBaseModel):
    """Index entry for a single artifact tracked in the snapshot."""

    path: str = ""
    sha256: str = ""
    schema_id: str = ""
    writer_worker: str = ""
    ts: str = ""
    event_id: str = ""


class WorkItem(LauncherBaseModel):
    """A tracked unit of work within the pipeline."""

    model_config = ConfigDict(extra="forbid", frozen=False)

    work_item_id: str = ""
    worker: str = ""
    status: str = WORK_ITEM_STATUS_QUEUED
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    attempt: int = 1
    inputs: List[Any] = Field(default_factory=list)
    outputs: List[Any] = Field(default_factory=list)
    scope_key: Optional[str] = None


class Snapshot(LauncherBaseModel):
    """Point-in-time state of a pipeline run, materialized from events."""

    model_config = ConfigDict(extra="forbid", frozen=False)

    schema_version: str = "1.0.0"
    run_id: str = ""
    run_state: str = "CREATED"
    artifacts_index: Dict[str, ArtifactIndexEntry] = Field(default_factory=dict)
    work_items: List[WorkItem] = Field(default_factory=list)
    issues: List[Any] = Field(default_factory=list)
    section_states: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Snapshot":
        if not data:
            return cls()
        return cls.model_validate(data)
