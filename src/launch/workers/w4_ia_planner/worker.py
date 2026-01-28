"""TC-430: W4 IAPlanner worker implementation.

This module implements the W4 IAPlanner that generates a comprehensive page plan
(information architecture) for documentation content before any writing occurs.

W4 IAPlanner performs:
1. Load product_facts.json from TC-410 (W2 FactsBuilder)
2. Load snippet_catalog.json from TC-420 (W3 SnippetCurator)
3. Load ruleset and run configuration
4. Determine launch tier based on repository quality signals
5. Generate page plan with URLs, titles, sections, and content assignments
6. Emit events and write page_plan.json artifact

Output artifacts:
- page_plan.json (schema-validated per specs/schemas/page_plan.schema.json)

Spec references:
- specs/06_page_planning.md (Page planning algorithm)
- specs/21_worker_contracts.md:157-176 (W4 IAPlanner contract)
- specs/10_determinism_and_caching.md (Stable output requirements)
- specs/11_state_and_events.md (Event emission)
- specs/33_public_url_mapping.md (URL path computation)

TC-430: W4 IAPlanner
"""

from __future__ import annotations

import datetime
import hashlib
import json
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

from ...io.run_layout import RunLayout
from ...models.event import (
    Event,
    EVENT_WORK_ITEM_STARTED,
    EVENT_WORK_ITEM_FINISHED,
    EVENT_ARTIFACT_WRITTEN,
    EVENT_ISSUE_OPENED,
    EVENT_RUN_FAILED,
)
from ...models.run_config import RunConfig
from ...io.run_config import load_and_validate_run_config
from ...io.atomic import atomic_write_json
from ...util.logging import get_logger

logger = get_logger()


class IAPlannerError(Exception):
    """Base exception for W4 IAPlanner errors."""
    pass


class IAPlannerPlanIncompleteError(IAPlannerError):
    """Insufficient evidence to meet minimum page requirements."""
    pass


class IAPlannerURLCollisionError(IAPlannerError):
    """URL path collision detected."""
    pass


class IAPlannerValidationError(IAPlannerError):
    """Page plan validation failed."""
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


