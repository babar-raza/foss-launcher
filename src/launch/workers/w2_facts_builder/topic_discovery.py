"""Topic discovery from FOSS repo documentation.

Reference: content-generator src/agents/research/topic_identification.py
TC-2900: Thin-output detection + API inventory enrichment.
"""
from __future__ import annotations
import json
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_VALID_SECTIONS = {"kb", "docs", "blog", "products", "reference"}

# TC-2900: Per-section minimum topic thresholds.
# Sections below these counts trigger enriched fallback.
_MIN_TOPICS_PER_SECTION: Dict[str, int] = {
    "products": 1,
    "blog": 1,
    "kb": 2,
    "docs": 2,
    "reference": 1,
}

_SECTION_TOPIC_PROMPT = """\
You are a content strategist designing documentation for a software library.

Product: {product_name}
Description: {product_description}

Key claims and capabilities (primary source):
{claims_sample}

Identify exactly {max_topics} actionable article topics distributed across these sections:
  "kb":       How-to guides — things a developer actively DOES with this library
  "docs":     Technical guides, API usage patterns, format conversion walkthroughs
  "blog":     Educational posts, use-case spotlights, trend-driven angles
  "products": Value propositions, feature overviews, capability summaries

Rules:
- At least 2 topics per section (kb, docs, blog, products)
- Topics must be grounded in the claims above — no generic programming topics
- slug_seed must be kebab-case, 2-4 words maximum
- Exclude internal developer topics: contributing guidelines, CI/CD, governance, code style

Output a JSON array only (no markdown, no prose):
[
  {{
    "section": "kb",
    "title": "How to Convert OBJ Files to STL",
    "intent": "Developer needs to convert between 3D mesh formats",
    "source_evidence": ["Scene.Save", "format support for OBJ/STL"],
    "keywords": ["obj", "stl", "convert", "export"],
    "slug_seed": "convert-obj-to-stl",
    "rationale": "Primary use case for 3D processing libraries",
    "target_audience": "Python developer",
    "suggested_page_role": "howto_article"
  }}
]
"""


