"""SEO keyword utilities adapted from content-generator.

Reference: content-generator src/agents/seo/keyword_extraction.py + keyword_injection.py

TC-2395: SEO Hardening — keyword extraction from content + natural injection
(1.5% density cap) + 3-provider metadata fallback with quality enforcement.
"""
from __future__ import annotations
import hashlib
import json as _json
import pathlib as _pathlib
import re
import time
from collections import Counter
from typing import Any, List, Optional


STOPWORDS = frozenset({
    "this", "that", "with", "from", "have", "will", "been", "they",
    "their", "your", "when", "what", "which", "where", "also", "more",
    "than", "about", "each", "into", "between", "through", "during",
})


def extract_keywords_from_content(content: str, max_keywords: int = 10) -> List[str]:
    """Heuristic keyword extraction from page content.

    Reference: content-generator keyword_extraction.py heuristic fallback path.
    No LLM needed — uses frequency analysis on meaningful words.
    """
    # Strip frontmatter
    if content.startswith("---"):
        end = content.find("\n---", 3)
        if end != -1:
            content = content[end + 4:]

    # Extract meaningful words (4+ chars, not stopwords)
    words = re.findall(r'\b[A-Za-z][a-z]{3,}\b', content)
    keywords = [w.lower() for w in words if w.lower() not in STOPWORDS]

    # Prefer capitalized words (likely proper nouns / product names)
    proper = [w.lower() for w in re.findall(r'\b[A-Z][a-z]{3,}\b', content)]

    # Combine: proper nouns first, then by frequency
    freq = Counter(keywords)
    proper_set = set(proper)
    sorted_kws = (
        [w for w in proper_set if freq[w] >= 2]
        + [w for w, _ in freq.most_common(max_keywords * 2) if w not in proper_set]
    )
    return sorted_kws[:max_keywords]


def inject_keywords_naturally(
    content: str,
    keywords: List[str],
    max_density: float = 0.015,
) -> str:
    """Inject keywords into content if below density threshold.

    Reference: content-generator keyword_injection.py inject_keywords_naturally()
    Max density: 1.5% (content-generator standard).
    """
    words = content.split()
    word_count = len(words)
    if word_count == 0:
        return content

    for kw in keywords:
        current_count = content.lower().count(kw.lower())
        current_density = current_count / word_count
        # Only inject if below half the max density
        if current_density < max_density / 2:
            content = _inject_at_paragraph_boundary(content, kw)

    return content


def enforce_seo_metadata_quality(meta: dict, content: str, title: str = "") -> dict:
    """Enforce content-generator seo_metadata.py quality rules:

    - seoTitle != title (add differentiator if identical)
    - description: 50-160 chars
    - Extract description from sentences 2-4 if generated description fails quality check

    Reference: content-generator seo_metadata.py _enhance_seo_metadata()
    """
    # 1. Ensure seoTitle differs from title
    seo_title = meta.get("seoTitle", "")
    page_title = title or meta.get("title", "")
    if seo_title and page_title and seo_title.lower() == page_title.lower():
        # Add differentiator — truncate and add ellipsis
        meta["seoTitle"] = page_title[:52] + "..." if len(page_title) > 52 else page_title + " | Guide"

    # 2. Enforce description length 50-160 chars
    desc = meta.get("description", "")
    if len(desc) < 50 or (page_title and page_title.lower() in desc.lower()):
        # Extract from sentences 2-4 of content
        clean_content = re.sub(r'^---.*?---\s*', '', content, flags=re.DOTALL)
        clean_content = re.sub(r'#{1,6}\s+', '', clean_content)
        clean_content = re.sub(r'```.*?```', '', clean_content, flags=re.DOTALL)
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', clean_content) if len(s.strip()) > 20]
        if len(sentences) >= 2:
            extracted = " ".join(sentences[1:4]).strip()
            if 50 <= len(extracted) <= 160:
                meta["description"] = extracted
            elif len(extracted) > 160:
                meta["description"] = extracted[:157] + "..."

    # 3. Truncate if still over 160
    if len(meta.get("description", "")) > 160:
        meta["description"] = meta["description"][:157] + "..."

    return meta


def _inject_at_paragraph_boundary(content: str, keyword: str) -> str:
    """Inject keyword naturally at a paragraph boundary."""
    paragraphs = content.split("\n\n")
    for i, para in enumerate(paragraphs[1:], 1):  # Skip first paragraph
        if (not para.startswith("#") and not para.startswith("```")
                and len(para.split()) > 20
                and keyword.lower() not in para.lower()):
            # Add keyword reference at start of paragraph
            paragraphs[i] = f"When working with {keyword}, {para[0].lower()}{para[1:]}"
            return "\n\n".join(paragraphs)
    return content  # No suitable injection point found


class SlugRefinementCache:
    """File-based cache for expensive PyTrends + Gemini slug queries.

    TTL: PyTrends results -> 3600s (1h), Gemini results -> 86400s (24h).
    Cache file lives at run_dir/work/slug_cache.json (per-run, not global).
    """

    _PYTRENDS_TTL = 3600    # 1 hour
    _GEMINI_TTL = 86400     # 24 hours

    def __init__(self, cache_path: _pathlib.Path) -> None:
        self._path = cache_path
        self._data: dict = {}
        if cache_path.exists():
            try:
                self._data = _json.loads(cache_path.read_text(encoding="utf-8"))
            except Exception:
                self._data = {}

    def get(self, key: str, ttl: int) -> Optional[Any]:
        """Return cached value if present and within TTL, else None."""
        entry = self._data.get(key)
        if not entry:
            return None
        if time.time() - entry.get("ts", 0) > ttl:
            return None
        return entry["value"]

    def set(self, key: str, value: Any) -> None:
        """Store value with current timestamp."""
        self._data[key] = {"ts": time.time(), "value": value}
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(_json.dumps(self._data, indent=2), encoding="utf-8")

    def pytrends_key(self, query: str) -> str:
        """Cache key for a PyTrends query."""
        return f"pt:{hashlib.md5(query.encode()).hexdigest()}"

    def gemini_key(self, title: str, keywords: list) -> str:
        """Cache key for a Gemini slug refinement request."""
        content = f"{title}:{','.join(sorted(str(k) for k in keywords))}"
        return f"gm:{hashlib.md5(content.encode()).hexdigest()}"
