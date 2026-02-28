"""State store — file-based persistent artifact cache for autopilot reuse.

Store layout::

    <store_root>/
      <family>/<platform>/
        raw/                        # TC-3250: RAW layer (W1, SHA-only key)
          <repo_sha>/
            w1/  *.json
        derived/                    # TC-3250: DERIVED layer (W2-W4, SHA+sig key)
          <repo_sha>/
            <sig>/
              w2/  *.json
              w3/  *.json
              w4/  *.json
        manifest.json
        artifacts/                  # Legacy layout (backward compat) + W5/W8/W9
          <repo_sha>/
            w5/  *.json
            w8/  *.json
            w9/  *.json
            provenance.json
        conflicts/
          <repo_sha>/
            <worker_id>/  *.json   (saved on content-mismatch)

Safety invariant
~~~~~~~~~~~~~~~~
``publish_worker_artifacts`` and ``publish_run_artifacts`` NEVER overwrite an
existing file unless the incoming content is byte-identical (SHA-256 check).
If the content differs the incoming file is copied to ``conflicts/`` and a
``StoreConflictError`` is raised.

Two-layer design (TC-3250)
~~~~~~~~~~~~~~~~~~~~~~~~~~
W1 artifacts are keyed by ``repo_sha`` only (RAW layer — stable extraction).
W2/W3/W4 artifacts are keyed by ``(repo_sha, sig)`` (DERIVED layer —
interpretation-dependent).  ``sig`` is computed by
``launch.provenance.compute_interpretation_signature(run_config)``.

TC-3010 — Autopilot: State Store Library
TC-3060 — Expand to full pipeline coverage (W1-W5, W8, W9)
TC-3070 — Wire provenance validation into artifact reuse
TC-3250 — SHA-scoped two-layer worker cache (RAW + DERIVED)
"""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from launch.provenance import compute_file_sha256

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class StoreConflictError(Exception):
    """Raised when publishing would overwrite an existing artifact with different content."""


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_STORE_ROOT = ".foss_state"
_PUBLISHABLE_WORKERS = ("w1", "w2", "w3", "w4", "w5", "w8", "w9")

# Two-layer store (TC-3250)
_RAW_LAYER = "raw"
_DERIVED_LAYER = "derived"
_RAW_WORKERS = frozenset(["w1"])
_DERIVED_WORKERS = frozenset(["w2", "w3", "w4"])

# Event type constants for two-layer hydration observability (TC-3250).
# Defined here to avoid dependency on src/launch/models/** (owned by TC-250).
# TODO(TC-250): migrate to models/event.py when TC-250 allows event constant additions.
STORE_HYDRATE_RAW_USED = "STORE_HYDRATE_RAW_USED"
STORE_HYDRATE_DERIVED_USED = "STORE_HYDRATE_DERIVED_USED"
STORE_DERIVED_MISS_SIGNATURE = "STORE_DERIVED_MISS_SIGNATURE"

# Module-level artifact → worker mapping used by both old and new publish functions.
# W1 artifacts go to the RAW layer; W2/W3/W4 go to the DERIVED layer;
# W5/W8/W9 go to the legacy artifacts/ layout.
_ARTIFACT_WORKER_MAP: Dict[str, str] = {
    # W1 outputs
    "repo_inventory.json": "w1",
    "frontmatter_contract.json": "w1",
    "site_context.json": "w1",
    "hugo_facts.json": "w1",
    "resolved_refs.json": "w1",
    "discovered_docs.json": "w1",
    "discovered_examples.json": "w1",
    # W2 outputs
    "product_facts.json": "w2",
    "evidence_map.json": "w2",
    "api_inventory.json": "w2",
    "repo_truth.json": "w2",
    "extracted_claims.json": "w2",
    "code_analysis.json": "w2",
    "code_understanding.json": "w2",
    # W3 outputs
    "snippet_catalog.json": "w3",
    "code_snippets.json": "w3",
    "doc_snippets.json": "w3",
    # W4 outputs
    "page_plan.json": "w4",
    "shared_facts.json": "w4",
    # W5 outputs
    "draft_manifest.json": "w5",
    "sanitizer_metrics.json": "w5",
    # W8 outputs
    "patch_bundle.json": "w8",
    # W9 outputs
    "validation_report.json": "w9",
}


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def get_store_root(run_config: Dict[str, Any]) -> Path:
    """Return the state store root directory.

    Checks ``run_config["autopilot"]["state_store_root"]`` first,
    falls back to ``".foss_state"`` relative to CWD.
    """
    autopilot = run_config.get("autopilot", {})
    custom = autopilot.get("state_store_root", "")
    if custom:
        return Path(custom)
    return Path(_DEFAULT_STORE_ROOT)


