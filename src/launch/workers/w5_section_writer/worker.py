"""TC-440: W5 SectionWriter worker implementation.

This module implements the W5 SectionWriter that generates markdown content for
documentation page sections using templates and LLM-based content generation.

W5 SectionWriter performs:
1. Load page_plan.json from TC-430 (W4 IAPlanner)
2. Load product_facts.json from TC-410 (W2 FactsBuilder)
3. Load snippet_catalog.json from TC-420 (W3 SnippetCurator)
4. Generate markdown content for each page section
5. Ground content in facts and snippets with claim markers
6. Emit events and write draft files + manifest

Output artifacts:
- drafts/<page_id>_<section_id>.md (one per section)
- draft_manifest.json (listing all draft files)

Spec references:
- specs/07_section_templates.md (Section writing templates)
- specs/21_worker_contracts.md:195-226 (W5 SectionWriter contract)
- specs/10_determinism_and_caching.md (Stable output requirements)
- specs/11_state_and_events.md (Event emission)
- specs/23_claim_markers.md (Claim marker format)

TC-440: W5 SectionWriter
"""

from __future__ import annotations

import datetime
import hashlib
import json
import re
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, List

from ...io.run_layout import RunLayout
from ...models.event import (
    Event,
    EVENT_WORK_ITEM_STARTED,
    EVENT_WORK_ITEM_FINISHED,
    EVENT_ARTIFACT_WRITTEN,
    EVENT_ISSUE_OPENED,
    EVENT_RUN_FAILED,
)
from ...io.atomic import atomic_write_json
from ...util.logging import get_logger
from .link_transformer import transform_cross_section_links

logger = get_logger()


class SectionWriterError(Exception):
    """Base exception for W5 SectionWriter errors."""
    pass


class SectionWriterClaimMissingError(SectionWriterError):
    """Required claim not found in evidence map."""
    pass


class SectionWriterSnippetMissingError(SectionWriterError):
    """Required snippet not found in snippet catalog."""
    pass


class SectionWriterTemplateError(SectionWriterError):
    """Template rendering failure."""
    pass


class SectionWriterUnfilledTokensError(SectionWriterError):
    """Draft contains unfilled template tokens."""
    pass


class SectionWriterLLMError(SectionWriterError):
    """LLM API failure."""
    pass


