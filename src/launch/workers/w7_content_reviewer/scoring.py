"""Scoring and routing logic for W7 ContentReviewer.

This module implements the scoring rubric and routing logic that determines
whether content passes review, needs changes, or must be rejected.

TC-1100-P1: W7 ContentReviewer Phase 1 - Core Review Logic
Pattern: Integrator pattern (similar to W2 worker.py orchestration)

Spec reference: abstract-hugging-kite.md:484-556 (Scoring Rubric)
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


def calculate_scores(issues: List[Dict[str, Any]], num_pages: int = 0) -> Dict[str, int]:
    """Calculate dimension scores (1-5) based on issues found.

    Scoring rubric per dimension (density-aware, per-page thresholds):
    - 5: Zero issues
    - 4: Minor issues only (< 4 WARNs/page)
    - 3: Moderate issues (4-6 WARNs/page or 1-2 ERRORs)
    - 2: Major issues (>6 WARNs/page or 3+ ERRORs)
    - 1: Critical issues (BLOCKERs present)

    When num_pages=1 (default for single-page or tests without location fields),
    density thresholds produce identical results to absolute counts.

    Args:
        issues: List of issue dicts from check modules
                Each dict has: check, severity, message, location, etc.
        num_pages: Number of pages being reviewed. If 0 or negative,
                   auto-detected from unique issue location paths.

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
        elif check_name.startswith('formatting_quality.'):
            # Phase 0 (TC-2360) formatting defects count against content quality
            dimension_issues['content_quality'].append((severity, issue))

    # Derive page count from issue locations if not provided
    if num_pages <= 0:
        pages = set()
        for issue in issues:
            path = str(issue.get('location', {}).get('path', 'unknown'))
            pages.add(path)
        num_pages = max(1, len(pages))

    # Calculate score per dimension
    scores = {}
    for dimension, dim_issues in dimension_issues.items():
        scores[dimension] = _calculate_dimension_score(dim_issues, num_pages)

    return scores


def _calculate_dimension_score(issues: List[tuple], num_pages: int = 1) -> int:
    """Calculate score (1-5) for a single dimension using density-aware thresholds.

    BLOCKER-2b fix: Uses per-page warning density instead of absolute counts.
    When num_pages=1 (default), thresholds are identical to absolute counts,
    ensuring full backward compatibility with existing tests.

    Rubric (density-aware):
    - 5: Zero issues
    - 4: Minor issues only (< 4.0 WARNs/page)
    - 3: Moderate issues (4.0-6.0 WARNs/page or 1-2 ERRORs)
    - 2: Major issues (>6.0 WARNs/page or 3+ ERRORs)
    - 1: Critical issues (BLOCKERs present)

    Args:
        issues: List of (severity, issue_dict) tuples
        num_pages: Number of pages being reviewed (default 1)

    Returns:
        Score 1-5
    """
    if not issues:
        return 5  # Zero issues = perfect score

    # Count by severity
    blocker_count = sum(1 for sev, _ in issues if sev == 'blocker')
    error_count = sum(1 for sev, _ in issues if sev == 'error')
    warn_count = sum(1 for sev, _ in issues if sev == 'warn')

    # Density-aware: convert absolute warn count to per-page density
    num_pages = max(1, num_pages)
    warns_per_page = warn_count / num_pages

    # Apply rubric (density-aware thresholds)
    if blocker_count > 0:
        return 1  # Critical: BLOCKERs present

    if error_count >= 3:
        return 2  # Major: 3+ ERRORs

    if warns_per_page > 6.0:
        return 2  # Major: >6 WARNs/page

    if error_count >= 1:
        return 3  # Moderate: 1-2 ERRORs

    if warns_per_page >= 4.0:
        return 3  # Moderate: 4-6 WARNs/page

    # Minor issues: < 4 WARNs/page with zero errors
    if warn_count >= 1:
        return 4  # PASS-worthy

    return 5  # Should not reach here, but default to perfect


def calculate_per_page_scores(
    issues: List[Dict[str, Any]],
) -> Dict[str, Dict[str, int]]:
    """Calculate dimension scores per page independently.

    TC-1752: Each page gets its own set of scores (content_quality, technical_accuracy,
    usability). This enables identifying specific weak pages during calibration.

    Args:
        issues: List of issue dicts, each with location.path identifying the page.

    Returns:
        Dict mapping page path to dimension scores.
        Example: {"docs/guide.md": {"content_quality": 4, "technical_accuracy": 5, "usability": 3}}
    """
    # Group issues by page path
    page_issues: Dict[str, List[Dict[str, Any]]] = {}
    for issue in issues:
        path = str(issue.get("location", {}).get("path", "unknown"))
        page_issues.setdefault(path, []).append(issue)

    # Score each page independently (num_pages=1 per page)
    per_page_scores = {}
    for page_path, page_issue_list in page_issues.items():
        per_page_scores[page_path] = calculate_scores(page_issue_list, num_pages=1)

    return per_page_scores


