"""IntakeBundle — output of the Intake worker."""
from __future__ import annotations

from typing import Any, Literal

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

    # TC-5321 (INT-H3): Enriched identity quality signals for downstream phases.
    # acquisition_confidence: overall identity resolution quality ("high"/"medium"/"low")
    # import_confidence: confidence that canonical_import matches repo truth ("high"/"medium"/"low"/"none")
    # canonical_import_candidates: top candidates extracted directly from repo source files
    # repo_signals: dict with readme_present, is_empty_clone, license_detected, etc.
    # field_provenance: per-field source (families_yaml, config_override, inferred_default)
    # is_fresh_clone: True if the repo was freshly cloned (not from cache)
    acquisition_confidence: str = ""
    import_confidence: str = ""
    canonical_import_candidates: list[str] = []
    repo_signals: dict[str, Any] = {}
    field_provenance: dict[str, str] = {}
    is_fresh_clone: bool = False
