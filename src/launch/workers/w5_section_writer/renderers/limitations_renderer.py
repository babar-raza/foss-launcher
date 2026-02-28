"""Limitations section renderer — structured JSON + freeform curation.

Feature flag: LAUNCH_STRUCTURED_LIMITATIONS=json|freeform (default: freeform)
In json mode: LLM generates JSON, this module parses + renders deterministic markdown.
In freeform mode (default): curate_freeform_limitations() deduplicates, groups, and
caps raw claim bullets into readable markdown (TC-2910).
Falls back to freeform on any parse/validation failure.
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

_STRUCTURED_MODE = os.environ.get("LAUNCH_STRUCTURED_LIMITATIONS", "freeform")

LLM_JSON_PROMPT_ADDENDUM = (
    "\n\nCRITICAL: Output ONLY a JSON array using this EXACT schema:\n"
    '[{"title": "Short title (max 10 words)", "description": "One to two sentences.", "workaround": "Workaround or null"}]\n'
    "No prose, no explanation, no code fences. Start with [ and end with ]."
)


def is_structured_mode() -> bool:
    """True when LAUNCH_STRUCTURED_LIMITATIONS=json."""
    return _STRUCTURED_MODE == "json"


def parse_limitations_json(raw: str) -> Optional[List[Dict[str, Any]]]:
    """Extract and validate JSON limitations array from LLM output.

    Handles:
      - Bare JSON array: [{"title": ...}]
      - JSON inside ```json ... ``` or ``` ... ``` fences
      - Leading/trailing prose (finds first [ ... ] pair)
      - Null workaround values

    Returns None on any parse or validation failure (caller should fall back to freeform).
    """
    if not raw or not raw.strip():
        return None

    text = raw.strip()

    # Strip code fence if present
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if fence_match:
        text = fence_match.group(1).strip()

    # Find outermost JSON array bounds
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end <= start:
        return None

    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None

    if not isinstance(data, list):
        return None

    validated = []
    for item in data:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "")).strip()
        description = str(item.get("description", "")).strip()
        # Minimum length validation
        if len(title) < 3 or len(description) < 10:
            continue
        workaround = item.get("workaround")
        if workaround is not None:
            workaround = str(workaround).strip() or None
        validated.append({
            "title": title,
            "description": description,
            "workaround": workaround,
        })

    return validated if validated else None


def render_limitations_to_markdown(
    items: List[Dict[str, Any]],
    product_name: str,
    claim_ids: Optional[List[str]] = None,
) -> str:
    """Render validated limitations list to deterministic markdown.

    Args:
        items: Validated list from parse_limitations_json()
        product_name: Used in introductory sentence
        claim_ids: Optional claim IDs to embed as HTML comment markers

    Returns:
        Deterministic markdown string (same input -> same output, always)
    """
    if not items:
        return f"No verified limitations documented in sources for {product_name}."

    lines = [f"Known limitations and constraints for {product_name}:\n"]

    for i, item in enumerate(items):
        lines.append(f"**{item['title']}**")
        lines.append(f"{item['description']}")
        if item.get("workaround"):
            lines.append(f"*Workaround*: {item['workaround']}")
        if claim_ids and i < len(claim_ids) and claim_ids[i]:
            lines.append(f"<!-- claim: {claim_ids[i]} -->")
        lines.append("")

    return "\n".join(lines).rstrip()


# ---------------------------------------------------------------------------
# TC-2910: Freeform curation constants
# ---------------------------------------------------------------------------
MAX_CURATED_BULLETS = 6
MAX_SECTION_CHARS = 1200
DEDUP_SIMILARITY_THRESHOLD = 0.75
MIN_GROUP_SIZE = 3

_DOES_NOT_SUPPORT_RE = re.compile(
    r"^(.+?)\s+does not yet support\s+(.+)$", re.IGNORECASE
)


def _dedup_bullets(
    bullets: List[Tuple[str, str]],
    product_name: str,
) -> List[Tuple[str, List[str]]]:
    """Deduplicate sanitized bullets, merging citation IDs for near-duplicates.

    Args:
        bullets: List of (sanitized_text, claim_id) tuples.
        product_name: Used to strip shared product-name tokens from comparison.

    Returns:
        List of (sanitized_text, [claim_id, ...]) with near-dupes merged.
    """
    from launch.workers._shared.jaccard import jaccard_similarity, _tokenize

    product_tokens: Set[str] = set(_tokenize(product_name.lower()))
    accepted: List[Tuple[str, List[str], Set[str]]] = []

    for text, cid in bullets:
        tokens = set(_tokenize(text.lower())) - product_tokens
        merged = False
        for i, (_, ids, existing_tokens) in enumerate(accepted):
            sim = jaccard_similarity(tokens, existing_tokens)
            if sim >= DEDUP_SIMILARITY_THRESHOLD:
                ids.append(cid)
                merged = True
                break
        if not merged:
            accepted.append((text, [cid], tokens))

    return [(text, ids) for text, ids, _ in accepted]


def _group_by_prefix(
    bullets: List[Tuple[str, str]],
    product_name: str,
    *,
    min_group_size: int = MIN_GROUP_SIZE,
) -> Tuple[List[Tuple[str, List[str]]], List[Tuple[str, str]]]:
    """Partition bullets by 'does not yet support' prefix pattern.

    If 3+ bullets match, merge into a single summary bullet listing methods.
    Returns (grouped_results, remaining_bullets) where remaining_bullets
    are those that didn't match the prefix pattern and still need dedup.
    """
    support_items: List[Tuple[str, str, str]] = []  # (method, text, claim_id)
    other_items: List[Tuple[str, str]] = []  # (text, claim_id)

    for text, cid in bullets:
        m = _DOES_NOT_SUPPORT_RE.match(text)
        if m:
            method = m.group(2).rstrip(".")
            support_items.append((method, text, cid))
        else:
            other_items.append((text, cid))

    grouped: List[Tuple[str, List[str]]] = []

    if len(support_items) >= min_group_size:
        methods = [name for name, _, _ in support_items]
        all_cids = [cid for _, _, cid in support_items]
        if len(methods) <= 5:
            method_list = ", ".join(methods[:-1]) + f", and {methods[-1]}"
        else:
            method_list = ", ".join(methods[:4]) + f", and {len(methods) - 4} others"
        grouped_text = (
            f"Several API methods are not yet implemented, "
            f"including {method_list}."
        )
        grouped.append((grouped_text, all_cids))
    else:
        # Too few to group — return as remaining for dedup
        for _, text, cid in support_items:
            other_items.append((text, cid))

    return grouped, other_items


def _enforce_caps(
    grouped: List[Tuple[str, List[str]]],
    max_bullets: int,
    max_section_chars: int,
) -> List[Tuple[str, List[str]]]:
    """Enforce maximum bullet count and total character budget."""
    result: List[Tuple[str, List[str]]] = []
    total_chars = 0
    for text, cids in grouped[:max_bullets]:
        line_cost = len(text) + 4  # "- " prefix + newline + claim comment
        if total_chars + line_cost > max_section_chars and result:
            break
        result.append((text, cids))
        total_chars += line_cost
    return result


def curate_freeform_limitations(
    claims: List[Dict[str, Any]],
    product_name: str,
    *,
    max_bullets: int = MAX_CURATED_BULLETS,
    max_section_chars: int = MAX_SECTION_CHARS,
) -> str:
    """Curate freeform limitation claims into grouped, deduplicated markdown.

    TC-2910: Pipeline — pre-filter, sanitize, dedup, group, cap, render.

    Args:
        claims: Raw claim dicts with claim_id, claim_text, optional enriched_text.
        product_name: Product display name for intro sentence.
        max_bullets: Maximum rendered bullet points (default 6).
        max_section_chars: Maximum total section character count (default 1200).

    Returns:
        Rendered markdown with intro line, bullets, and claim comment markers.
    """
    if not claims:
        return "No known limitations at this time."

    # Lazy imports to avoid circular dependency (content_generators imports us)
    from ..generators.content_generators import (
        _is_user_facing_claim,
        _get_display_text,
        _sanitize_limitation_bullet,
    )
    from ..worker import _smart_truncate, MAX_CLAIM_FILTER_LENGTH, MAX_BULLET_LEN

    # Stage 1: Pre-filter and sanitize
    sanitized_bullets: List[Tuple[str, str]] = []  # (text, claim_id)
    for claim in claims:
        raw_text = claim.get("claim_text", "")
        if len(raw_text) > MAX_CLAIM_FILTER_LENGTH:
            continue
        if not _is_user_facing_claim(claim):
            continue
        display = _get_display_text(claim)
        bullet = _sanitize_limitation_bullet(display)
        if bullet is None:
            continue
        max_body = MAX_BULLET_LEN - 2
        if len(bullet) > max_body:
            bullet = _smart_truncate(bullet, max_body)
        sanitized_bullets.append((bullet, claim.get("claim_id", "")))

    if not sanitized_bullets:
        return "No verified limitations found in sources."

    # Stage 2: Group by prefix (structural, before dedup)
    grouped, remaining = _group_by_prefix(sanitized_bullets, product_name)

    # Stage 3: Dedup remaining (non-grouped) bullets
    deduped = _dedup_bullets(remaining, product_name)

    # Stage 4: Combine grouped + deduped, then cap
    combined = grouped + deduped
    capped = _enforce_caps(combined, max_bullets, max_section_chars)

    # Stage 5: Render
    lines = [f"Known limitations and constraints for {product_name}:", ""]
    for text, cids in capped:
        lines.append(f"- {text}")
        for cid in cids:
            if cid:
                lines.append(f"<!-- claim: {cid} -->")

    logger.info(
        "[W5] Curated %d limitation claims -> %d bullets (from %d raw)",
        len(claims), len(capped), len(sanitized_bullets),
    )

    return "\n".join(lines)
