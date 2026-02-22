#!/usr/bin/env python3
"""Utility to re-run W8 (LinkerAndPatcher) and W9 (Validator) on an existing run.

Use this when you changed only W8 or W9 code and want to verify the fix
without re-running the full pipeline (W1–W7).

Usage:
    python scripts/rerun_w8_w9.py --run <run_dir>
    python scripts/rerun_w8_w9.py --latest 3d
    python scripts/rerun_w8_w9.py --latest note

Examples:
    # Re-run on a specific run directory
    python scripts/rerun_w8_w9.py --run runs/r_20260219T021813Z_launch_pilot-aspose-3d-foss-python_3711472_default_98a0a866

    # Re-run on the most recent 3D pilot run
    python scripts/rerun_w8_w9.py --latest 3d

    # Re-run without W9 (just apply patches)
    python scripts/rerun_w8_w9.py --latest 3d --skip-w9
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def get_repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def find_latest_run(repo_root: Path, pilot_key: str) -> Path:
    """Find the most recent run directory matching pilot_key in the manifest."""
    manifest = repo_root / "runs" / "manifest.jsonl"
    if not manifest.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest}")

    matches = []
    with open(manifest, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                pilot = entry.get("pilot", "")
                # Match "3d", "note", "cells" etc. in pilot name
                if pilot_key.lower() in pilot.lower():
                    out_dir = entry.get("output_dir", "")
                    if out_dir:
                        matches.append((entry.get("completed_at", ""), Path(out_dir)))
            except json.JSONDecodeError:
                continue

    if not matches:
        raise ValueError(f"No run found for pilot key '{pilot_key}'")

    # Sort by timestamp descending, return latest
    matches.sort(key=lambda x: x[0], reverse=True)
    latest_path = matches[0][1]
    print(f"[rerun] Latest run for '{pilot_key}': {latest_path.name}")
    return latest_path


def load_run_config(run_dir: Path) -> dict:
    """Load run_config from the run directory (persisted as run_config.yaml at run time)."""
    import sys
    repo_root = run_dir.parent.parent
    sys.path.insert(0, str(repo_root / "src"))

    # run_config.yaml is copied to the run directory root at pipeline start
    rc_yaml = run_dir / "run_config.yaml"
    if rc_yaml.exists():
        from launch.io.run_config import load_and_validate_run_config
        config = load_and_validate_run_config(repo_root, rc_yaml)
        return config

    raise FileNotFoundError(
        f"run_config.yaml not found in {run_dir}/. "
        "Cannot re-run without run configuration."
    )


def _ensure_paths() -> None:
    """Add repo src/ and root to sys.path for module resolution."""
    repo_root = get_repo_root()
    src = str(repo_root / "src")
    root = str(repo_root)
    if src not in sys.path:
        sys.path.insert(0, src)
    if root not in sys.path:
        sys.path.insert(0, root)


def rerun_w8(run_dir: Path, run_config: dict) -> None:
    """Re-apply W8 LinkerAndPatcher patches."""
    _ensure_paths()
    from launch.workers.w8_linker_and_patcher.worker import execute_linker_and_patcher

    print("[rerun] Running W8 LinkerAndPatcher...")
    result = execute_linker_and_patcher(run_dir=run_dir, run_config=run_config)
    applied = result.get("patches_applied", 0)
    skipped = result.get("patches_skipped", 0)
    print(f"[rerun] W8 complete: {applied} applied, {skipped} skipped")


def rerun_w9(run_dir: Path, run_config: dict) -> bool:
    """Re-run W9 Validator. Returns True if all gates pass."""
    _ensure_paths()
    from launch.workers.w9_validator.worker import execute_validator

    print("[rerun] Running W9 Validator...")
    report = execute_validator(run_dir=run_dir, run_config=run_config)

    gates = report.get("gates", [])
    failed = [g for g in gates if not g.get("ok", True)]
    passed = [g for g in gates if g.get("ok", True)]

    print(f"[rerun] W9 gates: {len(passed)} PASS, {len(failed)} FAIL")
    for g in failed:
        print(f"  FAIL: {g['name']}")

    # Show error-severity issues
    issues = report.get("issues", [])
    errors = [i for i in issues if i.get("severity") in ("error", "blocker")]
    if errors:
        print(f"[rerun] {len(errors)} error/blocker issues:")
        for iss in errors[:10]:  # cap at 10
            msg = iss.get("message", "")
            code = iss.get("error_code", "")
            line = f"  {code}: {msg}"
            # Encode to ASCII to avoid Windows cp1252 console errors with special Unicode chars
            print(line.encode("ascii", errors="replace").decode("ascii"))

    overall_ok = len(failed) == 0
    print(f"[rerun] Validation: {'PASS' if overall_ok else 'FAIL'}")
    return overall_ok


def main() -> int:
    parser = argparse.ArgumentParser(description="Re-run W8 and W9 on an existing run")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--run", type=Path, help="Path to run directory")
    group.add_argument("--latest", metavar="PILOT_KEY",
                       help="Re-run on most recent run matching this pilot key (3d, note, cells)")
    parser.add_argument("--skip-w9", action="store_true",
                        help="Skip W9 validation (only re-apply W8 patches)")
    parser.add_argument("--skip-w8", action="store_true",
                        help="Skip W8 (only re-run W9 validation)")
    args = parser.parse_args()

    repo_root = get_repo_root()

    # Resolve run directory
    if args.latest:
        run_dir = find_latest_run(repo_root, args.latest)
    else:
        run_dir = args.run
        if not run_dir.is_absolute():
            run_dir = repo_root / run_dir

    if not run_dir.exists():
        print(f"ERROR: Run directory not found: {run_dir}", file=sys.stderr)
        return 1

    print(f"[rerun] Run directory: {run_dir}")

    # Load run config
    try:
        run_config = load_run_config(run_dir)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    # Re-run stages
    if not args.skip_w8:
        rerun_w8(run_dir, run_config)

    if not args.skip_w9:
        ok = rerun_w9(run_dir, run_config)
        return 0 if ok else 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
