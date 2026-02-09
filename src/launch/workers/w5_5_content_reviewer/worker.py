"""W5.5 ContentReviewer worker implementation.

This module implements TC-1100: Content review for generated markdown across
3 dimensions: Content Quality, Technical Accuracy, and Usability.

Main entry point:
- execute_content_reviewer: Review drafts and produce review_report.json

Exception hierarchy:
- ContentReviewerError: Base exception
- ContentReviewerArtifactMissingError: Required artifact not found
- ContentReviewerValidationError: Review validation failed

TC-1100-P1: W5.5 ContentReviewer Phase 1 - Core Review Logic
Pattern: Integrator with intelligence modules (similar to W2 FactsBuilder)

Spec reference: abstract-hugging-kite.md (W5.5 ContentReviewer implementation plan)
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any

from launch.io.artifact_store import ArtifactStore

from .checks import content_quality, technical_accuracy, usability
from .scoring import calculate_scores, route_review_result
from .fixes.auto_fixes import apply_auto_fixes
from .fixes.iteration_tracker import IterationTracker
from .fixes.llm_regen import spawn_enhancement_agents


# Exception hierarchy
class ContentReviewerError(Exception):
    """Base exception for ContentReviewer errors."""
    pass


class ContentReviewerArtifactMissingError(ContentReviewerError):
    """Required artifact not found."""
    pass


class ContentReviewerValidationError(ContentReviewerError):
    """Review validation failed."""
    pass


def execute_content_reviewer(run_dir: Path, run_config: Dict[str, Any]) -> Dict[str, Any]:
    """W5.5 ContentReviewer worker - reviews generated markdown.

    Reviews content across 3 dimensions:
    1. Content Quality: readability, structure, completeness
    2. Technical Accuracy: code correctness, claim validity, API references
    3. Usability: navigation, accessibility, user journey

    Args:
        run_dir: Path to run directory
        run_config: Run configuration dict

    Returns:
        Dict with:
        {
            "status": "success" | "failed",
            "review_report": {...},  # review_report.json content
            "overall_status": "PASS" | "NEEDS_CHANGES" | "REJECT",
            "pages_reviewed": int,
            "pages_passed": int,
            "pages_failed": int,
        }

    Raises:
        ContentReviewerArtifactMissingError: If required artifact not found
        ContentReviewerValidationError: If validation fails

    Spec reference: abstract-hugging-kite.md:240-286 (worker.py requirements)
    """
    # Validate run_dir
    if not run_dir.exists():
        raise ContentReviewerArtifactMissingError(f"Run directory not found: {run_dir}")

    # Define paths
    artifacts_dir = run_dir / "artifacts"
    drafts_dir = run_dir / "drafts"

    # Emit REVIEW_STARTED event
    _emit_event(run_dir, "REVIEW_STARTED", {
        "run_dir": str(run_dir),
        "worker": "W5.5_ContentReviewer",
    })

    # Load required artifacts
    product_facts = _load_artifact(artifacts_dir, "product_facts.json")
    snippet_catalog = _load_artifact(artifacts_dir, "snippet_catalog.json")
    page_plan = _load_artifact(artifacts_dir, "page_plan.json")
    evidence_map = _load_artifact(artifacts_dir, "evidence_map.json")

    # Check drafts directory exists
    if not drafts_dir.exists():
        raise ContentReviewerArtifactMissingError(f"Drafts directory not found: {drafts_dir}")

    # Get list of draft files
    draft_files = sorted(drafts_dir.rglob("*.md"))
    if not draft_files:
        raise ContentReviewerValidationError("No draft files found in drafts directory")

    # Run all checks across 3 dimensions
    all_issues = []

    # Dimension 1: Content Quality (12 checks)
    content_quality_issues = content_quality.check_all(
        drafts_dir=drafts_dir,
        product_facts=product_facts,
        page_plan=page_plan,
    )
    all_issues.extend(content_quality_issues)

    # Dimension 2: Technical Accuracy (12 checks)
    technical_accuracy_issues = technical_accuracy.check_all(
        drafts_dir=drafts_dir,
        product_facts=product_facts,
        snippet_catalog=snippet_catalog,
        evidence_map=evidence_map,
        page_plan=page_plan,
    )
    all_issues.extend(technical_accuracy_issues)

    # Dimension 3: Usability (12 checks)
    usability_issues = usability.check_all(
        drafts_dir=drafts_dir,
        page_plan=page_plan,
        product_facts=product_facts,
    )
    all_issues.extend(usability_issues)

    # Apply deterministic auto-fixes (Phase 2)
    tracker = IterationTracker(run_dir=run_dir)
    auto_fixable = [i for i in all_issues if i.get("auto_fixable", False)]
    fix_results = []
    if auto_fixable:
        fix_results = apply_auto_fixes(
            issues=auto_fixable,
            drafts_dir=drafts_dir,
            product_facts=product_facts,
            iteration_tracker=tracker,
        )
        # Emit FIX_APPLIED events for successful fixes
        for fix_result in fix_results:
            if fix_result.get("success"):
                _emit_event(run_dir, "FIX_APPLIED", fix_result)

    agent_results = []

    # Sort issues for determinism (by severity, check, path, line, issue_id)
    all_issues.sort(key=lambda i: (
        _severity_sort_key(i.get('severity', 'warn')),
        i.get('check', ''),
        i.get('location', {}).get('path', ''),
        i.get('location', {}).get('line', 0),
        i.get('issue_id', ''),
    ))

    # Calculate scores per dimension (1-5 scale)
    dimension_scores = calculate_scores(all_issues)

    # Route based on scores and issues
    overall_status = route_review_result(dimension_scores, all_issues)

    # Count severity levels
    severity_counts = {
        'blocker': sum(1 for i in all_issues if i.get('severity') == 'blocker'),
        'error': sum(1 for i in all_issues if i.get('severity') == 'error'),
        'warn': sum(1 for i in all_issues if i.get('severity') == 'warn'),
        'info': sum(1 for i in all_issues if i.get('severity') == 'info'),
    }

    # Count pages by status
    pages_by_path = {}
    for issue in all_issues:
        path = issue.get('location', {}).get('path', 'unknown')
        if path not in pages_by_path:
            pages_by_path[path] = {
                'path': path,
                'issues': [],
            }
        pages_by_path[path]['issues'].append(issue)

    # Determine page status (PASS if no BLOCKER/ERROR, FAIL otherwise)
    pages_passed = 0
    pages_failed = 0
    for page_path, page_data in pages_by_path.items():
        has_blocker_or_error = any(
            i.get('severity') in ['blocker', 'error']
            for i in page_data['issues']
        )
        if has_blocker_or_error:
            pages_failed += 1
        else:
            pages_passed += 1

    # Emit PAGE_REVIEWED events
    for page_path in pages_by_path.keys():
        _emit_event(run_dir, "PAGE_REVIEWED", {
            "page_path": page_path,
            "issue_count": len(pages_by_path[page_path]['issues']),
        })

    # Build review report
    review_report = {
        "schema_version": "1.0.0",
        "review_id": str(uuid.uuid4()),
        "run_dir": str(run_dir),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ok": overall_status == "PASS",
        "overall_status": overall_status,
        "dimension_scores": dimension_scores,
        "severity_counts": severity_counts,
        "pages_reviewed": len(draft_files),
        "pages_passed": pages_passed,
        "pages_failed": pages_failed,
        "issues": all_issues,
        "fix_results": fix_results,
        "agent_results": agent_results,
    }

    # Write review_report.json
    review_report_path = artifacts_dir / "review_report.json"
    with open(review_report_path, 'w', encoding='utf-8') as f:
        json.dump(review_report, f, indent=2, ensure_ascii=False)

    # Delegate to specialist agents for non-auto-fixable issues (Phase 3)
    if overall_status in ("NEEDS_CHANGES", "REJECT"):
        agent_results = spawn_enhancement_agents(all_issues, run_dir, run_config)

    # Write iteration tracking artifact
    tracker.write_iterations_json()

    # Emit REVIEW_COMPLETED event
    _emit_event(run_dir, "REVIEW_COMPLETED", {
        "overall_status": overall_status,
        "pages_reviewed": len(draft_files),
        "pages_passed": pages_passed,
        "pages_failed": pages_failed,
        "total_issues": len(all_issues),
    })

    # Return result
    return {
        "status": "success",
        "review_report": review_report,
        "overall_status": overall_status,
        "pages_reviewed": len(draft_files),
        "pages_passed": pages_passed,
        "pages_failed": pages_failed,
    }


# Helper functions

def _load_artifact(artifacts_dir: Path, artifact_name: str) -> Dict[str, Any]:
    """Load JSON artifact from artifacts directory.

    Args:
        artifacts_dir: Path to artifacts directory
        artifact_name: Artifact filename (e.g., product_facts.json)

    Returns:
        Parsed JSON artifact

    Raises:
        ContentReviewerArtifactMissingError: If artifact not found
    """
    artifact_path = artifacts_dir / artifact_name
    if not artifact_path.exists():
        raise ContentReviewerArtifactMissingError(
            f"Required artifact not found: {artifact_name}"
        )

    with open(artifact_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def _emit_event(run_dir: Path, event_type: str, payload: Dict[str, Any],
                run_id: str = None, trace_id: str = None, span_id: str = None) -> None:
    """Emit telemetry event to events.ndjson via ArtifactStore.

    Uses the same Event model as all other workers (TC-1033 pattern),
    ensuring event_id, run_id, trace_id, span_id are always present.

    Args:
        run_dir: Run directory path
        event_type: Event type (e.g., REVIEW_STARTED)
        payload: Event payload dict
        run_id: Run identifier (defaults to run_dir.name)
        trace_id: Trace ID for telemetry (defaults to new UUID)
        span_id: Span ID for telemetry (defaults to new UUID)
    """
    store = ArtifactStore(run_dir=run_dir)
    store.emit_event(
        event_type,
        payload,
        run_id=run_id,
        trace_id=trace_id,
        span_id=span_id,
    )


def _severity_sort_key(severity: str) -> int:
    """Get sort key for severity (lower number = higher priority).

    Args:
        severity: Severity string (blocker, error, warn, info)

    Returns:
        Sort key integer
    """
    severity_order = {
        'blocker': 0,
        'error': 1,
        'warn': 2,
        'info': 3,
    }
    return severity_order.get(severity.lower(), 4)