def get_store_key(run_config: Dict[str, Any]) -> Path:
    """Build store key path from run config.

    Returns a ``Path`` like ``cells/python``.
    """
    family = run_config.get("family", "unknown")
    platform = run_config.get("target_platform", "unknown")
    return Path(family) / platform


def list_available_shas(store_root: Path, store_key: Path) -> List[str]:
    """List all repo_sha values that have stored artifacts.

    Returns a **sorted** list of SHA directory names under ``artifacts/``.
    """
    artifacts_dir = store_root / store_key / "artifacts"
    if not artifacts_dir.is_dir():
        return []
    return sorted(
        d.name for d in artifacts_dir.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    )


def find_artifact_set(
    store_root: Path,
    store_key: Path,
    repo_sha: str,
) -> Optional[Path]:
    """Find the artifact set for a specific *repo_sha* (legacy layout).

    Returns the path to ``artifacts/<repo_sha>/`` if it exists **and**
    contains at least one publishable worker subdirectory, else ``None``.

    This function supports the legacy single-layer layout for backward
    compatibility.  New code should prefer ``find_raw_artifact_set`` and
    ``find_derived_artifact_set``.
    """
    sha_dir = store_root / store_key / "artifacts" / repo_sha
    if not sha_dir.is_dir():
        return None
    # Must have at least one worker subdir
    worker_dirs = [
        d for d in sha_dir.iterdir()
        if d.is_dir() and d.name in _PUBLISHABLE_WORKERS
    ]
    if not worker_dirs:
        return None
    return sha_dir


# ---------------------------------------------------------------------------
# Two-layer store path helpers (TC-3250)
# ---------------------------------------------------------------------------

def get_raw_dir(store_root: Path, store_key: Path, repo_sha: str) -> Path:
    """Return the RAW layer directory for a given repo_sha.

    Path: ``<store_root>/<key>/raw/<repo_sha>/``
    """
    return store_root / store_key / _RAW_LAYER / repo_sha


def get_derived_dir(
    store_root: Path,
    store_key: Path,
    repo_sha: str,
    sig: str,
) -> Path:
    """Return the DERIVED layer directory for a given (repo_sha, sig) pair.

    Path: ``<store_root>/<key>/derived/<repo_sha>/<sig>/``
    """
    return store_root / store_key / _DERIVED_LAYER / repo_sha / sig


def find_raw_artifact_set(
    store_root: Path,
    store_key: Path,
    repo_sha: str,
) -> Optional[Path]:
    """Find the RAW artifact set for a given repo_sha.

    Returns the path to ``raw/<repo_sha>/`` if it contains a non-empty
    ``w1/`` subdirectory, else ``None``.

    The RAW set is keyed by SHA only — no interpretation signature.
    """
    raw_dir = get_raw_dir(store_root, store_key, repo_sha)
    w1_dir = raw_dir / "w1"
    if w1_dir.is_dir() and any(w1_dir.glob("*.json")):
        return raw_dir
    return None


