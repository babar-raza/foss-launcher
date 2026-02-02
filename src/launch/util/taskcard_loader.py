"""Taskcard loading and parsing utilities.

Loads taskcard YAML frontmatter from plans/taskcards/ directory.
Supports enforcement of write fence policy per taskcard allowed_paths.

Spec references:
- plans/taskcards/00_TASKCARD_CONTRACT.md (Taskcard structure)
- specs/34_strict_compliance_guarantees.md (Write fence policy)
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


class TaskcardError(Exception):
    """Base exception for taskcard errors."""

    pass


class TaskcardNotFoundError(TaskcardError):
    """Taskcard file not found."""

    def __init__(self, taskcard_id: str):
        super().__init__(f"Taskcard not found: {taskcard_id}")
        self.taskcard_id = taskcard_id


class TaskcardParseError(TaskcardError):
    """Taskcard YAML parsing failed."""

    def __init__(self, taskcard_id: str, error: str):
        super().__init__(f"Failed to parse taskcard {taskcard_id}: {error}")
        self.taskcard_id = taskcard_id
        self.error = error


def find_taskcard_file(taskcard_id: str, repo_root: Path) -> Optional[Path]:
    """Find taskcard file by ID.

    Taskcards are stored as: plans/taskcards/TC-{id}_{slug}.md

    Args:
        taskcard_id: Taskcard ID (e.g., "TC-100")
        repo_root: Repository root directory

    Returns:
        Path to taskcard file, or None if not found

    Examples:
        >>> find_taskcard_file("TC-100", Path("."))
        Path("plans/taskcards/TC-100_bootstrap_repo.md")
    """
    taskcards_dir = repo_root / "plans" / "taskcards"
    if not taskcards_dir.exists():
        return None

    # Pattern: TC-{id}_*.md
    pattern = f"{taskcard_id}_*.md"
    matches = list(taskcards_dir.glob(pattern))

    if not matches:
        return None

    # Return first match (should only be one)
    return matches[0]


def parse_frontmatter(content: str) -> tuple[Optional[Dict[str, Any]], str]:
    """Parse YAML frontmatter from markdown content.

    Args:
        content: Markdown file content

    Returns:
        Tuple of (frontmatter dict or None, body content)

    Examples:
        >>> content = "---\\nid: TC-100\\n---\\n# Body"
        >>> fm, body = parse_frontmatter(content)
        >>> fm['id']
        'TC-100'
    """
    # Match frontmatter: --- at start, YAML content, closing ---
    match = re.match(r"^---\s*\n(.*?\n)---\s*\n(.*)$", content, re.DOTALL)
    if not match:
        return None, content

    try:
        frontmatter = yaml.safe_load(match.group(1))
        body = match.group(2)
        return frontmatter, body
    except yaml.YAMLError as e:
        # Return None for invalid YAML (will be caught by caller)
        return None, content


def load_taskcard(taskcard_id: str, repo_root: Path) -> Dict[str, Any]:
    """Load and parse taskcard by ID.

    Args:
        taskcard_id: Taskcard ID (e.g., "TC-100")
        repo_root: Repository root directory

    Returns:
        Taskcard frontmatter dictionary

    Raises:
        TaskcardNotFoundError: If taskcard file doesn't exist
        TaskcardParseError: If YAML parsing fails

    Examples:
        >>> tc = load_taskcard("TC-100", Path("."))
        >>> tc['id']
        'TC-100'
        >>> tc['status']
        'Done'
        >>> tc['allowed_paths']
        ['pyproject.toml', 'src/launch/__init__.py', ...]
    """
    # Find taskcard file
    taskcard_file = find_taskcard_file(taskcard_id, repo_root)
    if taskcard_file is None:
        raise TaskcardNotFoundError(taskcard_id)

    # Read file content
    try:
        content = taskcard_file.read_text(encoding="utf-8")
    except Exception as e:
        raise TaskcardParseError(taskcard_id, f"Failed to read file: {e}")

    # Parse frontmatter
    frontmatter, body = parse_frontmatter(content)
    if frontmatter is None:
        raise TaskcardParseError(taskcard_id, "No valid YAML frontmatter found")

    # Validate required fields
    if "id" not in frontmatter:
        raise TaskcardParseError(taskcard_id, "Missing required field: id")

    # Normalize ID format (handle both "TC-100" and "TC-100" in frontmatter)
    frontmatter_id = str(frontmatter["id"])
    if not frontmatter_id.startswith("TC-"):
        frontmatter_id = f"TC-{frontmatter_id}"

    if frontmatter_id != taskcard_id:
        raise TaskcardParseError(
            taskcard_id,
            f"ID mismatch: requested {taskcard_id}, found {frontmatter_id}",
        )

    return frontmatter


def get_allowed_paths(taskcard: Dict[str, Any]) -> List[str]:
    """Extract allowed_paths from taskcard.

    Args:
        taskcard: Taskcard frontmatter dictionary

    Returns:
        List of allowed path patterns (may be empty)

    Examples:
        >>> tc = load_taskcard("TC-100", Path("."))
        >>> paths = get_allowed_paths(tc)
        >>> "pyproject.toml" in paths
        True
    """
    allowed_paths = taskcard.get("allowed_paths", [])

    # Validate all entries are strings
    if not isinstance(allowed_paths, list):
        return []

    return [str(path) for path in allowed_paths if isinstance(path, str)]


def get_taskcard_status(taskcard: Dict[str, Any]) -> Optional[str]:
    """Get taskcard status.

    Args:
        taskcard: Taskcard frontmatter dictionary

    Returns:
        Status string (e.g., "In-Progress", "Done", "Draft"), or None if missing

    Examples:
        >>> tc = load_taskcard("TC-100", Path("."))
        >>> get_taskcard_status(tc)
        'Done'
    """
    return taskcard.get("status")
