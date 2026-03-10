"""Evaluate worker — quality assessment and GO/NO-GO decision.

Phase A: Run 11 deterministic checks on each generated page.
Phase B: Optional LLM-based review for deeper evaluation.
Grading: Assign A-F grades based on findings severity.
Verdict: Evaluate GO/NO-GO criteria against aggregate results.
Diagnosis: Map failures back to responsible upstream workers.
"""
from __future__ import annotations

import logging
import re
import time
from pathlib import Path
from typing import Any

from launcher.models.base import LauncherBaseModel
from launcher.models.content import ContentManifest
from launcher.models.evaluation import (
    EvaluationReport,
    Finding,
    Grade,
    PageEvaluation,
    QualitySummary,
    Verdict,
)
from launcher.orchestrator.worker_contract import SelfReviewResult, WorkerContext, WorkerContract
from launcher.workers.evaluate.checks import (
    check_api_identifiers,  # TC-HYBRID-05
    check_artifacts,
    check_claim_coverage,  # TC-3880 Wave 2 (E4)
    check_claim_leakage,
    check_code,
    check_contradiction,   # TC-HYBRID-06
    check_density,
    check_format_truth,    # TC-HYBRID-06
    check_frontmatter,
    check_golden_spec_from_markdown,
    check_product_names,
    check_readability_from_markdown,
    check_reference_completeness,
    check_repetition,
    check_safety,
    check_semantic_structure,
    check_seo,
    check_spec_leakage,
    check_structure,
)
from launcher.io.run_layout import RunLayout
from launcher.workers.evaluate.diagnosis import diagnose_root_causes
from launcher.workers.evaluate.go_criteria import evaluate_go_criteria
from launcher.workers.evaluate.grader import grade_page

logger = logging.getLogger(__name__)


def _resolve_skills_path(skills_cfg: object | None, run_dir: Path) -> Path:
    """Resolve the skills.md path with CWD-relative fallback chain.

    Resolution order:
    1. As-is if absolute.
    2. Relative to CWD (project-root convention for CLI use).
    3. Relative to run_dir.parent (project-root inference for library use).

    Returns the first existing path, or the CWD-relative path as fallback
    (skills_loader will handle the missing-file case gracefully).
    """
    raw = getattr(skills_cfg, "path", "skills.md") if skills_cfg else "skills.md"
    p = Path(raw)
    if p.is_absolute():
        return p
    cwd_path = Path.cwd() / p
    if cwd_path.exists():
        return cwd_path
    root_path = run_dir.parent / p
    if root_path.exists():
        return root_path
    return cwd_path


