"""TC-410: W2 FactsBuilder integrator worker.

This module implements the W2 FactsBuilder integrator that orchestrates all
sub-workers (TC-411, TC-412, TC-413) into a single cohesive worker
that the orchestrator can call.

W2 FactsBuilder performs:
1. TC-411: Extract claims from documentation
2. TC-412: Map evidence from claims to docs/examples
3. TC-413: Detect contradictions and resolve conflicts

Output artifacts:
- extracted_claims.json (TC-411)
- evidence_map.json (TC-412, updated by TC-413)
- product_facts.json (final, assembled from all sub-workers)

Spec references:
- specs/21_worker_contracts.md:98-125 (W2 FactsBuilder contract)
- specs/28_coordination_and_handoffs.md (Worker coordination)
- specs/11_state_and_events.md (State transitions and events)
- specs/03_product_facts_and_evidence.md (Facts extraction algorithm)

TC-410: W2 FactsBuilder integrator
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
from ...io.hashing import sha256_bytes
from ...models.claim_registry import REGISTRY
from ...models.event import (
    Event,
    EVENT_WORK_ITEM_STARTED,
    EVENT_WORK_ITEM_FINISHED,
    EVENT_ARTIFACT_WRITTEN,
)
from ...models.run_config import RunConfig
from ...io.run_config import load_and_validate_run_config
from ...io.atomic import atomic_write_json
from ...clients.llm_provider import LLMProviderClient, LLMError, create_llm_client_from_config
from ...util.logging import get_logger

# Import sub-worker functions
from .extract_claims import (
    extract_claims,
    detect_format_conversions,
    ClaimsExtractionError,
    ClaimsValidationError,
)
from .map_evidence import (
    map_evidence,
    EvidenceMappingError,
)
from .detect_contradictions import (
    detect_contradictions,
    ContradictionDetectionError,
)
from .enrich_claims import enrich_claims_batch, enrich_claim_text_batch, DEFAULT_BATCH_SIZE
from .._shared.slug_constants import FAMILY_KEYWORD_MAP, extract_family_keyword

logger = get_logger()


class FactsBuilderError(Exception):
    """Base exception for W2 FactsBuilder errors."""
    pass


class FactsBuilderClaimsError(FactsBuilderError):
    """Claims extraction failed."""
    pass


class FactsBuilderEvidenceError(FactsBuilderError):
    """Evidence mapping failed."""
    pass


class FactsBuilderContradictionError(FactsBuilderError):
    """Contradiction detection failed."""
    pass


class FactsBuilderAssemblyError(FactsBuilderError):
    """Product facts assembly failed."""
    pass


# --- Plan A3: Synthesized claim validation ------------------------------------

_FABRICATED_METRIC_RE = re.compile(
    r'\d+\s*(?:[x%]|ms\b|seconds?\b|minutes?\b)\s*'
    r'(?:per|faster|slower|improvement|reduction|accuracy|performance|for)',
    re.IGNORECASE,
)


def _validate_synthesized_claims(
    claims: List[Dict[str, Any]],
    grounded_count: int,
) -> List[Dict[str, Any]]:
    """Filter LLM-synthesized claims: cap count per kind and reject fabricated metrics.

    - Grounded claims (with real citations) are never filtered.
    - Synthesized claims with fabricated numbers + no citations are rejected.
    - Remaining synthesized claims are capped at max(5, grounded_count * 0.2) per kind.
    - All retained synthesized claims get confidence forced to 'low'.
    """
    grounded = [c for c in claims if c.get("source_type") != "llm_synthesized"]
    synthesized = [c for c in claims if c.get("source_type") == "llm_synthesized"]

    if not synthesized:
        return claims

    cap_per_kind = max(5, int(grounded_count * 0.2))

    validated = []
    for c in synthesized:
        text = c.get("claim_text", "")
        citations = c.get("citations", [])
        # Reject fabricated metrics without source backing
        if _FABRICATED_METRIC_RE.search(text) and not citations:
            logger.info("w2_reject_fabricated_metric claim=%s", text[:80])
            continue
        c["confidence"] = "low"
        validated.append(c)

    # Enforce cap per claim_kind
    kind_counts: Dict[str, int] = {}
    capped: List[Dict[str, Any]] = []
    for c in validated:
        kind = c.get("claim_kind", "unknown")
        kind_counts[kind] = kind_counts.get(kind, 0) + 1
        if kind_counts[kind] <= cap_per_kind:
            capped.append(c)
        else:
            logger.info(
                "w2_synth_cap_exceeded kind=%s count=%d cap=%d",
                kind, kind_counts[kind], cap_per_kind,
            )

    logger.info(
        "w2_synthesized_validation grounded=%d synth_in=%d rejected=%d capped_out=%d",
        grounded_count, len(synthesized),
        len(synthesized) - len(validated),
        len(capped),
    )
    return grounded + capped


# ------------------------------------------------------------------------------


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
        event_type: Event type string
        payload: Event payload dictionary

    Spec reference: specs/11_state_and_events.md
    """
    store = ArtifactStore(run_dir=run_layout.run_dir)
    store.emit_event(
        event_type,
        payload,
        run_id=run_id,
        trace_id=trace_id,
        span_id=span_id,
    )


def emit_artifact_written_event(
    run_layout: RunLayout,
    run_id: str,
    trace_id: str,
    span_id: str,
    artifact_name: str,
    schema_id: Optional[str] = None,
) -> None:
    """Emit ARTIFACT_WRITTEN event for an artifact.

    TC-1033: Uses ArtifactStore for sha256 computation via centralized hashing.

    Args:
        run_layout: Run directory layout
        run_id: Run identifier
        trace_id: Trace ID for telemetry
        span_id: Span ID for telemetry
        artifact_name: Artifact filename (e.g., "product_facts.json")
        schema_id: Schema identifier (e.g., "product_facts.schema.json")

    Spec reference: specs/21_worker_contracts.md:38-40
    """
    artifact_path = run_layout.artifacts_dir / artifact_name

    if not artifact_path.exists():
        return

    content = artifact_path.read_bytes()
    sha256_hash = sha256_bytes(content)

    store = ArtifactStore(run_dir=run_layout.run_dir)
    store.emit_event(
        EVENT_ARTIFACT_WRITTEN,
        {
            "name": artifact_name,
            "path": str(artifact_path.relative_to(run_layout.run_dir)),
            "sha256": sha256_hash,
            "schema_id": schema_id,
        },
        run_id=run_id,
        trace_id=trace_id,
        span_id=span_id,
    )


def _select_priority_claims(
    claims: List[Dict],
    claim_groups: Dict[str, List[str]],
    max_llm: int = 200,
) -> tuple:
    """Split claims into LLM-priority and offline-fallback groups.

    TC-1730: Priority order ensures the most documentation-critical claims
    get LLM enrichment first. Remaining claims use offline heuristics.

    Args:
        claims: All extracted claims.
        claim_groups: claim_groups dict mapping group names to claim ID lists.
        max_llm: Maximum claims for LLM enrichment.

    Returns:
        (llm_claims, offline_claims) tuple.
    """
    priority_order = [
        "key_features", "install_steps", "use_cases", "faq",
        "troubleshooting", "best_practices", "workflow_claims",
        "tutorials", "performance", "quickstart_steps",
        "compatibility_notes", "limitations",
    ]

    # Build claim_id -> claim lookup
    claim_by_id = {c.get("claim_id", ""): c for c in claims if c.get("claim_id")}

    selected_ids: set = set()
    llm_claims = []

    # Select by priority group order
    for group in priority_order:
        if len(llm_claims) >= max_llm:
            break
        for cid in claim_groups.get(group, []):
            if cid in selected_ids:
                continue
            claim = claim_by_id.get(cid)
            if claim:
                llm_claims.append(claim)
                selected_ids.add(cid)
                if len(llm_claims) >= max_llm:
                    break

    # Remaining claims go to offline
    offline_claims = [c for c in claims if c.get("claim_id", "") not in selected_ids]

    return llm_claims, offline_claims


def _infer_audience(claims: List[Dict], product_family: str, product_name: str) -> str:
    """Infer target audience from claims and metadata.

    TC-1612: Populate positioning.audience from claims analysis.

    Args:
        claims: List of claim dicts
        product_family: Product family name
        product_name: Product name

    Returns:
        Inferred audience string
    """
    # Check for enterprise/production mentions
    claim_texts = ' '.join(c.get('claim_text', '') for c in claims[:50]).lower()

    if 'enterprise' in claim_texts or 'production' in claim_texts or 'scalable' in claim_texts:
        return "Enterprise developers and software architects"

    # Check manifest compatibility claims for platform
    for c in claims:
        if c.get('claim_kind') == 'compatibility' and 'python' in c.get('claim_text', '').lower():
            return "Python developers"
        if c.get('source_type') == 'manifest' and 'node' in c.get('claim_text', '').lower():
            return "Node.js developers"

    # Fallback based on product family
    if product_family:
        return f"Software developers working with {product_family}"

    return "Software developers and AI agents"


def _infer_who_it_is_for(claims: List[Dict], product_name: str, supported_formats: List[Dict]) -> str:
    """Infer who_it_is_for from product capabilities.

    TC-1612: Populate positioning.who_it_is_for from product facts.
    USER REQUIREMENT: Must mention "both humans and AI agents".

    Args:
        claims: List of claim dicts
        product_name: Product name
        supported_formats: List of format dicts

    Returns:
        Who_it_is_for string including "both humans and AI agents"
    """
    # Extract format names
    formats = [f.get('format', '') for f in supported_formats[:5]]
    format_str = ', '.join(formats) if formats else "various file formats"

    # Get platform from claims
    platform = "Python"  # default
    for c in claims:
        if 'javascript' in c.get('claim_text', '').lower():
            platform = "JavaScript"
            break
        if 'java' in c.get('claim_text', '').lower() and 'javascript' not in c.get('claim_text', '').lower():
            platform = "Java"
            break

    # USER REQUIREMENT: Must mention "both humans and AI agents"
    return f"Both humans and AI agents who need to work with {format_str} in {platform}"


def _synthesize_manifest_claims(
    manifest_data: Dict[str, Any],
    product_name: str,
) -> List[Dict[str, Any]]:
    """Synthesize claims from parsed setup.py manifest data.

    Generates structured claims for install command, Python version requirement,
    dependency information, and version from manifest fields.

    Args:
        manifest_data: Parsed manifest dict (from parse_setup_py)
        product_name: Product name for claim text

    Returns:
        List of claim dicts with claim_id, claim_text, claim_kind, etc.
    """
    from .extract_claims import compute_claim_id

    claims: List[Dict[str, Any]] = []
    manifest_citation = [{
        "path": "setup.py",
        "start_line": 1,
        "end_line": 1,
        "source_type": "manifest",
    }]

    pkg_name = manifest_data.get("name", "")

    # 1. Install claim
    if pkg_name:
        claim_text = f"Install {product_name} with pip: pip install {pkg_name}"
        claim_kind = "workflow"
        claims.append({
            "claim_id": compute_claim_id(claim_text, claim_kind, product_name),
            "claim_text": claim_text,
            "claim_kind": claim_kind,
            "truth_status": "fact",
            "confidence": "high",
            "source_type": "manifest",
            "source_priority": 1,
            "source_relevance": 100,
            "citations": [dict(c) for c in manifest_citation],
        })

    # 2. Python version requirement
    python_requires = manifest_data.get("python_requires", "")
    if python_requires:
        claim_text = f"{product_name} requires Python {python_requires}"
        claim_kind = "compatibility"
        claims.append({
            "claim_id": compute_claim_id(claim_text, claim_kind, product_name),
            "claim_text": claim_text,
            "claim_kind": claim_kind,
            "truth_status": "fact",
            "confidence": "high",
            "source_type": "manifest",
            "source_priority": 1,
            "source_relevance": 100,
            "citations": [dict(c) for c in manifest_citation],
        })

    # 3. Dependency information
    install_requires = manifest_data.get("install_requires", [])
    if not install_requires:
        claim_text = (
            f"{product_name} has zero runtime dependencies, "
            "making it lightweight and easy to install"
        )
        claim_kind = "feature"
    else:
        deps = ", ".join(sorted(install_requires))
        claim_text = f"{product_name} depends on {deps}"
        claim_kind = "feature"

    claims.append({
        "claim_id": compute_claim_id(claim_text, claim_kind, product_name),
        "claim_text": claim_text,
        "claim_kind": claim_kind,
        "truth_status": "fact",
        "confidence": "high",
        "source_type": "manifest",
        "source_priority": 1,
        "source_relevance": 100,
        "citations": [dict(c) for c in manifest_citation],
    })

    # 4. Version claim
    version = manifest_data.get("version", "")
    if version:
        claim_text = f"{product_name} version {version} is the current release"
        claim_kind = "feature"
        claims.append({
            "claim_id": compute_claim_id(claim_text, claim_kind, product_name),
            "claim_text": claim_text,
            "claim_kind": claim_kind,
            "truth_status": "fact",
            "confidence": "high",
            "source_type": "manifest",
            "source_priority": 1,
            "source_relevance": 100,
            "citations": [dict(c) for c in manifest_citation],
        })

    return claims


def _normalize_claim_identity(claim_text: str, claim_kind: str) -> str:
    """Compute a normalized identity key for claim matching.

    TC-1762: Used for incremental claim merging to match claims across runs.
    Identity is based on lowercased, stripped claim_text + claim_kind to allow
    minor whitespace/casing changes without treating claims as different.

    Args:
        claim_text: The claim text to normalize.
        claim_kind: The claim kind (e.g., 'key_feature', 'install_step').

    Returns:
        A string identity key for matching.
    """
    text = ' '.join(claim_text.lower().split())  # normalize whitespace + lowercase
    kind = claim_kind.lower().strip()
    return f"{kind}::{text}"


def _merge_claims_incremental(
    current_claims: List[Dict[str, Any]],
    previous_facts: Dict[str, Any],
) -> tuple:
    """Merge current claims with previous run's claims for incremental stability.

    TC-1762: Incremental claim merging preserves claim_id stability across runs
    so that downstream artifacts (page plans, drafts) referencing claim IDs remain
    valid when claims haven't materially changed.

    Strategy:
    - Matched claims (same text+kind): retain OLD claim_id for stability
    - New claims (in current but not previous): keep new claim_id
    - Deprecated claims (in previous but not current): add with deprecated=true

    Args:
        current_claims: Claims from the current run.
        previous_facts: Full product_facts dict from the previous run.

    Returns:
        Tuple of (merged_claims, incremental_metadata) where incremental_metadata
        contains merge statistics.
    """
    previous_claims = previous_facts.get('claims', [])
    if not previous_claims:
        return current_claims, {
            'merge_performed': True,
            'previous_claim_count': 0,
            'current_claim_count': len(current_claims),
            'matched': 0,
            'new': len(current_claims),
            'deprecated': 0,
            'final_claim_count': len(current_claims),
        }

    # Build identity → claim mapping for previous claims
    prev_by_identity: Dict[str, Dict[str, Any]] = {}
    for claim in previous_claims:
        identity = _normalize_claim_identity(
            claim.get('claim_text', ''),
            claim.get('claim_kind', ''),
        )
        # First occurrence wins (stable ordering)
        if identity not in prev_by_identity:
            prev_by_identity[identity] = claim

    # Track which previous claims were matched
    matched_prev_identities: set = set()
    merged: List[Dict[str, Any]] = []
    stats_matched = 0
    stats_new = 0

    for claim in current_claims:
        identity = _normalize_claim_identity(
            claim.get('claim_text', ''),
            claim.get('claim_kind', ''),
        )

        if identity in prev_by_identity:
            # Matched: use OLD claim_id for stability, but update other fields
            prev_claim = prev_by_identity[identity]
            stable_claim = dict(claim)  # start with current data
            stable_claim['claim_id'] = prev_claim['claim_id']  # preserve old ID
            # Remove deprecated flag if it was set in previous run
            stable_claim.pop('deprecated', None)
            merged.append(stable_claim)
            matched_prev_identities.add(identity)
            stats_matched += 1
        else:
            # New claim: keep as-is
            merged.append(dict(claim))
            stats_new += 1

    # Add deprecated claims (in previous but not current)
    stats_deprecated = 0
    for identity, prev_claim in prev_by_identity.items():
        if identity not in matched_prev_identities:
            deprecated_claim = dict(prev_claim)
            deprecated_claim['deprecated'] = True
            merged.append(deprecated_claim)
            stats_deprecated += 1

    metadata = {
        'merge_performed': True,
        'previous_claim_count': len(previous_claims),
        'current_claim_count': len(current_claims),
        'matched': stats_matched,
        'new': stats_new,
        'deprecated': stats_deprecated,
        'final_claim_count': len(merged),
    }

    logger.info(
        "incremental_claim_merge",
        previous=len(previous_claims),
        current=len(current_claims),
        matched=stats_matched,
        new=stats_new,
        deprecated=stats_deprecated,
        final=len(merged),
    )

    return merged, metadata


# ---------------------------------------------------------------------------
# TC-2512/2513/2517: Family capability registry extraction (deterministic)
# ---------------------------------------------------------------------------

