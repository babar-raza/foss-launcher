"""Latest run state — cross-run artifact and repo reuse via snapshot.

Persists ALL artifacts, drafts, and work directory references from each run
into a ``latest/`` directory under the store key.  On subsequent runs with
matching repo SHA + interpretation signature, the snapshot is hydrated into the
new run directory — providing near-instant startup when nothing has changed.

TC-3660: Latest Run State
Spec: specs/48_autopilot_phase_selection.md §Latest Run State
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Cross-platform directory link helper
# ---------------------------------------------------------------------------

def _create_dir_link(target: Path, link: Path) -> bool:
    """Create a directory symlink (or Windows junction as fallback).

    Returns True on success, False on failure.
    """
    try:
        os.symlink(str(target), str(link), target_is_directory=True)
        return True
    except OSError:
        pass

    # Windows fallback: junction via mklink /J
    if sys.platform == "win32":
        try:
            subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(link), str(target)],
                check=True,
                capture_output=True,
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError, OSError):
            pass

    return False


def _win_path(p: Path) -> Path:
    """Prefix path with ``\\\\?\\`` on Windows to bypass MAX_PATH.

    Idempotent: already-prefixed paths returned unchanged.  No-op on non-Windows.
    """
    if sys.platform != "win32":
        return p
    s = str(p)
    if s.startswith("\\\\?\\"):
        return p
    return Path("\\\\?\\" + s)


# ---------------------------------------------------------------------------
# Write latest state
# ---------------------------------------------------------------------------

def write_latest_state(
    run_dir: Path,
    run_config: Dict[str, Any],
    store_root: Path,
    store_key: Path,
) -> None:
    """Snapshot the current run into ``latest/`` under the store key.

    Called unconditionally after ``launch drive`` (even on failure) so that the
    next run for the same product can reuse repos, artifacts, and drafts.
    """
    from launch.provenance import compute_interpretation_signature

    _t0 = time.monotonic()

    repo_sha = run_config.get("github_ref", "")
    sig = compute_interpretation_signature(run_config)

    latest_dir = store_root / store_key / "latest"
    tmp_dir = store_root / store_key / "latest_tmp"

    # ── Build meta.json ──
    last_run_state = ""
    failed_gate_count = -1

    snapshot_path = run_dir / "snapshot.json"
    if snapshot_path.is_file():
        try:
            snap = json.loads(snapshot_path.read_text(encoding="utf-8"))
            last_run_state = snap.get("state", "")
        except Exception:
            pass

    report_path = run_dir / "artifacts" / "validation_report.json"
    if report_path.is_file():
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
            gates = report.get("gates", [])
            failed_gate_count = sum(
                1 for g in gates if not g.get("ok", True) and not g.get("skipped", False)
            )
        except Exception:
            pass

    # Count drafts
    drafts_dir = run_dir / "drafts"
    drafts_count = 0
    if drafts_dir.is_dir():
        drafts_count = sum(1 for _ in drafts_dir.rglob("*.md"))

    # List artifacts
    artifacts_dir = run_dir / "artifacts"
    artifact_names: List[str] = []
    if artifacts_dir.is_dir():
        artifact_names = sorted(
            f.name for f in artifacts_dir.iterdir() if f.is_file() and f.suffix == ".json"
        )

    meta = {
        "schema_version": "1.0",
        "run_id": run_dir.name,
        "run_dir": str(run_dir.resolve()),
        "repo_sha": repo_sha,
        "interpretation_sig": sig,
        "last_run_state": last_run_state,
        "failed_gate_count": failed_gate_count,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "drafts_count": drafts_count,
        "artifact_names": artifact_names,
    }

    # ── Build work_refs.json ──
    work_refs: Dict[str, Optional[str]] = {}
    for name in ("repo", "site", "workflows"):
        work_path = run_dir / "work" / name
        if work_path.is_dir() and (work_path / ".git").exists():
            # Resolve symlinks to avoid chains
            work_refs[name] = str(work_path.resolve())
        else:
            work_refs[name] = None

    # ── Atomic write: tmp → latest ──
    if tmp_dir.exists():
        shutil.rmtree(_win_path(tmp_dir))
    _win_path(tmp_dir).mkdir(parents=True, exist_ok=True)

    (tmp_dir / "meta.json").write_text(
        json.dumps(meta, indent=2, sort_keys=True), encoding="utf-8"
    )
    (tmp_dir / "work_refs.json").write_text(
        json.dumps(work_refs, indent=2, sort_keys=True), encoding="utf-8"
    )

    # Copy artifacts
    tmp_artifacts = tmp_dir / "artifacts"
    tmp_artifacts.mkdir(exist_ok=True)
    _artifacts_written = 0
    if artifacts_dir.is_dir():
        for f in artifacts_dir.iterdir():
            if f.is_file() and f.suffix == ".json":
                shutil.copy2(str(f), str(tmp_artifacts / f.name))
                _artifacts_written += 1

    # Copy drafts (preserving subdirectory structure)
    tmp_drafts = tmp_dir / "drafts"
    _drafts_written = 0
    if drafts_dir.is_dir():
        for md_file in drafts_dir.rglob("*.md"):
            rel = md_file.relative_to(drafts_dir)
            dest = tmp_drafts / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(md_file), str(dest))
            _drafts_written += 1

    # Swap: remove old latest, rename tmp to latest
    if latest_dir.exists():
        shutil.rmtree(_win_path(latest_dir))
    shutil.move(str(tmp_dir), str(latest_dir))

    _work_refs_count = sum(1 for v in work_refs.values() if v is not None)
    _duration = time.monotonic() - _t0

    logger.info(
        "[LatestState] Wrote snapshot: %d artifacts, %d drafts, SHA=%s, sig=%s",
        len(artifact_names),
        drafts_count,
        repo_sha[:12] if repo_sha else "?",
        sig[:12] if sig else "?",
    )
    logger.info(
        "[LatestState] write_metrics: artifacts=%d, drafts=%d, "
        "work_refs=%d, duration_seconds=%.3f",
        _artifacts_written,
        _drafts_written,
        _work_refs_count,
        _duration,
    )


# ---------------------------------------------------------------------------
# Hydrate from latest state
# ---------------------------------------------------------------------------

def hydrate_latest_state(
    run_dir: Path,
    run_config: Dict[str, Any],
    store_root: Path,
    store_key: Path,
) -> int:
    """Restore artifacts, drafts, and work directory links from latest snapshot.

    Returns the total number of files/links created.  Returns 0 if no compatible
    snapshot exists.
    """
    from launch.provenance import compute_interpretation_signature

    _t0 = time.monotonic()

    latest_dir = store_root / store_key / "latest"
    meta_path = latest_dir / "meta.json"

    if not meta_path.is_file():
        logger.info("[LatestState] hydrate_skip: reason=no_meta")
        return 0

    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception:
        logger.warning("[LatestState] Failed to read meta.json, skipping")
        logger.info("[LatestState] hydrate_skip: reason=meta_read_error")
        return 0

    # ── Compatibility check ──
    required_sha = run_config.get("github_ref", "")
    required_sig = compute_interpretation_signature(run_config)

    stored_sha = meta.get("repo_sha", "")
    stored_sig = meta.get("interpretation_sig", "")

    if stored_sha != required_sha or stored_sig != required_sig:
        logger.info(
            "[LatestState] Incompatible snapshot (sha=%s→%s, sig=%s→%s), skipping",
            stored_sha[:12] if stored_sha else "?",
            required_sha[:12] if required_sha else "?",
            stored_sig[:12] if stored_sig else "?",
            required_sig[:12] if required_sig else "?",
        )
        logger.info("[LatestState] hydrate_skip: reason=incompatible")
        return 0

    total = 0
    _links_created = 0
    _links_failed = 0
    _artifacts_hydrated = 0
    _drafts_hydrated = 0

    # ── Repo reuse via symlink/junction ──
    refs_path = latest_dir / "work_refs.json"
    if refs_path.is_file():
        try:
            work_refs = json.loads(refs_path.read_text(encoding="utf-8"))
        except Exception:
            work_refs = {}

        for name in ("repo", "site", "workflows"):
            ref_str = work_refs.get(name)
            if ref_str is None:
                continue
            ref_path = Path(ref_str)
            if not ref_path.is_dir() or not (ref_path / ".git").exists():
                logger.info(
                    "[LatestState] work ref %s no longer valid, skipping", name
                )
                continue

            link_path = run_dir / "work" / name
            # Only attempt if the skeleton dir is empty
            try:
                os.rmdir(str(link_path))  # only works on empty dirs
            except OSError:
                # Dir not empty or doesn't exist — skip symlink
                continue

            if _create_dir_link(ref_path, link_path):
                logger.info("[LatestState] Linked work/%s → %s", name, ref_path)
                total += 1
                _links_created += 1
            else:
                # Re-create the empty directory so W1 can clone
                link_path.mkdir(parents=True, exist_ok=True)
                logger.warning(
                    "[LatestState] Failed to create link for work/%s", name
                )
                _links_failed += 1

    # ── Artifact hydration (non-overwriting) ──
    src_artifacts = latest_dir / "artifacts"
    dst_artifacts = run_dir / "artifacts"
    if src_artifacts.is_dir():
        for f in src_artifacts.iterdir():
            if f.is_file() and f.suffix == ".json":
                dest = dst_artifacts / f.name
                if not dest.exists():
                    shutil.copy2(str(f), str(dest))
                    total += 1
                    _artifacts_hydrated += 1

    # ── Draft hydration (non-overwriting) ──
    src_drafts = latest_dir / "drafts"
    dst_drafts = run_dir / "drafts"
    if src_drafts.is_dir():
        for md_file in src_drafts.rglob("*.md"):
            rel = md_file.relative_to(src_drafts)
            dest = dst_drafts / rel
            if not dest.exists():
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(md_file), str(dest))
                total += 1
                _drafts_hydrated += 1

    _duration = time.monotonic() - _t0

    logger.info("[LatestState] Hydrated %d files/links from latest snapshot", total)
    logger.info(
        "[LatestState] hydrate_metrics: artifacts=%d, drafts=%d, "
        "links_created=%d, links_failed=%d, duration_seconds=%.3f",
        _artifacts_hydrated,
        _drafts_hydrated,
        _links_created,
        _links_failed,
        _duration,
    )
    return total
