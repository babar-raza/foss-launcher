"""Gate: Truth Layer Completeness (Phase 2 Truth Policy).

Pre-flight check ensuring all required truth artifacts exist before
downstream gates execute.  Missing truth artifacts indicate an incomplete
pipeline run -- in ci/prod profiles this blocks deployment.

Required artifacts:
  - api_inventory.json   (W2)
  - shared_facts.json    (W4)
  - page_plan.json       (W4)

Profile-aware severity:
  - local: warn (gate passes)
  - ci:    error (gate fails)
  - prod:  blocker (gate fails)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Artifacts required for truth layer completeness
_REQUIRED_ARTIFACTS: List[Dict[str, str]] = [
    {
        "filename": "api_inventory.json",
        "producer": "W2",
        "error_code": "TRUTH_MISSING_API_INVENTORY",
    },
    {
        "filename": "repo_truth.json",
        "producer": "W2",
        "error_code": "TRUTH_MISSING_REPO_TRUTH",
    },
    {
        "filename": "shared_facts.json",
        "producer": "W4",
        "error_code": "TRUTH_MISSING_SHARED_FACTS",
    },
    {
        "filename": "page_plan.json",
        "producer": "W4",
        "error_code": "TRUTH_MISSING_PAGE_PLAN",
    },
]


def execute_gate(
    run_dir: Path, profile: str,
) -> Tuple[bool, List[Dict[str, Any]]]:
    """Execute truth layer completeness gate.

    Args:
        run_dir: Run directory path.
        profile: Validation profile (local, ci, prod).

    Returns:
        Tuple of (gate_passed, issues).
    """
    issues: List[Dict[str, Any]] = []
    artifacts_dir = run_dir / "artifacts"

    for req in _REQUIRED_ARTIFACTS:
        artifact_path = artifacts_dir / req["filename"]
        if not artifact_path.exists():
            severity = _severity_for_profile(profile)
            issues.append({
                "issue_id": f"truth_missing_{req['filename'].replace('.json', '')}",
                "gate": "gate_truth_layer_completeness",
                "severity": severity,
                "message": (
                    f"Required truth artifact '{req['filename']}' is missing. "
                    f"Expected from {req['producer']}."
                ),
                "error_code": req["error_code"],
                "status": "OPEN",
            })
        else:
            # Verify it is valid JSON (not corrupted/truncated)
            try:
                with open(artifact_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if not isinstance(data, dict):
                    severity = _severity_for_profile(profile)
                    issues.append({
                        "issue_id": f"truth_corrupt_{req['filename'].replace('.json', '')}",
                        "gate": "gate_truth_layer_completeness",
                        "severity": severity,
                        "message": (
                            f"Truth artifact '{req['filename']}' is not a JSON object."
                        ),
                        "error_code": req["error_code"].replace("MISSING", "CORRUPT"),
                        "status": "OPEN",
                    })
            except (json.JSONDecodeError, OSError) as e:
                severity = _severity_for_profile(profile)
                issues.append({
                    "issue_id": f"truth_corrupt_{req['filename'].replace('.json', '')}",
                    "gate": "gate_truth_layer_completeness",
                    "severity": severity,
                    "message": (
                        f"Truth artifact '{req['filename']}' is corrupted: {e}"
                    ),
                    "error_code": req["error_code"].replace("MISSING", "CORRUPT"),
                    "status": "OPEN",
                })

    gate_passed = not any(
        i.get("severity") in ("blocker", "error") for i in issues
    )
    return gate_passed, issues


def _severity_for_profile(profile: str) -> str:
    """Profile-aware severity for missing/corrupt artifacts."""
    if profile == "prod":
        return "blocker"
    if profile == "ci":
        return "error"
    return "warn"