# TC-2601: _FAMILY_KEYWORD_MAP imported from _shared.slug_constants
_FAMILY_KEYWORD_MAP = FAMILY_KEYWORD_MAP  # backward-compat alias

# Domain-specific keywords by family (used for SEO and slug generation)
_DOMAIN_KEYWORDS: Dict[str, List[str]] = {
    "3d": ["3d-models", "mesh", "scene", "geometry", "rendering", "animation"],
    "cells": ["workbook", "worksheet", "cell", "spreadsheet", "formula", "pivot-table"],
    "note": ["notebook", "page", "section", "onenote", "note"],
    "words": ["document", "paragraph", "table", "header", "footer"],
    "pdf": ["pdf", "page", "annotation", "form", "bookmark"],
    "slides": ["presentation", "slide", "shape", "animation", "transition"],
    "imaging": ["image", "pixel", "filter", "resize", "crop", "format"],
}

# Format detection regex — common file format extensions mentioned in claims
_FORMAT_RE = re.compile(
    r'\b('
    r'xlsx?|csv|ods|tsv|html?|pdf|docx?|pptx?|rtf|txt|xml|json|yaml'
    r'|obj|fbx|stl|dae|gltf|glb|ply|3ds|3mf|amf|u3d|rvm|off'
    r'|one|onetoc2'
    r'|png|jpg|jpeg|gif|bmp|tiff?|svg|webp|ico'
    r'|dwg|dxf'
    r')\b',
    re.IGNORECASE,
)

# Import/export direction keywords
_LOAD_KEYWORDS = frozenset(
    ["import", "read", "load", "parse", "open", "reads", "loads", "parses", "opens"]
)
_SAVE_KEYWORDS = frozenset(
    ["export", "write", "save", "generate", "writes", "saves", "generates", "create"]
)


def _validate_conversion_pairs(
    pairs: List[List[str]],
) -> List[List[str]]:
    """TC-2517: Validate and clean conversion pairs.

    - Each pair must have exactly 2 elements.
    - No self-conversion (source != target, case-insensitive).
    - Deterministically sorted by (source, target).

    Args:
        pairs: Raw conversion pairs (lists of two format strings).

    Returns:
        Validated, sorted list of [source, target] pairs.
    """
    validated: List[List[str]] = []
    seen: set = set()
    for pair in pairs:
        if not isinstance(pair, (list, tuple)):
            continue
        if len(pair) != 2:
            continue
        source = str(pair[0]).upper().strip()
        target = str(pair[1]).upper().strip()
        if not source or not target:
            continue
        # No self-conversion
        if source == target:
            continue
        key = (source, target)
        if key not in seen:
            seen.add(key)
            validated.append([source, target])
    # Deterministic sort
    validated.sort(key=lambda p: (p[0], p[1]))
    return validated


def _extract_family_keyword(family: str) -> str:
    """Map family identifier to SEO keyword using shared FAMILY_KEYWORD_MAP.

    TC-2601: Delegates to _shared.slug_constants.extract_family_keyword().

    Args:
        family: Product family string (e.g. "cells", "3d", "note").

    Returns:
        SEO keyword string; falls back to "files" for unknown families.
    """
    return extract_family_keyword(family)


def _extract_formats_from_claims(
    claims: List[Dict[str, Any]],
) -> Dict[str, Dict[str, List[str]]]:
    """Extract supported formats from claims, split by load/save direction.

    Scans all claims for file format mentions and infers direction from
    context keywords.

    Args:
        claims: List of claim dicts from product_facts.

    Returns:
        Dict with 'load' and 'save' keys, each containing a sorted list
        of format names (uppercase). Also returns 'format_claim_ids'.
    """
    load_formats: set = set()
    save_formats: set = set()
    all_formats: set = set()
    format_claim_ids: List[str] = []

    for claim in claims:
        text = claim.get("claim_text", "")
        text_lower = text.lower()
        matches = _FORMAT_RE.findall(text)
        if not matches:
            continue

        claim_id = claim.get("claim_id", "")
        if claim_id:
            format_claim_ids.append(claim_id)

        for fmt in matches:
            fmt_upper = fmt.upper()
            all_formats.add(fmt_upper)

            words = set(text_lower.split())
            has_load = bool(words & _LOAD_KEYWORDS)
            has_save = bool(words & _SAVE_KEYWORDS)

            if has_load:
                load_formats.add(fmt_upper)
            if has_save:
                save_formats.add(fmt_upper)
            # If no direction detected, add to both
            if not has_load and not has_save:
                load_formats.add(fmt_upper)
                save_formats.add(fmt_upper)

    return {
        "load": sorted(load_formats),
        "save": sorted(save_formats),
        "format_claim_ids": sorted(set(format_claim_ids)),
    }


