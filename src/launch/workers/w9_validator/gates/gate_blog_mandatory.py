"""Gate: Blog Mandatory Pages.

Spec v1.1 J2: Validates that the blog section of page_plan.json contains at
least the two mandatory blog posts required by ruleset.v1_1 —
one ``blog`` (launch/announcement) post and one ``feature_blog`` (feature
highlight) post.

A ``graceful_artifact_skip: true`` entry in the registry means this gate is
skipped when ``page_plan.json`` does not exist (offline / pre-W4 runs).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple


def execute_gate(run_dir: Path, profile: str) -> Tuple[bool, List[Dict[str, Any]]]:
    """Execute Gate: Blog Mandatory Pages.

    Validates that the blog section contains at least one ``blog`` role page
    and one ``feature_blog`` role page.

    Args:
        run_dir: Run directory path.
        profile: Validation profile (local, ci, prod).

    Returns:
        Tuple of (gate_passed, issues).
    """
    issues: List[Dict[str, Any]] = []

    page_plan_path = run_dir / "artifacts" / "page_plan.json"
    if not page_plan_path.exists():
        # graceful_artifact_skip: true — skip if no page_plan
        return True, []

    try:
        with page_plan_path.open(encoding="utf-8") as f:
            page_plan = json.load(f)
    except Exception as e:
        issues.append({
            "issue_id": "gate_blog_mandatory_page_plan_invalid",
            "gate": "gate_blog_mandatory",
            "severity": "error",
            "message": f"Failed to load page_plan.json: {e}",
            "error_code": "GATE_BLOG_MANDATORY_PAGE_PLAN_INVALID",
            "status": "OPEN",
        })
        return False, issues

    blog_roles: set = set()
    for page in page_plan.get("pages", []):
        if page.get("section") == "blog":
            role = page.get("page_role", "")
            if role:
                blog_roles.add(role)

    missing_roles: List[str] = []
    # Spec v1.1: at least one launch/announcement post
    if not (blog_roles & {"blog", "announcement", "blog_announcement"}):
        missing_roles.append("blog (launch announcement)")
    # Spec v1.1: at least one feature highlight post
    if "feature_blog" not in blog_roles:
        missing_roles.append("feature_blog (feature highlight)")

    if missing_roles:
        issues.append({
            "issue_id": "gate_blog_mandatory_missing",
            "gate": "gate_blog_mandatory",
            "severity": "error",
            "message": (
                f"Blog section is missing mandatory page roles. "
                f"Missing: {missing_roles}. "
                f"Found blog page roles: {sorted(blog_roles)}."
            ),
            "error_code": "GATE_BLOG_MANDATORY_MISSING",
            "status": "OPEN",
        })
        return False, issues

    return True, []
