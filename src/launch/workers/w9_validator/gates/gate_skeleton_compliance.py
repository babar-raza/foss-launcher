"""Gate: Skeleton Compliance (TC-3687).

Validates generated content against the page-role skeleton templates defined
in ``page_skeletons.py``.  Checks missing required sections — the unique
value not already covered by G4 (section structure).

Overlap with G4: duplicate-H2 and See-Also-position are also flagged here
but at ``warning`` severity so they do not block the pipeline (G4 blocks).

Requires ``page_plan.json`` to map files to page roles.  Gracefully skips
when the plan or skeleton is unavailable.

Spec: specs/07_section_templates.md §Skeleton-First Page Structure (TC-3674)
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

from launch.workers.w5_section_writer.page_skeletons import (
    PAGE_ROLE_SKELETONS,
    validate_against_skeleton,
)


def execute_gate(run_dir: Path, profile: str) -> Tuple[bool, List[Dict[str, Any]]]:
    """Execute skeleton compliance gate.

    Loads ``page_plan.json``, maps each markdown file to its page role,
    looks up the corresponding skeleton, and runs
    ``validate_against_skeleton()`` against the content.

    Args:
        run_dir: Run directory path.
        profile: Validation profile (local, ci, prod).

    Returns:
        Tuple of (gate_passed, list_of_issues).
    """
    issues: List[Dict[str, Any]] = []

    # Load page plan for role mapping
    page_metadata = _load_page_metadata(run_dir)
    if not page_metadata:
        return True, []

    site_dir = run_dir / "work" / "site"
    if not site_dir.exists():
        return True, []

    content_dir = site_dir / "content"
    if not content_dir.exists():
        # Fall back to site_dir itself for flat layouts
        content_dir = site_dir

    for md_file in sorted(content_dir.rglob("*.md")):
        try:
            content = md_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        slug = md_file.stem
        # _index.md uses parent directory name as slug
        if slug == "_index":
            slug = md_file.parent.name

        meta = page_metadata.get(slug, {})
        page_role = meta.get("page_role", "")

        if not page_role:
            continue

        skeleton = PAGE_ROLE_SKELETONS.get(page_role)
        if not skeleton:
            continue

        # Run skeleton validation
        skeleton_issues = validate_against_skeleton(content, skeleton)

        rel_path = str(md_file.relative_to(run_dir)).replace("\\", "/")

        for idx, issue in enumerate(skeleton_issues):
            error_code = _classify_error_code(issue["message"])
            # Extract heading name for unique issue_id
            heading_slug = _extract_heading_slug(issue["message"])
            issue_suffix = f"_{heading_slug}" if heading_slug else f"_{idx}"
            issues.append({
                "issue_id": f"skeleton_{error_code.lower()}_{slug}{issue_suffix}",
                "gate": "gate_skeleton_compliance",
                "severity": "warning",
                "message": (
                    f"[{page_role}] {issue['message']} "
                    f"(file: {md_file.name})"
                ),
                "error_code": error_code,
                "location": {"path": rel_path},
                "status": "OPEN",
            })

    # All issues are warnings — gate always passes
    gate_passed = not any(
        issue.get("severity") in ("blocker", "error") for issue in issues
    )
    return gate_passed, issues


def _classify_error_code(message: str) -> str:
    """Derive a structured error code from the issue message."""
    msg_lower = message.lower()
    if "missing required section" in msg_lower:
        return "SKELETON_SECTION_MISSING"
    if "must be the last" in msg_lower:
        return "SKELETON_SEE_ALSO_POSITION"
    if "duplicate" in msg_lower:
        return "SKELETON_DUPLICATE_H2"
    return "SKELETON_COMPLIANCE"


def _extract_heading_slug(message: str) -> str:
    """Extract heading name from issue message and slugify it."""
    # "Missing required section: ## Overview" → "overview"
    # 'Duplicate H2 heading: "overview" appears 2 times' → "overview"
    m = re.search(r"## (.+?)$", message)
    if m:
        return re.sub(r"[^a-z0-9]+", "_", m.group(1).lower()).strip("_")
    m = re.search(r'"([^"]+)"', message)
    if m:
        return re.sub(r"[^a-z0-9]+", "_", m.group(1).lower()).strip("_")
    return ""


def _load_page_metadata(run_dir: Path) -> Dict[str, Dict[str, Any]]:
    """Load page metadata from page_plan.json keyed by slug."""
    plan_path = run_dir / "artifacts" / "page_plan.json"
    if not plan_path.exists():
        return {}
    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}

    result: Dict[str, Dict[str, Any]] = {}
    for page in plan.get("pages", []):
        slug = page.get("slug", "")
        if slug:
            result[slug] = page
    return result
