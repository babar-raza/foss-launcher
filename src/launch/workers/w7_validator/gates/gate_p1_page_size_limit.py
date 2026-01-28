"""Gate P1: Page Size Limit.

Validates that all generated pages are under 500KB in size.

Per TC-571 requirements: Page Size Limit (< 500KB per page).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple


def execute_gate(run_dir: Path, profile: str) -> Tuple[bool, List[Dict[str, Any]]]:
    """Execute Gate P1: Page Size Limit.

    Validates that all generated markdown pages are under 500KB in size.

    Args:
        run_dir: Run directory path
        profile: Validation profile (local, ci, prod)

    Returns:
        Tuple of (gate_passed, issues)
    """
    issues = []
    max_size_kb = 500
    max_size_bytes = max_size_kb * 1024

    # Find all markdown files
    site_dir = run_dir / "work" / "site"
    if not site_dir.exists():
        return True, []

    md_files = sorted(site_dir.rglob("*.md"))

    for md_file in md_files:
        try:
            file_size = md_file.stat().st_size

            if file_size > max_size_bytes:
                size_kb = file_size / 1024
                issues.append(
                    {
                        "issue_id": f"page_size_limit_{md_file.name}",
                        "gate": "gate_p1_page_size_limit",
                        "severity": "error",
                        "message": f"Page {md_file.name} exceeds size limit: {size_kb:.2f}KB > {max_size_kb}KB",
                        "error_code": "GATE_PAGE_SIZE_LIMIT_EXCEEDED",
                        "location": {"path": str(md_file)},
                        "status": "OPEN",
                    }
                )

        except Exception as e:
            issues.append(
                {
                    "issue_id": f"page_size_check_error_{md_file.name}",
                    "gate": "gate_p1_page_size_limit",
                    "severity": "error",
                    "message": f"Error checking page size for {md_file.name}: {e}",
                    "error_code": "GATE_PAGE_SIZE_CHECK_ERROR",
                    "location": {"path": str(md_file)},
                    "status": "OPEN",
                }
            )

    # Gate passes if no error/blocker issues
    gate_passed = not any(
        issue["severity"] in ["blocker", "error"] for issue in issues
    )

    return gate_passed, issues
