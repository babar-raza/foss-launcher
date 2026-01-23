#!/usr/bin/env python3
"""
Pilots Contract Validator

Validates that pilots are canonically defined under specs/pilots/** and that
all binding documents/taskcards agree on this canonical path.

Gate G in validate_swarm_ready.py.

Exit codes:
  0 - All checks pass
  1 - One or more checks failed
"""

import sys
import re
from pathlib import Path
from typing import List, Tuple, Set


def find_repo_root() -> Path:
    """Find the repository root directory."""
    script_dir = Path(__file__).parent
    return script_dir.parent


def get_pilot_directories(repo_root: Path) -> List[str]:
    """Get list of pilot directory names under specs/pilots/."""
    pilots_dir = repo_root / "specs" / "pilots"
    if not pilots_dir.exists():
        return []

    pilots = []
    for item in sorted(pilots_dir.iterdir()):
        if item.is_dir() and item.name.startswith("pilot-"):
            pilots.append(item.name)
    return pilots


def check_pilot_required_files(repo_root: Path) -> List[str]:
    """
    Check that each pilot directory has required files.

    Required files per pilot:
    - run_config.pinned.yaml
    - expected_page_plan.json
    - expected_validation_report.json
    - notes.md

    Returns list of error messages.
    """
    errors = []
    pilots_dir = repo_root / "specs" / "pilots"

    if not pilots_dir.exists():
        errors.append(f"ERROR: specs/pilots/ directory does not exist")
        return errors

    pilots = get_pilot_directories(repo_root)

    if not pilots:
        errors.append("WARNING: No pilot directories found under specs/pilots/")
        return errors

    required_files = [
        "run_config.pinned.yaml",
        "expected_page_plan.json",
        "expected_validation_report.json",
        "notes.md"
    ]

    for pilot in pilots:
        pilot_dir = pilots_dir / pilot
        for req_file in required_files:
            file_path = pilot_dir / req_file
            if not file_path.exists():
                errors.append(f"MISSING: specs/pilots/{pilot}/{req_file}")

    return errors


def scan_file_for_configs_pilots_canonical(file_path: Path) -> List[str]:
    """
    Scan a file for references that claim configs/pilots/** is canonical.

    We look for patterns that suggest configs/pilots is the canonical source,
    not just a reference to templates.

    Returns list of problematic lines.
    """
    issues = []

    try:
        content = file_path.read_text(encoding='utf-8')
    except Exception:
        return issues

    # Patterns that suggest configs/pilots is canonical (not just templates)
    canonical_patterns = [
        r'[Cc]anonical.*configs/pilots',
        r'configs/pilots.*[Cc]anonical',
        r'[Pp]ilot configs? (?:in|under|at) `?configs/pilots',
        r'[Pp]ilot configuration.*configs/pilots',
        r'[Pp]inned pilot configs.*configs/pilots',
        # But exclude "template" references
    ]

    # Lines to exclude (template references are OK)
    exclude_patterns = [
        r'template',
        r'non-binding',
        r'authoring helper',
        r'_template',
    ]

    lines = content.split('\n')
    for i, line in enumerate(lines, 1):
        line_lower = line.lower()

        # Skip if line mentions templates
        if any(re.search(pat, line_lower) for pat in exclude_patterns):
            continue

        # Check for canonical claims
        for pattern in canonical_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                issues.append(f"{file_path}:{i}: {line.strip()[:80]}")
                break

    return issues


def check_canonical_path_consistency(repo_root: Path) -> List[str]:
    """
    Check that no binding doc/taskcard claims configs/pilots/** is canonical.

    The canonical source is specs/pilots/** per specs/13_pilots.md.
    configs/pilots/** should only be referenced as templates/non-binding.

    Returns list of error messages.
    """
    errors = []

    # Files to check
    check_paths = [
        "specs/13_pilots.md",
        "specs/pilot-blueprint.md",
        "plans/implementation_master_checklist.md",
        "plans/traceability_matrix.md",
    ]

    # Also check all taskcards
    taskcards_dir = repo_root / "plans" / "taskcards"
    if taskcards_dir.exists():
        for tc_file in taskcards_dir.glob("TC-*.md"):
            check_paths.append(str(tc_file.relative_to(repo_root)))

    for rel_path in check_paths:
        file_path = repo_root / rel_path
        if file_path.exists():
            issues = scan_file_for_configs_pilots_canonical(file_path)
            errors.extend(issues)

    return errors


def check_specs_13_defines_canonical(repo_root: Path) -> List[str]:
    """
    Verify that specs/13_pilots.md defines specs/pilots/** as canonical.

    Returns list of error messages.
    """
    errors = []
    pilots_spec = repo_root / "specs" / "13_pilots.md"

    if not pilots_spec.exists():
        errors.append("ERROR: specs/13_pilots.md does not exist")
        return errors

    content = pilots_spec.read_text(encoding='utf-8')

    # Check that it references specs/pilots/
    if "specs/pilots/" not in content:
        errors.append("ERROR: specs/13_pilots.md does not reference specs/pilots/ as canonical location")

    return errors


def main():
    """Main validation routine."""
    repo_root = find_repo_root()

    print("=" * 70)
    print("PILOTS CONTRACT VALIDATION")
    print("=" * 70)
    print(f"Repository: {repo_root}")
    print()

    all_errors = []

    # Check 1: specs/13_pilots.md defines canonical location
    print("Check 1: Verifying specs/13_pilots.md defines canonical location...")
    errors = check_specs_13_defines_canonical(repo_root)
    if errors:
        all_errors.extend(errors)
        for e in errors:
            print(f"  {e}")
    else:
        print("  PASS: specs/13_pilots.md references specs/pilots/ as canonical")
    print()

    # Check 2: Required files exist for each pilot
    print("Check 2: Verifying required pilot files exist...")
    errors = check_pilot_required_files(repo_root)
    if errors:
        all_errors.extend(errors)
        for e in errors:
            print(f"  {e}")
    else:
        pilots = get_pilot_directories(repo_root)
        print(f"  PASS: All required files present for {len(pilots)} pilot(s)")
    print()

    # Check 3: No doc claims configs/pilots is canonical
    print("Check 3: Checking for conflicting canonical path claims...")
    errors = check_canonical_path_consistency(repo_root)
    if errors:
        all_errors.extend(errors)
        print("  Found references that may claim configs/pilots is canonical:")
        for e in errors:
            print(f"    {e}")
    else:
        print("  PASS: No conflicting canonical path claims found")
    print()

    # Summary
    print("=" * 70)
    if all_errors:
        error_count = len([e for e in all_errors if e.startswith("ERROR") or e.startswith("MISSING")])
        warning_count = len([e for e in all_errors if e.startswith("WARNING")])
        print(f"RESULT: {error_count} error(s), {warning_count} warning(s)")
        if error_count > 0:
            print("Pilots contract validation FAILED")
            print("=" * 70)
            return 1
        else:
            print("Pilots contract validation PASSED (with warnings)")
            print("=" * 70)
            return 0
    else:
        print("RESULT: All pilots contract checks passed")
        print("=" * 70)
        return 0


if __name__ == "__main__":
    sys.exit(main())
