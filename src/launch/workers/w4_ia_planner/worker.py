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
from collections import Counter
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

from ...io.run_layout import RunLayout
from ...io.artifact_store import ArtifactStore
from ...models.claim_registry import REGISTRY
from ...models.site_config import SiteConfig, DEFAULT_SITE_CONFIG
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
from ...content.template_registry import resolve_ruleset_path, resolve_templates_root
from .._shared.slug_constants import (
    FAMILY_KEYWORD_MAP as _FAMILY_KEYWORD_MAP,
    TOPIC_CATEGORY_MAP as _TOPIC_CATEGORY_MAP,
    extract_family_keyword as _extract_family_keyword,
)

logger = get_logger()


# ---------------------------------------------------------------------------
# TC-2478: Shared Facts extraction (deterministic, no LLM)
# ---------------------------------------------------------------------------

def _extract_shared_facts(
    product_facts: Dict[str, Any],
    repo_truth: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Extract canonical facts from product_facts for cross-page consistency.

    Deterministic extraction -- no LLM needed. Facts are the single source of
    truth for version numbers, format lists, and installation methods.

    When *repo_truth* is provided, its deterministic values for license and
    python_requires override claims-based extraction.
    """
    claims = product_facts.get("claims", [])
    code_structure = product_facts.get("code_structure", {})

    # 1. Python version: extract from claims mentioning "Python X.Y"
    python_versions: set = set()
    version_re = re.compile(r"[Pp]ython\s*(?:>=?\s*)?(\d+\.\d+)")
    for c in claims:
        for m in version_re.finditer(c.get("claim_text", "")):
            python_versions.add(m.group(1))
    sorted_versions = sorted(
        python_versions,
        key=lambda v: tuple(map(int, v.split("."))),
    )

    # 2. Supported formats (handles both dict items and plain strings)
    formats = product_facts.get("supported_formats", [])
    _raw_names: list = []
    for f in formats:
        if isinstance(f, dict):
            _name = f.get("format", "")
        elif isinstance(f, str):
            _name = f
        else:
            _name = ""
        if _name:
            _raw_names.append(_name.upper())
    format_names = sorted(set(_raw_names))

    # 3. Installation: from install_steps claim group
    install_claims_ids = product_facts.get("claim_groups", {}).get("install_steps", [])
    install_claim_texts = [
        c.get("claim_text", "") for c in claims
        if c.get("claim_id") in set(install_claims_ids)
    ]
    pip_re = re.compile(r"pip\s+install\s+[\w.-]+")
    pip_cmd = ""
    for text in install_claim_texts:
        m = pip_re.search(text)
        if m:
            pip_cmd = m.group(0)
            break

    # 4. Package name — code_structure uses "package_names" (plural list)
    pkg_names_raw = code_structure.get("package_names") or code_structure.get("package_name")
    if isinstance(pkg_names_raw, list):
        package_name = pkg_names_raw[0] if pkg_names_raw else ""
    elif isinstance(pkg_names_raw, str):
        package_name = pkg_names_raw
    else:
        package_name = ""
    # Defensive: reject Python type repr strings (e.g. "List", "dict") that the LLM
    # occasionally emits instead of an actual package name.  These cause G20-005 because
    # "List" ends up as the canonical pip package name injected into every W5 page.
    _PYTHON_TYPE_REPRS = frozenset({
        "list", "List", "dict", "Dict", "str", "Str", "None", "NoneType",
        "tuple", "Tuple", "int", "float", "bool", "set", "Set", "object",
    })
    if package_name in _PYTHON_TYPE_REPRS:
        package_name = ""
    if not package_name:
        # Fallback: scan claims for aspose import statement
        import_re = re.compile(r"import\s+(aspose[\w.]*)")
        for c in claims:
            m = import_re.search(c.get("claim_text", ""))
            if m:
                package_name = m.group(1)
                break
    if not package_name:
        # Last resort: pip install command
        if pip_cmd:
            pip_parts = pip_cmd.split()
            if len(pip_parts) >= 3:
                package_name = pip_parts[-1]

    # 5. License info (TC-2870: Truth enforcement — license consistency)
    license_info = product_facts.get("license", {})
    license_spdx = license_info.get("spdx_id", "") if isinstance(license_info, dict) else ""
    license_name = license_info.get("name", "") if isinstance(license_info, dict) else ""

    # 6. repo_truth override: deterministic facts take priority over claims-based extraction
    if repo_truth:
        rt_lic = repo_truth.get("license", {})
        if rt_lic.get("spdx_id"):
            license_spdx = rt_lic["spdx_id"]
            license_name = rt_lic.get("name", license_name)

        rt_py = repo_truth.get("python_requires", {})
        if rt_py.get("min"):
            # Insert deterministic minimum at front if not already present
            if rt_py["min"] not in sorted_versions:
                sorted_versions = sorted(
                    set(sorted_versions) | {rt_py["min"]},
                    key=lambda v: tuple(map(int, v.split("."))),
                )

    return {
        "schema_version": "1.1",
        "runtime_versions": {
            "python": {
                "minimum": sorted_versions[0] if sorted_versions else "",
                "all_mentioned": sorted_versions,
            }
        },
        "supported_formats": format_names,
        "installation_method": pip_cmd,
        "package_name": package_name,
        "product_display_name": product_facts.get("product_name", ""),
        "product_slug": product_facts.get("product_slug", ""),
        "supported_platforms": product_facts.get("supported_platforms", []),
        "license": {
            "spdx_id": license_spdx,
            "name": license_name,
        },
    }


# ---------------------------------------------------------------------------
# TC-2514: Family capabilities registry loader
# ---------------------------------------------------------------------------

def _load_family_capabilities(run_dir: Path) -> Optional[Dict[str, Any]]:
    """Load family_capabilities.json from artifacts directory if available.

    TC-2514: Reads the registry artifact produced by W2 containing the
    family keyword, supported formats, conversion pairs, and evidence refs.
    Returns None if the file is missing or invalid (backward compat).

    Args:
        run_dir: Path to run directory

    Returns:
        Parsed dict with keys: keyword, supported_formats, conversion_pairs, etc.
        None if file missing or malformed.
    """
    caps_path = run_dir / "artifacts" / "family_capabilities.json"
    try:
        if caps_path.exists():
            data = json.loads(caps_path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "keyword" in data:
                logger.debug("family_capabilities_loaded path=%s", caps_path)
                return data
            logger.debug("family_capabilities_invalid missing_keyword path=%s", caps_path)
            return None
        logger.debug("family_capabilities_not_found path=%s", caps_path)
        return None
    except (json.JSONDecodeError, OSError) as exc:
        logger.debug("family_capabilities_load_error error=%s path=%s", exc, caps_path)
        return None


# ---------------------------------------------------------------------------
# TC-2480/2481: Evidence-aware slug generation
# ---------------------------------------------------------------------------

# TC-2601: _FAMILY_KEYWORD_MAP imported from _shared.slug_constants

# Mapping generic how-to intent → evidence-aware slug template (TC-2604)
# All templates use {platform} for multi-platform support (Spec 45).
_HOWTO_SLUG_TEMPLATES = {
    "open": "how-to-load-{family_keyword}-{platform}",
    "save": "how-to-save-{family_keyword}-{platform}",
    "convert": "how-to-convert-{source_format}-to-{target_format}-{platform}",
    "fix": "how-to-fix-{family_keyword}-errors-{platform}",
    "performance": "how-to-optimize-{family_keyword}-{platform}",
}

# TC-2604: Fallback convert template when no format evidence is available
_CONVERT_FALLBACK_TEMPLATE = "how-to-convert-{family_keyword}-{platform}"

# TC-2601: _TOPIC_CATEGORY_MAP imported from _shared.slug_constants


# TC-2601: _extract_family_keyword imported from _shared.slug_constants
# (now accepts optional family_capabilities for registry override)


def _extract_top_formats(product_facts: Dict[str, Any]) -> Tuple[str, str]:
    """Extract top two formats from product_facts for conversion slug."""
    formats = product_facts.get("supported_formats", [])
    format_evidence: Dict[str, int] = {}
    for f in formats:
        if isinstance(f, dict):
            name = f.get("format", "").upper()
            evidence_count = len(f.get("claim_ids", []))
        elif isinstance(f, str):
            name = f.upper()
            evidence_count = 1
        else:
            continue
        if name:
            format_evidence[name] = format_evidence.get(name, 0) + evidence_count
    ranked = sorted(format_evidence.keys(), key=lambda k: (-format_evidence[k], k))
    source = ranked[0].lower() if len(ranked) > 0 else ""
    target = ranked[1].lower() if len(ranked) > 1 else "other"
    return source, target


def _extract_top_conversion_pair(product_facts: Dict[str, Any]) -> Tuple[str, str]:
    """Extract top conversion pair from product_facts claim_groups.

    TC-2840: Handles multiple input formats from W2 normalization:
    - List[List[str]]: [["PDF","DOCX"], ["XLSX","CSV"]] → ("PDF", "DOCX")
    - List[dict]:      [{"source":"PDF","target":"DOCX"}] → ("PDF", "DOCX")
    - List[str]:       ["PDF","DOCX"] (legacy flat) → ("PDF", "DOCX")
    """
    conversion_pairs = product_facts.get("claim_groups", {}).get("conversion_pairs", [])
    if not conversion_pairs or not isinstance(conversion_pairs, list):
        return ("", "")

    first = conversion_pairs[0]

    # Handle List[List[str]] from W2 normalization (e.g., [["PDF","DOCX"]])
    if isinstance(first, (list, tuple)) and len(first) >= 2:
        return (str(first[0]).upper(), str(first[1]).upper())

    # Handle List[dict] (e.g., [{"source":"PDF","target":"DOCX"}])
    if isinstance(first, dict):
        src = first.get("source", first.get("from", ""))
        tgt = first.get("target", first.get("to", ""))
        if src and tgt:
            return (str(src).upper(), str(tgt).upper())

    # Handle flat List[str] legacy (e.g., ["PDF","DOCX"])
    if isinstance(first, str) and len(conversion_pairs) >= 2:
        return (str(conversion_pairs[0]).upper(), str(conversion_pairs[1]).upper())

    return ("", "")


def _derive_evidence_aware_slug(
    title: str,
    product_slug: str,
    product_facts: Dict[str, Any],
    max_length: int = 40,
    family_capabilities: Optional[Dict[str, Any]] = None,
    platform: str = "python",
) -> str:
    """Generate evidence-aware slug for KB how-to pages (TC-2481, TC-2604).

    Maps generic titles to family-specific slugs using evidenced capabilities.
    Falls back to _derive_semantic_slug() if no evidence match.

    TC-2514: When *family_capabilities* (from ``family_capabilities.json``)
    is provided, its ``keyword``, ``conversion_pairs``, and
    ``supported_formats`` fields override the hardcoded maps and the
    product_facts extraction.  The hardcoded maps remain the fallback when
    the registry artifact is absent.

    TC-2604: All templates now use ``{platform}`` placeholder.  The
    *platform* parameter defaults to ``"python"`` for backward compat.
    For the ``convert`` intent, a fallback template using
    ``{family_keyword}`` is used when no format evidence is available.

    Examples:
        "How to Open a File" + 3D → "how-to-load-3d-models-python"
        "How to Convert Formats" + Cells → "how-to-convert-xlsx-to-csv-python"
    """
    title_lower = title.lower()

    # Detect intent from title
    intent = None
    for keyword in _HOWTO_SLUG_TEMPLATES:
        if keyword in title_lower:
            intent = keyword
            break

    if not intent:
        return _derive_semantic_slug(title, max_length)

    template = _HOWTO_SLUG_TEMPLATES[intent]

    # TC-2601: Unified registry-aware family keyword extraction
    family_keyword = _extract_family_keyword(product_slug, family_capabilities)

    context: Dict[str, str] = {
        "family_keyword": family_keyword,
        "source_format": "",
        "target_format": "",
        "platform": platform,
    }

    if intent == "convert":
        # TC-2514: Prefer registry conversion pairs, then product_facts, then top formats
        _resolved_pair = ("", "")
        if family_capabilities:
            _reg_pairs = family_capabilities.get("conversion_pairs", [])
            if isinstance(_reg_pairs, list) and len(_reg_pairs) >= 2:
                _resolved_pair = (str(_reg_pairs[0]).upper(), str(_reg_pairs[1]).upper())
        if not (_resolved_pair[0] and _resolved_pair[1]):
            _resolved_pair = _extract_top_conversion_pair(product_facts)
        if _resolved_pair[0] and _resolved_pair[1]:
            context["source_format"] = _resolved_pair[0].lower()
            context["target_format"] = _resolved_pair[1].lower()
        else:
            # TC-2514: Prefer registry formats, then product_facts extraction
            _has_formats = False
            if family_capabilities and family_capabilities.get("supported_formats"):
                _reg_fmts = family_capabilities["supported_formats"]
                if isinstance(_reg_fmts, list) and len(_reg_fmts) >= 2:
                    context["source_format"] = str(_reg_fmts[0]).lower()
                    context["target_format"] = str(_reg_fmts[1]).lower()
                    _has_formats = True
                elif isinstance(_reg_fmts, list) and len(_reg_fmts) == 1:
                    context["source_format"] = str(_reg_fmts[0]).lower()
                    context["target_format"] = "other"
                    _has_formats = True
            if not _has_formats:
                source, target = _extract_top_formats(product_facts)
                context["source_format"] = source
                context["target_format"] = target
                _has_formats = bool(source and target)

            # TC-2604: Fallback to family_keyword convert template when
            # no format evidence is available at all.
            if not _has_formats:
                template = _CONVERT_FALLBACK_TEMPLATE

    try:
        slug = template.format(**context)
    except (KeyError, IndexError):
        return _derive_semantic_slug(title, max_length)

    # Clean up: remove empty segments, enforce max length
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    if len(slug) > max_length:
        truncated = slug[:max_length]
        last_hyphen = truncated.rfind("-")
        if last_hyphen > 10:
            truncated = truncated[:last_hyphen]
        slug = truncated.strip("-")

    return slug or _derive_semantic_slug(title, max_length)


def _infer_topic_category(title: str) -> str:
    """Infer topic_category from page title keywords (TC-2481b)."""
    title_lower = title.lower()
    for keyword, category in _TOPIC_CATEGORY_MAP.items():
        if keyword in title_lower:
            return category
    return ""


def _infer_format_scope(title: str, product_facts: Dict[str, Any], product_slug: str) -> str:
    """Infer format_scope from title + evidence (TC-2481b)."""
    title_lower = title.lower()
    if "convert" in title_lower:
        pair = _extract_top_conversion_pair(product_facts)
        if pair[0] and pair[1]:
            return f"{pair[0]}-to-{pair[1]}"
        source, target = _extract_top_formats(product_facts)
        if source and target:
            return f"{source.upper()}-to-{target.upper()}"
    return ""


# ---------------------------------------------------------------------------
# TC-2515: Slug collision detection
# ---------------------------------------------------------------------------

def _detect_slug_collisions(page_plan: Dict[str, Any]) -> List[Dict[str, str]]:
    """Detect duplicate slugs within the same section in a page plan.

    Groups pages by section (using ``page_role`` as primary grouping key,
    falling back to ``section`` or ``subdomain``).  Within each group,
    identifies slugs that appear more than once.

    Args:
        page_plan: Complete page plan dict with ``pages`` list.

    Returns:
        Sorted list of collision dicts::

            [{"slug": "...", "section": "...", "pages": ["title1", "title2"]}]

        Empty list when no collisions are found.
    """
    pages = page_plan.get("pages", [])
    # Group slugs by section
    section_slugs: Dict[str, Dict[str, List[str]]] = {}
    for page in pages:
        section = page.get("section", page.get("subdomain", "unknown"))
        slug = page.get("slug", "")
        if not slug:
            continue
        if section not in section_slugs:
            section_slugs[section] = {}
        title = page.get("title", page.get("slug", "untitled"))
        if slug not in section_slugs[section]:
            section_slugs[section][slug] = []
        section_slugs[section][slug].append(title)

    collisions: List[Dict[str, str]] = []
    for section in sorted(section_slugs.keys()):
        for slug in sorted(section_slugs[section].keys()):
            titles = section_slugs[section][slug]
            if len(titles) > 1:
                collisions.append({
                    "slug": slug,
                    "section": section,
                    "pages": sorted(titles),
                })
    return collisions


def _slugify(text: str) -> str:
    """Convert text to URL-safe slug."""
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')


def _get_section_expansion(page_expansion: dict, section: str) -> dict:
    """Get expansion config for a section with safe defaults.

    Stage 2 hardening: Centralises access to page_expansion config so callers
    always receive a normalised dict with all expected keys present.

    Args:
        page_expansion: The ``page_expansion`` dict from run_config.
        section: Section name (e.g. "docs", "kb", "reference").

    Returns:
        Dict with keys ``enabled`` (bool), ``min_pages`` (int), ``max_pages`` (int).
    """
    cfg = page_expansion.get(section, {})
    if not isinstance(cfg, dict):
        cfg = {}
    return {
        "enabled": cfg.get("enabled", True),
        "min_pages": cfg.get("min_pages", 0),
        "max_pages": cfg.get("max_pages", 999),
    }


def select_claims_by_similarity(
    purpose: str,
    candidates: List[Dict[str, Any]],
    top_k: int,
) -> List[Dict[str, Any]]:
    """Select top-K claims most semantically relevant to the page purpose.

    TC-2366: Uses TF-IDF cosine similarity from embeddings.py to rank candidate
    claims by relevance to the page purpose string. Falls back to returning
    candidates[:top_k] if the embeddings module is unavailable or inputs are empty.

    Args:
        purpose: Page purpose string (from page_plan["pages"][i]["purpose"])
        candidates: List of claim dicts, each with a "claim_text" field
        top_k: Maximum number of claims to return

    Returns:
        Up to top_k claim dicts, ordered by descending cosine similarity to purpose.
        When similarity scores are all zero (no vocabulary overlap), returns
        candidates[:top_k] as a fallback.
    """
    if not candidates:
        return []
    if not purpose or top_k <= 0:
        return candidates[:top_k]

    try:
        from ..w2_facts_builder.embeddings import (
            tokenize,
            compute_idf,
            compute_tfidf_vector,
            cosine_similarity,
        )
    except ImportError:
        return candidates[:top_k]

    purpose_tokens = tokenize(purpose)
    claim_token_lists = [tokenize(c.get("claim_text", "")) for c in candidates]

    # Build IDF over the purpose + all claim texts
    all_docs = [purpose_tokens] + claim_token_lists
    idf = compute_idf(all_docs)
    purpose_vec = compute_tfidf_vector(purpose_tokens, idf)

    scored: List[tuple] = []
    for claim, tokens in zip(candidates, claim_token_lists):
        claim_vec = compute_tfidf_vector(tokens, idf)
        score = cosine_similarity(purpose_vec, claim_vec)
        scored.append((score, claim))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = [c for _, c in scored[:top_k]]

    # If all scores are zero (no vocabulary overlap), fall back to order-preserving slice
    if all(s == 0.0 for s, _ in scored[:top_k]):
        return candidates[:top_k]

    return top


_ENTITY_NAME_RE = re.compile(r'(?:[A-Z][a-z0-9]+){2,}|class\s+(\w+)|def\s+(\w+)')


def _extract_snippet_names(snippet: Dict[str, Any]) -> set:
    """Extract PascalCase identifiers and class/def names from snippet code + tags."""
    code = snippet.get("code", "")
    tags = snippet.get("tags", [])
    names: set = set()
    for m in _ENTITY_NAME_RE.finditer(code):
        names.add(m.group(1) or m.group(2) or m.group(0))
    for tag in tags:
        names.add(tag.lower())
    # Discard empty/None
    names.discard(None)
    names.discard("")
    return {n.lower() for n in names}


def link_claims_to_snippets(
    claims: List[Dict[str, Any]],
    snippet_catalog: Dict[str, Any],
    max_per_claim: int = 2,
) -> List[Dict[str, Any]]:
    """Link each claim to 0-2 most relevant code snippets via entity name matching.

    TC-2368: Claim-to-snippet binding (RCA S-2). Adds ``demo_snippet_ids``
    to each claim dict by matching entity names (PascalCase identifiers,
    class/def names, tags) between snippet code and claim text.

    This replaces TF-IDF cosine similarity which failed due to vocabulary
    mismatch between prose claims and code tokens.

    Args:
        claims: List of claim dicts (from product_facts["claims"]).
        snippet_catalog: Snippet catalog dict (from snippet_catalog.json).
        max_per_claim: Maximum snippets to link per claim (default 2).

    Returns:
        Updated claim list with ``demo_snippet_ids: List[str]`` on each claim.
        Claims that already have ``demo_snippet_ids`` set are not modified.
        If catalog is empty, returns claims unchanged.
    """
    snippets = snippet_catalog.get("snippets", [])
    if not snippets or not claims:
        return claims

    # Pre-extract entity names per snippet
    snippet_name_sets = [_extract_snippet_names(s) for s in snippets]

    updated: List[Dict[str, Any]] = []
    for claim in claims:
        c = dict(claim)
        # Idempotent: do not overwrite existing bindings
        if c.get("demo_snippet_ids") is not None:
            updated.append(c)
            continue

        claim_text_lower = c.get("claim_text", "").lower()
        scored = []
        for idx, (names, snippet) in enumerate(zip(snippet_name_sets, snippets)):
            if not names:
                continue
            # Score = count of snippet entity names mentioned in claim text
            score = sum(1 for n in names if n in claim_text_lower)
            if score > 0:
                scored.append((score, snippet.get("snippet_id", "")))

        scored.sort(key=lambda x: -x[0])
        c["demo_snippet_ids"] = [sid for _, sid in scored[:max_per_claim] if sid]
        updated.append(c)

    return updated


def check_pre_generation_redundancy(
    planned_pages: List[Dict[str, Any]],
    threshold: float = 0.6,
) -> List[Dict[str, Any]]:
    """Detect pages with overlapping content before generation.

    Compares: title + purpose + top-3 claim texts per page.
    Non-blocking: returns warnings only (does not abort planning).

    TC-2386: W4 Pre-Generation Duplication Check (D-4).
    """
    from launch.workers._shared.jaccard import compute_word_set, jaccard_similarity
    page_word_sets = []
    for page in planned_pages:
        title = page.get("title", "")
        purpose = page.get("purpose", "")
        claim_texts = " ".join(
            c.get("claim_text", "") for c in page.get("claims", [])[:3]
        )
        page_word_sets.append(compute_word_set(f"{title} {purpose} {claim_texts}"))

    warnings = []
    n = len(planned_pages)
    for i in range(n):
        for j in range(i + 1, n):
            sim = jaccard_similarity(page_word_sets[i], page_word_sets[j])
            if sim > threshold:
                warnings.append({
                    "page_a": planned_pages[i].get("slug", f"page_{i}"),
                    "page_b": planned_pages[j].get("slug", f"page_{j}"),
                    "similarity": round(sim, 3),
                    "suggestion": "Consider merging or scoping these pages differently",
                })
    return warnings


def assign_page_role(
    section: str,
    slug: str,
    is_index: bool = False,
    available_claims: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Assign page role based on claim-kind distribution (primary) and slug/section (fallback).

    TC-2364: Content-signal classification — uses the claim-kind distribution of
    available_claims to infer the most appropriate role. Slug/section matching is
    retained as a fallback tiebreaker when claim signals are ambiguous.

    Implements content distribution strategy from specs/08_content_distribution_strategy.md.

    Args:
        section: Section name (products, docs, reference, kb, blog)
        slug: Page slug
        is_index: True if this is an index/TOC page (_index.md)
        available_claims: Optional list of claim dicts with a "claim_kind" field.
            When provided and non-empty, claim-kind distribution overrides slug matching.

    Returns:
        Page role string (landing, toc, comprehensive_guide, workflow_page,
        feature_showcase, troubleshooting, api_reference, faq, tutorial, ...)
    """
    # TOC page detection — structural, not content-driven
    if is_index and section == "docs":
        return "toc"

    # Comprehensive guide detection (developer-guide pages) — structural
    if slug == "developer-guide" or slug.endswith("/developer-guide"):
        return "comprehensive_guide"

    # Landing page detection (products overview) — structural
    if slug in ["overview", "index", "_index"] and section == "products":
        return "landing"

    # TC-2364: Content-signal classification using claim-kind distribution
    if available_claims:
        kind_counts: Counter = Counter(
            c.get("claim_kind", "") for c in available_claims
        )
        total = len(available_claims)
        if total > 0:
            # Rules applied in priority order (most specific first)
            if kind_counts.get("api", 0) / total >= 0.4:
                return "api_reference"
            if kind_counts.get("workflow", 0) / total >= 0.4:
                return "workflow_page"
            if kind_counts.get("limitation", 0) / total >= 0.5:
                return "troubleshooting"
            if kind_counts.get("faq", 0) / total >= 0.3 or "faq" in slug:
                return "faq"
            if kind_counts.get("feature", 0) / total >= 0.4:
                return "feature_showcase"
            # Signal is ambiguous — fall through to slug-based logic

    # --- Slug / section fallback (unchanged from pre-TC-2364) ---

    # TC-2202: Getting-started detection (docs section)
    if slug in ("getting-started", "quickstart", "getting_started"):
        return "getting_started"

    # Section-specific role assignment
    if section == "docs":
        return "workflow_page"

    if section == "kb":
        # TC-1633: New page_role assignments for Round 10 content types
        if slug == "faq":
            return "faq"  # Dedicated FAQ role for Q&A content

        if slug == "best-practices":
            return "best_practices"  # Best practices categorized content

        if "tutorial" in slug:  # Matches "tutorials", "tutorial-*", etc.
            return "tutorial"  # Step-by-step tutorial content

        # TC-1714: Performance guide detection
        if "performance" in slug:
            return "performance_guide"

        # Feature showcase detection (how-to, howto, or showcase in slug)
        # TC-993: "howto" matches new KB template filenames (howto.variant-*.md)
        if "how-to" in slug or "howto" in slug or "showcase" in slug:
            return "feature_showcase"
        return "troubleshooting"

    if section == "reference":
        return "api_reference"

    # TC-1902: Blog pages must reach generate_blog_content() in W5
    if section == "blog":
        return "blog_announcement"

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
            "unique_angle": "Product value proposition and platform overview",
            "avoid_overlap_with": ["getting_started", "developer_guide"],
        }

    # TOC page
    elif page_role == "toc":
        strategy = {
            "primary_focus": "Navigation hub",
            "forbidden_topics": ["duplicate_child_content", "code_snippets"],
            "claim_quota": {"min": 0, "max": 2},
            "child_pages": [],  # Will be populated by post-processing
            "unique_angle": "Navigation and content discovery",
            "avoid_overlap_with": [],
        }

    # TC-2202: Getting started page
    elif page_role == "getting_started":
        strategy = {
            "primary_focus": "Installation and first working example",
            "forbidden_topics": ["advanced_scenarios", "troubleshooting"],
            "claim_quota": {"min": 3, "max": 8},
            "unique_angle": "Step-by-step setup and first working example",
            "avoid_overlap_with": ["installation", "overview"],
        }

    # Comprehensive guide
    elif page_role == "comprehensive_guide":
        strategy = {
            "primary_focus": "All usage scenarios",
            "forbidden_topics": ["installation", "troubleshooting"],
            "claim_quota": {"min": len(workflows), "max": 50},
            "scenario_coverage": "all",
            "unique_angle": "All usage scenarios, advanced features, and workflow combinations",
            "avoid_overlap_with": ["getting_started", "tutorial"],
        }

    # Workflow page
    elif page_role == "workflow_page":
        strategy = {
            "primary_focus": "How-to guide",
            "forbidden_topics": ["other_workflows"],
            "claim_quota": {"min": 3, "max": 8},
            "unique_angle": "Single workflow end-to-end with code",
            "avoid_overlap_with": ["comprehensive_guide"],
        }

    # Feature showcase
    elif page_role == "feature_showcase":
        strategy = {
            "primary_focus": "Prominent feature how-to",
            "forbidden_topics": ["general_features", "api_reference", "other_features"],
            "claim_quota": {"min": 3, "max": 8},
            "unique_angle": "Deep dive into a single feature with practical examples",
            "avoid_overlap_with": ["developer_guide", "overview"],
        }

    # Troubleshooting
    elif page_role == "troubleshooting":
        strategy = {
            "primary_focus": "Problem-solution",
            "forbidden_topics": ["features", "installation"],
            "claim_quota": {"min": 1, "max": 5},
            "unique_angle": "Diagnosis and fixes for specific error messages and failure modes",
            "avoid_overlap_with": ["faq"],
        }

    # TC-1633: FAQ page (Q&A content)
    elif page_role == "faq":
        strategy = {
            "primary_focus": "Common questions and answers",
            "forbidden_topics": [],
            "claim_quota": {"min": 5, "max": 15},
            "content_approach": "q_and_a",
            "unique_angle": "Direct answers to specific developer questions — NOT a rehash of docs",
            "avoid_overlap_with": ["getting_started", "troubleshooting"],
        }

    # TC-1633: Best practices page (categorized recommendations)
    elif page_role == "best_practices":
        strategy = {
            "primary_focus": "Best practice recommendations",
            "forbidden_topics": [],
            "claim_quota": {"min": 5, "max": 15},
            "content_approach": "categorized_bullets",
            "unique_angle": "Performance optimization, error handling patterns, production readiness",
            "avoid_overlap_with": ["developer_guide"],
        }

    # TC-1633: Tutorial page (step-by-step guides)
    elif page_role == "tutorial":
        strategy = {
            "primary_focus": "Step-by-step tutorial",
            "forbidden_topics": [],
            "claim_quota": {"min": 3, "max": 10},
            "content_approach": "sequential_steps",
            "unique_angle": "End-to-end walkthrough of a real-world task with explanations",
            "avoid_overlap_with": ["getting_started", "developer_guide"],
        }

    # TC-2204: API reference
    elif page_role == "api_reference":
        strategy = {
            "primary_focus": "API class/method catalog",
            "forbidden_topics": ["tutorials", "installation"],
            "claim_quota": {"min": 5, "max": 25},
            "unique_angle": "Complete class/method/module catalog with signatures and brief descriptions",
            "avoid_overlap_with": ["developer_guide"],
        }

    # TC-2204: Blog announcement
    elif page_role == "blog_announcement":
        strategy = {
            "primary_focus": "Product announcement and highlights",
            "forbidden_topics": [],
            "claim_quota": {"min": 10, "max": 20},
            "unique_angle": "Product value proposition, key differentiators, real-world use cases",
            "avoid_overlap_with": ["getting_started", "feature_showcase"],
        }

    # Landing page (blog) — legacy fallback
    elif page_role == "landing" and section == "blog":
        strategy = {
            "primary_focus": "Synthesized overview",
            "forbidden_topics": [],
            "claim_quota": {"min": 10, "max": 20},
            "unique_angle": "Product value proposition, key differentiators, real-world use cases",
            "avoid_overlap_with": ["getting_started", "feature_showcase"],
        }

    # TC-2344: Format conversion page (products)
    elif page_role == "format_conversion":
        strategy = {
            "primary_focus": "Single format conversion with complete code example",
            "forbidden_topics": ["unrelated_formats", "detailed_api_internals"],
            "claim_quota": {"min": 2, "max": 8},
            "unique_angle": "Complete conversion guide with runnable code",
            "tone": "professional, practical, SEO-friendly",
        }

    # TC-2344: How-to article page (KB)
    elif page_role == "howto_article":
        strategy = {
            "primary_focus": "Single how-to task with step-by-step instructions",
            "forbidden_topics": ["other_features", "detailed_api"],
            "claim_quota": {"min": 3, "max": 10},
            "unique_angle": "Practical solution to specific developer problem",
            "tone": "practical, helpful, developer-friendly",
        }

    # TC-2344: Feature blog post
    elif page_role == "feature_blog":
        strategy = {
            "primary_focus": "Feature highlight in friendly, approachable tone",
            "forbidden_topics": ["detailed_api", "troubleshooting", "raw_parameters"],
            "claim_quota": {"min": 3, "max": 8},
            "unique_angle": "Why this feature matters, with quick code demo",
            "tone": "friendly, approachable, enthusiastic",
        }

    # Default fallback (minimal strategy)
    else:
        strategy = {
            "primary_focus": f"{section} page content",
            "forbidden_topics": [],
            "claim_quota": {"min": 1, "max": 10},
            "unique_angle": f"General {section} content",
            "avoid_overlap_with": [],
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


class IAPlannerConfigurationError(IAPlannerError):
    """Configuration conflict or invalid constraint detected (Stage 2 hardening)."""
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


def load_ruleset(repo_root: Path = None, ruleset_version: str = "ruleset.v1") -> Dict[str, Any]:
    """Load full ruleset from specs/rulesets/<ruleset_version>.yaml.

    TC-984: Loads the complete ruleset dict for use by load_and_merge_page_requirements()
    and other config-driven functions.

    Args:
        repo_root: Path to repository root (auto-detected from worker location if None)
        ruleset_version: Ruleset version identifier (default "ruleset.v1"). Read from
            run_config["ruleset_version"] when available (Spec v1.1 Stage 1).

    Returns:
        Full ruleset dictionary

    Raises:
        IAPlannerError: If ruleset is missing or invalid
    """
    if repo_root is None:
        repo_root = Path(__file__).parent.parent.parent.parent.parent

    try:
        ruleset_path = resolve_ruleset_path(repo_root, ruleset_version)
    except FileNotFoundError as e:
        raise IAPlannerError(str(e)) from e

    try:
        ruleset = load_yaml(ruleset_path)
        return ruleset
    except Exception as e:
        raise IAPlannerError(f"Failed to load ruleset: {e}")


def load_ruleset_quotas(repo_root: Path = None, ruleset_version: str = "ruleset.v1") -> Dict[str, Dict[str, int]]:
    """Load page quotas from specs/rulesets/<ruleset_version>.yaml.

    Per specs/01_system_contract.md and specs/rulesets/, the ruleset defines
    per-section page quotas (min_pages, max_pages) that guide page planning.

    Args:
        repo_root: Path to repository root (auto-detected from worker location if None)
        ruleset_version: Ruleset version identifier (default "ruleset.v1"). Read from
            run_config["ruleset_version"] when available (Spec v1.1 Stage 1).

    Returns:
        Dictionary mapping section names to quota dictionaries with min_pages/max_pages keys

    Raises:
        IAPlannerError: If ruleset is missing or invalid
    """
    if repo_root is None:
        # Auto-detect repo root from this file's location
        # src/launch/workers/w4_ia_planner/worker.py -> go up 5 levels to reach repo root
        repo_root = Path(__file__).parent.parent.parent.parent.parent

    try:
        ruleset_path = resolve_ruleset_path(repo_root, ruleset_version)
    except FileNotFoundError as e:
        raise IAPlannerError(str(e)) from e

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
    product_facts: Optional[Dict[str, Any]] = None,
    family_capabilities: Optional[Dict[str, Any]] = None,
    platform: str = "python",
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

    Spec v1.1: Mandatory page entries may specify "title" instead of "slug". In that case
    the slug is derived via _derive_semantic_slug(title) after substituting {family_display_name}.
    The "folder_index: true" field is passed through for docs/getting-started → _index.md output.

    Spec references:
    - specs/06_page_planning.md lines 261-283 (Configurable Page Requirements)
    - specs/rulesets/ruleset.v1_1.yaml (mandatory_pages with title + folder_index support)
    - specs/schemas/ruleset.schema.json ($defs/sectionMinPages, family_overrides)

    Args:
        ruleset: Loaded ruleset dictionary
        product_slug: Product family slug (e.g., "3d", "cells", "note")

    Returns:
        Dict mapping section_name to:
            {"mandatory_pages": [...], "optional_page_policies": [...]}
        Each mandatory_pages entry has: {"slug": str, "page_role": str} plus optional
            "title": str, "folder_index": bool fields when present in ruleset
        Each optional_page_policies entry has: {"page_role": str, "source": str, "priority": int}
    """
    sections_config = ruleset.get("sections", {})
    family_overrides = ruleset.get("family_overrides", {})

    merged = {}

    for section_name, section_cfg in sorted(sections_config.items()):
        # Load global mandatory pages for this section
        global_mandatory_raw = list(section_cfg.get("mandatory_pages", []))
        global_policies = list(section_cfg.get("optional_page_policies", []))

        # Spec v1.1: normalize mandatory page entries — derive slugs from titles when no slug given
        global_mandatory = []
        for entry in global_mandatory_raw:
            entry = dict(entry)  # shallow copy — never mutate YAML data in place
            if "slug" not in entry and "title" in entry:
                # Substitute {family_display_name} placeholder with product slug
                resolved_title = entry["title"].replace("{family_display_name}", product_slug)
                # TC-2481: Use evidence-aware slug for howto_article pages
                # TC-2514: Pass family_capabilities for registry-based keyword/format lookup
                if entry.get("page_role") == "howto_article" and product_facts:
                    entry["slug"] = _derive_evidence_aware_slug(
                        resolved_title, product_slug, product_facts,
                        family_capabilities=family_capabilities,
                        platform=platform,
                    )
                else:
                    entry["slug"] = _derive_semantic_slug(resolved_title)
                # Store resolved title so W5 can use it as the page title
                entry["title"] = resolved_title
            # TC-2481b: Add topic_category + format_scope for validation gates
            if "topic_category" not in entry:
                tc = _infer_topic_category(entry.get("title", entry.get("slug", "")))
                if tc:
                    entry["topic_category"] = tc
            if "format_scope" not in entry and product_facts:
                fs = _infer_format_scope(
                    entry.get("title", entry.get("slug", "")),
                    product_facts, product_slug,
                )
                if fs:
                    entry["format_scope"] = fs
            global_mandatory.append(entry)

        # Track existing slugs for deduplication
        existing_slugs = set(p["slug"] for p in global_mandatory)

        # Check for family overrides
        family_cfg = family_overrides.get(product_slug, {})
        family_section_cfg = family_cfg.get("sections", {}).get(section_name, {})

        if family_section_cfg:
            # UNION family mandatory_pages with global (dedup by slug)
            family_mandatory = family_section_cfg.get("mandatory_pages", [])
            for page_entry in family_mandatory:
                page_entry = dict(page_entry)  # shallow copy
                if "slug" not in page_entry and "title" in page_entry:
                    resolved_title = page_entry["title"].replace("{family_display_name}", product_slug)
                    # TC-2481: evidence-aware slug for howto_article pages
                    # TC-2514: Pass family_capabilities for registry-based keyword/format lookup
                    if page_entry.get("page_role") == "howto_article" and product_facts:
                        page_entry["slug"] = _derive_evidence_aware_slug(
                            resolved_title, product_slug, product_facts,
                            family_capabilities=family_capabilities,
                            platform=platform,
                        )
                    else:
                        page_entry["slug"] = _derive_semantic_slug(resolved_title)
                    page_entry["title"] = resolved_title
                # TC-2481b: Add topic_category + format_scope
                if "topic_category" not in page_entry:
                    tc = _infer_topic_category(page_entry.get("title", page_entry.get("slug", "")))
                    if tc:
                        page_entry["topic_category"] = tc
                if "format_scope" not in page_entry and product_facts:
                    fs = _infer_format_scope(
                        page_entry.get("title", page_entry.get("slug", "")),
                        product_facts, product_slug,
                    )
                    if fs:
                        page_entry["format_scope"] = fs
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


def _find_claims_for_topic(
    title: str,
    rationale: str,
    all_claims: List[Dict[str, Any]],
    covered_ids: set,
    max_claims: int = 10,
) -> List[str]:
    """Find claims relevant to a discovered topic via keyword overlap.

    Returns claim_ids of up to max_claims uncovered claims that share
    at least 2 significant words with the topic title/rationale.
    """
    topic_words = set(
        w.lower() for w in re.findall(r'[a-zA-Z]{3,}', f"{title} {rationale}")
    )
    # Filter out very common words
    stopwords = {
        "the", "and", "for", "with", "that", "this", "from", "are", "can",
        "use", "how", "not", "all", "has", "will", "your", "into", "also",
        "using", "about", "when", "does", "what", "which", "their", "been",
        "have", "more", "some", "other", "than", "each", "only", "such",
    }
    topic_words -= stopwords

    scored = []
    for claim in all_claims:
        cid = claim.get("claim_id", "")
        if cid in covered_ids:
            continue
        claim_words = set(
            w.lower() for w in re.findall(r'[a-zA-Z]{3,}', claim.get("claim_text", ""))
        )
        overlap = len(topic_words & claim_words)
        if overlap >= 2:
            scored.append((overlap, cid))

    scored.sort(key=lambda x: -x[0])
    return [cid for _, cid in scored[:max_claims]]


def _sanitize_page_spec_fields(page_spec: Dict[str, Any]) -> Dict[str, Any]:
    """Convert nested dicts/lists in content_strategy to human-readable strings.

    Prevents raw Python dict repr from leaking into W5 prose templates.
    Preserves schema-required dict fields (claim_quota) that validators expect.
    """
    # Fields the page_plan schema expects as structured objects — must NOT be flattened
    _PRESERVE_AS_DICT = {"claim_quota", "selected_workflow"}
    # Agent 43/44: Lists of structured objects used by W5 generators — preserve as-is
    _PRESERVE_AS_LIST = {"supported_formats", "conversion_pairs"}

    strategy = page_spec.get("content_strategy")
    if not isinstance(strategy, dict):
        return page_spec
    cleaned = {}
    for key, value in strategy.items():
        if isinstance(value, dict) and key not in _PRESERVE_AS_DICT:
            # Convert nested dict to "key1: val1, key2: val2" string
            cleaned[key] = ", ".join(f"{k}: {v}" for k, v in value.items())
        elif isinstance(value, list) and key not in _PRESERVE_AS_LIST:
            # Lists of strings are fine; lists of dicts get stringified
            cleaned[key] = [
                (", ".join(f"{k}: {v}" for k, v in item.items()) if isinstance(item, dict) else str(item))
                for item in value
            ]
        else:
            cleaned[key] = value
    page_spec["content_strategy"] = cleaned
    return page_spec


# Agent 44: High-intent verbs for blog workflow scoring
_HIGH_INTENT_VERBS = frozenset({
    "convert", "merge", "create", "protect", "render",
    "export", "import", "transform", "generate", "extract",
})


def _derive_blog_evidence_slug(
    workflow_title: str,
    product_slug: str,
    product_facts: Dict[str, Any],
    family_capabilities: Optional[Dict[str, Any]] = None,
    platform: str = "python",
) -> str:
    """TC-2607: Derive evidence-aware blog slug incorporating family keyword.

    Enriches the base semantic slug with the product family keyword when it
    isn't already present, preventing generic slugs like ``convert-formats``
    and producing family-specific ones like ``convert-formats-3d-models``.

    Length guard: enriched slug is capped at 40 chars; if the enriched form
    exceeds the limit, the base slug is returned unchanged.
    """
    family_kw = _extract_family_keyword(product_slug, family_capabilities)
    base_slug = _derive_semantic_slug(workflow_title)
    if not base_slug:
        return ""
    # Already contains family keyword — no enrichment needed
    if family_kw in base_slug:
        return base_slug
    enriched = f"{base_slug}-{family_kw}"
    if len(enriched) > 40:
        return base_slug
    return enriched


def score_blog_workflow(
    product_facts: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
    product_slug: str = "",
    family_capabilities: Optional[Dict[str, Any]] = None,
    platform: str = "python",
) -> Dict[str, Any]:
    """Agent 44: Deterministic scoring to pick the most marketable workflow for feature_blog slug.

    Scoring:
      +5  conversion workflow AND has evidenced snippets
      +3  workflow has >= 1 code snippet (tag overlap or claim overlap)
      +2  workflow title/tag contains a high-intent verb

    Tiebreaker: workflow_tag alphabetical (ascending).
    Fallback: {"slug": "feature-highlight", "score": 0} when no workflows or all score 0.
    """
    _fallback = {
        "slug": "feature-highlight", "workflow_tag": "", "title": "Feature Highlight",
        "claim_ids": [], "score": 0,
    }
    workflows = product_facts.get("workflows", [])
    if not workflows:
        return dict(_fallback)

    # Build snippet evidence sets
    snippet_tag_set: set = set()
    snippet_claim_set: set = set()
    for s in snippet_catalog.get("snippets", []):
        snippet_tag_set.update(s.get("tags", []))
        snippet_claim_set.update(s.get("claim_ids", []))

    scored = []
    for wf in workflows:
        tag = wf.get("workflow_tag", "")
        title = wf.get("title", wf.get("name", ""))
        wf_claims = set(wf.get("claim_ids", []))
        wf_stags = set(wf.get("snippet_tags", []))
        score = 0

        has_snippet = bool(wf_stags & snippet_tag_set or wf_claims & snippet_claim_set)
        is_conversion = any(
            kw in tag.lower() or kw in title.lower()
            for kw in ("convert", "conversion")
        )

        if is_conversion and has_snippet:
            score += 5
        if has_snippet:
            score += 3
        wf_words = set(re.split(r'[_\s-]+', f"{tag} {title}".lower()))
        if wf_words & _HIGH_INTENT_VERBS:
            score += 2

        scored.append((score, tag, wf))

    # Sort by (score DESC, workflow_tag ASC) for determinism
    scored.sort(key=lambda x: (-x[0], x[1]))

    if not scored or scored[0][0] == 0:
        return dict(_fallback)

    best_score, best_tag, best_wf = scored[0]
    best_title = best_wf.get("title", best_wf.get("name", best_tag))
    if product_slug:
        slug = _derive_blog_evidence_slug(
            best_title, product_slug, product_facts,
            family_capabilities=family_capabilities,
            platform=platform,
        ) or "feature-highlight"
    else:
        slug = _derive_semantic_slug(best_title) or "feature-highlight"

    return {
        "slug": slug,
        "workflow_tag": best_tag,
        "title": best_title,
        "claim_ids": sorted(best_wf.get("claim_ids", [])),
        "score": best_score,
    }


def _derive_semantic_slug(text: str, max_length: int = 40) -> str:
    """Derive a concise, human-readable slug from text using heuristic extraction.

    Instead of raw truncation (claim_text[:40]), this extracts the core noun
    phrase or action from the text to produce meaningful slugs.

    Examples:
        "Convert 3D models between formats" -> "convert-3d-models-between-formats"
        "11 Section 3: In cases where this document" -> "document-handling"
        "Load and manipulate 3D scenes" -> "load-and-manipulate-3d-scenes"
    """
    # Step 1: Strip spec-header prefixes (e.g., "11 Section 3:", "<11> Section 3:")
    text = re.sub(r'^<?(\d+)>?[\s.)\-:]+(?:Section\s+\d+[\s:.\-]*)?', '', text, flags=re.IGNORECASE).strip()
    # Strip angle-bracketed numbers at start (e.g., "<11>")
    text = re.sub(r'^<\d+>\s*', '', text).strip()
    # Strip filler preambles iteratively (chained preambles like "In cases where this document specifies that")
    _preamble_re = re.compile(
        r'^(?:In cases[,]?\s*where|When you need to|It is possible to|You can use|'
        r'this document specifies that|a field can only)\s+', re.IGNORECASE
    )
    for _ in range(3):  # max 3 passes to strip chained preambles
        new_text = _preamble_re.sub('', text).strip()
        if new_text == text:
            break
        text = new_text
    # Strip leading "Section N:" pattern that may remain
    text = re.sub(r'^Section\s+\d+[\s:.\-]*', '', text, flags=re.IGNORECASE).strip()

    # Step 2: Extract first meaningful phrase (up to 6 words)
    words = text.split()
    phrase_words = words[:6]
    phrase = " ".join(phrase_words)

    # Step 3: Slugify
    slug = phrase.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)   # Remove non-alphanumeric except spaces/hyphens
    slug = re.sub(r'\s+', '-', slug)              # Spaces to hyphens
    slug = re.sub(r'-{2,}', '-', slug)            # Collapse multiple hyphens
    slug = slug.strip('-')

    # Step 4: Enforce max length (truncate at word boundary)
    if len(slug) > max_length:
        truncated = slug[:max_length]
        # Don't cut in the middle of a word — find last hyphen
        last_hyphen = truncated.rfind('-')
        if last_hyphen > 10:  # Keep at least 10 chars
            truncated = truncated[:last_hyphen]
        slug = truncated.strip('-')

    return slug or "feature"


def _derive_page_title(text: str, prefix: str = "", max_length: int = 70) -> str:
    """Derive a human-readable page title from text.

    Instead of raw truncation (claim_text[:50]), this creates a proper title.
    """
    # Strip spec-header prefixes (e.g., "11 Section 3:", "<11> Section 3:")
    text = re.sub(r'^<?(\d+)>?[\s.)\-:]+(?:Section\s+\d+[\s:.\-]*)?', '', text, flags=re.IGNORECASE).strip()
    text = re.sub(r'^<\d+>\s*', '', text).strip()
    _preamble_re = re.compile(
        r'^(?:In cases[,]?\s*where|When you need to|It is possible to|You can use|'
        r'this document specifies that|a field can only)\s+', re.IGNORECASE
    )
    for _ in range(3):
        new_text = _preamble_re.sub('', text).strip()
        if new_text == text:
            break
        text = new_text
    text = re.sub(r'^Section\s+\d+[\s:.\-]*', '', text, flags=re.IGNORECASE).strip()

    # Take first ~10 words for title
    words = text.split()[:10]
    title = " ".join(words)

    # Add prefix if provided
    if prefix:
        title = f"{prefix} {title}"

    # Enforce max length
    if len(title) > max_length:
        truncated = title[:max_length]
        last_space = truncated.rfind(' ')
        if last_space > 20:
            truncated = truncated[:last_space]
        title = truncated

    return title or "Feature Guide"


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
    platform: str = "",
    content_policy=None,  # TC-2435: Optional[ContentPolicy], default None
    tier_multiplier: float = 1.0,  # TC-2439: quality_score multiplier from repo_profile
    evidence_policy=None,  # TC-2447: Optional[EvidenceBasedPolicy], default None
    eligible_roles=None,  # TC-2449: Optional[set[str]] from repo_profile signals, default None
    api_inventory=None,  # Phase 1: Optional api_inventory for public_surface filtering
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
        platform: V2 platform identifier (e.g., "python", "typescript")

    Returns:
        List of page specification dictionaries (deterministic order)
    """
    # TC-2447: Apply evidence-based section cap BEFORE computing N.
    # When evidence_policy is provided, optional_max_pages caps effective_max
    # for this section.  Mandatory pages are NEVER reduced — W4 guarantees them
    # via the mandatory injection loop which runs before this function.
    if evidence_policy is not None:
        _section_pol = evidence_policy.for_section(section)
        _capped_max = min(effective_max,
                         _section_pol.optional_max_pages + mandatory_page_count)
        if _capped_max < effective_max:
            import logging as _logging
            _logging.getLogger(__name__).info(
                "[W4 EvidencePolicy] section=%s: capping effective_max %d→%d "
                "(evidence_score=%.3f optional_max=%d)",
                section, effective_max, _capped_max,
                _section_pol.evidence_score, _section_pol.optional_max_pages,
            )
        effective_max = _capped_max

    N = effective_max - mandatory_page_count
    if N <= 0:
        return []

    # TC-2449: Filter optional_page_policies by eligible_roles when use_repo_profile=true
    if eligible_roles is not None:
        _before = len(optional_page_policies)
        optional_page_policies = [
            p for p in optional_page_policies
            if p.get("page_role", "") in eligible_roles
        ]
        if len(optional_page_policies) < _before:
            import logging as _logging
            _logging.getLogger(__name__).info(
                "[W4 EligibleRoles] section=%s: filtered %d→%d policies",
                section, _before, len(optional_page_policies),
            )

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
                slug = _derive_semantic_slug(claim_text)

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
                    "title": _derive_page_title(claim_text),
                    "purpose": f"Feature guide for {_derive_page_title(claim_text)}",
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
                slug = _derive_semantic_slug(wf_name)

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
                    "title": f"{_derive_page_title(wf_name)} Guide",
                    "purpose": f"Workflow guide for {_derive_page_title(wf_name)}",
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
                # TC-1901: Minimum quality threshold — need at least 1 matching snippet
                quality_score = (1 * 2) + (len(matching_snippets) * 3)
                if quality_score < 5:
                    continue

                slug = f"how-to-{_derive_semantic_slug(claim_text)}"

                candidates.append({
                    "slug": slug,
                    "page_role": page_role,
                    "priority": priority,
                    "quality_score": quality_score,
                    "title": _derive_page_title(claim_text, prefix="How to:"),
                    "purpose": f"Feature showcase: {_derive_page_title(claim_text)}",
                    "required_claim_ids": sorted([claim["claim_id"]]),
                    "required_snippet_tags": sorted(
                        [matching_snippets[0].get("tags", [""])[0]]
                        if matching_snippets else []
                    ),
                })

        elif source == "per_api_symbol":
            # One reference page per API class
            # TC-1604: classes may be dicts (from code_analyzer) — normalise to strings
            raw_classes = api_summary.get("classes", [])
            classes = [
                c["name"] if isinstance(c, dict) else c for c in raw_classes
            ]
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

        elif source == "per_api_object":
            # Spec v1.1 H2 (Q3=A): One reference_object_page per class/module/function.
            # Includes object_name + object_kind so W5 generator can locate API surface data.

            # Phase 1: Filter to public surface when available and confident.
            # public_surface.classes now contains import paths (e.g. "aspose.threed.Scene").
            # Build a short-name set for matching against class_name from raw_classes.
            _ps_class_names: Optional[set] = None
            _ps_fn_names: Optional[set] = None
            if api_inventory is not None:
                ps = api_inventory.get("public_surface", {})
                if ps.get("confidence", "unknown") != "unknown":
                    ps_cls = ps.get("classes", [])
                    if ps_cls:
                        # Accept both import paths AND short names (backward compat)
                        _ps_class_names = set(ps_cls) | {
                            p.rsplit(".", 1)[-1] for p in ps_cls
                        }
                    ps_fns = ps.get("functions", [])
                    if ps_fns:
                        _ps_fn_names = set(ps_fns) | {
                            p.rsplit(".", 1)[-1] for p in ps_fns
                        }

            raw_classes = api_summary.get("classes", [])
            for raw_cls in sorted(
                raw_classes,
                key=lambda c: (c["name"] if isinstance(c, dict) else c).lower(),
            ):
                if isinstance(raw_cls, dict):
                    class_name = raw_cls.get("name", "")
                else:
                    class_name = str(raw_cls)
                if not class_name:
                    continue
                # Phase 1: Skip non-public classes when public surface is known
                if _ps_class_names is not None and class_name not in _ps_class_names:
                    continue
                # Derive a clean slug from the class name (CamelCase → kebab-case)
                slug = _derive_semantic_slug(class_name)
                # Find claims mentioning this class
                matching_claims = [
                    c for c in claims
                    if class_name.lower() in c.get("claim_text", "").lower()
                    and c.get("claim_kind") == "api"
                ]
                # Snippets that reference the class name
                matching_snippets = [
                    s for s in snippets
                    if class_name.lower() in s.get("code", "").lower()
                ]
                quality_score = (len(matching_claims) * 2) + (len(matching_snippets) * 3)
                # Agent 45: Boost classes by API surface richness (methods/properties)
                if isinstance(raw_cls, dict):
                    _methods = raw_cls.get("methods", [])
                    _props = raw_cls.get("properties", [])
                    quality_score += min(len(_methods) // 3, 5)  # +1 per 3 methods, max +5
                    quality_score += min(len(_props), 3)          # +1 per property, max +3
                candidates.append({
                    "slug": slug,
                    "page_role": page_role,
                    "priority": priority,
                    "quality_score": quality_score,
                    "title": f"{class_name} Class Reference",
                    "purpose": f"Reference documentation for the {class_name} class",
                    "object_name": class_name,
                    "object_kind": "class",
                    "required_claim_ids": sorted(
                        [c["claim_id"] for c in matching_claims[:5]]
                    ),
                    "required_snippet_tags": sorted(
                        list({
                            tag
                            for s in matching_snippets[:3]
                            for tag in s.get("tags", [])
                        })[:3]
                    ),
                })
            # Also handle top-level functions if present
            raw_functions = api_summary.get("functions", [])
            for raw_fn in sorted(
                raw_functions,
                key=lambda f: (f["name"] if isinstance(f, dict) else f).lower(),
            ):
                if isinstance(raw_fn, dict):
                    fn_name = raw_fn.get("name", "")
                else:
                    fn_name = str(raw_fn)
                if not fn_name:
                    continue
                # Phase 1: Skip non-public functions when public surface is known
                if _ps_fn_names is not None and fn_name not in _ps_fn_names:
                    continue
                slug = _derive_semantic_slug(fn_name)
                matching_claims = [
                    c for c in claims
                    if fn_name.lower() in c.get("claim_text", "").lower()
                    and c.get("claim_kind") == "api"
                ]
                quality_score = len(matching_claims) * 2
                # Agent 45: Boost functions with docstrings or detailed info
                if isinstance(raw_fn, dict) and raw_fn.get("docstring"):
                    quality_score += 1
                candidates.append({
                    "slug": slug,
                    "page_role": page_role,
                    "priority": priority,
                    "quality_score": quality_score,
                    "title": f"{fn_name} Function Reference",
                    "purpose": f"Reference documentation for the {fn_name} function",
                    "object_name": fn_name,
                    "object_kind": "function",
                    "required_claim_ids": sorted(
                        [c["claim_id"] for c in matching_claims[:5]]
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

        elif source == "per_claim_group":
            # TC-1635: Generate page from claim_group when threshold met
            # Used for best_practices, tutorials, etc. from TC-1628 ruleset
            claim_group = policy.get("claim_group")  # e.g., "best_practices"
            min_claims = policy.get("min_claims", 1)
            slug = policy.get("slug", claim_group)
            section_path = policy.get("section_path", section)
            heading_overrides = policy.get("heading_overrides", [])

            if claim_group:
                claim_ids = claim_groups.get(claim_group, [])

                if len(claim_ids) >= min_claims:
                    # Threshold met → generate page
                    matching_claims = [
                        c for c in claims if c.get("claim_id") in set(claim_ids)
                    ]
                    quality_score = len(matching_claims)  # Higher = more content

                    # Title from heading_overrides or claim_group name
                    title_text = heading_overrides[0] if heading_overrides else claim_group.replace("_", " ").title()

                    candidates.append({
                        "slug": slug,
                        "page_role": page_role,
                        "priority": priority,
                        "quality_score": quality_score,
                        "title": title_text,
                        "purpose": f"{title_text} content from {claim_group}",
                        "required_claim_ids": sorted(claim_ids),
                        "required_snippet_tags": [],
                        "section_path": section_path,  # Override section if specified
                        "heading_overrides": heading_overrides,
                    })

        # TC-2343: per_format_conversion — one page per format conversion pair
        elif source == "per_format_conversion":
            conversion_pairs = claim_groups.get("conversion_pairs", [])
            for pair in conversion_pairs:
                src_fmt = pair.get("source", "unknown")
                tgt_fmt = pair.get("target", "unknown")
                pair_claim_ids = pair.get("claim_ids", [])
                if not pair_claim_ids:
                    continue
                slug = f"{src_fmt}-to-{tgt_fmt}"
                quality_score = len(pair_claim_ids) * 2
                matching_snippets = [s for s in snippets if any(
                    cid in s.get("claim_ids", []) for cid in pair_claim_ids)]
                quality_score += len(matching_snippets) * 3
                candidates.append({
                    "slug": slug,
                    "page_role": policy.get("page_role", "format_conversion"),
                    "priority": policy.get("priority", 99),
                    "quality_score": quality_score,
                    "title": f"Convert {src_fmt.upper()} to {tgt_fmt.upper()} using Python",
                    "purpose": f"Step-by-step guide for {src_fmt.upper()} to {tgt_fmt.upper()} conversion",
                    "required_claim_ids": sorted(pair_claim_ids[:10]),
                    "required_snippet_tags": [matching_snippets[0].get("tags", [""])[0]] if matching_snippets else [],
                    "content_strategy": {
                        "source_format": src_fmt,
                        "target_format": tgt_fmt,
                    },
                })

        # TC-2343: per_howto_cluster — one page per how-to topic cluster
        elif source == "per_howto_cluster":
            howto_clusters = claim_groups.get("how_to_clusters", {})
            for cluster_name, cluster_claim_ids in sorted(howto_clusters.items()):
                if len(cluster_claim_ids) < 3:
                    continue
                slug = f"how-to-{cluster_name}"
                quality_score = len(cluster_claim_ids) * 2
                matching_snippets = [s for s in snippets if any(
                    cid in s.get("claim_ids", []) for cid in cluster_claim_ids)]
                quality_score += len(matching_snippets) * 3
                candidates.append({
                    "slug": slug,
                    "page_role": policy.get("page_role", "howto_article"),
                    "priority": policy.get("priority", 99),
                    "quality_score": quality_score,
                    "title": _derive_page_title(cluster_name.replace("-", " "), prefix="How to:"),
                    "purpose": f"How-to guide for {cluster_name.replace('-', ' ')}",
                    "required_claim_ids": sorted(cluster_claim_ids[:10]),
                    "required_snippet_tags": [matching_snippets[0].get("tags", [""])[0]] if matching_snippets else [],
                })

        # TC-2343: per_feature_blog — one blog post per key feature with snippets
        elif source == "per_feature_blog":
            feature_ids = claim_groups.get("key_features", [])
            for fid in feature_ids:
                feature_claim = next((c for c in claims if c.get("claim_id") == fid), None)
                if not feature_claim:
                    continue
                claim_text = feature_claim.get("claim_text", "feature")
                matching_snippets = [s for s in snippets if fid in s.get("claim_ids", [])]
                if not matching_snippets:
                    continue  # Only generate blog for features WITH code examples
                # Create a short slug from the claim text
                slug_words = re.sub(r'[^a-z0-9\s]', '', claim_text.lower()).split()[:4]
                slug_base = "-".join(slug_words) if slug_words else "feature"
                slug = f"{product_slug}-{slug_base}-python"
                quality_score = 2 + len(matching_snippets) * 3
                candidates.append({
                    "slug": slug,
                    "page_role": policy.get("page_role", "feature_blog"),
                    "priority": policy.get("priority", 99),
                    "quality_score": quality_score,
                    "title": f"{claim_text[:50].strip()} with {product_slug.replace('-', ' ').title()} for Python",
                    "purpose": f"Blog post highlighting {claim_text[:50].strip()}",
                    "required_claim_ids": [fid],
                    "required_snippet_tags": [matching_snippets[0].get("tags", [""])[0]],
                })

    # TC-2439: Apply tier_multiplier to all quality scores before sorting
    if tier_multiplier != 1.0:
        for _c in candidates:
            _c["quality_score"] = _c["quality_score"] * tier_multiplier

    # Sort by (priority asc, quality_score desc, slug asc) -- DETERMINISTIC
    # Per specs/06_page_planning.md Step 4
    candidates.sort(key=lambda c: (c["priority"], -c["quality_score"], c["slug"]))

    # Select top N
    selected = candidates[:N]

    # TC-2435: Apply content_policy filter to optional page candidates
    if content_policy is not None:
        filtered = []
        for _cand in selected:
            _decision = content_policy.evaluate(_cand, section)
            if not _decision.accepted:
                import logging as _logging
                _logging.getLogger(__name__).info(
                    "[W4 Policy] Skipping optional '%s/%s': %s",
                    section, _cand.get("slug", "?"), _decision.rejection_reason,
                )
                continue
            if _decision.is_dry_run:
                _cand = {**_cand, "dry_run": True}
            filtered.append(_cand)
        selected = filtered

    # Build full page spec structures
    subdomain = get_subdomain_for_section(section)
    result_pages = []

    for candidate in selected:
        slug = candidate["slug"]
        role = candidate.get("page_role", assign_page_role(section, slug))
        strategy = build_content_strategy(role, section, workflows)

        # TC-1635: Use section_path from candidate if provided (per_claim_group)
        actual_section = candidate.get("section_path", section)

        page_spec = {
            "section": actual_section,
            "slug": slug,
            "output_path": compute_output_path(
                actual_section, slug, product_slug, subdomain=subdomain, platform=platform
            ),
            "url_path": compute_url_path(
                actual_section, slug, product_slug, platform=platform
            ),
            "title": candidate["title"],
            "purpose": candidate["purpose"],
            "template_variant": launch_tier,
            # TC-1635: Use heading_overrides from candidate if provided, else default
            "required_headings": candidate.get("heading_overrides") or _default_headings_for_role(role, product_facts),
            "required_claim_ids": candidate.get("required_claim_ids", []),
            "required_snippet_tags": candidate.get("required_snippet_tags", []),
            "cross_links": [],
            "seo_keywords": [product_slug, slug],
            "forbidden_topics": strategy.get("forbidden_topics", []),
            "page_role": role,
            "content_strategy": strategy,
        }
        # Spec v1.1 H2: Preserve reference object metadata so W5 generator can use it
        if candidate.get("object_name"):
            page_spec["object_name"] = candidate["object_name"]
        if candidate.get("object_kind"):
            page_spec["object_kind"] = candidate["object_kind"]
        result_pages.append(page_spec)

    logger.info(
        f"[W4 IAPlanner] Generated {len(result_pages)} optional pages for "
        f"section '{section}' (N={N}, candidates={len(candidates)})"
    )

    return result_pages


def _has_limitations(product_facts: Dict[str, Any]) -> bool:
    """Detect if product has limitations in product_facts.

    TC-CREV-C-TRACK2: Check both claim_groups.limitations and top-level limitations.

    Args:
        product_facts: Product facts dictionary

    Returns:
        True if product has limitations, False otherwise
    """
    claim_groups = product_facts.get('claim_groups', {})
    # Defensive: claim_groups may be a list (legacy format) instead of dict
    limitations_in_groups = claim_groups.get('limitations', []) if isinstance(claim_groups, dict) else []
    top_level_limitations = product_facts.get('limitations', [])
    return bool(limitations_in_groups or top_level_limitations)


def _default_headings_for_role(page_role: str, product_facts: Dict[str, Any] = None) -> List[str]:
    """Return default required headings based on page role.

    Provides standard heading structure per content distribution strategy.
    TC-CREV-C-TRACK2: Adds "Limitations" for appropriate page roles when product has limitations.

    Args:
        page_role: Page role string
        product_facts: Optional product facts dictionary (for limitations detection)

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
        # TC-1633: New page roles for Round 10 content types
        "faq": ["Frequently Asked Questions"],
        "best_practices": ["Best Practices", "Recommendations"],
        "tutorial": ["Tutorial", "Step-by-Step Guide"],
        # TC-2344: New page roles for Round 3 aspose.net alignment
        "format_conversion": ["Overview", "How It Works", "Code Example", "Advanced Options", "FAQ"],
        "howto_article": ["Goal", "When You'd Use This", "Prerequisites", "Steps", "Code Example", "Common Mistakes", "See Also"],
        "feature_blog": ["Introduction", "Key Highlights", "Quick Example", "Next Steps"],
        "performance_guide": ["Overview", "Benchmarks", "Optimization Tips", "Best Practices"],
        "blog_announcement": ["Announcement", "Key Highlights", "Getting Started", "Next Steps"],
    }
    headings = headings_map.get(page_role, ["Overview"]).copy()

    # TC-CREV-C-TRACK2: Add "Limitations" for appropriate page roles when product has limitations
    if product_facts and _has_limitations(product_facts):
        # Only add for overview-style pages (not TOC, getting-started, FAQ, troubleshooting)
        if page_role in ["landing", "comprehensive_guide", "api_reference"]:
            if "Limitations" not in headings:
                headings.append("Limitations")

    return headings


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
    platform: str = "",
) -> str:
    """Compute canonical URL path per specs/33_public_url_mapping.md.

    Per specs/33_public_url_mapping.md:83-86 and 106:
    - Section is implicit in subdomain (blog.aspose.org, docs.aspose.org, etc.)
    - Section name NEVER appears in URL path
    - V1 URL format: /<family>/<slug>/
    - V2 URL format: /<family>/<platform>/<slug>/  (when platform is non-empty)

    Args:
        section: Section name (products, docs, reference, kb, blog) - used for
                 subdomain determination but NOT included in URL path
        slug: Page slug
        product_slug: Product family slug (e.g., "cells", "words")
        locale: Language code (default: "en")
        platform: Platform segment (e.g., "python"). Empty string for V1 layout.

    Returns:
        Canonical URL path with leading and trailing slashes

    Examples:
        compute_url_path("docs", "getting-started", "cells")
        => "/cells/getting-started/"

        compute_url_path("docs", "getting-started", "cells", platform="python")
        => "/cells/python/getting-started/"

        compute_url_path("blog", "announcement", "3d")
        => "/3d/announcement/"

        compute_url_path("docs", "index", "cells", platform="python")
        => "/cells/python/" (index slug omitted - R17-005b fix)
    """
    # Per specs/33_public_url_mapping.md:83-86, 106:
    # Section is implicit in subdomain, NOT in URL path
    # V1 format: /<family>/<slug>/
    # V2 format: /<family>/<platform>/<slug>/
    parts = [product_slug]
    if platform:
        parts.append(platform)

    # R17-005b: Omit "index" slug - section index pages should have directory URL
    # _index.md files should map to /family/platform/ not /family/platform/index/
    if slug != "index":
        parts.append(slug)

    # Build path with leading and trailing slashes
    url_path = "/" + "/".join(parts) + "/"
    return url_path


def compute_absolute_url(
    section: str,
    slug: str,
    product_slug: str,
    platform: str = "",
    site_config: SiteConfig = None,
) -> str:
    """Compute absolute URL for a page (Phase 1B).

    Combines subdomain + url_path into a full absolute URL.
    Requirement: "all internal URLs posted by linker must be absolute."

    Args:
        section: Section name (products, docs, reference, kb, blog)
        slug: Page slug
        product_slug: Product family slug (e.g., "cells")
        platform: Platform segment (e.g., "python"). Empty for V1 layout.
        site_config: Optional SiteConfig override.

    Returns:
        Absolute URL (e.g., "https://docs.aspose.org/cells/python/overview/")
    """
    config = site_config or DEFAULT_SITE_CONFIG
    return config.build_url(section=section, family=product_slug, slug=slug, platform=platform)


def get_subdomain_for_section(section: str, site_config: SiteConfig = None) -> str:
    """Map section to subdomain per specs/18_site_repo_layout.md.

    Phase 1B: Delegates to SiteConfig for single-source subdomain mapping (DRY).

    Args:
        section: Section name (products, docs, reference, kb, blog)
        site_config: Optional SiteConfig override (defaults to DEFAULT_SITE_CONFIG)

    Returns:
        Subdomain string (e.g., "products.aspose.org")
    """
    config = site_config or DEFAULT_SITE_CONFIG
    return config.get_subdomain(section)


def compute_output_path(
    section: str,
    slug: str,
    product_slug: str,
    subdomain: str = None,
    locale: str = "en",
    platform: str = "",
) -> str:
    """Compute content file path relative to site repo root.

    Hugo-correct layout (TC-2000/2002):
    - Non-blog: content/<subdomain>/<family>/<locale>/[<platform>/]<slug>.md
    - Blog: content/blog.aspose.org/<family>/[<platform>/]<slug>/index.md (no locale)

    Key rules:
    - TC-2000: No section subdirectory (Hugo contentDir already scopes by section)
    - TC-2002: index/_index slugs become _index.md (branch bundle) for non-blog sections

    Args:
        section: Section name
        slug: Page slug
        product_slug: Product family slug
        subdomain: Hugo site subdomain (auto-determined from section if None)
        locale: Language code
        platform: Platform segment (e.g., "python"). Empty string for V1 layout.

    Returns:
        Content file path relative to site repo root
    """
    # TC-681: Auto-determine subdomain from section if not provided
    if subdomain is None:
        subdomain = get_subdomain_for_section(section)

    # TC-926: Blog posts use special format per specs/18_site_repo_layout.md
    # Path: content/blog.aspose.org/<family>/<slug>/index.md
    # V2:   content/blog.aspose.org/<family>/<platform>/<slug>/index.md
    # Note: NO locale segment, uses index.md instead of <slug>.md
    if section == "blog":
        # Build path components, skip empty product_slug to avoid double slash
        components = ["content", subdomain]
        if product_slug and product_slug.strip():
            components.append(product_slug)
        if platform:
            components.append(platform)
        components.extend([slug, "index.md"])
        output_path = "/".join(components)
        return output_path

    # TC-926 + TC-2000/2002: Hugo-correct path generation
    # All non-blog sections use the same {subdomain}/{family}/{locale}/ ordering
    components = ["content", subdomain]

    if product_slug and product_slug.strip():
        components.append(product_slug)
    components.append(locale)

    # V2: Insert platform after locale+family when non-empty
    if platform:
        components.append(platform)

    # TC-2002: Hugo section pages need _index.md (branch bundle), not index.md (leaf bundle)
    if (slug == "index" or slug == "_index") and section != "blog":
        filename = "_index.md"
    else:
        filename = f"{slug}.md"

    # TC-2000: No section subdirectory — Hugo contentDir already scopes by section
    components.append(filename)

    # Join and return (use / for consistent paths)
    output_path = "/".join(components)
    return output_path


def _build_page_title(slug: str, section: str, product_name: str, platform: str) -> str:
    """Build unique, product-specific page title.

    TC-2203/R17-014: Generates distinctive titles that include the product name
    and platform to differentiate pages across products.

    Args:
        slug: Page slug (e.g., "getting-started", "faq")
        section: Section name (docs, kb, reference, etc.)
        product_name: Full product name (e.g., "Aspose.3D for Python")
        platform: Target platform (e.g., "python", "")

    Returns:
        Unique page title string
    """
    platform_label = f"for {platform.title()}" if platform else ""
    short_name = product_name.split(" for ")[0] if " for " in product_name else product_name

    title_templates = {
        "getting-started": f"Getting Started with {short_name} {platform_label}".strip(),
        "developer-guide": f"{short_name} {platform_label} Developer Guide \u2014 Code Examples & Workflows".strip(),
        "installation": f"How to Install {short_name} {platform_label} \u2014 pip, Setup & Requirements".strip(),
        "faq": f"{short_name} {platform_label} FAQ \u2014 Common Questions Answered".strip(),
        "api-overview": f"{short_name} {platform_label} API Reference \u2014 Classes, Methods & Modules".strip(),
        "troubleshooting": f"{short_name} {platform_label} Troubleshooting \u2014 Common Errors & Solutions".strip(),
        "best-practices": f"{short_name} {platform_label} Best Practices \u2014 Performance & Code Quality".strip(),
        "tutorial": f"{short_name} {platform_label} Tutorial \u2014 Step-by-Step Guide".strip(),
        "index": f"{short_name} {platform_label} Documentation".strip(),
    }

    # Check exact slug match
    if slug in title_templates:
        return title_templates[slug]

    # Fallback: capitalize slug and add product name
    readable = slug.replace("-", " ").replace("_", " ").title()
    return f"{short_name} {readable} {platform_label}".strip()


def _build_page_description(slug: str, section: str, product_name: str, platform: str, purpose: str = "") -> str:
    """Build unique meta description (max 160 chars).

    TC-2203/R17-014: Generates distinctive descriptions that include the product
    name and platform for SEO and content differentiation.

    Args:
        slug: Page slug (e.g., "getting-started", "faq")
        section: Section name (docs, kb, reference, etc.)
        product_name: Full product name (e.g., "Aspose.3D for Python")
        platform: Target platform (e.g., "python", "")
        purpose: Optional purpose string for fallback descriptions

    Returns:
        Meta description string (max 160 chars)
    """
    platform_label = f"for {platform.title()}" if platform else ""
    short_name = product_name.split(" for ")[0] if " for " in product_name else product_name

    desc_templates = {
        "getting-started": f"Learn how to install and start using {short_name} {platform_label}. Step-by-step setup guide with code examples.",
        "developer-guide": f"Complete developer guide for {short_name} {platform_label} with code examples, workflows, and usage scenarios.",
        "installation": f"Install {short_name} {platform_label} via pip. System requirements, setup instructions, and verification steps.",
        "faq": f"Frequently asked questions about {short_name} {platform_label}. Direct answers with code examples.",
        "api-overview": f"{short_name} {platform_label} API reference. Browse classes, methods, modules, and constants.",
        "troubleshooting": f"Troubleshoot common {short_name} {platform_label} errors. Solutions with code fixes and explanations.",
        "best-practices": f"Best practices for {short_name} {platform_label}. Performance tips, code quality, and optimization.",
        "tutorial": f"Step-by-step {short_name} {platform_label} tutorial. Learn with practical code examples.",
    }

    if slug in desc_templates:
        desc = desc_templates[slug].strip()
    elif purpose:
        desc = f"{short_name} {platform_label}: {purpose}".strip()
    else:
        readable = slug.replace("-", " ").replace("_", " ")
        desc = f"{short_name} {platform_label} {readable} documentation and guide.".strip()

    # Truncate to 160 chars
    if len(desc) > 160:
        desc = desc[:157].rsplit(" ", 1)[0] + "..."
    return desc


def plan_pages_for_section(
    section: str,
    launch_tier: str,
    product_facts: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
    product_slug: str,
    platform: str = "",
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
        platform: V2 platform identifier (e.g., "python", "typescript")

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

    # TC-2203: Product name for unique titles/descriptions
    product_name = product_facts.get("product_name", "Product").strip()
    if not product_name:
        product_name = f"Aspose.{product_slug.capitalize()}"

    if section == "products":
        # Products section: overview/landing page
        slug = "overview"
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
        # TC-CREV-C-TRACK2: Build required_headings with Limitations if applicable
        overview_headings = ["Overview", "Key Features", "Supported Platforms", "Getting Started"]
        if _has_limitations(product_facts):
            overview_headings.append("Limitations")

        pages.append({
            "section": section,
            "slug": slug,
            "output_path": compute_output_path(section, slug, product_slug, subdomain=subdomain, platform=platform),
            "url_path": compute_url_path(section, slug, product_slug, platform=platform),
            "title": _build_page_title("overview", section, product_name, platform),
            "description": _build_page_description("overview", section, product_name, platform, purpose),
            "purpose": purpose,
            "template_variant": launch_tier,
            "required_headings": overview_headings,
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
            "output_path": compute_output_path(section, "_index", product_slug, platform=platform),
            "url_path": compute_url_path(section, "_index", product_slug, platform=platform),
            "title": _build_page_title("index", section, product_name, platform),
            "description": _build_page_description("index", section, product_name, platform, "Table of contents and navigation hub"),
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
            "output_path": compute_output_path(section, "getting-started", product_slug, platform=platform),
            "url_path": compute_url_path(section, "getting-started", product_slug, platform=platform),
            "title": _build_page_title("getting-started", section, product_name, platform),
            "description": _build_page_description("getting-started", section, product_name, platform, "Installation instructions and first task guide"),
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

        # TC-2320: Gather top claims per workflow (not just first)
        CLAIMS_PER_WORKFLOW = 3
        workflow_claim_ids = []
        for workflow in workflows:
            wf_id = workflow.get("workflow_id", "")
            # TC-1010: Find claims matching this workflow using top-level claim_groups
            wf_claim_ids = _resolve_claim_ids_for_group(product_facts, wf_id)
            matching_claims = [
                c["claim_id"] for c in claims
                if c.get("claim_id") in wf_claim_ids or wf_id in c.get("tags", [])
            ]
            if matching_claims:
                # TC-2320: Take top N claims per workflow instead of just first
                workflow_claim_ids.extend(matching_claims[:CLAIMS_PER_WORKFLOW])

        # Fallback: if no workflow-specific claims found, use first N claims
        if not workflow_claim_ids and workflows:
            workflow_claim_ids = [c["claim_id"] for c in claims[:len(workflows)]]

        # TC-2320: Deduplicate while preserving order
        seen = set()
        deduped_ids = []
        for cid in workflow_claim_ids:
            if cid not in seen:
                seen.add(cid)
                deduped_ids.append(cid)
        workflow_claim_ids = deduped_ids

        # TC-CREV-C-TRACK2: Build required_headings with Limitations if applicable
        dg_headings = ["Introduction", "Common Scenarios", "Advanced Scenarios", "Additional Resources"]
        if _has_limitations(product_facts):
            dg_headings.append("Limitations")

        pages.append({
            "section": section,
            "slug": "developer-guide",
            "output_path": compute_output_path(section, "developer-guide", product_slug, platform=platform),
            "url_path": compute_url_path(section, "developer-guide", product_slug, platform=platform),
            "title": _build_page_title("developer-guide", section, product_name, platform),
            "description": _build_page_description("developer-guide", section, product_name, platform, "Comprehensive listing of all major usage scenarios with source code"),
            "purpose": "Comprehensive listing of all major usage scenarios with source code",
            "template_variant": launch_tier,
            "required_headings": dg_headings,
            "required_claim_ids": workflow_claim_ids,
            "required_snippet_tags": sorted(set(snippet_tags)),  # All snippets
            "cross_links": [],
            "seo_keywords": [product_slug, "developer guide", "scenarios"],
            "forbidden_topics": dg_strategy.get("forbidden_topics", []),
            "page_role": dg_role,
            "content_strategy": dg_strategy,
        })

        # TC-2201 R17-007: Claim-density-driven topic cluster expansion
        n_claims = len(claims)
        if n_claims > 200:
            covered_ids = set()
            for p in pages:
                covered_ids.update(p.get("required_claim_ids", []))

            uncovered_groups = {}
            for group_name, group_ids in claim_groups_dict.items():
                # Skip groups that already have dedicated pages
                if group_name in ("key_features", "install_steps", "faq", "troubleshooting", "limitations"):
                    continue
                uncovered = [cid for cid in group_ids if cid not in covered_ids]
                if len(uncovered) >= 10:
                    uncovered_groups[group_name] = uncovered

            cluster_budget = max(0, 5 - max(0, len(pages) - 3))  # at most 5, minus any already-added pages beyond base 3
            for group_name, group_ids in sorted(uncovered_groups.items(), key=lambda x: -len(x[1]))[:cluster_budget]:
                slug = _slugify(group_name)
                role = assign_page_role("docs", slug)
                strategy = build_content_strategy(role, "docs", workflows)
                cluster_purpose = f"Detailed guide for {group_name.replace('_', ' ')}"
                pages.append({
                    "section": "docs",
                    "slug": slug,
                    "output_path": compute_output_path("docs", slug, product_slug, platform=platform),
                    "url_path": compute_url_path("docs", slug, product_slug, platform=platform),
                    "title": _build_page_title(slug, "docs", product_name, platform),
                    "description": _build_page_description(slug, "docs", product_name, platform, cluster_purpose),
                    "purpose": cluster_purpose,
                    "template_variant": launch_tier,
                    "required_headings": ["Overview", "Usage", "Examples"],
                    "required_claim_ids": sorted(group_ids)[:15],
                    "required_snippet_tags": [],
                    "cross_links": [],
                    "seo_keywords": [product_slug, group_name.replace("_", " ")],
                    "forbidden_topics": strategy.get("forbidden_topics", []),
                    "page_role": role,
                    "content_strategy": strategy,
                })
            if uncovered_groups:
                logger.info(f"[W4] Claim-density expansion: added {min(len(uncovered_groups), 5)} topic cluster pages "
                           f"(n_claims={n_claims}, uncovered_groups={len(uncovered_groups)})")

    elif section == "reference":
        # Reference section: API overview
        slug = "api-overview"
        api_summary = product_facts.get("api_surface_summary", {})

        # Assign page role and build content strategy
        ref_role = assign_page_role("reference", slug)
        ref_strategy = build_content_strategy(ref_role, "reference", workflows)

        # TC-CREV-C-TRACK2: Build required_headings with Limitations if applicable
        ref_headings = ["Overview", "Key Modules", "Core Classes", "Usage Patterns"]
        if _has_limitations(product_facts):
            ref_headings.append("Limitations")

        pages.append({
            "section": section,
            "slug": slug,
            "output_path": compute_output_path(section, slug, product_slug, platform=platform),
            "url_path": compute_url_path(section, slug, product_slug, platform=platform),
            "title": _build_page_title("api-overview", section, product_name, platform),
            "description": _build_page_description("api-overview", section, product_name, platform, "High-level API surface overview"),
            "purpose": "High-level API surface overview",
            "template_variant": launch_tier,
            "required_headings": ref_headings,
            # TC-2202/R17-012: Pass full API surface to reference generator
            "api_surface_summary": api_summary,
            "required_claim_ids": sorted(
                claim_groups_dict.get("key_features", []) +
                claim_groups_dict.get("api_classes", [])
            )[:25],
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
                module_purpose = f"Reference documentation for {module}"
                pages.append({
                    "section": section,
                    "slug": slug,
                    "output_path": compute_output_path(section, slug, product_slug, platform=platform),
                    "url_path": compute_url_path(section, slug, product_slug, platform=platform),
                    "title": _build_page_title(slug, section, product_name, platform),
                    "description": _build_page_description(slug, section, product_name, platform, module_purpose),
                    "purpose": module_purpose,
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
            slug = f"how-to-{_derive_semantic_slug(feature_text) or f'feature-{i+1}'}"

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

                showcase_purpose = f"Feature showcase: {_derive_page_title(feature_text)}"
                pages.append({
                    "section": "kb",
                    "slug": slug,
                    "output_path": compute_output_path("kb", slug, product_slug, platform=platform),
                    "url_path": compute_url_path("kb", slug, product_slug, platform=platform),
                    "title": _derive_page_title(feature_text, prefix="How to:"),
                    "description": _build_page_description(slug, "kb", product_name, platform, showcase_purpose),
                    "purpose": showcase_purpose,
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
            "output_path": compute_output_path("kb", "faq", product_slug, platform=platform),
            "url_path": compute_url_path("kb", "faq", product_slug, platform=platform),
            "title": _build_page_title("faq", "kb", product_name, platform),
            "description": _build_page_description("faq", "kb", product_name, platform, "Common questions and answers"),
            "purpose": "Common questions and answers",
            "template_variant": launch_tier,
            "required_headings": ["Installation", "Usage", "Troubleshooting"],
            # TC-1909: Use faq claim_group with generous cap; fallback to install_steps + limitations
            "required_claim_ids": sorted(
                claim_groups_dict.get("faq", []) or
                (claim_groups_dict.get("install_steps", []) + claim_groups_dict.get("limitations", []))
            )[:15],
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
                "output_path": compute_output_path("kb", "troubleshooting", product_slug, platform=platform),
                "url_path": compute_url_path("kb", "troubleshooting", product_slug, platform=platform),
                "title": _build_page_title("troubleshooting", "kb", product_name, platform),
                "description": _build_page_description("troubleshooting", "kb", product_name, platform, "Common issues and solutions"),
                "purpose": "Common issues and solutions",
                "template_variant": launch_tier,
                "required_headings": ["Installation Issues", "Runtime Errors", "Performance"],
                # TC-1634: Merge troubleshooting + limitations claim_groups
                "required_claim_ids": sorted(
                    claim_groups_dict.get("troubleshooting", []) +
                    claim_groups_dict.get("limitations", [])
                ),
                "required_snippet_tags": [],
                "cross_links": [],
                "seo_keywords": [product_slug, "troubleshooting"],
                "forbidden_topics": ts_strategy.get("forbidden_topics", []),
                "page_role": ts_role,
                "content_strategy": ts_strategy,
            })

    elif section == "blog":
        # Blog section: announcement post
        # TC-2201 R17-010: Dynamic blog slug from product name
        blog_slug = _slugify(f"introducing-{product_name}")
        blog_role = assign_page_role("blog", blog_slug)
        blog_strategy = build_content_strategy(blog_role, "blog", workflows)
        blog_purpose = "Product announcement and highlights"

        pages.append({
            "section": "blog",
            "slug": blog_slug,
            "output_path": compute_output_path("blog", blog_slug, product_slug, platform=platform),
            "url_path": compute_url_path("blog", blog_slug, product_slug, platform=platform),
            "title": f"Introducing {product_name} for Python \u2014 Open-Source {product_facts.get('product_family', '').upper()} Processing",
            "description": _build_page_description(blog_slug, "blog", product_name, platform, blog_purpose),
            "purpose": blog_purpose,
            "template_variant": launch_tier,
            "required_headings": ["Introduction", "Key Features", "Getting Started", "Next Steps"],
            # TC-1910: Use marketing-relevant claims (use_cases + key_features)
            "required_claim_ids": sorted(
                (claim_groups_dict.get("use_cases", [])[:5] +
                 claim_groups_dict.get("key_features", [])[:5]) or
                [c["claim_id"] for c in claims[:5]]
            )[:10],
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
    platform: str = "",
) -> None:
    """Add cross-links between pages per specs/06_page_planning.md:31-35.

    Cross-linking rules:
    - docs -> reference
    - kb -> docs
    - blog -> products

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


def _populate_products_cross_section_links(
    pages: List[Dict[str, Any]],
    product_slug: str,
    locale: str = "en",
    platform: str = "",
) -> None:
    """Agent 42: Populate content_strategy.cross_section_links on the products _index page.

    The products section home must link to all sibling section homes
    (docs, reference, kb, blog) for top-level navigation.

    Per specs/06_page_planning.md Agent 42 mandatory page catalog contract.

    Note: W4 normalizes ruleset slug "_index" → "index" in page specs (line 4296).
    Both "index" and "_index" are therefore checked when locating the section home.
    """
    for page in pages:
        if page.get("section") == "products" and page.get("slug") in ("index", "_index"):
            section_homes = []
            for section in ("docs", "reference", "kb", "blog"):
                section_homes.append(
                    build_absolute_public_url(
                        section=section,
                        family=product_slug,
                        locale=locale,
                        slug="_index",
                    )
                )
            page.setdefault("content_strategy", {})["cross_section_links"] = section_homes
            break


def add_claim_overlap_cross_links(pages: List[Dict[str, Any]]) -> None:
    """TC-1742: Add related_pages based on claim overlap between pages.

    For each page, finds other pages sharing claims and adds the top 3 by
    overlap score as related_pages. This data is consumed by W6 to inject
    'See Also' sections.

    Args:
        pages: List of page specifications (modified in place).
    """
    # Build claim_id → page_slugs mapping
    claim_to_pages: Dict[str, List[str]] = {}
    for page in pages:
        slug = page.get("slug", "")
        for cid in page.get("required_claim_ids", []):
            if cid not in claim_to_pages:
                claim_to_pages[cid] = []
            claim_to_pages[cid].append(slug)

    # For each page, compute overlap with every other page
    for page in pages:
        slug = page.get("slug", "")
        page_claims = set(page.get("required_claim_ids", []))
        if not page_claims:
            continue

        # Count shared claims with other pages
        overlap_counts: Dict[str, int] = {}
        for cid in page_claims:
            for other_slug in claim_to_pages.get(cid, []):
                if other_slug != slug:
                    overlap_counts[other_slug] = overlap_counts.get(other_slug, 0) + 1

        if not overlap_counts:
            continue

        # Sort by overlap count descending, take top 3
        sorted_related = sorted(overlap_counts.items(), key=lambda x: x[1], reverse=True)[:3]

        # Look up section for each related page
        slug_to_section = {p["slug"]: p["section"] for p in pages}
        related_pages = []
        for rel_slug, overlap_count in sorted_related:
            overlap_score = overlap_count / len(page_claims) if page_claims else 0.0
            related_pages.append({
                "slug": rel_slug,
                "section": slug_to_section.get(rel_slug, ""),
                "overlap_score": round(overlap_score, 2),
            })

        page["related_pages"] = related_pages


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
      _index* -> context-dependent (toc/landing/comprehensive_guide/workflow_page)
      index*  -> landing (blog posts)
      feature* -> workflow_page
      howto*  -> feature_showcase
      reference* (under reference section) -> api_reference
      installation*, license* -> workflow_page
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
            # Subsection _index (e.g., getting-started/_index.md) -> workflow_page
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
    platform: str = "",
) -> List[Dict[str, Any]]:
    """Enumerate templates from specs/templates/ hierarchy.

    Walks the template directory and discovers all template files,
    returning a deterministic list of template descriptors.

    Args:
        template_dir: Root template directory (specs/templates)
        subdomain: Subdomain (e.g., docs.aspose.org, blog.aspose.org)
        family: Product family (e.g., cells, words)
        locale: Language code (e.g., en, es)
        platform: Platform segment (e.g., "python"). Empty string for V1 layout.

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
        # Section comes from subdomain: docs.aspose.org -> "docs"
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

    # TC-1604: classes may contain dicts (from code_analyzer AST parsing) or plain
    # strings.  Normalise to string names before building the look-up set so that
    # unhashable dict entries don't crash set().
    raw_classes = product_facts.get("api_surface_summary", {}).get("classes", [])
    api_class_ids = set(
        c["name"] if isinstance(c, dict) else c for c in raw_classes
    )
    claims = product_facts.get("claims", [])

    # Filter out noise words from api_surface_summary class names
    noise_words = {
        "NotImplementedError", "PascalCase", "TestClass", "ValueError",
        "TypeError", "AttributeError", "ImportError", "RuntimeError",
        "KeyError", "IndexError", "FileNotFoundError", "IOError",
    }
    class_names = [n for n in api_class_ids if n not in noise_words]

    if not class_names:
        return defaults

    # Rank class names by mention frequency in claim text (most-mentioned = most important)
    combined_text = " ".join(c.get("claim_text", "") for c in claims)

    name_counts = {}
    for name in class_names:
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
    # TC-1713: Enrich body tokens from product_facts enriched claims when available
    _pf = product_facts or {}
    _claims = _pf.get("claims", [])
    _claim_map = {c.get("claim_id"): c for c in _claims}
    _cg = _pf.get("claim_groups", {})

    def _get_enriched(claim_ids, max_items=5, join_str="\n\n"):
        """Get enriched text from claim IDs, joining multiple claims."""
        texts = []
        for cid in (claim_ids or [])[:max_items]:
            claim = _claim_map.get(cid)
            if claim:
                text = claim.get("enriched_text") or claim.get("claim_text", "")
                if text and len(text.split()) >= 5:
                    texts.append(text)
        return join_str.join(texts)

    # TC-1713: Generate intro from positioning or key features
    _positioning = _pf.get("positioning", {})
    _tagline = _positioning.get("tagline", "")
    _short_desc = _positioning.get("short_description", "")
    if _tagline and _short_desc:
        tokens["__BODY_INTRO__"] = f"{_tagline} {_short_desc}"
    elif _short_desc:
        tokens["__BODY_INTRO__"] = _short_desc
    else:
        tokens["__BODY_INTRO__"] = f"Welcome to the {product_name} documentation. This guide covers the main features and capabilities."

    # TC-1713: Overview from key features
    _kf_text = _get_enriched(_cg.get("key_features", []), max_items=3)
    if _kf_text:
        tokens["__BODY_OVERVIEW__"] = f"{product_name} provides powerful capabilities for developers:\n\n{_kf_text}"
    else:
        tokens["__BODY_OVERVIEW__"] = f"{product_name} enables developers to work with {family} files programmatically."

    # TC-1713: Code samples from snippets context
    tokens["__BODY_CODE_SAMPLES__"] = f"The following examples demonstrate how to use the {product_name} API for common operations."

    # TC-1713: Conclusion
    tokens["__BODY_CONCLUSION__"] = f"This guide covered the essential features of {product_name}. Explore the API reference and tutorials for advanced usage patterns."

    # TC-1713: Prerequisites from install_steps
    _install_text = _get_enriched(_cg.get("install_steps", []), max_items=3)
    if _install_text:
        tokens["__BODY_PREREQUISITES__"] = _install_text
    else:
        tokens["__BODY_PREREQUISITES__"] = f"To use {product_name}, install the package with pip and import it in your Python project."

    # TC-1713: Steps from workflows
    _wf_text = _get_enriched(_cg.get("workflow_claims", []), max_items=5, join_str="\n\n")
    if _wf_text:
        tokens["__BODY_STEPS__"] = _wf_text
    else:
        tokens["__BODY_STEPS__"] = f"Follow these steps to get started with {product_name} in your application."

    # TC-1713: Key takeaways from best_practices
    _bp_text = _get_enriched(_cg.get("best_practices", []), max_items=5, join_str="\n- ")
    if _bp_text:
        tokens["__BODY_KEY_TAKEAWAYS__"] = f"- {_bp_text}"
    else:
        tokens["__BODY_KEY_TAKEAWAYS__"] = f"Key capabilities of {product_name} include comprehensive {family} file support and cross-platform compatibility."

    # TC-1713: Troubleshooting from troubleshooting/limitation claims
    _ts_text = _get_enriched(_cg.get("troubleshooting", []) or _cg.get("limitations", []), max_items=3)
    if _ts_text:
        tokens["__BODY_TROUBLESHOOTING__"] = _ts_text
    else:
        tokens["__BODY_TROUBLESHOOTING__"] = f"If you encounter issues with {product_name}, check your package version and dependencies. Consult the project's GitHub issues for known problems."

    tokens["__BODY_NOTES__"] = f"For the latest updates and release notes, check the {product_name} project repository."

    tokens["__BODY_SEE_ALSO__"] = f"Explore the {product_name} API reference, tutorials, and developer guide for more information."

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

        # TC-P3B: Enrich overview content for products pages with positioning + key features
        if section == "products" and product_facts:
            positioning = product_facts.get("positioning", {})
            tagline = positioning.get("tagline", "")
            short_desc = positioning.get("short_description", "")
            claim_groups_data = product_facts.get("claim_groups", {})
            feature_ids = sorted(claim_groups_data.get("key_features", []))[:5]
            claims_list = product_facts.get("claims", [])

            overview_parts = []
            if tagline:
                overview_parts.append(tagline)
            if short_desc:
                overview_parts.append(short_desc)

            # Add key features as markdown bullets with claim markers
            # R1: Filter code-like claims and sanitize for YAML safety
            feature_bullets = []
            for cid in feature_ids:
                claim = next((c for c in claims_list if c.get("claim_id") == cid), None)
                if claim:
                    # TC-1712: Prefer enriched_text for product page features
                    text = str(claim.get("enriched_text") or claim.get("claim_text", "")).replace("\n", " ").strip()[:200]
                    # Skip code-like claims (assignments, method calls, control flow)
                    if any(p in text for p in ['=', 'self.', '()', 'None:', 'True ', 'False ', 'assert ', 'print(']):
                        continue
                    # Sanitize YAML-breaking characters (comprehensive)
                    # Remove triple quotes, escape colons, remove braces, remove backticks
                    text = (text
                           .replace('"""', '')  # Remove docstring markers
                           .replace("'''", '')  # Remove single-quote docstrings
                           .replace(": ", " - ")  # Escape colon+space (most common)
                           .replace(":", " -")  # Escape remaining colons
                           .replace("{", "")  # Remove braces
                           .replace("}", "")
                           .replace("`", "")  # Remove backticks
                           .replace("|", "")  # Remove pipe (YAML block scalar)
                           .replace(">", "")  # Remove folded scalar
                           .strip())
                    # Skip if sanitization left nothing meaningful
                    if len(text) < 10:
                        continue
                    feature_bullets.append(f"- {text}")

            if feature_bullets:
                overview_parts.append("\n**Key Features:**\n")
                overview_parts.append("\n".join(feature_bullets))

            if overview_parts:
                tokens["__OVERVIEW_CONTENT__"] = "\n\n".join(overview_parts)
            else:
                tokens["__OVERVIEW_CONTENT__"] = f"This section covers {slug.replace('-', ' ')} in {product_name}. Learn about features, usage, and best practices."
        else:
            tokens["__OVERVIEW_CONTENT__"] = f"This section covers {slug.replace('-', ' ')} in {product_name}. Learn about features, usage, and best practices."

        tokens["__SUBTITLE__"] = f"{slug.replace('-', ' ').title()} Reference"
        tokens["__LINK_TITLE__"] = slug.replace('-', ' ').title()
        tokens["__LINKTITLE__"] = slug.replace('-', ' ').title()

        # BODY BLOCKS (structured content sections)
        # TC-1712/1713: Enrich body blocks from product_facts enriched claims
        _api_text = _get_enriched(_cg.get("key_features", [])[:3])
        tokens["__BODY_API_OVERVIEW__"] = _api_text if _api_text else f"The {product_name} API provides comprehensive access to {family} functionality."

        _feat_text = _get_enriched(_cg.get("key_features", [])[:5], join_str="\n- ")
        tokens["__BODY_FEATURES__"] = f"- {_feat_text}" if _feat_text else f"Key features include file format support, rendering, and platform integration."

        _gs_text = _get_enriched(_cg.get("install_steps", [])[:3])
        tokens["__BODY_GETTING_STARTED__"] = _gs_text if _gs_text else f"To get started with {product_name}, install the package and import the necessary modules."

        tokens["__BODY_EXAMPLES__"] = f"The following examples demonstrate common {family} operations with {product_name}."
        tokens["__BODY_GUIDES__"] = f"Explore detailed guides for working with {family} files using {product_name}."

        _qs_text = _get_enriched(_cg.get("quickstart_steps", [])[:3])
        tokens["__BODY_QUICKSTART__"] = _qs_text if _qs_text else f"Quick start guide for {product_name}."
        tokens["__BODY_IN_THIS_SECTION__"] = f"This section covers essential topics for {product_name} development."
        tokens["__BODY_NEXT_STEPS__"] = f"Explore advanced features and integration options for {product_name}."
        tokens["__BODY_RELATED_LINKS__"] = f"API reference, tutorials, and code examples for {product_name}."
        tokens["__BODY_SUPPORT__"] = f"Get support for {product_name} through documentation, forums, and technical assistance."

        _faq_text = _get_enriched(_cg.get("faq", [])[:3])
        tokens["__BODY_FAQ__"] = _faq_text if _faq_text else f"Frequently asked questions about {product_name}."

        _uc_text = _get_enriched(_cg.get("use_cases", [])[:3])
        tokens["__BODY_USECASES__"] = _uc_text if _uc_text else f"Common use cases for {product_name}."
        tokens["__BODY_USAGE_SNIPPET__"] = f"Basic usage example for {product_name}."
        tokens["__BODY_SYMPTOMS__"] = f"N/A"

        # BODY BLOCKS (left/right column layout)
        # TC-P3B: Enrich body blocks for products pages with workflow steps
        if section == "products" and product_facts:
            workflows = product_facts.get("workflows", [])
            if workflows:
                wf = workflows[0]
                wf_name = wf.get("name", "Getting Started")
                wf_desc = wf.get("description", "")
                tokens["__BODY_BLOCK_TITLE_LEFT__"] = f"How to Use {product_name}"
                steps = wf.get("steps", [])
                if steps:
                    step_text = "\n".join(f"- {s}" for s in steps[:5])
                    tokens["__BODY_BLOCK_CONTENT_LEFT__"] = step_text
                else:
                    tokens["__BODY_BLOCK_CONTENT_LEFT__"] = wf_desc or f"Follow the {wf_name} workflow to get started."
                tokens["__BODY_BLOCK_TITLE_RIGHT__"] = "Getting Started"
                tokens["__BODY_BLOCK_CONTENT_RIGHT__"] = f"Install {product_name} via package manager and follow the {wf_name.lower()} guide to begin development."
            else:
                tokens["__BODY_BLOCK_TITLE_LEFT__"] = "Features"
                tokens["__BODY_BLOCK_CONTENT_LEFT__"] = f"{product_name} provides comprehensive {family} file processing capabilities."
                tokens["__BODY_BLOCK_TITLE_RIGHT__"] = "Getting Started"
                tokens["__BODY_BLOCK_CONTENT_RIGHT__"] = f"Install {product_name} via package manager and explore the API documentation to begin development."
        else:
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
        # TC-P3B: Enrich FAQ for products pages with format/install/requirements questions
        if section == "products" and product_facts:
            supported_formats = product_facts.get("supported_formats", [])
            format_list = ", ".join(sorted(f.get("name", f.get("format", "")) for f in supported_formats)[:8]) if supported_formats else f"{family} files"
            tokens["__FAQ_QUESTION__"] = f"What formats does {product_name} support?"
            tokens["__FAQ_ANSWER__"] = f"{product_name} supports {format_list}. Install via pip and import the library to get started. See the documentation for complete format support details."
        else:
            tokens["__FAQ_QUESTION__"] = f"How do I use {product_name} in my project?"
            tokens["__FAQ_ANSWER__"] = f"Install {product_name} via package manager, import the library, and use the API to work with {family} files. See the getting started guide for detailed instructions."

        # PLUGIN/PRODUCT METADATA
        # TC-P3B: Enrich plugin metadata from positioning
        if section == "products" and product_facts:
            positioning = product_facts.get("positioning", {})
            p_desc = positioning.get("short_description", "")
            tokens["__PLUGIN_NAME__"] = product_name
            tokens["__PLUGIN_DESCRIPTION__"] = p_desc if p_desc else f"{product_name} library - comprehensive {family} file format support"
            tokens["__PLUGIN_PLATFORM__"] = "Python"
        else:
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
            # TC-1634: Add token mappings for new claim_groups (Round 10 content types)
            tokens["__USE_CASES_COUNT__"] = str(len(claim_groups.get("use_cases", [])))
            tokens["__FAQ_COUNT__"] = str(len(claim_groups.get("faq", [])))
            tokens["__BEST_PRACTICES_COUNT__"] = str(len(claim_groups.get("best_practices", [])))
            tokens["__PERFORMANCE_COUNT__"] = str(len(claim_groups.get("performance", [])))
            tokens["__TUTORIALS_COUNT__"] = str(len(claim_groups.get("tutorials", [])))
            tokens["__TROUBLESHOOTING_COUNT__"] = str(len(claim_groups.get("troubleshooting", [])))
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

    # TC-1711: Sanitize token values — ensure all are strings
    for token_name, value in list(tokens.items()):
        if not isinstance(value, str):
            if isinstance(value, (list, tuple)):
                tokens[token_name] = "\n".join(str(v) for v in value)
                logger.warning(
                    "[W4] Token %s had type %s, converted to joined string",
                    token_name, type(value).__name__,
                )
            elif isinstance(value, dict):
                tokens[token_name] = ""
                logger.error(
                    "[W4] Token %s was a dict — set to empty string to prevent data leakage",
                    token_name,
                )
            elif value is None:
                tokens[token_name] = ""
            else:
                tokens[token_name] = str(value)
                logger.warning(
                    "[W4] Token %s had type %s, cast to str",
                    token_name, type(value).__name__,
                )

    # TC-1903: Sanitize token values — strip code fence markers that would
    # nest inside template fences and cause broken markdown.
    for token_name, value in list(tokens.items()):
        if isinstance(value, str) and '```' in value:
            value = re.sub(r'```\w*\n?', '', value)
            value = re.sub(r'\n```\s*', ' ', value)
            tokens[token_name] = value.strip()

    return tokens


def fill_template_placeholders(
    template: Dict[str, Any],
    section: str,
    product_slug: str,
    locale: str,
    subdomain: str,
    product_facts: Optional[Dict[str, Any]] = None,
    platform: str = "",
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
        platform: V2 platform identifier (e.g., "python", "typescript")

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
        platform=platform,
    )

    url_path = compute_url_path(
        section=section,
        slug=slug,
        product_slug=product_slug,
        locale=locale,
        platform=platform,
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
    # Phase 1A: Use ClaimKindRegistry for semantic claim selection
    # Replaces positional slicing (key_features[2:7][:5]) with section/role-based selection
    required_claim_ids = []
    if product_facts:
        claim_groups = product_facts.get("claim_groups", {})
        if isinstance(claim_groups, dict):
            required_claim_ids = REGISTRY.select_claims_for_page(
                claim_groups, section, page_role
            )

    # Resolve title through token_mappings if it's still a placeholder
    resolved_title = title
    if resolved_title and resolved_title.startswith("__") and resolved_title.endswith("__"):
        resolved_title = token_mappings.get(resolved_title, resolved_title)

    return {
        "section": section,
        "slug": slug,
        "template_path": template["template_path"],
        "template_variant": template["variant"],
        "output_path": output_path,
        "url_path": url_path,
        "title": resolved_title,
        "purpose": f"Template-driven {section} page",
        "page_role": page_role,
        "content_strategy": content_strategy,
        "required_headings": [],
        "required_claim_ids": required_claim_ids,
        "required_snippet_tags": [],
        "cross_links": [],
        "token_mappings": token_mappings,
    }


def _apply_page_preservation(
    page_plan: Dict[str, Any],
    run_config: Any,
    run_layout: RunLayout,
) -> Dict[str, Any]:
    """TC-1763: Apply page preservation for incremental updates.

    Compares current page plan against a previous run's page plan to determine
    which pages are preserved (unchanged), updated, new, or deleted.

    Uses Jaccard similarity on claim IDs to measure page overlap:
      overlap = len(current_claims & previous_claims) / max(1, len(current_claims | previous_claims))

    Pages with overlap >= threshold are marked "preserved", those with partial
    overlap are "updated", brand-new pages are "new", and pages only in the
    previous run are added back as "deleted" (for downstream workers like W6
    to clean up files).

    Args:
        page_plan: Current page plan dict with "pages" list.
        run_config: RunConfig object or dict. Must support is_incremental_enabled(),
                    get_previous_run_path(), and get_incremental_config() if RunConfig.
        run_layout: RunLayout for loading previous artifacts.

    Returns:
        Modified page_plan with page_status set on each page.
    """
    # Determine if incremental is enabled -- handle both RunConfig and dict
    if isinstance(run_config, dict):
        incremental = run_config.get("incremental", {}) or {}
        if not incremental.get("enabled", False):
            return page_plan
        previous_run_path = incremental.get("previous_run_path")
        threshold = incremental.get("page_preservation_threshold", 0.75)
    else:
        if not run_config.is_incremental_enabled():
            return page_plan
        previous_run_path = run_config.get_previous_run_path()
        inc_config = run_config.get_incremental_config()
        threshold = inc_config.get("page_preservation_threshold", 0.75)

    # Load previous page plan
    previous_plan = run_layout.load_previous_artifact(
        "page_plan.json", previous_run_path
    )
    if previous_plan is None:
        logger.info("[W4 IAPlanner] No previous page_plan.json found; skipping preservation")
        # Mark all current pages as new
        for page in page_plan.get("pages", []):
            page["page_status"] = "new"
        return page_plan

    # Build lookup of previous pages by (section_path, slug)
    # Use section_path if present, otherwise fall back to section
    prev_pages_by_key: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for prev_page in previous_plan.get("pages", []):
        sp = prev_page.get("section_path", prev_page.get("section", ""))
        key = (sp, prev_page.get("slug", ""))
        prev_pages_by_key[key] = prev_page

    # Track which previous pages are matched so we can detect deletions
    matched_prev_keys: set = set()

    for page in page_plan.get("pages", []):
        sp = page.get("section_path", page.get("section", ""))
        key = (sp, page.get("slug", ""))
        prev_page = prev_pages_by_key.get(key)

        if prev_page is None:
            # Page exists in current but not in previous
            page["page_status"] = "new"
            continue

        matched_prev_keys.add(key)

        # Compute Jaccard similarity on claim IDs
        current_claims = set(page.get("required_claim_ids", []))
        previous_claims = set(prev_page.get("required_claim_ids", []))

        union_size = len(current_claims | previous_claims)
        if union_size == 0:
            # Both empty -- pages match perfectly
            overlap = 1.0
        else:
            overlap = len(current_claims & previous_claims) / max(1, union_size)

        if overlap >= threshold:
            page["page_status"] = "preserved"
        else:
            page["page_status"] = "updated"

    # Add deleted pages (in previous but not in current)
    for key, prev_page in sorted(prev_pages_by_key.items()):
        if key in matched_prev_keys:
            continue
        # Create a minimal deleted page entry
        deleted_page = dict(prev_page)
        deleted_page["page_status"] = "deleted"
        page_plan["pages"].append(deleted_page)

    preserved = sum(1 for p in page_plan["pages"] if p.get("page_status") == "preserved")
    updated = sum(1 for p in page_plan["pages"] if p.get("page_status") == "updated")
    new = sum(1 for p in page_plan["pages"] if p.get("page_status") == "new")
    deleted = sum(1 for p in page_plan["pages"] if p.get("page_status") == "deleted")
    logger.info(
        f"[W4 IAPlanner] Page preservation: "
        f"{preserved} preserved, {updated} updated, {new} new, {deleted} deleted "
        f"(threshold={threshold})"
    )

    return page_plan


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
        # Stage 2 hardening: Early config validation (before any I/O) — fail-fast on bad config
        _rc_dict = run_config if isinstance(run_config, dict) else {}
        _early_skip = _rc_dict.get("skip_sections", [])
        _early_required = _rc_dict.get("required_sections", [])
        _early_conflicted = set(_early_required) & set(_early_skip)
        if _early_conflicted:
            raise IAPlannerConfigurationError(
                f"[W4] Configuration conflict: sections {sorted(_early_conflicted)} appear in both "
                f"'required_sections' and 'skip_sections'. Required sections cannot be skipped. "
                f"Remove them from 'skip_sections' in run_config."
            )
        _early_expansion = _rc_dict.get("page_expansion", {})
        for _sec_name, _sec_cfg in _early_expansion.items():
            if isinstance(_sec_cfg, dict):
                _min_p = _sec_cfg.get("min_pages", 0)
                if _min_p > 0 and _sec_name in _early_skip:
                    raise IAPlannerConfigurationError(
                        f"[W4] Section '{_sec_name}' has page_expansion.min_pages={_min_p} "
                        f"but is listed in skip_sections. Remove it from skip_sections."
                    )

        # Load input artifacts
        product_facts = load_product_facts(run_layout.artifacts_dir)
        snippet_catalog = load_snippet_catalog(run_layout.artifacts_dir)

        # TC-2368: Link claims to demo snippets via TF-IDF similarity
        try:
            product_facts["claims"] = link_claims_to_snippets(
                product_facts.get("claims", []),
                snippet_catalog,
            )
        except Exception as _link_err:
            logger.warning("claim_snippet_linking_failed", error=str(_link_err))

        # Load section quotas from ruleset (TC-953)
        # src/launch/workers/w4_ia_planner/worker.py -> go up 5 levels to reach repo root
        repo_root = Path(__file__).parent.parent.parent.parent.parent
        # Spec v1.1 Stage 1: read ruleset_version from run_config (default: "ruleset.v1")
        _ruleset_version = (
            run_config.get("ruleset_version", "ruleset.v1")
            if isinstance(run_config, dict)
            else getattr(run_config, "ruleset_version", "ruleset.v1")
        )
        section_quotas = load_ruleset_quotas(repo_root, ruleset_version=_ruleset_version)

        # TC-984: Load full ruleset for config-driven page requirements
        ruleset = load_ruleset(repo_root, ruleset_version=_ruleset_version)

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
        # V2: Extract platform from run_config for platform-aware paths
        if isinstance(run_config_obj, dict):
            platform = run_config_obj.get("target_platform", "")
        else:
            platform = getattr(run_config_obj, "target_platform", "")

        # TC-2514: Load family capabilities registry (produced by W2) for slug generation
        family_capabilities = _load_family_capabilities(run_dir)

        # TC-984: Compute evidence volume and effective quotas
        # Per specs/06_page_planning.md "Optional Page Selection Algorithm"
        # TC-2605: Pass platform for platform-aware slug generation
        _slug_platform = platform or "python"
        merged_requirements = load_and_merge_page_requirements(
            ruleset, product_slug, product_facts,
            family_capabilities=family_capabilities,
            platform=_slug_platform,
        )
        evidence_volume = compute_evidence_volume(product_facts, snippet_catalog)
        effective_quotas = compute_effective_quotas(
            evidence_volume, launch_tier, section_quotas, merged_requirements
        )

        # TC-2529/TC-2530: Quality feedback loop — W4 consumes feedback for claim count adjustment
        _use_feedback_w4 = (
            run_config.get("use_feedback", False)
            if isinstance(run_config, dict)
            else getattr(run_config, "use_feedback", False)
        )
        _w4_feedback: Dict[str, Any] = {}
        if _use_feedback_w4:
            _w4_feedback = read_quality_feedback(run_dir)
            if _w4_feedback:
                logger.info(
                    "w4_feedback_loaded feedback_entries=%d",
                    len(_w4_feedback.get("pages", [])),
                )
            else:
                logger.info("w4_feedback_skip quality_feedback.json not found or empty")

        # Determine template directory (Spec v1.1 Agent-41: respect templates_version)
        _templates_version = (
            run_config.get("templates_version", "templates.v1")
            if isinstance(run_config, dict)
            else getattr(run_config, "templates_version", "templates.v1")
        )
        template_dir = resolve_templates_root(repo_root, _templates_version)

        # Plan pages using template enumeration
        all_pages = []
        sections_subdomains = [
            ("products", "products.aspose.org"),
            ("docs", "docs.aspose.org"),
            ("reference", "reference.aspose.org"),
            ("kb", "kb.aspose.org"),
            ("blog", "blog.aspose.org"),
        ]

        # TC-2201 R17-011: Allow sections to be skipped via run_config
        if isinstance(run_config_obj, dict):
            skip_sections = run_config_obj.get("skip_sections", [])
        else:
            skip_sections = getattr(run_config_obj, "skip_sections", [])

        # Stage 2 hardening: Validate required/skip conflict and page_expansion constraints
        _required_sections = (
            run_config_obj.get("required_sections", [])
            if isinstance(run_config_obj, dict)
            else getattr(run_config_obj, "required_sections", [])
        )
        _conflicted = set(_required_sections) & set(skip_sections)
        if _conflicted:
            raise IAPlannerConfigurationError(
                f"[W4] Configuration conflict: sections {sorted(_conflicted)} appear in both "
                f"'required_sections' and 'skip_sections'. Required sections cannot be skipped. "
                f"Remove them from 'skip_sections' in run_config."
            )
        _page_expansion = (
            run_config_obj.get("page_expansion", {})
            if isinstance(run_config_obj, dict)
            else getattr(run_config_obj, "page_expansion", {})
        )
        for _sec_name, _sec_cfg in _page_expansion.items():
            if isinstance(_sec_cfg, dict):
                _min_p = _sec_cfg.get("min_pages", 0)
                if _min_p > 0 and _sec_name in skip_sections:
                    raise IAPlannerConfigurationError(
                        f"[W4] Section '{_sec_name}' has page_expansion.min_pages={_min_p} "
                        f"but is listed in skip_sections. Remove it from skip_sections."
                    )
        logger.info(
            "w4_config_validated required=%s skip=%s expansion_sections=%s",
            _required_sections, skip_sections, list(_page_expansion.keys()),
        )

        for section, subdomain in sections_subdomains:
            # TC-2201 R17-011: Skip sections listed in skip_sections
            if section in skip_sections:
                logger.info(f"[W4] Skipping section '{section}' (in skip_sections)")
                continue

            # Enumerate templates for this section
            templates = enumerate_templates(
                template_dir=template_dir,
                subdomain=subdomain,
                family=product_slug,
                locale=locale,
                platform=platform,
            )

            if not templates:
                # Fallback to hardcoded planning if no templates found
                section_pages = plan_pages_for_section(
                    section=section,
                    launch_tier=launch_tier,
                    product_facts=product_facts,
                    snippet_catalog=snippet_catalog,
                    product_slug=product_slug,
                    platform=platform,
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
                    platform=platform,
                )
                all_pages.append(page_spec)

            logger.info(f"[W4 IAPlanner] Planned {len(selected)} pages for section: {section} (template-driven)")

        # TC-984: Inject config-driven mandatory pages
        # Per specs/06_page_planning.md "Step 1: Add all mandatory pages"
        # Mandatory pages from merged config that are not yet covered by template-generated pages
        for section, subdomain in sections_subdomains:
            # TC-RCA: Enforce skip_sections in mandatory page injection (Loop 2)
            if section in skip_sections:
                continue
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

            # TC-1741: Track used claim IDs for cross-page deduplication
            used_claim_ids = set()
            for p in all_pages:
                used_claim_ids.update(p.get("required_claim_ids", []))

            for mp in mandatory_pages_config:
                m_slug = mp.get("slug", "")
                m_role = mp.get("page_role", "")
                # Spec v1.1: carry through optional title and folder_index from ruleset entry
                m_title = mp.get("title", None)
                m_folder_index = mp.get("folder_index", False)
                # Normalize _index -> index to match enumerate_templates convention
                normalized_slug = "index" if m_slug == "_index" else m_slug
                if not m_slug:
                    continue
                if normalized_slug in existing_slugs:
                    # Agent 45: If mandatory page has explicit role, override the
                    # template-enumerated page's role (e.g., _index toc > template landing)
                    if m_role:
                        for p in all_pages:
                            if p["section"] == section and p["slug"] == normalized_slug:
                                if p["page_role"] != m_role:
                                    logger.info(
                                        "[W4 Agent45] Override %s/%s role: %s → %s (mandatory)",
                                        section, normalized_slug, p["page_role"], m_role,
                                    )
                                    p["page_role"] = m_role
                                break
                    continue
                m_slug = normalized_slug

                role = m_role or assign_page_role(section, m_slug, is_index=(m_slug == "_index"))

                # Agent 44: Override feature_blog slug with workflow-derived slug
                _wf_result = None
                if role == "feature_blog" and section == "blog":
                    _wf_result = score_blog_workflow(
                        product_facts, snippet_catalog,
                        product_slug=product_slug,
                        family_capabilities=family_capabilities,
                        platform=_slug_platform,
                    )
                    if _wf_result["score"] > 0:
                        m_slug = _wf_result["slug"]
                        m_title = _wf_result["title"]
                        logger.info(
                            "[W4 Agent44] feature_blog slug: %s (score=%d, workflow=%s)",
                            m_slug, _wf_result["score"], _wf_result["workflow_tag"],
                        )

                strategy = build_content_strategy(role, section, workflows=[])

                # TC-1741: Semantic claim selection via ClaimKindRegistry
                # Replaces positional slicing (key_features[2:7]) with audience-aware
                # selection using page_role priorities and cross-page deduplication.
                is_toc = role == "toc" or m_slug in ("index", "_index")

                if is_toc:
                    required_claim_ids = REGISTRY.select_claims_for_page(
                        claim_groups, section, role,
                        max_claims=2, exclude_ids=used_claim_ids,
                    )
                else:
                    required_claim_ids = REGISTRY.select_claims_for_page(
                        claim_groups, section, role,
                        exclude_ids=used_claim_ids,
                    )
                # Track used claims for cross-page deduplication
                used_claim_ids.update(required_claim_ids)

                # Spec v1.1: prefer ruleset title over slug-derived title
                display_title = (
                    m_title
                    or m_slug.replace("-", " ").replace("_", "").strip().title()
                    or "Index"
                )

                # Spec v1.1: folder_index=true → getting-started/_index.md layout
                output_path = compute_output_path(
                    section, m_slug, product_slug,
                    subdomain=subdomain, locale=locale, platform=platform,
                )
                if m_folder_index and not output_path.endswith("_index.md"):
                    # Replace trailing /<slug>.md with /<slug>/_index.md
                    output_path = output_path[: output_path.rfind("/")] + f"/{m_slug}/_index.md"

                page_spec = {
                    "section": section,
                    "slug": m_slug,
                    "output_path": output_path,
                    "url_path": compute_url_path(
                        section, m_slug, product_slug, locale=locale, platform=platform,
                    ),
                    # Agent 42: explicit subpath for folder-index pages so W5/downstream workers
                    # can identify nesting without re-parsing output_path.
                    "subpath": [m_slug] if m_folder_index else [],
                    "title": display_title,
                    # `purpose` = internal W5 LLM generation hint (never written to Hugo frontmatter)
                    "purpose": f"Mandatory {section} page: {m_slug}",
                    # `description` = SEO-friendly public metadata written to Hugo frontmatter.
                    # Uses human-readable section names so "kb" becomes "knowledge base", etc.
                    "description": "{title} - {prod} {sec}".format(
                        title=display_title,
                        prod=product_facts.get("product_name", ""),
                        sec={
                            "docs": "documentation guide",
                            "kb": "knowledge base article",
                            "reference": "API reference guide",
                            "products": "product guide",
                            "blog": "blog post",
                        }.get(section, f"{section} guide"),
                    ).strip(" -"),
                    "template_variant": launch_tier,
                    "required_headings": _default_headings_for_role(role, product_facts),
                    "required_claim_ids": required_claim_ids,
                    "required_snippet_tags": [],
                    "cross_links": [],
                    "page_role": role,
                    "content_strategy": strategy,
                    # Spec v1.1: hint for W5 when mandatory page has no supporting evidence
                    "not_evidenced_hint": len(required_claim_ids) == 0,
                }

                # Agent 43: Inject format evidence into conversion how-to pages
                _is_convert = (
                    role == "howto_article"
                    and (
                        "convert" in (m_slug or "").lower()
                        or "convert" in (m_title or "").lower()
                    )
                )
                if _is_convert:
                    raw_formats = product_facts.get("supported_formats", [])
                    fmt_list = sorted(
                        [
                            {"format": f.get("format", ""), "direction": f.get("direction", "unknown")}
                            for f in raw_formats
                            if f.get("format")
                        ],
                        key=lambda x: (x["format"], x["direction"]),
                    )
                    raw_pairs = claim_groups.get("conversion_pairs", [])
                    pair_list = sorted(
                        [
                            {"source": p["source"], "target": p["target"]}
                            for p in raw_pairs
                            if isinstance(p, dict) and p.get("source") and p.get("target")
                        ],
                        key=lambda x: (x["source"], x["target"]),
                    )
                    page_spec["content_strategy"]["is_conversion_howto"] = True
                    page_spec["content_strategy"]["supported_formats"] = fmt_list
                    page_spec["content_strategy"]["conversion_pairs"] = pair_list

                # Agent 44: Store workflow metadata in content_strategy for W5
                if _wf_result and _wf_result["score"] > 0:
                    page_spec["content_strategy"]["selected_workflow"] = {
                        "workflow_tag": _wf_result["workflow_tag"],
                        "score": _wf_result["score"],
                    }
                    if _wf_result["claim_ids"]:
                        page_spec["required_claim_ids"] = _wf_result["claim_ids"]
                        page_spec["not_evidenced_hint"] = False

                all_pages.append(page_spec)
                existing_slugs.add(m_slug)
                injected_count += 1

            if injected_count > 0:
                logger.info(
                    f"[W4 IAPlanner] Injected {injected_count} mandatory pages "
                    f"for section: {section} (config-driven)"
                )

        # TC-2435: Load content_policy from run_config["policy"] (None if key absent)
        from .content_policy import load_policy_config as _load_policy_config
        _rc_for_policy = run_config_obj if isinstance(run_config_obj, dict) else (
            run_config_obj.__dict__ if hasattr(run_config_obj, "__dict__") else {}
        )
        content_policy = _load_policy_config(_rc_for_policy)

        # TC-2439: Load repo_profile.json for quality_tier-based tier_multiplier
        import os as _os
        _repo_profile = {}
        if _os.environ.get("LAUNCH_REPO_PROFILING") == "1":
            try:
                _rp_path = run_layout.artifacts_dir / "repo_profile.json"
                if _rp_path.exists():
                    import json as _json_rp
                    _repo_profile = _json_rp.loads(_rp_path.read_text(encoding="utf-8"))
            except Exception as _rp_err:
                logger.warning("[W4] Failed to load repo_profile.json: %s", _rp_err)
        _quality_tier = _repo_profile.get("quality_tier", "standard") if _repo_profile else None
        tier_multiplier = 1.0  # default: no adjustment when no profile
        if _quality_tier:
            tier_multiplier = {"rich": 1.0, "standard": 0.85, "minimal": 0.7}.get(_quality_tier, 0.85)
            logger.info("[W4] repo_profile quality_tier=%s tier_multiplier=%.2f", _quality_tier, tier_multiplier)

        # TC-2447: Build EvidenceBasedPolicy when use_content_policy=true (default: false)
        # Zero behavior change when flag absent — pilots never set this flag.
        evidence_policy = None
        if _rc_for_policy.get("use_content_policy", False):
            try:
                from launch.content.policy.content_policy import EvidenceBasedPolicy as _EvidenceBasedPolicy
                import json as _json_ep
                # Load optional artifacts for richer evidence scoring
                _ep_topic_manifest: dict | None = None
                _ep_source_chunks: dict | None = None
                _tm_path = run_layout.artifacts_dir / "topic_manifest.json"
                if _tm_path.exists():
                    _ep_topic_manifest = _json_ep.loads(_tm_path.read_text(encoding="utf-8"))
                _sc_path = run_layout.artifacts_dir / "source_chunks.json"
                if _sc_path.exists():
                    _ep_source_chunks = _json_ep.loads(_sc_path.read_text(encoding="utf-8"))
                # Derive section caps from page_expansion config and section quotas
                _ep_section_caps: dict = {}
                _ep_mandatory_mins: dict = {}
                for _ep_sec, _ in sections_subdomains:
                    _ep_exp = _get_section_expansion(_page_expansion, _ep_sec)
                    _ep_section_caps[_ep_sec] = _ep_exp["max_pages"]
                    _ep_mandatory_mins[_ep_sec] = _ep_exp["min_pages"]
                evidence_policy = _EvidenceBasedPolicy.build(
                    sections=[s for s, _ in sections_subdomains],
                    product_facts=product_facts,
                    snippet_catalog=snippet_catalog,
                    topic_manifest=_ep_topic_manifest,
                    source_chunks=_ep_source_chunks,
                    repo_profile=_repo_profile if _repo_profile else None,
                    section_caps=_ep_section_caps,
                    mandatory_mins=_ep_mandatory_mins,
                )
                logger.info(
                    "[W4 EvidencePolicy] built for %d sections",
                    len([s for s, _ in sections_subdomains]),
                )
            except Exception as _ep_err:
                logger.warning("[W4] Failed to build EvidenceBasedPolicy: %s", _ep_err)
                evidence_policy = None

        # TC-2449: Build eligible_roles set from repo_profile signals
        # Gate: use_repo_profile=true (default: false) — pilots never set this
        _eligible_roles: set | None = None
        if _rc_for_policy.get("use_repo_profile", False) and _repo_profile:
            _eligible_roles = {
                "tutorial", "how-to", "howto_article", "faq", "blog_post",
                "overview", "comparison", "feature_showcase", "troubleshooting",
            }
            _ap_sigs = _repo_profile.get("api_signals", {})
            _ex_sigs_w4 = _repo_profile.get("examples_signals", {})
            # Unlock api_reference if meaningful API surface exists
            if _ap_sigs.get("api_surface_count", 0) >= 3 or _ap_sigs.get("has_api_docs_folder"):
                _eligible_roles.add("api_reference")
            # Unlock quickstart if examples folder exists
            if _ex_sigs_w4.get("has_examples_folder") or _ex_sigs_w4.get("example_file_count", 0) >= 2:
                _eligible_roles.add("quickstart")
            logger.info(
                "[W4] use_repo_profile: eligible_roles=%s",
                sorted(_eligible_roles),
            )

        # Phase 1: Load api_inventory for public_surface filtering in optional pages
        _api_inventory_w4: Optional[Dict[str, Any]] = None
        try:
            _inv_path = run_layout.artifacts_dir / "api_inventory.json"
            if _inv_path.exists():
                with _inv_path.open(encoding="utf-8") as _f:
                    _api_inventory_w4 = json.load(_f)
        except Exception:
            pass

        # TC-984: Evidence-driven optional page injection
        # Per specs/06_page_planning.md "Optional Page Selection Algorithm"
        # After the main template loop, inject optional pages to fill remaining quota
        for section, _subdomain in sections_subdomains:
            # TC-RCA: Enforce skip_sections in optional page injection (Loop 3)
            if section in skip_sections:
                continue
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
                platform=platform,
                content_policy=content_policy,
                tier_multiplier=tier_multiplier,
                evidence_policy=evidence_policy,   # TC-2447: None when use_content_policy=false
                eligible_roles=_eligible_roles,    # TC-2449: None when use_repo_profile=false
                api_inventory=_api_inventory_w4,   # Phase 1: public_surface filtering
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

        # TC-2394: Add discovered topics from topic_manifest.json as optional pages
        try:
            topic_manifest_path = run_layout.artifacts_dir / "topic_manifest.json"
            if topic_manifest_path.exists():
                import json as _json
                manifest = _json.loads(topic_manifest_path.read_text(encoding="utf-8"))
                discovered_topics = manifest.get("discovered_topics", [])
                # Track slugs across all sections (not just "docs") to avoid collisions
                _topic_existing_slugs = set(p["slug"] for p in all_pages)
                _topic_covered_ids = set(cid for p in all_pages for cid in p.get("required_claim_ids", []))
                _all_claims = product_facts.get("claims", [])
                # C1: Per-section topic budget — each section gets its own remaining capacity
                _valid_topic_sections = {"products", "docs", "kb", "blog", "reference"}
                _section_topic_budgets: dict = {}
                for _budget_sec in _valid_topic_sections:
                    _sec_quota = effective_quotas.get(
                        _budget_sec, section_quotas.get(_budget_sec, {"max_pages": 10})
                    ).get("max_pages", 10)
                    _sec_count = sum(1 for p in all_pages if p["section"] == _budget_sec)
                    _section_topic_budgets[_budget_sec] = max(0, _sec_quota - _sec_count)
                for topic in discovered_topics:
                    _topic_role = topic.get("suggested_page_role", "tutorial")
                    _topic_title = topic.get("title", "Discovered Topic")
                    _topic_slug = _derive_semantic_slug(_topic_title)
                    if _topic_slug in _topic_existing_slugs:
                        continue
                    # Use topic-declared section (from W2 section-scoped topic_discovery)
                    _topic_section = topic.get("section", "docs")
                    if _topic_section not in _valid_topic_sections:
                        _topic_section = "docs"  # safety: unknown section → docs
                    # C1: Check section-specific budget instead of global docs budget
                    if _section_topic_budgets.get(_topic_section, 0) <= 0:
                        continue
                    _topic_subdomain = get_subdomain_for_section(_topic_section)
                    # Respect page_expansion cap for this section
                    _sec_exp = _get_section_expansion(_page_expansion, _topic_section)
                    if not _sec_exp["enabled"]:
                        continue
                    _sec_count = sum(1 for _p in all_pages if _p.get("section") == _topic_section)
                    if _sec_count >= _sec_exp["max_pages"]:
                        logger.debug(
                            "w4_topic_skipped_over_cap section=%s cap=%d",
                            _topic_section, _sec_exp["max_pages"],
                        )
                        continue
                    # B5: Find claims for topic; skip page if no claims match
                    _topic_claim_ids = _find_claims_for_topic(
                        _topic_title, topic.get("rationale", ""),
                        _all_claims, _topic_covered_ids,
                    )
                    if not _topic_claim_ids:
                        logger.info("w4_skip_zero_claim_topic slug=%s title=%s", _topic_slug, _topic_title)
                        continue
                    _topic_strategy = build_content_strategy(_topic_role, _topic_section, product_facts.get("workflows", []))
                    _topic_page = {
                        "section": _topic_section,
                        "slug": _topic_slug,
                        "output_path": compute_output_path(
                            _topic_section, _topic_slug, product_slug, subdomain=_topic_subdomain, platform=platform
                        ),
                        "url_path": compute_url_path(
                            _topic_section, _topic_slug, product_slug, platform=platform
                        ),
                        "title": _topic_title,
                        "purpose": topic.get("rationale", ""),
                        "template_variant": launch_tier,
                        "required_headings": _default_headings_for_role(_topic_role, product_facts),
                        "required_claim_ids": _topic_claim_ids,
                        "required_snippet_tags": [],
                        "cross_links": [],
                        "seo_keywords": [product_slug, _topic_slug],
                        "forbidden_topics": _topic_strategy.get("forbidden_topics", []),
                        "page_role": _topic_role,
                        "content_strategy": _topic_strategy,
                        "source": "topic_discovery",
                        "claim_kind": "discovered_topic",
                    }
                    all_pages.append(_topic_page)
                    _topic_existing_slugs.add(_topic_slug)
                    _topic_covered_ids.update(_topic_claim_ids)
                    _section_topic_budgets[_topic_section] -= 1
                logger.info("w4_topic_manifest_loaded count=%d", len(discovered_topics))
        except Exception as _tm_err:
            logger.warning("w4_topic_manifest_load_failed error=%s", _tm_err)

        # C2: Pre-guard claim binding — bind claims to empty mandatory pages
        # so the zero-claim guard doesn't remove them.
        _all_claims_for_binding = product_facts.get("claims", [])
        _used_claim_ids = set(
            cid for p in all_pages for cid in p.get("required_claim_ids", [])
        )
        _nav_roles = {"toc", "landing", "index"}
        _bound_count = 0
        for _page in all_pages:
            if _page.get("required_claim_ids"):
                continue
            if _page.get("page_role", "") in _nav_roles:
                continue
            if _page.get("slug", "") in ("_index", "index"):
                continue
            _p_section = _page.get("section", "")
            _p_sec_exp = _get_section_expansion(_page_expansion, _p_section)
            _is_required = _p_section in _required_sections or _p_sec_exp["min_pages"] > 0
            if not _is_required:
                continue
            # Bind claims using keyword overlap with page title/purpose
            _bound_ids = _find_claims_for_topic(
                _page.get("title", ""), _page.get("purpose", ""),
                _all_claims_for_binding, _used_claim_ids, max_claims=3,
            )
            if _bound_ids:
                _page["required_claim_ids"] = _bound_ids
                _used_claim_ids.update(_bound_ids)
                _bound_count += 1
                logger.info(
                    "w4_claim_binding_rescued page=%s section=%s claims=%d",
                    _page.get("slug", "?"), _p_section, len(_bound_ids),
                )
        if _bound_count:
            logger.info("w4_claim_binding_total rescued=%d pages", _bound_count)

        # C3: Section-aware zero-claim guard (MOVED BEFORE min_pages enforcement)
        # Compute per-section min_pages for protection
        _section_min_pages: dict = {}
        for _sec, _sub in sections_subdomains:
            if _sec in skip_sections:
                continue
            _sec_exp = _get_section_expansion(_page_expansion, _sec)
            _min_p = _sec_exp["min_pages"]
            if _sec in _required_sections:
                _min_p = max(_min_p, 1)
            _section_min_pages[_sec] = _min_p

        _section_counts_pre: dict = {}
        for _p in all_pages:
            _s = _p.get("section", "")
            _section_counts_pre[_s] = _section_counts_pre.get(_s, 0) + 1

        _pre_guard_count = len(all_pages)
        _section_removals: dict = {}
        _guarded_pages = []
        for _p in all_pages:
            _has_claims = bool(_p.get("required_claim_ids"))
            _is_nav = _p.get("page_role", "") in _nav_roles
            _is_index = _p.get("slug", "") in ("_index", "index")
            if _has_claims or _is_nav or _is_index:
                _guarded_pages.append(_p)
            else:
                _sec = _p.get("section", "")
                _removals_so_far = _section_removals.get(_sec, 0)
                _remaining = _section_counts_pre.get(_sec, 0) - _removals_so_far
                _min_p = _section_min_pages.get(_sec, 0)
                if _remaining > _min_p:
                    _section_removals[_sec] = _removals_so_far + 1
                else:
                    _guarded_pages.append(_p)
                    logger.info(
                        "w4_guard_protected slug=%s section=%s (would drop below min=%d)",
                        _p.get("slug", "?"), _sec, _min_p,
                    )
        all_pages = _guarded_pages
        _removed = _pre_guard_count - len(all_pages)
        if _removed:
            logger.info("w4_zero_claim_guard removed=%d pages", _removed)

        # Post-planning: enforce mandatory minimums per section (Stage 2 hardening)
        # Now runs AFTER guard, so fallback pages are the final state.
        for _sec, _sub in sections_subdomains:
            if _sec in skip_sections:
                continue
            _sec_exp = _get_section_expansion(_page_expansion, _sec)
            _min_p = _sec_exp["min_pages"]
            if _sec in _required_sections:
                _min_p = max(_min_p, 1)
            if _min_p == 0:
                continue

            _section_pages = [p for p in all_pages if p.get("section") == _sec]
            _actual = len(_section_pages)
            if _actual < _min_p:
                logger.warning(
                    "w4_mandatory_min_not_met section=%s required=%d actual=%d triggering_fallback",
                    _sec, _min_p, _actual,
                )
                try:
                    _fallback_pages = plan_pages_for_section(
                        _sec, launch_tier, product_facts, snippet_catalog, product_slug, platform
                    )
                    _existing_slugs = {p.get("slug") for p in _section_pages}
                    _added = 0
                    for _fp in _fallback_pages:
                        if _fp.get("slug") not in _existing_slugs:
                            all_pages.append(_fp)
                            _existing_slugs.add(_fp.get("slug"))
                            _added += 1

                    _final_count = sum(1 for p in all_pages if p.get("section") == _sec)
                    if _final_count < _min_p:
                        raise RuntimeError(
                            f"[W4] Cannot meet mandatory minimum for section '{_sec}': "
                            f"required={_min_p}, produced={_final_count} (including fallback). "
                            f"Check W2 output (topic_manifest.json) and pilot config."
                        )
                    logger.info(
                        "w4_mandatory_fallback_applied section=%s added=%d total=%d",
                        _sec, _added, _final_count,
                    )
                except RuntimeError:
                    raise
                except Exception as _fb_err:
                    logger.warning(
                        "w4_mandatory_fallback_error section=%s error=%s",
                        _sec, _fb_err,
                    )

        # C4: Mandatory section guarantee — fail-fast if any required section is empty
        _guarantee_violations = []
        for _sec in _required_sections:
            _sec_pages = [p for p in all_pages if p.get("section") == _sec]
            _sec_exp = _get_section_expansion(_page_expansion, _sec)
            _min_p = max(_sec_exp["min_pages"], 1)
            if len(_sec_pages) < _min_p:
                _guarantee_violations.append(
                    f"Section '{_sec}': {len(_sec_pages)} pages, required >= {_min_p}"
                )
                continue
            # Check that at least one content page has claims
            _content_pages = [
                p for p in _sec_pages
                if p.get("page_role", "") not in _nav_roles
                and p.get("slug", "") not in ("_index", "index")
            ]
            _pages_with_claims = [p for p in _content_pages if p.get("required_claim_ids")]
            if _content_pages and not _pages_with_claims:
                _guarantee_violations.append(
                    f"Section '{_sec}': {len(_content_pages)} content pages but none have claims"
                )
        if _guarantee_violations:
            _msg = (
                "[W4] Mandatory section guarantee violated:\n"
                + "\n".join(f"  - {v}" for v in _guarantee_violations)
                + "\nCheck W2 output quality and run_config.required_sections."
            )
            logger.error(_msg)
            raise RuntimeError(_msg)

        # TC-1813: Slug deduplication — ensure no two pages in the same section
        # share the same slug. Append numeric suffixes when collisions occur.
        used_slugs: dict[str, set[str]] = {}  # section -> set of slugs
        deduped_pages = []
        for page in all_pages:
            section = page["section"]
            slug = page["slug"]
            if section not in used_slugs:
                used_slugs[section] = set()
            if slug in used_slugs[section]:
                # Find unique suffix
                counter = 2
                while f"{slug}-{counter}" in used_slugs[section]:
                    counter += 1
                new_slug = f"{slug}-{counter}"
                logger.debug(
                    f"[W4] Dedup slug collision: '{slug}' -> '{new_slug}' "
                    f"in section '{section}'"
                )
                slug = new_slug
                page["slug"] = slug
                # Update output_path and url_path with new slug
                page["output_path"] = compute_output_path(section, slug, product_slug, platform=platform)
                page["url_path"] = compute_url_path(section, slug, product_slug, platform=platform)
            used_slugs[section].add(slug)
            deduped_pages.append(page)
        all_pages = deduped_pages

        # TC-2386: Pre-generation redundancy check (D-4, non-blocking)
        redundancy_warnings = check_pre_generation_redundancy(all_pages)
        if redundancy_warnings:
            logger.warning(
                "pre_gen_redundancy_detected",
                count=len(redundancy_warnings),
                pairs=[(w["page_a"], w["page_b"]) for w in redundancy_warnings[:5]],
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
        add_cross_links(all_pages, product_slug=product_slug, platform=platform)

        # Agent 42: Populate cross_section_links on products _index page
        _populate_products_cross_section_links(
            all_pages, product_slug=product_slug, locale=locale, platform=platform,
        )

        # TC-1742: Add claim-overlap-based related_pages for See Also injection
        add_claim_overlap_cross_links(all_pages)

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

        # TC-P1C: Backfill child_pages on TOC pages so W5 generate_toc_content()
        # can list all children. Must happen after all pages are created.
        for page in all_pages:
            if page.get("page_role") == "toc":
                child_slugs = sorted([
                    p["slug"] for p in all_pages
                    if p["slug"] != page["slug"]
                    and p["section"] == page["section"]
                ])
                page.setdefault("content_strategy", {})["child_pages"] = child_slugs
                logger.info(
                    f"[W4 IAPlanner] Populated child_pages for TOC page "
                    f"'{page['slug']}': {child_slugs}"
                )

        # TC-P2C: Cross-page claim deduplication — each claim on ONE primary page.
        # Priority: products > docs > kb > reference (blog exempt).
        used_claim_ids: set = set()
        section_priority = ["products", "docs", "kb", "reference"]
        for target_section in section_priority:
            for page in sorted(all_pages, key=lambda p: p.get("slug", "")):
                if page.get("section") != target_section:
                    continue
                original = page.get("required_claim_ids", [])
                if not original:
                    continue
                deduped = [c for c in original if c not in used_claim_ids]
                # Respect claim_quota.min — if dedup drops below minimum, skip dedup for this page
                claim_quota = page.get("content_strategy", {}).get("claim_quota", {})
                min_claims = claim_quota.get("min", 0)
                if len(deduped) >= min_claims:
                    page["required_claim_ids"] = deduped
                    used_claim_ids.update(deduped)
                    if len(deduped) < len(original):
                        logger.info(
                            f"[W4 IAPlanner] Deduped claims for '{page['slug']}': "
                            f"{len(original)} -> {len(deduped)}"
                        )
                else:
                    # Keep original to meet minimum quota
                    used_claim_ids.update(original)
                    logger.info(
                        f"[W4 IAPlanner] Skipped dedup for '{page['slug']}' "
                        f"(would drop below min={min_claims})"
                    )

        # Phase 1B: Populate absolute_url for every page
        # Requirement: "all internal URLs posted by linker must be absolute"
        for page in all_pages:
            section = page.get("section", "docs")
            slug = page.get("slug", "")
            page["absolute_url"] = compute_absolute_url(
                section=section, slug=slug, product_slug=product_slug,
                platform=platform,
            )

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

        # TC-1763: Apply page preservation for incremental updates
        page_plan = _apply_page_preservation(page_plan, run_config_obj, run_layout)

        # B6: Sanitize content_strategy dicts before writing
        for page in page_plan.get("pages", []):
            _sanitize_page_spec_fields(page)

        # TC-2529/TC-2530: Apply feedback-based claim count adjustments
        if _use_feedback_w4 and _w4_feedback:
            _w4_params_before: Dict[str, Any] = {}
            _w4_params_after: Dict[str, Any] = {}
            _w4_adjusted_count = 0
            for _pg in page_plan.get("pages", []):
                _pg_slug = _pg.get("slug", "")
                _cq = _pg.get("claim_quota")
                if isinstance(_cq, dict) and "max" in _cq:
                    _old_max = _cq["max"]
                    _new_max = adjust_top_k_from_feedback(
                        _pg_slug, _old_max, _w4_feedback,
                    )
                    if _new_max != _old_max:
                        _w4_params_before[f"claim_quota_max:{_pg_slug}"] = _old_max
                        _w4_params_after[f"claim_quota_max:{_pg_slug}"] = _new_max
                        _cq["max"] = _new_max
                        _w4_adjusted_count += 1
            if _w4_adjusted_count > 0:
                logger.info(
                    "w4_feedback_claim_counts_adjusted pages_adjusted=%d",
                    _w4_adjusted_count,
                )
                # TC-2530: Emit feedback delta artifact for W4
                _emit_w4_feedback_delta(
                    run_dir=run_dir,
                    feedback=_w4_feedback,
                    parameters_before=_w4_params_before,
                    parameters_after=_w4_params_after,
                )
            else:
                logger.info("w4_feedback_no_claim_adjustments")

        # Validate page plan
        validate_page_plan(page_plan)

        # TC-2515: Detect slug collisions (warn only, don't fail)
        slug_collisions = _detect_slug_collisions(page_plan)
        if slug_collisions:
            for collision in slug_collisions:
                logger.warning(
                    "slug_collision_detected section=%s slug=%s pages=%s",
                    collision["section"], collision["slug"],
                    collision["pages"],
                )
            logger.warning(
                "slug_collision_summary total=%d collisions detected in page plan",
                len(slug_collisions),
            )

        # Write artifact
        artifact_path = run_layout.artifacts_dir / "page_plan.json"
        atomic_write_json(artifact_path, page_plan)

        logger.info(f"[W4 IAPlanner] Wrote page plan: {artifact_path} ({len(all_pages)} pages)")

        # TC-2435: Write content_policy.json artifact if policy was active
        if content_policy is not None:
            _policy_artifact_path = run_layout.artifacts_dir / "content_policy.json"
            atomic_write_json(_policy_artifact_path, content_policy.to_artifact())
            logger.info("[W4 IAPlanner] Wrote content_policy artifact: %s", _policy_artifact_path)

        # TC-2447: Write evidence_content_policy.json artifact if evidence policy was active
        if evidence_policy is not None:
            _ep_artifact_path = run_layout.artifacts_dir / "evidence_content_policy.json"
            atomic_write_json(_ep_artifact_path, evidence_policy.to_artifact())
            logger.info("[W4 IAPlanner] Wrote evidence_content_policy artifact: %s", _ep_artifact_path)

        # TC-2478: Write shared facts artifact for cross-page consistency
        # Load repo_truth.json for deterministic override when available
        _repo_truth: Optional[Dict[str, Any]] = None
        _rt_path = run_layout.artifacts_dir / "repo_truth.json"
        if _rt_path.exists():
            try:
                with _rt_path.open(encoding="utf-8") as _rtf:
                    _repo_truth = json.load(_rtf)
            except Exception:
                pass
        shared_facts = _extract_shared_facts(product_facts, repo_truth=_repo_truth)
        _shared_facts_path = run_layout.artifacts_dir / "shared_facts.json"
        atomic_write_json(_shared_facts_path, shared_facts)
        logger.info("shared_facts_written keys=%s", list(shared_facts.keys()))

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


# TC-2377: Quality Feedback Loop — W4 consumer helpers

def read_quality_feedback(run_dir: Path) -> Dict[str, Any]:
    """Read quality feedback from previous run, if available.

    Returns empty dict if no feedback file found (backwards compat).
    """
    feedback_path = run_dir / "work" / "quality_feedback.json"
    if not feedback_path.exists():
        return {}
    try:
        return json.loads(feedback_path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("quality_feedback_read_failed path=%s error=%s", str(feedback_path), str(e))
        return {}


def adjust_top_k_from_feedback(
    page_slug: str,
    default_top_k: int,
    feedback: Dict[str, Any],
) -> int:
    """Adjust top_k claim count based on previous run feedback.

    Increases top_k by 3 (max 20) if page had 'increase_claim_count' suggestion.
    Feature-flagged: only called when use_feedback=True.
    """
    for page in feedback.get("pages", []):
        path = page.get("output_path", "")
        if page_slug in path and "increase_claim_count" in page.get("suggested_actions", []):
            adjusted = min(default_top_k + 3, 20)
            logger.info(
                "top_k_adjusted_from_feedback slug=%s from_top_k=%d to_top_k=%d",
                page_slug,
                default_top_k,
                adjusted,
            )
            return adjusted
    return default_top_k


def _emit_w4_feedback_delta(
    run_dir: Path,
    feedback: Dict[str, Any],
    parameters_before: Dict[str, Any],
    parameters_after: Dict[str, Any],
) -> None:
    """TC-2530: Emit feedback_delta.json entry for W4 claim count adjustments.

    Appends to existing feedback_delta.json (W2 may have written first).
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
        "worker": "W4",
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
            "feedback_delta_written worker=W4 changes=%d path=%s",
            len(changes), str(delta_path),
        )
    except Exception as _delta_err:
        logger.warning("feedback_delta_write_failed worker=W4 error=%s", _delta_err)
