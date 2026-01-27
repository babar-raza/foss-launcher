"""Git clone and SHA resolution helpers.

Provides deterministic git clone and SHA resolution operations for W1 RepoScout.

Spec references:
- specs/02_repo_ingestion.md (Clone and fingerprint)
- specs/10_determinism_and_caching.md (Deterministic operations)
- specs/21_worker_contracts.md (W1 binding requirements)

TC-401: W1.1 Clone inputs and resolve SHAs deterministically
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class ResolvedRepo:
    """Result of resolving a git ref to a specific SHA.

    Attributes:
        repo_url: The repository URL that was cloned
        requested_ref: The ref that was requested (e.g., 'main', 'v1.0.0')
        resolved_sha: The full 40-character commit SHA resolved from the ref
        default_branch: The repository's default branch name (e.g., 'main')
        clone_path: Absolute path where the repository was cloned
    """

    repo_url: str
    requested_ref: str
    resolved_sha: str
    default_branch: str
    clone_path: str


class GitCloneError(Exception):
    """Raised when git clone operations fail."""

    pass


class GitResolveError(Exception):
    """Raised when git SHA resolution fails."""

    pass


def clone_and_resolve(
    repo_url: str,
    ref: str,
    target_dir: Path,
    shallow: bool = False,
) -> ResolvedRepo:
    """Clone a repository and resolve ref to a specific SHA.

    This function performs a deterministic clone operation:
    1. Clone the repository (shallow or full based on shallow parameter)
    2. Checkout the requested ref
    3. Resolve the ref to a full 40-character SHA
    4. Query the repository's default branch

    Per specs/02_repo_ingestion.md:36-44, this operation MUST:
    - Record the resolved SHA for deterministic reproducibility
    - Handle network failures gracefully with clear error messages
    - Be idempotent (re-running produces same result)

    Args:
        repo_url: Git repository URL (https or git protocol)
        ref: Git ref to checkout (branch name, tag, or SHA)
        target_dir: Directory where repository should be cloned
        shallow: If True, perform shallow clone (depth=1)

    Returns:
        ResolvedRepo containing resolved SHA and metadata

    Raises:
        GitCloneError: If clone operation fails
        GitResolveError: If SHA resolution fails

    Spec references:
    - specs/02_repo_ingestion.md:36-44 (Clone and fingerprint)
    - specs/21_worker_contracts.md:66-72 (W1 binding requirements)
    """
    # Ensure target directory's parent exists
    target_dir.parent.mkdir(parents=True, exist_ok=True)

    # Clone repository
    try:
        clone_cmd = ["git", "clone"]
        if shallow:
            clone_cmd.extend(["--depth", "1"])
        clone_cmd.extend(["--branch", ref, repo_url, str(target_dir)])

        result = subprocess.run(
            clone_cmd,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            # Network errors typically contain these keywords
            stderr_lower = result.stderr.lower()
            is_network_error = any(
                keyword in stderr_lower
                for keyword in ["connection", "timeout", "network", "429", "503"]
            )

            error_msg = f"Git clone failed for {repo_url} ref={ref}: {result.stderr}"
            if is_network_error:
                raise GitCloneError(
                    f"{error_msg} (RETRYABLE: Network error detected)"
                )
            else:
                raise GitCloneError(error_msg)

    except FileNotFoundError:
        raise GitCloneError(
            "Git executable not found. Please ensure git is installed and in PATH."
        )

    # Resolve ref to full SHA
    try:
        sha_result = subprocess.run(
            ["git", "-C", str(target_dir), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        resolved_sha = sha_result.stdout.strip()

        # Validate SHA format (must be 40-char hexadecimal)
        if len(resolved_sha) != 40 or not all(c in "0123456789abcdef" for c in resolved_sha):
            raise GitResolveError(
                f"Invalid SHA format resolved: {resolved_sha} (expected 40-char hex)"
            )

    except subprocess.CalledProcessError as e:
        raise GitResolveError(f"Failed to resolve SHA for ref {ref}: {e.stderr}")

    # Get default branch name
    try:
        # Query remote HEAD to get default branch
        default_branch_result = subprocess.run(
            ["git", "-C", str(target_dir), "symbolic-ref", "refs/remotes/origin/HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        # Output format: refs/remotes/origin/main
        default_branch_full = default_branch_result.stdout.strip()
        default_branch = default_branch_full.split("/")[-1]

    except subprocess.CalledProcessError:
        # Fallback: try to get from config
        try:
            config_result = subprocess.run(
                ["git", "-C", str(target_dir), "config", "--get", "init.defaultBranch"],
                capture_output=True,
                text=True,
                check=False,
            )
            if config_result.returncode == 0:
                default_branch = config_result.stdout.strip()
            else:
                # Last resort: assume 'main' (modern default)
                default_branch = "main"
        except subprocess.CalledProcessError:
            default_branch = "main"

    return ResolvedRepo(
        repo_url=repo_url,
        requested_ref=ref,
        resolved_sha=resolved_sha,
        default_branch=default_branch,
        clone_path=str(target_dir.absolute()),
    )


def resolve_remote_ref(repo_url: str, ref: str) -> str:
    """Resolve a git ref to SHA without cloning (using ls-remote).

    This is useful for checking remote refs without a full clone.
    However, for TC-401, we use clone_and_resolve() which provides
    both clone and resolution in one deterministic operation.

    Args:
        repo_url: Git repository URL
        ref: Git ref to resolve (branch, tag, or HEAD)

    Returns:
        Full 40-character commit SHA

    Raises:
        GitResolveError: If resolution fails
    """
    try:
        result = subprocess.run(
            ["git", "ls-remote", repo_url, ref],
            capture_output=True,
            text=True,
            check=True,
        )

        # Output format: <sha>\t<ref>
        lines = result.stdout.strip().split("\n")
        if not lines or not lines[0]:
            raise GitResolveError(f"No ref found for {ref} in {repo_url}")

        sha = lines[0].split("\t")[0]
        if len(sha) != 40 or not all(c in "0123456789abcdef" for c in sha):
            raise GitResolveError(f"Invalid SHA format: {sha}")

        return sha

    except subprocess.CalledProcessError as e:
        stderr_lower = e.stderr.lower()
        is_network_error = any(
            keyword in stderr_lower
            for keyword in ["connection", "timeout", "network", "429", "503"]
        )

        error_msg = f"Failed to resolve ref {ref} for {repo_url}: {e.stderr}"
        if is_network_error:
            raise GitResolveError(f"{error_msg} (RETRYABLE: Network error detected)")
        else:
            raise GitResolveError(error_msg)
    except FileNotFoundError:
        raise GitResolveError(
            "Git executable not found. Please ensure git is installed and in PATH."
        )
