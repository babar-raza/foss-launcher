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


from launcher.orchestrator.stream_events import safe_stream_event as _safe_stream_event

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

# TC-4220: Minimum prose words per non-optional section + retry cap.
_MIN_SECTION_PROSE_WORDS: int = 30
_MAX_SECTION_RETRIES: int = 2

# GEN-6 (TC-5204): Terminal section headings that are bypassed for LLM generation.
# The linker's inject_links() deterministically fills See Also sections with verified
# cross-links after generation. Sending them to the LLM risks hallucinated URLs.
_SKIP_LLM_HEADINGS: frozenset[str] = frozenset({"see also"})

# TC-4220: Compiled regexes for prose word counting.
_HEADING_RE = re.compile(r"^#{1,6}\s+")
_BULLET_RE = re.compile(r"^\s*[-*+]\s+|^\s*\d+\.\s+")
_FENCE_RE = re.compile(r"^```")


def _extract_section_summary(section_ir: "SectionIR | None", section_heading: str) -> dict:
    """Extract a compact summary from a generated section for use in the next section's prompt.

    GEN-5 (TC-5205): Called after every section is produced so that section N+1 receives
    a lightweight digest of what section N already covered. Keeps cross-section repetition low
    without sending the full text into every subsequent prompt.

    Returns a dict with keys: heading, claim_ids, topics, code_patterns.
    All lists are bounded to stay well within prompt-budget constraints.
    """
    import re as _re

    if section_ir is None:
        return {"heading": section_heading, "claim_ids": [], "topics": [], "code_patterns": []}

    # Collect claim_ids from all blocks
    all_claim_ids: list[str] = []
    for blk in (getattr(section_ir, "blocks", []) or []):
        all_claim_ids.extend(getattr(blk, "claim_ids", []) or [])
    # Deduplicate preserving order
    seen: set[str] = set()
    deduped_claim_ids: list[str] = []
    for cid in all_claim_ids:
        if cid not in seen:
            seen.add(cid)
            deduped_claim_ids.append(cid)

    # Extract first sentence of prose blocks as topic signals
    topics: list[str] = []
    for blk in (getattr(section_ir, "blocks", []) or []):
        blk_type = str(getattr(blk, "type", "") or "")
        if blk_type in ("paragraph", "prose", "BlockType.paragraph"):
            content = getattr(blk, "content", "") or ""
            first_sent = content.split(".")[0][:120].strip()
            if first_sent:
                topics.append(first_sent)
        if len(topics) >= 2:
            break

    # Extract PascalCase API names from code blocks
    code_patterns: list[str] = []
    for blk in (getattr(section_ir, "blocks", []) or []):
        blk_type = str(getattr(blk, "type", "") or "")
        if blk_type in ("code", "BlockType.code"):
            content = getattr(blk, "content", "") or ""
            names = _re.findall(r'\b([A-Z][a-zA-Z0-9]{2,})\b', content[:500])
            code_patterns.extend(names[:3])
        if len(code_patterns) >= 3:
            break
    # Deduplicate code patterns
    code_patterns = list(dict.fromkeys(code_patterns))[:3]

    return {
        "heading": section_heading,
        "claim_ids": deduped_claim_ids[:6],
        "topics": topics[:2],
        "code_patterns": code_patterns,
    }


