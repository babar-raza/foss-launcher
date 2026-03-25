"""Cross-page linker — post-generation linking pass.

Integrates into the Generate worker as Pass 2 (between generation and
rendering). Uses deterministic scoring for link selection and an optional
LLM sandwich for natural anchor text with title fallback.

Design principles:
  - Link selection is pure engineering (deterministic, no LLM)
  - Anchor text uses LLM with deterministic fallback
  - Targets cross-section links (docs<->reference, docs<->kb)
  - Self-determines quantity per page (0 to max_links)
  - Only emits links above min_score threshold
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from launcher.content.template_loader import SECTION_SUBDOMAIN_MAP
from launcher.models.content import CrossLink
from launcher.models.page_ir import BlockIR, BlockType, PageIR, SectionIR
from launcher.shared.jaccard import jaccard_similarity

if TYPE_CHECKING:
    from launcher.models.plan import PlannedPage
    from launcher.models.product import ProductIdentity
    from launcher.orchestrator.worker_contract import WorkerContext

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# TC-FIX-214 / SR-06: subdomain prefix stripping
# ---------------------------------------------------------------------------

_SUBDOMAIN_PREFIX_RE = re.compile(
    r"^/((?:kb|docs|reference|blog|products|releases)\.aspose\.org)/"
)


def strip_subdomain_prefix(url: str) -> str:
    """Strip leading subdomain prefix from a site-relative URL.

    ``/kb.aspose.org/cells/python/faq/`` → ``/cells/python/faq/``

    Only operates on site-relative paths (starting with ``/``).
    Absolute URLs (``https://...``) are returned unchanged.
    """
    return _SUBDOMAIN_PREFIX_RE.sub("/", url)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class PageEntry:
    """Lookup entry for a page in the linker index."""

    page_id: str
    title: str
    url: str
    section: str
    page_role: str
    claim_ids: frozenset[str]
    slug: str = ""  # from PlannedPage.frontmatter["slug"], defaults to page_id
    seo_keywords: frozenset[str] = field(default_factory=frozenset)


@dataclass
class LinkerConfig:
    """Tuning knobs for the linker, loaded from pipeline.yaml."""

    max_links: int = 5
    min_score: float = 0.15
    cross_section_bonus: float = 0.2
    same_section_penalty: float = 0.1


@dataclass
class ScoredLink:
    """A scored candidate link between two pages."""

    source_id: str
    target_id: str
    score: float
    anchor_text: str = ""


# Complementary page-role pairs that get an affinity bonus.
_ROLE_AFFINITY_PAIRS: set[frozenset[str]] = {
    frozenset({"howto_article", "reference_page"}),
    frozenset({"getting_started", "installation"}),
    frozenset({"getting_started", "howto_article"}),
    frozenset({"overview", "reference_page"}),
    frozenset({"faq", "howto_article"}),
    frozenset({"workflow_page", "reference_page"}),
}
_ROLE_AFFINITY_BONUS = 0.1


# ---------------------------------------------------------------------------
# Pure engineering functions (no LLM, no I/O)
# ---------------------------------------------------------------------------

_KEYWORD_OVERLAP_WEIGHT = 0.15


def _jaccard_frozensets(a: frozenset[str], b: frozenset[str]) -> float:
    """Jaccard similarity between two frozensets of strings."""
    if not a or not b:
        return 0.0
    union_size = len(a | b)
    return len(a & b) / union_size if union_size else 0.0


def build_page_index(page_plans: list[PlannedPage]) -> dict[str, PageEntry]:
    """Build a page_id -> PageEntry lookup from planned pages."""
    index: dict[str, PageEntry] = {}
    for pp in page_plans:
        section = infer_section(pp.page_id, pp.frontmatter)
        url = pp.frontmatter.get("url", f"/{pp.content_path}/") if pp.frontmatter else f"/{pp.content_path}/"
        slug = pp.frontmatter.get("slug", pp.page_id) if pp.frontmatter else pp.page_id
        index[pp.page_id] = PageEntry(
            page_id=pp.page_id,
            title=pp.title,
            url=url,
            section=section,
            page_role=pp.page_role,
            claim_ids=frozenset(pp.assigned_claims),
            slug=slug,
            seo_keywords=frozenset(getattr(pp, "seo_keywords", []) or []),
        )
    return index


def score_links(
    page_plans: list[PlannedPage],
    config: LinkerConfig,
) -> dict[str, list[ScoredLink]]:
    """Score all candidate links for each page. Deterministic.

    Algorithm:
      1. Jaccard similarity on assigned_claims (base score)
      2. Cross-section bonus if sections differ
      3. Same-section penalty if same section
      4. Role affinity bonus for complementary page roles
      5. Filter below min_score
      6. Sort descending, cap at max_links
    """
    index = build_page_index(page_plans)
    page_ids = sorted(index.keys())  # deterministic order
    result: dict[str, list[ScoredLink]] = {}

    for src_id in page_ids:
        src = index[src_id]
        # Skip TOC pages — they don't get See Also
        if src.page_role == "toc":
            result[src_id] = []
            continue

        candidates: list[ScoredLink] = []
        for tgt_id in page_ids:
            if tgt_id == src_id:
                continue
            tgt = index[tgt_id]
            # Skip linking to TOC pages
            if tgt.page_role == "toc":
                continue

            # Base: Jaccard on claim sets
            base = jaccard_similarity(src.claim_ids, tgt.claim_ids)

            # SEO keyword overlap bonus
            if src.seo_keywords or tgt.seo_keywords:
                kw_overlap = _jaccard_frozensets(src.seo_keywords, tgt.seo_keywords)
                base += kw_overlap * _KEYWORD_OVERLAP_WEIGHT

            # Cross-section bonus / same-section penalty
            if src.section != tgt.section:
                base += config.cross_section_bonus
            else:
                base -= config.same_section_penalty

            # Role affinity bonus
            role_pair = frozenset({src.page_role, tgt.page_role})
            if role_pair in _ROLE_AFFINITY_PAIRS:
                base += _ROLE_AFFINITY_BONUS

            # Clamp to [0, 1]
            score = max(0.0, min(1.0, base))

            if score >= config.min_score:
                candidates.append(ScoredLink(
                    source_id=src_id,
                    target_id=tgt_id,
                    score=round(score, 4),
                ))

        # Sort descending by score, then by target_id for determinism
        candidates.sort(key=lambda c: (-c.score, c.target_id))
        result[src_id] = candidates[: config.max_links]

    return result


def inject_links(
    page_ir: PageIR,
    links: list[ScoredLink],
    page_index: dict[str, PageEntry],
    source_section: str,
) -> PageIR:
    """Inject See Also section with links into a PageIR.

    - TOC pages: skip (they already have child listings)
    - If See Also SectionIR exists: append link list block
    - If not: create new SectionIR at end
    """
    if page_ir.page_role == "toc" or not links:
        return page_ir

    # Build link items
    items: list[str] = []
    for link in links:
        tgt = page_index.get(link.target_id)
        if tgt is None:
            continue
        url = resolve_link_url(source_section, tgt.section, tgt.url)
        anchor = link.anchor_text or tgt.title
        # Guard: if anchor_text looks like a Python dict repr, use fallback
        if anchor and (anchor.strip().startswith("{") or anchor.strip().startswith("[{")):
            anchor = tgt.title  # use page title as fallback
        items.append(f"[{anchor}]({url})")

    if not items:
        return page_ir

    link_block = BlockIR(type=BlockType.list, items=items)

    # Look for existing See Also section
    sections = list(page_ir.sections)
    see_also_idx = None
    for i, sec in enumerate(sections):
        if sec.section_id == "see_also" or sec.heading.lower().strip() == "see also":
            see_also_idx = i
            break

    if see_also_idx is not None:
        # TC-3896: Replace the See Also section's blocks with the fresh link block.
        # Previously this appended, causing duplicate blocks when the heal loop
        # re-ran the generate worker (each re-run added another link block).
        # Replacing makes inject_links() idempotent: N calls → exactly 1 link block.
        # Preserve any non-list content (author-written prose) before the link block.
        existing = sections[see_also_idx]
        non_link_blocks = [b for b in existing.blocks if b.type != BlockType.list]
        sections[see_also_idx] = existing.model_copy(
            update={"blocks": non_link_blocks + [link_block]},
        )
    else:
        # Create new See Also section
        sections.append(SectionIR(
            section_id="see_also",
            heading="See Also",
            level=2,
            blocks=[link_block],
        ))

    return page_ir.model_copy(update={"sections": sections})


def absolutize_urls(
    page_ir: PageIR,
    source_section: str,
    page_index: dict[str, PageEntry],
) -> PageIR:
    """Convert cross-subdomain relative URLs to absolute in all blocks."""
    # Build a set of known relative URLs and their target sections
    url_to_section: dict[str, str] = {}
    for entry in page_index.values():
        url_to_section[entry.url] = entry.section

    source_host = SECTION_SUBDOMAIN_MAP.get(source_section, "docs.aspose.org")

    def _absolutize(text: str) -> str:
        """Replace relative markdown links that cross subdomains."""
        def _replace_link(m: re.Match) -> str:
            link_text = m.group(1)
            href = m.group(2)
            target_section = url_to_section.get(href)
            if target_section is None:
                return m.group(0)
            target_host = SECTION_SUBDOMAIN_MAP.get(target_section, "docs.aspose.org")
            if target_host != source_host:
                return f"[{link_text}](https://{target_host}{href})"
            return m.group(0)

        return re.sub(r'\[([^\]]+)\]\((/[^)]+)\)', _replace_link, text)

    sections: list[SectionIR] = []
    for sec in page_ir.sections:
        blocks: list[BlockIR] = []
        for block in sec.blocks:
            if block.type == BlockType.paragraph:
                blocks.append(block.model_copy(
                    update={"content": _absolutize(block.content)},
                ))
            elif block.type == BlockType.list:
                blocks.append(block.model_copy(
                    update={"items": [_absolutize(item) for item in block.items]},
                ))
            else:
                blocks.append(block)
        sections.append(sec.model_copy(update={"blocks": blocks}))

    return page_ir.model_copy(update={"sections": sections})


def resolve_link_url(source_section: str, target_section: str, target_url: str) -> str:
    """Resolve a link URL, absolutizing if cross-subdomain."""
    source_host = SECTION_SUBDOMAIN_MAP.get(source_section, "docs.aspose.org")
    target_host = SECTION_SUBDOMAIN_MAP.get(target_section, "docs.aspose.org")
    if source_host != target_host:
        return f"https://{target_host}{target_url}"
    return target_url


# ---------------------------------------------------------------------------
# LLM sandwich for anchor text
# ---------------------------------------------------------------------------

_ANCHOR_PROMPT_TEMPLATE = """\
Generate short, natural anchor text for cross-page links in technical documentation.

Source page: "{source_title}" (role: {source_role})
Product: {product_name}

For each target page below, write a 3-8 word anchor phrase that describes
what the reader will find. Do NOT include URLs, markdown, or the product name.

Targets:
{targets_block}

Respond with a JSON array of strings, one anchor per target, in order.
Example: ["Learn how to install", "Explore the API reference", "Common troubleshooting tips"]
"""


async def generate_anchor_texts(
    scored_links: list[ScoredLink],
    page_index: dict[str, PageEntry],
    context: WorkerContext | None,
    product_name: str = "",
) -> list[ScoredLink]:
    """LLM sandwich for anchor text generation.

    Pre-LLM:  Build prompt with source/target context.
    LLM:      Single batch call for all links from one source page.
    Post-LLM: Validate length, no markdown/URLs. Fallback to title.
    """
    if not scored_links:
        return scored_links

    source_id = scored_links[0].source_id
    source_entry = page_index.get(source_id)
    if source_entry is None:
        return _apply_title_fallback(scored_links, page_index)

    # Pre-LLM: build prompt
    targets_lines: list[str] = []
    for i, link in enumerate(scored_links, 1):
        tgt = page_index.get(link.target_id)
        if tgt:
            targets_lines.append(f"{i}. \"{tgt.title}\" (role: {tgt.page_role})")

    if not targets_lines:
        return _apply_title_fallback(scored_links, page_index)

    prompt = _ANCHOR_PROMPT_TEMPLATE.format(
        source_title=source_entry.title,
        source_role=source_entry.page_role,
        product_name=product_name or "the product",
        targets_block="\n".join(targets_lines),
    )

    # LLM call
    raw_response = None
    if context and context.llm_config:
        try:
            raw_response = await _call_llm_for_anchors(prompt, context)
        except Exception as e:
            logger.warning("[Linker] LLM anchor text call failed: %s", e)

    if not raw_response:
        return _apply_title_fallback(scored_links, page_index)

    # Post-LLM: parse and validate
    anchors = _parse_anchor_response(raw_response, len(scored_links))
    validated_anchors: list[str] = []
    fallback_titles: list[str] = []
    for i, link in enumerate(scored_links):
        tgt = page_index.get(link.target_id)
        fallback_title = tgt.title if tgt else link.target_id
        fallback_titles.append(fallback_title)

        if i < len(anchors):
            validated = _sanitize_anchor_text(anchors[i], fallback_title)
        else:
            validated = fallback_title
        validated_anchors.append(validated)

    # SEO-19: de-duplicate near-identical anchor texts (V2AC-01)
    deduped_anchors = _deduplicate_anchors(validated_anchors, fallback_titles)

    result: list[ScoredLink] = []
    for link, anchor_text in zip(scored_links, deduped_anchors):
        result.append(ScoredLink(
            source_id=link.source_id,
            target_id=link.target_id,
            score=link.score,
            anchor_text=anchor_text,
        ))

    return result


def _apply_title_fallback(
    links: list[ScoredLink],
    page_index: dict[str, PageEntry],
) -> list[ScoredLink]:
    """Apply target page title as anchor text (deterministic fallback)."""
    result: list[ScoredLink] = []
    for link in links:
        tgt = page_index.get(link.target_id)
        result.append(ScoredLink(
            source_id=link.source_id,
            target_id=link.target_id,
            score=link.score,
            anchor_text=tgt.title if tgt else link.target_id,
        ))
    return result


def _parse_anchor_response(raw: str, expected_count: int) -> list[str]:
    """Parse LLM response as JSON array of strings.

    Handles two LLM response formats:
    - Plain strings: ["Frequently asked questions", "Create charts"]
    - Structured dicts: [{"type": "anchor", "text": "FAQ"}, ...]

    When dicts are returned, extract the text field to avoid rendering the
    dict literal as anchor text (TC-3890).
    """
    # Try to find a JSON array in the response
    match = re.search(r'\[.*\]', raw, re.DOTALL)
    if not match:
        return []
    try:
        parsed = json.loads(match.group(0))
        if isinstance(parsed, list):
            result: list[str] = []
            for x in parsed[:expected_count]:
                if isinstance(x, str):
                    result.append(x)
                elif isinstance(x, dict):
                    # LLM returned a structured dict instead of a plain string.
                    # Try common text-field names; fall back to empty string so
                    # _sanitize_anchor_text will use the page title fallback.
                    text = x.get("text") or x.get("anchor") or x.get("label") or ""
                    result.append(str(text))
                else:
                    result.append(str(x))
            return result
    except (json.JSONDecodeError, ValueError):
        pass
    return []


def _sanitize_anchor_text(anchor: str, fallback: str) -> str:
    """Validate and sanitize LLM-generated anchor text: 3-8 words, no markdown/URLs."""
    anchor = anchor.strip().strip('"').strip("'")

    # Reject Python dict/list literals — safety net for TC-3890 (unrendered LLM artifacts).
    # These arise when _parse_anchor_response receives a non-string item and str() is
    # called on it, producing e.g. "{'type': 'anchor', 'text': 'FAQ'}".
    if anchor.startswith(("{", "[{")):
        return fallback

    words = anchor.split()

    # Length check
    if len(words) < 2 or len(words) > 10:
        return fallback

    # No URLs
    if re.search(r'https?://', anchor):
        return fallback

    # No markdown syntax
    if re.search(r'[\[\]()#*`]', anchor):
        return fallback

    return anchor


# ---------------------------------------------------------------------------
# Anchor text quality validation (SEO-19) — TC-3845
# ---------------------------------------------------------------------------

_GENERIC_ANCHORS: frozenset[str] = frozenset({
    "click here", "read more", "learn more", "here", "this", "link",
    "more", "info", "details", "page", "article", "post",
})

# Non-descriptive words used in the "has noun" check.  Anchors consisting
# entirely of these words provide no topical signal to search engines.
_NON_DESCRIPTIVE: frozenset[str] = frozenset({
    "see", "go", "get", "use", "try", "read", "click", "check",
    "find", "view", "open", "look", "take", "make", "run",
    "to", "for", "in", "on", "at", "by", "of", "the", "a", "an",
    "and", "or", "with", "from", "this", "that", "how", "your",
})


def _validate_anchor(text: str) -> bool:
    """Return True if *text* is acceptable as link anchor text.

    Rejects:
    - Empty / too-short text (≤3 chars)
    - Exact matches against *_GENERIC_ANCHORS* (e.g. "click here")
    - All-filler text where no word is both >3 chars and outside
      *_NON_DESCRIPTIVE* (e.g. "go to the for")
    """
    if not text or len(text.strip()) <= 3:
        return False
    lower = text.strip().lower()
    if lower in _GENERIC_ANCHORS:
        return False
    # Descriptive check: require at least one word >3 chars not in _NON_DESCRIPTIVE.
    words = lower.split()
    has_noun = any(w not in _NON_DESCRIPTIVE and len(w) > 3 for w in words)
    if not has_noun:
        return False
    return True


def _check_anchor_diversity(anchors: list[str]) -> bool:
    """Return True if >=50% of anchors are unique (acceptable diversity)."""
    if not anchors:
        return True
    unique = len({a.lower().strip() for a in anchors})
    return unique / len(anchors) >= 0.5


def _deduplicate_anchors(anchors: list[str], fallbacks: list[str]) -> list[str]:
    """Replace near-duplicate anchors with their fallback title (V2AC-01).

    For each anchor, compute word-overlap against all previously accepted anchors.
    If overlap exceeds 0.6, substitute the corresponding fallback title.

    Uses max(|A|, |B|) as denominator to avoid false positives on asymmetric-length
    pairs (e.g. "Install" vs "Install Aspose.Cells" share 1 word; with min
    denominator overlap=1.0 (false dup); with max denominator overlap=0.33 (distinct)).

    Args:
        anchors:   Generated anchor strings (one per link).
        fallbacks: Deterministic fallback strings (target page titles), same length.

    Returns:
        List of accepted anchors; near-duplicates replaced with their fallback.
    """
    if len(anchors) != len(fallbacks):
        return list(anchors)  # length mismatch — return unchanged

    result: list[str] = []
    for i, anchor in enumerate(anchors):
        words_i = set(anchor.lower().split())
        is_dup = False
        for j in range(i):
            words_j = set(result[j].lower().split())
            if not words_i or not words_j:
                continue
            denom = max(len(words_i), len(words_j))
            overlap = len(words_i & words_j) / denom if denom > 0 else 0.0
            if overlap > 0.6:
                is_dup = True
                break
        result.append(fallbacks[i] if is_dup else anchor)
    return result


async def _call_llm_for_anchors(prompt: str, context: WorkerContext) -> str | None:
    """Call LLM for anchor text generation."""
    import os
    from launcher.clients.llm_provider import LLMProviderClient

    if not context.llm_config:
        return None

    api_key = os.environ.get("litellm_key", "")
    client = LLMProviderClient(
        api_base_url=context.llm_config.primary.base_url,
        model=context.llm_config.primary.model,
        run_dir=context.run_dir,
        api_key=api_key,
        temperature=0.0,
        max_tokens=256,
        reasoning_model=(
            context.llm_config.reasoning.model if context.llm_config.reasoning else None
        ),
        routing=context.llm_config.routing,
    )

    messages = [{"role": "user", "content": prompt}]
    loop = asyncio.get_running_loop()
    response = await loop.run_in_executor(
        None, lambda: client.chat_completion(messages, task_type="generate"),
    )
    return response.get("content", "") if isinstance(response, dict) else str(response)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

async def link_pages(
    page_irs: list[PageIR],
    page_plans: list[PlannedPage],
    product: ProductIdentity,
    context: WorkerContext | None = None,
    config: LinkerConfig | None = None,
) -> tuple[list[PageIR], list[CrossLink]]:
    """Full linking pass: score -> anchor text -> inject -> absolutize.

    Returns (linked_page_irs, cross_links).
    """
    if config is None:
        config = LinkerConfig()

    page_index = build_page_index(page_plans)
    scored = score_links(page_plans, config)

    all_cross_links: list[CrossLink] = []
    linked_irs: list[PageIR] = []

    # Process each page
    for page_ir in page_irs:
        pid = page_ir.page_id
        page_links = scored.get(pid, [])
        src_entry = page_index.get(pid)
        source_section = src_entry.section if src_entry else "docs"
        logger.debug("[Linker] %s: %d candidate links", pid, len(page_links))

        # Generate anchor texts (LLM sandwich with fallback)
        if page_links:
            page_links = await generate_anchor_texts(
                page_links, page_index, context,
                product_name=product.display_name,
            )

        # Inject links into PageIR
        linked_ir = inject_links(page_ir, page_links, page_index, source_section)

        # Absolutize cross-subdomain URLs
        linked_ir = absolutize_urls(linked_ir, source_section, page_index)

        linked_irs.append(linked_ir)

        # Build CrossLink manifest entries (use slug for consistency with GeneratedPage)
        src_slug = src_entry.slug if src_entry else pid
        for link in page_links:
            tgt = page_index.get(link.target_id)
            if tgt:
                url = resolve_link_url(source_section, tgt.section, tgt.url)
                all_cross_links.append(CrossLink(
                    source=src_slug,
                    target=tgt.slug,
                    anchor_text=link.anchor_text,
                    url=url,
                    link_type="see_also",
                ))

    # Build TOC -> child cross-links (restores links lost when _build_cross_links was removed)
    toc_links = _build_toc_child_links(page_index)
    all_cross_links.extend(toc_links)

    logger.info(
        "[Linker] Linked %d pages, produced %d cross-links (%d see_also, %d toc_child)",
        len(linked_irs), len(all_cross_links),
        len(all_cross_links) - len(toc_links), len(toc_links),
    )
    return linked_irs, all_cross_links


# ---------------------------------------------------------------------------
# Contextual inline link injection
# ---------------------------------------------------------------------------

def _find_existing_link_spans(text: str) -> list[tuple[int, int]]:
    """Return (start, end) index ranges of existing [anchor](url) links in text.

    Used by inject_contextual_links to skip injection inside already-linked spans
    without relying on a lookbehind regex (which only checks one char).
    """
    spans: list[tuple[int, int]] = []
    for m in re.finditer(r"\[[^\]]*\]\([^)]*\)", text):
        spans.append((m.start(), m.end()))
    return spans


def inject_contextual_links(
    page_ir: "PageIR",
    scored_links: list["ScoredLink"],
    page_index: dict[str, "PageEntry"],
    source_id: str,
    max_inline: int = 2,
) -> tuple["PageIR", list]:
    """Inject inline contextual links into paragraph blocks where topic is mentioned.

    Algorithm:
    1. Build topic->url map from scored_links (title words + keywords)
    2. For each paragraph block, find multi-word title matches (never in code blocks)
    3. Wrap first occurrence in [text](url), skip if already linked
    4. Cap at max_inline total per page
    5. Return modified PageIR (via model_copy) + CrossLink list
    """
    injected_count = 0
    cross_links = []
    new_sections = []

    # Build topic->(url, target_id) map — sorted for determinism
    topic_map: list[tuple[str, str, str]] = []
    for sl in sorted(scored_links, key=lambda s: (-s.score, s.target_id)):
        if sl.source_id != source_id and sl.target_id != source_id:
            continue
        target_id = sl.target_id if sl.source_id == source_id else sl.source_id
        if target_id == source_id:
            continue
        entry = page_index.get(target_id)
        if entry is None:
            continue
        topic_words = entry.title.lower().split()
        if len(topic_words) >= 2:
            topic_map.append((entry.title, entry.url, target_id))

    if not topic_map:
        return page_ir, cross_links

    for section in page_ir.sections:
        new_blocks = []
        for block in section.blocks:
            if injected_count >= max_inline:
                new_blocks.append(block)
                continue
            # Only inject into paragraph blocks
            if block.type != BlockType.paragraph:
                new_blocks.append(block)
                continue
            text = block.content or ""
            modified = text
            for title, url, target_id in topic_map:
                if injected_count >= max_inline:
                    break
                # Find first occurrence not inside an existing [anchor](url) span
                escaped = re.escape(title)
                existing_spans = _find_existing_link_spans(modified)
                pattern = re.compile(escaped, re.IGNORECASE)
                match = None
                for m in pattern.finditer(modified):
                    if not any(s <= m.start() and m.end() <= e for s, e in existing_spans):
                        match = m
                        break
                if match:
                    replacement = f"[{match.group()}]({url})"
                    modified = modified[:match.start()] + replacement + modified[match.end():]
                    injected_count += 1
                    cross_links.append({"source_id": source_id, "target_id": target_id, "link_type": "contextual"})
                    break  # one link per block
            if modified != text:
                block = block.model_copy(update={"content": modified})
            new_blocks.append(block)
        new_sections.append(section.model_copy(update={"blocks": new_blocks}))

    new_page_ir = page_ir.model_copy(update={"sections": new_sections})
    return new_page_ir, cross_links


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_toc_child_links(page_index: dict[str, PageEntry]) -> list[CrossLink]:
    """Build TOC -> child cross-links for every TOC page.

    A TOC page's children are non-TOC pages in the same section.
    """
    toc_pages = [e for e in page_index.values() if e.page_role == "toc"]
    links: list[CrossLink] = []
    for toc in toc_pages:
        children = [
            e for e in page_index.values()
            if e.page_id != toc.page_id
            and e.section == toc.section
            and e.page_role != "toc"
        ]
        for child in sorted(children, key=lambda c: c.page_id):
            links.append(CrossLink(
                source=toc.slug,
                target=child.slug,
                anchor_text=child.title,
                url=child.url,
                link_type="toc_child",
            ))
    return links


def infer_section(page_id: str, frontmatter: dict[str, Any] | None = None) -> str:
    """Infer site section from page_id (e.g., 'docs-install' -> 'docs').

    Falls back to frontmatter["section"] if no dash in page_id, then "docs".
    """
    if "-" in page_id:
        return page_id.split("-", 1)[0]
    if frontmatter:
        return frontmatter.get("section") or "docs"
    return "docs"


def load_linker_config(pipeline_config: dict[str, Any]) -> LinkerConfig:
    """Load LinkerConfig from pipeline.yaml's linker section."""
    raw = pipeline_config.get("linker", {})
    return LinkerConfig(
        max_links=raw.get("max_links", 5),
        min_score=raw.get("min_score", 0.15),
        cross_section_bonus=raw.get("cross_section_bonus", 0.2),
        same_section_penalty=raw.get("same_section_penalty", 0.1),
    )
