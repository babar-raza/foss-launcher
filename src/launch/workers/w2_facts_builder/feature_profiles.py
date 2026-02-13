"""TC-1411: Structured feature profiles for W2 FactsBuilder.

Groups related claims into coherent feature descriptions with capabilities,
limitations, code examples, and audience level.  Feature profiles provide
structured, in-depth information that goes beyond individual sentence claims.

**Approach (heuristic + optional LLM)**:
1. Heuristic grouping: Cluster claims by keyword overlap
2. Optional LLM enrichment: Generate summaries and details for each group

Feature profiles are stored in ``product_facts.json`` under the
``feature_profiles`` key and consumed by W5 SectionWriter for richer content.

Spec references:
- specs/03_product_facts_and_evidence.md (Claims and evidence)
- specs/21_worker_contracts.md (W2 FactsBuilder contract)
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set

from ...clients.llm_provider import LLMProviderClient
from ...util.logging import get_logger
from .embeddings import compute_idf, compute_tfidf_vector, tokenize

logger = get_logger()

# Generic keywords for feature grouping (topic -> keyword set)
# These keywords are product-agnostic and cover common software library topics.
FEATURE_KEYWORDS: Dict[str, List[str]] = {
    "installation": ["install", "pip", "npm", "setup", "dependency", "dependencies", "requirements", "package"],
    "getting_started": ["getting started", "quickstart", "quick start", "tutorial", "hello world", "first steps"],
    "import_export": ["import", "export", "convert", "save", "load", "read", "write", "parse", "serialize"],
    "data_processing": ["process", "transform", "filter", "aggregate", "merge", "batch", "pipeline"],
    "api_reference": ["class", "method", "function", "api", "interface", "module", "provides", "endpoint"],
    "configuration": ["config", "configure", "option", "options", "settings", "parameter", "environment"],
    "error_handling": ["error", "exception", "handle", "retry", "fallback", "timeout", "validation"],
    "performance": ["performance", "optimize", "cache", "async", "parallel", "concurrent", "batch"],
    "security": ["auth", "authenticate", "token", "credential", "encrypt", "permission", "secure"],
    "integration": ["integrate", "plugin", "extension", "middleware", "hook", "adapter", "connector"],
}

# Keywords that are ambiguous in certain domains (e.g. 3D, file formats) and should
# not be the sole basis for assigning a claim to a topic.  If ALL matching keywords
# for a topic are in this set, the claim is NOT assigned unless score >= 3.
AMBIGUOUS_KEYWORDS: Dict[str, Set[str]] = {
    "security": {"token", "secure"},           # "token" = data token in parsers
    "integration": {"extension", "hook"},      # "extension" = file extension
    "performance": {"batch", "cache"},         # "batch" = batch processing
    "import_export": {"import"},               # "import" = Python import
    "api_reference": {"class", "method", "function", "module"},  # too generic alone
}


def _compute_keyword_score(
    claim_text: str,
    keywords: List[str],
) -> int:
    """Count how many keywords match in a claim text."""
    text_lower = claim_text.lower()
    return sum(1 for kw in keywords if kw in text_lower)


def _assign_claim_to_topics(
    claim: Dict[str, Any],
) -> List[str]:
    """Assign a claim to zero or more topics based on keyword overlap.

    Requires at least 2 keyword matches (threshold raised from 1 to reduce
    misclassification).  Additionally, if ALL matching keywords for a topic
    are in the AMBIGUOUS_KEYWORDS set, the topic is only assigned when
    score >= 3 — ensuring that domain-ambiguous terms like "token" or
    "extension" don't cause false classification on their own.
    """
    text = claim.get("claim_text", "")
    text_lower = text.lower()
    assigned = []
    for topic, keywords in FEATURE_KEYWORDS.items():
        score = _compute_keyword_score(text, keywords)
        if score < 2:
            continue
        # Check if ALL matching keywords are ambiguous for this topic
        ambiguous = AMBIGUOUS_KEYWORDS.get(topic, set())
        if ambiguous:
            matching_kws = [kw for kw in keywords if kw in text_lower]
            non_ambiguous = [kw for kw in matching_kws if kw not in ambiguous]
            if not non_ambiguous and score < 3:
                continue  # All matches are ambiguous — skip unless very strong
        assigned.append(topic)
    return assigned


def _extract_dynamic_keywords(claims: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    """Extract product-specific topic keywords from claim corpus using TF-IDF.

    Args:
        claims: List of claim dicts with claim_text

    Returns:
        Dict mapping topic name -> list of dynamic keywords
    """
    if len(claims) < 10:
        return {}  # Need sufficient corpus for meaningful TF-IDF

    texts = [c.get('claim_text', '') for c in claims if c.get('claim_text')]
    if not texts:
        return {}

    try:
        # Tokenize all claims
        tokenized_docs = [tokenize(text) for text in texts]

        # Compute IDF across the corpus
        idf = compute_idf(tokenized_docs)

        # Aggregate TF-IDF scores across all documents
        term_scores = {}
        for tokens in tokenized_docs:
            vec = compute_tfidf_vector(tokens, idf)
            for term, score in vec.items():
                term_scores[term] = term_scores.get(term, 0.0) + score

        # Take top 30 terms overall
        top_terms = sorted(term_scores.items(), key=lambda x: -x[1])[:30]

        # Group into a single "domain_specific" topic
        # Future enhancement: cluster by co-occurrence patterns
        return {"domain_specific": [term for term, _ in top_terms]}
    except Exception as e:
        logger.warning("dynamic_keyword_extraction_failed", error=str(e))
        return {}


def cluster_claims_by_feature(
    claims: List[Dict[str, Any]],
    dynamic_keywords: Optional[Dict[str, List[str]]] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """Group claims into feature clusters using keyword overlap.

    Claims may belong to multiple clusters.  Claims with no keyword match
    are placed in an "other" cluster.

    Args:
        claims: List of claim dicts (must have claim_text, claim_id)
        dynamic_keywords: Optional dict of dynamic keywords to merge with static keywords

    Returns:
        Dict mapping topic name -> list of claims in that cluster
    """
    # Merge static and dynamic keywords
    merged_keywords = dict(FEATURE_KEYWORDS)
    if dynamic_keywords:
        for topic, keywords in dynamic_keywords.items():
            if topic in merged_keywords:
                merged_keywords[topic].extend(keywords)
            else:
                merged_keywords[topic] = keywords

    clusters: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    for claim in claims:
        # Use merged keywords for topic assignment
        topics = _assign_claim_to_topics_with_keywords(claim, merged_keywords)
        if topics:
            for topic in topics:
                clusters[topic].append(claim)
        else:
            clusters["other"].append(claim)

    return dict(clusters)


def _assign_claim_to_topics_with_keywords(
    claim: Dict[str, Any],
    keywords_dict: Dict[str, List[str]],
) -> List[str]:
    """Assign a claim to zero or more topics based on keyword overlap.

    This is a generalized version of _assign_claim_to_topics that accepts
    a custom keyword dictionary (for dynamic keyword merging).

    Requires at least 2 keyword matches (threshold raised from 1 to reduce
    misclassification).  Additionally, if ALL matching keywords for a topic
    are in the AMBIGUOUS_KEYWORDS set, the topic is only assigned when
    score >= 3 — ensuring that domain-ambiguous terms like "token" or
    "extension" don't cause false classification on their own.
    """
    text = claim.get("claim_text", "")
    text_lower = text.lower()
    assigned = []
    for topic, keywords in keywords_dict.items():
        score = _compute_keyword_score(text, keywords)
        if score < 2:
            continue
        # Check if ALL matching keywords are ambiguous for this topic
        ambiguous = AMBIGUOUS_KEYWORDS.get(topic, set())
        if ambiguous:
            matching_kws = [kw for kw in keywords if kw in text_lower]
            non_ambiguous = [kw for kw in matching_kws if kw not in ambiguous]
            if not non_ambiguous and score < 3:
                continue  # All matches are ambiguous — skip unless very strong
        assigned.append(topic)
    return assigned


def _extract_capabilities_and_limitations(
    claims: List[Dict[str, Any]],
) -> tuple:
    """Split claims into capabilities and limitations.

    Returns:
        (capabilities: List[str], limitations: List[str])
    """
    capabilities = []
    limitations = []

    for claim in claims:
        text = claim.get("claim_text", "")
        kind = claim.get("claim_kind", "feature")
        if kind == "limitation":
            limitations.append(text)
        else:
            capabilities.append(text)

    return capabilities, limitations


def _generate_feature_id(topic: str) -> str:
    """Generate a stable feature ID from topic name."""
    return f"fp_{topic}"


def _infer_audience(claims: List[Dict[str, Any]]) -> str:
    """Infer audience level from claim content."""
    text_blob = " ".join(c.get("claim_text", "") for c in claims).lower()
    advanced_markers = ["architecture", "internal", "binary format", "specification", "chunk"]
    intermediate_markers = ["configuration", "option", "parameter", "customize"]

    if any(m in text_blob for m in advanced_markers):
        return "advanced"
    if any(m in text_blob for m in intermediate_markers):
        return "intermediate"
    return "beginner"


# Regex to find CamelCase class names in claim text
_CLASS_NAME_RE = re.compile(r'\b([A-Z][a-zA-Z0-9]{2,})\b')

# Common English words that look CamelCase but aren't class names
_CAMELCASE_STOP_WORDS = frozenset({
    'The', 'This', 'That', 'Does', 'Not', 'Can', 'Has', 'For', 'And', 'With',
    'From', 'Into', 'Are', 'Was', 'Were', 'All', 'Any', 'Each', 'New', 'Old',
    'Use', 'Set', 'Get', 'Add', 'Run', 'See', 'May', 'Try', 'Let', 'Put',
    'CSV', 'JSON', 'XML', 'HTML', 'HTTP', 'API', 'SDK', 'URL', 'PDF', 'OBJ',
    'FBX', 'STL', 'PLY', 'USD', 'DXF', 'DAE', 'GLB',
})


def _extract_class_names_from_claims(claims: List[Dict[str, Any]]) -> List[str]:
    """Extract CamelCase class names mentioned in claim texts.

    Returns deduplicated names in order of first appearance.
    """
    seen: Set[str] = set()
    result: List[str] = []
    for claim in claims:
        text = claim.get("claim_text", "")
        for match in _CLASS_NAME_RE.finditer(text):
            name = match.group(1)
            if name in _CAMELCASE_STOP_WORDS:
                continue
            if name not in seen:
                seen.add(name)
                result.append(name)
    return result


def _find_code_example_for_topic(
    topic_claims: List[Dict[str, Any]],
    code_examples: Dict[str, str],
    api_classes_map: Dict[str, List[str]],
) -> tuple:
    """Find the best code example and API classes for a topic.

    Bridges topic names to class names by extracting CamelCase class names from
    the topic's claim texts, then looking up those class names in the code_examples
    dict (which is keyed by lowercased class/workflow names).

    Returns:
        (code_example: str, api_classes: List[str])
    """
    class_names = _extract_class_names_from_claims(topic_claims)

    best_example = ""
    matched_classes: List[str] = []

    for name in class_names:
        name_lower = name.lower()
        if name_lower in code_examples and code_examples[name_lower]:
            if not best_example:
                best_example = code_examples[name_lower]
            matched_classes.append(name)

    return best_example, matched_classes


def build_feature_profiles_heuristic(
    claims: List[Dict[str, Any]],
    code_understanding: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Build feature profiles from claims using heuristic clustering.

    Args:
        claims: List of claim dicts
        code_understanding: Optional code_understanding.json data

    Returns:
        List of feature profile dicts
    """
    # Extract dynamic keywords from claim corpus
    dynamic_keywords = _extract_dynamic_keywords(claims)
    has_dynamic_keywords = bool(dynamic_keywords)

    # Cluster claims using merged static + dynamic keywords
    clusters = cluster_claims_by_feature(claims, dynamic_keywords)

    # Build code example map from code_understanding
    code_examples: Dict[str, str] = {}
    api_classes_map: Dict[str, List[str]] = {}
    if code_understanding:
        for workflow in code_understanding.get("usage_workflows", []):
            name = workflow.get("name", "").lower().replace(" ", "_")
            steps = workflow.get("steps", [])
            code_lines = [s.get("code", "") for s in steps if s.get("code")]
            if code_lines:
                code_examples[name] = "\n".join(code_lines)
            api_classes_map[name] = workflow.get("api_involved", [])

        for profile in code_understanding.get("class_profiles", []):
            cls_name = profile.get("name", "").lower()
            usage = profile.get("typical_usage", "")
            if usage:
                code_examples[cls_name] = usage

    # Lower cluster minimum when dynamic keywords are used (more specific matching)
    min_cluster_size = 2 if has_dynamic_keywords else 3

    profiles = []
    for topic, topic_claims in sorted(clusters.items()):
        if len(topic_claims) < min_cluster_size:
            # Skip tiny clusters — they're likely noise
            continue

        capabilities, limitations = _extract_capabilities_and_limitations(topic_claims)
        claim_ids = sorted(set(c.get("claim_id", "") for c in topic_claims))

        # Find best code example for this topic
        # First try direct topic name match (e.g., "installation" workflow)
        example = code_examples.get(topic, "")
        api_classes = api_classes_map.get(topic, [])

        # Bridge: if no direct match, find class names in claim texts
        if not example:
            example, bridged_classes = _find_code_example_for_topic(
                topic_claims, code_examples, api_classes_map,
            )
            if bridged_classes and not api_classes:
                api_classes = bridged_classes

        # Use highest source_relevance claim's text as summary
        best_claim = max(
            topic_claims,
            key=lambda c: c.get("source_relevance", 50),
        )
        summary = best_claim.get("claim_text", "")

        # Build detail from all capability claims
        detail = " ".join(capabilities[:5]) if capabilities else summary

        # Pretty name from topic
        pretty_name = topic.replace("_", " ").title()

        tags = [topic]
        # Add claim_kind tags
        tags.extend(sorted(set(c.get("claim_kind", "") for c in topic_claims if c.get("claim_kind"))))

        profiles.append({
            "feature_id": _generate_feature_id(topic),
            "name": pretty_name,
            "summary": summary,
            "detail": detail,
            "related_claims": claim_ids,
            "capabilities": capabilities[:10],
            "limitations": limitations[:5],
            "code_example": example,
            "api_classes": api_classes,
            "audience": _infer_audience(topic_claims),
            "tags": sorted(set(tags)),
        })

    return profiles


