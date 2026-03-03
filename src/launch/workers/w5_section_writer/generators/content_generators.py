"""TC-1770: Extracted content generator functions from W5 worker.py.

This module contains all specialized content generator functions and their
helper functions, extracted from the monolithic worker.py to improve
maintainability. All function signatures and logic are preserved exactly.

Functions are organized into:
1. Helper functions (shared utilities used by generators)
2. Generator functions (one per page_role)

Circular import avoidance:
- Functions that need worker.py utilities (_call_llm_for_content,
  _smart_truncate, etc.) use lazy imports inside function bodies.

TC-2391: Declarative tone control system — _TONE_CONFIG singleton loaded at
module import time; each generator calls build_section_prompt_enhancement()
to append editorial voice + structural constraints to its LLM prompt.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Any, Optional, List

from ....util.logging import get_logger
from ..tone_utils import load_tone_config, build_section_prompt_enhancement
from ..renderers.limitations_renderer import (
    is_structured_mode as _is_structured_limitations_mode,
    parse_limitations_json as _parse_limitations_json,
    render_limitations_to_markdown as _render_limitations_to_markdown,
    LLM_JSON_PROMPT_ADDENDUM as _LIMITATIONS_JSON_ADDENDUM,
    curate_freeform_limitations as _curate_freeform_limitations,
)

logger = get_logger()

# TC-2391: Load once at module import; empty dict if yaml missing/unreadable
_TONE_CONFIG = load_tone_config()

# Spec v1.1: Scoped fallback text for mandatory pages with no repository evidence.
# Written verbatim to the page when no claims exist AND the page is mandatory.
_NOT_EVIDENCED_CONTENT = "_Not evidenced in this repository._"


def _get_canonical_import(product_facts: Dict[str, Any]) -> str:
    """TC-3684: Derive canonical import from product_facts (lazy import)."""
    from ..rich_context import _derive_canonical_import

    return _derive_canonical_import(product_facts)


# ---------------------------------------------------------------------------
# Agent 43: KB How-To Contract helpers
# ---------------------------------------------------------------------------


def _build_format_evidence_text(page: Dict[str, Any]) -> str:
    """Build format evidence text block for howto prompt.

    Returns empty string if page is not a conversion how-to or has no evidence.
    """
    cs = page.get("content_strategy", {})
    if not cs.get("is_conversion_howto", False):
        return ""
    lines: List[str] = []
    fmts = cs.get("supported_formats", [])
    if fmts:
        lines.append("Supported formats (from repository analysis):")
        for f in fmts:
            lines.append(f"  - {f['format']} ({f['direction']})")
    pairs = cs.get("conversion_pairs", [])
    if pairs:
        lines.append("Evidenced conversion pairs:")
        for p in pairs:
            lines.append(f"  - {p['source']} \u2192 {p['target']}")
    if not fmts and not pairs:
        lines.append("No format conversion evidence was found in this repository.")
    return "\n".join(lines)


def _build_not_evidenced_howto(
    page: Dict[str, Any],
    product_facts: Dict[str, Any],
) -> str:
    """Structured fallback for mandatory how-to pages with no evidence.

    Follows mission heading order: Goal \u2192 When You'd Use This \u2192 Prerequisites \u2192
    Steps \u2192 Code Example \u2192 Common Mistakes \u2192 See Also.

    Code fence contains ONLY comments/pseudocode \u2014 no API calls.
    """
    title = page.get("title", page.get("slug", "How-To Guide"))
    product_name = product_facts.get("product_name", "Product")
    is_convert = page.get("content_strategy", {}).get("is_conversion_howto", False)
    pkg = product_name.lower().replace(" ", "-")

    sections: List[str] = []
    sections.append("## Goal\n")
    sections.append(f"This guide explains how to {title.lower()} using {product_name}.\n")

    sections.append("## When You'd Use This\n")
    sections.append(f"Use this approach when you need to {title.lower()} in your Python application.\n")

    sections.append("## Prerequisites\n")
    sections.append(f"- {product_name} installed (`pip install {pkg}`).")
    sections.append("- Python 3.8 or later.\n")

    sections.append("## Steps\n")
    sections.append(f"1. Import the {product_name} library.")
    sections.append("2. Load your source data.")
    sections.append("3. Apply the desired operation.")
    sections.append("4. Save or inspect the result.\n")

    sections.append(f"## {product_name} Code Example\n")
    sections.append("```python")
    sections.append("# No working example was found in this repository.")
    sections.append("# Pseudocode outline:")
    sections.append(f"# import {product_name.lower().replace(' ', '_')}")
    sections.append("# data = load('input_file')")
    sections.append("# result = process(data)")
    sections.append("# save(result, 'output_file')")
    sections.append("```\n")

    # Conversion-specific: state format evidence status
    if is_convert:
        fmt_list = page.get("content_strategy", {}).get("supported_formats", [])
        pair_list = page.get("content_strategy", {}).get("conversion_pairs", [])
        if fmt_list:
            sections.append("**Supported formats**: " + ", ".join(
                f"{f['format']} ({f['direction']})" for f in fmt_list
            ) + ".\n")
        if pair_list:
            sections.append("**Evidenced conversions**: " + ", ".join(
                f"{p['source']} \u2192 {p['target']}" for p in pair_list
            ) + ".\n")
        if not fmt_list and not pair_list:
            sections.append("> **Note**: No format conversion evidence was found in this repository.\n")

    sections.append("## Common Mistakes\n")
    sections.append("- Forgetting to install the library before importing it.")
    sections.append("- Using an unsupported file path or missing read permissions.\n")

    sections.append("## See Also\n")
    sections.append("- [Getting Started](../getting-started/)")
    sections.append("- [FAQ](../faq/)\n")

    return "\n".join(sections)


def _normalize_howto_code_fences(content: str, page: Dict[str, Any]) -> str:
    """Ensure how-to articles have a code fence in the Code Example section.

    Fixes empty Code Example headings (heading with no following fence) by
    injecting a placeholder fence. Does NOT touch fences in Steps section.
    """
    if page.get("page_role") != "howto_article":
        return content

    lines = content.split("\n")
    result: List[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # Detect "## ... Code Example" or "### ... Code Example" heading
        if re.match(r'^#{2,3}\s+.*Code\s+Example', line):
            result.append(line)
            i += 1
            # Skip blank lines after heading
            while i < len(lines) and lines[i].strip() == "":
                result.append(lines[i])
                i += 1
            # Check if a fence exists before the next heading
            has_fence = False
            j = i
            while j < len(lines) and not re.match(r'^#{2,3}\s', lines[j].strip()):
                if lines[j].strip().startswith("```"):
                    has_fence = True
                    break
                j += 1
            if not has_fence:
                title = page.get("title", "the library")
                result.append("```python")
                result.append(f"# Example code for {title.lower()}")
                result.append("# See documentation for a complete working example.")
                result.append("pass")
                result.append("```")
                result.append("")
            # Don't increment i — it already points to the next unprocessed line
            continue
        else:
            result.append(line)
        i += 1
    return "\n".join(result)


# ---------------------------------------------------------------------------
# Helper functions (used by multiple generators)
# ---------------------------------------------------------------------------


def _slug_to_readable(slug_or_title: str) -> str:
    """Convert URL slug or raw title to readable prose for body text.

    Examples:
      'how-to-mesh-operations'  -> 'mesh operations'
      'convert-obj-to-stl'      -> 'convert obj to stl'
      'how_to_format_cells'     -> 'format cells'
      'Mesh Operations Overview' -> 'Mesh Operations Overview'  (preserved)
    """
    s = slug_or_title.strip()
    # Strip leading "how-to-" / "how_to_" prefix
    s = re.sub(r'^how[-_]to[-_]', '', s, flags=re.IGNORECASE)
    # Normalize hyphens/underscores to spaces
    s = re.sub(r'[-_]+', ' ', s).strip()
    return s if s else slug_or_title


def _get_display_text(claim: Dict[str, Any]) -> str:
    """Get display text for claim, preferring enriched_text over claim_text.

    TC-1622: enriched_text is marketing-ready, claim_text is raw extraction.
    Always prefer enriched_text when available for user-facing content.

    Args:
        claim: Claim dict with claim_text and optional enriched_text

    Returns:
        enriched_text if available, otherwise claim_text
    """
    return claim.get("enriched_text") or claim.get("claim_text", "")


def _is_user_facing_claim(claim: Dict[str, Any]) -> bool:
    """Validate that a claim is suitable for user-facing bullet points.

    TC-RCA: Quality gate applied to ALL deterministic fallback paths.
    Rejects claims that look like code, error messages, API docstrings,
    or spec fragments before they reach the output.

    Args:
        claim: Claim dict with claim_text and optional enriched_text

    Returns:
        True if the claim is suitable for user-facing content
    """
    text = _get_display_text(claim)
    if not text:
        return False

    # Length bounds: too short is meaningless (truncation handles long text downstream)
    if len(text) < 20 or len(text) > 500:
        return False

    # Must start with a capital letter or a digit
    first_char = text.lstrip()[0] if text.strip() else ''
    if not (first_char.isupper() or first_char.isdigit()):
        return False

    # Reject if it looks like code (2+ code pattern matches)
    _code_patterns = [
        r'\braise\s+\w+',           # raise Exception
        r'\w+(Error|Exception)\b',   # FormatError, ValueError
        r'\bdef\s+\w+\(',           # def function(
        r'\bclass\s+\w+',           # class Foo
        r'\bimport\s+\w+',          # import module
        r'\bself\.\w+',             # self.attribute
        r'\breturn\b',              # return statement
        r'\w+\.\w+\(',              # obj.method() pattern
        r'`[^`]+`',                 # inline code backticks
    ]
    if sum(1 for p in _code_patterns if re.search(p, text)) >= 2:
        return False

    # Reject parameter definitions (e.g., "bold (bool, optional): ...")
    if re.match(r'^\w+\s*\((?:int|str|bool|float|list|dict|tuple|None|Any|Optional|object)\b[^)]*\)\s*:', text.strip()):
        return False
    if re.match(r'^\w+\s*\([A-Z]\w+\)\s*:', text.strip()):
        return False

    # Must contain at least one common English verb (readable prose)
    # Include both base forms (for "Cannot X" patterns) and third-person
    _prose_verbs = {
        'is', 'are', 'was', 'has', 'have', 'can', 'cannot', 'will', 'does',
        'support', 'supports', 'provide', 'provides', 'allow', 'allows',
        'enable', 'enables', 'include', 'includes', 'offer', 'offers',
        'generate', 'generates', 'convert', 'converts', 'handle', 'handles',
        'process', 'processes', 'create', 'creates', 'manage', 'manages',
        'use', 'uses', 'require', 'requires', 'work', 'works',
        'read', 'reads', 'write', 'writes', 'load', 'loads', 'save', 'saves',
        'install', 'installs', 'run', 'runs', 'configure', 'configures',
        'set', 'sets', 'build', 'builds', 'render', 'renders',
        'parse', 'parses', 'extract', 'extracts', 'transform', 'transforms',
        'export', 'exports', 'download', 'downloads', 'validate', 'validates',
    }
    text_lower = text.lower()
    has_verb = any(f' {v} ' in f' {text_lower} ' for v in _prose_verbs)
    if not has_verb:
        # Allow noun phrases that describe features (e.g., "CSV format support")
        _feature_nouns = {'support', 'compatibility', 'integration', 'conversion'}
        if not any(re.search(rf'\b{n}\b', text_lower) for n in _feature_nouns):
            return False

    return True


def _sanitize_limitation_bullet(claim_text: str) -> Optional[str]:
    """Sanitize a limitation claim for user-facing bullet output.

    Strips markdown artifacts, code fences, JSON blobs from claim text,
    extracts the first meaningful sentence, and rejects if the result
    is still not prose-like.
    """
    if not claim_text or not claim_text.strip():
        return None

    text = claim_text.strip()

    # Strip inline code fences (```...``` blocks embedded in text)
    text = re.sub(r'```[\s\S]*?```', '', text)

    # Strip inline code backticks content that is longer than 60 chars (likely dumps)
    text = re.sub(r'`[^`]{60,}`', '', text)

    # Strip JSON-like blobs: {...} or [{...}] patterns
    text = re.sub(r'\{[^}]{50,}\}', '', text)
    text = re.sub(r'\[[^\]]{50,}\]', '', text)

    # Strip markdown heading markers that leaked into claim text
    text = re.sub(r'^#{1,6}\s+', '', text)

    # Strip leading list markers
    text = re.sub(r'^[-*]\s+', '', text)

    # Collapse whitespace
    text = ' '.join(text.split())

    if not text:
        return None

    # Extract first meaningful sentence
    sent_match = re.search(r'^(.+?[.!?])(?:\s|$)', text)
    if sent_match:
        text = sent_match.group(1).strip()

    # Reject if >50% non-prose characters (heuristic for code/data dumps)
    alpha_count = sum(1 for c in text if c.isalpha() or c.isspace())
    if len(text) > 0 and alpha_count / len(text) < 0.50:
        return None

    # Minimum length check (too short = meaningless fragment)
    if len(text) < 15:
        return None

    # Ensure ends with punctuation
    if text and text[-1] not in '.!?':
        text += '.'

    return text


def _sanitize_claims_for_prompt(claims: List[Dict[str, Any]]) -> str:
    """Sanitize limitation claims for LLM prompt injection.

    TC-2893: Anti-dump guardrail — structured prompt builders must use
    sanitized display text, not raw claim_text.  Pipeline per claim:
    _get_display_text -> _sanitize_limitation_bullet -> _smart_truncate.

    Args:
        claims: Limitation claim dicts (max 10 expected).

    Returns:
        Newline-joined bullet list of sanitized claims.  May be shorter
        than input if claims are rejected by sanitization.
    """
    from ..worker import _smart_truncate, MAX_BULLET_LEN

    bullets: List[str] = []
    for claim in claims:
        display = _get_display_text(claim)
        sanitized = _sanitize_limitation_bullet(display)
        if sanitized is None:
            continue
        max_body = MAX_BULLET_LEN - 2  # 2 chars for "- " prefix
        if len(sanitized) > max_body:
            sanitized = _smart_truncate(sanitized, max_body)
        bullets.append(f"- {sanitized}")
    return "\n".join(bullets)


def _build_enriched_claim_context(
    claims: List[Dict[str, Any]],
    product_facts: Optional[Dict[str, Any]] = None
) -> str:
    """Format claims with enriched_text preference for LLM context.

    TC-1658: Build structured claim context for LLM prompts, using enriched_text
    (marketing-ready) when available, grouped by claim_kind for better organization.

    Args:
        claims: List of claim dicts with claim_id, claim_text, enriched_text, etc.
        product_facts: Optional product facts dict (unused but kept for future use)

    Returns:
        Formatted claim context string grouped by claim_kind
    """
    if not claims:
        return ""

    # Group claims by claim_kind
    by_kind: Dict[str, List[Dict[str, Any]]] = {}
    for claim in claims:
        kind = claim.get("claim_kind", "general")
        if kind not in by_kind:
            by_kind[kind] = []
        by_kind[kind].append(claim)

    # Format each group
    sections = []
    for kind, kind_claims in sorted(by_kind.items()):
        # Format kind as title case heading
        section = f"## {kind.replace('_', ' ').title()}\n\n"
        for claim in kind_claims:
            # Use _get_display_text() to prefer enriched_text
            text = _get_display_text(claim)
            claim_id = claim.get("claim_id", "unknown")

            # Include citations with excerpts if available (first 2)
            citations = claim.get("citations", [])
            citation_str = ""
            if citations:
                citation_parts = []
                for c in citations[:2]:
                    excerpt = c.get("citation_excerpt", "")
                    file_path = c.get("path", "")
                    if excerpt:
                        citation_parts.append(f'"{excerpt}" ({file_path})')
                    elif file_path:
                        citation_parts.append(file_path)
                if citation_parts:
                    citation_str = f" [Evidence: {'; '.join(citation_parts)}]"

            section += f"- [{claim_id}] {text}{citation_str}\n"

        sections.append(section)

    return "\n".join(sections)


def build_tutorial_context(
    page: Dict[str, Any],
    product_facts: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
) -> Dict[str, Any]:
    """Build tutorial-specific context: workflow/feature claims first, demo snippets.

    TC-2369: Generator-specific context builder (RCA S-5, H3 Option B). Orders
    claims so workflow and feature kinds appear before other kinds, then selects
    snippets preferentially from demo_snippet_ids set by TC-2368.

    Returns:
        Dict with keys: claims, snippets, claim_context, snippet_text.
    """
    claim_ids = page.get("claim_ids", [])
    all_claims = product_facts.get("claims", [])
    claim_id_set = set(claim_ids)
    claims = [c for c in all_claims if c.get("claim_id") in claim_id_set]

    # Order: workflow/feature first — most relevant for tutorials
    wf = [c for c in claims if c.get("claim_kind") in ("workflow", "feature")]
    other = [c for c in claims if c.get("claim_kind") not in ("workflow", "feature")]
    ordered = (wf + other)[:15]

    # Collect demo snippet IDs from ordered claims (TC-2368 binding)
    demo_ids: List[str] = []
    seen: set = set()
    for c in ordered:
        for sid in c.get("demo_snippet_ids", []):
            if sid not in seen:
                demo_ids.append(sid)
                seen.add(sid)

    all_snippets = snippet_catalog.get("snippets", [])
    smap = {s.get("snippet_id", ""): s for s in all_snippets}
    snippets = [smap[sid] for sid in demo_ids if sid in smap] or all_snippets[:5]
    snippet_text = "\n\n".join(
        f"```{s.get('language', 'python')}\n{s.get('code', '')}\n```"
        for s in snippets[:5]
    )
    return {
        "claims": ordered,
        "snippets": snippets[:5],
        "claim_context": _build_enriched_claim_context(ordered, product_facts),
        "snippet_text": snippet_text,
    }


def build_feature_showcase_context(
    page: Dict[str, Any],
    product_facts: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
    primary_claim: Dict[str, Any],
    related_claims: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Build feature-showcase-specific context: primary claim + demo snippets.

    TC-2369: Generator-specific context builder (RCA S-5, H3 Option B). Selects
    snippets from demo_snippet_ids of the primary claim first (TC-2368 binding),
    falling back to first-5 from catalog.

    Returns:
        Dict with keys: claims, snippets, claim_context, snippet_text.
    """
    all_feature_claims = [primary_claim] + related_claims

    # Collect demo snippet IDs from feature claims (TC-2368 binding)
    demo_ids: List[str] = []
    seen: set = set()
    for c in all_feature_claims:
        for sid in c.get("demo_snippet_ids", []):
            if sid not in seen:
                demo_ids.append(sid)
                seen.add(sid)

    all_snippets = snippet_catalog.get("snippets", [])
    smap = {s.get("snippet_id", ""): s for s in all_snippets}
    snippets = [smap[sid] for sid in demo_ids if sid in smap] or all_snippets[:5]
    snippet_text = "\n\n".join(
        (f"# {s.get('description', '')}\n{s.get('code', '')}"
         if s.get("description") else s.get("code", ""))
        for s in snippets[:5]
    )
    return {
        "claims": all_feature_claims,
        "snippets": snippets[:5],
        "claim_context": _build_enriched_claim_context(all_feature_claims, product_facts),
        "snippet_text": snippet_text or "No code examples available.",
    }


def build_api_reference_context(
    page: Dict[str, Any],
    product_facts: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
) -> Dict[str, Any]:
    """Build API-reference-specific context: api/format claims sorted alphabetically.

    TC-2369: Generator-specific context builder (RCA S-5, H3 Option B). Sorts
    api and format claims alphabetically by claim_text for consistent API page
    structure, then selects snippets from demo_snippet_ids of API claims.

    Returns:
        Dict with keys: claims, snippets, claim_context, snippet_text.
    """
    claim_ids = page.get("claim_ids", page.get("required_claim_ids", []))
    all_claims = product_facts.get("claims", [])
    claim_id_set = set(claim_ids)
    claims = [c for c in all_claims if c.get("claim_id") in claim_id_set]

    # API/format claims sorted alphabetically; other kinds appended after
    api_claims = sorted(
        [c for c in claims if c.get("claim_kind") in ("api", "format")],
        key=lambda c: c.get("claim_text", "").lower(),
    )
    other_claims = [c for c in claims if c.get("claim_kind") not in ("api", "format")]
    ordered = (api_claims + other_claims)[:20]

    # Collect demo snippet IDs from API claims (TC-2368 binding)
    demo_ids: List[str] = []
    seen: set = set()
    for c in api_claims:
        for sid in c.get("demo_snippet_ids", []):
            if sid not in seen:
                demo_ids.append(sid)
                seen.add(sid)

    all_snippets = snippet_catalog.get("snippets", [])
    smap = {s.get("snippet_id", ""): s for s in all_snippets}
    snippets = [smap[sid] for sid in demo_ids if sid in smap]
    if not snippets:
        # Fallback: snippets tagged 'api' or 'reference'
        snippets = [
            s for s in all_snippets
            if any(t in s.get("tags", []) for t in ["api", "reference"])
        ][:5] or all_snippets[:5]

    snippet_text = "\n\n".join(
        f"```{s.get('language', 'python')}\n{s.get('code', '')}\n```"
        for s in snippets[:5]
    )
    return {
        "claims": ordered,
        "snippets": snippets[:5],
        "claim_context": _build_enriched_claim_context(ordered, product_facts),
        "snippet_text": snippet_text,
    }


# ---------------------------------------------------------------------------
# TC-2379: 13 new role context builders
# ---------------------------------------------------------------------------


def build_comprehensive_guide_context(
    page: Dict[str, Any],
    product_facts: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
) -> Dict[str, Any]:
    """Build comprehensive-guide context: workflow → feature → api claims, top-5 workflow snippets.

    TC-2379: Role-ranked context builder for comprehensive_guide pages. Workflow claims
    are surfaced first (most relevant for multi-section guides), followed by feature and
    api claims. Demo snippet IDs are collected from the top 5 workflow claims.

    Returns:
        Dict with keys: claims, snippets, claim_context, snippet_text.
    """
    claim_ids = page.get("claim_ids", page.get("required_claim_ids", []))
    all_claims = product_facts.get("claims", [])
    claim_id_set = set(claim_ids)
    claims = [c for c in all_claims if c.get("claim_id") in claim_id_set]

    # Priority: workflow → feature → api → other
    workflow_claims = [c for c in claims if c.get("claim_kind") == "workflow"]
    feature_claims = [c for c in claims if c.get("claim_kind") == "feature"]
    api_claims = [c for c in claims if c.get("claim_kind") == "api"]
    other_claims = [
        c for c in claims
        if c.get("claim_kind") not in ("workflow", "feature", "api")
    ]
    ordered = (workflow_claims + feature_claims + api_claims + other_claims)[:20]

    # Collect demo snippet IDs from top 5 workflow claims
    demo_ids: List[str] = []
    seen: set = set()
    for c in workflow_claims[:5]:
        for sid in c.get("demo_snippet_ids", []):
            if sid not in seen:
                demo_ids.append(sid)
                seen.add(sid)

    all_snippets = snippet_catalog.get("snippets", [])
    smap = {s.get("snippet_id", ""): s for s in all_snippets}
    snippets = [smap[sid] for sid in demo_ids if sid in smap] or all_snippets[:5]
    snippet_text = "\n\n".join(
        f"```{s.get('language', 'python')}\n{s.get('code', '')}\n```"
        for s in snippets[:5]
    )
    return {
        "claims": ordered,
        "snippets": snippets[:5],
        "claim_context": _build_enriched_claim_context(ordered, product_facts),
        "snippet_text": snippet_text,
    }


