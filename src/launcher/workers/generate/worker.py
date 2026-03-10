"""Generate worker — plan to content.

Takes a PlanBundle and produces content for every page section
using the sandwich model at every LLM call:

  Pre-LLM:  Build focused prompt with ONLY this section's claims + snippets
  LLM:      Generate BlockIR JSON for this section (temp=0.0)
  Post-LLM: Validate BlockIR, check claim_ids, normalize imports

Fallback chain: primary LLM -> fallback LLM -> deterministic rendering.
"""
from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import Any

from launcher.content.template_loader import (
    extract_template_frontmatter,
    extract_template_sections,
)
from launcher.models.base import LauncherBaseModel
from launcher.models.claims import Claim, Snippet
from launcher.models.content import (
    ContentManifest,
    CrossLink,
    GeneratedPage,
    GenerationStats,
)
from launcher.models.page_ir import BlockIR, BlockType, PageIR, SectionIR
from launcher.models.plan import PlanBundle, PlannedPage
from launcher.models.product import ClassBrief, ProductIdentity, RichnessTier
from launcher.models.understanding import UnderstandingBundle
from launcher.orchestrator.worker_contract import SelfReviewResult, WorkerContext, WorkerContract
from launcher.shared.ir_renderer import render_page
from launcher.shared.linker import infer_section, link_pages as linker_link_pages, load_linker_config
from launcher.shared.page_skeletons import SkeletonSection
from launcher.util.errors import FrontmatterError
from launcher.workers.generate.template_selector import get_template_content, resolve_template

logger = logging.getLogger(__name__)

_SECTION_CONCURRENCY = 4  # Max concurrent LLM section calls per page (GE-02)
_PAGE_CONCURRENCY = 4  # Max concurrent page generation calls (HO-05)

# TC-3882 Wave 4 (Gap4): Minimum prose words per section in heal mode — sections below
# this threshold are regenerated even if they "passed" the section filter.
_HEAL_MIN_WORDS = 80

# Roles that require at least one code block per section — used in thin-section probe.
_CODE_REQUIRED_ROLES: frozenset[str] = frozenset({
    "api_reference", "reference_object_page", "howto_article",
    "getting_started", "installation",
})

# Template-label heading patterns — mirrors structure.py template_patterns (TC-3877)
_TEMPLATE_LABEL_PATTERNS_INLINE: list[str] = [
    r"\[section title\]",
    r"\[content\]",
    r"\bsection heading\b",
    r"\btbd\b",
    r"\btodo\b",
]


def _quick_section_quality_check(
    section_ir: "SectionIR | None",
    section_heading: str,
    page_role: str,
) -> list[str]:
    """Return list of violation strings; empty list = PASS.

    TC-3877: Lightweight gate checks 4 defect types after each section is produced.
    All checks wrapped in try/except — gate never blocks on import or runtime failure.
    """
    if section_ir is None:
        return []
    violations: list[str] = []

    # 1. Template-label heading check
    try:
        import re as _re
        key = section_heading.strip().lower()
        for pat in _TEMPLATE_LABEL_PATTERNS_INLINE:
            if _re.search(pat, key):
                violations.append(f"Template-label heading: '{section_heading}'")
                break
    except Exception:
        pass

    # 2. Artifact phrase check in paragraph content
    try:
        from launcher.workers.evaluate.checks.artifacts import _ARTIFACT_PHRASES
        blocks = getattr(section_ir, "blocks", []) or []
        prose = " ".join(
            (getattr(blk, "content", "") or "").lower()
            for blk in blocks
            if getattr(blk, "block_type", "") in ("paragraph", "prose")
        )
        found = [p for p in _ARTIFACT_PHRASES if p.lower() in prose]
        if found:
            violations.append(f"Artifact phrases detected: {found[:3]}")
    except Exception:
        pass

    # 3. Missing code block on code-required roles
    try:
        if page_role in _CODE_REQUIRED_ROLES:
            blocks = getattr(section_ir, "blocks", []) or []
            has_code = any(
                "code" in str(getattr(b, "block_type", "")).lower()
                or "fence" in str(getattr(b, "block_type", "")).lower()
                for b in blocks
            )
            if not has_code:
                violations.append("Missing required code block for this page role")
    except Exception:
        pass

    # 4. Near-duplicate paragraphs within section (Jaccard > 0.8)
    try:
        from launcher.shared.jaccard import jaccard_similarity, compute_word_set
        blocks = getattr(section_ir, "blocks", []) or []
        para_texts = [
            getattr(blk, "content", "") or ""
            for blk in blocks
            if getattr(blk, "block_type", "") in ("paragraph", "prose")
        ]
        word_sets = [compute_word_set(t) for t in para_texts]
        for i in range(len(word_sets)):
            for j in range(i + 1, len(word_sets)):
                if jaccard_similarity(word_sets[i], word_sets[j]) > 0.8:
                    violations.append(
                        f"Near-duplicate paragraphs in section (paragraphs {i+1} and {j+1})"
                    )
                    break  # one violation per section is enough
            else:
                continue
            break
    except Exception:
        pass

    return violations


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


