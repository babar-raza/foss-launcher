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
import re
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

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
from ...models.run_config import RunConfig
from ...io.run_config import load_and_validate_run_config
from ...io.atomic import atomic_write_json
from ...io.yamlio import load_yaml
from ...util.logging import get_logger
from ...resolvers.public_urls import build_absolute_public_url

logger = get_logger()


def assign_page_role(section: str, slug: str, is_index: bool = False) -> str:
    """Assign page role based on section, slug, and type.

    Implements content distribution strategy from specs/08_content_distribution_strategy.md.

    Args:
        section: Section name (products, docs, reference, kb, blog)
        slug: Page slug
        is_index: True if this is an index/TOC page (_index.md)

    Returns:
        Page role string (landing, toc, comprehensive_guide, workflow_page,
        feature_showcase, troubleshooting, api_reference)
    """
    # TOC page detection (docs section index)
    if is_index and section == "docs":
        return "toc"

    # Comprehensive guide detection (developer-guide pages)
    if slug == "developer-guide" or slug.endswith("/developer-guide"):
        return "comprehensive_guide"

    # Landing page detection (products overview, blog posts)
    if slug in ["overview", "index", "_index"] and section == "products":
        return "landing"

    # Section-specific role assignment
    if section == "docs":
        return "workflow_page"

    if section == "kb":
        # TC-977: FAQ should not have troubleshooting role (avoids forbidden topics like "installation")
        if slug == "faq":
            return "landing"  # Landing role allows installation content

        # Feature showcase detection (how-to, howto, or showcase in slug)
        # TC-993: "howto" matches new KB template filenames (howto.variant-*.md)
        if "how-to" in slug or "howto" in slug or "showcase" in slug:
            return "feature_showcase"
        return "troubleshooting"

    if section == "reference":
        return "api_reference"

    if section == "blog":
        return "landing"

    # Default fallback
    return "landing"


