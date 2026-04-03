"""Evaluate worker — quality assessment and GO/NO-GO decision.

Phase A: Run deterministic checks on each generated page.
Phase B: Optional LLM-based review for deeper evaluation.
Grading: Assign A-F grades based on findings severity.
Verdict: Evaluate GO/NO-GO criteria against aggregate results.
Diagnosis: Map failures back to responsible upstream workers.
"""
from __future__ import annotations

import logging
import re
import time
from collections import Counter
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
    check_api_allowlist,       # TC-REG-301: prose-level backtick identifier check
    check_api_identifiers,  # TC-HYBRID-05
    check_artifacts,
    check_opener_boilerplate,  # TC-QG-01
    check_claim_coverage,  # TC-3880 Wave 2 (E4)
    check_claim_leakage,
    check_code,
    check_contradiction,   # TC-HYBRID-06
    check_density,
    check_format_truth,    # TC-HYBRID-06
    check_frontmatter,
    check_golden_spec_from_markdown,
    check_install_recipe,  # TC-HO-02
    check_limitations_contradiction,  # TC-HO-01
    check_product_names,
    check_readability_from_markdown,
    check_reference_completeness,
    check_repetition,
    check_route_consistency,  # TC-4050 (Wave 4A)
    check_safety,
    check_semantic_structure,
    check_seo,
    check_spec_leakage,
    check_structure,
    # --- TC-EVAL-500: Wire disconnected checks (Wave 1 — critical) ---
    check_forbidden_content,
    check_content_utility,
    check_link_validity,
    check_code_completeness_workflow,
    check_faq_structure,
    check_contract_compliance,
    # --- TC-EVAL-500: Wire disconnected checks (Wave 2 — quality) ---
    check_golden_conformance,
    check_heading_echo,
    check_prose_lead,
    check_sentence_openings,
    check_paragraph_monotony,
    check_explanation_gap,
    check_low_specificity,
    # --- TC-EVAL-500: structure.py uncalled functions ---
    check_section_order,
    check_terminal_section,
    check_duplicate_sections,
    # --- TC-EVAL-500: hallucination_rate additional functions ---
    check_content_grounding,
    # --- TC-EVAL-502: New checks ---
    check_code_platform,
    check_ecosystem_contamination,  # TC-5329: wrong-ecosystem code token detection
    check_unsourced_metrics,
    check_content_viability,
    # --- TC-5308: Extraction quality gate ---
    check_extraction_quality,
)
from launcher.io.run_layout import RunLayout
from launcher.util.errors import WorkerError
from launcher.workers.evaluate.diagnosis import diagnose_root_causes
from launcher.workers.evaluate.go_criteria import evaluate_go_criteria
from launcher.workers.evaluate.grader import annotate_graded_severity, grade_page

logger = logging.getLogger(__name__)