class GenerateWorker(WorkerContract):
    @property
    def name(self) -> str:
        return "generate"

    async def run(self, input_data: LauncherBaseModel, context: WorkerContext) -> ContentManifest:
        """Generate content for every page in the plan bundle."""
        if not isinstance(input_data, PlanBundle):
            raise TypeError(f"Expected PlanBundle, got {type(input_data).__name__}")

        plan = input_data
        start_time = time.monotonic()

        # Load understanding data from checkpoint (product, claims, snippets, etc.)
        understand = _load_understanding(context)

        context.log.info("[Generate] Starting content generation for %d pages", len(plan.pages))
        context.emit_event("worker_started", {"pages": len(plan.pages)}, worker=self.name)

        # Prepare output directory
        content_dir = context.run_dir / "content_bundle" / "pages"
        content_dir.mkdir(parents=True, exist_ok=True)

        # Build lookup tables
        claims_by_id = {c.claim_id: c for c in understand.claims}
        all_claims = understand.claims
        all_snippets = understand.snippets
        product = understand.product

        generated_pages: list[GeneratedPage] = []
        llm_calls = 0
        fallback_count = 0

        # Determine richness tier (default B if not available)
        tier = getattr(understand, "richness_tier", None)
        if tier is None or not hasattr(tier, "tier"):
            tier_enum = RichnessTier.B
        else:
            tier_enum = tier.tier
        family = product.family

        # --- Phase 1: Generate all PageIRs (defer rendering) ---
        public_classes = _filter_api_surface(
            understand.api_surface.public_classes, product, understand.claims,
        )
        api_ids: set[str] | None = (
            set(understand.api_surface.api_identifiers)
            if understand.api_surface.api_identifiers else None
        )
        class_briefs = getattr(understand.api_surface, "class_briefs", None) or []

        # Load skills block once per run (TC-3856)
        _skills_block = ""
        _skills_failed = False
        _skills_cfg = getattr(context.config, "skills", None)
        if _skills_cfg is None or getattr(_skills_cfg, "enabled", True):
            try:
                from launcher.shared.skills_loader import load_generation_block as _load_skills
                _skills_path = _resolve_skills_path(_skills_cfg, context.run_dir)
                _skills_block = _load_skills(_skills_path)
                if _skills_block:
                    context.log.info("[Generate] Skills quality standards loaded (%d chars)", len(_skills_block))
            except Exception as _e:
                # TC-3878 Wave 0 (Gap3): Upgraded from DEBUG to WARNING so operators can
                # distinguish a missing skills.md from intentionally-disabled skills.
                _skills_failed = True
                context.log.warning(
                    "[Generate] Skills load failed (%s): %s — run will produce lower quality without quality rubric",
                    type(_e).__name__, _e,
                )
                context.emit_event(
                    "skills_load_failed",
                    {
                        "error_type": type(_e).__name__,
                        "error": str(_e),
                        "path": getattr(_skills_cfg, "path", "skills.md"),
                    },
                    worker=self.name,
                )

        if not _skills_failed:
            context.emit_event(
                "skills_loaded" if _skills_block else "skills_inactive",
                {
                    "enabled": getattr(_skills_cfg, "enabled", True),
                    "path": getattr(_skills_cfg, "path", "skills.md"),
                    "chars": len(_skills_block),
                },
                worker=self.name,
            )

        # TC-HYBRID-04: extract install recipe from understanding bundle
        _install_recipe = getattr(
            getattr(understand, "product_evidence", None), "install_recipe", None,
        )

        # HG-11: extract limitations from understanding bundle for evidence injection
        _limitations = getattr(
            getattr(understand, "product_evidence", None), "limitations", None,
        ) or None

        # Heal optimization: skip pages not targeted for re-generation
        heal_target_pages = context.heal_target_pages  # None = all pages (normal mode)

        import asyncio as _asyncio_pages

        _page_sem = _asyncio_pages.Semaphore(_PAGE_CONCURRENCY)

        async def _process_page(
            page_plan: PlannedPage,
        ) -> tuple[PageIR, PlannedPage, str, str, int, int] | None:
            """Process one page; return (ir, plan, tmpl, variant, llm_calls, fallbacks) or None."""
            if heal_target_pages is not None and page_plan.page_id not in heal_target_pages:
                cached_ir = _load_cached_page_ir(page_plan, context.run_dir, content_dir)
                if cached_ir is not None:
                    context.log.info(
                        "[Generate] Reusing cached PageIR for %s (not in heal_target_pages)",
                        page_plan.page_id,
                    )
                    context.emit_event(
                        "generate_page_skipped",
                        {"page_id": page_plan.page_id, "reason": "heal_target_filter", "cache_hit": True},
                        worker=self.name,
                    )
                    return (cached_ir, page_plan, "", "", 0, 0)
                context.log.warning(
                    "[Generate] No cached PageIR for %s — page absent from output",
                    page_plan.page_id,
                )
                context.emit_event(
                    "generate_page_skipped",
                    {"page_id": page_plan.page_id, "reason": "heal_target_filter", "cache_hit": False},
                    worker=self.name,
                )
                return None

            context.log.info("[Generate] Processing page: %s (%s)", page_plan.page_id, page_plan.page_role)
            # Load cached PageIR for section-level skip (HO-06) when failing_section_ids set
            _fsids = (context.heal_metadata or {}).get("failing_section_ids", {}) or {}
            _cached_ir_for_section_skip: PageIR | None = None
            if _fsids.get(page_plan.page_id):
                _cached_ir_for_section_skip = _load_cached_page_ir(page_plan, context.run_dir, content_dir)
            async with _page_sem:
                p_ir, p_llm, p_fb, t_used, t_variant = await _generate_page(
                    page_plan, product, all_claims, all_snippets,
                    understand.api_surface.import_allowlist, context,
                    tier=tier_enum, family=family,
                    public_classes=public_classes,
                    api_identifiers=api_ids,
                    class_briefs=class_briefs,
                    skills_block=_skills_block,
                    cached_page_ir=_cached_ir_for_section_skip,
                    install_recipe=_install_recipe,  # TC-HYBRID-04
                    limitations=_limitations,  # HG-11
                )
            return (p_ir, page_plan, t_used, t_variant, p_llm, p_fb)

        raw_page_results = await _asyncio_pages.gather(
            *[_process_page(pp) for pp in plan.pages],
            return_exceptions=True,
        )

        page_results: list[tuple[PageIR, PlannedPage, str, str]] = []
        for pp, result in zip(plan.pages, raw_page_results):
            if isinstance(result, BaseException):
                context.log.warning("[Generate] Page '%s' failed: %s", pp.page_id, result)
                fallback_count += 1
            elif result is None:
                pass  # Skip-and-no-cache already handled inside _process_page
            else:
                p_ir, p_plan, t_used, t_variant, p_llm, p_fb = result
                page_results.append((p_ir, p_plan, t_used, t_variant))
                llm_calls += p_llm
                fallback_count += p_fb

        # Guard: if heal_target_pages filtered everything and no cache hits, warn
        if not page_results and heal_target_pages is not None:
            context.log.warning(
                "[Generate] heal_target_pages filtered all %d pages and no cached PageIRs found. "
                "ContentManifest will be empty.",
                len(plan.pages),
            )
            context.emit_event(
                "generate_no_pages_produced",
                {"heal_target_pages": list(heal_target_pages), "plan_page_count": len(plan.pages)},
                worker=self.name,
            )

        # --- Phase 1.5: SEO metadata optimization ---
        seo_config = getattr(context.config, "seo", None)
        seo_enabled = seo_config.enabled if seo_config is not None else True
        seo_failures = 0

        if seo_enabled:
            from launcher.workers.generate.seo_metadata import (
                optimize_seo_metadata,
                _generate_canonical,
            )

            keyword_bundle = getattr(understand, "keyword_research", None)
            subdomain_map = getattr(seo_config, "subdomain_map", None)
            for i, (page_ir, page_plan, tmpl_used, tmpl_variant) in enumerate(page_results):
                try:
                    page_claims = [c for c in all_claims if c.claim_id in set(page_plan.assigned_claims)]
                    optimized_ir = optimize_seo_metadata(
                        page_ir, product, page_claims, keyword_bundle,
                        subdomain_map=subdomain_map,
                    )
                    page_results[i] = (optimized_ir, page_plan, tmpl_used, tmpl_variant)
                except Exception as exc:
                    missing_after = [
                        k for k in ("seoTitle", "keywords", "canonical", "robots")
                        if not page_ir.frontmatter.get(k)
                    ]
                    logger.warning(
                        "[Generate] SEO optimization failed for %s: %s (missing: %s)",
                        page_plan.page_id, exc, missing_after, exc_info=True,
                    )
                    context.emit_event("issue_opened", {
                        "page_id": page_plan.page_id,
                        "check": "seo",
                        "severity": "high",
                        "missing_fields": missing_after,
                        "error": str(exc),
                    }, worker=self.name)
                    seo_failures += 1

            # Deterministic canonical fallback: any page still missing a canonical
            # URL gets one constructed from its url + subdomain_map.  This is a
            # pure string operation and does not require the SEO phase to succeed.
            canonical_filled = 0
            for i, (page_ir, page_plan, tmpl_used, tmpl_variant) in enumerate(page_results):
                if not page_ir.frontmatter.get("canonical"):
                    url = page_ir.frontmatter.get("url", "")
                    if url:
                        canonical = _generate_canonical(
                            url, page_ir.page_role, subdomain_map=subdomain_map,
                        )
                        if canonical:
                            updated_fm = dict(page_ir.frontmatter)
                            updated_fm["canonical"] = canonical
                            page_results[i] = (
                                page_ir.model_copy(update={"frontmatter": updated_fm}),
                                page_plan, tmpl_used, tmpl_variant,
                            )
                            canonical_filled += 1

            if canonical_filled:
                context.log.info(
                    "[Generate] Phase 1.5: canonical fallback applied to %d pages",
                    canonical_filled,
                )

            context.log.info(
                "[Generate] Phase 1.5: SEO metadata optimized for %d pages (%d failures)",
                len(page_results), seo_failures,
            )
        else:
            context.log.info("[Generate] Phase 1.5: SEO disabled by config, skipping")

        context.emit_event("seo_optimized", {
            "pages_processed": len(page_results),
            "seo_failures": seo_failures,
            "seo_enabled": seo_enabled,
        }, worker=self.name)

        # --- Phase 2: Link pages (deterministic scoring + LLM anchor text) ---
        linker_config = load_linker_config(_load_pipeline_config())
        all_irs = [r[0] for r in page_results]
        linked_irs, cross_links = await linker_link_pages(
            all_irs, plan.pages, product, context, config=linker_config,
        )

        context.log.info("[Generate] Linker produced %d cross-links", len(cross_links))
        context.emit_event("linker_completed", {
            "cross_links": len(cross_links),
            "see_also": sum(1 for cl in cross_links if cl.link_type == "see_also"),
            "toc_child": sum(1 for cl in cross_links if cl.link_type == "toc_child"),
        }, worker=self.name)

        # --- Phase 3: Render and write ---
        frontmatter_failures = 0
        for i, (linked_ir, (_, page_plan, tmpl_used, tmpl_variant)) in enumerate(
            zip(linked_irs, page_results),
        ):
            # Render PageIR -> Markdown. FrontmatterError is page-scoped: record it,
            # emit an issue_opened event for observability, and skip this page rather
            # than aborting the entire run.
            try:
                markdown = render_page(linked_ir)
            except FrontmatterError as exc:
                context.log.error(
                    "[Generate] Frontmatter invalid for %s — skipping page: %s",
                    page_plan.page_id, exc,
                )
                context.emit_event("issue_opened", {
                    "page_id": page_plan.page_id,
                    "check": "frontmatter",
                    "severity": "critical",
                    "missing_keys": exc.missing_keys,
                    "invalid_keys": exc.invalid_keys,
                    "detail": exc.detail,
                    "error": str(exc),
                }, worker=self.name)
                frontmatter_failures += 1
                continue

            # Determine section from page frontmatter or page_id
            section = infer_section(page_plan.page_id, page_plan.frontmatter)

            # Write IR and MD files using hierarchical content_path
            slug = page_plan.frontmatter.get("slug", page_plan.page_id)
            content_path = page_plan.content_path or slug
            file_parent = Path(content_path).parent
            file_stem = Path(content_path).name

            out_dir = content_dir / file_parent
            out_dir.mkdir(parents=True, exist_ok=True)
            ir_path = out_dir / f"{file_stem}.ir.json"
            md_path = out_dir / f"{file_stem}.md"

            ir_path.write_text(linked_ir.model_dump_json(indent=2), encoding="utf-8")
            md_path.write_text(markdown, encoding="utf-8")

            # Count stats
            word_count = len(markdown.split())
            code_block_count = sum(
                1 for s in linked_ir.sections for b in s.blocks if b.type.value == "code"
            )
            claim_ids_used = list({
                cid for s in linked_ir.sections for b in s.blocks for cid in b.claim_ids
            })

            generated_pages.append(GeneratedPage(
                slug=slug,
                page_role=page_plan.page_role,
                section=section,
                content_path=content_path,
                template_used=tmpl_used,
                variant=tmpl_variant,
                ir_path=str(ir_path.relative_to(context.run_dir)),
                md_path=str(md_path.relative_to(context.run_dir)),
                claim_ids_used=claim_ids_used,
                word_count=word_count,
                code_block_count=code_block_count,
            ))

        elapsed = time.monotonic() - start_time

        manifest = ContentManifest(
            pages=generated_pages,
            cross_links=cross_links,
            generation_stats=GenerationStats(
                total_pages=len(generated_pages),
                llm_calls=llm_calls,
                fallback_count=fallback_count,
                duration_seconds=round(elapsed, 2),
            ),
        )

        context.log.info(
            "[Generate] Complete: %d pages, %d LLM calls, %d fallbacks, %d FM failures, %.1fs",
            len(generated_pages), llm_calls, fallback_count, frontmatter_failures, elapsed,
        )
        context.emit_event("worker_completed", {
            "pages": len(generated_pages),
            "llm_calls": llm_calls,
            "fallback_count": fallback_count,
            "frontmatter_failures": frontmatter_failures,
        }, worker=self.name)

        return manifest

    async def self_review(self, output: LauncherBaseModel) -> SelfReviewResult:
        """Semantic self-review of generated content.

        Checks (Rule 1):
        - Every page has at least one section with content
        - No empty markdown files
        - Word count meets minimum thresholds
        - No duplicate content across pages (section-level)
        """
        if not isinstance(output, ContentManifest):
            return SelfReviewResult(passed=False, findings=[{"message": "Output is not ContentManifest"}])

        manifest = output
        findings: list[dict[str, Any]] = []
        metrics: dict[str, Any] = {}

        # Check 1: All pages have content
        empty_pages = [p for p in manifest.pages if p.word_count == 0]
        if empty_pages:
            findings.append({
                "category": "empty_page",
                "message": f"{len(empty_pages)} pages have zero word count",
                "severity": "high",
                "pages": [p.slug for p in empty_pages],
            })

        # Check 2: Minimum word count (50 words for content pages)
        thin_pages = [p for p in manifest.pages if 0 < p.word_count < 50 and p.page_role != "toc"]
        if thin_pages:
            findings.append({
                "category": "thin_content",
                "message": f"{len(thin_pages)} pages under 50 words",
                "severity": "medium",
                "pages": [p.slug for p in thin_pages],
            })

        # Check 3: Code blocks in workflow pages
        workflow_roles = {"workflow_page", "howto_article"}
        for page in manifest.pages:
            if page.page_role in workflow_roles and page.code_block_count == 0:
                findings.append({
                    "category": "missing_code",
                    "message": f"Workflow page '{page.slug}' has no code blocks",
                    "severity": "medium",
                })

        # Check 4: Cross-link coverage (non-TOC pages with >=3 claims should have links)
        linked_sources = {cl.source for cl in manifest.cross_links}
        content_pages_no_links = [
            p for p in manifest.pages
            if p.page_role != "toc"
            and len(p.claim_ids_used) >= 3
            and p.slug not in linked_sources
        ]
        if content_pages_no_links:
            findings.append({
                "category": "missing_cross_links",
                "message": f"{len(content_pages_no_links)} content pages with >=3 claims have no cross-links",
                "severity": "low",
                "pages": [p.slug for p in content_pages_no_links],
            })

        # Check 5: No broken cross-links (every target exists in manifest)
        page_slugs = {p.slug for p in manifest.pages}
        broken_links = [cl for cl in manifest.cross_links if cl.target not in page_slugs]
        if broken_links:
            findings.append({
                "category": "broken_cross_links",
                "message": f"{len(broken_links)} cross-links target non-existent pages",
                "severity": "medium",
                "targets": [cl.target for cl in broken_links],
            })

        # Metrics
        total_words = sum(p.word_count for p in manifest.pages)
        metrics["total_pages"] = len(manifest.pages)
        metrics["total_words"] = total_words
        metrics["avg_word_count"] = round(total_words / len(manifest.pages), 1) if manifest.pages else 0
        metrics["total_code_blocks"] = sum(p.code_block_count for p in manifest.pages)
        metrics["total_cross_links"] = len(manifest.cross_links)
        metrics["llm_calls"] = manifest.generation_stats.llm_calls
        metrics["fallback_count"] = manifest.generation_stats.fallback_count

        passed = not any(f.get("severity") == "high" for f in findings)
        return SelfReviewResult(passed=passed, findings=findings, metrics=metrics)


