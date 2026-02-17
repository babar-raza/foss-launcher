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
from pathlib import Path
from typing import Any, Dict, List

from ...util.logging import get_logger
from .cache import SEOCache
from .keyword_research import research_keywords
from .keyword_optimizer import extract_keywords, inject_keywords_naturally
from .seo_metadata import optimize_seo_metadata

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

    for md_file in md_files:
        try:
            content = md_file.read_text(encoding="utf-8")
            original_content = content

            # Determine page slug from file path
            slug = md_file.stem
            if slug == "_index":
                slug = "index"
            page = page_lookup.get(slug, {"slug": slug})

            # Determine section from path
            section = _detect_section(md_file, site_content)

            # Phase 2: Keyword extraction & injection
            page_keywords = extract_keywords(content)

            # Merge with research keywords for this page slug
            research_page_kw = keywords_data.get("per_page", {}).get(slug, [])
            merged_keywords = _merge_keywords(
                page_keywords, research_page_kw,
                keywords_data.get("primary_keywords", [])
            )

            content = inject_keywords_naturally(content, merged_keywords[:5])

            # Phase 3: SEO metadata optimization
            content = optimize_seo_metadata(
                content, page, merged_keywords,
                product_name, platform,
                section=section, family=product_family,
            )

            # Write back if changed
            if content != original_content:
                md_file.write_text(content, encoding="utf-8")
                pages_optimized += 1
                report["optimized"].append(slug)
                logger.info(
                    "[W10] Optimized page",
                    file=md_file.name,
                    keywords=len(merged_keywords),
                )
            else:
                report["skipped"].append(slug)

        except Exception as e:
            logger.warning(
                "[W10] Failed to optimize page",
                file=md_file.name,
                error=str(e),
            )
            report["skipped"].append(str(md_file.name))

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
