"""Gate: Reference Page Completeness (TC-3676).

Validates that reference pages (api_reference, reference_object_page) contain
the structural elements required for useful API documentation:
1. At least one code fence (not just a placeholder ``pass``)
2. At least one API table (markdown table with relevant headers)
3. Page mentions its object_name (if available from page_plan)

Error codes:
  REF_MISSING_CODE_FENCE   -- no qualifying code fence found
  REF_PLACEHOLDER_CODE     -- code fence contains only placeholder content
  REF_MISSING_API_TABLE    -- no API summary table found
  REF_MISSING_OBJECT_NAME  -- page does not mention its object_name

Spec: specs/09_validation_gates.md §Quality Enforcement Hardening
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_REFERENCE_ROLES = frozenset({"api_reference", "reference_object_page"})

# Placeholder-only code patterns (trivially useless code fences)
_PLACEHOLDER_RE = re.compile(
    r"^\s*(?:pass|\.\.\.|\#\s*(?:TODO|FIXME|placeholder|no code|see)\b.*)\s*$",
    re.IGNORECASE | re.MULTILINE,
)

# API table header patterns — at least one column must match
_API_TABLE_HEADERS = re.compile(
    r"\b(?:parameter|property|method|function|field|member|argument|return|type|description)\b",
    re.IGNORECASE,
)


def execute_gate(run_dir: Path, profile: str) -> Tuple[bool, List[Dict[str, Any]]]:
    """Execute reference completeness gate.

    Applies ONLY to pages with page_role in (api_reference, reference_object_page).

    Args:
        run_dir: Run directory path.
        profile: Validation profile (local, ci, prod).

    Returns:
        Tuple of (gate_passed, issues).
    """
    issues: List[Dict[str, Any]] = []

    # Load page_plan to identify reference pages
    plan_path = run_dir / "artifacts" / "page_plan.json"
    if not plan_path.exists():
        return True, []

    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return True, []

    pages = plan.get("pages", [])
    ref_pages = [p for p in pages if p.get("page_role") in _REFERENCE_ROLES]
    if not ref_pages:
        return True, []

    site_dir = run_dir / "work" / "site" / "content"

    for page in ref_pages:
        slug = page.get("slug", "unknown")
        output_path = page.get("output_path", "")
        object_name = page.get("object_name", "")

        # Find the generated markdown file
        md_path = _find_md_file(site_dir, output_path, slug)
        if md_path is None or not md_path.exists():
            continue

        try:
            content = md_path.read_text(encoding="utf-8")
        except OSError:
            continue

        rel_path = str(md_path.relative_to(run_dir)).replace("\\", "/")

        # 1. Check for qualifying code fences
        fences = _extract_code_fences(content)
        if not fences:
            issues.append(_make_issue(
                f"ref_missing_code_{slug}",
                "error",
                f"Reference page '{slug}' has no code fences",
                "REF_MISSING_CODE_FENCE",
                rel_path,
            ))
        elif all(_is_placeholder(f) for f in fences):
            issues.append(_make_issue(
                f"ref_placeholder_code_{slug}",
                "error",
                f"Reference page '{slug}' has only placeholder code",
                "REF_PLACEHOLDER_CODE",
                rel_path,
            ))

        # 2. Check for API table
        if not _has_api_table(content):
            issues.append(_make_issue(
                f"ref_missing_table_{slug}",
                "error",
                f"Reference page '{slug}' has no API summary table",
                "REF_MISSING_API_TABLE",
                rel_path,
            ))

        # 3. Check object_name mentioned
        if object_name and object_name.lower() not in content.lower():
            issues.append(_make_issue(
                f"ref_missing_objname_{slug}",
                "warn",
                f"Reference page '{slug}' does not mention its object_name '{object_name}'",
                "REF_MISSING_OBJECT_NAME",
                rel_path,
            ))

    gate_passed = not any(
        issue.get("severity") in ("blocker", "error") for issue in issues
    )
    return gate_passed, issues


def _make_issue(
    issue_id: str,
    severity: str,
    message: str,
    error_code: str,
    path: str,
) -> Dict[str, Any]:
    return {
        "issue_id": issue_id,
        "gate": "gate_reference_completeness",
        "severity": severity,
        "message": message,
        "error_code": error_code,
        "location": {"path": path},
        "status": "OPEN",
    }


def _find_md_file(
    site_dir: Path, output_path: str, slug: str,
) -> Optional[Path]:
    """Find the markdown file for a reference page."""
    if not site_dir.exists():
        return None

    # Try output_path first
    if output_path:
        candidate = site_dir / output_path
        if candidate.exists():
            return candidate
        # Try with .md extension
        if not output_path.endswith(".md"):
            candidate = site_dir / f"{output_path}.md"
            if candidate.exists():
                return candidate

    # Fallback: search by slug
    for md_file in site_dir.rglob("*.md"):
        if md_file.stem == slug:
            return md_file

    return None


def _extract_code_fences(content: str) -> List[str]:
    """Extract code fence bodies from markdown."""
    fences: List[str] = []
    in_fence = False
    fence_lines: List[str] = []

    for line in content.split("\n"):
        if line.strip().startswith("```"):
            if in_fence:
                fences.append("\n".join(fence_lines))
                fence_lines = []
                in_fence = False
            else:
                in_fence = True
                fence_lines = []
        elif in_fence:
            fence_lines.append(line)

    return fences


def _is_placeholder(code: str) -> bool:
    """Check if a code fence body is trivially placeholder content."""
    stripped = code.strip()
    if not stripped:
        return True
    # All lines are placeholder-like
    for line in stripped.split("\n"):
        line = line.strip()
        if not line:
            continue
        if not _PLACEHOLDER_RE.match(line):
            return False
    return True


def _has_api_table(content: str) -> bool:
    """Check if content contains a markdown table with API-relevant headers."""
    in_fence = False
    found_header = False

    for line in content.split("\n"):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        # Look for table header rows (contain | and API keywords)
        if "|" in line and _API_TABLE_HEADERS.search(line):
            found_header = True
        # Look for separator row after header
        if found_header and re.match(r"^\s*\|[\s:-]+\|", line):
            return True

    return False
