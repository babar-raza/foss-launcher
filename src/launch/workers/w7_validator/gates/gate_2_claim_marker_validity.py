"""Gate 2: Claim Marker Validity.

Validates that all claim_ids in content exist in product_facts.json.

Per specs/09_validation_gates.md (Gate 2 requirements derived from Gate 9 TruthLock).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple


def execute_gate(run_dir: Path, profile: str) -> Tuple[bool, List[Dict[str, Any]]]:
    """Execute Gate 2: Claim Marker Validity.

    Validates that all claim_ids referenced in content exist in product_facts.json.

    Args:
        run_dir: Run directory path
        profile: Validation profile (local, ci, prod)

    Returns:
        Tuple of (gate_passed, issues)
    """
    issues = []

    # Load product_facts.json to get valid claim_ids
    product_facts_path = run_dir / "artifacts" / "product_facts.json"
    if not product_facts_path.exists():
        # If product_facts doesn't exist, skip this gate (Gate 1 will catch it)
        return True, []

    try:
        with product_facts_path.open() as f:
            product_facts = json.load(f)
    except Exception as e:
        issues.append(
            {
                "issue_id": "claim_marker_product_facts_invalid",
                "gate": "gate_2_claim_marker_validity",
                "severity": "error",
                "message": f"Failed to load product_facts.json: {e}",
                "error_code": "GATE_CLAIM_MARKER_PRODUCT_FACTS_INVALID",
                "status": "OPEN",
            }
        )
        return False, issues

    # Extract all claim_ids from product_facts
    valid_claim_ids = set()

    # Check claim_groups (list of claim objects)
    claim_groups = product_facts.get("claim_groups", [])
    for claim_group in claim_groups:
        if isinstance(claim_group, dict):
            claim_id = claim_group.get("claim_id")
            if claim_id:
                valid_claim_ids.add(claim_id)

    # Find all markdown files
    site_dir = run_dir / "work" / "site"
    if not site_dir.exists():
        return True, []

    md_files = sorted(site_dir.rglob("*.md"))

    # Pattern to match claim markers like [claim:claim_id] or {claim_id}
    claim_pattern = re.compile(r"\[claim:([a-zA-Z0-9_-]+)\]|\{claim:([a-zA-Z0-9_-]+)\}")

    for md_file in md_files:
        try:
            content = md_file.read_text(encoding="utf-8")

            # Find all claim markers
            for match in claim_pattern.finditer(content):
                claim_id = match.group(1) or match.group(2)

                if claim_id not in valid_claim_ids:
                    # Calculate line number
                    line_num = content[: match.start()].count("\n") + 1

                    issues.append(
                        {
                            "issue_id": f"claim_marker_invalid_{md_file.name}_{claim_id}",
                            "gate": "gate_2_claim_marker_validity",
                            "severity": "error",
                            "message": f"Claim marker references non-existent claim_id: {claim_id}",
                            "error_code": "GATE_CLAIM_MARKER_INVALID",
                            "location": {"path": str(md_file), "line": line_num},
                            "status": "OPEN",
                        }
                    )

        except Exception as e:
            issues.append(
                {
                    "issue_id": f"claim_marker_read_error_{md_file.name}",
                    "gate": "gate_2_claim_marker_validity",
                    "severity": "error",
                    "message": f"Error reading file {md_file.name}: {e}",
                    "error_code": "GATE_CLAIM_MARKER_READ_ERROR",
                    "location": {"path": str(md_file)},
                    "status": "OPEN",
                }
            )

    # Gate passes if no error/blocker issues
    gate_passed = not any(
        issue["severity"] in ["blocker", "error"] for issue in issues
    )

    return gate_passed, issues
