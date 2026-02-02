#!/usr/bin/env python3
"""
VFV Harness: Verify-Fix-Verify pilot determinism.

Usage:
  run_pilot_vfv.py --pilot <pilot_id> [--goldenize] [--verbose]

Exits:
  0: Determinism PASS
  1: Determinism FAIL or artifacts missing
  2: Script error
"""

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime
import shutil


def get_repo_root() -> Path:
    """Get the repository root (parent of scripts/)."""
    return Path(__file__).resolve().parent.parent


def compute_canonical_hash(json_path: Path) -> str:
    """Compute canonical SHA256 hash of JSON artifact."""
    with json_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def run_pilot_e2e(pilot_id: str, run_suffix: str, repo_root: Path) -> Path:
    """Run pilot E2E and return run_dir."""
    venv_python = repo_root / ".venv" / "Scripts" / "python.exe"
    if not venv_python.exists():
        # Fallback for Unix-like systems
        venv_python = repo_root / ".venv" / "bin" / "python"

    if not venv_python.exists():
        raise FileNotFoundError(f"Virtual environment python not found: {venv_python}")

    config_path = repo_root / "specs" / "pilots" / pilot_id / "run_config.pinned.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"Pilot config not found: {config_path}")

    # Build CLI command
    cmd = [
        str(venv_python),
        "-c",
        "from launch.cli import main; main()",
        "run",
        "--config",
        str(config_path)
    ]

    started_at = datetime.now()

    # Execute and capture output
    result = subprocess.run(
        cmd,
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

    if result.returncode != 0:
        print(f"ERROR: Pilot run failed with exit code {result.returncode}")
        print(f"STDOUT:\n{result.stdout}")
        print(f"STDERR:\n{result.stderr}")
        sys.exit(2)

    # Find run_dir by looking for newest runs/* directory created after start
    runs_dir = repo_root / "runs"
    if not runs_dir.exists():
        raise RuntimeError("Runs directory not found")

    candidates = []
    for entry in runs_dir.iterdir():
        if entry.is_dir() and not entry.name.startswith(".") and not entry.name.startswith("agent_"):
            # Check if created after we started
            mtime = datetime.fromtimestamp(entry.stat().st_mtime)
            if mtime >= started_at:
                candidates.append((mtime, entry))

    if not candidates:
        raise RuntimeError("Could not determine run_dir from pilot output")

    # Sort by modification time (newest first)
    candidates.sort(reverse=True)
    run_dir = candidates[0][1]

    return run_dir


def verify_artifacts_exist(run_dir: Path) -> bool:
    """Check if both artifacts exist."""
    artifacts_dir = run_dir / "artifacts"
    if not artifacts_dir.exists():
        return False

    page_plan = artifacts_dir / "page_plan.json"
    validation_report = artifacts_dir / "validation_report.json"

    return page_plan.exists() and validation_report.exists()


def compare_artifacts(run_dir1: Path, run_dir2: Path) -> dict:
    """Compare artifacts and return determinism results."""
    artifacts = ["page_plan.json", "validation_report.json"]
    results = {}

    for artifact in artifacts:
        path1 = run_dir1 / "artifacts" / artifact
        path2 = run_dir2 / "artifacts" / artifact

        hash1 = compute_canonical_hash(path1)
        hash2 = compute_canonical_hash(path2)

        results[artifact] = {
            "hash1": hash1,
            "hash2": hash2,
            "deterministic": hash1 == hash2
        }

    return results


def capture_golden_artifacts(run_dir: Path, pilot_id: str, results: dict, repo_root: Path):
    """Copy artifacts to expected_*.json and update notes.md."""
    pilot_spec_dir = repo_root / "specs" / "pilots" / pilot_id

    # Copy artifacts
    for artifact in ["page_plan.json", "validation_report.json"]:
        src = run_dir / "artifacts" / artifact
        dst = pilot_spec_dir / f"expected_{artifact}"
        shutil.copy(src, dst)
        print(f"Captured: {dst}")

    # Update notes.md
    notes_path = pilot_spec_dir / "notes.md"
    notes_content = f"""# Golden Artifacts for {pilot_id}

**Captured**: {datetime.now().isoformat()}

## Determinism Status: PASS

### page_plan.json
- **Canonical Hash**: `{results['page_plan.json']['hash1']}`

### validation_report.json
- **Canonical Hash**: `{results['validation_report.json']['hash1']}`

## Verification
Two-run determinism verified. Both artifacts produce identical canonical JSON hashes.
"""

    with notes_path.open("w", encoding="utf-8") as f:
        f.write(notes_content)

    print(f"Updated: {notes_path}")


def main():
    parser = argparse.ArgumentParser(description="VFV harness for pilot determinism")
    parser.add_argument("--pilot", required=True, help="Pilot ID")
    parser.add_argument("--goldenize", action="store_true", help="Capture golden artifacts on PASS")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    args = parser.parse_args()

    repo_root = get_repo_root()

    print(f"Running VFV for pilot: {args.pilot}")

    # Run 1
    print("\n=== Run 1 ===")
    try:
        run_dir1 = run_pilot_e2e(args.pilot, "vfv_run1", repo_root)
    except Exception as e:
        print(f"ERROR during run1: {e}")
        sys.exit(2)

    if not verify_artifacts_exist(run_dir1):
        print("FAIL: Artifacts missing in run1")
        sys.exit(1)
    print(f"Run1 complete: {run_dir1}")

    # Run 2
    print("\n=== Run 2 ===")
    try:
        run_dir2 = run_pilot_e2e(args.pilot, "vfv_run2", repo_root)
    except Exception as e:
        print(f"ERROR during run2: {e}")
        sys.exit(2)

    if not verify_artifacts_exist(run_dir2):
        print("FAIL: Artifacts missing in run2")
        sys.exit(1)
    print(f"Run2 complete: {run_dir2}")

    # Compare
    print("\n=== Determinism Check ===")
    results = compare_artifacts(run_dir1, run_dir2)

    all_deterministic = all(r["deterministic"] for r in results.values())

    for artifact, r in results.items():
        status = "PASS" if r["deterministic"] else "FAIL"
        print(f"{artifact}: {status}")
        if args.verbose:
            print(f"  Hash1: {r['hash1']}")
            print(f"  Hash2: {r['hash2']}")

    # Goldenize if requested and deterministic
    if all_deterministic:
        print("\nDeterminism: PASS")
        if args.goldenize:
            print("\n=== Capturing Golden Artifacts ===")
            capture_golden_artifacts(run_dir1, args.pilot, results, repo_root)
        sys.exit(0)
    else:
        print("\nDeterminism: FAIL")
        sys.exit(1)


if __name__ == "__main__":
    main()
