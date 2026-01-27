"""State model for orchestrator and snapshot.

State represents the current run state and is reconstructed via event replay.

Spec references:
- specs/11_state_and_events.md (State model and transitions)
- specs/schemas/snapshot.schema.json (Snapshot schema)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .base import BaseModel


# Run states (binding per specs/11_state_and_events.md:14-29)
RUN_STATE_CREATED = "CREATED"
RUN_STATE_CLONED_INPUTS = "CLONED_INPUTS"
RUN_STATE_INGESTED = "INGESTED"
RUN_STATE_FACTS_READY = "FACTS_READY"
RUN_STATE_PLAN_READY = "PLAN_READY"
RUN_STATE_DRAFTING = "DRAFTING"
RUN_STATE_DRAFT_READY = "DRAFT_READY"
RUN_STATE_LINKING = "LINKING"
RUN_STATE_VALIDATING = "VALIDATING"
RUN_STATE_FIXING = "FIXING"
RUN_STATE_READY_FOR_PR = "READY_FOR_PR"
RUN_STATE_PR_OPENED = "PR_OPENED"
RUN_STATE_DONE = "DONE"
RUN_STATE_FAILED = "FAILED"
RUN_STATE_CANCELLED = "CANCELLED"

# Section states (binding per specs/11_state_and_events.md:31-37)
SECTION_STATE_NOT_STARTED = "NOT_STARTED"
SECTION_STATE_OUTLINED = "OUTLINED"
SECTION_STATE_DRAFTED = "DRAFTED"
SECTION_STATE_MERGED_IN_WORKTREE = "MERGED_IN_WORKTREE"
SECTION_STATE_DONE = "DONE"
SECTION_STATE_BLOCKED = "BLOCKED"

# Work item statuses (per specs/schemas/snapshot.schema.json:142-150)
WORK_ITEM_STATUS_QUEUED = "queued"
WORK_ITEM_STATUS_RUNNING = "running"
WORK_ITEM_STATUS_FINISHED = "finished"
WORK_ITEM_STATUS_FAILED = "failed"
WORK_ITEM_STATUS_SKIPPED = "skipped"


class ArtifactIndexEntry(BaseModel):
    """Artifact index entry in snapshot.

    Tracks written artifacts with metadata per specs/schemas/snapshot.schema.json:68-101.
    """

    def __init__(
        self,
        path: str,
        sha256: str,
        schema_id: str,
        writer_worker: str,
        ts: Optional[str] = None,
        event_id: Optional[str] = None,
    ):
        self.path = path
        self.sha256 = sha256
        self.schema_id = schema_id
        self.writer_worker = writer_worker
        self.ts = ts
        self.event_id = event_id

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "path": self.path,
            "sha256": self.sha256,
            "schema_id": self.schema_id,
            "writer_worker": self.writer_worker,
        }
        if self.ts is not None:
            result["ts"] = self.ts
        if self.event_id is not None:
            result["event_id"] = self.event_id
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ArtifactIndexEntry:
        return cls(
            path=data["path"],
            sha256=data["sha256"],
            schema_id=data["schema_id"],
            writer_worker=data["writer_worker"],
            ts=data.get("ts"),
            event_id=data.get("event_id"),
        )


class WorkItem(BaseModel):
    """Work item in orchestrator queue.

    Represents a unit of work assigned to a worker.
    Per specs/schemas/snapshot.schema.json:103-164.
    """

    def __init__(
        self,
        work_item_id: str,
        worker: str,
        attempt: int,
        status: str,
        inputs: List[str],
        outputs: List[str],
        scope_key: Optional[str] = None,
        started_at: Optional[str] = None,
        finished_at: Optional[str] = None,
        error: Optional[Dict[str, Any]] = None,
    ):
        self.work_item_id = work_item_id
        self.worker = worker
        self.attempt = attempt
        self.status = status
        self.inputs = inputs
        self.outputs = outputs
        self.scope_key = scope_key
        self.started_at = started_at
        self.finished_at = finished_at
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "work_item_id": self.work_item_id,
            "worker": self.worker,
            "attempt": self.attempt,
            "status": self.status,
            "inputs": self.inputs,
            "outputs": self.outputs,
        }
        if self.scope_key is not None:
            result["scope_key"] = self.scope_key
        if self.started_at is not None:
            result["started_at"] = self.started_at
        if self.finished_at is not None:
            result["finished_at"] = self.finished_at
        if self.error is not None:
            result["error"] = self.error
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> WorkItem:
        return cls(
            work_item_id=data["work_item_id"],
            worker=data["worker"],
            attempt=data["attempt"],
            status=data["status"],
            inputs=data["inputs"],
            outputs=data["outputs"],
            scope_key=data.get("scope_key"),
            started_at=data.get("started_at"),
            finished_at=data.get("finished_at"),
            error=data.get("error"),
        )


class Snapshot(BaseModel):
    """Snapshot of current run state.

    Materialized after each state transition for resume/replay.
    Per specs/schemas/snapshot.schema.json and specs/11_state_and_events.md:100-111.
    """

    def __init__(
        self,
        schema_version: str,
        run_id: str,
        run_state: str,
        artifacts_index: Dict[str, ArtifactIndexEntry],
        work_items: List[WorkItem],
        issues: List[Dict[str, Any]],
        section_states: Optional[Dict[str, str]] = None,
    ):
        self.schema_version = schema_version
        self.run_id = run_id
        self.run_state = run_state
        self.artifacts_index = artifacts_index
        self.work_items = work_items
        self.issues = issues
        self.section_states = section_states or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "run_state": self.run_state,
            "section_states": self.section_states,
            "artifacts_index": {k: v.to_dict() for k, v in self.artifacts_index.items()},
            "work_items": [item.to_dict() for item in self.work_items],
            "issues": self.issues,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Snapshot:
        return cls(
            schema_version=data["schema_version"],
            run_id=data["run_id"],
            run_state=data["run_state"],
            artifacts_index={
                k: ArtifactIndexEntry.from_dict(v) for k, v in data["artifacts_index"].items()
            },
            work_items=[WorkItem.from_dict(item) for item in data["work_items"]],
            issues=data["issues"],
            section_states=data.get("section_states", {}),
        )
