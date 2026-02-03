#!/usr/bin/env python3
"""
TC-903: VFV (Verify-First-Validate) Harness with strict 2-run determinism.

Usage:
    python scripts/run_pilot_vfv.py --pilot <pilot_id> --output <path> [--goldenize] [--allow_placeholders]

Features:
- Preflight: Reject placeholder all-zero SHAs (unless --allow_placeholders)
- Run pilot twice (deterministic execution)
- Verify BOTH artifacts exist: page_plan.json, validation_report.json
- Compute canonical SHA256 for BOTH artifacts in BOTH runs
- Extract page counts per subdomain from page_plan.json
- Determinism check: run1 vs run2 hashes must match for BOTH artifacts
- Goldenize only if: PASS + --goldenize flag + no placeholders
- Comprehensive JSON report with all checks

Exit codes:
    0 - PASS (determinism verified)
    1 - FAIL (non-deterministic or missing artifacts)
    2 - ERROR (execution error or preflight failure)
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Import from run_pilot.py
sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_pilot import get_repo_root, run_pilot


def canonical_json_hash(data: Any) -> str:
    """Compute SHA256 of canonical JSON representation (sorted keys, no whitespace)."""
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


def is_placeholder_sha(sha: str) -> bool:
    """Check if SHA is a placeholder (all zeros)."""
    return bool(re.match(r"^0+$", sha))


def preflight_check(repo_root: Path, pilot_id: str, allow_placeholders: bool) -> Dict[str, Any]:
    """
    Perform preflight checks on pilot config.

    Args:
        repo_root: Repository root path
        pilot_id: Pilot identifier
        allow_placeholders: If True, allow placeholder SHAs (for dev/testing only)

    Returns:
        Preflight report dict with 'passed' boolean
    """
    config_path = repo_root / "specs" / "pilots" / pilot_id / "run_config.pinned.yaml"

    if not config_path.exists():
        return {
            "passed": False,
            "error": f"Config not found: {config_path}"
        }

    # Load config
    sys.path.insert(0, str(repo_root / "src"))
    try:
        from launch.io.run_config import load_and_validate_run_config
        config = load_and_validate_run_config(repo_root, config_path)
    except Exception as e:
        return {
            "passed": False,
            "error": f"Config validation failed: {e}"
        }

    # Extract repo URLs and SHAs
    repo_urls = {}
    pinned_shas = {}
    placeholders_detected = False

    # Check github_repo_url and github_ref
    if "github_repo_url" in config:
        repo_urls["github_repo"] = config["github_repo_url"]
    if "github_ref" in config:
        sha = config["github_ref"]
        pinned_shas["github_repo"] = sha
        if is_placeholder_sha(sha):
            placeholders_detected = True

    # Check site_repo_url and site_ref
    if "site_repo_url" in config:
        repo_urls["site_repo"] = config["site_repo_url"]
    if "site_ref" in config:
        sha = config["site_ref"]
        pinned_shas["site_repo"] = sha
        if is_placeholder_sha(sha):
            placeholders_detected = True

    # Check workflows_repo_url and workflows_ref (optional)
    if "workflows_repo_url" in config:
        repo_urls["workflows_repo"] = config["workflows_repo_url"]
    if "workflows_ref" in config:
        sha = config["workflows_ref"]
        pinned_shas["workflows_repo"] = sha
        if is_placeholder_sha(sha):
            placeholders_detected = True

    # Print repo URLs and SHAs for transparency
    print("\n" + "="*70)
    print("PREFLIGHT CHECK")
    print("="*70)
    print(f"Pilot: {pilot_id}")
    print(f"\nRepo URLs:")
    for key, url in sorted(repo_urls.items()):
        print(f"  {key}: {url}")

    print(f"\nPinned SHAs:")
    for key, sha in sorted(pinned_shas.items()):
        placeholder_marker = " [PLACEHOLDER]" if is_placeholder_sha(sha) else ""
        print(f"  {key}: {sha}{placeholder_marker}")

    # Check for placeholders
    if placeholders_detected:
        print(f"\nWARNING: Placeholder SHAs detected!")
        if not allow_placeholders:
            return {
                "passed": False,
                "repo_urls": repo_urls,
                "pinned_shas": pinned_shas,
                "placeholders_detected": True,
                "error": "Placeholder SHAs detected. Use --allow_placeholders to bypass (dev/testing only)."
            }
        else:
            print("  Proceeding with --allow_placeholders flag (DEV/TESTING ONLY)")

    print("\nPreflight: PASS")

    return {
        "passed": True,
        "repo_urls": repo_urls,
        "pinned_shas": pinned_shas,
        "placeholders_detected": placeholders_detected
    }


def extract_page_counts(page_plan_data: Dict[str, Any]) -> Dict[str, int]:
    """
    Extract page counts per subdomain from page_plan.json.

    Args:
        page_plan_data: Loaded page_plan.json data

    Returns:
        Dict mapping subdomain to page count
    """
    try:
        pages = page_plan_data.get("pages", [])
        counts = {}

        for page in pages:
            subdomain = page.get("subdomain", "unknown")
            counts[subdomain] = counts.get(subdomain, 0) + 1

        return counts
    except Exception as e:
        # Log warning but don't fail (observability, not critical)
        print(f"  WARNING: Could not extract page counts: {e}")
        return {}


def goldenize(
    repo_root: Path,
    pilot_id: str,
    run1_artifacts: Dict[str, Any],
    page_counts: Dict[str, int]
) -> Dict[str, Any]:
    """
    Goldenize artifacts to specs/pilots/<pilot>/ directory.

    Args:
        repo_root: Repository root path
        pilot_id: Pilot identifier
        run1_artifacts: Artifacts from run1 (with data and sha256)
        page_counts: Page counts per subdomain

    Returns:
        Goldenization report dict
    """
    pilot_dir = repo_root / "specs" / "pilots" / pilot_id

    # Get current git commit SHA
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=True
        )
        git_commit = result.stdout.strip()
    except Exception:
        git_commit = "unknown"

    timestamp_utc = datetime.datetime.now(datetime.UTC).isoformat() + "Z"

    artifacts_written = []

    # Copy page_plan.json
    if "page_plan" in run1_artifacts:
        expected_path = pilot_dir / "expected_page_plan.json"
        with open(expected_path, "w", encoding="utf-8") as f:
            json.dump(
                run1_artifacts["page_plan"]["data"],
                f,
                sort_keys=True,
                indent=2,
                ensure_ascii=False
            )
        artifacts_written.append(str(expected_path.relative_to(repo_root)))

    # Copy validation_report.json
    if "validation_report" in run1_artifacts:
        expected_path = pilot_dir / "expected_validation_report.json"
        with open(expected_path, "w", encoding="utf-8") as f:
            json.dump(
                run1_artifacts["validation_report"]["data"],
                f,
                sort_keys=True,
                indent=2,
                ensure_ascii=False
            )
        artifacts_written.append(str(expected_path.relative_to(repo_root)))

    # Update notes.md
    notes_path = pilot_dir / "notes.md"
    notes_content = ""

    if notes_path.exists():
        with open(notes_path, "r", encoding="utf-8") as f:
            notes_content = f.read()

    # Append goldenization entry
    entry = f"""
