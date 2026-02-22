"""Gate 4: Frontmatter Required Fields.

Validates that all markdown files have required frontmatter fields (title, layout, permalink).

Per specs/09_validation_gates.md (Gate 2 Markdown Lint and Frontmatter Validation).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml


def parse_frontmatter(content: str) -> Tuple[Optional[Dict[str, Any]], str]:
    """Parse YAML frontmatter from markdown content.

    Args:
        content: Markdown file content

    Returns:
        Tuple of (frontmatter dict or None, body content)
    """
    # Match frontmatter: --- at start, YAML content, closing ---
    # The \n? after closing --- handles frontmatter-only files (e.g., products template)
    match = re.match(r"^---\s*\n(.*?\n)---\s*\n?(.*)$", content, re.DOTALL)
    if not match:
        return None, content

    try:
        frontmatter = yaml.safe_load(match.group(1))
        body = match.group(2)
        return frontmatter, body
    except yaml.YAMLError:
        return None, content


def _check_seo_fields(frontmatter: Dict[str, Any], path: str) -> List[Dict]:
    """Check SEO frontmatter quality (D-8 / TC-2387).

    Checks:
    - G4-SEO-001: description field present
    - G4-SEO-002: description <= 160 chars
    - G4-SEO-003: seoTitle <= 60 chars
    """
    import os

    issues = []

    def _slug(p: str) -> str:
        return re.sub(r"[^a-zA-Z0-9_-]", "_", os.path.splitext(os.path.basename(p))[0])[:40]

    description = frontmatter.get("description", "")
    if not description:
        issues.append({
            "issue_id": f"gate4_seo_no_desc_{_slug(path)}",
            "gate": "gate_4_frontmatter",
            "severity": "warn",
            "message": "Missing 'description' field (required for SEO)",
            "error_code": "G4-SEO-001",
            "location": {"path": path, "line": 1},
            "status": "OPEN",
        })
    elif len(description) > 160:
        issues.append({
            "issue_id": f"gate4_seo_long_desc_{_slug(path)}",
            "gate": "gate_4_frontmatter",
            "severity": "warn",
            "message": f"'description' is {len(description)} chars (max 160 for SEO)",
            "error_code": "G4-SEO-002",
            "location": {"path": path, "line": 1},
            "status": "OPEN",
        })

    seo_title = frontmatter.get("seoTitle", frontmatter.get("title", ""))
    if seo_title and len(seo_title) > 60:
        issues.append({
            "issue_id": f"gate4_seo_long_title_{_slug(path)}",
            "gate": "gate_4_frontmatter",
            "severity": "warn",
            "message": f"'seoTitle' is {len(seo_title)} chars (max 60 for SEO)",
            "error_code": "G4-SEO-003",
            "location": {"path": path, "line": 1},
            "status": "OPEN",
        })

    return issues


def execute_gate(run_dir: Path, profile: str) -> Tuple[bool, List[Dict[str, Any]]]:
    """Execute Gate 4: Frontmatter Required Fields.

    Validates that all markdown files have required frontmatter fields.

    Required fields: title, layout, permalink

    Args:
        run_dir: Run directory path
        profile: Validation profile (local, ci, prod)

    Returns:
        Tuple of (gate_passed, issues)
    """
    issues = []

    # Required frontmatter fields
    required_fields = ["title", "layout", "permalink"]

    # Find all markdown files
    site_dir = run_dir / "work" / "site"
    if not site_dir.exists():
        return True, []

    md_files = sorted(site_dir.rglob("*.md"))

    for md_file in md_files:
        try:
            content = md_file.read_text(encoding="utf-8")
            frontmatter, _ = parse_frontmatter(content)

            if frontmatter is None:
                issues.append(
                    {
                        "issue_id": f"frontmatter_missing_{md_file.name}",
                        "gate": "gate_4_frontmatter_required_fields",
                        "severity": "error",
                        "message": f"File missing frontmatter: {md_file.name}",
                        "error_code": "GATE_FRONTMATTER_MISSING",
                        "location": {"path": str(md_file), "line": 1},
                        "status": "OPEN",
                    }
                )
                continue

            # Check for required fields
            for field in required_fields:
                if field not in frontmatter or not frontmatter[field]:
                    issues.append(
                        {
                            "issue_id": f"frontmatter_field_missing_{md_file.name}_{field}",
                            "gate": "gate_4_frontmatter_required_fields",
                            "severity": "error",
                            "message": f"Required frontmatter field '{field}' missing or empty in {md_file.name}",
                            "error_code": "GATE_FRONTMATTER_REQUIRED_FIELD_MISSING",
                            "location": {"path": str(md_file), "line": 1},
                            "status": "OPEN",
                        }
                    )

            # SEO field quality checks (TC-2387 / D-8)
            if frontmatter is not None:
                seo_issues = _check_seo_fields(frontmatter, str(md_file))
                issues.extend(seo_issues)

        except Exception as e:
            issues.append(
                {
                    "issue_id": f"frontmatter_read_error_{md_file.name}",
                    "gate": "gate_4_frontmatter_required_fields",
                    "severity": "error",
                    "message": f"Error reading file {md_file.name}: {e}",
                    "error_code": "GATE_FRONTMATTER_READ_ERROR",
                    "location": {"path": str(md_file)},
                    "status": "OPEN",
                }
            )

    # Gate passes if no error/blocker issues
    gate_passed = not any(
        issue["severity"] in ["blocker", "error"] for issue in issues
    )

    return gate_passed, issues