from launcher.orchestrator.stream_events import safe_stream_event as _safe_stream_event


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

        # TC-5306: Detect stale understanding checkpoint (side-load traceability).
        _uc_run_id = getattr(manifest, "understanding_checkpoint_run_id", None)
        if _uc_run_id is not None and _uc_run_id != context.run_id:
            logger.warning(
                "TC-5306: ContentManifest built from stale understanding checkpoint "
                "(checkpoint run_id=%r, current run_id=%r). "
                "Evaluate may be using evidence from a different run.",
                _uc_run_id,
                context.run_id,
            )

        # TC-HO-09-R: Emit checkpoint_fallback for missing manifest fields
        _emitted_pe_fallback = False
        if not getattr(manifest, "api_fact_member_names", None):
            context.emit_event("checkpoint_fallback", {
                "field": "extraction_db",
                "reason": "not_in_manifest",
            }, worker=self.name)
        _pe = getattr(manifest, "product_evidence", None)
        if _pe is None or (hasattr(_pe, "limitations") and not _pe.limitations
                           and not getattr(_pe, "capabilities", None)
                           and not getattr(_pe, "install_recipe", None)
                           and not getattr(_pe, "input_formats", None)
                           and not getattr(_pe, "output_formats", None)):
            context.emit_event("checkpoint_fallback", {
                "field": "product_evidence",
                "reason": "manifest_product_evidence_empty",
            }, worker=self.name)
            _emitted_pe_fallback = True
        _as = getattr(manifest, "api_surface", None)
        if _as is not None and not getattr(_as, "public_classes", None):
            context.emit_event("checkpoint_fallback", {
                "field": "api_surface",
                "reason": "empty_in_manifest",
            }, worker=self.name)

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

        # HC-TIER-01: Load repo-level richness_tier once per run for tier-aware thresholds.
        # check_density and check_structure use _TIER_DENSITY / _TIER_HEADING when tier passed.
        # Default "A" is conservative (strictest thresholds — no false negatives on load failure).
        _richness_tier_str: str = "A"
        try:
            _rt_cp = _load_understand_checkpoint(context)
            _rt_obj = _rt_cp.get("richness_tier", {})
            _richness_tier_str = _rt_obj.get("tier", "A") if isinstance(_rt_obj, dict) else "A"
        except Exception:
            pass  # Checkpoint absent or malformed — conservative default

        # TC-HAL-09: Lazy-load claims_by_id from understand checkpoint (once per run)
        _hal09_claims_by_id: dict[str, Any] | None = None
        _hal09_claims_load_attempted = False

        def _get_claims_by_id() -> dict[str, Any]:
            nonlocal _hal09_claims_by_id, _hal09_claims_load_attempted
            if _hal09_claims_load_attempted:
                return _hal09_claims_by_id or {}
            _hal09_claims_load_attempted = True
            try:
                import json as _json
                _cp_path = context.run_dir / "understand_checkpoint.json"
                if _cp_path.exists():
                    _raw = _json.loads(_cp_path.read_text(encoding="utf-8"))
                    from launcher.models.claims import Claim as _Claim
                    _hal09_claims_by_id = {
                        c["claim_id"]: _Claim.model_validate(c)
                        for c in _raw.get("claims", [])
                        if isinstance(c, dict) and "claim_id" in c
                    }
            except Exception:
                logger.debug("[Evaluate] TC-HAL-09: failed to load claims for hallucination check", exc_info=True)
            return _hal09_claims_by_id or {}

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
            # TC-HO-09: Prefer api_surface and product_evidence from graph-state
            # manifest fields (populated by Generate worker from UnderstandingBundle).
            # Fall back to disk side-loads only when manifest fields are empty
            # (backward compatibility with runs produced before TC-HO-09).
            _manifest_api = manifest.api_surface
            _manifest_pe = manifest.product_evidence
            _use_manifest_api = bool(
                _manifest_api.public_classes or _manifest_api.api_identifiers
            )
            _use_manifest_pe = bool(
                _manifest_pe.supported_formats
                or _manifest_pe.input_formats
                or _manifest_pe.output_formats
                or _manifest_pe.limitations
                or _manifest_pe.install_recipe is not None
            )
            _api_surface_arg = (
                _manifest_api if _use_manifest_api else _load_api_surface_obj(context)
            )
            _pe_raw = _manifest_pe.model_dump(mode="json") if _use_manifest_pe else _load_product_evidence(context)
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
                # TC-HO-09: prefers manifest field over disk side-load.
                api_surface=_api_surface_arg,
                # TC-HO-01/02: pass product_evidence for limitations + install recipe checks.
                # TC-HO-09: prefers manifest field (as dict) over disk side-load.
                product_evidence=_pe_raw,
                # HC-TIER-01: pass repo-level richness tier for calibrated density/structure thresholds.
                richness_tier=_richness_tier_str,
                # TC-5308: pass extraction_completeness for thin-extraction quality gating.
                extraction_completeness=getattr(manifest, "extraction_completeness", None),
            )

            # TC-HAL-09: Hallucination rate check
            try:
                from launcher.workers.evaluate.checks.hallucination_rate import check_hallucination_rate as _check_hal
                _hal_findings_raw, _hal_rate = _check_hal(
                    getattr(gen_page, 'claim_ids_used', []) or [],
                    _get_claims_by_id(),
                )
                for _hf in _hal_findings_raw:
                    findings.append(Finding(
                        check=_hf["check"],
                        message=_hf["message"],
                        severity=_hf["severity"],
                        location=_hf.get("location", ""),
                    ))
            except Exception:
                logger.debug("[Evaluate] TC-HAL-09: hallucination_rate check skipped", exc_info=True)

            # TC-5164: Evidence adequacy attribution (reads page_evidence_index from manifest)
            _pei = getattr(manifest, "page_evidence_index", {}) or {}
            if _pei:
                try:
                    from launcher.workers.evaluate.checks.evidence_adequacy import (
                        check_evidence_adequacy as _check_ea,
                    )
                    for _ea_f in _check_ea(gen_page, _pei):
                        findings.append(Finding(
                            check=_ea_f["check"],
                            message=_ea_f["message"],
                            severity=_ea_f["severity"],
                            location=_ea_f.get("location", ""),
                        ))
                except Exception:
                    logger.debug("[Evaluate] TC-5164: evidence_adequacy check skipped", exc_info=True)

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
                        manifest_api_surface=manifest.api_surface,  # TC-HO-09: prefer graph state
                    )
                findings.extend(llm_findings)

            # TC-5316: Annotate graded_severity before building PageEvaluation so
            # routing decisions downstream can use the grader's actual effective severity
            # rather than the reported severity (which may differ for LLM checks).
            findings = annotate_graded_severity(findings)
            grade = grade_page(findings)
            check_results = _aggregate_check_results(findings)
            page_eval = PageEvaluation(
                slug=gen_page.slug,
                content_path=gen_page.content_path,
                grade=grade,
                findings=findings,
                check_results=check_results,
            )
            await _safe_stream_event("page_evaluated", {
                "slug": gen_page.slug,
                "grade": grade.value if hasattr(grade, "value") else str(grade),
                "findings": len(findings),
            })
            return (page_eval, gen_page.word_count, set(gen_page.claim_ids_used))

        # TC-DET-001: Sequential page evaluation for deterministic ordering.
        # Pages are evaluated in manifest order to eliminate concurrency-induced
        # non-determinism (LLM review results depend on order when semaphore is shared).
        raw_eval_results: list[tuple | BaseException] = []
        for gp in manifest.pages:
            try:
                result = await _evaluate_page_llm(gp)
                raw_eval_results.append(result)
            except BaseException as exc:
                raw_eval_results.append(exc)

        page_evals: list[PageEvaluation] = []
        total_words = 0
        all_claim_ids: set[str] = set()  # covered claim IDs (actually used in generated pages)
        # TC-5304: collect all assigned claim IDs from manifest to compute real coverage fraction.
        # Previously the formula used len(covered)/max(len(covered), 1) which always = 1.0.
        all_assigned_claim_ids: set[str] = set()
        for gp in manifest.pages:
            all_assigned_claim_ids.update(getattr(gp, "assigned_claim_ids", []) or [])

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
                    new_findings = annotate_graded_severity(
                        list(page_evals[idx].findings) + [Finding(
                            check="permalink",
                            message=f"Permalink collision: '{path_key}' used by {len(indices)} pages",
                            severity="critical",
                            location=page_evals[idx].slug,
                        )]
                    )
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

        # TC-5304/TC-5327: real coverage = covered ∩ assigned / assigned.
        # Fall back to 1.0 only when nothing was assigned (nothing to cover).
        if not all_assigned_claim_ids:
            logger.debug("TC-5327: no assigned claims — claim_coverage defaulting to 1.0")
            _claim_coverage = 1.0
        else:
            _claim_coverage = len(all_claim_ids & all_assigned_claim_ids) / len(all_assigned_claim_ids)

        quality = QualitySummary(
            pages_by_grade=grade_counts,
            avg_word_count=avg_words,
            claim_coverage=_claim_coverage,
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
        # TC-HO-09: prefer manifest api_surface over disk side-load when available.
        _manifest_api_top = manifest.api_surface
        _api_surface_obj = (
            _manifest_api_top
            if (_manifest_api_top.public_classes or _manifest_api_top.api_identifiers)
            else _load_api_surface_obj(context)
        )
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


def _run_check(
    check_fn: "Any", findings: "list[Finding]", _log_slug: str, *args: "Any", **kwargs: "Any"
) -> None:
    """ICS-02: Run one deterministic check, accumulate findings, log per-check counts."""
    try:
        result = check_fn(*args, **kwargs)
        if result:
            logger.debug(
                "[Evaluate] check=%s slug=%s findings=%d",
                check_fn.__name__, _log_slug, len(result),
            )
        findings.extend(result)
    except Exception:
        logger.warning(
            "[Evaluate] check=%s slug=%s FAILED — skipped", check_fn.__name__, _log_slug,
            exc_info=True,
        )


def _run_deterministic_checks(
    content: str, slug: str, *, page_role: str = "", product_name: str = "",
    canonical_import: str = "", runtime_import: str = "",
    golden_dir: "Path | None" = None,
    claim_texts: "list[str] | None" = None,
    api_surface: "Any | None" = None,  # TC-HYBRID-05: ApiSurface | None
    product_evidence: "dict | None" = None,  # TC-HO-01/02: from understand checkpoint
    richness_tier: str = "A",  # HC-TIER-01: repo-level tier for calibrated thresholds
    extraction_completeness: "Any | None" = None,  # TC-5308: ExtractionCompleteness | None
) -> list[Finding]:
    """Run all deterministic checks on a page."""
    findings: list[Finding] = []
    _run_check(check_frontmatter, findings, slug, content, slug)
    _run_check(check_structure, findings, slug, content, slug, richness_tier=richness_tier)
    _run_check(check_code, findings, slug, content, slug, canonical_import=canonical_import, runtime_import=runtime_import)
    _run_check(check_density, findings, slug, content, slug, page_role=page_role, richness_tier=richness_tier)
    _run_check(check_spec_leakage, findings, slug, content, slug, page_role=page_role)
    _run_check(check_claim_leakage, findings, slug, content, slug)
    _run_check(check_artifacts, findings, slug, content, slug, product_name=product_name)
    _run_check(check_opener_boilerplate, findings, slug, content, slug)
    _run_check(check_safety, findings, slug, content, slug, page_role=page_role)
    _run_check(check_seo, findings, slug, content, slug, product_name=product_name)
    _run_check(check_repetition, findings, slug, content, slug, page_role=page_role)
    _run_check(check_product_names, findings, slug, content, slug, product_name=product_name)
    _run_check(check_semantic_structure, findings, slug, content, slug, page_role=page_role)
    _run_check(check_reference_completeness, findings, slug, content, slug, page_role=page_role)
    _run_check(check_readability_from_markdown, findings, slug, content, slug)
    _run_check(check_golden_spec_from_markdown, findings, slug, content, slug, page_role, golden_dir)
    # TC-3880 Wave 2 (E4): claim coverage check — only runs when claim_texts populated.
    if claim_texts:
        _run_check(check_claim_coverage, findings, slug, content, slug, claim_texts)
    # TC-HYBRID-05: API identifier verification (skips when api_surface is None/low confidence).
    _run_check(check_api_identifiers, findings, slug, content, slug, api_surface=api_surface)
    # TC-REG-301: Prose-level backtick identifier check (skips when api_surface is None).
    _run_check(check_api_allowlist, findings, slug, content, api_surface, slug)
    # TC-HYBRID-06: Format contradiction + truth checks (skip when no format_matrix).
    _run_check(check_contradiction, findings, slug, content, slug, api_surface=api_surface)
    _run_check(check_format_truth, findings, slug, content, slug, api_surface=api_surface)
    # TC-4050 (Wave 4A): route consistency — slug topic words must appear in prose.
    _run_check(check_route_consistency, findings, slug, content, slug, page_role=page_role)
    # TC-HO-01: Limitations contradiction — content must not affirm unsupported/deprecated features.
    _run_check(check_limitations_contradiction, findings, slug, content, slug, product_evidence=product_evidence)
    # TC-HO-02: Install recipe — install pages must use the correct install command.
    _run_check(check_install_recipe, findings, slug, content, slug, page_role=page_role, product_evidence=product_evidence)
    # --- TC-EVAL-500: Wire disconnected checks (Wave 1 — critical) ---
    _run_check(check_forbidden_content, findings, slug, content, slug)
    _run_check(check_content_utility, findings, slug, content, slug)
    _run_check(check_link_validity, findings, slug, content, slug)
    _run_check(check_code_completeness_workflow, findings, slug, content, slug, page_role=page_role)
    _run_check(check_faq_structure, findings, slug, content, slug, page_role=page_role)
    _run_check(check_contract_compliance, findings, slug, content, slug, page_role=page_role, product_name=product_name)
    # --- TC-EVAL-500: Wire disconnected checks (Wave 2 — quality) ---
    _run_check(check_golden_conformance, findings, slug, content, slug, page_role=page_role, golden_dir=golden_dir)
    _run_check(check_heading_echo, findings, slug, content, slug)
    _run_check(check_prose_lead, findings, slug, content, slug, page_role=page_role, product_name=product_name)
    _run_check(check_sentence_openings, findings, slug, content, slug, page_role=page_role)
    _run_check(check_paragraph_monotony, findings, slug, content, slug)
    _run_check(check_explanation_gap, findings, slug, content, slug, page_role=page_role)
    _run_check(check_low_specificity, findings, slug, content, slug, page_role=page_role)
    # --- TC-EVAL-500: structure.py uncalled functions ---
    _run_check(check_section_order, findings, slug, content, slug, page_role=page_role)
    _run_check(check_terminal_section, findings, slug, content, slug)
    _run_check(check_duplicate_sections, findings, slug, content, slug)
    # --- TC-EVAL-500: hallucination_rate — content grounding (conditional) ---
    if claim_texts:
        _run_check(check_content_grounding, findings, slug, content, claim_texts, slug=slug)
    # --- TC-EVAL-502: New checks ---
    _run_check(check_code_platform, findings, slug, content, slug, page_role=page_role)
    _run_check(check_ecosystem_contamination, findings, slug, content, slug, page_role=page_role)  # TC-5329
    _run_check(check_unsourced_metrics, findings, slug, content, slug)
    _run_check(check_content_viability, findings, slug, content, slug)
    # --- TC-5308: Extraction quality gate ---
    # SR-02: signature is (slug, content, location, *, ...) — pass slug as first positional arg
    _run_check(check_extraction_quality, findings, slug, slug, content, slug, extraction_completeness=extraction_completeness)
    # ICS-02: aggregate finding counts by severity for observability
    by_sev = Counter(f.severity for f in findings)
    logger.info(
        "[Evaluate] deterministic_checks slug=%s total=%d critical=%d high=%d medium=%d low=%d",
        slug, len(findings),
        by_sev.get("critical", 0),
        by_sev.get("high", 0),
        by_sev.get("medium", 0),
        by_sev.get("low", 0),
    )
    return findings


_api_surface_cache: dict[str, str] = {}
_api_surface_obj_cache: dict[str, Any] = {}  # TC-HYBRID-05: caches full ApiSurface objects
_product_evidence_cache: dict[str, Any] = {}  # TC-HO-01/02: caches product_evidence dict


def _load_understand_checkpoint(context: WorkerContext) -> dict:
    """Load understand_checkpoint.json or raise WorkerError.

    TC-HO-03: Single authoritative loader for the understand checkpoint.
    Raises WorkerError (not returns None) when the file is absent or malformed,
    making checkpoint absence a hard failure visible to callers.

    Returns
    -------
    dict
        The fully parsed checkpoint dict. Callers extract sub-dicts as needed,
        e.g. ``cp.get("api_surface", {})`` or ``cp.get("product_evidence", {})``.

    Raises
    ------
    WorkerError
        If ``understand_checkpoint.json`` does not exist under ``context.run_dir``.
    WorkerError
        If the file exists but is not valid JSON.
    """
    import json as _json

    cp_path = context.run_dir / "understand_checkpoint.json"
    if not cp_path.exists():
        raise WorkerError(
            f"understand_checkpoint.json not found at {cp_path}. "
            "Run the Understand worker before Evaluate."
        )
    try:
        with cp_path.open(encoding="utf-8") as _f:
            return _json.load(_f)
    except _json.JSONDecodeError as exc:
        raise WorkerError(
            f"understand_checkpoint.json is malformed: {exc}"
        ) from exc


def _load_api_surface_obj(context: WorkerContext) -> Any:
    """Load full ApiSurface model from understand checkpoint (cached per run).

    TC-HYBRID-05: Used by check_api_identifiers gate. Returns None when checkpoint
    is absent, malformed, or the api_surface key is missing.

    Delegates to ``_load_understand_checkpoint`` for the actual I/O; keeps the
    per-run_id cache and the silent-None fallback for backward compatibility with
    call sites that handle None.
    """
    run_id = context.run_id
    if run_id in _api_surface_obj_cache:
        return _api_surface_obj_cache[run_id]

    api_surface_obj = None
    try:
        from launcher.models.product import ApiSurface as _ApiSurface
        cp = _load_understand_checkpoint(context)
        api_surface_data = cp.get("api_surface", {})
        if api_surface_data:
            api_surface_obj = _ApiSurface.model_validate(api_surface_data)
    except Exception:
        logger.debug("[Evaluate] Could not load ApiSurface object from checkpoint", exc_info=True)

    _api_surface_obj_cache[run_id] = api_surface_obj
    return api_surface_obj


def _load_product_evidence(context: WorkerContext) -> "dict | None":
    """Load product_evidence dict from understand checkpoint (cached per run).

    TC-HO-01/02: Used by check_limitations_contradiction and check_install_recipe.
    Returns None when checkpoint is absent, malformed, or the product_evidence
    key is missing. Callers must handle None gracefully.
    """
    run_id = context.run_id
    if run_id in _product_evidence_cache:
        return _product_evidence_cache[run_id]

    product_evidence: dict | None = None
    try:
        cp = _load_understand_checkpoint(context)
        pe_data = cp.get("product_evidence")
        if pe_data and isinstance(pe_data, dict):
            product_evidence = pe_data
    except Exception:
        logger.debug("[Evaluate] Could not load product_evidence from checkpoint", exc_info=True)

    _product_evidence_cache[run_id] = product_evidence
    return product_evidence


def _build_api_surface_summary_from_briefs(briefs: list) -> str:
    """Build an API surface summary string from class_briefs dicts.

    HG-19: Prefers typed_methods (complete AST-extracted list) over the methods
    string list (which is capped and may omit important methods like Scene.open,
    Scene.save, Scene.from_file). Same preference applied to typed_properties.
    This prevents false-positive factual_accuracy findings in the LLM reviewer
    when valid API methods are absent from the incomplete methods list.
    """
    lines = []
    for b in briefs[:50]:
        parts = [b["name"]]
        # HG-19: Prefer typed_methods (complete AST list) over methods (capped string list).
        # Deduplicate by name first: getter/setter pairs share a name and waste cap slots,
        # pushing key methods like open/save/from_file past the cap.
        typed_methods = b.get("typed_methods") or []
        if typed_methods:
            seen_names: set[str] = set()
            unique_names: list[str] = []
            for m in typed_methods:
                n = m["name"]
                if n not in seen_names:
                    seen_names.add(n)
                    unique_names.append(n)
            parts.append(f"methods: {', '.join(unique_names[:16])}")
        elif b.get("methods"):
            parts.append(f"methods: {', '.join(b['methods'][:8])}")
        # HG-19: Prefer typed_properties names over properties string list
        typed_props = b.get("typed_properties") or []
        if typed_props:
            prop_names = [p["name"] for p in typed_props[:8]]
            parts.append(f"props: {', '.join(prop_names)}")
        elif b.get("properties"):
            parts.append(f"props: {', '.join(b['properties'][:5])}")
        lines.append(" — ".join(parts))
    return "\n".join(f"- {line}" for line in lines) if lines else ""


def _load_api_surface_summary(context: WorkerContext) -> str:
    """Load API surface summary from understand checkpoint (cached per run).

    Delegates to ``_load_understand_checkpoint`` for the actual I/O; keeps the
    per-run_id cache and the silent-empty-string fallback for backward
    compatibility with call sites in the LLM review path.
    """
    run_id = context.run_id
    if run_id in _api_surface_cache:
        return _api_surface_cache[run_id]

    summary = ""
    try:
        cp = _load_understand_checkpoint(context)
        briefs = cp.get("api_surface", {}).get("class_briefs", [])
        summary = _build_api_surface_summary_from_briefs(briefs)
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
    manifest_api_surface: "Any | None" = None,
) -> tuple[Grade | None, list[Finding]]:
    """Run Phase B LLM review on a page.

    TC-3882 Wave 4 (E8/H4):
    - E8: use_lite_mode selects review_prompt_lite.txt (4 checks only)
    - H4: phase_a_findings injected into Phase B prompt context

    TC-HO-09: accepts manifest_api_surface to prefer graph-state over disk side-load.
    """
    from launcher.workers.evaluate.llm_review import llm_review_page

    product_name = context.config.display_name or context.config.product_name or ""
    # TC-HO-09: prefer manifest api_surface for summary when available.
    if manifest_api_surface is not None and (
        getattr(manifest_api_surface, "public_classes", None)
        or getattr(manifest_api_surface, "api_identifiers", None)
    ):
        _briefs = [
            b.model_dump(mode="json") if hasattr(b, "model_dump") else b
            for b in (getattr(manifest_api_surface, "class_briefs", None) or [])
        ]
        api_summary = _build_api_surface_summary_from_briefs(_briefs)
    else:
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


