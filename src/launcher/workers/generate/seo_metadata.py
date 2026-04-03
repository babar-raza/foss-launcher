"""Post-generation SEO metadata optimization (Phase 1.5).

Runs after LLM generation, before cross-linking/rendering.
All operations are deterministic string ops except optional Gemini calls.

TC-3810: Created for v2 SEO module.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Protocol, runtime_checkable

from launcher.models.claims import Claim
from launcher.models.page_ir import PageIR
from launcher.models.product import ProductIdentity
from launcher.shared.slug_engine import strip_html_entities, extract_family_keyword

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Protocol types for type safety (SEO-03)
# ------------------------------------------------------------------


@runtime_checkable
class KeywordBundleLike(Protocol):
    """Structural type for keyword research bundles."""
    primary_keywords: list[str]
    per_page: dict[str, list[str]]


@runtime_checkable
class GeminiClientLike(Protocol):
    """Structural type for Gemini SEO client."""
    @property
    def available(self) -> bool: ...
    def generate_description(
        self, title: str, product_name: str, claims_summary: str,
    ) -> str: ...


# Shared stop-word set for SEO keyword extraction (SEO-04).
# TC-SEO-601: Expanded with common 4+ char function words and domain-generic nouns
# that appear in every page and provide no discriminating SEO value.
SEO_STOP_WORDS: frozenset[str] = frozenset({
    # Original: articles, conjunctions, prepositions, basic verbs
    "a", "an", "the", "and", "but", "or", "for", "in", "on", "to",
    "of", "is", "it", "by", "at", "as", "how", "with", "this", "that",
    "can", "be", "are", "was", "has", "have", "not", "from", "table",
    # TC-SEO-601: Common 4+ char function words missed by original set
    "when", "then", "also", "into", "more", "over", "such", "been",
    "will", "your", "they", "them", "these", "what", "some", "very",
    "just", "each", "both", "than", "only", "well", "here", "does",
    "were", "even", "used", "uses", "which", "while", "about",
    "their", "there", "where", "after", "other", "would", "could",
    "should", "using", "being", "those", "every", "under", "between",
    # TC-SEO-601: Domain-generic technical nouns that appear on every Aspose page
    "code", "data", "page", "file", "docs", "type", "time", "list",
    "item", "make", "need", "want", "note", "work", "like", "take",
})

# TC-HEAL-005: Patterns that identify question-style or irrelevant search queries
# that should never appear in product documentation keyword lists.
# These typically come from external keyword research tools that include
# informational/navigational queries alongside commercial/product queries.
_KEYWORD_REJECT_PATTERNS: tuple[re.Pattern[str], ...] = (
    # Question-opener patterns — informational queries not suitable for doc keywords
    re.compile(r"^\s*(is|are|can|how|what|why|when|where|which|does|do|did)\s", re.IGNORECASE),
    # Commercial/comparison signals — not relevant to product docs
    re.compile(r"\b(cost|price|pricing|versus|alternative|symptoms?)\b", re.IGNORECASE),
    # "vs " comparison shorthand (require trailing space to avoid "vs." at end)
    re.compile(r"\bvs\s", re.IGNORECASE),
    # Comparison phrasing
    re.compile(r"difference\s+between", re.IGNORECASE),
    # NOTE: "\bsafe\b" intentionally omitted — "is X safe" is caught by the
    # question-opener above; standalone "safe" causes false positives on
    # legitimate doc keywords like "thread-safe", "type-safe", "fail-safe".
)


def _is_irrelevant_keyword(kw: str) -> bool:
    """Return True if a keyword is a question-pattern or irrelevant search query.

    TC-HEAL-005: Filters out informational/navigational queries that harm SEO
    relevance and credibility when they appear in product documentation frontmatter.
    Only rejects keywords that clearly match question or comparison patterns —
    product-specific terms like "dotnet 3d library" are always accepted.
    """
    return any(p.search(kw) for p in _KEYWORD_REJECT_PATTERNS)


# Subdomain map for canonical URL construction.
_SUBDOMAIN_MAP: dict[str, str] = {
    "docs": "docs.aspose.org",
    "reference": "reference.aspose.org",
    "kb": "kb.aspose.org",
    "blog": "blog.aspose.org",
    "products": "products.aspose.org",
}
# Reverse map: full subdomain -> short key (for URLs that include subdomain as path).
_SUBDOMAIN_REVERSE: dict[str, str] = {v: k for k, v in _SUBDOMAIN_MAP.items()}


def _calculate_reading_time(word_count: int, words_per_minute: int = 200) -> int:
    """Return estimated reading time in minutes (minimum 1)."""
    return max(1, round(word_count / words_per_minute))


def _inject_freshness_dates(fm: dict, *, update_lastmod: bool = True) -> dict:
    """Add date/lastmod/datePublished/dateModified to frontmatter.

    - date: set once on first generation, never overwritten if already present
    - lastmod: updated to current UTC time only when *update_lastmod* is True,
      or when lastmod is absent/empty (first generation always sets it).
      Pass update_lastmod=False for idempotent re-runs where content has not
      changed, to prevent spurious git diffs and CDN cache invalidation.
    - datePublished: mirrors date
    - dateModified: mirrors lastmod
    Always use UTC and ISO 8601 format YYYY-MM-DDTHH:MM:SSZ.
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if "date" not in fm or not fm["date"]:
        fm["date"] = now
    if update_lastmod or not fm.get("lastmod"):
        fm["lastmod"] = now
    fm["datePublished"] = fm["date"]
    fm["dateModified"] = fm["lastmod"]
    return fm


