"""Gate 9: Navigation Integrity.

Validates that all navigation links exist and no orphaned pages.

Per specs/09_validation_gates.md (navigation integrity requirements).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple


def execute_gate(run_dir: Path, profile: str) -> Tuple[bool, List[Dict[str, Any]]]:
    """Execute Gate 9: Navigation Integrity.

    Validates navigation links exist and checks for orphaned pages.

    Args:
        run_dir: Run directory path
        profile: Validation profile (local, ci, prod)

    Returns:
        Tuple of (gate_passed, issues)
    """
    issues = []

    # Load page_plan.json to get expected pages
    page_plan_path = run_dir / "artifacts" / "page_plan.json"
    if not page_plan_path.exists():
        # If page_plan doesn't exist, skip this gate
        return True, []

    try:
        with page_plan_path.open(encoding="utf-8") as f:
            page_plan = json.load(f)
    except Exception as e:
        issues.append(
            {
                "issue_id": "navigation_page_plan_invalid",
                "gate": "gate_9_navigation_integrity",
                "severity": "error",
                "message": f"Failed to load page_plan.json: {e}",
                "error_code": "GATE_NAVIGATION_PAGE_PLAN_INVALID",
                "status": "OPEN",
            }
        )
        return False, issues

    # Extract expected pages from page_plan
    planned_pages: Set[str] = set()

    pages = page_plan.get("pages", [])
    for page in pages:
        if isinstance(page, dict):
            output_path = page.get("output_path")
            if output_path:
                planned_pages.add(output_path)

    # Find all actual markdown files
    site_dir = run_dir / "work" / "site"
    if not site_dir.exists():
        return True, []

    md_files = sorted(site_dir.rglob("*.md"))

    # Collect all actual page paths (relative to site_dir)
    actual_pages: Set[str] = set()
    for md_file in md_files:
        rel_path = str(md_file.relative_to(site_dir))
        # Normalize path separators to forward slashes for cross-platform compatibility
        rel_path = rel_path.replace("\\", "/")
        actual_pages.add(rel_path)

    # Check for orphaned pages (actual pages not in plan)
    orphaned_pages = actual_pages - planned_pages

    for orphan in sorted(orphaned_pages):
        issues.append(
            {
                "issue_id": f"navigation_orphan_{orphan.replace('/', '_')}",
                "gate": "gate_9_navigation_integrity",
                "severity": "warn",
                "message": f"Orphaned page not in page_plan: {orphan}",
                "error_code": "GATE_NAVIGATION_ORPHAN_PAGE",
                "location": {"path": str(site_dir / orphan)},
                "status": "OPEN",
            }
        )

    # Check for missing planned pages (pages in plan but not generated)
    missing_pages = planned_pages - actual_pages

    for missing in sorted(missing_pages):
        issues.append(
            {
                "issue_id": f"navigation_missing_{missing.replace('/', '_')}",
                "gate": "gate_9_navigation_integrity",
                "severity": "error",
                "message": f"Planned page not generated: {missing}",
                "error_code": "GATE_NAVIGATION_MISSING_PAGE",
                "status": "OPEN",
            }
        )

    # Pattern to match navigation frontmatter field
    # Look for nav_menu or menu fields in frontmatter
    for md_file in md_files:
        try:
            content = md_file.read_text(encoding="utf-8")

            # Parse frontmatter
            frontmatter_match = re.match(
                r"^---\s*\n(.*?\n)---\s*\n", content, re.DOTALL
            )
            if frontmatter_match:
                import yaml

                try:
                    frontmatter = yaml.safe_load(frontmatter_match.group(1))

                    # Check for nav_menu field
                    nav_menu = frontmatter.get("nav_menu") or frontmatter.get("menu")
                    if nav_menu and isinstance(nav_menu, list):
                        # Validate nav links exist
                        for nav_item in nav_menu:
                            if isinstance(nav_item, dict):
                                link = nav_item.get("link") or nav_item.get("url")
                                if link and not link.startswith("http"):
                                    # Internal link - check if it exists
                                    # Strip leading slash
                                    link_path = link.lstrip("/")
                                    if link_path not in actual_pages:
                                        issues.append(
                                            {
                                                "issue_id": f"navigation_broken_link_{md_file.name}_{link_path.replace('/', '_')}",
                                                "gate": "gate_9_navigation_integrity",
                                                "severity": "error",
                                                "message": f"Navigation link to non-existent page: {link}",
                                                "error_code": "GATE_NAVIGATION_BROKEN_LINK",
                                                "location": {"path": str(md_file)},
                                                "status": "OPEN",
                                            }
                                        )

                except yaml.YAMLError:
                    pass  # YAML errors caught by other gates

        except Exception:
            # Error reading file - will be caught by other gates
            pass

    # Gate passes if no error/blocker issues (warnings are OK)
    gate_passed = not any(
        issue["severity"] in ["blocker", "error"] for issue in issues
    )

    return gate_passed, issues
