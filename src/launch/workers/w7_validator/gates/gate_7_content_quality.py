"""Gate 7: Content Quality.

Validates minimum content length and checks for placeholder text.

Per specs/09_validation_gates.md (content quality requirements).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Tuple


def execute_gate(run_dir: Path, profile: str) -> Tuple[bool, List[Dict[str, Any]]]:
    """Execute Gate 7: Content Quality.

    Validates minimum content length and checks for Lorem Ipsum placeholder text.

    Args:
        run_dir: Run directory path
        profile: Validation profile (local, ci, prod)

    Returns:
        Tuple of (gate_passed, issues)
    """
    issues = []

    # Minimum content length (characters, excluding frontmatter)
    MIN_CONTENT_LENGTH = 100

    # Find all markdown files
    site_dir = run_dir / "work" / "site"
    if not site_dir.exists():
        return True, []

    md_files = sorted(site_dir.rglob("*.md"))

    # Pattern to match Lorem Ipsum text (case-insensitive)
    lorem_pattern = re.compile(r"lorem\s+ipsum", re.IGNORECASE)

    for md_file in md_files:
        try:
            content = md_file.read_text(encoding="utf-8")

            # Extract body content (skip frontmatter)
            # Frontmatter is between --- at start
            frontmatter_match = re.match(
                r"^---\s*\n.*?\n---\s*\n(.*)$", content, re.DOTALL
            )
            if frontmatter_match:
                body = frontmatter_match.group(1)
            else:
                body = content

            # Strip whitespace and measure length
            body_stripped = body.strip()

            # Check minimum length
            if len(body_stripped) < MIN_CONTENT_LENGTH:
                issues.append(
                    {
                        "issue_id": f"content_quality_length_{md_file.name}",
                        "gate": "gate_7_content_quality",
                        "severity": "warn",
                        "message": f"Content too short in {md_file.name}: {len(body_stripped)} characters (minimum {MIN_CONTENT_LENGTH})",
                        "error_code": "GATE_CONTENT_QUALITY_MIN_LENGTH",
                        "location": {"path": str(md_file)},
                        "status": "OPEN",
                    }
                )

            # Check for Lorem Ipsum placeholder text
            lorem_matches = list(lorem_pattern.finditer(content))
            if lorem_matches:
                for match in lorem_matches:
                    line_num = content[: match.start()].count("\n") + 1

                    issues.append(
                        {
                            "issue_id": f"content_quality_lorem_{md_file.name}_{line_num}",
                            "gate": "gate_7_content_quality",
                            "severity": "error",
                            "message": f"Lorem Ipsum placeholder text found in {md_file.name}",
                            "error_code": "GATE_CONTENT_QUALITY_LOREM_IPSUM",
                            "location": {"path": str(md_file), "line": line_num},
                            "status": "OPEN",
                        }
                    )

        except Exception as e:
            issues.append(
                {
                    "issue_id": f"content_quality_check_error_{md_file.name}",
                    "gate": "gate_7_content_quality",
                    "severity": "error",
                    "message": f"Error checking content quality in {md_file.name}: {e}",
                    "error_code": "GATE_CONTENT_QUALITY_CHECK_ERROR",
                    "location": {"path": str(md_file)},
                    "status": "OPEN",
                }
            )

    # Gate passes if no error/blocker issues (warnings are OK)
    gate_passed = not any(
        issue["severity"] in ["blocker", "error"] for issue in issues
    )

    return gate_passed, issues
