"""Unit tests for taskcard_validation.py.

Tests taskcard status validation and authorization checks.
"""

import pytest

from launch.util.taskcard_validation import (
    TaskcardInactiveError,
    get_active_status_list,
    get_inactive_status_list,
    is_taskcard_active,
    validate_taskcard_active,
)


class TestIsTaskcardActive:
    """Test is_taskcard_active (non-raising)."""

    def test_active_status_in_progress(self):
        """Test that In-Progress status is active."""
        taskcard = {"id": "TC-100", "status": "In-Progress"}

        assert is_taskcard_active(taskcard) is True

    def test_active_status_done(self):
        """Test that Done status is active."""
        taskcard = {"id": "TC-100", "status": "Done"}

        assert is_taskcard_active(taskcard) is True

    def test_inactive_status_draft(self):
        """Test that Draft status is inactive."""
        taskcard = {"id": "TC-100", "status": "Draft"}

        assert is_taskcard_active(taskcard) is False

    def test_inactive_status_blocked(self):
        """Test that Blocked status is inactive."""
        taskcard = {"id": "TC-100", "status": "Blocked"}

        assert is_taskcard_active(taskcard) is False

    def test_inactive_status_cancelled(self):
        """Test that Cancelled status is inactive."""
        taskcard = {"id": "TC-100", "status": "Cancelled"}

        assert is_taskcard_active(taskcard) is False

    def test_missing_status(self):
        """Test that missing status is inactive."""
        taskcard = {"id": "TC-100"}

        assert is_taskcard_active(taskcard) is False

    def test_invalid_status(self):
        """Test that unknown status is inactive."""
        taskcard = {"id": "TC-100", "status": "UnknownStatus"}

        assert is_taskcard_active(taskcard) is False


class TestValidateTaskcardActive:
    """Test validate_taskcard_active (raising)."""

    def test_validate_active_in_progress(self):
        """Test that In-Progress status passes validation."""
        taskcard = {"id": "TC-100", "status": "In-Progress"}

        # Should not raise
        validate_taskcard_active(taskcard)

    def test_validate_active_done(self):
        """Test that Done status passes validation."""
        taskcard = {"id": "TC-100", "status": "Done"}

        # Should not raise
        validate_taskcard_active(taskcard)

    def test_validate_inactive_draft_raises(self):
        """Test that Draft status raises TaskcardInactiveError."""
        taskcard = {"id": "TC-100", "status": "Draft"}

        with pytest.raises(TaskcardInactiveError) as exc_info:
            validate_taskcard_active(taskcard)

        assert exc_info.value.taskcard_id == "TC-100"
        assert exc_info.value.status == "Draft"
        assert "TC-100" in str(exc_info.value)
        assert "Draft" in str(exc_info.value)
        assert "In-Progress" in str(exc_info.value)

    def test_validate_inactive_blocked_raises(self):
        """Test that Blocked status raises TaskcardInactiveError."""
        taskcard = {"id": "TC-200", "status": "Blocked"}

        with pytest.raises(TaskcardInactiveError) as exc_info:
            validate_taskcard_active(taskcard)

        assert exc_info.value.taskcard_id == "TC-200"
        assert exc_info.value.status == "Blocked"

    def test_validate_missing_status_raises(self):
        """Test that missing status raises TaskcardInactiveError."""
        taskcard = {"id": "TC-300"}

        with pytest.raises(TaskcardInactiveError) as exc_info:
            validate_taskcard_active(taskcard)

        assert exc_info.value.taskcard_id == "TC-300"
        assert exc_info.value.status == "MISSING"

    def test_validate_unknown_status_raises(self):
        """Test that unknown status raises TaskcardInactiveError."""
        taskcard = {"id": "TC-400", "status": "UnknownStatus"}

        with pytest.raises(TaskcardInactiveError) as exc_info:
            validate_taskcard_active(taskcard)

        assert exc_info.value.status == "UnknownStatus"


class TestGetStatusLists:
    """Test status list helpers."""

    def test_get_active_status_list(self):
        """Test that active status list is correct."""
        active = get_active_status_list()

        assert isinstance(active, list)
        assert "In-Progress" in active
        assert "Done" in active
        assert "Draft" not in active
        assert "Blocked" not in active

    def test_get_inactive_status_list(self):
        """Test that inactive status list is correct."""
        inactive = get_inactive_status_list()

        assert isinstance(inactive, list)
        assert "Draft" in inactive
        assert "Blocked" in inactive
        assert "Cancelled" in inactive
        assert "In-Progress" not in inactive
        assert "Done" not in inactive

    def test_status_lists_are_disjoint(self):
        """Test that active and inactive lists don't overlap."""
        active = set(get_active_status_list())
        inactive = set(get_inactive_status_list())

        # Should have no overlap
        assert len(active & inactive) == 0

    def test_status_lists_are_sorted(self):
        """Test that status lists are sorted (deterministic)."""
        active = get_active_status_list()
        inactive = get_inactive_status_list()

        assert active == sorted(active)
        assert inactive == sorted(inactive)
