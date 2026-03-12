"""Git publish helper — copy promoted pages to content repo and open a PR.

Used by PublishWorker when output.content_repo_dir is configured. All git and
gh operations run via launcher.util.subprocess (secure wrapper that blocks
execution from untrusted ingested-repo directories).
"""
from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path

from launcher.util import subprocess as safe_sub

logger = logging.getLogger(__name__)


def resolve_content_repo_dir(raw: str) -> Path:
    """Expand env-vars and user home then return an absolute resolved Path.

    Supports both Unix ($VAR) and Windows (%VAR%) env-var syntax via
    os.path.expandvars.  Relative paths are resolved against the process CWD.

    Args:
        raw: String from OutputConfig.content_repo_dir, e.g. "${ASPOSE_CONTENT_REPO}".

    Returns:
        Absolute Path to the local content repo clone.
    """
    expanded = os.path.expandvars(os.path.expanduser(raw))
    return Path(expanded).resolve()


def copy_to_content_repo(
    deploy_dir: Path,
    content_repo_dir: Path,
    promoted_content_paths: list[str],
) -> list[Path]:
    """Copy promoted .md files from the deploy/ staging dir into the content repo.

    Only copies files listed in promoted_content_paths (content_path strings
    without the .md suffix).  Creates parent directories as needed.

    Args:
        deploy_dir: Root of the local deploy/ staging directory.
        content_repo_dir: Root of the cloned content repo.
        promoted_content_paths: content_path values for pages promoted this run
            (e.g. ``"docs.aspose.org/3d/python/developer-guide/features"``).

    Returns:
        List of absolute destination paths that were written.
    """
    written: list[Path] = []
    for content_path in promoted_content_paths:
        src = deploy_dir / (content_path + ".md")
        if not src.exists():
            logger.warning("[GitPublisher] Source file not found: %s", src)
            continue
        dest = content_repo_dir / (content_path + ".md")
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        written.append(dest)
        logger.debug("[GitPublisher] Copied %s → %s", src.name, dest.relative_to(content_repo_dir))
    return written


def git_create_branch(repo_dir: Path, branch_name: str) -> None:
    """Create and checkout a new git branch in the given repo.

    Args:
        repo_dir: Absolute path to the local git repository root.
        branch_name: Name for the new branch (e.g. ``"launch/3d-python/abc123456789"``).

    Raises:
        subprocess.CalledProcessError: If git exits non-zero (e.g. branch already exists).
    """
    safe_sub.run(
        ["git", "checkout", "-b", branch_name],
        cwd=repo_dir,
        check=True,
        capture_output=True,
    )
    logger.debug("[GitPublisher] Created branch: %s", branch_name)


def git_add_and_commit(repo_dir: Path, files: list[Path], message: str) -> None:
    """Stage the given files and create a commit in the local repo.

    Args:
        repo_dir: Absolute path to the local git repository root.
        files: Absolute paths of files to stage; relative to repo_dir for the git command.
        message: Commit message string.

    Raises:
        subprocess.CalledProcessError: If git exits non-zero.
    """
    rel_files = [str(f.relative_to(repo_dir)) for f in files]
    safe_sub.run(
        ["git", "add", "--"] + rel_files,
        cwd=repo_dir,
        check=True,
        capture_output=True,
    )
    safe_sub.run(
        ["git", "commit", "-m", message],
        cwd=repo_dir,
        check=True,
        capture_output=True,
    )
    logger.debug("[GitPublisher] Committed %d file(s): %s", len(files), message[:60])


def git_push(repo_dir: Path, branch_name: str) -> None:
    """Push the branch to the remote named 'origin'.

    Args:
        repo_dir: Absolute path to the local git repository root.
        branch_name: Name of the branch to push.

    Raises:
        subprocess.CalledProcessError: If git exits non-zero.
    """
    safe_sub.run(
        ["git", "push", "origin", branch_name],
        cwd=repo_dir,
        check=True,
        capture_output=True,
    )
    logger.debug("[GitPublisher] Pushed branch: %s", branch_name)


def gh_create_pr(
    repo_dir: Path,
    title: str,
    body: str,
    base: str = "main",
) -> str:
    """Create a GitHub pull request using the gh CLI tool.

    The gh CLI must be installed and authenticated (``gh auth login``).

    Args:
        repo_dir: Absolute path to the local git repository root.
        title: PR title string.
        body: PR body markdown.
        base: Target branch for the PR (default: ``"main"``).

    Returns:
        URL of the created pull request (e.g. ``"https://github.com/org/repo/pull/42"``).

    Raises:
        subprocess.CalledProcessError: If gh exits non-zero (not installed, auth error, etc.).
    """
    result = safe_sub.run(
        ["gh", "pr", "create", "--title", title, "--body", body, "--base", base],
        cwd=repo_dir,
        check=True,
        capture_output=True,
        text=True,
    )
    url = result.stdout.strip()
    logger.debug("[GitPublisher] PR created: %s", url)
    return url
