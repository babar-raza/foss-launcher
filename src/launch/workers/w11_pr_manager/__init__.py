"""TC-480: W9 PRManager worker package.

This package implements the W9 PRManager worker for creating pull requests
via the GitHub commit service.

Entry point:
    execute_pr_manager(run_dir, run_config, commit_client) -> Dict[str, Any]

Exceptions:
    PRManagerError: Base exception for all PR manager errors
    PRManagerNoChangesError: No changes to commit
    PRManagerAuthFailedError: GitHub authentication failed
    PRManagerRateLimitedError: GitHub rate limit exceeded
    PRManagerBranchExistsError: Target branch already exists
    PRManagerTimeoutError: Commit service call timeout
    PRManagerMissingArtifactError: Required artifact not found

Spec references:
    - specs/12_pr_and_release.md (PR creation workflow)
    - specs/17_github_commit_service.md (Commit service integration)
    - specs/21_worker_contracts.md:322-344 (W9 PRManager contract)
"""

from .worker import (
    execute_pr_manager,
    PRManagerError,
    PRManagerNoChangesError,
    PRManagerAuthFailedError,
    PRManagerRateLimitedError,
    PRManagerBranchExistsError,
    PRManagerTimeoutError,
    PRManagerMissingArtifactError,
    generate_branch_name,
    generate_pr_title,
    generate_pr_body,
    extract_affected_paths,
    generate_rollback_steps,
)

__all__ = [
    "execute_pr_manager",
    "PRManagerError",
    "PRManagerNoChangesError",
    "PRManagerAuthFailedError",
    "PRManagerRateLimitedError",
    "PRManagerBranchExistsError",
    "PRManagerTimeoutError",
    "PRManagerMissingArtifactError",
    "generate_branch_name",
    "generate_pr_title",
    "generate_pr_body",
    "extract_affected_paths",
    "generate_rollback_steps",
]