class EvaluateWorker(WorkerContract):
    def __init__(self) -> None:
        # Lazy-loaded on first run() call when golden config is enabled (V2CP-02)
        self._golden_index: Any | None = None

    @property
    def name(self) -> str:
        return "evaluate"

    def _load_golden_index(self, context: WorkerContext) -> Any | None:
        """Load GoldenIndex from config (once per worker instance)."""
        if self._golden_index is not None:
            return self._golden_index
        try:
            golden_cfg = getattr(context.config, "golden", {}) or {}
            if golden_cfg.get("enabled"):
                from launcher.shared.golden_loader import GoldenIndex
                golden_dir = Path(golden_cfg.get("dir", "golden/"))
                self._golden_index = GoldenIndex.load(golden_dir)
        except Exception:
            pass
        return self._golden_index

    async def run(self, input_data: LauncherBaseModel, context: WorkerContext) -> EvaluationReport:
        """Evaluate all generated pages and produce a GO/NO-GO report."""
        if not isinstance(input_data, ContentManifest):
            raise TypeError(f"Expected ContentManifest, got {type(input_data).__name__}")

        manifest = input_data
        start_time = time.monotonic()

        context.log.info("[Evaluate] Starting evaluation of %d pages", len(manifest.pages))
        context.emit_event("worker_started", {"pages": len(manifest.pages)}, worker=self.name)

        import asyncio as _asyncio_eval

        _eval_sem = _asyncio_eval.Semaphore(4)  # _PAGE_CONCURRENCY for evaluate

        # Create evaluation artifact directory
        _artifacts_enabled = True
        layout = RunLayout(run_dir=context.run_dir)
        try:
            eval_pages_dir = layout.evaluation_dir / "pages"
            eval_pages_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            logger.warning(
                "[Evaluate] Cannot create evaluation artifact directory; artifacts disabled",
                exc_info=True,
            )
            _artifacts_enabled = False

        product_name = context.config.display_name or context.config.product_name or ""
        eval_fast_path = getattr(context, "eval_fast_path", False)

        # Resolve golden_dir once per run for check_golden_spec_from_markdown (TC-3864)
        _golden_cfg = getattr(context.config, "golden", {}) or {}
        _golden_dir: Path | None = None
        if _golden_cfg.get("enabled"):
            _golden_dir = Path(_golden_cfg.get("dir", "golden/"))

        # Load skills evaluation criteria once per run (TC-3856)
        _skills_criteria = ""
        _skills_cfg = getattr(context.config, "skills", None)
        if _skills_cfg is None or getattr(_skills_cfg, "enabled", True):
            try:
                from launcher.shared.skills_loader import load_evaluation_block as _load_eval_skills
                _skills_path = _resolve_skills_path(_skills_cfg, context.run_dir)
                _skills_criteria = _load_eval_skills(_skills_path)
                if _skills_criteria:
                    context.log.info("[Evaluate] Skills evaluation criteria loaded (%d chars)", len(_skills_criteria))
            except Exception as _e:
                context.log.debug("[Evaluate] Skills load skipped: %s", _e)

        context.emit_event(
            "skills_loaded" if _skills_criteria else "skills_inactive",
            {
                "enabled": getattr(_skills_cfg, "enabled", True),
                "path": getattr(_skills_cfg, "path", "skills.md"),
                "chars": len(_skills_criteria),
            },
            worker=self.name,
        )

        # TC-3881 Wave 3 (H9): Selective evaluate — resolve heal target set once.
        _heal_targets: frozenset[str] | None = (
            frozenset(context.heal_target_pages)
            if context.heal_target_pages is not None else None
        )

        # TC-HYBRID-08: content cache for cross-page review (slug -> markdown text)
        _page_content_cache: dict[str, str] = {}

        async def _evaluate_page_llm(gen_page: Any) -> tuple[PageEvaluation, int, set[str]]:
            """Evaluate one page; return (PageEvaluation, word_count, claim_ids)."""

            # TC-3881 (H9): In heal mode, skip re-evaluation of non-target pages.
            if _heal_targets is not None and gen_page.slug not in _heal_targets:
                # Populate content cache for cross-page review even for skipped pages.
                _heal_md_path = context.run_dir / gen_page.md_path
                if _heal_md_path.exists():
                    try:
                        _page_content_cache[gen_page.slug] = _heal_md_path.read_text(encoding="utf-8")
                    except Exception:
                        pass

                # Try to load cached PageEvaluation from disk (use same key as _write_page_artifact)
                safe_slug = _safe_slug(gen_page.content_path or gen_page.slug)
                cached_eval_path = context.run_dir / "evaluation" / "pages" / f"{safe_slug}.eval.json"
                if cached_eval_path.exists():
                    try:
                        cached_eval = PageEvaluation.model_validate_json(
                            cached_eval_path.read_text(encoding="utf-8")
                        )
                        context.emit_event(
                            "evaluate_page_skipped",
                            {"slug": gen_page.slug, "cached": True},
                            worker=self.name,
                        )
                        return (cached_eval, gen_page.word_count, set(gen_page.claim_ids_used))
                    except Exception:
                        pass  # Fall through to full evaluation on cache miss/error

            md_path = context.run_dir / gen_page.md_path
            if not md_path.exists():
                return (
                    PageEvaluation(
                        slug=gen_page.slug,
                        content_path=gen_page.content_path,
                        grade=Grade.F,
                        findings=[Finding(
                            check="file_missing",
                            message=f"Markdown file not found: {gen_page.md_path}",
                            severity="critical",
                            location=gen_page.slug,
                        )],
                    ),
                    0,
                    set(),
                )

            content = md_path.read_text(encoding="utf-8")

            # TC-HYBRID-08: cache content for cross-page review
            _page_content_cache[gen_page.slug] = content

            # Phase A: deterministic checks (no LLM — no semaphore needed)
            findings = _run_deterministic_checks(
                content, gen_page.slug,
                page_role=gen_page.page_role,
                product_name=product_name,
                canonical_import=context.config.canonical_import or "",
                runtime_import=getattr(context.config, "runtime_import", "") or "",
                golden_dir=_golden_dir,
                # TC-3880 Wave 2 (E4): claim_texts from generate worker for coverage check.
                claim_texts=getattr(gen_page, "claim_texts", []),
                # TC-HYBRID-05: pass ApiSurface for API identifier verification gate.
                api_surface=_load_api_surface_obj(context),
            )

            # TC-3882 Wave 4 (E9): When PageIR is available, run section-level golden check
            # using check_block_spec_compliance (richer than markdown-based aggregation).
            # Replace any existing structure/golden findings from check_golden_spec_from_markdown
            # with section-level findings for golden compliance.
            _ir_path_str = getattr(gen_page, "ir_path", "") or ""
            if _ir_path_str and _golden_dir is not None:
                try:
                    _ir_full_path = context.run_dir / _ir_path_str
                    if _ir_full_path.exists():
                        from launcher.models.page_ir import PageIR as _PageIR
                        _page_ir = _PageIR.model_validate_json(
                            _ir_full_path.read_text(encoding="utf-8")
                        )
                        from launcher.workers.evaluate.checks.structure import (
                            check_block_spec_compliance as _cbc,
                        )
                        _ir_findings_raw = _cbc(_page_ir, gen_page.page_role, _golden_dir)
                        if _ir_findings_raw:
                            # Remove check_golden_spec_from_markdown findings (already in list)
                            # to avoid double-counting; replace with section-level findings.
                            findings = [
                                f for f in findings
                                if not (
                                    f.check == "structure"
                                    and "golden spec" in (f.message or "").lower()
                                )
                            ]
                            for _rf in _ir_findings_raw:
                                findings.append(Finding(
                                    check=_rf.get("check", "structure"),
                                    message=_rf.get("message", ""),
                                    severity=_rf.get("severity", "medium"),
                                    location=_rf.get("location", gen_page.slug),
                                    section_id=_rf.get("location"),  # location = heading in cbc
                                ))
                            context.emit_event(
                                "evaluate_using_page_ir_check",
                                {"slug": gen_page.slug, "ir_findings": len(_ir_findings_raw)},
                                worker=self.name,
                            )
                except Exception:
                    logger.debug("[Evaluate] E9 PageIR golden check failed for %s", gen_page.slug, exc_info=True)

            # Phase B: optional LLM review (skipped in heal fast-path mode)
            # TC-3882 Wave 4 (E8): Lite mode for non-final heal steps; full mode otherwise.
            _heal_step_idx: int = (_heal_meta := getattr(context, "heal_metadata", None) or {}).get("heal_step", 0)
            _heal_max_steps: int = _heal_meta.get("heal_max_steps", 1)
            # Lite mode: in heal mode AND not the final step
            _is_in_heal = bool(_heal_meta.get("responsible_worker"))
            _is_final_heal_step = (_heal_step_idx >= _heal_max_steps - 1)
            _use_lite_mode = _is_in_heal and not _is_final_heal_step
            if context.llm_config and not eval_fast_path:
                async with _eval_sem:
                    _llm_grade, llm_findings = await _run_llm_review(
                        content, gen_page, context,
                        skills_criteria=_skills_criteria,
                        phase_a_findings=findings,  # TC-3882 (H4): pass Phase A context
                        use_lite_mode=_use_lite_mode,  # TC-3882 (E8): lite mode for heal
                    )
                findings.extend(llm_findings)

            grade = grade_page(findings)
            check_results = _aggregate_check_results(findings)
            page_eval = PageEvaluation(
                slug=gen_page.slug,
                content_path=gen_page.content_path,
                grade=grade,
                findings=findings,
                check_results=check_results,
            )
            return (page_eval, gen_page.word_count, set(gen_page.claim_ids_used))

        raw_eval_results = await _asyncio_eval.gather(
            *[_evaluate_page_llm(gp) for gp in manifest.pages],
            return_exceptions=True,
        )

        page_evals: list[PageEvaluation] = []
        total_words = 0
        all_claim_ids: set[str] = set()

        for gp, result in zip(manifest.pages, raw_eval_results):
            if isinstance(result, BaseException):
                logger.warning("[Evaluate] Page '%s' evaluation failed: %s", gp.slug, result)
                page_evals.append(PageEvaluation(
                    slug=gp.slug,
                    content_path=gp.content_path,
                    grade=Grade.F,
                    findings=[Finding(
                        check="evaluation_error",
                        message=f"Evaluation failed: {result!s}",
                        severity="critical",
                        location=gp.slug,
                    )],
                ))
            else:
                pe, w, cids = result
                page_evals.append(pe)
                total_words += w
                all_claim_ids.update(cids)

        # Manifest-level: permalink collision check
        # Group by content_path (unique Hugo path) when available, fall back to slug.
        # Pages at different content_paths with the same slug (e.g. _index) are NOT collisions.
        path_counts: dict[str, list[int]] = {}
        for idx, pe in enumerate(page_evals):
            key = pe.content_path or pe.slug
            path_counts.setdefault(key, []).append(idx)
        for path_key, indices in path_counts.items():
            if len(indices) > 1:
                for idx in indices:
                    new_findings = list(page_evals[idx].findings) + [Finding(
                        check="permalink",
                        message=f"Permalink collision: '{path_key}' used by {len(indices)} pages",
                        severity="critical",
                        location=page_evals[idx].slug,
                    )]
                    page_evals[idx] = PageEvaluation(
                        slug=page_evals[idx].slug,
                        content_path=page_evals[idx].content_path,
                        grade=grade_page(new_findings),
                        findings=new_findings,
                        check_results=page_evals[idx].check_results,
                    )

        # Write per-page evaluation artifacts (after collision re-grading)
        if _artifacts_enabled:
            for page_eval in page_evals:
                _write_page_artifact(context, page_eval)

        # Build quality summary
        grade_counts: dict[str, int] = {}
        for pe in page_evals:
            grade_counts[pe.grade.value] = grade_counts.get(pe.grade.value, 0) + 1

        avg_words = round(total_words / len(page_evals), 1) if page_evals else 0.0

        quality = QualitySummary(
            pages_by_grade=grade_counts,
            avg_word_count=avg_words,
            claim_coverage=len(all_claim_ids) / max(len(all_claim_ids), 1),
        )

        # Build preliminary report for GO criteria
        report = EvaluationReport(
            verdict=Verdict.NO_GO,
            pages=page_evals,
            quality=quality,
        )

        # GO/NO-GO
        verdict, go_criteria = evaluate_go_criteria(report)

        # Root-cause diagnosis if NO-GO
        # TC-3880 Wave 2 (H8): Use min_severity="medium" so Grade C pages (3+ MEDIUMs)
        # are included in the diagnosis and become visible to the heal loop.
        diagnoses = []
        if verdict == Verdict.NO_GO:
            diagnoses = diagnose_root_causes(page_evals, min_severity="medium")

        elapsed = time.monotonic() - start_time

        final_report = EvaluationReport(
            verdict=verdict,
            pages=page_evals,
            quality=quality,
            gates=[],
            root_cause_diagnosis=diagnoses,
            go_criteria=go_criteria,
        )

        # TC-HYBRID-08: Cross-page consistency review (NO_GO only)
        cross_page_findings: list[Finding] = []
        if verdict == Verdict.NO_GO:
            try:
                from launcher.workers.evaluate.cross_page_review import run_cross_page_review
                _content_map = {p.slug: _page_content_cache.get(p.slug, "") for p in final_report.pages}
                cross_page_findings = run_cross_page_review(_content_map)
                if cross_page_findings:
                    context.emit_event(
                        "cross_page_contradictions_found",
                        {"count": len(cross_page_findings)},
                        worker=self.name,
                    )
                    logger.warning(
                        "[Evaluate] Cross-page contradictions: %d findings", len(cross_page_findings)
                    )
            except Exception:
                logger.debug("cross_page_review failed", exc_info=True)
        final_report = final_report.model_copy(update={"cross_page_findings": cross_page_findings})

        # TC-HYBRID-10: Compute API surface coverage metric
        _api_surface_obj = _load_api_surface_obj(context)
        _coverage = _compute_api_surface_coverage(page_evals, _api_surface_obj, _page_content_cache)
        if _coverage < 0.5 and _coverage > 0.0:
            context.emit_event(
                "evidence_quality_low",
                {"api_surface_coverage": _coverage},
                worker=self.name,
            )
            logger.warning("[Evaluate] Low API surface coverage: %.2f", _coverage)
        final_report = final_report.model_copy(update={"api_surface_coverage": _coverage})

        context.log.info(
            "[Evaluate] Complete: verdict=%s, %d pages, %.1fs",
            verdict.value, len(page_evals), elapsed,
        )
        context.emit_event("worker_completed", {
            "verdict": verdict.value,
            "pages": len(page_evals),
            "grades": grade_counts,
        }, worker=self.name)

        # Write evaluation summary artifact
        if _artifacts_enabled:
            _write_summary_artifact(context, final_report)

        return final_report

    async def self_review(self, output: LauncherBaseModel) -> SelfReviewResult:
        """Verify evaluation report consistency."""
        if not isinstance(output, EvaluationReport):
            return SelfReviewResult(passed=False, findings=[{"message": "Output is not EvaluationReport"}])

        report = output
        findings: list[dict[str, Any]] = []
        metrics: dict[str, Any] = {}

        # Check: all pages have a grade
        ungraded = [p.slug for p in report.pages if not p.grade]
        if ungraded:
            findings.append({
                "category": "ungraded_pages",
                "message": f"{len(ungraded)} pages without grades",
                "severity": "high",
            })

        # Check: GO verdict requires no critical findings
        if report.verdict == Verdict.GO:
            crit = sum(1 for p in report.pages for f in p.findings if f.severity == "critical")
            if crit > 0:
                findings.append({
                    "category": "invalid_go",
                    "message": f"GO verdict with {crit} critical findings",
                    "severity": "high",
                })

        # Metrics
        metrics["total_pages"] = len(report.pages)
        metrics["verdict"] = report.verdict.value
        metrics["grades"] = report.quality.pages_by_grade

        passed = not any(f.get("severity") == "high" for f in findings)
        return SelfReviewResult(passed=passed, findings=findings, metrics=metrics)


