"""W7 ContentReviewer worker implementation.

This module implements TC-1100: Content review for generated markdown across
3 dimensions: Content Quality, Technical Accuracy, and Usability.

Main entry point:
- execute_content_reviewer: Review drafts and produce review_report.json

Exception hierarchy:
- ContentReviewerError: Base exception
- ContentReviewerArtifactMissingError: Required artifact not found
- ContentReviewerValidationError: Review validation failed

TC-1100-P1: W7 ContentReviewer Phase 1 - Core Review Logic
Pattern: Integrator with intelligence modules (similar to W2 FactsBuilder)

Spec reference: abstract-hugging-kite.md (W7 ContentReviewer implementation plan)
"""

from __future__ import annotations

import json
import logging
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any

from launch.io.artifact_store import ArtifactStore

from .checks import content_quality, technical_accuracy, usability
from .checks import semantic_accuracy  # TC-2403: top-level for helper access
from .checks.quality_gate import decide_quality_outcome, compute_weighted_score
from .scoring import calculate_scores, route_review_result
from .fixes.auto_fixes import apply_auto_fixes
from .fixes.iteration_tracker import IterationTracker
from .fixes.llm_regen import spawn_enhancement_agents

logger = logging.getLogger(__name__)


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


def _run_checks_parallel(
    drafts_dir: Path,
    product_facts: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
    evidence_map: Dict[str, Any],
    page_plan: Dict[str, Any],
    llm_client: Any,
    n_workers: int = 4,
    *,
    include_semantic: bool = True,
):
    """Run W7 check dimensions concurrently (TC-2403).

    Returns (all_issues, semantic_issues). semantic_issues is empty when
    include_semantic=False (caller should restore from cache for re-checks
    after deterministic-only auto-fix passes).

    Thread safety: all dimensions read artifacts read-only; no shared
    mutable state between dimensions.
    """
    dims = {
        "cq": (content_quality.check_all, {
            "drafts_dir": drafts_dir,
            "product_facts": product_facts,
            "page_plan": page_plan,
        }),
        "ta": (technical_accuracy.check_all, {
            "drafts_dir": drafts_dir,
            "product_facts": product_facts,
            "snippet_catalog": snippet_catalog,
            "evidence_map": evidence_map,
            "page_plan": page_plan,
        }),
        "us": (usability.check_all, {
            "drafts_dir": drafts_dir,
            "page_plan": page_plan,
            "product_facts": product_facts,
        }),
    }
    if include_semantic:
        dims["sa"] = (semantic_accuracy.check_all, {
            "drafts_dir": drafts_dir,
            "product_facts": product_facts,
            "llm_client": llm_client,
            "snippet_catalog": snippet_catalog,
        })

    all_issues: List[Any] = []
    semantic_issues: List[Any] = []
    effective = min(n_workers, len(dims)) if n_workers > 1 else 1

    if effective <= 1:
        for name, (fn, kwargs) in dims.items():
            result = list(fn(**kwargs))
            if name == "sa":
                semantic_issues = result
            all_issues.extend(result)
        return all_issues, semantic_issues

    with ThreadPoolExecutor(max_workers=effective, thread_name_prefix="w7_checks") as pool:
        futures = {pool.submit(fn, **kwargs): name for name, (fn, kwargs) in dims.items()}
        for fut in as_completed(futures):
            name = futures[fut]
            try:
                result = list(fut.result())
            except Exception as exc:
                logger.warning("[W7] Check dimension %s failed: %s", name, exc)
                result = []
            if name == "sa":
                semantic_issues = result
            all_issues.extend(result)

    return all_issues, semantic_issues