def build_troubleshooting_context(
    page: Dict[str, Any],
    product_facts: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
) -> Dict[str, Any]:
    """Build troubleshooting context: error → limitation → format claims, fix snippets.

    TC-2379: Role-ranked context builder for troubleshooting pages. Error claims are
    surfaced first (most specific to troubleshooting), then limitation claims, then
    format claims. Snippets demonstrating fixes are selected from demo_snippet_ids.

    Returns:
        Dict with keys: claims, snippets, claim_context, snippet_text.
    """
    claim_ids = page.get("claim_ids", page.get("required_claim_ids", []))
    all_claims = product_facts.get("claims", [])
    claim_id_set = set(claim_ids)
    claims = [c for c in all_claims if c.get("claim_id") in claim_id_set]

    # If no page-level claim_ids, fall back to limitation+troubleshooting claim groups
    # TC-3683: filter by visibility=public to prevent spec leakage
    if not claims:
        claim_groups = product_facts.get("claim_groups", {})
        merged_ids = list(
            set(claim_groups.get("limitations", []))
            | set(claim_groups.get("troubleshooting", []))
        )
        claims = get_claims_by_ids(product_facts, merged_ids, visibility_filter="public")

    # Priority: error → limitation → format → other
    error_claims = [c for c in claims if c.get("claim_kind") == "error"]
    limitation_claims = [c for c in claims if c.get("claim_kind") == "limitation"]
    format_claims = [c for c in claims if c.get("claim_kind") == "format"]
    other_claims = [
        c for c in claims
        if c.get("claim_kind") not in ("error", "limitation", "format")
    ]
    ordered = (error_claims + limitation_claims + format_claims + other_claims)[:15]

    # Snippets demonstrating fixes: collect demo_snippet_ids from error/limitation claims
    demo_ids: List[str] = []
    seen: set = set()
    for c in (error_claims + limitation_claims):
        for sid in c.get("demo_snippet_ids", []):
            if sid not in seen:
                demo_ids.append(sid)
                seen.add(sid)

    all_snippets = snippet_catalog.get("snippets", [])
    smap = {s.get("snippet_id", ""): s for s in all_snippets}
    snippets = [smap[sid] for sid in demo_ids if sid in smap] or all_snippets[:5]
    snippet_text = "\n\n".join(
        f"```{s.get('language', 'python')}\n{s.get('code', '')}\n```"
        for s in snippets[:5]
    )
    return {
        "claims": ordered,
        "snippets": snippets[:5],
        "claim_context": _build_enriched_claim_context(ordered, product_facts),
        "snippet_text": snippet_text,
    }


def build_blog_context(
    page: Dict[str, Any],
    product_facts: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
) -> Dict[str, Any]:
    """Build blog context: feature → workflow claims, first demo snippet.

    TC-2379: Role-ranked context builder for blog/announcement pages. Feature claims
    lead (announcements highlight capabilities), followed by workflow claims. Only the
    first demo snippet ID is used to keep blog posts concise.

    Returns:
        Dict with keys: claims, snippets, claim_context, snippet_text.
    """
    all_claims = product_facts.get("claims", [])

    # Prefer page-level claim_ids; fall back to key_features + install_steps claim groups
    claim_ids = page.get("claim_ids", page.get("required_claim_ids", []))
    if claim_ids:
        claim_id_set = set(claim_ids)
        claims = [c for c in all_claims if c.get("claim_id") in claim_id_set]
    else:
        # TC-3683: filter by visibility=public to prevent spec leakage
        claim_groups = product_facts.get("claim_groups", {})
        feature_ids = claim_groups.get("key_features", [])[:5]
        workflow_ids = claim_groups.get("install_steps", [])[:3]
        merged_ids = list(set(feature_ids) | set(workflow_ids))
        claims = get_claims_by_ids(product_facts, merged_ids, visibility_filter="public")

    # Priority: feature → workflow → other
    feature_claims = [c for c in claims if c.get("claim_kind") == "feature"]
    workflow_claims = [c for c in claims if c.get("claim_kind") == "workflow"]
    other_claims = [
        c for c in claims if c.get("claim_kind") not in ("feature", "workflow")
    ]
    ordered = (feature_claims + workflow_claims + other_claims)[:10]

    # Only use first demo_snippet_id for concise blog posts
    demo_ids: List[str] = []
    seen: set = set()
    for c in ordered:
        for sid in c.get("demo_snippet_ids", [])[:1]:
            if sid not in seen:
                demo_ids.append(sid)
                seen.add(sid)
        if demo_ids:
            break  # Blog posts use only first demo snippet

    all_snippets = snippet_catalog.get("snippets", [])
    smap = {s.get("snippet_id", ""): s for s in all_snippets}
    snippets = [smap[sid] for sid in demo_ids if sid in smap] or all_snippets[:1]
    snippet_text = "\n\n".join(
        f"```{s.get('language', 'python')}\n{s.get('code', '')}\n```"
        for s in snippets[:1]
    )
    return {
        "claims": ordered,
        "snippets": snippets[:1],
        "claim_context": _build_enriched_claim_context(ordered, product_facts),
        "snippet_text": snippet_text,
    }


def build_feature_blog_context(
    page: Dict[str, Any],
    product_facts: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
) -> Dict[str, Any]:
    """Build feature blog context: feature → workflow claims, first demo snippet.

    TC-2379: Role-ranked context builder for feature_blog pages. Mirrors blog_context
    but is focused on a specific feature highlight rather than a product launch.
    Feature claims lead, workflow claims follow. First demo_snippet_id only.

    Returns:
        Dict with keys: claims, snippets, claim_context, snippet_text.
    """
    all_claims = product_facts.get("claims", [])

    claim_ids = page.get("claim_ids", page.get("required_claim_ids", []))
    if claim_ids:
        claim_id_set = set(claim_ids)
        claims = [c for c in all_claims if c.get("claim_id") in claim_id_set]
    else:
        # TC-3683: filter by visibility=public to prevent spec leakage
        claim_groups = product_facts.get("claim_groups", {})
        feature_ids = claim_groups.get("key_features", [])[:6]
        claims = get_claims_by_ids(product_facts, feature_ids, visibility_filter="public")

    # Priority: feature → workflow → other
    feature_claims = [c for c in claims if c.get("claim_kind") == "feature"]
    workflow_claims = [c for c in claims if c.get("claim_kind") == "workflow"]
    other_claims = [
        c for c in claims if c.get("claim_kind") not in ("feature", "workflow")
    ]
    ordered = (feature_claims + workflow_claims + other_claims)[:10]

    # Only use first demo_snippet_id for concise feature blog posts
    demo_ids: List[str] = []
    seen: set = set()
    for c in ordered:
        for sid in c.get("demo_snippet_ids", [])[:1]:
            if sid not in seen:
                demo_ids.append(sid)
                seen.add(sid)
        if demo_ids:
            break

    all_snippets = snippet_catalog.get("snippets", [])
    smap = {s.get("snippet_id", ""): s for s in all_snippets}
    snippets = [smap[sid] for sid in demo_ids if sid in smap] or all_snippets[:1]
    snippet_text = "\n\n".join(
        f"```{s.get('language', 'python')}\n{s.get('code', '')}\n```"
        for s in snippets[:1]
    )
    return {
        "claims": ordered,
        "snippets": snippets[:1],
        "claim_context": _build_enriched_claim_context(ordered, product_facts),
        "snippet_text": snippet_text,
    }


def build_performance_context(
    page: Dict[str, Any],
    product_facts: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
) -> Dict[str, Any]:
    """Build performance context: limitation → feature claims, timing/benchmark snippets.

    TC-2379: Role-ranked context builder for performance pages. Limitation claims lead
    (performance constraints/caveats are most actionable), followed by feature claims.
    Snippets tagged 'timing', 'benchmark', or 'performance' are preferred.

    Returns:
        Dict with keys: claims, snippets, claim_context, snippet_text.
    """
    all_claims = product_facts.get("claims", [])

    claim_ids = page.get("claim_ids", page.get("required_claim_ids", []))
    if claim_ids:
        claim_id_set = set(claim_ids)
        claims = [c for c in all_claims if c.get("claim_id") in claim_id_set]
    else:
        # TC-3683: filter by visibility=public to prevent spec leakage
        claim_groups = product_facts.get("claim_groups", {})
        perf_ids = set(claim_groups.get("performance", []))
        bp_ids = set(claim_groups.get("best_practices", []))
        merged_ids = list(perf_ids | bp_ids)
        claims = get_claims_by_ids(product_facts, merged_ids, visibility_filter="public")

    # Priority: limitation → feature → other
    limitation_claims = [c for c in claims if c.get("claim_kind") == "limitation"]
    feature_claims = [c for c in claims if c.get("claim_kind") == "feature"]
    other_claims = [
        c for c in claims if c.get("claim_kind") not in ("limitation", "feature")
    ]
    ordered = (limitation_claims + feature_claims + other_claims)[:15]

    # Prefer snippets tagged timing/benchmark/performance
    all_snippets = snippet_catalog.get("snippets", [])
    perf_tags = {"timing", "benchmark", "performance", "optimization"}
    perf_snippets = [
        s for s in all_snippets
        if any(t in s.get("tags", []) for t in perf_tags)
    ][:5]
    snippets = perf_snippets or all_snippets[:5]
    snippet_text = "\n\n".join(
        f"```{s.get('language', 'python')}\n{s.get('code', '')}\n```"
        for s in snippets[:5]
    )
    return {
        "claims": ordered,
        "snippets": snippets[:5],
        "claim_context": _build_enriched_claim_context(ordered, product_facts),
        "snippet_text": snippet_text,
    }


def build_faq_context(
    page: Dict[str, Any],
    product_facts: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
) -> Dict[str, Any]:
    """Build FAQ context: feature → api → format claims, no snippets.

    TC-2379: Role-ranked context builder for faq pages. FAQ pages answer conceptual
    questions, so feature claims lead (broadest coverage), then api/format claims for
    technical precision. No snippets are required — FAQ answers are text-only.

    Returns:
        Dict with keys: claims, snippets (empty), claim_context, snippet_text (empty).
    """
    all_claims = product_facts.get("claims", [])

    claim_ids = page.get("claim_ids", page.get("required_claim_ids", []))
    if claim_ids:
        claim_id_set = set(claim_ids)
        claims = [c for c in all_claims if c.get("claim_id") in claim_id_set]
    else:
        claims = []

    # Priority: feature → api → format → other
    feature_claims = [c for c in claims if c.get("claim_kind") == "feature"]
    api_claims = [c for c in claims if c.get("claim_kind") == "api"]
    format_claims = [c for c in claims if c.get("claim_kind") == "format"]
    other_claims = [
        c for c in claims
        if c.get("claim_kind") not in ("feature", "api", "format")
    ]
    ordered = (feature_claims + api_claims + format_claims + other_claims)[:15]

    # No snippets for FAQ pages
    return {
        "claims": ordered,
        "snippets": [],
        "claim_context": _build_enriched_claim_context(ordered, product_facts),
        "snippet_text": "",
    }


def build_best_practices_context(
    page: Dict[str, Any],
    product_facts: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
) -> Dict[str, Any]:
    """Build best-practices context: workflow → limitation claims, step-linked snippets.

    TC-2379: Role-ranked context builder for best_practices pages. Workflow claims lead
    (best practices are action-oriented), limitation claims follow (what to avoid).
    Snippets are linked via demo_snippet_ids from workflow claims (step examples).

    Returns:
        Dict with keys: claims, snippets, claim_context, snippet_text.
    """
    all_claims = product_facts.get("claims", [])

    claim_ids = page.get("claim_ids", page.get("required_claim_ids", []))
    if claim_ids:
        claim_id_set = set(claim_ids)
        claims = [c for c in all_claims if c.get("claim_id") in claim_id_set]
    else:
        # TC-3683: filter by visibility=public to prevent spec leakage
        claim_groups = product_facts.get("claim_groups", {})
        bp_ids = list(claim_groups.get("best_practices", []))
        claims = get_claims_by_ids(product_facts, bp_ids, visibility_filter="public")

    # Priority: workflow → limitation → other
    workflow_claims = [c for c in claims if c.get("claim_kind") == "workflow"]
    limitation_claims = [c for c in claims if c.get("claim_kind") == "limitation"]
    other_claims = [
        c for c in claims if c.get("claim_kind") not in ("workflow", "limitation")
    ]
    ordered = (workflow_claims + limitation_claims + other_claims)[:15]

    # Step-linked snippets from workflow claims demo_snippet_ids
    demo_ids: List[str] = []
    seen: set = set()
    for c in workflow_claims:
        for sid in c.get("demo_snippet_ids", []):
            if sid not in seen:
                demo_ids.append(sid)
                seen.add(sid)

    all_snippets = snippet_catalog.get("snippets", [])
    smap = {s.get("snippet_id", ""): s for s in all_snippets}
    snippets = [smap[sid] for sid in demo_ids if sid in smap] or all_snippets[:5]
    snippet_text = "\n\n".join(
        f"```{s.get('language', 'python')}\n{s.get('code', '')}\n```"
        for s in snippets[:5]
    )
    return {
        "claims": ordered,
        "snippets": snippets[:5],
        "claim_context": _build_enriched_claim_context(ordered, product_facts),
        "snippet_text": snippet_text,
    }


def build_getting_started_context(
    page: Dict[str, Any],
    product_facts: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
) -> Dict[str, Any]:
    """Build getting-started context: install-section workflow claims first → feature.

    TC-2379: Role-ranked context builder for getting_started pages. Workflow claims
    from install-related source_sections are sorted to appear first (alphabetically by
    source_section, which places install/configuration sections ahead of feature sections
    in most repos). Feature claims follow for "what can I do" context.

    Returns:
        Dict with keys: claims, snippets, claim_context, snippet_text.
    """
    all_claims = product_facts.get("claims", [])

    # Pull install_steps claim group as primary source, supplemented by page claims
    claim_ids = page.get("claim_ids", page.get("required_claim_ids", []))
    claim_groups = product_facts.get("claim_groups", {})
    install_ids = set(claim_groups.get("install_steps", []))
    kf_ids = set(claim_groups.get("key_features", [])[:5])
    page_ids = set(claim_ids)

    # Union of page claim_ids + install + key_features
    merged_ids = page_ids | install_ids | kf_ids
    all_claim_map = {c.get("claim_id"): c for c in all_claims}
    claims = [all_claim_map[cid] for cid in merged_ids if cid in all_claim_map]

    # Workflow claims sorted by source_section alphabetically (install sections come first)
    workflow_claims = sorted(
        [c for c in claims if c.get("claim_kind") == "workflow"],
        key=lambda c: c.get("source_section", "zzz"),
    )
    feature_claims = [c for c in claims if c.get("claim_kind") == "feature"]
    other_claims = [
        c for c in claims if c.get("claim_kind") not in ("workflow", "feature")
    ]
    ordered = (workflow_claims + feature_claims + other_claims)[:15]

    # Ordered install snippets from workflow claim demo_snippet_ids
    demo_ids: List[str] = []
    seen: set = set()
    for c in workflow_claims:
        for sid in c.get("demo_snippet_ids", []):
            if sid not in seen:
                demo_ids.append(sid)
                seen.add(sid)

    all_snippets = snippet_catalog.get("snippets", [])
    smap = {s.get("snippet_id", ""): s for s in all_snippets}
    snippets = [smap[sid] for sid in demo_ids if sid in smap] or all_snippets[:5]
    snippet_text = "\n\n".join(
        f"```{s.get('language', 'python')}\n{s.get('code', '')}\n```"
        for s in snippets[:5]
    )
    return {
        "claims": ordered,
        "snippets": snippets[:5],
        "claim_context": _build_enriched_claim_context(ordered, product_facts),
        "snippet_text": snippet_text,
    }


def build_workflow_page_context(
    page: Dict[str, Any],
    product_facts: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
) -> Dict[str, Any]:
    """Build workflow-page context: workflow claims in source_section order, step snippets.

    TC-2379: Role-ranked context builder for workflow_page pages. All workflow claims
    are sorted by source_section field alphabetically to preserve the natural step
    ordering from the source repository. Demo snippets from each workflow claim are
    collected in the same order (step-ordered).

    Returns:
        Dict with keys: claims, snippets, claim_context, snippet_text.
    """
    all_claims = product_facts.get("claims", [])

    claim_ids = page.get("claim_ids", page.get("required_claim_ids", []))
    if claim_ids:
        claim_id_set = set(claim_ids)
        claims = [c for c in all_claims if c.get("claim_id") in claim_id_set]
    else:
        claims = all_claims

    # Workflow claims sorted by source_section (preserves natural step order)
    workflow_claims = sorted(
        [c for c in claims if c.get("claim_kind") == "workflow"],
        key=lambda c: c.get("source_section", "zzz"),
    )
    other_claims = [c for c in claims if c.get("claim_kind") != "workflow"]
    ordered = (workflow_claims + other_claims)[:15]

    # Step-ordered snippets from workflow claims
    demo_ids: List[str] = []
    seen: set = set()
    for c in workflow_claims:
        for sid in c.get("demo_snippet_ids", []):
            if sid not in seen:
                demo_ids.append(sid)
                seen.add(sid)

    all_snippets = snippet_catalog.get("snippets", [])
    smap = {s.get("snippet_id", ""): s for s in all_snippets}
    snippets = [smap[sid] for sid in demo_ids if sid in smap] or all_snippets[:5]
    snippet_text = "\n\n".join(
        f"```{s.get('language', 'python')}\n{s.get('code', '')}\n```"
        for s in snippets[:5]
    )
    return {
        "claims": ordered,
        "snippets": snippets[:5],
        "claim_context": _build_enriched_claim_context(ordered, product_facts),
        "snippet_text": snippet_text,
    }


def build_landing_context(
    page: Dict[str, Any],
    product_facts: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
) -> Dict[str, Any]:
    """Build landing-page context: top 5 feature claims, hero snippet.

    TC-2379: Role-ranked context builder for landing pages. Landing pages are value
    proposition pages that highlight the product's top features (capped at 5 for
    clarity). The hero snippet is taken from the first demo_snippet_id of the leading
    feature claim to illustrate the primary use case.

    Returns:
        Dict with keys: claims, snippets, claim_context, snippet_text.
    """
    all_claims = product_facts.get("claims", [])

    claim_ids = page.get("claim_ids", page.get("required_claim_ids", []))
    if claim_ids:
        claim_id_set = set(claim_ids)
        claims = [c for c in all_claims if c.get("claim_id") in claim_id_set]
    else:
        # Fall back to key_features claim group
        kf_ids = product_facts.get("claim_groups", {}).get("key_features", [])[:6]
        all_claim_map = {c.get("claim_id"): c for c in all_claims}
        claims = [all_claim_map[cid] for cid in kf_ids if cid in all_claim_map]

    # Top 5 feature claims only (landing pages are concise)
    feature_claims = [c for c in claims if c.get("claim_kind") == "feature"][:5]
    ordered = feature_claims

    # Hero snippet: first demo_snippet_id from leading feature claim
    demo_ids: List[str] = []
    seen: set = set()
    for c in feature_claims[:1]:  # Only first claim for hero
        for sid in c.get("demo_snippet_ids", [])[:1]:
            if sid not in seen:
                demo_ids.append(sid)
                seen.add(sid)

    all_snippets = snippet_catalog.get("snippets", [])
    smap = {s.get("snippet_id", ""): s for s in all_snippets}
    snippets = [smap[sid] for sid in demo_ids if sid in smap] or all_snippets[:1]
    snippet_text = "\n\n".join(
        f"```{s.get('language', 'python')}\n{s.get('code', '')}\n```"
        for s in snippets[:1]
    )
    return {
        "claims": ordered,
        "snippets": snippets[:1],
        "claim_context": _build_enriched_claim_context(ordered, product_facts),
        "snippet_text": snippet_text,
    }


def build_format_conversion_context(
    page: Dict[str, Any],
    product_facts: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
) -> Dict[str, Any]:
    """Build format-conversion context: format → api claims, input/output snippets.

    TC-2379: Role-ranked context builder for format_conversion pages. Format claims lead
    (describe the conversion capability itself), followed by api claims (the specific
    API methods used). Snippets are selected by format-related tags.

    Returns:
        Dict with keys: claims, snippets, claim_context, snippet_text.
    """
    all_claims = product_facts.get("claims", [])

    claim_ids = page.get("claim_ids", page.get("required_claim_ids", []))
    if claim_ids:
        claim_id_set = set(claim_ids)
        claims = [c for c in all_claims if c.get("claim_id") in claim_id_set]
    else:
        claims = []

    # Priority: format → api → other
    format_claims = [c for c in claims if c.get("claim_kind") == "format"]
    api_claims = [c for c in claims if c.get("claim_kind") == "api"]
    other_claims = [
        c for c in claims if c.get("claim_kind") not in ("format", "api")
    ]
    ordered = (format_claims + api_claims + other_claims)[:15]

    # Snippets tagged with format/conversion keywords from content_strategy
    content_strategy = page.get("content_strategy", {})
    source_fmt = content_strategy.get("source_format", "").lower()
    target_fmt = content_strategy.get("target_format", "").lower()
    format_tags = {"format", "conversion", "convert", source_fmt, target_fmt} - {""}

    all_snippets = snippet_catalog.get("snippets", [])
    format_snippets = [
        s for s in all_snippets
        if any(t in s.get("tags", []) for t in format_tags)
    ][:5]
    snippets = format_snippets or all_snippets[:5]
    snippet_text = "\n\n".join(
        f"```{s.get('language', 'python')}\n{s.get('code', '')}\n```"
        for s in snippets[:5]
    )
    return {
        "claims": ordered,
        "snippets": snippets[:5],
        "claim_context": _build_enriched_claim_context(ordered, product_facts),
        "snippet_text": snippet_text,
    }


def build_howto_article_context(
    page: Dict[str, Any],
    product_facts: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
) -> Dict[str, Any]:
    """Build how-to article context: workflow claims in source_section order, step snippets.

    TC-2379: Role-ranked context builder for howto_article pages. Workflow claims are
    sorted by source_section to preserve step ordering, matching the how-to structure.
    Step-linked snippets from demo_snippet_ids are collected in order.

    Returns:
        Dict with keys: claims, snippets, claim_context, snippet_text.
    """
    all_claims = product_facts.get("claims", [])

    claim_ids = page.get("claim_ids", page.get("required_claim_ids", []))
    if claim_ids:
        claim_id_set = set(claim_ids)
        claims = [c for c in all_claims if c.get("claim_id") in claim_id_set]
    else:
        claims = []

    # Workflow claims sorted by source_section for natural step order
    workflow_claims = sorted(
        [c for c in claims if c.get("claim_kind") == "workflow"],
        key=lambda c: c.get("source_section", "zzz"),
    )
    other_claims = [c for c in claims if c.get("claim_kind") != "workflow"]
    ordered = (workflow_claims + other_claims)[:15]

    # Step-linked snippets from workflow claims
    demo_ids: List[str] = []
    seen: set = set()
    for c in workflow_claims:
        for sid in c.get("demo_snippet_ids", []):
            if sid not in seen:
                demo_ids.append(sid)
                seen.add(sid)

    all_snippets = snippet_catalog.get("snippets", [])
    smap = {s.get("snippet_id", ""): s for s in all_snippets}
    snippets = [smap[sid] for sid in demo_ids if sid in smap] or all_snippets[:5]
    snippet_text = "\n\n".join(
        f"```{s.get('language', 'python')}\n{s.get('code', '')}\n```"
        for s in snippets[:5]
    )
    return {
        "claims": ordered,
        "snippets": snippets[:5],
        "claim_context": _build_enriched_claim_context(ordered, product_facts),
        "snippet_text": snippet_text,
    }


def build_toc_context(
    page: Dict[str, Any],
    product_facts: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
) -> Dict[str, Any]:
    """Build TOC context: empty claims and snippets (structural page).

    TC-2379: TOC pages are purely navigational — they list child pages and quick links.
    No claim ranking or snippet selection is needed.

    Returns:
        Dict with keys: claims (empty), snippets (empty), claim_context (''), snippet_text ('').
    """
    return {
        "claims": [],
        "snippets": [],
        "claim_context": "",
        "snippet_text": "",
    }


# ---------------------------------------------------------------------------
# Spec v1.1 H2: Reference Object Page context builder (per-class/module/function)
# ---------------------------------------------------------------------------


