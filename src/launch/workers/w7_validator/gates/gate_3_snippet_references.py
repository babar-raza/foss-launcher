"""Gate 3: Snippet References.

Validates that all snippet_ids referenced in content exist in snippet_catalog.json.

Per specs/09_validation_gates.md (Gate 8 Snippet Checks).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple


def execute_gate(run_dir: Path, profile: str) -> Tuple[bool, List[Dict[str, Any]]]:
    """Execute Gate 3: Snippet References.

    Validates that all snippet_ids referenced in content exist in snippet_catalog.json.

    Args:
        run_dir: Run directory path
        profile: Validation profile (local, ci, prod)

    Returns:
        Tuple of (gate_passed, issues)
    """
    issues = []

    # Load snippet_catalog.json to get valid snippet_ids
    snippet_catalog_path = run_dir / "artifacts" / "snippet_catalog.json"
    if not snippet_catalog_path.exists():
        # If snippet_catalog doesn't exist, skip this gate
        return True, []

    try:
        with snippet_catalog_path.open(encoding="utf-8") as f:
            snippet_catalog = json.load(f)
    except Exception as e:
        issues.append(
            {
                "issue_id": "snippet_ref_catalog_invalid",
                "gate": "gate_3_snippet_references",
                "severity": "error",
                "message": f"Failed to load snippet_catalog.json: {e}",
                "error_code": "GATE_SNIPPET_CATALOG_INVALID",
                "status": "OPEN",
            }
        )
        return False, issues

    # Extract all snippet_ids from catalog
    valid_snippet_ids = set()

    # snippet_catalog is a list of snippet objects
    snippets = snippet_catalog.get("snippets", [])
    for snippet in snippets:
        if isinstance(snippet, dict):
            snippet_id = snippet.get("snippet_id")
            if snippet_id:
                valid_snippet_ids.add(snippet_id)

    # Find all markdown files
    site_dir = run_dir / "work" / "site"
    if not site_dir.exists():
        return True, []

    md_files = sorted(site_dir.rglob("*.md"))

    # Pattern to match snippet references like [snippet:snippet_id] or {{snippet:snippet_id}}
    snippet_pattern = re.compile(
        r"\[snippet:([a-zA-Z0-9_-]+)\]|\{\{snippet:([a-zA-Z0-9_-]+)\}\}"
    )

    for md_file in md_files:
        try:
            content = md_file.read_text(encoding="utf-8")

            # Find all snippet references
            for match in snippet_pattern.finditer(content):
                snippet_id = match.group(1) or match.group(2)

                if snippet_id not in valid_snippet_ids:
                    # Calculate line number
                    line_num = content[: match.start()].count("\n") + 1

                    issues.append(
                        {
                            "issue_id": f"snippet_ref_invalid_{md_file.name}_{snippet_id}",
                            "gate": "gate_3_snippet_references",
                            "severity": "error",
                            "message": f"Snippet reference to non-existent snippet_id: {snippet_id}",
                            "error_code": "GATE_SNIPPET_NOT_IN_CATALOG",
                            "location": {"path": str(md_file), "line": line_num},
                            "status": "OPEN",
                        }
                    )

        except Exception as e:
            issues.append(
                {
                    "issue_id": f"snippet_ref_read_error_{md_file.name}",
                    "gate": "gate_3_snippet_references",
                    "severity": "error",
                    "message": f"Error reading file {md_file.name}: {e}",
                    "error_code": "GATE_SNIPPET_READ_ERROR",
                    "location": {"path": str(md_file)},
                    "status": "OPEN",
                }
            )

    # Gate passes if no error/blocker issues
    gate_passed = not any(
        issue["severity"] in ["blocker", "error"] for issue in issues
    )

    return gate_passed, issues
