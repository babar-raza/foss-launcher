"""Source-grounded Phase 1 repo inspection."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from launcher.phase1.acquisition import acquire_repository
from launcher.phase1.config_generator import _extract_family, _extract_platform
from launcher.shared.identity import resolve_identity
from launcher.workers.scout.scout import build_scout_inventory, run_scout


def inspect_repo(
    repo: dict[str, Any],
    *,
    work_dir: Path,
    family: str | None = None,
    platform: str | None = None,
    launch_tier: str = "core",
    allowed_org_prefixes: list[str] | None = None,
) -> dict[str, Any]:
    resolved_family = family or _extract_family(repo)
    resolved_platform = platform or _extract_platform(repo, default_platform="python")
    identity = resolve_identity(resolved_family, resolved_platform)
    acquisition = acquire_repository(
        family=resolved_family,
        platform=resolved_platform,
        repo_url=repo.get("html_url", ""),
        display_name=identity.display_name,
        canonical_import=identity.canonical_import,
        runtime_import=identity.runtime_import,
        launch_tier=launch_tier,
        provenance=dict(identity.provenance),
        work_dir=work_dir,
        allowed_org_prefixes=allowed_org_prefixes,
    )
    repo_info, repo_content, budget_log, budget_log_overflow = asyncio.run(run_scout(acquisition.repo_dir))
    return {
        "phase": "phase1_inspection",
        "repo": repo,
        "family": resolved_family,
        "platform": resolved_platform,
        "display_name": identity.display_name,
        "canonical_import": identity.canonical_import,
        "runtime_import": identity.runtime_import,
        "acquisition": acquisition.artifact,
        "shared_facts": repo_info.shared_facts.model_dump(),
        "scout": build_scout_inventory(repo_info, repo_content, budget_log, budget_log_overflow),
    }


def inspect_repo_by_url(
    repo_url: str,
    *,
    repo: dict[str, Any],
    work_dir: Path,
    family: str | None = None,
    platform: str | None = None,
    launch_tier: str = "core",
    allowed_org_prefixes: list[str] | None = None,
) -> dict[str, Any]:
    repo_data = dict(repo)
    repo_data.setdefault("html_url", repo_url)
    return inspect_repo(
        repo_data,
        work_dir=work_dir,
        family=family,
        platform=platform,
        launch_tier=launch_tier,
        allowed_org_prefixes=allowed_org_prefixes,
    )


def write_inspection_artifact(
    artifact_path: Path,
    *,
    inspection: dict[str, Any],
    classification: dict[str, Any] | None = None,
) -> None:
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(inspection)
    if classification is not None:
        payload["classification"] = classification
    artifact_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


__all__ = ["inspect_repo", "inspect_repo_by_url", "write_inspection_artifact"]
