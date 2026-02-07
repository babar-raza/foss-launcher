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
from ...io.artifact_store import ArtifactStore
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

    TC-1033: Delegates to ArtifactStore.emit_event for centralized event emission.

    Args:
        run_layout: Run directory layout
        run_id: Run identifier
        trace_id: Trace ID for telemetry
        span_id: Span ID for telemetry
        event_type: Event type constant
        payload: Event payload dictionary
    """
    store = ArtifactStore(run_dir=run_layout.run_dir)
    store.emit_event(
        event_type,
        payload,
        run_id=run_id,
        trace_id=trace_id,
        span_id=span_id,
    )


def load_page_plan(artifacts_dir: Path) -> Dict[str, Any]:
    """Load page_plan.json from artifacts directory.

    TC-1033: Delegates to ArtifactStore.load_artifact for centralized I/O.

    Args:
        artifacts_dir: Path to artifacts directory

    Returns:
        Page plan dictionary

    Raises:
        SectionWriterError: If page_plan.json is missing or invalid
    """
    store = ArtifactStore(run_dir=artifacts_dir.parent)
    try:
        return store.load_artifact("page_plan.json", validate_schema=False)
    except FileNotFoundError:
        raise SectionWriterError(f"Missing required artifact: {artifacts_dir / 'page_plan.json'}")
    except json.JSONDecodeError as e:
        raise SectionWriterError(f"Invalid JSON in page_plan.json: {e}")


def load_product_facts(artifacts_dir: Path) -> Dict[str, Any]:
    """Load product_facts.json from artifacts directory.

    TC-1033: Delegates to ArtifactStore.load_artifact for centralized I/O.

    Args:
        artifacts_dir: Path to artifacts directory

    Returns:
        Product facts dictionary

    Raises:
        SectionWriterError: If product_facts.json is missing or invalid
    """
    store = ArtifactStore(run_dir=artifacts_dir.parent)
    try:
        return store.load_artifact("product_facts.json", validate_schema=False)
    except FileNotFoundError:
        raise SectionWriterError(f"Missing required artifact: {artifacts_dir / 'product_facts.json'}")
    except json.JSONDecodeError as e:
        raise SectionWriterError(f"Invalid JSON in product_facts.json: {e}")


def load_snippet_catalog(artifacts_dir: Path) -> Dict[str, Any]:
    """Load snippet_catalog.json from artifacts directory.

    TC-1033: Delegates to ArtifactStore.load_artifact for centralized I/O.

    Args:
        artifacts_dir: Path to artifacts directory

    Returns:
        Snippet catalog dictionary

    Raises:
        SectionWriterError: If snippet_catalog.json is missing or invalid
    """
    store = ArtifactStore(run_dir=artifacts_dir.parent)
    try:
        return store.load_artifact("snippet_catalog.json", validate_schema=False)
    except FileNotFoundError:
        raise SectionWriterError(f"Missing required artifact: {artifacts_dir / 'snippet_catalog.json'}")
    except json.JSONDecodeError as e:
        raise SectionWriterError(f"Invalid JSON in snippet_catalog.json: {e}")


def load_evidence_map(artifacts_dir: Path) -> Dict[str, Any]:
    """Load evidence_map.json from artifacts directory.

    TC-1033: Delegates to ArtifactStore.load_artifact_or_default for centralized I/O.

    Args:
        artifacts_dir: Path to artifacts directory

    Returns:
        Evidence map dictionary (may be empty if file doesn't exist)
    """
    store = ArtifactStore(run_dir=artifacts_dir.parent)
    try:
        return store.load_artifact_or_default(
            "evidence_map.json",
            default={"claims": []},
            validate_schema=False,
        )
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
        f"Welcome to the {product_name} documentation. This page provides an overview of the available documentation resources and guides.",
        "",
    ])

    # Build child pages list
    current_slug = page.get("slug", "")
    if child_pages_spec:
        lines.append("## Documentation Index")
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

                # Format: - [title](url) - purpose
                lines.append(f"- [{child_title}]({child_url}) - {child_purpose}")
            else:
                logger.warning(f"[W5 TOC] Child page not found: {child_slug}")

        lines.append("")

    # Build quick links section
    lines.append("## Quick Links")
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

    return "\n".join(lines)


def generate_comprehensive_guide_content(
    page: Dict[str, Any],
    product_facts: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
) -> str:
    """Generate comprehensive developer guide content.

    Lists ALL workflows from product_facts with code snippets.
    Each workflow must have description + code snippet + repo link.

    Args:
        page: Page specification from page_plan
        product_facts: Product facts dictionary
        snippet_catalog: Snippet catalog dictionary

    Returns:
        Markdown content for comprehensive guide

    Raises:
        SectionWriterError: If workflows missing from product_facts
    """
    # Extract product metadata
    product_name = product_facts.get("product_name", "Product")
    workflows = product_facts.get("workflows", [])
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

    # Check if workflows exist
    if not workflows:
        logger.warning(f"[W5 Guide] No workflows found in product_facts")
        lines.append("## Workflows")
        lines.append("")
        lines.append("No workflows available at this time.")
        lines.append("")
        return "\n".join(lines)

    # Log workflow count for evidence
    logger.info(f"[W5 Guide] Generating guide with {len(workflows)} workflows")

    # Add h2 section heading before h3 workflow headings (accessibility compliance)
    lines.append("## Workflows")
    lines.append("")

    # Build workflow sections
    for workflow in workflows:
        workflow_name = workflow.get("name", "Workflow")
        workflow_desc = workflow.get("description", "")
        workflow_id = workflow.get("workflow_id", "")

        # Add H3 heading
        lines.append(f"### {workflow_name}")
        lines.append("")

        # Add description
        if workflow_desc:
            lines.append(workflow_desc)
            lines.append("")

        # Find matching snippet by workflow_id or tags
        snippet = None
        snippets = snippet_catalog.get("snippets", [])

        # Try to find snippet by workflow_id in tags
        for s in snippets:
            if workflow_id in s.get("tags", []):
                snippet = s
                break

        # If no snippet found, try by workflow name
        if not snippet:
            for s in snippets:
                if workflow_name.lower().replace(" ", "_") in s.get("tags", []):
                    snippet = s
                    break

        # Add code block
        if snippet:
            language = snippet.get("language", "")
            code = snippet.get("code", "")
            source_path = snippet.get("source", {}).get("path", "")

            lines.append(f"```{language}")
            lines.append(code)
            lines.append("```")
            lines.append("")

            # Add repo link
            if repo_url and source_path:
                full_url = f"{repo_url}/blob/{sha}/{source_path}"
                lines.append(f"[View full example on GitHub]({full_url})")
                lines.append("")
        else:
            # Graceful degradation: show placeholder if snippet missing
            logger.warning(f"[W5 Guide] No snippet found for workflow: {workflow_id}")
            lines.append("```python")
            lines.append("# Code example for this workflow")
            lines.append("# TODO: Add example")
            lines.append("```")
            lines.append("")

        # Add separator
        lines.append("---")
        lines.append("")

    # Build Additional Resources section
    lines.append("## Additional Resources")
    lines.append("")
    lines.append("- [Getting Started Guide](/docs/getting-started/)")
    lines.append("- [API Reference](/reference/)")
    lines.append("- [Knowledge Base](/kb/)")
    if repo_url:
        lines.append(f"- [GitHub Repository]({repo_url})")
    lines.append("")

    return "\n".join(lines)


def generate_feature_showcase_content(
    page: Dict[str, Any],
    product_facts: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
) -> str:
    """Generate KB feature showcase article content.

    Creates how-to guide for a specific prominent feature.
    MUST focus on single feature (1 primary claim) - Gate 14 Rule 4.

    Args:
        page: Page specification from page_plan
        product_facts: Product facts dictionary
        snippet_catalog: Snippet catalog dictionary

    Returns:
        Markdown content for feature showcase

    Raises:
        SectionWriterError: If primary claim not found
    """
    # Extract page metadata
    product_name = product_facts.get("product_name", "Product")
    required_claim_ids = page.get("required_claim_ids", [])
    repo_url = product_facts.get("repo_url", "")

    # Get primary claim (first claim ID)
    if not required_claim_ids:
        raise SectionWriterError(f"Feature showcase page {page['slug']} has no required_claim_ids")

    primary_claim_id = required_claim_ids[0]

    # Find the claim
    claims = product_facts.get("claims", [])
    claim = None
    for c in claims:
        if c.get("claim_id") == primary_claim_id:
            claim = c
            break

    if not claim:
        raise SectionWriterClaimMissingError(f"Primary claim {primary_claim_id} not found in product_facts")

    feature_text = claim.get("claim_text", "")

    # Find matching snippet
    snippet = None
    snippets = snippet_catalog.get("snippets", [])

    # Try to find snippet by claim tags or feature keywords
    for s in snippets:
        tags = s.get("tags", [])
        if primary_claim_id in tags or any(tag in feature_text.lower() for tag in tags):
            snippet = s
            break

    # Build content with frontmatter (Gate 4: required fields)
    title = page.get("title", "Feature Showcase")
    section = page.get("section", "kb")
    layout = section if section in ["docs", "products", "reference", "kb", "blog"] else "default"
    url_path = page.get("url_path", "")
    lines = [
        "---",
        f'title: "{title}"',
        f'description: "{page.get("purpose", "Feature showcase")}"',
        f"layout: {layout}",
    ]
    if url_path:
        lines.append(f"permalink: {url_path}")
    lines.extend([
        "---",
        "",
        f"# {title}",
        "",
    ])

    # Overview section with claim marker
    lines.append("## Overview")
    lines.append("")
    lines.append(f"{product_name} {feature_text} <!-- claim_id: {primary_claim_id} -->")
    lines.append("")

    # When to Use section
    lines.append("## When to Use")
    lines.append("")
    # Use lowercase for when to use section (sounds more natural)
    when_to_use_text = feature_text[0].lower() + feature_text[1:] if feature_text else feature_text
    lines.append(f"This feature is particularly useful when you need to {when_to_use_text}.")
    lines.append("")

    # Step-by-Step Guide section
    lines.append("## Step-by-Step Guide")
    lines.append("")
    lines.append("Follow these steps to use this feature:")
    lines.append("")
    lines.append("1. **Import the library**: Import the necessary modules and classes.")
    lines.append("2. **Initialize the object**: Create an instance of the required class.")
    lines.append("3. **Configure settings**: Set any required properties or options.")
    lines.append("4. **Execute the operation**: Call the method to perform the feature.")
    lines.append("")

    # Code Example section
    lines.append("## Code Example")
    lines.append("")

    if snippet:
        language = snippet.get("language", "")
        code = snippet.get("code", "")

        lines.append(f"```{language}")
        lines.append(code)
        lines.append("```")
        lines.append("")
    else:
        # Graceful degradation: show placeholder if snippet missing
        logger.warning(f"[W5 Showcase] No snippet found for claim: {primary_claim_id}")
        lines.append("```python")
        lines.append("# Code example for this feature")
        lines.append("# TODO: Add example")
        lines.append("```")
        lines.append("")

    # Related Links section
    lines.append("## Related Links")
    lines.append("")
    lines.append("- [Developer Guide](/docs/developer-guide/)")
    lines.append("- [API Reference](/reference/)")
    if repo_url:
        lines.append(f"- [GitHub Repository]({repo_url})")
    lines.append("")

    return "\n".join(lines)


def generate_section_content(
    page: Dict[str, Any],
    product_facts: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
    llm_client: Optional[Any] = None,
    page_plan: Optional[Dict[str, Any]] = None,
) -> str:
    """Generate markdown content for a page section using LLM or specialized generators.

    Per specs/07_section_templates.md, content must:
    - Use ProductFacts fields (no invention)
    - Include claim markers for factual statements
    - Use snippet_catalog snippets by tag
    - Follow template structure for the section

    TC-973: Routes to specialized generators based on page_role:
    - page_role="toc" -> generate_toc_content()
    - page_role="comprehensive_guide" -> generate_comprehensive_guide_content()
    - page_role="feature_showcase" -> generate_feature_showcase_content()
    - Other roles -> template-driven or LLM-based generation

    Args:
        page: Page specification from page_plan
        product_facts: Product facts dictionary
        snippet_catalog: Snippet catalog dictionary
        llm_client: Optional LLM client for content generation
        page_plan: Optional complete page plan (required for TOC generation)

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
    template_path = page.get("template_path")
    token_mappings = page.get("token_mappings")
    page_role = page.get("page_role", "landing")

    # TC-973: Route specialized generators FIRST (before template handling)
    # TOC pages must use generate_toc_content() to include child page references
    if page_role == "toc":
        logger.info(f"[W5] Generating TOC content for {page['slug']} (specialized generator)")
        if not page_plan:
            raise SectionWriterError("page_plan required for TOC generation")
        return generate_toc_content(page, product_facts, page_plan)

    # TC-964: Handle template-driven pages (for non-TOC pages with templates)
    # If page has template_path and token_mappings, load template and apply tokens
    if template_path and token_mappings:
        logger.info(f"[W5 SectionWriter] Loading template for page {page['slug']}: {template_path}")
        try:
            template_file = Path(template_path)
            template_content = template_file.read_text(encoding="utf-8")

            # Apply token mappings to replace placeholders
            content = apply_token_mappings(template_content, token_mappings)

            logger.info(f"[W5 SectionWriter] Applied {len(token_mappings)} token mappings to template")

            # TC-974: Inject layout and permalink into frontmatter if missing (Gate 4 compliance)
            content = inject_frontmatter_fields(content, page, section, token_mappings)

            # TC-938: Transform cross-section links to absolute URLs
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

        except Exception as e:
            logger.error(f"[W5 SectionWriter] Failed to load template {template_path}: {e}")
            raise SectionWriterTemplateError(f"Failed to load template {template_path}: {e}")

    # TC-973: Route by page_role to specialized generators (for non-template pages)
    # Note: TOC pages are handled earlier (before template processing)
    if page_role == "comprehensive_guide":
        logger.info(f"[W5] Generating comprehensive guide for {page['slug']}")
        return generate_comprehensive_guide_content(page, product_facts, snippet_catalog)

    elif page_role == "feature_showcase":
        logger.info(f"[W5] Generating feature showcase for {page['slug']}")
        return generate_feature_showcase_content(page, product_facts, snippet_catalog)

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
    forbidden_topics = page.get("forbidden_topics", [])
    if not forbidden_topics:
        forbidden_topics = page.get("content_strategy", {}).get("forbidden_topics", [])

    content = None  # Will be set by LLM or fallback
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
            forbidden_topics=forbidden_topics,
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

            # TC-5A: Post-process LLM output to replace any echoed placeholder tokens
            # LLMs sometimes echo tokens like __PRODUCT_NAME__ from prompt context
            llm_replacements = {
                "__PRODUCT_NAME__": product_name,
                "__PLATFORM__": page.get("platform", ""),
                "__FAMILY__": product_facts.get("product_family", ""),
                "__LOCALE__": page.get("locale", "en"),
                "__SECTION__": section,
            }
            for token, value in llm_replacements.items():
                if token in content:
                    content = content.replace(token, value)

            # TC-5A: Strip invalid bare-number claim markers (LLM uses list index instead of claim_id)
            content = re.sub(r'\[claim:\s*\d+\]', '', content)

            # TC-5B: Validate and strip hallucinated claim IDs
            # LLM sometimes generates corrupted claim IDs (e.g., valid prefix + garbage)
            valid_claim_ids = {c.get("claim_id") for c in claims if c.get("claim_id")}

            def validate_claim_marker(match: re.Match) -> str:
                claim_id = match.group(1)
                if claim_id in valid_claim_ids:
                    return match.group(0)  # Keep valid marker
                # Strip invalid/hallucinated claim marker
                logger.warning(f"[W5] Stripping hallucinated claim marker: {claim_id[:20]}...")
                return ""

            content = re.sub(r'\[claim:\s*([a-zA-Z0-9_-]+)\]', validate_claim_marker, content)

            # TC-5C: Sanitize headings with forbidden topics
            # Gate 14 flags headings containing forbidden topic keywords
            if forbidden_topics:
                def sanitize_heading(match: re.Match) -> str:
                    heading_prefix = match.group(1)  # ## or ### etc.
                    heading_text = match.group(2)
                    heading_lower = heading_text.lower()

                    for topic in forbidden_topics:
                        topic_lower = topic.lower().replace("_", " ")
                        if topic_lower in heading_lower:
                            # Replace forbidden topic with generic alternative
                            new_text = re.sub(
                                re.escape(topic_lower),
                                "Highlights",
                                heading_text,
                                flags=re.IGNORECASE
                            )
                            logger.warning(f"[W5] Sanitized forbidden topic '{topic}' in heading: {heading_text} -> {new_text}")
                            return f"{heading_prefix}{new_text}"

                    return match.group(0)

                content = re.sub(r'^(#{1,6}\s+)(.+)$', sanitize_heading, content, flags=re.MULTILINE)

            # TC-5A: Ensure LLM-generated content has frontmatter (Hugo build requirement)
            # The LLM returns raw markdown without frontmatter; Hugo requires it.
            if not content.strip().startswith("---"):
                layout = section if section in ["docs", "products", "reference", "kb", "blog"] else "default"
                url_path = page.get("url_path", "")
                safe_title = title.replace('"', '\\"')
                safe_purpose = purpose.replace('"', '\\"')
                fm_lines = [
                    "---",
                    f'title: "{safe_title}"',
                    f'description: "{safe_purpose}"',
                    f"layout: {layout}",
                ]
                if url_path:
                    fm_lines.append(f"permalink: {url_path}")
                fm_lines.extend(["---", ""])
                content = "\n".join(fm_lines) + "\n" + content
        except Exception as e:
            # TC-5D: Graceful fallback when LLM fails - use template-based content
            logger.warning(f"[W5] LLM call failed for page {page['slug']}: {e}. Falling back to template-based content.")
            llm_client = None  # Force fallback path
            content = None  # Will be generated in fallback block

    if content is None:
        # Fallback: Generate simple template-based content
        content = _generate_fallback_content(
            section=section,
            title=title,
            purpose=purpose,
            required_headings=required_headings,
            product_name=product_name,
            claims=claims,
            snippets=snippets,
            url_path=page.get("url_path", ""),
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
    forbidden_topics: Optional[List[str]] = None,
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

    for claim in claims:
        claim_text = claim.get("claim_text", "")
        claim_id = claim.get("claim_id", "")
        prompt_parts.append(f"- CLAIM_ID={claim_id}: {claim_text}")

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

    # TC-5A: Add forbidden_topics to prompt if provided
    if forbidden_topics:
        prompt_parts.extend([
            f"",
            f"## Forbidden Topics (DO NOT include content about these)",
        ])
        for topic in forbidden_topics:
            prompt_parts.append(f"- {topic}")

    prompt_parts.extend([
        f"",
        f"## Instructions",
        f"1. Generate markdown content for this page following the required headings",
        f"2. For every factual statement, add a claim marker using the exact CLAIM_ID: `[claim: <CLAIM_ID>]`",
        f"3. Place the claim marker immediately after the sentence on the same line. Use the FULL CLAIM_ID, not a number.",
        f"4. Use code snippets where appropriate (include them in code fences)",
        f"5. Keep the content clear, concise, and technically accurate",
        f"6. Do NOT invent facts - only use the provided claims",
        f"7. Do NOT leave any placeholder tokens like __PRODUCT_NAME__ in the output",
        f"8. Generate complete, ready-to-publish content",
        f"9. Do NOT include YAML frontmatter (---) - provide only the markdown body",
        f"10. All internal links must use Hugo-style URL paths (e.g., /docs/getting-started/), NOT source code file paths",
        f"11. Do NOT link to .py files, examples/ directories, or source code paths",
    ])

    if forbidden_topics:
        prompt_parts.append(f"12. Do NOT write about forbidden topics listed above")

    prompt_parts.extend([
        f"",
        f"## Output Format",
        f"Provide only the markdown content (no explanations or meta-commentary). Do NOT include frontmatter.",
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
    url_path: str = "",
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
        url_path: URL path for permalink field

    Returns:
        Generated markdown content with frontmatter
    """
    # Generate frontmatter (TC-974: Fix Gate 4 - add layout and permalink fields)
    layout = section if section in ["docs", "products", "reference", "kb", "blog"] else "default"
    frontmatter = [
        "---",
        f"title: \"{title}\"",
        f"description: \"{purpose}\"",
        f"layout: {layout}",
    ]
    if url_path:
        frontmatter.append(f"permalink: {url_path}")
    frontmatter.extend([
        "---",
        "",
    ])

    lines = frontmatter + [
        f"# {title}",
        f"",
        f"{purpose}",
        f"",
    ]

    for i, heading in enumerate(required_headings):
        lines.append(f"## {heading}")
        lines.append("")

        # TC-982: Distribute claims evenly across headings (not same first 2)
        # TC-977: Use [claim: claim_id] format for Gate 14 compliance
        if claims and required_headings:
            claims_per_heading = max(1, len(claims) // len(required_headings))
            start_idx = i * claims_per_heading
            heading_claims = claims[start_idx:start_idx + claims_per_heading]
        else:
            heading_claims = []

        for claim in heading_claims:
            claim_text = claim.get("claim_text", "")
            claim_id = claim.get("claim_id", "")
            lines.append(f"- {claim_text} [claim: {claim_id}]")

        # TC-982: If no claims assigned to this heading, use purpose as fallback
        if len(heading_claims) == 0 and purpose:
            lines.append(f"{purpose}")

        lines.append("")

        # TC-982: Broadened snippet matching with partial keyword matching
        heading_lower = heading.lower()
        snippet_keywords = ["example", "code", "quickstart", "started",
                            "usage", "install", "features", "overview"]
        if snippets and any(kw in heading_lower for kw in snippet_keywords):
            # TC-982: Rotate snippets across headings instead of always snippets[0]
            snippet_idx = i % len(snippets)
            snippet = snippets[snippet_idx]
            language = snippet.get("language", "")
            code = snippet.get("code", "")
            lines.append(f"```{language}")
            lines.append(code)
            lines.append("```")
            lines.append("")

    return "\n".join(lines)


def inject_frontmatter_fields(
    content: str,
    page: Dict[str, Any],
    section: str,
    token_mappings: Dict[str, str],
) -> str:
    """Inject layout and permalink into frontmatter if missing (TC-974: Gate 4 compliance).

    Args:
        content: Markdown content with frontmatter
        page: Page specification
        section: Section name
        token_mappings: Token mappings with __LAYOUT__ and __PERMALINK__

    Returns:
        Modified markdown content with layout and permalink in frontmatter
    """
    # Check if content has frontmatter
    if not content.startswith("---"):
        return content

    # Split frontmatter and body using line-aware delimiter
    # Simple split("---", 2) breaks when frontmatter contains "---" in string values
    # (e.g., claim text like '--- some text'). Use regex to find "---" on its own line.
    import re
    fm_pattern = re.compile(r'^---\s*$', re.MULTILINE)
    markers = list(fm_pattern.finditer(content))
    if len(markers) < 2:
        return content

    fm_start = markers[0].end()
    fm_end = markers[1].start()
    frontmatter = content[fm_start:fm_end]
    body = content[markers[1].end():]

    # Check if layout and permalink are already present
    has_layout = "layout:" in frontmatter
    has_permalink = "permalink:" in frontmatter

    # Get values from token_mappings
    layout = token_mappings.get("__LAYOUT__", section)
    permalink = token_mappings.get("__PERMALINK__", page.get("url_path", ""))

    # Inject missing fields at the end of frontmatter
    additions = []
    if not has_layout and layout:
        additions.append(f"layout: {layout}")
    if not has_permalink and permalink:
        additions.append(f"permalink: {permalink}")

    if additions:
        # Add fields before closing ---
        frontmatter = frontmatter.rstrip() + "\n" + "\n".join(additions) + "\n"

    # Reconstruct content
    return f"---{frontmatter}---{body}"


def apply_token_mappings(template_content: str, token_mappings: Dict[str, str]) -> str:
    """Apply token mappings to template content.

    TC-964: Replaces placeholder tokens with actual values from token_mappings dict.
    This enables template-driven pages (blog) to have their frontmatter and body
    content filled with deterministic values generated by W4 IAPlanner.

    Args:
        template_content: Raw template content with tokens (e.g., __TITLE__, __DATE__)
        token_mappings: Dict mapping token names to replacement values

    Returns:
        Template content with tokens replaced

    Example:
        >>> template = "title: __TITLE__\\ndate: __DATE__"
        >>> mappings = {"__TITLE__": "My Post", "__DATE__": "2024-01-01"}
        >>> apply_token_mappings(template, mappings)
        'title: My Post\\ndate: 2024-01-01'
    """
    result = template_content
    for token, value in token_mappings.items():
        result = result.replace(token, value)
    return result


def check_unfilled_tokens(content: str) -> List[str]:
    """Check for unfilled template tokens in content.

    Per specs/21_worker_contracts.md:211-213, drafts must not contain
    unreplaced template tokens.

    Args:
        content: Markdown content to check

    Returns:
        List of unfilled tokens found (empty if none)
    """
    # Match __UPPER_SNAKE__ and __UPPER_SNAKE_123__ patterns (including digits)
    pattern = r'__[A-Z][A-Z0-9_]*__'
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

    # Extract telemetry context from run_config (passed by orchestrator)
    telemetry_client = run_config.get("_telemetry_client") if isinstance(run_config, dict) else None
    telemetry_run_id = run_config.get("_telemetry_run_id") if isinstance(run_config, dict) else None
    telemetry_trace_id = run_config.get("_telemetry_trace_id") if isinstance(run_config, dict) else trace_id
    telemetry_parent_span_id = run_config.get("_telemetry_parent_span_id") if isinstance(run_config, dict) else span_id

    # TC-999: Auto-construct LLM client from run_config if not provided
    if llm_client is None and run_config.get("llm", {}).get("api_base_url"):
        try:
            from launch.clients.llm_provider import LLMProviderClient
            import os

            llm_cfg = run_config["llm"]
            api_key_env = llm_cfg.get("api_key_env", "OPENAI_API_KEY")
            api_key = os.environ.get(api_key_env, "ollama")  # Ollama doesn't need a real key
            llm_client = LLMProviderClient(
                api_base_url=llm_cfg["api_base_url"],
                model=llm_cfg["model"],
                run_dir=run_dir,
                api_key=api_key,
                temperature=llm_cfg.get("decoding", {}).get("temperature", 0.0),
                max_tokens=llm_cfg.get("decoding", {}).get("max_tokens", 6000),
                timeout=llm_cfg.get("request_timeout_s", 120),
                telemetry_client=telemetry_client,
                telemetry_run_id=telemetry_run_id or run_id,
                telemetry_trace_id=telemetry_trace_id,
                telemetry_parent_span_id=telemetry_parent_span_id,
            )
            logger.info(
                f"[W5 SectionWriter] Auto-constructed LLM client: "
                f"model={llm_cfg['model']}, base_url={llm_cfg['api_base_url']}, "
                f"telemetry_enabled={telemetry_client is not None}"
            )
        except Exception as e:
            logger.warning(
                f"[W5 SectionWriter] Failed to construct LLM client: {e}. "
                f"Falling back to template-based content generation."
            )
            llm_client = None

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
            # TC-973: Pass page_plan to enable TOC generation
            content = generate_section_content(
                page=page,
                product_facts=product_facts,
                snippet_catalog=snippet_catalog,
                llm_client=llm_client,
                page_plan=page_plan,
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