def build_content_strategy(
    page_role: str,
    section: str,
    workflows: List[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build content distribution strategy based on page role.

    Implements content strategy rules from specs/08_content_distribution_strategy.md.

    Args:
        page_role: Page role (landing, toc, comprehensive_guide, etc.)
        section: Section name (products, docs, reference, kb, blog)
        workflows: List of workflows from product_facts (needed for comprehensive_guide)

    Returns:
        Content strategy dictionary with primary_focus, forbidden_topics,
        claim_quota (min/max), child_pages (for toc), scenario_coverage (for comprehensive_guide)
    """
    if workflows is None:
        workflows = []

    strategy = {}

    # Landing page (products)
    if page_role == "landing" and section == "products":
        strategy = {
            "primary_focus": "Product positioning",
            "forbidden_topics": ["detailed_api", "troubleshooting"],
            "claim_quota": {"min": 5, "max": 10},
        }

    # TOC page
    elif page_role == "toc":
        strategy = {
            "primary_focus": "Navigation hub",
            "forbidden_topics": ["duplicate_child_content", "code_snippets"],
            "claim_quota": {"min": 0, "max": 2},
            "child_pages": [],  # Will be populated by post-processing
        }

    # Comprehensive guide
    elif page_role == "comprehensive_guide":
        strategy = {
            "primary_focus": "All usage scenarios",
            "forbidden_topics": ["installation", "troubleshooting"],
            "claim_quota": {"min": len(workflows), "max": 50},
            "scenario_coverage": "all",
        }

    # Workflow page
    elif page_role == "workflow_page":
        strategy = {
            "primary_focus": "How-to guide",
            "forbidden_topics": ["other_workflows"],
            "claim_quota": {"min": 3, "max": 8},
        }

    # Feature showcase
    elif page_role == "feature_showcase":
        strategy = {
            "primary_focus": "Prominent feature how-to",
            "forbidden_topics": ["general_features", "api_reference", "other_features"],
            "claim_quota": {"min": 3, "max": 8},
        }

    # Troubleshooting
    elif page_role == "troubleshooting":
        strategy = {
            "primary_focus": "Problem-solution",
            "forbidden_topics": ["features", "installation"],
            "claim_quota": {"min": 1, "max": 5},
        }

    # Landing page (blog)
    elif page_role == "landing" and section == "blog":
        strategy = {
            "primary_focus": "Synthesized overview",
            "forbidden_topics": [],
            "claim_quota": {"min": 10, "max": 20},
        }

    # Default fallback (minimal strategy)
    else:
        strategy = {
            "primary_focus": f"{section} page content",
            "forbidden_topics": [],
            "claim_quota": {"min": 1, "max": 10},
        }

    return strategy


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


def load_product_facts(artifacts_dir: Path) -> Dict[str, Any]:
    """Load product_facts.json from artifacts directory.

    TC-1033: Delegates to ArtifactStore.load_artifact for centralized I/O.

    Args:
        artifacts_dir: Path to artifacts directory

    Returns:
        Product facts dictionary

    Raises:
        IAPlannerError: If product_facts.json is missing or invalid
    """
    store = ArtifactStore(run_dir=artifacts_dir.parent)
    try:
        return store.load_artifact("product_facts.json", validate_schema=False)
    except FileNotFoundError:
        raise IAPlannerError(f"Missing required artifact: {artifacts_dir / 'product_facts.json'}")
    except json.JSONDecodeError as e:
        raise IAPlannerError(f"Invalid JSON in product_facts.json: {e}")


def load_snippet_catalog(artifacts_dir: Path) -> Dict[str, Any]:
    """Load snippet_catalog.json from artifacts directory.

    TC-1033: Delegates to ArtifactStore.load_artifact for centralized I/O.

    Args:
        artifacts_dir: Path to artifacts directory

    Returns:
        Snippet catalog dictionary

    Raises:
        IAPlannerError: If snippet_catalog.json is missing or invalid
    """
    store = ArtifactStore(run_dir=artifacts_dir.parent)
    try:
        return store.load_artifact("snippet_catalog.json", validate_schema=False)
    except FileNotFoundError:
        raise IAPlannerError(f"Missing required artifact: {artifacts_dir / 'snippet_catalog.json'}")
    except json.JSONDecodeError as e:
        raise IAPlannerError(f"Invalid JSON in snippet_catalog.json: {e}")


def load_ruleset(repo_root: Path = None) -> Dict[str, Any]:
    """Load full ruleset from ruleset.v1.yaml.

    TC-984: Loads the complete ruleset dict for use by load_and_merge_page_requirements()
    and other config-driven functions.

    Args:
        repo_root: Path to repository root (auto-detected from worker location if None)

    Returns:
        Full ruleset dictionary

    Raises:
        IAPlannerError: If ruleset is missing or invalid
    """
    if repo_root is None:
        repo_root = Path(__file__).parent.parent.parent.parent.parent

    ruleset_path = repo_root / "specs" / "rulesets" / "ruleset.v1.yaml"
    if not ruleset_path.exists():
        raise IAPlannerError(f"Missing ruleset: {ruleset_path}")

    try:
        ruleset = load_yaml(ruleset_path)
        return ruleset
    except Exception as e:
        raise IAPlannerError(f"Failed to load ruleset: {e}")


def load_ruleset_quotas(repo_root: Path = None) -> Dict[str, Dict[str, int]]:
    """Load page quotas from ruleset.v1.yaml.

    Per specs/01_system_contract.md and specs/rulesets/, the ruleset defines
    per-section page quotas (min_pages, max_pages) that guide page planning.

    Args:
        repo_root: Path to repository root (auto-detected from worker location if None)

    Returns:
        Dictionary mapping section names to quota dictionaries with min_pages/max_pages keys

    Raises:
        IAPlannerError: If ruleset is missing or invalid
    """
    if repo_root is None:
        # Auto-detect repo root from this file's location
        # src/launch/workers/w4_ia_planner/worker.py -> go up 5 levels to reach repo root
        repo_root = Path(__file__).parent.parent.parent.parent.parent

    ruleset_path = repo_root / "specs" / "rulesets" / "ruleset.v1.yaml"
    if not ruleset_path.exists():
        raise IAPlannerError(f"Missing ruleset: {ruleset_path}")

    try:
        ruleset = load_yaml(ruleset_path)
        sections_config = ruleset.get("sections", {})

        # Extract quotas for each section
        quotas = {}
        for section, config in sections_config.items():
            quotas[section] = {
                "min_pages": config.get("min_pages", 1),
                "max_pages": config.get("max_pages", 10),
            }

        logger.info(f"[W4 IAPlanner] Loaded section quotas from ruleset: {quotas}")
        return quotas

    except Exception as e:
        raise IAPlannerError(f"Failed to load ruleset: {e}")


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
    # Handle run_config as either dict or object (TC-925 robustness)
    if isinstance(run_config, dict):
        tier = run_config.get('launch_tier')
    else:
        tier = getattr(run_config, 'launch_tier', None)

    if tier:
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
    example_inventory = product_facts.get("example_inventory", {})
    # Handle case where example_inventory might be a list or dict (d582eca fix)
    if isinstance(example_inventory, dict):
        example_roots = example_inventory.get("example_roots", [])
    else:
        example_roots = []
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

    # TC-984: Soften CI-absent tier reduction per specs/06_page_planning.md
    # "CI-absent tier reduction softening" (TC-983, binding):
    # Only reduce when BOTH CI and tests are absent.
    # If CI absent but tests present, log adjustment but keep tier.
    ci_present = repo_health.get("ci_present", False)
    tests_present = repo_health.get("tests_present", False)
    if not ci_present and not tests_present:
        new_tier = "minimal" if tier == "standard" else ("standard" if tier == "rich" else tier)
        if new_tier != tier:
            adjustments.append({
                "adjustment": "reduced",
                "from_tier": tier,
                "to_tier": new_tier,
                "reason": "Both CI and tests absent in repository",
                "signal": "ci_and_tests_absent"
            })
            tier = new_tier
    elif not ci_present and tests_present:
        adjustments.append({
            "adjustment": "unchanged",
            "from_tier": tier,
            "to_tier": tier,
            "reason": "CI absent but tests present, keeping tier",
            "signal": "ci_absent_tests_present"
        })

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


def load_and_merge_page_requirements(
    ruleset: Dict[str, Any],
    product_slug: str,
) -> Dict[str, Dict[str, Any]]:
    """Load and merge mandatory page requirements from ruleset + family overrides.

    Per specs/06_page_planning.md "Configurable Page Requirements (TC-983)":
    1. Reads mandatory_pages + optional_page_policies from ruleset sections
    2. Reads family_overrides for product_slug (if exists)
    3. Merges: global mandatory_pages UNION family mandatory_pages (deduplicate by slug)
    4. Returns per-section merged config

    Merge logic (binding per spec):
    - Global mandatory_pages form the base list
    - Family override mandatory_pages are UNIONED (not replaced)
    - If a slug already exists in global list, the family entry is skipped (dedup by slug)

    Spec references:
    - specs/06_page_planning.md lines 261-283 (Configurable Page Requirements)
    - specs/rulesets/ruleset.v1.yaml (mandatory_pages, optional_page_policies, family_overrides)
    - specs/schemas/ruleset.schema.json ($defs/sectionMinPages, family_overrides)

    Args:
        ruleset: Loaded ruleset dictionary (from ruleset.v1.yaml)
        product_slug: Product family slug (e.g., "3d", "cells", "note")

    Returns:
        Dict mapping section_name to:
            {"mandatory_pages": [...], "optional_page_policies": [...]}
        Each mandatory_pages entry has: {"slug": str, "page_role": str}
        Each optional_page_policies entry has: {"page_role": str, "source": str, "priority": int}
    """
    sections_config = ruleset.get("sections", {})
    family_overrides = ruleset.get("family_overrides", {})

    merged = {}

    for section_name, section_cfg in sorted(sections_config.items()):
        # Load global mandatory pages for this section
        global_mandatory = list(section_cfg.get("mandatory_pages", []))
        global_policies = list(section_cfg.get("optional_page_policies", []))

        # Track existing slugs for deduplication
        existing_slugs = set(p["slug"] for p in global_mandatory)

        # Check for family overrides
        family_cfg = family_overrides.get(product_slug, {})
        family_section_cfg = family_cfg.get("sections", {}).get(section_name, {})

        if family_section_cfg:
            # UNION family mandatory_pages with global (dedup by slug)
            family_mandatory = family_section_cfg.get("mandatory_pages", [])
            for page_entry in family_mandatory:
                if page_entry["slug"] not in existing_slugs:
                    global_mandatory.append(page_entry)
                    existing_slugs.add(page_entry["slug"])
                else:
                    logger.debug(
                        f"[W4] Family override slug '{page_entry['slug']}' already in global "
                        f"mandatory_pages for section '{section_name}', skipping"
                    )

            # UNION family optional_page_policies (append, no dedup needed)
            family_policies = family_section_cfg.get("optional_page_policies", [])
            global_policies.extend(family_policies)

        merged[section_name] = {
            "mandatory_pages": global_mandatory,
            "optional_page_policies": global_policies,
        }

    logger.info(
        f"[W4 IAPlanner] Merged page requirements for '{product_slug}': "
        + ", ".join(
            f"{s}={len(v['mandatory_pages'])}m+{len(v['optional_page_policies'])}p"
            for s, v in sorted(merged.items())
        )
    )

    return merged


def _resolve_claim_ids_for_group(product_facts: dict, group_key: str) -> set:
    """Resolve claim IDs belonging to a claim_group key using top-level claim_groups dict.

    product_facts.claim_groups is a dict like {"key_features": ["c1","c2"], "install_steps": ["c3"]}.
    This function returns all claim_ids whose group key partially matches the given group_key.

    TC-1010: Individual claim objects do NOT have a 'claim_group' field.
    Grouping is stored at TOP LEVEL in product_facts["claim_groups"].

    Args:
        product_facts: Product facts dictionary with top-level claim_groups dict
        group_key: The group key to look up (e.g. "key_features", "install_steps",
                   or a workflow_id like "load_and_convert")

    Returns:
        Set of claim_id strings belonging to matching groups. Empty set if no match.
    """
    claim_groups = product_facts.get("claim_groups", {})
    if not isinstance(claim_groups, dict):
        return set()
    result = set()
    for key, ids in claim_groups.items():
        if group_key in key or key in group_key:
            if isinstance(ids, list):
                result.update(ids)
    return result


def compute_evidence_volume(
    product_facts: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
) -> Dict[str, int]:
    """Compute evidence volume metrics from product_facts and snippet_catalog.

    Per specs/06_page_planning.md "Step 0: Compute evidence volume" (TC-983):
    quality_score = (claim_count * 2) + (snippet_count * 3) + (api_symbol_count * 1)

    Note: claim_groups is a TOP-LEVEL dict in product_facts mapping group names
    to lists of claim_id strings. It is NOT a per-claim field.

    Spec references:
    - specs/06_page_planning.md lines 289-301 (evidence_volume computation)
    - specs/schemas/page_plan.schema.json (evidence_volume property)

    Args:
        product_facts: Product facts dictionary with claims, claim_groups,
                       workflows, api_surface_summary
        snippet_catalog: Snippet catalog dictionary with snippets list

    Returns:
        Dict with keys: total_score, claim_count, snippet_count,
        api_symbol_count, workflow_count, key_feature_count
    """
    claims = product_facts.get("claims", [])
    snippets = snippet_catalog.get("snippets", [])
    api_summary = product_facts.get("api_surface_summary", {})
    workflows = product_facts.get("workflows", [])
    # claim_groups is a TOP-LEVEL dict, NOT a per-claim field (per MEMORY.md)
    claim_groups = product_facts.get("claim_groups", {})
    if not isinstance(claim_groups, dict):
        claim_groups = {}

    claim_count = len(claims)
    snippet_count = len(snippets)
    # api_symbol_count: sum of lengths of all list-valued entries in api_summary
    api_symbol_count = sum(
        len(v) for v in api_summary.values() if isinstance(v, list)
    )
    workflow_count = len(workflows)
    key_feature_count = len(claim_groups.get("key_features", []))

    total_score = (claim_count * 2) + (snippet_count * 3) + (api_symbol_count * 1)

    evidence = {
        "total_score": total_score,
        "claim_count": claim_count,
        "snippet_count": snippet_count,
        "api_symbol_count": api_symbol_count,
        "workflow_count": workflow_count,
        "key_feature_count": key_feature_count,
    }

    logger.info(f"[W4 IAPlanner] Evidence volume: {evidence}")
    return evidence


def compute_effective_quotas(
    evidence_volume: Dict[str, int],
    launch_tier: str,
    section_quotas: Dict[str, Dict[str, int]],
    merged_requirements: Dict[str, Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """Compute effective per-section quotas from evidence volume and tier.

    Per specs/06_page_planning.md "Step 1.5: Compute effective quotas" (TC-983):
    - Tier scaling coefficients: minimal=0.3, standard=0.7, rich=1.0
    - Evidence-based section targets computed per section
    - Effective max = clamp(evidence_target, min_pages, tier_adjusted_max)

    Spec references:
    - specs/06_page_planning.md lines 306-316 (effective quotas)
    - specs/schemas/page_plan.schema.json (effective_quotas property)

    Args:
        evidence_volume: Dict from compute_evidence_volume()
        launch_tier: Final launch tier (minimal, standard, rich)
        section_quotas: Dict from load_ruleset_quotas() with min_pages/max_pages
        merged_requirements: Dict from load_and_merge_page_requirements()

    Returns:
        Dict mapping section name to:
            {"min_pages": int, "max_pages": int (effective),
             "evidence_target": int, "tier_adjusted_max": int}
    """
    tier_coefficients = {"minimal": 0.3, "standard": 0.7, "rich": 1.0}
    coefficient = tier_coefficients.get(launch_tier, 0.7)

    effective = {}

    for section, quota in sorted(section_quotas.items()):
        min_pages = quota.get("min_pages", 1)
        max_pages = quota.get("max_pages", 10)

        # Tier-adjusted max: at least min_pages
        tier_adjusted_max = max(min_pages, int(max_pages * coefficient))

        # Get mandatory page count for this section
        section_req = merged_requirements.get(section, {})
        mandatory_count = len(section_req.get("mandatory_pages", []))

        # Compute evidence-based targets per section
        # Per specs/06_page_planning.md lines 309-314
        if section == "products":
            evidence_target = 1
        elif section == "docs":
            evidence_target = mandatory_count + evidence_volume.get("workflow_count", 0)
        elif section == "reference":
            evidence_target = 1 + evidence_volume.get("api_symbol_count", 0) // 3
        elif section == "kb":
            evidence_target = mandatory_count + min(
                evidence_volume.get("key_feature_count", 0), 5
            )
        elif section == "blog":
            evidence_target = 1 + (1 if evidence_volume.get("total_score", 0) > 200 else 0)
        else:
            evidence_target = min_pages

        # Clamp: effective_max = clamp(evidence_target, min_pages, tier_adjusted_max)
        effective_max = max(min_pages, min(evidence_target, tier_adjusted_max))

        effective[section] = {
            "min_pages": min_pages,
            "max_pages": effective_max,
            "evidence_target": evidence_target,
            "tier_adjusted_max": tier_adjusted_max,
        }

    logger.info(
        f"[W4 IAPlanner] Effective quotas (tier={launch_tier}): "
        + ", ".join(
            f"{s}={v['max_pages']}" for s, v in sorted(effective.items())
        )
    )

    return effective


def generate_optional_pages(
    section: str,
    mandatory_page_count: int,
    effective_max: int,
    product_facts: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
    product_slug: str,
    launch_tier: str,
    optional_page_policies: List[Dict[str, Any]],
    platform: str = "",  # DEPRECATED: ignored, kept for backward compat
) -> List[Dict[str, Any]]:
    """Generate optional pages from evidence using policy-driven candidate selection.

    Per specs/06_page_planning.md "Optional Page Selection Algorithm" (TC-983):
    1. Compute N = effective_max - mandatory_page_count
    2. Generate candidates from each optional_page_policy source
    3. Score each candidate: quality_score = (claim_count * 2) + (snippet_count * 3)
    4. Sort by (priority asc, quality_score desc, slug asc) -- DETERMINISTIC
    5. Select top N candidates

    Each candidate is built with the full page spec structure using existing
    helper functions: compute_output_path(), compute_url_path(), assign_page_role(),
    build_content_strategy(), get_subdomain_for_section().

    Spec references:
    - specs/06_page_planning.md lines 285-350 (Optional Page Selection Algorithm)
    - specs/08_content_distribution_strategy.md (content distribution rules)

    Args:
        section: Section name (products, docs, reference, kb, blog)
        mandatory_page_count: Number of mandatory pages already planned
        effective_max: Effective max_pages from compute_effective_quotas()
        product_facts: Product facts dictionary
        snippet_catalog: Snippet catalog dictionary
        product_slug: Product family slug
        launch_tier: Launch tier (minimal, standard, rich)
        optional_page_policies: List of policy dicts from merged config
        platform: DEPRECATED - ignored, kept for backward compatibility

    Returns:
        List of page specification dictionaries (deterministic order)
    """
    N = effective_max - mandatory_page_count
    if N <= 0:
        return []

    claims = product_facts.get("claims", [])
    claim_groups = product_facts.get("claim_groups", {})
    if not isinstance(claim_groups, dict):
        claim_groups = {}
    snippets = snippet_catalog.get("snippets", [])
    workflows = product_facts.get("workflows", [])
    api_summary = product_facts.get("api_surface_summary", {})

    # Build claim lookup for scoring
    snippet_tags_set = set(tag for s in snippets for tag in s.get("tags", []))

    candidates = []

    for policy in optional_page_policies:
        source = policy.get("source", "")
        priority = policy.get("priority", 99)
        page_role = policy.get("page_role", "workflow_page")

        if source == "per_feature":
            # One candidate per key_feature claim
            key_feature_ids = claim_groups.get("key_features", [])
            key_feature_claims = [
                c for c in claims if c.get("claim_id") in set(key_feature_ids)
            ]
            for claim in key_feature_claims:
                claim_text = claim.get("claim_text", "feature")
                raw_slug = claim_text[:40].lower().replace(" ", "-").replace("/", "-")
                sanitized = re.sub(r"[^a-z0-9\-]", "", raw_slug)
                sanitized = re.sub(r"-{2,}", "-", sanitized).strip("-")
                slug = sanitized or "feature"

                # Score: count of claims related to this feature + snippet coverage
                feature_tags = claim.get("tags", [])
                matching_snippets = [
                    s for s in snippets
                    if any(tag in s.get("tags", []) for tag in feature_tags)
                ]
                quality_score = (1 * 2) + (len(matching_snippets) * 3)

                candidates.append({
                    "slug": slug,
                    "page_role": page_role,
                    "priority": priority,
                    "quality_score": quality_score,
                    "title": f"{claim_text[:50]}",
                    "purpose": f"Feature guide for {claim_text[:50]}",
                    "required_claim_ids": sorted([claim["claim_id"]]),
                    "required_snippet_tags": sorted(
                        [feature_tags[0]] if feature_tags else []
                    ),
                })

        elif source == "per_workflow":
            # One candidate per workflow
            for workflow in workflows:
                wf_id = workflow.get("workflow_id", "")
                wf_name = workflow.get("name", wf_id)
                raw_slug = wf_name[:40].lower().replace(" ", "-").replace("/", "-")
                sanitized = re.sub(r"[^a-z0-9\-]", "", raw_slug)
                sanitized = re.sub(r"-{2,}", "-", sanitized).strip("-")
                slug = sanitized or "workflow"

                # TC-1010: Find claims matching this workflow using top-level claim_groups
                wf_claim_ids = _resolve_claim_ids_for_group(product_facts, wf_id)
                matching_claims = [
                    c for c in claims
                    if c.get("claim_id") in wf_claim_ids or wf_id in c.get("tags", [])
                ]
                matching_snippets = [
                    s for s in snippets
                    if wf_id in s.get("tags", [])
                ]
                quality_score = (len(matching_claims) * 2) + (len(matching_snippets) * 3)

                candidates.append({
                    "slug": slug,
                    "page_role": page_role,
                    "priority": priority,
                    "quality_score": quality_score,
                    "title": f"{wf_name[:50]} Guide",
                    "purpose": f"Workflow guide for {wf_name[:50]}",
                    "required_claim_ids": sorted(
                        [c["claim_id"] for c in matching_claims[:5]]
                    ),
                    "required_snippet_tags": sorted(
                        [wf_id] if wf_id else []
                    ),
                })

        elif source == "per_key_feature":
            # One KB showcase per key_feature with snippet coverage
            key_feature_ids = claim_groups.get("key_features", [])
            key_feature_claims = [
                c for c in claims if c.get("claim_id") in set(key_feature_ids)
            ]
            for claim in key_feature_claims:
                claim_text = claim.get("claim_text", "feature")
                feature_tags = claim.get("tags", [])
                matching_snippets = [
                    s for s in snippets
                    if any(tag in s.get("tags", []) for tag in feature_tags)
                ]
                # Only generate if snippet coverage exists
                if not matching_snippets and not snippets:
                    continue

                raw_slug = claim_text[:40].lower().replace(" ", "-").replace("/", "-")
                sanitized = re.sub(r"[^a-z0-9\-]", "", raw_slug)
                sanitized = re.sub(r"-{2,}", "-", sanitized).strip("-")
                slug = f"how-to-{sanitized or 'feature'}"

                quality_score = (1 * 2) + (len(matching_snippets) * 3)

                candidates.append({
                    "slug": slug,
                    "page_role": page_role,
                    "priority": priority,
                    "quality_score": quality_score,
                    "title": f"How to: {claim_text[:50]}",
                    "purpose": f"Feature showcase for {claim_text[:50]}",
                    "required_claim_ids": sorted([claim["claim_id"]]),
                    "required_snippet_tags": sorted(
                        [matching_snippets[0].get("tags", [""])[0]]
                        if matching_snippets else []
                    ),
                })

        elif source == "per_api_symbol":
            # One reference page per API class
            classes = api_summary.get("classes", [])
            for class_name in sorted(classes):
                slug = class_name.lower().replace(".", "-")
                # Find claims mentioning this class
                matching_claims = [
                    c for c in claims
                    if class_name.lower() in c.get("claim_text", "").lower()
                ]
                quality_score = (len(matching_claims) * 2)

                candidates.append({
                    "slug": slug,
                    "page_role": page_role,
                    "priority": priority,
                    "quality_score": quality_score,
                    "title": f"{class_name} Reference",
                    "purpose": f"API reference for {class_name}",
                    "required_claim_ids": sorted(
                        [c["claim_id"] for c in matching_claims[:3]]
                    ),
                    "required_snippet_tags": [],
                })

        elif source == "per_deep_dive":
            # One blog deep-dive if evidence > threshold
            total_score = (
                (len(claims) * 2) + (len(snippets) * 3)
                + sum(len(v) for v in api_summary.values() if isinstance(v, list))
            )
            if total_score > 200:
                candidates.append({
                    "slug": "deep-dive",
                    "page_role": page_role,
                    "priority": priority,
                    "quality_score": total_score,
                    "title": f"Deep Dive: {product_facts.get('product_name', 'Product')}",
                    "purpose": "In-depth technical exploration",
                    "required_claim_ids": sorted(
                        [c["claim_id"] for c in claims[:10]]
                    ),
                    "required_snippet_tags": sorted(
                        list(snippet_tags_set)[:3]
                    ),
                })

    # Sort by (priority asc, quality_score desc, slug asc) -- DETERMINISTIC
    # Per specs/06_page_planning.md Step 4
    candidates.sort(key=lambda c: (c["priority"], -c["quality_score"], c["slug"]))

    # Select top N
    selected = candidates[:N]

    # Build full page spec structures
    subdomain = get_subdomain_for_section(section)
    result_pages = []

    for candidate in selected:
        slug = candidate["slug"]
        role = candidate.get("page_role", assign_page_role(section, slug))
        strategy = build_content_strategy(role, section, workflows)

        page_spec = {
            "section": section,
            "slug": slug,
            "output_path": compute_output_path(
                section, slug, product_slug, subdomain=subdomain
            ),
            "url_path": compute_url_path(
                section, slug, product_slug
            ),
            "title": candidate["title"],
            "purpose": candidate["purpose"],
            "template_variant": launch_tier,
            "required_headings": _default_headings_for_role(role),
            "required_claim_ids": candidate.get("required_claim_ids", []),
            "required_snippet_tags": candidate.get("required_snippet_tags", []),
            "cross_links": [],
            "seo_keywords": [product_slug, slug],
            "forbidden_topics": strategy.get("forbidden_topics", []),
            "page_role": role,
            "content_strategy": strategy,
        }
        result_pages.append(page_spec)

    logger.info(
        f"[W4 IAPlanner] Generated {len(result_pages)} optional pages for "
        f"section '{section}' (N={N}, candidates={len(candidates)})"
    )

    return result_pages


def _default_headings_for_role(page_role: str) -> List[str]:
    """Return default required headings based on page role.

    Provides standard heading structure per content distribution strategy.

    Args:
        page_role: Page role string

    Returns:
        List of heading strings
    """
    headings_map = {
        "landing": ["Overview", "Key Features", "Getting Started"],
        "toc": ["Introduction", "Documentation Index"],
        "comprehensive_guide": ["Introduction", "Common Scenarios", "Advanced Scenarios"],
        "workflow_page": ["Overview", "Prerequisites", "Step-by-Step Guide", "Code Example"],
        "feature_showcase": ["Overview", "When to Use", "Step-by-Step Guide", "Code Example"],
        "troubleshooting": ["Common Issues", "Solutions", "Related Links"],
        "api_reference": ["Overview", "Classes", "Methods", "Examples"],
    }
    return headings_map.get(page_role, ["Overview"])


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
    locale: str = "en",
    platform: str = "",  # DEPRECATED: ignored, kept for backward compat
) -> str:
    """Compute canonical URL path per specs/33_public_url_mapping.md.

    Per specs/33_public_url_mapping.md:83-86 and 106:
    - Section is implicit in subdomain (blog.aspose.org, docs.aspose.org, etc.)
    - Section name NEVER appears in URL path
    - URL format: /<family>/<slug>/

    Args:
        section: Section name (products, docs, reference, kb, blog) - used for
                 subdomain determination but NOT included in URL path
        slug: Page slug
        product_slug: Product family slug (e.g., "cells", "words")
        locale: Language code (default: "en")
        platform: DEPRECATED - ignored, kept for backward compatibility

    Returns:
        Canonical URL path with leading and trailing slashes

    Examples:
        compute_url_path("docs", "getting-started", "cells")
        => "/cells/getting-started/"  (NOT /cells/docs/getting-started/)

        compute_url_path("blog", "announcement", "3d")
        => "/3d/announcement/"  (NOT /3d/blog/announcement/)
    """
    # Per specs/33_public_url_mapping.md:83-86, 106:
    # Section is implicit in subdomain, NOT in URL path
    # Format: /<family>/<slug>/
    parts = [product_slug, slug]

    # Build path with leading and trailing slashes
    url_path = "/" + "/".join(parts) + "/"
    return url_path


def get_subdomain_for_section(section: str) -> str:
    """Map section to subdomain per specs/18_site_repo_layout.md.

    Args:
        section: Section name (products, docs, reference, kb, blog)

    Returns:
        Subdomain string (e.g., "products.aspose.org")
    """
    subdomain_map = {
        "products": "products.aspose.org",
        "docs": "docs.aspose.org",
        "reference": "reference.aspose.org",
        "kb": "kb.aspose.org",
        "blog": "blog.aspose.org",
    }
    return subdomain_map.get(section, "docs.aspose.org")


def compute_output_path(
    section: str,
    slug: str,
    product_slug: str,
    subdomain: str = None,
    locale: str = "en",
    platform: str = "",  # DEPRECATED: ignored, kept for backward compat
) -> str:
    """Compute content file path relative to site repo root.

    V1 layout:
    - Non-blog: content/<subdomain>/<family>/<locale>/<section>/<slug>.md
    - Blog: content/blog.aspose.org/<family>/<slug>/index.md (no locale)

    Args:
        section: Section name
        slug: Page slug
        product_slug: Product family slug
        subdomain: Hugo site subdomain (auto-determined from section if None)
        locale: Language code
        platform: DEPRECATED - ignored, kept for backward compatibility

    Returns:
        Content file path relative to site repo root
    """
    # TC-681: Auto-determine subdomain from section if not provided
    if subdomain is None:
        subdomain = get_subdomain_for_section(section)

    # TC-926: Blog posts use special format per specs/18_site_repo_layout.md
    # Path: content/blog.aspose.org/<family>/<slug>/index.md
    # Note: NO locale segment, uses index.md instead of <slug>.md
    if section == "blog":
        # Build path components, skip empty product_slug to avoid double slash
        components = ["content", subdomain]
        if product_slug and product_slug.strip():
            components.append(product_slug)
        components.extend([slug, "index.md"])
        output_path = "/".join(components)
        return output_path

    # TC-926: Handle empty product_slug gracefully (prevent double slashes)
    # Build path components list, skip empty segments
    components = ["content", subdomain]
    if product_slug and product_slug.strip():
        components.append(product_slug)
    components.append(locale)

    if section == "products":
        # Products section uses family root (no section subdirectory)
        components.append(f"{slug}.md")
    else:
        # Other sections (docs, reference, kb) include section subdirectory
        components.extend([section, f"{slug}.md"])

    # Join and return (use / for consistent paths)
    output_path = "/".join(components)
    return output_path


def plan_pages_for_section(
    section: str,
    launch_tier: str,
    product_facts: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
    product_slug: str,
    platform: str = "",  # DEPRECATED: ignored, kept for backward compat
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
        platform: DEPRECATED - ignored, kept for backward compatibility

    Returns:
        List of page specification dictionaries
    """
    pages = []
    claims = product_facts.get("claims", [])
    claim_groups = product_facts.get("claim_groups", {})
    # claim_groups_dict maps group names (e.g. "key_features") to lists of claim_id strings
    claim_groups_dict = claim_groups if isinstance(claim_groups, dict) else {}
    snippets = snippet_catalog.get("snippets", [])
    workflows = product_facts.get("workflows", [])

    # Get available snippet tags
    snippet_tags = sorted(set(tag for s in snippets for tag in s.get("tags", [])))

    if section == "products":
        # Products section: overview/landing page
        slug = "overview"
        product_name = product_facts.get('product_name', '').strip()
        if not product_name:
            product_name = f"Aspose.{product_slug.capitalize()}"
        title = f"{product_name} Overview"
        purpose = "Product overview and positioning"

        # Assign page role and build content strategy
        products_role = assign_page_role("products", slug)
        products_strategy = build_content_strategy(products_role, "products", workflows)

        # Select claims for overview (positioning, features)
        overview_claim_ids = sorted(
            claim_groups_dict.get("key_features", []) +
            claim_groups_dict.get("install_steps", [])
        )[:10]

        subdomain = get_subdomain_for_section(section)
        pages.append({
            "section": section,
            "slug": slug,
            "output_path": compute_output_path(section, slug, product_slug, subdomain=subdomain),
            "url_path": compute_url_path(section, slug, product_slug),
            "title": title,
            "purpose": purpose,
            "template_variant": launch_tier,
            "required_headings": ["Overview", "Key Features", "Supported Platforms", "Getting Started"],
            "required_claim_ids": overview_claim_ids[:5] if launch_tier == "minimal" else overview_claim_ids,
            "required_snippet_tags": snippet_tags[:2] if snippet_tags else [],
            "cross_links": [],  # Will be populated after all pages are planned
            "seo_keywords": [product_slug, "overview"],
            "forbidden_topics": products_strategy.get("forbidden_topics", []),
            "page_role": products_role,
            "content_strategy": products_strategy,
        })

    elif section == "docs":
        # Docs section: TOC + getting-started + developer-guide (comprehensive)
        # Per TC-972: Create exactly 3 pages with proper page_role and content_strategy

        # Page 1: TOC (_index.md) - Navigation hub
        toc_role = assign_page_role("docs", "_index", is_index=True)
        toc_strategy = build_content_strategy(toc_role, "docs", workflows)
        pages.append({
            "section": section,
            "slug": "_index",
            "output_path": compute_output_path(section, "_index", product_slug),
            "url_path": compute_url_path(section, "_index", product_slug),
            "title": f"{product_facts.get('product_name', 'Product')} Documentation",
            "purpose": "Table of contents and navigation hub",
            "template_variant": launch_tier,
            "required_headings": ["Introduction", "Documentation Index", "Quick Links"],
            "required_claim_ids": [c["claim_id"] for c in claims[:2]],  # Brief intro only
            "required_snippet_tags": [],  # No code on TOC
            "cross_links": [],
            "seo_keywords": [product_slug, "documentation"],
            "forbidden_topics": toc_strategy.get("forbidden_topics", []),
            "page_role": toc_role,
            "content_strategy": toc_strategy,
        })

        # Page 2: Getting Started - Installation and first task
        gs_role = assign_page_role("docs", "getting-started")
        gs_strategy = build_content_strategy(gs_role, "docs", workflows)

        # TC-1010: Select install and quickstart claims using top-level claim_groups
        install_claim_ids = set()
        for group_name in ["install_steps", "quickstart_steps", "installation", "quickstart"]:
            install_claim_ids.update(_resolve_claim_ids_for_group(product_facts, group_name))
        install_quickstart_claims = [
            c["claim_id"] for c in claims
            if c.get("claim_id") in install_claim_ids
        ][:5]

        pages.append({
            "section": section,
            "slug": "getting-started",
            "output_path": compute_output_path(section, "getting-started", product_slug),
            "url_path": compute_url_path(section, "getting-started", product_slug),
            "title": "Getting Started",
            "purpose": "Installation instructions and first task guide",
            "template_variant": launch_tier,
            "required_headings": ["Installation", "Basic Usage", "Prerequisites", "Next Steps"],
            "required_claim_ids": install_quickstart_claims if install_quickstart_claims else [c["claim_id"] for c in claims[:3]],
            "required_snippet_tags": snippet_tags[:1] if snippet_tags else [],
            "cross_links": [],
            "seo_keywords": [product_slug, "getting started"],
            "forbidden_topics": gs_strategy.get("forbidden_topics", []),
            "page_role": gs_role,
            "content_strategy": gs_strategy,
        })

        # Page 3: Developer Guide - Comprehensive listing of ALL scenarios
        dg_role = assign_page_role("docs", "developer-guide")
        dg_strategy = build_content_strategy(dg_role, "docs", workflows)

        # Gather one claim per workflow
        workflow_claim_ids = []
        for workflow in workflows:
            wf_id = workflow.get("workflow_id", "")
            # TC-1010: Find first claim matching this workflow using top-level claim_groups
            wf_claim_ids = _resolve_claim_ids_for_group(product_facts, wf_id)
            matching_claims = [
                c["claim_id"] for c in claims
                if c.get("claim_id") in wf_claim_ids or wf_id in c.get("tags", [])
            ]
            if matching_claims:
                workflow_claim_ids.append(matching_claims[0])

        # Fallback: if no workflow-specific claims found, use first N claims
        if not workflow_claim_ids and workflows:
            workflow_claim_ids = [c["claim_id"] for c in claims[:len(workflows)]]

        pages.append({
            "section": section,
            "slug": "developer-guide",
            "output_path": compute_output_path(section, "developer-guide", product_slug),
            "url_path": compute_url_path(section, "developer-guide", product_slug),
            "title": "Developer Guide - All Usage Scenarios",
            "purpose": "Comprehensive listing of all major usage scenarios with source code",
            "template_variant": launch_tier,
            "required_headings": ["Introduction", "Common Scenarios", "Advanced Scenarios", "Additional Resources"],
            "required_claim_ids": workflow_claim_ids,
            "required_snippet_tags": sorted(set(snippet_tags)),  # All snippets
            "cross_links": [],
            "seo_keywords": [product_slug, "developer guide", "scenarios"],
            "forbidden_topics": dg_strategy.get("forbidden_topics", []),
            "page_role": dg_role,
            "content_strategy": dg_strategy,
        })

    elif section == "reference":
        # Reference section: API overview
        slug = "api-overview"
        api_summary = product_facts.get("api_surface_summary", {})

        # Assign page role and build content strategy
        ref_role = assign_page_role("reference", slug)
        ref_strategy = build_content_strategy(ref_role, "reference", workflows)

        pages.append({
            "section": section,
            "slug": slug,
            "output_path": compute_output_path(section, slug, product_slug),
            "url_path": compute_url_path(section, slug, product_slug),
            "title": "API Reference Overview",
            "purpose": "High-level API surface overview",
            "template_variant": launch_tier,
            "required_headings": ["Overview", "Key Modules", "Core Classes", "Usage Patterns"],
            "required_claim_ids": sorted(claim_groups_dict.get("key_features", []))[:5],
            "required_snippet_tags": snippet_tags[:1] if snippet_tags else [],
            "cross_links": [],
            "seo_keywords": [product_slug, "api", "reference"],
            "forbidden_topics": ref_strategy.get("forbidden_topics", []),
            "page_role": ref_role,
            "content_strategy": ref_strategy,
        })

        # For standard/rich tiers, add module pages
        if launch_tier in ["standard", "rich"]:
            modules = api_summary.get("key_modules", [])[:2 if launch_tier == "standard" else 3]
            for module in modules:
                slug = module.lower().replace(".", "-")
                module_role = assign_page_role("reference", slug)
                module_strategy = build_content_strategy(module_role, "reference", workflows)
                pages.append({
                    "section": section,
                    "slug": slug,
                    "output_path": compute_output_path(section, slug, product_slug),
                    "url_path": compute_url_path(section, slug, product_slug),
                    "title": f"{module} Module",
                    "purpose": f"Reference documentation for {module}",
                    "template_variant": launch_tier,
                    "required_headings": ["Overview", "Classes", "Methods", "Examples"],
                    "required_claim_ids": [],
                    "required_snippet_tags": snippet_tags[:1] if snippet_tags else [],
                    "cross_links": [],
                    "seo_keywords": [product_slug, module],
                    "forbidden_topics": module_strategy.get("forbidden_topics", []),
                    "page_role": module_role,
                    "content_strategy": module_strategy,
                })

    elif section == "kb":
        # KB section: Feature showcases (2-3) + troubleshooting (1-2)
        # Per TC-972: Create feature showcase articles for prominent features + troubleshooting pages

        # Feature showcase selection: Get key_features claims with snippet coverage
        key_feature_ids = set(claim_groups_dict.get("key_features", []))
        key_feature_claims = [c for c in claims if c["claim_id"] in key_feature_ids]

        # Determine showcase count based on tier
        showcase_count = 2 if launch_tier == "minimal" else 3

        # Create feature showcase pages
        for i, feature_claim in enumerate(key_feature_claims[:showcase_count]):
            # Generate slug from feature text
            feature_text = feature_claim.get("claim_text", f"feature-{i+1}")
            raw_slug = feature_text[:40].lower().replace(' ', '-').replace('/', '-')
            # Strip characters invalid on Windows (: [ ] < > | * ? ") and collapse runs
            sanitized = re.sub(r'[^a-z0-9\-]', '', raw_slug)
            sanitized = re.sub(r'-{2,}', '-', sanitized).strip('-')
            slug = f"how-to-{sanitized or f'feature-{i+1}'}"

            # Check if snippets exist with matching tags
            feature_tags = feature_claim.get("tags", [])
            matching_snippets = [
                s for s in snippets
                if any(tag in s.get("tags", []) for tag in feature_tags)
            ]

            # Only create showcase if feature has code examples
            if matching_snippets or snippets:  # Fallback to any snippet if no exact match
                showcase_role = assign_page_role("kb", slug)
                showcase_strategy = build_content_strategy(showcase_role, "kb", workflows)

                pages.append({
                    "section": "kb",
                    "slug": slug,
                    "output_path": compute_output_path("kb", slug, product_slug),
                    "url_path": compute_url_path("kb", slug, product_slug),
                    "title": f"How to: {feature_text[:50]}",
                    "purpose": f"Feature showcase for {feature_text[:50]}",
                    "template_variant": launch_tier,
                    "required_headings": ["Overview", "When to Use", "Step-by-Step Guide", "Code Example", "Related Links"],
                    "required_claim_ids": [feature_claim["claim_id"]],  # Single feature focus
                    "required_snippet_tags": [matching_snippets[0].get("tags", [""])[0]] if matching_snippets else (snippet_tags[:1] if snippet_tags else []),
                    "cross_links": [],
                    "seo_keywords": [product_slug, "how-to", slug.replace("how-to-", "")],
                    "forbidden_topics": showcase_strategy.get("forbidden_topics", []),
                    "page_role": showcase_role,
                    "content_strategy": showcase_strategy,
                })

        # Troubleshooting pages
        # FAQ (always created)
        faq_role = assign_page_role("kb", "faq")
        faq_strategy = build_content_strategy(faq_role, "kb", workflows)
        pages.append({
            "section": "kb",
            "slug": "faq",
            "output_path": compute_output_path("kb", "faq", product_slug),
            "url_path": compute_url_path("kb", "faq", product_slug),
            "title": "Frequently Asked Questions",
            "purpose": "Common questions and answers",
            "template_variant": launch_tier,
            "required_headings": ["Installation", "Usage", "Troubleshooting"],
            "required_claim_ids": sorted(
                claim_groups_dict.get("install_steps", []) +
                claim_groups_dict.get("limitations", [])
            )[:5],
            "required_snippet_tags": [],
            "cross_links": [],
            "seo_keywords": [product_slug, "faq"],
            "forbidden_topics": faq_strategy.get("forbidden_topics", []),
            "page_role": faq_role,
            "content_strategy": faq_strategy,
        })

        # Troubleshooting guide (standard/rich tiers only)
        if launch_tier in ["standard", "rich"]:
            ts_role = assign_page_role("kb", "troubleshooting")
            ts_strategy = build_content_strategy(ts_role, "kb", workflows)
            pages.append({
                "section": "kb",
                "slug": "troubleshooting",
                "output_path": compute_output_path("kb", "troubleshooting", product_slug),
                "url_path": compute_url_path("kb", "troubleshooting", product_slug),
                "title": "Troubleshooting Guide",
                "purpose": "Common issues and solutions",
                "template_variant": launch_tier,
                "required_headings": ["Installation Issues", "Runtime Errors", "Performance"],
                "required_claim_ids": [],
                "required_snippet_tags": [],
                "cross_links": [],
                "seo_keywords": [product_slug, "troubleshooting"],
                "forbidden_topics": ts_strategy.get("forbidden_topics", []),
                "page_role": ts_role,
                "content_strategy": ts_strategy,
            })

    elif section == "blog":
        # Blog section: announcement post
        blog_role = assign_page_role("blog", "announcement")
        blog_strategy = build_content_strategy(blog_role, "blog", workflows)

        pages.append({
            "section": "blog",
            "slug": "announcement",
            "output_path": compute_output_path("blog", "announcement", product_slug),
            "url_path": compute_url_path("blog", "announcement", product_slug),
            "title": f"Announcing {product_facts.get('product_name', 'Product')}",
            "purpose": "Product announcement and highlights",
            "template_variant": launch_tier,
            "required_headings": ["Introduction", "Key Features", "Getting Started", "Next Steps"],
            "required_claim_ids": [c["claim_id"] for c in claims[:5]],
            "required_snippet_tags": snippet_tags[:1] if snippet_tags else [],
            "cross_links": [],
            "seo_keywords": [product_slug, "announcement"],
            "forbidden_topics": blog_strategy.get("forbidden_topics", []),
            "page_role": blog_role,
            "content_strategy": blog_strategy,
        })

    return pages


def add_cross_links(
    pages: List[Dict[str, Any]],
    product_slug: str = "3d",
    platform: str = "",  # DEPRECATED: ignored, kept for backward compat
) -> None:
    """Add cross-links between pages per specs/06_page_planning.md:31-35.

    Cross-linking rules:
    - docs → reference
    - kb → docs
    - blog → products

    TC-1001: Cross-links now use absolute URLs (https://...) via build_absolute_public_url
    for correct cross-subdomain navigation.

    Args:
        pages: List of page specifications (modified in place)
        product_slug: Product family slug (e.g., "3d", "cells")
        platform: DEPRECATED - ignored, kept for backward compatibility
    """
    # Build lookup by section
    by_section = {}
    for page in pages:
        section = page["section"]
        if section not in by_section:
            by_section[section] = []
        by_section[section].append(page)

    # Add cross-links per rules using absolute URLs (TC-1001)
    for page in pages:
        section = page["section"]

        if section == "docs":
            # Link to reference pages
            if "reference" in by_section:
                page["cross_links"] = [
                    build_absolute_public_url(
                        section=p["section"],
                        family=product_slug,
                        locale="en",
                        slug=p["slug"],
                    )
                    for p in by_section["reference"][:2]
                ]

        elif section == "kb":
            # Link to docs pages
            if "docs" in by_section:
                page["cross_links"] = [
                    build_absolute_public_url(
                        section=p["section"],
                        family=product_slug,
                        locale="en",
                        slug=p["slug"],
                    )
                    for p in by_section["docs"][:2]
                ]

        elif section == "blog":
            # Link to products page
            if "products" in by_section:
                page["cross_links"] = [
                    build_absolute_public_url(
                        section=p["section"],
                        family=product_slug,
                        locale="en",
                        slug=p["slug"],
                    )
                    for p in by_section["products"][:1]
                ]


def check_url_collisions(pages: List[Dict[str, Any]]) -> List[str]:
    """Check for URL path collisions.

    Per specs/06_page_planning.md:75-83, if multiple pages resolve to the
    same url_path, this is a blocker error.

    TC-969: Collision detection must account for sections (subdomains).
    Pages on different subdomains (docs.aspose.org vs blog.aspose.org) can
    have the same URL path without collision since sections are implicit in subdomain.

    Args:
        pages: List of page specifications

    Returns:
        List of error messages (empty if no collisions)
    """
    # TC-969: Key by (section, url_path) to allow same paths on different subdomains
    url_to_pages = {}
    for page in pages:
        section = page["section"]
        url_path = page["url_path"]
        key = (section, url_path)  # Section determines subdomain
        if key not in url_to_pages:
            url_to_pages[key] = []
        url_to_pages[key].append(page["output_path"])

    errors = []
    for (section, url_path), output_paths in url_to_pages.items():
        if len(output_paths) > 1:
            errors.append(
                f"URL collision in section '{section}': {url_path} maps to multiple pages: {', '.join(output_paths)}"
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


def _derive_page_role_from_template(
    filename: str, relative_path: str, section: str
) -> str:
    """Derive page_role from template filename prefix and path context.

    TC-993: Per specs/21_worker_contracts.md binding requirement for page_role derivation.

    Rules:
      _index* → context-dependent (toc/landing/comprehensive_guide/workflow_page)
      index*  → landing (blog posts)
      feature* → workflow_page
      howto*  → feature_showcase
      reference* (under reference section) → api_reference
      installation*, license* → workflow_page
    """
    slug = filename.replace(".md", "")
    if ".variant-" in slug:
        slug = slug.split(".variant-")[0]

    # Normalize path separators
    rel_parts = relative_path.replace("\\", "/").split("/")
    # Concrete parent dirs (not placeholders, not the filename itself)
    concrete_parents = [
        p for p in rel_parts[:-1]
        if not p.startswith("__") and p
    ]

    if slug == "_index" or slug == "index":
        if "developer-guide" in concrete_parents:
            return "comprehensive_guide"
        if concrete_parents:
            # Subsection _index (e.g., getting-started/_index.md) → workflow_page
            return "workflow_page"
        # Root-level _index
        if section == "docs":
            return "toc"
        return "landing"

    if slug.startswith("feature"):
        return "workflow_page"
    if slug.startswith("howto"):
        return "feature_showcase"
    if slug.startswith("reference") and section == "reference":
        return "api_reference"
    if slug in ("installation", "license"):
        return "workflow_page"

    # Fallback to section-level assignment
    return assign_page_role(section, slug)


def enumerate_templates(
    template_dir: Path,
    subdomain: str,
    family: str,
    locale: str,
    platform: str = "",  # DEPRECATED: ignored, kept for backward compat
) -> List[Dict[str, Any]]:
    """Enumerate templates from specs/templates/ hierarchy.

    Walks the template directory and discovers all template files,
    returning a deterministic list of template descriptors.

    Args:
        template_dir: Root template directory (specs/templates)
        subdomain: Subdomain (e.g., docs.aspose.org, blog.aspose.org)
        family: Product family (e.g., cells, words)
        locale: Language code (e.g., en, es)
        platform: DEPRECATED - ignored, kept for backward compatibility

    Returns:
        List of template descriptors with deterministic ordering
    """
    templates = []

    # Search from family level to discover all templates in placeholder or literal directories
    # The rglob("*.md") below will recursively find templates in any nested structure:
    # - __LOCALE__/*.md
    # - __POST_SLUG__/*.md
    # This fixes the bug where we searched for literal "en/" dirs that don't exist
    search_root = template_dir / subdomain / family

    if not search_root.exists():
        logger.debug(f"[W4] Template directory not found: {search_root}")
        return []

    # Walk directory tree and find all .md files
    templates_discovered = list(search_root.rglob("*.md"))

    # TC-967: Filter out README files and templates with placeholder filenames
    # Placeholder directories are OK (needed for path structure), but filenames must be concrete
    # to prevent URL collisions like /3d/python/__REFERENCE_SLUG__/
    import re
    placeholder_pattern = re.compile(r'__[A-Z_]+__')

    templates_to_process = []
    for template_path in templates_discovered:
        # Skip README files
        if template_path.name == "README.md":
            continue

        # TC-967: Filter out templates with placeholder filenames
        # Check FILENAME only (not full path) to allow placeholder directories
        filename = template_path.name
        if placeholder_pattern.search(filename):
            logger.debug(
                f"[W4] Skipping template with placeholder filename: {template_path.relative_to(search_root)}"
            )
            continue

        templates_to_process.append(template_path)

    # Process filtered templates
    for template_path in templates_to_process:
        path_str = str(template_path)

        # Skip obsolete templates with __PLATFORM__ placeholder (V2 removed)
        if "__PLATFORM__" in path_str:
            logger.debug(f"[W4] Skipping obsolete template with __PLATFORM__: {path_str}")
            continue

        # HEAL-BUG4: Skip obsolete blog templates with __LOCALE__ folder structure
        # Per specs/33_public_url_mapping.md:100, blog uses filename-based i18n (no locale folder)
        if subdomain == "blog.aspose.org":
            if "__LOCALE__" in path_str:
                logger.debug(f"[W4] Skipping obsolete blog template with __LOCALE__: {path_str}")
                continue

        # Extract template metadata
        filename = template_path.name
        relative_path = template_path.relative_to(search_root)

        # TC-968: Extract section from subdomain (not directory path)
        # Directory names like __LOCALE__ are placeholders, not sections
        # Section comes from subdomain: docs.aspose.org → "docs"
        section = subdomain.split('.')[0]

        # Extract slug from filename
        slug = filename.replace(".md", "")
        if ".variant-" in slug:
            base_slug, variant = slug.split(".variant-", 1)
            slug = base_slug
        else:
            variant = "default"

        # Handle _index files
        if slug == "_index":
            slug = "index"

        # Extract placeholders from template content
        placeholders = []
        try:
            content = template_path.read_text(encoding="utf-8")
            import re
            placeholders = sorted(set(re.findall(r'__([A-Z_]+)__', content)))
        except Exception:
            pass

        # Determine if mandatory
        is_mandatory = (
            filename == "_index.md" or
            "/mandatory/" in str(template_path) or
            "mandatory: true" in content if 'content' in locals() else False
        )

        # TC-993: Derive page_role from template filename prefix
        # Per specs/21_worker_contracts.md binding requirement
        page_role = _derive_page_role_from_template(
            filename, str(relative_path), section
        )

        templates.append({
            "section": section,
            "template_path": str(template_path),
            "slug": slug,
            "filename": filename,
            "variant": variant,
            "is_mandatory": is_mandatory,
            "placeholders": placeholders,
            "page_role": page_role,
        })

    # Sort deterministically by template_path only
    templates.sort(key=lambda t: t["template_path"])

    return templates


def classify_templates(
    templates: List[Dict[str, Any]],
    launch_tier: str,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Classify templates into mandatory and optional based on launch tier.

    HEAL-BUG2: De-duplicates index pages per section to prevent URL collisions.
    If multiple _index.md variants exist for the same section, only the first
    (alphabetically by template_path) is selected.

    Args:
        templates: List of template descriptors
        launch_tier: Launch tier (minimal, standard, rich)

    Returns:
        Tuple of (mandatory_templates, optional_templates)
    """
    mandatory = []
    optional = []

    # HEAL-BUG2: Track index pages per section to prevent duplicates
    seen_index_pages = {}  # Key: section, Value: template

    # HEAL-BUG2: Sort templates deterministically for consistent variant selection
    # Templates are sorted alphabetically by template_path to ensure the first
    # variant alphabetically is always selected when duplicates exist
    sorted_templates = sorted(templates, key=lambda t: t.get("template_path", ""))

    duplicates_skipped = 0

    for template in sorted_templates:
        slug = template["slug"]
        section = template["section"]

        # HEAL-BUG2: De-duplicate index pages per section
        if slug == "index":
            if section in seen_index_pages:
                logger.debug(f"[W4] Skipping duplicate index page for section '{section}': {template.get('template_path')}")
                duplicates_skipped += 1
                continue
            seen_index_pages[section] = template

        # Classify as mandatory or optional
        if template["is_mandatory"]:
            mandatory.append(template)
        else:
            # Filter optional templates by launch tier variant
            variant = template["variant"]

            if launch_tier == "minimal" and variant in ["minimal", "default"]:
                optional.append(template)
            elif launch_tier == "standard" and variant in ["minimal", "standard", "default"]:
                optional.append(template)
            elif launch_tier == "rich":
                optional.append(template)

    if duplicates_skipped > 0:
        logger.info(f"[W4] De-duplicated {duplicates_skipped} duplicate index pages")

    return mandatory, optional


def select_templates_with_quota(
    mandatory: List[Dict[str, Any]],
    optional: List[Dict[str, Any]],
    max_pages: int,
) -> List[Dict[str, Any]]:
    """Select templates respecting quota while ensuring all mandatory templates.

    Args:
        mandatory: List of mandatory templates
        optional: List of optional templates
        max_pages: Maximum number of pages allowed

    Returns:
        List of selected templates (mandatory + optional up to quota)
    """
    selected = list(mandatory)  # Always include all mandatory

    # Calculate remaining quota
    remaining = max_pages - len(mandatory)

    if remaining > 0:
        # Add optional templates up to quota (deterministic order)
        selected.extend(optional[:remaining])

    return selected


def extract_title_from_template(template_path: str) -> str:
    """Extract title field from template frontmatter.

    TC-963: IAPlanner requires "title" field in page specifications.
    Templates must have YAML frontmatter with a "title" field.

    Args:
        template_path: Path to template file

    Returns:
        Title string from frontmatter, or placeholder if not found

    Raises:
        IAPlannerValidationError: If template has no frontmatter or missing title
    """
    import yaml

    try:
        template_file = Path(template_path)
        content = template_file.read_text(encoding="utf-8")

        # Parse frontmatter (YAML between --- delimiters)
        if content.startswith("---"):
            # Split on --- and take the second part (first is empty)
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter_text = parts[1]
                frontmatter = yaml.safe_load(frontmatter_text)

                if frontmatter and "title" in frontmatter:
                    return frontmatter["title"]
                else:
                    raise IAPlannerValidationError(
                        f"Template {template_path} has frontmatter but missing 'title' field"
                    )
            else:
                raise IAPlannerValidationError(
                    f"Template {template_path} has malformed frontmatter"
                )
        else:
            raise IAPlannerValidationError(
                f"Template {template_path} has no frontmatter (must start with ---)"
            )
    except Exception as e:
        if isinstance(e, IAPlannerValidationError):
            raise
        logger.error(f"[W4] Failed to extract title from template {template_path}: {e}")
        raise IAPlannerValidationError(
            f"Failed to extract title from template {template_path}: {e}"
        )



def _extract_symbols_from_claims(
    product_facts: Dict[str, Any],
    family: str,
) -> Dict[str, str]:
    """Extract API class/symbol names from product_facts claims.

    TC-981: Replaces hardcoded 3D-specific values (Scene, Entity, Node) with
    product-specific class names derived from claim text.

    Strategy:
    1. Find claims whose claim_id appears in api_surface_summary.classes
    2. Extract bold-delimited class names from their claim_text
    3. Rank by frequency of occurrence in the claim text (deterministic tie-break)
    4. Fallback to family-based naming if no API claims found

    Args:
        product_facts: Product facts dictionary with claims and api_surface_summary
        family: Product family slug (e.g., '3d', 'note')

    Returns:
        Dict with keys: key_symbols, popular_classes, signature_class, entry_point
    """
    # Defaults based on family name
    default_class = f"{family.capitalize()}Document"
    defaults = {
        "key_symbols": f"{default_class}, {family.capitalize()}Page",
        "popular_classes": f"{default_class}, {family.capitalize()}Page",
        "signature_class": default_class,
        "entry_point": default_class,
    }

    if not product_facts:
        return defaults

    api_class_ids = set(
        product_facts.get("api_surface_summary", {}).get("classes", [])
    )
    claims = product_facts.get("claims", [])

    if not api_class_ids or not claims:
        return defaults

    # Collect claim texts for claims that match api_surface_summary.classes
    api_claim_texts = [
        c["claim_text"]
        for c in claims
        if c.get("claim_id") in api_class_ids
    ]

    if not api_claim_texts:
        return defaults

    combined_text = " ".join(api_claim_texts)

    # Strategy 1: Extract **BoldName** patterns (markdown bold class names)
    bold_names = re.findall(r"\*\*([A-Z][a-zA-Z]+)\*\*", combined_text)

    # Strategy 2: Extract PascalCase names (multi-word like GlobalTransform)
    pascal_names = re.findall(r"\b([A-Z][a-z]+(?:[A-Z][a-z]*)+)\b", combined_text)

    # Combine unique names, filter out noise words
    noise_words = {
        "NotImplementedError", "PascalCase", "TestClass", "ValueError",
        "TypeError", "AttributeError", "ImportError", "RuntimeError",
        "KeyError", "IndexError", "FileNotFoundError", "IOError",
    }
    unique_names = set()
    for name in bold_names + pascal_names:
        if name not in noise_words:
            unique_names.add(name)

    if not unique_names:
        return defaults

    # Rank by frequency of standalone occurrence in combined text (deterministic)
    # Tie-break: alphabetical sort for stability
    name_counts = {}
    for name in unique_names:
        # Count standalone word occurrences (word boundary match)
        pattern = r"\b" + re.escape(name) + r"\b"
        name_counts[name] = len(re.findall(pattern, combined_text))

    # Sort by (-frequency, name) for deterministic ordering
    ranked_names = sorted(name_counts.keys(), key=lambda n: (-name_counts[n], n))

    # Pick top symbols (up to 4 for popular_classes, up to 3 for key_symbols)
    popular = ", ".join(ranked_names[:4])
    key = ", ".join(ranked_names[:3])

    # Pick the most frequent class as the signature/entry point
    signature_class = ranked_names[0]

    return {
        "key_symbols": key,
        "popular_classes": popular,
        "signature_class": signature_class,
        "entry_point": signature_class,
    }


def generate_content_tokens(
    page_spec: Dict[str, Any],
    section: str,
    family: str,
    locale: str = "en",
    product_facts: Optional[Dict[str, Any]] = None,
    platform: str = "",  # DEPRECATED: ignored, kept for backward compat
) -> Dict[str, str]:
    """Generate content-specific placeholder token values.

    TC-964: For blog templates, creates deterministic token values for
    title, description, author, date, and body content (20 tokens).

    TC-970: Extended to support docs/products/reference/kb templates with
    97 additional tokens including enable flags, metadata, body blocks,
    code blocks, FAQ content, and plugin/product information.

    TC-981: Accepts product_facts to derive product-specific API class names
    instead of hardcoded 3D values. Falls back to family-based naming.

    This function generates all tokens needed to fill template frontmatter
    and body placeholders, ensuring deterministic output for VFV verification.

    Args:
        page_spec: Page specification dict
        section: Section name (e.g., "blog", "docs", "products", "reference", "kb")
        family: Product family (e.g., "3d", "note")
        locale: Language code (default: "en")
        product_facts: Optional product facts dict for deriving API symbols
        platform: DEPRECATED - ignored, kept for backward compatibility

    Returns:
        Dict mapping token names to filled values (20 for blog, 97+ for docs)

    Raises:
        ValueError: If required fields missing from page_spec
    """
    tokens = {}

    # Get slug from page spec
    slug = page_spec.get("slug", "index")

    # Generate product name
    product_name = f"Aspose.{family.capitalize()}"

    # FRONTMATTER TOKENS

    # Generate title from page context
    # For blog index pages, use simple product-focused title
    if slug == "index":
        tokens["__TITLE__"] = f"{product_name} - Documentation and Resources"
    else:
        tokens["__TITLE__"] = f"{product_name} - {slug.replace('-', ' ').title()}"

    # Generate SEO title (max 60 chars)
    tokens["__SEO_TITLE__"] = f"{product_name} | {slug.replace('-', ' ').title()}"

    # Generate description
    tokens["__DESCRIPTION__"] = f"Comprehensive guide and resources for {product_name}. Learn how to use {family} features in your applications."

    # Generate summary
    tokens["__SUMMARY__"] = f"Learn how to use {product_name} for {slug.replace('-', ' ')} with examples and documentation."

    # Generate author (deterministic)
    tokens["__AUTHOR__"] = "Aspose Documentation Team"

    # Generate date (use fixed date for determinism per specs/10_determinism_and_caching.md)
    # NOTE: Per TC-964 requirements, must be deterministic. Using fixed date.
    tokens["__DATE__"] = "2024-01-01"

    # Generate draft status
    tokens["__DRAFT__"] = "false"

    # Generate tags (for YAML list format)
    tokens["__TAG_1__"] = family

    # Generate categories
    tokens["__CATEGORY_1__"] = "documentation"

    # BODY CONTENT TOKENS

    # Generate intro body content
    tokens["__BODY_INTRO__"] = f"Welcome to the {product_name} documentation. This guide provides comprehensive information about using {family} features in your applications."

    # Generate overview body content
    tokens["__BODY_OVERVIEW__"] = f"{product_name} enables developers to work with {family} files programmatically. This section covers the main features and capabilities."

    # Generate code samples body content
    tokens["__BODY_CODE_SAMPLES__"] = f"Below are example code snippets demonstrating common {family} operations. These examples show how to use the {product_name} API effectively."

    # Generate conclusion body content
    tokens["__BODY_CONCLUSION__"] = f"This guide covered the essential features of {product_name}. For more information, explore the additional documentation and API reference materials."

    # Generate optional body sections (for enhanced templates)
    tokens["__BODY_PREREQUISITES__"] = f"To use {product_name}, ensure you have the Aspose.{family.capitalize()} package added to your project."

    tokens["__BODY_STEPS__"] = f"Follow these steps to get started with {product_name} in your application."

    tokens["__BODY_KEY_TAKEAWAYS__"] = f"Key features of {product_name} include comprehensive {family} file support, easy-to-use API, and cross-platform compatibility."

    tokens["__BODY_TROUBLESHOOTING__"] = f"Common issues when using {product_name} include dependency conflicts and configuration errors. Check the documentation for solutions."

    tokens["__BODY_NOTES__"] = f"Additional notes and tips for working with {product_name}."

    tokens["__BODY_SEE_ALSO__"] = f"For more information, see the {product_name} API reference and additional tutorials."

    # TC-970: Docs/Products/Reference/KB tokens
    # Generate 97 additional tokens for documentation templates
    if section in ["docs", "products", "reference", "kb"]:
        # ENABLE FLAGS (boolean string values for Hugo YAML frontmatter)
        tokens["__FAQ_ENABLE__"] = "true"
        tokens["__OVERVIEW_ENABLE__"] = "true"
        tokens["__BODY_ENABLE__"] = "true"
        tokens["__MORE_FORMATS_ENABLE__"] = "true" if section == "products" else "false"
        tokens["__SUBMENU_ENABLE__"] = "false"  # Minimal tier
        tokens["__SUPPORT_AND_LEARNING_ENABLE__"] = "true"
        tokens["__BACK_TO_TOP_ENABLE__"] = "true"
        tokens["__SUPPORT_ENABLE__"] = "true"
        tokens["__SINGLE_ENABLE__"] = "true" if section == "reference" else "false"
        tokens["__TESTIMONIALS_ENABLE__"] = "false"  # Minimal tier
        tokens["__BUTTON_ENABLE__"] = "false"  # Minimal tier

        # HEAD METADATA (complementing existing __SEO_TITLE__ from blog section)
        tokens["__HEAD_TITLE__"] = f"{product_name} - {slug.replace('-', ' ').title()}"
        tokens["__HEAD_DESCRIPTION__"] = f"Learn how to use {product_name} for {slug.replace('-', ' ')}. Comprehensive documentation and API reference."

        # PAGE CONTENT
        tokens["__PAGE_TITLE__"] = slug.replace('-', ' ').title()
        tokens["__PAGE_DESCRIPTION__"] = f"Documentation for {product_name}"
        tokens["__OVERVIEW_TITLE__"] = "Overview"
        tokens["__OVERVIEW_CONTENT__"] = f"This section covers {slug.replace('-', ' ')} in {product_name}. Learn about features, usage, and best practices."
        tokens["__SUBTITLE__"] = f"{slug.replace('-', ' ').title()} Reference"
        tokens["__LINK_TITLE__"] = slug.replace('-', ' ').title()
        tokens["__LINKTITLE__"] = slug.replace('-', ' ').title()

        # BODY BLOCKS (structured content sections)
        tokens["__BODY_API_OVERVIEW__"] = f"The {product_name} API provides comprehensive access to {family} functionality."
        tokens["__BODY_FEATURES__"] = f"Key features include file format support, rendering capabilities, and platform integration."
        tokens["__BODY_GETTING_STARTED__"] = f"To get started with {product_name}, install the package and import the necessary modules."
        tokens["__BODY_EXAMPLES__"] = f"The following examples demonstrate common {family} operations."
        tokens["__BODY_GUIDES__"] = f"Explore detailed guides for working with {family} files in your applications."
        tokens["__BODY_QUICKSTART__"] = f"Quick start guide for {product_name}."
        tokens["__BODY_IN_THIS_SECTION__"] = f"This section covers essential topics for {product_name} development."
        tokens["__BODY_NEXT_STEPS__"] = f"Next, explore advanced features and integration options for {product_name}."
        tokens["__BODY_RELATED_LINKS__"] = f"Related documentation: API reference, tutorials, and examples."
        tokens["__BODY_SUPPORT__"] = f"Get support for {product_name} through documentation, forums, and technical assistance."
        tokens["__BODY_FAQ__"] = f"Frequently asked questions about {product_name}."
        tokens["__BODY_USECASES__"] = f"Common use cases for {product_name}."
        tokens["__BODY_USAGE_SNIPPET__"] = f"Basic usage example for {product_name}."
        tokens["__BODY_SYMPTOMS__"] = f"N/A"

        # BODY BLOCKS (left/right column layout)
        tokens["__BODY_BLOCK_TITLE_LEFT__"] = "Features"
        tokens["__BODY_BLOCK_CONTENT_LEFT__"] = f"{product_name} provides comprehensive {family} file processing capabilities."
        tokens["__BODY_BLOCK_TITLE_RIGHT__"] = "Getting Started"
        tokens["__BODY_BLOCK_CONTENT_RIGHT__"] = f"Install {product_name} via package manager and explore the API documentation to begin development."

        # BODY BLOCKS (reference/API specific)
        # TC-981: Derive class names from product_facts instead of hardcoding 3D values
        symbols = _extract_symbols_from_claims(product_facts, family) if product_facts else _extract_symbols_from_claims(None, family)
        tokens["__BODY_NAMESPACE__"] = f"Aspose.{family.capitalize()}"
        tokens["__BODY_KEY_NAMESPACES__"] = f"Aspose.{family.capitalize()}, Aspose.{family.capitalize()}.{symbols['signature_class']}"
        tokens["__BODY_KEY_SYMBOLS__"] = symbols["key_symbols"]
        tokens["__BODY_POPULAR_CLASSES__"] = symbols["popular_classes"]
        tokens["__BODY_SIGNATURE__"] = f"class {symbols['signature_class']}"
        tokens["__BODY_PARAMETERS__"] = f"No parameters"
        tokens["__BODY_RETURNS__"] = f"Returns a {symbols['signature_class']} object"
        tokens["__BODY_REMARKS__"] = f"Use {symbols['entry_point']} as the entry point for {family} operations."
        tokens["__BODY_PURPOSE__"] = f"Provides {family} file processing functionality"
        tokens["__BODY_CAUSE__"] = f"N/A"
        tokens["__BODY_RESOLUTION__"] = f"Refer to documentation for troubleshooting guidance"

        # CODE BLOCKS (placeholder GitHub gist references - deterministic hash)
        gist_hash = hashlib.md5(f"{family}_{slug}".encode()).hexdigest()[:12]
        tokens["__BODY_BLOCK_GIST_HASH__"] = gist_hash
        tokens["__BODY_BLOCK_GIST_FILE__"] = f"{slug.replace('-', '_')}_example.py"
        tokens["__SINGLE_GIST_HASH__"] = gist_hash
        tokens["__SINGLE_GIST_FILE__"] = f"{slug.replace('-', '_')}_sample.py"
        tokens["__CODESAMPLES__"] = f"Code samples for {product_name} demonstrating {slug.replace('-', ' ')} operations."

        # FAQ CONTENT
        tokens["__FAQ_QUESTION__"] = f"How do I use {product_name} in my project?"
        tokens["__FAQ_ANSWER__"] = f"Install {product_name} via package manager, import the library, and use the API to work with {family} files. See the getting started guide for detailed instructions."

        # PLUGIN/PRODUCT METADATA
        tokens["__PLUGIN_NAME__"] = product_name
        tokens["__PLUGIN_DESCRIPTION__"] = f"{product_name} library - comprehensive {family} file format support"
        tokens["__PLUGIN_PLATFORM__"] = ""
        tokens["__CART_ID__"] = f"aspose-{family}"
        tokens["__PRODUCT_NAME__"] = product_name
        tokens["__REFERENCE_SLUG__"] = slug
        tokens["__TOPIC_SLUG__"] = slug
        tokens["__FAMILY__"] = family
        tokens["__CASE_STUDIES_LINK__"] = f"/case-studies/{family}/"

        # MISC TOKENS
        tokens["__TOKEN__"] = ""  # Generic placeholder - empty string
        tokens["__WEIGHT__"] = "10"  # Default weight for sidebar ordering
        tokens["__SIDEBAR_OPEN__"] = "false"
        tokens["__LOCALE__"] = locale
        tokens["__LASTMOD__"] = "2024-01-01"  # Deterministic date
        tokens["__SECTION_PATH__"] = f"/{section}/"
        tokens["__UPPER_SNAKE__"] = slug.replace('-', '_').upper()
        tokens["__ENHANCED__"] = "false"  # Minimal tier

        # SINGLE PAGE CONTENT (for reference pages)
        tokens["__SINGLE_TITLE__"] = f"{slug.replace('-', ' ').title()} Reference"
        tokens["__SINGLE_CONTENT__"] = f"Detailed reference documentation for {slug.replace('-', ' ')} in {product_name}."

        # TESTIMONIALS (disabled for minimal tier)
        tokens["__TESTIMONIALS_TITLE__"] = "What Developers Say"
        tokens["__TESTIMONIALS_SUBTITLE__"] = "Developer Feedback"
        tokens["__TESTIMONIAL_MESSAGE__"] = f"{product_name} is a powerful library for {family} development."
        tokens["__TESTIMONIAL_POSTER__"] = "Anonymous Developer"

        # TC-998: Products structured section tokens
        tokens["__FEATURES_ENABLE__"] = "true"
        tokens["__FEATURES_TITLE__"] = "Features"
        # Build features from claim_groups (YAML-safe: escape quotes, strip newlines, limit length)
        features_items = []
        if product_facts:
            claim_groups = product_facts.get("claim_groups", {})
            feature_ids = sorted(claim_groups.get("key_features", []))[:5]
            claims_list = product_facts.get("claims", [])
            for cid in feature_ids:
                claim = next((c for c in claims_list if c.get("claim_id") == cid), None)
                if claim:
                    # Sanitize claim_text for YAML: strip newlines, limit length
                    # Use YAML single-quoted strings (only ' needs escaping as '')
                    text = claim.get("claim_text", cid)
                    text = str(text).replace("\n", " ").replace("\r", " ").strip()
                    text = text[:100]  # Limit length for YAML safety
                    text = text.replace("'", "''")  # YAML single-quote escaping
                    features_items.append(f"- '{text}'")
        if not features_items:
            features_items = [
                f"- '{family.upper()} file format support'",
                f"- 'Cross-platform compatibility'",
                f"- 'Comprehensive API for {family} operations'",
            ]
        # Join with \n    so template indent (4 spaces before __FEATURES_ITEMS__)
        # applies to the first item, and subsequent items get matching 4-space indent
        tokens["__FEATURES_ITEMS__"] = ("\n" + "    ").join(features_items)
        tokens["__CODE_EXAMPLES_ENABLE__"] = "true"
        tokens["__CODE_EXAMPLES_TITLE__"] = "Code Examples"
        # YAML-safe: use single-quoted strings, no leading indent (template provides it)
        safe_product_name = product_name.replace("'", "''")
        tokens["__CODE_EXAMPLES__"] = f"- title: 'Getting Started'\n      content: 'Basic usage example for {safe_product_name}.'"
        tokens["__FORMATS_ENABLE__"] = "true" if section == "products" else "false"
        tokens["__FORMATS_TITLE__"] = "Supported Formats"
        tokens["__FORMATS_CONTENT__"] = f"Comprehensive format support for {family} files including import, export, and conversion capabilities."

        # TC-998: Installation/package tokens
        tokens["__BODY_INSTALLATION__"] = f"Install {product_name} via your preferred package manager or download from the official repository."
        tokens["__BODY_PACKAGE_INSTALL__"] = f"pip install aspose-{family}"
        tokens["__BODY_MANUAL_INSTALL__"] = f"Download the latest release from the official repository and install manually."
        tokens["__BODY_VERIFY_INSTALL__"] = f"python -c \"import aspose.{family}; print('Installation verified')\""
        tokens["__BODY_SYSTEM_REQUIREMENTS__"] = f"Python 3.7 or later."
        tokens["__REPO_URL__"] = f"https://github.com/aspose-{family}-foss/Aspose.{family.capitalize()}-FOSS"

        # TC-998: Licensing tokens
        tokens["__BODY_LICENSE_TYPES__"] = f"Free and commercial licensing options are available for {product_name}."
        tokens["__BODY_APPLY_LICENSE__"] = f"Set the license before making any API calls to remove evaluation limitations."
        tokens["__BODY_METERED_LICENSE__"] = f"Metered licensing allows pay-per-use billing for {product_name}."
        tokens["__BODY_EVAL_LIMITATIONS__"] = f"Evaluation mode includes watermarks and processing limits."

        # TC-998: API Reference tokens (must be after symbols extraction at line 2239)
        tokens["__BODY_CONSTRUCTORS__"] = f"class {symbols['signature_class']}()"
        tokens["__BODY_PROPERTIES__"] = f"Properties and attributes of {symbols['signature_class']}"
        tokens["__BODY_METHODS__"] = f"Methods available in {symbols['signature_class']}"
        tokens["__BODY_KEY_MEMBERS__"] = f"Key members: {symbols['key_symbols']}"
        tokens["__BODY_KEY_FEATURES__"] = f"Key features of {product_name}"
        tokens["__BODY_PLATFORM_LIST__"] = "Python, .NET, Java, C++"
        tokens["__CATEGORY_2__"] = "reference"

        # TC-998: Navigation/URL tokens
        tokens["__BODY_REFERENCE_LINKS__"] = f"API Reference for {product_name}"
        tokens["__BODY_POPULAR_GUIDES__"] = "Getting Started, Developer Guide, API Reference"
        tokens["__BODY_POPULAR_TOPICS__"] = "Installation, Configuration, File Conversion"
        tokens["__URL_DEVELOPER_GUIDE__"] = f"/{family}/developer-guide/"
        tokens["__URL_GETTING_STARTED__"] = f"/{family}/getting-started/"
        tokens["__URL_PRODUCTS__"] = f"https://products.aspose.org/{family}/"
        tokens["__URL_KB__"] = f"https://kb.aspose.org/{family}/"
        tokens["__URL_REFERENCE__"] = f"https://reference.aspose.org/{family}/"

        # TC-998: KB-specific tokens
        tokens["__BODY_HOW_TO_USE__"] = f"Step-by-step guide for using {product_name} in your applications."
        tokens["__BODY_COMMON_ISSUES__"] = f"Common issues and solutions when working with {product_name}."
        tokens["__BODY_CONVERTER_LINKS__"] = f"Related conversion guides for {family} file formats."

        # TC-998: Structural tokens
        tokens["__ADVANCED_SCENARIOS_SECTION__"] = f"Advanced usage scenarios for {product_name} including batch processing and custom configurations."
        tokens["__COMMON_SCENARIOS_SECTION__"] = f"Common usage scenarios for {product_name} in everyday development."
        tokens["__CHILD_PAGES_LIST__"] = ""
        tokens["__BODY_USE_CASES__"] = f"Common use cases for {product_name}."

        # TC-998: KB howto digit-containing frontmatter tokens
        tokens["__KEYWORD_1__"] = f"{family}"
        tokens["__KEYWORD_2__"] = f"{product_name}"
        tokens["__KEYWORD_3__"] = f"{family} API"
        for step_num in range(1, 11):
            tokens[f"__STEP_{step_num}__"] = f"Step {step_num}: {product_name} operation {step_num}"

    # TC-974: Add layout and permalink tokens (for Gate 4 compliance)
    # These tokens are required in frontmatter for Hugo site generation
    layout = section if section in ["docs", "products", "reference", "kb", "blog"] else "default"
    tokens["__LAYOUT__"] = layout

    # Get permalink from page_spec if available
    url_path = page_spec.get("url_path", "")
    if url_path:
        tokens["__PERMALINK__"] = url_path
    else:
        tokens["__PERMALINK__"] = f"/{section}/{slug}/"

    return tokens


def fill_template_placeholders(
    template: Dict[str, Any],
    section: str,
    product_slug: str,
    locale: str,
    subdomain: str,
    product_facts: Optional[Dict[str, Any]] = None,
    platform: str = "",  # DEPRECATED: ignored, kept for backward compat
) -> Dict[str, Any]:
    """Fill template placeholders to create page specification.

    TC-981: Accepts product_facts to assign claims and derive product-specific
    tokens for template-driven pages.

    Args:
        template: Template descriptor
        section: Section name
        product_slug: Product family slug
        locale: Language code
        subdomain: Subdomain
        product_facts: Optional product facts dict for claim assignment
        platform: DEPRECATED - ignored, kept for backward compatibility

    Returns:
        Page specification dictionary
    """
    slug = template["slug"]

    # Compute paths
    output_path = compute_output_path(
        section=section,
        slug=slug,
        product_slug=product_slug,
        subdomain=subdomain,
        locale=locale,
    )

    url_path = compute_url_path(
        section=section,
        slug=slug,
        product_slug=product_slug,
        locale=locale,
    )

    # TC-963: Extract title from template frontmatter
    # Required for IAPlanner PagePlan validation
    title = extract_title_from_template(template["template_path"])

    # TC-964: Generate token mappings for template-driven pages
    # This enables W5 SectionWriter to fill template placeholder tokens
    page_spec_base = {
        "section": section,
        "slug": slug,
        "template_path": template["template_path"],
        "template_variant": template["variant"],
        "output_path": output_path,
        "url_path": url_path,
    }

    token_mappings = generate_content_tokens(
        page_spec=page_spec_base,
        section=section,
        family=product_slug,
        locale=locale,
        product_facts=product_facts,
    )

    # TC-972/TC-993: Assign page_role from template descriptor if available,
    # otherwise fallback to assign_page_role
    is_index = slug == "index" or slug == "_index"
    page_role = template.get("page_role") or assign_page_role(section, slug, is_index=is_index)
    content_strategy = build_content_strategy(page_role, section, workflows=[])

    # TC-981: Assign claims from claim_groups to template-driven pages (RC-2)
    # Template pages previously got hardcoded empty required_claim_ids: []
    # TC-VFV: Use EXCLUSIVE claim subsets per section to avoid duplication warnings
    required_claim_ids = []
    if product_facts:
        claim_groups = product_facts.get("claim_groups", {})
        if isinstance(claim_groups, dict):
            key_features = sorted(claim_groups.get("key_features", []))
            install_steps = sorted(claim_groups.get("install_steps", []))
            limitations = sorted(claim_groups.get("limitations", []))

            # TC-VFV: TOC pages get minimal claims (0-2 per spec 08)
            if page_role == "toc":
                required_claim_ids = key_features[:2]
            # Assign EXCLUSIVE claim subsets per section with MAX quotas enforced
            elif section == "products":
                # Products: key_features[2:7], max 5 claims
                required_claim_ids = key_features[2:7][:5]
            elif section == "docs":
                # Docs: key_features[7:12] + install_steps, max 8 claims
                required_claim_ids = (key_features[7:12] + install_steps)[:8]
            elif section == "reference":
                # Reference: key_features[12:14], max 5 claims
                required_claim_ids = key_features[12:17][:5]
            elif section == "kb":
                # KB: install_steps + limitations, max 5 claims
                required_claim_ids = (install_steps + limitations)[:5]
            elif section == "blog":
                # Blog: max 20 claims per spec
                required_claim_ids = (key_features + install_steps)[:20]

    return {
        "section": section,
        "slug": slug,
        "template_path": template["template_path"],
        "template_variant": template["variant"],
        "output_path": output_path,
        "url_path": url_path,
        "title": title,
        "purpose": f"Template-driven {section} page",
        "page_role": page_role,
        "content_strategy": content_strategy,
        "required_headings": [],
        "required_claim_ids": required_claim_ids,
        "required_snippet_tags": [],
        "cross_links": [],
        "token_mappings": token_mappings,
    }


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

        # Load section quotas from ruleset (TC-953)
        # src/launch/workers/w4_ia_planner/worker.py -> go up 5 levels to reach repo root
        repo_root = Path(__file__).parent.parent.parent.parent.parent
        section_quotas = load_ruleset_quotas(repo_root)

        # TC-984: Load full ruleset for config-driven page requirements
        ruleset = load_ruleset(repo_root)

        # Load run_config if not provided (follow W2 pattern - TC-925)
        if run_config is None:
            repo_root = Path(__file__).parent.parent.parent.parent.parent
            run_config_path = run_dir / "run_config.yaml"
            config_data = load_and_validate_run_config(repo_root, run_config_path)
            run_config_obj = RunConfig.from_dict(config_data)
        else:
            # Keep as dict if provided (tests may provide minimal run_config)
            # Don't force conversion to RunConfig - handle both dict and object below
            run_config_obj = run_config

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

        # Get product slug (family) from run_config
        # Per TC-681: Use run_config.family for path construction, not product_facts
        # Fallback to product_facts or defaults if run_config doesn't have these fields (test fixtures)
        # TC-902: Handle both dict and RunConfig object (blog paths require family segment)
        if isinstance(run_config_obj, dict):
            product_slug = run_config_obj.get("family", product_facts.get("product_slug", "product"))
        else:
            product_slug = getattr(run_config_obj, "family", product_facts.get("product_slug", "product"))
        locale = "en"  # Default locale (can be extracted from run_config later if needed)

        # TC-984: Compute evidence volume and effective quotas
        # Per specs/06_page_planning.md "Optional Page Selection Algorithm"
        merged_requirements = load_and_merge_page_requirements(ruleset, product_slug)
        evidence_volume = compute_evidence_volume(product_facts, snippet_catalog)
        effective_quotas = compute_effective_quotas(
            evidence_volume, launch_tier, section_quotas, merged_requirements
        )

        # Determine template directory
        # src/launch/workers/w4_ia_planner/worker.py -> go up 5 levels to reach repo root
        template_dir = Path(__file__).parent.parent.parent.parent.parent / "specs" / "templates"

        # Plan pages using template enumeration
        all_pages = []
        sections_subdomains = [
            ("products", "products.aspose.org"),
            ("docs", "docs.aspose.org"),
            ("reference", "reference.aspose.org"),
            ("kb", "kb.aspose.org"),
            ("blog", "blog.aspose.org"),
        ]

        for section, subdomain in sections_subdomains:
            # Enumerate templates for this section
            templates = enumerate_templates(
                template_dir=template_dir,
                subdomain=subdomain,
                family=product_slug,
                locale=locale,
            )

            if not templates:
                # Fallback to hardcoded planning if no templates found
                section_pages = plan_pages_for_section(
                    section=section,
                    launch_tier=launch_tier,
                    product_facts=product_facts,
                    snippet_catalog=snippet_catalog,
                    product_slug=product_slug,
                )
                all_pages.extend(section_pages)
                logger.info(f"[W4 IAPlanner] Planned {len(section_pages)} pages for section: {section} (fallback)")
                continue

            # Classify templates by launch tier
            mandatory, optional = classify_templates(templates, launch_tier)

            # TC-984: Apply effective quota (evidence-scaled) instead of static quota
            # Falls back to section_quotas if section not in effective_quotas
            eff_quota = effective_quotas.get(section, section_quotas.get(section, {"min_pages": 1, "max_pages": 10}))
            max_pages = eff_quota.get("max_pages", 10)
            selected = select_templates_with_quota(mandatory, optional, max_pages)

            # Fill placeholders to create page specs
            for template in selected:
                page_spec = fill_template_placeholders(
                    template=template,
                    section=section,
                    product_slug=product_slug,
                    locale=locale,
                    subdomain=subdomain,
                    product_facts=product_facts,
                )
                all_pages.append(page_spec)

            logger.info(f"[W4 IAPlanner] Planned {len(selected)} pages for section: {section} (template-driven)")

        # TC-984: Inject config-driven mandatory pages
        # Per specs/06_page_planning.md "Step 1: Add all mandatory pages"
        # Mandatory pages from merged config that are not yet covered by template-generated pages
        for section, subdomain in sections_subdomains:
            section_req = merged_requirements.get(section, {})
            mandatory_pages_config = section_req.get("mandatory_pages", [])
            if not mandatory_pages_config:
                continue

            existing_slugs = set(
                p["slug"] for p in all_pages if p["section"] == section
            )
            injected_count = 0

            claim_groups = product_facts.get("claim_groups", {})
            if not isinstance(claim_groups, dict):
                claim_groups = {}

            for mp in mandatory_pages_config:
                m_slug = mp.get("slug", "")
                m_role = mp.get("page_role", "")
                # Normalize _index → index to match enumerate_templates convention
                normalized_slug = "index" if m_slug == "_index" else m_slug
                if not m_slug or normalized_slug in existing_slugs:
                    continue
                m_slug = normalized_slug

                role = m_role or assign_page_role(section, m_slug, is_index=(m_slug == "_index"))
                strategy = build_content_strategy(role, section, workflows=[])

                # TC-VFV: Assign EXCLUSIVE claim subsets per section to avoid duplication
                # TOC/index pages: 0-2 claims per spec 08_content_distribution_strategy.md
                # Other pages: section-specific quotas with exclusive claim ranges
                required_claim_ids = []
                is_toc = role == "toc" or m_slug in ("index", "_index")

                key_features = sorted(claim_groups.get("key_features", []))
                install_steps = sorted(claim_groups.get("install_steps", []))
                limitations = sorted(claim_groups.get("limitations", []))

                if is_toc:
                    required_claim_ids = key_features[:2]
                elif section == "products":
                    # Products: max 5 claims
                    required_claim_ids = key_features[2:7][:5]
                elif section == "docs":
                    # Docs: max 8 claims
                    required_claim_ids = (key_features[7:12] + install_steps)[:8]
                elif section == "reference":
                    # Reference: max 5 claims
                    required_claim_ids = key_features[12:17][:5]
                elif section == "kb":
                    # KB: install_steps + limitations, max 5 claims
                    required_claim_ids = (install_steps + limitations)[:5]
                elif section == "blog":
                    # Blog: max 20 claims
                    required_claim_ids = (key_features + install_steps)[:20]

                page_spec = {
                    "section": section,
                    "slug": m_slug,
                    "output_path": compute_output_path(
                        section, m_slug, product_slug,
                        subdomain=subdomain, locale=locale,
                    ),
                    "url_path": compute_url_path(
                        section, m_slug, product_slug, locale=locale,
                    ),
                    "title": m_slug.replace("-", " ").replace("_", "").strip().title() or "Index",
                    "purpose": f"Mandatory {section} page: {m_slug}",
                    "template_variant": launch_tier,
                    "required_headings": _default_headings_for_role(role),
                    "required_claim_ids": required_claim_ids,
                    "required_snippet_tags": [],
                    "cross_links": [],
                    "page_role": role,
                    "content_strategy": strategy,
                }
                all_pages.append(page_spec)
                existing_slugs.add(m_slug)
                injected_count += 1

            if injected_count > 0:
                logger.info(
                    f"[W4 IAPlanner] Injected {injected_count} mandatory pages "
                    f"for section: {section} (config-driven)"
                )

        # TC-984: Evidence-driven optional page injection
        # Per specs/06_page_planning.md "Optional Page Selection Algorithm"
        # After the main template loop, inject optional pages to fill remaining quota
        for section, _subdomain in sections_subdomains:
            section_req = merged_requirements.get(section, {})
            optional_policies = section_req.get("optional_page_policies", [])
            if not optional_policies:
                continue

            eff_quota = effective_quotas.get(section, {})
            effective_max = eff_quota.get("max_pages", 0)

            # Count existing pages for this section
            existing_section_pages = [p for p in all_pages if p["section"] == section]
            existing_count = len(existing_section_pages)

            if existing_count >= effective_max:
                continue

            # Collect existing slugs to avoid duplicates
            existing_slugs = set(p["slug"] for p in existing_section_pages)

            # Generate optional pages
            optional_pages = generate_optional_pages(
                section=section,
                mandatory_page_count=existing_count,
                effective_max=effective_max,
                product_facts=product_facts,
                snippet_catalog=snippet_catalog,
                product_slug=product_slug,
                launch_tier=launch_tier,
                optional_page_policies=optional_policies,
            )

            # Deduplicate by slug against existing pages
            for opt_page in optional_pages:
                if opt_page["slug"] not in existing_slugs:
                    all_pages.append(opt_page)
                    existing_slugs.add(opt_page["slug"])
                else:
                    logger.debug(
                        f"[W4] Skipping optional page '{opt_page['slug']}' in "
                        f"section '{section}' - slug already exists"
                    )

        # Populate child_pages for TOC pages
        logger.info("[W4] Populating child_pages for TOC pages")
        for page in all_pages:
            if page.get("page_role") == "toc":
                section = page["section"]
                # Find all pages in same section (excluding TOC itself)
                child_slugs = [
                    p["slug"]
                    for p in all_pages
                    if p["section"] == section and p["slug"] != "_index"
                ]
                # Sort for deterministic ordering
                child_slugs.sort()
                page["content_strategy"]["child_pages"] = child_slugs
                logger.debug(f"[W4] TOC page {section}/_index has {len(child_slugs)} children: {child_slugs}")

        # Add cross-links between pages (TC-1001: absolute URLs)
        add_cross_links(all_pages, product_slug=product_slug)

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
        # TC-984: Include evidence_volume and effective_quotas per
        # specs/schemas/page_plan.schema.json (TC-983)
        page_plan = {
            "schema_version": "1.0",
            "product_slug": product_slug,
            "launch_tier": launch_tier,
            "launch_tier_adjustments": adjustments,
            "inferred_product_type": product_type,
            "evidence_volume": evidence_volume,
            "effective_quotas": {
                s: {"max_pages": q["max_pages"]}
                for s, q in sorted(effective_quotas.items())
            },
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
