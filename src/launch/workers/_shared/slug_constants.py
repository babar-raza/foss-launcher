"""Shared slug generation constants and helpers.

Canonical source of family keyword mappings, topic category maps, and
the ``extract_family_keyword()`` helper used by W2, W4, W6, and Gate 30.

TC-2601: Extracted from duplicate definitions in W2, W4, and Gate 30 to
eliminate drift risk and provide a single source of truth.
"""

from __future__ import annotations

from typing import Any, Dict, FrozenSet, List, Optional

# ---------------------------------------------------------------------------
# Family keyword map for slug templates
# ---------------------------------------------------------------------------
# Maps product family identifiers (substring match) to SEO-friendly nouns.
# Used by W2 (family_capabilities extraction), W4 (slug generation), and
# W6 (slug validation).

FAMILY_KEYWORD_MAP: Dict[str, str] = {
    "3d": "3d-models",
    "threed": "3d-models",
    "cells": "spreadsheets",
    "excel": "spreadsheets",
    "note": "notebooks",
    "onenote": "notebooks",
    "words": "documents",
    "pdf": "pdf-files",
    "slides": "presentations",
    "imaging": "images",
}

# ---------------------------------------------------------------------------
# Topic category inference map
# ---------------------------------------------------------------------------
# Maps title keywords to canonical topic categories for KB how-to pages.
# Used by W4 (_infer_topic_category) and Gate 30 (legacy slug inference).

TOPIC_CATEGORY_MAP: Dict[str, str] = {
    "open": "load_file",
    "load": "load_file",
    "save": "save_file",
    "write": "save_file",
    "export": "save_file",
    "convert": "convert_formats",
    "transform": "convert_formats",
    "fix": "troubleshoot",
    "error": "troubleshoot",
    "debug": "troubleshoot",
    "performance": "optimize_performance",
    "optimize": "optimize_performance",
    "improve": "optimize_performance",
}

# Derived at import time — guaranteed to stay in sync with TOPIC_CATEGORY_MAP.
REQUIRED_TOPIC_CATEGORIES: FrozenSet[str] = frozenset(
    set(TOPIC_CATEGORY_MAP.values())
)


# ---------------------------------------------------------------------------
# Leading stop-words for algorithmic slug cleanup (TC-3651)
# ---------------------------------------------------------------------------
# Used as fallback when LLM-based slug refinement is unavailable.

SLUG_LEADING_STOP_WORDS: FrozenSet[str] = frozenset({
    "you", "your", "we", "our", "they", "their", "it", "its",
    "a", "an", "the", "this", "that", "these", "those",
    "is", "are", "was", "were", "be", "can", "could", "may",
    "might", "will", "would", "shall", "should", "do", "does",
    "to", "of", "in", "for", "with", "on", "at", "by", "from",
    "allows", "enables", "provides", "supports", "used",
    "able", "possible", "also", "just", "only",
})


def strip_leading_stop_words(slug: str, min_remaining: int = 2) -> str:
    """Strip leading stop-words from a hyphen-separated slug.

    Removes words from the front of the slug that match
    ``SLUG_LEADING_STOP_WORDS`` while keeping at least *min_remaining*
    parts so the slug is never reduced to nothing useful.

    Args:
        slug: Hyphenated slug string (e.g. ``"you-can-create-rules"``).
        min_remaining: Minimum number of parts to keep.

    Returns:
        Cleaned slug string.
    """
    parts: List[str] = slug.split("-")
    while len(parts) > min_remaining and parts[0] in SLUG_LEADING_STOP_WORDS:
        parts.pop(0)
    return "-".join(parts)


def extract_family_keyword(
    product_slug: str,
    family_capabilities: Optional[Dict[str, Any]] = None,
) -> str:
    """Extract family keyword, preferring registry override.

    When *family_capabilities* (from ``family_capabilities.json``) is
    provided and contains a ``keyword`` field, that value is used.
    Otherwise falls back to ``FAMILY_KEYWORD_MAP`` substring match.

    Args:
        product_slug: Product slug string (e.g. "3d", "cells", "note").
        family_capabilities: Optional registry artifact dict.

    Returns:
        SEO keyword string; falls back to ``"files"`` for unknown families.
    """
    if family_capabilities and family_capabilities.get("keyword"):
        return family_capabilities["keyword"]
    slug_lower = product_slug.lower()
    for key, kw in FAMILY_KEYWORD_MAP.items():
        if key in slug_lower:
            return kw
    return "files"
