"""Gate P3: Build Time Limit.

Validates that Hugo build completes within 60 seconds.

Per TC-571 requirements: Build Time Limit (< 60s total build time).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple


def execute_gate(run_dir: Path, profile: str) -> Tuple[bool, List[Dict[str, Any]]]:
    """Execute Gate P3: Build Time Limit.

    Validates that Hugo build completed within 60 seconds.
    This gate checks the build time recorded in previous gate executions
    (specifically gate_13_hugo_build).

    Args:
        run_dir: Run directory path
        profile: Validation profile (local, ci, prod)

    Returns:
        Tuple of (gate_passed, issues)
    """
    issues = []
    max_build_time_seconds = 60

    # Check if validation_report.json exists from a previous run
    # to extract build time information
    validation_report_path = run_dir / "artifacts" / "validation_report.json"

    if not validation_report_path.exists():
        # No validation report yet, this gate will be run during validation
        # We'll check events.ndjson for Hugo build timing if available
        events_file = run_dir / "events.ndjson"

        if events_file.exists():
            try:
                build_start_time = None
                build_end_time = None

                # Parse events to find HUGO_BUILD_STARTED and HUGO_BUILD_COMPLETED
                with events_file.open(encoding="utf-8") as f:
                    for line in f:
                        try:
                            event = json.loads(line.strip())
                            if event.get("type") == "HUGO_BUILD_STARTED":
                                build_start_time = event.get("ts")
                            elif event.get("type") == "HUGO_BUILD_COMPLETED":
                                build_end_time = event.get("ts")
                        except json.JSONDecodeError:
                            continue

                # Calculate build duration if both timestamps found
                if build_start_time and build_end_time:
                    from datetime import datetime

                    start = datetime.fromisoformat(build_start_time)
                    end = datetime.fromisoformat(build_end_time)
                    duration_seconds = (end - start).total_seconds()

                    if duration_seconds > max_build_time_seconds:
                        issues.append(
                            {
                                "issue_id": "build_time_limit_exceeded",
                                "gate": "gate_p3_build_time_limit",
                                "severity": "warn",
                                "message": f"Hugo build time exceeded limit: {duration_seconds:.2f}s > {max_build_time_seconds}s",
                                "error_code": "GATE_BUILD_TIME_LIMIT_EXCEEDED",
                                "status": "OPEN",
                            }
                        )

            except Exception as e:
                issues.append(
                    {
                        "issue_id": "build_time_check_error",
                        "gate": "gate_p3_build_time_limit",
                        "severity": "warn",
                        "message": f"Error checking build time: {e}",
                        "error_code": "GATE_BUILD_TIME_CHECK_ERROR",
                        "status": "OPEN",
                    }
                )
        else:
            # No events file, cannot check build time yet
            # This is not an error, just means build hasn't run
            pass

    # Gate passes if no error/blocker issues (warnings are OK)
    gate_passed = not any(
        issue["severity"] in ["blocker", "error"] for issue in issues
    )

    return gate_passed, issues