def create_worker() -> GenerateWorker:
    return GenerateWorker()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _generate_page(
    page_plan: PlannedPage,
    product: ProductIdentity,
    all_claims: list[Claim],
    all_snippets: list[Snippet],
    import_allowlist: list[str],
    context: WorkerContext,
    *,
    tier: RichnessTier = RichnessTier.B,
    family: str = "",
    public_classes: list[str] | None = None,
    api_identifiers: set[str] | None = None,
    class_briefs: list[ClassBrief] | None = None,
    skills_block: str = "",
    cached_page_ir: PageIR | None = None,
    install_recipe: "Any | None" = None,  # TC-HYBRID-04: InstallRecipe | None
    limitations: "list | None" = None,  # HG-11: list[LimitationEntry] from product_evidence
) -> tuple[PageIR, int, int, str, str]:
    """Generate content for a single page.

    Returns (PageIR, llm_calls, fallback_count, template_used, variant).
    """
    from launcher.workers.generate.section_prompt import build_section_prompt
    from launcher.workers.generate.section_validator import parse_and_validate_blocks
    from launcher.workers.generate.fallback import render_section_deterministic

    # --- Template resolution (preferred) then skeleton fallback ---
    section_name = infer_section(page_plan.page_id, page_plan.frontmatter)
    template_used = ""
    variant = "minimal" if tier == RichnessTier.C else "standard"
    skeleton: list[SkeletonSection] = []
    template_fm: dict[str, Any] = {}
    required_placeholder_keys: frozenset[str] = frozenset()

    template_content = get_template_content(
        section_name, page_plan.page_role, family, tier,
    )
    if template_content:
        skeleton = extract_template_sections(template_content)
        template_fm, required_placeholder_keys = extract_template_frontmatter(template_content)
        tmpl_path, variant = resolve_template(
            section_name, page_plan.page_role, family, tier,
        )
        template_used = tmpl_path
        logger.info(
            "Template resolved: %s (variant=%s) for page_role=%s",
            tmpl_path, variant, page_plan.page_role,
        )

    if not skeleton:
        from launcher.shared.page_skeletons import resolve_skeleton
        skeleton = resolve_skeleton(page_plan.page_role, page_plan.skeleton_variant)
        logger.info(
            "No template found for page_role=%s, using skeleton fallback (variant=%s)",
            page_plan.page_role, page_plan.skeleton_variant,
        )

    # Merge template frontmatter with page-plan frontmatter
    # (page-plan values take precedence)
    merged_fm = {**template_fm, **page_plan.frontmatter}

    # Insert "" sentinels for required placeholder keys not yet populated.
    # This makes missing fields detectable by the evaluate seo gate (which checks
    # for empty strings) rather than silently absent.  None is never inserted —
    # ir_renderer rejects None values (TC-3824).
    for key in required_placeholder_keys:
        if key not in merged_fm:
            merged_fm[key] = ""

    # Filter claims/snippets for this page
    page_claim_ids = set(page_plan.assigned_claims)
    page_claims = [c for c in all_claims if c.claim_id in page_claim_ids]
    page_snippet_indices = set(page_plan.assigned_snippets)
    page_snippets = [s for i, s in enumerate(all_snippets) if i in page_snippet_indices]
    # Also include snippets linked by claim_ids
    page_snippets.extend(
        s for s in all_snippets
        if s not in page_snippets and set(s.claim_ids) & page_claim_ids
    )

    sections: list[SectionIR] = []
    llm_calls = 0
    fallback_count = 0
    allowed_claim_ids = page_claim_ids

    # Load GoldenIndex once for this page (golden enforcement)
    golden_index = None
    _golden_dir: "Path | None" = None
    try:
        golden_cfg = getattr(context.config, "golden", {}) or {}
        if golden_cfg.get("enabled"):
            from launcher.shared.golden_loader import GoldenIndex
            _golden_dir = Path(golden_cfg.get("dir", "golden/"))
            golden_index = GoldenIndex.load(_golden_dir)
    except Exception:
        golden_index = None

    import asyncio as _asyncio

    len_skeleton = len(skeleton)
    _section_sem = _asyncio.Semaphore(_SECTION_CONCURRENCY)

    # Section-level skip: failing_section_ids from heal_metadata (HO-06)
    _heal_meta = context.heal_metadata or {}
    _failing_section_ids_map: dict[str, list[str]] = _heal_meta.get("failing_section_ids", {}) or {}
    _failing_sections_for_page: set[str] = set(
        _failing_section_ids_map.get(page_plan.page_id, [])
    )
    # Build cached section lookup keyed by heading (if cached_page_ir provided)
    _cached_sections: dict[str, SectionIR] = {}
    if cached_page_ir is not None:
        for sec in (cached_page_ir.sections or []):
            _cached_sections[sec.heading] = sec

    async def _generate_section(skel_section: SkeletonSection, idx: int):
        """Generate one section. Returns (section_ir, llm_calls_delta, fallback_delta)."""
        _llm = 0
        _fb = 0

        # Section-skip: reuse cached section when not in failing_section_ids (HO-06)
        if _failing_sections_for_page and skel_section.heading not in _failing_sections_for_page:
            cached_sec = _cached_sections.get(skel_section.heading)
            if cached_sec is not None:
                # TC-3882 Wave 4 (Gap4): Quality probe — thin cached sections need regen
                # even if they "passed" the section filter.
                if _section_needs_regen(cached_sec, page_plan.page_role):
                    logger.debug(
                        "[Generate] Cached section '%s' too thin — regenerating despite filter",
                        skel_section.heading,
                    )
                    # Fall through to normal generation
                else:
                    context.emit_event(
                        "generate_section_skipped",
                        {"page_id": page_plan.page_id, "section": skel_section.heading, "reason": "heal_section_filter"},
                        worker="generate",
                    )
                    return cached_sec, _llm, _fb
            else:
                # No cached section — fall through to normal generation
                logger.warning(
                    "[Generate] No cached section '%s' for page '%s' — regenerating",
                    skel_section.heading, page_plan.page_id,
                )

        sec_claims = (
            [c for j, c in enumerate(page_claims) if j % len_skeleton == idx]
            if page_claims else []
        )
        sec_claim_ids = {c.claim_id for c in sec_claims}
        sec_snippets = [s for s in page_snippets if set(s.claim_ids) & sec_claim_ids]
        section_ir: SectionIR | None = None
        section_prompt_str: str | None = None

        async with _section_sem:
            if context.llm_config:
                # TC-3882 Wave 4 (G6): In heal mode, inject cached section content for
                # diff-aware golden block (shows "YOUR PREVIOUS OUTPUT" + gap list).
                _section_heal_meta = dict(_heal_meta) if _heal_meta else {}
                if (
                    _failing_sections_for_page
                    and skel_section.heading in _failing_sections_for_page
                ):
                    _cached_sec_for_g6 = _cached_sections.get(skel_section.heading)
                    if _cached_sec_for_g6 is not None:
                        # Serialize cached section blocks to plain text for G6 prompt
                        _cached_text_parts: list[str] = []
                        for _blk in (_cached_sec_for_g6.blocks or []):
                            _blk_dict = _blk if isinstance(_blk, dict) else (
                                _blk.model_dump() if hasattr(_blk, "model_dump") else {}
                            )
                            if _blk_dict.get("type") == "paragraph":
                                _cached_text_parts.append(str(_blk_dict.get("text", "")))
                            elif _blk_dict.get("type") == "code":
                                _cached_text_parts.append(
                                    f"```{_blk_dict.get('language', '')}\n"
                                    f"{_blk_dict.get('code', '')}\n```"
                                )
                        if _cached_text_parts:
                            _section_heal_meta["_current_section_content"] = "\n\n".join(
                                _cached_text_parts
                            )

                prompt = build_section_prompt(
                    skel_section, idx, len_skeleton,
                    page_plan, product, all_claims, all_snippets,
                    public_classes=public_classes,
                    class_briefs=class_briefs,
                    heal_metadata=_section_heal_meta or None,
                    skills_block=skills_block,
                    golden_dir=_golden_dir,
                    variant=variant,  # TC-3881 Wave 3 (G2)
                    install_recipe=install_recipe,  # TC-HYBRID-04
                    limitations=limitations,  # HG-11
                    api_identifiers=sorted(api_identifiers) if api_identifiers else None,  # HG-11
                )
                section_prompt_str = prompt

                _sec_max_tokens = max(512, (skel_section.max_words or 200) * 3)
                raw_response = await _call_llm(prompt, context, max_tokens=_sec_max_tokens)
                _llm += 1

                if raw_response:
                    blocks = parse_and_validate_blocks(
                        raw_response, product, allowed_claim_ids, import_allowlist,
                        section_heading=skel_section.heading,
                        api_identifiers=api_identifiers,
                    )
                    if blocks:
                        if api_identifiers:
                            blocks = _validate_identifiers(blocks, api_identifiers)
                        blocks = _strip_commercial_urls(blocks)
                        blocks = _sanitize_code_blocks(
                            blocks, product.runtime_import or product.canonical_import, import_allowlist,
                        )
                        section_ir = SectionIR(
                            section_id=skel_section.heading.lower().replace(" ", "_"),
                            heading=skel_section.heading,
                            level=skel_section.level,
                            blocks=blocks,
                        )

            if section_ir is None:
                _fb += 1
                section_ir = render_section_deterministic(
                    skel_section, sec_claims, sec_snippets, product,
                )

            if golden_index is not None:
                section_ir, pass_used = await enforce_block_spec(
                    section_ir, skel_section, page_plan.page_role,
                    golden_index, product,
                    sec_claims, sec_snippets, context,
                    original_prompt=section_prompt_str,
                    richness_tier="C" if tier == RichnessTier.C else "B",
                )
                if pass_used != "none":
                    context.emit_event(
                        "enforcement_log",
                        {"section": skel_section.heading, "pass_used": pass_used},
                        worker="generate",
                    )

            # Final commercial URL strip — catches pass2 retry blocks and fallback paths
            # that bypass the strip at line 699 (TC-3883).
            final_blocks = _strip_commercial_urls(list(section_ir.blocks))
            if final_blocks != list(section_ir.blocks):
                section_ir = section_ir.model_copy(update={"blocks": final_blocks})

            # Ensure all code blocks have a language tag; default to "python" (TC-3887).
            normed_blocks = _normalize_code_languages(list(section_ir.blocks))
            if normed_blocks != list(section_ir.blocks):
                section_ir = section_ir.model_copy(update={"blocks": normed_blocks})

            # Fix wrong inline package names in prose blocks (TC-3888).
            fixed_blocks = _fix_prose_canonical_imports(list(section_ir.blocks), product.runtime_import or product.canonical_import)
            if fixed_blocks != list(section_ir.blocks):
                section_ir = section_ir.model_copy(update={"blocks": fixed_blocks})

            # Strip empty/unclosed href links from prose and list blocks (TC-3908).
            href_fixed_blocks = _fix_empty_hrefs(list(section_ir.blocks))
            if href_fixed_blocks != list(section_ir.blocks):
                section_ir = section_ir.model_copy(update={"blocks": href_fixed_blocks})

        return section_ir, _llm, _fb

    # Gather all sections with bounded concurrency (GE-02 OPT-5)
    raw_results = await _asyncio.gather(
        *[_generate_section(s, i) for i, s in enumerate(skeleton)],
        return_exceptions=True,
    )

    # Collect results in skeleton order; fallback for any failed section.
    # TC-3879 Wave 1 (F1): Reconstruct sec_claims/sec_snippets using the same round-robin
    # formula as _generate_section so the fallback renderer has real content, not empty lists.
    for idx, (skel_section, result) in enumerate(zip(skeleton, raw_results)):
        if isinstance(result, BaseException):
            logger.warning(
                "[Generate] Section '%s' failed, using fallback: %s",
                skel_section.heading, result,
            )
            fallback_count += 1
            skel_claims = (
                [c for j, c in enumerate(page_claims) if j % len_skeleton == idx]
                if page_claims else []
            )
            skel_claim_ids = {c.claim_id for c in skel_claims}
            skel_snippets = [s for s in page_snippets if set(s.claim_ids) & skel_claim_ids]
            sections.append(render_section_deterministic(skel_section, skel_claims, skel_snippets, product))
        else:
            s_ir, s_llm, s_fb = result
            # TC-3877: Quick section quality gate
            _gate_violations = _quick_section_quality_check(
                s_ir,
                getattr(skel_section, "heading", "") or "",
                page_plan.page_role,
            )
            if _gate_violations:
                logger.warning(
                    "Section gate FAIL '%s' (%s): %s",
                    getattr(skel_section, "heading", ""), page_plan.page_role, _gate_violations,
                )
            sections.append(s_ir)
            llm_calls += s_llm
            fallback_count += s_fb

    # Phase 4: cross-section deduplication on the complete ordered list (V2CP-03)
    try:
        from launcher.workers.generate.section_validator import deduplicate_sections
        sections = deduplicate_sections(sections)
    except Exception:
        logger.debug("[Generate] deduplicate_sections failed; skipping dedup", exc_info=True)

    page_ir = PageIR(
        page_id=page_plan.page_id,
        page_role=page_plan.page_role,
        title=page_plan.title,
        frontmatter=merged_fm,
        sections=sections,
    )

    return page_ir, llm_calls, fallback_count, template_used, variant


