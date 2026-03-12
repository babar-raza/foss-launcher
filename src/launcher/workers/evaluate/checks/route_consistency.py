"""Check: Route consistency — slug topic words appear in page prose.

TC-4037: Pages that receive wrong claims (e.g., formula-calculation page
getting PDF-only claims) produce prose that never mentions the topic in
their slug. Detects this misrouting with a HIGH finding.
"""
from __future__ import annotations

import re

from launcher.models.evaluation import Finding

# English stop words and short words that carry no topic signal from a slug.
_STOP_WORDS: frozenset[str] = frozenset({
    "how", "the", "and", "for", "with", "from", "into", "that", "this",
    "are", "was", "been", "have", "will", "your", "our", "its", "can",
    "not", "but", "all", "any", "some", "each", "more", "when", "then",
    "than", "also", "both", "most", "many",
    "page", "pages", "site", "docs", "post", "blog",  # generic web structure terms
})

# Page roles where slug-topic matching is not meaningful.
_SKIP_ROLES: frozenset[str] = frozenset({
    "landing", "blog_announcement", "faq", "troubleshooting",
    "feature_blog", "getting_started", "overview",
})


def _extract_slug_words(slug: str) -> list[str]:
    """Extract meaningful topic words from a slug.

    Splits on ``-``, filters stop words and short words (< 4 chars).
    Returns empty list if no meaningful words remain (check is skipped).
    """
    parts = slug.lstrip("/").split("/")
    # Use the last path component (e.g. "formula-calculation" from "docs/formula-calculation")
    last = parts[-1] if parts else slug
    # Remove index markers
    last = last.replace("_index", "").replace("index", "")
    words = last.split("-")
    return [
        w.lower() for w in words
        if len(w) >= 4 and w.lower() not in _STOP_WORDS
    ]


def _strip_frontmatter(content: str) -> str:
    """Remove YAML frontmatter block from content."""
    if content.startswith("---"):
        end = content.find("---", 3)
        if end != -1:
            return content[end + 3:]
    return content


def check_route_consistency(
    content: str,
    slug: str,
    *,
    page_role: str = "",
) -> list[Finding]:
    """Check that slug topic words appear in the page prose.

    Returns a HIGH finding if none of the meaningful slug words are found
    in the rendered prose. Skips for roles where topic matching is not
    meaningful (landing pages, FAQs, etc.) and when no meaningful words
    can be extracted from the slug.

    Args:
        content: Rendered markdown content (may include frontmatter).
        slug: Page slug (e.g. ``formula-calculation`` or ``docs/formula-calculation``).
        page_role: Hugo page role — used to skip non-content page roles.
    """
    if page_role in _SKIP_ROLES:
        return []

    topic_words = _extract_slug_words(slug)
    if not topic_words:
        return []

    # Strip frontmatter and code blocks before prose search.
    prose = _strip_frontmatter(content)
    prose = re.sub(r"```.*?```", "", prose, flags=re.DOTALL)
    prose = re.sub(r"`[^`\n]+`", "", prose)
    prose_lower = prose.lower()

    if any(w in prose_lower for w in topic_words):
        return []

    return [
        Finding(
            check="route_consistency",
            message=(
                f"Off-topic page: slug topic words {topic_words} "
                f"not found in prose — claims may be misrouted"
            ),
            severity="high",
            location=slug,
        )
    ]
