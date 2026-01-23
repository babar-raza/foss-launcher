#!/usr/bin/env python3
"""
MCP Contract Validator

Validates that both MCP quickstart tools are documented in specs:
- launch_start_run_from_product_url (product page URL quickstart)
- launch_start_run_from_github_repo_url (GitHub repo URL quickstart)

Gate H in validate_swarm_ready.py.

Exit codes:
  0 - All checks pass
  1 - One or more checks failed
"""

import sys
import re
from pathlib import Path
from typing import List, Tuple


def find_repo_root() -> Path:
    """Find the repository root directory."""
    script_dir = Path(__file__).parent
    return script_dir.parent


def check_mcp_endpoints_spec(repo_root: Path) -> Tuple[List[str], List[str]]:
    """
    Check that specs/14_mcp_endpoints.md documents both quickstart tools.

    Returns:
        Tuple of (errors, warnings)
    """
    errors = []
    warnings = []

    mcp_endpoints = repo_root / "specs" / "14_mcp_endpoints.md"

    if not mcp_endpoints.exists():
        errors.append("ERROR: specs/14_mcp_endpoints.md does not exist")
        return errors, warnings

    content = mcp_endpoints.read_text(encoding='utf-8')

    # Check for product URL quickstart
    if "launch_start_run_from_product_url" not in content:
        errors.append("ERROR: specs/14_mcp_endpoints.md missing launch_start_run_from_product_url")

    # Check for GitHub repo URL quickstart
    if "launch_start_run_from_github_repo_url" not in content:
        errors.append("ERROR: specs/14_mcp_endpoints.md missing launch_start_run_from_github_repo_url")

    # Check for backward compatibility note
    if "launch_start_run_from_url" in content:
        if "deprecated" not in content.lower() and "alias" not in content.lower():
            warnings.append("WARNING: launch_start_run_from_url referenced without deprecation note")

    return errors, warnings


def check_mcp_tool_schemas_spec(repo_root: Path) -> Tuple[List[str], List[str]]:
    """
    Check that specs/24_mcp_tool_schemas.md has schemas for both quickstart tools.

    Returns:
        Tuple of (errors, warnings)
    """
    errors = []
    warnings = []

    mcp_schemas = repo_root / "specs" / "24_mcp_tool_schemas.md"

    if not mcp_schemas.exists():
        errors.append("ERROR: specs/24_mcp_tool_schemas.md does not exist")
        return errors, warnings

    content = mcp_schemas.read_text(encoding='utf-8')

    # Check for product URL quickstart schema section
    if "### launch_start_run_from_product_url" not in content:
        errors.append("ERROR: specs/24_mcp_tool_schemas.md missing ### launch_start_run_from_product_url section")

    # Check for GitHub repo URL quickstart schema section
    if "### launch_start_run_from_github_repo_url" not in content:
        errors.append("ERROR: specs/24_mcp_tool_schemas.md missing ### launch_start_run_from_github_repo_url section")

    # Check that GitHub quickstart has required elements
    if "launch_start_run_from_github_repo_url" in content:
        # Check for inference behavior documentation
        if "Behavior (binding)" not in content or "Inference algorithm" not in content:
            warnings.append("WARNING: launch_start_run_from_github_repo_url may be missing behavior/inference documentation")

        # Check for ambiguity handling
        if "missing_fields" not in content:
            errors.append("ERROR: launch_start_run_from_github_repo_url missing ambiguity handling (missing_fields)")

        # Check for confidence threshold
        if "confidence" not in content.lower():
            warnings.append("WARNING: launch_start_run_from_github_repo_url may be missing confidence threshold documentation")

    return errors, warnings


def check_taskcards_exist(repo_root: Path) -> Tuple[List[str], List[str]]:
    """
    Check that taskcards exist for both quickstart tools.

    Returns:
        Tuple of (errors, warnings)
    """
    errors = []
    warnings = []

    taskcards_dir = repo_root / "plans" / "taskcards"

    # Check TC-511 for product URL quickstart
    tc_511 = taskcards_dir / "TC-511_mcp_quickstart_url.md"
    if not tc_511.exists():
        errors.append("ERROR: TC-511 taskcard not found (product URL quickstart)")
    else:
        content = tc_511.read_text(encoding='utf-8')
        if "launch_start_run_from_product_url" not in content:
            errors.append("ERROR: TC-511 does not reference launch_start_run_from_product_url")

    # Check TC-512 for GitHub repo URL quickstart
    tc_512 = taskcards_dir / "TC-512_mcp_quickstart_github_repo_url.md"
    if not tc_512.exists():
        errors.append("ERROR: TC-512 taskcard not found (GitHub repo URL quickstart)")
    else:
        content = tc_512.read_text(encoding='utf-8')
        if "launch_start_run_from_github_repo_url" not in content:
            errors.append("ERROR: TC-512 does not reference launch_start_run_from_github_repo_url")

    return errors, warnings


def main():
    """Main validation routine."""
    repo_root = find_repo_root()

    print("=" * 70)
    print("MCP CONTRACT VALIDATION")
    print("=" * 70)
    print(f"Repository: {repo_root}")
    print()

    all_errors = []
    all_warnings = []

    # Check 1: MCP endpoints spec
    print("Check 1: Verifying specs/14_mcp_endpoints.md...")
    errors, warnings = check_mcp_endpoints_spec(repo_root)
    all_errors.extend(errors)
    all_warnings.extend(warnings)
    if errors:
        for e in errors:
            print(f"  {e}")
    else:
        print("  PASS: Both quickstart tools documented in MCP endpoints spec")
    if warnings:
        for w in warnings:
            print(f"  {w}")
    print()

    # Check 2: MCP tool schemas spec
    print("Check 2: Verifying specs/24_mcp_tool_schemas.md...")
    errors, warnings = check_mcp_tool_schemas_spec(repo_root)
    all_errors.extend(errors)
    all_warnings.extend(warnings)
    if errors:
        for e in errors:
            print(f"  {e}")
    else:
        print("  PASS: Both quickstart tools have schema sections")
    if warnings:
        for w in warnings:
            print(f"  {w}")
    print()

    # Check 3: Taskcards exist
    print("Check 3: Verifying taskcards exist for both quickstart tools...")
    errors, warnings = check_taskcards_exist(repo_root)
    all_errors.extend(errors)
    all_warnings.extend(warnings)
    if errors:
        for e in errors:
            print(f"  {e}")
    else:
        print("  PASS: TC-511 and TC-512 exist and reference correct tool names")
    if warnings:
        for w in warnings:
            print(f"  {w}")
    print()

    # Summary
    print("=" * 70)
    error_count = len(all_errors)
    warning_count = len(all_warnings)

    if error_count > 0:
        print(f"RESULT: {error_count} error(s), {warning_count} warning(s)")
        print("MCP contract validation FAILED")
        print("=" * 70)
        return 1
    elif warning_count > 0:
        print(f"RESULT: 0 error(s), {warning_count} warning(s)")
        print("MCP contract validation PASSED (with warnings)")
        print("=" * 70)
        return 0
    else:
        print("RESULT: All MCP contract checks passed")
        print("=" * 70)
        return 0


if __name__ == "__main__":
    sys.exit(main())
