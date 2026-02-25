"""Gate: Reference Object Pages.

Spec v1.1 J4: Validates that the reference section of page_plan.json contains
at least one ``reference_object_page`` beyond the mandatory ``api-overview``
page, when API surface data is available in product_facts.json.

This gate uses ``graceful_artifact_skip: true`` — it is skipped when:
  - ``page_plan.json`` does not exist, OR
  - ``product_facts.json`` does not exist, OR
  - ``api_surface_summary.classes`` is empty (no API discovered).

This ensures the gate never fails a repo with no detectable public API.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple


def execute_gate(run_dir: Path, profile: str) -> Tuple[bool, List[Dict[str, Any]]]:
    """Execute Gate: Reference Object Pages.

    Validates that when API classes exist in product_facts, the reference
    section in page_plan contains at least one reference_object_page beyond
    the api-overview landing page.

    Args:
        run_dir: Run directory path.
        profile: Validation profile (local, ci, prod).

    Returns:
        Tuple of (gate_passed, issues).
    """
    issues: List[Dict[str, Any]] = []

    page_plan_path = run_dir / "artifacts" / "page_plan.json"
    product_facts_path = run_dir / "artifacts" / "product_facts.json"

    # Graceful skip when artifacts are absent
    if not page_plan_path.exists() or not product_facts_path.exists():
        return True, []

    try:
        with product_facts_path.open(encoding="utf-8") as f:
            product_facts = json.load(f)
    except Exception as e:
        issues.append({
            "issue_id": "gate_ref_objects_product_facts_invalid",
            "gate": "gate_reference_objects",
            "severity": "error",
            "message": f"Failed to load product_facts.json: {e}",
            "error_code": "GATE_REF_OBJECTS_PRODUCT_FACTS_INVALID",
            "status": "OPEN",
        })
        return False, issues

    # Graceful skip when no API classes discovered
    api_surface = product_facts.get("api_surface_summary", {})
    raw_classes = api_surface.get("classes", [])
    if not raw_classes:
        return True, []

    try:
        with page_plan_path.open(encoding="utf-8") as f:
            page_plan = json.load(f)
    except Exception as e:
        issues.append({
            "issue_id": "gate_ref_objects_page_plan_invalid",
            "gate": "gate_reference_objects",
            "severity": "error",
            "message": f"Failed to load page_plan.json: {e}",
            "error_code": "GATE_REF_OBJECTS_PAGE_PLAN_INVALID",
            "status": "OPEN",
        })
        return False, issues

    # Count reference_object_page entries in the reference section
    object_pages = [
        p for p in page_plan.get("pages", [])
        if p.get("section") == "reference"
        and p.get("page_role") in (
            "reference_object_page", "reference_object", "class_reference", "module_reference"
        )
    ]

    if not object_pages:
        n_classes = len(raw_classes)
        issues.append({
            "issue_id": "gate_ref_objects_none_found",
            "gate": "gate_reference_objects",
            "severity": "warn",
            "message": (
                f"Reference section has no reference_object_page entries, but "
                f"product_facts has {n_classes} API class(es). "
                f"Ensure ruleset.v1_1.yaml reference.optional_page_policies includes "
                f"'per_api_object' source and the run uses ruleset_version: 'ruleset.v1_1'."
            ),
            "error_code": "GATE_REF_OBJECTS_NONE_FOUND",
            "status": "OPEN",
        })
        # Warn only — not a hard failure (optional policy may be capped by evidence score)
        return True, issues

    return True, []
