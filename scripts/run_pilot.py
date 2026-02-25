#!/usr/bin/env python3
"""
TC-520 / TC-2503: Pilot runner with deterministic enumeration, CLI execution,
and phase-bounded mode.

Usage:
    python scripts/run_pilot.py --pilot <pilot_id> [--dry-run] [--output <path>]
    python scripts/run_pilot.py --pilot <pilot_id> --phase-start P3 --phase-end P5

Supports:
- Deterministic pilot enumeration (sorted)
- Dry-run mode: validate config only, no network/cloning
- Full execution: runs CLI and captures artifacts
- Deterministic JSON report with SHA256 checksums
- Phase-bounded execution with artifact verification (TC-2503)
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import shutil
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

    # Execute and capture output (2-hour hard ceiling to prevent infinite hangs)
    try:
        result = subprocess.run(
            cmd,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=7200,
        )
    except subprocess.TimeoutExpired as te:
        finished_at = datetime.datetime.now(datetime.UTC)
        return {
            "exit_code": -1,
            "run_dir": None,
            "started_at_utc": started_at.isoformat() + "Z",
            "finished_at_utc": finished_at.isoformat() + "Z",
            "stdout": te.stdout or "",
            "stderr": te.stderr or "",
            "timeout": True,
        }

    finished_at = datetime.datetime.now(datetime.UTC)

    # TC-2473: Prefer structured run_summary.json artifact over text parsing
    run_dir = None
    runs_dir = repo_root / "runs"
    if runs_dir.exists():
        summary_candidates = []
        for entry in runs_dir.iterdir():
            if entry.is_dir() and not entry.name.startswith("."):
                summary_path = entry / "artifacts" / "run_summary.json"
                if summary_path.exists():
                    mtime = datetime.datetime.fromtimestamp(entry.stat().st_mtime, tz=datetime.UTC)
                    if mtime >= started_at:
                        try:
                            with open(summary_path, encoding="utf-8") as f:
                                summary = json.load(f)
                            summary_candidates.append((mtime, str(entry), summary))
                        except Exception:
                            pass
        if summary_candidates:
            summary_candidates.sort(reverse=True)
            run_dir = summary_candidates[0][1]

    # Fallback: parse output to find run_dir (legacy text-based method)
    if not run_dir:
        for line in result.stdout.split("\n") + result.stderr.split("\n"):
            if "run_dir" in line.lower() or "output directory" in line.lower():
                parts = line.split()
                for part in parts:
                    if "runs/" in part or "runs\\" in part:
                        run_dir = part.strip("'\"")
                        if run_dir.lower().startswith("run_dir="):
                            run_dir = run_dir[8:]
                        break
                if run_dir:
                    break

    # Fallback 2: search for newest runs/ directory created after start time
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

    # TC-2473: Include run_summary if available
    report = {
        "exit_code": result.returncode,
        "run_dir": run_dir,
        "started_at_utc": started_at.isoformat() + "Z",
        "finished_at_utc": finished_at.isoformat() + "Z",
        "stdout": result.stdout,
        "stderr": result.stderr,
    }
    if run_dir:
        summary_path = Path(run_dir) / "artifacts" / "run_summary.json"
        if summary_path.exists():
            try:
                with open(summary_path, encoding="utf-8") as f:
                    report["run_summary"] = json.load(f)
            except Exception:
                pass
    return report


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
    output_path: Optional[Path] = None,
    export_content: Optional[Path] = None,
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

    # Export content_preview to user-specified directory
    if export_content and report.get("run_dir"):
        run_path = Path(report["run_dir"])
        if not run_path.is_absolute():
            run_path = repo_root / run_path
        content_preview = run_path / "content_preview"
        if content_preview.exists():
            export_content.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(content_preview, export_content, dirs_exist_ok=True)
            report["exported_content"] = str(export_content)

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


def _resume_pilot(pilot_id: str, from_worker: str) -> int:
    """Resume the most recent run for pilot_id from from_worker.

    Reads runs/manifest.jsonl to find the most recent run directory for this
    pilot, then calls `launch resume --run-dir <dir> --from-worker <alias>`.

    Returns subprocess exit code.

    Spec reference: specs/43_resumable_pipeline.md §run_pilot.py Integration (TC-2399)
    """
    repo_root = get_repo_root()
    manifest_path = repo_root / "runs" / "manifest.jsonl"

    if not manifest_path.exists():
        print(
            f"ERROR: runs/manifest.jsonl not found. "
            f"Run a full pilot first before using --from-worker.",
            file=sys.stderr,
        )
        return 1

    # Find the most recent run for this pilot (last matching line in manifest)
    matching_run_dir: Optional[str] = None
    with open(manifest_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("pilot") == pilot_id:
                matching_run_dir = entry.get("output_dir")

    if not matching_run_dir:
        print(
            f"ERROR: No prior run found for pilot '{pilot_id}' in runs/manifest.jsonl. "
            f"Run a full pilot first before using --from-worker.",
            file=sys.stderr,
        )
        return 1

    run_dir_path = Path(matching_run_dir)
    if not run_dir_path.is_absolute():
        run_dir_path = repo_root / run_dir_path

    if not run_dir_path.exists():
        print(
            f"ERROR: Most recent run directory does not exist: {run_dir_path}",
            file=sys.stderr,
        )
        return 1

    print(f"Resuming pilot '{pilot_id}' from worker '{from_worker}'")
    print(f"Run directory: {run_dir_path}")

    venv_python = repo_root / ".venv" / "Scripts" / "python.exe"
    if not venv_python.exists():
        venv_python = repo_root / ".venv" / "bin" / "python"

    cmd = [
        str(venv_python),
        "-c",
        "from launch.cli import main; main()",
        "resume",
        "--run-dir",
        str(run_dir_path),
        "--from-worker",
        from_worker,
    ]

    try:
        result = subprocess.run(cmd, cwd=str(repo_root), timeout=7200)
        return result.returncode
    except subprocess.TimeoutExpired:
        print("ERROR: Resume timed out after 2 hours.", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


# ---------------------------------------------------------------------------
# TC-2503: Phase-bounded execution
# ---------------------------------------------------------------------------

#: Valid phase identifiers (mirrors phase_executor._PHASE_ORDER).
_VALID_PHASE_IDS = ("P1", "P2", "P3", "P4", "P5", "P6")

#: Mapping of phase identifiers to the entry worker alias for subprocess resume.
_PHASE_ENTRY_WORKERS: Dict[str, str] = {
    "P1": "W1",
    "P2": "W3",
    "P3": "W5",
    "P4": "W7",
    "P5": "W9",
    "P6": "W11",
}


def _find_latest_run_dir(pilot_id: str) -> Optional[Path]:
    """Find the most recent run directory for *pilot_id* from manifest.jsonl.

    Returns:
        Absolute Path to the run directory, or None if not found.
    """
    repo_root = get_repo_root()
    manifest_path = repo_root / "runs" / "manifest.jsonl"

    if not manifest_path.exists():
        return None

    matching_run_dir: Optional[str] = None
    with open(manifest_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("pilot") == pilot_id:
                matching_run_dir = entry.get("output_dir")

    if not matching_run_dir:
        return None

    run_dir_path = Path(matching_run_dir)
    if not run_dir_path.is_absolute():
        run_dir_path = repo_root / run_dir_path

    if not run_dir_path.exists():
        return None

    return run_dir_path


def _run_pilot_phased(
    pilot_id: str,
    phase_start: str,
    phase_end: str,
) -> int:
    """Execute a pilot in phase-bounded mode with artifact verification.

    For ``--phase-start P1`` a fresh full-pipeline run is triggered (the
    pipeline executes W1 through W11 end-to-end).  For later phases a
    ``launch resume`` subprocess is dispatched from the phase's entry worker.

    After execution, ``verify_phase_range()`` checks that the artifacts
    expected for *phase_start* through *phase_end* are present and valid.

    Args:
        pilot_id: Pilot identifier (e.g. ``pilot-aspose-3d-foss-python``).
        phase_start: First phase to execute (``P1`` .. ``P6``).
        phase_end: Last phase to execute (``P1`` .. ``P6``).

    Returns:
        Process exit code (0 = all OK, 1 = error).

    TC-2503
    """
    repo_root = get_repo_root()
    start_idx = _VALID_PHASE_IDS.index(phase_start)
    end_idx = _VALID_PHASE_IDS.index(phase_end)

    if end_idx < start_idx:
        print(
            f"ERROR: --phase-end {phase_end} precedes --phase-start {phase_start}. "
            f"Phase order: {', '.join(_VALID_PHASE_IDS)}",
            file=sys.stderr,
        )
        return 1

    print(f"Phase mode: {phase_start} -> {phase_end} for pilot '{pilot_id}'")

    # ------------------------------------------------------------------
    # 1. Execute: either fresh run (P1) or resume from entry worker
    # ------------------------------------------------------------------
    run_dir: Optional[Path] = None
    exit_code = 0

    if phase_start == "P1":
        # Fresh full-pipeline run via subprocess (same as normal execution)
        config_path = repo_root / "specs" / "pilots" / pilot_id / "run_config.pinned.yaml"
        exec_result = execute_pilot_cli(repo_root, config_path)
        exit_code = exec_result.get("exit_code", 1)
        raw_dir = exec_result.get("run_dir")
        if raw_dir:
            run_dir = Path(raw_dir)
            if not run_dir.is_absolute():
                run_dir = repo_root / run_dir
        print(f"Pipeline exit code: {exit_code}")
        if run_dir:
            print(f"Run directory: {run_dir}")
    else:
        # Resume from the entry worker of the start phase
        entry_worker = _PHASE_ENTRY_WORKERS[phase_start]
        run_dir = _find_latest_run_dir(pilot_id)

        if not run_dir:
            print(
                f"ERROR: No prior run found for pilot '{pilot_id}'. "
                f"Run a full pilot (--phase-start P1) first.",
                file=sys.stderr,
            )
            return 1

        print(f"Resuming from {entry_worker} (phase {phase_start})")
        print(f"Run directory: {run_dir}")
        exit_code = _resume_pilot(pilot_id, entry_worker)

    # ------------------------------------------------------------------
    # 2. Verify phase artifacts
    # ------------------------------------------------------------------
    if run_dir and run_dir.exists():
        print()
        print("=" * 60)
        print("Phase Artifact Verification")
        print("=" * 60)

        # Import verifier (lazy — keeps top-level import clean)
        sys.path.insert(0, str(repo_root / "src"))
        from launch.orchestrator.phase_verifier import verify_phase_range

        try:
            verifications = verify_phase_range(
                run_dir, phase_start, phase_end, repo_root=repo_root
            )
        except Exception as exc:
            print(f"ERROR: Verification failed: {exc}", file=sys.stderr)
            return 1

        _print_phase_summary(verifications)

        # If any phase verification failed, override exit code
        if any(not v.ok for v in verifications):
            exit_code = max(exit_code, 1)
    else:
        print("WARNING: No run directory available -- skipping verification.")

    return exit_code


def _print_phase_summary(verifications: list) -> None:
    """Print a human-readable table of phase verification results.

    Args:
        verifications: List of ``PhaseVerificationResult`` objects from
            ``verify_phase_range()``.
    """
    for v in verifications:
        status = "PASS" if v.ok else "FAIL"
        check_count = len(v.checks)
        print(f"  {v.phase_id}: {status}  ({check_count} checks)")

        if v.missing:
            for m in v.missing:
                print(f"    MISSING: {m}")
        if v.schema_errors:
            for s in v.schema_errors:
                print(f"    SCHEMA_ERROR: {s}")

    # Summary line
    total = len(verifications)
    passed = sum(1 for v in verifications if v.ok)
    print()
    if passed == total:
        print(f"All {total} phases verified OK.")
    else:
        print(f"{passed}/{total} phases verified OK. {total - passed} failed.")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="TC-520 / TC-2503: Run a pilot with deterministic enumeration, reporting, and phase mode"
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
        "--export-content",
        type=Path,
        help="Copy content_preview tree to this directory after run"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available pilots and exit"
    )
    parser.add_argument(
        "--from-worker",
        default=None,
        metavar="ALIAS",
        help=(
            "Resume from a specific worker using the most recent run for this pilot. "
            "Valid aliases: W1-W11 or full node names (e.g. W5, draft_sections). "
            "Reads runs/manifest.jsonl to find the most recent run for --pilot. "
            "Mutually exclusive with --phase-start / --phase-end. "
            "Spec: specs/43_resumable_pipeline.md (TC-2399)"
        ),
    )
    parser.add_argument(
        "--phase-start",
        default=None,
        metavar="PHASE",
        help=(
            "First phase to execute in phase-bounded mode (P1-P6). "
            "Defaults to P1 when --phase-end is provided. "
            "Mutually exclusive with --from-worker. "
            "TC-2503"
        ),
    )
    parser.add_argument(
        "--phase-end",
        default=None,
        metavar="PHASE",
        help=(
            "Last phase to execute in phase-bounded mode (P1-P6). "
            "Defaults to P6 when --phase-start is provided. "
            "Mutually exclusive with --from-worker. "
            "TC-2503"
        ),
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

    # -------------------------------------------------------------------
    # TC-2503: Validate mutual exclusivity and phase arguments
    # -------------------------------------------------------------------
    phase_mode = args.phase_start is not None or args.phase_end is not None

    if phase_mode and args.from_worker:
        print(
            "ERROR: --phase-start / --phase-end cannot be combined with --from-worker.",
            file=sys.stderr,
        )
        return 1

    if phase_mode:
        # Apply defaults: --phase-start defaults to P1, --phase-end defaults to P6
        phase_start = args.phase_start or "P1"
        phase_end = args.phase_end or "P6"

        # Validate identifiers
        if phase_start not in _VALID_PHASE_IDS:
            print(
                f"ERROR: Invalid --phase-start '{phase_start}'. "
                f"Valid phases: {', '.join(_VALID_PHASE_IDS)}",
                file=sys.stderr,
            )
            return 1
        if phase_end not in _VALID_PHASE_IDS:
            print(
                f"ERROR: Invalid --phase-end '{phase_end}'. "
                f"Valid phases: {', '.join(_VALID_PHASE_IDS)}",
                file=sys.stderr,
            )
            return 1

        return _run_pilot_phased(args.pilot, phase_start, phase_end)

    # TC-2399: Handle --from-worker (resume mode)
    if args.from_worker:
        return _resume_pilot(args.pilot, args.from_worker)

    # Run pilot
    try:
        report = run_pilot(
            pilot_id=args.pilot,
            dry_run=args.dry_run,
            output_path=args.output,
            export_content=args.export_content,
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

            if report.get("exported_content"):
                print(f"Content exported to: {report['exported_content']}")

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