def create_worker() -> EvaluateWorker:
    return EvaluateWorker()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _compute_api_surface_coverage(
    pages: "list[PageEvaluation]",
    api_surface: "Any | None",
    page_content_cache: "dict[str, str] | None" = None,
) -> float:
    """Compute ratio of pages that mention at least one API identifier.

    Scans actual page *content* (from page_content_cache) for API class/method
    names — NOT finding messages.  Returns 0.0 when no API surface or no pages.

    TC-HYBRID-10: Used to emit evidence_quality_low event.
    """
    if not api_surface or not pages:
        return 0.0
    try:
        from launcher.models.product import ApiSurface
        if not isinstance(api_surface, ApiSurface):
            return 0.0
        # Collect all known identifiers (lowered for case-insensitive match)
        known_ids: set[str] = set()
        for ident in (api_surface.api_identifiers or []):
            known_ids.add(ident.lower())
        for cls in api_surface.class_briefs or []:
            known_ids.add(cls.name.lower())
            for m in cls.methods or []:
                known_ids.add(m.lower())
            for m in cls.typed_methods or []:
                known_ids.add(m.name.lower())
        if not known_ids:
            return 0.0

        _cache = page_content_cache or {}

        # Count pages where at least one API identifier appears in page content
        backed = sum(
            1 for p in pages
            if any(
                kid in _cache.get(p.slug, "").lower()
                for kid in known_ids
            )
        )
        return backed / len(pages) if pages else 0.0
    except Exception:
        return 0.0