def _extract_family_capabilities(
    product_facts: Dict[str, Any],
    run_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """TC-2513: Deterministic extraction of family capabilities from product_facts.

    Builds a family_capabilities.json artifact containing SEO keywords,
    supported formats, conversion pairs, feature clusters, and domain
    keywords derived from claims and claim_groups.

    No LLM calls — purely deterministic.

    Args:
        product_facts: Assembled product_facts dict.
        run_config: Optional run configuration dict (for family field).

    Returns:
        Dict conforming to family_capabilities.schema.json.
    """
    # 1. Extract family from run_config, fallback to product_facts
    family = ""
    if run_config and isinstance(run_config, dict):
        family = run_config.get("family", "")
    if not family:
        family = product_facts.get("product_family", "")
    if not family:
        # Infer from product_slug
        slug = product_facts.get("product_slug", "")
        for key in _FAMILY_KEYWORD_MAP:
            if key in slug.lower():
                family = key
                break
    family = family.lower().strip() if family else ""

    # 2. Map to SEO keyword
    keyword = _extract_family_keyword(family) if family else "files"

    # 3. Extract formats from claims
    claims = product_facts.get("claims", [])
    format_data = _extract_formats_from_claims(claims)

    supported_formats = {
        "load": format_data["load"],
        "save": format_data["save"],
    }

    # 4. Extract conversion pairs from claim_groups
    claim_groups = product_facts.get("claim_groups", {})
    raw_pairs = claim_groups.get("conversion_pairs", [])
    # Normalize: conversion_pairs may be list of [src, tgt] or list of dicts
    normalized_pairs: List[List[str]] = []
    for item in raw_pairs:
        if isinstance(item, (list, tuple)) and len(item) == 2:
            normalized_pairs.append([str(item[0]), str(item[1])])
        elif isinstance(item, dict):
            src = item.get("source", item.get("from", ""))
            tgt = item.get("target", item.get("to", ""))
            if src and tgt:
                normalized_pairs.append([str(src), str(tgt)])

    # TC-2517: Validate conversion pairs
    conversion_pairs = _validate_conversion_pairs(normalized_pairs)

    # 5. Feature clusters from claim_groups keys (non-empty groups only)
    feature_clusters = sorted([
        key for key, ids in claim_groups.items()
        if isinstance(ids, list) and len(ids) > 0
        and key not in ("conversion_pairs", "format_conversions")
    ])

    # 6. Domain keywords
    family_base = family.split("-")[0] if family else ""
    domain_keywords = sorted(_DOMAIN_KEYWORDS.get(family_base, []))

    # 7. Evidence refs
    feature_claim_ids: List[str] = []
    for group_key in ("key_features", "use_cases"):
        feature_claim_ids.extend(claim_groups.get(group_key, []))
    feature_claim_ids = sorted(set(feature_claim_ids))

    return {
        "schema_version": "1.0",
        "family": family,
        "keyword": keyword,
        "supported_formats": supported_formats,
        "conversion_pairs": conversion_pairs,
        "feature_clusters": feature_clusters,
        "domain_keywords": domain_keywords,
        "evidence_refs": {
            "format_claim_ids": format_data["format_claim_ids"],
            "feature_claim_ids": feature_claim_ids,
        },
    }


def assemble_product_facts(
    run_layout: RunLayout,
    evidence_map: Dict[str, Any],
    run_config: Optional[Dict[str, Any]] = None,
    llm_client: Optional[Any] = None,
) -> Dict[str, Any]:
    """Assemble final product_facts.json from evidence_map and repo_inventory.

    Per specs/21_worker_contracts.md:98-125, product_facts.json must include:
    - Claims with stable IDs
    - Claim groups (key_features, install_steps, workflows, etc.)
    - Supported formats extracted from format claims
    - API surface summary
    - Example inventory

    Args:
        run_layout: Run directory layout
        evidence_map: Evidence map from TC-412/413
        run_config: Run configuration dict (optional, for product_name/family)
        llm_client: Optional LLM client for workflow generation (TC-1623)

    Returns:
        Product facts dictionary

    Raises:
        FactsBuilderAssemblyError: If assembly fails

    Spec: specs/schemas/product_facts.schema.json
    """
    # Load repo_inventory for metadata
    repo_inventory_path = run_layout.artifacts_dir / "repo_inventory.json"
    if not repo_inventory_path.exists():
        raise FactsBuilderAssemblyError(
            f"repo_inventory.json not found: {repo_inventory_path}"
        )

    with open(repo_inventory_path, 'r', encoding='utf-8') as f:
        repo_inventory = json.load(f)

    # Load code analysis from artifact (TC-1042, generated in execute_facts_builder())
    code_analysis_path = run_layout.artifacts_dir / "code_analysis.json"
    code_analysis = {}
    if code_analysis_path.exists():
        with open(code_analysis_path, 'r', encoding='utf-8') as f:
            code_analysis = json.load(f)

    # Extract metadata — prefer run_config over repo_inventory for product_name
    product_name = ''
    if run_config:
        product_name = run_config.get('product_name', '')
    if not product_name:
        product_name = repo_inventory.get('product_name', '')
    if not product_name:
        # Fallback: derive from repo URL
        repo_url_fallback = evidence_map.get('repo_url', '')
        if repo_url_fallback:
            product_name = repo_url_fallback.split('/')[-1].replace('.git', '').replace('-', ' ').title()

    # Extract product_family from run_config
    product_family = ''
    if run_config:
        product_family = run_config.get('family', '')
    repo_url = evidence_map.get('repo_url', '')
    repo_sha = evidence_map.get('repo_sha', '')

    # Generate product_slug from product_name
    product_slug = product_name.lower().replace(' ', '-').replace('_', '-')

    claims = evidence_map.get('claims', [])

    # TC-1604: Helper to infer source quality from claim or its citations

    _META_CITATION_MARKERS = ('agents.md', '.claude/', 'claude.md', 'contributing.md')
    _IMPL_CITATION_MARKERS = ('implementation', '_implementation', 'architecture', 'design')

    def _is_low_quality_source(claim):
        """Check if claim comes from meta/implementation docs or low-quality code sources.

        TC-1616: source_code is low quality for key_features/features (marketing content),
        but OK for api_reference (technical reference documentation).
        """
        st = claim.get('source_type', '')
        claim_kind = claim.get('claim_kind', '')

        # TC-1616: Source code is low quality for key_features, OK for api_reference
        if st == 'source_code':
            if claim_kind in ('key_feature', 'feature'):
                return True  # Deprioritize for marketing content

        # Existing meta/implementation doc checks
        if st in ('implementation_doc', 'meta'):
            return True

        # Fallback: check citation paths when source_type is missing
        if not st:
            for cit in claim.get('citations', []):
                path = cit.get('path', '').lower().replace('\\', '/')
                if any(m in path for m in _META_CITATION_MARKERS):
                    return True
                if any(m in path for m in _IMPL_CITATION_MARKERS):
                    return True

        return False

    # Phase 1A: Use ClaimKindRegistry for single-pass routing (replaces if/elif chains)
    _initial_groups = REGISTRY.build_claim_groups(claims, is_low_quality_fn=_is_low_quality_source)

    # Extract local references for downstream quality ranking and workflow building
    key_features = list(_initial_groups.get('key_features', []))
    install_steps = list(_initial_groups.get('install_steps', []))
    quickstart_steps = list(_initial_groups.get('quickstart_steps', []))
    workflow_claims = list(_initial_groups.get('workflow_claims', []))
    limitations = list(_initial_groups.get('limitations', []))
    compatibility_notes = list(_initial_groups.get('compatibility_notes', []))
    use_cases = list(_initial_groups.get('use_cases', []))
    faq_claims = list(_initial_groups.get('faq', []))
    best_practices = list(_initial_groups.get('best_practices', []))
    performance_claims = list(_initial_groups.get('performance', []))
    tutorial_claims = list(_initial_groups.get('tutorials', []))
    troubleshooting_claims = list(_initial_groups.get('troubleshooting', []))

    # Cap limitations to avoid over-representation (most useful 15)
    if len(limitations) > 15:
        # Prefer fact over inference, then by claim text length (more informative)
        def _limitation_quality(cid):
            c = claim_lookup_all.get(cid, {})
            is_fact = 1 if c.get('truth_status') == 'fact' else 0
            return (-is_fact, -len(c.get('claim_text', '')))
        claim_lookup_all = {c['claim_id']: c for c in claims}
        limitations.sort(key=_limitation_quality)
        limitations = limitations[:15]

    # TC-1604: Quality-rank key_features (README > manifest > others; longer > shorter)
    claim_lookup = {c['claim_id']: c for c in claims}

    def _claim_quality(cid):
        c = claim_lookup.get(cid, {})
        source_type = c.get('source_type', '')
        # Fallback: infer source type from citation paths
        if not source_type:
            for cit in c.get('citations', []):
                path = cit.get('path', '').lower()
                if 'readme' in path:
                    source_type = 'readme_technical'
                    break
                elif 'setup.py' in path or 'pyproject' in path:
                    source_type = 'manifest'
                    break
        relevance = c.get('source_relevance', 50)
        length_score = min(len(c.get('claim_text', '')), 200)
        type_bonus = 100 if source_type.startswith('readme') else (
            80 if source_type == 'manifest' else 0
        )
        return -(type_bonus + relevance + length_score)  # negative for ascending sort

    key_features.sort(key=_claim_quality)

    # Extract supported formats from format claims (TC-1515: deduplicated)
    import re

    def _merge_directions(existing: str, new: str) -> str:
        if existing == new:
            return existing
        if existing == 'unknown':
            return new
        if new == 'unknown':
            return existing
        if {existing, new} == {'import', 'export'}:
            return 'both'
        return 'both' if 'both' in (existing, new) else existing

    format_data: dict = {}  # format_name → {format, status, direction, claim_ids}
    for claim in claims:
        if claim.get('claim_kind') == 'format':
            claim_text = claim.get('claim_text', '').lower()

            format_match = re.search(
                r'\b(obj|fbx|stl|dae|gltf|glb|ply|3ds|3mf|amf|u3d|rvm|off|one|pdf|dwg|dxf)\b',
                claim_text,
            )
            if format_match:
                format_name = format_match.group(1).upper()

                is_negative = any(neg in claim_text for neg in ['does not', 'cannot', 'not supported', 'unsupported'])
                status = 'unknown' if is_negative else 'implemented'

                import_kws = ('import', 'read', 'load', 'parse', 'open', 'reads', 'loads', 'parses')
                export_kws = ('export', 'write', 'save', 'generate', 'writes', 'saves', 'generates')
                has_import = any(w in claim_text for w in import_kws)
                has_export = any(w in claim_text for w in export_kws)

                if has_import and has_export:
                    direction = 'both'
                elif 'both' in claim_text:
                    direction = 'both'
                elif has_import:
                    direction = 'import'
                elif has_export:
                    direction = 'export'
                else:
                    direction = 'unknown'

                if format_name not in format_data:
                    format_data[format_name] = {
                        'format': format_name,
                        'status': status,
                        'direction': direction,
                        'claim_ids': [claim['claim_id']],
                    }
                else:
                    existing = format_data[format_name]
                    existing['claim_ids'].append(claim['claim_id'])
                    existing['direction'] = _merge_directions(existing['direction'], direction)
                    if status == 'implemented':
                        existing['status'] = 'implemented'

    supported_formats = list(format_data.values())
    # Backward compat: keep claim_id pointing to first claim
    for entry in supported_formats:
        entry['claim_id'] = entry['claim_ids'][0]

    # TC-1516: Load code_understanding early — needed for workflows + feature_profiles + examples
    code_understanding_path = run_layout.artifacts_dir / "code_understanding.json"
    code_understanding = None
    if code_understanding_path.exists():
        try:
            with open(code_understanding_path, 'r', encoding='utf-8') as f:
                code_understanding = json.load(f)
        except Exception:
            pass

    # Build enriched workflows (TC-1043)
    from .enrich_workflows import enrich_workflow

    snippet_catalog_path = run_layout.artifacts_dir / "snippet_catalog.json"
    snippet_catalog = {'snippets': []}
    if snippet_catalog_path.exists():
        with open(snippet_catalog_path, 'r', encoding='utf-8') as f:
            snippet_catalog = json.load(f)

    # Build step-aware workflows from decomposed claims (TC-1611)
    claim_lookup = {c['claim_id']: c for c in claims}

    def _build_workflow_from_step_claims(tag, title, claim_ids):
        """Build workflow with steps from claims that have step_order.

        TC-1611: Synthesize workflow objects from decomposed README claims.
        Each claim with step_order becomes a workflow step.

        Args:
            tag: Workflow tag (e.g., 'installation', 'quickstart')
            title: Human-readable workflow title
            claim_ids: List of claim IDs belonging to this workflow

        Returns:
            Workflow dictionary with ordered steps
        """
        step_claims = []
        for cid in claim_ids:
            c = claim_lookup.get(cid, {})
            step_claims.append((c.get('step_order', 999), c))
        step_claims.sort(key=lambda x: x[0])

        steps = []
        for i, (_, c) in enumerate(step_claims, 1):
            steps.append({
                'step_num': i,
                'step_id': f"step_{i}",
                'name': c.get('claim_text', f'Step {i}'),
                'claim_id': c.get('claim_id'),
                'snippet_id': None,
            })

        return {
            'workflow_id': f"wf_{tag}",
            'workflow_tag': tag,
            'title': title,
            'name': title,
            'description': f'{title} workflow for {product_name}',
            'complexity': 'simple' if len(steps) <= 3 else 'moderate',
            'estimated_time_minutes': 5 + (len(steps) - 1) * 2,
            'steps': steps,
            'claim_ids': claim_ids,
            'snippet_tags': [tag],
        }

    workflows = []
    # Build installation workflow from decomposed claims
    if install_steps:
        workflows.append(_build_workflow_from_step_claims(
            'installation',
            'Installation',
            install_steps
        ))

    # Build quickstart workflow from decomposed claims
    if quickstart_steps:
        workflows.append(_build_workflow_from_step_claims(
            'quickstart',
            'Quick Start',
            quickstart_steps
        ))

    # TC-1617: Merge and enrich workflows
    def _merge_workflows(claim_workflows, cu_workflows):
        """Merge code_understanding workflows with claim-based workflows.

        TC-1617: Strategy - prefer README workflows (higher quality), add
        code_understanding workflows only for NEW workflow types.

        Args:
            claim_workflows: Workflows from README claims
            cu_workflows: Workflows from code_understanding

        Returns:
            Merged workflow list with deduplication
        """
        merged = []
        seen_tags = set()

        # Add README workflows first (higher priority)
        for wf in claim_workflows:
            tag = wf.get('workflow_tag', '')
            merged.append(wf)
            seen_tags.add(tag)

        # Add code_understanding workflows for NEW types only
        for wf in cu_workflows:
            tag = wf.get('workflow_tag', '')
            if tag not in seen_tags:
                # Expand step descriptions with "how to" context
                for step in wf.get('steps', []):
                    if 'name' in step:
                        name = step['name']
                        # Add "How to" prefix if not already present
                        if not name.lower().startswith('how to'):
                            step['name'] = f"How to {name.lower()}"
                merged.append(wf)
                seen_tags.add(tag)

        return merged

    def _synthesize_common_task_workflows(product_facts_partial, claims_list):
        """Synthesize workflows for common tasks inferred from product capabilities.

        TC-1617: Creates format conversion and batch processing workflows based
        on product features.

        Args:
            product_facts_partial: Partial product facts (with supported_formats)
            claims_list: All claims for inference

        Returns:
            List of synthesized workflow dicts
        """
        synthesized = []
        pname = product_facts_partial.get('product_name', 'Product')

        # Synthesize format conversion workflow if 2+ formats
        formats = product_facts_partial.get('supported_formats', [])
        if len(formats) >= 2:
            source_fmt = formats[0]
            target_fmt = formats[1]
            synthesized.append({
                'workflow_id': f"wf_format_conversion",
                'workflow_tag': 'format_conversion',
                'title': f"Convert between {source_fmt} and {target_fmt} formats",
                'name': 'Format Conversion',
                'description': f'Convert files from {source_fmt} to {target_fmt} using {pname}',
                'complexity': 'simple',
                'estimated_time_minutes': 5,
                'steps': [
                    {'step_num': 1, 'step_id': 'step_1', 'name': f'Load {source_fmt} file', 'claim_id': None, 'snippet_id': None},
                    {'step_num': 2, 'step_id': 'step_2', 'name': 'Process content', 'claim_id': None, 'snippet_id': None},
                    {'step_num': 3, 'step_id': 'step_3', 'name': f'Save as {target_fmt} format', 'claim_id': None, 'snippet_id': None},
                ],
                'claim_ids': [],
                'source': 'synthesized',
            })

        # Synthesize batch processing workflow if batch indicators present
        batch_indicators = ['batch', 'multiple', 'list', 'collection']
        api_claims = [c for c in claims_list if c.get('claim_kind') == 'api_reference']
        has_batch = any(
            ind in c.get('claim_text', '').lower()
            for c in api_claims
            for ind in batch_indicators
        )

        if has_batch:
            synthesized.append({
                'workflow_id': f"wf_batch_processing",
                'workflow_tag': 'batch_processing',
                'title': 'Process multiple files in batch',
                'name': 'Batch Processing',
                'description': f'Process multiple files efficiently using {pname}',
                'complexity': 'moderate',
                'estimated_time_minutes': 10,
                'steps': [
                    {'step_num': 1, 'step_id': 'step_1', 'name': 'Prepare list of input files', 'claim_id': None, 'snippet_id': None},
                    {'step_num': 2, 'step_id': 'step_2', 'name': 'Iterate over files', 'claim_id': None, 'snippet_id': None},
                    {'step_num': 3, 'step_id': 'step_3', 'name': 'Process each file', 'claim_id': None, 'snippet_id': None},
                    {'step_num': 4, 'step_id': 'step_4', 'name': 'Save results', 'claim_id': None, 'snippet_id': None},
                ],
                'claim_ids': [],
                'source': 'synthesized',
            })

        return synthesized

    # TC-1516/TC-1617: Bridge code_understanding usage_workflows into product_facts
    cu_workflows = []
    if code_understanding:
        for cu_wf in code_understanding.get('usage_workflows', []):
            wf_name = cu_wf.get('name', '')
            wf_tag = wf_name.lower().replace(' ', '_')[:30]

            cu_steps = cu_wf.get('steps', [])
            if len(cu_steps) < 2:
                continue  # Skip trivial 1-step workflows

            steps = []
            for i, step in enumerate(cu_steps, start=1):
                steps.append({
                    'step_num': i,
                    'step_id': f"step_{i}",
                    'name': step.get('description', f'Step {i}'),
                    'claim_id': None,
                    'snippet_id': None,
                    'code': step.get('code', ''),
                })

            n = len(steps)
            cu_workflows.append({
                'workflow_id': f"wf_cu_{wf_tag}",
                'workflow_tag': wf_tag,
                'name': wf_name,
                'title': wf_name,
                'description': cu_wf.get('description', ''),
                'complexity': 'simple' if n <= 2 else ('moderate' if n <= 5 else 'complex'),
                'estimated_time_minutes': 5 + (n - 1) * 3,
                'steps': steps,
                'claim_ids': [],
                'source': 'code_understanding',
            })

    # TC-1617: Merge README workflows with code_understanding workflows
    workflows = _merge_workflows(workflows, cu_workflows)

    # TC-1617: Synthesize common task workflows
    # Note: Need partial product_facts for formats, so build minimal dict
    partial_facts = {
        'product_name': product_name,
        'supported_formats': supported_formats,
    }
    synthesized = _synthesize_common_task_workflows(partial_facts, claims)
    workflows.extend(synthesized)

    # Build API surface summary from code analysis (TC-1042)
    api_surface_summary = code_analysis.get("api_surface", {})
    if not api_surface_summary.get("classes") and not api_surface_summary.get("functions"):
        # Fallback: extract from claim text if code analysis found nothing
        api_claims = [c for c in claims if c.get('claim_kind') == 'api']
        if api_claims:
            api_surface_summary['classes'] = [c['claim_id'] for c in api_claims if 'class' in c.get('claim_text', '').lower()]
            api_surface_summary['functions'] = [c['claim_id'] for c in api_claims if 'function' in c.get('claim_text', '').lower()]

    # Build enriched example inventory (TC-1044)
    from .enrich_examples import enrich_example

    example_inventory = []
    discovered_examples_path = run_layout.artifacts_dir / "discovered_examples.json"
    if discovered_examples_path.exists():
        with open(discovered_examples_path, 'r', encoding='utf-8') as f:
            discovered_examples = json.load(f)
            example_files = discovered_examples.get('example_file_details', [])
            example_repo_dir = run_layout.work_dir / "repo"
            if not example_repo_dir.exists():
                example_repo_dir = run_layout.work_dir
            # TC-2405: Pre-assign IDs sequentially (must happen before threads read dicts)
            for i, example_file in enumerate(example_files):
                example_file['example_id'] = f"example_{i+1}"
                example_file['primary_snippet_id'] = f"snippet_{i+1}"

            _n_ex = min(
                len(example_files),
                run_config.get("max_parallel_batches", 4) if run_config else 4,
            )
            if _n_ex <= 1 or len(example_files) <= 1:
                for example_file in example_files:
                    try:
                        example_inventory.append(
                            enrich_example(example_file, example_repo_dir, claims)
                        )
                    except Exception as e:
                        import logging
                        logging.getLogger(__name__).warning(f"Failed to enrich example: {e}")
                        example_inventory.append({
                            'example_id': example_file.get('example_id'),
                            'title': example_file.get('path', '').split('/')[-1],
                            'tags': example_file.get('tags', []),
                            'primary_snippet_id': example_file.get('primary_snippet_id'),
                        })
            else:
                from concurrent.futures import ThreadPoolExecutor, as_completed as _as_completed_ex
                _ex_results: dict = {}
                with ThreadPoolExecutor(max_workers=_n_ex, thread_name_prefix="ex_enrich") as pool:
                    _ex_futures = {
                        pool.submit(enrich_example, ef, example_repo_dir, claims): idx
                        for idx, ef in enumerate(example_files)
                    }
                    for fut in _as_completed_ex(_ex_futures):
                        idx = _ex_futures[fut]
                        ef = example_files[idx]
                        try:
                            _ex_results[idx] = fut.result()
                        except Exception as e:
                            import logging
                            logging.getLogger(__name__).warning(f"Failed to enrich example: {e}")
                            _ex_results[idx] = {
                                'example_id': ef.get('example_id'),
                                'title': ef.get('path', '').split('/')[-1],
                                'tags': ef.get('tags', []),
                                'primary_snippet_id': ef.get('primary_snippet_id'),
                            }
                example_inventory = [_ex_results[i] for i in range(len(example_files))]

    # Extract supported_platforms from compatibility claims (TC-1509)
    supported_platforms = repo_inventory.get('supported_platforms', [])
    if not supported_platforms:
        import re as _re
        for claim in claims:
            raw_kind = claim.get('claim_kind', 'feature')
            ck = REGISTRY.normalize_kind(raw_kind)
            if ck == 'compatibility':
                ctext = claim.get('claim_text', '').lower()
                for m in _re.finditer(r'python\s*(\d+\.\d+)\+?', ctext):
                    plat = f"Python {m.group(1)}+"
                    if plat not in supported_platforms:
                        supported_platforms.append(plat)
                for os_name in ['windows', 'linux', 'macos']:
                    if os_name in ctext:
                        pretty = os_name.title()
                        if pretty not in supported_platforms:
                            supported_platforms.append(pretty)

    # TC-1623: LLM workflow step generation for shallow workflows
    LLM_WORKFLOW_THRESHOLDS = {
        'installation': (8, 10),     # (min_steps, target_steps)
        'quickstart': (5, 8),
        'format_conversion': (4, 6),
    }

    if llm_client is not None:
        from .extract_claims import llm_generate_workflow_steps, compute_claim_id

        # TC-2405: Pre-filter workflows needing enrichment, then parallelize LLM calls.
        # Mutations (claims.append, wf['steps'].append) applied in main thread after as_completed.
        _pending_wfs = []
        for wf in workflows:
            tag = wf.get('workflow_tag', '')
            if tag not in LLM_WORKFLOW_THRESHOLDS:
                continue
            min_steps, target_steps = LLM_WORKFLOW_THRESHOLDS[tag]
            if len(wf.get('steps', [])) >= min_steps:
                continue  # Already has enough steps
            _pending_wfs.append((wf, tag, min_steps, target_steps))

        if _pending_wfs:
            def _call_llm_for_wf(wf, tag, target_steps):
                existing = [s.get('name', '') for s in wf.get('steps', [])]
                return wf, tag, wf.get('steps', [])[:], llm_generate_workflow_steps(
                    workflow_tag=tag,
                    workflow_title=wf.get('title', tag),
                    existing_steps=existing,
                    api_surface=api_surface_summary,
                    positioning=code_analysis.get('positioning', {}),
                    product_name=product_name,
                    llm_client=llm_client,
                    target_steps=target_steps,
                )

            _n_wf = min(
                len(_pending_wfs),
                run_config.get("max_parallel_batches", 4) if run_config else 4,
            )
            if _n_wf <= 1:
                # Sequential path — identical to pre-TC-2405 behavior
                for wf, tag, _min_steps, target_steps in _pending_wfs:
                    current_steps = wf.get('steps', [])
                    try:
                        _, _, _, new_steps = _call_llm_for_wf(wf, tag, target_steps)
                        if new_steps:
                            max_step_num = max((s.get('step_num', 0) for s in current_steps), default=0)
                            for i, ns in enumerate(new_steps, start=1):
                                step_num = max_step_num + i
                                claim_text = ns.get('claim_text', ns.get('name', f'Step {step_num}'))
                                claim_kind = 'workflow'
                                claim_id = compute_claim_id(claim_text, claim_kind, product_name)
                                claims.append({'claim_id': claim_id, 'claim_text': claim_text,
                                               'claim_kind': claim_kind, 'truth_status': 'inference',
                                               'confidence': 'medium', 'source_type': 'llm_synthesized',
                                               'citations': [], 'step_order': step_num})
                                wf['steps'].append({'step_num': step_num, 'step_id': f'step_{step_num}',
                                                    'name': claim_text, 'claim_id': claim_id, 'snippet_id': None})
                                wf['claim_ids'].append(claim_id)
                            total = len(wf['steps'])
                            wf['complexity'] = 'simple' if total <= 3 else ('moderate' if total <= 6 else 'complex')
                            wf['estimated_time_minutes'] = 5 + (total - 1) * 2
                            logger.info("llm_workflow_steps_generated", workflow_tag=tag,
                                        existing_steps=len(current_steps), new_steps=len(new_steps),
                                        total_steps=len(wf['steps']))
                    except Exception as e:
                        logger.warning("llm_workflow_generation_failed", workflow_tag=tag, error=str(e))
            else:
                from concurrent.futures import ThreadPoolExecutor, as_completed as _as_completed_wf
                with ThreadPoolExecutor(max_workers=_n_wf, thread_name_prefix="wf_enrich") as pool:
                    _wf_futures = [
                        pool.submit(_call_llm_for_wf, wf, tag, target_steps)
                        for wf, tag, _min_steps, target_steps in _pending_wfs
                    ]
                    for fut in _as_completed_wf(_wf_futures):
                        try:
                            wf, tag, current_steps_snap, new_steps = fut.result()
                            if new_steps:
                                # current_steps_snap is a copy taken before LLM call
                                max_step_num = max((s.get('step_num', 0) for s in current_steps_snap), default=0)
                                for i, ns in enumerate(new_steps, start=1):
                                    step_num = max_step_num + i
                                    claim_text = ns.get('claim_text', ns.get('name', f'Step {step_num}'))
                                    claim_kind = 'workflow'
                                    claim_id = compute_claim_id(claim_text, claim_kind, product_name)
                                    claims.append({'claim_id': claim_id, 'claim_text': claim_text,
                                                   'claim_kind': claim_kind, 'truth_status': 'inference',
                                                   'confidence': 'medium', 'source_type': 'llm_synthesized',
                                                   'citations': [], 'step_order': step_num})
                                    wf['steps'].append({'step_num': step_num, 'step_id': f'step_{step_num}',
                                                        'name': claim_text, 'claim_id': claim_id,
                                                        'snippet_id': None})
                                    wf['claim_ids'].append(claim_id)
                                total = len(wf['steps'])
                                wf['complexity'] = 'simple' if total <= 3 else ('moderate' if total <= 6 else 'complex')
                                wf['estimated_time_minutes'] = 5 + (total - 1) * 2
                                logger.info("llm_workflow_steps_generated", workflow_tag=tag,
                                            existing_steps=len(current_steps_snap), new_steps=len(new_steps),
                                            total_steps=len(wf['steps']))
                        except Exception as e:
                            logger.warning("llm_workflow_generation_failed", workflow_tag="unknown", error=str(e))

    # TC-1901: Sanitize code fence markers from claim text.
    # install_steps and other claims sometimes contain literal ```bash or
    # ```python from README code blocks, which nest inside templates.
    from .extract_claims import _sanitize_claim_text
    for claim in claims:
        original = claim.get('claim_text', '')
        sanitized = _sanitize_claim_text(original)
        if sanitized != original:
            claim['claim_text'] = sanitized

    # Assemble product_facts
    product_facts = {
        'schema_version': '1.0.0',
        'product_name': product_name,
        'product_family': product_family,
        'product_slug': product_slug,
        'repo_url': repo_url,
        'repo_sha': repo_sha,
        # Positioning from code analysis (TC-1042)
        'positioning': {
            'tagline': code_analysis.get("positioning", {}).get("tagline") or f"{product_name} - Product tagline",
            'short_description': code_analysis.get("positioning", {}).get("short_description") or f"A product for working with {product_name}",
            # TC-1612: Pass through audience and who_it_is_for from code_analysis if present
            **({k: v for k, v in code_analysis.get("positioning", {}).items() if k in ['audience', 'who_it_is_for'] and v})
        },
        'supported_platforms': supported_platforms,
        'claims': claims,
        # TC-1703: Cap claim groups to prevent bloat and ensure quality
        'claim_groups': {
            'key_features': sorted(set(key_features))[:25],
            'install_steps': sorted(set(install_steps))[:15],
            'quickstart_steps': sorted(set(quickstart_steps))[:10],
            'workflow_claims': sorted(set(workflow_claims))[:12],
            'limitations': sorted(set(limitations))[:15],
            'compatibility_notes': sorted(set(compatibility_notes))[:10],
            # TC-1632: New claim groups (Round 10 content types)
            'use_cases': sorted(set(use_cases))[:15],
            'faq': sorted(set(faq_claims))[:15],
            'best_practices': sorted(set(best_practices))[:15],
            'performance': sorted(set(performance_claims))[:10],
            'tutorials': sorted(set(tutorial_claims))[:10],
            'troubleshooting': sorted(set(troubleshooting_claims))[:15],
        },
        'supported_formats': supported_formats,
        'workflows': workflows,
        'api_surface_summary': api_surface_summary,
        'example_inventory': example_inventory,
    }

    # TC-1702: Troubleshooting Fallback — if no troubleshooting claims found,
    # synthesize from limitation claims or error messages in code
    ts_group = product_facts['claim_groups'].get('troubleshooting', [])
    if len(ts_group) < 3:
        # Promote limitation claims as troubleshooting fallback
        lim_ids = product_facts['claim_groups'].get('limitations', [])
        claim_id_set = {c.get('claim_id') for c in claims}
        for lid in lim_ids:
            if lid not in set(ts_group) and lid in claim_id_set:
                ts_group.append(lid)
            if len(ts_group) >= 5:
                break
        # Also promote any error_messages that aren't already in troubleshooting
        for claim in claims:
            if claim.get('source_type') == 'source_code' and claim.get('claim_kind') == 'troubleshooting':
                cid = claim.get('claim_id', '')
                if cid and cid not in set(ts_group):
                    ts_group.append(cid)
                if len(ts_group) >= 10:
                    break
        product_facts['claim_groups']['troubleshooting'] = sorted(set(ts_group))[:15]
        logger.info(f"[W2] TC-1702: Troubleshooting fallback: {len(ts_group)} claims (promoted from limitations/code)")

    # TC-1612: Enrich positioning with audience and who_it_is_for
    if not product_facts['positioning'].get('audience'):
        product_facts['positioning']['audience'] = _infer_audience(
            claims, product_family, product_name
        )
    if not product_facts['positioning'].get('who_it_is_for'):
        product_facts['positioning']['who_it_is_for'] = _infer_who_it_is_for(
            claims, product_name, supported_formats
        )

    # Code structure from code analysis (TC-1042)
    code_structure = code_analysis.get("code_structure")
    if code_structure:
        product_facts["code_structure"] = code_structure

    # Version from code analysis (TC-1042)
    version = code_analysis.get("constants", {}).get("version")
    if version:
        product_facts["version"] = version

    # TC-1601: Populate distribution and version from manifest claims
    manifest_claims_list = [c for c in claims if c.get('source_type') == 'manifest']
    for mc in manifest_claims_list:
        claim_text = mc.get('claim_text', '')
        # Extract pip install command → distribution field
        # TC-1607: Use schema-compliant array format (product_facts.schema.json lines 345-389)
        if 'pip install' in claim_text.lower():
            pip_match = re.search(r'pip install (\S+)', claim_text)
            if pip_match:
                pip_pkg = pip_match.group(1)
                product_facts["distribution"] = [{
                    "method": "pip",
                    "identifier": pip_pkg,
                    "install_commands": [f"pip install {pip_pkg}"],
                }]
        # Extract version from "version X is the current release"
        if 'version' in claim_text.lower() and 'current release' in claim_text.lower():
            ver_match = re.search(r'version (\S+)', claim_text)
            if ver_match and "version" not in product_facts:
                product_facts["version"] = ver_match.group(1)

    # TC-1607: Populate runtime_requirements from manifest claims
    runtime_reqs = {}
    for mc in manifest_claims_list:
        ct = mc.get('claim_text', '')
        if 'requires Python' in ct or 'requires python' in ct.lower():
            import re as _rt_re
            ver_match = _rt_re.search(r'Python\s+([\d.><=!~]+)', ct)
            if ver_match:
                runtime_reqs.setdefault('language_versions', []).append(
                    f"Python {ver_match.group(1)}"
                )
    # Extract OS from compatibility claims
    for cc in claims:
        if cc.get('claim_kind') == 'compatibility':
            ctext = cc.get('claim_text', '').lower()
            for os_name in ['windows', 'linux', 'macos']:
                if os_name in ctext:
                    runtime_reqs.setdefault('os', [])
                    pretty = os_name.title()
                    if pretty not in runtime_reqs['os']:
                        runtime_reqs['os'].append(pretty)
    if runtime_reqs:
        product_facts["runtime_requirements"] = runtime_reqs

    # TC-1607: Populate dependencies from manifest claims
    deps_runtime = []
    for mc in manifest_claims_list:
        ct = mc.get('claim_text', '')
        if 'depends on' in ct.lower():
            # Extract dependency names after "depends on"
            dep_match = re.search(r'depends on (.+)', ct, re.IGNORECASE)
            if dep_match:
                deps_runtime = [d.strip() for d in dep_match.group(1).split(',')]
        elif 'zero runtime dependencies' in ct.lower() or 'zero dependencies' in ct.lower():
            deps_runtime = []  # Explicitly empty
    if deps_runtime or any(
        'zero' in mc.get('claim_text', '').lower() and 'dependenc' in mc.get('claim_text', '').lower()
        for mc in manifest_claims_list
    ):
        product_facts["dependencies"] = {"runtime": deps_runtime}

    # TC-1609: Populate license from repo inventory
    license_info = repo_inventory.get('license', {})
    if not license_info:
        # Fallback: scan repo_inventory files for LICENSE patterns
        for item in repo_inventory.get('files', []):
            path = item.get('path', '') if isinstance(item, dict) else str(item)
            if any(name in path.upper() for name in ['LICENSE', 'LICENCE', 'COPYING']):
                license_info = {'file_path': path}
                break
    if license_info:
        product_facts["license"] = {
            "spdx_id": license_info.get("spdx_id", ""),
            "name": license_info.get("name", license_info.get("type", "")),
            "file_path": license_info.get("file_path", license_info.get("path", "")),
        }
        if license_info.get("url"):
            product_facts["license"]["url"] = license_info["url"]

    # Feature profiles (TC-1411): structured feature groupings from claims
    try:
        from .feature_profiles import build_feature_profiles, synthesize_use_cases_from_profiles
        feature_profiles = build_feature_profiles(
            claims=claims,
            product_name=product_name,
            code_understanding=code_understanding,
        )
        product_facts["feature_profiles"] = feature_profiles

        # TC-1618: Synthesize use cases from feature profiles for marketing content
        if feature_profiles:
            from .extract_claims import compute_claim_id, classify_claim_kind
            synthesized_use_cases = synthesize_use_cases_from_profiles(
                feature_profiles, product_name
            )
            if synthesized_use_cases:
                # Generate claim_id for each synthesized use case
                for uc in synthesized_use_cases:
                    # Classify and assign claim_kind (should already be 'use_case')
                    claim_kind = classify_claim_kind(uc.get("claim_text", ""))
                    uc["claim_kind"] = "use_case"  # Override with explicit type
                    # Generate stable claim_id
                    uc["claim_id"] = compute_claim_id(
                        uc["claim_text"], uc["claim_kind"], product_name
                    )
                    # Add default truth_status
                    uc.setdefault("truth_status", "verified")
                    uc.setdefault("citations", [])

                # Add synthesized use cases to claims list
                claims.extend(synthesized_use_cases)
                logger.info(
                    "synthesized_use_cases_from_profiles",
                    product_name=product_name,
                    count=len(synthesized_use_cases),
                )
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Feature profiles failed: {e}")
        product_facts["feature_profiles"] = []

    # TC-1624: LLM use case and tutorial generation
    if llm_client is not None:
        try:
            from .feature_profiles import llm_generate_use_cases, llm_generate_tutorials
            from .extract_claims import compute_claim_id

            # Count existing use cases
            existing_use_case_texts = [
                c.get('claim_text', '') for c in claims
                if c.get('claim_kind') == 'use_case'
            ]

            if len(existing_use_case_texts) < 10:
                new_use_cases = llm_generate_use_cases(
                    api_surface=api_surface_summary,
                    supported_formats=supported_formats,
                    positioning=code_analysis.get('positioning', {}),
                    product_name=product_name,
                    existing_use_cases=existing_use_case_texts,
                    llm_client=llm_client,
                    target_count=15,
                )

                for uc in new_use_cases:
                    uc['claim_id'] = compute_claim_id(
                        uc['claim_text'], uc['claim_kind'], product_name
                    )
                    claims.append(uc)

                if new_use_cases:
                    logger.info(
                        "llm_use_cases_generated",
                        count=len(new_use_cases),
                        existing=len(existing_use_case_texts),
                    )

            # Count existing tutorials
            existing_tutorials = [
                c for c in claims if c.get('claim_kind') == 'tutorial'
            ]

            if len(existing_tutorials) < 3:
                new_tutorials = llm_generate_tutorials(
                    workflows=workflows,
                    api_surface=api_surface_summary,
                    positioning=code_analysis.get('positioning', {}),
                    product_name=product_name,
                    llm_client=llm_client,
                    target_count=5,
                )

                for t in new_tutorials:
                    t['claim_id'] = compute_claim_id(
                        t['claim_text'], t['claim_kind'], product_name
                    )
                    claims.append(t)

                if new_tutorials:
                    logger.info(
                        "llm_tutorials_generated",
                        count=len(new_tutorials),
                    )
        except Exception as e:
            logger.warning("llm_use_case_tutorial_generation_failed", error=str(e))

    # TC-1625: LLM FAQ and troubleshooting generation
    if llm_client is not None:
        try:
            from .extract_claims import (
                llm_generate_faq_entries,
                llm_generate_troubleshooting_entries,
                compute_claim_id,
            )

            # Gather limitation texts for LLM context
            limitation_texts = [
                c.get('claim_text', '') for c in claims
                if c.get('claim_kind') == 'limitation'
            ][:10]  # Cap at 10 for prompt size

            # Count existing FAQ
            existing_faq = [c for c in claims if c.get('claim_kind') == 'faq']
            if len(existing_faq) < 10:
                new_faqs = llm_generate_faq_entries(
                    limitation_claims=limitation_texts,
                    api_surface=api_surface_summary,
                    product_name=product_name,
                    llm_client=llm_client,
                    target_count=12,
                )
                for faq in new_faqs:
                    faq['claim_id'] = compute_claim_id(
                        faq['claim_text'], faq['claim_kind'], product_name
                    )
                    claims.append(faq)
                if new_faqs:
                    logger.info("llm_faq_generated", count=len(new_faqs))

            # Count existing troubleshooting
            existing_ts = [c for c in claims if c.get('claim_kind') == 'troubleshooting']
            if len(existing_ts) < 10:
                new_ts = llm_generate_troubleshooting_entries(
                    limitation_claims=limitation_texts,
                    api_surface=api_surface_summary,
                    product_name=product_name,
                    llm_client=llm_client,
                    target_count=10,
                )
                for ts in new_ts:
                    ts['claim_id'] = compute_claim_id(
                        ts['claim_text'], ts['claim_kind'], product_name
                    )
                    claims.append(ts)
                if new_ts:
                    logger.info("llm_troubleshooting_generated", count=len(new_ts))
        except Exception as e:
            logger.warning("llm_faq_troubleshooting_generation_failed", error=str(e))

    # TC-1626: LLM best practices and performance generation
    if llm_client is not None:
        try:
            from .extract_claims import (
                llm_generate_best_practices,
                llm_generate_performance_claims,
                compute_claim_id,
            )

            # First: harvest best_practices from code_understanding (already LLM-generated)
            cu_best_practices = []
            cu_perf_chars = []
            if code_understanding:
                cu_best_practices = code_understanding.get('best_practices', [])
                cu_perf_chars = code_understanding.get('performance_characteristics', [])

            # Convert code_understanding best_practices to claims if not already present
            for bp in cu_best_practices:
                if isinstance(bp, dict):
                    cat = bp.get('category', '')
                    rec = bp.get('recommendation', '')
                    rat = bp.get('rationale', '')
                    text = f"Best practice ({cat}): {rec}. {rat}" if rat else f"Best practice ({cat}): {rec}"
                    cid = compute_claim_id(text, 'best_practice', product_name)
                    if not any(c.get('claim_id') == cid for c in claims):
                        claims.append({
                            'claim_id': cid,
                            'claim_text': text,
                            'claim_kind': 'best_practice',
                            'truth_status': 'inference',
                            'confidence': 'medium',
                            'source_type': 'code_understanding',
                            'citations': [],
                        })

            # Convert code_understanding performance_characteristics to claims
            for pc in cu_perf_chars:
                if isinstance(pc, dict):
                    metric = pc.get('metric', '')
                    value = pc.get('value', '')
                    conds = pc.get('conditions', '')
                    text = f"{metric}: {value} ({conds})" if conds else f"{metric}: {value}"
                    cid = compute_claim_id(text, 'performance', product_name)
                    if not any(c.get('claim_id') == cid for c in claims):
                        claims.append({
                            'claim_id': cid,
                            'claim_text': text,
                            'claim_kind': 'performance',
                            'truth_status': 'inference',
                            'confidence': 'medium',
                            'source_type': 'code_understanding',
                            'citations': [],
                        })

            # Still below threshold? Generate via dedicated LLM call
            existing_bp = [c for c in claims if c.get('claim_kind') == 'best_practice']
            if len(existing_bp) < 8:
                code_patterns = [bp.get('recommendation', '') if isinstance(bp, dict) else str(bp) for bp in cu_best_practices]
                new_bps = llm_generate_best_practices(
                    api_surface=api_surface_summary,
                    code_patterns=code_patterns,
                    product_name=product_name,
                    llm_client=llm_client,
                    target_count=10,
                )
                for bp in new_bps:
                    bp['claim_id'] = compute_claim_id(
                        bp['claim_text'], bp['claim_kind'], product_name
                    )
                    claims.append(bp)
                if new_bps:
                    logger.info("llm_best_practices_generated", count=len(new_bps))

            # Performance claims
            existing_perf = [c for c in claims if c.get('claim_kind') == 'performance']
            if len(existing_perf) < 5:
                new_perfs = llm_generate_performance_claims(
                    api_surface=api_surface_summary,
                    product_name=product_name,
                    llm_client=llm_client,
                    target_count=5,
                )
                for pc in new_perfs:
                    pc['claim_id'] = compute_claim_id(
                        pc['claim_text'], pc['claim_kind'], product_name
                    )
                    claims.append(pc)
                if new_perfs:
                    logger.info("llm_performance_claims_generated", count=len(new_perfs))
        except Exception as e:
            logger.warning("llm_best_practices_generation_failed", error=str(e))

    # Plan A3: Validate LLM-synthesized claims — cap count and reject
    # fabricated metrics before they pollute downstream content.
    grounded_count = len([c for c in claims if c.get("source_type") != "llm_synthesized"])
    claims = _validate_synthesized_claims(claims, grounded_count)
    product_facts['claims'] = claims

    # Phase 1A: Single-pass rebuild of claim_groups after LLM synthesis.
    # REGISTRY.build_claim_groups() routes ALL claims (including LLM-synthesized)
    # in one pass, eliminating the need for second routing loop (TC-1632 fix)
    # and manual rebuild (TC-1900).
    product_facts['claim_groups'] = REGISTRY.build_claim_groups(
        claims, is_low_quality_fn=_is_low_quality_source
    )

    # TC-1733: Ensure critical claim groups have minimum population.
    # If any critical group has fewer than MIN_CRITICAL_CLAIMS, relax quality
    # filter for that group and re-scan claims to fill the gap.
    _CRITICAL_GROUPS = ("key_features", "install_steps", "workflow_claims")
    _MIN_CRITICAL_CLAIMS = 3
    claim_groups = product_facts['claim_groups']
    for group_key in _CRITICAL_GROUPS:
        group_ids = claim_groups.get(group_key, [])
        if len(group_ids) < _MIN_CRITICAL_CLAIMS:
            # Find claims that match this group's kind pattern but were filtered
            # (e.g., by low-quality check). Re-route WITHOUT quality filter.
            needed = _MIN_CRITICAL_CLAIMS - len(group_ids)
            existing = set(group_ids)
            candidates = []
            for c in claims:
                cid = c.get("claim_id", "")
                if cid in existing:
                    continue
                routed_group = REGISTRY.route_claim(c, is_low_quality=False)
                if routed_group == group_key:
                    candidates.append(cid)
            backfill = candidates[:needed]
            if backfill:
                claim_groups[group_key] = group_ids + backfill
                logger.info(
                    f"[W2] TC-1733: Backfilled {len(backfill)} claims into "
                    f"'{group_key}' (was {len(group_ids)}, now {len(group_ids) + len(backfill)})"
                )

    # TC-1512: Populate example_inventory from code_understanding when W1 found
    # no examples/ directory.  This harvests typical_usage from class profiles
    # and code from usage_workflows so downstream workers have code examples.
    if not example_inventory and code_understanding:
        for cls_profile in code_understanding.get('class_profiles', []):
            usage = cls_profile.get('typical_usage', '')
            if usage and len(usage) > 20 and not usage.startswith("# See source"):
                example_inventory.append({
                    'example_id': f"cu_{cls_profile['name'].lower()}",
                    'title': f"{cls_profile['name']} Usage",
                    'tags': ['api', cls_profile.get('module', '')],
                    'primary_snippet_id': '',
                    'description': cls_profile.get('purpose', ''),
                    'code': usage,
                })
        for workflow in code_understanding.get('usage_workflows', []):
            steps_code = '\n'.join(
                s.get('code', '') for s in workflow.get('steps', []) if s.get('code')
            )
            if steps_code:
                wf_name = workflow.get('name', 'workflow')
                example_inventory.append({
                    'example_id': f"wf_{wf_name.lower().replace(' ', '_')[:30]}",
                    'title': wf_name,
                    'tags': ['workflow'],
                    'primary_snippet_id': '',
                    'description': workflow.get('description', ''),
                    'code': steps_code,
                })
        # Update the product_facts since example_inventory was mutated
        product_facts['example_inventory'] = example_inventory

    # TC-1762: Incremental claim merging — stabilize claim IDs across runs
    # when incremental mode is enabled.  Must run AFTER all claim generation
    # (LLM synthesis, feature profiles, etc.) and AFTER claim_groups rebuild.
    try:
        rc = RunConfig.from_dict(run_config) if isinstance(run_config, dict) else run_config
        if rc is not None and rc.is_incremental_enabled():
            previous_path = rc.get_previous_run_path()
            if previous_path:
                previous_facts = run_layout.load_previous_artifact(
                    "product_facts.json", previous_path
                )
                if previous_facts:
                    merged_claims, inc_metadata = _merge_claims_incremental(
                        product_facts['claims'], previous_facts
                    )
                    product_facts['claims'] = merged_claims
                    product_facts['incremental_metadata'] = inc_metadata

                    # Rebuild claim_groups with merged claims (IDs may have changed)
                    product_facts['claim_groups'] = REGISTRY.build_claim_groups(
                        merged_claims, is_low_quality_fn=_is_low_quality_source
                    )

                    logger.info(
                        "incremental_merge_applied",
                        previous_run=previous_path,
                        matched=inc_metadata['matched'],
                        new=inc_metadata['new'],
                        deprecated=inc_metadata['deprecated'],
                    )
    except Exception as exc:
        # Incremental merge is best-effort — never block the pipeline
        logger.warning("incremental_claim_merge_skipped", error=str(exc))

    # TC-2342: Detect format conversions and how-to clusters
    try:
        conversion_data = detect_format_conversions(
            product_facts.get("claims", []),
            product_facts.get("api_surface_summary", {}),
            llm_client=llm_client,
            product_name=product_facts.get("product_name", ""),
            product_description=product_facts.get("description", ""),
        )
        product_facts["claim_groups"]["format_conversions"] = conversion_data["format_conversions"]
        product_facts["claim_groups"]["conversion_pairs"] = conversion_data["conversion_pairs"]
        product_facts["claim_groups"]["how_to_clusters"] = conversion_data["how_to_clusters"]
    except Exception as exc:
        logger.warning("format_conversion_detection_skipped", error=str(exc))

    return product_facts


def execute_extraction_phase(
    run_dir: Path,
    run_config: Optional[Dict[str, Any]] = None,
    run_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    span_id: Optional[str] = None,
) -> Dict[str, Any]:
    """W2a: Deterministic extraction phase. No LLM calls.

    Performs all deterministic operations:
    1. Code analysis (AST parsing, manifest extraction)
    2. Extract claims (heuristic, no LLM)
    3. Map evidence (Jaccard + TF-IDF similarity)
    4. Detect contradictions (Jaccard-based)
    5. Manifest claims + code limitations

    All outputs are fully reproducible with PYTHONHASHSEED=0.
    Can be cached and reused without re-running.

    Args:
        run_dir: Run directory path
        run_config: Run configuration dictionary
        run_id: Run identifier
        trace_id: Trace ID for telemetry
        span_id: Span ID for telemetry

    Returns:
        Dictionary with extraction results:
        {
            "status": "success" | "failed",
            "artifacts": { "extracted_claims": str, "evidence_map": str, "code_analysis": str },
            "metadata": { "total_claims": int, ... },
            "error": Optional[str]
        }
    """
    run_id = run_id or f"run_{uuid.uuid4().hex[:8]}"
    trace_id = trace_id or str(uuid.uuid4())
    span_id = span_id or str(uuid.uuid4())

    run_layout = RunLayout(run_dir=run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    # Load run_config if not provided
    if run_config is None:
        repo_root = Path(__file__).parent.parent.parent.parent.parent
        run_config_path = run_dir / "run_config.yaml"
        config_data = load_and_validate_run_config(repo_root, run_config_path)
        run_config_dict = config_data
    else:
        run_config_dict = run_config

    emit_event(
        run_layout, run_id, trace_id, span_id,
        "W2A_EXTRACTION_STARTED",
        {"worker": "W2a_Extractor", "task": "execute_extraction_phase"},
    )

    result = {"status": "success", "artifacts": {}, "metadata": {}, "error": None}

    try:
        repo_dir = run_layout.work_dir / "repo"
        if not repo_dir.exists():
            raise FactsBuilderError(f"Repository directory not found: {repo_dir}")

        # Step 1: Code analysis (deterministic)
        from .code_analyzer import analyze_repository_code

        repo_inventory_path = run_layout.artifacts_dir / "repo_inventory.json"
        if repo_inventory_path.exists():
            with open(repo_inventory_path, 'r', encoding='utf-8') as f:
                repo_inventory = json.load(f)
            product_name_for_analysis = (
                repo_inventory.get('product_name', '')
                or (run_config_dict or {}).get('product_name', '')
            )
            code_analysis = analyze_repository_code(repo_dir, repo_inventory, product_name_for_analysis)

            code_analysis_path = run_layout.artifacts_dir / "code_analysis.json"
            atomic_write_json(code_analysis_path, code_analysis)
            emit_artifact_written_event(
                run_layout, run_id, trace_id, span_id, "code_analysis.json", schema_id=None
            )
            result["artifacts"]["code_analysis"] = str(code_analysis_path)

        # Step 2: Extract claims (deterministic — no LLM)
        extracted_claims = extract_claims(
            repo_dir=repo_dir,
            run_dir=run_dir,
            llm_client=None,  # Force deterministic extraction
        )

        emit_artifact_written_event(
            run_layout, run_id, trace_id, span_id, "extracted_claims.json", schema_id=None
        )
        result["artifacts"]["extracted_claims"] = str(
            run_layout.artifacts_dir / "extracted_claims.json"
        )
        result["metadata"]["total_claims"] = extracted_claims["metadata"]["total_claims"]
        result["metadata"]["fact_claims"] = extracted_claims["metadata"]["fact_claims"]
        result["metadata"]["inference_claims"] = extracted_claims["metadata"]["inference_claims"]

        # Step 3: Map evidence (deterministic)
        evidence_map = map_evidence(
            repo_dir=repo_dir,
            run_dir=run_dir,
            llm_client=None,
            run_id=run_id,
            trace_id=trace_id,
            span_id=span_id,
        )

        emit_artifact_written_event(
            run_layout, run_id, trace_id, span_id,
            "evidence_map.json", schema_id="evidence_map.schema.json",
        )
        result["artifacts"]["evidence_map"] = str(
            run_layout.artifacts_dir / "evidence_map.json"
        )

        # Step 4: Detect contradictions (deterministic)
        evidence_map = detect_contradictions(
            run_dir=run_dir,
            llm_client=None,
        )

        emit_artifact_written_event(
            run_layout, run_id, trace_id, span_id,
            "evidence_map.json", schema_id="evidence_map.schema.json",
        )
        result["metadata"]["contradictions_detected"] = len(
            evidence_map.get("contradictions", [])
        )

        # Step 5: Manifest claims + code limitations (deterministic)
        setup_py_path = repo_dir / "setup.py"
        if setup_py_path.exists():
            try:
                from .code_analyzer import parse_setup_py

                manifest_data = parse_setup_py(setup_py_path)
                if manifest_data:
                    product_name_for_manifest = (
                        manifest_data.get("name", "")
                        or (run_config_dict or {}).get("product_name", "")
                    )
                    manifest_claims = _synthesize_manifest_claims(
                        manifest_data, product_name_for_manifest
                    )
                    existing_ids = {c["claim_id"] for c in evidence_map.get("claims", [])}
                    for mc in manifest_claims:
                        if mc["claim_id"] not in existing_ids:
                            evidence_map["claims"].append(mc)
                            existing_ids.add(mc["claim_id"])
                    evidence_map_path = run_layout.artifacts_dir / "evidence_map.json"
                    atomic_write_json(evidence_map_path, evidence_map)
            except Exception as e:
                logger.warning("w2a_manifest_claims_failed", error=str(e))

        try:
            from .code_analyzer import extract_code_limitations

            code_limitations = extract_code_limitations(
                repo_dir, (run_config_dict or {}).get('product_name', '')
            )
            if code_limitations:
                existing_ids = {c["claim_id"] for c in evidence_map.get("claims", [])}
                for lc in code_limitations:
                    if lc["claim_id"] not in existing_ids:
                        evidence_map["claims"].append(lc)
                evidence_map_path = run_layout.artifacts_dir / "evidence_map.json"
                atomic_write_json(evidence_map_path, evidence_map)
        except Exception as e:
            logger.warning("w2a_code_limitations_failed", error=str(e))

        emit_event(
            run_layout, run_id, trace_id, span_id,
            "W2A_EXTRACTION_COMPLETED",
            {
                "total_claims": result["metadata"]["total_claims"],
                "contradictions": result["metadata"]["contradictions_detected"],
            },
        )

        return result

    except (FactsBuilderClaimsError, FactsBuilderEvidenceError,
            FactsBuilderContradictionError) as e:
        raise
    except Exception as e:
        raise FactsBuilderError(f"Extraction phase failed: {e}") from e


def execute_synthesis_phase(
    run_dir: Path,
    run_config: Optional[Dict[str, Any]] = None,
    run_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    span_id: Optional[str] = None,
    llm_client: Optional[LLMProviderClient] = None,
) -> Dict[str, Any]:
    """W2b: LLM synthesis phase. Enhances W2a outputs.

    Requires W2a extraction phase artifacts on disk.
    Performs LLM-dependent operations:
    1. Code understanding (LLM with offline fallback)
    2. Classify claims (LLM with heuristic fallback)
    3. Enrich claims (LLM with offline fallback)
    4. Enrich claim text for key features (LLM)
    5. Assemble product_facts.json (with LLM supplemental generation)

    Args:
        run_dir: Run directory path
        run_config: Run configuration dictionary
        run_id: Run identifier
        trace_id: Trace ID for telemetry
        span_id: Span ID for telemetry
        llm_client: Optional LLM client (will auto-initialize from config if None)

    Returns:
        Dictionary with synthesis results:
        {
            "status": "success" | "failed",
            "artifacts": { "product_facts": str, "code_understanding": str },
            "metadata": { "claims_enriched": int, ... },
            "error": Optional[str]
        }
    """
    run_id = run_id or f"run_{uuid.uuid4().hex[:8]}"
    trace_id = trace_id or str(uuid.uuid4())
    span_id = span_id or str(uuid.uuid4())

    run_layout = RunLayout(run_dir=run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    run_config_dict = run_config or {}

    # Check W2a prerequisites early (before expensive config parsing)
    extracted_claims_path = run_layout.artifacts_dir / "extracted_claims.json"
    if not extracted_claims_path.exists():
        raise FactsBuilderError(
            "W2a extraction artifacts not found. Run execute_extraction_phase() first."
        )

    # Initialize LLM client if not provided
    if llm_client is None and isinstance(run_config_dict, dict) and run_config_dict.get("llm"):
        try:
            llm_client = create_llm_client_from_config(
                run_config=run_config_dict,
                run_dir=run_dir,
            )
        except Exception as e:
            logger.warning("w2b_llm_client_init_failed", error=str(e))

    emit_event(
        run_layout, run_id, trace_id, span_id,
        "W2B_SYNTHESIS_STARTED",
        {"worker": "W2b_Synthesizer", "llm_available": llm_client is not None},
    )

    result = {"status": "success", "artifacts": {}, "metadata": {}, "error": None}

    # TC-2529: Quality feedback loop — read feedback from prior run (synthesis path)
    _use_feedback_synth = (
        run_config_dict.get("use_feedback", False)
        if isinstance(run_config_dict, dict)
        else False
    )
    _w2b_feedback: Dict[str, Any] = {}
    _synth_snippet_threshold = 0.5
    if _use_feedback_synth:
        _fb_path_synth = run_layout.run_dir / "work" / "quality_feedback.json"
        if _fb_path_synth.exists():
            try:
                _w2b_feedback = json.loads(_fb_path_synth.read_text(encoding="utf-8"))
                _old_synth = _synth_snippet_threshold
                _synth_snippet_threshold = adjust_snippet_threshold_from_feedback(
                    _old_synth, _w2b_feedback,
                )
                logger.info(
                    "feedback_applied_synthesis similarity_threshold_before=%.3f similarity_threshold_after=%.3f",
                    _old_synth, _synth_snippet_threshold,
                )
                result["metadata"]["feedback_applied"] = True
                # TC-2530: Emit feedback delta artifact (synthesis path)
                _emit_feedback_delta(
                    run_dir=run_layout.run_dir,
                    worker="W2",
                    feedback=_w2b_feedback,
                    parameters_before={"similarity_threshold": _old_synth},
                    parameters_after={"similarity_threshold": _synth_snippet_threshold},
                )
            except Exception as _fb_synth_err:
                logger.warning("feedback_read_failed_synthesis error=%s", _fb_synth_err)
        else:
            logger.info("feedback_skip_synthesis quality_feedback.json not found")

    try:
        repo_dir = run_layout.work_dir / "repo"
        if not repo_dir.exists():
            raise FactsBuilderError(f"Repository directory not found: {repo_dir}")

        with open(extracted_claims_path, 'r', encoding='utf-8') as f:
            extracted_claims = json.load(f)

        evidence_map_path = run_layout.artifacts_dir / "evidence_map.json"
        if not evidence_map_path.exists():
            raise FactsBuilderError("evidence_map.json not found from W2a phase.")

        with open(evidence_map_path, 'r', encoding='utf-8') as f:
            evidence_map = json.load(f)

        # Load code_analysis.json from W2a
        code_analysis_path = run_layout.artifacts_dir / "code_analysis.json"
        code_analysis = {}
        if code_analysis_path.exists():
            with open(code_analysis_path, 'r', encoding='utf-8') as f:
                code_analysis = json.load(f)

        repo_inventory_path = run_layout.artifacts_dir / "repo_inventory.json"
        product_name = extracted_claims.get("product_name", "")
        if not product_name and repo_inventory_path.exists():
            with open(repo_inventory_path, 'r', encoding='utf-8') as f:
                product_name = json.load(f).get("product_name", "")

        # Step 1: Code understanding (LLM with offline fallback)
        try:
            from .code_understanding import build_code_understanding

            code_understanding = build_code_understanding(
                code_analysis=code_analysis,
                repo_dir=repo_dir,
                product_name=product_name,
                llm_client=llm_client,
            )
            code_understanding_path = run_layout.artifacts_dir / "code_understanding.json"
            atomic_write_json(code_understanding_path, code_understanding)
            emit_artifact_written_event(
                run_layout, run_id, trace_id, span_id,
                "code_understanding.json", schema_id=None,
            )
            result["artifacts"]["code_understanding"] = str(code_understanding_path)
        except Exception as e:
            logger.warning("w2b_code_understanding_failed", error=str(e))

        # Step 2: Classify claims (LLM with heuristic fallback)
        classify_enabled = True
        if isinstance(run_config_dict, dict):
            classify_enabled = run_config_dict.get("classify_claims", True)

        if classify_enabled and len(extracted_claims.get("claims", [])) > 0:
            try:
                from .classify_claims import classify_claims_batch

                n_claims = len(extracted_claims["claims"])
                classify_offline = llm_client is None or n_claims > 500
                classify_cache_dir = run_layout.run_dir / "cache" / "classified_claims"

                classified_claims = classify_claims_batch(
                    claims=extracted_claims["claims"],
                    product_name=product_name,
                    llm_client=llm_client if not classify_offline else None,
                    cache_dir=classify_cache_dir,
                    offline_mode=classify_offline,
                    repo_url=extracted_claims.get("repo_url", ""),
                    repo_sha=extracted_claims.get("repo_sha", ""),
                )

                pre_count = len(extracted_claims["claims"])
                extracted_claims["claims"] = classified_claims
                atomic_write_json(extracted_claims_path, extracted_claims)

                result["metadata"]["claims_classified"] = pre_count
                result["metadata"]["claims_after_classification"] = len(classified_claims)
            except Exception as e:
                logger.warning("w2b_classify_claims_failed", error=str(e))

        # Step 3: Enrich claims (LLM with offline fallback)
        enrich_enabled = True
        if isinstance(run_config_dict, dict):
            enrich_enabled = run_config_dict.get("enrich_claims", True)

        if enrich_enabled and len(extracted_claims.get("claims", [])) > 0:
            try:
                n_claims = len(extracted_claims["claims"])
                # TC-2300: Use config-driven limit instead of hardcoded 500
                max_enrich_claims = run_config_dict.get("max_enrich_claims", 1000) if isinstance(run_config_dict, dict) else 1000
                force_llm = run_config_dict.get("force_llm_enrich", False) if isinstance(run_config_dict, dict) else False
                offline_mode = llm_client is None or (n_claims > max_enrich_claims and not force_llm)

                if offline_mode and llm_client is not None and n_claims > max_enrich_claims:
                    logger.info(
                        "w2_enrich_offline",
                        reason="claim_count_exceeds_limit",
                        n_claims=n_claims,
                        limit=max_enrich_claims,
                        force_llm=force_llm,
                    )

                enrichment_cache_dir = run_layout.run_dir / "cache" / "enriched_claims"
                _enrich_timeout = run_config_dict.get("enrich_timeout_s", None) if isinstance(run_config_dict, dict) else None

                enriched_claims = enrich_claims_batch(
                    claims=extracted_claims["claims"],
                    product_name=product_name,
                    llm_client=llm_client,
                    cache_dir=enrichment_cache_dir,
                    offline_mode=offline_mode,
                    repo_url=extracted_claims.get("repo_url", ""),
                    repo_sha=extracted_claims.get("repo_sha", ""),
                    timeout=_enrich_timeout,
                )
                extracted_claims["claims"] = enriched_claims
                atomic_write_json(extracted_claims_path, extracted_claims)
                result["metadata"]["claims_enriched"] = len(enriched_claims)
            except Exception as e:
                logger.warning("w2b_enrich_claims_failed", error=str(e))

        # Step 4: Enrich claim text for key features (LLM)
        if llm_client is not None and len(extracted_claims.get("claims", [])) > 0:
            try:
                key_feature_ids = [
                    c["claim_id"] for c in extracted_claims["claims"]
                    if c.get("claim_kind") in ("feature", "api", "key_feature")
                ]
                # TC-2300: Use same config-driven limit for text enrichment
                max_enrich_claims = run_config_dict.get("max_enrich_claims", 1000) if isinstance(run_config_dict, dict) else 1000
                force_llm = run_config_dict.get("force_llm_enrich", False) if isinstance(run_config_dict, dict) else False
                offline_1622 = llm_client is None or (len(key_feature_ids) > max_enrich_claims and not force_llm)

                if offline_1622 and llm_client is not None and len(key_feature_ids) > max_enrich_claims:
                    logger.info(
                        "w2_enrich_text_offline",
                        reason="key_feature_count_exceeds_limit",
                        n_key_features=len(key_feature_ids),
                        limit=max_enrich_claims,
                        force_llm=force_llm,
                    )

                positioning = {}
                if code_analysis_path.exists():
                    with open(code_analysis_path, 'r', encoding='utf-8') as f:
                        positioning = json.load(f).get("positioning", {})

                enriched_text_claims = enrich_claim_text_batch(
                    claims=extracted_claims["claims"],
                    key_feature_ids=key_feature_ids,
                    product_name=product_name,
                    positioning=positioning,
                    llm_client=llm_client,
                    offline_mode=offline_1622,
                    batch_size=DEFAULT_BATCH_SIZE,
                    timeout=_enrich_timeout,
                )
                extracted_claims["claims"] = enriched_text_claims
                atomic_write_json(extracted_claims_path, extracted_claims)
                result["metadata"]["claims_text_enriched"] = sum(
                    1 for c in enriched_text_claims if "enriched_text" in c
                )
            except Exception as e:
                logger.warning("w2b_enrich_claim_text_failed", error=str(e))

        # Step 5: Assemble product_facts.json (with LLM supplemental generation)
        # Re-read evidence_map to include any W2a-added manifest/limitation claims
        with open(evidence_map_path, 'r', encoding='utf-8') as f:
            evidence_map = json.load(f)

        # Merge enriched claims into evidence_map for assembly
        evidence_map["claims"] = extracted_claims["claims"]

        product_facts = assemble_product_facts(
            run_layout, evidence_map,
            run_config=run_config_dict,
            llm_client=llm_client,
        )

        # TC-2438: Add citation_quality_score to claims when LAUNCH_REPO_PROFILING=1
        import os as _os
        if _os.environ.get("LAUNCH_REPO_PROFILING") == "1":
            try:
                _rp_path = run_layout.artifacts_dir / "repo_profile.json"
                if _rp_path.exists():
                    import json as _json
                    _repo_profile = _json.loads(_rp_path.read_text(encoding="utf-8"))
                    _source_weights = dict(_repo_profile.get("source_type_weights", {}))
                    if _source_weights:
                        # TC-2449: Boost example weight for examples-rich repos
                        _ex_sigs = _repo_profile.get("examples_signals", {})
                        if _ex_sigs.get("has_examples_folder"):
                            _source_weights["example"] = min(
                                1.0, _source_weights.get("example", 0.85) + 0.10
                            )
                            logger.info(
                                "[W2] examples_heavy repo: example source weight → %.2f",
                                _source_weights["example"],
                            )
                        from ..w1_repo_scout.repo_profiler import score_citation_quality as _scq
                        _scored = 0
                        for _claim in product_facts.get("claims", []):
                            _cits = _claim.get("citations", [])
                            _claim["citation_quality_score"] = round(
                                _scq(_cits, _source_weights), 4
                            )
                            _scored += 1
                        logger.info(
                            "[W2] Added citation_quality_score to %d claims", _scored
                        )
            except Exception as _cqs_err:
                logger.warning("[W2] citation_quality_score failed (non-fatal): %s", _cqs_err)

        output_path = run_layout.artifacts_dir / "product_facts.json"
        atomic_write_json(output_path, product_facts)
        emit_artifact_written_event(
            run_layout, run_id, trace_id, span_id,
            "product_facts.json", schema_id="product_facts.schema.json",
        )
        result["artifacts"]["product_facts"] = str(output_path)

        # TC-2513: Extract family capabilities (deterministic, no LLM)
        try:
            fc = _extract_family_capabilities(product_facts, run_config=run_config_dict)
            fc_path = run_layout.artifacts_dir / "family_capabilities.json"
            atomic_write_json(fc_path, fc)
            emit_artifact_written_event(
                run_layout, run_id, trace_id, span_id,
                "family_capabilities.json",
                schema_id="family_capabilities.schema.json",
            )
            result["artifacts"]["family_capabilities"] = str(fc_path)
            logger.info(
                "family_capabilities_extracted",
                family=fc.get("family", ""),
                keyword=fc.get("keyword", ""),
                conversion_pairs=len(fc.get("conversion_pairs", [])),
                feature_clusters=len(fc.get("feature_clusters", [])),
            )
        except Exception as _fc_err:
            logger.warning("family_capabilities_extraction_failed error=%s", _fc_err)

        # Step 6: Build ProductProfile from assembled facts
        try:
            from ...models.product_profile import ProductProfile

            profile = ProductProfile.from_product_facts(
                product_facts=product_facts,
                run_config=run_config_dict,
                code_analysis=code_analysis,
            )
            profile_path = run_layout.artifacts_dir / "product_profile.json"
            atomic_write_json(profile_path, profile.to_dict())
            emit_artifact_written_event(
                run_layout, run_id, trace_id, span_id,
                "product_profile.json", schema_id=None,
            )
            result["artifacts"]["product_profile"] = str(profile_path)
            logger.info(
                "product_profile_built",
                product_name=profile.product_name,
                category=profile.product_category,
                tone=profile.content_tone,
                complexity=profile.complexity_level,
                claim_kinds=len(profile.claim_summary),
                has_rich_content=profile.has_rich_content,
            )
        except Exception as e:
            logger.warning("w2b_product_profile_failed", error=str(e))

        emit_event(
            run_layout, run_id, trace_id, span_id,
            "W2B_SYNTHESIS_COMPLETED",
            {"claims_in_facts": len(product_facts.get("claims", []))},
        )

        return result

    except (FactsBuilderClaimsError, FactsBuilderEvidenceError,
            FactsBuilderContradictionError, FactsBuilderAssemblyError) as e:
        raise
    except Exception as e:
        raise FactsBuilderError(f"Synthesis phase failed: {e}") from e


def execute_facts_builder(
    run_dir: Path,
    run_config: Optional[Dict[str, Any]] = None,
    run_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    span_id: Optional[str] = None,
    llm_client: Optional[LLMProviderClient] = None,
) -> Dict[str, Any]:
    """Execute W2 FactsBuilder worker (TC-410 integrator).

    This is the main entry point for W2 FactsBuilder. It orchestrates all
    sub-workers in sequence:
    1. TC-411: Extract claims from documentation
    2. TC-412: Map evidence to claims
    3. TC-413: Detect and resolve contradictions
    4. Assemble final product_facts.json

    Args:
        run_dir: Run directory path
        run_config: Run configuration dictionary (optional, will load from disk if None)
        run_id: Run identifier (optional, generated if None)
        trace_id: Trace ID for telemetry (optional, generated if None)
        span_id: Span ID for telemetry (optional, generated if None)
        llm_client: Optional LLM client for claims extraction and evidence mapping

    Returns:
        Dictionary with completion status and artifact paths:
        {
            "status": "success" | "failed",
            "artifacts": {
                "extracted_claims": str,
                "evidence_map": str,
                "product_facts": str
            },
            "metadata": {
                "total_claims": int,
                "fact_claims": int,
                "inference_claims": int,
                "contradictions_detected": int,
                "auto_resolved": int
            },
            "error": Optional[str]
        }

    Raises:
        FactsBuilderClaimsError: If claims extraction fails
        FactsBuilderEvidenceError: If evidence mapping fails
        FactsBuilderContradictionError: If contradiction detection fails
        FactsBuilderAssemblyError: If product facts assembly fails

    Spec references:
    - specs/21_worker_contracts.md:98-125 (W2 FactsBuilder contract)
    - specs/28_coordination_and_handoffs.md (Worker coordination)
    """
    # Generate default IDs if not provided
    run_id = run_id or f"run_{uuid.uuid4().hex[:8]}"
    trace_id = trace_id or str(uuid.uuid4())
    span_id = span_id or str(uuid.uuid4())

    run_layout = RunLayout(run_dir=run_dir)

    # Ensure run directory exists
    run_dir.mkdir(parents=True, exist_ok=True)

    # Load run_config if not provided
    if run_config is None:
        repo_root = Path(__file__).parent.parent.parent.parent.parent
        run_config_path = run_dir / "run_config.yaml"
        config_data = load_and_validate_run_config(repo_root, run_config_path)
        run_config_obj = RunConfig.from_dict(config_data)
        run_config_dict = config_data
    else:
        run_config_obj = RunConfig.from_dict(run_config)
        run_config_dict = run_config

    # Extract telemetry context from run_config (passed by orchestrator)
    telemetry_client = run_config_dict.get("_telemetry_client") if isinstance(run_config_dict, dict) else None
    telemetry_run_id = run_config_dict.get("_telemetry_run_id") if isinstance(run_config_dict, dict) else None
    telemetry_trace_id = run_config_dict.get("_telemetry_trace_id") if isinstance(run_config_dict, dict) else trace_id
    telemetry_parent_span_id = run_config_dict.get("_telemetry_parent_span_id") if isinstance(run_config_dict, dict) else span_id

    # Initialize LLM client if not provided (uses shared factory with fallback support)
    if llm_client is None and hasattr(run_config_obj, 'llm') and run_config_obj.llm:
        try:
            llm_client = create_llm_client_from_config(
                run_config=run_config_dict,
                run_dir=run_dir,
                telemetry_client=telemetry_client,
                telemetry_run_id=telemetry_run_id or run_id,
                telemetry_trace_id=telemetry_trace_id,
                telemetry_parent_span_id=telemetry_parent_span_id,
            )
            if llm_client:
                logger.info(
                    "w2_llm_client_initialized",
                    model=llm_client.model,
                    api_base_url=llm_client.api_base_url,
                    api_key_present=llm_client.api_key is not None,
                    fallback_configured=llm_client.fallback_api_base_url is not None,
                    telemetry_enabled=telemetry_client is not None,
                )
        except Exception as e:
            logger.warning("w2_llm_client_init_failed", error=str(e))
            # Continue without LLM client (will use heuristic extraction)
            llm_client = None

    if llm_client is None:
        logger.warning(
            "w2_using_offline_path",
            message="No LLM client available. Code understanding and claim enrichment will use offline heuristics. "
                    "Documentation quality will be limited. Configure llm section in run_config to enable LLM.",
            llm_config_present=hasattr(run_config_obj, 'llm') and bool(run_config_obj.llm),
        )

    # Emit WORK_ITEM_STARTED
    emit_event(
        run_layout,
        run_id,
        trace_id,
        span_id,
        EVENT_WORK_ITEM_STARTED,
        {
            "worker": "W2_FactsBuilder",
            "task": "execute_facts_builder",
            "taskcard": "TC-410",
            "sub_workers": ["TC-411", "TC-412", "TC-413"],
        },
    )

    result = {
        "status": "success",
        "artifacts": {},
        "metadata": {},
        "error": None,
    }

    # TC-2529: Quality feedback loop — read feedback from prior run
    _use_feedback = (
        run_config_dict.get("use_feedback", False)
        if isinstance(run_config_dict, dict)
        else getattr(run_config_dict, "use_feedback", False)
    )
    _w2_feedback: Dict[str, Any] = {}
    _snippet_threshold = 0.5  # Default dedup threshold
    if _use_feedback:
        _feedback_path = run_layout.run_dir / "work" / "quality_feedback.json"
        if _feedback_path.exists():
            try:
                _w2_feedback = json.loads(_feedback_path.read_text(encoding="utf-8"))
                _old_threshold = _snippet_threshold
                _snippet_threshold = adjust_snippet_threshold_from_feedback(
                    _old_threshold, _w2_feedback,
                )
                logger.info(
                    "feedback_applied similarity_threshold_before=%.3f similarity_threshold_after=%.3f feedback_entries=%d",
                    _old_threshold,
                    _snippet_threshold,
                    len(_w2_feedback.get("pages", [])),
                )
                result["metadata"]["feedback_applied"] = True
                result["metadata"]["snippet_threshold_before"] = _old_threshold
                result["metadata"]["snippet_threshold_after"] = _snippet_threshold
                # TC-2530: Emit feedback delta artifact
                _emit_feedback_delta(
                    run_dir=run_layout.run_dir,
                    worker="W2",
                    feedback=_w2_feedback,
                    parameters_before={"similarity_threshold": _old_threshold},
                    parameters_after={"similarity_threshold": _snippet_threshold},
                )
            except Exception as _fb_err:
                logger.warning("feedback_read_failed error=%s", _fb_err)
                _w2_feedback = {}
        else:
            logger.info("feedback_skip quality_feedback.json not found, using default thresholds")
    else:
        result["metadata"]["feedback_applied"] = False

    try:
        # Get repo_dir from run_layout
        repo_dir = run_layout.work_dir / "repo"
        if not repo_dir.exists():
            raise FactsBuilderError(f"Repository directory not found: {repo_dir}")

        # Step 0.5: TC-1042 - Run code analysis (required for TC-1401)
        # Must run BEFORE extract_claims() so code_analysis.json exists for code-grounded claims
        from .code_analyzer import analyze_repository_code

        emit_event(
            run_layout,
            run_id,
            trace_id,
            span_id,
            "FACTS_BUILDER_STEP_STARTED",
            {"step": "TC-1042", "description": "Analyze repository code (TC-1401 prerequisite)"},
        )

        repo_inventory_path = run_layout.artifacts_dir / "repo_inventory.json"
        if repo_inventory_path.exists():
            with open(repo_inventory_path, 'r', encoding='utf-8') as f:
                repo_inventory = json.load(f)
            product_name_for_analysis = repo_inventory.get('product_name', '') or (run_config or {}).get('product_name', '')
            code_analysis = analyze_repository_code(repo_dir, repo_inventory, product_name_for_analysis)

            # Write code_analysis.json artifact (TC-1042, required for TC-1401)
            code_analysis_path = run_layout.artifacts_dir / "code_analysis.json"
            atomic_write_json(code_analysis_path, code_analysis)

            emit_artifact_written_event(
                run_layout, run_id, trace_id, span_id, "code_analysis.json", schema_id=None
            )

        emit_event(
            run_layout,
            run_id,
            trace_id,
            span_id,
            "FACTS_BUILDER_STEP_COMPLETED",
            {"step": "TC-1042", "status": "success"},
        )

        # Step 0.75: TC-1410 - Build LLM-powered code understanding
        emit_event(
            run_layout,
            run_id,
            trace_id,
            span_id,
            "FACTS_BUILDER_STEP_STARTED",
            {"step": "TC-1410", "description": "Build code understanding"},
        )

        try:
            from .code_understanding import build_code_understanding

            code_understanding = build_code_understanding(
                code_analysis=code_analysis,
                repo_dir=repo_dir,
                product_name=product_name_for_analysis,
                llm_client=llm_client,
            )

            # Write code_understanding.json artifact
            code_understanding_path = run_layout.artifacts_dir / "code_understanding.json"
            atomic_write_json(code_understanding_path, code_understanding)

            emit_artifact_written_event(
                run_layout, run_id, trace_id, span_id,
                "code_understanding.json", schema_id=None,
            )

            result["artifacts"]["code_understanding"] = str(code_understanding_path)

            emit_event(
                run_layout, run_id, trace_id, span_id,
                "FACTS_BUILDER_STEP_COMPLETED",
                {
                    "step": "TC-1410",
                    "status": "success",
                    "source": code_understanding.get("metadata", {}).get("source", "unknown"),
                    "classes_profiled": len(code_understanding.get("class_profiles", [])),
                },
            )
        except Exception as e:
            # Code understanding failure MUST NOT crash W2
            error_type = type(e).__name__
            error_str = str(e)
            is_auth_error = "401" in error_str or "403" in error_str or "auth" in error_str.lower()
            logger.warning(
                "code_understanding_failed",
                error=error_str,
                error_type=error_type,
                is_auth_error=is_auth_error,
                llm_model=llm_client.model if llm_client else "none",
                api_key_present=llm_client.api_key is not None if llm_client else False,
                suggestion="Check API key configuration" if is_auth_error else "Check LLM endpoint availability",
            )
            emit_event(
                run_layout, run_id, trace_id, span_id,
                "FACTS_BUILDER_STEP_COMPLETED",
                {"step": "TC-1410", "status": "skipped", "reason": error_str},
            )

        # Step 1: TC-411 - Extract claims
        emit_event(
            run_layout,
            run_id,
            trace_id,
            span_id,
            "FACTS_BUILDER_STEP_STARTED",
            {"step": "TC-411", "description": "Extract claims from documentation"},
        )

        try:
            extracted_claims = extract_claims(
                repo_dir=repo_dir,
                run_dir=run_dir,
                llm_client=llm_client,
            )
        except (ClaimsExtractionError, ClaimsValidationError) as e:
            raise FactsBuilderClaimsError(f"Claims extraction failed: {e}") from e

        # Emit artifact written event
        emit_artifact_written_event(
            run_layout, run_id, trace_id, span_id, "extracted_claims.json", schema_id=None
        )

        result["artifacts"]["extracted_claims"] = str(
            run_layout.artifacts_dir / "extracted_claims.json"
        )
        result["metadata"]["total_claims"] = extracted_claims["metadata"]["total_claims"]
        result["metadata"]["fact_claims"] = extracted_claims["metadata"]["fact_claims"]
        result["metadata"]["inference_claims"] = extracted_claims["metadata"]["inference_claims"]

        emit_event(
            run_layout,
            run_id,
            trace_id,
            span_id,
            "FACTS_BUILDER_STEP_COMPLETED",
            {"step": "TC-411", "status": "success", "claims_extracted": len(extracted_claims["claims"])},
        )

        # Handle edge case: zero claims extracted
        if len(extracted_claims["claims"]) == 0:
            logger.warning(
                "facts_builder_zero_claims",
                repo_url=extracted_claims.get("repo_url"),
                message="No claims extracted. Proceeding with empty ProductFacts.",
            )
            emit_event(
                run_layout,
                run_id,
                trace_id,
                span_id,
                "FACTS_BUILDER_ZERO_CLAIMS",
                {"repo_url": extracted_claims.get("repo_url")},
            )

        # Handle edge case: sparse claims (< 5)
        if len(extracted_claims["claims"]) < 5 and len(extracted_claims["claims"]) > 0:
            logger.warning(
                "facts_builder_sparse_claims",
                total_claims=len(extracted_claims["claims"]),
                message="Fewer than 5 claims extracted. Launch tier forced to minimal.",
            )
            emit_event(
                run_layout,
                run_id,
                trace_id,
                span_id,
                "FACTS_BUILDER_SPARSE_CLAIMS",
                {"total_claims": len(extracted_claims["claims"])},
            )

        # Step 1.25: TC-1402 - Classify claims to filter non-user-facing content
        # Per Content Quality Hardening Plan: filter internal_detail + developer_instruction
        classify_enabled = True
        if isinstance(run_config, dict):
            classify_enabled = run_config.get("classify_claims", True)
        elif hasattr(run_config_obj, "classify_claims"):
            classify_enabled = getattr(run_config_obj, "classify_claims", True)

        if classify_enabled and len(extracted_claims.get("claims", [])) > 0:
            emit_event(
                run_layout, run_id, trace_id, span_id,
                "FACTS_BUILDER_STEP_STARTED",
                {"step": "TC-1402", "description": "Classify claims"},
            )

            try:
                from .classify_claims import classify_claims_batch

                n_claims = len(extracted_claims["claims"])
                classify_offline = llm_client is None or n_claims > 500

                classify_cache_dir = run_layout.run_dir / "cache" / "classified_claims"

                pre_count = len(extracted_claims["claims"])
                classified_claims = classify_claims_batch(
                    claims=extracted_claims["claims"],
                    product_name=extracted_claims.get("product_name", ""),
                    llm_client=llm_client if not classify_offline else None,
                    cache_dir=classify_cache_dir,
                    offline_mode=classify_offline,
                    repo_url=extracted_claims.get("repo_url", ""),
                    repo_sha=extracted_claims.get("repo_sha", ""),
                )

                post_count = len(classified_claims)
                extracted_claims["claims"] = classified_claims

                # Re-write extracted_claims.json with filtered claims
                extracted_claims_path = run_layout.artifacts_dir / "extracted_claims.json"
                atomic_write_json(extracted_claims_path, extracted_claims)

                result["metadata"]["claims_classified"] = pre_count
                result["metadata"]["claims_after_classification"] = post_count
                result["metadata"]["claims_filtered"] = pre_count - post_count

                emit_event(
                    run_layout, run_id, trace_id, span_id,
                    "FACTS_BUILDER_STEP_COMPLETED",
                    {
                        "step": "TC-1402",
                        "status": "success",
                        "claims_before": pre_count,
                        "claims_after": post_count,
                        "claims_filtered": pre_count - post_count,
                    },
                )
            except Exception as e:
                logger.warning("classify_claims_failed", error=str(e))
                emit_event(
                    run_layout, run_id, trace_id, span_id,
                    "FACTS_BUILDER_STEP_COMPLETED",
                    {"step": "TC-1402", "status": "skipped", "reason": str(e)},
                )

        # Step 1.5: TC-1045 - Enrich claims via LLM (between TC-411 and TC-412)
        # Per spec 08 section 9.1: enrichment runs AFTER extraction, BEFORE evidence mapping
        enrich_enabled = True
        if isinstance(run_config, dict):
            enrich_enabled = run_config.get("enrich_claims", True)
        elif hasattr(run_config_obj, "enrich_claims"):
            enrich_enabled = getattr(run_config_obj, "enrich_claims", True)

        if enrich_enabled and len(extracted_claims.get("claims", [])) > 0:
            emit_event(
                run_layout,
                run_id,
                trace_id,
                span_id,
                "FACTS_BUILDER_STEP_STARTED",
                {"step": "TC-1045", "description": "Enrich claims via LLM"},
            )

            try:
                # TC-1730: Chunked LLM enrichment — priority-based top-N claims
                # get LLM enrichment, rest get enhanced offline heuristics.
                # Replaces hard 500-claim auto-offline cutoff.
                n_claims = len(extracted_claims.get("claims", []))
                enrichment_batch_size = 200  # Default from ruleset
                if isinstance(run_config, dict):
                    enrichment_batch_size = run_config.get(
                        "claims", {}
                    ).get("enrichment_batch_size", 200)

                # Set up cache directory per spec 08 section 5.2
                enrichment_cache_dir = run_layout.run_dir / "cache" / "enriched_claims"
                _enrich_timeout = run_config.get("enrich_timeout_s", None) if isinstance(run_config, dict) else None

                if llm_client is None:
                    # No LLM: all claims get offline enrichment
                    enriched_claims = enrich_claims_batch(
                        claims=extracted_claims["claims"],
                        product_name=extracted_claims.get("product_name", ""),
                        llm_client=None,
                        cache_dir=enrichment_cache_dir,
                        offline_mode=True,
                        repo_url=extracted_claims.get("repo_url", ""),
                        repo_sha=extracted_claims.get("repo_sha", ""),
                    )
                elif n_claims <= enrichment_batch_size:
                    # Small claim set: all get LLM enrichment
                    enriched_claims = enrich_claims_batch(
                        claims=extracted_claims["claims"],
                        product_name=extracted_claims.get("product_name", ""),
                        llm_client=llm_client,
                        cache_dir=enrichment_cache_dir,
                        offline_mode=False,
                        repo_url=extracted_claims.get("repo_url", ""),
                        repo_sha=extracted_claims.get("repo_sha", ""),
                        timeout=_enrich_timeout,
                    )
                else:
                    # Large claim set: top-N by priority get LLM, rest offline
                    llm_claims, offline_claims = _select_priority_claims(
                        extracted_claims["claims"],
                        extracted_claims.get("claim_groups", {}),
                        max_llm=enrichment_batch_size,
                    )
                    logger.info(
                        "enrichment_chunked",
                        total=n_claims,
                        llm_count=len(llm_claims),
                        offline_count=len(offline_claims),
                    )

                    # Enrich priority claims via LLM
                    llm_enriched = enrich_claims_batch(
                        claims=llm_claims,
                        product_name=extracted_claims.get("product_name", ""),
                        llm_client=llm_client,
                        cache_dir=enrichment_cache_dir,
                        offline_mode=False,
                        repo_url=extracted_claims.get("repo_url", ""),
                        repo_sha=extracted_claims.get("repo_sha", ""),
                        timeout=_enrich_timeout,
                    )

                    # Enrich remaining claims offline
                    offline_enriched = enrich_claims_batch(
                        claims=offline_claims,
                        product_name=extracted_claims.get("product_name", ""),
                        llm_client=None,
                        cache_dir=enrichment_cache_dir,
                        offline_mode=True,
                        repo_url=extracted_claims.get("repo_url", ""),
                        repo_sha=extracted_claims.get("repo_sha", ""),
                    )

                    enriched_claims = llm_enriched + offline_enriched

                # Update extracted_claims in-memory
                extracted_claims["claims"] = enriched_claims

                # Re-write extracted_claims.json with enrichment fields
                extracted_claims_path = run_layout.artifacts_dir / "extracted_claims.json"
                atomic_write_json(extracted_claims_path, extracted_claims)

                # Re-emit artifact written event for updated file
                emit_artifact_written_event(
                    run_layout, run_id, trace_id, span_id,
                    "extracted_claims.json", schema_id=None,
                )

                result["metadata"]["claims_enriched"] = len(enriched_claims)

                emit_event(
                    run_layout,
                    run_id,
                    trace_id,
                    span_id,
                    "FACTS_BUILDER_STEP_COMPLETED",
                    {
                        "step": "TC-1045",
                        "status": "success",
                        "claims_enriched": len(enriched_claims),
                    },
                )

            except Exception as enrichment_error:
                # Per spec 08 section 9.4: enrichment failure MUST NOT crash W2
                logger.error(
                    "claim_enrichment_integration_failed",
                    error=str(enrichment_error),
                    message="Claim enrichment failed; continuing with unenriched claims",
                )
                emit_event(
                    run_layout,
                    run_id,
                    trace_id,
                    span_id,
                    "CLAIM_ENRICHMENT_FAILED",
                    {
                        "error_type": type(enrichment_error).__name__,
                        "error_message": str(enrichment_error),
                    },
                )

        # Step 1.75: TC-1622 - Enrich claim text for key_features
        # Adds marketing-ready enriched_text field to key_feature claims via LLM
        if llm_client is not None and len(extracted_claims.get("claims", [])) > 0:
            emit_event(
                run_layout, run_id, trace_id, span_id,
                "FACTS_BUILDER_STEP_STARTED",
                {"step": "TC-1622", "description": "Enrich claim text for key features"},
            )

            try:
                # Load code_analysis for positioning context
                code_analysis_path_1622 = run_layout.artifacts_dir / "code_analysis.json"
                positioning_1622 = {}
                if code_analysis_path_1622.exists():
                    with open(code_analysis_path_1622, 'r', encoding='utf-8') as f:
                        ca_1622 = json.load(f)
                        positioning_1622 = ca_1622.get("positioning", {})

                # Build key_feature_ids from claim grouping logic
                # (matches assemble_product_facts grouping for feature/api claims)
                key_feature_ids_1622 = []
                for c in extracted_claims["claims"]:
                    ck = c.get("claim_kind", "feature")
                    if ck in ("feature", "api", "key_feature"):
                        key_feature_ids_1622.append(c["claim_id"])

                # TC-1630: Use candidate count (key_features only), not total claim count
                # Note pilot: 343 candidates < 500 → LLM enrichment runs
                # 3D pilot: ~60 candidates < 500 → LLM enrichment runs
                offline_1622 = llm_client is None or len(key_feature_ids_1622) > 500

                product_name_1622 = extracted_claims.get("product_name", "") or (run_config_dict or {}).get("product_name", "")
                _enrich_timeout_1622 = run_config.get("enrich_timeout_s", None) if isinstance(run_config, dict) else None

                enriched_text_claims = enrich_claim_text_batch(
                    claims=extracted_claims["claims"],
                    key_feature_ids=key_feature_ids_1622,
                    product_name=product_name_1622,
                    positioning=positioning_1622,
                    llm_client=llm_client,
                    offline_mode=offline_1622,
                    batch_size=DEFAULT_BATCH_SIZE,
                    timeout=_enrich_timeout_1622,
                )

                extracted_claims["claims"] = enriched_text_claims

                # Re-write extracted_claims.json with enriched_text fields
                extracted_claims_path = run_layout.artifacts_dir / "extracted_claims.json"
                atomic_write_json(extracted_claims_path, extracted_claims)

                enriched_text_count = sum(
                    1 for c in enriched_text_claims if "enriched_text" in c
                )
                result["metadata"]["claims_text_enriched"] = enriched_text_count

                emit_event(
                    run_layout, run_id, trace_id, span_id,
                    "FACTS_BUILDER_STEP_COMPLETED",
                    {
                        "step": "TC-1622",
                        "status": "success",
                        "claims_text_enriched": enriched_text_count,
                        "key_feature_candidates": len(key_feature_ids_1622),
                    },
                )

            except Exception as text_enrich_error:
                # TC-1622: Text enrichment failure MUST NOT crash W2
                logger.warning(
                    "enrich_claim_text_integration_failed",
                    error=str(text_enrich_error),
                    message="Claim text enrichment failed; continuing with original claim_text",
                )
                emit_event(
                    run_layout, run_id, trace_id, span_id,
                    "FACTS_BUILDER_STEP_COMPLETED",
                    {"step": "TC-1622", "status": "skipped", "reason": str(text_enrich_error)},
                )

        # Step 2: TC-412 - Map evidence
        emit_event(
            run_layout,
            run_id,
            trace_id,
            span_id,
            "FACTS_BUILDER_STEP_STARTED",
            {"step": "TC-412", "description": "Map evidence to claims"},
        )

        try:
            evidence_map = map_evidence(
                repo_dir=repo_dir,
                run_dir=run_dir,
                llm_client=llm_client,
                run_id=run_id,
                trace_id=trace_id,
                span_id=span_id,
            )
        except EvidenceMappingError as e:
            raise FactsBuilderEvidenceError(f"Evidence mapping failed: {e}") from e

        # Emit artifact written event
        emit_artifact_written_event(
            run_layout,
            run_id,
            trace_id,
            span_id,
            "evidence_map.json",
            schema_id="evidence_map.schema.json",
        )

        result["artifacts"]["evidence_map"] = str(
            run_layout.artifacts_dir / "evidence_map.json"
        )
        result["metadata"]["claims_with_evidence"] = evidence_map["metadata"]["claims_with_evidence"]

        emit_event(
            run_layout,
            run_id,
            trace_id,
            span_id,
            "FACTS_BUILDER_STEP_COMPLETED",
            {
                "step": "TC-412",
                "status": "success",
                "claims_with_evidence": evidence_map["metadata"]["claims_with_evidence"],
            },
        )

        # Step 3: TC-413 - Detect contradictions
        emit_event(
            run_layout,
            run_id,
            trace_id,
            span_id,
            "FACTS_BUILDER_STEP_STARTED",
            {"step": "TC-413", "description": "Detect and resolve contradictions"},
        )

        try:
            evidence_map = detect_contradictions(
                run_dir=run_dir,
                llm_client=llm_client,
            )
        except ContradictionDetectionError as e:
            raise FactsBuilderContradictionError(f"Contradiction detection failed: {e}") from e

        # Re-emit evidence_map artifact written event (it was updated)
        emit_artifact_written_event(
            run_layout,
            run_id,
            trace_id,
            span_id,
            "evidence_map.json",
            schema_id="evidence_map.schema.json",
        )

        contradictions = evidence_map.get("contradictions", [])
        result["metadata"]["contradictions_detected"] = len(contradictions)
        result["metadata"]["auto_resolved"] = evidence_map["metadata"].get("auto_resolved_contradictions", 0)

        emit_event(
            run_layout,
            run_id,
            trace_id,
            span_id,
            "FACTS_BUILDER_STEP_COMPLETED",
            {
                "step": "TC-413",
                "status": "success",
                "contradictions_detected": len(contradictions),
                "auto_resolved": result["metadata"]["auto_resolved"],
            },
        )

        # Handle edge case: contradictory evidence detected
        if len(contradictions) > 0:
            emit_event(
                run_layout,
                run_id,
                trace_id,
                span_id,
                "FACTS_BUILDER_CONTRADICTION_DETECTED",
                {
                    "total_contradictions": len(contradictions),
                    "auto_resolved": result["metadata"]["auto_resolved"],
                },
            )

        # Step 3.5: TC-1601 - Synthesize manifest claims from setup.py
        setup_py_path = repo_dir / "setup.py"
        if setup_py_path.exists():
            try:
                from .code_analyzer import parse_setup_py

                manifest_data = parse_setup_py(setup_py_path)
                if manifest_data:
                    product_name_for_manifest = (
                        manifest_data.get("name", "")
                        or (run_config_dict or {}).get("product_name", "")
                    )
                    manifest_claims = _synthesize_manifest_claims(
                        manifest_data, product_name_for_manifest
                    )
                    # Merge into evidence_map claims (avoid duplicates)
                    existing_ids = {c["claim_id"] for c in evidence_map.get("claims", [])}
                    added = 0
                    for mc in manifest_claims:
                        if mc["claim_id"] not in existing_ids:
                            evidence_map["claims"].append(mc)
                            existing_ids.add(mc["claim_id"])
                            added += 1

                    if added > 0:
                        # Re-write evidence_map with new claims
                        evidence_map_path = run_layout.artifacts_dir / "evidence_map.json"
                        atomic_write_json(evidence_map_path, evidence_map)

                        logger.info(
                            "manifest_claims_synthesized",
                            source="setup.py",
                            claims_added=added,
                            product_name=product_name_for_manifest,
                        )

                    emit_event(
                        run_layout, run_id, trace_id, span_id,
                        "FACTS_BUILDER_STEP_COMPLETED",
                        {
                            "step": "TC-1601",
                            "status": "success",
                            "manifest_source": "setup.py",
                            "claims_added": added,
                        },
                    )
            except Exception as e:
                logger.warning("manifest_claims_synthesis_failed", error=str(e))
                emit_event(
                    run_layout, run_id, trace_id, span_id,
                    "FACTS_BUILDER_STEP_COMPLETED",
                    {"step": "TC-1601", "status": "skipped", "reason": str(e)},
                )

        # Step 3.75: TC-1605 - Extract limitations from source code
        try:
            from .code_analyzer import extract_code_limitations
            code_limitations = extract_code_limitations(repo_dir, product_name_for_analysis)
            if code_limitations:
                existing_ids = {c["claim_id"] for c in evidence_map.get("claims", [])}
                new_count = 0
                for lc in code_limitations:
                    if lc["claim_id"] not in existing_ids:
                        evidence_map["claims"].append(lc)
                        new_count += 1
                if new_count > 0:
                    # Re-write evidence_map with new limitation claims
                    evidence_map_path = run_layout.artifacts_dir / "evidence_map.json"
                    atomic_write_json(evidence_map_path, evidence_map)
                logger.info(
                    "code_limitation_claims_extracted",
                    total=len(code_limitations),
                    new=new_count,
                    deduplicated=len(code_limitations) - new_count,
                )
        except Exception as e:
            logger.warning("code_limitation_extraction_failed", error=str(e))

        # Step 4: Assemble product_facts.json
        emit_event(
            run_layout,
            run_id,
            trace_id,
            span_id,
            "FACTS_BUILDER_STEP_STARTED",
            {"step": "assemble", "description": "Assemble product_facts.json"},
        )

        try:
            product_facts = assemble_product_facts(run_layout, evidence_map, run_config=run_config_dict, llm_client=llm_client)
        except FactsBuilderAssemblyError as e:
            raise FactsBuilderAssemblyError(f"Product facts assembly failed: {e}") from e

        # Write product_facts.json
        # TC-2438/TC-2449: Add citation_quality_score to claims when LAUNCH_REPO_PROFILING=1
        import os as _os
        if _os.environ.get("LAUNCH_REPO_PROFILING") == "1":
            try:
                _rp_path = run_layout.artifacts_dir / "repo_profile.json"
                if _rp_path.exists():
                    import json as _json
                    _repo_profile = _json.loads(_rp_path.read_text(encoding="utf-8"))
                    _source_weights = dict(_repo_profile.get("source_type_weights", {}))
                    if _source_weights:
                        # TC-2449: Boost example weight for examples-rich repos
                        _ex_sigs = _repo_profile.get("examples_signals", {})
                        if _ex_sigs.get("has_examples_folder"):
                            _source_weights["example"] = min(
                                1.0, _source_weights.get("example", 0.85) + 0.10
                            )
                            logger.info(
                                "[W2] examples_heavy repo: example source weight → %.2f",
                                _source_weights["example"],
                            )
                        from ..w1_repo_scout.repo_profiler import score_citation_quality as _scq
                        _scored = 0
                        for _claim in product_facts.get("claims", []):
                            _cits = _claim.get("citations", [])
                            _claim["citation_quality_score"] = round(
                                _scq(_cits, _source_weights), 4
                            )
                            _scored += 1
                        logger.info(
                            "[W2] Added citation_quality_score to %d claims", _scored
                        )
            except Exception as _cqs_err:
                logger.warning("[W2] citation_quality_score failed (non-fatal): %s", _cqs_err)

        output_path = run_layout.artifacts_dir / "product_facts.json"
        atomic_write_json(output_path, product_facts)

        # TC-2383: Source chunking for W5 retrieval
        try:
            from launch.workers.w2_facts_builder.chunk_sources import chunk_source_files
            repo_dir_str = run_config_dict.get("repo_dir", "") if isinstance(run_config_dict, dict) else getattr(run_config_dict, "repo_dir", "")
            # Fallback: pilots clone repo to work_dir/repo (repo_dir not set in run_config)
            if not repo_dir_str:
                _fallback = run_layout.work_dir / "repo"
                if _fallback.exists():
                    repo_dir_str = str(_fallback)
            if repo_dir_str:
                repo_dir_path = Path(repo_dir_str)
                if repo_dir_path.exists():
                    logger.info("w2_chunking_sources repo_dir=%s", repo_dir_str)
                    chunks = chunk_source_files(repo_dir_path)
                    source_chunks_path = run_layout.artifacts_dir / "source_chunks.json"
                    import json as _json
                    source_chunks_path.write_text(
                        _json.dumps({"chunks": chunks, "count": len(chunks)}, indent=2),
                        encoding="utf-8",
                    )
                    logger.info("w2_source_chunks_written count=%d", len(chunks))
        except Exception as _chunk_err:
            logger.warning("w2_source_chunking_failed error=%s", _chunk_err)

        # TC-2394: Topic discovery from source docs (B2: always produce manifest)
        try:
            from launch.workers.w2_facts_builder.topic_discovery import (
                discover_topics_from_docs,
                derive_deterministic_topics,
                validate_topic_coverage,
            )
            import json as _json

            _mandatory = (
                run_config.get("required_sections", ["products", "blog", "kb"])
                if isinstance(run_config, dict) else ["products", "blog", "kb"]
            )
            _all_claims = product_facts.get("claims", [])
            _product_name = product_facts.get("product_name", "")
            _product_desc = product_facts.get("description", "")
            doc_chunks: list = []

            if llm_client is not None:
                # LLM path: use source chunks + claims
                source_chunks_path = run_layout.artifacts_dir / "source_chunks.json"
                if source_chunks_path.exists():
                    chunks_data = _json.loads(source_chunks_path.read_text(encoding="utf-8"))
                    doc_chunks = chunks_data.get("chunks", [])
                claim_groups = product_facts.get("claim_groups", {})
                topics = discover_topics_from_docs(
                    doc_chunks,
                    claim_groups,
                    llm_client,
                    claims=_all_claims,
                    product_name=_product_name,
                    product_description=_product_desc,
                    mandatory_sections=_mandatory,
                    max_topics=12,
                )
                _method = "llm"
            else:
                # B2: Deterministic fallback — derive from claims only (offline mode)
                topics = derive_deterministic_topics(
                    _all_claims,
                    product_name=_product_name,
                    mandatory_sections=_mandatory,
                    max_topics=12,
                )
                _method = "deterministic_fallback"

            # B3: Coverage validation
            _warnings = validate_topic_coverage(topics, _mandatory)
            for _w in _warnings:
                logger.warning("w2_topic_coverage %s", _w)

            # Compute per-section counts
            _per_section: dict = {}
            for _t in topics:
                _s = _t.get("section", "docs")
                _per_section[_s] = _per_section.get(_s, 0) + 1

            topic_manifest = {
                "discovered_topics": topics,
                "method": _method,
                "per_section_counts": _per_section,
                "warnings": _warnings,
                "dedup_threshold": _snippet_threshold,
                "source_doc_count": len(doc_chunks),
                "claims_used": len(_all_claims),
            }
            topic_manifest_path = run_layout.artifacts_dir / "topic_manifest.json"
            topic_manifest_path.write_text(
                _json.dumps(topic_manifest, indent=2), encoding="utf-8"
            )
            logger.info(
                "w2_topic_discovery_complete method=%s count=%d warnings=%d",
                _method, len(topics), len(_warnings),
            )
        except Exception as _td_err:
            logger.warning("w2_topic_discovery_failed error=%s", _td_err)

        # Emit artifact written event
        emit_artifact_written_event(
            run_layout,
            run_id,
            trace_id,
            span_id,
            "product_facts.json",
            schema_id="product_facts.schema.json",
        )

        result["artifacts"]["product_facts"] = str(output_path)

        # TC-2513: Extract family capabilities (deterministic, no LLM)
        try:
            fc = _extract_family_capabilities(product_facts, run_config=run_config_dict)
            fc_path = run_layout.artifacts_dir / "family_capabilities.json"
            atomic_write_json(fc_path, fc)
            emit_artifact_written_event(
                run_layout, run_id, trace_id, span_id,
                "family_capabilities.json",
                schema_id="family_capabilities.schema.json",
            )
            result["artifacts"]["family_capabilities"] = str(fc_path)
            logger.info(
                "family_capabilities_extracted",
                family=fc.get("family", ""),
                keyword=fc.get("keyword", ""),
                conversion_pairs=len(fc.get("conversion_pairs", [])),
                feature_clusters=len(fc.get("feature_clusters", [])),
            )
        except Exception as _fc_err:
            logger.warning("family_capabilities_extraction_failed error=%s", _fc_err)

        emit_event(
            run_layout,
            run_id,
            trace_id,
            span_id,
            "FACTS_BUILDER_STEP_COMPLETED",
            {"step": "assemble", "status": "success"},
        )

        # Emit WORK_ITEM_FINISHED
        emit_event(
            run_layout,
            run_id,
            trace_id,
            span_id,
            EVENT_WORK_ITEM_FINISHED,
            {
                "worker": "W2_FactsBuilder",
                "task": "execute_facts_builder",
                "taskcard": "TC-410",
                "status": "success",
                "artifacts_produced": list(result["artifacts"].keys()),
            },
        )

        # Emit telemetry events (per spec requirement)
        emit_event(
            run_layout,
            run_id,
            trace_id,
            span_id,
            "FACTS_BUILDER_STARTED",
            {"repo_url": evidence_map.get("repo_url")},
        )

        emit_event(
            run_layout,
            run_id,
            trace_id,
            span_id,
            "FACTS_BUILDER_COMPLETED",
            {
                "total_claims": result["metadata"]["total_claims"],
                "fact_claims": result["metadata"]["fact_claims"],
                "inference_claims": result["metadata"]["inference_claims"],
            },
        )

        logger.info(
            "facts_builder_completed",
            total_claims=result["metadata"]["total_claims"],
            contradictions_detected=result["metadata"]["contradictions_detected"],
            artifacts_produced=list(result["artifacts"].keys()),
            examples_processed_count=len(product_facts.get("example_inventory", [])),
        )

        return result

    except FactsBuilderClaimsError:
        # Re-raise our own exceptions as-is
        raise

    except FactsBuilderEvidenceError:
        # Re-raise our own exceptions as-is
        raise

    except FactsBuilderContradictionError:
        # Re-raise our own exceptions as-is
        raise

    except FactsBuilderAssemblyError:
        # Re-raise our own exceptions as-is
        raise

    except FileNotFoundError as e:
        # Missing dependencies
        error_msg = f"Missing required artifact or directory: {e}"
        result["status"] = "failed"
        result["error"] = error_msg

        # Emit failure event
        emit_event(
            run_layout,
            run_id,
            trace_id,
            span_id,
            "WORK_ITEM_FAILED",
            {
                "worker": "W2_FactsBuilder",
                "task": "execute_facts_builder",
                "taskcard": "TC-410",
                "error": error_msg,
                "error_type": "missing_artifact",
                "retryable": False,
            },
        )

        raise FactsBuilderError(error_msg) from e

    except Exception as e:
        # Unexpected errors
        error_msg = f"Unexpected error: {e}"
        result["status"] = "failed"
        result["error"] = error_msg

        # Emit failure event
        emit_event(
            run_layout,
            run_id,
            trace_id,
            span_id,
            "WORK_ITEM_FAILED",
            {
                "worker": "W2_FactsBuilder",
                "task": "execute_facts_builder",
                "taskcard": "TC-410",
                "error": error_msg,
                "error_type": "unexpected",
                "retryable": False,
            },
        )

        raise FactsBuilderError(error_msg) from e


# TC-2377: Quality Feedback Loop — W2 consumer helper

def adjust_snippet_threshold_from_feedback(
    default_threshold: float,
    feedback: Dict[str, Any],
) -> float:
    """Lower snippet similarity threshold if feedback indicates low snippet coverage.

    Reduces threshold by 0.05 (min 0.2) if any page has 'lower_snippet_threshold' action.
    Feature-flagged: only called when use_feedback=True.
    """
    pages_needing_lower = [
        p for p in feedback.get("pages", [])
        if "lower_snippet_threshold" in p.get("suggested_actions", [])
    ]
    if pages_needing_lower:
        adjusted = max(default_threshold - 0.05, 0.2)
        logger.info(
            "snippet_threshold_adjusted_from_feedback from_threshold=%.3f to_threshold=%.3f page_count=%d",
            default_threshold,
            adjusted,
            len(pages_needing_lower),
        )
        return adjusted
    return default_threshold


def _emit_feedback_delta(
    run_dir: Path,
    worker: str,
    feedback: Dict[str, Any],
    parameters_before: Dict[str, Any],
    parameters_after: Dict[str, Any],
) -> None:
    """TC-2530: Emit feedback_delta.json showing what feedback was consumed.

    Appends an entry to ``artifacts/feedback_delta.json``. If the file already
    exists (e.g. W2 wrote first, W4 appends), we load and extend it.

    Args:
        run_dir: Run directory path.
        worker: Worker identifier (e.g. "W2", "W4").
        feedback: Raw feedback dict that was read.
        parameters_before: Parameter values before adjustment.
        parameters_after: Parameter values after adjustment.
    """
    import datetime as _dt

    changes = []
    for key in sorted(set(parameters_before) | set(parameters_after)):
        old_val = parameters_before.get(key)
        new_val = parameters_after.get(key)
        if old_val != new_val:
            changes.append({
                "parameter": key,
                "old": old_val,
                "new": new_val,
                "reason": f"quality_feedback from prior run ({len(feedback.get('pages', []))} pages)",
            })

    entry = {
        "worker": worker,
        "feedback_source": "quality_feedback.json",
        "feedback_entries_read": len(feedback.get("pages", [])),
        "parameters_before": parameters_before,
        "parameters_after": parameters_after,
        "changes": changes,
        "timestamp_utc": _dt.datetime.now(_dt.timezone.utc).isoformat().replace("+00:00", "Z"),
    }

    artifacts_dir = run_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    delta_path = artifacts_dir / "feedback_delta.json"

    try:
        if delta_path.exists():
            existing = json.loads(delta_path.read_text(encoding="utf-8"))
        else:
            existing = {"schema_version": "1.0", "entries": []}

        existing["entries"].append(entry)
        atomic_write_json(delta_path, existing)
        logger.info(
            "feedback_delta_written worker=%s changes=%d path=%s",
            worker, len(changes), str(delta_path),
        )
    except Exception as _delta_err:
        logger.warning("feedback_delta_write_failed worker=%s error=%s", worker, _delta_err)
