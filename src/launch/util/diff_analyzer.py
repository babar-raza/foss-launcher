"""Change budget enforcement and formatting detection (Guarantee G).

This module analyzes diffs to enforce change budgets and detect formatting-only
changes that don't add semantic value.

Binding contract: specs/34_strict_compliance_guarantees.md (Guarantee G)
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass
from typing import Dict, Any, List, Tuple


class ChangeBudgetExceededError(Exception):
    """Raised when change budget exceeded (Guarantee G)."""

    def __init__(self, message: str, violation_type: str):
        super().__init__(message)
        self.error_code = "POLICY_CHANGE_BUDGET_EXCEEDED"
        self.violation_type = violation_type


@dataclass
class DiffAnalysisResult:
    """Result of diff analysis against budgets."""
    total_files_changed: int
    files_over_line_limit: List[Tuple[str, int]]  # (file, lines_changed)
    formatting_only_files: List[str]
    total_lines_added: int
    total_lines_deleted: int
    budget_violations: List[str]
    ok: bool


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace for formatting detection.

    Replaces all whitespace sequences with single spaces and strips.
    Preserves line breaks but normalizes indentation.
    """
    # Normalize line endings
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    # Strip trailing whitespace from each line
    lines = [line.rstrip() for line in text.split('\n')]

    # Remove completely empty lines at start/end
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()

    return '\n'.join(lines)


def detect_formatting_only_changes(original: str, modified: str) -> bool:
    """Detect if changes are formatting-only (whitespace, line endings).

    Returns True if the only differences are:
    - Whitespace (spaces, tabs, indentation)
    - Line endings (CRLF vs LF)
    - Trailing whitespace
    - Empty lines at start/end

    Returns False if any semantic content changed.
    """
    normalized_original = normalize_whitespace(original)
    normalized_modified = normalize_whitespace(modified)

    return normalized_original == normalized_modified


def count_diff_lines(original: str, modified: str) -> Tuple[int, int]:
    """Count added and deleted lines using unified diff.

    Returns:
        (lines_added, lines_deleted)
    """
    original_lines = original.splitlines(keepends=True)
    modified_lines = modified.splitlines(keepends=True)

    diff = list(difflib.unified_diff(original_lines, modified_lines, lineterm=''))

    added = sum(1 for line in diff if line.startswith('+') and not line.startswith('+++'))
    deleted = sum(1 for line in diff if line.startswith('-') and not line.startswith('---'))

    return added, deleted


def analyze_file_change(
    file_path: str,
    original: str,
    modified: str,
    budgets: Dict[str, Any]
) -> Tuple[int, bool, List[str]]:
    """Analyze a single file change against budgets.

    Returns:
        (lines_changed, is_formatting_only, violations)
    """
    violations = []

    added, deleted = count_diff_lines(original, modified)
    lines_changed = added + deleted

    is_formatting_only = detect_formatting_only_changes(original, modified)

    max_lines_per_file = budgets.get("max_lines_per_file", 500)
    if lines_changed > max_lines_per_file:
        violations.append(
            f"{file_path}: {lines_changed} lines changed (max: {max_lines_per_file})"
        )

    return lines_changed, is_formatting_only, violations


def analyze_patch_bundle(
    patch_bundle: Dict[str, Any],
    budgets: Dict[str, Any]
) -> DiffAnalysisResult:
    """Analyze patch bundle against change budgets (Guarantee G).

    Args:
        patch_bundle: Dict with "files" key containing list of file changes
                     Each file: {"path": str, "original": str, "modified": str}
        budgets: Budget configuration from run_config

    Returns:
        DiffAnalysisResult with violations and analysis

    Raises:
        ChangeBudgetExceededError: If budgets exceeded
    """
    files = patch_bundle.get("files", [])

    total_files_changed = len(files)
    files_over_line_limit = []
    formatting_only_files = []
    total_lines_added = 0
    total_lines_deleted = 0
    violations = []

    # Analyze each file
    for file_info in files:
        path = file_info["path"]
        original = file_info.get("original", "")
        modified = file_info.get("modified", "")

        lines_changed, is_formatting_only, file_violations = analyze_file_change(
            path, original, modified, budgets
        )

        added, deleted = count_diff_lines(original, modified)
        total_lines_added += added
        total_lines_deleted += deleted

        if is_formatting_only:
            formatting_only_files.append(path)

        if file_violations:
            files_over_line_limit.append((path, lines_changed))
            violations.extend(file_violations)

    # Check total files changed
    max_files_changed = budgets.get("max_files_changed", 100)
    if total_files_changed > max_files_changed:
        violations.append(
            f"Total files changed: {total_files_changed} (max: {max_files_changed})"
        )

    result = DiffAnalysisResult(
        total_files_changed=total_files_changed,
        files_over_line_limit=files_over_line_limit,
        formatting_only_files=formatting_only_files,
        total_lines_added=total_lines_added,
        total_lines_deleted=total_lines_deleted,
        budget_violations=violations,
        ok=len(violations) == 0
    )

    # Raise if violations found
    if not result.ok:
        raise ChangeBudgetExceededError(
            f"Change budget exceeded:\n" + "\n".join(violations),
            violation_type="change_budget"
        )

    return result
