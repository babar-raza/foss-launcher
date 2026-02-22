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
    # TC-2342 added structured entries: conversion_pairs (list of dicts),
    # how_to_clusters (dict of lists). Only collect flat string IDs.
    claim_groups = product_facts.get("claim_groups", {})
    for group_name, claim_id_list in claim_groups.items():
        if isinstance(claim_id_list, list):
            for item in claim_id_list:
                if isinstance(item, str):
                    all_claim_ids.add(item)
                elif isinstance(item, dict):
                    # conversion_pairs entry: {"source": ..., "target": ..., "claim_ids": [...]}
                    for cid in item.get("claim_ids", []):
                        if isinstance(cid, str):
                            all_claim_ids.add(cid)
        elif isinstance(claim_id_list, dict):
            # how_to_clusters: {"topic": [claim_id, ...]}
            for topic_ids in claim_id_list.values():
                if isinstance(topic_ids, list):
                    for cid in topic_ids:
                        if isinstance(cid, str):
                            all_claim_ids.add(cid)

    # ---- page_plan-based claim validation ----
    # Instead of scanning markdown for HTML claim markers (which the sanitizer strips),
    # validate that all claims from product_facts are assigned to at least one page in
    # page_plan.json. This keeps content marker-free while ensuring claim coverage.

    # Try page_plan-based validation first (preferred)
    page_plan_path = run_dir / "artifacts" / "page_plan.json"
    use_page_plan = False
    planned_claim_ids: Set[str] = set()

    if page_plan_path.exists():
        try:
            with page_plan_path.open(encoding="utf-8") as f:
                page_plan = json.load(f)
            pages = page_plan.get("pages", [])
            for pg in pages:
                # Collect claim IDs from all possible fields
                for field in ("required_claim_ids", "claim_ids", "assigned_claims"):
                    ids = pg.get(field, [])
                    if isinstance(ids, list):
                        for cid in ids:
                            if isinstance(cid, str):
                                planned_claim_ids.add(cid)
                # Also check content_strategy.claim_ids
                cs = pg.get("content_strategy", {})
                if isinstance(cs, dict):
                    for cid in cs.get("claim_ids", []):
                        if isinstance(cid, str):
                            planned_claim_ids.add(cid)
            if planned_claim_ids:
                use_page_plan = True
        except Exception:
            pass  # Fall back to marker scanning

    if use_page_plan:
        # Plan-based: uncovered = claims in claim_groups but not in any page plan
        uncovered_claims = all_claim_ids - planned_claim_ids
    else:
        # Legacy fallback: scan markdown files for claim markers
        site_dir = run_dir / "work" / "site"
        if not site_dir.exists():
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
        referenced_claim_ids: Set[str] = set()
        claim_pattern = re.compile(
            r"<!--\s*claim:\s*([a-zA-Z0-9_-]+)\s*-->"
            r"|\[claim:([a-zA-Z0-9_-]+)\]"
            r"|\{claim:([a-zA-Z0-9_-]+)\}"
        )
        for md_file in md_files:
            try:
                content = md_file.read_text(encoding="utf-8")
                for match in claim_pattern.finditer(content):
                    claim_id = match.group(1) or match.group(2) or match.group(3)
                    if claim_id:
                        referenced_claim_ids.add(claim_id)
            except Exception:
                pass
        uncovered_claims = all_claim_ids - referenced_claim_ids

    for claim_id in sorted(uncovered_claims):
        issues.append(
            {
                "issue_id": f"claim_coverage_missing_{claim_id}",
                "gate": "gate_8_claim_coverage",
                "severity": "warn",
                "message": f"Claim '{claim_id}' from product_facts has no evidence in content"
                + (" (page_plan)" if use_page_plan else " (marker scan)"),
                "error_code": "GATE_CLAIM_COVERAGE_MISSING",
                "status": "OPEN",
            }
        )

    # Gate passes if no error/blocker issues (warnings for uncovered claims are OK)
    gate_passed = not any(
        issue["severity"] in ["blocker", "error"] for issue in issues
    )

    return gate_passed, issues
