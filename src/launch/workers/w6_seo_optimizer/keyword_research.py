"""Keyword research using Google Trends, Suggest API, and heuristics."""

from __future__ import annotations

import json
import re
import time
import urllib.request
import urllib.parse
from typing import Any, Dict, List, Optional

from ...util.logging import get_logger

logger = get_logger()

# Stop words for keyword extraction
STOP_WORDS = frozenset({
    "the", "and", "for", "are", "but", "not", "you", "all", "can", "had",
    "her", "was", "one", "our", "out", "has", "his", "how", "its", "may",
    "new", "now", "old", "see", "way", "who", "did", "get", "let", "say",
    "she", "too", "use", "with", "this", "that", "from", "they", "been",
    "have", "many", "some", "them", "than", "each", "make", "like", "will",
    "into", "over", "such", "your", "also", "most", "when", "what", "here",
    "just", "more", "about", "which", "their", "there", "would", "other",
    "could", "after", "these", "should", "being", "using", "where", "does",
    "very", "every", "between", "through", "because", "while", "before",
    "during", "under", "above", "below", "both", "same", "well", "only",
})


def research_keywords(
    product_name: str,
    product_family: str,
    platform: str,
    claims: List[Dict[str, Any]],
    *,
    cache: Optional[Any] = None,
    offline: bool = False,
) -> Dict[str, Any]:
    """Research SEO keywords from multiple sources.

    Args:
        product_name: e.g., "Aspose.3D for Python via .NET"
        product_family: e.g., "3d"
        platform: e.g., "python"
        claims: Product claims list
        cache: Optional SEOCache instance
        offline: If True, skip network calls

    Returns:
        {
            "primary_keywords": [...],
            "long_tail": [...],
            "per_page": {"slug": [...], ...},
            "sources": {"trends": [...], "suggest": [...], "claims": [...], "patterns": [...]},
        }
    """
    result: Dict[str, Any] = {
        "primary_keywords": [],
        "long_tail": [],
        "per_page": {},
        "sources": {"trends": [], "suggest": [], "claims": [], "patterns": []},
    }

    # Source 1: Google Trends (pytrends)
    if not offline:
        trends_kw = _fetch_trends_keywords(product_name, product_family, platform, cache)
        result["sources"]["trends"] = trends_kw
        result["primary_keywords"].extend(trends_kw[:5])

    # Source 2: Google Suggest API
    if not offline:
        suggest_kw = _fetch_suggest_keywords(product_name, product_family, platform, cache)
        result["sources"]["suggest"] = suggest_kw
        result["long_tail"].extend(suggest_kw[:10])

    # Source 3: Claim-derived keywords (always available)
    claim_kw = _extract_claim_keywords(claims, product_family, platform)
    result["sources"]["claims"] = claim_kw
    result["primary_keywords"].extend(claim_kw[:5])

    # Source 4: Dev search patterns (always available)
    pattern_kw = _generate_search_patterns(product_name, product_family, platform, claims)
    result["sources"]["patterns"] = pattern_kw
    result["long_tail"].extend(pattern_kw[:10])

    # Deduplicate
    result["primary_keywords"] = _dedupe(result["primary_keywords"])[:8]
    result["long_tail"] = _dedupe(result["long_tail"])[:15]

    # Build per-page keyword assignments
    result["per_page"] = _assign_per_page_keywords(
        result["primary_keywords"], result["long_tail"], product_family, platform
    )

    logger.info(
        "[W10 Keywords] Research complete",
        primary=len(result["primary_keywords"]),
        long_tail=len(result["long_tail"]),
        page_assignments=len(result["per_page"]),
    )

    return result


def _fetch_trends_keywords(
    product_name: str, family: str, platform: str, cache: Optional[Any] = None
) -> List[str]:
    """Fetch related keywords from Google Trends via pytrends."""
    cache_key = f"trends:{family}:{platform}"
    if cache:
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

    keywords: List[str] = []
    try:
        from pytrends.request import TrendReq  # type: ignore[import-untyped]
        pytrends = TrendReq(hl='en-US', tz=360)

        # Query product-related terms
        queries = [f"{family} {platform}", f"{platform} {family} library"]
        for query in queries:
            try:
                pytrends.build_payload([query], timeframe='today 3-m')
                related = pytrends.related_queries()
                if query in related and related[query].get("top") is not None:
                    top_df = related[query]["top"]
                    if hasattr(top_df, "iterrows"):
                        for _, row in top_df.iterrows():
                            kw = str(row.get("query", "")).strip()
                            if kw and len(kw) > 3:
                                keywords.append(kw.lower())
                time.sleep(1.5)  # Rate limiting
            except Exception as e:
                logger.debug(
                    "[W10 Trends] Query failed",
                    query=query,
                    error=str(e),
                )
                continue

    except ImportError:
        logger.info("[W10 Trends] pytrends not installed, skipping Google Trends")
    except Exception as e:
        logger.warning("[W10 Trends] Failed", error=str(e))

    keywords = _dedupe(keywords)[:10]
    if cache and keywords:
        cache.set(cache_key, keywords, ttl=3600)
    return keywords