def _sanitize_draft_file(draft_file: Path, family: str, platform: str) -> None:
    """Apply W7 post-sanitizers to one draft file in-place (TC-2403).

    Extracted from execute_content_reviewer to enable ThreadPoolExecutor
    parallelization across draft files.
    """
    from .._shared.content_sanitizer import (
        fix_heading_missing_space,
        fix_inline_heading,
        fix_missing_space_after_period,
        fix_sentence_heading,
        fix_single_backtick_code_blocks,
        fix_code_fences,
        fix_trailing_periods_in_code,
        fix_excess_backtick_fences,
        fix_nested_fences,
        collapse_duplicate_fence_openings,
        fix_empty_code_example_section,
        fence_bare_commands,
        fence_bare_code_lines,
        fix_bare_language_line,
        fix_prose_in_code_blocks,
        strip_visible_claim_markers,
        strip_orphan_claim_markers,
        strip_pipeline_comments,
        strip_emojis,
        strip_boilerplate_sentences,
        strip_llm_scaffolding,
        merge_adjacent_code_blocks,
        strip_double_periods,
        fix_collapsed_frontmatter,
        absolutize_links,
        close_unclosed_fences,
        fix_truncated_sentences,
    )

    def _safe(fn, content, *args):
        try:
            return fn(content, *args)
        except Exception as exc:
            logger.warning(
                "[W7] Post-sanitize %s failed for %s: %s", fn.__name__, draft_file.name, exc
            )
            return content

    try:
        text = draft_file.read_text(encoding="utf-8")
    except Exception:
        return

    sanitized = _safe(strip_llm_scaffolding, text)
    # Phase 0: Structural heading normalization (before fence passes)
    sanitized = _safe(fix_heading_missing_space, sanitized)
    sanitized = _safe(fix_inline_heading, sanitized)
    sanitized = _safe(fix_sentence_heading, sanitized)
    sanitized = _safe(fix_missing_space_after_period, sanitized)
    # Phase 1: Bare code detection (before fence normalization)
    sanitized = _safe(fence_bare_commands, sanitized)
    sanitized = _safe(fix_bare_language_line, sanitized)
    sanitized = _safe(fence_bare_code_lines, sanitized)
    # Phase 2: Fence normalization chain (strict ordering, matches W5 pipeline)
    sanitized = _safe(fix_collapsed_frontmatter, sanitized)
    sanitized = _safe(close_unclosed_fences, sanitized)
    sanitized = _safe(fix_nested_fences, sanitized)
    sanitized = _safe(fix_single_backtick_code_blocks, sanitized)
    sanitized = _safe(fix_excess_backtick_fences, sanitized)
    sanitized = _safe(collapse_duplicate_fence_openings, sanitized)
    sanitized = _safe(fix_empty_code_example_section, sanitized)
    sanitized = _safe(fix_code_fences, sanitized)
    sanitized = _safe(fix_trailing_periods_in_code, sanitized)
    sanitized = _safe(fix_prose_in_code_blocks, sanitized)
    sanitized = _safe(merge_adjacent_code_blocks, sanitized)
    # Phase 3: Content cleanup
    sanitized = _safe(strip_visible_claim_markers, sanitized)
    sanitized = _safe(strip_pipeline_comments, sanitized)
    sanitized = _safe(strip_orphan_claim_markers, sanitized)
    sanitized = _safe(strip_emojis, sanitized)
    sanitized = _safe(strip_boilerplate_sentences, sanitized)
    sanitized = _safe(strip_double_periods, sanitized)
    sanitized = _safe(fix_truncated_sentences, sanitized)
    # Determine section from file path
    _section = "default"
    rel = str(draft_file).replace("\\", "/")
    for sec in ("docs", "reference", "kb", "blog", "products"):
        if f"{sec}.aspose.org" in rel:
            _section = sec
            break
    sanitized = _safe(absolutize_links, sanitized, _section, family, platform)
    if sanitized != text:
        draft_file.write_text(sanitized, encoding="utf-8")