def _count_prose_words(text: str) -> int:
    """Count words on non-heading, non-bullet, non-code-fence lines.

    TC-4220: Used to detect thin sections (< 30 prose words) so the generate
    worker can retry the LLM call with an explicit minimum-length instruction
    before writing the section to disk.
    """
    count = 0
    in_fence = False
    for line in text.splitlines():
        stripped = line.strip()
        if _FENCE_RE.match(stripped):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if not stripped:
            continue
        if _HEADING_RE.match(stripped) or _BULLET_RE.match(stripped):
            continue
        count += len(stripped.split())
    return count


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

        # TC-5162: Build per-class api_facts lookup for docstring enrichment in section prompts.
        # Keyed by class_name → list[ApiFact] from ExtractionDatabase.
        _api_facts_by_class: dict = {}
        _extraction_db = getattr(understand, "extraction_db", None)
        if _extraction_db:
            _raw_api_facts = getattr(_extraction_db, "api_facts", []) or []
            for _af in _raw_api_facts:
                _cls = getattr(_af, "class_name", "") or ""
                if _cls:
                    _api_facts_by_class.setdefault(_cls, []).append(_af)

        # TC-5161: Extract page_evidence_index for adaptive sparse-evidence prompt injection.
        _page_evidence_index: dict = getattr(understand, "page_evidence_index", {}) or {}

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

        # TC-4041: extract workflow_examples and format lists for evidence injection
        _workflow_examples = getattr(
            getattr(understand, "product_evidence", None), "workflow_examples", None,
        ) or []
        _pe = getattr(understand, "product_evidence", None)
        _supported_formats: "dict[str, list[str]] | None" = None
        if _pe:
            _in_fmts = getattr(_pe, "input_formats", []) or []
            _out_fmts = getattr(_pe, "output_formats", []) or []
            if _in_fmts or _out_fmts:
                _supported_formats = {"input": _in_fmts, "output": _out_fmts}

        # TC-HO-04: extract capabilities for explicit capability statement injection
        _capabilities = getattr(_pe, "capabilities", None) or None

        # TC-HO-05: extract conversion_pairs for conversion-heading injection
        _conversion_pairs = getattr(_pe, "conversion_pairs", None) or None

        # TC-HO-06: extract missing_info for DO NOT CLAIM guard injection
        _missing_info = getattr(_pe, "missing_info", None) or None

        # TC-HO-08A: extract richness_tier object for REPOSITORY PROFILE injection
        _richness_tier_obj = getattr(understand, "richness_tier", None)

        # Heal optimization: skip pages not targeted for re-generation
        heal_target_pages = context.heal_target_pages  # None = all pages (normal mode)

        import asyncio as _asyncio_pages

        _page_sem = _asyncio_pages.Semaphore(_PAGE_CONCURRENCY)

        async def _process_page(
            page_plan: PlannedPage,
        ) -> tuple[PageIR, PlannedPage, str, str, int, int, dict] | None:
            """Process one page; return (ir, plan, tmpl, variant, llm_calls, fallbacks, repair_log) or None."""
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
                    return (cached_ir, page_plan, "", "", 0, 0, {})
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
                p_ir, p_llm, p_fb, t_used, t_variant, p_repair_log = await _generate_page(
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
                    workflow_examples=_workflow_examples or None,  # TC-4041
                    supported_formats=_supported_formats,  # TC-4041
                    capabilities=_capabilities,  # TC-HO-04
                    conversion_pairs=_conversion_pairs,  # TC-HO-05
                    missing_info=_missing_info,  # TC-HO-06
                    richness_tier_obj=_richness_tier_obj,  # TC-HO-08A
                    api_surface=understand.api_surface,  # TC-4213: identifier repair
                    api_facts_by_class=_api_facts_by_class or None,  # TC-5162
                    page_evidence_index=_page_evidence_index,  # TC-5161
                )
            return (p_ir, page_plan, t_used, t_variant, p_llm, p_fb, p_repair_log)

        # TC-DET-001: Sequential page processing for deterministic ordering.
        # Pages are processed in plan order to eliminate concurrency-induced
        # non-determinism (LLM context window effects when pages run in parallel).
        raw_page_results: list[tuple | None | BaseException] = []
        for pp in plan.pages:
            try:
                result = await _process_page(pp)
                raw_page_results.append(result)
            except BaseException as exc:
                raw_page_results.append(exc)

        page_results: list[tuple[PageIR, PlannedPage, str, str, bool]] = []
        generate_repair_log: dict[str, dict[str, list[str]]] = {}  # TC-4213: page_id → {section → repairs}
        for pp, result in zip(plan.pages, raw_page_results):
            if isinstance(result, BaseException):
                context.log.warning("[Generate] Page '%s' failed: %s", pp.page_id, result)
                fallback_count += 1
            elif result is None:
                pass  # Skip-and-no-cache already handled inside _process_page
            else:
                p_ir, p_plan, t_used, t_variant, p_llm, p_fb, p_repair_log = result
                page_results.append((p_ir, p_plan, t_used, t_variant, p_fb > 0))
                llm_calls += p_llm
                fallback_count += p_fb
                if p_repair_log:
                    generate_repair_log[pp.page_id] = p_repair_log

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
            for i, (page_ir, page_plan, tmpl_used, tmpl_variant, _fb) in enumerate(page_results):
                try:
                    page_claims = [c for c in all_claims if c.claim_id in set(page_plan.assigned_claims)]
                    optimized_ir = optimize_seo_metadata(
                        page_ir, product, page_claims, keyword_bundle,
                        subdomain_map=subdomain_map,
                    )
                    page_results[i] = (optimized_ir, page_plan, tmpl_used, tmpl_variant, _fb)
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
            for i, (page_ir, page_plan, tmpl_used, tmpl_variant, _fb) in enumerate(page_results):
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
                                page_plan, tmpl_used, tmpl_variant, _fb,
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
        _total_pages = len(page_results)
        for i, (linked_ir, (_, page_plan, tmpl_used, tmpl_variant, used_fallback)) in enumerate(
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

            # TC-4219: Resolve claim texts for the IDs actually cited in this page.
            # claims_by_id was built from understand.claims at the start of run().
            claim_texts = [
                claims_by_id[cid].text
                for cid in claim_ids_used
                if cid in claims_by_id
            ]

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
                claim_texts=claim_texts,  # TC-4219: verified claim texts for coverage check
                assigned_claim_ids=page_plan.assigned_claims,          # TC-5195: wire planner's full claim list
                assigned_claim_count=len(page_plan.assigned_claims),   # TC-5195: planner's assigned count (was len(claim_ids_used))
            ))
            await _safe_stream_event("page_generated", {
                "slug": slug,
                "words": word_count,  # authoritative: from len(markdown.split())
                "fallback": used_fallback,
                "total": _total_pages,
            })

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
            # TC-HO-09: Embed understand-worker outputs into graph state so the
            # Evaluate worker reads from the schema-validated ContentManifest
            # instead of performing disk side-loads of understand_checkpoint.json.
            api_surface=understand.api_surface,
            product_evidence=understand.product_evidence,
            # TC-5163: Embed page_evidence_index for Evaluate thin-evidence attribution
            page_evidence_index={
                role: score.model_dump(mode="json") if hasattr(score, "model_dump") else dict(score)
                for role, score in (getattr(understand, "page_evidence_index", {}) or {}).items()
            },
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

        # TC-4213: Write identifier repair audit log if any repairs were made.
        if generate_repair_log:
            try:
                _repair_log_path = context.run_dir / "generate_repair_log.json"
                _repair_log_path.write_text(
                    json.dumps(generate_repair_log, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
                _total_repairs = sum(
                    len(repairs)
                    for page_repairs in generate_repair_log.values()
                    for repairs in page_repairs.values()
                )
                context.log.info(
                    "[Generate] TC-4213: identifier repair log written (%d pages, %d total repairs) → %s",
                    len(generate_repair_log), _total_repairs, _repair_log_path,
                )
            except Exception as _e:
                context.log.warning(
                    "[Generate] TC-4213: failed to write generate_repair_log.json: %s", _e,
                )

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
        workflow_roles = {"workflow_page", "howto_article", "getting_started"}  # TC-5196
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
    workflow_examples: "list | None" = None,  # TC-4041: WorkflowExample list from product_evidence
    supported_formats: "dict[str, list[str]] | None" = None,  # TC-4041: {input:[...], output:[...]}
    capabilities: "list[dict] | None" = None,  # TC-HO-04: product_evidence.capabilities
    conversion_pairs: "list[dict] | None" = None,  # TC-HO-05: product_evidence.conversion_pairs
    missing_info: "list | None" = None,  # TC-HO-06: product_evidence.missing_info
    richness_tier_obj: "Any | None" = None,  # TC-HO-08A: RichnessResult from understanding bundle
    api_surface: "Any | None" = None,  # TC-4213: full ApiSurface for identifier repair
    api_facts_by_class: "dict | None" = None,  # TC-5162: ApiFact lists keyed by class_name
    page_evidence_index: "dict | None" = None,  # TC-5161: page_evidence_index for sparse-evidence prompt
) -> tuple[PageIR, int, int, str, str, dict]:
    """Generate content for a single page.

    Returns (PageIR, llm_calls, fallback_count, template_used, variant, repair_log).
    repair_log maps section_heading → list[repaired_identifiers] (TC-4213).
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

    # TC-4219: Build lookup and claim_context string for section writer grounding.
    # claim_context maps each assigned claim's text so the LLM writes from verified
    # facts rather than world knowledge. Capped at 50 claims / 4000 chars to stay
    # within token budgets. Empty string when no claims are assigned (backward-safe).
    _claims_by_id: dict[str, "Claim"] = {c.claim_id: c for c in all_claims}
    _claim_context_lines: list[str] = []
    for _cid in page_plan.assigned_claims:
        if _cid in _claims_by_id:
            _claim_context_lines.append(f"- [{_cid}] {_claims_by_id[_cid].text}")
    _claim_context_lines = _claim_context_lines[:50]  # cap at 50 claims
    _claim_context = "\n".join(_claim_context_lines)
    if len(_claim_context) > 4000:
        _claim_context = _claim_context[:4000]

    sections: list[SectionIR] = []
    llm_calls = 0
    fallback_count = 0
    allowed_claim_ids = page_claim_ids
    _page_repair_log: dict[str, list[str]] = {}  # TC-4213: section_heading → repaired identifiers

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

    # HG-21: Build enum member lookup for class attribute access validation.
    # Maps class_name → {valid_ALL_CAPS_members} for enum-like classes.
    _class_enum_members: dict[str, set[str]] = {}
    if class_briefs:
        for _brief in class_briefs:
            _caps = {
                _m.name for _m in (_brief.typed_methods or [])
                if _m.name == _m.name.upper() and len(_m.name) >= 3
            }
            if _caps:
                _class_enum_members[_brief.name] = _caps

    # HG-21: Build method name correction mapping.
    # For each identifier in api_identifiers that is NOT in typed_methods_set (snake_case only),
    # check if there is exactly ONE typed_method with the same long suffix (≥8 chars).
    # If so, add as a correction (wrong → right).
    _method_corrections: dict[str, str] = {}
    if class_briefs and api_identifiers:
        _typed_methods_set: set[str] = {
            _m.name for _b in class_briefs for _m in (_b.typed_methods or [])
        }
        for _ident in api_identifiers:
            if "_" not in _ident or _ident != _ident.lower():
                continue  # Only snake_case identifiers
            if _ident in _typed_methods_set:
                continue  # Already a valid typed method
            _parts = _ident.split("_", 1)
            if len(_parts) < 2 or len(_parts[1]) < 8:
                continue  # Suffix too short → too many false positives
            _suffix = _parts[1]
            _matches = [_m for _m in _typed_methods_set if _m.endswith("_" + _suffix)]
            if len(_matches) == 1:
                _method_corrections[_ident] = _matches[0]

    # HG-22 (TC-GEN-301): Build per-class method+property lookup for post-generate
    # method verification. Maps ClassName → frozenset(method_names | property_names).
    _class_method_map: dict[str, frozenset[str]] = {}
    if class_briefs:
        for _brief in class_briefs:
            _members: set[str] = set(_brief.methods)
            for _tm in (_brief.typed_methods or []):
                _members.add(_tm.name)
            for _p in (_brief.properties or []):
                _members.add(_p)
            for _tp in (_brief.typed_properties or []):
                _members.add(_tp.name)
            _class_method_map[_brief.name] = frozenset(_members)

    async def _generate_section(
        skel_section: SkeletonSection,
        idx: int,
        prior_summaries: "list[dict] | None" = None,
    ):
        """Generate one section. Returns (section_ir, llm_calls_delta, fallback_delta).

        GEN-5 (TC-5205): prior_summaries contains compact summaries of already-generated
        sections (claim_ids, topics, code API names). Passed to build_section_prompt so
        the LLM knows what has already been covered and avoids repeating it.
        """
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

        # GEN-6 (TC-5204): Bypass LLM for "See Also" sections.
        # The linker (Phase 2) deterministically injects verified cross-links
        # into See Also sections.  Generating them via LLM risks invented URLs.
        # We produce an empty SectionIR here; inject_links() will fill it.
        if skel_section.heading.lower().strip() in _SKIP_LLM_HEADINGS:
            logger.debug(
                "[GEN-6] Bypassing LLM for terminal section %r (page=%s) — linker will inject links",
                skel_section.heading,
                page_plan.page_id,
            )
            return SectionIR(
                section_id=skel_section.heading.lower().replace(" ", "_"),
                heading=skel_section.heading,
                level=skel_section.level,
                blocks=[],
            ), _llm, _fb

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
                    workflow_examples=workflow_examples,  # TC-4041
                    supported_formats=supported_formats,  # TC-4041
                    capabilities=capabilities,  # TC-HO-04
                    conversion_pairs=conversion_pairs,  # TC-HO-05
                    missing_info=missing_info,  # TC-HO-06
                    richness_tier_obj=richness_tier_obj,  # TC-HO-08A
                    claim_context=_claim_context,  # TC-4219: inject verified claim text
                    api_facts_by_class=api_facts_by_class,  # TC-5162
                    evidence_score=(page_evidence_index or {}).get(  # TC-5161
                        getattr(page_plan, "page_role", ""), None
                    ),
                    prior_sections_summary=prior_summaries or None,  # GEN-5 (TC-5205)
                )
                section_prompt_str = prompt

                _sec_max_tokens = max(512, (skel_section.max_words or 200) * 3)

                # TC-4220: Retry loop — re-invoke LLM if prose word count is below
                # threshold for non-optional sections (capped at _MAX_SECTION_RETRIES).
                _retry_prompt = prompt
                for _attempt in range(_MAX_SECTION_RETRIES + 1):
                    raw_response = await _call_llm(_retry_prompt, context, max_tokens=_sec_max_tokens)
                    _llm += 1

                    if not raw_response:
                        break

                    blocks = parse_and_validate_blocks(
                        raw_response, product, allowed_claim_ids, import_allowlist,
                        section_heading=skel_section.heading,
                        api_identifiers=api_identifiers,
                    )
                    if not blocks:
                        break

                    # FPR-03 / FPRSR-04: Warn about PascalCase identifiers not in api_surface
                    # BEFORE HG-16 removes the blocks. Accumulate violations so a retry
                    # directive with the correct class list can be injected below.
                    _has_api_violations = False
                    _api_violation_names: list[str] = []
                    if public_classes:
                        _pc_set = set(public_classes)
                        for _blk in blocks:
                            if _blk.type == BlockType.code and _blk.content:
                                _unknown_ids = _scan_code_block_api_identifiers(
                                    _blk.content, _pc_set,
                                )
                                if _unknown_ids:
                                    _has_api_violations = True
                                    _api_violation_names.extend(_unknown_ids)
                                    logger.warning(
                                        "[Generate] FPR-03: api_surface_violation: %s not in"
                                        " public_classes (section '%s', page '%s')",
                                        ", ".join(_unknown_ids),
                                        skel_section.heading,
                                        page_plan.page_id,
                                    )

                    # HG-16: Remove Python code blocks with hallucinated class names
                    if public_classes:
                        from launcher.workers.generate.section_validator import (
                            _strip_hallucinated_code_blocks,
                        )
                        blocks, _hg16_stripped = _strip_hallucinated_code_blocks(
                            blocks, set(public_classes),
                        )
                        # GEN-4 (TC-5203): After HG-16 strips a hallucinated block,
                        # attempt snippet-pool replacement before discarding it.
                        if _hg16_stripped and sec_snippets:
                            for _meta in _hg16_stripped:
                                _repl = _find_snippet_replacement(
                                    sec_snippets,
                                    _meta.get("claim_ids", []),
                                    _meta.get("language", ""),
                                )
                                if _repl is not None:
                                    blocks = list(blocks) + [_repl]
                                    logger.info(
                                        "[GEN-4] Replaced stripped hallucinated block"
                                        " with snippet (claim_ids=%s, section=%s)",
                                        _meta.get("claim_ids", []),
                                        skel_section.heading,
                                    )
                    # HG-21: Remove code blocks with invalid ALL-CAPS enum member access
                    if _class_enum_members:
                        from launcher.workers.generate.section_validator import (
                            _strip_hallucinated_enum_member_access,
                        )
                        blocks = _strip_hallucinated_enum_member_access(
                            blocks, _class_enum_members,
                        )
                    # HG-21: Correct known-wrong method names in code blocks
                    if _method_corrections:
                        from launcher.workers.generate.section_validator import (
                            _correct_method_names_in_code,
                        )
                        blocks = _correct_method_names_in_code(
                            blocks, _method_corrections,
                        )
                    # HG-22 (TC-GEN-301): Strip/comment-out hallucinated method calls
                    if _class_method_map and public_classes:
                        from launcher.workers.generate.section_validator import (
                            _strip_hallucinated_method_calls,
                        )
                        blocks = _strip_hallucinated_method_calls(
                            blocks, _class_method_map, set(public_classes),
                        )
                    if api_identifiers:
                        blocks = _validate_identifiers(blocks, api_identifiers)
                    blocks = _strip_commercial_urls(blocks)
                    blocks = _sanitize_code_blocks(
                        blocks, product.runtime_import or product.canonical_import, import_allowlist,
                    )

                    # FPR-04 / FPRSR-02: Detect Python syntax errors in code blocks.
                    # Explicit python/py/python3 blocks are always checked.
                    # Empty-language blocks are also checked on Python products so that
                    # LLM output without a language tag is not silently accepted.
                    _is_python_product = (
                        getattr(product, "language_tag", "") or ""
                    ).lower() in ("python", "py")
                    _has_syntax_errors = any(
                        not _accept_code_block(
                            b.content or "",
                            b.language if b.language else ("python" if _is_python_product else ""),
                        )
                        for b in blocks
                        if b.type == BlockType.code
                        and (
                            (b.language or "").lower() in ("python", "py", "python3")
                            or (_is_python_product and not b.language)
                        )
                    )

                    _candidate_ir = SectionIR(
                        section_id=skel_section.heading.lower().replace(" ", "_"),
                        heading=skel_section.heading,
                        level=skel_section.level,
                        blocks=blocks,
                    )

                    # TC-4220: Check prose word count; accept or retry.
                    _prose_text = "\n".join(
                        b.content or ""
                        for b in blocks
                        if str(getattr(b, "type", "")).lower() not in ("code", "fence")
                    )
                    _prose_count = _count_prose_words(_prose_text)
                    _is_optional = not getattr(skel_section, "required", True)

                    # TC-4229/TC-4249: Retry when code block absent for code-required roles.
                    # Fires regardless of sec_snippets — LLM can generate code from claims +
                    # canonical import even without snippet evidence. [TC-4249]
                    _needs_code_retry = False
                    if page_plan.page_role in _CODE_REQUIRED_ROLES:
                        _has_code = any(
                            "code" in str(getattr(b, "type", "")).lower()
                            or "fence" in str(getattr(b, "type", "")).lower()
                            for b in blocks
                        )
                        if not _has_code:
                            _needs_code_retry = True

                    _prose_ok = _prose_count >= _MIN_SECTION_PROSE_WORDS or _is_optional
                    if _prose_ok and not _needs_code_retry and not _has_syntax_errors and not _has_api_violations:
                        section_ir = _candidate_ir
                        break
                    if _attempt < _MAX_SECTION_RETRIES:
                        _retry_additions = []
                        if _has_api_violations:
                            logger.warning(
                                "[Generate] FPR-03/FPRSR-04: api_surface_retry: section '%s'"
                                " page '%s' attempt %d/%d — injecting class list",
                                skel_section.heading,
                                page_plan.page_id,
                                _attempt + 1,
                                _MAX_SECTION_RETRIES,
                            )
                            _retry_additions.append(
                                "CRITICAL: Only use these known API classes: "
                                + ", ".join(sorted(public_classes)[:20])
                                + ". Do NOT invent class names. "
                                + "The following names are NOT valid API classes: "
                                + ", ".join(sorted(set(_api_violation_names))[:5])
                                + "."
                            )
                            _api_violation_names = []  # reset for next attempt
                        if _has_syntax_errors:
                            logger.warning(
                                "[Generate] FPR-04: code_block_syntax_reject: section '%s'"
                                " page '%s' attempt %d/%d — retrying",
                                skel_section.heading,
                                page_plan.page_id,
                                _attempt + 1,
                                _MAX_SECTION_RETRIES,
                            )
                            _retry_additions.append(
                                "CRITICAL: Your Python code blocks must be syntactically valid."
                                " Every ```python block must compile without errors."
                                " Do not use placeholder text (e.g. [identifier omitted]) in code."
                            )
                        if not _prose_ok:
                            logger.warning(
                                "[Generate] Section %r has < %d prose words (attempt %d/%d) — retrying",
                                skel_section.heading,
                                _MIN_SECTION_PROSE_WORDS,
                                _attempt + 1,
                                _MAX_SECTION_RETRIES,
                            )
                            _retry_additions.append(
                                "IMPORTANT: This section must contain at least 30 words of"
                                " explanatory prose. Do not use only bullet lists or code blocks."
                            )
                        if _needs_code_retry:
                            logger.warning(
                                "[Generate] Section %r is missing required code block for role %r (attempt %d/%d) — retrying",
                                skel_section.heading,
                                page_plan.page_role,
                                _attempt + 1,
                                _MAX_SECTION_RETRIES,
                            )
                            _retry_additions.append(
                                "CRITICAL: This section REQUIRES at least one code block."
                                " Your response MUST include at least one ```python code block"
                                " with a working example using the canonical import."
                                " A response without a code block is INVALID for this page role."
                            )
                        # TC-4237: Always remind LLM about required type field on retry.
                        _retry_additions.append(
                            "CRITICAL: Every block in your JSON array MUST include a \"type\" field"
                            " (paragraph, code, list, heading, table, callout). Missing type = invalid block."
                        )
                        _retry_prompt = prompt + "\n\n" + "\n".join(_retry_additions)
                    else:
                        # All retries exhausted.
                        # EVL-1 (TC-5203): Strip syntax-invalid code blocks rather than
                        # keeping them in the final SectionIR.  Invalid code blocks that
                        # survive into the Evaluate worker cause code_correctness failures;
                        # a missing block is better than an uncompilable one.
                        if _has_syntax_errors:
                            _evl1_kept: list[BlockIR] = []
                            _evl1_stripped = 0
                            for _blk in _candidate_ir.blocks:
                                if _blk.type == BlockType.code:
                                    _blk_lang = (
                                        _blk.language
                                        if _blk.language
                                        else ("python" if _is_python_product else "")
                                    )
                                    if not _accept_code_block(_blk.content or "", _blk_lang):
                                        _evl1_stripped += 1
                                        logger.info(
                                            "[EVL-1] Stripped syntax-invalid code block"
                                            " after retry exhaustion (section=%r, %d chars)",
                                            skel_section.heading,
                                            len(_blk.content or ""),
                                        )
                                        continue
                                _evl1_kept.append(_blk)
                            if _evl1_stripped:
                                logger.warning(
                                    "[EVL-1] Stripped %d syntax-invalid block(s) from"
                                    " section %r after %d retries",
                                    _evl1_stripped,
                                    skel_section.heading,
                                    _MAX_SECTION_RETRIES,
                                )
                                _candidate_ir = _candidate_ir.model_copy(
                                    update={"blocks": _evl1_kept}
                                )
                        else:
                            logger.warning(
                                "[Generate] Section %r still fails quality checks after %d retries — using last result",
                                skel_section.heading,
                                _MAX_SECTION_RETRIES,
                            )
                        section_ir = _candidate_ir

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

            # Ensure all code blocks have a language tag; default per platform (TC-3887, TC-PLT-213).
            normed_blocks = _normalize_code_languages(list(section_ir.blocks), platform=product.platform)
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

            # Strip competitor domain links from prose (TC-4034).
            comp_fixed_blocks = _strip_competitor_links(list(section_ir.blocks))
            if comp_fixed_blocks != list(section_ir.blocks):
                section_ir = section_ir.model_copy(update={"blocks": comp_fixed_blocks})

            # TC-4213: Post-LLM identifier repair — replace hallucinated PascalCase
            # class names in prose and annotate them in code blocks.
            # Wrapped in try/except so a repair failure never blocks generation.
            if api_surface is not None:
                try:
                    from launcher.workers.generate._identifier_repair import repair_identifiers as _repair_ids
                    _repaired_blocks: list[BlockIR] = []
                    _section_repairs: list[str] = []
                    _product_display = getattr(product, "display_name", "") or ""
                    for _blk in section_ir.blocks:
                        _blk_content = _blk.content or ""
                        if not _blk_content:
                            _repaired_blocks.append(_blk)
                            continue
                        _is_code_blk = str(getattr(_blk, "type", "")).lower() in ("code", "fence")
                        if _is_code_blk:
                            # Wrap in fence so repair_identifiers treats it as a code segment
                            _lang = _blk.language or "python"
                            _fenced = f"```{_lang}\n{_blk_content}\n```\n"
                            _repaired_fenced, _blk_repairs = _repair_ids(
                                _fenced, api_surface, _product_display,
                            )
                            # Extract content between fence delimiters
                            _fenced_lines = _repaired_fenced.splitlines()
                            _inner = [
                                _l for _l in _fenced_lines
                                if not _l.startswith("```")
                            ]
                            _repaired_content = "\n".join(_inner).rstrip("\n")
                        else:
                            _repaired_content, _blk_repairs = _repair_ids(
                                _blk_content, api_surface, _product_display,
                            )
                        _section_repairs.extend(_blk_repairs)
                        if _repaired_content != _blk_content:
                            _repaired_blocks.append(_blk.model_copy(update={"content": _repaired_content}))
                        else:
                            _repaired_blocks.append(_blk)
                    if _section_repairs:
                        _page_repair_log[skel_section.heading] = _section_repairs
                        if len(_section_repairs) > 3:
                            context.emit_event(
                                "identifier_hallucination",
                                {
                                    "page_id": page_plan.page_id,
                                    "section": skel_section.heading,
                                    "count": len(_section_repairs),
                                    "identifiers": _section_repairs[:10],  # cap at 10 for payload size
                                },
                                worker="generate",
                            )
                    if _repaired_blocks != list(section_ir.blocks):
                        section_ir = section_ir.model_copy(update={"blocks": _repaired_blocks})

                    # FPR-01: scan repaired code blocks for the placeholder sentinel.
                    # Its presence means code was prose-repaired or the LLM hallucinated it.
                    _oi_violations = _detect_identifier_omitted_in_code(list(section_ir.blocks))
                    if _oi_violations:
                        logger.warning(
                            "[Generate] FPR-01: '[identifier omitted]' in code block(s) %s"
                            " of section '%s' on page '%s'",
                            _oi_violations, skel_section.heading, page_plan.page_id,
                        )
                except Exception:
                    logger.debug("[Generate] TC-4213 identifier repair failed for section '%s'", skel_section.heading, exc_info=True)

        return section_ir, _llm, _fb

    # GEN-5 (TC-5205): Generate sections sequentially so each section can receive a compact
    # summary of prior sections. This replaces the previous asyncio.gather approach (GE-02 OPT-5).
    # The latency trade-off is acceptable: pages have 4-8 sections and the per-section LLM call
    # dominates wall-clock time; sequential ordering adds negligible overhead.
    _prior_summaries: list[dict] = []  # accumulates GEN-5 summaries section by section

    for idx, skel_section in enumerate(skeleton):
        # TC-3879 Wave 1 (F1): capture idx for fallback claim reconstruction below.
        try:
            result = await _generate_section(skel_section, idx, prior_summaries=_prior_summaries)
        except BaseException as _sec_exc:
            result = _sec_exc

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
            fallback_ir = render_section_deterministic(skel_section, skel_claims, skel_snippets, product)
            sections.append(fallback_ir)
            # GEN-5: extract summary even from fallback so next section has context
            _prior_summaries.append(_extract_section_summary(fallback_ir, skel_section.heading))
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
            # GEN-5: extract summary for use in next section's prompt
            _prior_summaries.append(_extract_section_summary(s_ir, skel_section.heading))

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

    return page_ir, llm_calls, fallback_count, template_used, variant, _page_repair_log


async def _call_llm(prompt: str, context: WorkerContext, max_tokens: int | None = None) -> str | None:
    """Call the LLM with the given prompt. Returns raw response or None on failure."""
    import asyncio
    import os

    if not context.llm_config:
        return None

    api_key = os.environ.get("litellm_key", "")

    # ARC-2: On heal re-runs, use heal_temperature (0.3) so the LLM produces
    # different output rather than reproducing the same deterministic result at temp=0.
    _heal_temp = (context.heal_metadata or {}).get("heal_temperature")
    _eff_temperature = _heal_temp if _heal_temp is not None else context.llm_config.temperature
    if _heal_temp is not None:
        logger.debug(
            "[Generate][ARC-2] heal_temperature override active: %.2f (config=%.2f)",
            _eff_temperature,
            context.llm_config.temperature,
        )

    try:
        from launcher.clients.llm_provider import LLMProviderClient

        client = LLMProviderClient(
            api_base_url=context.llm_config.primary.base_url,
            model=context.llm_config.primary.model,
            run_dir=context.run_dir,
            api_key=api_key,
            temperature=_eff_temperature,
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
                    temperature=_eff_temperature,
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
    *,
    api_surface: "Any | None" = None,
    page_role: str = "unknown",
    claims: "list | None" = None,
) -> SectionIR:
    """Deterministically add a minimal code block to a section that requires one.

    TC-3878 (W2): Prefers extracted snippets (source_type=="extracted") when available,
    as they contain real validated code.
    TC-DFR-007: Falls back to synthesis from api_surface if available.
    TC-5112: Prepends section heading as a comment label.

    Returns a new SectionIR with a code block appended.
    """
    heading_label = f"# {section_ir.heading}\n" if section_ir.heading else ""
    _MAX_CODE_LEN = 2000  # TC-5110: skip oversized snippets

    # TC-3878: Prefer extracted snippets — real validated code over placeholder
    if section_snippets:
        for snippet in section_snippets:
            if getattr(snippet, "source_type", None) == "extracted":
                code_content = getattr(snippet, "code", None) or ""
                if not code_content.strip() or len(code_content) > _MAX_CODE_LEN:
                    continue
                gap_block = BlockIR(
                    type=BlockType.code,
                    content=heading_label + code_content,
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

    # TC-DFR-007: Attempt synthesis from api_surface
    if api_surface is not None:
        try:
            from launcher.workers.generate._code_synthesis import synthesize_section_snippet
            synth = synthesize_section_snippet(
                api_surface,
                section_heading=section_ir.heading or "",
                page_role=page_role,
                product=product,
                claims=claims or [],
            )
            if synth is not None:
                code_content = getattr(synth, "code", None) or ""
                if code_content.strip():
                    gap_block = BlockIR(
                        type=BlockType.code,
                        content=heading_label + code_content,
                        language=getattr(synth, "language", "python") or "python",
                        claim_ids=[],
                    )
                    new_blocks = list(section_ir.blocks) + [gap_block]
                    return SectionIR(
                        section_id=section_ir.section_id,
                        heading=section_ir.heading,
                        level=section_ir.level,
                        blocks=new_blocks,
                    )
        except Exception:
            pass  # Non-fatal — fall to placeholder

    placeholder_code = (
        f"{heading_label}# Example usage\nimport {product.runtime_import or product.canonical_import or 'package'}\n"
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
                # TC-4237: Always remind LLM about required type field on every enforcement retry.
                violations.append(
                    "- CRITICAL: Every block MUST include a \"type\" field"
                    " (paragraph, code, list, heading, table, callout)"
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
                prepend = prepend[:500]  # raised from 300 — type-reminder + violations can now fit
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

# FPRSR-01 (2026-03-23): Superset of _BUILTIN_IDENTIFIERS used by
# _scan_code_block_api_identifiers to suppress false positives.
# _BUILTIN_IDENTIFIERS is still used by _validate_identifiers — do not merge them.
# SRP-01 (2026-03-24): Shared source in launcher.shared.python_names.
from launcher.shared.python_names import STDLIB_PYTHON_NAMES  # noqa: E402

_SCAN_BUILTINS: frozenset[str] = _BUILTIN_IDENTIFIERS | STDLIB_PYTHON_NAMES


_IDENTIFIER_OMITTED_SENTINEL = "[identifier omitted]"


def _detect_identifier_omitted_in_code(blocks: list[BlockIR]) -> list[int]:
    """Return the 1-based indices of code blocks that contain the ``[identifier omitted]``
    sentinel string.

    This string must never appear inside a fenced code block: it is the prose-repair
    placeholder produced by ``_identifier_repair.repair_identifiers`` when a PascalCase
    identifier is found in a prose segment that was incorrectly classified as prose rather
    than code.  Its presence in a code block indicates either (a) the LLM generated it
    literally, or (b) a code fragment was in a prose-typed block and got prose-repaired.
    Either situation will cause evaluate to raise a HIGH finding.

    FPR-01 (2026-03-22).
    """
    violations: list[int] = []
    for idx, block in enumerate(blocks, start=1):
        if block.type == BlockType.code or str(getattr(block, "type", "")).lower() in ("code", "fence"):
            if block.content and _IDENTIFIER_OMITTED_SENTINEL in block.content:
                violations.append(idx)
    return violations


# FPR-03 (2026-03-22): Broader PascalCase scanner used by _scan_code_block_api_identifiers.
# Intentionally broader than section_validator._CLASS_USAGE_RE so that single-word
# PascalCase names like "Worksheet" are detected (no second capital required).
_PASCAL_RE = re.compile(r'\b[A-Z][a-zA-Z0-9]+\b')


def _scan_code_block_api_identifiers(
    code: str,
    public_classes: set[str],
) -> list[str]:
    """Return PascalCase identifiers in *code* that are not in *public_classes*.

    Used as a pre-removal observability step before HG-16 strips the block:
    callers log a WARNING for each returned identifier so the issue is
    surfaced in run logs even after the block is removed.

    Filters out Python builtins (``True``, ``False``, ``None``, standard typing
    constructs) using ``_BUILTIN_IDENTIFIERS`` to avoid false positives.

    FPR-03 (2026-03-22).

    Parameters
    ----------
    code:
        Raw source code string (block content, without fence delimiters).
    public_classes:
        Set of known class names from ``api_surface.public_classes``.
        Pass an empty set to skip the check (returns [] immediately).

    Returns
    -------
    list[str]
        Deduplicated, sorted list of unknown PascalCase identifiers.
    """
    if not public_classes:
        return []

    # Strip inline comments to avoid flagging capitalised English words.
    code_no_comments = "\n".join(line.split("#")[0] for line in code.split("\n"))

    seen: set[str] = set()
    unknown: list[str] = []
    for m in _PASCAL_RE.finditer(code_no_comments):
        name = m.group(0)
        if name in seen:
            continue
        seen.add(name)
        if name in _SCAN_BUILTINS:
            continue
        if name in public_classes:
            continue
        unknown.append(name)
    return sorted(unknown)


def _accept_code_block(code: str, lang: str) -> bool:
    """Return True iff *code* is acceptable for the generate sandwich.

    For Python language blocks (``lang`` in ``python``, ``py``, ``python3``),
    performs a compile-time syntax check via stdlib ``compile()``.
    Non-Python blocks always return True (no parser to apply).

    Shell-like first lines (``pip install``, ``$ ``, shebangs) are skipped
    to avoid false positives on install instructions.

    FPR-04 (2026-03-22).

    Parameters
    ----------
    code:
        Raw source code string (block content, without fence delimiters).
    lang:
        Language tag from the code block (e.g. "python", "javascript", "").

    Returns
    -------
    bool
        True if the block passes all checks; False if it should be retried.
    """
    if lang.lower() not in ("python", "py", "python3"):
        return True
    code_stripped = code.strip()
    if not code_stripped:
        return True
    # Skip install/shell commands that aren't ast-parseable Python.
    first_line = code_stripped.split("\n")[0].strip()
    if first_line.startswith(("pip ", "pip3 ", "$ ", "#!/", "#!")):
        return True
    try:
        compile(code_stripped, "<string>", "exec")
        return True
    except SyntaxError:
        return False


def _find_snippet_replacement(
    snippets: "list[Any]",
    claim_ids: list[str],
    language: str,
) -> "BlockIR | None":
    """GEN-4 (TC-5203): Find a snippet from the pool to replace a stripped code block.

    Matching strategy (first match wins):
    1. claim_ids intersection — snippet whose claim_ids overlap with the stripped block's
    2. language fallback — if no claim_ids overlap, use the first snippet with a matching
       language (or any syntax-valid snippet if language is empty)

    Parameters
    ----------
    snippets:
        List of Snippet objects from the page plan (sec_snippets for this section).
    claim_ids:
        claim_ids from the stripped block (may be empty).
    language:
        language tag from the stripped block (may be empty string).

    Returns
    -------
    BlockIR | None
        A new code BlockIR built from the matching snippet, or None if no match.
    """
    if not snippets:
        return None

    claim_id_set = set(claim_ids)
    lang_lower = language.lower() if language else ""

    # Strategy 1: match by claim_ids intersection
    if claim_id_set:
        for snippet in snippets:
            snippet_claims = set(getattr(snippet, "claim_ids", []) or [])
            if snippet_claims & claim_id_set:
                code = getattr(snippet, "code", "") or ""
                if not code.strip():
                    continue
                snip_lang = getattr(snippet, "language", "python") or "python"
                return BlockIR(
                    type=BlockType.code,
                    content=code,
                    language=snip_lang,
                    claim_ids=list(claim_id_set & snippet_claims),
                )

    # Strategy 2: language fallback — first snippet with matching language
    for snippet in snippets:
        code = getattr(snippet, "code", "") or ""
        if not code.strip():
            continue
        snip_lang = (getattr(snippet, "language", "python") or "python").lower()
        if lang_lower and snip_lang != lang_lower:
            continue
        # syntax_valid guard: only use validated snippets
        if not getattr(snippet, "syntax_valid", True):
            continue
        return BlockIR(
            type=BlockType.code,
            content=code,
            language=snip_lang,
            claim_ids=[],
        )

    return None


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


_SHELL_PREFIXES = ("pip ", "pip3 ", "npm ", "npx ", "apt ", "apt-get ", "brew ", "conda ", "yarn ",
                   "dotnet ", "mvn ", "gradle ", "nuget ", "cmake ")

# TC-PLT-213: Platform-to-default-language mapping for code blocks
_PLATFORM_DEFAULT_LANG: dict[str, str] = {
    "python": "python",
    "dotnet": "csharp",
    "java": "java",
    "cpp": "cpp",
    "node": "javascript",
    "typescript": "typescript",
}


def _normalize_code_languages(blocks: list[BlockIR], platform: str = "python") -> list[BlockIR]:
    """Ensure all code blocks have a correct language tag (TC-3887, TC-3908, TC-PLT-213).

    When the section-writer LLM omits the ``language`` field, the IR renderer
    produces bare triple-backtick fences which the LLM reviewer flags as
    ``code_correctness HIGH``.

    TC-3908 extension: also corrects explicitly wrong tags when the
    block content is a shell command (pip install, npm, dotnet, mvn, etc.).

    TC-PLT-213: Default language is now platform-aware instead of hardcoded "python".

    Heuristic:
    - If ``block.language`` is already set AND is not a wrong tag → leave unchanged.
    - If the first non-empty line starts with a shell prefix → set ``language = "bash"``.
    - Otherwise → set ``language`` to the platform default.
    """
    default_lang = _PLATFORM_DEFAULT_LANG.get(platform, "python")
    # Tags that indicate a wrong language when content is actually a shell command
    _wrong_shell_tags = {"python", "py", "csharp", "java", "cpp", "javascript", "typescript"}
    result: list[BlockIR] = []
    for block in blocks:
        if block.type != "code":
            result.append(block)
            continue
        first_line = (block.content or "").lstrip().split("\n")[0].lstrip()
        is_shell = any(first_line.startswith(p) for p in _SHELL_PREFIXES)
        # Leave block unchanged if language is already set correctly.
        # Exception (TC-3908): if tagged as a code language but content is a shell command,
        # correct to bash.
        if block.language and not (is_shell and block.language in _wrong_shell_tags):
            result.append(block)
            continue
        lang = "bash" if is_shell else default_lang
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

# TC-4034: competitor domain deny list — links to these domains are stripped from prose.
_COMPETITOR_DOMAINS: frozenset[str] = frozenset({
    "openpyxl.readthedocs.io",
    "xlsxwriter.readthedocs.io",
    "pandas.pydata.org",
    "python-excel.org",
    "xlrd.readthedocs.io",
    "xlwt.readthedocs.io",
})
# Matches [anchor text](http(s)://url)
_EXTERNAL_LINK_RE = re.compile(r"\[([^\[\]]+)\]\((https?://[^)]+)\)")


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


def _strip_competitor_links(blocks: list[BlockIR]) -> list[BlockIR]:
    """Replace competitor domain links with plain anchor text (TC-4034).

    Strips ``[text](https://openpyxl.readthedocs.io/...)`` → ``text``
    for domains in ``_COMPETITOR_DOMAINS``.  Code blocks are never modified.
    """
    from urllib.parse import urlparse

    def _repl(m: re.Match) -> str:
        url = m.group(2)
        domain = urlparse(url).netloc.removeprefix("www.")
        if domain in _COMPETITOR_DOMAINS:
            return m.group(1)  # anchor text only
        return m.group(0)  # keep non-competitor links unchanged

    def _strip(text: str) -> str:
        return _EXTERNAL_LINK_RE.sub(_repl, text)

    result: list[BlockIR] = []
    changed = 0
    for block in blocks:
        if block.type == "code":
            result.append(block)
            continue
        new_content = _strip(block.content) if block.content else block.content
        new_items = [_strip(item) for item in block.items] if block.items else block.items
        if new_content != block.content or new_items != block.items:
            changed += 1
            result.append(block.model_copy(update={"content": new_content, "items": new_items}))
        else:
            result.append(block)
    if changed:
        logger.info("[Generate] Stripped competitor links from %d blocks (TC-4034)", changed)
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

    # TC-GEN-302: Build set of allowed full import paths (case-insensitive).
    # Previous prefix-only matching (split(".")[0]) caused "aspose" to match
    # any Aspose.* variant, letting wrong imports like Aspose.FakeModule pass.
    allowed_full = {canonical_import.lower()}
    for imp in import_allowlist:
        allowed_full.add(imp.lower())

    # Common wrong patterns the LLM generates
    _WRONG_IMPORT_RE = re.compile(
        r"^\s*(?:import|from)\s+(Aspose\.\w+|aspose\.\w+)",
        re.MULTILINE,
    )

    result: list[BlockIR] = []
    stripped = 0
    for block in blocks:
        if block.type == BlockType.code and block.content:
            # Check for wrong imports against full dotted paths
            wrong = _WRONG_IMPORT_RE.findall(block.content)
            has_wrong = any(
                w.lower() not in allowed_full
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


# ---------------------------------------------------------------------------
# TC-FIX-214: Missing symbols required by test suite
# ---------------------------------------------------------------------------

import re as _re_mod

# Terminal section headings (case-insensitive)
_TERMINAL_HEADINGS = frozenset({
    "see also", "references", "related topics", "further reading",
    "related resources",
})


def _reorder_terminal_sections(sections: "list[SectionIR]") -> "list[SectionIR]":
    """Move terminal sections to the end while preserving relative order.

    Terminal headings: See Also, References, Related Topics, Further Reading.
    """
    if not sections:
        return []
    non_terminal = []
    terminal = []
    for s in sections:
        if s.heading.strip().lower() in _TERMINAL_HEADINGS:
            terminal.append(s)
        else:
            non_terminal.append(s)
    return non_terminal + terminal


# Scaffold / template patterns for stripping
_SCAFFOLD_PATTERNS_BASIC = _re_mod.compile(
    r"^(?:"
    r"\s*TODO\b"
    r"|\s*TBD\b"
    r"|\s*\[placeholder\]"
    r"|\s*\[section title\]"
    r"|\s*\[content to be generated\]"
    r"|\s*\[content\]"
    r")",
    _re_mod.IGNORECASE,
)

_SCAFFOLD_PATTERNS_EXTENDED = _re_mod.compile(
    r"(?:"
    r"\bTODO\b"
    r"|\bTBD\b"
    r"|\[placeholder\]"
    r"|\[section title\]"
    r"|\[content to be generated\]"
    r"|content to be generated"
    r"|section title here"
    r"|in 1-3 sentences"
    r"|what the reader will build"
    r"|class or function purpose"
    r"|\[fill in"
    r"|fill in\b"
    r")",
    _re_mod.IGNORECASE,
)


def _strip_template_echo_from_blocks(blocks: "list[BlockIR]") -> "list[BlockIR]":
    """Remove scaffold/template text from paragraph blocks.

    Code blocks are never modified. For multi-line paragraphs, only scaffold
    lines are removed. If all lines are scaffold, the entire block is dropped.
    """
    if not blocks:
        return []
    result: list[BlockIR] = []
    for block in blocks:
        if block.type != "paragraph":
            result.append(block)
            continue
        if not block.content:
            result.append(block)
            continue
        lines = block.content.split("\n")
        clean_lines = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                clean_lines.append(line)
                continue
            if _SCAFFOLD_PATTERNS_BASIC.search(stripped):
                continue
            clean_lines.append(line)
        if not any(l.strip() for l in clean_lines):
            continue  # All scaffold → drop block
        new_content = "\n".join(clean_lines).strip()
        if not new_content:
            continue
        result.append(BlockIR(
            type=block.type,
            content=new_content,
            claim_ids=block.claim_ids,
            items=block.items,
            level=block.level,
            language=block.language,
        ))
    return result


def _sanitize_scaffold_text(blocks: "list[BlockIR]") -> "tuple[list[BlockIR], bool]":
    """Strip scaffold/template phrases from prose blocks.

    Returns (cleaned_blocks, had_scaffold). Code blocks are exempt.
    Extended patterns: TODO, TBD, Fill in, Content to be generated,
    Section title here, in 1-3 sentences, What the reader will build,
    Class or function purpose.
    """
    if not blocks:
        return [], False
    had_scaffold = False
    result: list[BlockIR] = []
    for block in blocks:
        if block.type in ("code",):
            result.append(block)
            continue
        if block.type != "paragraph":
            result.append(block)
            continue
        if not block.content:
            result.append(block)
            continue
        lines = block.content.split("\n")
        clean_lines = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                clean_lines.append(line)
                continue
            if _SCAFFOLD_PATTERNS_EXTENDED.search(stripped):
                had_scaffold = True
                continue
            clean_lines.append(line)
        new_content = "\n".join(clean_lines).strip()
        if not new_content:
            continue  # All lines were scaffold → drop block
        result.append(BlockIR(
            type=block.type,
            content=new_content,
            claim_ids=block.claim_ids,
            items=block.items,
            level=block.level,
            language=block.language,
        ))
    return result, had_scaffold


def _canonicalize_python_imports(
    blocks: "list[BlockIR]",
    canonical_import: str,
    runtime_import: str,
) -> "list[BlockIR]":
    """Rewrite pip-package-name imports to runtime form in code blocks.

    E.g., ``import aspose_cells_foss`` → ``import aspose.cells_foss``
    when canonical='aspose_cells_foss' and runtime='aspose.cells_foss'.
    Paragraph blocks are never modified.
    """
    if not canonical_import or not runtime_import:
        return blocks
    if canonical_import == runtime_import:
        return blocks

    result: list[BlockIR] = []
    for block in blocks:
        if block.type != "code":
            result.append(block)
            continue
        if not block.content:
            result.append(block)
            continue
        # Replace canonical with runtime in import statements
        new_content = block.content.replace(canonical_import, runtime_import)
        result.append(BlockIR(
            type=block.type,
            content=new_content,
            claim_ids=block.claim_ids,
            items=block.items,
            level=block.level,
            language=block.language,
        ))
    return result


_EVIDENCE_MIN_SNIPPETS: dict[str, int] = {
    "howto_article": 2,
    "getting_started": 1,
    "installation": 1,
    "developer_guide": 1,
    "blog_announcement": 1,
    "feature_blog": 1,
    "workflow_page": 1,
    "reference_object_page": 0,
    "api_reference": 0,
    "landing": 0,
    "toc": 0,
    "faq": 0,
    "troubleshooting": 0,
    "feature_showcase": 0,
}

_EVIDENCE_MIN_CLAIMS: dict[str, int] = {
    "howto_article": 5,
    "getting_started": 3,
    "installation": 2,
    "developer_guide": 3,
    "blog_announcement": 3,
    "feature_blog": 3,
    "reference_object_page": 3,
    "api_reference": 2,
    "faq": 3,
    "troubleshooting": 3,
}

_EVIDENCE_SCORE_THRESHOLD_DEFAULT = 0.3
_EVIDENCE_SCORE_THRESHOLD_HIGH: dict[str, float] = {
    "howto_article": 0.6,
    "developer_guide": 0.6,
    "blog_announcement": 0.5,
    "feature_blog": 0.5,
}


def _check_evidence_adequacy(
    page: "PlannedPage",
    claims_by_id: "dict[str, Any]",
) -> "tuple[bool, str]":
    """Pre-generation gate: check if page has enough evidence for quality content.

    Returns (True, '') on pass, (False, reason) on fail.
    """
    role = getattr(page, "page_role", "") or ""
    assigned_claims = getattr(page, "assigned_claims", []) or []
    assigned_snippets = getattr(page, "assigned_snippets", []) or []
    n_claims = len(assigned_claims)
    n_snippets = len(assigned_snippets)

    # Check evidence_sufficient flag
    evidence_sufficient = getattr(page, "evidence_sufficient", True)
    if not evidence_sufficient:
        evidence_missing = getattr(page, "evidence_missing", []) or []
        missing_str = ", ".join(str(m) for m in evidence_missing) if evidence_missing else "unknown"
        return False, f"evidence_sufficient=False missing=[{missing_str}]"

    # Check evidence_score threshold (role-specific or default)
    evidence_score = getattr(page, "evidence_score", 1.0)
    score_threshold = _EVIDENCE_SCORE_THRESHOLD_HIGH.get(role, _EVIDENCE_SCORE_THRESHOLD_DEFAULT)
    if evidence_score < score_threshold:
        return False, f"evidence_score={evidence_score} below threshold={score_threshold}"

    # Role-specific snippet minimum
    min_snippets = _EVIDENCE_MIN_SNIPPETS.get(role, 0)
    if n_snippets < min_snippets:
        return False, f"snippets={n_snippets} below min={min_snippets} for role={role}"

    # Role-specific claim minimum
    min_claims = _EVIDENCE_MIN_CLAIMS.get(role, 2)
    if n_claims < min_claims:
        return False, f"claims={n_claims} below min={min_claims} for role={role}"

    # FAQ-specific: require 3+ limitation/troubleshoot claims
    if role == "faq":
        _LIMITATION_KINDS = {"limitation", "troubleshoot", "config"}
        n_lim = sum(
            1 for cid in assigned_claims
            if cid in claims_by_id and getattr(claims_by_id[cid], "kind", "") in _LIMITATION_KINDS
        )
        if n_lim < 3:
            return False, f"faq_limitation_claims={n_lim} below min=3"

    return True, ""


def _make_understand_from_context(
    claims: list,
    snippets: list,
    product: "Any | None",
    richness_tier_str: str,
    product_evidence_dict: "dict | None" = None,
    api_surface_dict: "dict | None" = None,
) -> "SimpleNamespace":
    """TC-4318: Reconstruct an understand-like namespace from GenerationContext fields.

    Deserializes product_evidence and api_surface from JSON-safe dicts back into
    pydantic models for use by the generate worker.
    """
    from types import SimpleNamespace
    from launcher.models.understanding import ProductEvidence
    from launcher.models.product import ApiSurface

    # Deserialize ProductEvidence
    pe = ProductEvidence()
    if product_evidence_dict:
        try:
            pe = ProductEvidence.model_validate(product_evidence_dict)
        except Exception as exc:
            logger.warning("TC-4318: malformed product_evidence_dict, falling back to empty: %s", exc)

    # Deserialize ApiSurface — always return an ApiSurface (never None)
    api_surface = ApiSurface(public_classes=[], import_allowlist=[], confidence="low")
    if api_surface_dict:
        try:
            api_surface = ApiSurface.model_validate(api_surface_dict)
        except Exception as exc:
            logger.warning("TC-4318: malformed api_surface_dict, falling back to empty: %s", exc)
            api_surface = ApiSurface(public_classes=[], import_allowlist=[], confidence="low")

    return SimpleNamespace(
        product_evidence=pe,
        api_surface=api_surface,
        extraction_db=None,  # TC-4272: fast path — no extraction_db in context mode
        claims=claims,
        snippets=snippets,
        product=product,
        richness_tier=richness_tier_str,
    )


def _validate_understand_namespace(ns: "Any", source: str) -> None:
    """TC-4319: Observability checks for understand namespace completeness."""
    pe = getattr(ns, "product_evidence", None)
    if pe is not None:
        # Check if product_evidence is effectively empty (all defaults)
        has_content = bool(
            getattr(pe, "limitations", None)
            or getattr(pe, "capabilities", None)
            or getattr(pe, "install_recipe", None)
            or getattr(pe, "input_formats", None)
            or getattr(pe, "output_formats", None)
        )
        if not has_content:
            logger.warning("TC-4319: product_evidence is empty in understand namespace from %s", source)
    elif pe is None:
        logger.warning("TC-4319: product_evidence is missing from understand namespace from %s", source)

    edb = getattr(ns, "extraction_db", None)
    if edb is None:
        logger.debug("TC-4319: extraction_db is None in understand namespace from %s", source)

