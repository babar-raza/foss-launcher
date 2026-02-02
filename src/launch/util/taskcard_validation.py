"""Taskcard validation utilities.

Validates taskcard status and authorization for write operations.
Enforces write fence policy per specs/34_strict_compliance_guarantees.md.

Spec references:
- plans/taskcards/00_TASKCARD_CONTRACT.md (Taskcard lifecycle)
- specs/34_strict_compliance_guarantees.md (Guarantee E: Write fence)
"""

from __future__ import annotations

from typing import Any, Dict

from .taskcard_loader import TaskcardError, get_taskcard_status


class TaskcardInactiveError(TaskcardError):
    """Taskcard is not in active status."""

    def __init__(self, taskcard_id: str, status: str):
        super().__init__(
            f"Taskcard {taskcard_id} is not active (status: {status}). "
            f"Only taskcards with status 'In-Progress' or 'Done' can authorize writes."
        )
        self.taskcard_id = taskcard_id
        self.status = status


# Active statuses that authorize file writes
ACTIVE_STATUSES = {"In-Progress", "Done"}

# Inactive statuses that block file writes
INACTIVE_STATUSES = {"Draft", "Blocked", "Cancelled"}


def is_taskcard_active(taskcard: Dict[str, Any]) -> bool:
    """Check if taskcard is in active status (non-raising).

    Args:
        taskcard: Taskcard frontmatter dictionary

    Returns:
        True if taskcard has active status, False otherwise

    Examples:
        >>> tc = {"status": "In-Progress"}
        >>> is_taskcard_active(tc)
        True

        >>> tc = {"status": "Draft"}
        >>> is_taskcard_active(tc)
        False

        >>> tc = {}  # Missing status
        >>> is_taskcard_active(tc)
        False
    """
    status = get_taskcard_status(taskcard)
    return status in ACTIVE_STATUSES


def validate_taskcard_active(taskcard: Dict[str, Any]) -> None:
    """Validate that taskcard is in active status (raising).

    Args:
        taskcard: Taskcard frontmatter dictionary

    Raises:
        TaskcardInactiveError: If taskcard is not active

    Examples:
        >>> tc = {"id": "TC-100", "status": "In-Progress"}
        >>> validate_taskcard_active(tc)  # No error

        >>> tc = {"id": "TC-100", "status": "Draft"}
        >>> validate_taskcard_active(tc)
        TaskcardInactiveError: Taskcard TC-100 is not active (status: Draft)...
    """
    status = get_taskcard_status(taskcard)
    taskcard_id = taskcard.get("id", "UNKNOWN")

    if status is None:
        raise TaskcardInactiveError(taskcard_id, "MISSING")

    if status not in ACTIVE_STATUSES:
        raise TaskcardInactiveError(taskcard_id, status)


def get_active_status_list() -> list[str]:
    """Get list of active statuses.

    Returns:
        List of status values considered active

    Examples:
        >>> get_active_status_list()
        ['In-Progress', 'Done']
    """
    return sorted(ACTIVE_STATUSES)


def get_inactive_status_list() -> list[str]:
    """Get list of inactive statuses.

    Returns:
        List of status values considered inactive

    Examples:
        >>> get_inactive_status_list()
        ['Blocked', 'Cancelled', 'Draft']
    """
    return sorted(INACTIVE_STATUSES)