_SEVERITY_PENALTY: dict[str, int] = {
    "critical": 25,
    "high": 10,
    "medium": 5,
    "low": 2,
}
_CONFORMANCE_WEIGHT = 0.35
_FINDINGS_WEIGHT = 0.65


def _compute_numeric_score(
    findings: "list[Finding]",
    conformance: float | None,
) -> float:
    """Compute a 0-100 numeric quality score from findings + golden conformance.

    TC-FIX-214: Blended score used by grading pipeline.
    ``findings_base`` = 100 - sum(severity penalties).
    When *conformance* is not None, blended as:
        ``findings_base * 0.65 + conformance * 100 * 0.35``
    """
    penalty = sum(_SEVERITY_PENALTY.get(f.severity, 0) for f in findings)
    base = max(0.0, 100.0 - penalty)

    if conformance is None:
        return base

    return round(base * _FINDINGS_WEIGHT + conformance * 100 * _CONFORMANCE_WEIGHT, 2)


def _compute_claim_coverage(
    pages: "list[Any]",
    page_evals: "list[PageEvaluation]",
) -> float:
    """Compute claim coverage ratio: (assigned - uncovered) / assigned.

    TC-PA-01: Aggregates uncovered_claim_texts counts from claim_coverage findings
    across all page evaluations relative to total assigned claims from page manifests.

    Returns 1.0 when no claims are assigned (backward compat with old manifests).
    """
    total_assigned = sum(getattr(p, "assigned_claim_count", 0) for p in pages)
    if total_assigned == 0:
        return 1.0

    total_uncovered = 0
    for pe in page_evals:
        for f in pe.findings:
            if f.check == "claim_coverage":
                total_uncovered += len(getattr(f, "uncovered_claim_texts", []))

    return round(1.0 - (total_uncovered / total_assigned), 4)