def discover_topics_from_docs(
    doc_chunks: List[dict],
    existing_claim_groups: dict,
    llm_client,
    *,
    claims: List[dict] = None,
    product_name: str = "",
    product_description: str = "",
    mandatory_sections: List[str] = None,
    max_topics: int = 12,
    api_inventory: Optional[Dict[str, Any]] = None,
    supported_formats: Optional[List[dict]] = None,
    workflows: Optional[List[dict]] = None,
) -> List[dict]:
    """Identify article topics distributed across all content sections.

    Returns list of topic dicts with: section, title, intent, source_evidence,
    keywords, slug_seed, rationale, target_audience, suggested_page_role.

    Args:
        doc_chunks: Documentation chunks from W1 ingestion.
        existing_claim_groups: claim_groups dict from W2 (used for dedup comparison).
        llm_client: LLM client for topic generation.
        claims: Full claims list (primary signal, preferred over doc_chunks).
        product_name: Product name for prompt context.
        product_description: Product description for prompt context.
        mandatory_sections: Sections that must have ≥1 topic (fallback fires if missing).
        max_topics: Maximum topics to return.
        api_inventory: Optional api_inventory.json dict for enriched fallback.
        supported_formats: Optional list of format dicts for enriched fallback.
        workflows: Optional list of workflow dicts for enriched fallback.

    Uses TF-IDF cosine sim dedup gate (threshold 0.5 against title-like strings only).
    """
    if not doc_chunks and not claims:
        return []

    # Use claims as primary signal (60 claims >> 10 doc chunks)
    claims = claims or []
    if claims:
        claims_sample = "\n".join(
            f"- {c.get('claim_text', '')[:120]}"
            for c in claims[:60]
        )
    else:
        claims_sample = "\n\n".join(
            c.get("text", "")[:300] for c in doc_chunks[:6]
        )[:3000]

    prompt = _SECTION_TOPIC_PROMPT.format(
        product_name=product_name or "Unknown",
        product_description=(product_description or "")[:400],
        claims_sample=claims_sample,
        max_topics=max_topics,
    )

    try:
        response = llm_client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            call_id="topic_discovery",
            temperature=0.3,
            max_tokens=2000,
        )
        raw = response.get("content", "")
        topics = _parse_topics_json(raw)
    except Exception as e:
        logger.warning("topic_discovery_llm_fail error=%s", e)
        topics = []

    # Fix missing/invalid section fields
    for t in topics:
        if t.get("section") not in _VALID_SECTIONS:
            t["section"] = "docs"  # safe default

    # Dedup: only compare against title-like strings (> 2 words); threshold 0.5
    title_like = [k for k in existing_claim_groups.keys() if len(k.split()) > 2]
    approved = _dedup_topics(topics, title_like, threshold=0.5)

    # TC-2900: Enforce mandatory sections with thin-output detection.
    # Fire enriched fallback when section count < _MIN_TOPICS_PER_SECTION, not just 0.
    mandatory_sections = mandatory_sections or ["products", "blog", "kb"]
    fallback_topics: list = []
    for sec in mandatory_sections:
        sec_count = sum(1 for t in approved if t.get("section") == sec)
        min_needed = _MIN_TOPICS_PER_SECTION.get(sec, 1)
        deficit = min_needed - sec_count
        if deficit > 0:
            logger.warning(
                "topic_discovery_thin_output section=%s count=%d min=%d product=%s",
                sec, sec_count, min_needed, product_name,
            )
            fallback_topics += _enriched_fallback_topics(
                sec, deficit, claims, product_name,
                api_inventory=api_inventory,
                supported_formats=supported_formats,
                workflows=workflows,
            )

    # B1 fix: reserve slots for mandatory fallbacks BEFORE truncation so they
    # are never sliced away when the LLM fills all max_topics slots.
    reserved = len(fallback_topics)
    approved = approved[: max(0, max_topics - reserved)]
    approved += fallback_topics

    return approved[:max_topics]


def _fallback_topics_for_section(
    section: str, claims: List[dict], product_name: str
) -> List[dict]:
    """Derive minimum topics from claim data when LLM fails. Always returns ≥1 topic."""
    if section == "products":
        return [{
            "section": "products",
            "title": f"{product_name} Overview",
            "intent": "Product landing and capability summary",
            "keywords": [product_name.lower().split()[0]] if product_name else [],
            "slug_seed": "overview",
            "rationale": "Required product landing page",
            "suggested_page_role": "feature_showcase",
            "source_evidence": [],
        }]
    if section == "blog":
        slug = f"introducing-{product_name.lower().replace(' ', '-')}" if product_name else "introducing"
        return [{
            "section": "blog",
            "title": f"Introducing {product_name}" if product_name else "Product Announcement",
            "intent": "Product announcement and highlights",
            "keywords": [product_name.lower().split()[0], "python", "foss"] if product_name else ["python", "foss"],
            "slug_seed": slug[:40],
            "rationale": "Mandatory product announcement blog post",
            "suggested_page_role": "blog_post",
            "source_evidence": [],
        }]
    if section == "reference":
        return [{
            "section": "reference",
            "title": f"{product_name} API Reference",
            "intent": "API class and method reference documentation",
            "keywords": ["api", "reference", "class", "method"],
            "slug_seed": "api-reference",
            "rationale": "Required reference documentation",
            "suggested_page_role": "api_reference",
            "source_evidence": [],
        }]
    # kb / docs: derive from top 3 claims
    fallbacks = []
    for c in claims[:3]:
        text = c.get("claim_text", "feature")[:60]
        slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40]
        fallbacks.append({
            "section": section,
            "title": text,
            "intent": text,
            "keywords": slug.split("-")[:4],
            "slug_seed": slug,
            "suggested_page_role": "howto_article",
            "source_evidence": [],
        })
    if not fallbacks:
        fallbacks = [{
            "section": section,
            "title": f"{section.title()} Guide",
            "intent": "General guide",
            "keywords": [],
            "slug_seed": "guide",
            "suggested_page_role": "howto_article",
            "source_evidence": [],
        }]
    return fallbacks


