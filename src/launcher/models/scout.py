"""ScoutBundle — output of the Scout worker.

Contains identity fields passed through from IntakeBundle plus the full
RepoInfo produced by the Scout phase (file inventory, shared facts, budget log).

The raw file content (repo_content dict) is NOT serialized here — it flows
through the pipeline state (context.repo_content) for efficiency.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from .base import LauncherBaseModel
from .understanding import RepoInfo


class ScoutBundle(LauncherBaseModel):
    """Output of the Scout worker — repository inventory and shared facts.

    Contains all identity fields from IntakeBundle (pass-through) plus
    the full RepoInfo produced by Scout phase A.  The raw file content
    (repo_content dict) is NOT serialized here — it flows through the
    pipeline state (context.repo_content) for efficiency.
    """

    # Identity pass-through from IntakeBundle
    family: str
    platform: str
    repo_url: str
    display_name: str
    canonical_import: str
    runtime_import: str = ""
    launch_tier: Literal["full", "core", "minimal"]
    repo_sha: str = ""
    repo_dir: str  # Understand still needs this for API surface extraction
    discovered_at: str = ""

    # Scout-produced inventory (full RepoInfo)
    repo_info: RepoInfo = Field(default_factory=RepoInfo)

    # Budget log (from Scout — not serialized inside RepoInfo)
    budget_log: list[dict[str, Any]] = Field(default_factory=list)
    budget_log_overflow_count: int = 0
