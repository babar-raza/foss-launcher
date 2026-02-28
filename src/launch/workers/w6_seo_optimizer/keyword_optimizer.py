"""Keyword extraction and density-controlled injection."""

from __future__ import annotations

import re
from typing import Dict, List

from ...util.logging import get_logger
from .keyword_research import STOP_WORDS

logger = get_logger()


def extract_keywords(content: str, max_keywords: int = 8) -> List[str]:
    """Extract keywords from markdown content using frequency analysis.

    Strips code blocks, frontmatter, and HTML comments before analysis.
    """
    # Strip frontmatter
    body = content
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            body = parts[2]

    # Strip code blocks
    body = re.sub(r'```[\s\S]*?```', '', body)

    # Strip HTML comments
    body = re.sub(r'<!--[\s\S]*?-->', '', body)

    # Strip markdown links (keep text, remove URLs)
    body = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', body)

    # Extract words
    words = re.findall(r'\b[a-z]{3,}\b', body.lower())

    # Frequency analysis
    freq: Dict[str, int] = {}
    for word in words:
        if word not in STOP_WORDS:
            freq[word] = freq.get(word, 0) + 1

    sorted_words = sorted(freq.items(), key=lambda x: -x[1])
    return [w for w, _ in sorted_words[:max_keywords]]


def inject_keywords_naturally(
    content: str,
    keywords: List[str],
    max_density: float = 1.5,
) -> str:
    """DEPRECATED (TC-3400): This function was a no-op (``modified`` never set True).

    Use ``keyword_utils.inject_keywords_naturally`` instead. This stub is kept
    for backward compatibility of any direct imports.
    """
    return content


def calculate_keyword_density(content: str, keyword: str) -> float:
    """Calculate keyword density as percentage."""
    # Strip non-prose content
    body = content
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            body = parts[2]

    body = re.sub(r'```[\s\S]*?```', '', body)
    body = re.sub(r'<!--[\s\S]*?-->', '', body)

    total_words = len(body.split())
    if total_words == 0:
        return 0.0

    keyword_count = body.lower().count(keyword.lower())
    return (keyword_count / total_words) * 100
