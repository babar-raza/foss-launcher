"""Atomic file operations with hermetic path validation (Guarantee B).

All write operations validate that paths are within allowed boundaries
to prevent path escape attacks.

Layer 3 Defense: Taskcard authorization enforcement at write time.
This is the STRONGEST enforcement layer in the 4-layer defense-in-depth system.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, List, Optional

from ..util.path_validation import (
    PathValidationError,
    is_source_code_path,
    validate_no_path_traversal,
    validate_path_matches_patterns,
)


def get_enforcement_mode() -> str:
    """Get taskcard enforcement mode from environment.

    Returns:
        "strict" (enforce taskcard policy) or "disabled" (local dev mode)

    Environment:
        LAUNCH_TASKCARD_ENFORCEMENT: Set to "disabled" for local development
    """
    mode = os.environ.get("LAUNCH_TASKCARD_ENFORCEMENT", "strict")
    if mode not in ["strict", "disabled"]:
        raise ValueError(
            f"Invalid LAUNCH_TASKCARD_ENFORCEMENT value: {mode}. "
            f"Must be 'strict' or 'disabled'."
        )
    return mode


def validate_taskcard_authorization(
    path: Path,
    taskcard_id: Optional[str],
    allowed_paths: Optional[List[str]],
    enforcement_mode: str,
    repo_root: Path,
) -> None:
    """Validate write authorization via taskcard (Layer 3 enforcement).

    This is the STRONGEST enforcement point in the defense-in-depth system.

    Args:
        path: File path to write
        taskcard_id: Taskcard ID authorizing write (e.g., "TC-100")
        allowed_paths: Explicit allowed paths (if None, loaded from taskcard)
        enforcement_mode: "strict" or "disabled"
        repo_root: Repository root for pattern matching

    Raises:
        PathValidationError: If write not authorized

    Error codes:
        - POLICY_TASKCARD_MISSING: Protected path write without taskcard
        - POLICY_TASKCARD_INACTIVE: Taskcard status is Draft/Blocked
        - POLICY_TASKCARD_PATH_VIOLATION: Path not in allowed_paths
    """
    # Skip enforcement in disabled mode
    if enforcement_mode == "disabled":
        return

    # Check if path is protected (requires taskcard)
    if is_source_code_path(path, repo_root):
        if taskcard_id is None:
            raise PathValidationError(
                f"Write to protected path '{path}' requires taskcard authorization. "
                f"Protected paths: src/launch/**, specs/**, plans/taskcards/**. "
                f"Set LAUNCH_TASKCARD_ENFORCEMENT=disabled for local development.",
                error_code="POLICY_TASKCARD_MISSING",
            )

        # Load and validate taskcard
        from ..util.taskcard_loader import get_allowed_paths, load_taskcard
        from ..util.taskcard_validation import validate_taskcard_active

        try:
            taskcard = load_taskcard(taskcard_id, repo_root)
        except Exception as e:
            raise PathValidationError(
                f"Failed to load taskcard {taskcard_id}: {e}",
                error_code="POLICY_TASKCARD_MISSING",
            ) from e

        # Validate taskcard is active
        try:
            validate_taskcard_active(taskcard)
        except Exception as e:
            raise PathValidationError(
                f"Taskcard {taskcard_id} is not active: {e}",
                error_code="POLICY_TASKCARD_INACTIVE",
            ) from e

        # Get allowed paths
        if allowed_paths is None:
            allowed_paths = get_allowed_paths(taskcard)

        # Validate path matches patterns
        if not validate_path_matches_patterns(path, allowed_paths, repo_root=repo_root):
            raise PathValidationError(
                f"Path '{path}' not authorized by taskcard {taskcard_id}. "
                f"Allowed paths: {allowed_paths}. "
                f"Add this path to the taskcard's allowed_paths or use a different taskcard.",
                error_code="POLICY_TASKCARD_PATH_VIOLATION",
            )


def atomic_write_text(
    path: Path,
    text: str,
    encoding: str = 'utf-8',
    *,
    validate_boundary: Optional[Path] = None,
    taskcard_id: Optional[str] = None,
    allowed_paths: Optional[List[str]] = None,
    enforcement_mode: Optional[str] = None,
    repo_root: Optional[Path] = None,
) -> None:
    """Write text to file atomically with path validation.

    Layer 3 Defense: Validates taskcard authorization for protected paths.

    Args:
        path: Destination file path
        text: Text content to write
        encoding: Text encoding (default: utf-8)
        validate_boundary: Optional boundary to enforce (e.g., RUN_DIR)
        taskcard_id: Taskcard ID authorizing write (e.g., "TC-100")
        allowed_paths: Explicit allowed paths (overrides taskcard)
        enforcement_mode: "strict" or "disabled" (defaults to env var)
        repo_root: Repository root (defaults to cwd)

    Raises:
        PathValidationError: If path validation or taskcard authorization fails
    """
    # Basic path traversal check
    validate_no_path_traversal(path)

    # Boundary validation if provided
    if validate_boundary:
        from ..util.path_validation import validate_path_in_boundary
        validate_path_in_boundary(path, validate_boundary)

    # Layer 3: Taskcard authorization enforcement
    if enforcement_mode is None:
        enforcement_mode = get_enforcement_mode()

    if repo_root is None:
        repo_root = Path.cwd()

    validate_taskcard_authorization(
        path, taskcard_id, allowed_paths, enforcement_mode, repo_root
    )

    # Perform atomic write
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(text, encoding=encoding)
    os.replace(tmp, path)


def atomic_write_json(
    path: Path,
    obj: Any,
    *,
    validate_boundary: Optional[Path] = None,
    taskcard_id: Optional[str] = None,
    allowed_paths: Optional[List[str]] = None,
    enforcement_mode: Optional[str] = None,
    repo_root: Optional[Path] = None,
) -> None:
    """Write JSON to file atomically with path validation.

    Layer 3 Defense: Validates taskcard authorization for protected paths.

    Args:
        path: Destination file path
        obj: Object to serialize as JSON
        validate_boundary: Optional boundary to enforce (e.g., RUN_DIR)
        taskcard_id: Taskcard ID authorizing write (e.g., "TC-100")
        allowed_paths: Explicit allowed paths (overrides taskcard)
        enforcement_mode: "strict" or "disabled" (defaults to env var)
        repo_root: Repository root (defaults to cwd)

    Raises:
        PathValidationError: If path validation or taskcard authorization fails
    """
    text = json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + '\n'
    atomic_write_text(
        path,
        text,
        encoding='utf-8',
        validate_boundary=validate_boundary,
        taskcard_id=taskcard_id,
        allowed_paths=allowed_paths,
        enforcement_mode=enforcement_mode,
        repo_root=repo_root,
    )
