"""TC-GLD-016: Tests for word count depth enforcement logic.

Verifies that the depth enforcement threshold correctly identifies sections
whose prose count is below 50% of the golden word target, and that the
_depth_retried flag caps retries at 1.
"""
from __future__ import annotations

import pytest


def _check_depth_too_thin(
    prose_count: int,
    golden_word_targets: dict[str, int] | None,
    heading: str,
    depth_retried: bool,
) -> bool:
    """Extract the depth enforcement logic from worker.py for isolated testing.

    This mirrors the TC-GLD-016 block in generate/worker.py exactly:
    - prose_ok is assumed True (we only test the depth threshold)
    - Returns True if section is too thin and needs a depth retry
    """
    _prose_ok = True  # Assumed: prose already passed the 30-word floor
    if _prose_ok and not depth_retried:
        _gwt = golden_word_targets or {}
        _golden_target = _gwt.get(heading, 0)
        if _golden_target > 0 and prose_count < _golden_target * 0.5:
            return True
    return False


class TestDepthEnforcement:
    """TC-GLD-016: Word count depth enforcement threshold."""

    def test_thin_section_detected(self):
        """Section at 40% of golden target (below 50%) must be flagged."""
        assert _check_depth_too_thin(
            prose_count=80,
            golden_word_targets={"Installation": 200},
            heading="Installation",
            depth_retried=False,
        )

    def test_adequate_section_not_flagged(self):
        """Section at 60% of golden target (above 50%) must NOT be flagged."""
        assert not _check_depth_too_thin(
            prose_count=120,
            golden_word_targets={"Installation": 200},
            heading="Installation",
            depth_retried=False,
        )

    def test_exact_boundary_not_flagged(self):
        """Section at exactly 50% of golden target must NOT be flagged (>=, not >)."""
        assert not _check_depth_too_thin(
            prose_count=100,
            golden_word_targets={"Installation": 200},
            heading="Installation",
            depth_retried=False,
        )

    def test_boundary_minus_one_flagged(self):
        """Section at 49.5% of golden target (just below 50%) must be flagged."""
        assert _check_depth_too_thin(
            prose_count=99,
            golden_word_targets={"Installation": 200},
            heading="Installation",
            depth_retried=False,
        )

    def test_no_golden_target_not_flagged(self):
        """When no golden word target exists for heading, never flag."""
        assert not _check_depth_too_thin(
            prose_count=10,
            golden_word_targets={"OtherSection": 200},
            heading="Installation",
            depth_retried=False,
        )

    def test_none_golden_targets_not_flagged(self):
        """When golden_word_targets is None, never flag."""
        assert not _check_depth_too_thin(
            prose_count=10,
            golden_word_targets=None,
            heading="Installation",
            depth_retried=False,
        )

    def test_empty_golden_targets_not_flagged(self):
        """When golden_word_targets is empty dict, never flag."""
        assert not _check_depth_too_thin(
            prose_count=10,
            golden_word_targets={},
            heading="Installation",
            depth_retried=False,
        )

    def test_zero_golden_target_not_flagged(self):
        """When golden target is 0, never flag (guard: _golden_target > 0)."""
        assert not _check_depth_too_thin(
            prose_count=10,
            golden_word_targets={"Installation": 0},
            heading="Installation",
            depth_retried=False,
        )

    def test_already_retried_not_flagged(self):
        """When _depth_retried is True, never flag (cap at 1 retry)."""
        assert not _check_depth_too_thin(
            prose_count=10,
            golden_word_targets={"Installation": 200},
            heading="Installation",
            depth_retried=True,
        )

    def test_very_thin_section(self):
        """Section at 5% of golden target must be flagged."""
        assert _check_depth_too_thin(
            prose_count=10,
            golden_word_targets={"Overview": 200},
            heading="Overview",
            depth_retried=False,
        )
