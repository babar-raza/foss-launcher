"""Slug generation engine — full v1 port for v2.

Ported from v1's ``slug_constants.py`` and ``w4_ia_planner/worker.py``
slug generation layers.  Adapted for v2's typed ``ProductEvidence`` model.

Six layers:
1. Constants (family keywords, topic categories, stop words, templates)
2. extract_family_keyword — substring match against FAMILY_KEYWORD_MAP
3. strip_leading_stop_words — remove filler from slug head
4. derive_semantic_slug — heuristic text-to-slug extraction
5. derive_evidence_aware_slug — intent + evidence → template slug
6. derive_blog_evidence_slug — enriches semantic slug with family keyword
7. score_blog_workflow — deterministic workflow scoring for blog slugs
8. refine_slugs_batch — LLM or algorithmic slug cleanup
9. validate_slug_safety — detect malformed slugs (Gate 19 port)

TC-3780: Created for v2.
"""

from __future__ import annotations

import html
import logging
import re
from collections import Counter
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from launcher.models.understanding import ProductEvidence

logger = logging.getLogger(__name__)

# Regex to normalize malformed HTML entities missing trailing semicolons.
# Matches known entity names preceded by & and NOT already followed by ;
# e.g. "&reg" -> "&reg;" so html.unescape() can handle them.
_MALFORMED_ENTITY_RE = re.compile(
    r"&(reg|trade|copy|amp|nbsp|quot|apos|lt|gt)(?=[^;a-z]|$)",
    re.IGNORECASE,
)

# Noise words: OS/platform/environment terms that pollute slugs.
# These are stripped from slug input text unless they match a family keyword.
_NOISE_WORDS: frozenset[str] = frozenset({
    "microsoft", "windows", "desktop", "linux", "macos", "server",
    "ubuntu", "debian", "centos", "alpine", "docker", "container",
    "cloud", "azure", "aws", "gcp", "heroku",
})

# Compiled regex for entity artifact detection in validate_slug_safety().
# Catches HTML entity remnants glued to words (e.g. "excelreg" from "&reg;").
# Requires 3+ preceding letters to avoid false positives on short prefixes.
_ENTITY_ARTIFACT_RE = re.compile(r"[a-z]{3,}(?:reg|trade|copy)(?=-|$)")

