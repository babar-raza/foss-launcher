#!/usr/bin/env python3
"""Detect ENGINE_VERSION drift: W2/W3/W4 source changed without version bump.

SR-04 (TC-3250 healing): Prevents silent stale-derived-artifact reuse by
checking that ENGINE_VERSION in provenance.py is bumped whenever the source
files that feed W2/W3/W4 interpretation change.

Usage:
    python tools/check_engine_version_drift.py          # check + auto-regen
    python tools/check_engine_version_drift.py --check   # check only (CI mode)

Exit codes:
    0  Lock is current (or regenerated after ENGINE_VERSION bump)
    1  Source drift detected without ENGINE_VERSION bump
    2  Usage / unexpected error
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Dict, List

# ---------------------------------------------------------------------------
# Configuration — directories whose changes affect W2/W3/W4 interpretation
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent

PROVENANCE_MODULE = REPO_ROOT / "src" / "launch" / "provenance" / "provenance.py"

LOCKFILE = REPO_ROOT / "src" / "launch" / "provenance" / ".engine_version_lock.json"

#: Glob patterns relative to REPO_ROOT whose content determines the
#: interpretation fingerprint.  Only ``*.py`` and ``*.json`` are hashed.
SOURCE_PATTERNS: List[str] = [
    "src/launch/workers/w2_facts_builder/**/*.py",
    "src/launch/workers/w3_snippet_curator/**/*.py",
    "src/launch/workers/w4_ia_planner/**/*.py",
    "specs/schemas/api_inventory.schema.json",
    "specs/schemas/repo_truth.schema.json",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_engine_version(module_path: Path) -> str:
    """Extract ENGINE_VERSION = '...' from provenance.py."""
    text = module_path.read_text(encoding="utf-8")
    m = re.search(r'^ENGINE_VERSION\s*=\s*["\']([^"\']+)["\']', text, re.MULTILINE)
    if not m:
        raise RuntimeError(f"ENGINE_VERSION not found in {module_path}")
    return m.group(1)


def _collect_source_files(repo_root: Path, patterns: List[str]) -> List[Path]:
    """Expand glob patterns and return a sorted list of existing files."""
    files: List[Path] = []
    for pattern in patterns:
        files.extend(repo_root.glob(pattern))
    # Deduplicate and sort for determinism
    return sorted(set(f for f in files if f.is_file()))


def _compute_fingerprint(files: List[Path], repo_root: Path) -> str:
    """SHA-256 of (sorted relative paths + file contents)."""
    h = hashlib.sha256()
    for f in files:
        rel = f.relative_to(repo_root).as_posix()
        h.update(rel.encode("utf-8"))
        h.update(b"\x00")
        h.update(f.read_bytes())
        h.update(b"\x00")
    return h.hexdigest()


def _read_lockfile(lockfile: Path) -> Dict[str, str]:
    """Read lockfile, return {} if missing or corrupt."""
    if not lockfile.is_file():
        return {}
    try:
        return json.loads(lockfile.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _write_lockfile(lockfile: Path, engine_version: str, fingerprint: str) -> None:
    lockfile.parent.mkdir(parents=True, exist_ok=True)
    lockfile.write_text(
        json.dumps(
            {
                "engine_version": engine_version,
                "source_fingerprint": fingerprint,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Main logic (importable for tests)
# ---------------------------------------------------------------------------


def check_drift(
    repo_root: Path = REPO_ROOT,
    provenance_module: Path = PROVENANCE_MODULE,
    lockfile: Path = LOCKFILE,
    patterns: List[str] = SOURCE_PATTERNS,
    *,
    check_only: bool = False,
) -> int:
    """Check for ENGINE_VERSION drift.

    Returns 0 if OK (lock current or regenerated), 1 if drift detected.
    """
    engine_version = _read_engine_version(provenance_module)
    source_files = _collect_source_files(repo_root, patterns)

    if not source_files:
        print(f"WARNING: No source files matched patterns: {patterns}", file=sys.stderr)
        return 0

    fingerprint = _compute_fingerprint(source_files, repo_root)
    lock = _read_lockfile(lockfile)

    if not lock:
        # First run — create lockfile
        if check_only:
            print(
                f"ERROR: Lockfile {lockfile} does not exist. "
                "Run without --check to generate it.",
                file=sys.stderr,
            )
            return 1
        _write_lockfile(lockfile, engine_version, fingerprint)
        print(f"OK: Created lockfile with ENGINE_VERSION={engine_version}")
        return 0

    locked_version = lock.get("engine_version", "")
    locked_fingerprint = lock.get("source_fingerprint", "")

    if locked_fingerprint == fingerprint and locked_version == engine_version:
        # No changes
        print(f"OK: ENGINE_VERSION={engine_version}, sources unchanged.")
        return 0

    if locked_version != engine_version:
        # ENGINE_VERSION was bumped — regenerate lockfile
        if check_only:
            print(
                f"OK: ENGINE_VERSION bumped ({locked_version} -> {engine_version}). "
                "Lockfile needs regeneration (run without --check).",
            )
            return 0
        _write_lockfile(lockfile, engine_version, fingerprint)
        print(
            f"OK: ENGINE_VERSION bumped ({locked_version} -> {engine_version}). "
            "Lockfile regenerated."
        )
        return 0

    # Fingerprint changed but ENGINE_VERSION did not
    print(
        f"ERROR: W2/W3/W4 source files changed but ENGINE_VERSION "
        f"was not bumped (still {engine_version}).\n"
        f"  Locked fingerprint:  {locked_fingerprint[:16]}...\n"
        f"  Current fingerprint: {fingerprint[:16]}...\n"
        f"Fix: Bump ENGINE_VERSION in {provenance_module.relative_to(repo_root)} "
        f"or run this script without --check to regenerate the lockfile.",
        file=sys.stderr,
    )
    return 1


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    ci_mode = "--check" in sys.argv
    sys.exit(check_drift(check_only=ci_mode))
