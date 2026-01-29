#!/usr/bin/env python3
"""
TC-520: Pilot runner script with deterministic enumeration and CLI execution.

Usage:
    python scripts/run_pilot.py --pilot <pilot_id> [--dry-run] [--output <path>]

Supports:
- Deterministic pilot enumeration (sorted)
- Dry-run mode: validate config only, no network/cloning
- Full execution: runs CLI and captures artifacts
- Deterministic JSON report with SHA256 checksums
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


def get_repo_root() -> Path:
    """Get the repository root (parent of scripts/)."""
    return Path(__file__).resolve().parent.parent


def enumerate_pilots(repo_root: Path) -> List[str]:
    """
    Enumerate pilot IDs from specs/pilots/ in sorted deterministic order.

    Returns:
        Sorted list of pilot_id strings.
    """
    pilots_dir = repo_root / "specs" / "pilots"
    if not pilots_dir.exists():
        return []

    pilot_ids = []
    for entry in pilots_dir.iterdir():
        if entry.is_dir() and not entry.name.startswith("."):
            pilot_ids.append(entry.name)

    return sorted(pilot_ids)


def validate_pilot_config(repo_root: Path, pilot_id: str) -> Dict[str, Any]:
    """
    Validate pilot configuration using existing loader.

    Args:
        repo_root: Repository root path
        pilot_id: Pilot identifier

    Returns:
        Validated config dictionary

    Raises:
        Exception if validation fails
    """
    config_path = repo_root / "specs" / "pilots" / pilot_id / "run_config.pinned.yaml"

    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")

    # Import the existing loader
    sys.path.insert(0, str(repo_root / "src"))
    from launch.io.run_config import load_and_validate_run_config

    config = load_and_validate_run_config(repo_root, config_path)
    return config


def compute_sha256(file_path: Path) -> str:
    """Compute SHA256 checksum of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def execute_pilot_cli(repo_root: Path, config_path: Path) -> Dict[str, Any]:
    """
    Execute pilot via CLI and capture results.

    Args:
        repo_root: Repository root path
        config_path: Path to run_config.pinned.yaml

    Returns:
        Dictionary with exit_code, run_dir, start/end times
    """
    venv_python = repo_root / ".venv" / "Scripts" / "python.exe"
    if not venv_python.exists():
        # Fallback for Unix-like systems
        venv_python = repo_root / ".venv" / "bin" / "python"

    if not venv_python.exists():
        raise FileNotFoundError(f"Virtual environment python not found: {venv_python}")

    # Build CLI command
    # Use: python -c "from launch.cli import main; main()" run --config <config>
    cmd = [
        str(venv_python),
        "-c",
        "from launch.cli import main; main()",
        "run",
        "--config",
        str(config_path)
    ]

    started_at = datetime.datetime.now(datetime.UTC)

    # Execute and capture output
    result = subprocess.run(
        cmd,
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

    finished_at = datetime.datetime.now(datetime.UTC)

    # Parse output to find run_dir
    run_dir = None
    for line in result.stdout.split("\n") + result.stderr.split("\n"):
        if "run_dir" in line.lower() or "output directory" in line.lower():
            # Try to extract path
            parts = line.split()
            for part in parts:
                if "runs/" in part or "runs\\" in part:
                    run_dir = part.strip("'\"")
                    break
            if run_dir:
                break

    # If run_dir not found in output, search for newest runs/<product_slug>_* directory
    if not run_dir:
        runs_dir = repo_root / "runs"
        if runs_dir.exists():
            # Find newest directory matching pattern (created after start time)
            candidates = []
            for entry in runs_dir.iterdir():
                if entry.is_dir() and not entry.name.startswith("."):
                    # Check if created after we started
                    mtime = datetime.datetime.fromtimestamp(entry.stat().st_mtime, tz=datetime.UTC)
                    if mtime >= started_at:
                        candidates.append((mtime, entry))

            if candidates:
                # Sort by modification time (newest first)
                candidates.sort(reverse=True)
                run_dir = str(candidates[0][1])

    return {
        "exit_code": result.returncode,
        "run_dir": run_dir,
        "started_at_utc": started_at.isoformat() + "Z",
        "finished_at_utc": finished_at.isoformat() + "Z",
        "stdout": result.stdout,
        "stderr": result.stderr
    }


def collect_artifacts(repo_root: Path, run_dir: Optional[str]) -> Dict[str, Any]:
    """
    Collect artifact paths and checksums from run directory.

    Args:
        repo_root: Repository root path
        run_dir: Run directory path (relative or absolute)

    Returns:
        Dictionary with artifact_paths and sha256 checksums
    """
    if not run_dir:
        return {"artifact_paths": {}, "checksums": {}}

    run_path = Path(run_dir)
    if not run_path.is_absolute():
        run_path = repo_root / run_path

    artifacts = {}
    checksums = {}

    # Look for known artifacts
    artifact_names = ["page_plan.json", "validation_report.json"]

    # Check in artifacts/ subdirectory
    artifacts_dir = run_path / "artifacts"
    if artifacts_dir.exists():
        for artifact_name in artifact_names:
            artifact_path = artifacts_dir / artifact_name
            if artifact_path.exists():
                rel_path = str(artifact_path.relative_to(repo_root))
                artifacts[artifact_name.replace(".json", "")] = rel_path
                checksums[artifact_name] = compute_sha256(artifact_path)

    return {
        "artifact_paths": artifacts,
        "checksums": checksums
    }


def run_pilot(
    pilot_id: str,
    dry_run: bool = False,
    output_path: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Run a pilot with optional dry-run mode.

    Args:
        pilot_id: Pilot identifier
        dry_run: If True, only validate config without execution
        output_path: Optional path to write JSON report

    Returns:
        Report dictionary
    """
    repo_root = get_repo_root()

    # Validate pilot exists
    pilots = enumerate_pilots(repo_root)
    if pilot_id not in pilots:
        raise ValueError(
            f"Pilot '{pilot_id}' not found. Available pilots: {', '.join(pilots)}"
        )

    config_path = repo_root / "specs" / "pilots" / pilot_id / "run_config.pinned.yaml"

    # Validate configuration
    try:
        config = validate_pilot_config(repo_root, pilot_id)
        validation_passed = True
        validation_error = None
    except Exception as e:
        validation_passed = False
        validation_error = str(e)
        config = None

    report = {
        "pilot_id": pilot_id,
        "config_path": str(config_path.relative_to(repo_root)),
        "dry_run": dry_run,
        "validation_passed": validation_passed,
        "validation_error": validation_error
    }

    if not validation_passed:
        if output_path:
            write_report(report, output_path)
        return report

    # If dry-run, stop here
    if dry_run:
        report["message"] = "Dry-run: validation passed, no execution performed"
        if output_path:
            write_report(report, output_path)
        return report

    # Execute pilot
    try:
        exec_result = execute_pilot_cli(repo_root, config_path)
        report.update(exec_result)

        # Collect artifacts
        artifacts_info = collect_artifacts(repo_root, exec_result.get("run_dir"))
        report.update(artifacts_info)

    except Exception as e:
        report["execution_error"] = str(e)

    # Write report if output path provided
    if output_path:
        write_report(report, output_path)

    return report


def write_report(report: Dict[str, Any], output_path: Path) -> None:
    """Write deterministic JSON report (sorted keys, compact)."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(
            report,
            f,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            indent=None
        )


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="TC-520: Run a pilot with deterministic enumeration and reporting"
    )
    parser.add_argument(
        "--pilot",
        required=True,
        help="Pilot ID to run (e.g., pilot-aspose-3d-foss-python)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate config only, no execution"
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Path to write JSON report (optional)"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available pilots and exit"
    )

    args = parser.parse_args()

    # Handle --list
    if args.list:
        repo_root = get_repo_root()
        pilots = enumerate_pilots(repo_root)
        print("Available pilots:")
        for pilot_id in pilots:
            print(f"  - {pilot_id}")
        return 0

    # Run pilot
    try:
        report = run_pilot(
            pilot_id=args.pilot,
            dry_run=args.dry_run,
            output_path=args.output
        )

        # Print summary
        print(f"Pilot: {report['pilot_id']}")
        print(f"Validation: {'PASS' if report['validation_passed'] else 'FAIL'}")

        if not report['validation_passed']:
            print(f"Error: {report['validation_error']}")
            return 1

        if args.dry_run:
            print("Mode: DRY-RUN (validation only)")
            return 0

        if "exit_code" in report:
            print(f"Exit code: {report['exit_code']}")
            print(f"Run dir: {report.get('run_dir', 'N/A')}")

            if report.get("artifact_paths"):
                print("Artifacts:")
                for name, path in sorted(report["artifact_paths"].items()):
                    checksum = report["checksums"].get(f"{name}.json", "N/A")
                    print(f"  {name}: {path} (SHA256: {checksum[:16]}...)")

            return report["exit_code"]

        if "execution_error" in report:
            print(f"Execution error: {report['execution_error']}")
            return 1

        return 0

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