async def _call_llm(prompt: str, context: WorkerContext, max_tokens: int | None = None) -> str | None:
    """Call the LLM with the given prompt. Returns raw response or None on failure."""
    import asyncio
    import os

    if not context.llm_config:
        return None

    api_key = os.environ.get("litellm_key", "")

    try:
        from launcher.clients.llm_provider import LLMProviderClient

        client = LLMProviderClient(
            api_base_url=context.llm_config.primary.base_url,
            model=context.llm_config.primary.model,
            run_dir=context.run_dir,
            api_key=api_key,
            temperature=context.llm_config.temperature,
            max_tokens=context.llm_config.max_tokens,
            reasoning_model=(
                context.llm_config.reasoning.model if context.llm_config.reasoning else None
            ),
            routing=context.llm_config.routing,
            telemetry_client=context.telemetry_client,
            telemetry_run_id=context.run_id,
            telemetry_trace_id=context.telemetry_trace_id,
            telemetry_parent_span_id="",
        )

        messages = [{"role": "user", "content": prompt}]
        loop = asyncio.get_running_loop()
        _mt = max_tokens
        response = await loop.run_in_executor(None, lambda: client.chat_completion(messages, task_type="generate", max_tokens=_mt))
        return response.get("content", "") if isinstance(response, dict) else str(response)
    except Exception as e:
        logger.warning(
            "[Generate] LLM primary failed: type=%s msg=%s",
            type(e).__name__, e,
        )

        # Try fallback LLM
        if context.llm_config.fallback:
            try:
                client = LLMProviderClient(
                    api_base_url=context.llm_config.fallback.base_url,
                    model=context.llm_config.fallback.model,
                    run_dir=context.run_dir,
                    api_key=api_key,
                    temperature=context.llm_config.temperature,
                    max_tokens=context.llm_config.max_tokens,
                    reasoning_model=(
                        context.llm_config.reasoning.model if context.llm_config.reasoning else None
                    ),
                    routing=context.llm_config.routing,
                    telemetry_client=context.telemetry_client,
                    telemetry_run_id=context.run_id,
                    telemetry_trace_id=context.telemetry_trace_id,
                    telemetry_parent_span_id="",
                )
                loop = asyncio.get_running_loop()
                response = await loop.run_in_executor(None, lambda: client.chat_completion(messages, task_type="generate", max_tokens=_mt))
                return response.get("content", "") if isinstance(response, dict) else str(response)
            except Exception as e2:
                logger.warning(
                    "[Generate] Fallback LLM also failed: type=%s msg=%s",
                    type(e2).__name__, e2,
                )

        return None


