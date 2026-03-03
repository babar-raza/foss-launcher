"""Unit tests for W7 review pilot promotion (TC-3676).

Tests that _is_review_required returns True for pilot profile
and that gate_review_report_required has error severity for pilot.
"""

from __future__ import annotations

import pytest

from launch.orchestrator.graph import _is_review_required
from launch.workers.w9_validator.gates.gate_review_report_required import (
    _severity_for_profile,
)


class TestIsReviewRequiredPilot:
    """TC-3676: _is_review_required should return True for pilot profile."""

    def test_pilot_requires_review(self):
        config = {"validation_profile": "pilot"}
        assert _is_review_required(config) is True

    def test_ci_requires_review(self):
        config = {"validation_profile": "ci"}
        assert _is_review_required(config) is True

    def test_prod_requires_review(self):
        config = {"validation_profile": "prod"}
        assert _is_review_required(config) is True

    def test_local_does_not_require_review(self):
        config = {"validation_profile": "local"}
        assert _is_review_required(config) is False

    def test_explicit_override_wins(self):
        config = {"validation_profile": "local", "review_required": True}
        assert _is_review_required(config) is True

    def test_explicit_false_overrides_pilot(self):
        config = {"validation_profile": "pilot", "review_required": False}
        assert _is_review_required(config) is False


class TestSeverityForProfilePilot:
    """TC-3676: _severity_for_profile should return error for pilot."""

    def test_pilot_is_error(self):
        assert _severity_for_profile("pilot") == "error"

    def test_ci_is_error(self):
        assert _severity_for_profile("ci") == "error"

    def test_prod_is_blocker(self):
        assert _severity_for_profile("prod") == "blocker"

    def test_local_is_info(self):
        assert _severity_for_profile("local") == "info"
