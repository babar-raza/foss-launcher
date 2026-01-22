#!/usr/bin/env python3
"""
STATUS_BOARD Generator

Reads YAML frontmatter from all taskcards and generates a unified
STATUS_BOARD.md table for swarm coordination.

This ensures single source of truth: taskcard frontmatter is canonical,
and the status board is a generated view.
"""

import sys
import re
from pathlib import Path
from typing import Dict, List
import yaml
from datetime import datetime


def extract_frontmatter(content: str) -> Dict | None:
    """Extract YAML frontmatter from markdown content."""
    if not content.startswith("---\n"):
        return None

    match = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
    if not match:
        return None

    try:
        data = yaml.safe_load(match.group(1))
        return data if isinstance(data, dict) else None
    except yaml.YAMLError:
        return None


def read_taskcard_metadata(filepath: Path) -> Dict | None:
    """Read taskcard and extract metadata."""
    try:
        content = filepath.read_text(encoding="utf-8")
        frontmatter = extract_frontmatter(content)
        if frontmatter:
            # Add filename for reference
            frontmatter["_filename"] = filepath.name
        return frontmatter
    except Exception as e:
        print(f"Warning: Failed to read {filepath.name}: {e}", file=sys.stderr)
        return None


def find_taskcards(base_path: Path) -> List[Path]:
    """Find all taskcard markdown files."""
    taskcards_dir = base_path / "plans" / "taskcards"
    if not taskcards_dir.exists():
        return []

    taskcards = []
    for md_file in taskcards_dir.glob("*.md"):
        if re.match(r"^TC-\d+.*\.md$", md_file.name):
            taskcards.append(md_file)

    return sorted(taskcards)


def format_list(items: List[str]) -> str:
    """Format a list for markdown cell (comma-separated)."""
    if not items:
        return "-"
    return ", ".join(items)


def generate_status_board(taskcards_metadata: List[Dict]) -> str:
    """Generate STATUS_BOARD markdown content."""
    lines = [
        "# Taskcard Status Board",
        "",
        "> **Auto-generated** by `tools/generate_status_board.py`",
        "> **Do not edit manually** - all changes will be overwritten",
        "> **Single source of truth**: taskcard YAML frontmatter",
        "",
        f"Last generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}",
        "",
        "## Status Values",
        "",
        "- **Draft**: Taskcard under development, not ready for implementation",
        "- **Ready**: Taskcard complete and ready for agent pickup",
        "- **In-Progress**: Currently being implemented by an agent",
        "- **Blocked**: Cannot proceed due to dependencies or unresolved issues",
        "- **Done**: Implementation complete and accepted",
        "",
        "## Taskcards",
        "",
        "| ID | Title | Status | Owner | Depends On | Allowed Paths | Evidence Required | Updated |",
        "|---|---|---|---|---|---|---|---|",
    ]

    # Sort by ID
    sorted_cards = sorted(taskcards_metadata, key=lambda x: x.get("id", ""))

    for card in sorted_cards:
        tc_id = card.get("id", "MISSING")
        title = card.get("title", "MISSING")
        status = card.get("status", "MISSING")
        owner = card.get("owner", "MISSING")
        depends_on = format_list(card.get("depends_on", []))

        # Truncate long path lists
        allowed_paths = card.get("allowed_paths", [])
        if len(allowed_paths) > 3:
            paths_display = f"{len(allowed_paths)} paths"
        else:
            paths_display = format_list(allowed_paths)

        # Truncate long evidence lists
        evidence = card.get("evidence_required", [])
        if len(evidence) > 3:
            evidence_display = f"{len(evidence)} items"
        else:
            evidence_display = format_list(evidence)

        updated = card.get("updated", "MISSING")

        lines.append(
            f"| {tc_id} | {title} | {status} | {owner} | {depends_on} | "
            f"{paths_display} | {evidence_display} | {updated} |"
        )

    lines.extend([
        "",
        "## Summary",
        "",
        f"- **Total taskcards**: {len(sorted_cards)}",
    ])

    # Count by status
    status_counts = {}
    for card in sorted_cards:
        status = card.get("status", "MISSING")
        status_counts[status] = status_counts.get(status, 0) + 1

    for status, count in sorted(status_counts.items()):
        lines.append(f"- **{status}**: {count}")

    lines.append("")
    return "\n".join(lines)


def main():
    """Main generation routine."""
    # Determine repo root
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent

    print(f"Generating STATUS_BOARD from taskcards in: {repo_root}")

    # Find all taskcards
    taskcards = find_taskcards(repo_root)
    if not taskcards:
        print("ERROR: No taskcards found in plans/taskcards/")
        return 1

    print(f"Found {len(taskcards)} taskcard(s)")

    # Read metadata from all taskcards
    metadata_list = []
    for tc_path in taskcards:
        metadata = read_taskcard_metadata(tc_path)
        if metadata:
            metadata_list.append(metadata)
        else:
            print(f"Warning: Skipping {tc_path.name} (no valid frontmatter)")

    if not metadata_list:
        print("ERROR: No valid taskcard metadata found")
        return 1

    # Generate STATUS_BOARD content
    board_content = generate_status_board(metadata_list)

    # Write to file
    output_path = repo_root / "plans" / "taskcards" / "STATUS_BOARD.md"
    try:
        output_path.write_text(board_content, encoding="utf-8")
        print(f"\nSUCCESS: Generated {output_path.relative_to(repo_root)}")
        print(f"  Total taskcards: {len(metadata_list)}")
        return 0
    except Exception as e:
        print(f"ERROR: Failed to write STATUS_BOARD: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
