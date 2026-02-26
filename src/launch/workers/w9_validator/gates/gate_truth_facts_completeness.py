"""Gate: Truth Facts Completeness.

Validates that repo_truth.json canonical facts are populated when source
files exist.  Different from gate_truth_layer_completeness (which only checks
file existence) — this gate checks *content quality*.

Profile-aware severity:
  - local: warn only (gate passes)
  - ci:    error (gate fails)
  - prod:  blocker (gate fails)

Uses graceful_artifact_skip: true — skipped when repo_truth.json is absent
(existence is checked by gate_truth_layer_completeness at order 0).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple


def execute_gate(
    run_dir: Path, profile: str,
) -> Tuple[bool, List[Dict[str, Any]]]:
    """Execute Truth Facts Completeness gate."""
    issues: List[Dict[str, Any]] = []

    rt_path = run_dir / "artifacts" / "repo_truth.json"
    if not rt_path.exists():
        return True, []  # Graceful skip: existence checked by gate 0

    try:
        with rt_path.open(encoding="utf-8") as f:
            repo_truth = json.load(f)
    except Exception:
        return True, []  # Graceful skip: corruption checked by gate 0

    if not isinstance(repo_truth, dict):
        return True, []

    # Check: LICENSE file found but spdx_id empty → unrecognized license
    lic = repo_truth.get("license", {})
    if lic.get("source") and not lic.get("spdx_id"):
        issues.append({
            "issue_id": "truth_facts_license_unrecognized",
            "gate": "gate_truth_facts_completeness",
            "severity": _severity_for_profile(profile),
            "message": (
                f"LICENSE file found ({lic['source']}) but SPDX ID could not "
                f"be determined. Add a recognized license or update detection."
            ),
            "error_code": "TRUTH_FACTS_LICENSE_UNRECOGNIZED",
            "status": "OPEN",
        })

    # Check: package_name missing
    pkg = repo_truth.get("package_name", {})
    if not pkg.get("value"):
        issues.append({
            "issue_id": "truth_facts_package_name_missing",
            "gate": "gate_truth_facts_completeness",
            "severity": _severity_for_profile(profile),
            "message": "No package_name found in manifest files.",
            "error_code": "TRUTH_FACTS_PACKAGE_NAME_MISSING",
            "status": "OPEN",
        })

    # Check: python_requires missing (info only — many repos lack this)
    py = repo_truth.get("python_requires", {})
    if not py.get("min") and not py.get("spec"):
        issues.append({
            "issue_id": "truth_facts_python_requires_missing",
            "gate": "gate_truth_facts_completeness",
            "severity": "info",
            "message": "No python_requires found in manifest files.",
            "error_code": "TRUTH_FACTS_PYTHON_REQUIRES_MISSING",
            "status": "OPEN",
        })

    gate_passed = not any(
        i["severity"] in ("blocker", "error") for i in issues
    )
    return gate_passed, issues


def _severity_for_profile(profile: str) -> str:
    """Profile-aware severity for truth facts issues."""
    if profile == "prod":
        return "blocker"
    if profile == "ci":
        return "error"
    return "warn"
