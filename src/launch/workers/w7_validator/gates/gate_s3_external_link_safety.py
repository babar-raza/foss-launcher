"""Gate S3: External Link Safety.

Validates that external links use HTTPS only.

Per TC-571 requirements: External Link Safety (HTTPS only, no broken external links).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Tuple


def execute_gate(run_dir: Path, profile: str) -> Tuple[bool, List[Dict[str, Any]]]:
    """Execute Gate S3: External Link Safety.

    Validates that external links:
    - Use HTTPS protocol (not HTTP)
    - Are properly formed URLs

    Note: This gate does NOT check if links are broken (reachable).
    That would require network calls which are handled by Gate 7 in the spec.
    This gate focuses on security (HTTPS enforcement).

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

    # Pattern to match markdown links: [text](url)
    link_pattern = re.compile(r'\[([^\]]*)\]\(([^)]+)\)')

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

            # Check each link
            for line_num, line in processed_lines:
                for match in link_pattern.finditer(line):
                    link_text = match.group(1)
                    link_url = match.group(2).strip()

                    # Check if it's an external link
                    if link_url.startswith("http://"):
                        issues.append(
                            {
                                "issue_id": f"external_link_http_{md_file.name}_{line_num}",
                                "gate": "gate_s3_external_link_safety",
                                "severity": "error",
                                "message": f"Insecure HTTP link found in {md_file.name} at line {line_num}: {link_url[:50]}",
                                "error_code": "GATE_EXTERNAL_LINK_INSECURE_HTTP",
                                "location": {"path": str(md_file), "line": line_num},
                                "status": "OPEN",
                            }
                        )
                    elif link_url.startswith("https://"):
                        # HTTPS link is OK, no issue
                        pass
                    elif link_url.startswith("//"):
                        # Protocol-relative URL - warn to be explicit
                        issues.append(
                            {
                                "issue_id": f"external_link_protocol_relative_{md_file.name}_{line_num}",
                                "gate": "gate_s3_external_link_safety",
                                "severity": "warn",
                                "message": f"Protocol-relative URL found in {md_file.name} at line {line_num}: {link_url[:50]}. Consider using explicit https://",
                                "error_code": "GATE_EXTERNAL_LINK_PROTOCOL_RELATIVE",
                                "location": {"path": str(md_file), "line": line_num},
                                "status": "OPEN",
                            }
                        )

            # Also check HTML image tags for external sources
            img_pattern = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.IGNORECASE)
            for line_num, line in processed_lines:
                for match in img_pattern.finditer(line):
                    img_src = match.group(1).strip()

                    if img_src.startswith("http://"):
                        issues.append(
                            {
                                "issue_id": f"external_img_http_{md_file.name}_{line_num}",
                                "gate": "gate_s3_external_link_safety",
                                "severity": "error",
                                "message": f"Insecure HTTP image source in {md_file.name} at line {line_num}: {img_src[:50]}",
                                "error_code": "GATE_EXTERNAL_LINK_INSECURE_HTTP",
                                "location": {"path": str(md_file), "line": line_num},
                                "status": "OPEN",
                            }
                        )

        except Exception as e:
            issues.append(
                {
                    "issue_id": f"external_link_check_error_{md_file.name}",
                    "gate": "gate_s3_external_link_safety",
                    "severity": "error",
                    "message": f"Error checking external links in {md_file.name}: {e}",
                    "error_code": "GATE_EXTERNAL_LINK_CHECK_ERROR",
                    "location": {"path": str(md_file)},
                    "status": "OPEN",
                }
            )

    # Gate passes if no error/blocker issues (warnings are OK)
    gate_passed = not any(
        issue["severity"] in ["blocker", "error"] for issue in issues
    )

    return gate_passed, issues