def find_derived_artifact_set(
    store_root: Path,
    store_key: Path,
    repo_sha: str,
    sig: str,
) -> Optional[Path]:
    """Find the DERIVED artifact set for a given (repo_sha, sig) pair.

    Returns the path to ``derived/<repo_sha>/<sig>/`` if it contains at
    least one non-empty worker subdirectory (w2, w3, or w4), else ``None``.

    Returns ``None`` if the sig does not match — callers should recompute
    W2/W3/W4 in that case.
    """
    derived_dir = get_derived_dir(store_root, store_key, repo_sha, sig)
    for w in ("w2", "w3", "w4"):
        worker_dir = derived_dir / w
        if worker_dir.is_dir() and any(worker_dir.glob("*.json")):
            return derived_dir
    if derived_dir.is_dir() and any(
        (derived_dir / w).is_dir() for w in ("w2", "w3", "w4")
    ):
        logger.debug(
            "store_find_derived_empty: %s/%s has dirs but no JSON",
            repo_sha[:12], sig[:12],
        )
    return None


# ---------------------------------------------------------------------------
# Two-layer hydration (TC-3250)
# ---------------------------------------------------------------------------

def hydrate_from_raw(run_dir: Path, raw_set: Path) -> int:
    """Hydrate W1 artifacts from the RAW layer into a run directory.

    Copies all ``*.json`` files from ``raw_set/w1/`` into
    ``run_dir/artifacts/``.  Existing files are not overwritten.

    Returns the number of files copied.
    """
    target_dir = run_dir / "artifacts"
    target_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    w1_dir = raw_set / "w1"
    if w1_dir.is_dir():
        for src_file in sorted(w1_dir.glob("*.json")):
            dst = target_dir / src_file.name
            if not dst.exists():
                shutil.copy2(src_file, dst)
                count += 1
            else:
                logger.debug("hydrate_raw_skip_existing: %s", dst.name)

    logger.info("store_hydrate_raw: %d files -> %s", count, run_dir)
    return count


def hydrate_from_derived(run_dir: Path, derived_set: Path) -> int:
    """Hydrate W2/W3/W4 artifacts from the DERIVED layer into a run directory.

    Copies all ``*.json`` files from ``derived_set/w{2,3,4}/`` into
    ``run_dir/artifacts/``.  Existing files are not overwritten.

    Returns the number of files copied.
    """
    target_dir = run_dir / "artifacts"
    target_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    for w in ("w2", "w3", "w4"):
        w_dir = derived_set / w
        if w_dir.is_dir():
            for src_file in sorted(w_dir.glob("*.json")):
                dst = target_dir / src_file.name
                if not dst.exists():
                    shutil.copy2(src_file, dst)
                    count += 1
                else:
                    logger.debug("hydrate_derived_skip_existing: %s", dst.name)

    logger.info("store_hydrate_derived: %d files -> %s", count, run_dir)
    return count


# ---------------------------------------------------------------------------
# Two-layer publishing (TC-3250)
# ---------------------------------------------------------------------------

def publish_raw_artifacts(
    store_root: Path,
    store_key: Path,
    repo_sha: str,
    run_dir: Path,
) -> int:
    """Publish W1 artifacts to the RAW layer.

    Safe to call regardless of pipeline success — only files that exist
    in ``run_dir/artifacts/`` and map to W1 are published.

    Returns the number of files published.
    """
    artifacts_dir = run_dir / "artifacts"
    if not artifacts_dir.is_dir():
        return 0

    raw_w1_dir = get_raw_dir(store_root, store_key, repo_sha) / "w1"
    conflicts_dir = store_root / store_key / "conflicts" / repo_sha / "raw" / "w1"

    count = 0
    for fname, worker in _ARTIFACT_WORKER_MAP.items():
        if worker not in _RAW_WORKERS:
            continue
        src = artifacts_dir / fname
        if src.is_file():
            _safe_copy_file(src, raw_w1_dir / fname, conflicts_dir)
            count += 1

    if count > 0:
        logger.info("store_publish_raw: %s -> %d files", repo_sha[:12], count)
    return count


