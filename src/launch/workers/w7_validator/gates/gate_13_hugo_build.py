"""Gate 13: Hugo Build.

Validates that Hugo site builds successfully.

Per specs/09_validation_gates.md (Gate 5 Hugo Build).
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Dict, List, Tuple


def execute_gate(run_dir: Path, profile: str) -> Tuple[bool, List[Dict[str, Any]]]:
    """Execute Gate 13: Hugo Build.

    Validates that Hugo site builds successfully in production mode.

    Args:
        run_dir: Run directory path
        profile: Validation profile (local, ci, prod)

    Returns:
        Tuple of (gate_passed, issues)
    """
    issues = []

    # Determine timeout based on profile
    timeouts = {"local": 300, "ci": 600, "prod": 600}  # seconds
    timeout = timeouts.get(profile, 300)

    # Site directory
    site_dir = run_dir / "work" / "site"
    if not site_dir.exists():
        # No site to build
        return True, []

    # Check if Hugo is available
    try:
        result = subprocess.run(
            ["hugo", "version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            issues.append(
                {
                    "issue_id": "hugo_build_tool_missing",
                    "gate": "gate_13_hugo_build",
                    "severity": "blocker",
                    "message": "Hugo tool not found or not working",
                    "error_code": "GATE_HUGO_BUILD_TOOL_MISSING",
                    "status": "OPEN",
                }
            )
            return False, issues

    except FileNotFoundError:
        issues.append(
            {
                "issue_id": "hugo_build_tool_missing",
                "gate": "gate_13_hugo_build",
                "severity": "blocker",
                "message": "Hugo tool not found in PATH",
                "error_code": "GATE_HUGO_BUILD_TOOL_MISSING",
                "status": "OPEN",
            }
        )
        return False, issues
    except subprocess.TimeoutExpired:
        issues.append(
            {
                "issue_id": "hugo_build_version_check_timeout",
                "gate": "gate_13_hugo_build",
                "severity": "error",
                "message": "Hugo version check timed out",
                "error_code": "GATE_HUGO_BUILD_TIMEOUT",
                "status": "OPEN",
            }
        )
        return False, issues

    # Run Hugo build
    try:
        result = subprocess.run(
            ["hugo", "--minify", "--environment", "production"],
            cwd=site_dir,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        # Check for errors in output
        if result.returncode != 0:
            issues.append(
                {
                    "issue_id": "hugo_build_failed",
                    "gate": "gate_13_hugo_build",
                    "severity": "blocker",
                    "message": f"Hugo build failed with exit code {result.returncode}",
                    "error_code": "GATE_HUGO_BUILD_FAILED",
                    "status": "OPEN",
                    "suggested_fix": result.stderr[:500] if result.stderr else None,
                }
            )

        # Check for ERROR messages in output
        if "ERROR" in result.stderr or "ERROR" in result.stdout:
            # Extract error lines
            error_lines = [
                line
                for line in (result.stderr + result.stdout).split("\n")
                if "ERROR" in line
            ]

            issues.append(
                {
                    "issue_id": "hugo_build_errors",
                    "gate": "gate_13_hugo_build",
                    "severity": "blocker",
                    "message": f"Hugo build reported errors: {'; '.join(error_lines[:3])}",
                    "error_code": "GATE_HUGO_BUILD_ERROR",
                    "status": "OPEN",
                }
            )

    except subprocess.TimeoutExpired:
        issues.append(
            {
                "issue_id": "hugo_build_timeout",
                "gate": "gate_13_hugo_build",
                "severity": "blocker",
                "message": f"Hugo build exceeded timeout of {timeout}s",
                "error_code": "GATE_HUGO_BUILD_TIMEOUT",
                "status": "OPEN",
            }
        )
    except Exception as e:
        issues.append(
            {
                "issue_id": "hugo_build_exception",
                "gate": "gate_13_hugo_build",
                "severity": "blocker",
                "message": f"Hugo build failed with exception: {e}",
                "error_code": "GATE_HUGO_BUILD_FAILED",
                "status": "OPEN",
            }
        )

    # Gate passes if no issues (all Hugo build issues are blockers)
    gate_passed = len(issues) == 0

    return gate_passed, issues
