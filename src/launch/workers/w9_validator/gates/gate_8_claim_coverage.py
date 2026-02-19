"""Gate 8: Claim Coverage.

Validates that all claims have evidence in content.

Per specs/09_validation_gates.md (claim coverage requirements).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple


def execute_gate(run_dir: Path, profile: str) -> Tuple[bool, List[Dict[str, Any]]]:
    """Execute Gate 8: Claim Coverage.

    Validates that all claims in product_facts have evidence in generated content.

    Args:
        run_dir: Run directory path
        profile: Validation profile (local, ci, prod)

    Returns:
        Tuple of (gate_passed, issues)
    """
    issues = []

    # Load product_facts.json to get all claims
    product_facts_path = run_dir / "artifacts" / "product_facts.json"
    if not product_facts_path.exists():
        # If product_facts doesn't exist, skip this gate
        return True, []

    try:
        with product_facts_path.open(encoding="utf-8") as f:
            product_facts = json.load(f)
    except Exception as e:
        issues.append(
            {
                "issue_id": "claim_coverage_product_facts_invalid",
                "gate": "gate_8_claim_coverage",
                "severity": "error",
                "message": f"Failed to load product_facts.json: {e}",
                "error_code": "GATE_CLAIM_COVERAGE_PRODUCT_FACTS_INVALID",
                "status": "OPEN",
            }
        )
        return False, issues

    # Extract all claim_ids from product_facts
    all_claim_ids: Set[str] = set()

    # claim_groups is dict[str, list[str]] mapping group names to claim ID lists
    # e.g., {"key_features": ["c1", "c2"], "limitations": ["c3"]}
    claim_groups = product_facts.get("claim_groups", {})
    for group_name, claim_id_list in claim_groups.items():
        all_claim_ids.update(claim_id_list)

    # Find all markdown files and collect claim_ids referenced
    site_dir = run_dir / "work" / "site"
    if not site_dir.exists():
        # No content generated yet
        if all_claim_ids:
            issues.append(
                {
                    "issue_id": "claim_coverage_no_content",
                    "gate": "gate_8_claim_coverage",
                    "severity": "error",
                    "message": f"No content generated but {len(all_claim_ids)} claims exist in product_facts",
                    "error_code": "GATE_CLAIM_COVERAGE_NO_CONTENT",
                    "status": "OPEN",
                }
            )
            return False, issues
        return True, []

    md_files = sorted(site_dir.rglob("*.md"))

    # Collect all claim_ids referenced in content
    referenced_claim_ids: Set[str] = set()

    # Pattern to match claim markers: HTML comments (new) and brackets (legacy)
    # Supports both: <!-- claim: id --> (current) and [claim:id] (backward compat)
    claim_pattern = re.compile(
        r"<!--\s*claim:\s*([a-zA-Z0-9_-]+)\s*-->"  # HTML comment format (current)
        r"|\[claim:([a-zA-Z0-9_-]+)\]"  # Bracket format (legacy)
        r"|\{claim:([a-zA-Z0-9_-]+)\}"  # Curly brace format (legacy)
    )

    for md_file in md_files:
        try:
            content = md_file.read_text(encoding="utf-8")

            # Find all claim markers
            for match in claim_pattern.finditer(content):
                # Extract from whichever capture group matched (HTML comment, bracket, or curly)
                claim_id = match.group(1) or match.group(2) or match.group(3)
                if claim_id:
                    referenced_claim_ids.add(claim_id)

        except Exception:
            # Error reading file - will be caught by other gates
            pass

    # Check for claims without evidence in content
    uncovered_claims = all_claim_ids - referenced_claim_ids

    for claim_id in sorted(uncovered_claims):
        issues.append(
            {
                "issue_id": f"claim_coverage_missing_{claim_id}",
                "gate": "gate_8_claim_coverage",
                "severity": "warn",
                "message": f"Claim '{claim_id}' from product_facts has no evidence in content",
                "error_code": "GATE_CLAIM_COVERAGE_MISSING",
                "status": "OPEN",
            }
        )

    # Gate passes if no error/blocker issues (warnings for uncovered claims are OK)
    gate_passed = not any(
        issue["severity"] in ["blocker", "error"] for issue in issues
    )

    return gate_passed, issues