# ---------------------------------------------------------------------------
# TC-2900: Enriched fallback generators using api_inventory, formats, workflows
# ---------------------------------------------------------------------------


def _enriched_fallback_topics(
    section: str,
    count: int,
    claims: List[dict],
    product_name: str,
    *,
    api_inventory: Optional[Dict[str, Any]] = None,
    supported_formats: Optional[List[dict]] = None,
    workflows: Optional[List[dict]] = None,
) -> List[dict]:
    """Derive enriched fallback topics using all available deterministic signals.

    Fires when a section is THIN (below _MIN_TOPICS_PER_SECTION).
    Uses api_inventory, supported_formats, and workflows as additional signals
    beyond raw claim text.  Falls back to _fallback_topics_for_section() when
    enriched signals are unavailable.
    """
    topics: List[dict] = []

    if section == "reference":
        topics = _reference_topics_from_inventory(api_inventory, product_name, count)
    elif section == "kb":
        topics = _kb_topics_from_signals(
            claims, product_name, count,
            workflows=workflows,
            supported_formats=supported_formats,
        )
    elif section == "docs":
        topics = _docs_topics_from_inventory(
            claims, product_name, count,
            api_inventory=api_inventory,
        )
    elif section == "blog":
        topics = _blog_topics_from_formats(
            claims, product_name, count,
            supported_formats=supported_formats,
        )
    elif section == "products":
        topics = _fallback_topics_for_section("products", claims, product_name)[:count]

    # If enriched signals didn't produce enough, fall back to claim-based
    if len(topics) < count:
        old_fallbacks = _fallback_topics_for_section(section, claims, product_name)
        existing_slugs = {t.get("slug_seed") for t in topics}
        for fb in old_fallbacks:
            if fb.get("slug_seed") not in existing_slugs and len(topics) < count:
                topics.append(fb)
                existing_slugs.add(fb.get("slug_seed"))

    return topics[:count]


def _reference_topics_from_inventory(
    api_inventory: Optional[Dict[str, Any]],
    product_name: str,
    count: int,
) -> List[dict]:
    """Generate reference topics from api_inventory classes grouped by module."""
    if not api_inventory:
        return []

    classes = api_inventory.get("classes", [])
    if not classes:
        return []

    # Group by top-level module (first 2 segments of import_path)
    module_groups: Dict[str, List[str]] = {}
    for cls in classes:
        import_path = cls.get("import_path", "")
        parts = import_path.split(".")
        module_key = ".".join(parts[:2]) if len(parts) >= 2 else import_path
        if module_key:
            module_groups.setdefault(module_key, []).append(cls.get("name", ""))

    topics: List[dict] = []
    # Stable sort: descending class count, then alphabetical module name
    for module_key in sorted(module_groups, key=lambda k: (-len(module_groups[k]), k)):
        class_names = module_groups[module_key]
        slug = re.sub(r"[^a-z0-9]+", "-", module_key.lower()).strip("-")[:34]
        topics.append({
            "section": "reference",
            "title": f"{product_name} {module_key} API Reference",
            "intent": f"API reference for {len(class_names)} classes in {module_key}",
            "keywords": ["api", "reference"] + sorted(c.lower() for c in class_names[:3]),
            "slug_seed": f"ref-{slug}"[:40],
            "rationale": f"Derived from {len(class_names)} classes in api_inventory",
            "suggested_page_role": "api_reference",
            "source_evidence": [],
            "target_audience": "Python developer",
        })
        if len(topics) >= count:
            break
    return topics


