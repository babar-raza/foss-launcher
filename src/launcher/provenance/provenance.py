"""Deterministic provenance tracking for artifact reuse.

Provides hashing helpers and provenance compatibility checking to ensure
artifact reuse is safe, auditable, and deterministic.

Uses only stdlib: hashlib, json, pathlib. No external dependencies.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Interpretation signature
# ---------------------------------------------------------------------------

#: Bump this when interpretation logic changes in a way that produces
#: different outputs for the same input (same repo_sha).
#: Determines the ``sig`` component of the derived cache key.
ENGINE_VERSION = "2.3.0"


def compute_interpretation_signature(run_config: Dict[str, Any]) -> str:
    """Compute a 12-character hex interpretation signature for cache keying.

    The signature changes when any of the following change:
    - ``ENGINE_VERSION`` (bump when pipeline logic changes)
    - ``ruleset_version`` (affects content rules)
    - ``templates_version`` (affects IA structure)

    Returns a 12-character lowercase hex string (prefix of SHA-256).
    Deterministic: same inputs always produce the same output.
    """
    payload = json.dumps(
        {
            "engine_version": ENGINE_VERSION,
            "ruleset_version": run_config.get("ruleset_version", ""),
            "templates_version": run_config.get("templates_version", ""),
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:12]


def compute_file_sha256(path: Path) -> str:
    """Compute SHA-256 hash of a file's contents.

    Reads in binary mode for determinism across platforms.
    Returns lowercase hex digest.
    """
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def compute_tree_hash(paths: List[Path]) -> Dict[str, str]:
    """Compute SHA-256 hashes for multiple files.

    Returns a dict mapping relative path strings to hex digests.
    Paths are sorted for deterministic ordering regardless of filesystem
    enumeration order.
    """
    result: Dict[str, str] = {}
    for p in sorted(paths, key=lambda x: str(x)):
        if p.is_file():
            result[str(p)] = compute_file_sha256(p)
    return result


def build_provenance(
    run_config: Dict[str, Any],
    repo_sha: str,
    *,
    site_sha: str = "",
    workflows_sha: str = "",
    launcher_version: str = "",
    upstream_artifact_hashes: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Build a provenance record from run configuration and repo state.

    The provenance record captures all version-relevant inputs that
    determine whether a cached artifact set can be safely reused.
    """
    return {
        "schema_version": "1.0",
        "repo_url": run_config.get("github_repo_url", ""),
        "repo_sha": repo_sha,
        "site_repo_url": run_config.get("site_repo_url", ""),
        "site_sha": site_sha,
        "workflows_repo_url": run_config.get("workflows_repo_url", ""),
        "workflows_sha": workflows_sha,
        "ruleset_version": run_config.get("ruleset_version", ""),
        "templates_version": run_config.get("templates_version", ""),
        "launcher_version": launcher_version,
        "upstream_artifact_hashes": upstream_artifact_hashes or {},
    }


def validate_provenance_compat(
    provenance: Dict[str, Any],
    *,
    required_repo_sha: str,
    required_ruleset_version: str = "",
    required_templates_version: str = "",
) -> Tuple[bool, List[Dict[str, str]]]:
    """Check whether a stored provenance record is compatible with current requirements.

    Returns (ok, reasons) where reasons is a list of dicts with
    'code' and 'message' keys explaining each incompatibility.
    """
    reasons: List[Dict[str, str]] = []

    stored_sha = provenance.get("repo_sha", "")
    if stored_sha != required_repo_sha:
        reasons.append({
            "code": "REPO_SHA_MISMATCH",
            "message": f"Stored repo_sha {stored_sha!r} != required {required_repo_sha!r}",
        })

    if required_ruleset_version:
        stored_rv = provenance.get("ruleset_version", "")
        if stored_rv != required_ruleset_version:
            reasons.append({
                "code": "RULESET_VERSION_MISMATCH",
                "message": f"Stored ruleset_version {stored_rv!r} != required {required_ruleset_version!r}",
            })

    if required_templates_version:
        stored_tv = provenance.get("templates_version", "")
        if stored_tv != required_templates_version:
            reasons.append({
                "code": "TEMPLATES_VERSION_MISMATCH",
                "message": f"Stored templates_version {stored_tv!r} != required {required_templates_version!r}",
            })

    return (len(reasons) == 0, reasons)