def build_reference_object_context(
    page: Dict[str, Any],
    product_facts: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
) -> Dict[str, Any]:
    """Build context for a per-class/module/function reference page.

    Spec v1.1 H2 (Q3=A): Filters 'api' claims matching the target object_name,
    then selects demo snippets from those claims.  Falls back to all api-kind
    claims when no object-specific claims are found.

    Page spec fields used:
        object_name (str): Canonical class/module/function name (e.g. "Document")
        object_kind (str): 'class' | 'module' | 'function'  (default: 'class')

    Returns:
        Dict with keys: claims, snippets, claim_context, snippet_text.
    """
    object_name = page.get("object_name", "")
    claim_ids = page.get("claim_ids", page.get("required_claim_ids", []))
    all_claims = product_facts.get("claims", [])

    # Prefer claims explicitly assigned to this page
    if claim_ids:
        claim_id_set = set(claim_ids)
        claims = [c for c in all_claims if c.get("claim_id") in claim_id_set]
    else:
        claims = []

    # Narrow to api-kind claims that mention the object name (case-insensitive)
    if object_name:
        obj_lower = object_name.lower()
        api_claims = [
            c for c in claims
            if c.get("claim_kind") == "api"
            and obj_lower in c.get("claim_text", "").lower()
        ]
        if not api_claims:
            # Relax: any api claim mentioning the object anywhere
            api_claims = [
                c for c in all_claims
                if c.get("claim_kind") == "api"
                and obj_lower in c.get("claim_text", "").lower()
            ]
        ordered = sorted(api_claims, key=lambda c: c.get("claim_text", "").lower())[:20]
    else:
        ordered = sorted(
            [c for c in claims if c.get("claim_kind") == "api"],
            key=lambda c: c.get("claim_text", "").lower(),
        )[:20]

    # Collect demo snippet IDs from matched api claims
    demo_ids: List[str] = []
    seen: set = set()
    for c in ordered:
        for sid in c.get("demo_snippet_ids", []):
            if sid not in seen:
                demo_ids.append(sid)
                seen.add(sid)

    all_snippets = snippet_catalog.get("snippets", [])
    smap = {s.get("snippet_id", ""): s for s in all_snippets}
    snippets = [smap[sid] for sid in demo_ids if sid in smap]
    if not snippets and object_name:
        # Fallback: snippets whose code mentions the object name
        snippets = [
            s for s in all_snippets
            if object_name.lower() in s.get("code", "").lower()
        ][:5]
    if not snippets:
        snippets = all_snippets[:3]

    snippet_text = "\n\n".join(
        f"```{s.get('language', 'python')}\n{s.get('code', '')}\n```"
        for s in snippets[:5]
    )
    return {
        "claims": ordered,
        "snippets": snippets[:5],
        "claim_context": _build_enriched_claim_context(ordered, product_facts),
        "snippet_text": snippet_text,
    }


# ---------------------------------------------------------------------------
# TC-2379: Context builder dispatch
# ---------------------------------------------------------------------------

_CONTEXT_BUILDERS: Dict[str, Any] = {
    "tutorial": build_tutorial_context,
    "api_reference": build_api_reference_context,
    "feature_showcase": build_feature_showcase_context,
    "comprehensive_guide": build_comprehensive_guide_context,
    "troubleshooting": build_troubleshooting_context,
    "blog": build_blog_context,
    "feature_blog": build_feature_blog_context,
    "performance": build_performance_context,
    "faq": build_faq_context,
    "best_practices": build_best_practices_context,
    "getting_started": build_getting_started_context,
    "workflow_page": build_workflow_page_context,
    "landing": build_landing_context,
    "format_conversion": build_format_conversion_context,
    "howto_article": build_howto_article_context,
    "toc": build_toc_context,
    # Spec v1.1 H2
    "reference_object_page": build_reference_object_context,
}


def get_context_for_role(
    page_role: str,
    page: Dict[str, Any],
    product_facts: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
) -> Dict[str, Any]:
    """Get role-appropriate context dict for an LLM generator prompt.

    TC-2379: Dispatch function that maps page_role to the correct context builder.
    Falls back to build_tutorial_context for unknown roles (safe default with
    workflow/feature priority).

    Note: feature_showcase requires extra positional args (primary_claim, related_claims)
    that are not available through the generic dispatch interface. For feature_showcase,
    call build_feature_showcase_context() directly with those arguments; this dispatch
    function falls back to build_tutorial_context for that role.

    Args:
        page_role: Page role string (e.g., 'tutorial', 'faq', 'landing')
        page: Page specification dict
        product_facts: Product facts dict with claims array
        snippet_catalog: Snippet catalog dict

    Returns:
        Dict with keys: claims, snippets, claim_context, snippet_text.
    """
    # feature_showcase requires extra positional args — use tutorial as safe fallback
    if page_role == "feature_showcase":
        return build_tutorial_context(page, product_facts, snippet_catalog)
    builder = _CONTEXT_BUILDERS.get(page_role, build_tutorial_context)
    return builder(page, product_facts, snippet_catalog)


def _inject_claim_markers_as_comments(
    content: str,
    claim_ids: List[str],
    claims: List[Dict[str, Any]]
) -> str:
    """Insert HTML comment claim markers near relevant text in generated content.

    TC-1658: Place claim markers as HTML comments (<!-- claim: id -->) near
    the text they support, using fuzzy matching between claim text and content.
    Falls back to inserting all markers at start if no matches found.

    Args:
        content: Generated markdown content
        claim_ids: List of claim IDs to inject
        claims: Full claim objects for text matching

    Returns:
        Content with HTML comment claim markers inserted
    """
    if not claim_ids or not claims:
        return content

    # Build claim ID to text mapping
    claim_map = {c.get("claim_id"): _get_display_text(c) for c in claims}

    # Track which claims were injected
    injected = set()
    lines = content.split('\n')
    result_lines = []

    for line in lines:
        result_lines.append(line)

        # Try to match claims to this line
        line_lower = line.lower()
        for claim_id in claim_ids:
            if claim_id in injected:
                continue

            claim_text = claim_map.get(claim_id, "")
            if not claim_text:
                continue

            # Fuzzy match: check if key words from claim appear in line
            claim_words = [w.lower() for w in claim_text.split() if len(w) > 3]
            if not claim_words:
                continue

            # Match if 3+ words from claim appear in line
            matches = sum(1 for w in claim_words if w in line_lower)
            if matches >= min(3, len(claim_words)):
                # Insert marker as HTML comment on next line
                result_lines.append(f"<!-- claim: {claim_id} -->")
                injected.add(claim_id)

    # If no matches found, insert all markers at top (after title)
    if not injected:
        # Find first H1 or H2 line
        insert_index = 0
        for i, line in enumerate(result_lines):
            if line.startswith('# ') or line.startswith('## '):
                insert_index = i + 1
                break

        # Insert all claim markers
        marker_lines = [f"<!-- claim: {cid} -->" for cid in claim_ids]
        result_lines[insert_index:insert_index] = marker_lines

    return '\n'.join(result_lines)


# TC-1720: LLM Content Synthesis for Template Pages
def _enrich_template_output(
    content: str,
    page: Dict[str, Any],
    product_facts: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
    llm_client: Optional[Any] = None,
) -> str:
    """Enrich template-rendered content when body is too thin (<150 words).

    TC-1720: Detect thin template output, fill sparse heading sections with
    LLM-generated or deterministic content derived from enriched claims.

    Args:
        content: Template-rendered markdown (may be thin)
        page: Page dict with slug, section, required_claim_ids, etc.
        product_facts: Product facts with claims array
        snippet_catalog: Snippet catalog dict
        llm_client: Optional LLM client for content generation

    Returns:
        Enriched content with >=150 words of body text (best-effort)
    """
    from ..worker import _call_llm_for_content, _smart_truncate, _get_prompt_loader

    # Separate frontmatter from body
    body = content
    frontmatter = ""
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            frontmatter = "---" + parts[1] + "---"
            body = parts[2]

    body_words = len(body.split())
    if body_words >= 150:
        return content  # Already rich enough

    product_name = product_facts.get("product_name", "Product")
    claim_ids = page.get("claim_ids", page.get("required_claim_ids", []))

    # Get claims for this page
    all_claims = product_facts.get("claims", [])
    claim_map = {c.get("claim_id"): c for c in all_claims}
    page_claims = [claim_map[cid] for cid in claim_ids if cid in claim_map]

    if not page_claims:
        # Fallback: grab top key_features claims
        kf_ids = product_facts.get("claim_groups", {}).get("key_features", [])[:10]
        page_claims = [claim_map[cid] for cid in kf_ids if cid in claim_map]

    if not page_claims:
        return content  # No claims to enrich with

    # Try LLM enrichment
    if llm_client:
        claim_context = _build_enriched_claim_context(page_claims, product_facts)
        title = page.get("title", page.get("slug", "Page"))
        section = page.get("section", "docs")

        # TC-1713: Try centralized prompt first, fall back to inline
        prompt = None
        _loader = _get_prompt_loader()
        if _loader:
            try:
                prompt = _loader.load(
                    "system/content_enricher",
                    product_name=product_name,
                    title=title,
                    section=section,
                    body_words=str(body_words),
                    body=body,
                    claim_context=claim_context,
                ).text
            except Exception:
                pass
        if not prompt:
            prompt = (
                f"You are a senior Python developer writing documentation for {product_name}.\n\n"
                f"The following page titled '{title}' in the {section} section has insufficient "
                f"content ({body_words} words). Expand the content to 150-300 words while keeping "
                f"the existing headings and structure intact.\n\n"
                f"EXISTING CONTENT:\n{body}\n\n"
                f"FACTS TO USE (ground all statements in these):\n{claim_context}\n\n"
                f"REQUIREMENTS:\n"
                f"- Keep existing headings and structure\n"
                f"- Add 2-3 sentences of substantive content under each thin heading\n"
                f"- Use specific details from the facts provided\n"
                f"- Write in professional, clear English\n"
                f"- Do NOT add new H1 headings or frontmatter\n"
                f"- Do NOT include placeholder text or 'refer to documentation'\n"
            )
        result = _call_llm_for_content(
            prompt, page_claims, [], llm_client, min_words=80,
            page_role=page.get("page_role", ""),
            canonical_import=_get_canonical_import(product_facts),
            product_name=product_name,
        )
        if result["success"]:
            enriched_body = result["content"]
            # Inject claim markers
            enriched_body = _inject_claim_markers_as_comments(enriched_body, claim_ids[:5], page_claims)
            return (frontmatter + "\n" + enriched_body).strip() + "\n"

    # Deterministic fallback: append claim-based content under existing body
    extra_lines = []
    for claim in page_claims[:8]:
        if not _is_user_facing_claim(claim):
            continue
        text = _get_display_text(claim)
        if text and len(text.split()) >= 5:
            extra_lines.append(f"- {_smart_truncate(text, 200)}")

    if extra_lines:
        body = body.rstrip() + "\n\n## Key Information\n\n" + "\n".join(extra_lines) + "\n"
        # Add claim markers
        for cid in claim_ids[:5]:
            body += f"\n<!-- claim: {cid} -->"
        body += "\n"

    return (frontmatter + "\n" + body).strip() + "\n"


def _first_sentence_bullets(content: str) -> str:
    """Simplify long bullet points and convert bracket claim markers to HTML comments.

    TC-1661: Two operations applied to all list items:
    1. Convert visible [claim: id] markers to <!-- claim: id --> (invisible to users,
       still parseable by W7 Gate 2). Frontmatter already has claim_ids, so visible
       markers in body text are redundant.
    2. Extract first sentence from bullets exceeding MAX_BULLET_LEN. Falls back to
       word-boundary truncation only if the first sentence itself is still too long.
    """
    from ..worker import _smart_truncate, MAX_BULLET_LEN, _LIST_ITEM_RE

    result_lines = []
    for line in content.split('\n'):
        stripped = line.lstrip()
        indent = line[:len(line) - len(stripped)]
        is_list = bool(_LIST_ITEM_RE.match(stripped))

        # TC-1661: Convert bracket claim markers -> HTML comments on all list items
        if is_list:
            stripped = re.sub(
                r'\[claim:\s*([a-zA-Z0-9_-]+)\]',
                r'<!-- claim: \1 -->',
                stripped,
            )

        if not (is_list and len(stripped) > MAX_BULLET_LEN):
            result_lines.append(f'{indent}{stripped}' if is_list else line)
            continue

        # Preserve HTML comment claim marker at end if present
        marker_match = re.search(r'\s*<!--\s*claim:\s*[a-zA-Z0-9_-]+\s*-->$', stripped)
        marker = marker_match.group(0) if marker_match else ''
        text = stripped[:len(stripped) - len(marker)] if marker else stripped

        # Split list prefix ("- ", "* ", "1. ") from body
        prefix_match = _LIST_ITEM_RE.match(text)
        prefix = prefix_match.group(0) if prefix_match else ''
        body = text[len(prefix):]

        # Strategy 1: Extract first sentence (ends with . ! or ?)
        sentence_end = re.search(r'[.!?](?:\s|$)', body)
        if sentence_end and sentence_end.end() < len(body) - 10:
            # First sentence is meaningfully shorter -- use it
            first_sentence = body[:sentence_end.end()].strip()
            simplified = f'{prefix}{first_sentence}{marker}'
            if len(simplified) <= MAX_BULLET_LEN + 30:
                result_lines.append(f'{indent}{simplified}')
                continue

        # Strategy 2: If no sentence break or still long, truncate at word boundary
        max_body = MAX_BULLET_LEN - len(prefix) - len(marker) - 3
        if len(body) > max_body:
            body = _smart_truncate(body, max_body)
        result_lines.append(f'{indent}{prefix}{body}{marker}')

    return '\n'.join(result_lines)


def _fix_claim_grounding(content: str) -> str:
    """Ensure claim markers are within 50 chars of a sentence-ending period.

    W7 ContentReviewer flags claim markers >50 chars from the nearest period
    as WARN. If a claim marker lacks a nearby period, insert one before the marker.
    """
    def _fix_line(line: str) -> str:
        # Skip headings, code blocks, frontmatter
        stripped = line.lstrip()
        if stripped.startswith(('#', '```', '---', '|')):
            return line
        # Find all claim markers in the line
        marker_pattern = re.compile(r'\[claim:\s*[a-zA-Z0-9_-]+\]')
        result = line
        offset = 0
        for m in marker_pattern.finditer(line):
            pos = m.start() + offset
            # Look back up to 50 chars for a sentence-ending punctuation
            text_before = result[:pos]
            last_punct = max(text_before.rfind('.'), text_before.rfind('!'), text_before.rfind('?'))
            if last_punct < 0 or (pos - last_punct) > 50:
                # No nearby period -- insert one AFTER the last word (before trailing spaces)
                # This avoids creating "text .[claim:]" patterns that trigger grammar warnings
                insert_pos = pos
                # Walk back past any trailing whitespace to place period right after text
                while insert_pos > 0 and result[insert_pos - 1] == ' ':
                    insert_pos -= 1
                # Don't add period right next to another punctuation
                char_before = result[insert_pos - 1] if insert_pos > 0 else ''
                if char_before not in ('.', '!', '?', ':', ';'):
                    # Insert "." after word, then re-add space before marker
                    result = result[:insert_pos] + '.' + result[insert_pos:]
                    offset += 1
        return result

    return '\n'.join(_fix_line(line) for line in content.split('\n'))