def optimize_seo_metadata(
    page_ir: PageIR,
    product: ProductIdentity,
    claims: list[Claim],
    keyword_bundle: KeywordBundleLike | None = None,
    gemini_client: GeminiClientLike | None = None,
    *,
    subdomain_map: dict[str, str] | None = None,
    update_lastmod: bool = True,
) -> PageIR:
    """Post-generation SEO optimization of all frontmatter fields.

    Uses Gemini for high-quality descriptions when available,
    falls back to heuristic chain otherwise.

    Returns a new PageIR with updated frontmatter.
    """
    fm = dict(page_ir.frontmatter)

    # 1. Sanitize title first (fixes entity cascade bug).
    title = fm.get("title", page_ir.title)
    title = _sanitize_title(title)
    fm["title"] = title

    # 2. Generate seoTitle (distinct from title, <=60 chars).
    seo_title = _generate_seo_title(title, product.display_name)
    # TC-3882 Wave 4 (F2): Fallback when title is non-empty but seoTitle generation returns empty.
    if not seo_title and title:
        seo_title = title[:55].strip()
    fm["seoTitle"] = seo_title

    # 3. Generate description (priority chain).
    description = _generate_description(
        page_ir, product, claims, gemini_client,
    )
    if description:
        fm["description"] = description

    # 4. Canonical URL.
    url = fm.get("url", "")
    slug_for_canonical = fm.get("slug", "") or getattr(page_ir, "slug", "") or ""
    if url:
        canonical = _generate_canonical(url, page_ir.page_role, subdomain_map=subdomain_map)
    else:
        # TC-3882 Wave 4 (F2): Fallback: build canonical from slug when url is empty.
        canonical = _canonical_from_slug(slug_for_canonical, page_ir.page_role)
    if canonical:
        fm["canonical"] = canonical

    # 5. Robots directive.
    fm["robots"] = _robots_directive(page_ir.page_role, fm.get("slug", ""))

    # 6. Enhance keywords.
    existing_kw = fm.get("keywords", []) or []
    if isinstance(existing_kw, str):
        existing_kw = [k.strip() for k in existing_kw.split(",") if k.strip()]
    enhanced = _enhance_keywords(
        existing_kw, claims, product.family, keyword_bundle,
    )
    # TC-NET-004: Remove keywords that belong to competing platforms so that,
    # e.g., "python slides" never appears in a .NET page's frontmatter.
    _platform = getattr(product, "platform", "") or ""
    fm["keywords"] = _filter_platform_keywords(enhanced, _platform)

    # 7. Final quality enforcement.
    fm = _enforce_metadata_quality(fm)

    # 8. Inject freshness dates (date/lastmod/datePublished/dateModified).
    fm = _inject_freshness_dates(fm, update_lastmod=update_lastmod)

    # 9. Reading time estimate (TC-3846).
    try:
        desc_words = len(str(fm.get("description") or "").split())
        fm["reading_time"] = _calculate_reading_time(desc_words + 200)  # base estimate
    except Exception:
        pass

    # TC-3873 W1-S4: Final completeness guarantee for all required SEO fields.
    fm = _ensure_required_seo_fields(fm, page_ir.page_role, product.display_name or "")

    return page_ir.model_copy(update={"frontmatter": fm})


