"""5-source keyword research engine for SEO.

Sources:
1. Google Trends (PyTrends) — trending related queries
2. Google Suggest — autocomplete suggestions
3. Gemini LLM — AI-expanded keyword analysis
4. Claim-derived — frequency analysis on product claims
5. Developer search patterns — heuristic templates

All external calls are cached and rate-limited.  When external APIs
are unavailable, the engine degrades gracefully to local-only sources.

TC-3808: Created for v2 SEO module.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from launcher.models.base import LauncherBaseModel
from launcher.shared.api_rate_limiter import (
    create_suggest_limiter,
    create_trends_limiter,
)
from launcher.shared.seo_cache import (
    SEOCache,
    TTL_EXTERNAL_API,
    TTL_LOCAL,
    build_cache_dir,
    make_cache_key,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Output model
# ---------------------------------------------------------------------------


class KeywordResearchBundle(LauncherBaseModel):
    """Keyword research results cached per family/platform."""

    primary_keywords: list[str] = []
    long_tail: list[str] = []
    per_page: dict[str, list[str]] = {}
    sources: dict[str, list[str]] = {}
    gemini_available: bool = False
    cached_at: str = ""
    cache_version: int = 1


# ---------------------------------------------------------------------------
# Stop words for keyword extraction
# ---------------------------------------------------------------------------

_STOP_WORDS: frozenset[str] = frozenset({
    "a", "an", "the", "and", "but", "or", "for", "in", "on", "to",
    "of", "is", "it", "by", "at", "as", "be", "if", "do", "no",
    "this", "that", "with", "from", "have", "has", "had", "will",
    "been", "they", "are", "was", "were", "not", "can", "you",
    "your", "its", "our", "we", "them", "their", "all", "each",
    "which", "when", "where", "how", "what", "who", "whom",
    "also", "just", "more", "most", "very", "only", "such",
    "than", "then", "some", "any", "other", "about", "into",
    "over", "after", "before", "between", "under", "through",
})

# High-intent verbs for developer search pattern generation.
_USE_CASE_VERBS: list[str] = [
    "convert", "load", "save", "export", "import", "create",
    "generate", "parse", "render", "extract", "merge", "split",
    "read", "write", "open", "transform",
]

# Page-slug to keyword-match-terms mapping for per-page assignment.
_PAGE_KEYWORD_MAP: dict[str, list[str]] = {
    "getting-started": ["install", "getting started", "setup", "quickstart"],
    "installation": ["install", "pip", "setup", "requirements"],
    "developer-guide": ["example", "tutorial", "how to", "guide"],
    "faq": ["faq", "question", "error", "problem", "issue"],
    "troubleshooting": ["error", "fix", "problem", "issue", "troubleshoot"],
    "api-overview": ["api", "reference", "class", "method", "module"],
    "best-practices": ["best practice", "performance", "optimization"],
    "tutorial": ["tutorial", "step by step", "example", "learn"],
}

# Google Trends query terms per product family.
# Niche queries like "cells python" return zero results — use broader
# domain-specific terms that Google Trends actually indexes.
_FAMILY_TREND_TERMS: dict[str, list[str]] = {
    "cells": ["python excel", "openpyxl", "python spreadsheet"],
    "words": ["python docx", "python word document"],
    "pdf": ["python pdf", "pdf library python"],
    "slides": ["python pptx", "python powerpoint"],
    "email": ["python email", "python imap"],
    "imaging": ["python image processing", "pillow python"],
    "barcode": ["python barcode", "python qr code"],
}


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def research_keywords(
    product_name: str,
    family: str,
    platform: str,
    claims: list[Any],
    cache_root: Path,
    offline: bool = False,
    gemini_api_key: str = "",
) -> KeywordResearchBundle:
    """Run keyword research from up to 5 sources.

    Parameters
    ----------
    product_name:
        Product display name (e.g. ``"Aspose.Cells FOSS for Python"``).
    family:
        Product family (e.g. ``"cells"``).
    platform:
        Platform (e.g. ``"python"``).
    claims:
        List of claim objects or dicts with ``text`` or ``claim_text``.
    cache_root:
        Root directory for SEO cache (e.g. ``<project>/.seo_cache``).
    offline:
        If True, skip all external API calls and use cache + local only.
    gemini_api_key:
        Gemini API key.  Empty string disables Gemini source.

    Returns
    -------
    KeywordResearchBundle
        Merged, deduplicated keyword research results.
    """
    cache_dir = build_cache_dir(cache_root, family, platform)
    cache = SEOCache(cache_dir, default_ttl=TTL_EXTERNAL_API)

    sources: dict[str, list[str]] = {}

    # --- Source 1: Google Trends ---
    if not offline:
        trends_kw = _fetch_trends_keywords(family, platform, cache)
        if trends_kw:
            sources["trends"] = trends_kw
            logger.info("[KeywordResearch] Trends: %d keywords", len(trends_kw))

    # --- Source 2: Google Suggest ---
    if not offline:
        suggest_kw = _fetch_suggest_keywords(
            product_name, family, platform, cache,
        )
        if suggest_kw:
            sources["suggest"] = suggest_kw
            logger.info("[KeywordResearch] Suggest: %d keywords", len(suggest_kw))

    # --- Source 3: Gemini ---
    gemini_available = False
    if not offline and gemini_api_key:
        from launcher.clients.gemini_client import GeminiSEOClient

        gemini = GeminiSEOClient(api_key=gemini_api_key, cache=cache)
        existing = _flatten_sources(sources)
        gemini_kw = gemini.analyze_keywords(family, platform, product_name, existing)
        if gemini_kw:
            sources["gemini"] = gemini_kw
            gemini_available = True
            logger.info("[KeywordResearch] Gemini: %d keywords", len(gemini_kw))

    # --- Source 4: Claim-derived keywords ---
    claim_texts = _extract_claim_texts(claims)
    claims_hash = hashlib.sha256(
        "\n".join(sorted(claim_texts)).encode("utf-8"),
    ).hexdigest()[:16]
    claim_kw = cache.get_or_compute(
        "claim_keywords",
        make_cache_key(family, platform, "claims", claims_hash),
        lambda: _extract_claim_keywords(claim_texts),
        ttl=TTL_LOCAL,
    )
    if claim_kw:
        sources["claims"] = claim_kw
        logger.info("[KeywordResearch] Claims: %d keywords", len(claim_kw))

    # --- Source 5: Developer search patterns ---
    short_name = product_name.split(" for ")[0].split()[-1] if product_name else family
    patterns = cache.get_or_compute(
        "search_patterns",
        make_cache_key(family, platform, "patterns"),
        lambda: _generate_search_patterns(
            short_name, family, platform, claim_texts,
        ),
        ttl=TTL_LOCAL,
    )
    if patterns:
        sources["patterns"] = patterns
        logger.info("[KeywordResearch] Patterns: %d keywords", len(patterns))

    # --- Merge ---
    all_keywords = _flatten_sources(sources)
    primary = _deduplicate(all_keywords)[:8]
    long_tail = [kw for kw in _deduplicate(all_keywords) if len(kw.split()) >= 3][:15]

    # Per-page assignment.
    per_page = _assign_per_page_keywords(primary + long_tail, family, platform)

    import datetime

    bundle = KeywordResearchBundle(
        primary_keywords=primary,
        long_tail=long_tail,
        per_page=per_page,
        sources={k: v[:20] for k, v in sources.items()},
        gemini_available=gemini_available,
        cached_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    )

    logger.info(
        "[KeywordResearch] Complete: %d primary, %d long-tail, %d pages, "
        "sources=%s, gemini=%s",
        len(primary), len(long_tail), len(per_page),
        list(sources.keys()), gemini_available,
    )
    return bundle


# ---------------------------------------------------------------------------
# Source 1: Google Trends
# ---------------------------------------------------------------------------


def _fetch_trends_keywords(
    family: str,
    platform: str,
    cache: SEOCache,
) -> list[str]:
    """Fetch trending related queries via PyTrends.

    Returns empty list if pytrends is not installed or API fails.
    """
    cache_key = make_cache_key(family, platform, "trends")
    cached = cache.get("trends", cache_key)
    if cached is not None:
        return cached

    try:
        from pytrends.request import TrendReq  # type: ignore[import-untyped]
    except ImportError:
        logger.warning(
            "[KeywordResearch] pytrends not installed — skipping Google Trends. "
            "Install with: pip install pytrends",
        )
        return []

    limiter = create_trends_limiter()
    keywords: list[str] = []

    trend_terms = _FAMILY_TREND_TERMS.get(
        family,
        [f"{platform} {family}", f"{platform} {family} library"],
    )
    queries = trend_terms[:3]

    # Reuse one TrendReq session across all queries (SEO-13).
    pytrends = TrendReq(hl="en-US", tz=360)

    for query in queries:
        limiter.acquire()
        try:
            pytrends.build_payload([query], timeframe="today 3-m")
            related = pytrends.related_queries()

            if query in related and related[query].get("top") is not None:
                df = related[query]["top"]
                for _, row in df.iterrows():
                    kw = str(row.get("query", "")).strip()
                    if kw and len(kw) > 3:
                        keywords.append(kw)

            limiter.record_success()
        except Exception as exc:
            logger.warning("[KeywordResearch] Trends query failed: %s", exc)
            limiter.record_error(429)  # Assume rate limit.

    result = _deduplicate(keywords)[:10]
    if result:
        cache.set("trends", cache_key, result)
    else:
        logger.info("[KeywordResearch] Trends: no related queries found for %s/%s", family, platform)
    return result


# ---------------------------------------------------------------------------
# Source 2: Google Suggest
# ---------------------------------------------------------------------------


def _fetch_suggest_keywords(
    product_name: str,
    family: str,
    platform: str,
    cache: SEOCache,
) -> list[str]:
    """Fetch Google autocomplete suggestions."""
    cache_key = make_cache_key(family, platform, "suggest")
    cached = cache.get("suggest", cache_key)
    if cached is not None:
        return cached

    limiter = create_suggest_limiter()
    keywords: list[str] = []

    short_name = product_name.split(" for ")[0].split()[-1] if product_name else family
    queries = [
        f"{family} {platform}",
        f"python {family}",
        f"how to {family} {platform}",
        f"{short_name} {platform}",
    ]

    for query in queries:
        limiter.acquire()
        try:
            encoded = urllib.parse.quote_plus(query)
            url = (
                f"https://suggestqueries.google.com/complete/search"
                f"?client=firefox&q={encoded}"
            )
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            if isinstance(data, list) and len(data) >= 2:
                suggestions = data[1]
                if isinstance(suggestions, list):
                    for s in suggestions:
                        s_str = str(s).strip()
                        if s_str and len(s_str) > 3:
                            keywords.append(s_str)

            limiter.record_success()
        except Exception as exc:
            logger.warning("[KeywordResearch] Suggest query failed: %s", exc)

    result = _deduplicate(keywords)[:10]
    if result:
        cache.set("suggest", cache_key, result)
    return result


# ---------------------------------------------------------------------------
# Source 4: Claim-derived keywords
# ---------------------------------------------------------------------------


def _extract_claim_texts(claims: list[Any]) -> list[str]:
    """Extract text from claim objects or dicts."""
    texts: list[str] = []
    for c in claims:
        if hasattr(c, "text"):
            texts.append(c.text)
        elif isinstance(c, dict):
            texts.append(c.get("text", c.get("claim_text", "")))
    return [t for t in texts if t]


def _extract_claim_keywords(claim_texts: list[str]) -> list[str]:
    """Frequency analysis on claim texts to extract significant keywords."""
    word_freq: dict[str, int] = {}
    for text in claim_texts:
        words = re.findall(r"\b[a-z]{3,}\b", text.lower())
        for w in words:
            if w not in _STOP_WORDS:
                word_freq[w] = word_freq.get(w, 0) + 1

    # Sort by frequency descending.
    sorted_words = sorted(word_freq.items(), key=lambda x: (-x[1], x[0]))
    return [w for w, _ in sorted_words[:20]]


# ---------------------------------------------------------------------------
# Source 5: Developer search patterns
# ---------------------------------------------------------------------------


def _generate_search_patterns(
    short_name: str,
    family: str,
    platform: str,
    claim_texts: list[str],
) -> list[str]:
    """Generate heuristic developer search patterns."""
    patterns: list[str] = [
        f"how to install {short_name} {platform}",
        f"{short_name} {platform} tutorial",
        f"{short_name} {platform} example",
        f"{short_name} {platform} getting started",
        f"python {family} library",
        f"{family} {platform} documentation",
        f"{short_name} {platform} api reference",
        f"best {family} library for {platform}",
    ]

    # Extract use-case verbs from claims.
    combined = " ".join(claim_texts).lower()
    for verb in _USE_CASE_VERBS:
        if verb in combined:
            patterns.append(f"how to {verb} {family} files {platform}")

    return _deduplicate(patterns)


# ---------------------------------------------------------------------------
# Per-page keyword assignment
# ---------------------------------------------------------------------------


def _assign_per_page_keywords(
    all_keywords: list[str],
    family: str,
    platform: str,
) -> dict[str, list[str]]:
    """Map keywords to page slugs using heuristic matching."""
    per_page: dict[str, list[str]] = {}
    base_keywords = [family, platform]

    for slug, match_terms in _PAGE_KEYWORD_MAP.items():
        page_keywords = list(base_keywords)
        for kw in all_keywords:
            kw_lower = kw.lower()
            if any(term in kw_lower for term in match_terms):
                if kw not in page_keywords:
                    page_keywords.append(kw)
        per_page[slug] = page_keywords[:8]

    return per_page


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _flatten_sources(sources: dict[str, list[str]]) -> list[str]:
    """Flatten all source keyword lists into one list."""
    result: list[str] = []
    for keywords in sources.values():
        result.extend(keywords)
    return result


def _deduplicate(keywords: list[str]) -> list[str]:
    """Deduplicate keywords preserving order, case-insensitive."""
    seen: set[str] = set()
    result: list[str] = []
    for kw in keywords:
        key = kw.lower().strip()
        if key and key not in seen:
            seen.add(key)
            result.append(kw.strip())
    return result
