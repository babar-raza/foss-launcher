#!/usr/bin/env python3
"""
Supply Chain Pinning Validator (Gate K)

Validates that dependencies are pinned and installed from lock file per Guarantee C:
- uv.lock exists
- Makefile uses frozen install (uv sync --frozen)
- .venv exists

See: specs/34_strict_compliance_guarantees.md (Guarantee C)

Exit codes:
  0 - Supply chain pinning is valid
  1 - Supply chain pinning violations detected
"""

import re
import sys
from pathlib import Path
from typing import List


def check_lockfile_exists(repo_root: Path) -> List[str]:
    """Check that uv.lock exists."""
    errors = []

    lockfile = repo_root / "uv.lock"
    if not lockfile.exists():
        errors.append("uv.lock not found (supply-chain pinning requires lockfile)")

    return errors


def check_venv_exists(repo_root: Path) -> List[str]:
    """Check that .venv exists."""
    errors = []

    venv_dir = repo_root / ".venv"
    if not venv_dir.exists():
        errors.append(".venv not found (run 'python -m venv .venv' first)")

    return errors


def check_makefile_frozen_install(repo_root: Path) -> List[str]:
    """Check that Makefile install targets use frozen install."""
    errors = []

    makefile = repo_root / "Makefile"
    if not makefile.exists():
        # Makefile is optional, but if present must use frozen
        return errors

    try:
        content = makefile.read_text(encoding="utf-8")
    except Exception as e:
        errors.append(f"Failed to read Makefile: {e}")
        return errors

    # Check for uv sync --frozen in install targets
    has_frozen_install = False
    has_non_frozen_install = False

    # Look for uv sync commands
    uv_sync_lines = [line for line in content.split("\n") if "uv sync" in line]

    for line in uv_sync_lines:
        if "--frozen" in line:
            has_frozen_install = True
        else:
            # uv sync without --frozen
            has_non_frozen_install = True

    if has_non_frozen_install:
        errors.append(
            "Makefile contains 'uv sync' without --frozen (supply-chain pinning requires frozen install)"
        )

    if not has_frozen_install and uv_sync_lines:
        errors.append(
            "Makefile uses 'uv sync' but not with --frozen flag (add --frozen)"
        )

    return errors


def main():
    """Main validation routine."""
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent

    print("=" * 70)
    print("SUPPLY CHAIN PINNING VALIDATION (Gate K)")
    print("=" * 70)
    print(f"Repository: {repo_root}")
    print()

    all_errors = []

    # Check 1: Lockfile exists
    print("Check 1: Verifying uv.lock exists...")
    errors = check_lockfile_exists(repo_root)
    if errors:
        all_errors.extend(errors)
        print(f"  FAIL: {errors[0]}")
    else:
        print("  PASS: uv.lock exists")

    # Check 2: .venv exists
    print("\nCheck 2: Verifying .venv exists...")
    errors = check_venv_exists(repo_root)
    if errors:
        all_errors.extend(errors)
        print(f"  FAIL: {errors[0]}")
    else:
        print("  PASS: .venv exists")

    # Check 3: Makefile uses frozen install
    print("\nCheck 3: Verifying Makefile uses frozen install...")
    errors = check_makefile_frozen_install(repo_root)
    if errors:
        all_errors.extend(errors)
        for err in errors:
            print(f"  FAIL: {err}")
    else:
        print("  PASS: Makefile install uses --frozen (or no Makefile)")

    print()
    print("=" * 70)
    if not all_errors:
        print("RESULT: Supply chain pinning is compliant")
        print("=" * 70)
        return 0
    else:
        print("RESULT: Supply chain pinning validation FAILED")
        print()
        print("Errors:")
        for i, err in enumerate(all_errors, 1):
            print(f"  {i}. {err}")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
