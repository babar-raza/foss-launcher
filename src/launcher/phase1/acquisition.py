"""Pre-pipeline acquisition CLI tools.

Runtime acquisition logic (clone, signals, artifact) now lives in
``launcher.workers.intake.acquisition``. This module re-exports those
symbols for backward compatibility and adds the pre-pipeline CLI
entry points: ``acquire_repository`` and ``load_allowed_org_prefixes``.

Pre-pipeline usage (discover, inspect, batch-onboard) imports from here.
Runtime pipeline usage imports from ``launcher.workers.intake.acquisition``
via the ``launcher.workers.intake.clone`` re-export interface.
"""
from __future__ import annotations

import functools
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Re-export runtime acquisition symbols for backward compatibility.
# Pre-pipeline scripts that currently import from this module continue to work.
from launcher.workers.intake.acquisition import (
    _CLONE_SHA_MARKER,
    _CLONE_TIMESTAMP_MARKER,
    _CLONE_URL_MARKER,
    _STALE_CACHE_DAYS,
    _check_url_collision,
    _extract_brand_from_org,
    _extract_brand_from_url,
    _get_cache_dir,
    _get_repo_sha,
    _log_cache_age,
    _normalize_slug,
    _write_cache_timestamp,
    build_acquisition_artifact,
    build_repo_signals,
    check_remote_sha,
    clone_repo_cached,
    compute_acquisition_confidence,
    resolve_tier,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AcquisitionResult:
    repo_dir: Path
    repo_sha: str
    is_fresh_clone: bool
    artifact: dict[str, Any]


@functools.lru_cache(maxsize=8)
def load_allowed_org_prefixes(config_path: Path) -> tuple[str, ...]:
    try:
        from launcher.phase1.config_loader import load_intake_config

        cfg = load_intake_config(config_path)
        return tuple(f"https://github.com/{org.name}/" for org in cfg.organizations)
    except Exception:
        logger.warning(
            "[Phase1] Could not load intake config for org allowlist - clone restriction disabled. Check %s exists.",
            config_path,
        )
        return ()


def acquire_repository(
    *,
    family: str,
    platform: str,
    repo_url: str,
    display_name: str,
    canonical_import: str,
    runtime_import: str,
    launch_tier: str,
    provenance: dict[str, str],
    work_dir: Path,
    allowed_org_prefixes: list[str] | None = None,
) -> AcquisitionResult:
    repo_dir, repo_sha, is_fresh_clone = clone_repo_cached(
        repo_url,
        family=family,
        platform=platform,
        work_dir=work_dir,
        allowed_org_prefixes=allowed_org_prefixes,
    )
    discovered_at = datetime.now(timezone.utc).isoformat()
    artifact = build_acquisition_artifact(
        family=family,
        platform=platform,
        repo_url=repo_url,
        display_name=display_name,
        canonical_import=canonical_import,
        runtime_import=runtime_import,
        launch_tier=launch_tier,
        repo_sha=repo_sha,
        repo_dir=repo_dir,
        discovered_at=discovered_at,
        is_fresh_clone=is_fresh_clone,
        provenance=provenance,
    )
    if artifact["failure_state"]:
        raise RuntimeError(
            f"[Phase1] Acquisition produced unusable clone state for {repo_url!r}: {artifact['failure_state']}"
        )
    return AcquisitionResult(
        repo_dir=repo_dir,
        repo_sha=repo_sha,
        is_fresh_clone=is_fresh_clone,
        artifact=artifact,
    )


__all__ = [
    # Pre-pipeline CLI entry points (owned here)
    "AcquisitionResult",
    "acquire_repository",
    "load_allowed_org_prefixes",
    # Re-exported from workers.intake.acquisition for backward compat
    "_CLONE_SHA_MARKER",
    "_CLONE_TIMESTAMP_MARKER",
    "_CLONE_URL_MARKER",
    "_check_url_collision",
    "_extract_brand_from_org",
    "_extract_brand_from_url",
    "_get_cache_dir",
    "_get_repo_sha",
    "_log_cache_age",
    "_normalize_slug",
    "_write_cache_timestamp",
    "build_acquisition_artifact",
    "build_repo_signals",
    "check_remote_sha",
    "clone_repo_cached",
    "compute_acquisition_confidence",
    "resolve_tier",
]
