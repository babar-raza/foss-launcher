"""Worker invocation interface for orchestrator.

Implements worker invocation contracts per specs/21_worker_contracts.md
and specs/28_coordination_and_handoffs.md.

Spec references:
- specs/21_worker_contracts.md (Global worker rules and I/O contracts)
- specs/28_coordination_and_handoffs.md (Work item contract)
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from launch.models.event import (
    EVENT_WORK_ITEM_FINISHED,
    EVENT_WORK_ITEM_QUEUED,
    EVENT_WORK_ITEM_STARTED,
    Event,
)
from launch.models.state import WORK_ITEM_STATUS_QUEUED, WorkItem
from launch.state.event_log import append_event, generate_event_id, generate_span_id


class WorkerInvoker:
    """Invokes workers with proper contracts and event logging.

    Implements the work item contract per specs/28_coordination_and_handoffs.md:42-56.
    """

    def __init__(self, run_id: str, run_dir: Path, trace_id: str, parent_span_id: str):
        """Initialize worker invoker.

        Args:
            run_id: Run ID
            run_dir: Path to RUN_DIR
            trace_id: Trace ID for telemetry
            parent_span_id: Parent span ID for telemetry
        """
        self.run_id = run_id
        self.run_dir = run_dir
        self.trace_id = trace_id
        self.parent_span_id = parent_span_id

    def queue_work_item(
        self,
        worker: str,
        inputs: List[str],
        outputs: List[str],
        attempt: int = 1,
        scope_key: Optional[str] = None,
    ) -> str:
        """Queue a work item for execution.

        Args:
            worker: Worker name (e.g., "W1.RepoScout")
            inputs: List of input artifact names or paths
            outputs: List of output artifact names or paths
            attempt: Attempt number (default: 1)
            scope_key: Scope key for parallel work items (optional)

        Returns:
            Work item ID

        Spec reference: specs/28_coordination_and_handoffs.md:42-56
        """
        # Generate work_item_id: {run_id}:{worker}:{attempt}:{scope_key}
        if scope_key:
            work_item_id = f"{self.run_id}:{worker}:{attempt}:{scope_key}"
        else:
            work_item_id = f"{self.run_id}:{worker}:{attempt}"

        # Emit WORK_ITEM_QUEUED event
        event = Event(
            event_id=generate_event_id(),
            run_id=self.run_id,
            ts=datetime.now(timezone.utc).isoformat(),
            type=EVENT_WORK_ITEM_QUEUED,
            payload={
                "work_item_id": work_item_id,
                "worker": worker,
                "attempt": attempt,
                "scope_key": scope_key,
                "inputs": inputs,
                "outputs": outputs,
            },
            trace_id=self.trace_id,
            span_id=generate_span_id(),
            parent_span_id=self.parent_span_id,
        )
        append_event(self.run_dir / "events.ndjson", event)

        return work_item_id

    def start_work_item(self, work_item_id: str) -> None:
        """Mark work item as started.

        Args:
            work_item_id: Work item ID

        Spec reference: specs/21_worker_contracts.md:33-39
        """
        event = Event(
            event_id=generate_event_id(),
            run_id=self.run_id,
            ts=datetime.now(timezone.utc).isoformat(),
            type=EVENT_WORK_ITEM_STARTED,
            payload={"work_item_id": work_item_id},
            trace_id=self.trace_id,
            span_id=generate_span_id(),
            parent_span_id=self.parent_span_id,
        )
        append_event(self.run_dir / "events.ndjson", event)

    def finish_work_item(
        self,
        work_item_id: str,
        success: bool = True,
        error: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Mark work item as finished.

        Args:
            work_item_id: Work item ID
            success: Whether work item succeeded
            error: Error details (if failed)

        Spec reference: specs/21_worker_contracts.md:33-39
        """
        event = Event(
            event_id=generate_event_id(),
            run_id=self.run_id,
            ts=datetime.now(timezone.utc).isoformat(),
            type=EVENT_WORK_ITEM_FINISHED,
            payload={
                "work_item_id": work_item_id,
                "success": success,
                "error": error,
            },
            trace_id=self.trace_id,
            span_id=generate_span_id(),
            parent_span_id=self.parent_span_id,
        )
        append_event(self.run_dir / "events.ndjson", event)

    def invoke_worker(
        self,
        worker: str,
        inputs: List[str],
        outputs: List[str],
        scope_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Invoke a worker with proper contract.

        STUB for TC-300: Full worker implementation is in TC-400+ taskcards.
        This method defines the interface that workers will implement.

        Args:
            worker: Worker name (e.g., "W1.RepoScout")
            inputs: List of input artifact names or paths
            outputs: List of output artifact names or paths
            scope_key: Scope key for parallel work items (optional)

        Returns:
            Worker result dictionary

        Spec reference: specs/21_worker_contracts.md:14-19
        """
        # Queue work item
        work_item_id = self.queue_work_item(worker, inputs, outputs, scope_key=scope_key)

        # Start work item
        self.start_work_item(work_item_id)

        # TODO: Actual worker invocation will be implemented in worker taskcards (TC-400+)
        # For TC-300, this is a stub that simulates successful execution
        result = {"status": "success", "work_item_id": work_item_id}

        # Finish work item
        self.finish_work_item(work_item_id, success=True)

        return result
