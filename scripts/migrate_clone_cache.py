#!/usr/bin/env python3
"""One-time migration: rename corrupted po_* clone-cache dirs to correct aspose_* names.

Background
----------
The regex in _extract_brand_from_url previously used r"[-._\\s]+" in a raw string.
In a Python raw string, \\s is NOT the whitespace class — it is a literal backslash + 's'.
This made the character class split on the letter 's', turning "aspose" into "po":

    re.split(r"[-._\\s]+", "aspose-3d-foss")  # old, broken
    → ['a', 'po', 'e-3d-fo', '', '']  → brand = "po"

All clone-cache directories were therefore named po_<family>_<platform> instead of
aspose_<family>_<platform>.  The code fix was applied in acquisition.py (r"[-._\\\\s]+"
→ r"[-._\\s]+"), but the cache dirs were never renamed.  This script performs that
one-time rename.

Usage
-----
    python scripts/migrate_clone_cache.py [--cache-root PATH] [--dry-run]

Default cache root: intake/.clone_cache/ (relative to repo root, i.e. the directory
containing this script's parent).

The script reads the .clone_url marker in each cache dir to derive the correct brand
from the URL, then renames the directory atomically.  Dirs without a .clone_url marker
are skipped with a warning.

Exit codes
----------
0  All renames succeeded (or nothing was needed).
1  One or more errors occurred.
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Single source of truth: load _extract_brand_from_org directly from acquisition.py
# without triggering the package __init__.py (which pulls in third-party deps).
import importlib.util as _ilu
import sys as _sys

_ACQ_PATH = Path(__file__).resolve().parent.parent / "src" / "launcher" / "phase1" / "acquisition.py"
_spec = _ilu.spec_from_file_location("launcher.phase1.acquisition", _ACQ_PATH)
_acq = _ilu.module_from_spec(_spec)  # type: ignore[arg-type]
# Register before exec so that @dataclass can resolve __module__ references.
_sys.modules["launcher.phase1.acquisition"] = _acq
_spec.loader.exec_module(_acq)  # type: ignore[union-attr]
_extract_brand_from_org = _acq._extract_brand_from_org

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

_CLONE_URL_MARKER = ".clone_url"


def _extract_brand_from_url(repo_url: str) -> str:
    try:
        org = repo_url.split("/")[3]
        return _extract_brand_from_org(org)
    except (IndexError, AttributeError):
        return "unknown"


def migrate(cache_root: Path, *, dry_run: bool) -> int:
    """Rename all misnamed cache directories under cache_root.

    Returns 0 on full success, 1 if any error occurred.
    """
    if not cache_root.is_dir():
        logger.error("[migrate] Cache root does not exist: %s", cache_root)
        return 1

    errors = 0
    renames = 0
    skipped = 0

    for entry in sorted(cache_root.iterdir()):
        if not entry.is_dir():
            continue

        url_marker = entry / _CLONE_URL_MARKER
        if not url_marker.exists():
            logger.warning("[migrate] Skipping %s — no .clone_url marker", entry.name)
            skipped += 1
            continue

        try:
            repo_url = url_marker.read_text(encoding="utf-8").strip()
        except OSError as exc:
            logger.error("[migrate] Cannot read .clone_url in %s: %s", entry.name, exc)
            errors += 1
            continue

        correct_brand = _extract_brand_from_url(repo_url)
        if correct_brand == "unknown":
            logger.warning(
                "[migrate] Cannot derive brand from URL %r (dir=%s) — skipping",
                repo_url,
                entry.name,
            )
            skipped += 1
            continue

        # Parse the old dir name: everything after the first underscore is family_platform tail
        old_name = entry.name
        parts = old_name.split("_", 1)
        if len(parts) < 2:
            logger.warning("[migrate] Dir %r has no underscore — cannot parse family/platform, skipping", old_name)
            skipped += 1
            continue

        family_platform_tail = parts[1]
        new_name = f"{correct_brand}_{family_platform_tail}"

        if old_name == new_name:
            logger.info("[migrate] %s — already correct, no rename needed", old_name)
            continue

        new_path = cache_root / new_name
        if new_path.exists():
            logger.warning(
                "[migrate] Target %s already exists — skipping rename of %s (manual resolution required)",
                new_name,
                old_name,
            )
            skipped += 1
            continue

        if dry_run:
            logger.info("[dry-run] would rename %s → %s  (url=%s)", old_name, new_name, repo_url)
        else:
            try:
                entry.rename(new_path)
                logger.info("[migrate] renamed %s → %s  (url=%s)", old_name, new_name, repo_url)
                renames += 1
            except OSError as exc:
                logger.error("[migrate] Failed to rename %s → %s: %s", old_name, new_name, exc)
                errors += 1

    mode = "dry-run" if dry_run else "migration"
    logger.info(
        "[migrate] %s complete — %d renamed, %d skipped, %d errors",
        mode,
        renames,
        skipped,
        errors,
    )
    return 0 if errors == 0 else 1


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    default_cache_root = repo_root / "intake" / ".clone_cache"

    parser = argparse.ArgumentParser(
        description="Rename corrupted po_* clone-cache dirs to correct brand-prefixed names."
    )
    parser.add_argument(
        "--cache-root",
        type=Path,
        default=default_cache_root,
        help=f"Path to .clone_cache directory (default: {default_cache_root})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print renames without executing them.",
    )
    args = parser.parse_args()

    rc = migrate(args.cache_root, dry_run=args.dry_run)
    sys.exit(rc)


if __name__ == "__main__":
    main()
