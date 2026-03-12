from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from launcher.models.base import LauncherBaseModel


class PatchAction(str, Enum):
    """Action to take on a file in the target repository."""

    create = "create"
    update = "update"
    delete = "delete"


class Patch(LauncherBaseModel):
    """A single file-level change to the target repository."""

    file_path: str
    action: PatchAction
    content_hash: str = ""


class PullRequest(LauncherBaseModel):
    """Metadata for the pull request opened by Publish."""

    url: str = ""
    number: int = 0
    title: str = ""
    state: str = "draft"


class PublishBundle(LauncherBaseModel):
    """Complete output of the Publish worker."""

    patches: list[Patch] = Field(default_factory=list)
    pr: PullRequest = Field(default_factory=PullRequest)
    published_at: str = ""
    deployed_count: int = 0
    """Number of pages promoted to the deploy_dir staging directory."""
    merge_request_url: str = ""
    """Pull request URL in the content repo (empty if not created)."""
    merge_request_branch: str = ""
    """Git branch used for the merge request (empty if not created)."""
