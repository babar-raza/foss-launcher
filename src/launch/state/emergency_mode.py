"""Emergency mode detection and handling for manual content edits.

This module implements the emergency mode flag (`allow_manual_edits`) that serves
as an escape hatch for manual content modifications. By default, manual edits are
strictly forbidden as per `plans/policies/no_manual_content_edits.md`.

When enabled, this mode allows manual edits but enforces strict documentation
requirements in the validation report and orchestrator master review.

Spec references:
- specs/11_state_and_events.md
- specs/12_pr_and_release.md
- plans/policies/no_manual_content_edits.md
- specs/schemas/run_config.schema.json
- specs/schemas/validation_report.schema.json
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict


def is_emergency_mode_enabled(run_config: Dict[str, Any]) -> bool:
    """Check if emergency mode (allow_manual_edits) is enabled in run_config.

    Args:
        run_config: Loaded and validated run_config dictionary

    Returns:
        True if allow_manual_edits is explicitly set to true, False otherwise

    Note:
        Default is False as per specs/schemas/run_config.schema.json line 453-456.
        Emergency mode should only be used when absolutely necessary and with
        full documentation of affected files and rationale.
    """
    return run_config.get("allow_manual_edits", False)


def get_emergency_mode_config(run_config: Dict[str, Any]) -> Dict[str, bool]:
    """Extract emergency mode configuration from run_config.

    Args:
        run_config: Loaded and validated run_config dictionary

    Returns:
        Dictionary with emergency mode settings:
        - allow_manual_edits: Whether manual edits are permitted

    Note:
        This function provides a structured interface for accessing emergency
        mode settings, making it easier to extend with additional flags in future.
    """
    return {
        "allow_manual_edits": is_emergency_mode_enabled(run_config)
    }


def validate_emergency_mode_preconditions(
    run_config: Dict[str, Any],
    validation_report: Dict[str, Any] | None = None
) -> tuple[bool, list[str]]:
    """Validate that all emergency mode preconditions are met.

    As per plans/policies/no_manual_content_edits.md, emergency mode requires:
    1. run_config flag `allow_manual_edits: true`
    2. validation_report enumerates affected files and sets `manual_edits=true`
    3. orchestrator master review lists affected files and rationale (checked separately)

    Args:
        run_config: Loaded and validated run_config dictionary
        validation_report: Optional validation report to check for manual_edits field

    Returns:
        Tuple of (valid, errors):
        - valid: True if all preconditions are met
        - errors: List of error messages describing missing preconditions
    """
    errors = []

    # Check if emergency mode is enabled
    if not is_emergency_mode_enabled(run_config):
        errors.append(
            "Emergency mode not enabled: run_config.allow_manual_edits must be true"
        )

    # If validation_report provided, check manual_edits field
    if validation_report is not None:
        if not validation_report.get("manual_edits", False):
            errors.append(
                "validation_report.manual_edits must be true when manual edits occurred"
            )

        # Check that manual_edited_files is present and non-empty when manual_edits=true
        if validation_report.get("manual_edits", False):
            manual_files = validation_report.get("manual_edited_files", [])
            if not manual_files:
                errors.append(
                    "validation_report.manual_edited_files must enumerate all manually "
                    "edited files when manual_edits=true"
                )

    return len(errors) == 0, errors


def format_emergency_mode_warning(manual_files: list[str]) -> str:
    """Format a warning message for emergency mode usage.

    Args:
        manual_files: List of manually edited file paths

    Returns:
        Formatted warning message for logs and reports
    """
    file_list = "\n".join(f"  - {f}" for f in sorted(manual_files))
    return (
        f"EMERGENCY MODE ACTIVE: Manual content edits detected\n"
        f"Affected files ({len(manual_files)}):\n"
        f"{file_list}\n"
        f"\n"
        f"This run bypassed automated content generation. All changes must be "
        f"documented in the orchestrator master review with full rationale."
    )