# ------------------------------------------------------------------
# Internal functions
# ------------------------------------------------------------------


def _sanitize_title(title: str) -> str:
    """Strip HTML entities and normalize whitespace in title."""
    if not title:
        return title
    cleaned = strip_html_entities(title)
    # Collapse multiple spaces.
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _generate_seo_title(
    title: str, product_name: str, max_len: int = 60,
) -> str:
    """Generate an seoTitle distinct from title, <=max_len chars.

    If product short name not in title, prepend it.
    If result == title, append differentiator.
    """
    if not title:
        return ""

    # Short product name: before " for " (e.g. "Aspose.Cells FOSS")
    short_product = product_name.split(" for ")[0] if product_name else ""

    result = title
    # Prepend product name if missing.
    if short_product and short_product.lower() not in title.lower():
        candidate = f"{short_product} {title}"
        if len(candidate) <= max_len:
            result = candidate

    # Truncate at word boundary if too long.
    if len(result) > max_len:
        truncated = result[:max_len]
        last_space = truncated.rfind(" ")
        if last_space > max_len // 2:
            result = truncated[:last_space]
        else:
            result = truncated

    # Ensure distinct from title.
    if result == title:
        # Avoid doubling product name in the suffix.
        if short_product and short_product.lower() not in title.lower():
            suffix = f" | {short_product}"
        else:
            suffix = " | Guide"
        if len(result) + len(suffix) <= max_len:
            result = result + suffix

    return result.strip()


def _generate_description(
    page_ir: PageIR,
    product: ProductIdentity,
    claims: list[Claim],
    gemini_client: GeminiClientLike | None = None,
    max_len: int = 160,
) -> str:
    """Generate a meta description using priority chain.

    Priority:
    1. Gemini-generated (if available)
    2. Purpose field from frontmatter
    3. Content extraction (sentences 2-3 from first paragraph)
    4. Claim-derived (first claim text)
    5. Template fallback
    """
    page_id = getattr(page_ir, "page_id", "unknown")
    title = page_ir.frontmatter.get("title", page_ir.title)

    # 1. Gemini-generated.
    if gemini_client is not None and getattr(gemini_client, "available", False):
        try:
            claims_summary = "; ".join(c.text[:80] for c in claims[:5])
            desc = gemini_client.generate_description(
                title, product.display_name, claims_summary,
            )
            if desc and 50 <= len(desc) <= max_len:
                logger.debug("[SEO] %s: description source=gemini", page_id)
                return desc
        except Exception:
            logger.debug("[SEO] Gemini description failed, falling through", exc_info=True)

    # 2. Purpose field.
    purpose = page_ir.frontmatter.get("purpose", "")
    if purpose and len(purpose) >= 50:
        logger.debug("[SEO] %s: description source=purpose", page_id)
        return _truncate_description(purpose, max_len)

    # 3. Content extraction from first paragraph block.
    desc = _extract_from_content(page_ir)
    if desc and len(desc) >= 50:
        logger.debug("[SEO] %s: description source=content", page_id)
        return _truncate_description(desc, max_len)

    # 4. Claim-derived.
    if claims:
        claim_text = claims[0].text
        sentences = re.split(r"(?<=[.!?])\s+", claim_text)
        if sentences:
            first_sentence = sentences[0]
            if len(first_sentence) >= 30:
                desc = f"{product.display_name}: {first_sentence}"
                logger.debug("[SEO] %s: description source=claim", page_id)
                return _truncate_description(desc, max_len)

    # 5. Template fallback.
    family_kw = extract_family_keyword(product.family)
    desc = f"{product.display_name} {family_kw} library: {title}"
    logger.debug("[SEO] %s: description source=template", page_id)
    return _truncate_description(desc, max_len)


