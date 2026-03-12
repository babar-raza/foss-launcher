"""IntakeBundle — output of the Intake worker."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from .base import LauncherBaseModel


class IntakeBundle(LauncherBaseModel):
    """Validated and enriched product identity produced by Intake."""

    family: str
    platform: str
    repo_url: str
    display_name: str
    canonical_import: str
    runtime_import: str = ""
    launch_tier: Literal["full", "core", "minimal"]
    repo_sha: str = ""
    repo_dir: str = ""
    discovered_at: str = ""
