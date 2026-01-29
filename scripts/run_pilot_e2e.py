#!/usr/bin/env python3
"""
TC-522: Pilot E2E CLI execution and determinism verification.

Usage:
    python scripts/run_pilot_e2e.py --pilot <pilot_id> --output <path>

Features:
- Executes pilot twice (two consecutive runs)
- Compares actual vs expected artifacts (JSON semantic equality + SHA256)
- Verifies determinism (run1 vs run2 artifact checksums must match)
- Produces comprehensive report with pass/fail per check
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Import from run_pilot.py
sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_pilot import get_repo_root, run_pilot


def canonical_json_hash(data: Any) -> str:
    """Compute SHA256 of canonical JSON representation."""
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def load_json_file(file_path: Path) -> Optional[Dict[str, Any]]:
    """Load JSON file, return None if missing or invalid."""
    if not file_path.exists():
        return None

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return None


def compare_json_semantic(actual: Any, expected: Any) -> tuple[bool, Optional[str]]:
    """
    Compare two JSON objects for semantic equality.

    Returns:
        (is_equal, difference_description)
    """
    if actual == expected:
        return (True, None)

    # Compute difference summary
    if type(actual) != type(expected):
        return (False, f"Type mismatch: {type(actual).__name__} vs {type(expected).__name__}")

    if isinstance(actual, dict):
        actual_keys = set(actual.keys())
        expected_keys = set(expected.keys())

        missing = expected_keys - actual_keys
        extra = actual_keys - expected_keys

        if missing or extra:
            diff = []
            if missing:
                diff.append(f"Missing keys: {sorted(missing)}")
            if extra:
                diff.append(f"Extra keys: {sorted(extra)}")
            return (False, "; ".join(diff))

        # Check values
        for key in actual_keys:
            is_equal, diff = compare_json_semantic(actual[key], expected[key])
            if not is_equal:
                return (False, f"Key '{key}': {diff}")

    elif isinstance(actual, list):
        if len(actual) != len(expected):
            return (False, f"List length mismatch: {len(actual)} vs {len(expected)}")

        for i, (a, e) in enumerate(zip(actual, expected)):
            is_equal, diff = compare_json_semantic(a, e)
            if not is_equal:
                return (False, f"Index {i}: {diff}")

    else:
        return (False, f"Value mismatch: {actual!r} vs {expected!r}")

    return (True, None)


def run_pilot_e2e(pilot_id: str, output_path: Path) -> Dict[str, Any]:
    """
    Run pilot E2E with determinism verification.

    Executes pilot twice, compares artifacts against expected, verifies determinism.

    Args:
        pilot_id: Pilot identifier
        output_path: Path to write JSON report

    Returns:
        Report dictionary
    """
    repo_root = get_repo_root()
    pilot_dir = repo_root / "specs" / "pilots" / pilot_id

    # Check pilot exists
    if not pilot_dir.exists():
        return {
            "pilot_id": pilot_id,
            "error": f"Pilot directory not found: {pilot_dir}",
            "status": "ERROR"
        }

    report = {
        "pilot_id": pilot_id,
        "runs": {},
        "comparisons": {},
        "determinism": {},
        "status": "UNKNOWN"
    }

    # Expected artifacts
    expected_files = {
        "page_plan": pilot_dir / "expected_page_plan.json",
        "validation_report": pilot_dir / "expected_validation_report.json"
    }

    expected_data = {}
    for artifact_name, expected_path in expected_files.items():
        data = load_json_file(expected_path)
        if data:
            expected_data[artifact_name] = {
                "path": str(expected_path.relative_to(repo_root)),
                "data": data,
                "sha256": canonical_json_hash(data)
            }
        else:
            expected_data[artifact_name] = {
                "path": str(expected_path.relative_to(repo_root)),
                "missing": True
            }

    # Run pilot twice
    run_results = []
    for run_num in [1, 2]:
        print(f"\n{'='*70}")
        print(f"Run {run_num}/2: {pilot_id}")
        print('='*70)

        # Execute pilot
        temp_output = repo_root / "artifacts" / f"pilot_e2e_{pilot_id}_run{run_num}.json"
        try:
            run_report = run_pilot(pilot_id=pilot_id, dry_run=False, output_path=temp_output)
        except Exception as e:
            run_report = {"error": str(e)}

        # Extract artifacts
        artifacts = {}
        if "run_dir" in run_report and run_report["run_dir"]:
            run_dir = Path(run_report["run_dir"])
            if not run_dir.is_absolute():
                run_dir = repo_root / run_dir

            artifacts_dir = run_dir / "artifacts"
            if artifacts_dir.exists():
                for artifact_name in ["page_plan", "validation_report"]:
                    artifact_file = artifacts_dir / f"{artifact_name}.json"
                    if artifact_file.exists():
                        data = load_json_file(artifact_file)
                        if data:
                            artifacts[artifact_name] = {
                                "path": str(artifact_file.relative_to(repo_root)),
                                "data": data,
                                "sha256": canonical_json_hash(data)
                            }

        run_result = {
            "run_num": run_num,
            "exit_code": run_report.get("exit_code"),
            "run_dir": run_report.get("run_dir"),
            "artifacts": artifacts,
            "error": run_report.get("error")
        }

        run_results.append(run_result)
        report["runs"][f"run{run_num}"] = {
            "exit_code": run_result["exit_code"],
            "run_dir": run_result["run_dir"],
            "artifact_paths": {k: v["path"] for k, v in artifacts.items()},
            "artifact_checksums": {k: v["sha256"] for k, v in artifacts.items()}
        }

        if run_result.get("error"):
            print(f"  ERROR: {run_result['error']}")
        elif run_result["exit_code"] == 0:
            print(f"  ✓ Pilot completed successfully")
            print(f"  Run dir: {run_result['run_dir']}")
            print(f"  Artifacts: {len(artifacts)}")
        else:
            print(f"  ✗ Pilot failed with exit code: {run_result['exit_code']}")

    # Compare actual vs expected (using run1)
    print(f"\n{'='*70}")
    print("Expected vs Actual Comparison (Run 1)")
    print('='*70)

    run1_artifacts = run_results[0]["artifacts"]

    for artifact_name in ["page_plan", "validation_report"]:
        expected_info = expected_data.get(artifact_name, {})
        actual_info = run1_artifacts.get(artifact_name, {})

        comparison = {
            "artifact": artifact_name,
            "expected_path": expected_info.get("path"),
            "actual_path": actual_info.get("path"),
            "expected_missing": expected_info.get("missing", False),
            "actual_missing": len(actual_info) == 0
        }

        if expected_info.get("missing"):
            comparison["status"] = "SKIP"
            comparison["reason"] = "Expected artifact not available (placeholder)"
        elif len(actual_info) == 0:
            comparison["status"] = "FAIL"
            comparison["reason"] = "Actual artifact not produced"
        else:
            # Compare semantically
            is_equal, diff = compare_json_semantic(
                actual_info["data"],
                expected_info["data"]
            )

            comparison["semantic_match"] = is_equal
            comparison["expected_sha256"] = expected_info["sha256"]
            comparison["actual_sha256"] = actual_info["sha256"]
            comparison["sha256_match"] = expected_info["sha256"] == actual_info["sha256"]

            if is_equal:
                comparison["status"] = "PASS"
            else:
                comparison["status"] = "FAIL"
                comparison["difference"] = diff

        report["comparisons"][artifact_name] = comparison

        # Print result
        status = comparison["status"]
        if status == "PASS":
            print(f"  ✓ {artifact_name}: MATCH")
        elif status == "SKIP":
            print(f"  ⊘ {artifact_name}: SKIPPED ({comparison['reason']})")
        else:
            print(f"  ✗ {artifact_name}: {comparison.get('reason', 'MISMATCH')}")
            if "difference" in comparison:
                print(f"    Diff: {comparison['difference']}")

    # Determinism check (run1 vs run2)
    print(f"\n{'='*70}")
    print("Determinism Verification (Run 1 vs Run 2)")
    print('='*70)

    run1_artifacts = run_results[0]["artifacts"]
    run2_artifacts = run_results[1]["artifacts"]

    for artifact_name in ["page_plan", "validation_report"]:
        run1_info = run1_artifacts.get(artifact_name, {})
        run2_info = run2_artifacts.get(artifact_name, {})

        determinism = {
            "artifact": artifact_name,
            "run1_present": len(run1_info) > 0,
            "run2_present": len(run2_info) > 0
        }

        if len(run1_info) == 0 or len(run2_info) == 0:
            determinism["status"] = "FAIL"
            determinism["reason"] = "Artifact missing in one or both runs"
        else:
            run1_sha = run1_info["sha256"]
            run2_sha = run2_info["sha256"]

            determinism["run1_sha256"] = run1_sha
            determinism["run2_sha256"] = run2_sha
            determinism["match"] = run1_sha == run2_sha

            if run1_sha == run2_sha:
                determinism["status"] = "PASS"
            else:
                determinism["status"] = "FAIL"
                determinism["reason"] = "SHA256 mismatch between runs"

        report["determinism"][artifact_name] = determinism

        # Print result
        status = determinism["status"]
        if status == "PASS":
            print(f"  ✓ {artifact_name}: DETERMINISTIC")
            print(f"    SHA256: {determinism['run1_sha256'][:16]}...")
        else:
            print(f"  ✗ {artifact_name}: {determinism.get('reason', 'NON-DETERMINISTIC')}")
            if "run1_sha256" in determinism:
                print(f"    Run 1: {determinism['run1_sha256'][:16]}...")
                print(f"    Run 2: {determinism['run2_sha256'][:16]}...")

    # Overall status
    comparison_pass = all(
        c["status"] in ["PASS", "SKIP"]
        for c in report["comparisons"].values()
    )
    determinism_pass = all(
        d["status"] == "PASS"
        for d in report["determinism"].values()
    )

    if comparison_pass and determinism_pass:
        report["status"] = "PASS"
    elif run_results[0].get("error") or run_results[1].get("error"):
        report["status"] = "ERROR"
    else:
        report["status"] = "FAIL"

    # Write report
    write_report(report, output_path)

    # Print summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print('='*70)
    print(f"Status: {report['status']}")
    print(f"Comparisons: {sum(1 for c in report['comparisons'].values() if c['status'] == 'PASS')}/{len(report['comparisons'])} passed")
    print(f"Determinism: {sum(1 for d in report['determinism'].values() if d['status'] == 'PASS')}/{len(report['determinism'])} passed")
    print(f"\nReport written to: {output_path}")

    return report


def write_report(report: Dict[str, Any], output_path: Path) -> None:
    """Write deterministic JSON report."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(
            report,
            f,
            sort_keys=True,
            indent=2,
            ensure_ascii=False
        )


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="TC-522: Pilot E2E CLI execution and determinism verification"
    )
    parser.add_argument(
        "--pilot",
        required=True,
        help="Pilot ID to run (e.g., pilot-aspose-3d-foss-python)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Path to write JSON report"
    )

    args = parser.parse_args()

    try:
        report = run_pilot_e2e(pilot_id=args.pilot, output_path=args.output)

        # Exit with appropriate code
        if report["status"] == "PASS":
            return 0
        elif report["status"] == "ERROR":
            return 2
        else:
            return 1

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