def _run_deterministic_checks(
    content: str, slug: str, *, page_role: str = "", product_name: str = "",
    canonical_import: str = "", runtime_import: str = "",
    golden_dir: "Path | None" = None,
    claim_texts: "list[str] | None" = None,
    api_surface: "Any | None" = None,  # TC-HYBRID-05: ApiSurface | None
) -> list[Finding]:
    """Run all deterministic checks on a page."""
    findings: list[Finding] = []
    findings.extend(check_frontmatter(content, slug))
    findings.extend(check_structure(content, slug))
    findings.extend(check_code(content, slug, canonical_import=canonical_import, runtime_import=runtime_import))
    findings.extend(check_density(content, slug, page_role=page_role))
    findings.extend(check_spec_leakage(content, slug, page_role=page_role))
    findings.extend(check_claim_leakage(content, slug))
    findings.extend(check_artifacts(content, slug, product_name=product_name))
    findings.extend(check_safety(content, slug, page_role=page_role))
    findings.extend(check_seo(content, slug, product_name=product_name))
    findings.extend(check_repetition(content, slug, page_role=page_role))
    findings.extend(check_product_names(content, slug, product_name=product_name))
    findings.extend(check_semantic_structure(content, slug, page_role=page_role))
    findings.extend(check_reference_completeness(content, slug, page_role=page_role))
    findings.extend(check_readability_from_markdown(content, slug))
    findings.extend(check_golden_spec_from_markdown(content, slug, page_role, golden_dir))
    # TC-3880 Wave 2 (E4): claim coverage check — only runs when claim_texts populated.
    if claim_texts:
        findings.extend(check_claim_coverage(content, slug, claim_texts))
    # TC-HYBRID-05: API identifier verification (skips when api_surface is None/low confidence).
    findings.extend(check_api_identifiers(content, slug, api_surface=api_surface))
    # TC-HYBRID-06: Format contradiction + truth checks (skip when no format_matrix).
    findings.extend(check_contradiction(content, slug, api_surface=api_surface))
    findings.extend(check_format_truth(content, slug, api_surface=api_surface))
    return findings