def check_publication_readiness(
    per_page_scores: Dict[str, Dict[str, int]],
    threshold: int = 4,
    pass_rate: float = 0.8,
) -> Dict[str, Any]:
    """Check if content meets publication readiness criteria.

    TC-1752: Publication-ready when >= pass_rate of pages have all dimensions >= threshold.

    Args:
        per_page_scores: Per-page scores from calculate_per_page_scores().
        threshold: Minimum score per dimension (default 4 = PASS-worthy).
        pass_rate: Fraction of pages that must meet threshold (default 0.8 = 80%).

    Returns:
        Dict with:
        - ready: bool - meets publication criteria
        - total_pages: int
        - passing_pages: int
        - failing_pages: list of {path, scores, failing_dimensions}
        - actual_pass_rate: float
    """
    total_pages = len(per_page_scores)
    if total_pages == 0:
        return {
            "ready": True,
            "total_pages": 0,
            "passing_pages": 0,
            "failing_pages": [],
            "actual_pass_rate": 1.0,
        }

    passing_pages = 0
    failing_pages = []

    for page_path, scores in per_page_scores.items():
        failing_dims = [
            dim for dim, score in scores.items() if score < threshold
        ]
        if not failing_dims:
            passing_pages += 1
        else:
            failing_pages.append({
                "path": page_path,
                "scores": scores,
                "failing_dimensions": failing_dims,
            })

    actual_pass_rate = passing_pages / total_pages

    return {
        "ready": actual_pass_rate >= pass_rate,
        "total_pages": total_pages,
        "passing_pages": passing_pages,
        "failing_pages": failing_pages,
        "actual_pass_rate": round(actual_pass_rate, 3),
    }


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
        path = str(loc.get('path', 'unknown'))
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


def verify_scores_with_llm(
    llm_client,
    dimension_scores: Dict[str, int],
    issues: List[Dict],
    deterministic_status: str,
    draft_samples: Dict[str, str],
) -> Optional[Dict[str, Any]]:
    """LLM verifies deterministic scores and detects edge cases.

    TC-2339: After deterministic scoring, the LLM reviews scores against
    actual content samples. It can downgrade routing decisions but cannot
    override REJECT to PASS (safety constraint enforced in worker.py).

    Returns dict with llm_status, llm_scores, edge_cases, agreement, override_reason.
    Returns None if LLM call fails (graceful degradation).
    """
    prompt_path = Path(__file__).parent / "prompts" / "score_verifier.txt"
    prompt_template = prompt_path.read_text(encoding="utf-8")

    # Build issue summary (top 10 by severity)
    sorted_issues = sorted(
        issues,
        key=lambda i: {"blocker": 0, "error": 1, "warn": 2, "info": 3}.get(
            i.get("severity", "info"), 4
        ),
    )
    issue_lines = []
    for iss in sorted_issues[:10]:
        issue_lines.append(
            f"- [{iss.get('severity', 'info').upper()}] "
            f"{iss.get('check', '')}: {iss.get('message', '')[:100]}"
        )
    issue_summary = "\n".join(issue_lines) if issue_lines else "No issues found."

    # Build content samples
    sample_lines = []
    for path, content in list(draft_samples.items())[:5]:
        sample_lines.append(f"### {path}\n{content[:500]}\n")
    content_samples = "\n".join(sample_lines) if sample_lines else "No content available."

    prompt = prompt_template.format(
        dimension_scores=json.dumps(dimension_scores, indent=2),
        deterministic_status=deterministic_status,
        issue_summary=issue_summary,
        content_samples=content_samples,
    )

    try:
        response = llm_client.chat_completion(
            messages=[
                {"role": "system", "content": "You are a content quality auditor. Return JSON only."},
                {"role": "user", "content": prompt},
            ],
            call_id="w7_score_verification",
            temperature=0.1,
            max_tokens=1024,
        )
        text = response.get("content", "") if isinstance(response, dict) else str(response)
        # Extract JSON from response — find outermost { } containing "llm_status"
        import re as _re
        json_match = _re.search(r'\{.*?"llm_status".*\}', text, _re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except Exception as e:
        logger.warning(f"[W7] LLM score verification failed: {e}")

    return None
