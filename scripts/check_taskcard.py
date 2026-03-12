"""AG-002 Enforcement Hook — Taskcard-First Workflow Gate.

Called by Claude Code as a PreToolUse hook for Edit/Write tools.
Receives tool input as JSON on stdin.
Exits 0 to allow, exits 1 to block (stderr shown to agent).
"""

import json
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TASKCARD_DIR = REPO_ROOT / "plans" / "taskcards"

PROTECTED_PREFIXES = [
    "src/launcher/",
    "configs/",
    "specs/schemas/",
]


def get_file_path(data: dict) -> str:
    """Extract file_path from hook input JSON."""
    if "tool_input" in data:
        return data["tool_input"].get("file_path", "")
    return data.get("file_path", "")


def normalize_to_relative(file_path: str) -> str:
    """Convert an absolute path to a repo-relative forward-slash path."""
    # Normalize separators
    p = file_path.replace("\\", "/")

    # Try to strip repo root prefix
    repo_str = str(REPO_ROOT).replace("\\", "/")
    if p.startswith(repo_str):
        p = p[len(repo_str):]

    # Also try case-insensitive match (Windows)
    elif p.lower().startswith(repo_str.lower()):
        p = p[len(repo_str):]

    # Strip leading slash
    return p.lstrip("/")


def is_protected(rel_path: str) -> bool:
    """Check if a relative path falls under a protected prefix."""
    for prefix in PROTECTED_PREFIXES:
        if rel_path.startswith(prefix):
            return True
    return False


def find_active_taskcard() -> str | None:
    """Find a taskcard with status: In-Progress."""
    if not TASKCARD_DIR.is_dir():
        return None

    pattern = re.compile(r"^status:\s*[\"']?In-Progress[\"']?", re.MULTILINE)

    for tc_file in TASKCARD_DIR.glob("TC-*.md"):
        if tc_file.name == "TC-000_TEMPLATE.md":
            continue
        try:
            content = tc_file.read_text(encoding="utf-8", errors="replace")
            if pattern.search(content):
                return tc_file.name
        except OSError:
            continue

    return None


def main() -> int:
    try:
        raw = sys.stdin.read()
        data = json.loads(raw)
    except (json.JSONDecodeError, Exception):
        # Can't parse input — allow (don't block on hook errors)
        return 0

    file_path = get_file_path(data)
    if not file_path:
        return 0

    rel_path = normalize_to_relative(file_path)

    if not is_protected(rel_path):
        return 0

    # Protected path — must have an active taskcard
    active_tc = find_active_taskcard()

    if active_tc is None:
        sys.stderr.write(
            "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n"
            "!! AG-002 VIOLATION — WRITE BLOCKED                        !!\n"
            "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n"
            "\n"
            f"You are attempting to write to a PROTECTED path:\n"
            f"  {rel_path}\n"
            "\n"
            f"No taskcard with status 'In-Progress' found in:\n"
            f"  plans/taskcards/\n"
            "\n"
            "REQUIRED STEPS:\n"
            "  1. STOP — do not write code\n"
            "  2. Create a taskcard from plans/taskcards/TC-000_TEMPLATE.md\n"
            "  3. Fill ALL 14 mandatory sections\n"
            "  4. Present the taskcard to the user and get approval\n"
            "  5. Set status to In-Progress\n"
            "  6. THEN retry this write\n"
            "\n"
            "This is a BLOCKING rule. There are NO exceptions.\n"
        )
        return 1

    sys.stderr.write(f"AG-002 OK: Active taskcard {active_tc} — write to {rel_path} allowed.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