def execute_content_reviewer(run_dir: Path, run_config: Dict[str, Any]) -> Dict[str, Any]:
    """W7 ContentReviewer worker - reviews generated markdown.

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
        "worker": "W7_ContentReviewer",
    })

    # Load required artifacts
    product_facts = _load_artifact(artifacts_dir, "product_facts.json")
    snippet_catalog = _load_artifact(artifacts_dir, "snippet_catalog.json")
    page_plan = _load_artifact(artifacts_dir, "page_plan.json")
    evidence_map = _load_artifact(artifacts_dir, "evidence_map.json")

    # Initialize LLM client for semantic checks (TC-1405, TC-2101)
    llm_client = None
    llm_cfg = run_config.get("llm", {})
    if llm_cfg.get("api_base_url") or llm_cfg.get("endpoint"):
        try:
            from launch.clients.llm_provider import create_llm_client_from_config
            llm_client = create_llm_client_from_config(
                run_config=run_config,
                run_dir=run_dir,
            )
        except Exception:
            pass  # Semantic checks will use offline fallback

    # Check drafts directory exists
    if not drafts_dir.exists():
        raise ContentReviewerArtifactMissingError(f"Drafts directory not found: {drafts_dir}")

    # Get list of draft files
    draft_files = sorted(drafts_dir.rglob("*.md"))
    if not draft_files:
        raise ContentReviewerValidationError("No draft files found in drafts directory")

    # TC-2403: Parallel worker count for check dimensions and post-sanitization
    n_workers = max(1, min(8, run_config.get("max_parallel_workers_w7", 4)))

    # ── Phase 0: LLM Format Review + Fix (TC-2360) ──────────────────────────
    # Detect and fix 7 formatting defect types (FQ-1..FQ-7) before the existing
    # 36-check cycle so subsequent checks run on already-cleaned content.
    # Gracefully skips when llm_client is None — zero impact on offline runs.
    from .fixes.llm_format_fix import run_llm_format_fix
    format_issues, format_fix_results = run_llm_format_fix(
        drafts_dir=drafts_dir,
        llm_client=llm_client,
        n_workers=n_workers,
    )

    # TC-2403: Run all 4 check dimensions concurrently.
    # semantic_issues captured separately for reuse in deterministic re-check passes
    # (deterministic auto-fixes cannot affect semantic accuracy results).
    all_issues = list(format_issues)  # seed with Phase 0 issues
    _dim_issues, _semantic_cache = _run_checks_parallel(
        drafts_dir, product_facts, snippet_catalog, evidence_map, page_plan,
        llm_client, n_workers, include_semantic=True,
    )
    all_issues.extend(_dim_issues)

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

    # Re-check after auto-fixes for accurate scoring.
    # Auto-fixes modify draft files on disk; re-running checks reflects actual state.
    # TC-2403: Skip semantic accuracy on deterministic re-checks — deterministic fixes
    # (heading expansion, term normalization, frontmatter repair) cannot affect API
    # hallucination or content relevance. Restore _semantic_cache from initial run.
    if fix_results and any(fr.get("success") for fr in fix_results):
        _dim_issues, _ = _run_checks_parallel(
            drafts_dir, product_facts, snippet_catalog, evidence_map, page_plan,
            llm_client, n_workers, include_semantic=False,
        )
        all_issues = _dim_issues + _semantic_cache  # restore semantic from initial run

        # Second fix pass: catch any new auto-fixable issues introduced by first-pass fixes
        # (e.g. frontmatter corruption from metadata title replacement).
        second_fixable = [i for i in all_issues if i.get("auto_fixable", False)]
        if second_fixable:
            second_fix_results = apply_auto_fixes(
                issues=second_fixable,
                drafts_dir=drafts_dir,
                product_facts=product_facts,
                iteration_tracker=tracker,
            )
            fix_results.extend(second_fix_results)
            for fr in second_fix_results:
                if fr.get("success"):
                    _emit_event(run_dir, "FIX_APPLIED", fr)

            # Final re-check after second fix pass (also skip semantic — still deterministic)
            if any(fr.get("success") for fr in second_fix_results):
                _dim_issues, _ = _run_checks_parallel(
                    drafts_dir, product_facts, snippet_catalog, evidence_map, page_plan,
                    llm_client, n_workers, include_semantic=False,
                )
                all_issues = _dim_issues + _semantic_cache  # restore semantic

    # Sort issues for determinism (by severity, check, path, line, issue_id)
    # line may be a list (e.g. [10, 20]) from some checks — coerce to int to avoid TypeError
    def _line_sort_key(loc: Any) -> int:
        v = loc.get('line', 0) if isinstance(loc, dict) else 0
        return v if isinstance(v, int) else 0

    all_issues.sort(key=lambda i: (
        _severity_sort_key(i.get('severity', 'warn')),
        i.get('check', ''),
        str(i.get('location', {}).get('path', '')),
        _line_sort_key(i.get('location', {})),
        i.get('issue_id', ''),
    ))

    # Calculate scores per dimension (1-5 scale, density-aware)
    dimension_scores = calculate_scores(all_issues, num_pages=len(draft_files))

    # Route based on scores and issues
    overall_status = route_review_result(dimension_scores, all_issues)

    # TC-2339: LLM score verification
    llm_verification = None
    if llm_client and run_config.get("review_llm_verify", True):
        draft_samples = {}
        for df in draft_files[:5]:
            try:
                draft_samples[str(df.relative_to(drafts_dir))] = df.read_text(encoding="utf-8")[:500]
            except Exception:
                pass
        from .scoring import verify_scores_with_llm
        llm_verification = verify_scores_with_llm(
            llm_client, dimension_scores, all_issues, overall_status, draft_samples
        )
        if llm_verification and not llm_verification.get("agreement", True):
            logger.warning(
                f"[W7] LLM disagrees: deterministic={overall_status}, "
                f"llm={llm_verification.get('llm_status')}, "
                f"reason={llm_verification.get('override_reason')}"
            )
            llm_status = llm_verification.get("llm_status", overall_status)
            # Safety: LLM cannot override REJECT->PASS
            if overall_status == "PASS" and llm_status != "PASS":
                overall_status = llm_status
            elif overall_status == "NEEDS_CHANGES" and llm_status == "REJECT":
                overall_status = "REJECT"
        if llm_verification and llm_verification.get("edge_cases"):
            for ec in llm_verification["edge_cases"]:
                all_issues.append({
                    "check": "llm_edge_case",
                    "severity": "info",
                    "message": ec,
                    "location": {"path": "aggregate", "line": 0},
                    "auto_fixable": False,
                })

    # TC-2341: LLM Regen for NEEDS_CHANGES/REJECT (BEFORE report writing)
    agent_results = []
    if overall_status in ("NEEDS_CHANGES", "REJECT"):
        agent_results = spawn_enhancement_agents(
            all_issues, run_dir, run_config,
            llm_client=llm_client, drafts_dir=drafts_dir,
            n_workers=n_workers,
        )
        # Re-check after LLM modifications (TC-2403: full refresh including semantic —
        # LLM regen may introduce new hallucinations that must be caught)
        if any(ar.get("files_modified") for ar in agent_results):
            _dim_issues, _semantic_cache = _run_checks_parallel(
                drafts_dir, product_facts, snippet_catalog, evidence_map, page_plan,
                llm_client, n_workers, include_semantic=True,
            )
            all_issues = list(_dim_issues)
            dimension_scores = calculate_scores(all_issues, num_pages=len(draft_files))
            overall_status = route_review_result(dimension_scores, all_issues)
            logger.info(f"[W7] Post-LLM re-score: {overall_status} (scores={dimension_scores})")

    # TC-2104 + TC-RCA + TC-2403: Post-LLM sanitization (parallelized per file).
    # Auto-fixes and LLM regen can introduce new single-backtick fences,
    # trailing periods in code, visible claim markers, and other artifacts.
    # Re-sanitize all draft files with the full set of relevant sanitizers.
    # TC-2403: Each file processed by _sanitize_draft_file() via ThreadPoolExecutor.
    _family = run_config.get("family", run_config.get("product_family", ""))
    _platform = run_config.get("target_platform", "")
    _n_sanitize = min(len(draft_files), n_workers) if n_workers > 1 else 1
    if _n_sanitize <= 1:
        for _df in draft_files:
            _sanitize_draft_file(_df, _family, _platform)
    else:
        with ThreadPoolExecutor(max_workers=_n_sanitize, thread_name_prefix="w7_sanitize") as _pool:
            _futs = [_pool.submit(_sanitize_draft_file, _df, _family, _platform) for _df in draft_files]
            for _fut in as_completed(_futs):
                try:
                    _fut.result()
                except Exception as _exc:
                    logger.warning("[W7] Post-sanitize file failed: %s", _exc)

    # TC-2396: Three-layer quality gate (additive, does not replace route_review_result)
    quality_outcome = None
    weighted_score = None
    human_review_required = False
    try:
        check_results = [
            {
                "name": i.get("check", "").split(".")[-1] if "." in i.get("check", "") else i.get("check", ""),
                "passed": False,
            }
            for i in all_issues
        ]
        quality_outcome = decide_quality_outcome(check_results)
        weighted_score = compute_weighted_score(check_results)
        logger.info(
            "quality_gate_outcome outcome=%s weighted_score=%.3f",
            quality_outcome, weighted_score,
        )
        # Store for use in routing
        if quality_outcome == "REVIEW":
            human_review_required = True
    except Exception as _qg_err:
        logger.warning("quality_gate_failed error=%s", _qg_err)

    # Severity counts and page status
    severity_counts = {
        'blocker': sum(1 for i in all_issues if i.get('severity') == 'blocker'),
        'error': sum(1 for i in all_issues if i.get('severity') == 'error'),
        'warn': sum(1 for i in all_issues if i.get('severity') == 'warn'),
        'info': sum(1 for i in all_issues if i.get('severity') == 'info'),
    }
    pages_by_path = {}
    for issue in all_issues:
        path = str(issue.get('location', {}).get('path', 'unknown'))
        if path not in pages_by_path:
            pages_by_path[path] = {'path': path, 'issues': []}
        pages_by_path[path]['issues'].append(issue)
    pages_passed = sum(1 for pd in pages_by_path.values()
                       if not any(i.get('severity') in ['blocker', 'error'] for i in pd['issues']))
    pages_failed = len(pages_by_path) - pages_passed

    # Emit PAGE_REVIEWED events
    for page_path in pages_by_path.keys():
        _emit_event(run_dir, "PAGE_REVIEWED", {
            "page_path": page_path,
            "issue_count": len(pages_by_path[page_path]['issues']),
        })

    # Build review report with FINAL scores
    _reviewed_at = datetime.now(timezone.utc).isoformat()
    review_report = {
        "schema_version": "1.0.0",
        "review_id": str(uuid.uuid4()),
        "run_dir": str(run_dir),
        "timestamp": _reviewed_at,
        "reviewed_at": _reviewed_at,  # gate_1 schema compliance
        "ok": overall_status == "PASS",
        "overall_status": overall_status,
        "dimension_scores": dimension_scores,
        "severity_counts": severity_counts,
        "pages_reviewed": len(draft_files),
        "pages_passed": pages_passed,
        "pages_failed": pages_failed,
        "issues": all_issues,
        "format_fix_results": format_fix_results,
        "fix_results": fix_results,
        "agent_results": agent_results,
        "llm_verification": llm_verification,
        "quality_gate_outcome": quality_outcome,
        "quality_gate_weighted_score": weighted_score,
        "human_review_required": human_review_required,
    }
    review_report_path = artifacts_dir / "review_report.json"
    with open(review_report_path, 'w', encoding='utf-8') as f:
        json.dump(review_report, f, indent=2, ensure_ascii=False)

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