def _kb_topics_from_signals(
    claims: List[dict],
    product_name: str,
    count: int,
    *,
    workflows: Optional[List[dict]] = None,
    supported_formats: Optional[List[dict]] = None,
) -> List[dict]:
    """Generate kb how-to topics from workflows and format conversion pairs."""
    topics: List[dict] = []
    slugs_used: set = set()

    # Signal 1: Each workflow -> one kb how-to topic
    for wf in (workflows or []):
        if len(topics) >= count:
            break
        tag = wf.get("workflow_tag", "")
        title = wf.get("title", tag)
        if not tag:
            continue
        slug = re.sub(r"[^a-z0-9]+", "-", tag.lower()).strip("-")[:40]
        if slug in slugs_used:
            continue
        slugs_used.add(slug)
        topics.append({
            "section": "kb",
            "title": f"How to {title} with {product_name}",
            "intent": f"Step-by-step guide for {title}",
            "keywords": sorted(set(slug.split("-")[:4] + ["howto"])),
            "slug_seed": slug,
            "rationale": f"Derived from workflow '{tag}'",
            "suggested_page_role": "howto_article",
            "source_evidence": sorted(wf.get("claim_ids", [])[:3]),
            "target_audience": "Python developer",
        })

    # Signal 2: Format conversion pairs from implemented formats
    impl_formats = sorted(
        [f for f in (supported_formats or []) if isinstance(f, dict)],
        key=lambda f: f.get("format", ""),
    )
    if len(impl_formats) >= 2:
        for i, fmt_a in enumerate(impl_formats):
            if len(topics) >= count:
                break
            for fmt_b in impl_formats[i + 1:]:
                if len(topics) >= count:
                    break
                a_name = fmt_a.get("format", "")
                b_name = fmt_b.get("format", "")
                if not a_name or not b_name:
                    continue
                slug = f"convert-{a_name.lower()}-to-{b_name.lower()}"[:40]
                if slug in slugs_used:
                    continue
                slugs_used.add(slug)
                topics.append({
                    "section": "kb",
                    "title": f"How to Convert {a_name} to {b_name} with {product_name}",
                    "intent": f"Convert {a_name} files to {b_name} format",
                    "keywords": sorted([a_name.lower(), b_name.lower(), "convert"]),
                    "slug_seed": slug,
                    "rationale": f"Derived from supported_formats: {a_name} + {b_name}",
                    "suggested_page_role": "howto_article",
                    "source_evidence": [],
                    "target_audience": "Python developer",
                })

    return topics[:count]


def _docs_topics_from_inventory(
    claims: List[dict],
    product_name: str,
    count: int,
    *,
    api_inventory: Optional[Dict[str, Any]] = None,
) -> List[dict]:
    """Generate docs tutorial topics from api_inventory top classes by method count."""
    topics: List[dict] = []
    if not api_inventory:
        return topics

    classes = api_inventory.get("classes", [])
    if not classes:
        return topics

    # Sort by method count descending, then name ascending for determinism
    ranked = sorted(
        classes,
        key=lambda c: (-len(c.get("methods", [])), c.get("name", "")),
    )
    for cls in ranked[:count]:
        name = cls.get("name", "")
        if not name:
            continue
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:34]
        topics.append({
            "section": "docs",
            "title": f"Working with {name} in {product_name}",
            "intent": f"Tutorial: using the {name} class",
            "keywords": sorted([name.lower(), "tutorial", "api"]),
            "slug_seed": f"guide-{slug}"[:40],
            "rationale": f"Derived from api_inventory: {name} ({len(cls.get('methods', []))} methods)",
            "suggested_page_role": "tutorial",
            "source_evidence": [],
            "target_audience": "Python developer",
        })
    return topics[:count]