_api_surface_cache: dict[str, str] = {}
_api_surface_obj_cache: dict[str, Any] = {}  # TC-HYBRID-05: caches full ApiSurface objects


def _load_api_surface_obj(context: WorkerContext) -> Any:
    """Load full ApiSurface model from understand checkpoint (cached per run).

    TC-HYBRID-05: Used by check_api_identifiers gate. Returns None when checkpoint
    is absent, malformed, or the api_surface key is missing.
    """
    run_id = context.run_id
    if run_id in _api_surface_obj_cache:
        return _api_surface_obj_cache[run_id]

    api_surface_obj = None
    try:
        import json as _json
        from launcher.models.product import ApiSurface as _ApiSurface
        cp_path = context.run_dir / "understand_checkpoint.json"
        if cp_path.exists():
            cp = _json.loads(cp_path.read_text(encoding="utf-8"))
            api_surface_data = cp.get("api_surface", {})
            if api_surface_data:
                api_surface_obj = _ApiSurface.model_validate(api_surface_data)
    except Exception:
        logger.debug("[Evaluate] Could not load ApiSurface object from checkpoint", exc_info=True)

    _api_surface_obj_cache[run_id] = api_surface_obj
    return api_surface_obj


def _load_api_surface_summary(context: WorkerContext) -> str:
    """Load API surface summary from understand checkpoint (cached per run)."""
    run_id = context.run_id
    if run_id in _api_surface_cache:
        return _api_surface_cache[run_id]

    summary = ""
    try:
        import json as _json
        cp_path = context.run_dir / "understand_checkpoint.json"
        if cp_path.exists():
            cp = _json.loads(cp_path.read_text(encoding="utf-8"))
            briefs = cp.get("api_surface", {}).get("class_briefs", [])
            lines = []
            for b in briefs[:50]:
                parts = [b["name"]]
                if b.get("methods"):
                    parts.append(f"methods: {', '.join(b['methods'][:8])}")
                if b.get("properties"):
                    parts.append(f"props: {', '.join(b['properties'][:5])}")
                lines.append(" — ".join(parts))
            if lines:
                summary = "\n".join(f"- {line}" for line in lines)
    except Exception:
        logger.debug("[Evaluate] Could not load API surface summary", exc_info=True)

    _api_surface_cache[run_id] = summary
    return summary


