"""W10 SEO Optimizer Worker: Post-process final .md files for on-page SEO.

Pipeline position: After W6 (LinkerAndPatcher), before W7 (Validator).
Operates on the site/content directory produced by W6.

Phases:
1. Keyword Research -- Google Trends + Suggest + heuristic (cached)
2. Keyword Extraction & Injection -- density-controlled natural insertion
3. SEO Metadata -- frontmatter optimization (seoTitle, description, keywords, canonical)

TC-2205: W10 SEO Optimizer Worker
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional

from ...util.logging import get_logger
from .cache import SEOCache
from .keyword_research import research_keywords
from .keyword_optimizer import extract_keywords, inject_keywords_naturally
from .seo_metadata import optimize_seo_metadata
from .keyword_utils import (
    extract_keywords_from_content,
    inject_keywords_naturally as inject_kw_naturally,
    enforce_seo_metadata_quality,
)

logger = get_logger()


class SEOOptimizerError(Exception):
    """Base exception for W10 SEO Optimizer errors."""
    pass


class SEOOptimizerArtifactMissingError(SEOOptimizerError):
    """Required artifact not found."""
    pass


def execute_seo_optimizer(
    run_dir: Path, run_config: Dict[str, Any]
) -> Dict[str, Any]:
    """W10 SEO Optimizer worker -- optimizes final .md files for on-page SEO.

    Steps:
    1. Load product_facts.json and page_plan.json from artifacts
    2. Research keywords once for the product (cached)
    3. For each .md file in site/content/:
       a. Extract page-specific keywords
       b. Merge with research keywords
       c. Inject keywords naturally
       d. Optimize SEO metadata in frontmatter
       e. Write back optimized .md
    4. Write seo_report.json and return results

    Args:
        run_dir: Path to run directory
        run_config: Run configuration dict

    Returns:
        Dict with:
        {
            "status": "ok" | "skipped" | "disabled",
            "pages_optimized": int,
            "report": {...},
        }

    Raises:
        SEOOptimizerArtifactMissingError: If required artifact not found
    """
    # Check if SEO is enabled (defaults to True)
    if not run_config.get("seo_enabled", True):
        logger.info("[W10] SEO optimization disabled in run_config")
        return {"status": "disabled"}

    # Locate site content directory
    site_content = run_dir / "work" / "site" / "content"
    if not site_content.exists():
        logger.warning("[W10] No site/content directory found, skipping SEO optimization")
        return {"status": "skipped", "reason": "no content directory"}

    # Load required artifacts
    artifacts_dir = run_dir / "artifacts"
    product_facts = _load_artifact(artifacts_dir, "product_facts.json")
    page_plan = _load_artifact(artifacts_dir, "page_plan.json")
    page_plan_path = artifacts_dir / "page_plan.json"

    # Stage 4: SEO slug refinement for kb + blog sections (cached PyTrends + LLM)
    if run_config.get("seo_enabled", False) if isinstance(run_config, dict) else False:
        try:
            drafts_dir = run_dir / "work" / "drafts"
            page_plan = _refine_slugs_for_sections(
                page_plan, run_dir, run_config, drafts_dir
            )
            # Write updated page_plan.json atomically
            _tmp = page_plan_path.with_suffix(".tmp")
            _tmp.write_text(json.dumps(page_plan, indent=2), encoding="utf-8")
            _tmp.replace(page_plan_path)
            logger.info("w6_page_plan_updated_with_seo_slugs")
        except Exception as _slug_refine_err:
            logger.warning("w6_slug_refinement_failed error=%s", _slug_refine_err)

    # Initialize cache
    cache_path = run_dir / "work" / "seo_cache.json"
    cache = SEOCache(cache_path)

    # Phase 1: Keyword research (cached)
    product_name = product_facts.get("product_name", "Product")
    product_family = product_facts.get("product_family", "")
    platform = run_config.get("target_platform", "")
    claims = product_facts.get("claims", [])
    offline = run_config.get("offline_mode", False)

    keywords_data = cache.get_or_compute(
        f"research:{product_family}:{platform}",
        lambda: research_keywords(
            product_name, product_family, platform, claims,
            cache=cache, offline=offline,
        ),
        ttl=3600,
    )

    logger.info(
        "[W10] Keyword research complete",
        primary=len(keywords_data.get("primary_keywords", [])),
        long_tail=len(keywords_data.get("long_tail", [])),
    )

    # Phase 2 & 3: Process each .md file
    md_files = sorted(site_content.rglob("*.md"))
    pages_optimized = 0
    report: Dict[str, Any] = {
        "total_files": len(md_files),
        "optimized": [],
        "skipped": [],
        "keyword_stats": {},
    }

    # Build page lookup from page_plan
    page_lookup: Dict[str, Dict[str, Any]] = {}
    for page in page_plan.get("pages", []):
        page_lookup[page.get("slug", "")] = page

    # TC-2403: Parallel per-page SEO optimization. Pages are independent (shared
    # keywords_data and page_lookup are read-only). max_parallel_pages from run_config.
    max_parallel = min(max(run_config.get("max_parallel_pages", 4), 1), 16)

    def _optimize_one_page(md_file: Path):
        """Optimize a single page. Returns (slug, changed, error_name)."""
        try:
            content = md_file.read_text(encoding="utf-8")
            original_content = content

            slug = md_file.stem
            if slug == "_index":
                slug = "index"
            page = page_lookup.get(slug, {"slug": slug})
            section = _detect_section(md_file, site_content)

            page_keywords = extract_keywords(content)
            content_keywords = extract_keywords_from_content(content)
            existing_keywords = list(dict.fromkeys(page_keywords + content_keywords))

            research_page_kw = keywords_data.get("per_page", {}).get(slug, [])
            merged_keywords = _merge_keywords(
                existing_keywords, research_page_kw,
                keywords_data.get("primary_keywords", [])
            )
            all_keywords = list(dict.fromkeys(existing_keywords + merged_keywords))[:15]

            content = inject_keywords_naturally(content, all_keywords[:5])
            content = inject_kw_naturally(content, all_keywords, max_density=0.015)
            content = optimize_seo_metadata(
                content, page, all_keywords,
                product_name, platform,
                section=section, family=product_family,
            )

            meta = {
                "seoTitle": _get_seo_field(content, "seoTitle"),
                "description": _get_seo_field(content, "description"),
                "title": page.get("title", ""),
            }
            meta = enforce_seo_metadata_quality(meta, content, title=page.get("title", ""))
            if meta.get("seoTitle"):
                content = _update_seo_field(content, "seoTitle", meta["seoTitle"])
            if meta.get("description"):
                content = _update_seo_field(content, "description", meta["description"])

            changed = content != original_content
            if changed:
                md_file.write_text(content, encoding="utf-8")
                logger.info("[W10] Optimized page", file=md_file.name, keywords=len(merged_keywords))
            return slug, changed, None
        except Exception as e:
            logger.warning("[W10] Failed to optimize page", file=md_file.name, error=str(e))
            return str(md_file.name), False, e

    if max_parallel > 1 and len(md_files) > 1:
        n_workers = min(len(md_files), max_parallel)
        with ThreadPoolExecutor(max_workers=n_workers, thread_name_prefix="seo_page") as pool:
            futures = {pool.submit(_optimize_one_page, f): f for f in md_files}
            for fut in as_completed(futures):
                slug, changed, err = fut.result()
                if err is not None:
                    report["skipped"].append(slug)
                elif changed:
                    pages_optimized += 1
                    report["optimized"].append(slug)
                else:
                    report["skipped"].append(slug)
    else:
        for md_file in md_files:
            slug, changed, err = _optimize_one_page(md_file)
            if err is not None:
                report["skipped"].append(slug)
            elif changed:
                pages_optimized += 1
                report["optimized"].append(slug)
            else:
                report["skipped"].append(slug)

    report["keyword_stats"] = {
        "primary": keywords_data.get("primary_keywords", []),
        "long_tail_count": len(keywords_data.get("long_tail", [])),
        "pages_with_assignments": len(keywords_data.get("per_page", {})),
    }

    # Save report
    report_path = run_dir / "work" / "seo_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    logger.info(
        "[W10] SEO optimization complete",
        optimized=pages_optimized,
        total=len(md_files),
    )
    return {"status": "ok", "pages_optimized": pages_optimized, "report": report}


def _load_artifact(artifacts_dir: Path, artifact_name: str) -> Dict[str, Any]:
    """Load JSON artifact from artifacts directory.

    Args:
        artifacts_dir: Path to artifacts directory
        artifact_name: Artifact filename (e.g., product_facts.json)

    Returns:
        Parsed JSON artifact

    Raises:
        SEOOptimizerArtifactMissingError: If artifact not found
    """
    artifact_path = artifacts_dir / artifact_name
    if not artifact_path.exists():
        raise SEOOptimizerArtifactMissingError(
            f"Required artifact not found: {artifact_path}"
        )
    return json.loads(artifact_path.read_text(encoding="utf-8"))


def _detect_section(md_file: Path, site_content: Path) -> str:
    """Detect section from file path (e.g., docs.aspose.org -> docs)."""
    rel = md_file.relative_to(site_content)
    parts = rel.parts
    if parts:
        first_dir = parts[0]
        section_map = {
            "docs.aspose.org": "docs",
            "reference.aspose.org": "reference",
            "kb.aspose.org": "kb",
            "blog.aspose.org": "blog",
            "products.aspose.org": "products",
        }
        return section_map.get(first_dir, "docs")
    return "docs"


def _merge_keywords(
    extracted: List[str], page_specific: List[str], global_primary: List[str]
) -> List[str]:
    """Merge keywords from multiple sources, deduplicated."""
    seen: set[str] = set()
    result: List[str] = []
    for kw_list in [page_specific, extracted, global_primary]:
        for kw in kw_list:
            normalized = kw.lower().strip()
            if normalized and normalized not in seen:
                seen.add(normalized)
                result.append(kw)
    return result[:8]


def _get_seo_field(content: str, field: str) -> str:
    """Extract a frontmatter field value as plain string (strips quotes).

    TC-2395: Used to read seoTitle/description for quality enforcement.
    """
    import re as _re
    match = _re.search(
        rf'^{_re.escape(field)}:\s*"?([^"\n]*)"?\s*$', content, _re.MULTILINE
    )
    return match.group(1).strip() if match else ""


def _update_seo_field(content: str, field: str, value: str) -> str:
    """Update an existing frontmatter field with a new quoted value.

    TC-2395: Writes back quality-enforced metadata values.
    Only updates if the field already exists in frontmatter.
    """
    import re as _re
    pattern = rf'^({_re.escape(field)}:)\s*.*$'
    replacement = rf'\1 "{value}"'
    return _re.sub(pattern, replacement, content, count=1, flags=_re.MULTILINE)


import re as _re

_SEO_SLUG_SECTIONS = {"kb", "blog"}


def _is_valid_slug(slug: str) -> bool:
    """Slug must be non-empty, <=40 chars, only [a-z0-9-]."""
    return (
        bool(slug)
        and len(slug) <= 40
        and bool(_re.match(r'^[a-z0-9][a-z0-9-]*[a-z0-9]$', slug))
    )


def _generate_seo_slug_via_llm(
    title: str,
    current_slug: str,
    trend_keywords: list,
    family: str,
    platform: str,
    llm_client: Any,
) -> Optional[str]:
    """One LLM call -> SEO-optimized slug. Returns None on failure."""
    trends_str = ", ".join(trend_keywords) if trend_keywords else "(none available)"
    prompt = (
        f"Generate an SEO-optimized URL slug for a technical article.\n\n"
        f"Article title: {title}\n"
        f"Current slug: {current_slug}\n"
        f"Trending keywords (from Google Trends): {trends_str}\n"
        f"Product family: {family}, Platform: {platform}\n\n"
        f"Rules:\n"
        f"- Output ONLY the slug (lowercase, hyphens, letters/digits only)\n"
        f"- Maximum 40 characters\n"
        f"- Must be meaningful and search-friendly\n"
        f"- Incorporate trending keywords if they add value\n"
        f"- No 'how-to-' prefix unless truly necessary\n\n"
        f"Output the slug only, nothing else:"
    )
    try:
        response = llm_client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            call_id="seo_slug_refinement",
            temperature=0.1,
            max_tokens=20,
        )
        raw = response.get("content", "").strip().split("\n")[0].strip()
        return raw if _is_valid_slug(raw) else None
    except Exception:
        return None


def _refine_slugs_for_sections(
    page_plan: dict,
    run_dir: Path,
    run_config: dict,
    drafts_dir: Optional[Path],
) -> dict:
    """Phase 2 slug refinement via PyTrends + LLM (cached).

    Only processes kb and blog sections (structural sections unchanged).
    Updates page_plan in memory; caller writes updated page_plan.json.
    Also renames draft files to match new slugs.

    Returns: updated page_plan dict with slug_changes log.
    """
    import logging as _logging
    _logger = _logging.getLogger(__name__)

    family = run_config.get("family", "") if isinstance(run_config, dict) else ""
    platform = run_config.get("target_platform", "python") if isinstance(run_config, dict) else "python"
    slug_changes = []

    from launch.workers.w6_seo_optimizer.keyword_utils import SlugRefinementCache
    cache = SlugRefinementCache(run_dir / "work" / "slug_cache.json")

    # Build LLM client from run_config if possible
    llm_client = None
    if isinstance(run_config, dict) and run_config.get("llm", {}).get("api_base_url"):
        try:
            from launch.clients.llm_provider import create_llm_client_from_config
            llm_client = create_llm_client_from_config(run_config=run_config, run_dir=run_dir)
        except Exception as _e:
            _logger.warning("w6_slug_refine_llm_client_unavailable error=%s", _e)

    # Try to get PyTrends keywords
    trends_available = False
    try:
        from launch.workers.w6_seo_optimizer.keyword_research import _fetch_trends_keywords
        trends_available = True
    except (ImportError, Exception):
        _logger.warning("w6_slug_refine_pytrends_unavailable")

    for page in page_plan.get("pages", []):
        if page.get("section") not in _SEO_SLUG_SECTIONS:
            continue

        current_slug = page.get("slug", "")
        title = page.get("title", "") or current_slug
        if not current_slug or not title:
            continue

        # Step 1: Get PyTrends related keywords (cached 1h)
        trend_keywords: List[str] = []
        if trends_available:
            trends_query = f"{family} {platform} {current_slug.replace('-', ' ')}"
            pt_cache_key = cache.pytrends_key(trends_query)
            cached_trends = cache.get(pt_cache_key, SlugRefinementCache._PYTRENDS_TTL)
            if cached_trends is not None:
                trend_keywords = cached_trends
            else:
                try:
                    trend_keywords = _fetch_trends_keywords(
                        f"{family} {platform}", family=family, platform=platform
                    )[:5]
                    cache.set(pt_cache_key, trend_keywords)
                    _logger.info(
                        "w6_pytrends_fetched query=%s keywords=%s",
                        trends_query, trend_keywords,
                    )
                except Exception as e:
                    _logger.warning("w6_pytrends_fail query=%s error=%s", trends_query, e)

        # Step 2: Gemini/LLM slug optimization (cached 24h)
        seo_slug = None
        if llm_client is not None:
            gm_cache_key = cache.gemini_key(title, trend_keywords)
            seo_slug = cache.get(gm_cache_key, SlugRefinementCache._GEMINI_TTL)
            if seo_slug is None:
                seo_slug = _generate_seo_slug_via_llm(
                    title, current_slug, trend_keywords, family, platform, llm_client
                )
                if seo_slug:
                    cache.set(gm_cache_key, seo_slug)
                    _logger.info(
                        "w6_seo_slug_generated original=%s seo=%s",
                        current_slug, seo_slug,
                    )

        # Step 3: Validate and apply (only if changed and valid)
        if seo_slug and seo_slug != current_slug and _is_valid_slug(seo_slug):
            # Try to rename draft file
            if drafts_dir is not None:
                old_draft = Path(drafts_dir) / f"{page.get('section', '')}/{current_slug}/index.md"
                new_draft = Path(drafts_dir) / f"{page.get('section', '')}/{seo_slug}/index.md"
                if old_draft.exists():
                    try:
                        new_draft.parent.mkdir(parents=True, exist_ok=True)
                        old_draft.rename(new_draft)
                        _logger.info("w6_draft_renamed %s -> %s", old_draft, new_draft)
                    except Exception as e:
                        _logger.warning("w6_draft_rename_failed error=%s", e)

            # Update page spec (atomic update via dict mutation)
            old_output_path = page.get("output_path", "")
            old_url_path = page.get("url_path", "")
            page["output_path"] = old_output_path.replace(f"/{current_slug}/", f"/{seo_slug}/")
            page["url_path"] = old_url_path.replace(f"/{current_slug}/", f"/{seo_slug}/")
            slug_changes.append({
                "section": page.get("section", ""),
                "old": current_slug,
                "new": seo_slug,
                "source": "pytrends+llm" if trend_keywords else "llm",
            })
            page["slug"] = seo_slug

    page_plan["slug_changes"] = slug_changes
    _logger.info("w6_slug_refinement_complete changed=%d", len(slug_changes))
    return page_plan
