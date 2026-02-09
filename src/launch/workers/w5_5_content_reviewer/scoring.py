"""Scoring and routing logic for W5.5 ContentReviewer.

This module implements the scoring rubric and routing logic that determines
whether content passes review, needs changes, or must be rejected.

TC-1100-P1: W5.5 ContentReviewer Phase 1 - Core Review Logic
Pattern: Integrator pattern (similar to W2 worker.py orchestration)

Spec reference: abstract-hugging-kite.md:484-556 (Scoring Rubric)
"""

from typing import Dict, List, Any


def calculate_scores(issues: List[Dict[str, Any]]) -> Dict[str, int]:
    """Calculate dimension scores (1-5) based on issues found.

    Scoring rubric per dimension:
    - 5: Zero issues
    - 4: Minor issues only (1-3 WARNs), auto-fixable
    - 3: Moderate issues (4-6 WARNs or 1-2 ERRORs)
    - 2: Major issues (>6 WARNs or 3+ ERRORs)
    - 1: Critical issues (BLOCKERs present)

    Args:
        issues: List of issue dicts from check modules
                Each dict has: check, severity, message, location, etc.

    Returns:
        Dict with keys: content_quality, technical_accuracy, usability
        Values are scores 1-5

    Spec reference: abstract-hugging-kite.md:484-534
    """
    # Group issues by dimension
    dimension_issues = {
        'content_quality': [],
        'technical_accuracy': [],
        'usability': [],
    }

    for issue in issues:
        check_name = issue.get('check', '')
        severity = issue.get('severity', 'warn')

        # Determine dimension from check name
        if check_name.startswith('content_quality.'):
            dimension_issues['content_quality'].append((severity, issue))
        elif check_name.startswith('technical_accuracy.'):
            dimension_issues['technical_accuracy'].append((severity, issue))
        elif check_name.startswith('usability.'):
            dimension_issues['usability'].append((severity, issue))

    # Calculate score per dimension
    scores = {}
    for dimension, dim_issues in dimension_issues.items():
        scores[dimension] = _calculate_dimension_score(dim_issues)

    return scores


def _calculate_dimension_score(issues: List[tuple]) -> int:
    """Calculate score (1-5) for a single dimension.

    Rubric:
    - 5: Zero issues
    - 4: Minor issues only (1-3 WARNs), auto-fixable
    - 3: Moderate issues (4-6 WARNs or 1-2 ERRORs)
    - 2: Major issues (>6 WARNs or 3+ ERRORs)
    - 1: Critical issues (BLOCKERs present)

    Args:
        issues: List of (severity, issue_dict) tuples

    Returns:
        Score 1-5
    """
    if not issues:
        return 5  # Zero issues = perfect score

    # Count by severity
    blocker_count = sum(1 for sev, _ in issues if sev == 'blocker')
    error_count = sum(1 for sev, _ in issues if sev == 'error')
    warn_count = sum(1 for sev, _ in issues if sev == 'warn')

    # Count auto-fixable issues
    auto_fixable_count = sum(1 for _, iss in issues if iss.get('auto_fixable', False))

    # Apply rubric
    if blocker_count > 0:
        return 1  # Critical: BLOCKERs present

    if error_count >= 3:
        return 2  # Major: 3+ ERRORs

    if warn_count > 6:
        return 2  # Major: >6 WARNs

    if error_count >= 1:
        return 3  # Moderate: 1-2 ERRORs

    if warn_count >= 4:
        return 3  # Moderate: 4-6 WARNs

    # Minor issues: 1-3 WARNs
    if warn_count >= 1:
        # If all minor issues are auto-fixable, score is 4
        if auto_fixable_count == len(issues):
            return 4
        else:
            return 3  # Not all auto-fixable = moderate

    return 5  # Should not reach here, but default to perfect


def route_review_result(scores: Dict[str, int], issues: List[Dict[str, Any]]) -> str:
    """Route content based on scores and issues.

    Routing logic:
    - PASS: all dimensions ≥4, zero BLOCKER/ERROR (or all auto-fixed), <5 WARNs per page
    - NEEDS_CHANGES: any dimension = 3, 1-2 ERRORs, 5-10 WARNs per page
    - REJECT: any dimension ≤2, any BLOCKER, 3+ ERRORs, >10 WARNs per page

    Args:
        scores: Dimension scores from calculate_scores()
        issues: List of issue dicts (for additional routing logic)

    Returns:
        "PASS", "NEEDS_CHANGES", or "REJECT"

    Spec reference: abstract-hugging-kite.md:536-556
    """
    # Count severity levels
    blocker_count = sum(1 for iss in issues if iss.get('severity') == 'blocker')
    error_count = sum(1 for iss in issues if iss.get('severity') == 'error')
    warn_count = sum(1 for iss in issues if iss.get('severity') == 'warn')

    # Count auto-fixable errors
    auto_fixable_error_count = sum(
        1 for iss in issues
        if iss.get('severity') == 'error' and iss.get('auto_fixable', False)
    )

    # REJECT conditions
    if blocker_count > 0:
        return "REJECT"  # Any BLOCKER = reject

    if any(score <= 2 for score in scores.values()):
        return "REJECT"  # Any dimension ≤2 = reject

    if error_count >= 3 and (error_count - auto_fixable_error_count) >= 3:
        return "REJECT"  # 3+ non-auto-fixable errors = reject

    # Estimate pages (rough heuristic: group issues by location path)
    pages = set()
    for iss in issues:
        loc = iss.get('location', {})
        path = loc.get('path', 'unknown')
        pages.add(path)

    num_pages = max(1, len(pages))  # Avoid division by zero
    warns_per_page = warn_count / num_pages

    if warns_per_page > 10:
        return "REJECT"  # >10 warns per page = reject

    # NEEDS_CHANGES conditions
    if any(score == 3 for score in scores.values()):
        return "NEEDS_CHANGES"  # Any dimension = 3

    if error_count >= 1 and (error_count - auto_fixable_error_count) >= 1:
        return "NEEDS_CHANGES"  # 1-2 non-auto-fixable errors

    if 5 <= warns_per_page <= 10:
        return "NEEDS_CHANGES"  # 5-10 warns per page

    # PASS conditions
    if all(score >= 4 for score in scores.values()):
        # All dimensions ≥4
        if error_count == 0 or error_count == auto_fixable_error_count:
            # Zero errors OR all errors auto-fixable
            if warns_per_page < 5:
                return "PASS"

    # Default to NEEDS_CHANGES if unclear
    return "NEEDS_CHANGES"
