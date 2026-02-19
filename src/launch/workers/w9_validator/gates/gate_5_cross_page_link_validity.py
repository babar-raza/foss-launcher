"""Gate 5: Cross-Page Link Validity.

Validates that all internal markdown links resolve to existing files.

Per specs/09_validation_gates.md (Gate 6 Internal Links).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Tuple
from urllib.parse import urlparse


def execute_gate(run_dir: Path, profile: str) -> Tuple[bool, List[Dict[str, Any]]]:
    """Execute Gate 5: Cross-Page Link Validity.

    Validates that all internal markdown links resolve to existing files.

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

    # Pattern to match markdown links: [text](url) or [text](url#anchor)
    link_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

    for md_file in md_files:
        try:
            content = md_file.read_text(encoding="utf-8")

            # Skip code blocks
            lines = content.split("\n")
            in_code_block = False
            processed_content = []

            for line in lines:
                if line.strip().startswith("```"):
                    in_code_block = not in_code_block
                    continue
                if not in_code_block:
                    processed_content.append(line)

            content_no_code = "\n".join(processed_content)

            # Find all links
            for match in link_pattern.finditer(content_no_code):
                link_text = match.group(1)
                link_url = match.group(2)

                # Parse URL
                parsed = urlparse(link_url)

                # Skip external links (http://, https://, mailto:, etc.)
                if parsed.scheme in ["http", "https", "mailto", "ftp"]:
                    continue

                # Skip absolute paths starting with / (Hugo-specific)
                if link_url.startswith("/"):
                    continue

                # Extract path without anchor
                link_path = parsed.path
                if not link_path:
                    # Anchor-only link like #heading
                    continue

                # Resolve relative path
                try:
                    target_path = (md_file.parent / link_path).resolve()

                    # Check if target exists - try multiple Hugo conventions
                    target_exists = target_path.exists()

                    if not target_exists:
                        # Hugo convention: ./foo/ links to foo.md or foo/_index.md
                        link_no_slash = link_path.rstrip("/")
                        if link_no_slash:
                            # Try as .md file
                            md_target = (md_file.parent / f"{link_no_slash}.md").resolve()
                            if md_target.exists():
                                target_exists = True
                            else:
                                # Try as _index.md inside directory
                                index_target = (md_file.parent / link_no_slash / "_index.md").resolve()
                                if index_target.exists():
                                    target_exists = True
                                else:
                                    # Try as index.md inside directory
                                    index_target = (md_file.parent / link_no_slash / "index.md").resolve()
                                    if index_target.exists():
                                        target_exists = True

                    if not target_exists:
                        # Calculate line number
                        line_num = content[: match.start()].count("\n") + 1

                        issues.append(
                            {
                                "issue_id": f"link_broken_{md_file.name}_{target_path.name}",
                                "gate": "gate_5_cross_page_link_validity",
                                "severity": "error",
                                "message": f"Broken internal link to '{link_path}' in {md_file.name}",
                                "error_code": "GATE_LINK_BROKEN_INTERNAL",
                                "location": {"path": str(md_file), "line": line_num},
                                "status": "OPEN",
                            }
                        )

                except Exception:
                    # Invalid relative path
                    line_num = content[: match.start()].count("\n") + 1

                    issues.append(
                        {
                            "issue_id": f"link_invalid_{md_file.name}_{link_path}",
                            "gate": "gate_5_cross_page_link_validity",
                            "severity": "error",
                            "message": f"Invalid relative link '{link_path}' in {md_file.name}",
                            "error_code": "GATE_LINK_BROKEN_RELATIVE",
                            "location": {"path": str(md_file), "line": line_num},
                            "status": "OPEN",
                        }
                    )

        except Exception as e:
            issues.append(
                {
                    "issue_id": f"link_check_error_{md_file.name}",
                    "gate": "gate_5_cross_page_link_validity",
                    "severity": "error",
                    "message": f"Error checking links in {md_file.name}: {e}",
                    "error_code": "GATE_LINK_CHECK_ERROR",
                    "location": {"path": str(md_file)},
                    "status": "OPEN",
                }
            )

    # Gate passes if no error/blocker issues
    gate_passed = not any(
        issue["severity"] in ["blocker", "error"] for issue in issues
    )

    return gate_passed, issues