def _fetch_suggest_keywords(
    product_name: str, family: str, platform: str, cache: Optional[Any] = None
) -> List[str]:
    """Fetch autocomplete suggestions from Google Suggest API (free, no key)."""
    cache_key = f"suggest:{family}:{platform}"
    if cache:
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

    keywords: List[str] = []
    queries = [
        f"{family} {platform}",
        f"python {family}",
        f"how to {family} {platform}",
        f"{product_name.split()[0].lower()} {platform}",
    ]

    for query in queries:
        try:
            encoded = urllib.parse.quote(query)
            url = f"https://suggestqueries.google.com/complete/search?client=firefox&q={encoded}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if isinstance(data, list) and len(data) >= 2:
                    for suggestion in data[1]:
                        if isinstance(suggestion, str) and len(suggestion) > 3:
                            keywords.append(suggestion.lower())
            time.sleep(0.5)  # Be polite
        except Exception as e:
            logger.debug(
                "[W10 Suggest] Query failed",
                query=query,
                error=str(e),
            )
            continue

    keywords = _dedupe(keywords)[:15]
    if cache and keywords:
        cache.set(cache_key, keywords, ttl=3600)
    return keywords


def _extract_claim_keywords(
    claims: List[Dict[str, Any]], family: str, platform: str
) -> List[str]:
    """Extract keywords from product claims using frequency analysis."""
    word_freq: Dict[str, int] = {}

    for claim in claims[:100]:  # Cap for performance
        text = claim.get("claim_text", "")
        words = re.findall(r'\b[a-z]{3,}\b', text.lower())
        for word in words:
            if word not in STOP_WORDS:
                word_freq[word] = word_freq.get(word, 0) + 1

    # Sort by frequency, return top keywords
    sorted_words = sorted(word_freq.items(), key=lambda x: -x[1])
    return [w for w, _ in sorted_words[:20]]


def _generate_search_patterns(
    product_name: str, family: str, platform: str, claims: List[Dict[str, Any]]
) -> List[str]:
    """Generate developer search patterns as long-tail keywords."""
    patterns: List[str] = []
    short_name = product_name.split()[0].lower() if product_name else family

    # Standard developer search patterns
    templates = [
        f"how to install {short_name} {platform}",
        f"{short_name} {platform} tutorial",
        f"{short_name} {platform} example",
        f"{short_name} {platform} getting started",
        f"python {family} library",
        f"{family} {platform} documentation",
        f"{short_name} {platform} api reference",
        f"best {family} library for {platform}",
    ]
    patterns.extend(templates)

    # Extract use-case-derived patterns from claims
    use_case_verbs: set[str] = set()
    for claim in claims[:50]:
        text = claim.get("claim_text", "").lower()
        for verb in [
            "convert", "load", "save", "export", "import",
            "create", "generate", "parse", "render", "extract",
        ]:
            if verb in text:
                use_case_verbs.add(verb)

    for verb in sorted(use_case_verbs)[:5]:
        patterns.append(f"how to {verb} {family} files {platform}")
        patterns.append(f"{platform} {verb} {family}")

    return patterns


def _assign_per_page_keywords(
    primary: List[str], long_tail: List[str], family: str, platform: str
) -> Dict[str, List[str]]:
    """Assign keywords to specific page slugs."""
    all_kw = primary + long_tail

    page_mapping: Dict[str, List[str]] = {
        "getting-started": ["install", "getting started", "setup", "quickstart"],
        "installation": ["install", "pip", "setup", "requirements"],
        "developer-guide": ["example", "tutorial", "how to", "guide"],
        "faq": ["faq", "question", "error", "problem", "issue"],
        "troubleshooting": ["error", "fix", "problem", "issue", "troubleshoot"],
        "api-overview": ["api", "reference", "class", "method", "module"],
        "best-practices": ["best practice", "performance", "optimization"],
        "tutorial": ["tutorial", "step by step", "example", "learn"],
    }

    result: Dict[str, List[str]] = {}
    for slug, match_terms in page_mapping.items():
        page_kw: List[str] = [family, platform]  # Always include
        for kw in all_kw:
            if any(term in kw for term in match_terms):
                page_kw.append(kw)
        result[slug] = _dedupe(page_kw)[:8]

    return result


def _dedupe(items: List[str]) -> List[str]:
    """Deduplicate while preserving order."""
    seen: set[str] = set()
    result: List[str] = []
    for item in items:
        normalized = item.strip().lower()
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(item.strip())
    return result