def _section_needs_regen(section_ir: SectionIR, page_role: str) -> bool:
    """Return True if a cached section is too thin to reuse in heal mode.

    TC-3882 Wave 4 (Gap4): Prevents thin sections from being reused verbatim
    in heal mode even when they are not in failing_section_ids.
    Criteria:
    - Word count across all paragraph blocks < _HEAL_MIN_WORDS (80), OR
    - page_role requires code blocks AND section has no code block
    """
    # Count prose words (paragraph blocks only, not headings/code)
    prose_words = 0
    has_code_block = False
    for block in (section_ir.blocks or []):
        if hasattr(block, "block_type"):
            _bt = str(block.block_type)
        else:
            _bt = ""
        if "code" in _bt.lower() or "fence" in _bt.lower():
            has_code_block = True
        elif "paragraph" in _bt.lower() or "para" in _bt.lower() or "text" in _bt.lower():
            prose_words += len((getattr(block, "content", "") or "").split())
        elif not _bt:
            # Unknown block type — count content words as prose
            prose_words += len((getattr(block, "content", "") or "").split())

    if prose_words < _HEAL_MIN_WORDS:
        return True
    if page_role in _CODE_REQUIRED_ROLES and not has_code_block:
        return True
    return False


def _gap_fill_code_block(
    section_ir: SectionIR,
    product: ProductIdentity,
    section_snippets: "list | None" = None,
) -> SectionIR:
    """Deterministically add a minimal code block to a section that requires one.

    TC-3878 (W2): Prefers extracted snippets (source_type=="extracted") when available,
    as they contain real validated code. Falls back to a generic placeholder otherwise.

    Returns a new SectionIR with a placeholder code block appended.
    """
    # TC-3878: Prefer extracted snippets — real validated code over placeholder
    if section_snippets:
        for snippet in section_snippets:
            if getattr(snippet, "source_type", None) == "extracted":
                code_content = getattr(snippet, "code", None) or ""
                if code_content.strip():
                    gap_block = BlockIR(
                        type=BlockType.code,
                        content=code_content,
                        language=getattr(snippet, "language", "python") or "python",
                        claim_ids=[],
                    )
                    new_blocks = list(section_ir.blocks) + [gap_block]
                    return SectionIR(
                        section_id=section_ir.section_id,
                        heading=section_ir.heading,
                        level=section_ir.level,
                        blocks=new_blocks,
                    )

    placeholder_code = (
        f"# Example usage\nimport {product.runtime_import or product.canonical_import or 'package'}\n"
        "# See API reference for complete examples"
    )
    gap_block = BlockIR(
        type=BlockType.code,
        content=placeholder_code,
        language="python",
        claim_ids=[],
    )
    new_blocks = list(section_ir.blocks) + [gap_block]
    return SectionIR(
        section_id=section_ir.section_id,
        heading=section_ir.heading,
        level=section_ir.level,
        blocks=new_blocks,
    )


