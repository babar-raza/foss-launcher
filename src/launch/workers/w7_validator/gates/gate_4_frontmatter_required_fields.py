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
    match = re.match(r"^---\s*\n(.*?\n)---\s*\n(.*)$", content, re.DOTALL)
    if not match:
        return None, content

    try:
        frontmatter = yaml.safe_load(match.group(1))
        body = match.group(2)
        return frontmatter, body
    except yaml.YAMLError:
        return None, content


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