def emit_event(
    run_layout: RunLayout,
    run_id: str,
    trace_id: str,
    span_id: str,
    event_type: str,
    payload: Dict[str, Any],
) -> None:
    """Emit a single event to events.ndjson.

    Args:
        run_layout: Run directory layout
        run_id: Run identifier
        trace_id: Trace ID for telemetry
        span_id: Span ID for telemetry
        event_type: Event type constant
        payload: Event payload dictionary
    """
    event = Event(
        event_id=str(uuid.uuid4()),
        run_id=run_id,
        ts=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        type=event_type,
        payload=payload,
        trace_id=trace_id,
        span_id=span_id,
    )

    events_file = run_layout.run_dir / "events.ndjson"
    with open(events_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(event.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")


def load_page_plan(artifacts_dir: Path) -> Dict[str, Any]:
    """Load page_plan.json from artifacts directory.

    Args:
        artifacts_dir: Path to artifacts directory

    Returns:
        Page plan dictionary

    Raises:
        SectionWriterError: If page_plan.json is missing or invalid
    """
    page_plan_path = artifacts_dir / "page_plan.json"
    if not page_plan_path.exists():
        raise SectionWriterError(f"Missing required artifact: {page_plan_path}")

    try:
        with open(page_plan_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise SectionWriterError(f"Invalid JSON in page_plan.json: {e}")


def load_product_facts(artifacts_dir: Path) -> Dict[str, Any]:
    """Load product_facts.json from artifacts directory.

    Args:
        artifacts_dir: Path to artifacts directory

    Returns:
        Product facts dictionary

    Raises:
        SectionWriterError: If product_facts.json is missing or invalid
    """
    product_facts_path = artifacts_dir / "product_facts.json"
    if not product_facts_path.exists():
        raise SectionWriterError(f"Missing required artifact: {product_facts_path}")

    try:
        with open(product_facts_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise SectionWriterError(f"Invalid JSON in product_facts.json: {e}")


def load_snippet_catalog(artifacts_dir: Path) -> Dict[str, Any]:
    """Load snippet_catalog.json from artifacts directory.

    Args:
        artifacts_dir: Path to artifacts directory

    Returns:
        Snippet catalog dictionary

    Raises:
        SectionWriterError: If snippet_catalog.json is missing or invalid
    """
    snippet_catalog_path = artifacts_dir / "snippet_catalog.json"
    if not snippet_catalog_path.exists():
        raise SectionWriterError(f"Missing required artifact: {snippet_catalog_path}")

    try:
        with open(snippet_catalog_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise SectionWriterError(f"Invalid JSON in snippet_catalog.json: {e}")


def load_evidence_map(artifacts_dir: Path) -> Dict[str, Any]:
    """Load evidence_map.json from artifacts directory.

    Args:
        artifacts_dir: Path to artifacts directory

    Returns:
        Evidence map dictionary (may be empty if file doesn't exist)
    """
    evidence_map_path = artifacts_dir / "evidence_map.json"
    if not evidence_map_path.exists():
        # Evidence map may not exist yet; return empty structure
        return {"claims": []}

    try:
        with open(evidence_map_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise SectionWriterError(f"Invalid JSON in evidence_map.json: {e}")


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


def generate_section_content(
    page: Dict[str, Any],
    product_facts: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
    llm_client: Optional[Any] = None,
) -> str:
    """Generate markdown content for a page section using LLM.

    Per specs/07_section_templates.md, content must:
    - Use ProductFacts fields (no invention)
    - Include claim markers for factual statements
    - Use snippet_catalog snippets by tag
    - Follow template structure for the section

    Args:
        page: Page specification from page_plan
        product_facts: Product facts dictionary
        snippet_catalog: Snippet catalog dictionary
        llm_client: Optional LLM client for content generation

    Returns:
        Generated markdown content as string

    Raises:
        SectionWriterClaimMissingError: If required claim not found
        SectionWriterSnippetMissingError: If required snippet not found
        SectionWriterLLMError: If LLM call fails
    """
    section = page["section"]
    title = page["title"]
    purpose = page["purpose"]
    required_headings = page.get("required_headings", [])
    required_claim_ids = page.get("required_claim_ids", [])
    required_snippet_tags = page.get("required_snippet_tags", [])
    template_variant = page.get("template_variant", "standard")

    # Get claims and snippets
    claims = get_claims_by_ids(product_facts, required_claim_ids)
    snippets = get_snippets_by_tags(snippet_catalog, required_snippet_tags)

    # Check for missing claims (emit warning but continue)
    if len(claims) < len(required_claim_ids):
        found_ids = {c["claim_id"] for c in claims}
        missing_ids = [cid for cid in required_claim_ids if cid not in found_ids]
        logger.warning(
            f"[W5 SectionWriter] Missing claims for page {page['slug']}: {missing_ids}"
        )

    # Check for missing snippets (emit warning but continue)
    if len(snippets) == 0 and len(required_snippet_tags) > 0:
        logger.warning(
            f"[W5 SectionWriter] No snippets found for page {page['slug']} with tags: {required_snippet_tags}"
        )

    # Build context for LLM prompt
    product_name = product_facts.get("product_name", "Product")
    positioning = product_facts.get("positioning", {})
    short_desc = positioning.get("short_description", "")
    tagline = positioning.get("tagline", "")

    # Build prompt for LLM
    if llm_client:
        prompt = _build_section_prompt(
            section=section,
            title=title,
            purpose=purpose,
            required_headings=required_headings,
            product_name=product_name,
            short_desc=short_desc,
            tagline=tagline,
            claims=claims,
            snippets=snippets,
            template_variant=template_variant,
        )

        try:
            response = llm_client.chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a technical documentation writer. Generate clear, accurate markdown content following the provided template structure and grounding all factual statements in provided claims."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                call_id=f"section_writer_{page['slug']}",
                temperature=0.0,  # Deterministic
            )
            content = response["content"]
        except Exception as e:
            raise SectionWriterLLMError(f"LLM call failed for page {page['slug']}: {e}")
    else:
        # Fallback: Generate simple template-based content
        content = _generate_fallback_content(
            section=section,
            title=title,
            purpose=purpose,
            required_headings=required_headings,
            product_name=product_name,
            claims=claims,
            snippets=snippets,
        )

    # TC-938: Transform cross-section links to absolute URLs
    # This ensures links between different sections (blog→docs, docs→reference, etc.)
    # use absolute URLs that work across the subdomain architecture
    page_metadata = {
        "locale": page.get("locale", "en"),
        "family": product_facts.get("product_family", ""),
        "platform": page.get("platform", ""),
    }
    content = transform_cross_section_links(
        markdown_content=content,
        current_section=section,
        page_metadata=page_metadata,
    )

    return content


def _build_section_prompt(
    section: str,
    title: str,
    purpose: str,
    required_headings: List[str],
    product_name: str,
    short_desc: str,
    tagline: str,
    claims: List[Dict[str, Any]],
    snippets: List[Dict[str, Any]],
    template_variant: str,
) -> str:
    """Build LLM prompt for section content generation.

    Args:
        section: Section name (products, docs, reference, kb, blog)
        title: Page title
        purpose: Page purpose
        required_headings: List of required heading titles
        product_name: Product name
        short_desc: Product short description
        tagline: Product tagline
        claims: List of claim dictionaries
        snippets: List of snippet dictionaries
        template_variant: Template variant (minimal, standard, rich)

    Returns:
        Formatted prompt string
    """
    prompt_parts = [
        f"# Task: Generate documentation page content",
        f"",
        f"## Page Information",
        f"- Section: {section}",
        f"- Title: {title}",
        f"- Purpose: {purpose}",
        f"- Template Variant: {template_variant}",
        f"",
        f"## Product Context",
        f"- Product Name: {product_name}",
        f"- Short Description: {short_desc}",
        f"- Tagline: {tagline}",
        f"",
        f"## Required Headings",
    ]

    for heading in required_headings:
        prompt_parts.append(f"- {heading}")

    prompt_parts.extend([
        f"",
        f"## Available Claims (use these for factual statements)",
    ])

    for i, claim in enumerate(claims, 1):
        claim_text = claim.get("claim_text", "")
        claim_id = claim.get("claim_id", "")
        prompt_parts.append(f"{i}. {claim_text} [claim_id: {claim_id}]")

    if not claims:
        prompt_parts.append("(No claims available)")

    prompt_parts.extend([
        f"",
        f"## Available Code Snippets",
    ])

    for i, snippet in enumerate(snippets, 1):
        snippet_id = snippet.get("snippet_id", "")
        language = snippet.get("language", "")
        tags = ", ".join(snippet.get("tags", []))
        code = snippet.get("code", "")
        # Truncate long snippets in prompt
        if len(code) > 500:
            code = code[:500] + "\n... (truncated)"
        prompt_parts.append(f"{i}. Snippet ID: {snippet_id} (Language: {language}, Tags: {tags})")
        prompt_parts.append(f"```{language}")
        prompt_parts.append(code)
        prompt_parts.append("```")
        prompt_parts.append("")

    if not snippets:
        prompt_parts.append("(No code snippets available)")

    prompt_parts.extend([
        f"",
        f"## Instructions",
        f"1. Generate markdown content for this page following the required headings",
        f"2. For every factual statement or bullet point, add a claim marker: `<!-- claim_id: <CLAIM_ID> -->`",
        f"3. Place the claim marker immediately after the sentence on the same line",
        f"4. Use code snippets where appropriate (include them in code fences)",
        f"5. Keep the content clear, concise, and technically accurate",
        f"6. Do NOT invent facts - only use the provided claims",
        f"7. Do NOT leave any placeholder tokens like __PRODUCT_NAME__ in the output",
        f"8. Generate complete, ready-to-publish content",
        f"",
        f"## Output Format",
        f"Provide only the markdown content (no explanations or meta-commentary).",
    ])

    return "\n".join(prompt_parts)


def _generate_fallback_content(
    section: str,
    title: str,
    purpose: str,
    required_headings: List[str],
    product_name: str,
    claims: List[Dict[str, Any]],
    snippets: List[Dict[str, Any]],
) -> str:
    """Generate simple fallback content without LLM.

    Used when LLM client is not available for testing or fallback scenarios.

    Args:
        section: Section name
        title: Page title
        purpose: Page purpose
        required_headings: List of required headings
        product_name: Product name
        claims: List of claims
        snippets: List of snippets

    Returns:
        Generated markdown content
    """
    lines = [
        f"# {title}",
        f"",
        f"{purpose}",
        f"",
    ]

    for heading in required_headings:
        lines.append(f"## {heading}")
        lines.append("")

        # Add a few claims under each heading
        heading_claims = claims[:2]
        for claim in heading_claims:
            claim_text = claim.get("claim_text", "")
            claim_id = claim.get("claim_id", "")
            lines.append(f"- {claim_text} <!-- claim_id: {claim_id} -->")

        lines.append("")

        # Add a snippet if available
        if snippets and heading.lower() in ["example", "code example", "quickstart", "getting started"]:
            snippet = snippets[0]
            language = snippet.get("language", "")
            code = snippet.get("code", "")
            lines.append(f"```{language}")
            lines.append(code)
            lines.append("```")
            lines.append("")

    return "\n".join(lines)


def check_unfilled_tokens(content: str) -> List[str]:
    """Check for unfilled template tokens in content.

    Per specs/21_worker_contracts.md:211-213, drafts must not contain
    unreplaced template tokens.

    Args:
        content: Markdown content to check

    Returns:
        List of unfilled tokens found (empty if none)
    """
    # Match __UPPER_SNAKE__ pattern
    pattern = r'__[A-Z_]+__'
    matches = re.findall(pattern, content)
    return list(set(matches))  # Return unique tokens


def generate_page_id(page: Dict[str, Any]) -> str:
    """Generate deterministic page ID from page specification.

    Args:
        page: Page specification dictionary

    Returns:
        Page ID string (e.g., "products_overview", "docs_getting-started")
    """
    section = page["section"]
    slug = page["slug"]
    return f"{section}_{slug}"


def execute_section_writer(
    run_dir: Path,
    run_config: Dict[str, Any],
    llm_client: Optional[Any] = None,
) -> Dict[str, Any]:
    """Execute W5 SectionWriter worker.

    Generates markdown content for all planned pages using templates,
    product facts, and snippet catalog.

    Per specs/07_section_templates.md and specs/21_worker_contracts.md:195-226.

    Args:
        run_dir: Path to run directory
        run_config: Run configuration dictionary
        llm_client: Optional LLM client for content generation

    Returns:
        Dictionary containing:
        - status: "success" or "failed"
        - manifest_path: Path to draft_manifest.json
        - draft_count: Number of drafts generated
        - total_pages: Total pages processed

    Raises:
        SectionWriterError: If section writing fails
        SectionWriterUnfilledTokensError: If unfilled tokens remain
        SectionWriterLLMError: If LLM call fails
    """
    run_layout = RunLayout(run_dir=run_dir)
    run_id = run_config.get("run_id", "unknown")
    trace_id = str(uuid.uuid4())
    span_id = str(uuid.uuid4())

    logger.info(f"[W5 SectionWriter] Starting section writing for run {run_id}")

    # Emit start event
    emit_event(
        run_layout=run_layout,
        run_id=run_id,
        trace_id=trace_id,
        span_id=span_id,
        event_type=EVENT_WORK_ITEM_STARTED,
        payload={"worker": "w5_section_writer", "phase": "section_writing"},
    )

    try:
        # Load input artifacts
        page_plan = load_page_plan(run_layout.artifacts_dir)
        product_facts = load_product_facts(run_layout.artifacts_dir)
        snippet_catalog = load_snippet_catalog(run_layout.artifacts_dir)
        evidence_map = load_evidence_map(run_layout.artifacts_dir)

        pages = page_plan.get("pages", [])
        logger.info(f"[W5 SectionWriter] Processing {len(pages)} pages")

        # Create drafts directory
        drafts_dir = run_layout.run_dir / "drafts"
        drafts_dir.mkdir(parents=True, exist_ok=True)

        # Generate content for each page
        draft_files = []
        for page in pages:
            page_id = generate_page_id(page)
            slug = page["slug"]
            section = page["section"]

            logger.info(f"[W5 SectionWriter] Generating content for page: {page_id}")

            # Generate section content
            content = generate_section_content(
                page=page,
                product_facts=product_facts,
                snippet_catalog=snippet_catalog,
                llm_client=llm_client,
            )

            # Check for unfilled tokens
            unfilled_tokens = check_unfilled_tokens(content)
            if unfilled_tokens:
                error_msg = f"Unfilled tokens in page {page_id}: {', '.join(unfilled_tokens)}"
                logger.error(f"[W5 SectionWriter] {error_msg}")

                # Emit issue
                emit_event(
                    run_layout=run_layout,
                    run_id=run_id,
                    trace_id=trace_id,
                    span_id=span_id,
                    event_type=EVENT_ISSUE_OPENED,
                    payload={
                        "issue_id": f"unfilled_tokens_{page_id}",
                        "error_code": "SECTION_WRITER_UNFILLED_TOKENS",
                        "severity": "blocker",
                        "message": error_msg,
                        "page_id": page_id,
                        "tokens": unfilled_tokens,
                    },
                )

                raise SectionWriterUnfilledTokensError(error_msg)

            # Write draft file
            # Per specs/21_worker_contracts.md:206, use section subdirectories
            section_dir = drafts_dir / section
            section_dir.mkdir(parents=True, exist_ok=True)

            draft_filename = f"{slug}.md"
            draft_path = section_dir / draft_filename

            with open(draft_path, "w", encoding="utf-8") as f:
                f.write(content)

            logger.info(f"[W5 SectionWriter] Wrote draft: {draft_path}")

            # Track draft file
            draft_files.append({
                "page_id": page_id,
                "section": section,
                "slug": slug,
                "output_path": page["output_path"],
                "draft_path": str(draft_path.relative_to(run_layout.run_dir)),
                "title": page["title"],
                "word_count": len(content.split()),
                "claim_count": content.count("<!-- claim_id:"),
            })

            # Emit draft written event
            emit_event(
                run_layout=run_layout,
                run_id=run_id,
                trace_id=trace_id,
                span_id=span_id,
                event_type=EVENT_ARTIFACT_WRITTEN,
                payload={
                    "artifact": "draft",
                    "page_id": page_id,
                    "path": str(draft_path),
                },
            )

        # Sort draft files deterministically per specs/10_determinism_and_caching.md:43
        # Sort by (section_order, output_path)
        section_order = {"products": 0, "docs": 1, "reference": 2, "kb": 3, "blog": 4}
        draft_files.sort(key=lambda d: (section_order.get(d["section"], 99), d["output_path"]))

        # Build manifest
        manifest = {
            "schema_version": "1.0",
            "run_id": run_id,
            "total_pages": len(pages),
            "draft_count": len(draft_files),
            "drafts": draft_files,
        }

        # Write manifest
        manifest_path = run_layout.artifacts_dir / "draft_manifest.json"
        atomic_write_json(manifest_path, manifest)

        logger.info(f"[W5 SectionWriter] Wrote draft manifest: {manifest_path}")

        # Emit manifest written event
        emit_event(
            run_layout=run_layout,
            run_id=run_id,
            trace_id=trace_id,
            span_id=span_id,
            event_type=EVENT_ARTIFACT_WRITTEN,
            payload={
                "artifact": "draft_manifest.json",
                "path": str(manifest_path),
                "draft_count": len(draft_files),
            },
        )

        # Emit completion event
        emit_event(
            run_layout=run_layout,
            run_id=run_id,
            trace_id=trace_id,
            span_id=span_id,
            event_type=EVENT_WORK_ITEM_FINISHED,
            payload={
                "worker": "w5_section_writer",
                "phase": "section_writing",
                "status": "success",
                "draft_count": len(draft_files),
            },
        )

        return {
            "status": "success",
            "manifest_path": str(manifest_path),
            "draft_count": len(draft_files),
            "total_pages": len(pages),
        }

    except Exception as e:
        logger.error(f"[W5 SectionWriter] Section writing failed: {e}")

        # Emit failure event
        emit_event(
            run_layout=run_layout,
            run_id=run_id,
            trace_id=trace_id,
            span_id=span_id,
            event_type=EVENT_RUN_FAILED,
            payload={
                "worker": "w5_section_writer",
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )

        raise
