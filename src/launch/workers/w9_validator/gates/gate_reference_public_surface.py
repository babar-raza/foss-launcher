"""Gate: Reference Public Surface Boundary.

Validates that reference_object_page entries in page_plan.json only reference
symbols that appear in api_inventory.json's public_surface.  Prevents
generation of reference documentation for internal/private API symbols.

Profile-aware severity:
  - local: warn only (gate passes)
  - ci:    error (gate fails)
  - prod:  blocker (gate fails)

Uses graceful_artifact_skip: true -- skipped when:
  - api_inventory.json does not exist
  - page_plan.json does not exist
  - public_surface.confidence is "unknown"
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Page roles that indicate reference documentation
_REF_ROLES = frozenset({
    "reference_object_page",
    "reference_object",
    "class_reference",
    "module_reference",
})


def execute_gate(
    run_dir: Path, profile: str,
) -> Tuple[bool, List[Dict[str, Any]]]:
    """Execute Gate: Reference Public Surface Boundary."""
    issues: List[Dict[str, Any]] = []

    inv_path = run_dir / "artifacts" / "api_inventory.json"
    page_plan_path = run_dir / "artifacts" / "page_plan.json"

    # Graceful skip when artifacts are absent
    if not inv_path.exists() or not page_plan_path.exists():
        return True, []

    try:
        with inv_path.open(encoding="utf-8") as f:
            inventory = json.load(f)
    except Exception:
        return True, []  # Corrupted inventory: graceful skip

    # Graceful skip when public surface confidence is unknown
    public_surface = inventory.get("public_surface", {})
    confidence = public_surface.get("confidence", "unknown")
    if confidence == "unknown":
        return True, []

    # public_surface.classes may contain import paths (e.g. "aspose.threed.Scene")
    # or short names (backward compat). Build both sets for matching.
    ps_raw_classes = set(public_surface.get("classes", []))
    ps_raw_functions = set(public_surface.get("functions", []))
    ps_classes = ps_raw_classes | {p.rsplit(".", 1)[-1] for p in ps_raw_classes}
    ps_functions = ps_raw_functions | {p.rsplit(".", 1)[-1] for p in ps_raw_functions}
    if not ps_classes and not ps_functions:
        return True, []  # Empty public surface: nothing to validate

    try:
        with page_plan_path.open(encoding="utf-8") as f:
            page_plan = json.load(f)
    except Exception:
        return True, []

    # Find reference_object_page entries with object_name
    for page in page_plan.get("pages", []):
        if page.get("page_role") not in _REF_ROLES:
            continue
        if page.get("section") != "reference":
            continue

        object_name = page.get("object_name", "")
        object_kind = page.get("object_kind", "class")

        if not object_name:
            continue

        # Check if the object is in public surface
        if object_kind == "function":
            is_public = object_name in ps_functions
        else:  # class or default
            is_public = object_name in ps_classes

        if not is_public:
            severity = _severity_for_profile(profile)
            issues.append({
                "issue_id": f"gate_ref_public_surface_{object_name}",
                "gate": "gate_reference_public_surface",
                "severity": severity,
                "message": (
                    f"Reference page for '{object_name}' ({object_kind}) exists "
                    f"but '{object_name}' is not in api_inventory public_surface "
                    f"(confidence={confidence}). This may expose internal API "
                    f"documentation."
                ),
                "error_code": "GATE_REF_PUBLIC_SURFACE_VIOLATION",
                "status": "OPEN",
            })

    gate_passed = not any(
        issue["severity"] in ("blocker", "error") for issue in issues
    )
    return gate_passed, issues


def _severity_for_profile(profile: str) -> str:
    """Profile-aware severity for public surface violations."""
    if profile == "prod":
        return "blocker"
    if profile == "ci":
        return "error"
    return "warn"
