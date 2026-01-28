"""Policy enforcement for orchestrator master review.

This module implements orchestrator-level policy enforcement, particularly for
emergency mode (manual edits) compliance checking. When manual edits are used,
the orchestrator must explicitly document all affected files and rationale.

Spec references:
- specs/12_pr_and_release.md (PR requirements)
- plans/policies/no_manual_content_edits.md (enforcement rules)
- specs/schemas/validation_report.schema.json
- specs/schemas/issue.schema.json
"""

from __future__ import annotations

from typing import Any, Dict, List

from ..state.emergency_mode import is_emergency_mode_enabled


def check_manual_edits_documentation(
    run_config: Dict[str, Any],
    validation_report: Dict[str, Any],
    master_review: Dict[str, Any] | None = None
) -> tuple[bool, List[Dict[str, Any]]]:
    """Check that manual edits are properly documented when emergency mode is used.

    As per plans/policies/no_manual_content_edits.md, when allow_manual_edits=true
    and manual edits occurred, the orchestrator master review must:
    1. List all affected files
    2. Provide rationale for each manual edit

    Args:
        run_config: Loaded and validated run_config dictionary
        validation_report: Validation report with manual_edits status
        master_review: Optional orchestrator master review document

    Returns:
        Tuple of (ok, issues):
        - ok: True if documentation requirements are met
        - issues: List of Issue dictionaries for any violations

    Note:
        This function creates BLOCKER issues when manual edits are used without
        proper documentation, preventing PR creation until resolved.
    """
    issues = []

    # If emergency mode not enabled, nothing to check
    if not is_emergency_mode_enabled(run_config):
        return True, []

    # Check if manual edits occurred
    manual_edits = validation_report.get("manual_edits", False)
    if not manual_edits:
        return True, []

    # Get list of manually edited files
    manual_files = validation_report.get("manual_edited_files", [])
    if not manual_files:
        issues.append({
            "issue_id": "POLICY_001",
            "gate": "policy_enforcement",
            "severity": "blocker",
            "error_code": "MANUAL_EDITS_NOT_ENUMERATED",
            "message": (
                "Emergency mode active but validation_report.manual_edited_files is empty. "
                "All manually edited files must be enumerated."
            ),
            "files": [],
            "status": "OPEN"
        })
        return False, issues

    # Check master review documentation
    if master_review is None:
        issues.append({
            "issue_id": "POLICY_002",
            "gate": "policy_enforcement",
            "severity": "blocker",
            "error_code": "MASTER_REVIEW_MISSING",
            "message": (
                f"Emergency mode used with {len(manual_files)} manual edits, but orchestrator "
                f"master review is missing. Master review must list affected files and rationale."
            ),
            "files": manual_files,
            "status": "OPEN"
        })
        return False, issues

    # Validate master review contains manual edits section
    manual_edits_section = master_review.get("manual_edits")
    if not manual_edits_section:
        issues.append({
            "issue_id": "POLICY_003",
            "gate": "policy_enforcement",
            "severity": "blocker",
            "error_code": "MASTER_REVIEW_NO_MANUAL_EDITS_SECTION",
            "message": (
                f"Master review missing 'manual_edits' section. Emergency mode used with "
                f"{len(manual_files)} files modified."
            ),
            "files": manual_files,
            "status": "OPEN"
        })
        return False, issues

    # Validate all files are documented
    documented_files = set(manual_edits_section.get("files", []))
    undocumented = set(manual_files) - documented_files
    if undocumented:
        issues.append({
            "issue_id": "POLICY_004",
            "gate": "policy_enforcement",
            "severity": "blocker",
            "error_code": "MANUAL_EDITS_UNDOCUMENTED_FILES",
            "message": (
                f"Master review does not document all manually edited files. "
                f"Missing: {sorted(undocumented)}"
            ),
            "files": list(undocumented),
            "status": "OPEN"
        })
        return False, issues

    # Validate rationale is provided
    rationale = manual_edits_section.get("rationale")
    if not rationale or len(rationale.strip()) < 20:
        issues.append({
            "issue_id": "POLICY_005",
            "gate": "policy_enforcement",
            "severity": "blocker",
            "error_code": "MASTER_REVIEW_INSUFFICIENT_RATIONALE",
            "message": (
                "Master review must provide detailed rationale (minimum 20 characters) "
                "explaining why manual edits were necessary."
            ),
            "files": manual_files,
            "status": "OPEN"
        })
        return False, issues

    return True, []


def enforce_pr_requirements(
    run_config: Dict[str, Any],
    validation_report: Dict[str, Any],
    pr_data: Dict[str, Any] | None = None
) -> tuple[bool, List[Dict[str, Any]]]:
    """Enforce PR requirements including emergency mode documentation.

    As per specs/12_pr_and_release.md, PRs must include:
    - Summary of what was launched
    - Page inventory by section with links
    - Evidence summary
    - Validation checklist results
    - Emergency mode documentation (if applicable)

    Args:
        run_config: Loaded and validated run_config dictionary
        validation_report: Validation report
        pr_data: Optional PR description/metadata

    Returns:
        Tuple of (ok, issues):
        - ok: True if all PR requirements are met
        - issues: List of Issue dictionaries for any violations
    """
    issues = []

    # If no PR data, cannot validate (may be intentional in local mode)
    if pr_data is None:
        return True, []

    # Check emergency mode documentation in PR body
    if is_emergency_mode_enabled(run_config):
        manual_edits = validation_report.get("manual_edits", False)
        if manual_edits:
            pr_body = pr_data.get("body", "")
            if "emergency mode" not in pr_body.lower() and "manual edit" not in pr_body.lower():
                manual_files = validation_report.get("manual_edited_files", [])
                issues.append({
                    "issue_id": "POLICY_006",
                    "gate": "policy_enforcement",
                    "severity": "blocker",
                    "error_code": "PR_MISSING_EMERGENCY_MODE_NOTICE",
                    "message": (
                        f"PR description must include emergency mode notice when manual edits "
                        f"are used. {len(manual_files)} files were manually edited."
                    ),
                    "files": manual_files,
                    "suggested_fix": (
                        "Add an 'Emergency Mode' section to PR body listing all manually edited "
                        "files and rationale."
                    ),
                    "status": "OPEN"
                })
                return False, issues

    return True, []


def create_policy_enforcement_report(
    run_config: Dict[str, Any],
    validation_report: Dict[str, Any],
    master_review: Dict[str, Any] | None = None,
    pr_data: Dict[str, Any] | None = None
) -> Dict[str, Any]:
    """Create a comprehensive policy enforcement report.

    Args:
        run_config: Loaded and validated run_config dictionary
        validation_report: Validation report
        master_review: Optional orchestrator master review
        pr_data: Optional PR description/metadata

    Returns:
        Policy enforcement report with all checks and issues
    """
    all_issues = []

    # Check manual edits documentation
    docs_ok, docs_issues = check_manual_edits_documentation(
        run_config, validation_report, master_review
    )
    all_issues.extend(docs_issues)

    # Check PR requirements
    pr_ok, pr_issues = enforce_pr_requirements(
        run_config, validation_report, pr_data
    )
    all_issues.extend(pr_issues)

    overall_ok = docs_ok and pr_ok

    return {
        "ok": overall_ok,
        "emergency_mode_enabled": is_emergency_mode_enabled(run_config),
        "manual_edits_occurred": validation_report.get("manual_edits", False),
        "checks": {
            "manual_edits_documentation": docs_ok,
            "pr_requirements": pr_ok
        },
        "issues": all_issues,
        "blocker_count": sum(1 for issue in all_issues if issue["severity"] == "blocker")
    }
