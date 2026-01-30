#!/usr/bin/env python3
"""
Multi-pilot VFV runner.

Usage:
  run_multi_pilot_vfv.py --pilots pilot1,pilot2 [--goldenize]
"""

import argparse
import subprocess
import sys
from pathlib import Path


def get_repo_root() -> Path:
    """Get the repository root (parent of scripts/)."""
    return Path(__file__).resolve().parent.parent


def run_pilot_vfv(pilot_id: str, goldenize: bool, repo_root: Path) -> bool:
    """Run VFV for single pilot. Returns True if PASS."""
    venv_python = repo_root / ".venv" / "Scripts" / "python.exe"
    if not venv_python.exists():
        # Fallback for Unix-like systems
        venv_python = repo_root / ".venv" / "bin" / "python"

    if not venv_python.exists():
        raise FileNotFoundError(f"Virtual environment python not found: {venv_python}")

    cmd = [
        str(venv_python),
        str(repo_root / "scripts" / "run_pilot_vfv.py"),
        "--pilot", pilot_id
    ]
    if goldenize:
        cmd.append("--goldenize")

    result = subprocess.run(cmd, cwd=str(repo_root))
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="Multi-pilot VFV runner")
    parser.add_argument("--pilots", required=True, help="Comma-separated pilot IDs")
    parser.add_argument("--goldenize", action="store_true", help="Capture goldens for passing pilots")
    args = parser.parse_args()

    repo_root = get_repo_root()
    pilot_ids = [p.strip() for p in args.pilots.split(",")]

    print(f"Running VFV for {len(pilot_ids)} pilots")

    results = {}
    for pilot_id in pilot_ids:
        print(f"\n{'='*60}")
        print(f"Pilot: {pilot_id}")
        print('='*60)
        passed = run_pilot_vfv(pilot_id, args.goldenize, repo_root)
        results[pilot_id] = passed

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print('='*60)

    for pilot_id, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"{pilot_id}: {status}")

    total_pass = sum(results.values())
    total = len(results)
    print(f"\nTotal: {total_pass}/{total} PASS")

    sys.exit(0 if all(results.values()) else 1)


if __name__ == "__main__":
    main()