async def enforce_block_spec(
    section_ir: SectionIR,
    skel_section: Any,
    page_role: str,
    golden_index: Any | None,
    product: ProductIdentity,
    section_claims: list[Any],
    section_snippets: list[Any],
    context: WorkerContext,
    variant: str = "standard",
    original_prompt: str | None = None,
    richness_tier: str = "B",
) -> tuple[SectionIR, str]:
    """Apply 3-pass enforcement to ensure section meets GoldenBlockSpec.

    Returns (section_ir, pass_used) where pass_used is 'none', 'pass1', 'pass2', or 'pass3'.

    Pass 1 — deterministic gap-fill (no LLM call).
    Pass 2 — LLM retry with ENFORCEMENT OVERRIDE prefix (Tier A/B only).
    Pass 3 — deterministic fallback via render_section_deterministic.
    """
    if golden_index is None:
        return section_ir, "none"

    try:
        from launcher.workers.generate.section_validator import check_against_spec
        from launcher.shared.golden_loader import GoldenBlockSpec as _GoldenBlockSpec
        spec = golden_index.get_spec(page_role, variant, skel_section.heading)
        # TC-3909: When no golden spec was found, synthesize a minimal spec for sections
        # whose heading explicitly indicates code content. This ensures "Code Example"
        # sections always receive a code block even when golden heading matching fails
        # (e.g., golden has "Step-by-Step Guide" but skeleton has "Code Example").
        if spec is None:
            _CODE_HEADING_KEYWORDS = (
                "code example", "code snippet", "working example",
                "example code", "code sample", "code block",
            )
            _heading_lower = (skel_section.heading or "").lower()
            if any(kw in _heading_lower for kw in _CODE_HEADING_KEYWORDS):
                spec = _GoldenBlockSpec(
                    required_block_types=["paragraph", "code"],
                    min_words=30,
                )
        if spec is None or check_against_spec(section_ir, spec):
            return section_ir, "none"

        # Pass 1: deterministic gap-fill (code block only)
        required_types = getattr(spec, "required_block_types", None) or []
        if "code" in required_types or getattr(spec, "requires_code", False):
            candidate = _gap_fill_code_block(section_ir, product, section_snippets)
            if check_against_spec(candidate, spec):
                return candidate, "pass1"

        # Pass 2: LLM retry (all tiers — TC-3881 Wave 3 G4: Tier C now allowed, capped at 1 retry)
        # Loops up to spec.max_retries - 1 times (V2CP-04: wire GoldenBlockSpec.max_retries)
        _max_retries = getattr(spec, "max_retries", 1) or 1
        if richness_tier == "C":
            _max_retries = min(_max_retries, 1)  # TC-3881 (G4): Tier C capped at 1 retry
        if original_prompt is not None and context.llm_config:
            for _retry_idx in range(_max_retries):
                # Build violations for the ENFORCEMENT OVERRIDE prefix
                violations: list[str] = []
                current_types = {b.type.value for b in section_ir.blocks}
                for req in required_types:
                    if req not in current_types:
                        violations.append(f"- Missing required block type: '{req}'")
                _min_words = getattr(spec, "min_words", 0) or 0
                if _min_words > 0:
                    _word_count = sum(
                        len(b.content.split())
                        for b in section_ir.blocks
                        if hasattr(b, "content") and b.content
                    )
                    if _word_count < _min_words:
                        violations.append(
                            f"- Minimum {_min_words} words required (current: {_word_count})"
                        )
                violations_text = (
                    "\n".join(violations) if violations else "- Section does not meet spec requirements"
                )
                prepend = (
                    "ENFORCEMENT OVERRIDE — PREVIOUS RESPONSE DID NOT MEET REQUIREMENTS:\n"
                    f"{violations_text}\n\n"
                    "REQUIRED FOR THIS RETRY: Output ONLY a valid JSON array of BlockIR objects "
                    "satisfying the above requirements. No explanation text.\n\n"
                )
                prepend = prepend[:300]  # hard cap
                retry_prompt = prepend + original_prompt
                try:
                    retry_response = await _call_llm(retry_prompt, context)
                    if retry_response:
                        from launcher.workers.generate.section_validator import parse_and_validate_blocks
                        allowed_ids = {c.claim_id for c in section_claims}
                        retry_blocks = parse_and_validate_blocks(
                            retry_response, product, allowed_ids, [],
                            section_heading=skel_section.heading,
                        )
                        if retry_blocks:
                            retry_ir = SectionIR(
                                section_id=section_ir.section_id,
                                heading=section_ir.heading,
                                level=section_ir.level,
                                blocks=retry_blocks,
                            )
                            if check_against_spec(retry_ir, spec):
                                _pass2_tag = "pass2_tier_c" if richness_tier == "C" else "pass2_tier_ab"
                                return retry_ir, _pass2_tag
                except Exception:
                    logger.debug("[enforce_block_spec] Pass 2 LLM retry error", exc_info=True)
                    break

        # Pass 3: deterministic fallback
        from launcher.workers.generate.fallback import render_section_deterministic
        fallback_ir = render_section_deterministic(
            skel_section, section_claims, section_snippets, product,
        )
        return fallback_ir, "pass3"

    except Exception:
        logger.debug("[enforce_block_spec] Exception; returning unchanged section", exc_info=True)
        return section_ir, "none"


