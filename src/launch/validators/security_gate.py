"""Security validation gate for detecting secrets in run output.

Binding contracts:
- specs/09_validation_gates.md (security validation)
- specs/34_strict_compliance_guarantees.md (security requirements)

This gate:
1. Scans all files in RUN_DIR for secrets
2. Reports findings as BLOCKER issues
3. Generates detailed security_report.json
4. Integrates with validation framework
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..security.file_scanner import scan_directory, filter_results_with_secrets, count_total_secrets


def run_security_gate(
    run_dir: Path,
    allowlist: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Run security validation gate on a run directory.

    Args:
        run_dir: Path to RUN_DIR
        allowlist: List of allowlist patterns for files that can contain secrets

    Returns:
        Gate result dictionary with findings
    """
    # Default allowlist for test fixtures
    if allowlist is None:
        allowlist = [
            "test_secrets.py",
            "test_fixtures",
            "test_data",
            ".test.",
        ]

    # Scan all files in run_dir
    results = scan_directory(
        run_dir,
        allowlist=allowlist,
        recursive=True,
        exclude_dirs={".git", "node_modules", "__pycache__", ".venv", "venv", ".pytest_cache"},
    )

    # Filter to only results with secrets
    findings = filter_results_with_secrets(results)

    # Count totals
    total_secrets = count_total_secrets(results)
    files_scanned = len([r for r in results if not r.is_binary and not r.is_allowlisted])

    # Determine if passed (no secrets found)
    passed = total_secrets == 0

    # Build report
    report = {
        "schema_version": "1.0",
        "scan_timestamp": datetime.now(timezone.utc).isoformat(),
        "files_scanned": files_scanned,
        "secrets_found": total_secrets,
        "passed": passed,
        "findings": [],
    }

    # Add detailed findings
    for result in findings:
        finding = {
            "file_path": result.file_path,
            "secrets": [
                {
                    "secret_type": secret.secret_type,
                    "line_number": secret.line_number,
                    "context": secret.context,
                    "confidence": secret.confidence,
                }
                for secret in result.secrets_found
            ],
        }
        report["findings"].append(finding)

    return report


def validate_security(
    run_dir: Path,
    allowlist: Optional[List[str]] = None,
) -> tuple[bool, List[Dict[str, Any]]]:
    """Validate security for integration with validation framework.

    Args:
        run_dir: Path to RUN_DIR
        allowlist: List of allowlist patterns

    Returns:
        Tuple of (passed, issues)
    """
    report = run_security_gate(run_dir, allowlist)

    # Write security report
    artifacts_dir = run_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    report_path = artifacts_dir / "security_report.json"

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, sort_keys=True)
        f.write("\n")

    # Build issues list
    issues: List[Dict[str, Any]] = []

    if not report["passed"]:
        # Create an issue for each finding
        for idx, finding in enumerate(report["findings"]):
            issue = {
                "issue_id": f"iss_security_secret_{idx}",
                "gate": "security",
                "severity": "blocker",
                "error_code": "SECURITY_SECRET_DETECTED",
                "message": f"Secret(s) detected in {finding['file_path']}",
                "files": [finding["file_path"]],
                "suggested_fix": "Remove secrets from code. Use environment variables or secret management service.",
            }
            issues.append(issue)

    return report["passed"], issues