# Compiled regex for trademark/copyright symbol removal.
_TRADEMARK_SYMBOL_RE = re.compile(r"[®™©]")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FAMILY_KEYWORD_MAP: dict[str, str] = {
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

TOPIC_CATEGORY_MAP: dict[str, str] = {
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

SLUG_LEADING_STOP_WORDS: frozenset[str] = frozenset({
    "you", "your", "we", "our", "they", "their", "it", "its",
    "a", "an", "the", "this", "that", "these", "those",
    "is", "are", "was", "were", "be", "can", "could", "may",
    "might", "will", "would", "shall", "should", "do", "does",
    "to", "of", "in", "for", "with", "on", "at", "by", "from",
    "allows", "enables", "provides", "supports", "used",
    "able", "possible", "also", "just", "only",
})

_HOWTO_SLUG_TEMPLATES: dict[str, str] = {
    "open": "how-to-load-{family_keyword}-{platform}",
    "save": "how-to-save-{family_keyword}-{platform}",
    "convert": "how-to-convert-{source_format}-to-{target_format}-{platform}",
    "fix": "how-to-fix-{family_keyword}-errors-{platform}",
    "performance": "how-to-optimize-{family_keyword}-{platform}",
}

_CONVERT_FALLBACK_TEMPLATE = "how-to-convert-{family_keyword}-{platform}"

_HIGH_INTENT_VERBS: frozenset[str] = frozenset({
    "convert", "create", "export", "generate", "import", "load",
    "merge", "open", "parse", "read", "render", "save", "split",
    "transform", "write",
})

# ---------------------------------------------------------------------------
# Preamble-stripping regex (compiled once)
# ---------------------------------------------------------------------------

_PREAMBLE_RE = re.compile(
    r"^(?:In cases[,]?\s*where|When you need to|It is possible to|You can use|"
    r"this document specifies that|a field can only)\s+",
    re.IGNORECASE,
)

_VALID_REFINED_SLUG_RE = re.compile(
    r"^[a-z0-9]([a-z0-9]|-(?!-))*[a-z0-9]$|^[a-z0-9]$"
)

_SLUG_REFINEMENT_PROMPT = """\
For each slug below, extract the core 2-5 word topic. \
Remove filler words (you, can, this, that, allows, enables, etc.). \
Keep action verbs and nouns. Return one cleaned slug per line, same order. \
Use only lowercase and hyphens.

{slugs}"""


# ---------------------------------------------------------------------------
# Layer 1: extract_family_keyword
# ---------------------------------------------------------------------------


def extract_family_keyword(family: str) -> str:
    """Extract SEO-friendly family keyword via substring match.

    Args:
        family: Product family identifier (e.g. ``"cells"``, ``"3d"``).

    Returns:
        Matched keyword or ``"files"`` as fallback.
    """
    family_lower = family.lower()
    for key, kw in FAMILY_KEYWORD_MAP.items():
        if key in family_lower:
            return kw
    return "files"


# ---------------------------------------------------------------------------
# Layer 2: strip_leading_stop_words
# ---------------------------------------------------------------------------


def strip_leading_stop_words(slug: str, min_remaining: int = 2) -> str:
    """Strip leading stop words from a hyphen-separated slug.

    Removes words from the front that match ``SLUG_LEADING_STOP_WORDS``
    while keeping at least *min_remaining* parts.

    Args:
        slug: Hyphenated slug string (e.g. ``"you-can-create-rules"``).
        min_remaining: Minimum number of parts to keep.

    Returns:
        Cleaned slug string.
    """
    if not slug:
        return ""
    parts: list[str] = slug.split("-")
    while len(parts) > min_remaining and parts[0] in SLUG_LEADING_STOP_WORDS:
        parts.pop(0)
    return "-".join(parts)


# ---------------------------------------------------------------------------
# Shared: HTML entity normalization
# ---------------------------------------------------------------------------


def strip_html_entities(text: str) -> str:
    """Normalize and strip HTML entities and trademark symbols from text.

    Steps:
    1. Fix malformed entities missing semicolons (e.g. ``&reg`` -> ``&reg;``)
    2. Iteratively decode HTML entities via ``html.unescape()`` until stable,
       handling double-encoded input like ``&amp;reg;`` -> ``&reg;`` -> ``®``.
       Capped at 5 iterations to prevent pathological input from looping.
    3. Remove trademark symbols (®, ™, ©)

    Returns cleaned text.  Logs at DEBUG when text is modified.
    """
    original = text
    # Fix malformed entities (missing semicolons)
    text = _MALFORMED_ENTITY_RE.sub(r"&\1;", text)
    # Iteratively decode HTML entities until stable (handles double-encoding)
    for _ in range(5):
        decoded = html.unescape(text)
        if decoded == text:
            break
        text = decoded
    else:
        logger.warning(
            "HTML entity decode did not converge after 5 passes: %r", original
        )
    # Remove trademark symbols
    text = _TRADEMARK_SYMBOL_RE.sub("", text)
    if text != original:
        logger.debug(
            "Stripped HTML entities from slug input: %r -> %r", original, text
        )
    return text


# Backward-compat alias (SEO-03).
_strip_html_entities = strip_html_entities


# ---------------------------------------------------------------------------
# Layer 3: derive_semantic_slug
# ---------------------------------------------------------------------------


def derive_semantic_slug(text: str, max_length: int = 40) -> str:
    """Derive a concise, human-readable slug from text.

    Strips spec headers, preambles, and extracts the first 6 meaningful
    words, then slugifies the result.

    Args:
        text: Raw text to derive slug from.
        max_length: Maximum slug length; truncates at word boundary.

    Returns:
        Slugified string, or ``"feature"`` if input is empty.
    """
    if not text or not text.strip():
        return "feature"

    # Strip spec-header prefixes (e.g. "11 Section 3:", "<11> Section 3:")
    text = re.sub(
        r"^<?(\d+)>?[\s.)\-:]+(?:Section\s+\d+[\s:.\-]*)?",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()
    text = re.sub(r"^<\d+>\s*", "", text).strip()

    # Strip filler preambles iteratively (max 3 passes)
    for _ in range(3):
        new_text = _PREAMBLE_RE.sub("", text).strip()
        if new_text == text:
            break
        text = new_text

    # Strip remaining "Section N:" patterns
    text = re.sub(
        r"^Section\s+\d+[\s:.\-]*", "", text, flags=re.IGNORECASE
    ).strip()

    # Decode HTML entities and strip trademark symbols
    text = strip_html_entities(text)

    # Filter noise words (OS/platform terms that pollute slugs)
    words = text.split()
    non_noise = [w for w in words if w.lower() not in _NOISE_WORDS]
    if non_noise:
        words = non_noise

    # Extract first 6 meaningful words
    phrase = " ".join(words[:6])

    # Slugify
    slug = phrase.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"-{2,}", "-", slug)
    slug = slug.strip("-")

    # Enforce max length at word boundary
    if len(slug) > max_length:
        truncated = slug[:max_length]
        last_hyphen = truncated.rfind("-")
        if last_hyphen > 10:
            truncated = truncated[:last_hyphen]
        slug = truncated.strip("-")

    return slug or "feature"


# ---------------------------------------------------------------------------
# Layer 4: derive_evidence_aware_slug
# ---------------------------------------------------------------------------


def _extract_top_conversion_pair(
    product_evidence: ProductEvidence,
) -> tuple[str, str]:
    """Extract top conversion pair from ProductEvidence."""
    pairs = product_evidence.conversion_pairs
    if not pairs:
        return ("", "")

    first = pairs[0]
    if isinstance(first, dict):
        src = first.get("source", first.get("from", ""))
        tgt = first.get("target", first.get("to", ""))
        if src and tgt:
            return (str(src).upper(), str(tgt).upper())

    return ("", "")


def _extract_top_formats(
    product_evidence: ProductEvidence,
) -> tuple[str, str]:
    """Extract top two formats from ProductEvidence.supported_formats."""
    formats = product_evidence.supported_formats
    if not formats:
        return ("", "")

    clean: list[str] = []
    for f in formats:
        name = str(f).upper().strip()
        if name:
            clean.append(name)

    if len(clean) >= 2:
        return (clean[0].lower(), clean[1].lower())
    elif len(clean) == 1:
        return (clean[0].lower(), "other")
    return ("", "")


def derive_evidence_aware_slug(
    title: str,
    family: str,
    product_evidence: ProductEvidence,
    platform: str = "python",
    max_length: int = 40,
) -> str:
    """Generate evidence-aware slug for KB how-to pages.

    Maps generic titles to family-specific slugs using evidenced
    capabilities from ``ProductEvidence``.  Falls back to
    ``derive_semantic_slug()`` if no evidence match.

    Args:
        title: Page title text.
        family: Product family identifier.
        product_evidence: Typed evidence bundle from Understand worker.
        platform: Platform identifier (default ``"python"``).
        max_length: Maximum slug length.

    Returns:
        Evidence-aware slug string.
    """
    # Decode HTML entities and strip trademark symbols before processing
    title = strip_html_entities(title)
    title_lower = title.lower()

    # Detect intent from title
    intent: str | None = None
    for keyword in _HOWTO_SLUG_TEMPLATES:
        if keyword in title_lower:
            intent = keyword
            break

    if not intent:
        return derive_semantic_slug(title, max_length)

    template = _HOWTO_SLUG_TEMPLATES[intent]
    family_keyword = extract_family_keyword(family)

    context: dict[str, str] = {
        "family_keyword": family_keyword,
        "source_format": "",
        "target_format": "",
        "platform": platform,
    }

    if intent == "convert":
        # Try conversion pairs first
        src, tgt = _extract_top_conversion_pair(product_evidence)
        if src and tgt:
            context["source_format"] = src.lower()
            context["target_format"] = tgt.lower()
        else:
            # Try supported_formats
            fmt_src, fmt_tgt = _extract_top_formats(product_evidence)
            if fmt_src and fmt_tgt and fmt_tgt != "other":
                context["source_format"] = fmt_src
                context["target_format"] = fmt_tgt
            else:
                # Fallback to family keyword convert template
                template = _CONVERT_FALLBACK_TEMPLATE

    try:
        slug = template.format(**context)
    except (KeyError, IndexError):
        return derive_semantic_slug(title, max_length)

    # Clean up
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    if len(slug) > max_length:
        truncated = slug[:max_length]
        last_hyphen = truncated.rfind("-")
        if last_hyphen > 10:
            truncated = truncated[:last_hyphen]
        slug = truncated.strip("-")

    return slug or derive_semantic_slug(title, max_length)


# ---------------------------------------------------------------------------
# Layer 5: derive_blog_evidence_slug
# ---------------------------------------------------------------------------


def derive_blog_evidence_slug(
    title: str,
    family: str,
    product_evidence: ProductEvidence,
    platform: str = "python",
) -> str:
    """Derive evidence-aware blog slug with family keyword enrichment.

    Enriches the base semantic slug with the product family keyword when
    it is not already present.  Caps at 40 characters.

    Args:
        title: Blog workflow title.
        family: Product family identifier.
        product_evidence: Typed evidence bundle.
        platform: Platform identifier.

    Returns:
        Enriched slug string.
    """
    # Defensive: strip entities before any processing
    title = strip_html_entities(title)
    family_kw = extract_family_keyword(family)
    base_slug = derive_semantic_slug(title)
    if not base_slug:
        return ""
    # Already contains family keyword — skip enrichment
    if family_kw in base_slug:
        return base_slug
    enriched = f"{base_slug}-{family_kw}"
    if len(enriched) > 40:
        return base_slug
    return enriched


# ---------------------------------------------------------------------------
# Layer 6: score_blog_workflow
# ---------------------------------------------------------------------------


def score_blog_workflow(
    product_evidence: ProductEvidence,
    snippets: list[Any],
    family: str,
    platform: str = "python",
) -> dict[str, Any]:
    """Deterministic scoring to pick the most marketable workflow.

    Scoring:
      +5  conversion workflow AND has evidenced snippets
      +3  workflow has >= 1 code snippet (tag/claim overlap)
      +2  workflow title/tag contains a high-intent verb

    Tiebreaker: workflow name alphabetical (ascending).
    Fallback: ``{"slug": "feature-highlight", "score": 0}`` when empty.

    Args:
        product_evidence: Typed evidence bundle with ``workflows``.
        snippets: List of snippet dicts with ``tags`` and ``claim_ids``.
        family: Product family identifier.
        platform: Platform identifier.

    Returns:
        Dict with keys: slug, workflow_tag, title, score.
    """
    _fallback: dict[str, Any] = {
        "slug": "feature-highlight",
        "workflow_tag": "",
        "title": "Feature Highlight",
        "score": 0,
    }

    workflows = product_evidence.workflows
    if not workflows:
        return dict(_fallback)

    # Build snippet evidence sets
    snippet_tag_set: set[str] = set()
    snippet_claim_set: set[str] = set()
    for s in snippets:
        if isinstance(s, dict):
            snippet_tag_set.update(s.get("tags", []))
            snippet_claim_set.update(s.get("claim_ids", []))

    scored: list[tuple[int, str, dict[str, Any]]] = []
    for wf in workflows:
        name = wf.get("name", wf.get("workflow_tag", ""))
        title = wf.get("title", name)
        wf_claims = set(wf.get("claim_ids", []))
        wf_stags = set(wf.get("snippet_tags", wf.get("tags", [])))
        score = 0

        has_snippet = bool(
            wf_stags & snippet_tag_set or wf_claims & snippet_claim_set
        )
        is_conversion = any(
            kw in name.lower() or kw in title.lower()
            for kw in ("convert", "conversion")
        )

        if is_conversion and has_snippet:
            score += 5
        if has_snippet:
            score += 3
        wf_words = set(re.split(r"[_\s-]+", f"{name} {title}".lower()))
        if wf_words & _HIGH_INTENT_VERBS:
            score += 2

        scored.append((score, name, wf))

    # Sort by (score DESC, name ASC) for determinism
    scored.sort(key=lambda x: (-x[0], x[1]))

    if not scored or scored[0][0] == 0:
        return dict(_fallback)

    best_score, best_name, best_wf = scored[0]
    best_title = best_wf.get("title", best_name)

    slug = derive_blog_evidence_slug(
        best_title, family, product_evidence, platform=platform
    ) or "feature-highlight"

    return {
        "slug": slug,
        "workflow_tag": best_name,
        "title": best_title,
        "score": best_score,
    }


# ---------------------------------------------------------------------------
# Layer 7: refine_slugs_batch
# ---------------------------------------------------------------------------


def refine_slugs_batch(
    slugs: list[str],
    llm_client: Any = None,
) -> list[str]:
    """Batch-clean slugs using LLM (or algorithmic fallback).

    When *llm_client* is provided and responsive, sends a single batch
    prompt asking the LLM to extract the core topic for each slug.  If
    the LLM is unavailable or returns unexpected output, falls through
    to ``strip_leading_stop_words`` per slug.

    Args:
        slugs: List of raw slug strings.
        llm_client: Optional LLM client with ``chat_completion`` method.

    Returns:
        List of cleaned slug strings (same length as input).
    """
    if not slugs:
        return []

    if llm_client is not None:
        try:
            response = llm_client.chat_completion(
                [
                    {
                        "role": "user",
                        "content": _SLUG_REFINEMENT_PROMPT.format(
                            slugs="\n".join(slugs),
                        ),
                    }
                ],
                temperature=0.0,
            )
            cleaned = response.strip().splitlines()
            if len(cleaned) == len(slugs):
                result: list[str] = []
                for original, raw in zip(slugs, cleaned):
                    new_slug = raw.strip().lower()
                    new_slug = strip_html_entities(new_slug)
                    new_slug = re.sub(r"\s+", "-", new_slug)
                    new_slug = re.sub(r"[^a-z0-9-]", "", new_slug)
                    new_slug = re.sub(r"-{2,}", "-", new_slug).strip("-")
                    if not new_slug or not _VALID_REFINED_SLUG_RE.match(new_slug):
                        logger.warning(
                            "[SlugEngine] refine_slugs_batch: LLM slug %r rejected"
                            " (invalid after normalisation) — falling back to %r",
                            new_slug or raw.strip(),
                            original,
                        )
                        result.append(original)
                        continue
                    issues = validate_slug_safety(new_slug)
                    if issues:
                        logger.warning(
                            "[SlugEngine] refine_slugs_batch: LLM slug %r failed"
                            " safety check %s — falling back to %r",
                            new_slug,
                            issues,
                            original,
                        )
                        result.append(original)
                    else:
                        result.append(new_slug)
                return result
        except Exception:
            pass

    # Algorithmic fallback
    return [strip_leading_stop_words(s) for s in slugs]


# ---------------------------------------------------------------------------
# Layer 8: validate_slug_safety
# ---------------------------------------------------------------------------


def validate_slug_safety(slug: str) -> list[str]:
    """Validate slug for safety issues that would produce broken URLs.

    Checks:
    - repr tokens (``[``, ``]``, ``'``, ``"``)
    - doubled hyphens
    - empty segments (``//``)
    - 2+ consecutive stop words at start
    - doubled URL path segments (``python/python``)
    - HTML entity remnants glued to words (``excelreg``, ``windowstrade``)

    Args:
        slug: Slug string to validate.

    Returns:
        List of issue descriptions (empty means safe).
    """
    issues: list[str] = []

    # Check repr tokens
    repr_chars = {"[", "]", "'", '"'}
    found_repr = [c for c in repr_chars if c in slug]
    if found_repr:
        issues.append(
            f"Repr/bracket tokens found: {', '.join(sorted(found_repr))}"
        )

    # Check doubled hyphens
    if "--" in slug:
        issues.append("Doubled hyphens detected")

    # Check empty segments (slashes)
    if "//" in slug:
        issues.append("Empty URL segments (consecutive slashes)")

    # Check 2+ consecutive stop words at start
    parts = slug.split("-")
    consecutive_stop = 0
    for part in parts:
        if part.lower() in SLUG_LEADING_STOP_WORDS:
            consecutive_stop += 1
        else:
            break
    if consecutive_stop >= 2:
        issues.append(
            f"{consecutive_stop} consecutive stop words at slug start"
        )

    # Check doubled URL path segments
    if "/" in slug:
        segments = slug.split("/")
        for i in range(len(segments) - 1):
            if segments[i] and segments[i] == segments[i + 1]:
                issues.append(
                    f"Doubled URL segment: '{segments[i]}'"
                )
                break

    # Check for HTML entity remnants glued to words (e.g. "excelreg" from "&reg;")
    if _ENTITY_ARTIFACT_RE.search(slug):
        issues.append(
            "Possible HTML entity remnant (e.g. 'excelreg' from '&reg;')"
        )

    return issues


# ---------------------------------------------------------------------------
# Layer 9: validate_slug_quality
# ---------------------------------------------------------------------------


def validate_slug_quality(slug: str, family: str = "") -> list[str]:
    """Check slug for semantic quality issues beyond URL safety.

    Catches:
    - Consecutive duplicate words (``windows-windows``)
    - Redundant words (same word appears 2+ times)
    - High stop-word ratio (sentence fragments)
    - OS/platform noise words that aren't product-relevant

    Args:
        slug: Slug string to check.
        family: Product family (to protect family keywords from noise filter).

    Returns:
        List of quality issue descriptions (empty means good).
    """
    issues: list[str] = []
    if not slug or slug == "_index":
        return issues

    parts = slug.split("-")

    # Consecutive duplicate words: "windows-windows"
    for i in range(len(parts) - 1):
        if parts[i] and parts[i] == parts[i + 1]:
            issues.append(f"Consecutive duplicate word: '{parts[i]}'")
            break

    # Redundant words: same word appears 2+ times (non-consecutive)
    # Stem by stripping trailing 's' on words > 3 chars to catch singular/plural
    stems = [p.rstrip("s") if len(p) > 3 else p for p in parts if p]
    stem_counts = Counter(stems)
    repeated = [w for w, c in stem_counts.items() if c >= 2 and w not in ("to", "for")]
    if repeated:
        issues.append(f"Redundant words: {', '.join(sorted(repeated))}")

    # High stop-word ratio → sentence fragment
    # Exempt short slugs (<=3 parts) and how-to patterns
    if len(parts) > 3 and not slug.startswith("how-to-"):
        stop_count = sum(1 for p in parts if p in SLUG_LEADING_STOP_WORDS)
        ratio = stop_count / len(parts) if parts else 0
        if ratio >= 0.5:
            issues.append(
                f"Sentence fragment: {stop_count}/{len(parts)} words are stop words"
            )

    # OS/platform noise words
    family_kws = set()
    if family:
        fk = extract_family_keyword(family)
        family_kws.update(fk.split("-"))
        family_kws.add(family.lower())
    noise_found = [
        p for p in parts
        if p in _NOISE_WORDS and p not in family_kws
    ]
    if len(noise_found) >= 2:
        issues.append(f"OS/platform noise: {', '.join(noise_found)}")

    return issues


# ---------------------------------------------------------------------------
# Layer 10: extract_slug_core
# ---------------------------------------------------------------------------


def extract_slug_core(text: str, family: str = "", platform: str = "python") -> str:
    """Extract a verb+noun core slug from text.

    Scans for a high-intent verb and the noun phrase following it,
    then combines as ``{verb}-{noun}-{family_keyword}``.

    Args:
        text: Raw text (e.g. workflow title or claim).
        family: Product family identifier.
        platform: Platform identifier.

    Returns:
        Structured slug or empty string if no verb found.
    """
    if not text:
        return ""

    text = strip_html_entities(text)
    words = text.lower().split()

    # Find first high-intent verb
    verb_idx = -1
    verb = ""
    for i, w in enumerate(words):
        # Strip punctuation for matching
        clean = re.sub(r"[^a-z]", "", w)
        if clean in _HIGH_INTENT_VERBS:
            verb_idx = i
            verb = clean
            break

    if verb_idx < 0:
        return ""

    # Collect up to 2 noun words after the verb, skipping stop words
    nouns: list[str] = []
    for w in words[verb_idx + 1:]:
        clean = re.sub(r"[^a-z0-9]", "", w)
        if not clean or clean in SLUG_LEADING_STOP_WORDS:
            continue
        if clean in _NOISE_WORDS:
            continue
        nouns.append(clean)
        if len(nouns) >= 2:
            break

    if not nouns:
        return ""

    family_kw = extract_family_keyword(family) if family else ""
    core = f"{verb}-{'-'.join(nouns)}"

    # Append family keyword if not already present
    if family_kw and family_kw not in core:
        enriched = f"{core}-{family_kw}"
        if len(enriched) <= 50:
            core = enriched

    return core
