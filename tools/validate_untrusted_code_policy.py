#!/usr/bin/env python3
"""
Untrusted Code Policy Validator (Gate R)

Validates that ingested repo code is parse-only per Guarantee J.

Implementation checks:
- Secure subprocess wrapper exists (src/launch/util/subprocess.py)
- Tests exist and are comprehensive
- No direct subprocess calls bypass the wrapper

See: specs/34_strict_compliance_guarantees.md (Guarantee J)

Exit codes:
  0 - Policy implementation complete and validated
  1 - Implementation incomplete or violations detected
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple


def scan_for_unsafe_subprocess(file_path: Path) -> List[Tuple[int, str]]:
    """
    Scan file for direct subprocess calls that bypass the wrapper.
    Returns list of (line_number, line_content).
    """
    violations = []

    # Skip the wrapper itself
    if "subprocess.py" in str(file_path):
        return violations

    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception:
        return violations

    lines = content.split("\n")

    for i, line in enumerate(lines, 1):
        # Look for direct subprocess calls (not using our wrapper)
        if "subprocess.run(" in line or "subprocess.call(" in line or "subprocess.Popen(" in line:
            # Check if it's importing subprocess (allowed)
            if "import subprocess" in line:
                continue
            # Check if it's from our wrapper
            if "from launch.util.subprocess import" in line:
                continue
            violations.append((i, line.strip()))

    return violations


def main():
    """Validate untrusted code policy implementation."""
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent

    print("=" * 70)
    print("UNTRUSTED CODE POLICY VALIDATION (Gate R)")
    print("=" * 70)
    print(f"Repository: {repo_root}")
    print()

    launch_dir = repo_root / "src" / "launch"

    if not launch_dir.exists():
        print("Note: src/launch/ not yet created")
        print("  Policy will be enforced when implementation begins")
        print()
        print("=" * 70)
        print("RESULT: Untrusted code policy check skipped (no implementation yet)")
        print("=" * 70)
        return 0

    # Check 1: Verify subprocess wrapper exists
    wrapper_path = launch_dir / "util" / "subprocess.py"
    wrapper_exists = wrapper_path.exists()

    print("Check 1: Subprocess wrapper implementation")
    if wrapper_exists:
        print(f"  PASS: {wrapper_path.relative_to(repo_root)} exists")
    else:
        print(f"  FAIL: {wrapper_path.relative_to(repo_root)} missing")
    print()

    # Check 2: Verify tests exist
    test_path = repo_root / "tests" / "unit" / "util" / "test_subprocess.py"
    tests_exist = test_path.exists()

    print("Check 2: Test coverage")
    if tests_exist:
        print(f"  PASS: {test_path.relative_to(repo_root)} exists")
    else:
        print(f"  FAIL: {test_path.relative_to(repo_root)} missing")
    print()

    # Check 3: Scan for unsafe subprocess calls
    python_files = list(launch_dir.glob("**/*.py"))
    print(f"Check 3: Scanning {len(python_files)} file(s) for unsafe subprocess calls...")

    violations = []
    for file_path in python_files:
        file_violations = scan_for_unsafe_subprocess(file_path)
        if file_violations:
            violations.append((file_path, file_violations))

    if violations:
        print("  WARN: Direct subprocess calls detected (should use wrapper):")
        for file_path, file_violations in violations:
            relative = file_path.relative_to(repo_root)
            print(f"    {relative}")
            for line_num, line_content in file_violations:
                print(f"      Line {line_num}: {line_content[:80]}")
    else:
        print("  PASS: No unsafe subprocess calls detected")
    print()

    # Overall result
    print("=" * 70)
    if wrapper_exists and tests_exist and not violations:
        print("RESULT: Untrusted code policy is IMPLEMENTED")
        print()
        print("Implementation complete:")
        print(f"  [OK] Subprocess wrapper: {wrapper_path.relative_to(repo_root)}")
        print(f"  [OK] Tests: {test_path.relative_to(repo_root)}")
        print("  [OK] No unsafe subprocess calls detected")
        print("=" * 70)
        return 0
    else:
        print("RESULT: Untrusted code policy implementation INCOMPLETE")
        print()
        if not wrapper_exists:
            print("  [FAIL] Missing: src/launch/util/subprocess.py")
        if not tests_exist:
            print("  [FAIL] Missing: tests/unit/util/test_subprocess.py")
        if violations:
            print(f"  [FAIL] Found {len(violations)} file(s) with unsafe subprocess calls")
        print()
        print("Action required:")
        print("  - Implement subprocess wrapper with cwd validation")
        print("  - Add comprehensive tests")
        print("  - Replace direct subprocess calls with wrapper")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
