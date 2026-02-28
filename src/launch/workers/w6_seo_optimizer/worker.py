"""W6 SEO Optimizer Worker: Post-process final .md files for on-page SEO.

Pipeline position: After W5 (SectionWriter), before W7 (ContentReviewer).
Operates on the site/content directory produced by W5.

Phases:
1. Keyword Research -- Google Trends + Suggest + heuristic (cached)
2. Keyword Extraction & Injection -- density-controlled natural insertion
3. SEO Metadata -- frontmatter optimization (seoTitle, description, keywords, canonical)

Slug Contract (spec 45):
W4 is the sole owner of slug, output_path, and url_path. W6 DOES NOT rewrite slugs
by default. Set slug_rewrite_enabled: true in run_config to opt in to slug rewriting
(experimental; KB and Blog sections only).

TC-2205: W6 SEO Optimizer Worker
"""

from __future__ import annotations

import json
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional

from ...util.logging import get_logger
from .cache import SEOCache
from .keyword_research import research_keywords
from .keyword_optimizer import extract_keywords
from .seo_metadata import optimize_seo_metadata
from .keyword_utils import (
    extract_keywords_from_content,
    inject_keywords_naturally as inject_kw_naturally,
    enforce_seo_metadata_quality,
)

logger = get_logger()


class SEOOptimizerError(Exception):
    """Base exception for W6 SEO Optimizer errors."""
    pass


class SEOOptimizerArtifactMissingError(SEOOptimizerError):
    """Required artifact not found."""
    pass