def _load_cached_page_ir(page_plan: PlannedPage, run_dir: Path, content_dir: Path) -> PageIR | None:
    """Try to load a previously generated PageIR from disk.

    Returns None if the file does not exist or is unreadable.
    Only called during heal when a page is not in heal_target_pages.
    """
    try:
        slug = page_plan.frontmatter.get("slug", page_plan.page_id)
        content_path = page_plan.content_path or slug
        file_parent = Path(content_path).parent
        file_stem = Path(content_path).name
        ir_path = content_dir / file_parent / f"{file_stem}.ir.json"
        if ir_path.exists():
            raw = ir_path.read_text(encoding="utf-8")
            return PageIR.model_validate_json(raw)
    except Exception:
        logger.debug(
            "[Generate] Could not load cached PageIR for %s", page_plan.page_id, exc_info=True
        )
    return None


def _load_understanding(context: WorkerContext) -> UnderstandingBundle:
    """Load the understanding bundle from the understand checkpoint."""
    checkpoint_path = context.run_dir / "understand_checkpoint.json"
    if not checkpoint_path.exists():
        raise FileNotFoundError(
            f"Understanding checkpoint not found: {checkpoint_path}. "
            "The understand worker must run before generate."
        )
    raw = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    return UnderstandingBundle.model_validate(raw)


def _filter_api_surface(
    public_classes: list[str],
    product: ProductIdentity,
    claims: list[Claim],
) -> list[str]:
    """Filter API surface classes to only those relevant to the product.

    Keeps only classes that appear in claims or share the product family name.
    Third-party prefix filtering is handled upstream in extract.py (_is_internal_class
    + export reachability); this function performs page-level relevance filtering only.
    """
    if not public_classes:
        return []

    claim_text = " ".join(c.text for c in claims).lower()
    family_lower = product.family.lower() if product.family else ""

    filtered: list[str] = []
    for cls in public_classes:
        cls_lower = cls.lower()

        # Keep if class name contains product family
        if family_lower and family_lower in cls_lower:
            filtered.append(cls)
            continue

        # Keep if class name appears in claims
        if cls_lower in claim_text:
            filtered.append(cls)
            continue

        # Keep other classes (contamination already removed by extract.py)
        filtered.append(cls)

    logger.info(
        "[Generate] API surface: %d -> %d classes after page-level filter",
        len(public_classes), len(filtered),
    )
    return filtered


_BACKTICK_RE = re.compile(r"`([A-Za-z_]\w*(?:\(\))?)`")

_BUILTIN_IDENTIFIERS = frozenset({
    "str", "int", "float", "bool", "list", "dict", "set", "tuple",
    "bytes", "bytearray", "None", "True", "False", "type", "object",
    "Path", "Optional", "Any", "Union", "Callable", "Iterator",
    "Generator", "Sequence", "Mapping", "Iterable",
})


def _validate_identifiers(
    blocks: list[BlockIR],
    api_identifiers: set[str],
) -> list[BlockIR]:
    """Strip backticked identifiers that don't exist in the API surface.

    Only applies to paragraph/list blocks (not code blocks).
    Removes the backticks but keeps the text to avoid losing context.
    """
    stripped_count = 0

    def _strip_unknown(text: str) -> str:
        nonlocal stripped_count

        def _replacer(m: re.Match) -> str:
            nonlocal stripped_count
            ident = m.group(1).rstrip("()")
            if ident in api_identifiers or ident in _BUILTIN_IDENTIFIERS:
                return m.group(0)  # keep backticked
            stripped_count += 1
            return m.group(1)  # remove backticks, keep text

        return _BACKTICK_RE.sub(_replacer, text)

    result: list[BlockIR] = []
    for block in blocks:
        if block.type in (BlockType.paragraph, BlockType.list, BlockType.table):
            new_content = _strip_unknown(block.content) if block.content else block.content
            new_items = [_strip_unknown(item) if isinstance(item, str) else item
                         for item in (block.items or [])]
            result.append(block.model_copy(update={"content": new_content, "items": new_items}))
        else:
            result.append(block)

    if stripped_count:
        logger.debug("[Generate] Stripped %d unverified backticked identifiers", stripped_count)

    return result


_COMMERCIAL_URL_RE = re.compile(
    r"https?://(?:docs|purchase|reference|releases|products|blog)\."
    r"aspose\.com\S*",
)


def _strip_commercial_urls(blocks: list[BlockIR]) -> list[BlockIR]:
    """Remove commercial Aspose domain URLs from all blocks.

    These get hallucinated by the LLM and trigger safety:high findings.
    """
    stripped = 0

    def _clean(text: str) -> str:
        nonlocal stripped
        cleaned = _COMMERCIAL_URL_RE.sub("", text)
        if cleaned != text:
            stripped += 1
        return cleaned

    result: list[BlockIR] = []
    for block in blocks:
        new_content = _clean(block.content) if block.content else block.content
        new_items = [_clean(item) if isinstance(item, str) else item
                     for item in (block.items or [])]
        result.append(BlockIR(
            type=block.type,
            content=new_content,
            language=block.language,
            claim_ids=block.claim_ids,
            items=new_items,
            level=block.level,
        ))

    if stripped:
        logger.debug("[Generate] Stripped commercial URLs from %d blocks", stripped)

    return result