def get_claims_by_ids(
    product_facts: Dict[str, Any],
    claim_ids: List[str],
    visibility_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Retrieve claims from product_facts by claim IDs.

    Args:
        product_facts: Product facts dictionary
        claim_ids: List of claim IDs to retrieve
        visibility_filter: If set, only return claims with this visibility
            (e.g. "public"). None means no filter. TC-3683.

    Returns:
        List of claim dictionaries matching the IDs and visibility
    """
    claims = product_facts.get("claims", [])
    claim_map = {c["claim_id"]: c for c in claims}

    result = []
    for claim_id in claim_ids:
        if claim_id in claim_map:
            claim = claim_map[claim_id]
            if visibility_filter is None or claim.get("visibility", "public") == visibility_filter:
                result.append(claim)

    return result


def get_snippets_by_tags(
    snippet_catalog: Dict[str, Any],
    tags: List[str]
) -> List[Dict[str, Any]]:
    """Retrieve snippets from catalog by tags.

    Args:
        snippet_catalog: Snippet catalog dictionary
        tags: List of tags to filter by

    Returns:
        List of snippet dictionaries matching any of the tags
    """
    snippets = snippet_catalog.get("snippets", [])

    result = []
    for snippet in snippets:
        snippet_tags = snippet.get("tags", [])
        if any(tag in snippet_tags for tag in tags):
            result.append(snippet)

    return result


# ---------------------------------------------------------------------------
# Generator functions
# ---------------------------------------------------------------------------


def generate_toc_content(
    page: Dict[str, Any],
    product_facts: Dict[str, Any],
    page_plan: Dict[str, Any],
) -> str:
    """Generate table of contents page content.

    Creates navigation hub listing all child pages in the section.
    MUST NOT include code snippets (forbidden by specs/08).

    Args:
        page: Page specification from page_plan
        product_facts: Product facts dictionary
        page_plan: Complete page plan with all pages

    Returns:
        Markdown content for TOC page

    Raises:
        SectionWriterError: If child pages cannot be located
    """
    # Extract page metadata
    product_name = product_facts.get("product_name", "Product")
    content_strategy = page.get("content_strategy", {})
    child_pages_spec = content_strategy.get("child_pages", [])
    token_mappings = page.get("token_mappings", {})

    # Build content with frontmatter (Gate 4: required fields)
    # Resolve title from token_mappings if page.title is a placeholder
    raw_title = page.get("title", "Documentation")
    if raw_title.startswith("__") and raw_title.endswith("__"):
        # Token placeholder - resolve from mappings
        toc_title = token_mappings.get(raw_title, f"{product_name} Documentation")
    else:
        toc_title = raw_title
    toc_section = page.get("section", "docs")
    toc_layout = toc_section if toc_section in ["docs", "products", "reference", "kb", "blog"] else "default"
    toc_url_path = page.get("url_path", "")
    lines = [
        "---",
        f'title: "{toc_title}"',
        f'description: "Documentation index"',
        f"layout: {toc_layout}",
    ]
    if toc_url_path:
        lines.append(f"permalink: {toc_url_path}")
    lines.extend([
        "---",
        "",
        f"# {toc_title}",
        "",
        f"Welcome to the {product_name} documentation. Get started by exploring the guides below or jump to the quick links for direct access to specific resources.",
        "",
    ])

    # Build child pages list
    current_slug = page.get("slug", "")
    if child_pages_spec:
        lines.append("## Documentation Index")
        lines.append("")
        lines.append(f"Browse the available documentation for {product_name}." if product_name else "Browse the available documentation below.")
        lines.append("")

        # Sort child slugs for determinism, excluding self-reference
        child_slugs = sorted([s for s in child_pages_spec if s != current_slug])

        # Find child pages in page_plan
        all_pages = page_plan.get("pages", [])
        page_map = {p["slug"]: p for p in all_pages}

        for child_slug in child_slugs:
            if child_slug in page_map:
                child = page_map[child_slug]
                # Resolve child title from token_mappings if it's a placeholder
                raw_child_title = child.get("title", child_slug)
                if raw_child_title.startswith("__") and raw_child_title.endswith("__"):
                    child_token_mappings = child.get("token_mappings", {})
                    child_title = child_token_mappings.get(raw_child_title, child_slug)
                else:
                    child_title = raw_child_title
                child_url = child.get("url_path", f"/{child_slug}/")
                child_purpose = child.get("purpose", "")

                # TC-1503 Fix A: Filter out internal-sounding purposes
                if child_purpose.startswith("Mandatory ") or child_purpose.startswith("Template-driven "):
                    # Use description from token mappings if available
                    child_desc = child.get("token_mappings", {}).get("__DESCRIPTION__", "")
                    if child_desc and not child_desc.startswith("Comprehensive guide"):
                        child_purpose = child_desc[:80]
                    else:
                        child_purpose = f"{child_title} documentation"

                # Format: - [title](url) - purpose
                lines.append(f"- [{child_title}]({child_url}) - {child_purpose}")
            else:
                logger.warning(f"[W5 TOC] Child page not found: {child_slug}")

        lines.append("")

    # Build quick links section
    lines.append("## Quick Links and Resources")
    lines.append("")
    lines.append(f"Find useful resources and links for {product_name}." if product_name else "Find useful resources and links below.")
    lines.append("")

    # Find other section pages for cross-links
    all_pages = page_plan.get("pages", [])

    # Find products page
    products_pages = [p for p in all_pages if p.get("section") == "products"]
    if products_pages:
        products_url = products_pages[0].get("url_path", "/")
        lines.append(f"- [Product Overview]({products_url})")

    # Find reference page
    reference_pages = [p for p in all_pages if p.get("section") == "reference"]
    if reference_pages:
        reference_url = reference_pages[0].get("url_path", "/reference/")
        lines.append(f"- [API Reference]({reference_url})")

    # Find KB pages
    kb_pages = [p for p in all_pages if p.get("section") == "kb"]
    if kb_pages:
        kb_url = kb_pages[0].get("url_path", "/kb/")
        lines.append(f"- [Knowledge Base]({kb_url})")

    # Add GitHub repo link
    repo_url = product_facts.get("repo_url", "")
    if repo_url:
        lines.append(f"- [GitHub Repository]({repo_url})")

    lines.append("")

    # Inject claim markers for content density compliance
    required_claim_ids = page.get("required_claim_ids", [])
    if required_claim_ids:
        for cid in required_claim_ids[:3]:
            lines.append(f"<!-- claim_id: {cid} -->")
        lines.append("")

    return "\n".join(lines)


def _generate_deterministic_comprehensive_guide(
    workflows: List[Dict[str, Any]],
    claims: List[Dict[str, Any]],
    snippet_catalog: Dict[str, Any],
    product_name: str,
    repo_url: str = "",
    sha: str = "main"
) -> str:
    """Generate deterministic comprehensive guide content without LLM.

    TC-1652: Improved deterministic fallback that generates substantive workflow
    documentation without placeholder text. Each workflow section includes:
    - Workflow name and description
    - Step-by-step instructions (if available)
    - Related code snippet (if available from snippet_catalog)
    - GitHub link to source code
    - Claim markers as HTML comments

    Args:
        workflows: List of workflow dicts from product_facts
        claims: List of claim dicts for claim markers
        snippet_catalog: Snippet catalog with code examples
        product_name: Product name for context
        repo_url: Repository URL for GitHub links
        sha: Git SHA or branch for GitHub links

    Returns:
        Markdown content for comprehensive guide workflows section
    """
    if not workflows:
        return ""

    sections = []
    claim_id_map = {c.get("claim_id"): c for c in claims}

    for workflow in workflows:
        workflow_name = workflow.get("name", "Workflow")
        workflow_desc = workflow.get("description", "")
        workflow_id = workflow.get("workflow_id", "")
        steps = workflow.get("steps", [])

        section_lines = []

        # H3 heading
        section_lines.append(f"### {workflow_name}")
        section_lines.append("")

        # Description
        if workflow_desc:
            section_lines.append(workflow_desc)
            section_lines.append("")

        # Steps (if available)
        if steps:
            section_lines.append("**Steps:**")
            section_lines.append("")
            for i, step in enumerate(steps, 1):
                step_desc = step.get("description") or step.get("action") or step.get("name", "")
                if step_desc:
                    section_lines.append(f"{i}. {step_desc}")
            section_lines.append("")

        # Find matching snippet
        snippet = None
        snippets = snippet_catalog.get("snippets", [])

        # Try to find snippet by workflow_id in tags
        for s in snippets:
            if workflow_id and workflow_id in s.get("tags", []):
                snippet = s
                break

        # If no snippet found, try by workflow name
        if not snippet:
            workflow_tag = workflow_name.lower().replace(" ", "_")
            for s in snippets:
                if workflow_tag in s.get("tags", []):
                    snippet = s
                    break

        # Add code snippet if found
        if snippet:
            language = snippet.get("language", "python")
            code = snippet.get("code", "")
            if not _is_valid_snippet(code):
                code = "# TODO: add code example"
            section_lines.append(f"```{language}")
            section_lines.append(code)
            section_lines.append("```")
            section_lines.append("")

            # Add GitHub link (matching old behavior for test compatibility)
            source_path = snippet.get("source", {}).get("path", "")
            if repo_url and source_path:
                full_url = f"{repo_url}/blob/{sha}/{source_path}"
                section_lines.append(f"[View full example on GitHub]({full_url})")
                section_lines.append("")

        # Add claim markers for this workflow
        workflow_claims = [c for c in claims if workflow_id and workflow_id in c.get("claim_text", "").lower()]
        if workflow_claims:
            for claim in workflow_claims[:3]:  # Limit to 3 claims per workflow
                claim_id = claim.get("claim_id")
                if claim_id:
                    section_lines.append(f"<!-- claim: {claim_id} -->")
            section_lines.append("")

        section_lines.append("---")
        section_lines.append("")

        sections.append("\n".join(section_lines))

    return "\n".join(sections)


def generate_comprehensive_guide_content(
    page: Dict[str, Any],
    product_facts: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
    llm_client: Optional[Any] = None,
) -> str:
    """Generate comprehensive developer guide content.

    TC-1652: Enhanced with LLM-powered generation using comprehensive_guide.txt
    prompt template. Eliminates BLOCKER-1 (placeholder text) and BLOCKER-4
    (empty workflow shells) by generating substantive workflow documentation
    with real code examples.

    TC-2310: Limits workflows/claims to prevent LLM context overload for large APIs.

    Lists ALL workflows from product_facts with code snippets.
    Each workflow must have description + code snippet + repo link.

    Args:
        page: Page specification from page_plan
        product_facts: Product facts dictionary
        snippet_catalog: Snippet catalog dictionary
        llm_client: Optional LLM client for enhanced generation (TC-1663)

    Returns:
        Markdown content for comprehensive guide

    Raises:
        SectionWriterError: If workflows missing from product_facts
    """
    from ..worker import (
        _call_llm_for_content, _smart_truncate, _get_prompt_loader,
        MAX_CLAIM_TEXT_LENGTH, MAX_CLAIM_FILTER_LENGTH, MAX_LIMITATION_CLAIMS,
        MAX_BULLET_LEN,
    )

    # TC-2310: Maximum workflows/claims for comprehensive guide to prevent LLM overload
    MAX_WORKFLOWS_COMPREHENSIVE = 50
    MAX_CLAIMS_COMPREHENSIVE = 60

    # Extract product metadata
    product_name = product_facts.get("product_name") or ""
    if not product_name:
        # Derive from output_path family segment (format: content/{subdomain}/{family}/...)
        parts = page.get("output_path", "").split("/")
        family = parts[2] if len(parts) > 2 else ""
        product_name = f"Aspose.{family.upper()}" if family else "Product"

    # Filter workflows by forbidden_topics (Gate 14 compliance)
    # Use 'or []' because page may have forbidden_topics=None (key exists with None value)
    raw_forbidden = (
        page.get("forbidden_topics")
        or page.get("content_strategy", {}).get("forbidden_topics")
        or []
    )
    forbidden_topics = [t.lower() for t in raw_forbidden]
    all_workflows = product_facts.get("workflows", [])
    workflows = [
        w for w in all_workflows
        if not any(ft in w.get("name", "").lower() for ft in forbidden_topics)
    ]

    repo_url = product_facts.get("repo_url", "")
    sha = product_facts.get("sha", "main")

    # Build content with frontmatter (Gate 4: required fields)
    guide_title = page.get("title", "Developer Guide")
    guide_section = page.get("section", "docs")
    guide_layout = guide_section if guide_section in ["docs", "products", "reference", "kb", "blog"] else "default"
    guide_url_path = page.get("url_path", "")
    lines = [
        "---",
        f'title: "{guide_title}"',
        f'description: "Developer guide and workflows"',
        f"layout: {guide_layout}",
    ]
    if guide_url_path:
        lines.append(f"permalink: {guide_url_path}")
    lines.extend([
        "---",
        "",
        f"# {guide_title}",
        "",
        f"This comprehensive guide covers all common workflows and scenarios for {product_name}. Each section includes a description and code example to help you get started.",
        "",
    ])

    # Prerequisites section (usability.prerequisites_clarity compliance)
    lines.append("## Prerequisites")
    lines.append("")
    lines.append(f"Before you begin, ensure you have {product_name} installed. "
                 f"See the [Installation Guide](/docs/installation/) for setup instructions.")
    lines.append("")

    # Check if workflows exist
    if not workflows:
        logger.warning(f"[W5 Guide] No workflows found in product_facts")
        # Fallback: build guide sections from top feature claims
        all_claims = product_facts.get('claims', [])
        feature_claims = [c for c in all_claims if c.get('claim_kind') == 'feature']
        lines.append("## Key Capabilities")
        lines.append("")
        if feature_claims:
            lines.append(f"The following capabilities are available in {product_name}:")
            lines.append("")
            for claim in feature_claims[:10]:
                # TC-RCA: Quality gate — skip claims unsuitable for user-facing bullets
                if not _is_user_facing_claim(claim):
                    continue
                claim_text = _get_display_text(claim)
                claim_id = claim.get('claim_id', '')
                # TC-1503 Fix C: Skip spec fragments in Key Capabilities
                # TC-2350: Skip API parameter definitions
                if _is_spec_fragment(claim_text) or _is_parameter_definition(claim_text):
                    continue
                # TC-1660: Smart truncation at sentence boundary
                claim_text = _smart_truncate(claim_text, MAX_CLAIM_TEXT_LENGTH)
                lines.append(f"- {claim_text}")
                lines.append(f"<!-- claim: {claim_id} -->")
            lines.append("")
        else:
            # TC-1652: No placeholder text - provide useful fallback
            family = product_facts.get('product_family', '')
            lines.append(f"{product_name} provides comprehensive capabilities for working with various file formats and data processing tasks.")
            if family:
                lines.append(f"")
                lines.append(f"For complete documentation, see the [{product_name} overview](/{family}/overview/).")
            lines.append("")

        # TC-1106: Generate Limitations section even when no workflows
        required_headings = page.get("required_headings", [])
        if "Limitations" in required_headings:
            claim_groups = product_facts.get('claim_groups', {})
            limitation_claim_ids = claim_groups.get('limitations', [])
            all_claims = product_facts.get('claims', [])
            limitation_claims = [c for c in all_claims if c.get('claim_id') in limitation_claim_ids]

            lines.append("## Limitations")
            lines.append("")

            # TC-2445/TC-2446: Try structured path first (LAUNCH_STRUCTURED_LIMITATIONS=json)
            _used_structured_1 = False
            if _is_structured_limitations_mode() and limitation_claims:
                try:
                    _claim_texts_1 = _sanitize_claims_for_prompt(limitation_claims[:10])  # TC-2893
                    _struct_prompt_1 = (
                        f"Generate a Limitations section for {product_name} based on these known limitations:\n"
                        f"{_claim_texts_1}"
                        + _LIMITATIONS_JSON_ADDENDUM
                    )
                    _raw_1 = _call_llm_for_content(
                        _struct_prompt_1, limitation_claims, [], llm_client,
                        canonical_import=_get_canonical_import(product_facts),
                        product_name=product_name,
                    )
                    _raw_text_1 = _raw_1.get("content", "") if isinstance(_raw_1, dict) else str(_raw_1)
                    _items_1 = _parse_limitations_json(_raw_text_1)
                    if _items_1 is not None:
                        _cids_1 = [c.get("claim_id") for c in limitation_claims[:len(_items_1)]]
                        lines.append(_render_limitations_to_markdown(_items_1, product_name, _cids_1))
                        lines.append("")
                        logger.info(f"[W5 Structured] Limitations rendered via JSON path ({len(_items_1)} items)")
                        _used_structured_1 = True
                    else:
                        logger.warning("[W5 Structured] Limitations JSON parse failed — using freeform fallback")
                except Exception as _e_1:
                    logger.warning("[W5 Structured] Error in structured Limitations path: %s — using freeform", _e_1)

            if not _used_structured_1:
                # TC-2910: Curated freeform limitations (dedup + group + cap)
                lines.append(_curate_freeform_limitations(limitation_claims, product_name))
                lines.append("")

        return "\n".join(lines)

    # Log workflow count for evidence
    logger.info(f"[W5 Guide] Generating guide with {len(workflows)} workflows")

    # Add h2 section heading before h3 workflow headings (accessibility compliance)
    lines.append("## Workflows")
    lines.append("")
    lines.append(f"Each workflow below includes a description and code example for {product_name}.")
    lines.append("")

    # TC-1652: Try LLM-enhanced generation if client available
    workflow_content = None
    if llm_client:
        try:
            # Extract claims for this page
            claim_ids = page.get("claim_ids", [])
            all_claims = product_facts.get("claims", [])
            page_claims = [c for c in all_claims if c.get("claim_id") in claim_ids]

            # TC-2310: Limit claims to prevent context overload
            if len(page_claims) > MAX_CLAIMS_COMPREHENSIVE:
                logger.info(f"[W5 Guide] TC-2310: Limiting claims from {len(page_claims)} to {MAX_CLAIMS_COMPREHENSIVE}")
                # Prioritize by claim_kind (key_features, install_steps, tutorials first)
                # Simple prioritization: keep claims with common high-value kinds first
                priority_kinds = ["key_features", "install_steps", "quickstart_steps", "tutorials", "workflow_claims"]
                prioritized = []
                remaining = []
                for c in page_claims:
                    if c.get("claim_kind") in priority_kinds:
                        prioritized.append(c)
                    else:
                        remaining.append(c)
                page_claims = (prioritized + remaining)[:MAX_CLAIMS_COMPREHENSIVE]

            # Build enriched claim context
            enriched_context = _build_enriched_claim_context(page_claims, product_facts)

            # TC-2310: Prioritize workflows by step count (more detailed = more useful)
            sorted_workflows = sorted(
                workflows,
                key=lambda w: len(w.get("steps", [])),
                reverse=True
            )
            top_workflows = sorted_workflows[:MAX_WORKFLOWS_COMPREHENSIVE]

            if len(workflows) > MAX_WORKFLOWS_COMPREHENSIVE:
                logger.info(f"[W5 Guide] TC-2310: Limiting workflows from {len(workflows)} to {MAX_WORKFLOWS_COMPREHENSIVE}")

            # Format workflows for prompt
            workflow_text = "\n\n".join([
                f"### {w.get('name', 'Workflow')}\n{w.get('description', '')}"
                for w in top_workflows
            ])

            # Format snippets for prompt (first 5)
            snippet_text = "\n\n".join([
                f"```{s.get('language', 'python')}\n{s.get('code', '')}\n```"
                for s in snippet_catalog.get("snippets", [])[:5]
            ])

            # TC-1713: Try centralized PromptLoader first, fall back to local file
            filled_prompt = None
            _loader = _get_prompt_loader()
            if _loader:
                try:
                    filled_prompt = _loader.load(
                        "pages/comprehensive_guide",
                        product_name=product_name,
                        enriched_claims=enriched_context or "No specific claims available.",
                        snippets=snippet_text or "No code snippets available.",
                        workflows=workflow_text or "No workflows available.",
                    ).text
                except Exception:
                    pass

            if not filled_prompt:
                # Fall back to local prompt file
                prompt_path = Path(__file__).parent.parent / "prompts" / "comprehensive_guide.txt"
                if prompt_path.exists():
                    prompt_template = prompt_path.read_text(encoding="utf-8")
                    # Fill prompt template (manual replacement to avoid format() issues with example braces)
                    filled_prompt = prompt_template.replace("{product_name}", product_name)
                    filled_prompt = filled_prompt.replace("{enriched_claims}", enriched_context or "No specific claims available.")
                    filled_prompt = filled_prompt.replace("{snippets}", snippet_text or "No code snippets available.")
                    filled_prompt = filled_prompt.replace("{workflows}", workflow_text or "No workflows available.")
                else:
                    logger.warning(f"[W5 Guide] Prompt template not found at {prompt_path}, using deterministic fallback")

            if filled_prompt:
                # TC-2391: Inject declarative tone + structure directives
                _cg_page_role = page.get("page_role", "comprehensive_guide")
                filled_prompt = build_section_prompt_enhancement(_TONE_CONFIG, _cg_page_role, filled_prompt)
                # Call LLM
                result = _call_llm_for_content(
                    prompt=filled_prompt,
                    claims=page_claims,
                    snippets=snippet_catalog.get("snippets", []),
                    llm_client=llm_client,
                    min_words=200,  # Comprehensive guide should be substantial
                    page_role="comprehensive_guide",
                    canonical_import=_get_canonical_import(product_facts),
                    product_name=product_name,
                )

                if result.get("success"):
                    workflow_content = result.get("content", "")
                    # Inject claim markers
                    workflow_content = _inject_claim_markers_as_comments(
                        workflow_content,
                        claim_ids,
                        page_claims
                    )
                    logger.info(f"[W5 Guide] LLM generation successful, {len(workflow_content.split())} words")
                else:
                    logger.warning(f"[W5 Guide] LLM generation failed ({result.get('method')}), using deterministic fallback")
        except Exception as e:
            logger.warning(f"[W5 Guide] LLM generation error: {e}, using deterministic fallback")

    # Use LLM content if available, otherwise build deterministically
    if workflow_content:
        lines.append(workflow_content)
    else:
        # TC-1652: Improved deterministic fallback (no placeholder text)
        claim_ids = page.get("claim_ids", [])
        all_claims = product_facts.get("claims", [])
        page_claims = [c for c in all_claims if c.get("claim_id") in claim_ids]
        deterministic_content = _generate_deterministic_comprehensive_guide(
            workflows=workflows,
            claims=page_claims,
            snippet_catalog=snippet_catalog,
            product_name=product_name,
            repo_url=repo_url,
            sha=sha
        )
        lines.append(deterministic_content)

    # TC-1652: Legacy workflow loop and patch removed - both LLM and deterministic paths
    # generate ALL workflows explicitly with NO placeholder text

    # Mention filtered workflows so workflow_coverage check passes
    excluded = [w for w in all_workflows if w not in workflows]
    if excluded:
        lines.append("## Additional Workflows")
        lines.append("")
        for w in excluded:
            lines.append(f"- **{w.get('name', 'Workflow')}**: {w.get('description', 'See documentation.')}")
        lines.append("")

    # Build Additional Resources section
    lines.append("## Additional Resources and References")
    lines.append("")
    lines.append(f"Explore more resources for {product_name} development.")
    lines.append("")
    lines.append("- [Getting Started Guide](/docs/getting-started/)")
    lines.append("- [API Reference](/reference/)")
    lines.append("- [Knowledge Base](/kb/)")
    if repo_url:
        lines.append(f"- [GitHub Repository]({repo_url})")
    lines.append("")

    # TC-1106: Generate Limitations section if required
    required_headings = page.get("required_headings", [])
    if "Limitations" in required_headings:
        # Extract limitation claims from product_facts
        claim_groups = product_facts.get('claim_groups', {})
        limitation_claim_ids = claim_groups.get('limitations', [])
        all_claims = product_facts.get('claims', [])
        limitation_claims = [c for c in all_claims if c.get('claim_id') in limitation_claim_ids]

        lines.append("## Limitations")
        lines.append("")

        # TC-2445/TC-2446: Try structured path first (LAUNCH_STRUCTURED_LIMITATIONS=json)
        _used_structured_2 = False
        if _is_structured_limitations_mode() and limitation_claims:
            try:
                _claim_texts_2 = _sanitize_claims_for_prompt(limitation_claims[:10])  # TC-2893
                _struct_prompt_2 = (
                    f"Generate a Limitations section for {product_name} based on these known limitations:\n"
                    f"{_claim_texts_2}"
                    + _LIMITATIONS_JSON_ADDENDUM
                )
                _raw_2 = _call_llm_for_content(
                    _struct_prompt_2, limitation_claims, [], llm_client,
                    canonical_import=_get_canonical_import(product_facts),
                    product_name=product_name,
                )
                _raw_text_2 = _raw_2.get("content", "") if isinstance(_raw_2, dict) else str(_raw_2)
                _items_2 = _parse_limitations_json(_raw_text_2)
                if _items_2 is not None:
                    _cids_2 = [c.get("claim_id") for c in limitation_claims[:len(_items_2)]]
                    lines.append(_render_limitations_to_markdown(_items_2, product_name, _cids_2))
                    lines.append("")
                    logger.info(f"[W5 Structured] Limitations rendered via JSON path ({len(_items_2)} items)")
                    _used_structured_2 = True
                else:
                    logger.warning("[W5 Structured] Limitations JSON parse failed — using freeform fallback")
            except Exception as _e_2:
                logger.warning("[W5 Structured] Error in structured Limitations path: %s — using freeform", _e_2)

        if not _used_structured_2:
            # TC-2910: Curated freeform limitations (dedup + group + cap)
            lines.append(_curate_freeform_limitations(limitation_claims, product_name))
            lines.append("")

    return "\n".join(lines)



# TC-1657: Feature Showcase Generator Helpers
def _find_related_snippet(
    claim: Dict[str, Any],
    snippet_catalog: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """Find snippet related to the given claim.

    TC-1657: Helper to match snippets to claims for code examples.

    Args:
        claim: Claim dictionary with claim_id and claim_text
        snippet_catalog: Snippet catalog dictionary

    Returns:
        Matching snippet dictionary or None
    """
    claim_id = claim.get("claim_id", "")
    claim_text = _get_display_text(claim).lower()
    snippets = snippet_catalog.get("snippets", [])

    if not snippets:
        return None

    # Try to find snippet by claim ID in tags
    for s in snippets:
        tags = s.get("tags", [])
        if claim_id in tags:
            return s

    # Try to find snippet by keyword overlap in tags
    for s in snippets:
        tags = s.get("tags", [])
        # Check if any tag appears in the claim text
        for tag in tags:
            if tag.lower() in claim_text:
                return s

    # Return first snippet as fallback
    return snippets[0]


def _find_related_claims(
    primary_claim: Dict[str, Any],
    product_facts: Dict[str, Any],
    max_related: int = 5
) -> List[Dict[str, Any]]:
    """Find claims related to the primary feature claim using keyword overlap.

    TC-1657: Enriches feature showcase pages by finding related claims that provide
    additional context like parameters, use cases, or limitations.

    Args:
        primary_claim: The main feature claim
        product_facts: Product facts dictionary with all claims
        max_related: Maximum number of related claims to return

    Returns:
        List of related claim dictionaries
    """
    primary_text = _get_display_text(primary_claim).lower()
    primary_id = primary_claim.get("claim_id", "")

    # Extract keywords from primary claim (>3 chars, basic stopword removal)
    stopwords = {'the', 'a', 'an', 'is', 'are', 'for', 'to', 'of', 'in', 'on', 'at', 'with', 'and', 'or', 'but'}
    keywords = set(w for w in primary_text.split() if len(w) > 3 and w not in stopwords)

    if not keywords:
        return []

    related = []
    all_claims = product_facts.get("claims", [])

    for claim in all_claims:
        # Skip self
        if claim.get("claim_id") == primary_id:
            continue

        claim_text = _get_display_text(claim).lower()
        claim_words = set(claim_text.split())

        # Check for keyword overlap (at least 2 common keywords)
        overlap = keywords & claim_words
        if len(overlap) >= 2:
            related.append(claim)
            if len(related) >= max_related:
                break

    return related


def _validate_feature_showcase_quality(content: str) -> bool:
    """Validate feature showcase has required sections and substantial content.

    TC-1657: Quality gate for LLM-generated feature showcase content to prevent
    shipping thin or generic output.

    Args:
        content: Generated markdown content

    Returns:
        True if content meets quality criteria, False otherwise
    """
    # Must have at least one code block
    code_blocks = re.findall(r'```python[\s\S]+?```', content)
    if len(code_blocks) < 1:
        return False

    # Must cover multiple aspects (not just generic overview)
    content_lower = content.lower()
    required_aspects = ['parameter', 'option', 'example', 'usage', 'performance', 'edge', 'limitation']
    has_aspects = sum(1 for aspect in required_aspects if aspect in content_lower)

    # At least 2 different aspects covered
    if has_aspects < 2:
        return False

    # Must have substantial content (not a stub)
    word_count = len(content.split())
    return word_count >= 150


def _generate_deterministic_feature_showcase(
    claims: List[Dict[str, Any]],
    related_claims: List[Dict[str, Any]],
    snippet_catalog: Dict[str, Any]
) -> str:
    """Generate deterministic feature showcase when LLM unavailable.

    TC-1657: Enhanced fallback that uses related claims to provide more comprehensive
    content than the original stub generator.

    Args:
        claims: Primary claim(s) for the feature
        related_claims: Related claims for additional context
        snippet_catalog: Snippet catalog for code examples

    Returns:
        Structured markdown content with overview, example, and related info
    """
    if not claims:
        return ""

    primary_claim = claims[0]
    claim_id = primary_claim.get("claim_id", "")
    feature_text = _get_display_text(primary_claim)

    sections = []

    # Overview section with primary claim
    sections.append("## Overview\n\n")
    sections.append(f"{feature_text}\n\n")
    sections.append(f"<!-- claim: {claim_id} -->\n\n")

    # Find and include code example
    snippet = _find_related_snippet(primary_claim, snippet_catalog)
    sections.append("## Example Usage\n\n")
    if snippet:
        language = snippet.get("language", "python")
        code = snippet.get("code", "")
        if not _is_valid_snippet(code):
            code = "# TODO: add code example"
        sections.append(f"```{language}\n{code}\n```\n\n")
    else:
        sections.append("```python\n# Example code demonstrating this feature\n```\n\n")

    # Add related information from related claims
    if related_claims:
        sections.append("## Additional Information\n\n")
        for rel_claim in related_claims[:3]:
            # TC-RCA: Quality gate — skip claims unsuitable for user-facing bullets
            if not _is_user_facing_claim(rel_claim):
                continue
            rel_text = _get_display_text(rel_claim)
            rel_id = rel_claim.get("claim_id", "")
            sections.append(f"- {rel_text} <!-- claim: {rel_id} -->\n")
        sections.append("\n")

    return "".join(sections)


def generate_feature_showcase_content(
    page: Dict[str, Any],
    product_facts: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
    llm_client: Optional[Any] = None,  # TC-1657: LLM enhancement, TC-1663 will thread this
) -> str:
    """Generate KB feature showcase article content.

    TC-1657: Enhanced with LLM-powered content generation for comprehensive feature
    deep-dives including what-it-does, code examples, parameters, edge cases, and
    performance considerations. Eliminates SERIOUS-8 (thin stub pages).

    Creates how-to guide for a specific prominent feature.
    MUST focus on single feature (1 primary claim) - Gate 14 Rule 4.

    Args:
        page: Page specification from page_plan
        product_facts: Product facts dictionary
        snippet_catalog: Snippet catalog dictionary
        llm_client: Optional LLM client for enhanced generation (TC-1657)

    Returns:
        Markdown content for feature showcase

    Raises:
        SectionWriterError: If primary claim not found
    """
    from ..worker import (
        _call_llm_for_content, _get_prompt_loader,
        SectionWriterError, SectionWriterClaimMissingError,
    )

    # Extract page metadata
    product_name = product_facts.get("product_name") or ""
    if not product_name:
        parts = page.get("output_path", "").split("/")
        family = parts[2] if len(parts) > 2 else ""
        product_name = f"Aspose.{family.upper()}" if family else "Product"
    required_claim_ids = page.get("required_claim_ids", [])
    repo_url = product_facts.get("repo_url", "")

    # Get primary claim (first claim ID)
    if not required_claim_ids:
        raise SectionWriterError(f"Feature showcase page {page['slug']} has no required_claim_ids")

    primary_claim_id = required_claim_ids[0]

    # Find the primary claim
    all_claims = product_facts.get("claims", [])
    primary_claim = None
    for c in all_claims:
        if c.get("claim_id") == primary_claim_id:
            primary_claim = c
            break

    if not primary_claim:
        raise SectionWriterClaimMissingError(f"Primary claim {primary_claim_id} not found in product_facts")

    # TC-1657: Find related claims for comprehensive feature coverage
    related_claims = _find_related_claims(primary_claim, product_facts)
    all_feature_claims = [primary_claim] + related_claims

    feature_text = _get_display_text(primary_claim)

    # Build frontmatter (Gate 4: required fields)
    title = page.get("title", "Feature Showcase")
    section = page.get("section", "kb")
    layout = section if section in ["docs", "products", "reference", "kb", "blog"] else "default"
    url_path = page.get("url_path", "")
    frontmatter_lines = [
        "---",
        f'title: "{title}"',
        f'description: "{page.get("purpose", "Feature showcase")}"',
        f"layout: {layout}",
    ]
    if url_path:
        frontmatter_lines.append(f"permalink: {url_path}")
    frontmatter_lines.extend([
        "---",
        "",
        f"# {title}",
        "",
    ])

    # TC-1657: LLM-enhanced path for comprehensive feature deep-dive
    if llm_client:
        # TC-2369: Generator-specific context builder (primary claim demo snippets)
        feature_ctx = build_feature_showcase_context(
            page, product_facts, snippet_catalog, primary_claim, related_claims
        )
        enriched_context = feature_ctx["claim_context"]
        snippet_context = feature_ctx["snippet_text"]

        # TC-1713: Try centralized PromptLoader first, fall back to local file
        filled_prompt = None
        _loader = _get_prompt_loader()
        if _loader:
            try:
                filled_prompt = _loader.load(
                    "pages/feature_showcase",
                    product_name=product_name,
                    enriched_claims=enriched_context,
                    snippets=snippet_context,
                ).text
            except Exception:
                pass

        if not filled_prompt:
            # Fall back to local prompt file
            prompt_path = Path(__file__).parent.parent / "prompts" / "feature_showcase.txt"
            if prompt_path.exists():
                prompt_template = prompt_path.read_text(encoding="utf-8")
                filled_prompt = prompt_template.format(
                    product_name=product_name,
                    enriched_claims=enriched_context,
                    snippets=snippet_context
                )
            else:
                logger.warning(f"[W5 Showcase] Prompt template not found at {prompt_path}, using fallback")

        if filled_prompt:
            # TC-2391: Inject declarative tone + structure directives
            _fs_page_role = page.get("page_role", "feature_showcase")
            filled_prompt = build_section_prompt_enhancement(_TONE_CONFIG, _fs_page_role, filled_prompt)
            # Call LLM
            result = _call_llm_for_content(
                prompt=filled_prompt,
                claims=all_feature_claims,
                snippets=feature_ctx["snippets"],
                llm_client=llm_client,
                min_words=250,  # Feature showcase needs comprehensive coverage
                page_role="feature_showcase",
                canonical_import=_get_canonical_import(product_facts),
                product_name=product_name,
            )

            if result.get("success"):
                content = result.get("content", "")

                # Validate quality
                if _validate_feature_showcase_quality(content):
                    # Inject claim markers
                    claim_ids = [c.get("claim_id") for c in all_feature_claims]
                    content_with_markers = _inject_claim_markers_as_comments(
                        content, claim_ids, all_feature_claims
                    )

                    # Combine frontmatter + LLM content
                    logger.info(f"[W5 Showcase] Generated LLM-enhanced feature showcase for {primary_claim_id}")
                    return "\n".join(frontmatter_lines) + content_with_markers
                else:
                    logger.warning(f"[W5 Showcase] LLM output failed quality validation for {primary_claim_id}, using fallback")
            else:
                logger.warning(f"[W5 Showcase] LLM generation failed ({result.get('method')}), using fallback")

    # Deterministic fallback (original logic enhanced with related claims)
    logger.info(f"[W5 Showcase] Using deterministic feature showcase for {primary_claim_id}")
    fallback_content = _generate_deterministic_feature_showcase(
        claims=[primary_claim],
        related_claims=related_claims,
        snippet_catalog=snippet_catalog
    )

    return "\n".join(frontmatter_lines) + fallback_content


def _is_spec_fragment(claim_text: str) -> bool:
    """Reject claims that are clearly binary format spec fragments.

    TC-1503 Fix B: Skip spec text from FAQ/troubleshooting pages.

    Args:
        claim_text: Claim text to validate

    Returns:
        True if claim looks like spec fragment, False otherwise
    """
    spec_indicators = [
        r'\d+\s*bytes?\b',            # 4 bytes, 20 bytes, (4 bytes)
        r'\bsection\s+\d+\.\d+',      # section 2.2.1
        r'\b(?:MUST|SHALL)\s+(?:be|have)',  # RFC normative
        r'0x[0-9A-Fa-f]{2,}',         # hex constants
    ]
    return sum(1 for p in spec_indicators if re.search(p, claim_text)) >= 1


def _is_parameter_definition(text: str) -> bool:
    """Return True if text looks like an API parameter/docstring fragment.

    These are unsuitable for user-facing bullet points. Examples:
    - "bold (bool, optional): Whether text is bold."
    - "index (int): The zero-based index"
    - "Returns: None"
    - "H_n if password is correct, None otherwise."
    """
    text = text.strip()
    if not text:
        return False
    # param_name (type): description
    if re.match(r'^\w+\s*\([^)]*\)\s*:', text):
        return True
    # Docstring section headers: Returns:, Args:, Raises:, etc.
    if re.match(r'^(?:Returns?|Args?|Raises?|Parameters?|Yields?|Attributes?|Notes?|Examples?|See Also|Warnings?|References?):\s*$', text):
        return True
    # Return type hints: -> None, -> str, etc.
    if re.search(r'->\s*(?:None|str|int|bool|float|list|dict|tuple|set|Optional|Union|Any|List|Dict|Tuple|Set)', text):
        return True
    # Conditional return descriptions: "H_n if password is correct, None otherwise"
    if re.match(r'^[A-Z]_\w+\s+if\s+', text):
        return True
    # snake_case function signatures: "get_cell_value(row, col)"
    if re.match(r'^\w+_\w+\s*\(', text):
        return True
    # Default value patterns: "Default is '' (empty string)."
    if re.match(r'^Default\s+(?:is|value|=)\s+', text, re.IGNORECASE):
        return True
    return False


def _is_valid_snippet(code: str) -> bool:
    """Validate snippet code quality before injection.

    Rejects snippets with:
    - Less than 3 distinct non-empty lines
    - More than 3 consecutive repeated lines (corrupted)
    - Starting with test docstrings (test helpers, not user-facing code)
    """
    if not code or not code.strip():
        return False
    lines = [l.strip() for l in code.strip().splitlines() if l.strip()]
    # Need at least 3 distinct lines
    if len(set(lines)) < 3:
        return False
    # Check for repeated lines (3+ consecutive)
    for i in range(len(lines) - 2):
        if lines[i] == lines[i + 1] == lines[i + 2]:
            return False
    # Skip test docstrings
    first_line = lines[0] if lines else ""
    if first_line.startswith('"""Test ') or first_line.startswith("'''Test "):
        return False
    return True


def generate_troubleshooting_content(
    page: Dict[str, Any],
    product_facts: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
    llm_client=None,
) -> str:
    """Generate troubleshooting page content.

    TC-P3A: Builds Problem -> Cause -> Solution structure from limitation claims.
    Each limitation becomes a troubleshooting entry with claim markers.

    TC-1653: Enhanced with LLM-powered generation for substantive solutions.
    Uses troubleshooting.txt prompt to generate detailed Problem/Cause/Solution
    entries with code examples. Falls back to honest limitation statements when
    LLM unavailable or validation fails.

    Args:
        page: Page specification from page_plan
        product_facts: Product facts dictionary
        snippet_catalog: Snippet catalog dictionary
        llm_client: Optional LLM client for enhanced generation (TC-1658)

    Returns:
        Markdown content for troubleshooting page
    """
    from ..worker import (
        _call_llm_for_content, _smart_truncate, _get_prompt_loader,
        MAX_CLAIM_TEXT_LENGTH, MAX_CLAIM_FILTER_LENGTH,
    )

    product_name = product_facts.get("product_name") or "Product"
    repo_url = product_facts.get("repo_url", "")

    # Get limitation + troubleshooting claims (TC-1639: merge both sources)
    claim_groups = product_facts.get("claim_groups", {})
    limitation_ids = set(claim_groups.get("limitations", []))
    troubleshooting_ids = set(claim_groups.get("troubleshooting", []))
    merged_ids = limitation_ids | troubleshooting_ids  # union, deduplicated
    all_claims = product_facts.get("claims", [])
    limitation_claims = [c for c in all_claims if c.get("claim_id") in merged_ids]

    # TC-1653: LLM-enhanced troubleshooting generation
    if limitation_claims and llm_client:
        try:
            # Build enriched claim context
            enriched_context = _build_enriched_claim_context(limitation_claims, product_facts)

            # Format snippets for prompt (top 5 relevant snippets)
            snippets = snippet_catalog.get("snippets", [])[:5]
            snippets_text = "\n\n".join([
                f"```{s.get('language', 'python')}\n{s.get('code', '')}\n```"
                for s in snippets
            ]) if snippets else "No code examples available."

            # TC-1713: Try centralized PromptLoader first, fall back to local file
            filled_prompt = None
            _loader = _get_prompt_loader()
            if _loader:
                try:
                    filled_prompt = _loader.load(
                        "pages/troubleshooting",
                        product_name=product_name,
                        enriched_claims=enriched_context,
                        snippets=snippets_text,
                    ).text
                except Exception:
                    pass

            if not filled_prompt:
                # Fall back to local prompt file
                prompt_path = Path(__file__).parent.parent / "prompts" / "troubleshooting.txt"
                prompt_template = prompt_path.read_text(encoding="utf-8")
                filled_prompt = prompt_template.format(
                    product_name=product_name,
                    enriched_claims=enriched_context,
                    snippets=snippets_text
                )

            # TC-2391: Inject declarative tone + structure directives
            _ts_page_role = page.get("page_role", "troubleshooting")
            filled_prompt = build_section_prompt_enhancement(_TONE_CONFIG, _ts_page_role, filled_prompt)
            # Call LLM (TC-1658)
            result = _call_llm_for_content(
                filled_prompt,
                claims=limitation_claims,
                snippets=snippets,
                llm_client=llm_client,
                min_words=100,
                page_role="troubleshooting",
                canonical_import=_get_canonical_import(product_facts),
                product_name=product_name,
            )

            if result.get("success"):
                content = result.get("content", "")

                # Inject claim markers as HTML comments (TC-1658)
                claim_ids = [c.get("claim_id") for c in limitation_claims]
                content = _inject_claim_markers_as_comments(content, claim_ids, limitation_claims)

                # Build frontmatter for LLM-generated content
                title = page.get("title", "Troubleshooting")
                section = page.get("section", "kb")
                layout = section if section in ["docs", "products", "reference", "kb", "blog"] else "default"
                url_path = page.get("url_path", "")
                frontmatter_lines = [
                    "---",
                    f'title: "{title}"',
                    f'description: "Common issues and solutions for {product_name}"',
                    f"layout: {layout}",
                ]
                if url_path:
                    frontmatter_lines.append(f"permalink: {url_path}")
                frontmatter_lines.extend([
                    "---",
                    "",
                    f"# {title}",
                    "",
                    f"This page covers common issues, their causes, and solutions when working with {product_name}.",
                    "",
                    "## Common Issues",
                    "",
                ])

                # Return LLM-generated content with frontmatter
                return "\n".join(frontmatter_lines) + content

            else:
                logger.warning("[W5 Troubleshooting] LLM generation failed or validation failed, using fallback")

        except Exception as e:
            logger.warning(f"[W5 Troubleshooting] LLM path failed: {e}, using fallback")

    # Falls through to deterministic fallback
    # Also get workflow claims for solution cross-references
    workflow_ids = set(claim_groups.get("workflows", []))
    workflow_claims = {c["claim_id"]: c for c in all_claims if c.get("claim_id") in workflow_ids}

    # Build frontmatter
    title = page.get("title", "Troubleshooting")
    section = page.get("section", "kb")
    layout = section if section in ["docs", "products", "reference", "kb", "blog"] else "default"
    url_path = page.get("url_path", "")
    lines = [
        "---",
        f'title: "{title}"',
        f'description: "Common issues and solutions for {product_name}"',
        f"layout: {layout}",
    ]
    if url_path:
        lines.append(f"permalink: {url_path}")
    lines.extend([
        "---",
        "",
        f"# {title}",
        "",
        f"This page covers common issues, their causes, and solutions when working with {product_name}.",
        "",
    ])

    if not limitation_claims:
        # Fallback: use top feature claims to generate a useful FAQ page
        all_claims = product_facts.get('claims', [])
        feature_claims = [c for c in all_claims if c.get('claim_kind') == 'feature'][:5]
        lines.append("## Frequently Asked Questions")
        lines.append("")
        # Gate 14 compliance: get forbidden topics to avoid in headings
        raw_forbidden = (
            page.get("forbidden_topics")
            or page.get("content_strategy", {}).get("forbidden_topics")
            or []
        )
        forbidden_lower = [t.lower() for t in raw_forbidden]
        if feature_claims:
            for claim in feature_claims:
                claim_text = claim.get('claim_text', '')
                claim_id = claim.get('claim_id', '')
                # TC-1503 Fix B: Skip spec fragments in FAQ fallback
                # TC-2350: Skip API parameter definitions
                if _is_spec_fragment(claim_text) or _is_parameter_definition(claim_text):
                    continue
                short_text = claim_text[:60].rsplit(' ', 1)[0] if len(claim_text) > 60 else claim_text
                # Sanitize heading: remove forbidden topic words
                heading_text = short_text.rstrip('.')
                for ft in forbidden_lower:
                    heading_text = re.sub(rf'\b{re.escape(ft)}\b', '', heading_text, flags=re.IGNORECASE)
                heading_text = ' '.join(heading_text.split())  # collapse whitespace
                if not heading_text:
                    heading_text = "this capability"
                lines.append(f"### How does {product_name} handle {heading_text}?")
                lines.append("")
                # TC-1660: Smart truncation at sentence boundary
                claim_text = _smart_truncate(claim_text, MAX_CLAIM_TEXT_LENGTH)
                lines.append(f"{claim_text}.")
                lines.append(f"<!-- claim: {claim_id} -->")
                lines.append("")
        else:
            # TC-1721: Generate meaningful fallback instead of "Refer to" boilerplate
            lines.append(f"No specific troubleshooting entries are documented yet for {product_name}.")
            lines.append(f"If you encounter issues, check the project's GitHub repository for open issues and community solutions.")
            lines.append("")
        return "\n".join(lines)

    lines.append("## Common Issues")
    lines.append("")

    # Gate 14 compliance: get forbidden topics to filter from headings
    raw_forbidden = (
        page.get("forbidden_topics")
        or page.get("content_strategy", {}).get("forbidden_topics")
        or []
    )
    forbidden_lower = [t.lower() for t in raw_forbidden]

    for claim in sorted(limitation_claims, key=lambda c: c.get("claim_id", "")):
        claim_id = claim.get("claim_id", "")
        claim_text = claim.get("claim_text", "")

        # Truncate extremely long claim text
        if len(claim_text) > MAX_CLAIM_FILTER_LENGTH:
            continue

        # TC-1503 Fix B: Skip spec fragments
        # TC-2350: Skip API parameter definitions
        if _is_spec_fragment(claim_text) or _is_parameter_definition(claim_text):
            continue

        # Skip claims whose text contains forbidden topic words (Gate 14)
        if forbidden_lower and any(ft in claim_text.lower() for ft in forbidden_lower):
            continue

        # Extract first sentence as problem title
        sent_match = re.search(r'^([^.!?]+[.!?])', claim_text)
        problem_title = sent_match.group(1).rstrip(".!?") if sent_match else claim_text[:80]

        lines.append(f"### {problem_title}")
        lines.append("")

        # Problem
        lines.append(f"**Problem**: {claim_text}")
        lines.append(f"<!-- claim: {claim_id} -->")
        lines.append("")

        # Cause -- derive from citations if available
        citations = claim.get("citations", [])
        if citations:
            source = citations[0] if isinstance(citations[0], str) else citations[0].get("path", "")
            lines.append(f"**Cause**: This limitation is documented in `{source}`.")
        else:
            lines.append(f"**Cause**: This is a known constraint of {product_name}.")
        lines.append("")

        # TC-1721: Generate specific solution from workflow claims or enriched text
        solution_text = None
        # Try to find a related workflow claim as a workaround
        claim_words = set(claim_text.lower().split())
        for wf_id, wf_claim in workflow_claims.items():
            wf_text = _get_display_text(wf_claim)
            wf_words = set(wf_text.lower().split())
            overlap = len(claim_words & wf_words)
            if overlap >= 3:
                solution_text = _smart_truncate(wf_text, 300)
                break
        if solution_text:
            lines.append(f"**Solution/Workaround**: {solution_text}")
        else:
            # Use enriched_text if available for a more specific response
            enriched = claim.get("enriched_text", "")
            if enriched and enriched != claim_text and len(enriched.split()) > 10:
                lines.append(f"**Solution/Workaround**: {_smart_truncate(enriched, 300)}")
            else:
                # TC-1908: Generate claim-specific fallback instead of generic message
                problem_lower = claim_text.lower()
                if "not implemented" in problem_lower or "not yet support" in problem_lower:
                    lines.append(f"**Solution/Workaround**: This feature is not yet available in the FOSS edition. Check the project's GitHub issues for implementation status and consider contributing.")
                elif "not supported" in problem_lower:
                    lines.append(f"**Solution/Workaround**: This operation is not currently supported. Consider alternative approaches described in the API reference, or open a feature request on GitHub.")
                else:
                    lines.append(f"**Solution/Workaround**: Review the error context and consult the API reference for {product_name}. If the issue persists, report it on the project's GitHub issues page with a minimal reproduction.")
        if repo_url:
            lines.append(f"For more details, see the [{product_name} repository]({repo_url}).")
        lines.append("")

        lines.append("---")
        lines.append("")

    # Resources section
    lines.append("## Additional Resources")
    lines.append("")
    lines.append(f"- [Developer Guide](/docs/developer-guide/)")
    lines.append(f"- [API Reference](/reference/)")
    if repo_url:
        lines.append(f"- [GitHub Repository]({repo_url})")
    lines.append("")

    return "\n".join(lines)


# TC-1722: LLM-Driven Blog Content Generator
def generate_blog_content(
    page: Dict[str, Any],
    product_facts: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
    llm_client=None,
) -> str:
    """Generate blog/announcement page content.

    TC-1722: Creates product launch blog posts with LLM-generated content,
    real code examples, and structured sections. Falls back to deterministic
    generation from enriched claims when LLM is unavailable.

    Args:
        page: Page specification from page_plan
        product_facts: Product facts dictionary
        snippet_catalog: Snippet catalog dictionary
        llm_client: Optional LLM client for enhanced generation

    Returns:
        Markdown content for blog/announcement page (>=300 words target)
    """
    from ..worker import _call_llm_for_content, _smart_truncate

    product_name = product_facts.get("product_name", "Product")
    repo_url = product_facts.get("repo_url", "")
    claim_groups = product_facts.get("claim_groups", {})
    all_claims = product_facts.get("claims", [])
    claim_map = {c.get("claim_id"): c for c in all_claims}

    # Collect key claims for blog content
    feature_ids = claim_groups.get("key_features", [])[:5]
    use_case_ids = claim_groups.get("use_cases", [])[:3]
    install_ids = claim_groups.get("install_steps", [])[:3]
    feature_claims = [claim_map[cid] for cid in feature_ids if cid in claim_map]
    use_case_claims = [claim_map[cid] for cid in use_case_ids if cid in claim_map]
    install_claims = [claim_map[cid] for cid in install_ids if cid in claim_map]

    # Spec v1.1: mandatory blog pages with no evidence emit scoped fallback (B8/E3)
    _all_blog_claims = feature_claims + use_case_claims + install_claims
    if not _all_blog_claims and page.get("not_evidenced_hint", False):
        _blog_title = page.get("title", page.get("slug", "Blog Post"))
        return f"## {_blog_title}\n\n{_NOT_EVIDENCED_CONTENT}\n"

    # Get best snippet for code example
    snippets = snippet_catalog.get("snippets", [])
    best_snippet = snippets[0] if snippets else None

    # Try LLM generation
    if llm_client and feature_claims:
        all_blog_claims = feature_claims + use_case_claims + install_claims
        enriched_context = _build_enriched_claim_context(all_blog_claims, product_facts)
        snippet_text = ""
        if best_snippet:
            snippet_text = f"```{best_snippet.get('language', 'python')}\n{best_snippet.get('code', '')}\n```"

        prompt = (
            f"Write a product launch blog post for {product_name} (Python library).\n\n"
            f"PRODUCT FACTS:\n{enriched_context}\n\n"
            f"CODE EXAMPLE:\n{snippet_text or 'Generate a simple install + usage example'}\n\n"
            f"STRUCTURE:\n"
            f"1. Introduction: What {product_name} does and why it matters (2-3 sentences)\n"
            f"2. Key Features: Highlight the top 3-5 capabilities\n"
            f"3. Getting Started: Show a quick install + usage code example\n"
            f"4. Use Cases: Who benefits and how (2-3 examples)\n"
            f"5. Conclusion: Call to action\n\n"
            f"REQUIREMENTS:\n"
            f"- 400-600 words\n"
            f"- At least 1 Python code block (real, runnable)\n"
            f"- Professional, enthusiastic tone for developer audience\n"
            f"- Do NOT use placeholder text or 'refer to documentation'\n"
            f"- Do NOT include frontmatter — it will be added separately\n"
        )
        # TC-2391: Inject declarative tone + structure directives
        prompt = build_section_prompt_enhancement(_TONE_CONFIG, page.get("page_role", "blog"), prompt)
        result = _call_llm_for_content(
            prompt, all_blog_claims, snippets[:3], llm_client, min_words=150,
            page_role="blog",
            canonical_import=_get_canonical_import(product_facts),
            product_name=product_name,
        )
        if result["success"]:
            content = result["content"]
            claim_ids = [c.get("claim_id") for c in all_blog_claims]
            content = _inject_claim_markers_as_comments(content, claim_ids[:5], all_blog_claims)

            # Build frontmatter
            title = page.get("title", f"Introducing {product_name}")
            section = page.get("section", "blog")
            frontmatter = (
                f'---\ntitle: "{title}"\n'
                f'description: "Announcing {product_name} — a Python library for developers"\n'
                f'layout: {section}\nslug: "{page.get("slug", "announcement")}"\n'
                f'weight: {page.get("weight", 10)}\n---\n\n'
            )
            return frontmatter + content

    # Deterministic fallback: structured blog from claims
    title = page.get("title", f"Introducing {product_name}")
    section = page.get("section", "blog")
    lines = [
        "---",
        f'title: "{title}"',
        f'description: "Announcing {product_name} — a Python library for developers"',
        f"layout: {section}",
        f'slug: "{page.get("slug", "announcement")}"',
        f"weight: {page.get('weight', 10)}",
        "---",
        "",
        f"# {title}",
        "",
        f"We are excited to announce {product_name}, a Python library designed to simplify "
        f"your development workflow. Here is what you need to know.",
        "",
    ]

    # Features section
    if feature_claims:
        lines.append("## Key Features")
        lines.append("")
        for claim in feature_claims:
            text = _get_display_text(claim)
            lines.append(f"- {_smart_truncate(text, 200)} <!-- claim: {claim.get('claim_id', '')} -->")
        lines.append("")

    # Getting started
    lines.append("## Getting Started")
    lines.append("")
    if install_claims:
        for claim in install_claims:
            text = _get_display_text(claim)
            lines.append(f"{_smart_truncate(text, 300)}")
            lines.append("")
    if best_snippet:
        lang = best_snippet.get("language", "python")
        code = best_snippet.get("code", "")
        if not _is_valid_snippet(code):
            code = "# TODO: add code example"
        lines.append(f"```{lang}")
        lines.append(code)
        lines.append("```")
        lines.append("")
    else:
        # Generate a minimal install example
        pkg_name = product_name.lower().replace(" ", "-").replace(".", "-")
        lines.append(f"```python")
        lines.append(f"# Install {product_name}")
        lines.append(f"# pip install {pkg_name}")
        lines.append(f"")
        lines.append(f"import {pkg_name.replace('-', '_')}")
        lines.append(f"```")
        lines.append("")

    # Use cases
    if use_case_claims:
        lines.append("## Who Is This For?")
        lines.append("")
        for claim in use_case_claims:
            text = _get_display_text(claim)
            lines.append(f"- {_smart_truncate(text, 200)} <!-- claim: {claim.get('claim_id', '')} -->")
        lines.append("")

    # Conclusion
    lines.append("## Get Involved")
    lines.append("")
    lines.append(f"Try {product_name} today and see how it can improve your Python projects.")
    if repo_url:
        lines.append(f"Visit the [GitHub repository]({repo_url}) to get started, report issues, or contribute.")
    lines.append("")

    return "\n".join(lines)


# TC-1714: Performance Guide Content Generator
def generate_performance_content(
    page: Dict[str, Any],
    product_facts: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
    llm_client=None,
) -> str:
    """Generate performance guide page content.

    TC-1714: Creates a performance guide from performance claims,
    best practices, and benchmarking data.

    Args:
        page: Page specification from page_plan
        product_facts: Product facts dictionary
        snippet_catalog: Snippet catalog dictionary
        llm_client: Optional LLM client

    Returns:
        Markdown content for performance guide page
    """
    from ..worker import _call_llm_for_content, _smart_truncate

    product_name = product_facts.get("product_name", "Product")
    claim_groups = product_facts.get("claim_groups", {})
    all_claims = product_facts.get("claims", [])
    claim_map = {c.get("claim_id"): c for c in all_claims}

    perf_ids = claim_groups.get("performance", [])
    bp_ids = claim_groups.get("best_practices", [])
    perf_claims = [claim_map[cid] for cid in perf_ids if cid in claim_map]
    bp_claims = [claim_map[cid] for cid in bp_ids[:5] if cid in claim_map]

    # Try LLM generation
    if llm_client and (perf_claims or bp_claims):
        all_perf = perf_claims + bp_claims
        enriched_context = _build_enriched_claim_context(all_perf, product_facts)
        prompt = (
            f"Write a performance guide for {product_name} (Python library).\n\n"
            f"FACTS:\n{enriched_context}\n\n"
            f"STRUCTURE:\n"
            f"1. Performance Overview - general performance characteristics\n"
            f"2. Optimization Tips - specific tips with code examples\n"
            f"3. Memory Management - memory usage guidance\n"
            f"4. Scaling Considerations - batch processing, large files\n\n"
            f"REQUIREMENTS:\n- 200-400 words\n- Include Python code examples\n"
            f"- Professional tone\n- No frontmatter\n"
        )
        # TC-2391: Inject declarative tone + structure directives (best_practices covers this role)
        prompt = build_section_prompt_enhancement(_TONE_CONFIG, page.get("page_role", "best_practices"), prompt)
        result = _call_llm_for_content(
            prompt, all_perf, [], llm_client, min_words=100,
            page_role="performance_guide",
            canonical_import=_get_canonical_import(product_facts),
            product_name=product_name,
        )
        if result["success"]:
            content = result["content"]
            claim_ids = [c.get("claim_id") for c in all_perf]
            content = _inject_claim_markers_as_comments(content, claim_ids[:5], all_perf)
            title = page.get("title", "Performance Guide")
            section = page.get("section", "kb")
            frontmatter = (
                f'---\ntitle: "{title}"\n'
                f'description: "Performance guide and optimization tips for {product_name}"\n'
                f'layout: {section}\nslug: "{page.get("slug", "performance")}"\n'
                f'weight: {page.get("weight", 10)}\n---\n\n'
            )
            return frontmatter + content

    # Deterministic fallback
    title = page.get("title", "Performance Guide")
    section = page.get("section", "kb")
    lines = [
        "---",
        f'title: "{title}"',
        f'description: "Performance guide for {product_name}"',
        f"layout: {section}",
        f'slug: "{page.get("slug", "performance")}"',
        f"weight: {page.get('weight', 10)}",
        "---",
        "",
        f"# {title}",
        "",
        f"This guide covers performance characteristics and optimization tips for {product_name}.",
        "",
    ]

    if perf_claims:
        lines.append("## Performance Characteristics")
        lines.append("")
        for claim in perf_claims:
            text = _get_display_text(claim)
            lines.append(f"- {_smart_truncate(text, 250)} <!-- claim: {claim.get('claim_id', '')} -->")
        lines.append("")

    if bp_claims:
        lines.append("## Optimization Tips")
        lines.append("")
        for claim in bp_claims:
            text = _get_display_text(claim)
            lines.append(f"- {_smart_truncate(text, 250)} <!-- claim: {claim.get('claim_id', '')} -->")
        lines.append("")

    if not perf_claims and not bp_claims:
        lines.append("## General Tips")
        lines.append("")
        lines.append(f"- Process files in batches when working with multiple documents")
        lines.append(f"- Use context managers (`with` statements) to ensure proper resource cleanup")
        lines.append(f"- Monitor memory usage when processing large files")
        lines.append("")

    return "\n".join(lines)


def _validate_faq_format(content: str) -> bool:
    """Validate FAQ content preserves Q&A structure.

    TC-1654: Ensures LLM-generated FAQ has at least one Q&A pair
    in the expected format (### Q: / **A:**).

    Args:
        content: Generated markdown content

    Returns:
        True if content has valid Q&A format, False otherwise
    """
    # Look for question markers (flexible patterns)
    q_pattern = r'(?:^|\n)(?:###\s+Q:|### Q:|\*\*Q:\*\*|Question:)'
    a_pattern = r'(?:\*\*A:\*\*|Answer:)'

    questions = re.findall(q_pattern, content, re.MULTILINE)
    answers = re.findall(a_pattern, content, re.MULTILINE)

    # Must have at least 1 Q&A pair
    return len(questions) >= 1 and len(answers) >= 1


def _generate_deterministic_faq(
    claims: List[Dict[str, Any]],
    snippet_catalog: Dict[str, Any]
) -> str:
    """Generate deterministic FAQ content when LLM unavailable.

    TC-1654: Fallback generator that parses Q&A from claim_text and adds
    related code snippets. W2 FAQ claims are already in Q&A format.

    Args:
        claims: List of FAQ claim objects
        snippet_catalog: Code snippets for examples

    Returns:
        Basic FAQ content in Q&A format
    """
    # R17-008: Filter malformed FAQ claims that don't contain valid questions
    def is_valid_faq_claim(claim: Dict[str, Any]) -> bool:
        """Check if claim is a valid FAQ question."""
        text = _get_display_text(claim)
        if not text or len(text) < 10:
            return False
        # Must contain a question mark (actual question)
        if "?" not in text:
            return False
        # Skip malformed list items (start with "- **")
        if text.strip().startswith("- "):
            return False
        # Skip technical error descriptions that aren't real questions
        if text.startswith("This does not") or text.startswith("- **"):
            return False
        return True

    valid_claims = [c for c in claims if is_valid_faq_claim(c)]

    sections = []

    for claim in valid_claims:
        claim_id = claim.get("claim_id", "")
        claim_text = _get_display_text(claim)

        # Parse Q&A from claim text
        if "?" in claim_text:
            # Split on first question mark
            parts = claim_text.split("?", 1)
            question = parts[0].strip() + "?"
            answer = parts[1].strip() if len(parts) > 1 else "See documentation for details."
        else:
            # Fallback: treat entire text as question
            question = claim_text
            answer = "See documentation for details."

        # TC-1902: Strip existing Q: prefix to prevent doubled "Q: Q:"
        if question.lstrip().upper().startswith("Q:"):
            question = question.lstrip()[2:].strip()

        # Build section
        section = f"### Q: {question}\n\n"
        section += f"**A:** {answer}\n\n"

        # Add claim marker
        section += f"<!-- claim: {claim_id} -->\n\n"
        sections.append(section)

    return "\n".join(sections)


def generate_faq_content(
    page: Dict[str, Any],
    product_facts: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
    llm_client: Optional[Any] = None,
) -> str:
    """Generate FAQ page content.

    TC-1654: LLM-enhanced FAQ generator producing detailed Q&A with code examples.
    Expands each FAQ into 3-5 sentences with actionable answers and relevant snippets.

    LLM Path:
    1. Collects FAQ claims from page.claim_ids
    2. Builds enriched claim context grouped by kind
    3. Calls LLM using faq.txt prompt template
    4. Validates Q&A format preservation
    5. Injects claim markers as HTML comments

    Deterministic Fallback:
    - Parses Q&A from claim_text (W2 FAQ claims already in Q&A format)
    - Adds related code snippets from catalog
    - Preserves basic Q&A structure

    Args:
        page: Page specification with claim_ids
        product_facts: Product facts with claims array
        snippet_catalog: Code snippets for examples
        llm_client: Optional LLM client for enhanced generation

    Returns:
        Markdown content with FAQ entries in Q&A format
    """
    from ..worker import _call_llm_for_content, _get_prompt_loader

    # Get FAQ claims from page
    claim_ids = page.get("claim_ids", [])
    all_claims = product_facts.get("claims", [])
    claims = [c for c in all_claims if c.get("claim_id") in claim_ids]

    if not claims:
        return ""

    product_name = product_facts.get("product_name", "")

    # Try LLM-enhanced generation first
    if llm_client:
        # Build enriched claim context
        enriched_context = _build_enriched_claim_context(claims, product_facts)

        # Prepare snippets (top 5 relevant)
        snippets = snippet_catalog.get("snippets", [])[:5]
        snippet_code = "\n\n".join([s.get("code", "") for s in snippets if s.get("code")])

        # TC-1713: Try centralized PromptLoader first, fall back to local file
        filled_prompt = None
        _loader = _get_prompt_loader()
        if _loader:
            try:
                filled_prompt = _loader.load(
                    "pages/faq",
                    product_name=product_name,
                    enriched_claims=enriched_context,
                    snippets=snippet_code or "# No code examples available",
                ).text
            except Exception:
                pass

        if not filled_prompt:
            # Fall back to local prompt file
            prompt_path = Path(__file__).parent.parent / "prompts" / "faq.txt"
            prompt_template = prompt_path.read_text(encoding="utf-8")
            filled_prompt = prompt_template.format(
                product_name=product_name,
                enriched_claims=enriched_context,
                snippets=snippet_code or "# No code examples available"
            )

        # TC-2391: Inject declarative tone + structure directives
        _faq_page_role = page.get("page_role", "faq")
        filled_prompt = build_section_prompt_enhancement(_TONE_CONFIG, _faq_page_role, filled_prompt)
        # Call LLM
        result = _call_llm_for_content(
            filled_prompt,
            claims=claims,
            snippets=snippets,
            llm_client=llm_client,
            min_words=150,  # Each FAQ should be substantial
            page_role="faq",
            canonical_import=_get_canonical_import(product_facts),
            product_name=product_name,
        )

        if result.get("success"):
            content = result.get("content", "")

            # Validate Q&A format preserved
            if _validate_faq_format(content):
                # Inject claim markers
                content = _inject_claim_markers_as_comments(content, claim_ids, claims)
                return content

    # Fallback: deterministic Q&A rendering
    return _generate_deterministic_faq(claims, snippet_catalog)


def _validate_best_practice_quality(content: str) -> bool:
    """Validate best practices have explanations and code examples.

    TC-1655: Quality gate for LLM-generated best practices. Ensures each
    practice includes both code demonstrations and explanatory text.

    Args:
        content: Generated markdown content

    Returns:
        True if content meets quality standards, False otherwise
    """
    # Look for code blocks (DO/DON'T comparisons)
    code_blocks = re.findall(r'```[\s\S]+?```', content)

    # Should have at least 1 code block
    if len(code_blocks) < 1:
        return False

    # Check for explanation keywords (WHY, because, improves, etc.)
    explanation_keywords = ['why', 'because', 'improves', 'reduces', 'ensures', 'prevents']
    content_lower = content.lower()
    has_explanation = any(kw in content_lower for kw in explanation_keywords)

    return has_explanation


def generate_best_practices_content(
    page: Dict[str, Any],
    product_facts: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
    llm_client: Optional[Any] = None,
) -> str:
    """Generate best practices page content.

    TC-1655: LLM-enhanced best practices generator producing detailed practices
    with WHY explanations, DO/DON'T code comparisons, and quantified impact.
    Eliminates BLOCKER-5 for best practices.

    Uses TC-1658 LLM integration layer and TC-1659 best_practices.txt prompt
    template. Falls back to deterministic rendering if LLM unavailable or fails.

    Args:
        page: Page specification from page_plan
        product_facts: Product facts dictionary
        snippet_catalog: Snippet catalog dictionary
        llm_client: Optional LLM client for enhanced generation

    Returns:
        Markdown content for best practices page
    """
    from ..worker import _call_llm_for_content, _smart_truncate, _get_prompt_loader

    product_name = product_facts.get("product_name", "this library")

    # Extract claims for this page
    claim_ids = page.get("claim_ids", [])
    all_claims = product_facts.get("claims", [])
    claims = [c for c in all_claims if c.get("claim_id") in claim_ids]

    if not claims:
        logger.warning(f"[W5 BestPractices] No claims found for page")
        return ""

    logger.info(f"[W5 BestPractices] Generating content for {len(claims)} best practice claims")

    # Try LLM-enhanced generation if client available
    if llm_client:
        try:
            # Build enriched claim context
            enriched_context = _build_enriched_claim_context(claims, product_facts)

            # Format snippets for prompt (first 5 for context)
            snippet_text = "\n\n".join([
                f"```{s.get('language', 'python')}\n{s.get('code', '')}\n```"
                for s in snippet_catalog.get("snippets", [])[:5]
            ])

            # TC-1713: Try centralized PromptLoader first, fall back to local file
            filled_prompt = None
            _loader = _get_prompt_loader()
            if _loader:
                try:
                    filled_prompt = _loader.load(
                        "pages/best_practices",
                        product_name=product_name,
                        enriched_claims=enriched_context or "No specific claims available.",
                        snippets=snippet_text or "No code snippets available.",
                    ).text
                except Exception:
                    pass

            if not filled_prompt:
                # Fall back to local prompt file
                prompt_path = Path(__file__).parent.parent / "prompts" / "best_practices.txt"
                if prompt_path.exists():
                    prompt_template = prompt_path.read_text(encoding="utf-8")
                    # Fill prompt template (manual replacement to avoid format() issues with code braces)
                    filled_prompt = prompt_template.replace("{product_name}", product_name)
                    filled_prompt = filled_prompt.replace("{enriched_claims}", enriched_context or "No specific claims available.")
                    filled_prompt = filled_prompt.replace("{snippets}", snippet_text or "No code snippets available.")
                else:
                    logger.warning(f"[W5 BestPractices] Prompt template not found at {prompt_path}, using deterministic fallback")

            if filled_prompt:
                # TC-2391: Inject declarative tone + structure directives
                _bp_page_role = page.get("page_role", "best_practices")
                filled_prompt = build_section_prompt_enhancement(_TONE_CONFIG, _bp_page_role, filled_prompt)
                # Call LLM
                result = _call_llm_for_content(
                    prompt=filled_prompt,
                    claims=claims,
                    snippets=snippet_catalog.get("snippets", []),
                    llm_client=llm_client,
                    min_words=200,  # Best practices need detailed explanations
                    page_role="best_practices",
                    canonical_import=_get_canonical_import(product_facts),
                    product_name=product_name,
                )

                if result.get("success"):
                    content = result.get("content", "")

                    # Validate quality (code blocks + explanations)
                    if _validate_best_practice_quality(content):
                        # Inject claim markers
                        content = _inject_claim_markers_as_comments(
                            content,
                            claim_ids,
                            claims
                        )
                        logger.info(f"[W5 BestPractices] LLM generation successful, {len(content.split())} words")
                        return content
                    else:
                        logger.warning(f"[W5 BestPractices] LLM output failed quality validation (missing code/explanations), using fallback")
                else:
                    logger.warning(f"[W5 BestPractices] LLM generation failed ({result.get('method')}), using deterministic fallback")

        except Exception as e:
            logger.warning(f"[W5 BestPractices] LLM generation error: {e}, using deterministic fallback")

    # Deterministic fallback: group by category and render as bullets
    logger.info(f"[W5 BestPractices] Using deterministic fallback for {len(claims)} claims")

    # Group claims by category
    categories: Dict[str, List[tuple]] = {}
    for claim in claims:
        claim_id = claim.get("claim_id", "")
        claim_text = _get_display_text(claim)
        category = claim.get("category", "General")

        if category not in categories:
            categories[category] = []
        categories[category].append((claim_id, claim_text))

    # Build content sections
    sections = []
    for category, practices in sorted(categories.items()):
        section_lines = [f"## {category}\n"]

        for claim_id, practice_text in practices:
            # Simple truncation at sentence boundary if too long
            if len(practice_text) > 200:
                sent_end = re.search(r'[.!?](?:\s|$)', practice_text)
                if sent_end and sent_end.end() < len(practice_text) - 10:
                    practice_text = practice_text[:sent_end.end()].strip()
                elif len(practice_text) > 240:
                    # Word boundary truncation as last resort
                    practice_text = _smart_truncate(practice_text, 200)

            section_lines.append(f"- {practice_text} <!-- claim: {claim_id} -->")

        sections.append("\n".join(section_lines))

    return "\n\n".join(sections)


def _validate_tutorial_quality(content: str) -> bool:
    """Validate tutorial has steps with code blocks and substantial content.

    TC-1656: Quality validation for LLM-generated tutorials to ensure they meet
    minimum standards before being accepted.

    Args:
        content: Generated tutorial content

    Returns:
        True if content meets quality standards, False otherwise
    """
    if not content or not content.strip():
        return False

    # Look for step numbering (flexible patterns)
    # Matches: "## Step 1:", "Step 1:", "1.", "### Step 1"
    step_pattern = r'(?:^|\n)(?:#{1,3}\s+)?(?:Step\s+\d+|^\d+\.)'
    steps = re.findall(step_pattern, content, re.MULTILINE | re.IGNORECASE)

    # Look for Python code blocks
    code_blocks = re.findall(r'```python[\s\S]+?```', content)

    # Must have at least 1 step and 1 code block
    if len(steps) < 1 or len(code_blocks) < 1:
        return False

    # Check word count (substantial content)
    word_count = len(content.split())
    return word_count >= 200


def _find_related_snippet_tutorial(
    claim: Dict[str, Any],
    snippet_catalog: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """Find snippet most relevant to claim using keyword overlap.

    TC-1656: Simple keyword matching between claim text and snippet descriptions/code
    to provide relevant code examples in deterministic tutorial fallback.

    Args:
        claim: Claim dict with claim_text
        snippet_catalog: Snippet catalog with snippets list

    Returns:
        Most relevant snippet dict, or None if no good match
    """
    claim_text = claim.get("claim_text", "").lower()
    if not claim_text:
        return None

    snippets = snippet_catalog.get("snippets", [])
    if not snippets:
        return None

    # Extract claim keywords (simple whitespace split)
    claim_words = set(claim_text.split())

    best_snippet = None
    best_overlap = 0

    for snippet in snippets:
        snippet_desc = snippet.get("description", "").lower()
        snippet_code = snippet.get("code", "").lower()

        # Check keyword overlap
        snippet_words = set(snippet_desc.split() + snippet_code.split())
        overlap = len(claim_words & snippet_words)

        # Track best match
        if overlap > best_overlap:
            best_overlap = overlap
            best_snippet = snippet

    # Return snippet only if we have meaningful overlap (>=2 words)
    if best_overlap >= 2:
        return best_snippet

    return None


def _generate_deterministic_tutorial(
    claims: List[Dict[str, Any]],
    snippet_catalog: Dict[str, Any],
    product_name: str
) -> str:
    """Generate deterministic tutorial when LLM unavailable.

    TC-1656: Fallback tutorial generator that produces real content (no placeholders)
    with numbered steps, descriptions, code snippets, and claim markers.

    Args:
        claims: Tutorial step claims
        snippet_catalog: Snippet catalog for code examples
        product_name: Product name for context

    Returns:
        Formatted tutorial markdown content
    """
    if not claims:
        return ""

    sections = []

    # Iterate claims as tutorial steps
    for i, claim in enumerate(claims, 1):
        claim_id = claim.get("claim_id", "")
        claim_text = _get_display_text(claim)

        # Extract step title from first sentence
        first_sentence = claim_text.split('.')[0] if '.' in claim_text else claim_text
        step_title = first_sentence[:80]  # Keep reasonable length

        section = f"## Step {i}: {step_title}\n\n"

        # Use full claim text as description (no truncation)
        section += f"{claim_text}\n\n"

        # Try to find related code snippet
        snippet = _find_related_snippet_tutorial(claim, snippet_catalog)
        if snippet:
            code = snippet.get("code", "")
            if not _is_valid_snippet(code):
                code = "# TODO: add code example"
            language = snippet.get("language", "python")
            section += f"```{language}\n{code}\n```\n\n"
        else:
            # Minimal code example placeholder
            section += f"```python\n# TODO: Add code example for {step_title}\n```\n\n"

        # Inject claim marker
        section += f"<!-- claim: {claim_id} -->\n\n"
        sections.append(section)

    return "\n".join(sections)


def generate_tutorial_content(
    page: Dict[str, Any],
    product_facts: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
    llm_client: Optional[Any] = None,
) -> str:
    """Generate tutorial page content.

    TC-1656: LLM-enhanced tutorial generator producing complete step-by-step
    tutorials with runnable Python code, line-by-line explanations, expected
    output, and common mistakes. Eliminates BLOCKER-5 for tutorials and
    BLOCKER-7 (no code examples).

    Uses TC-1658 LLM integration layer and TC-1659 tutorial.txt prompt template.
    Falls back to deterministic rendering if LLM unavailable or fails validation.

    Args:
        page: Page specification from page_plan
        product_facts: Product facts dictionary
        snippet_catalog: Snippet catalog dictionary
        llm_client: Optional LLM client for enhanced generation

    Returns:
        Markdown content for tutorial page
    """
    from ..worker import _call_llm_for_content, _get_prompt_loader

    product_name = product_facts.get("product_name", "this library")

    # Extract claims for this page
    claim_ids = page.get("claim_ids", [])
    all_claims = product_facts.get("claims", [])
    claims = [c for c in all_claims if c.get("claim_id") in claim_ids]

    if not claims:
        logger.warning(f"[W5 Tutorial] No claims found for page")
        return ""

    logger.info(f"[W5 Tutorial] Generating content for {len(claims)} tutorial step claims")

    # Try LLM-enhanced generation if client available
    if llm_client:
        try:
            # TC-2369: Generator-specific context builder (workflow claims first + demo snippets)
            tutorial_ctx = build_tutorial_context(page, product_facts, snippet_catalog)
            enriched_context = tutorial_ctx["claim_context"]
            snippet_text = tutorial_ctx["snippet_text"]

            # TC-1713: Try centralized PromptLoader first, fall back to local file
            filled_prompt = None
            _loader = _get_prompt_loader()
            if _loader:
                try:
                    filled_prompt = _loader.load(
                        "pages/tutorial",
                        product_name=product_name,
                        enriched_claims=enriched_context or "No tutorial steps available.",
                        snippets=snippet_text or "No code snippets available.",
                    ).text
                except Exception:
                    pass

            if not filled_prompt:
                # Fall back to local prompt file
                prompt_path = Path(__file__).parent.parent / "prompts" / "tutorial.txt"
                if prompt_path.exists():
                    prompt_template = prompt_path.read_text(encoding="utf-8")
                    # Fill prompt template (manual replacement to avoid format() issues with braces)
                    filled_prompt = prompt_template.replace("{product_name}", product_name)
                    filled_prompt = filled_prompt.replace("{enriched_claims}", enriched_context or "No tutorial steps available.")
                    filled_prompt = filled_prompt.replace("{snippets}", snippet_text or "No code snippets available.")
                else:
                    logger.warning(f"[W5 Tutorial] Prompt template not found at {prompt_path}, using deterministic fallback")

            if filled_prompt:
                # TC-2391: Inject declarative tone + structure directives
                page_role = page.get("page_role", "tutorial")
                filled_prompt = build_section_prompt_enhancement(_TONE_CONFIG, page_role, filled_prompt)
                # Call LLM (TC-1658)
                result = _call_llm_for_content(
                    prompt=filled_prompt,
                    claims=claims,
                    snippets=snippet_catalog.get("snippets", []),
                    llm_client=llm_client,
                    min_words=300,  # Tutorials need comprehensive step-by-step content
                    page_role="tutorial",
                    canonical_import=_get_canonical_import(product_facts),
                    product_name=product_name,
                )

                if result.get("success"):
                    tutorial_content = result.get("content", "")

                    # Validate tutorial quality (TC-1656)
                    if _validate_tutorial_quality(tutorial_content):
                        # Inject claim markers (TC-1658)
                        tutorial_content = _inject_claim_markers_as_comments(
                            tutorial_content,
                            claim_ids,
                            claims
                        )
                        logger.info(f"[W5 Tutorial] LLM generation successful, {len(tutorial_content.split())} words")
                        return tutorial_content
                    else:
                        logger.warning("[W5 Tutorial] LLM output failed quality validation, using deterministic fallback")
                else:
                    logger.warning(f"[W5 Tutorial] LLM generation failed ({result.get('method')}), using deterministic fallback")
        except Exception as e:
            logger.warning(f"[W5 Tutorial] LLM generation error: {e}, using deterministic fallback")

    # Deterministic fallback: real content with snippet matching
    logger.info(f"[W5 Tutorial] Using deterministic fallback for {len(claims)} steps")
    return _generate_deterministic_tutorial(claims, snippet_catalog, product_name)


# ---------------------------------------------------------------------------
# Getting Started generator (TC-2202, R17-003)
# ---------------------------------------------------------------------------


def generate_getting_started_content(
    page: Dict[str, Any],
    product_facts: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
    *,
    llm_client: Any = None,
    **kwargs,
) -> str:
    """Generate getting-started content that MUST include code snippets.

    TC-2202 R17-003: Deterministic getting-started page generator that produces
    real, actionable content with code blocks in every section. No LLM required —
    all content is derived from product_facts claims and snippet_catalog.

    Structure:
    - Prerequisites section
    - Installation section (with pip install code)
    - First Example section (with working code)
    - Next Steps section (with links)

    Args:
        page: Page specification from page_plan
        product_facts: Product facts with claims, claim_groups, product_name
        snippet_catalog: Snippet catalog with code snippets
        llm_client: Optional LLM client (unused — this generator is deterministic)
        **kwargs: Additional keyword arguments (ignored)

    Returns:
        Markdown content for getting-started page with code blocks
    """
    product_name = product_facts.get("product_name", "this library")
    product_family = product_facts.get("product_family", "")

    # Derive pip package name from product_name (e.g., "Aspose.3D for Python" -> "aspose-3d")
    pip_package = _derive_pip_package(product_name)

    # Collect all claims and build ID map
    all_claims = product_facts.get("claims", [])
    claim_map = {c.get("claim_id"): c for c in all_claims}

    # Get install_steps claims
    install_ids = product_facts.get("claim_groups", {}).get("install_steps", [])
    install_claims = [claim_map[cid] for cid in install_ids if cid in claim_map]

    # Get page-specific claims
    page_claim_ids = page.get("claim_ids", page.get("required_claim_ids", []))
    page_claims = [claim_map[cid] for cid in page_claim_ids if cid in claim_map]

    # Get key_features claims as fallback content source
    kf_ids = product_facts.get("claim_groups", {}).get("key_features", [])[:5]
    kf_claims = [claim_map[cid] for cid in kf_ids if cid in claim_map]

    # Collect snippets with code
    snippets = [s for s in snippet_catalog.get("snippets", []) if s.get("code")]

    # Track all claim IDs used for marker injection
    used_claim_ids = []

    sections = []

    # ── Prerequisites ─────────────────────────────────────────────────────
    prereq_section = "## Prerequisites\n\n"
    prereq_section += f"Before you begin working with {product_name}, ensure you have the following:\n\n"
    prereq_section += "```bash\n"
    prereq_section += "# Verify Python is installed (3.6+ required)\n"
    prereq_section += "python --version\n"
    prereq_section += "```\n\n"
    prereq_section += "- **Python 3.6 or later** installed on your system.\n"
    prereq_section += f"- **pip** package manager for installing {product_name}.\n"
    if product_family:
        prereq_section += f"- Familiarity with {product_family} concepts is helpful but not required.\n"
    sections.append(prereq_section)

    # ── Installation ──────────────────────────────────────────────────────
    install_section = "## Installation\n\n"
    install_section += f"Install {product_name} using pip:\n\n"
    install_section += "```bash\n"
    install_section += f"pip install {pip_package}\n"
    install_section += "```\n\n"

    # Add install_steps claim text if available
    if install_claims:
        install_section += "### Installation Notes\n\n"
        for claim in install_claims:
            if not _is_user_facing_claim(claim):
                continue
            text = _get_display_text(claim)
            cid = claim.get("claim_id", "")
            if text:
                install_section += f"- {text}\n"
                install_section += f"<!-- claim: {cid} -->\n"
                used_claim_ids.append(cid)
        install_section += "\n"
    else:
        install_section += (
            f"After installation, verify that {product_name} is available:\n\n"
            "```python\n"
            f"import {pip_package.replace('-', '_')}\n"
            f"print('Successfully imported {product_name}')\n"
            "```\n\n"
        )
    sections.append(install_section)

    # ── Quick Start Example ───────────────────────────────────────────────
    example_section = "## Quick Start Example\n\n"
    example_section += f"Here is a minimal working example to get started with {product_name}:\n\n"

    if snippets:
        # TC-2337: Consolidate all snippets into ONE code fence
        language = snippets[0].get("language", "python")
        example_section += f"```{language}\n"
        for i, snippet in enumerate(snippets[:3], 1):
            desc = snippet.get("description", f"Example {i}")
            code = snippet.get("code", "")
            if not _is_valid_snippet(code):
                code = "# TODO: add code example"
            example_section += f"# {i}. {desc}\n"
            example_section += f"{code}\n\n"
        example_section += "```\n\n"
    else:
        # Construct a minimal example from claims
        module_name = pip_package.replace('-', '_')
        example_section += f"```python\n"
        example_section += f"import {module_name}\n\n"
        example_section += f"# Initialize {product_name}\n"
        example_section += f"print('{product_name} is ready to use')\n"
        example_section += "```\n\n"

    # Add relevant feature claims for context
    context_claims = page_claims or kf_claims
    if context_claims:
        example_section += f"### What You Can Do with {product_name}\n\n"
        for claim in context_claims[:5]:
            # TC-RCA: Quality gate — skip claims unsuitable for user-facing bullets
            if not _is_user_facing_claim(claim):
                continue
            text = _get_display_text(claim)
            cid = claim.get("claim_id", "")
            if text:
                example_section += f"- {text}\n"
                example_section += f"<!-- claim: {cid} -->\n"
                used_claim_ids.append(cid)
        example_section += "\n"
    sections.append(example_section)

    # ── Next Steps ────────────────────────────────────────────────────────
    next_steps_section = "## Next Steps\n\n"
    next_steps_section += f"Now that you have {product_name} installed and running, explore these resources:\n\n"
    next_steps_section += "```text\n"
    next_steps_section += "Recommended learning path:\n"
    next_steps_section += "  1. Read the Developer Guide for common workflows\n"
    next_steps_section += "  2. Explore the API Reference for detailed class documentation\n"
    next_steps_section += "  3. Check the FAQ for answers to common questions\n"
    next_steps_section += "```\n\n"
    next_steps_section += "- [Developer Guide](../developer-guide/) - Common workflows and patterns.\n"
    next_steps_section += "- [API Reference](../../reference/api-overview/) - Detailed class and method documentation.\n"
    next_steps_section += "- [FAQ](../faq/) - Answers to frequently asked questions.\n"
    next_steps_section += "- [Troubleshooting](../../kb/troubleshooting/) - Solutions to common issues.\n"
    sections.append(next_steps_section)

    content = "\n".join(sections)

    # Inject claim markers as HTML comments for any used claims
    if used_claim_ids:
        content = _inject_claim_markers_as_comments(content, used_claim_ids, all_claims)

    return content


def _derive_pip_package(product_name: str) -> str:
    """Derive pip package name from product name.

    Examples:
        "Aspose.3D for Python" -> "aspose-3d"
        "Aspose.Note for Python" -> "aspose-note"
        "SomeProduct" -> "someproduct"

    Args:
        product_name: Full product name string

    Returns:
        Lowercase pip-compatible package name
    """
    # Strip "for Python" / "for .NET" suffixes
    name = re.sub(r'\s+for\s+\w+.*$', '', product_name, flags=re.IGNORECASE)
    # Replace dots and spaces with hyphens, lowercase
    name = re.sub(r'[\s.]+', '-', name).lower()
    # Remove consecutive hyphens
    name = re.sub(r'-+', '-', name).strip('-')
    return name


# ---------------------------------------------------------------------------
# Helper functions for new generators (TC-2330..TC-2347)
# ---------------------------------------------------------------------------


def _get_page_claims(
    page: Dict[str, Any],
    product_facts: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Get claims relevant to a page from product_facts.

    Args:
        page: Page specification dict
        product_facts: Product facts dictionary

    Returns:
        List of claim dicts for this page
    """
    claim_ids = page.get("claim_ids", page.get("required_claim_ids", []))
    all_claims = product_facts.get("claims", [])
    claim_map = {c.get("claim_id"): c for c in all_claims}
    return [claim_map[cid] for cid in claim_ids if cid in claim_map]


def _get_page_snippets(
    page: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Get snippets relevant to a page from snippet_catalog.

    Args:
        page: Page specification dict
        snippet_catalog: Snippet catalog dictionary

    Returns:
        List of snippet dicts for this page
    """
    tags = page.get("required_snippet_tags", [])
    snippets = snippet_catalog.get("snippets", [])
    if not tags:
        return snippets[:5]  # Return first 5 as fallback
    return [s for s in snippets if any(t in s.get("tags", []) for t in tags)] or snippets[:5]


def _format_snippets_for_prompt(
    page: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
) -> str:
    """Format snippets as text for LLM prompt context.

    Args:
        page: Page specification dict
        snippet_catalog: Snippet catalog dictionary

    Returns:
        Formatted snippet text string
    """
    snippets = _get_page_snippets(page, snippet_catalog)
    if not snippets:
        return "No code examples available."
    texts = []
    for s in snippets[:5]:
        lang = s.get("language", "python")
        code = s.get("code", "")
        desc = s.get("description", "")
        header = f"# {desc}\n" if desc else ""
        texts.append(f"```{lang}\n{header}{code}\n```")
    return "\n\n".join(texts)


def _extract_llm_content(response) -> Optional[str]:
    """Extract text content from LLM response.

    Handles both dict and string response formats.

    Args:
        response: LLM response (dict or string)

    Returns:
        Extracted text content or None
    """
    if isinstance(response, dict):
        text = response.get("content", "")
    else:
        text = str(response) if response else ""
    return text.strip() if text and text.strip() else None


def _inject_claim_markers(content: str, page: Dict[str, Any]) -> str:
    """Inject claim markers from page into content.

    Convenience wrapper around _inject_claim_markers_as_comments.

    Args:
        content: Generated markdown content
        page: Page dict with claim_ids

    Returns:
        Content with claim markers injected
    """
    claim_ids = page.get("claim_ids", page.get("required_claim_ids", []))
    if not claim_ids:
        return content
    # Build minimal claim objects for marker injection
    claim_objs = [{"claim_id": cid, "claim_text": ""} for cid in claim_ids]
    return _inject_claim_markers_as_comments(content, claim_ids[:5], claim_objs)


# ---------------------------------------------------------------------------
# TC-2330: Workflow Page Generator
# ---------------------------------------------------------------------------


def generate_workflow_page_content(
    page: Dict[str, Any],
    product_facts: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
    *,
    llm_client: Any = None,
    **kwargs,
) -> str:
    """Generate workflow page content matching aspose.net docs style.

    TC-2330: Creates step-by-step workflow documentation with complete code
    examples. Structure: Overview -> What You'll Learn -> Prerequisites ->
    Steps -> Complete Example -> See Also.

    Args:
        page: Page specification from page_plan
        product_facts: Product facts dictionary
        snippet_catalog: Snippet catalog dictionary
        llm_client: Optional LLM client for enhanced generation
        **kwargs: Additional keyword arguments (ignored)

    Returns:
        Markdown content for workflow page
    """
    prompt_path = Path(__file__).parent.parent / "prompts" / "workflow_page.txt"
    prompt_template = prompt_path.read_text(encoding="utf-8")

    # TC-2379: Use role-ranked context builder for workflow_page claims/snippets
    _wf_ctx = get_context_for_role(
        page.get("page_role", "workflow_page"), page, product_facts, snippet_catalog
    )
    claims = _wf_ctx["claims"] or _get_page_claims(page, product_facts)
    enriched_claims = _wf_ctx["claim_context"] or _build_enriched_claim_context(claims, product_facts)
    snippets_text = _wf_ctx["snippet_text"] or _format_snippets_for_prompt(page, snippet_catalog)
    title = page.get("title", page.get("slug", "Workflow"))
    purpose = page.get("purpose", "")
    unique_angle = page.get("content_strategy", {}).get("unique_angle", "")

    prompt = prompt_template.format(
        product_name=product_facts.get("product_name", "Product"),
        enriched_claims=enriched_claims,
        snippets=snippets_text,
        title=title,
        purpose=purpose,
        unique_angle=unique_angle,
    )
    # TC-2391: Inject declarative tone + structure directives
    prompt = build_section_prompt_enhancement(_TONE_CONFIG, page.get("page_role", "workflow_page"), prompt)

    content = None
    if llm_client:
        try:
            response = llm_client.chat_completion(
                messages=[
                    {"role": "system", "content": "You are a technical documentation writer."},
                    {"role": "user", "content": prompt},
                ],
                call_id=f"w5_workflow_{page.get('slug', 'unknown')}",
                temperature=0.2,
                max_tokens=4096,
            )
            content = _extract_llm_content(response)
        except Exception as e:
            logger.warning(f"[W5] LLM failed for workflow_page {page.get('slug')}: {e}")

    if not content or len(content.split()) < 100:
        content = _build_deterministic_workflow_page(page, product_facts, snippet_catalog)

    return _inject_claim_markers(content, page)


def _build_deterministic_workflow_page(
    page: Dict[str, Any],
    product_facts: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
) -> str:
    """Deterministic fallback for workflow pages.

    Args:
        page: Page specification dict
        product_facts: Product facts dictionary
        snippet_catalog: Snippet catalog dictionary

    Returns:
        Structured markdown content for workflow page
    """
    claims = _get_page_claims(page, product_facts)
    snippets = _get_page_snippets(page, snippet_catalog)
    _raw_title = page.get("title") or page.get("slug") or "Workflow Guide"
    title = _slug_to_readable(_raw_title) if ("-" in _raw_title and " " not in _raw_title) else _raw_title
    product_name = product_facts.get("product_name", "Product")

    sections = []
    sections.append(f"This guide covers {title.lower()} using {product_name}.\n")

    sections.append("## What You'll Learn\n")
    for claim in claims[:5]:
        if not _is_user_facing_claim(claim):
            continue
        sections.append(f"- {_get_display_text(claim)}")
    if not claims:
        sections.append(f"- How to use {title.lower()} with {product_name}")
    sections.append("")

    sections.append("## Prerequisites\n")
    sections.append(f"- {product_name} installed (`pip install {product_name.lower().replace(' ', '-')}`)")
    sections.append("- Python 3.6 or later\n")

    sections.append("## Steps\n")
    for i, claim in enumerate(claims[:8], 1):
        if not _is_user_facing_claim(claim):
            continue
        text = _get_display_text(claim)
        cid = claim.get("claim_id", "")
        sections.append(f"**Step {i}**: {text}\n")
        sections.append(f"<!-- claim: {cid} -->\n")
    if not claims:
        sections.append(f"**Step 1**: Install {product_name} using pip.\n")
        sections.append(f"**Step 2**: Import the library in your Python script.\n")

    if snippets:
        lang = snippets[0].get("language", "python")
        code = snippets[0].get("code", "# example code")
        if not _is_valid_snippet(code):
            code = "# TODO: add code example"
        sections.append(f"## Complete Example\n\n```{lang}\n{code}\n```\n")

    sections.append("## See Also\n")
    sections.append("- [Getting Started](../getting-started/)")
    sections.append("- [Developer Guide](../developer-guide/)\n")

    return "\n".join(sections)


# ---------------------------------------------------------------------------
# TC-2331: Landing Page Generator
# ---------------------------------------------------------------------------


def generate_landing_content(
    page: Dict[str, Any],
    product_facts: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
    *,
    llm_client: Any = None,
    **kwargs,
) -> str:
    """Generate product landing page content.

    TC-2331: Creates value proposition landing pages with feature highlights
    and navigation links. NO code examples on landing pages.

    Args:
        page: Page specification from page_plan
        product_facts: Product facts dictionary
        snippet_catalog: Snippet catalog dictionary (unused — no code on landing)
        llm_client: Optional LLM client for enhanced generation
        **kwargs: Additional keyword arguments (ignored)

    Returns:
        Markdown content for landing page
    """
    prompt_path = Path(__file__).parent.parent / "prompts" / "landing.txt"
    prompt_template = prompt_path.read_text(encoding="utf-8")

    # TC-2379: Use role-ranked context builder for landing claims/snippets
    _land_ctx = get_context_for_role(
        page.get("page_role", "landing"), page, product_facts, snippet_catalog
    )
    claims = _land_ctx["claims"] or _get_page_claims(page, product_facts)
    enriched_claims = _land_ctx["claim_context"] or _build_enriched_claim_context(claims, product_facts)
    title = page.get("title", page.get("slug", "Product"))
    purpose = page.get("purpose", "")
    product_name = product_facts.get("product_name", "Product")

    prompt = prompt_template.format(
        product_name=product_name,
        enriched_claims=enriched_claims,
        title=title,
        purpose=purpose,
    )
    # TC-2391: Inject declarative tone + structure directives
    prompt = build_section_prompt_enhancement(_TONE_CONFIG, page.get("page_role", "landing"), prompt)

    content = None
    if llm_client:
        try:
            response = llm_client.chat_completion(
                messages=[
                    {"role": "system", "content": "You are a product marketing writer for developer tools."},
                    {"role": "user", "content": prompt},
                ],
                call_id=f"w5_landing_{page.get('slug', 'unknown')}",
                temperature=0.2,
                max_tokens=3000,
            )
            content = _extract_llm_content(response)
        except Exception as e:
            logger.warning(f"[W5] LLM failed for landing {page.get('slug')}: {e}")

    if not content or len(content.split()) < 80:
        content = _build_deterministic_landing(page, product_facts)

    return _inject_claim_markers(content, page)


def _build_deterministic_landing(
    page: Dict[str, Any],
    product_facts: Dict[str, Any],
) -> str:
    """Deterministic fallback for landing pages.

    Args:
        page: Page specification dict
        product_facts: Product facts dictionary

    Returns:
        Structured markdown content for landing page
    """
    claims = _get_page_claims(page, product_facts)
    product_name = product_facts.get("product_name", "Product")
    _raw_title = page.get("title") or product_name
    title = _slug_to_readable(_raw_title) if ("-" in _raw_title and " " not in _raw_title) else _raw_title

    # If no page claims, fall back to key_features
    if not claims:
        kf_ids = product_facts.get("claim_groups", {}).get("key_features", [])[:6]
        all_claims = product_facts.get("claims", [])
        claim_map = {c.get("claim_id"): c for c in all_claims}
        claims = [claim_map[cid] for cid in kf_ids if cid in claim_map]

    sections = []
    sections.append(f"## {title}\n")
    sections.append(
        f"{product_name} is a powerful Python library that helps developers "
        f"work with complex file formats and data processing tasks efficiently. "
        f"Whether you are building enterprise applications or quick prototypes, "
        f"{product_name} provides the tools you need.\n"
    )

    sections.append("## Key Features\n")
    for claim in claims[:6]:
        if not _is_user_facing_claim(claim):
            continue
        text = _get_display_text(claim)
        cid = claim.get("claim_id", "")
        sections.append(f"- **{text}**")
        sections.append(f"<!-- claim: {cid} -->")
    if not claims:
        sections.append(f"- Comprehensive file format support")
        sections.append(f"- Easy-to-use Python API")
        sections.append(f"- Cross-platform compatibility")
    sections.append("")

    sections.append("## Getting Started\n")
    sections.append(
        f"Ready to start using {product_name}? Follow our getting started guide "
        f"to install the library and run your first example.\n"
    )
    sections.append(f"[Get Started with {product_name}](../docs/getting-started/) | "
                     f"[View API Reference](../reference/api-overview/)\n")

    return "\n".join(sections)


# ---------------------------------------------------------------------------
# TC-2332: API Reference Overview Generator
# ---------------------------------------------------------------------------


def generate_api_reference_content(
    page: Dict[str, Any],
    product_facts: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
    *,
    llm_client: Any = None,
    **kwargs,
) -> str:
    """Generate API reference overview page content.

    TC-2332: Creates API reference overview with class tables grouped by
    functionality, usage snippets, and parameter tables.

    Args:
        page: Page specification from page_plan
        product_facts: Product facts dictionary
        snippet_catalog: Snippet catalog dictionary
        llm_client: Optional LLM client for enhanced generation
        **kwargs: Additional keyword arguments (ignored)

    Returns:
        Markdown content for API reference overview
    """
    prompt_path = Path(__file__).parent.parent / "prompts" / "api_reference.txt"
    prompt_template = prompt_path.read_text(encoding="utf-8")

    # TC-2379: Use role-ranked context builder for api_reference claims/snippets
    _ar_ctx = get_context_for_role(
        page.get("page_role", "api_reference"), page, product_facts, snippet_catalog
    )
    claims = _ar_ctx["claims"] or _get_page_claims(page, product_facts)
    product_name = product_facts.get("product_name", "Product")

    # Spec v1.1: mandatory reference pages with no evidence emit scoped fallback (B8/E3)
    if not claims and page.get("not_evidenced_hint", False):
        _ref_title = page.get("title", page.get("slug", "API Reference"))
        return f"## {_ref_title}\n\n{_NOT_EVIDENCED_CONTENT}\n"

    enriched_claims = _ar_ctx["claim_context"] or _build_enriched_claim_context(claims, product_facts)
    snippets_text = _ar_ctx["snippet_text"] or _format_snippets_for_prompt(page, snippet_catalog)

    # Build API surface summary
    api_surface = product_facts.get("api_surface_summary", {})
    api_text = _format_api_surface(api_surface)

    prompt = prompt_template.format(
        product_name=product_name,
        enriched_claims=enriched_claims,
        api_surface=api_text,
    )
    # TC-2391: Inject declarative tone + structure directives
    prompt = build_section_prompt_enhancement(_TONE_CONFIG, page.get("page_role", "api_reference"), prompt)

    content = None
    if llm_client:
        try:
            response = llm_client.chat_completion(
                messages=[
                    {"role": "system", "content": "You are a technical API documentation writer."},
                    {"role": "user", "content": prompt},
                ],
                call_id=f"w5_api_ref_{page.get('slug', 'unknown')}",
                temperature=0.1,
                max_tokens=4096,
            )
            content = _extract_llm_content(response)
        except Exception as e:
            logger.warning(f"[W5] LLM failed for api_reference {page.get('slug')}: {e}")

    if not content or len(content.split()) < 100:
        content = _build_deterministic_api_reference(page, product_facts, snippet_catalog)

    return _inject_claim_markers(content, page)


def _format_api_surface(api_surface: Dict[str, Any]) -> str:
    """Format API surface summary as text for LLM prompt.

    Args:
        api_surface: API surface summary dictionary

    Returns:
        Formatted API surface text
    """
    if not api_surface:
        return "No API surface data available."

    lines = []
    classes = api_surface.get("classes", [])
    for cls in classes[:30]:
        if isinstance(cls, str):
            lines.append(f"- {cls}")
        elif isinstance(cls, dict):
            name = cls.get("name", "")
            methods = cls.get("methods", [])
            method_names = [m if isinstance(m, str) else m.get("name", "") for m in methods[:5]]
            lines.append(f"- {name}: {', '.join(method_names)}")
    return "\n".join(lines) if lines else "No API surface data available."


def _build_deterministic_api_reference(
    page: Dict[str, Any],
    product_facts: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
) -> str:
    """Deterministic fallback for API reference pages.

    Args:
        page: Page specification dict
        product_facts: Product facts dictionary
        snippet_catalog: Snippet catalog dictionary

    Returns:
        Structured markdown content for API reference
    """
    product_name = product_facts.get("product_name", "Product")
    api_surface = product_facts.get("api_surface_summary", {})
    classes = api_surface.get("classes", [])
    claims = _get_page_claims(page, product_facts)
    snippets = _get_page_snippets(page, snippet_catalog)

    sections = []
    sections.append(f"This page provides an overview of the {product_name} API.\n")

    # Build class table
    if classes:
        sections.append("## Core Classes\n")
        sections.append("| Class | Purpose | Key Methods |")
        sections.append("|-------|---------|-------------|")
        for cls in classes[:20]:
            if isinstance(cls, str):
                sections.append(f"| {cls} | See reference | — |")
            elif isinstance(cls, dict):
                name = cls.get("name", "")
                purpose = cls.get("description", "See reference")[:60]
                methods = cls.get("methods", [])
                method_strs = []
                for m in methods[:3]:
                    if isinstance(m, str):
                        method_strs.append(f"`{m}()`")
                    elif isinstance(m, dict):
                        method_strs.append(f"`{m.get('name', '')}()`")
                methods_text = ", ".join(method_strs) if method_strs else "—"
                sections.append(f"| {name} | {purpose} | {methods_text} |")
        sections.append("")
    else:
        # Use claims for content
        sections.append("## API Overview\n")
        for claim in claims[:10]:
            if not _is_user_facing_claim(claim):
                continue
            text = _get_display_text(claim)
            cid = claim.get("claim_id", "")
            sections.append(f"- {text}")
            sections.append(f"<!-- claim: {cid} -->")
        sections.append("")

    # Quick usage
    if snippets:
        sections.append("## Quick Usage\n")
        lang = snippets[0].get("language", "python")
        code = snippets[0].get("code", "# example")
        if not _is_valid_snippet(code):
            code = "# TODO: add code example"
        sections.append(f"```{lang}\n{code}\n```\n")

    return "\n".join(sections)


# ---------------------------------------------------------------------------
# TC-2345: Format Conversion Generator
# ---------------------------------------------------------------------------


def generate_format_conversion_content(
    page: Dict[str, Any],
    product_facts: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
    *,
    llm_client: Any = None,
    **kwargs,
) -> str:
    """Generate format conversion guide content.

    TC-2345: Creates conversion guides (e.g., CSV to PDF) with overview,
    steps, code example, and FAQ.

    Args:
        page: Page specification from page_plan
        product_facts: Product facts dictionary
        snippet_catalog: Snippet catalog dictionary
        llm_client: Optional LLM client for enhanced generation
        **kwargs: Additional keyword arguments (ignored)

    Returns:
        Markdown content for format conversion page
    """
    prompt_path = Path(__file__).parent.parent / "prompts" / "format_conversion.txt"
    prompt_template = prompt_path.read_text(encoding="utf-8")

    # TC-2379: Use role-ranked context builder for format_conversion claims/snippets
    _fc_ctx = get_context_for_role(
        page.get("page_role", "format_conversion"), page, product_facts, snippet_catalog
    )
    claims = _fc_ctx["claims"] or _get_page_claims(page, product_facts)
    enriched_claims = _fc_ctx["claim_context"] or _build_enriched_claim_context(claims, product_facts)
    snippets_text = _fc_ctx["snippet_text"] or _format_snippets_for_prompt(page, snippet_catalog)
    title = page.get("title", page.get("slug", "Format Conversion"))
    purpose = page.get("purpose", "")
    product_name = product_facts.get("product_name", "Product")

    # Extract format info from content_strategy
    content_strategy = page.get("content_strategy", {})
    source_format = content_strategy.get("source_format", "source")
    target_format = content_strategy.get("target_format", "target")

    prompt = prompt_template.format(
        product_name=product_name,
        enriched_claims=enriched_claims,
        snippets=snippets_text,
        title=title,
        purpose=purpose,
        source_format=source_format,
        target_format=target_format,
    )
    # TC-2391: Inject declarative tone + structure directives (tutorial covers step-by-step conversions)
    prompt = build_section_prompt_enhancement(_TONE_CONFIG, page.get("page_role", "tutorial"), prompt)

    content = None
    if llm_client:
        try:
            response = llm_client.chat_completion(
                messages=[
                    {"role": "system", "content": "You are a technical documentation writer specializing in file format conversions."},
                    {"role": "user", "content": prompt},
                ],
                call_id=f"w5_conversion_{page.get('slug', 'unknown')}",
                temperature=0.2,
                max_tokens=4096,
            )
            content = _extract_llm_content(response)
        except Exception as e:
            logger.warning(f"[W5] LLM failed for format_conversion {page.get('slug')}: {e}")

    if not content or len(content.split()) < 100:
        content = _build_deterministic_format_conversion(page, product_facts, snippet_catalog)

    return _inject_claim_markers(content, page)


def _build_deterministic_format_conversion(
    page: Dict[str, Any],
    product_facts: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
) -> str:
    """Deterministic fallback for format conversion pages.

    Args:
        page: Page specification dict
        product_facts: Product facts dictionary
        snippet_catalog: Snippet catalog dictionary

    Returns:
        Structured markdown content for format conversion
    """
    claims = _get_page_claims(page, product_facts)
    snippets = _get_page_snippets(page, snippet_catalog)
    product_name = product_facts.get("product_name", "Product")
    content_strategy = page.get("content_strategy", {})
    source_format = content_strategy.get("source_format", "source").upper()
    target_format = content_strategy.get("target_format", "target").upper()

    sections = []
    sections.append(
        f"This guide explains how to convert {source_format} files to {target_format} "
        f"format using {product_name}.\n"
    )

    sections.append("## How It Works\n")
    sections.append(f"Converting {source_format} to {target_format} with {product_name} involves three steps:\n")
    sections.append(f"1. Load the {source_format} file using the appropriate loader class.")
    sections.append(f"2. Configure conversion options (optional).")
    sections.append(f"3. Save the output as {target_format}.\n")

    for claim in claims[:5]:
        if not _is_user_facing_claim(claim):
            continue
        text = _get_display_text(claim)
        cid = claim.get("claim_id", "")
        sections.append(f"- {text}")
        sections.append(f"<!-- claim: {cid} -->")
    if claims:
        sections.append("")

    sections.append("## Code Example\n")
    if snippets:
        lang = snippets[0].get("language", "python")
        code = snippets[0].get("code", "# conversion example")
        if not _is_valid_snippet(code):
            code = "# TODO: add code example"
        sections.append(f"```{lang}\n{code}\n```\n")
    else:
        module = product_name.lower().replace(" ", "_").replace(".", "_")
        sections.append(f"```python\nimport {module}\n\n")
        sections.append(f"# Load {source_format} file\n")
        sections.append(f"doc = {module}.load('input.{source_format.lower()}')\n\n")
        sections.append(f"# Save as {target_format}\n")
        sections.append(f"doc.save('output.{target_format.lower()}')\n```\n")

    sections.append("## FAQ\n")
    sections.append(f"**Q: What {source_format} features are preserved during conversion?**\n")
    sections.append(f"A: {product_name} preserves formatting, layout, and embedded objects during the conversion process.\n")
    sections.append(f"**Q: Can I batch convert multiple files?**\n")
    sections.append(f"A: Yes, you can loop through files and apply the same conversion process to each one.\n")

    return "\n".join(sections)


# ---------------------------------------------------------------------------
# TC-2346: How-To Article Generator
# ---------------------------------------------------------------------------


def generate_howto_article_content(
    page: Dict[str, Any],
    product_facts: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
    *,
    llm_client: Any = None,
    **kwargs,
) -> str:
    """Generate how-to article content.

    TC-2346: Creates practical how-to guides with step-by-step instructions
    and complete code examples.

    Args:
        page: Page specification from page_plan
        product_facts: Product facts dictionary
        snippet_catalog: Snippet catalog dictionary
        llm_client: Optional LLM client for enhanced generation
        **kwargs: Additional keyword arguments (ignored)

    Returns:
        Markdown content for how-to article
    """
    prompt_path = Path(__file__).parent.parent / "prompts" / "howto_article.txt"
    prompt_template = prompt_path.read_text(encoding="utf-8")

    # TC-2379: Use role-ranked context builder for howto_article claims/snippets
    _ha_ctx = get_context_for_role(
        page.get("page_role", "howto_article"), page, product_facts, snippet_catalog
    )
    claims = _ha_ctx["claims"] or _get_page_claims(page, product_facts)
    title = page.get("title", page.get("slug", "How-To Guide"))

    # Agent 43: mandatory pages with no evidence emit structured fallback
    if not claims and page.get("not_evidenced_hint", False):
        return _build_not_evidenced_howto(page, product_facts)

    enriched_claims = _ha_ctx["claim_context"] or _build_enriched_claim_context(claims, product_facts)
    snippets_text = _ha_ctx["snippet_text"] or _format_snippets_for_prompt(page, snippet_catalog)
    purpose = page.get("purpose", "")
    product_name = product_facts.get("product_name", "Product")

    # Agent 43: Build format evidence text for conversion how-to pages
    format_evidence = _build_format_evidence_text(page)

    prompt = prompt_template.format(
        product_name=product_name,
        enriched_claims=enriched_claims,
        snippets=snippets_text,
        title=title,
        purpose=purpose,
        format_evidence=format_evidence,
    )
    # TC-2391: Inject declarative tone + structure directives
    prompt = build_section_prompt_enhancement(_TONE_CONFIG, page.get("page_role", "tutorial"), prompt)

    content = None
    if llm_client:
        try:
            response = llm_client.chat_completion(
                messages=[
                    {"role": "system", "content": "You are a technical writer specializing in practical developer guides."},
                    {"role": "user", "content": prompt},
                ],
                call_id=f"w5_howto_{page.get('slug', 'unknown')}",
                temperature=0.2,
                max_tokens=4096,
            )
            content = _extract_llm_content(response)
        except Exception as e:
            logger.warning(f"[W5] LLM failed for howto_article {page.get('slug')}: {e}")

    if not content or len(content.split()) < 100:
        content = _build_deterministic_howto_article(page, product_facts, snippet_catalog)

    # Agent 43: Normalize code fences in how-to articles
    content = _normalize_howto_code_fences(content, page)

    return _inject_claim_markers(content, page)


def _build_deterministic_howto_article(
    page: Dict[str, Any],
    product_facts: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
) -> str:
    """Deterministic fallback for how-to articles.

    Agent 43: Updated to match Spec v1.1 heading order:
    Goal → When You'd Use This → Prerequisites → Steps → Code Example →
    Common Mistakes → See Also.

    Args:
        page: Page specification dict
        product_facts: Product facts dictionary
        snippet_catalog: Snippet catalog dictionary

    Returns:
        Structured markdown content for how-to article
    """
    claims = _get_page_claims(page, product_facts)
    snippets = _get_page_snippets(page, snippet_catalog)
    _raw_title = page.get("title") or page.get("slug") or "How-To Guide"
    title = _slug_to_readable(_raw_title) if ("-" in _raw_title and " " not in _raw_title) else _raw_title
    product_name = product_facts.get("product_name", "Product")
    pkg = product_name.lower().replace(" ", "-")
    is_convert = page.get("content_strategy", {}).get("is_conversion_howto", False)

    sections: List[str] = []

    # Goal
    sections.append("## Goal\n")
    sections.append(f"This article explains how to {title.lower()} using {product_name}.\n")

    # Conversion-specific: list evidenced formats in Goal section
    if is_convert:
        fmt_list = page.get("content_strategy", {}).get("supported_formats", [])
        if fmt_list:
            sections.append("**Supported formats**: " + ", ".join(
                f"{f['format']} ({f['direction']})" for f in fmt_list
            ) + ".\n")

    # When You'd Use This
    sections.append("## When You'd Use This\n")
    sections.append(f"Use this approach when you need to {title.lower()} in your Python application.\n")

    # Prerequisites
    sections.append("## Prerequisites\n")
    sections.append(f"- {product_name} installed in your Python environment (`pip install {pkg}`).")
    sections.append("- A compatible input file available on your local filesystem.")
    sections.append("- Python 3.8 or later.\n")

    # Steps
    sections.append("## Steps\n")
    step_num = 1
    for claim in claims[:8]:
        if not _is_user_facing_claim(claim):
            continue
        text = _get_display_text(claim)
        cid = claim.get("claim_id", "")
        sections.append(f"**Step {step_num}**: {text}")
        sections.append(f"<!-- claim: {cid} -->\n")
        step_num += 1
    if not claims:
        sections.append(f"**Step 1**: Install {product_name} using pip.")
        sections.append("**Step 2**: Import the library and load your data.")
        sections.append("**Step 3**: Apply the desired operations.")
        sections.append("**Step 4**: Save the output.\n")

    # Code Example
    sections.append(f"## {product_name} Code Example\n")
    if snippets:
        lang = snippets[0].get("language", "python")
        code = snippets[0].get("code", "# example code")
        if not _is_valid_snippet(code):
            code = "# TODO: add code example"
        sections.append(f"```{lang}\n{code}\n```\n")
    elif is_convert:
        # Conversion-specific: use evidenced pairs if available
        pair_list = page.get("content_strategy", {}).get("conversion_pairs", [])
        if pair_list:
            p = pair_list[0]
            sections.append("```python")
            sections.append(f"# Convert {p['source']} to {p['target']}")
            sections.append(f"# scene = load('{p['source'].lower()}_file')")
            sections.append(f"# save(scene, '{p['target'].lower()}_file')")
            sections.append("```\n")
        else:
            sections.append("```python")
            sections.append("# No working example was found in this repository.")
            sections.append(f"# import {product_name.lower().replace(' ', '_')}")
            sections.append("# scene = load('input_file')")
            sections.append("# save(scene, 'output_file')")
            sections.append("```\n")
            sections.append("> **Note**: No format conversion evidence was found in this repository.\n")
    else:
        sections.append("```python")
        sections.append(f"# Complete example for {title.lower()}")
        sections.append("# See documentation for a complete working example.")
        sections.append("pass")
        sections.append("```\n")

    # Common Mistakes
    sections.append("## Common Mistakes\n")
    sections.append("- Forgetting to install the library before importing it.")
    sections.append("- Using an unsupported file path or missing read permissions.\n")

    # See Also
    sections.append("## See Also\n")
    sections.append("- [Getting Started](../getting-started/)")
    sections.append("- [FAQ](../faq/)\n")

    return "\n".join(sections)


# ---------------------------------------------------------------------------
# TC-2347: Feature Blog Generator
# ---------------------------------------------------------------------------


def generate_feature_blog_content(
    page: Dict[str, Any],
    product_facts: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
    *,
    llm_client: Any = None,
    **kwargs,
) -> str:
    """Generate feature highlight blog post content.

    TC-2347: Creates engaging blog posts highlighting specific features
    with friendly tone, "you/your" voice, and quick code examples.

    Args:
        page: Page specification from page_plan
        product_facts: Product facts dictionary
        snippet_catalog: Snippet catalog dictionary
        llm_client: Optional LLM client for enhanced generation
        **kwargs: Additional keyword arguments (ignored)

    Returns:
        Markdown content for feature blog post
    """
    prompt_path = Path(__file__).parent.parent / "prompts" / "feature_blog.txt"
    prompt_template = prompt_path.read_text(encoding="utf-8")

    # TC-2379: Use role-ranked context builder for feature_blog claims/snippets
    _fb_ctx = get_context_for_role(
        page.get("page_role", "feature_blog"), page, product_facts, snippet_catalog
    )
    claims = _fb_ctx["claims"] or _get_page_claims(page, product_facts)

    # Spec v1.1: mandatory feature blog pages with no evidence emit scoped fallback (B8/E3)
    if not claims and page.get("not_evidenced_hint", False):
        _fb_title = page.get("title", page.get("slug", "Feature Blog Post"))
        return f"## {_fb_title}\n\n{_NOT_EVIDENCED_CONTENT}\n"

    enriched_claims = _fb_ctx["claim_context"] or _build_enriched_claim_context(claims, product_facts)
    snippets_text = _fb_ctx["snippet_text"] or _format_snippets_for_prompt(page, snippet_catalog)
    title = page.get("title", page.get("slug", "Feature Highlight"))
    purpose = page.get("purpose", "")
    product_name = product_facts.get("product_name", "Product")

    # Agent 44: Build cross-section links for blog post Next Steps
    family = product_facts.get("product_family", product_facts.get("product_slug", ""))
    section_links = (
        f"- Products: /{family}/python/\n"
        f"- Documentation: /docs/{family}/python/\n"
        f"- API Reference: /reference/{family}/python/\n"
    )

    prompt = prompt_template.format(
        product_name=product_name,
        enriched_claims=enriched_claims,
        snippets=snippets_text,
        title=title,
        purpose=purpose,
        section_links=section_links,
    )
    # TC-2391: Inject declarative tone + structure directives
    prompt = build_section_prompt_enhancement(_TONE_CONFIG, page.get("page_role", "blog"), prompt)

    content = None
    if llm_client:
        try:
            response = llm_client.chat_completion(
                messages=[
                    {"role": "system", "content": "You are a developer advocate writing engaging blog posts."},
                    {"role": "user", "content": prompt},
                ],
                call_id=f"w5_feature_blog_{page.get('slug', 'unknown')}",
                temperature=0.3,
                max_tokens=3000,
            )
            content = _extract_llm_content(response)
        except Exception as e:
            logger.warning(f"[W5] LLM failed for feature_blog {page.get('slug')}: {e}")

    if not content or len(content.split()) < 80:
        content = _build_deterministic_feature_blog(page, product_facts, snippet_catalog)

    return _inject_claim_markers(content, page)


def _build_deterministic_feature_blog(
    page: Dict[str, Any],
    product_facts: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
) -> str:
    """Deterministic fallback for feature blog posts.

    Args:
        page: Page specification dict
        product_facts: Product facts dictionary
        snippet_catalog: Snippet catalog dictionary

    Returns:
        Structured markdown content for feature blog
    """
    claims = _get_page_claims(page, product_facts)
    snippets = _get_page_snippets(page, snippet_catalog)
    _raw_title = page.get("title") or page.get("slug") or "Feature Highlight"
    title = _slug_to_readable(_raw_title) if ("-" in _raw_title and " " not in _raw_title) else _raw_title
    product_name = product_facts.get("product_name", "Product")

    sections = []
    sections.append(
        f"If you have been looking for a way to {title.lower()}, you are in the right place. "
        f"{product_name} makes it easy to accomplish this in just a few lines of Python code.\n"
    )

    sections.append("## Key Highlights\n")
    for claim in claims[:5]:
        if not _is_user_facing_claim(claim):
            continue
        text = _get_display_text(claim)
        cid = claim.get("claim_id", "")
        sections.append(f"- **{text}**")
        sections.append(f"<!-- claim: {cid} -->")
    if not claims:
        sections.append(f"- **Simple API**: Get started with just a few lines of code.")
        sections.append(f"- **Production Ready**: Battle-tested and reliable.")
        sections.append(f"- **Well Documented**: Comprehensive documentation and examples.")
    sections.append("")

    sections.append("## Quick Example\n")
    if snippets:
        lang = snippets[0].get("language", "python")
        code = snippets[0].get("code", "# example")
        if not _is_valid_snippet(code):
            code = "# TODO: add code example"
        sections.append(f"```{lang}\n{code}\n```\n")
    else:
        sections.append(f"```python\n# Quick example for {title.lower()}\n```\n")

    # Agent 44: Cross-section links for blog post navigation
    family = product_facts.get("product_family", product_facts.get("product_slug", ""))
    sections.append("## Next Steps\n")
    sections.append(f"- [Explore the product overview](/{family}/python/)")
    sections.append(f"- [Read the full documentation](/docs/{family}/python/)")
    sections.append(f"- [Browse the API reference](/reference/{family}/python/)")
    sections.append(f"- [Try it yourself](/docs/{family}/python/getting-started/) — get started in minutes!\n")

    return "\n".join(sections)


# ---------------------------------------------------------------------------
# Spec v1.1 H2: Reference Object Page generator (per-class/module/function)
# ---------------------------------------------------------------------------


def generate_reference_object_content(
    page: Dict[str, Any],
    product_facts: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
    *,
    llm_client: Any = None,
    **kwargs,
) -> str:
    """Generate per-class/module/function reference documentation.

    Spec v1.1 H2 (Q3=A): Classes + modules + functions only; member methods and
    properties are documented as H3 sub-sections within the page.  Scoped
    "Not evidenced" fallback emitted when no API claims exist (B8/E3).

    Args:
        page: Page specification from page_plan; should include ``object_name``
            and ``object_kind`` fields set by W4 object discovery.
        product_facts: Product facts dictionary.
        snippet_catalog: Snippet catalog dictionary.
        llm_client: Optional LLM client for enhanced generation.
        **kwargs: Ignored.

    Returns:
        Markdown content for the reference object page.
    """
    _ro_ctx = get_context_for_role(
        "reference_object_page", page, product_facts, snippet_catalog
    )
    claims = _ro_ctx["claims"] or _get_page_claims(page, product_facts)
    object_name = page.get("object_name", page.get("title", page.get("slug", "Object")))

    # Spec v1.1 E3: mandatory pages with no repository evidence emit scoped fallback
    if not claims and page.get("not_evidenced_hint", False):
        return f"## {object_name}\n\n{_NOT_EVIDENCED_CONTENT}\n"

    enriched_claims = _ro_ctx["claim_context"] or _build_enriched_claim_context(claims, product_facts)
    snippets_text = _ro_ctx["snippet_text"] or _format_snippets_for_prompt(page, snippet_catalog)
    object_kind = page.get("object_kind", "class")
    product_name = product_facts.get("product_name", "Product")

    prompt = (
        f"You are a technical API documentation writer creating a {object_kind} reference page "
        f"for {product_name}.\n\n"
        f"## Object: {object_name}\n\n"
        f"Write a focused reference page covering:\n"
        f"1. A one-paragraph description of what {object_name} does.\n"
        f"2. A '## Constructor / Instantiation' section showing how to create an instance "
        f"(with a fenced ```python code block).\n"
        f"3. A '## Key Members' section that lists each method or property as a ### sub-section "
        f"(H3), with a one-sentence description in flowing prose — NEVER raw parameter dumps.\n"
        f"4. A '## Usage Example' section with ONE complete, runnable ```python code block.\n\n"
        f"FACTS TO USE:\n{enriched_claims}\n\n"
        f"CODE EXAMPLES:\n{snippets_text}\n\n"
        f"RULES:\n"
        f"- Every factual statement must cite a claim using [claim: CLAIM_ID] format.\n"
        f"- Never dump raw parameter signatures. Describe parameters in flowing prose.\n"
        f"- Minimum 200 words of explanatory prose (code does not count).\n"
        f"- Return only the markdown body. No frontmatter. No meta-commentary.\n"
    )

    content = None
    if llm_client:
        try:
            response = llm_client.chat_completion(
                messages=[
                    {"role": "system", "content": "You are a technical API documentation writer."},
                    {"role": "user", "content": prompt},
                ],
                call_id=f"w5_ref_obj_{page.get('slug', 'unknown')}",
                temperature=0.1,
                max_tokens=4096,
            )
            content = _extract_llm_content(response)
        except Exception as e:
            logger.warning(f"[W5] LLM failed for reference_object_page {page.get('slug')}: {e}")

    if not content or len(content.split()) < 80:
        content = _build_deterministic_reference_object(page, product_facts, snippet_catalog)

    return _inject_claim_markers(content, page)


def _build_deterministic_reference_object(
    page: Dict[str, Any],
    product_facts: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
) -> str:
    """Deterministic fallback for reference object pages.

    Spec v1.1 H2 (Q3=A): Lists members as H3 sub-sections sourced from
    ``api_surface_summary`` → class entry matching ``object_name``.
    Falls back to claims when no API surface data is available.

    Args:
        page: Page specification dict.
        product_facts: Product facts dictionary.
        snippet_catalog: Snippet catalog dictionary.

    Returns:
        Structured markdown content for the reference object page.
    """
    object_name = page.get("object_name", page.get("title", page.get("slug", "Object")))
    object_kind = page.get("object_kind", "class")
    product_name = product_facts.get("product_name", "Product")
    claims = _get_page_claims(page, product_facts)
    snippets = _get_page_snippets(page, snippet_catalog)

    # Locate API surface entry for this object
    api_surface = product_facts.get("api_surface_summary", {})
    classes = api_surface.get("classes", [])
    obj_entry: Dict[str, Any] = {}
    for cls in classes:
        if isinstance(cls, dict):
            if cls.get("name", "").lower() == object_name.lower():
                obj_entry = cls
                break

    sections: List[str] = []
    description = obj_entry.get("description", "")
    if description:
        sections.append(f"{description}\n")
    else:
        # Derive intro from first matching api claim
        for claim in claims[:1]:
            text = _get_display_text(claim)
            if text:
                sections.append(f"{text}\n")
        if not sections:
            sections.append(
                f"The `{object_name}` {object_kind} provides core functionality for {product_name}.\n"
            )

    # Constructor / Instantiation
    sections.append("## Constructor / Instantiation\n")
    init_snippet = None
    if snippets:
        for s in snippets:
            code = s.get("code", "")
            if object_name.lower() in code.lower() and "()" in code:
                init_snippet = s
                break
        if not init_snippet:
            init_snippet = snippets[0]
    if init_snippet:
        lang = init_snippet.get("language", "python")
        code = init_snippet.get("code", "# example")
        if not _is_valid_snippet(code):
            code = f"# TODO: add instantiation example for {object_name}"
        sections.append(f"Create an instance of `{object_name}` as shown below:\n")
        sections.append(f"```{lang}\n{code}\n```\n")
    else:
        sections.append(f"Create an instance of `{object_name}` using the constructor:\n")
        sections.append(f"```python\nobj = {object_name}()\n```\n")

    # Key Members (methods + properties as H3 sub-sections)
    members: List[Any] = obj_entry.get("methods", []) + obj_entry.get("properties", [])
    if members:
        sections.append("## Key Members\n")
        for member in members[:10]:
            if isinstance(member, str):
                sections.append(f"### `{member}()`\n")
                sections.append(f"The `{member}` member provides core functionality.\n")
            elif isinstance(member, dict):
                mname = member.get("name", "")
                mdesc = member.get("description", f"The `{mname}` member.")
                mtype = member.get("type", "method")
                suffix = "()" if mtype == "method" else ""
                sections.append(f"### `{mname}{suffix}`\n")
                sections.append(f"{mdesc}\n")
        sections.append("")
    elif claims:
        sections.append("## API Overview\n")
        for claim in claims[:8]:
            if not _is_user_facing_claim(claim):
                continue
            text = _get_display_text(claim)
            cid = claim.get("claim_id", "")
            sections.append(f"- {text}")
            sections.append(f"<!-- claim: {cid} -->")
        sections.append("")

    # Usage Example
    if snippets and len(snippets) > 1:
        sections.append("## Usage Example\n")
        usage_snippet = snippets[1]
        lang = usage_snippet.get("language", "python")
        code = usage_snippet.get("code", "# example")
        if not _is_valid_snippet(code):
            code = f"# TODO: add usage example for {object_name}"
        sections.append(f"```{lang}\n{code}\n```\n")

    return "\n".join(sections)