async def _run_llm_review(
    content: str,
    gen_page: Any,
    context: WorkerContext,
    *,
    skills_criteria: str = "",
    phase_a_findings: "list[Finding] | None" = None,
    use_lite_mode: bool = False,
) -> tuple[Grade | None, list[Finding]]:
    """Run Phase B LLM review on a page.

    TC-3882 Wave 4 (E8/H4):
    - E8: use_lite_mode selects review_prompt_lite.txt (4 checks only)
    - H4: phase_a_findings injected into Phase B prompt context
    """
    from launcher.workers.evaluate.llm_review import llm_review_page

    product_name = context.config.display_name or context.config.product_name or ""
    api_summary = _load_api_surface_summary(context)

    # H4: Build heal context from heal_metadata if available
    _heal_meta: dict = getattr(context, "heal_metadata", None) or {}
    _heal_context_parts: list[str] = []
    if _heal_meta.get("priority_checks"):
        _heal_context_parts.append(f"Priority checks: {', '.join(_heal_meta['priority_checks'])}")
    if _heal_meta.get("root_causes"):
        _heal_context_parts.append(f"Root causes: {', '.join(_heal_meta['root_causes'])}")
    if _heal_meta.get("strategy"):
        _heal_context_parts.append(f"Strategy: {_heal_meta['strategy']}")
    heal_context = "\n".join(_heal_context_parts)

    return await llm_review_page(
        content=content,
        slug=gen_page.slug,
        page_role=gen_page.page_role,
        page_title=gen_page.slug,
        assigned_claims=gen_page.claim_ids_used,
        product_name=product_name,
        canonical_import=getattr(context.config, "runtime_import", "") or context.config.canonical_import or "",
        platform=context.config.platform,
        context=context,
        api_surface_summary=api_summary,
        skills_criteria=skills_criteria,
        phase_a_findings=phase_a_findings,
        heal_context=heal_context,
        use_lite_mode=use_lite_mode,
    )