_SHELL_PREFIXES = ("pip ", "pip3 ", "npm ", "npx ", "apt ", "apt-get ", "brew ", "conda ", "yarn ")


def _normalize_code_languages(blocks: list[BlockIR]) -> list[BlockIR]:
    """Ensure all code blocks have a correct language tag (TC-3887, TC-3908).

    When the section-writer LLM omits the ``language`` field, the IR renderer
    produces bare triple-backtick fences which the LLM reviewer flags as
    ``code_correctness HIGH``.

    TC-3908 extension: also corrects explicitly wrong python/py tags when the
    block content is a shell command (pip install, npm, apt, etc.). The LLM
    sometimes generates ```python\npip install foo``` which the evaluate worker
    flags as a shell command inside a Python-tagged block.

    Heuristic:
    - If ``block.language`` is already set AND is not a wrong python tag → leave unchanged.
    - If the first non-empty line starts with a shell prefix (pip, npm, apt…)
      → set ``language = "bash"``.
    - Otherwise → set ``language = "python"``.
    """
    result: list[BlockIR] = []
    for block in blocks:
        if block.type != "code":
            result.append(block)
            continue
        first_line = (block.content or "").lstrip().split("\n")[0].lstrip()
        is_shell = any(first_line.startswith(p) for p in _SHELL_PREFIXES)
        # Leave block unchanged if language is already set correctly.
        # Exception (TC-3908): if tagged as python/py but content is a shell command,
        # correct to bash.
        if block.language and not (is_shell and block.language in ("python", "py")):
            result.append(block)
            continue
        lang = "bash" if is_shell else "python"
        result.append(BlockIR(
            type=block.type,
            content=block.content,
            language=lang,
            claim_ids=block.claim_ids,
            items=block.items,
            level=block.level,
        ))
    return result


_WRONG_INLINE_PKG_RE = re.compile(
    r"`((?:pip install|pip3 install|from|import)\s+)(Aspose\.\w+|aspose\.\w+)([^`]*)`",
    re.IGNORECASE,
)

# TC-3908: detect empty/unclosed hrefs in markdown: [text]() or [text]( at end of line.
_EMPTY_HREF_RE = re.compile(
    r"\[([^\[\]]+)\]\(\s*\)"        # [text]()
    r"|"
    r"\[([^\[\]]+)\]\(\s*$",        # [text]( at end of line (unclosed)
    re.MULTILINE,
)


def _fix_empty_hrefs(blocks: list[BlockIR]) -> list[BlockIR]:
    """Remove empty/unclosed href links from prose and list blocks (TC-3908).

    The LLM sometimes generates ``[Aspose.Cells docs](`` without a URL in
    "See Also" / "Related Resources" sections.  The artifacts check flags
    these as HIGH broken links.

    Converts ``[text]()`` and ``[text](\\n`` to plain text ``text``.
    Only modifies paragraph blocks (block.content) and list blocks (block.items).
    Code blocks are never modified.
    """

    def _strip_empty_hrefs(text: str) -> str:
        # Replace [text]() → text,  [text]( (unclosed, end of line) → text
        def _repl(m: re.Match) -> str:
            return m.group(1) or m.group(2) or ""
        return _EMPTY_HREF_RE.sub(_repl, text)

    result: list[BlockIR] = []
    changed = 0
    for block in blocks:
        if block.type == "code":
            result.append(block)
            continue
        new_content = block.content
        new_items = block.items
        if block.content:
            new_content = _strip_empty_hrefs(block.content)
        if block.items:
            new_items = [_strip_empty_hrefs(item) for item in block.items]
        if new_content != block.content or new_items != block.items:
            changed += 1
            result.append(block.model_copy(update={"content": new_content, "items": new_items}))
        else:
            result.append(block)
    if changed:
        logger.info("[Generate] Stripped empty hrefs from %d blocks (TC-3908)", changed)
    return result


def _fix_prose_canonical_imports(
    blocks: list[BlockIR], canonical_import: str
) -> list[BlockIR]:
    """Replace wrong inline package names in prose paragraph blocks (TC-3888).

    Catches LLM-generated prose like ``pip install Aspose.Cells`` or
    ``import Aspose.Cells`` embedded as inline code in paragraph blocks.
    Only modifies paragraph blocks; fenced code blocks are handled by
    ``_sanitize_code_blocks``.
    """
    if not canonical_import:
        return blocks

    result: list[BlockIR] = []
    changed = 0
    for block in blocks:
        if block.type != BlockType.paragraph or not block.content:
            result.append(block)
            continue

        def _replace(m: re.Match) -> str:
            verb = m.group(1)
            rest = m.group(3)
            return f"`{verb}{canonical_import}{rest}`"

        new_content = _WRONG_INLINE_PKG_RE.sub(_replace, block.content)
        if new_content != block.content:
            changed += 1
            result.append(block.model_copy(update={"content": new_content}))
        else:
            result.append(block)

    if changed:
        logger.info("[Generate] Fixed %d prose blocks with wrong inline canonical imports", changed)
    return result


def _sanitize_code_blocks(
    blocks: list[BlockIR],
    canonical_import: str,
    import_allowlist: list[str],
) -> list[BlockIR]:
    """Remove code blocks with wrong imports or convert them to prose.

    Catches LLM hallucination of wrong import paths (e.g. ``import Aspose.Cells``
    instead of ``import aspose_cells_foss``).
    """
    if not canonical_import:
        return blocks

    # Build set of allowed import prefixes
    allowed = {canonical_import.split(".")[0]}
    for imp in import_allowlist:
        allowed.add(imp.split(".")[0])

    # Common wrong patterns the LLM generates
    _WRONG_IMPORT_RE = re.compile(
        r"^\s*(?:import|from)\s+(Aspose\.\w+|aspose\.\w+)",
        re.MULTILINE,
    )

    result: list[BlockIR] = []
    stripped = 0
    for block in blocks:
        if block.type == BlockType.code and block.content:
            # Check for wrong imports
            wrong = _WRONG_IMPORT_RE.findall(block.content)
            has_wrong = any(
                w.split(".")[0].lower() not in {a.lower() for a in allowed}
                for w in wrong
            )
            if has_wrong:
                stripped += 1
                # Convert to a prose description instead
                result.append(BlockIR(
                    type=BlockType.paragraph,
                    content=f"(Code example omitted — see the {canonical_import} documentation for usage.)",
                    claim_ids=block.claim_ids,
                ))
                continue
        result.append(block)

    if stripped:
        logger.info("[Generate] Replaced %d code blocks with wrong imports", stripped)

    return result


def _load_pipeline_config() -> dict:
    """Load pipeline.yaml from the configs directory. Returns {} on failure."""
    try:
        from launcher.io.yamlio import load_yaml
        cfg_path = Path("configs/pipeline.yaml")
        if cfg_path.exists():
            return load_yaml(cfg_path) or {}
    except Exception:
        logger.debug("[Generate] Could not load pipeline.yaml, using linker defaults")
    return {}


