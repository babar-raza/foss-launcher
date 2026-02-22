"""Topic discovery from FOSS repo documentation.

Reference: content-generator src/agents/research/topic_identification.py
"""
from __future__ import annotations
import json
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_VALID_SECTIONS = {"kb", "docs", "blog", "products", "reference"}

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

    # Enforce mandatory sections: fire fallback when LLM returns 0 for a required section
    mandatory_sections = mandatory_sections or ["products", "blog", "kb"]
    sections_present = {t.get("section") for t in approved}
    fallback_topics: list = []
    for sec in mandatory_sections:
        if sec not in sections_present:
            logger.warning(
                "topic_discovery_mandatory_fallback section=%s product=%s",
                sec, product_name,
            )
            fallback_topics += _fallback_topics_for_section(sec, claims, product_name)

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
) -> List[dict]:
    """Derive topics deterministically from claim data (no LLM required).

    Used when llm_client is None (offline mode).  Groups claims by kind,
    maps kinds to sections, and produces one topic per group.
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

    # Enforce mandatory section coverage (same pattern as LLM path)
    sections_present = {t.get("section") for t in topics}
    fallback_topics: list = []
    for sec in mandatory_sections:
        if sec not in sections_present:
            fallback_topics += _fallback_topics_for_section(sec, claims, product_name)

    reserved = len(fallback_topics)
    topics = topics[: max(0, max_topics - reserved)]
    topics += fallback_topics

    return topics[:max_topics]


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