def load_product_facts(artifacts_dir: Path) -> Dict[str, Any]:
    """Load product_facts.json from artifacts directory.

    Args:
        artifacts_dir: Path to artifacts directory

    Returns:
        Product facts dictionary

    Raises:
        IAPlannerError: If product_facts.json is missing or invalid
    """
    product_facts_path = artifacts_dir / "product_facts.json"
    if not product_facts_path.exists():
        raise IAPlannerError(f"Missing required artifact: {product_facts_path}")

    try:
        with open(product_facts_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise IAPlannerError(f"Invalid JSON in product_facts.json: {e}")


def load_snippet_catalog(artifacts_dir: Path) -> Dict[str, Any]:
    """Load snippet_catalog.json from artifacts directory.

    Args:
        artifacts_dir: Path to artifacts directory

    Returns:
        Snippet catalog dictionary

    Raises:
        IAPlannerError: If snippet_catalog.json is missing or invalid
    """
    snippet_catalog_path = artifacts_dir / "snippet_catalog.json"
    if not snippet_catalog_path.exists():
        raise IAPlannerError(f"Missing required artifact: {snippet_catalog_path}")

    try:
        with open(snippet_catalog_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise IAPlannerError(f"Invalid JSON in snippet_catalog.json: {e}")


def determine_launch_tier(
    product_facts: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
    run_config: RunConfig,
) -> Tuple[str, List[Dict[str, str]]]:
    """Determine launch tier based on repository quality signals.

    Per specs/06_page_planning.md:116-139, the launch tier is determined by:
    - Explicit config override (if provided)
    - Repository health signals (CI, tests, examples, docs)
    - Evidence quality (contradictions, phantom paths)

    Args:
        product_facts: Product facts dictionary
        snippet_catalog: Snippet catalog dictionary
        run_config: Run configuration

    Returns:
        Tuple of (launch_tier, adjustments_log)
        where launch_tier is one of: minimal, standard, rich
        and adjustments_log is a list of adjustment records
    """
    adjustments = []

    # Start with config-specified tier or default to standard
    if hasattr(run_config, 'launch_tier') and run_config.launch_tier:
        tier = run_config.launch_tier
        adjustments.append({
            "adjustment": "unchanged",
            "reason": f"Explicit launch_tier specified in run_config: {tier}",
            "signal": "config_override"
        })
    else:
        tier = "standard"
        adjustments.append({
            "adjustment": "unchanged",
            "from_tier": "standard",
            "to_tier": "standard",
            "reason": "Default launch tier (no explicit config)",
            "signal": "default"
        })

    # Get repository health signals
    repo_health = product_facts.get("repository_health", {})
    example_roots = product_facts.get("example_inventory", {}).get("example_roots", [])
    doc_roots = product_facts.get("doc_roots", [])
    contradictions = product_facts.get("contradictions", [])
    phantom_paths = product_facts.get("phantom_paths", [])

    # Tier reduction signals (per specs/06_page_planning.md:126-130)
    original_tier = tier

    # Force minimal if contradictions are unresolved
    if contradictions:
        tier = "minimal"
        adjustments.append({
            "adjustment": "reduced",
            "from_tier": original_tier,
            "to_tier": tier,
            "reason": f"Contradictions detected ({len(contradictions)} unresolved)",
            "signal": "contradictions_detected"
        })
        original_tier = tier

    # Reduce by one level if CI is missing
    if not repo_health.get("ci_present", False):
        new_tier = "minimal" if tier == "standard" else ("standard" if tier == "rich" else tier)
        if new_tier != tier:
            adjustments.append({
                "adjustment": "reduced",
                "from_tier": tier,
                "to_tier": new_tier,
                "reason": "CI not present in repository",
                "signal": "ci_absent"
            })
            tier = new_tier

    # Reduce by one level if phantom paths detected
    if phantom_paths:
        new_tier = "minimal" if tier == "standard" else ("standard" if tier == "rich" else tier)
        if new_tier != tier:
            adjustments.append({
                "adjustment": "reduced",
                "from_tier": tier,
                "to_tier": new_tier,
                "reason": f"Phantom paths detected ({len(phantom_paths)} paths)",
                "signal": "phantom_paths_detected"
            })
            tier = new_tier

    # Force minimal if no examples and only generated snippets
    snippets = snippet_catalog.get("snippets", [])
    has_real_snippets = any(s.get("source", {}).get("type") == "repo_file" for s in snippets)
    if not example_roots and not has_real_snippets:
        if tier != "minimal":
            adjustments.append({
                "adjustment": "reduced",
                "from_tier": tier,
                "to_tier": "minimal",
                "reason": "No example_roots and only generated snippets",
                "signal": "no_real_examples"
            })
            tier = "minimal"

    # Tier elevation signals (per specs/06_page_planning.md:120-124)
    # Only elevate if not already at max and no previous reductions
    if tier == "standard" and len([a for a in adjustments if a["adjustment"] == "reduced"]) == 0:
        elevation_signals = []
        if repo_health.get("ci_present", False):
            elevation_signals.append("ci_present")
        if repo_health.get("tests_present", False):
            test_count = repo_health.get("test_file_count", 0)
            if test_count > 10:
                elevation_signals.append("tests_present")
        if example_roots:
            elevation_signals.append("validated_examples")
        if doc_roots:
            elevation_signals.append("structured_docs")

        # Elevate to rich if we have 3+ elevation signals
        if len(elevation_signals) >= 3:
            adjustments.append({
                "adjustment": "elevated",
                "from_tier": tier,
                "to_tier": "rich",
                "reason": f"Strong quality signals: {', '.join(elevation_signals)}",
                "signal": "quality_signals"
            })
            tier = "rich"

    return tier, adjustments


def infer_product_type(product_facts: Dict[str, Any]) -> str:
    """Infer product type from product facts.

    Per specs/06_page_planning.md:110-115, product type determines
    heading and content emphasis.

    Args:
        product_facts: Product facts dictionary

    Returns:
        One of: cli, sdk, library, service, plugin, tool, other
    """
    # Check positioning and claims for hints
    positioning = product_facts.get("positioning", {})
    short_desc = positioning.get("short_description", "").lower()
    tagline = positioning.get("tagline", "").lower()

    # CLI indicators
    if any(word in short_desc or word in tagline for word in ["command-line", "cli", "command line"]):
        return "cli"

    # Service indicators
    if any(word in short_desc or word in tagline for word in ["service", "api", "rest", "endpoint"]):
        return "service"

    # SDK/library indicators (most common for Aspose products)
    if any(word in short_desc or word in tagline for word in ["sdk", "library", "api", "package"]):
        # Distinguish SDK vs library based on platform support
        platforms = product_facts.get("supported_platforms", [])
        if len(platforms) > 1:
            return "sdk"
        return "library"

    # Default to library for code-based products
    return "library"


def compute_url_path(
    section: str,
    slug: str,
    product_slug: str,
    platform: str = "python",
    locale: str = "en",
) -> str:
    """Compute canonical URL path per specs/33_public_url_mapping.md.

    For V2 layout with default language (en), the URL format is:
    /<family>/<platform>/<section_path>/<slug>/

    Args:
        section: Section name (products, docs, reference, kb, blog)
        slug: Page slug
        product_slug: Product family slug (e.g., "cells", "words")
        platform: Platform (e.g., "python", "java")
        locale: Language code (default: "en")

    Returns:
        Canonical URL path with leading and trailing slashes
    """
    # Per specs/33_public_url_mapping.md:64-66, for default language (en),
    # locale is dropped and platform appears after family
    parts = [product_slug, platform]

    # Add section if not at root
    if section != "products":
        parts.append(section)

    parts.append(slug)

    # Build path with leading and trailing slashes
    url_path = "/" + "/".join(parts) + "/"
    return url_path


def compute_output_path(
    section: str,
    slug: str,
    product_slug: str,
    subdomain: str = "docs.aspose.org",
    platform: str = "python",
    locale: str = "en",
) -> str:
    """Compute content file path relative to site repo root.

    For V2 layout:
    content/<subdomain>/<family>/<locale>/<platform>/<section>/<slug>.md

    Args:
        section: Section name
        slug: Page slug
        product_slug: Product family slug
        subdomain: Hugo site subdomain
        platform: Platform
        locale: Language code

    Returns:
        Content file path relative to site repo root
    """
    if section == "products":
        # Products section uses platform root
        return f"content/{subdomain}/{product_slug}/{locale}/{platform}/{slug}.md"
    else:
        return f"content/{subdomain}/{product_slug}/{locale}/{platform}/{section}/{slug}.md"


def plan_pages_for_section(
    section: str,
    launch_tier: str,
    product_facts: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
    product_slug: str,
    platform: str = "python",
) -> List[Dict[str, Any]]:
    """Plan pages for a single section based on launch tier.

    Per specs/06_page_planning.md:94-108, page counts vary by tier:
    - minimal: 1-2 pages per section
    - standard: 2-5 pages per section
    - rich: 5+ pages per section (evidence-grounded)

    Args:
        section: Section name (products, docs, reference, kb, blog)
        launch_tier: Launch tier (minimal, standard, rich)
        product_facts: Product facts dictionary
        snippet_catalog: Snippet catalog dictionary
        product_slug: Product family slug
        platform: Platform identifier

    Returns:
        List of page specification dictionaries
    """
    pages = []
    claims = product_facts.get("claims", [])
    claim_groups = product_facts.get("claim_groups", [])
    snippets = snippet_catalog.get("snippets", [])
    workflows = product_facts.get("workflows", [])

    # Get available snippet tags
    snippet_tags = sorted(set(tag for s in snippets for tag in s.get("tags", [])))

    if section == "products":
        # Products section: overview/landing page
        slug = "overview"
        title = f"{product_facts.get('product_name', 'Product')} Overview"
        purpose = "Product overview and positioning"

        # Select claims for overview (positioning, features)
        overview_claim_ids = [
            c["claim_id"] for c in claims[:10]  # Take first 10 claims
            if c.get("claim_group", "").lower() in ["positioning", "features", "overview"]
        ]

        pages.append({
            "section": section,
            "slug": slug,
            "output_path": compute_output_path(section, slug, product_slug, platform=platform),
            "url_path": compute_url_path(section, slug, product_slug, platform=platform),
            "title": title,
            "purpose": purpose,
            "template_variant": launch_tier,
            "required_headings": ["Overview", "Key Features", "Supported Platforms", "Getting Started"],
            "required_claim_ids": overview_claim_ids[:5] if launch_tier == "minimal" else overview_claim_ids,
            "required_snippet_tags": snippet_tags[:2] if snippet_tags else [],
            "cross_links": [],  # Will be populated after all pages are planned
            "seo_keywords": [product_slug, platform, "overview"],
            "forbidden_topics": []
        })

    elif section == "docs":
        # Docs section: how-to guides based on workflows
        max_pages = 1 if launch_tier == "minimal" else (3 if launch_tier == "standard" else 5)

        # Create getting-started page
        pages.append({
            "section": section,
            "slug": "getting-started",
            "output_path": compute_output_path(section, "getting-started", product_slug, platform=platform),
            "url_path": compute_url_path(section, "getting-started", product_slug, platform=platform),
            "title": "Getting Started",
            "purpose": "Installation and basic usage guide",
            "template_variant": launch_tier,
            "required_headings": ["Installation", "Basic Usage", "Prerequisites", "Next Steps"],
            "required_claim_ids": [c["claim_id"] for c in claims[:3]],
            "required_snippet_tags": snippet_tags[:1] if snippet_tags else [],
            "cross_links": [],
            "seo_keywords": [product_slug, platform, "getting started"],
            "forbidden_topics": []
        })

        # Create workflow-based guides
        for i, workflow in enumerate(workflows[:max_pages - 1]):
            slug = workflow.get("workflow_id", f"guide-{i+1}").lower().replace("_", "-")
            title = workflow.get("name", f"Guide {i+1}")

            # Find claims related to this workflow
            workflow_claim_ids = [
                c["claim_id"] for c in claims
                if workflow.get("workflow_id") in c.get("claim_group", "")
            ][:5]

            pages.append({
                "section": section,
                "slug": slug,
                "output_path": compute_output_path(section, slug, product_slug, platform=platform),
                "url_path": compute_url_path(section, slug, product_slug, platform=platform),
                "title": title,
                "purpose": workflow.get("description", f"How-to guide for {title}"),
                "template_variant": launch_tier,
                "required_headings": ["Overview", "Steps", "Example", "Troubleshooting"],
                "required_claim_ids": workflow_claim_ids,
                "required_snippet_tags": snippet_tags[:2] if snippet_tags else [],
                "cross_links": [],
                "seo_keywords": [product_slug, platform, slug],
                "forbidden_topics": []
            })

    elif section == "reference":
        # Reference section: API overview
        slug = "api-overview"
        api_summary = product_facts.get("api_surface_summary", {})

        pages.append({
            "section": section,
            "slug": slug,
            "output_path": compute_output_path(section, slug, product_slug, platform=platform),
            "url_path": compute_url_path(section, slug, product_slug, platform=platform),
            "title": "API Reference Overview",
            "purpose": "High-level API surface overview",
            "template_variant": launch_tier,
            "required_headings": ["Overview", "Key Modules", "Core Classes", "Usage Patterns"],
            "required_claim_ids": [c["claim_id"] for c in claims if "api" in c.get("claim_group", "").lower()][:5],
            "required_snippet_tags": snippet_tags[:1] if snippet_tags else [],
            "cross_links": [],
            "seo_keywords": [product_slug, platform, "api", "reference"],
            "forbidden_topics": []
        })

        # For standard/rich tiers, add module pages
        if launch_tier in ["standard", "rich"]:
            modules = api_summary.get("key_modules", [])[:2 if launch_tier == "standard" else 3]
            for module in modules:
                slug = module.lower().replace(".", "-")
                pages.append({
                    "section": section,
                    "slug": slug,
                    "output_path": compute_output_path(section, slug, product_slug, platform=platform),
                    "url_path": compute_url_path(section, slug, product_slug, platform=platform),
                    "title": f"{module} Module",
                    "purpose": f"Reference documentation for {module}",
                    "template_variant": launch_tier,
                    "required_headings": ["Overview", "Classes", "Methods", "Examples"],
                    "required_claim_ids": [],
                    "required_snippet_tags": snippet_tags[:1] if snippet_tags else [],
                    "cross_links": [],
                    "seo_keywords": [product_slug, platform, module],
                    "forbidden_topics": []
                })

    elif section == "kb":
        # KB section: FAQ, troubleshooting, limitations
        pages.append({
            "section": "kb",
            "slug": "faq",
            "output_path": compute_output_path("kb", "faq", product_slug, platform=platform),
            "url_path": compute_url_path("kb", "faq", product_slug, platform=platform),
            "title": "Frequently Asked Questions",
            "purpose": "Common questions and answers",
            "template_variant": launch_tier,
            "required_headings": ["Installation", "Usage", "Troubleshooting"],
            "required_claim_ids": [],
            "required_snippet_tags": [],
            "cross_links": [],
            "seo_keywords": [product_slug, platform, "faq"],
            "forbidden_topics": []
        })

        if launch_tier in ["standard", "rich"]:
            pages.append({
                "section": "kb",
                "slug": "troubleshooting",
                "output_path": compute_output_path("kb", "troubleshooting", product_slug, platform=platform),
                "url_path": compute_url_path("kb", "troubleshooting", product_slug, platform=platform),
                "title": "Troubleshooting Guide",
                "purpose": "Common issues and solutions",
                "template_variant": launch_tier,
                "required_headings": ["Installation Issues", "Runtime Errors", "Performance"],
                "required_claim_ids": [],
                "required_snippet_tags": [],
                "cross_links": [],
                "seo_keywords": [product_slug, platform, "troubleshooting"],
                "forbidden_topics": []
            })

            pages.append({
                "section": "kb",
                "slug": "limitations",
                "output_path": compute_output_path("kb", "limitations", product_slug, platform=platform),
                "url_path": compute_url_path("kb", "limitations", product_slug, platform=platform),
                "title": "Known Limitations",
                "purpose": "Known limitations and workarounds",
                "template_variant": launch_tier,
                "required_headings": ["Overview", "Platform Limitations", "Workarounds"],
                "required_claim_ids": [],
                "required_snippet_tags": [],
                "cross_links": [],
                "seo_keywords": [product_slug, platform, "limitations"],
                "forbidden_topics": []
            })

    elif section == "blog":
        # Blog section: announcement post
        pages.append({
            "section": "blog",
            "slug": "announcement",
            "output_path": compute_output_path("blog", "announcement", product_slug, platform=platform),
            "url_path": compute_url_path("blog", "announcement", product_slug, platform=platform),
            "title": f"Announcing {product_facts.get('product_name', 'Product')}",
            "purpose": "Product announcement and highlights",
            "template_variant": launch_tier,
            "required_headings": ["Introduction", "Key Features", "Getting Started", "Next Steps"],
            "required_claim_ids": [c["claim_id"] for c in claims[:5]],
            "required_snippet_tags": snippet_tags[:1] if snippet_tags else [],
            "cross_links": [],
            "seo_keywords": [product_slug, platform, "announcement"],
            "forbidden_topics": []
        })

    return pages


def add_cross_links(pages: List[Dict[str, Any]]) -> None:
    """Add cross-links between pages per specs/06_page_planning.md:31-35.

    Cross-linking rules:
    - docs → reference
    - kb → docs
    - blog → products

    Args:
        pages: List of page specifications (modified in place)
    """
    # Build lookup by section
    by_section = {}
    for page in pages:
        section = page["section"]
        if section not in by_section:
            by_section[section] = []
        by_section[section].append(page)

    # Add cross-links per rules
    for page in pages:
        section = page["section"]

        if section == "docs":
            # Link to reference pages
            if "reference" in by_section:
                page["cross_links"] = [p["url_path"] for p in by_section["reference"][:2]]

        elif section == "kb":
            # Link to docs pages
            if "docs" in by_section:
                page["cross_links"] = [p["url_path"] for p in by_section["docs"][:2]]

        elif section == "blog":
            # Link to products page
            if "products" in by_section:
                page["cross_links"] = [p["url_path"] for p in by_section["products"][:1]]


def check_url_collisions(pages: List[Dict[str, Any]]) -> List[str]:
    """Check for URL path collisions.

    Per specs/06_page_planning.md:75-83, if multiple pages resolve to the
    same url_path, this is a blocker error.

    Args:
        pages: List of page specifications

    Returns:
        List of error messages (empty if no collisions)
    """
    url_to_pages = {}
    for page in pages:
        url_path = page["url_path"]
        if url_path not in url_to_pages:
            url_to_pages[url_path] = []
        url_to_pages[url_path].append(page["output_path"])

    errors = []
    for url_path, output_paths in url_to_pages.items():
        if len(output_paths) > 1:
            errors.append(
                f"URL collision: {url_path} maps to multiple pages: {', '.join(output_paths)}"
            )

    return errors


def validate_page_plan(page_plan: Dict[str, Any]) -> None:
    """Validate page plan against schema requirements.

    Args:
        page_plan: Page plan dictionary

    Raises:
        IAPlannerValidationError: If validation fails
    """
    # Check required top-level fields
    required_fields = ["schema_version", "product_slug", "launch_tier", "pages"]
    for field in required_fields:
        if field not in page_plan:
            raise IAPlannerValidationError(f"Missing required field: {field}")

    # Check launch_tier is valid
    if page_plan["launch_tier"] not in ["minimal", "standard", "rich"]:
        raise IAPlannerValidationError(f"Invalid launch_tier: {page_plan['launch_tier']}")

    # Check pages is a list
    if not isinstance(page_plan["pages"], list):
        raise IAPlannerValidationError("pages must be a list")

    # Validate each page
    for i, page in enumerate(page_plan["pages"]):
        required_page_fields = [
            "section", "slug", "output_path", "url_path", "title", "purpose",
            "required_headings", "required_claim_ids", "required_snippet_tags", "cross_links"
        ]
        for field in required_page_fields:
            if field not in page:
                raise IAPlannerValidationError(f"Page {i}: missing required field: {field}")

        # Check section is valid
        if page["section"] not in ["products", "docs", "reference", "kb", "blog"]:
            raise IAPlannerValidationError(f"Page {i}: invalid section: {page['section']}")


def execute_ia_planner(
    run_dir: Path,
    run_config: Dict[str, Any],
    llm_client: Optional[Any] = None,
) -> Dict[str, Any]:
    """Execute W4 IAPlanner worker.

    Generates a comprehensive page plan (information architecture) for
    documentation content based on product facts and snippet catalog.

    Per specs/06_page_planning.md and specs/21_worker_contracts.md:157-176.

    Args:
        run_dir: Path to run directory
        run_config: Run configuration dictionary
        llm_client: Optional LLM client (not used in initial heuristic implementation)

    Returns:
        Dictionary containing:
        - status: "success" or "failed"
        - artifact_path: Path to generated page_plan.json
        - page_count: Number of pages planned
        - launch_tier: Final launch tier

    Raises:
        IAPlannerError: If planning fails
        IAPlannerPlanIncompleteError: If insufficient evidence for required sections
        IAPlannerURLCollisionError: If URL collisions detected
    """
    run_layout = RunLayout(run_dir=run_dir)
    run_id = run_config.get("run_id", "unknown")
    trace_id = str(uuid.uuid4())
    span_id = str(uuid.uuid4())

    logger.info(f"[W4 IAPlanner] Starting page planning for run {run_id}")

    # Emit start event
    emit_event(
        run_layout=run_layout,
        run_id=run_id,
        trace_id=trace_id,
        span_id=span_id,
        event_type=EVENT_WORK_ITEM_STARTED,
        payload={"worker": "w4_ia_planner", "phase": "page_planning"},
    )

    try:
        # Load input artifacts
        product_facts = load_product_facts(run_layout.artifacts_dir)
        snippet_catalog = load_snippet_catalog(run_layout.artifacts_dir)

        # Load run config as model if it exists
        config_path = run_dir / "run_config.yaml"
        if config_path.exists():
            run_config_obj = load_and_validate_run_config(config_path)
        else:
            # Use a simple object with just the fields we need
            class MinimalRunConfig:
                def __init__(self, launch_tier=None):
                    self.launch_tier = launch_tier

            run_config_obj = MinimalRunConfig(
                launch_tier=run_config.get("launch_tier")
            )

        # Determine launch tier
        launch_tier, adjustments = determine_launch_tier(
            product_facts=product_facts,
            snippet_catalog=snippet_catalog,
            run_config=run_config_obj,
        )

        logger.info(f"[W4 IAPlanner] Launch tier: {launch_tier} (after {len(adjustments)} adjustments)")

        # Infer product type
        product_type = infer_product_type(product_facts)
        logger.info(f"[W4 IAPlanner] Inferred product type: {product_type}")

        # Get product slug and platform
        product_slug = product_facts.get("product_slug", "product")
        # Assume Python platform for now (can be extracted from run_config later)
        platform = "python"

        # Plan pages for each section
        all_pages = []
        sections = ["products", "docs", "reference", "kb", "blog"]

        for section in sections:
            section_pages = plan_pages_for_section(
                section=section,
                launch_tier=launch_tier,
                product_facts=product_facts,
                snippet_catalog=snippet_catalog,
                product_slug=product_slug,
                platform=platform,
            )
            all_pages.extend(section_pages)
            logger.info(f"[W4 IAPlanner] Planned {len(section_pages)} pages for section: {section}")

        # Add cross-links between pages
        add_cross_links(all_pages)

        # Sort pages deterministically per specs/10_determinism_and_caching.md:43
        # Sort by (section_order, output_path)
        section_order = {"products": 0, "docs": 1, "reference": 2, "kb": 3, "blog": 4}
        all_pages.sort(key=lambda p: (section_order.get(p["section"], 99), p["output_path"]))

        # Check for URL collisions
        collision_errors = check_url_collisions(all_pages)
        if collision_errors:
            error_msg = "; ".join(collision_errors)
            logger.error(f"[W4 IAPlanner] URL collisions detected: {error_msg}")

            # Emit issue
            emit_event(
                run_layout=run_layout,
                run_id=run_id,
                trace_id=trace_id,
                span_id=span_id,
                event_type=EVENT_ISSUE_OPENED,
                payload={
                    "issue_id": "plan_url_collision",
                    "error_code": "IA_PLANNER_URL_COLLISION",
                    "severity": "blocker",
                    "message": error_msg,
                    "files": [p["output_path"] for p in all_pages],
                },
            )

            raise IAPlannerURLCollisionError(error_msg)

        # Build final page plan
        page_plan = {
            "schema_version": "1.0",
            "product_slug": product_slug,
            "launch_tier": launch_tier,
            "launch_tier_adjustments": adjustments,
            "inferred_product_type": product_type,
            "pages": all_pages,
        }

        # Validate page plan
        validate_page_plan(page_plan)

        # Write artifact
        artifact_path = run_layout.artifacts_dir / "page_plan.json"
        atomic_write_json(artifact_path, page_plan)

        logger.info(f"[W4 IAPlanner] Wrote page plan: {artifact_path} ({len(all_pages)} pages)")

        # Emit artifact written event
        emit_event(
            run_layout=run_layout,
            run_id=run_id,
            trace_id=trace_id,
            span_id=span_id,
            event_type=EVENT_ARTIFACT_WRITTEN,
            payload={
                "artifact": "page_plan.json",
                "path": str(artifact_path),
                "page_count": len(all_pages),
                "launch_tier": launch_tier,
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
                "worker": "w4_ia_planner",
                "phase": "page_planning",
                "status": "success",
                "page_count": len(all_pages),
            },
        )

        return {
            "status": "success",
            "artifact_path": str(artifact_path),
            "page_count": len(all_pages),
            "launch_tier": launch_tier,
        }

    except Exception as e:
        logger.error(f"[W4 IAPlanner] Planning failed: {e}")

        # Emit failure event
        emit_event(
            run_layout=run_layout,
            run_id=run_id,
            trace_id=trace_id,
            span_id=span_id,
            event_type=EVENT_RUN_FAILED,
            payload={
                "worker": "w4_ia_planner",
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )

        raise
