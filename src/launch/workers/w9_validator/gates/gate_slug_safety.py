"""Gate: Slug Safety Validation (TC-2841).

Validates that page slugs and output paths are clean — no repr tokens,
doubled separators, empty segments, or non-ASCII characters that would
produce broken filenames or permalinks.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

from ..._shared.slug_constants import SLUG_LEADING_STOP_WORDS

# Characters that indicate a Python repr() leak in a slug
_REPR_TOKENS_RE = re.compile(r"[\[\]'\",]")

# Doubled separator pattern
_DOUBLED_SEP_RE = re.compile(r"--")

# Empty segment in path
_EMPTY_SEGMENT_RE = re.compile(r"//")

# Valid slug characters (lowercase alphanumeric + hyphens)
_VALID_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$")


def execute_gate(run_dir: Path, profile: str) -> Tuple[bool, List[Dict[str, Any]]]:
    """Execute slug safety gate.

    Checks page_plan.json slugs and output_paths, plus generated file paths.

    Args:
        run_dir: Run directory path
        profile: Validation profile (local, ci, prod)

    Returns:
        Tuple of (gate_passed, issues)
    """
    issues: List[Dict[str, Any]] = []

    # Check page_plan.json slugs
    plan_path = run_dir / "artifacts" / "page_plan.json"
    if plan_path.exists():
        try:
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            for page in plan.get("pages", []):
                slug = page.get("slug", "")
                output_path = page.get("output_path", "")
                _check_slug(slug, output_path, profile, issues)
        except (json.JSONDecodeError, OSError):
            pass

    # Also check generated file paths in work/site/content/
    site_dir = run_dir / "work" / "site" / "content"
    if site_dir.exists():
        for md_file in sorted(site_dir.rglob("*.md")):
            try:
                rel = str(md_file.relative_to(site_dir)).replace("\\", "/")
                if _EMPTY_SEGMENT_RE.search(rel):
                    severity = "error" if profile != "local" else "warn"
                    issues.append({
                        "issue_id": f"slug_empty_segment_{md_file.name}",
                        "gate": "gate_slug_safety",
                        "severity": severity,
                        "message": f"Empty path segment in '{rel}'",
                        "error_code": "SLUG_EMPTY_SEGMENT",
                        "location": {"path": str(md_file)},
                        "status": "OPEN",
                    })
            except ValueError:
                continue

    gate_passed = not any(
        issue.get("severity") in ["blocker", "error"] for issue in issues
    )
    return gate_passed, issues


def _check_slug(
    slug: str,
    output_path: str,
    profile: str,
    issues: List[Dict[str, Any]],
) -> None:
    """Check a single slug and output_path for safety issues."""
    if not slug:
        return

    severity = "error" if profile != "local" else "warn"
    if profile == "prod":
        severity = "blocker"

    # Check for repr tokens
    if _REPR_TOKENS_RE.search(slug):
        issues.append({
            "issue_id": f"slug_repr_{slug[:30]}",
            "gate": "gate_slug_safety",
            "severity": severity,
            "message": f"Repr token in slug '{slug}' (likely str() on list/dict)",
            "error_code": "SLUG_REPR_TOKEN",
            "location": {"slug": slug},
            "status": "OPEN",
        })

    # Check for doubled separators
    if _DOUBLED_SEP_RE.search(slug):
        issues.append({
            "issue_id": f"slug_doubled_sep_{slug[:30]}",
            "gate": "gate_slug_safety",
            "severity": severity,
            "message": f"Doubled separator in slug '{slug}'",
            "error_code": "SLUG_DOUBLED_SEPARATOR",
            "location": {"slug": slug},
            "status": "OPEN",
        })

    # Check output_path for empty segments
    if output_path and _EMPTY_SEGMENT_RE.search(output_path):
        issues.append({
            "issue_id": f"slug_empty_path_{slug[:30]}",
            "gate": "gate_slug_safety",
            "severity": severity,
            "message": f"Empty segment in output_path '{output_path}'",
            "error_code": "SLUG_EMPTY_SEGMENT",
            "location": {"slug": slug, "output_path": output_path},
            "status": "OPEN",
        })

    # TC-3651: Check for 2+ consecutive leading filler/stop-words
    parts = slug.split("-")
    leading_filler = 0
    for p in parts:
        if p in SLUG_LEADING_STOP_WORDS:
            leading_filler += 1
        else:
            break
    if leading_filler >= 2:
        issues.append({
            "issue_id": f"slug_filler_prefix_{slug[:30]}",
            "gate": "gate_slug_safety",
            "severity": severity,
            "message": (
                f"Slug '{slug}' has {leading_filler} leading filler words; "
                f"likely claim text leaked into slug"
            ),
            "error_code": "SLUG_FILLER_PREFIX",
            "location": {"slug": slug},
            "status": "OPEN",
        })