## Goldenization Record

**Timestamp**: {timestamp_utc}
**Git Commit**: {git_commit}

**Artifact Hashes (Canonical JSON SHA256)**:
- page_plan.json: `{run1_artifacts.get('page_plan', {}).get('sha256', 'N/A')}`
- validation_report.json: `{run1_artifacts.get('validation_report', {}).get('sha256', 'N/A')}`

**Page Counts by Subdomain**:
"""

    if page_counts:
        for subdomain, count in sorted(page_counts.items()):
            entry += f"- {subdomain}: {count} pages\n"
    else:
        entry += "- (No page counts available)\n"

    entry += "\n---\n"

    # Append to notes.md
    notes_content += entry

    with open(notes_path, "w", encoding="utf-8") as f:
        f.write(notes_content)

    return {
        "performed": True,
        "timestamp_utc": timestamp_utc,
        "git_commit": git_commit,
        "artifacts_written": artifacts_written,
        "notes_updated": str(notes_path.relative_to(repo_root))
    }


def run_pilot_vfv(
    pilot_id: str,
    goldenize_flag: bool,
    allow_placeholders: bool,
    output_path: Path,
    approve_branch: bool = False
) -> Dict[str, Any]:
    """
    Run VFV harness: 2 runs, verify both artifacts, check determinism, optionally goldenize.

    Args:
        pilot_id: Pilot identifier
        goldenize_flag: If True, goldenize artifacts on PASS
        allow_placeholders: If True, allow placeholder SHAs
        output_path: Path to write JSON report
        approve_branch: If True, create approval marker for AG-001 bypass (TC-951)

    Returns:
        VFV report dict
    """
    repo_root = get_repo_root()

    report = {
        "pilot_id": pilot_id,
        "preflight": {},
        "runs": {},
        "determinism": {},
        "goldenization": {"performed": False},
        "status": "UNKNOWN"
    }

    # TC-951: Create approval marker if requested
    marker_path = repo_root / "runs" / ".git" / "AI_BRANCH_APPROVED"
    marker_created = False

    if approve_branch:
        try:
            marker_path.parent.mkdir(parents=True, exist_ok=True)
            marker_path.write_text("vfv-pilot-validation", encoding="utf-8")
            marker_created = True
            print(f"\nCreated approval marker for pilot validation: {marker_path}")
        except Exception as e:
            print(f"\nWARNING: Failed to create approval marker: {e}")

    try:
        # Preflight check
        preflight = preflight_check(repo_root, pilot_id, allow_placeholders)
        report["preflight"] = preflight

        if not preflight["passed"]:
            report["status"] = "ERROR"
            report["error"] = preflight.get("error", "Preflight check failed")
            write_report(report, output_path)
            return report

        # Run pilot twice
        run_results = []
    
        for run_num in [1, 2]:
            print(f"\n{'='*70}")
            print(f"RUN {run_num}/2: {pilot_id}")
            print('='*70)
    
            # Execute pilot
            temp_output = repo_root / "artifacts" / f"pilot_vfv_{pilot_id}_run{run_num}.json"
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
                    # Check page_plan.json
                    page_plan_file = artifacts_dir / "page_plan.json"
                    if page_plan_file.exists():
                        data = load_json_file(page_plan_file)
                        if data:
                            artifacts["page_plan"] = {
                                "path": str(page_plan_file.relative_to(repo_root)),
                                "data": data,
                                "sha256": canonical_json_hash(data)
                            }
    
                            # Extract page counts (only from run1)
                            if run_num == 1:
                                page_counts = extract_page_counts(data)
                                artifacts["page_plan"]["page_count_by_subdomain"] = page_counts
    
                    # Check validation_report.json
                    validation_report_file = artifacts_dir / "validation_report.json"
                    if validation_report_file.exists():
                        data = load_json_file(validation_report_file)
                        if data:
                            artifacts["validation_report"] = {
                                "path": str(validation_report_file.relative_to(repo_root)),
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
    
            # TC-920: Capture stdout/stderr diagnostics when run fails
            if run_result.get("exit_code") is not None and run_result["exit_code"] != 0:
                diagnostics = {}
    
                # Capture last 2000 chars of stdout
                stdout = run_report.get("stdout", "")
                if stdout:
                    diagnostics["stdout_tail"] = stdout[-2000:]
    
                # Capture last 4000 chars of stderr
                stderr = run_report.get("stderr", "")
                if stderr:
                    diagnostics["stderr_tail"] = stderr[-4000:]
    
                # Capture command executed (reconstruct from config path)
                diagnostics["command_executed"] = f"run_pilot(pilot_id='{pilot_id}')"
    
                # Capture run directory used
                diagnostics["run_dir_used"] = run_report.get("run_dir", "N/A")
    
                if diagnostics:
                    run_result["diagnostics"] = diagnostics
    
            run_results.append(run_result)
    
            # Store in report (without 'data' field to avoid bloat)
            report["runs"][f"run{run_num}"] = {
                "exit_code": run_result["exit_code"],
                "run_dir": run_result["run_dir"],
                "artifacts": {}
            }
    
            for artifact_name, artifact_info in artifacts.items():
                report_artifact = {
                    "path": artifact_info["path"],
                    "sha256": artifact_info["sha256"]
                }
                if "page_count_by_subdomain" in artifact_info:
                    report_artifact["page_count_by_subdomain"] = artifact_info["page_count_by_subdomain"]
    
                report["runs"][f"run{run_num}"]["artifacts"][artifact_name] = report_artifact
    
            # TC-920: Include diagnostics in report if present
            if "diagnostics" in run_result:
                report["runs"][f"run{run_num}"]["diagnostics"] = run_result["diagnostics"]
    
            # Print run summary
            if run_result.get("error"):
                print(f"  ERROR: {run_result['error']}")
            elif run_result["exit_code"] == 0:
                print(f"  SUCCESS: Pilot completed successfully")
                print(f"  Run dir: {run_result['run_dir']}")
                print(f"  Artifacts found: {len(artifacts)}")
                for artifact_name in artifacts:
                    print(f"    - {artifact_name}")
            else:
                print(f"  FAIL: Pilot failed with exit code: {run_result['exit_code']}")
    
        # Verify both artifacts exist in both runs
        run1_artifacts = run_results[0]["artifacts"]
        run2_artifacts = run_results[1]["artifacts"]
    
        missing_artifacts = []
        if "page_plan" not in run1_artifacts:
            missing_artifacts.append("page_plan.json in run1")
        if "validation_report" not in run1_artifacts:
            missing_artifacts.append("validation_report.json in run1")
        if "page_plan" not in run2_artifacts:
            missing_artifacts.append("page_plan.json in run2")
        if "validation_report" not in run2_artifacts:
            missing_artifacts.append("validation_report.json in run2")
    
        if missing_artifacts:
            report["status"] = "FAIL"
            report["error"] = f"Missing artifacts: {', '.join(missing_artifacts)}"
            write_report(report, output_path)
            return report
    
        # TC-950: Check exit codes before determinism
        # Status should be FAIL if either run had non-zero exit code
        run1_exit = run_results[0].get("exit_code")
        run2_exit = run_results[1].get("exit_code")
    
        if run1_exit != 0 or run2_exit != 0:
            report["status"] = "FAIL"
            report["error"] = f"Non-zero exit codes: run1={run1_exit}, run2={run2_exit}"
            print(f"\n{'='*70}")
            print("EXIT CODE CHECK")
            print('='*70)
            print(f"  FAIL: Run 1 exit_code={run1_exit}, Run 2 exit_code={run2_exit}")
            print(f"  Status cannot be PASS with non-zero exit codes")
            write_report(report, output_path)
            return report
    
        # Determinism check
        print(f"\n{'='*70}")
        print("DETERMINISM CHECK")
        print('='*70)
    
        determinism_checks = {}
    
        for artifact_name in ["page_plan", "validation_report"]:
            run1_sha = run1_artifacts[artifact_name]["sha256"]
            run2_sha = run2_artifacts[artifact_name]["sha256"]
    
            match = run1_sha == run2_sha
    
            determinism_checks[artifact_name] = {
                "match": match,
                "run1_sha256": run1_sha,
                "run2_sha256": run2_sha
            }
    
            if match:
                print(f"  PASS: {artifact_name}: DETERMINISTIC")
                print(f"    SHA256: {run1_sha[:16]}...")
            else:
                print(f"  FAIL: {artifact_name}: NON-DETERMINISTIC")
                print(f"    Run 1: {run1_sha[:16]}...")
                print(f"    Run 2: {run2_sha[:16]}...")
    
        report["determinism"] = determinism_checks
    
        # Overall determinism status
        all_match = all(check["match"] for check in determinism_checks.values())
    
        if all_match:
            report["determinism"]["status"] = "PASS"
            report["status"] = "PASS"
            print(f"\nDeterminism: PASS")
        else:
            report["determinism"]["status"] = "FAIL"
            report["status"] = "FAIL"
            print(f"\nDeterminism: FAIL")
    
        # Goldenization (only if PASS + --goldenize flag + no placeholders)
        if report["status"] == "PASS" and goldenize_flag:
            if preflight.get("placeholders_detected"):
                print(f"\nSkipping goldenization: Placeholder SHAs detected")
                report["goldenization"]["skipped"] = True
                report["goldenization"]["reason"] = "Placeholder SHAs detected"
            else:
                print(f"\n{'='*70}")
                print("GOLDENIZATION")
                print('='*70)
    
                try:
                    page_counts = run1_artifacts.get("page_plan", {}).get("page_count_by_subdomain", {})
                    goldenization_report = goldenize(repo_root, pilot_id, run1_artifacts, page_counts)
                    report["goldenization"] = goldenization_report
    
                    print(f"  SUCCESS: Artifacts goldenized:")
                    for artifact_path in goldenization_report["artifacts_written"]:
                        print(f"    - {artifact_path}")
                    print(f"  SUCCESS: Notes updated: {goldenization_report['notes_updated']}")
    
                except Exception as e:
                    report["goldenization"]["performed"] = False
                    report["goldenization"]["error"] = str(e)
                    print(f"  ERROR: Goldenization failed: {e}")
    
        # Write report
        write_report(report, output_path)
    
        # Print summary
        print(f"\n{'='*70}")
        print("SUMMARY")
        print('='*70)
        print(f"Pilot: {pilot_id}")
        print(f"Status: {report['status']}")
        print(f"Determinism: {report['determinism']['status']}")
        print(f"Goldenization: {'YES' if report['goldenization'].get('performed') else 'NO'}")
        print(f"\nReport written to: {output_path}")
    
        return report

    finally:
        # TC-951: Clean up approval marker if we created it
        if marker_created and marker_path.exists():
            try:
                marker_path.unlink()
                print(f"\nCleaned up approval marker: {marker_path}")
            except Exception as e:
                print(f"\nWARNING: Failed to clean up approval marker: {e}")


def write_report(report: Dict[str, Any], output_path: Path) -> None:
    """Write deterministic JSON report."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Remove 'data' fields from artifacts to avoid bloat
    report_copy = json.loads(json.dumps(report))  # Deep copy

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(
            report_copy,
            f,
            sort_keys=True,
            indent=2,
            ensure_ascii=False
        )


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="TC-903: VFV Harness - Strict 2-run determinism with goldenization"
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
    parser.add_argument(
        "--goldenize",
        action="store_true",
        help="Goldenize artifacts on PASS (only if no placeholders detected)"
    )
    parser.add_argument(
        "--allow_placeholders",
        action="store_true",
        help="Allow placeholder SHAs (dev/testing only)"
    )
    parser.add_argument(
        "--approve-branch",
        action="store_true",
        help="Automatically approve branch creation for pilot validation (bypasses AG-001)"
    )

    args = parser.parse_args()

    try:
        report = run_pilot_vfv(
            pilot_id=args.pilot,
            goldenize_flag=args.goldenize,
            allow_placeholders=args.allow_placeholders,
            approve_branch=args.approve_branch,
            output_path=args.output
        )

        # Exit with appropriate code
        if report["status"] == "PASS":
            return 0
        elif report["status"] == "FAIL":
            return 1
        else:  # ERROR
            return 2

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    sys.exit(main())
