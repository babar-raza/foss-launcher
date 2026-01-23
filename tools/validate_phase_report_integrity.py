#!/usr/bin/env python3
"""
Phase Report Integrity Validator

Validates that phase reports claiming gate results have corresponding
raw gate outputs saved in the gate_outputs/ directory.

This ensures that:
1. Gate A1 (spec pack validation) is never skipped
2. Reports accurately reflect actual gate execution
3. Gate outputs are preserved for audit

Rules:
- Legacy phases (phase-0 through phase-3): Not enforced (pre-standardization)
- Strict phases (phase-4 onwards): Must have gate_outputs/, A1 output, and change_log.md

Exit codes:
  0 - All phase reports are valid
  1 - One or more reports are missing gate outputs
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple

# Legacy phases created before standardization (not strictly enforced)
LEGACY_PHASES = {"phase-0_discovery", "phase-1_spec-hardening",
                 "phase-2_plan-taskcard-hardening", "phase-3_final-readiness"}


def find_phase_reports(repo_root: Path) -> List[Path]:
    """Find all phase report directories."""
    reports_dir = repo_root / "reports"
    if not reports_dir.exists():
        return []

    phase_dirs = []
    for path in sorted(reports_dir.iterdir()):
        if path.is_dir() and path.name.startswith("phase-"):
            phase_dirs.append(path)

    return phase_dirs


def check_phase_report_integrity(phase_dir: Path) -> Tuple[bool, List[str]]:
    """
    Check that a phase report has the required gate outputs.

    Returns:
        (passed, errors): Tuple of pass status and list of error messages
    """
    errors = []
    warnings = []
    phase_name = phase_dir.name

    # Check if this is a legacy phase (pre-standardization)
    if phase_name in LEGACY_PHASES:
        # Legacy phases are not strictly enforced
        return (True, [])

    # Check for gate_outputs directory
    gate_outputs_dir = phase_dir / "gate_outputs"
    if not gate_outputs_dir.exists():
        errors.append(f"{phase_name}: Missing gate_outputs/ directory")
        return (False, errors)

    # Check for at least one gate output file
    gate_files = list(gate_outputs_dir.glob("*"))
    if not gate_files:
        errors.append(f"{phase_name}: gate_outputs/ directory is empty")
        return (False, errors)

    # Check for GATE_SUMMARY.md or equivalent
    summary_files = [
        "GATE_SUMMARY.md",
        "gate_summary.md",
        "A1_output.txt",
        "A1_spec_pack.txt",
    ]
    has_summary = any((gate_outputs_dir / f).exists() for f in summary_files)

    # Also check if any file mentions Gate A1
    if not has_summary:
        for f in gate_files:
            if f.is_file():
                try:
                    content = f.read_text(encoding="utf-8", errors="ignore")
                    if "Gate A1" in content or "A1" in f.name:
                        has_summary = True
                        break
                except Exception:
                    pass

    if not has_summary:
        errors.append(
            f"{phase_name}: gate_outputs/ missing A1 (spec pack) validation output"
        )

    # Check that change_log.md exists (or global_change_log.md for orchestrator phases)
    has_change_log = (
        (phase_dir / "change_log.md").exists() or
        (phase_dir / "global_change_log.md").exists()
    )
    if not has_change_log:
        errors.append(f"{phase_name}: Missing change_log.md or global_change_log.md")

    # Check that diff_manifest.md exists (or global_diff_manifest.md)
    has_diff_manifest = (
        (phase_dir / "diff_manifest.md").exists() or
        (phase_dir / "global_diff_manifest.md").exists()
    )
    if not has_diff_manifest:
        # This is a soft warning, not a failure
        warnings.append(f"{phase_name}: Missing diff_manifest.md (recommended)")

    # Check that self_review_12d.md exists (if phase has deliverables)
    # This is a soft check - some phases may not need self-review
    if not (phase_dir / "self_review_12d.md").exists():
        # Only warn, don't fail
        pass

    return (len(errors) == 0, errors)


def main():
    """Main validation routine."""
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent

    print("=" * 70)
    print("PHASE REPORT INTEGRITY VALIDATION")
    print("=" * 70)
    print(f"Repository: {repo_root}")
    print()

    phase_dirs = find_phase_reports(repo_root)

    if not phase_dirs:
        print("No phase reports found in reports/")
        print("SKIPPED (nothing to validate)")
        return 0

    print(f"Found {len(phase_dirs)} phase report(s)")
    print()

    all_passed = True
    all_errors = []
    legacy_count = 0

    for phase_dir in phase_dirs:
        passed, errors = check_phase_report_integrity(phase_dir)

        # Mark legacy phases
        if phase_dir.name in LEGACY_PHASES:
            print(f"[LEGACY] {phase_dir.name} (pre-standardization, not enforced)")
            legacy_count += 1
        elif passed:
            print(f"[PASS] {phase_dir.name}")
        else:
            print(f"[FAIL] {phase_dir.name}")
            all_passed = False
            all_errors.extend(errors)

    print()
    print("=" * 70)

    if all_passed:
        print("SUCCESS: All phase reports have valid gate outputs")
        if legacy_count > 0:
            print(f"  (Note: {legacy_count} legacy phase(s) not enforced)")
        return 0
    else:
        print("FAILURE: Some phase reports are missing gate outputs")
        print()
        for error in all_errors:
            print(f"  - {error}")
        print()
        print("Strict phases (phase-4 onwards) MUST include:")
        print("  1. gate_outputs/ directory")
        print("  2. At least one file with A1 gate output (spec pack validation)")
        print("  3. change_log.md (or global_change_log.md for orchestrator phases)")
        print()
        print(f"Legacy phases (phase-0 through phase-3): {legacy_count} found, not enforced")
        return 1


if __name__ == "__main__":
    sys.exit(main())