def publish_derived_artifacts(
    store_root: Path,
    store_key: Path,
    repo_sha: str,
    sig: str,
    run_dir: Path,
) -> int:
    """Publish W2/W3/W4 artifacts to the DERIVED layer.

    Safe to call regardless of pipeline success — only files that exist
    in ``run_dir/artifacts/`` and map to W2/W3/W4 are published.

    Returns the number of files published.
    """
    artifacts_dir = run_dir / "artifacts"
    if not artifacts_dir.is_dir():
        return 0

    derived_base = get_derived_dir(store_root, store_key, repo_sha, sig)
    conflicts_base = store_root / store_key / "conflicts" / repo_sha / "derived" / sig

    count = 0
    for fname, worker in _ARTIFACT_WORKER_MAP.items():
        if worker not in _DERIVED_WORKERS:
            continue
        src = artifacts_dir / fname
        if src.is_file():
            target_dir = derived_base / worker
            conflicts_dir = conflicts_base / worker
            _safe_copy_file(src, target_dir / fname, conflicts_dir)
            count += 1

    if count > 0:
        logger.info(
            "store_publish_derived: %s/%s -> %d files",
            repo_sha[:12],
            sig,
            count,
        )
    return count


# ---------------------------------------------------------------------------
# Provenance (TC-3070)
# ---------------------------------------------------------------------------

