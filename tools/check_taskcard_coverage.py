#!/usr/bin/env python3
"""Check that all staged source files are covered by an active taskcard.

Exit 0 if all files covered, exit 1 if any file lacks taskcard coverage.
Intended for use in pre-commit hook.
"""
import sys
import subprocess
from fnmatch import fnmatch
from pathlib import Path

import yaml

TASKCARDS_DIR = Path("plans/taskcards")
SOURCE_PREFIX = "src/launch/"


def get_staged_source_files():
    """Get staged .py files under src/launch/."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
        capture_output=True,
        text=True,
    )
    return [
        f.replace("\\", "/")
        for f in result.stdout.strip().split("\n")
        if f.startswith(SOURCE_PREFIX) and f.endswith(".py")
    ]


def get_active_taskcard_paths():
    """Get allowed_paths from all In-Progress taskcards."""
    covered = []
    for tc_file in TASKCARDS_DIR.glob("TC-*.md"):
        try:
            content = tc_file.read_text(encoding="utf-8")
            if not content.startswith("---"):
                continue
            end = content.index("---", 3)
            fm = yaml.safe_load(content[3:end])
            if fm.get("status") == "In-Progress":
                paths = fm.get("allowed_paths", [])
                # Normalize to forward slashes
                covered.extend(p.replace("\\", "/") for p in paths)
        except Exception as exc:
            print(f"  warning: skipping {tc_file.name} ({exc})", file=sys.stderr)
            continue
    return covered


def file_matches_any_path(filepath, allowed_paths):
    """Check if filepath matches any allowed_path glob pattern."""
    return any(fnmatch(filepath, pat) for pat in allowed_paths)


def main():
    staged = get_staged_source_files()
    if not staged:
        return 0  # No source files staged

    allowed = get_active_taskcard_paths()
    uncovered = [f for f in staged if not file_matches_any_path(f, allowed)]

    if uncovered:
        print("ERROR: The following files have no In-Progress taskcard coverage:")
        for f in uncovered:
            print(f"  - {f}")
        print()
        if not allowed:
            print("No In-Progress taskcards found in plans/taskcards/.")
            print()
        print("Create a taskcard first: python scripts/create_taskcard.py")
        print(
            "Then set its status to 'In-Progress' and add these paths to allowed_paths."
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
