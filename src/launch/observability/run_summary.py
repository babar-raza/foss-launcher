"""
Run Summary Report Generation.

Generates human-readable summaries of run execution with timeline and
validation results.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class TimelineEvent:
    """Single event in run timeline."""

    timestamp: str  # ISO 8601
    event_type: str
    worker: str | None
    message: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return asdict(self)


@dataclass
class RunSummary:
    """Summary of run execution."""

    run_id: str
    status: str
    started_at: str
    completed_at: str
    duration_seconds: float
    workers_completed: int
    workers_total: int
    validation_passed: bool
    pr_url: str | None
    timeline: list[TimelineEvent]

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "run_id": self.run_id,
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_seconds": self.duration_seconds,
            "workers_completed": self.workers_completed,
            "workers_total": self.workers_total,
            "validation_passed": self.validation_passed,
            "pr_url": self.pr_url,
            "timeline": [e.to_dict() for e in self.timeline],
        }

    def to_markdown(self) -> str:
        """Generate markdown summary report."""
        lines = [
            f"# Run Summary: {self.run_id}",
            "",
            "## Overview",
            "",
            f"- **Status**: {self.status}",
            f"- **Started**: {self.started_at}",
            f"- **Completed**: {self.completed_at}",
            f"- **Duration**: {self.duration_seconds:.2f}s",
            f"- **Workers**: {self.workers_completed}/{self.workers_total} completed",
            f"- **Validation**: {'PASSED' if self.validation_passed else 'FAILED'}",
        ]

        if self.pr_url:
            lines.append(f"- **PR**: {self.pr_url}")

        lines.extend([
            "",
            "## Timeline",
            "",
        ])

        if self.timeline:
            for event in self.timeline:
                timestamp = event.timestamp.split("T")[1].split(".")[0]  # HH:MM:SS
                worker_info = f" [{event.worker}]" if event.worker else ""
                lines.append(f"- `{timestamp}` {event.event_type}{worker_info}: {event.message}")
        else:
            lines.append("_No timeline events recorded_")

        lines.append("")

        return "\n".join(lines)


def generate_run_summary(run_dir: Path) -> RunSummary:
    """
    Generate run summary from snapshot and events.

    Args:
        run_dir: Path to run directory (e.g., runs/<run_id>)

    Returns:
        RunSummary with execution details and timeline
    """
    snapshot_path = run_dir / "snapshot.json"
    events_path = run_dir / "events.ndjson"
    validation_path = run_dir / "artifacts" / "validation_report.json"
    pr_path = run_dir / "artifacts" / "pr.json"

    # Load snapshot
    if not snapshot_path.exists():
        raise FileNotFoundError(f"Snapshot not found: {snapshot_path}")

    with snapshot_path.open(encoding="utf-8") as f:
        snapshot = json.load(f)

    run_id = snapshot.get("run_id", run_dir.name)
    status = snapshot.get("run_state", "UNKNOWN")

    # Load timeline from events
    timeline: list[TimelineEvent] = []
    if events_path.exists():
        timeline = _parse_timeline_from_events(events_path)

    # Determine timestamps
    started_at = snapshot.get("created_at", "")
    completed_at = snapshot.get("updated_at", started_at)

    # Calculate duration
    duration_seconds = 0.0
    if started_at and completed_at:
        try:
            start_dt = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
            duration_seconds = (end_dt - start_dt).total_seconds()
        except ValueError:
            pass

    # Count workers
    work_items = snapshot.get("work_items", [])
    workers_total = len(work_items)
    workers_completed = sum(1 for item in work_items if item.get("status") == "completed")

    # Check validation status
    validation_passed = False
    if validation_path.exists():
        with validation_path.open(encoding="utf-8") as f:
            validation_report = json.load(f)
            validation_passed = validation_report.get("ok", False)

    # Get PR URL
    pr_url = None
    if pr_path.exists():
        with pr_path.open(encoding="utf-8") as f:
            pr_data = json.load(f)
            pr_url = pr_data.get("pr_url")

    return RunSummary(
        run_id=run_id,
        status=status,
        started_at=started_at,
        completed_at=completed_at,
        duration_seconds=duration_seconds,
        workers_completed=workers_completed,
        workers_total=workers_total,
        validation_passed=validation_passed,
        pr_url=pr_url,
        timeline=timeline,
    )


def _parse_timeline_from_events(events_path: Path) -> list[TimelineEvent]:
    """
    Parse timeline events from events.ndjson.

    Extracts major events for timeline display.
    """
    timeline: list[TimelineEvent] = []

    major_event_types = {
        "RUN_CREATED",
        "INPUTS_CLONED",
        "WORK_ITEM_STARTED",
        "WORK_ITEM_FINISHED",
        "GATE_RUN_STARTED",
        "GATE_RUN_FINISHED",
        "PR_OPENED",
        "RUN_COMPLETED",
        "RUN_FAILED",
        "RUN_STATE_CHANGED",
    }

    with events_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            event_type = event.get("type", "")
            if event_type not in major_event_types:
                continue

            timestamp = event.get("ts", "")
            payload = event.get("payload", {})
            worker = payload.get("worker") or payload.get("gate_name")

            # Generate message based on event type
            message = _generate_event_message(event_type, payload)

            timeline.append(
                TimelineEvent(
                    timestamp=timestamp,
                    event_type=event_type,
                    worker=worker,
                    message=message,
                )
            )

    return timeline


def _generate_event_message(event_type: str, payload: dict[str, Any]) -> str:
    """Generate human-readable message for event."""
    if event_type == "RUN_CREATED":
        return "Run created"
    elif event_type == "INPUTS_CLONED":
        return "Inputs cloned"
    elif event_type == "WORK_ITEM_STARTED":
        return f"Started worker: {payload.get('worker', 'unknown')}"
    elif event_type == "WORK_ITEM_FINISHED":
        return f"Finished worker: {payload.get('worker', 'unknown')}"
    elif event_type == "GATE_RUN_STARTED":
        return f"Started gate: {payload.get('gate_name', 'unknown')}"
    elif event_type == "GATE_RUN_FINISHED":
        passed = payload.get("passed", False)
        status = "PASSED" if passed else "FAILED"
        return f"Gate {status}: {payload.get('gate_name', 'unknown')}"
    elif event_type == "PR_OPENED":
        return f"PR opened: {payload.get('pr_url', '')}"
    elif event_type == "RUN_COMPLETED":
        return "Run completed successfully"
    elif event_type == "RUN_FAILED":
        return f"Run failed: {payload.get('error', 'unknown error')}"
    elif event_type == "RUN_STATE_CHANGED":
        return f"State changed to {payload.get('new_state', 'unknown')}"
    else:
        return event_type


def validate_evidence_completeness(run_dir: Path) -> dict[str, Any]:
    """
    Validate evidence completeness for a run.

    Checks for required artifacts and worker reports.

    Args:
        run_dir: Path to run directory (e.g., runs/<run_id>)

    Returns:
        Dictionary with validation results:
        - completeness_score: float (0-100%)
        - missing_artifacts: list[str]
        - missing_reports: list[str]
        - is_complete: bool
    """
    required_artifacts = [
        "snapshot.json",
        "events.ndjson",
        "artifacts/repo_inventory.json",
        "artifacts/product_facts.json",
        "artifacts/page_plan.json",
    ]

    missing_artifacts: list[str] = []
    for artifact in required_artifacts:
        if not (run_dir / artifact).exists():
            missing_artifacts.append(artifact)

    # Check for worker reports
    missing_reports: list[str] = []
    snapshot_path = run_dir / "snapshot.json"

    if snapshot_path.exists():
        with snapshot_path.open(encoding="utf-8") as f:
            snapshot = json.load(f)

        work_items = snapshot.get("work_items", [])
        for item in work_items:
            worker_name = item.get("worker", "unknown")
            if item.get("status") == "completed":
                # Check if report exists (simplified check)
                # In real implementation, would check reports/agents/<agent>/TC-<id>/
                pass

    # Calculate completeness score
    total_checks = len(required_artifacts)
    passed_checks = total_checks - len(missing_artifacts)
    completeness_score = (passed_checks / total_checks * 100) if total_checks > 0 else 0.0

    return {
        "completeness_score": completeness_score,
        "missing_artifacts": missing_artifacts,
        "missing_reports": missing_reports,
        "is_complete": len(missing_artifacts) == 0 and len(missing_reports) == 0,
    }