def _blog_topics_from_formats(
    claims: List[dict],
    product_name: str,
    count: int,
    *,
    supported_formats: Optional[List[dict]] = None,
) -> List[dict]:
    """Generate blog spotlight posts from supported formats."""
    topics: List[dict] = []
    formats = sorted(
        [f for f in (supported_formats or []) if isinstance(f, dict)],
        key=lambda f: f.get("format", ""),
    )
    for fmt in formats[:count]:
        fname = fmt.get("format", "")
        if not fname:
            continue
        slug = f"working-with-{fname.lower()}"[:40]
        topics.append({
            "section": "blog",
            "title": f"Working with {fname} Files Using {product_name}",
            "intent": f"Educational post about {fname} format support",
            "keywords": sorted([fname.lower(), "python", "foss"]),
            "slug_seed": slug,
            "rationale": f"Derived from supported_formats: {fname}",
            "suggested_page_role": "blog_post",
            "source_evidence": [],
            "target_audience": "Python developer",
        })
    return topics[:count]


def _dedup_topics(
    topics: List[dict], existing_titles: List[str], threshold: float
) -> List[dict]:
    """Remove topics too similar to existing_titles (cosine sim > threshold).

    Only compares against title-like strings (> 2 words) to avoid false positives
    from short claim_group keys like 'key_features'.
    """
    if not existing_titles:
        return topics
    try:
        from .embeddings import compute_tfidf_similarity as tfidf_cosine_similarity
        approved = []
        for topic in topics:
            title = topic.get("title", "")
            sims = [tfidf_cosine_similarity(title, et) for et in existing_titles]
            max_sim = max(sims) if sims else 0.0
            if max_sim < threshold:
                approved.append(topic)
            else:
                similar_to = existing_titles[sims.index(max_sim)]
                logger.info(
                    "TOPIC_DEDUP skip=%s similar_to=%s sim=%.2f",
                    title, similar_to, max_sim,
                )
        return approved
    except Exception as e:
        logger.warning("topic_dedup_fail error=%s — returning all topics", e)
        return topics


def _parse_topics_json(raw: str) -> List[dict]:
    """Parse JSON array from LLM response."""
    raw = raw.strip()
    # Strip JSON fence if present
    m = re.search(r"```json\s*\n(.*?)\n```", raw, re.DOTALL)
    if m:
        raw = m.group(1)
    elif raw.startswith("```"):
        m = re.search(r"```\s*\n(.*?)\n```", raw, re.DOTALL)
        if m:
            raw = m.group(1)
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return [t for t in data if isinstance(t, dict) and "title" in t]
        if isinstance(data, dict) and "topics" in data:
            return data["topics"]
    except (json.JSONDecodeError, ValueError):
        pass
    return []


# ---------------------------------------------------------------------------
# B2: Claim-kind → section mapping for deterministic fallback
# ---------------------------------------------------------------------------
_CLAIM_KIND_TO_SECTION: Dict[str, str] = {
    "key_feature": "products",
    "feature": "products",
    "api_reference": "docs",
    "format": "docs",
    "workflow": "kb",
    "tutorial": "kb",
    "use_case": "kb",
    "limitation": "docs",
    "troubleshooting": "kb",
    "faq": "kb",
    "best_practice": "blog",
    "performance": "blog",
    "metadata": "docs",
}

_SECTION_DEFAULT_ROLE: Dict[str, str] = {
    "products": "feature_showcase",
    "docs": "tutorial",
    "kb": "howto_article",
    "blog": "blog_post",
    "reference": "api_reference",
}


