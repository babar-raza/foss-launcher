"""Archive a completed run for long-term persistence.

Compresses bulky subdirectories (drafts/, artifacts/) into tar.gz archives
under runs/archives/<run_id>/, copies small metadata files uncompressed,
and optionally deletes the work/ directory to reclaim disk space.

Updates runs/manifest.jsonl with archive metadata.

Reference: RCA run-persistence plan (run manifest + archive tooling).

Usage:
    python scripts/archive_run.py <run_id_or_path> [--delete-work]
"""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import tarfile
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

RUNS_DIR = Path(__file__).resolve().parent.parent / "runs"

# Subdirectories to compress into tar.gz archives
ARCHIVE_DIRS = ("drafts", "artifacts")

# Small metadata files to copy uncompressed
METADATA_FILES = ("snapshot.json", "events.ndjson")


def find_run_dir(run_id_or_path: str) -> Path:
    """Resolve a run_id or explicit path to an existing run directory."""
    candidate = Path(run_id_or_path)
    if candidate.is_dir():
        return candidate.resolve()

    # Treat as a bare run_id under RUNS_DIR
    run_dir = RUNS_DIR / run_id_or_path
    if run_dir.is_dir():
        return run_dir.resolve()

    raise FileNotFoundError(
        f"Run directory not found: tried '{candidate}' and '{run_dir}'"
    )


def archive_run(run_dir: Path, delete_work: bool = False) -> Path:
    """Archive a single run.

    Args:
        run_dir: Resolved path to the run directory.
        delete_work: If True, delete the work/ subdirectory after archiving.

    Returns:
        Path to the archive directory (runs/archives/<run_id>/).
    """
    run_id = run_dir.name
    archives_root = RUNS_DIR / "archives"
    archive_dest = archives_root / run_id
    archive_dest.mkdir(parents=True, exist_ok=True)

    # 1. Compress bulky subdirectories
    for subdir_name in ARCHIVE_DIRS:
        subdir = run_dir / subdir_name
        if not subdir.is_dir():
            logger.info("Skipping %s (not present)", subdir_name)
            continue

        tar_path = archives_root / f"{run_id}_{subdir_name}.tar.gz"
        logger.info("Compressing %s -> %s", subdir, tar_path)
        with tarfile.open(tar_path, "w:gz") as tar:
            tar.add(str(subdir), arcname=subdir_name)
        logger.info("Created %s (%d bytes)", tar_path.name, tar_path.stat().st_size)

    # 2. Copy small metadata files uncompressed
    for fname in METADATA_FILES:
        src = run_dir / fname
        if src.is_file():
            dst = archive_dest / fname
            shutil.copy2(str(src), str(dst))
            logger.info("Copied %s -> %s", fname, dst)
        else:
            logger.info("Skipping %s (not present)", fname)

    # 3. Optionally delete work/ directory
    if delete_work:
        work_dir = run_dir / "work"
        if work_dir.is_dir():
            shutil.rmtree(str(work_dir))
            logger.info("Deleted work/ directory (%s)", work_dir)
        else:
            logger.info("No work/ directory to delete")

    # 4. Update manifest.jsonl
    _update_manifest(run_id, archive_dest)

    logger.info("Archive complete for run %s -> %s", run_id, archive_dest)
    return archive_dest


def _update_manifest(run_id: str, archive_dest: Path) -> None:
    """Mark the run as archived in manifest.jsonl."""
    manifest_path = RUNS_DIR / "manifest.jsonl"
    if not manifest_path.is_file():
        logger.warning("manifest.jsonl not found at %s; skipping update", manifest_path)
        return

    lines = manifest_path.read_text(encoding="utf-8").splitlines()
    updated_lines: list[str] = []
    found = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            updated_lines.append(line)
            continue
        try:
            entry = json.loads(stripped)
        except json.JSONDecodeError:
            updated_lines.append(line)
            continue

        if entry.get("run_id") == run_id:
            entry["archived"] = True
            entry["archive_path"] = str(archive_dest)
            entry["archived_at"] = datetime.now(timezone.utc).isoformat()
            updated_lines.append(json.dumps(entry, ensure_ascii=False))
            found = True
        else:
            updated_lines.append(line)

    if not found:
        logger.warning("Run %s not found in manifest.jsonl", run_id)

    manifest_path.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")
    logger.info("Updated manifest.jsonl (archived=%s)", found)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Archive a completed run for long-term persistence.",
    )
    parser.add_argument(
        "run_id",
        help="Run ID or full path to run directory",
    )
    parser.add_argument(
        "--delete-work",
        action="store_true",
        default=False,
        help="Delete the work/ subdirectory after archiving to reclaim disk space",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        default=False,
        help="Enable verbose (DEBUG) logging",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-8s %(message)s",
    )

    run_dir = find_run_dir(args.run_id)
    logger.info("Archiving run: %s", run_dir)
    archive_run(run_dir, delete_work=args.delete_work)


if __name__ == "__main__":
    main()