def _extract_from_content(page_ir: PageIR) -> str:
    """Extract sentences 2-3 from the first paragraph block."""
    for section in page_ir.sections:
        for block in section.blocks:
            if block.type.value == "paragraph" and block.content:
                sentences = re.split(r"(?<=[.!?])\s+", block.content)
                # Take sentences 2-3 (skip the lead sentence).
                relevant = [s for s in sentences[1:3] if len(s) >= 20]
                if relevant:
                    return " ".join(relevant)
    return ""


def _truncate_description(text: str, max_len: int = 160) -> str:
    """Truncate text to max_len at word boundary."""
    text = strip_html_entities(text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= max_len:
        return text
    truncated = text[:max_len - 3]
    last_space = truncated.rfind(" ")
    if last_space > max_len // 2:
        return truncated[:last_space] + "..."
    return truncated + "..."


def _canonical_from_slug(slug: str, page_role: str) -> str:
    """Construct canonical URL from slug when the URL field is empty.

    TC-3882 Wave 4 (F2): Fallback for pages where the planner didn't populate
    the url frontmatter field. Maps page_role to the correct subdomain.
    """
    if not slug:
        return ""
    _ROLE_SUBDOMAIN: dict[str, str] = {
        "api_reference": "reference",
        "reference_object_page": "reference",
        "blog_post": "blog",
    }
    section = _ROLE_SUBDOMAIN.get(page_role, "docs")
    subdomain = _SUBDOMAIN_MAP.get(section, "docs.aspose.org")
    clean_slug = slug.strip("/")
    return f"https://{subdomain}/{clean_slug}/"


def _generate_canonical(
    url: str,
    page_role: str,
    *,
    subdomain_map: dict[str, str] | None = None,
) -> str:
    """Construct canonical URL from page URL and role."""
    if not url:
        return ""

    sd_map = subdomain_map or _SUBDOMAIN_MAP
    sd_reverse = {v: k for k, v in sd_map.items()}

    # Detect section from URL path.
    parts = [p for p in url.strip("/").split("/") if p]
    section = "docs"  # default

    if page_role in ("api_reference", "reference_object_page"):
        section = "reference"
    elif parts:
        first = parts[0].lower()
        if first in sd_map:
            section = first
        elif first in sd_reverse:
            section = sd_reverse[first]

    subdomain = sd_map.get(section, sd_map.get("docs", "docs.aspose.org"))

    # Build path (skip the section prefix if it matches — either short key or full subdomain).
    path_parts = parts
    if path_parts:
        first_lower = path_parts[0].lower()
        if first_lower == section or first_lower in sd_reverse:
            path_parts = path_parts[1:]

    path = "/".join(path_parts)
    return f"https://{subdomain}/{path}/"


def _robots_directive(page_role: str, slug: str) -> str:
    """Determine robots directive for a page."""
    if slug == "_index" or page_role == "toc":
        return "noindex, follow"
    return "index, follow"


def _enhance_keywords(
    existing: list[str],
    claims: list[Claim],
    family: str,
    keyword_bundle: KeywordBundleLike | None = None,
) -> list[str]:
    """Enrich page keywords from multiple sources, capped at 8."""
    seen: set[str] = set()
    result: list[str] = []

    def _add(kw: str) -> None:
        key = kw.lower().strip()
        # TC-HEAL-005: Skip question-pattern and irrelevant search queries.
        if key and key not in seen and not _is_irrelevant_keyword(kw):
            seen.add(key)
            result.append(kw.strip())

    # 1. Existing keywords (from Planner).
    for kw in existing:
        _add(kw)

    # 2. Primary keywords from research bundle.
    if keyword_bundle is not None:
        for kw in getattr(keyword_bundle, "primary_keywords", []) or []:
            _add(kw)

    # 3. Claim-derived terms (top significant words from claims).
    word_freq: dict[str, int] = {}
    for claim in claims[:20]:
        words = claim.text.lower().split()
        for w in words:
            w = re.sub(r"[^a-z0-9]", "", w)
            if w and len(w) > 3 and w not in SEO_STOP_WORDS:
                word_freq[w] = word_freq.get(w, 0) + 1
    # TC-SEO-602: require frequency >= 2 to exclude single-occurrence jargon.
    top_claim_words = sorted(
        (w for w in word_freq if word_freq[w] >= 2),
        key=word_freq.get,
        reverse=True,
    )[:3]
    for w in top_claim_words:
        _add(w)

    # 4. Family keyword.
    family_kw = extract_family_keyword(family)
    if family_kw != "files":
        _add(family_kw)

    return result[:8]


# TC-NET-004: Terms that must not appear in keywords for each platform.
# Each entry is a frozenset of lowercase substrings to reject.
_PLATFORM_REJECT_TERMS: dict[str, frozenset[str]] = {
    "dotnet":     frozenset({"python", "pip ", "java ", "npm ", "nodejs", "typescript"}),
    "python":     frozenset({"dotnet", "csharp", "nuget", "java ", "npm ", "nodejs"}),
    "java":       frozenset({"python", "pip ", "dotnet", "csharp", "nuget", "npm "}),
    "typescript": frozenset({"python", "pip ", "java ", "dotnet", "csharp", "nuget"}),
    "cpp":        frozenset({"python", "pip ", "java ", "dotnet", "csharp", "npm "}),
}


def _filter_platform_keywords(keywords: list[str], platform: str) -> list[str]:
    """Remove keywords containing terms from competing platforms (TC-NET-004).

    For example, "python slides" is filtered out of a .NET page's keywords.
    """
    reject = _PLATFORM_REJECT_TERMS.get(platform, frozenset())
    if not reject:
        return keywords
    return [kw for kw in keywords if not any(r in kw.lower() for r in reject)]


def _enforce_metadata_quality(fm: dict) -> dict:
    """Final quality enforcement on all SEO metadata fields.

    Returns a new dict (shallow copy); does NOT mutate the input (SEO-04).
    """
    fm = dict(fm)  # Shallow copy — do not mutate caller's dict.
    title = fm.get("title", "")
    seo_title = fm.get("seoTitle", "")
    description = fm.get("description", "")

    # seoTitle must differ from title.
    if seo_title and seo_title == title:
        fm["seoTitle"] = seo_title + " | Guide"

    # Description length bounds.
    if description:
        if len(description) > 160:
            fm["description"] = _truncate_description(description, 160)
        elif len(description) < 50:
            # Too short — clear it so downstream can regenerate.
            fm["description"] = ""

    # Description must differ from title and seoTitle.
    if description and (description == title or description == seo_title):
        fm["description"] = ""

    # Final HTML entity sweep on all text fields.
    for key in ("title", "seoTitle", "description"):
        val = fm.get(key, "")
        if val and isinstance(val, str):
            cleaned = strip_html_entities(val)
            if cleaned != val:
                fm[key] = cleaned

    return fm

def _ensure_required_seo_fields(
    fm: dict,
    page_role: str,
    display_name: str = "",
) -> dict:
    """Guarantee all required SEO fields are present. Called unconditionally as final step.

    TC-3873 W1-S4: Post-LLM engineering fix to ensure completeness of SEO metadata.
    """
    title = fm.get("title", "") or ""

    # seoTitle: required, <=55 chars
    if not fm.get("seoTitle"):
        fm["seoTitle"] = title[:55]

    # robots: required
    if not fm.get("robots"):
        _noindex_roles = {"toc", "index", "sitemap"}
        fm["robots"] = "noindex" if page_role in _noindex_roles else "index, follow"

    # canonical: must start with https://
    canonical = fm.get("canonical", "")
    if not canonical or not str(canonical).startswith("https://"):
        slug = fm.get("slug", "")
        if slug:
            fm["canonical"] = f"https://docs.aspose.org/{slug.lstrip('/')}"

    # keywords: need >=3
    kws = fm.get("keywords") or []
    if isinstance(kws, list) and len(kws) < 3 and display_name:
        extra_tokens = [w.lower() for w in display_name.split() if len(w) > 3]
        combined = list(dict.fromkeys(kws + extra_tokens))
        fm["keywords"] = combined[:10]

    # description: required, <=160 chars
    if not fm.get("description"):
        base = f"{display_name}: {title}" if display_name else title
        if base:
            fm["description"] = base[:160]

    return fm