def _safe_slug(slug: str) -> str:
    """Sanitize slug for safe use as a filename."""
    # Preserve path structure: replace / with -- before general sanitization
    # so that distinct paths like "a/b_c" and "a_b/c" produce distinct filenames.
    result = slug.replace("/", "--")
    return re.sub(r"[^a-zA-Z0-9_-]", "_", result) or "unknown"


def _write_page_artifact(context: WorkerContext, page_eval: PageEvaluation) -> None:
    """Write a per-page evaluation artifact to disk."""
    try:
        safe = _safe_slug(page_eval.content_path or page_eval.slug)
        context.store.write_json(
            f"evaluation/pages/{safe}.eval.json",
            page_eval.model_dump(mode="json"),
        )
    except Exception:
        logger.warning(
            "[Evaluate] Failed to write page artifact for %s",
            page_eval.slug,
            exc_info=True,
        )


def _write_summary_artifact(context: WorkerContext, report: EvaluationReport) -> None:
    """Write the full evaluation summary artifact to disk."""
    try:
        context.store.write_json(
            "evaluation/evaluation_summary.json",
            report.model_dump(mode="json"),
        )
    except Exception:
        logger.warning(
            "[Evaluate] Failed to write evaluation summary artifact",
            exc_info=True,
        )


def _aggregate_check_results(findings: list[Finding]) -> dict[str, bool]:
    """Aggregate findings into per-check pass/fail."""
    checks_seen: dict[str, bool] = {}
    for f in findings:
        if f.check not in checks_seen:
            checks_seen[f.check] = True
        if f.severity in ("critical", "high"):
            checks_seen[f.check] = False
    return checks_seen