def build_feature_profiles(
    claims: List[Dict[str, Any]],
    product_name: str,
    code_understanding: Optional[Dict[str, Any]] = None,
    llm_client: Optional[LLMProviderClient] = None,
) -> List[Dict[str, Any]]:
    """Build structured feature profiles from claims.

    Uses heuristic clustering for deterministic grouping. When an LLM
    client is available, enriches each profile with a polished summary
    and detail description.

    Args:
        claims: List of claim dicts
        product_name: Product name for context
        code_understanding: Optional code_understanding.json data
        llm_client: Optional LLM client for enrichment

    Returns:
        List of feature profile dicts
    """
    if not claims:
        return []

    # Step 1: Heuristic clustering (always deterministic)
    profiles = build_feature_profiles_heuristic(claims, code_understanding)

    if not profiles:
        return []

    # Step 2: Optional LLM enrichment of summaries
    if llm_client is not None and len(profiles) > 0:
        try:
            profiles = _enrich_profiles_with_llm(
                profiles, product_name, llm_client
            )
        except Exception as e:
            logger.warning(
                "feature_profiles_llm_enrichment_failed",
                error=str(e),
                product_name=product_name,
            )
            # Keep heuristic profiles

    logger.info(
        "feature_profiles_built",
        product_name=product_name,
        profile_count=len(profiles),
        total_claims_covered=sum(len(p["related_claims"]) for p in profiles),
    )

    return profiles


