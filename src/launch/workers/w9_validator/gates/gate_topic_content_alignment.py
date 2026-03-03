"""Gate: Topic-Content Alignment (TC-3676).

Validates that page content actually matches its title and primary_focus.
Uses deterministic keyword overlap — no LLM calls.

Algorithm:
1. Extract title keywords from H1 + frontmatter title + primary_focus
2. Extract top frequent content words (exclude stopwords + product tokens)
3. Compute overlap: |title_keywords ∩ body_top_N| / |title_keywords|
4. ERROR if overlap < threshold AND title has >=3 content keywords

Error codes:
  TOPIC_DRIFT -- content does not match page title/topic

Spec: specs/09_validation_gates.md §Quality Enforcement Hardening
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

# Overlap threshold — below this, content is considered misaligned
TOPIC_ALIGNMENT_THRESHOLD = 0.40

# Warn threshold — between this and TOPIC_ALIGNMENT_THRESHOLD
TOPIC_ALIGNMENT_WARN_THRESHOLD = 0.60

# Minimum title keywords to trigger the check
MIN_TITLE_KEYWORDS = 3

# Minimum page word count to apply the check
MIN_WORD_COUNT = 100

# Page roles excluded from this check (too short or structural)
_SKIP_ROLES = frozenset({"toc", "landing"})

# Stopwords to exclude from keyword extraction
_STOPWORDS: Set[str] = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "it", "as", "be", "are", "was",
    "were", "been", "being", "has", "have", "had", "do", "does", "did",
    "will", "would", "could", "should", "may", "might", "can", "shall",
    "this", "that", "these", "those", "not", "no", "nor", "so", "if",
    "then", "than", "when", "while", "where", "how", "what", "which",
    "who", "whom", "why", "all", "each", "every", "both", "few", "more",
    "most", "other", "some", "such", "only", "own", "same", "into",
    "through", "during", "before", "after", "above", "below", "between",
    "about", "against", "over", "under", "again", "further", "once",
    "here", "there", "just", "also", "very", "too", "any", "its",
    "your", "you", "we", "our", "they", "their", "up", "out", "off",
    "down", "see", "use", "using", "used", "new", "get", "set",
}

# Product tokens to exclude (too common in docs, not meaningful for alignment)
_PRODUCT_TOKENS: Set[str] = {
    "aspose", "foss", "python", "java", "net", "dotnet", "typescript",
    "cells", "note", "words", "pdf", "slides", "email", "html",
    "documentation", "guide", "page", "article", "tutorial", "howto",
    "reference", "api", "overview", "example", "code",
}

# Word extraction pattern
_WORD_RE = re.compile(r"[a-z][a-z0-9]+", re.IGNORECASE)


def execute_gate(run_dir: Path, profile: str) -> Tuple[bool, List[Dict[str, Any]]]:
    """Execute topic-content alignment gate.

    Scans all .md files under work/site/content/ and checks title-body
    keyword overlap.

    Args:
        run_dir: Run directory path.
        profile: Validation profile (local, ci, prod).

    Returns:
        Tuple of (gate_passed, issues).
    """
    issues: List[Dict[str, Any]] = []

    # Load page_plan for page roles and primary_focus
    page_metadata = _load_page_metadata(run_dir)

    site_dir = run_dir / "work" / "site" / "content"
    if not site_dir.exists():
        return True, []

    for md_file in sorted(site_dir.rglob("*.md")):
        try:
            content = md_file.read_text(encoding="utf-8")
        except OSError:
            continue

        # Skip index files (section index pages, usually structural)
        if md_file.name == "_index.md":
            continue

        slug = md_file.stem
        meta = page_metadata.get(slug, {})
        page_role = meta.get("page_role", "")

        # Skip excluded roles
        if page_role in _SKIP_ROLES:
            continue

        # Extract title and body
        title, body = _split_title_body(content, meta)

        # Skip short pages
        body_words = _WORD_RE.findall(body)
        if len(body_words) < MIN_WORD_COUNT:
            continue

        # Extract keywords
        title_keywords = _extract_keywords(title)
        if len(title_keywords) < MIN_TITLE_KEYWORDS:
            continue

        body_keywords = _extract_top_keywords(body_words, top_n=100)

        # Compute overlap
        overlap = len(title_keywords & body_keywords) / len(title_keywords)
        rel_path = str(md_file.relative_to(run_dir)).replace("\\", "/")

        if overlap < TOPIC_ALIGNMENT_THRESHOLD:
            issues.append({
                "issue_id": f"topic_drift_{slug}",
                "gate": "gate_topic_content_alignment",
                "severity": "error",
                "message": (
                    f"Page '{slug}' title keywords have only {overlap:.0%} overlap "
                    f"with body content (threshold: {TOPIC_ALIGNMENT_THRESHOLD:.0%}). "
                    f"Title keywords: {sorted(title_keywords)}"
                ),
                "error_code": "TOPIC_DRIFT",
                "location": {"path": rel_path},
                "status": "OPEN",
            })
        elif overlap < TOPIC_ALIGNMENT_WARN_THRESHOLD:
            issues.append({
                "issue_id": f"topic_drift_warn_{slug}",
                "gate": "gate_topic_content_alignment",
                "severity": "warn",
                "message": (
                    f"Page '{slug}' has low title-body alignment ({overlap:.0%}). "
                    f"Title keywords: {sorted(title_keywords)}"
                ),
                "error_code": "TOPIC_DRIFT",
                "location": {"path": rel_path},
                "status": "OPEN",
            })

    gate_passed = not any(
        issue.get("severity") in ("blocker", "error") for issue in issues
    )
    return gate_passed, issues


def _load_page_metadata(run_dir: Path) -> Dict[str, Dict[str, Any]]:
    """Load page metadata from page_plan.json keyed by slug."""
    plan_path = run_dir / "artifacts" / "page_plan.json"
    if not plan_path.exists():
        return {}
    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}

    result: Dict[str, Dict[str, Any]] = {}
    for page in plan.get("pages", []):
        slug = page.get("slug", "")
        if slug:
            result[slug] = page
    return result


def _split_title_body(content: str, meta: Dict[str, Any]) -> Tuple[str, str]:
    """Split content into title string and body string.

    Title is composed of: H1 heading + frontmatter title + primary_focus.
    Body is the markdown content after frontmatter, with headings stripped
    so that heading text (which echoes the title) does not inflate overlap.
    """
    title_parts: List[str] = []

    # Frontmatter title
    fm_title = meta.get("title", "")
    if fm_title:
        title_parts.append(fm_title)

    # Primary focus
    primary_focus = meta.get("primary_focus", "")
    if primary_focus:
        title_parts.append(primary_focus)

    # H1 from content
    body = content
    # Strip frontmatter
    if content.startswith("---"):
        end = content.find("---", 3)
        if end > 0:
            body = content[end + 3:].strip()

    # Extract H1
    h1_match = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
    if h1_match:
        title_parts.append(h1_match.group(1))

    # Strip heading lines from body — headings echo the title and should not
    # inflate body keyword overlap.  Only paragraph prose counts as "content".
    body = re.sub(r"^#{1,6}\s+.*$", "", body, flags=re.MULTILINE)

    title = " ".join(title_parts)
    return title, body


def _extract_keywords(text: str) -> Set[str]:
    """Extract meaningful keywords from text."""
    words = _WORD_RE.findall(text.lower())
    return {
        w for w in words
        if w not in _STOPWORDS
        and w not in _PRODUCT_TOKENS
        and len(w) >= 3
    }


def _extract_top_keywords(words: List[str], top_n: int = 100) -> Set[str]:
    """Extract top N frequent keywords from word list."""
    filtered = [
        w.lower() for w in words
        if w.lower() not in _STOPWORDS
        and w.lower() not in _PRODUCT_TOKENS
        and len(w) >= 3
    ]
    counter = Counter(filtered)
    return {word for word, _ in counter.most_common(top_n)}
