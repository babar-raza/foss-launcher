"""Tests for TC-2396: Three-layer quality gate."""
import pytest
from launch.workers.w7_content_reviewer.checks.quality_gate import (
    decide_quality_outcome,
    compute_weighted_score,
    get_check_severity,
    CHECK_SEVERITY,
)


def test_decide_quality_outcome_pass():
    """All checks pass → PASS."""
    checks = [
        {"name": "code_syntax", "passed": True},
        {"name": "frontmatter_required", "passed": True},
        {"name": "grammar_style", "passed": True},
    ]
    assert decide_quality_outcome(checks) == "PASS"


def test_decide_quality_outcome_critical_fail():
    """One critical failure → FAIL (regardless of other checks)."""
    checks = [
        {"name": "code_syntax", "passed": False},   # critical
        {"name": "grammar_style", "passed": True},
    ]
    assert decide_quality_outcome(checks) == "FAIL"


def test_decide_quality_outcome_review():
    """6 non-critical failures → REVIEW (>5 threshold)."""
    checks = [
        {"name": "grammar_style", "passed": False},
        {"name": "bullet_length", "passed": False},
        {"name": "content_length", "passed": False},
        {"name": "keyword_density", "passed": False},
        {"name": "heading_descriptiveness", "passed": False},
        {"name": "example_clarity", "passed": False},
    ]
    assert decide_quality_outcome(checks) == "REVIEW"


def test_decide_quality_outcome_fail_too_many_warnings():
    """11 failures → FAIL (>10 threshold)."""
    checks = [{"name": "grammar_style", "passed": False}] * 11
    assert decide_quality_outcome(checks) == "FAIL"


def test_compute_weighted_score_all_pass():
    """All checks pass → score == 1.0."""
    checks = [
        {"name": "code_syntax", "passed": True},
        {"name": "grammar_style", "passed": True},
    ]
    assert compute_weighted_score(checks) == 1.0


def test_compute_weighted_score_mixed():
    """Critical check failed, low check passed → score between 0 and 1."""
    checks = [
        {"name": "code_syntax", "passed": False},   # weight 1.0
        {"name": "grammar_style", "passed": True},   # weight 0.25
    ]
    score = compute_weighted_score(checks)
    assert 0.0 < score < 1.0


def test_get_check_severity_known():
    """Known check name returns its declared weight."""
    assert get_check_severity("code_syntax") == 1.0
    assert get_check_severity("grammar_style") == 0.25


def test_get_check_severity_unknown():
    """Unknown check name defaults to 0.5."""
    assert get_check_severity("nonexistent_check") == 0.5


def test_decide_quality_outcome_empty():
    """No checks → PASS (nothing failed)."""
    assert decide_quality_outcome([]) == "PASS"