def execute_seo_optimizer(
    run_dir: Path, run_config: Dict[str, Any]
) -> Dict[str, Any]:
    """W6 SEO Optimizer worker -- optimizes final .md files for on-page SEO.

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
        logger.info("[W6] SEO optimization disabled in run_config")
        return {"status": "disabled"}

    # Locate site content directory
    site_content = run_dir / "work" / "site" / "content"
    if not site_content.exists():
        logger.warning("[W6] No site/content directory found, skipping SEO optimization")
        return {"status": "skipped", "reason": "no content directory"}

    # Load required artifacts
    artifacts_dir = run_dir / "artifacts"
    product_facts = _load_artifact(artifacts_dir, "product_facts.json")
    page_plan = _load_artifact(artifacts_dir, "page_plan.json")

    # Stage 4: SEO slug refinement for kb + blog sections (cached PyTrends + LLM)
    # Advisory-only — W4 is the sole owner of slug/output_path/url_path (spec 45).
    # When slug_rewrite_enabled=true, suggestions are written to
    # work/seo_slug_suggestions.json but page_plan.json is NEVER modified.
    slug_rewrite_on = (
        isinstance(run_config, dict)
        and run_config.get("slug_rewrite_enabled", False)
    )
    if slug_rewrite_on:
        try:
            suggestions = _refine_slugs_for_sections(
                page_plan, run_dir, run_config,
            )
            # Write advisory suggestions atomically (never mutate page_plan.json)
            suggestions_path = run_dir / "work" / "seo_slug_suggestions.json"
            suggestions_path.parent.mkdir(parents=True, exist_ok=True)
            _payload = json.dumps(suggestions, indent=2).encode("utf-8")
            _fd, _tmp = tempfile.mkstemp(
                dir=str(suggestions_path.parent), suffix=".tmp"
            )
            try:
                os.write(_fd, _payload)
                os.close(_fd)
                os.replace(_tmp, str(suggestions_path))
            except BaseException:
                try:
                    os.close(_fd)
                except Exception:
                    pass
                try:
                    os.unlink(_tmp)
                except Exception:
                    pass
                raise
            logger.info(
                "w6_slug_suggestions_written count=%d", len(suggestions)
            )
        except Exception as _slug_refine_err:
            logger.warning("w6_slug_refinement_failed error=%s", _slug_refine_err)
    else:
        logger.debug("w6_slug_rewrite_disabled slug_rewrite_enabled=False")

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
        "[W6] Keyword research complete",
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

    # Observability counters (mutable container shared by closure)
    _injection_stats = {"desc_injected": 0, "canonical_updated": 0}

    def _optimize_one_page(md_file: Path):
        """Optimize a single page. Returns (slug, changed, error_name)."""
        try:
            content = md_file.read_text(encoding="utf-8")
            original_content = content

            # TC-3400: Use parent folder name for index.md/_index.md files
            # so that getting-started/index.md resolves to "getting-started"
            if md_file.name in ("index.md", "_index.md"):
                slug = md_file.parent.name
            else:
                slug = md_file.stem
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

            content = inject_kw_naturally(content, all_keywords, max_density=0.015)
            content = optimize_seo_metadata(
                content, page, all_keywords,
                product_name, platform,
                section=section, family=product_family,
                is_section_index=(md_file.name == "_index.md"),
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

            # Track injection events for observability (SR-04)
            import re as _re
            _desc_before = bool(_re.search(r'^description:', original_content, _re.MULTILINE))
            _desc_after = bool(_re.search(r'^description:', content, _re.MULTILINE))
            _canon_before = _get_seo_field(original_content, "canonical")
            _canon_after = _get_seo_field(content, "canonical")
            if not _desc_before and _desc_after:
                _injection_stats["desc_injected"] += 1
                logger.info("[W6] w6_description_injected slug=%s", slug)
            if _canon_before != _canon_after and _canon_after:
                _injection_stats["canonical_updated"] += 1
                logger.info("[W6] w6_canonical_updated slug=%s", slug)

            changed = content != original_content
            if changed:
                md_file.write_text(content, encoding="utf-8")
                logger.info("[W6] Optimized page", file=md_file.name, keywords=len(merged_keywords))
            return slug, changed, None
        except Exception as e:
            logger.warning("[W6] Failed to optimize page", file=md_file.name, error=str(e))
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
    report["description_injected_count"] = _injection_stats["desc_injected"]
    report["canonical_updated_count"] = _injection_stats["canonical_updated"]

    # Save report
    report_path = run_dir / "work" / "seo_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    logger.info(
        "[W6] SEO optimization complete",
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

# ---------------------------------------------------------------------------
# TC-2516: Registry-validated slug format checking
# ---------------------------------------------------------------------------

def _load_family_capabilities_w6(run_dir: Path) -> Optional[Dict[str, Any]]:
    """Load family_capabilities.json for W6 registry-based validation.

    TC-2516: Used by W6 to validate that format names referenced in
    refined slugs are evidenced in the registry.  Returns None when the
    artifact is absent or malformed (no-op fallback).
    """
    caps_path = run_dir / "artifacts" / "family_capabilities.json"
    try:
        if caps_path.exists():
            data = json.loads(caps_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                logger.debug("w6_family_capabilities_loaded path=%s", caps_path)
                return data
        return None
    except (json.JSONDecodeError, OSError):
        return None


def _validate_slug_formats(
    slug: str,
    family_capabilities: Optional[Dict[str, Any]],
) -> List[str]:
    """Validate that format tokens in a slug are evidenced in the registry.

    TC-2516: Extracts format-like tokens from the slug (sequences of 2-5
    uppercase-letter segments when lowered) and checks whether they appear
    in ``family_capabilities["supported_formats"]``.

    Returns list of warning strings (empty if all formats valid or no registry).
    """
    if not family_capabilities:
        return []
    supported = family_capabilities.get("supported_formats", [])
    if not supported:
        return []
    supported_lower = {str(f).lower() for f in supported}

    # Extract format-like tokens: 2-5 char segments that look like file format names
    # e.g., from "how-to-convert-fbx-to-obj" → ["fbx", "obj"]
    _format_pattern = _re.compile(r'\b([a-z]{2,5})\b')
    tokens = _format_pattern.findall(slug)

    # Common slug words that are NOT format names
    _slug_stopwords = {
        "how", "to", "and", "the", "for", "with", "from", "into", "load",
        "save", "open", "fix", "convert", "common", "errors", "python",
        "models", "files", "other", "optimize", "performance", "data",
    }

    warnings: List[str] = []
    for token in tokens:
        if token in _slug_stopwords:
            continue
        if token not in supported_lower:
            warnings.append(
                f"w6_slug_format_not_in_registry slug={slug} token={token}"
            )
    return warnings


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
) -> Optional[List[Dict[str, str]]]:
    """TC-2609: One LLM call -> schema-validated SEO slug candidates.

    Returns list of ``{"slug": ..., "rationale": ...}`` dicts on success,
    or None on failure / schema violation.
    """
    trends_str = ", ".join(trend_keywords) if trend_keywords else "(none available)"
    prompt = (
        f"Generate 1-3 SEO-optimized URL slug candidates for a technical article.\n\n"
        f"Article title: {title}\n"
        f"Current slug: {current_slug}\n"
        f"Trending keywords (from Google Trends): {trends_str}\n"
        f"Product family: {family}, Platform: {platform}\n\n"
        f"Rules:\n"
        f"- Each slug: lowercase ASCII, hyphens only, 2-60 characters\n"
        f"- Pattern: ^[a-z0-9][a-z0-9-]*[a-z0-9]$\n"
        f"- Must be meaningful and search-friendly\n"
        f"- Incorporate trending keywords if they add value\n\n"
        f"Respond with JSON only:\n"
        f'{{"candidates": [{{"slug": "...", "rationale": "..."}}]}}'
    )
    try:
        response = llm_client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            call_id="seo_slug_refinement",
            temperature=0.1,
            max_tokens=200,
        )
        raw = response.get("content", "").strip()
        parsed = json.loads(raw)
        candidates = parsed.get("candidates", [])
        if not isinstance(candidates, list) or len(candidates) < 1:
            return None
        # TC-2609: Schema validation — each candidate must have slug + rationale
        valid = []
        for c in candidates[:3]:
            if not isinstance(c, dict):
                continue
            slug = c.get("slug", "")
            rationale = c.get("rationale", "")
            if not isinstance(slug, str) or not isinstance(rationale, str):
                continue
            if not _re.match(r'^[a-z0-9][a-z0-9-]*[a-z0-9]$', slug):
                continue
            if len(slug) > 60:
                continue
            valid.append({"slug": slug, "rationale": rationale[:200]})
        return valid if valid else None
    except (json.JSONDecodeError, Exception):
        return None


def _pick_best_candidate(
    candidates: List[Dict[str, str]],
    current_slug: str,
    existing_slugs: set,
    family_capabilities: Optional[Dict[str, Any]],
) -> Optional[str]:
    """TC-2610: Deterministic validation to pick the best slug candidate.

    Validation rules (in order of priority):
    1. Must not collide with existing slugs in the section
    2. Must pass format-token validation against registry
    3. Must differ from current slug (otherwise no benefit)
    4. First valid candidate wins (LLM ordered by preference)

    Returns the best valid slug, or None if all candidates fail.
    """
    for c in candidates:
        slug = c["slug"]
        if slug == current_slug:
            continue
        if slug in existing_slugs:
            continue
        # Format-token validation
        format_warnings = _validate_slug_formats(slug, family_capabilities)
        if format_warnings:
            logger.debug("w6_candidate_rejected_format slug=%s warnings=%s", slug, format_warnings)
            continue
        return slug
    return None


def _refine_slugs_for_sections(
    page_plan: dict,
    run_dir: Path,
    run_config: dict,
) -> List[Dict[str, Any]]:
    """Advisory slug refinement via PyTrends + LLM (cached).

    TC-3400: Advisory-only — returns a list of slug suggestions WITHOUT
    mutating page_plan or renaming any files.  Caller writes the
    suggestions to ``work/seo_slug_suggestions.json``.

    Only processes kb and blog sections (structural sections unchanged).

    Returns: list of suggestion dicts::

        [{"section", "old_slug", "suggested_slug", "rationale", "warnings"}]
    """
    import logging as _logging
    _logger = _logging.getLogger(__name__)

    family = run_config.get("family", "") if isinstance(run_config, dict) else ""
    platform = run_config.get("target_platform", "python") if isinstance(run_config, dict) else "python"
    suggestions: List[Dict[str, Any]] = []

    # TC-2516: Load family capabilities for format validation on refined slugs
    _family_caps = _load_family_capabilities_w6(run_dir)

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

    # TC-2610: Build per-section slug sets for collision detection
    section_slugs: Dict[str, set] = {}
    for page in page_plan.get("pages", []):
        sec = page.get("section", "")
        section_slugs.setdefault(sec, set()).add(page.get("slug", ""))

    for page in page_plan.get("pages", []):
        if page.get("section") not in _SEO_SLUG_SECTIONS:
            continue

        current_slug = page.get("slug", "")
        title = page.get("title", "") or current_slug
        if not current_slug or not title:
            continue

        sec = page.get("section", "")

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

        # Step 2: LLM slug candidates (schema-validated, cached 24h) — TC-2609
        seo_slug = None
        rationale = ""
        if llm_client is not None:
            gm_cache_key = cache.gemini_key(title, trend_keywords)
            _cached_slug = cache.get(gm_cache_key, SlugRefinementCache._GEMINI_TTL)
            if _cached_slug is not None and isinstance(_cached_slug, str):
                seo_slug = _cached_slug if _is_valid_slug(_cached_slug) else None
                rationale = "cached"
            elif _cached_slug is None:
                candidates = _generate_seo_slug_via_llm(
                    title, current_slug, trend_keywords, family, platform, llm_client
                )
                if candidates:
                    existing = section_slugs.get(sec, set())
                    seo_slug = _pick_best_candidate(
                        candidates, current_slug, existing, _family_caps,
                    )
                    if seo_slug:
                        # Find rationale for the picked slug
                        for c in candidates:
                            if c["slug"] == seo_slug:
                                rationale = c.get("rationale", "")
                                break
                        cache.set(gm_cache_key, seo_slug)
                        _logger.info(
                            "w6_seo_slug_generated original=%s seo=%s candidates=%d",
                            current_slug, seo_slug, len(candidates),
                        )
                    else:
                        _logger.info(
                            "w6_seo_slug_all_rejected original=%s candidates=%d",
                            current_slug, len(candidates),
                        )

        # Step 3: Record advisory suggestion (never mutate page_plan)
        if seo_slug and seo_slug != current_slug and _is_valid_slug(seo_slug):
            format_warnings = _validate_slug_formats(seo_slug, _family_caps)
            suggestions.append({
                "section": sec,
                "old_slug": current_slug,
                "suggested_slug": seo_slug,
                "rationale": rationale,
                "source": "pytrends+llm" if trend_keywords else "llm",
                "warnings": format_warnings,
            })
            # Update section slug set for subsequent collision checks
            section_slugs.setdefault(sec, set()).add(seo_slug)

    _logger.info("w6_slug_suggestions_complete count=%d", len(suggestions))
    return suggestions