def write_provenance(
    store_root: Path,
    store_key: Path,
    repo_sha: str,
    provenance_record: Dict[str, Any],
) -> Path:
    """Write ``provenance.json`` alongside worker dirs in the artifact set.

    Returns the path to the written file.
    """
    prov_path = store_root / store_key / "artifacts" / repo_sha / "provenance.json"
    prov_path.parent.mkdir(parents=True, exist_ok=True)
    prov_path.write_text(
        json.dumps(provenance_record, indent=2, sort_keys=True, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )
    logger.info("store_provenance_written: %s", prov_path)
    return prov_path


def read_provenance(artifact_set_path: Path) -> Optional[Dict[str, Any]]:
    """Read ``provenance.json`` from an artifact set.

    Returns the parsed dict, or ``None`` if the file is absent or unparseable.
    """
    prov_path = artifact_set_path / "provenance.json"
    if not prov_path.exists():
        return None
    try:
        return json.loads(prov_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        logger.warning("store_provenance_unreadable: %s", prov_path)
        return None


# ---------------------------------------------------------------------------
# Publishing
# ---------------------------------------------------------------------------

def publish_worker_artifacts(
    store_root: Path,
    store_key: Path,
    repo_sha: str,
    worker_id: str,
    artifacts_dir: Path,
) -> int:
    """Publish artifacts from a single worker into the store (legacy layout).

    Only publishes ``*.json`` files from *artifacts_dir*.
    Returns the number of files published.

    Args:
        store_root: State store root path.
        store_key: ``family/platform`` key path.
        repo_sha: Git commit SHA.
        worker_id: Worker identifier (e.g. ``"w1"``, ``"w2"``).
        artifacts_dir: Source directory containing artifact JSON files.
    """
    worker_id_lower = worker_id.lower()
    if worker_id_lower not in _PUBLISHABLE_WORKERS:
        logger.warning("store_skip_non_publishable: %s", worker_id)
        return 0

    target_dir = store_root / store_key / "artifacts" / repo_sha / worker_id_lower
    conflicts_dir = store_root / store_key / "conflicts" / repo_sha / worker_id_lower

    count = 0
    for src_file in sorted(artifacts_dir.glob("*.json")):
        if src_file.is_file():
            _safe_copy_file(src_file, target_dir / src_file.name, conflicts_dir)
            count += 1

    if count > 0:
        logger.info(
            "store_published: %s/%s -> %d files",
            repo_sha[:12],
            worker_id_lower,
            count,
        )
    return count


def publish_run_artifacts(
    store_root: Path,
    store_key: Path,
    repo_sha: str,
    run_dir: Path,
) -> int:
    """Publish late-stage pipeline artifacts into the legacy store layout.

    Scans ``run_dir/artifacts/`` for files matching W5/W8/W9 worker output
    patterns.  Returns the total number of files published.

    W1 artifacts are published by ``publish_raw_artifacts`` (RAW layer).
    W2/W3/W4 artifacts are published by ``publish_derived_artifacts``
    (DERIVED layer).  This function handles only W5/W8/W9 to the legacy
    ``artifacts/<repo_sha>/`` layout.

    W6/W7/W10/W11 are excluded (W6/W7 have no artifacts in ``artifacts/``,
    W10 does in-place fixes, W11 produces external-state ``pr.json``).
    """
    artifacts_dir = run_dir / "artifacts"
    if not artifacts_dir.is_dir():
        logger.warning("store_no_artifacts_dir: %s", run_dir)
        return 0

    total = 0
    for artifact_file in sorted(artifacts_dir.glob("*.json")):
        worker_id = _ARTIFACT_WORKER_MAP.get(artifact_file.name)
        # Skip W1/W2/W3/W4 — handled by new two-layer publish functions
        if worker_id and worker_id not in _RAW_WORKERS and worker_id not in _DERIVED_WORKERS:
            target_dir = (
                store_root / store_key / "artifacts" / repo_sha / worker_id
            )
            conflicts_dir = (
                store_root / store_key / "conflicts" / repo_sha / worker_id
            )
            _safe_copy_file(
                artifact_file, target_dir / artifact_file.name, conflicts_dir,
            )
            total += 1
        elif worker_id and (worker_id in _RAW_WORKERS or worker_id in _DERIVED_WORKERS):
            logger.debug(
                "store_publish_skip_two_layer: %s -> %s (use publish_raw/derived_artifacts)",
                artifact_file.name, worker_id,
            )

    if total > 0:
        _update_manifest(store_root, store_key, repo_sha)
        logger.info("store_publish_run: %s -> %d files", repo_sha[:12], total)
    return total


# ---------------------------------------------------------------------------
# Hydration (legacy)
# ---------------------------------------------------------------------------

def hydrate_run_dir(
    run_dir: Path,
    artifact_set_path: Path,
) -> int:
    """Copy stored artifacts into a run directory (legacy layout).

    Copies all ``*.json`` files from each worker subdirectory in the
    artifact set into ``run_dir/artifacts/``.

    Returns the number of files copied.
    """
    target_dir = run_dir / "artifacts"
    target_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    for worker_dir in sorted(artifact_set_path.iterdir()):
        if worker_dir.is_dir() and worker_dir.name in _PUBLISHABLE_WORKERS:
            for src_file in sorted(worker_dir.glob("*.json")):
                dst = target_dir / src_file.name
                if not dst.exists():
                    shutil.copy2(src_file, dst)
                    count += 1
                else:
                    logger.debug("hydrate_skip_existing: %s", dst.name)

    logger.info("store_hydrate: %d files -> %s", count, run_dir)
    return count


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _safe_copy_file(src: Path, dst: Path, conflicts_dir: Path) -> None:
    """Copy *src* to *dst* with SHA-256 collision detection.

    * If *dst* exists with identical content -- skip (idempotent).
    * If *dst* exists with different content -- copy to ``conflicts/`` and
      raise :class:`StoreConflictError`.
    * If *dst* does not exist -- copy.
    """
    if dst.exists():
        src_hash = compute_file_sha256(src)
        dst_hash = compute_file_sha256(dst)
        if src_hash == dst_hash:
            logger.debug("store_skip_identical: %s", dst)
            return
        # Conflict: save incoming file to conflicts/ and raise
        conflicts_dir.mkdir(parents=True, exist_ok=True)
        conflict_path = conflicts_dir / dst.name
        shutil.copy2(src, conflict_path)
        raise StoreConflictError(
            f"Content mismatch for {dst.name}: "
            f"existing={dst_hash[:12]}, incoming={src_hash[:12]}. "
            f"Incoming file saved to {conflict_path}"
        )
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def _update_manifest(
    store_root: Path,
    store_key: Path,
    repo_sha: str,
) -> None:
    """Update ``manifest.json`` for a store key after publishing."""
    manifest_path = store_root / store_key / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    if manifest_path.exists():
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = {}
    else:
        data = {}

    available = list_available_shas(store_root, store_key)
    data["best_sha"] = repo_sha
    data["available_shas"] = available
    data["schema_version"] = "1.0"

    manifest_path.write_text(
        json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
