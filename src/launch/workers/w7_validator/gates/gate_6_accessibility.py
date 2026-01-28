"""Gate 6: Accessibility.

Validates heading hierarchy and alt text for images.

Per specs/09_validation_gates.md (accessibility requirements).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Tuple


def execute_gate(run_dir: Path, profile: str) -> Tuple[bool, List[Dict[str, Any]]]:
    """Execute Gate 6: Accessibility.

    Validates heading hierarchy (no skipped levels) and alt text for images.

    Args:
        run_dir: Run directory path
        profile: Validation profile (local, ci, prod)

    Returns:
        Tuple of (gate_passed, issues)
    """
    issues = []

    # Find all markdown files
    site_dir = run_dir / "work" / "site"
    if not site_dir.exists():
        return True, []

    md_files = sorted(site_dir.rglob("*.md"))

    # Pattern to match headings: # Heading
    heading_pattern = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)

    # Pattern to match images: ![alt](url)
    image_pattern = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")

    for md_file in md_files:
        try:
            content = md_file.read_text(encoding="utf-8")

            # Skip code blocks
            lines = content.split("\n")
            in_code_block = False
            processed_lines = []

            for i, line in enumerate(lines, start=1):
                if line.strip().startswith("```"):
                    in_code_block = not in_code_block
                    continue
                if not in_code_block:
                    processed_lines.append((i, line))

            # Check heading hierarchy
            heading_levels = []
            for line_num, line in processed_lines:
                heading_match = heading_pattern.match(line)
                if heading_match:
                    level = len(heading_match.group(1))
                    heading_text = heading_match.group(2)

                    # Check for skipped levels
                    if heading_levels:
                        last_level = heading_levels[-1][0]
                        if level > last_level + 1:
                            issues.append(
                                {
                                    "issue_id": f"accessibility_heading_skip_{md_file.name}_{line_num}",
                                    "gate": "gate_6_accessibility",
                                    "severity": "warn",
                                    "message": f"Heading hierarchy skipped level in {md_file.name}: jumped from h{last_level} to h{level}",
                                    "error_code": "GATE_ACCESSIBILITY_HEADING_SKIP",
                                    "location": {"path": str(md_file), "line": line_num},
                                    "status": "OPEN",
                                }
                            )

                    heading_levels.append((level, heading_text, line_num))

            # Check image alt text
            for match in image_pattern.finditer(content):
                alt_text = match.group(1).strip()
                image_url = match.group(2)

                if not alt_text:
                    # Calculate line number
                    line_num = content[: match.start()].count("\n") + 1

                    issues.append(
                        {
                            "issue_id": f"accessibility_alt_text_{md_file.name}_{line_num}",
                            "gate": "gate_6_accessibility",
                            "severity": "warn",
                            "message": f"Image missing alt text in {md_file.name}: {image_url}",
                            "error_code": "GATE_ACCESSIBILITY_ALT_TEXT_MISSING",
                            "location": {"path": str(md_file), "line": line_num},
                            "status": "OPEN",
                        }
                    )

        except Exception as e:
            issues.append(
                {
                    "issue_id": f"accessibility_check_error_{md_file.name}",
                    "gate": "gate_6_accessibility",
                    "severity": "error",
                    "message": f"Error checking accessibility in {md_file.name}: {e}",
                    "error_code": "GATE_ACCESSIBILITY_CHECK_ERROR",
                    "location": {"path": str(md_file)},
                    "status": "OPEN",
                }
            )

    # Gate passes if no error/blocker issues (warnings are OK)
    gate_passed = not any(
        issue["severity"] in ["blocker", "error"] for issue in issues
    )

    return gate_passed, issues
