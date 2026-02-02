"""Gate U: Taskcard Authorization (Layer 4 post-run audit).

Validates that all file modifications are authorized by taskcard's allowed_paths.
This is the final defense layer in the 4-layer defense-in-depth system.

Per specs/09_validation_gates.md (Gate U).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from src.launch.util import subprocess as secure_subprocess


def get_modified_files_git(site_dir: Path) -> List[Path]:
    """Get list of files modified in site worktree using git.

    Args:
        site_dir: Site worktree directory (RUN_DIR/work/site)

    Returns:
        List of modified file paths (relative to site_dir)
    """
    if not site_dir.exists():
        return []

    try:
        # Run: git status --porcelain to get modified files
        result = secure_subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=site_dir,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            # Not a git repository or error
            return []

        # Parse git status output
        modified_files = []
        for line in result.stdout.splitlines():
            if len(line) < 4:
                continue

            # Format: "XY filename" where X/Y are status codes
            status = line[:2]
            filepath = line[3:].strip()

            # Include modified (M), added (A), or deleted (D) files
            # Ignore untracked (??) to avoid false positives
            if status.strip() and status != "??":
                modified_files.append(site_dir / filepath)

        return sorted(modified_files)

    except Exception:
        # Git command failed, return empty list
        return []


def execute_gate(run_dir: Path, profile: str) -> Tuple[bool, List[Dict[str, Any]]]:
    """Execute Gate U: Taskcard Authorization.

    Validates that all modified files are authorized by taskcard's allowed_paths.
    This is Layer 4 (post-run audit) of the defense-in-depth system.

    Args:
        run_dir: Run directory path
        profile: Validation profile (local, ci, prod)

    Returns:
        Tuple of (gate_passed, issues)

    Gate behavior:
    - Production runs without taskcard_id: BLOCKER
    - Local/CI runs without taskcard_id: Skip validation (pass)
    - Runs with taskcard: Validate all modified files match allowed_paths
    - Modified files outside allowed_paths: BLOCKER
    """
    issues = []

    # Load run_config to get taskcard_id
    run_config_path = run_dir / "run_config.json"
    if not run_config_path.exists():
        # No run_config, cannot validate (Gate 1 will catch this)
        return True, []

    try:
        with run_config_path.open() as f:
            run_config = json.load(f)
    except Exception as e:
        issues.append(
            {
                "issue_id": "gate_u_run_config_invalid",
                "gate": "gate_u_taskcard_authorization",
                "severity": "error",
                "message": f"Failed to load run_config.json: {e}",
                "error_code": "GATE_U_RUN_CONFIG_INVALID",
                "status": "OPEN",
            }
        )
        return False, issues

    taskcard_id = run_config.get("taskcard_id")

    # Check if production run requires taskcard
    if profile == "prod" and not taskcard_id:
        issues.append(
            {
                "issue_id": "gate_u_taskcard_missing_prod",
                "gate": "gate_u_taskcard_authorization",
                "severity": "blocker",
                "message": "Production run missing taskcard_id. All production runs must have taskcard authorization per write fence policy.",
                "error_code": "GATE_U_TASKCARD_MISSING",
                "status": "OPEN",
            }
        )
        return False, issues

    # Skip validation if no taskcard in local/ci mode
    if not taskcard_id:
        return True, []

    # Load taskcard to get allowed_paths
    repo_root = run_dir.parent.parent
    try:
        from launch.util.taskcard_loader import get_allowed_paths, load_taskcard
        from launch.util.taskcard_validation import validate_taskcard_active

        taskcard = load_taskcard(taskcard_id, repo_root)

        # Validate taskcard is active
        try:
            validate_taskcard_active(taskcard)
        except Exception as e:
            issues.append(
                {
                    "issue_id": f"gate_u_taskcard_inactive_{taskcard_id}",
                    "gate": "gate_u_taskcard_authorization",
                    "severity": "blocker",
                    "message": f"Taskcard {taskcard_id} is not active: {e}",
                    "error_code": "GATE_U_TASKCARD_INACTIVE",
                    "status": "OPEN",
                }
            )
            return False, issues

        allowed_paths = get_allowed_paths(taskcard)

    except Exception as e:
        issues.append(
            {
                "issue_id": f"gate_u_taskcard_load_failed_{taskcard_id}",
                "gate": "gate_u_taskcard_authorization",
                "severity": "blocker",
                "message": f"Failed to load taskcard {taskcard_id}: {e}",
                "error_code": "GATE_U_TASKCARD_LOAD_FAILED",
                "status": "OPEN",
            }
        )
        return False, issues

    # Get modified files from git
    site_dir = run_dir / "work" / "site"
    modified_files = get_modified_files_git(site_dir)

    # Validate each modified file against allowed_paths
    from launch.util.path_validation import validate_path_matches_patterns

    for modified_file in modified_files:
        try:
            # Make path relative to repo_root for matching
            relative_path = modified_file.relative_to(repo_root)
        except ValueError:
            # File is not under repo_root, skip
            continue

        # Check if file matches allowed patterns
        if not validate_path_matches_patterns(
            relative_path, allowed_paths, repo_root=repo_root
        ):
            issues.append(
                {
                    "issue_id": f"gate_u_path_violation_{relative_path.as_posix().replace('/', '_')}",
                    "gate": "gate_u_taskcard_authorization",
                    "severity": "blocker",
                    "message": f"File '{relative_path}' modified without taskcard authorization. Taskcard {taskcard_id} allowed_paths: {allowed_paths}",
                    "error_code": "GATE_U_TASKCARD_PATH_VIOLATION",
                    "location": {"path": str(relative_path)},
                    "status": "OPEN",
                }
            )

    # Gate passes if no issues
    gate_passed = len(issues) == 0

    return gate_passed, issues