def derive_deterministic_topics(
    claims: List[dict],
    *,
    product_name: str = "",
    mandatory_sections: Optional[List[str]] = None,
    max_topics: int = 12,
    api_inventory: Optional[Dict[str, Any]] = None,
    supported_formats: Optional[List[dict]] = None,
    workflows: Optional[List[dict]] = None,
) -> List[dict]:
    """Derive topics deterministically from claim data (no LLM required).

    Used when llm_client is None (offline mode).  Groups claims by kind,
    maps kinds to sections, and produces one topic per group.

    TC-2900: Uses api_inventory, supported_formats, workflows for enriched
    fallback when sections are below _MIN_TOPICS_PER_SECTION thresholds.
    """
    mandatory_sections = mandatory_sections or ["products", "blog", "kb"]

    # Group claims by section
    section_claims: Dict[str, List[dict]] = {}
    for c in claims:
        kind = c.get("claim_kind", "key_feature")
        section = _CLAIM_KIND_TO_SECTION.get(kind, "docs")
        section_claims.setdefault(section, []).append(c)

    topics: List[dict] = []
    for section in sorted(section_claims):
        sec_claims = section_claims[section]
        rep = sec_claims[0]
        text = rep.get("claim_text", "Feature")[:80]
        slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40]
        role = _SECTION_DEFAULT_ROLE.get(section, "tutorial")
        topics.append({
            "section": section,
            "title": f"{product_name} - {text}" if product_name else text,
            "intent": text,
            "source_evidence": [rep.get("claim_id", "")],
            "keywords": slug.split("-")[:4],
            "slug_seed": slug,
            "rationale": f"Derived from {len(sec_claims)} {section} claims",
            "target_audience": "Python developer",
            "suggested_page_role": role,
        })

    # TC-2900: Enforce mandatory section coverage with thin-output detection
    fallback_topics: list = []
    for sec in mandatory_sections:
        sec_count = sum(1 for t in topics if t.get("section") == sec)
        min_needed = _MIN_TOPICS_PER_SECTION.get(sec, 1)
        deficit = min_needed - sec_count
        if deficit > 0:
            fallback_topics += _enriched_fallback_topics(
                sec, deficit, claims, product_name,
                api_inventory=api_inventory,
                supported_formats=supported_formats,
                workflows=workflows,
            )

    reserved = len(fallback_topics)
    topics = topics[: max(0, max_topics - reserved)]
    topics += fallback_topics

    return topics[:max_topics]


# ---------------------------------------------------------------------------
# TC-2900: Output segregation + manifest builder
# ---------------------------------------------------------------------------


def detect_thin_sections(
    topics: List[dict],
    mandatory_sections: List[str],
) -> List[str]:
    """Return section names where topic count < _MIN_TOPICS_PER_SECTION."""
    thin: List[str] = []
    for sec in mandatory_sections:
        sec_count = sum(1 for t in topics if t.get("section") == sec)
        if sec_count < _MIN_TOPICS_PER_SECTION.get(sec, 1):
            thin.append(sec)
    return sorted(thin)


def build_topic_manifest(
    topics: List[dict],
    *,
    method: str,
    dedup_threshold: float = 0.5,
    source_doc_count: int = 0,
    claims_used: int = 0,
    thin_sections: Optional[List[str]] = None,
) -> dict:
    """Build topic_manifest.json with section-keyed segregation.

    Returns a dict with:
    - discovered_topics: flat list (backward compat for W4)
    - topics_by_section: {section: [topics...]} (new, for debugging/analytics)
    - thin_sections: sections that were below minimum threshold
    - schema_version: "1.1.0"
    """
    per_section: Dict[str, int] = {}
    by_section: Dict[str, List[dict]] = {}
    for t in topics:
        sec = t.get("section", "docs")
        per_section[sec] = per_section.get(sec, 0) + 1
        by_section.setdefault(sec, []).append(t)

    warnings = validate_topic_coverage(
        topics, ["products", "blog", "kb"]
    )

    return {
        "schema_version": "1.1.0",
        "discovered_topics": topics,
        "topics_by_section": dict(sorted(by_section.items())),
        "method": method,
        "per_section_counts": dict(sorted(per_section.items())),
        "warnings": warnings,
        "thin_sections": sorted(thin_sections or []),
        "dedup_threshold": dedup_threshold,
        "source_doc_count": source_doc_count,
        "claims_used": claims_used,
    }


def validate_topic_coverage(
    topics: List[dict],
    required_sections: List[str],
) -> List[str]:
    """Check that all required_sections have >= 1 topic.  Returns warning strings."""
    warnings: List[str] = []
    for sec in required_sections:
        count = sum(1 for t in topics if t.get("section") == sec)
        if count == 0:
            warnings.append(
                f"COVERAGE_GAP: section '{sec}' has 0 topics after discovery"
            )
    return warnings
