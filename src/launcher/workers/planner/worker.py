"""Planner worker — deterministic page plan with claim assignment.

Takes an UnderstandingBundle and produces a PlanBundle containing
the page plan (PlannedPage list) and claim assignment index.
"""
from __future__ import annotations

import logging
import time
from collections import Counter
from typing import Any

from launcher.models.base import LauncherBaseModel
from launcher.models.plan import PlanBundle
from launcher.models.understanding import UnderstandingBundle
from launcher.orchestrator.worker_contract import SelfReviewResult, WorkerContext, WorkerContract
from launcher.shared.page_skeletons import PAGE_ROLE_SKELETONS

logger = logging.getLogger(__name__)


class PlannerWorker(WorkerContract):
    @property
    def name(self) -> str:
        return "planner"

    async def run(self, input_data: LauncherBaseModel, context: WorkerContext) -> PlanBundle:
        """Build deterministic page plan from understanding bundle."""
        if not isinstance(input_data, UnderstandingBundle):
            raise TypeError(f"Expected UnderstandingBundle, got {type(input_data).__name__}")

        bundle = input_data
        start_time = time.monotonic()

        context.log.info("[Planner] Building page plan")
        context.emit_event("worker_started", {}, worker=self.name)

        # Heal mode: read directives from heal_metadata if present
        heal_metadata: dict = context.heal_metadata or {}
        re_run_count: int = heal_metadata.get("re_run_count", 0) or 0
        if re_run_count > 0:
            failed_pages = heal_metadata.get("failed_pages", []) or []
            failed_checks = heal_metadata.get("failed_checks", []) or []
            context.log.info(
                "[Planner] Heal mode (re_run=%d): %d pages need healing, checks: %s",
                re_run_count, len(failed_pages), failed_checks,
            )
            context.emit_event(
                "planner_heal_mode",
                {
                    "re_run_count": re_run_count,
                    "failed_pages": failed_pages,
                    "failed_checks": failed_checks,
                },
                worker=self.name,
            )

        from launcher.workers.planner.plan import run_plan

        # Instantiate Gemini client for slug refinement if available
        gemini_client = _get_gemini_client(context)

        page_evidence_index = getattr(bundle, "page_evidence_index", {}) or {}

        pages, claim_assignment_index = run_plan(
            bundle.product, bundle.richness_tier, bundle.claims, bundle.snippets,
            product_evidence=bundle.product_evidence,
            keyword_bundle=getattr(bundle, "keyword_research", None),
            api_surface=bundle.api_surface,
            gemini_client=gemini_client,
            page_evidence_index=page_evidence_index,
        )

        elapsed = time.monotonic() - start_time

        # TC-3881 Wave 3 (G7): Golden self-review with escalation tiers
        try:
            golden_enabled = getattr(context.config, "golden", {}).get("enabled", False) if hasattr(context.config, "golden") else False
            if golden_enabled:
                from launcher.shared.golden_loader import GoldenIndex
                from pathlib import Path
                golden_dir_str = getattr(context.config, "golden", {}).get("dir", "golden/")
                golden_index = GoldenIndex.load(Path(golden_dir_str))
                for page in pages:
                    golden_page = golden_index.get(page.page_role, getattr(page, "variant", "standard"))
                    if golden_page is None:
                        continue
                    planned_headings = [h.lower() for h in getattr(page, "skeleton", [])]
                    unmatched_headings: list[str] = []
                    for gs in golden_page.sections:
                        # Use corrected Jaccard threshold (0.5) matching G3
                        gh_words = set(gs.heading.lower().split())
                        matched = any(
                            len(gh_words & set(ph.split())) / max(len(gh_words | set(ph.split())), 1) >= 0.5
                            for ph in planned_headings
                        ) if len(gh_words) >= 2 else False
                        if not matched:
                            unmatched_headings.append(gs.heading)
                    unmatched = len(unmatched_headings)
                    if unmatched == 0:
                        pass  # all headings matched
                    elif unmatched <= 1:
                        logger.debug(
                            "Page %s: %d golden section unmatched (acceptable)",
                            page.page_id, unmatched,
                        )
                    elif unmatched <= 3:
                        # Tier 2: emit event, store on page
                        page.golden_unmatched_sections = unmatched_headings
                        context.emit_event(
                            "planning_golden_gap",
                            {
                                "page_id": page.page_id,
                                "unmatched_count": unmatched,
                                "unmatched_headings": unmatched_headings,
                            },
                            worker=self.name,
                        )
                    else:
                        # Tier 3: >= 4 unmatched — high severity
                        page.golden_unmatched_sections = unmatched_headings
                        context.emit_event(
                            "issue_opened",
                            {
                                "page_id": page.page_id,
                                "severity": "high",
                                "message": (
                                    f"Page {page.page_id}: {unmatched} golden sections have no "
                                    "planned counterpart — skeleton may produce poor quality content."
                                ),
                                "unmatched_headings": unmatched_headings,
                            },
                            worker=self.name,
                        )
        except Exception as exc:
            logger.debug("Golden self-review skipped: %s", exc)

        context.log.info("[Planner] Plan complete: %d pages, %.1fs", len(pages), elapsed)
        context.emit_event(
            "worker_completed",
            {"pages": len(pages)},
            worker=self.name,
        )

        return PlanBundle(
            pages=pages,
            claim_assignment_index=claim_assignment_index,
        )

    async def self_review(self, output: LauncherBaseModel) -> SelfReviewResult:
        """Validate plan integrity.

        Checks:
        - No claim appears on more than 2 pages
        - Every content page has at least 1 assigned claim (except TOC)
        - Permalink (page_id) uniqueness
        - TC-4218: Page title uniqueness (HIGH severity on collision)
        """
        if not isinstance(output, PlanBundle):
            return SelfReviewResult(passed=False, findings=[{"message": "Output is not PlanBundle"}])

        plan = output
        findings: list[dict[str, Any]] = []
        metrics: dict[str, Any] = {}

        # Check 1: Claim assignment cap (max 2 pages per claim)
        for claim_id, page_ids in plan.claim_assignment_index.items():
            if len(page_ids) > 2:
                findings.append({
                    "category": "claim_assignment",
                    "message": f"Claim {claim_id} assigned to {len(page_ids)} pages (max 2)",
                    "severity": "medium",
                })

        # Check 2: Page role validation against skeleton registry
        valid_roles = set(PAGE_ROLE_SKELETONS.keys())
        for page in plan.pages:
            if page.page_role not in valid_roles:
                findings.append({
                    "category": "invalid_role",
                    "message": f"Page '{page.page_id}' has unregistered role '{page.page_role}'",
                    "severity": "high",
                })

        # Check 3: Pages with claims (skip TOC)
        toc_roles = {"toc"}
        for page in plan.pages:
            if page.page_role not in toc_roles and not page.assigned_claims:
                findings.append({
                    "category": "thin_page",
                    "message": f"Page '{page.page_id}' ({page.page_role}) has no assigned claims",
                    "severity": "medium",
                })

        # Check 4: Permalink uniqueness
        seen: set[str] = set()
        for p in plan.pages:
            pid = p.page_id
            if pid in seen:
                findings.append({
                    "category": "permalink",
                    "message": f"Duplicate page_id: {pid}",
                    "severity": "high",
                })
            seen.add(pid)

        # Check 5: TC-4218 — Title uniqueness (HIGH severity; publication blocker)
        title_counter = Counter(p.title for p in plan.pages)
        duplicate_titles = [t for t, c in title_counter.items() if c > 1]
        if duplicate_titles:
            findings.append({
                "category": "title_uniqueness",
                "message": f"Duplicate page titles after dedup: {duplicate_titles}",
                "severity": "high",
            })

        # Metrics
        metrics["total_pages"] = len(plan.pages)
        metrics["mandatory_pages"] = sum(1 for p in plan.pages if p.mandatory)

        passed = not any(f.get("severity") == "high" for f in findings)
        return SelfReviewResult(passed=passed, findings=findings, metrics=metrics)


def create_worker() -> PlannerWorker:
    return PlannerWorker()


def _get_gemini_client(context: WorkerContext):
    """Instantiate Gemini SEO client if API key is available and SEO is enabled."""
    import os
    from pathlib import Path

    seo_config = getattr(context.config, "seo", None)
    if seo_config is not None and not getattr(seo_config, "slug_rewrite", True):
        return None

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        return None

    try:
        from launcher.clients.gemini_client import GeminiSEOClient
        from launcher.shared.seo_cache import SEOCache

        cache_root = context.run_dir.parent / ".seo_cache"
        cache = SEOCache(cache_root, default_ttl=7 * 86400)
        model = getattr(getattr(seo_config, "gemini", None), "model", "gemini-2.5-flash")
        return GeminiSEOClient(api_key=api_key, cache=cache, model=model)
    except Exception:
        logger.debug("[Planner] Failed to create Gemini client", exc_info=True)
        return None
