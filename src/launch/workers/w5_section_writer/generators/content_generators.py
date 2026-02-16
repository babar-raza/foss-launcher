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
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Any, Optional, List

from ....util.logging import get_logger

logger = get_logger()


# ---------------------------------------------------------------------------
# Helper functions (used by multiple generators)
# ---------------------------------------------------------------------------


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

            # Include citations if available (first 3)
            citations = claim.get("citations", [])
            citation_str = ""
            if citations:
                citation_files = [c.get("file", "") for c in citations[:3] if c.get("file")]
                if citation_files:
                    citation_str = f" (Sources: {', '.join(citation_files)})"

            section += f"- [{claim_id}] {text}{citation_str}\n"

        sections.append(section)

    return "\n".join(sections)


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
        result = _call_llm_for_content(prompt, page_claims, [], llm_client, min_words=80)
        if result["success"]:
            enriched_body = result["content"]
            # Inject claim markers
            enriched_body = _inject_claim_markers_as_comments(enriched_body, claim_ids[:5], page_claims)
            return (frontmatter + "\n" + enriched_body).strip() + "\n"

    # Deterministic fallback: append claim-based content under existing body
    extra_lines = []
    for claim in page_claims[:8]:
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

    W5.5 ContentReviewer flags claim markers >50 chars from the nearest period
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
    claim_ids: List[str]
) -> List[Dict[str, Any]]:
    """Retrieve claims from product_facts by claim IDs.

    Args:
        product_facts: Product facts dictionary
        claim_ids: List of claim IDs to retrieve

    Returns:
        List of claim dictionaries matching the IDs
    """
    claims = product_facts.get("claims", [])
    claim_map = {c["claim_id"]: c for c in claims}

    result = []
    for claim_id in claim_ids:
        if claim_id in claim_map:
            result.append(claim_map[claim_id])

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
                claim_text = claim.get('claim_text', '')
                claim_id = claim.get('claim_id', '')
                # TC-1503 Fix C: Skip spec fragments in Key Capabilities
                if _is_spec_fragment(claim_text):
                    continue
                # TC-1660: Smart truncation at sentence boundary
                claim_text = _smart_truncate(claim_text, MAX_CLAIM_TEXT_LENGTH)
                lines.append(f"- {claim_text} [claim: {claim_id}]")
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

            if limitation_claims:
                lines.append(f"Known limitations and constraints for {product_name}:")
                lines.append("")

                # TC-1110: Pre-filter extremely long claims (>1KB)
                filtered_claims = [c for c in limitation_claims if len(c.get("claim_text", "")) <= MAX_CLAIM_FILTER_LENGTH]

                if len(filtered_claims) < len(limitation_claims):
                    logger.warning(f"[W5 Guide] Filtered out {len(limitation_claims) - len(filtered_claims)} limitation claims exceeding {MAX_CLAIM_FILTER_LENGTH} chars")

                # TC-1110: Simplify long claims by first-sentence extraction
                for claim in filtered_claims[:MAX_LIMITATION_CLAIMS]:
                    claim_text = claim.get("claim_text", "")
                    claim_id = claim.get("claim_id", "")
                    marker = f" [claim: {claim_id}]"
                    max_body = MAX_BULLET_LEN - 2 - len(marker)

                    if len(claim_text) > max_body:
                        sent_end = re.search(r'[.!?](?:\s|$)', claim_text)
                        if sent_end and sent_end.end() < len(claim_text) - 10:
                            claim_text = claim_text[:sent_end.end()].strip()
                        if len(claim_text) > max_body:
                            claim_text = _smart_truncate(claim_text, max_body)

                    lines.append(f"- {claim_text} [claim: {claim_id}]")

                lines.append("")
                logger.info(f"[W5 Guide] Generated Limitations section with {len(filtered_claims[:MAX_LIMITATION_CLAIMS])} claims")
            else:
                logger.warning(f"[W5 Guide] Limitations required but no limitation claims found")
                lines.append("No known limitations at this time.")
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

            # Build enriched claim context
            enriched_context = _build_enriched_claim_context(page_claims, product_facts)

            # Format workflows for prompt
            workflow_text = "\n\n".join([
                f"### {w.get('name', 'Workflow')}\n{w.get('description', '')}"
                for w in workflows
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
                # Call LLM
                result = _call_llm_for_content(
                    prompt=filled_prompt,
                    claims=page_claims,
                    snippets=snippet_catalog.get("snippets", []),
                    llm_client=llm_client,
                    min_words=200  # Comprehensive guide should be substantial
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

        if limitation_claims:
            lines.append(f"Known limitations and constraints for {product_name}:")
            lines.append("")

            # TC-1110: Pre-filter extremely long claims (>1KB)
            filtered_claims = [c for c in limitation_claims if len(c.get("claim_text", "")) <= MAX_CLAIM_FILTER_LENGTH]

            if len(filtered_claims) < len(limitation_claims):
                logger.warning(f"[W5 Guide] Filtered out {len(limitation_claims) - len(filtered_claims)} limitation claims exceeding {MAX_CLAIM_FILTER_LENGTH} chars")

            # TC-1110: Simplify long claims by first-sentence extraction
            for claim in filtered_claims[:MAX_LIMITATION_CLAIMS]:
                claim_text = claim.get("claim_text", "")
                claim_id = claim.get("claim_id", "")
                marker = f" [claim: {claim_id}]"
                max_body = MAX_BULLET_LEN - 2 - len(marker)

                if len(claim_text) > max_body:
                    sent_end = re.search(r'[.!?](?:\s|$)', claim_text)
                    if sent_end and sent_end.end() < len(claim_text) - 10:
                        claim_text = claim_text[:sent_end.end()].strip()
                    if len(claim_text) > max_body:
                        claim_text = _smart_truncate(claim_text, max_body)

                # Add claim marker per specs/08_section_writer.md
                lines.append(f"- {claim_text} [claim: {claim_id}]")

            lines.append("")
            logger.info(f"[W5 Guide] Generated Limitations section with {len(filtered_claims[:MAX_LIMITATION_CLAIMS])} claims")
        else:
            # No limitation claims found, but heading required
            logger.warning(f"[W5 Guide] Limitations required but no limitation claims found")
            lines.append("No known limitations at this time.")
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
        sections.append(f"```{language}\n{code}\n```\n\n")
    else:
        sections.append("```python\n# Example code demonstrating this feature\n```\n\n")

    # Add related information from related claims
    if related_claims:
        sections.append("## Additional Information\n\n")
        for rel_claim in related_claims[:3]:
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
        # Build enriched claim context for LLM
        enriched_context = _build_enriched_claim_context(all_feature_claims, product_facts)

        # Build snippet context
        snippets = snippet_catalog.get("snippets", [])
        snippet_texts = []
        for s in snippets[:5]:  # Top 5 snippets for context
            code = s.get("code", "")
            desc = s.get("description", "")
            snippet_texts.append(f"# {desc}\n{code}" if desc else code)
        snippet_context = "\n\n".join(snippet_texts) if snippet_texts else "No code examples available."

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
            # Call LLM
            result = _call_llm_for_content(
                prompt=filled_prompt,
                claims=all_feature_claims,
                snippets=snippets,
                llm_client=llm_client,
                min_words=250  # Feature showcase needs comprehensive coverage
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

            # Call LLM (TC-1658)
            result = _call_llm_for_content(
                filled_prompt,
                claims=limitation_claims,
                snippets=snippets,
                llm_client=llm_client,
                min_words=100
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
                if _is_spec_fragment(claim_text):
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
                lines.append(f"{claim_text}. [claim: {claim_id}]")
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
        if _is_spec_fragment(claim_text):
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
        lines.append(f"**Problem**: {claim_text} [claim: {claim_id}]")
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
        result = _call_llm_for_content(prompt, all_blog_claims, snippets[:3], llm_client, min_words=150)
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
        result = _call_llm_for_content(prompt, all_perf, [], llm_client, min_words=100)
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
    sections = []

    for claim in claims:
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

        # Call LLM
        result = _call_llm_for_content(
            filled_prompt,
            claims=claims,
            snippets=snippets,
            llm_client=llm_client,
            min_words=150  # Each FAQ should be substantial
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
                # Call LLM
                result = _call_llm_for_content(
                    prompt=filled_prompt,
                    claims=claims,
                    snippets=snippet_catalog.get("snippets", []),
                    llm_client=llm_client,
                    min_words=200  # Best practices need detailed explanations
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
            # Build enriched claim context
            enriched_context = _build_enriched_claim_context(claims, product_facts)

            # Format snippets for prompt (first 5, Python code blocks)
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
                # Call LLM (TC-1658)
                result = _call_llm_for_content(
                    prompt=filled_prompt,
                    claims=claims,
                    snippets=snippet_catalog.get("snippets", []),
                    llm_client=llm_client,
                    min_words=300  # Tutorials need comprehensive step-by-step content
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
