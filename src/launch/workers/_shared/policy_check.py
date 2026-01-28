"""Shared policy check utilities for worker implementations.

This module provides reusable policy validation functions that can be used by
validation gates and workers to detect and report manual content edits.

Spec references:
- plans/policies/no_manual_content_edits.md
- specs/09_validation_gates.md
- specs/schemas/validation_report.schema.json
- specs/schemas/issue.schema.json
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Dict, List, Set

from launch.util.subprocess import run as subprocess_run


def enumerate_changed_content_files(
    work_dir: Path,
    base_ref: str = "HEAD",
    content_patterns: List[str] | None = None
) -> List[str]:
    """Enumerate all changed content files in the work directory.

    Uses git diff to deterministically list all modified content files relative
    to a base reference. Files are sorted for determinism per specs/10_determinism_and_caching.md.

    Args:
        work_dir: Path to the work/site directory (git repository)
        base_ref: Base git reference to diff against (default: HEAD)
        content_patterns: Optional list of glob patterns for content files
                         (default: ["*.md", "*.html"])

    Returns:
        Sorted list of relative file paths that were modified

    Note:
        This function implements the policy gate requirement to "enumerate all
        changed content files deterministically" per plans/policies/no_manual_content_edits.md
    """
    if content_patterns is None:
        content_patterns = ["*.md", "*.html"]

    try:
        # Get list of changed files
        result = subprocess_run(
            ["git", "diff", "--name-only", base_ref],
            cwd=str(work_dir),
            capture_output=True,
            text=True,
            check=True
        )

        changed_files = result.stdout.strip().split("\n") if result.stdout.strip() else []

        # Filter for content files only
        content_files = []
        for file_path in changed_files:
            path = Path(file_path)
            # Check if file matches any content pattern
            for pattern in content_patterns:
                if path.match(pattern):
                    content_files.append(file_path)
                    break

        # Sort for determinism
        return sorted(content_files)

    except subprocess.CalledProcessError as e:
        # If git diff fails, return empty list (may happen in fresh repo)
        return []


def check_file_in_patch_index(
    file_path: str,
    patch_index: Dict[str, Any]
) -> bool:
    """Check if a file is explained by the patch/evidence index.

    Args:
        file_path: Relative file path to check
        patch_index: Patch index dictionary mapping files to patch records

    Returns:
        True if file is explained in the patch index, False otherwise
    """
    # Normalize path separators for consistent lookup
    normalized_path = str(Path(file_path).as_posix())

    # Check if file exists in patch index
    return normalized_path in patch_index.get("files", {})


def find_unexplained_diffs(
    changed_files: List[str],
    patch_index: Dict[str, Any]
) -> List[str]:
    """Find content files that changed but are not explained by patch index.

    Args:
        changed_files: List of changed content file paths
        patch_index: Patch index dictionary mapping files to patch records

    Returns:
        Sorted list of unexplained file paths
    """
    unexplained = []

    for file_path in changed_files:
        if not check_file_in_patch_index(file_path, patch_index):
            unexplained.append(file_path)

    return sorted(unexplained)


def create_policy_violation_issue(
    unexplained_files: List[str],
    allow_manual_edits: bool
) -> Dict[str, Any]:
    """Create a policy violation Issue for unexplained content changes.

    Args:
        unexplained_files: List of files that changed without patch records
        allow_manual_edits: Whether emergency mode is enabled

    Returns:
        Issue dictionary conforming to specs/schemas/issue.schema.json

    Note:
        When allow_manual_edits=false, this creates a BLOCKER issue.
        When allow_manual_edits=true, this is handled differently (recorded in
        validation_report.manual_edited_files instead of failing).
    """
    if allow_manual_edits:
        # In emergency mode, this shouldn't be called - just record files
        # But if it is, make it a warning
        severity = "warn"
        error_code = "MANUAL_EDITS_DETECTED"
        message = (
            f"Emergency mode active: {len(unexplained_files)} files were manually edited "
            f"without patch records. These will be recorded in validation_report."
        )
    else:
        # Default mode: manual edits are forbidden
        severity = "blocker"
        error_code = "POLICY_MANUAL_EDITS_FORBIDDEN"
        message = (
            f"Policy violation: {len(unexplained_files)} content files were modified without "
            f"patch records. Manual content edits are forbidden. Set run_config.allow_manual_edits=true "
            f"only in emergencies and document all changes in the master review."
        )

    return {
        "issue_id": "POLICY_GATE_001",
        "gate": "policy",
        "severity": severity,
        "error_code": error_code,
        "message": message,
        "files": unexplained_files,
        "suggested_fix": (
            "Either: (1) Revert manual edits and regenerate content through pipeline, or "
            "(2) Enable emergency mode (allow_manual_edits=true) and document rationale."
        ),
        "status": "OPEN"
    }


def validate_manual_edits_policy(
    work_dir: Path,
    run_config: Dict[str, Any],
    patch_index: Dict[str, Any],
    base_ref: str = "HEAD"
) -> tuple[bool, List[str], List[Dict[str, Any]]]:
    """Validate the no-manual-content-edits policy.

    This is the main entry point for policy gate validation. It:
    1. Enumerates changed content files deterministically
    2. Checks each file against the patch/evidence index
    3. If unexplained files exist and allow_manual_edits=false: creates BLOCKER issue
    4. If unexplained files exist and allow_manual_edits=true: returns files for recording

    Args:
        work_dir: Path to work/site directory
        run_config: Loaded and validated run_config
        patch_index: Patch index mapping files to patch records
        base_ref: Base git reference to diff against

    Returns:
        Tuple of (ok, manual_files, issues):
        - ok: True if policy check passes (no blockers)
        - manual_files: List of manually edited files (empty unless emergency mode)
        - issues: List of Issue dictionaries
    """
    # Enumerate changed content files
    changed_files = enumerate_changed_content_files(work_dir, base_ref)

    # Find unexplained diffs
    unexplained = find_unexplained_diffs(changed_files, patch_index)

    # If no unexplained diffs, policy check passes
    if not unexplained:
        return True, [], []

    # Check emergency mode
    allow_manual_edits = run_config.get("allow_manual_edits", False)

    if allow_manual_edits:
        # Emergency mode: record files but don't block
        return True, unexplained, []
    else:
        # Default mode: create blocker issue
        issue = create_policy_violation_issue(unexplained, allow_manual_edits)
        return False, [], [issue]


def update_validation_report_for_manual_edits(
    validation_report: Dict[str, Any],
    manual_files: List[str]
) -> Dict[str, Any]:
    """Update validation report to record manual edits.

    When emergency mode is active and manual edits occurred, the validation report
    must be updated per specs/schemas/validation_report.schema.json lines 53-64.

    Args:
        validation_report: Existing validation report dictionary
        manual_files: List of manually edited file paths

    Returns:
        Updated validation report with manual_edits and manual_edited_files fields
    """
    if manual_files:
        validation_report["manual_edits"] = True
        validation_report["manual_edited_files"] = sorted(manual_files)
    else:
        validation_report["manual_edits"] = False
        validation_report["manual_edited_files"] = []

    return validation_report
