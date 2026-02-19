"""W6 LinkerAndPatcher worker module.

This module implements TC-450: Draft assembly and patch application.

Main entry point:
- execute_linker_and_patcher: Convert drafts to patches and apply to site worktree

Exception hierarchy:
- LinkerAndPatcherError: Base exception
- LinkerNoDraftsError: No drafts found
- LinkerPatchConflictError: Patch application conflict
- LinkerAllowedPathsViolationError: Path outside allowed_paths
- LinkerFrontmatterViolationError: Frontmatter schema violation
- LinkerWriteFailedError: File system write failure

Spec references:
- specs/08_patch_engine.md
- specs/22_navigation_and_existing_content_update.md
- specs/21_worker_contracts.md:228-251
"""

from .worker import (
    execute_linker_and_patcher,
    LinkerAndPatcherError,
    LinkerNoDraftsError,
    LinkerPatchConflictError,
    LinkerAllowedPathsViolationError,
    LinkerFrontmatterViolationError,
    LinkerWriteFailedError,
)

__all__ = [
    "execute_linker_and_patcher",
    "LinkerAndPatcherError",
    "LinkerNoDraftsError",
    "LinkerPatchConflictError",
    "LinkerAllowedPathsViolationError",
    "LinkerFrontmatterViolationError",
    "LinkerWriteFailedError",
]
