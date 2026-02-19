"""Gate S1: XSS Prevention.

Validates that content does not contain unsafe HTML or script tags.

Per TC-571 requirements: XSS Prevention (no unsafe HTML, script tags sanitized).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Tuple


def execute_gate(run_dir: Path, profile: str) -> Tuple[bool, List[Dict[str, Any]]]:
    """Execute Gate S1: XSS Prevention.

    Validates that markdown content does not contain:
    - Inline <script> tags
    - Unsafe HTML tags (onclick, onerror, etc.)
    - javascript: URLs
    - data: URLs with scripts

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

    # Patterns for XSS detection
    script_tag_pattern = re.compile(r"<script[^>]*>", re.IGNORECASE)
    event_handler_pattern = re.compile(
        r'\bon(click|load|error|mouseover|submit|focus|blur|change|keyup|keydown)=',
        re.IGNORECASE,
    )
    javascript_url_pattern = re.compile(r'javascript:', re.IGNORECASE)
    data_url_pattern = re.compile(r'data:text/html', re.IGNORECASE)
    unsafe_tags_pattern = re.compile(
        r'<(iframe|embed|object|applet|meta|base|link)[^>]*>', re.IGNORECASE
    )

    for md_file in md_files:
        try:
            content = md_file.read_text(encoding="utf-8")

            # Skip code blocks for XSS checks (code examples are OK)
            lines = content.split("\n")
            in_code_block = False
            processed_lines = []

            for i, line in enumerate(lines, start=1):
                if line.strip().startswith("```"):
                    in_code_block = not in_code_block
                    continue
                if not in_code_block:
                    processed_lines.append((i, line))

            # Check for script tags
            for line_num, line in processed_lines:
                if script_tag_pattern.search(line):
                    issues.append(
                        {
                            "issue_id": f"xss_script_tag_{md_file.name}_{line_num}",
                            "gate": "gate_s1_xss_prevention",
                            "severity": "blocker",
                            "message": f"Unsafe <script> tag found in {md_file.name} at line {line_num}",
                            "error_code": "GATE_XSS_SCRIPT_TAG",
                            "location": {"path": str(md_file), "line": line_num},
                            "status": "OPEN",
                        }
                    )

                # Check for event handlers
                if event_handler_pattern.search(line):
                    issues.append(
                        {
                            "issue_id": f"xss_event_handler_{md_file.name}_{line_num}",
                            "gate": "gate_s1_xss_prevention",
                            "severity": "blocker",
                            "message": f"Unsafe event handler found in {md_file.name} at line {line_num}",
                            "error_code": "GATE_XSS_EVENT_HANDLER",
                            "location": {"path": str(md_file), "line": line_num},
                            "status": "OPEN",
                        }
                    )

                # Check for javascript: URLs
                if javascript_url_pattern.search(line):
                    issues.append(
                        {
                            "issue_id": f"xss_javascript_url_{md_file.name}_{line_num}",
                            "gate": "gate_s1_xss_prevention",
                            "severity": "blocker",
                            "message": f"Unsafe javascript: URL found in {md_file.name} at line {line_num}",
                            "error_code": "GATE_XSS_JAVASCRIPT_URL",
                            "location": {"path": str(md_file), "line": line_num},
                            "status": "OPEN",
                        }
                    )

                # Check for data: URLs
                if data_url_pattern.search(line):
                    issues.append(
                        {
                            "issue_id": f"xss_data_url_{md_file.name}_{line_num}",
                            "gate": "gate_s1_xss_prevention",
                            "severity": "warn",
                            "message": f"Potentially unsafe data: URL found in {md_file.name} at line {line_num}",
                            "error_code": "GATE_XSS_DATA_URL",
                            "location": {"path": str(md_file), "line": line_num},
                            "status": "OPEN",
                        }
                    )

                # Check for unsafe HTML tags
                if unsafe_tags_pattern.search(line):
                    issues.append(
                        {
                            "issue_id": f"xss_unsafe_tag_{md_file.name}_{line_num}",
                            "gate": "gate_s1_xss_prevention",
                            "severity": "error",
                            "message": f"Potentially unsafe HTML tag found in {md_file.name} at line {line_num}",
                            "error_code": "GATE_XSS_UNSAFE_TAG",
                            "location": {"path": str(md_file), "line": line_num},
                            "status": "OPEN",
                        }
                    )

        except Exception as e:
            issues.append(
                {
                    "issue_id": f"xss_check_error_{md_file.name}",
                    "gate": "gate_s1_xss_prevention",
                    "severity": "error",
                    "message": f"Error checking XSS in {md_file.name}: {e}",
                    "error_code": "GATE_XSS_CHECK_ERROR",
                    "location": {"path": str(md_file)},
                    "status": "OPEN",
                }
            )

    # Gate passes if no error/blocker issues
    gate_passed = not any(
        issue["severity"] in ["blocker", "error"] for issue in issues
    )

    return gate_passed, issues
