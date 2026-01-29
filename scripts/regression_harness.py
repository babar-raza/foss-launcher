#!/usr/bin/env python3
"""
TC-520: Regression harness for pilot testing.

Usage:
    python scripts/regression_harness.py --list
    python scripts/regression_harness.py --run-all [--output <path>]
    python scripts/regression_harness.py --determinism [--output <path>]

Modes:
- list: Enumerate and print all pilot IDs (sorted)
- run-all: Execute each pilot once
- determinism: Execute each pilot twice and compare artifact checksums
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

# Import from run_pilot.py
sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_pilot import enumerate_pilots, get_repo_root, run_pilot


def list_pilots() -> List[str]:
    """List all available pilots in sorted order."""
    repo_root = get_repo_root()
    return enumerate_pilots(repo_root)


def run_all_pilots(output_path: Path | None = None) -> Dict[str, Any]:
    """
    Run all pilots once and collect results.

    Args:
        output_path: Optional path to write summary JSON

    Returns:
        Summary dictionary with results per pilot
    """
    repo_root = get_repo_root()
    pilots = enumerate_pilots(repo_root)

    summary = {
        "mode": "run-all",
        "total_pilots": len(pilots),
        "pilots": {},
        "passed": 0,
        "failed": 0
    }

    for pilot_id in pilots:
        print(f"\n{'='*70}")
        print(f"Running pilot: {pilot_id}")
        print('='*70)

        try:
            # Create temporary output for this pilot
            temp_output = repo_root / "artifacts" / f"run_all_{pilot_id}.json"
            report = run_pilot(pilot_id=pilot_id, dry_run=False, output_path=temp_output)

            success = report.get("exit_code") == 0 if "exit_code" in report else False

            summary["pilots"][pilot_id] = {
                "validation_passed": report.get("validation_passed", False),
                "exit_code": report.get("exit_code"),
                "run_dir": report.get("run_dir"),
                "artifacts": report.get("artifact_paths", {}),
                "checksums": report.get("checksums", {}),
                "success": success
            }

            if success:
                summary["passed"] += 1
                print(f"✓ {pilot_id}: PASSED")
            else:
                summary["failed"] += 1
                print(f"✗ {pilot_id}: FAILED (exit code: {report.get('exit_code', 'N/A')})")

        except Exception as e:
            summary["pilots"][pilot_id] = {
                "validation_passed": False,
                "error": str(e),
                "success": False
            }
            summary["failed"] += 1
            print(f"✗ {pilot_id}: ERROR - {e}")

    # Print summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print('='*70)
    print(f"Total pilots: {summary['total_pilots']}")
    print(f"Passed: {summary['passed']}")
    print(f"Failed: {summary['failed']}")

    # Write output
    if output_path:
        write_summary(summary, output_path)
        print(f"\nFull report written to: {output_path}")

    return summary


def run_determinism_check(output_path: Path | None = None) -> Dict[str, Any]:
    """
    Run all pilots twice and compare artifact checksums for determinism.

    Args:
        output_path: Optional path to write summary JSON

    Returns:
        Summary dictionary with determinism check results
    """
    repo_root = get_repo_root()
    pilots = enumerate_pilots(repo_root)

    summary = {
        "mode": "determinism",
        "total_pilots": len(pilots),
        "pilots": {},
        "deterministic": 0,
        "non_deterministic": 0,
        "failed": 0
    }

    for pilot_id in pilots:
        print(f"\n{'='*70}")
        print(f"Determinism check for: {pilot_id}")
        print('='*70)

        pilot_result = {
            "run1": {},
            "run2": {},
            "deterministic": False,
            "mismatches": []
        }

        try:
            # Run 1
            print("  Run 1...")
            temp_output1 = repo_root / "artifacts" / f"determinism_{pilot_id}_run1.json"
            report1 = run_pilot(pilot_id=pilot_id, dry_run=False, output_path=temp_output1)

            pilot_result["run1"] = {
                "exit_code": report1.get("exit_code"),
                "run_dir": report1.get("run_dir"),
                "checksums": report1.get("checksums", {})
            }

            if report1.get("exit_code") != 0:
                print(f"  Run 1 failed with exit code: {report1.get('exit_code')}")
                summary["failed"] += 1
                summary["pilots"][pilot_id] = pilot_result
                continue

            # Run 2
            print("  Run 2...")
            temp_output2 = repo_root / "artifacts" / f"determinism_{pilot_id}_run2.json"
            report2 = run_pilot(pilot_id=pilot_id, dry_run=False, output_path=temp_output2)

            pilot_result["run2"] = {
                "exit_code": report2.get("exit_code"),
                "run_dir": report2.get("run_dir"),
                "checksums": report2.get("checksums", {})
            }

            if report2.get("exit_code") != 0:
                print(f"  Run 2 failed with exit code: {report2.get('exit_code')}")
                summary["failed"] += 1
                summary["pilots"][pilot_id] = pilot_result
                continue

            # Compare checksums
            checksums1 = report1.get("checksums", {})
            checksums2 = report2.get("checksums", {})

            all_artifacts = set(checksums1.keys()) | set(checksums2.keys())

            mismatches = []
            for artifact in sorted(all_artifacts):
                hash1 = checksums1.get(artifact)
                hash2 = checksums2.get(artifact)

                if hash1 != hash2:
                    mismatches.append({
                        "artifact": artifact,
                        "run1_sha256": hash1,
                        "run2_sha256": hash2
                    })

            pilot_result["mismatches"] = mismatches
            pilot_result["deterministic"] = len(mismatches) == 0

            if pilot_result["deterministic"]:
                summary["deterministic"] += 1
                print(f"  ✓ Deterministic: All artifacts match")
                for artifact, hash_val in sorted(checksums1.items()):
                    print(f"    {artifact}: {hash_val[:16]}...")
            else:
                summary["non_deterministic"] += 1
                print(f"  ✗ Non-deterministic: {len(mismatches)} mismatch(es)")
                for mismatch in mismatches:
                    print(f"    {mismatch['artifact']}:")
                    print(f"      Run 1: {mismatch['run1_sha256']}")
                    print(f"      Run 2: {mismatch['run2_sha256']}")

                # Store evidence (copy artifacts for analysis)
                store_determinism_evidence(
                    repo_root, pilot_id,
                    report1.get("run_dir"),
                    report2.get("run_dir"),
                    mismatches
                )

        except Exception as e:
            pilot_result["error"] = str(e)
            summary["failed"] += 1
            print(f"  ✗ ERROR: {e}")

        summary["pilots"][pilot_id] = pilot_result

    # Print summary
    print(f"\n{'='*70}")
    print("DETERMINISM SUMMARY")
    print('='*70)
    print(f"Total pilots: {summary['total_pilots']}")
    print(f"Deterministic: {summary['deterministic']}")
    print(f"Non-deterministic: {summary['non_deterministic']}")
    print(f"Failed: {summary['failed']}")

    # Write output
    if output_path:
        write_summary(summary, output_path)
        print(f"\nFull report written to: {output_path}")

    return summary


def store_determinism_evidence(
    repo_root: Path,
    pilot_id: str,
    run_dir1: str | None,
    run_dir2: str | None,
    mismatches: List[Dict[str, Any]]
) -> None:
    """
    Store evidence of non-deterministic artifacts.

    Creates copies of mismatched artifacts in a determinism evidence directory.
    """
    if not run_dir1 or not run_dir2:
        return

    evidence_dir = repo_root / "artifacts" / "determinism_evidence" / pilot_id
    evidence_dir.mkdir(parents=True, exist_ok=True)

    print(f"    Storing evidence in: {evidence_dir}")

    # Copy mismatched artifacts
    import shutil

    for mismatch in mismatches:
        artifact_name = mismatch["artifact"]

        # Find artifact in run directories
        run1_path = Path(run_dir1) / "artifacts" / artifact_name
        run2_path = Path(run_dir2) / "artifacts" / artifact_name

        if not run1_path.is_absolute():
            run1_path = repo_root / run1_path
        if not run2_path.is_absolute():
            run2_path = repo_root / run2_path

        # Copy with run suffix
        if run1_path.exists():
            dest1 = evidence_dir / f"{artifact_name}.run1"
            shutil.copy2(run1_path, dest1)

        if run2_path.exists():
            dest2 = evidence_dir / f"{artifact_name}.run2"
            shutil.copy2(run2_path, dest2)

    # Write diff summary
    diff_summary_path = evidence_dir / "diff_summary.json"
    with open(diff_summary_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "pilot_id": pilot_id,
                "run1_dir": str(run_dir1),
                "run2_dir": str(run_dir2),
                "mismatches": mismatches
            },
            f,
            sort_keys=True,
            indent=2
        )


def write_summary(summary: Dict[str, Any], output_path: Path) -> None:
    """Write deterministic JSON summary."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(
            summary,
            f,
            sort_keys=True,
            indent=2,
            ensure_ascii=False
        )


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="TC-520: Regression harness for pilot testing"
    )

    # Mode selection (mutually exclusive)
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--list",
        action="store_true",
        help="List all available pilots"
    )
    mode_group.add_argument(
        "--run-all",
        action="store_true",
        help="Run all pilots once"
    )
    mode_group.add_argument(
        "--determinism",
        action="store_true",
        help="Run all pilots twice and check determinism"
    )

    parser.add_argument(
        "--output",
        type=Path,
        help="Path to write summary JSON report (for run-all and determinism modes)"
    )

    args = parser.parse_args()

    try:
        if args.list:
            pilots = list_pilots()
            print("Available pilots (sorted):")
            for pilot_id in pilots:
                print(f"  - {pilot_id}")
            return 0

        elif args.run_all:
            summary = run_all_pilots(output_path=args.output)
            return 0 if summary["failed"] == 0 else 1

        elif args.determinism:
            summary = run_determinism_check(output_path=args.output)
            return 0 if summary["non_deterministic"] == 0 and summary["failed"] == 0 else 1

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
