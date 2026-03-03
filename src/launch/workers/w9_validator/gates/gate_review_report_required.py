"""Gate: Review Report Required.

Enforces that review_report.json exists and has overall_status=="PASS"
in ci/prod profiles.  In local profile, issues are info-level (gate passes).
When review_enabled is False, the gate is a no-op (always passes).

Error codes:
  REVIEW_REPORT_MISSING  -- artifact absent or corrupted
  REVIEW_NOT_PASS        -- artifact exists but overall_status != "PASS"

Spec: specs/08_content_reviewer.md §Pipeline Position
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple


def execute_gate(
    run_dir: Path,
    run_config: Dict[str, Any],
    profile: str,
) -> Tuple[bool, List[Dict[str, Any]]]:
    """Execute review report required gate.

    No-op when review_enabled is False — mirrors W7 passthrough behavior.

    Args:
        run_dir:    Run directory path.
        run_config: Run configuration dictionary.
        profile:    Validation profile (local, ci, prod).

    Returns:
        Tuple of (gate_passed, issues).
    """
    # No-op: review was disabled, so no report is expected.
    # Mirrors specs/08_content_reviewer.md §Pipeline Position: "When disabled,
    # the pipeline passes through with no impact on existing workers."
    if not run_config.get("review_enabled", True):
        return True, []

    issues: List[Dict[str, Any]] = []
    report_path = run_dir / "artifacts" / "review_report.json"

    if not report_path.exists():
        severity = _severity_for_profile(profile)
        issues.append({
            "issue_id": "review_report_missing",
            "gate": "gate_review_report_required",
            "severity": severity,
            "message": "review_report.json is missing from artifacts/.",
            "error_code": "REVIEW_REPORT_MISSING",
            "status": "OPEN",
        })
    else:
        try:
            data = json.loads(report_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            severity = _severity_for_profile(profile)
            issues.append({
                "issue_id": "review_report_corrupt",
                "gate": "gate_review_report_required",
                "severity": severity,
                "message": f"review_report.json is corrupted: {e}",
                "error_code": "REVIEW_REPORT_MISSING",
                "status": "OPEN",
            })
            gate_passed = not any(
                i["severity"] in ("blocker", "error") for i in issues
            )
            return gate_passed, issues

        overall = data.get("overall_status", "UNKNOWN")
        if overall != "PASS":
            severity = _severity_for_profile(profile)
            issues.append({
                "issue_id": "review_not_pass",
                "gate": "gate_review_report_required",
                "severity": severity,
                "message": (
                    f"review_report.json overall_status is '{overall}', "
                    f"expected 'PASS'."
                ),
                "error_code": "REVIEW_NOT_PASS",
                "status": "OPEN",
            })

    gate_passed = not any(
        i["severity"] in ("blocker", "error") for i in issues
    )
    return gate_passed, issues


def _severity_for_profile(profile: str) -> str:
    """Profile-aware severity for review report issues.

    TC-3676: Pilot profile now returns "error" (was "info") to enforce
    W7 review quality during pilot runs.
    """
    if profile == "prod":
        return "blocker"
    if profile in ("ci", "pilot"):
        return "error"
    return "info"