def _enrich_profiles_with_llm(
    profiles: List[Dict[str, Any]],
    product_name: str,
    llm_client: LLMProviderClient,
) -> List[Dict[str, Any]]:
    """Enrich feature profiles with LLM-generated summaries.

    Sends all profiles in a single batch to generate polished summaries
    and details for each feature.
    """
    profiles_summary = []
    for p in profiles:
        profiles_summary.append({
            "feature_id": p["feature_id"],
            "name": p["name"],
            "capabilities": p["capabilities"][:5],
            "limitations": p["limitations"][:3],
        })

    system_msg = (
        "You are a technical documentation writer. For each feature profile below, "
        "write a concise 1-sentence summary and a 2-3 sentence detail description "
        "that would be useful in product documentation. Focus on what users can do.\n\n"
        "Return a JSON object where keys are feature_ids and values are "
        '{"summary": "...", "detail": "..."}.'
    )

    user_msg = (
        f"Product: {product_name}\n\n"
        f"Feature profiles:\n{json.dumps(profiles_summary, indent=2)}\n\n"
        "Generate summaries and details for each feature_id."
    )

    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg},
    ]

    response = llm_client.chat_completion(
        messages,
        call_id="feature_profile_enrichment",
        temperature=0.0,
        max_tokens=2048,
        response_format={"type": "json_object"},
    )

    raw = response.get("content", "")
    # Parse response
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        first_nl = cleaned.index("\n") if "\n" in cleaned else len(cleaned)
        cleaned = cleaned[first_nl + 1:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    enrichments = json.loads(cleaned.strip())

    # Apply enrichments
    for profile in profiles:
        fid = profile["feature_id"]
        if fid in enrichments:
            enriched = enrichments[fid]
            if enriched.get("summary"):
                profile["summary"] = enriched["summary"]
            if enriched.get("detail"):
                profile["detail"] = enriched["detail"]

    return profiles


def synthesize_use_cases_from_profiles(
    feature_profiles: List[Dict[str, Any]],
    product_name: str,
) -> List[Dict[str, Any]]:
    """Synthesize use cases from feature profile topics.

    TC-1618: Generate 2-3 use cases per high-density feature profile for
    blog/marketing content.

    Topic-specific templates:
    - import_export → "Convert files between formats", "Migrate legacy data"
    - data_processing → "Transform data programmatically", "Build ETL pipelines"
    - api_reference → "Build custom tools", "Automate repetitive tasks"
    - configuration → "Customize behavior for specific workflows"
    - performance → "Optimize processing for large datasets"

    Args:
        feature_profiles: List of feature profile dicts (from build_feature_profiles)
        product_name: Product name for templates

    Returns:
        List of synthesized use case claim dicts
    """
    use_cases = []

    # Topic-specific use case templates
    use_case_templates = {
        "import_export": [
            {
                "scenario": "File format conversion",
                "description": f"Convert files between different formats using {product_name} programmatically, enabling automated migration pipelines and batch processing workflows.",
                "benefit": "Eliminate manual conversion tasks and integrate format transformation into automated workflows",
                "example_domain": "Data migration",
            },
            {
                "scenario": "Legacy data migration",
                "description": f"Migrate legacy data to modern formats with {product_name}, preserving structure and metadata while upgrading to current standards.",
                "benefit": "Modernize data infrastructure without losing historical information",
                "example_domain": "System modernization",
            },
        ],
        "data_processing": [
            {
                "scenario": "Automated data transformation",
                "description": f"Transform data programmatically using {product_name} APIs, enabling custom processing logic and integration with existing data pipelines.",
                "benefit": "Automate repetitive data transformations and ensure consistency",
                "example_domain": "Data engineering",
            },
            {
                "scenario": "ETL pipeline construction",
                "description": f"Build ETL pipelines with {product_name} for automated data processing, extraction, and loading into target systems.",
                "benefit": "Streamline data workflows and reduce manual intervention",
                "example_domain": "Data integration",
            },
        ],
        "api_reference": [
            {
                "scenario": "Custom tool development",
                "description": f"Build custom tools and utilities on top of {product_name} APIs to address domain-specific requirements and workflow needs.",
                "benefit": "Extend core functionality to match unique business requirements",
                "example_domain": "Tool development",
            },
            {
                "scenario": "Workflow automation",
                "description": f"Automate repetitive tasks with {product_name} programmatic interfaces, reducing manual effort and improving consistency.",
                "benefit": "Increase productivity by automating routine operations",
                "example_domain": "Process automation",
            },
        ],
        "configuration": [
            {
                "scenario": "Workflow customization",
                "description": f"Customize {product_name} behavior for specific workflows by configuring options and parameters to match unique use case requirements.",
                "benefit": "Adapt the product to specific operational needs without code changes",
                "example_domain": "Configuration management",
            },
        ],
        "performance": [
            {
                "scenario": "Large-scale data processing",
                "description": f"Optimize processing for large datasets using {product_name} performance features like batching, caching, and parallel execution.",
                "benefit": "Handle enterprise-scale workloads efficiently",
                "example_domain": "High-volume processing",
            },
        ],
        "integration": [
            {
                "scenario": "System integration",
                "description": f"Integrate {product_name} with existing systems and workflows using plugins, adapters, and middleware connections.",
                "benefit": "Connect the product seamlessly to existing infrastructure",
                "example_domain": "Enterprise integration",
            },
        ],
    }

    # Generate use cases for profiles with sufficient claim density
    for profile in feature_profiles:
        topic = None
        # Extract topic from tags or feature_id
        tags = profile.get("tags", [])
        for tag in tags:
            if tag in use_case_templates:
                topic = tag
                break

        if not topic:
            # Try extracting from feature_id (e.g., "fp_import_export" → "import_export")
            feature_id = profile.get("feature_id", "")
            if feature_id.startswith("fp_"):
                potential_topic = feature_id[3:]  # Remove "fp_" prefix
                if potential_topic in use_case_templates:
                    topic = potential_topic

        if not topic:
            continue

        # Only generate use cases for high-density profiles (3+ claims)
        claim_ids = profile.get("related_claims", [])
        if len(claim_ids) < 3:
            continue

        # Generate use cases from templates for this topic
        templates = use_case_templates[topic]
        for template in templates:
            use_cases.append({
                "claim_text": f"{template['scenario']}: {template['description']}",
                "claim_kind": "use_case",
                "section_kind": "use_case",
                "source_type": "synthesized",
                "source_file": "feature_profiles_synthesis",
                "start_line": 0,
                "end_line": 0,
                "keyword_boost": True,
                "benefit": template["benefit"],
                "example_domain": template["example_domain"],
            })

    return use_cases
