#!/usr/bin/env python3
"""
CI Parity Validator (Gate Q)

Validates that CI workflows use canonical commands per Guarantee H:
- make install-uv (or make install)
- python tools/validate_swarm_ready.py
- pytest

See: specs/34_strict_compliance_guarantees.md (Guarantee H)

Exit codes:
  0 - CI parity is valid
  1 - CI parity violations detected
"""

import sys
from pathlib import Path
from typing import List, Tuple

import yaml


CANONICAL_COMMANDS = [
    "make install-uv",
    "tools/validate_swarm_ready.py",
    "pytest",
]

ALLOWED_INSTALL_VARIANTS = [
    "make install-uv",
    "make install",
]


def check_workflow_file(workflow_path: Path) -> Tuple[List[str], List[str]]:
    """
    Check a single workflow file for canonical commands.
    Returns (found_commands, missing_commands).
    """
    try:
        content = workflow_path.read_text(encoding="utf-8")
    except Exception as e:
        return [], [f"Failed to read {workflow_path.name}: {e}"]

    found = []
    missing = []

    # Check for install command (any variant)
    has_install = any(variant in content for variant in ALLOWED_INSTALL_VARIANTS)
    if has_install:
        found.append("install command")
    else:
        missing.append("install command (make install-uv or make install)")

    # Check for validate_swarm_ready.py
    if "tools/validate_swarm_ready.py" in content or "validate_swarm_ready.py" in content:
        found.append("validate_swarm_ready.py")
    else:
        missing.append("validate_swarm_ready.py")

    # Check for pytest
    if "pytest" in content:
        found.append("pytest")
    else:
        missing.append("pytest")

    return found, missing


def find_workflows(repo_root: Path) -> List[Path]:
    """Find all GitHub workflow files."""
    workflows_dir = repo_root / ".github" / "workflows"
    if not workflows_dir.exists():
        return []

    workflows = list(workflows_dir.glob("*.yml")) + list(workflows_dir.glob("*.yaml"))
    return sorted(workflows)


def main():
    """Main validation routine."""
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent

    print("=" * 70)
    print("CI PARITY VALIDATION (Gate Q)")
    print("=" * 70)
    print(f"Repository: {repo_root}")
    print()

    workflows = find_workflows(repo_root)

    if not workflows:
        print("WARNING: No CI workflows found in .github/workflows/")
        print("  This is acceptable if CI is not yet set up.")
        print()
        print("=" * 70)
        print("RESULT: CI parity check skipped (no workflows found)")
        print("=" * 70)
        return 0

    print(f"Found {len(workflows)} workflow(s) to validate")
    print()

    all_violations = []

    for workflow in workflows:
        relative_path = workflow.relative_to(repo_root)
        print(f"Checking: {relative_path}")

        found, missing = check_workflow_file(workflow)

        if missing:
            all_violations.append((relative_path, missing))
            print("  FAIL: Missing canonical commands:")
            for cmd in missing:
                print(f"    - {cmd}")
        else:
            print("  PASS: All canonical commands present")

    print()
    print("=" * 70)
    if not all_violations:
        print("RESULT: All CI workflows use canonical commands")
        print("=" * 70)
        return 0
    else:
        print("RESULT: CI parity validation FAILED")
        print()
        print("Violations:")
        for workflow_path, missing in all_violations:
            print(f"  {workflow_path}:")
            for cmd in missing:
                print(f"    - Missing: {cmd}")
        print()
        print("Canonical commands required:")
        print("  - make install-uv (or make install)")
        print("  - python tools/validate_swarm_ready.py")
        print("  - pytest")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
