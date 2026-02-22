"""Severity-weighted quality gate for W7 ContentReviewer.

Reference: content-generator src/agents/support/quality_gate.py
"""
from __future__ import annotations
from typing import Any, Dict, List

# Check severity weights (1.0=critical, 0.75=high, 0.5=medium, 0.25=low)
CHECK_SEVERITY: Dict[str, float] = {
    # Critical — any failure → not PASS
    "code_syntax":            1.0,
    "frontmatter_required":   1.0,
    "claim_validity":         1.0,
    "fence_balance":          1.0,
    # High
    "seo_title_length":       0.75,
    "seo_description_length": 0.75,
    "api_hallucination":      0.75,
    "technical_accuracy":     0.75,
    # Medium
    "content_length":         0.5,
    "keyword_density":        0.5,
    "heading_descriptiveness":0.5,
    "example_clarity":        0.5,
    # Low
    "grammar_style":          0.25,
    "bullet_length":          0.25,
}

SEVERITY_THRESHOLDS = {
    "critical_failures_allowed": 0,   # Any critical → not PASS
    "warn_for_review": 5,             # >5 warnings → REVIEW
    "warn_for_fail": 10,              # >10 warnings → FAIL
}


def compute_weighted_score(check_results: List[Dict[str, Any]]) -> float:
    """Return 0.0-1.0 weighted score across all checks."""
    total = sum(CHECK_SEVERITY.get(c.get("name", ""), 0.5) for c in check_results)
    passed = sum(
        CHECK_SEVERITY.get(c.get("name", ""), 0.5)
        for c in check_results
        if c.get("passed", False)
    )
    return passed / total if total else 1.0


def decide_quality_outcome(check_results: List[Dict[str, Any]]) -> str:
    """Return 'PASS', 'REVIEW', or 'FAIL' based on check results.

    Reference: content-generator quality_gate.py
    """
    critical_failures = [
        c for c in check_results
        if CHECK_SEVERITY.get(c.get("name", ""), 0.5) >= 1.0
        and not c.get("passed", True)
    ]
    all_failures = [c for c in check_results if not c.get("passed", True)]

    if critical_failures:
        return "FAIL"

    num_warnings = len(all_failures)
    if num_warnings > SEVERITY_THRESHOLDS["warn_for_fail"]:
        return "FAIL"
    if num_warnings > SEVERITY_THRESHOLDS["warn_for_review"]:
        return "REVIEW"

    return "PASS"


def get_check_severity(check_name: str) -> float:
    """Get severity weight for a check (defaults to 0.5 if unknown)."""
    return CHECK_SEVERITY.get(check_name, 0.5)
