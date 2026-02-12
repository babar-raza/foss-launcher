"""TC-1402: LLM-based claim classification to filter non-user-facing claims.

Classifies claims as:
- user_facing: Keep in product_facts for documentation
- internal_detail: Code internals, hex constants, internal identifiers
- developer_instruction: Comments directed at developers

Spec: Content Quality Hardening Plan (TC-1402)
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from ...clients.llm_provider import LLMProviderClient, LLMError
from ...io.atomic import atomic_write_json
from ...util.logging import get_logger

logger = get_logger()

# Cache schema version
CLASSIFY_SCHEMA_VERSION = "v1"
DEFAULT_BATCH_SIZE = 20

# System prompt for classification
SYSTEM_PROMPT = (
    "You are a technical documentation classifier. For each claim about a software library, "
    "determine if it is:\n"
    "- user_facing: Useful information for someone using the library (features, capabilities, "
    "  supported formats, installation steps, API usage, etc.)\n"
    "- internal_detail: Implementation internals not useful to end users (hex constants, "
    "  internal class names with jcid/guid patterns, binary format details, internal data structures)\n"
    "- developer_instruction: Comments directed at the library's developers, not users "
    "  (todo items, code review notes, 'we should', 'your job is to')\n\n"
    "Respond with a JSON array. Each element has: claim_id, classification (one of the 3 above)."
)

# User prompt template
USER_PROMPT_TEMPLATE = (
    "Classify these {claim_count} claims for the {product_name} library.\n\n"
    "Claims:\n{claims_json}\n\n"
    "For each claim, respond with:\n"
    "- claim_id: the claim's ID\n"
    "- classification: \"user_facing\" | \"internal_detail\" | \"developer_instruction\"\n\n"
    "Output format: JSON array of objects."
)

# Offline heuristic patterns
DEVELOPER_PATTERNS = [
    re.compile(r'\byour job is to\b', re.IGNORECASE),
    re.compile(r'\bwe don.t need\b', re.IGNORECASE),
    re.compile(r'\bcode in module\b', re.IGNORECASE),
    re.compile(r'\btodo\b', re.IGNORECASE),
    re.compile(r'\bfixme\b', re.IGNORECASE),
    re.compile(r'\bhack\b', re.IGNORECASE),
    re.compile(r'\bworkaround\b', re.IGNORECASE),
]

INTERNAL_PATTERNS = [
    re.compile(r'0x[0-9a-fA-F]{4,}'),      # Hex constants
    re.compile(r'\bjcid\w+', re.IGNORECASE),  # jcid-prefixed identifiers
    re.compile(r'\bguid[_\-]', re.IGNORECASE),  # GUID identifiers
    # TC-1501: Binary format spec patterns (prose-style)
    re.compile(r'\w+\s*\(\d+\s*bytes?\)\s*:', re.IGNORECASE),  # "gctxid (20 bytes):", "cRef (4 bytes):"
    re.compile(r'\bsection\s+\d+\.\d+', re.IGNORECASE),  # "section 2.2.1", "section 2.6.7"
    re.compile(r'\b(?:MUST|SHALL|SHOULD)\s+(?:be|have|contain)\b'),  # RFC normative language (uppercase)
    re.compile(r'\b(?:CompactID|FileNode|ExtendedGUID|PartitionID|ObjectDeclaration|PropertySet|OutlineElementRTL)\b'),  # OneNote spec identifiers
    re.compile(r'["\']0x[0-9A-Fa-f]{2}["\']'),  # Quoted byte values: "0x00", "0xFF"
]

# Pattern for CamelCase identifiers with 3+ uppercase letters
_CAMEL_CASE_RE = re.compile(r'[A-Z][a-z]+(?:[A-Z][a-z]+){2,}')

# Pattern for code-like identifiers (snake_case or camelCase mid-word)
_CODE_IDENT_RE = re.compile(r'\b[a-z]+(?:_[a-z]+)+\b|\b[a-z]+[A-Z]\w+\b')


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #


def classify_claims_batch(
    claims: List[Dict[str, Any]],
    product_name: str,
    llm_client: Optional[LLMProviderClient] = None,
    cache_dir: Optional[Path] = None,
    offline_mode: bool = False,
    repo_url: str = "",
    repo_sha: str = "",
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> List[Dict[str, Any]]:
    """Classify and filter claims, keeping only user_facing ones.

    Args:
        claims: List of claim dicts (must have claim_id, claim_text)
        product_name: Product name (e.g. "Aspose.3D")
        llm_client: Optional LLM provider client (None => offline)
        cache_dir: Directory for classification cache files
        offline_mode: Force offline heuristics
        repo_url: Repository URL (for cache key)
        repo_sha: Repository SHA (for cache key)
        batch_size: Claims per LLM call (default 20)

    Returns:
        Filtered list of claims (only user_facing). Same structure as input,
        unchanged.
    """
    start_time = time.time()
    total_count = len(claims)

    if total_count == 0:
        return []

    logger.info(
        "claim_classification_started",
        claim_count=total_count,
        offline_mode=offline_mode,
        has_llm_client=llm_client is not None,
    )

    # Decide classification mode
    use_llm = not offline_mode and llm_client is not None

    if use_llm:
        # Try cache first
        classifications = _try_cache_load(
            cache_dir, repo_url, repo_sha, claims, llm_client,
        )
        if classifications is None:
            # LLM classification with offline fallback per batch
            classifications = _classify_via_llm(
                claims, product_name, llm_client, batch_size,
            )
            # Save to cache
            _save_cache(
                cache_dir, repo_url, repo_sha, claims, llm_client,
                classifications,
            )
    else:
        classifications = _classify_offline(claims)

    # Filter to user_facing only
    user_facing = []
    internal_count = 0
    developer_count = 0

    claim_lookup = {c["claim_id"]: c for c in claims}
    for claim_id, label in classifications.items():
        if label == "user_facing":
            if claim_id in claim_lookup:
                user_facing.append(claim_lookup[claim_id])
        elif label == "internal_detail":
            internal_count += 1
        elif label == "developer_instruction":
            developer_count += 1

    # Ensure any claims not in classifications dict are kept (safety net)
    classified_ids = set(classifications.keys())
    for claim in claims:
        if claim["claim_id"] not in classified_ids:
            user_facing.append(claim)

    duration_ms = int((time.time() - start_time) * 1000)
    logger.info(
        "claim_classification_completed",
        duration_ms=duration_ms,
        total=total_count,
        user_facing=len(user_facing),
        internal_detail=internal_count,
        developer_instruction=developer_count,
        mode="llm" if use_llm else "offline",
    )

    return user_facing


# --------------------------------------------------------------------------- #
# Offline heuristic classification
# --------------------------------------------------------------------------- #


def _classify_offline(claims: List[Dict[str, Any]]) -> Dict[str, str]:
    """Classify claims using heuristic patterns (no LLM).

    Returns:
        Dict mapping claim_id -> classification label.
    """
    results: Dict[str, str] = {}

    for claim in claims:
        claim_id = claim["claim_id"]
        claim_text = claim.get("claim_text", "")
        results[claim_id] = _heuristic_classify(claim_text)

    return results


def _heuristic_classify(claim_text: str) -> str:
    """Classify a single claim text using heuristic patterns.

    Returns one of: "user_facing", "internal_detail", "developer_instruction"
    """
    # Check developer instruction patterns
    for pattern in DEVELOPER_PATTERNS:
        if pattern.search(claim_text):
            return "developer_instruction"

    # Check internal detail patterns
    for pattern in INTERNAL_PATTERNS:
        if pattern.search(claim_text):
            return "internal_detail"

    # Check CamelCase identifiers with 3+ capitals and length > 10
    camel_matches = _CAMEL_CASE_RE.findall(claim_text)
    for match in camel_matches:
        if len(match) > 10:
            return "internal_detail"

    # Check code identifier density (>15% of words look like code identifiers)
    words = claim_text.split()
    if words:
        code_words = _CODE_IDENT_RE.findall(claim_text)
        code_ratio = len(code_words) / len(words)
        if code_ratio > 0.15:
            return "internal_detail"

    return "user_facing"


# --------------------------------------------------------------------------- #
# LLM classification
# --------------------------------------------------------------------------- #


def _classify_via_llm(
    claims: List[Dict[str, Any]],
    product_name: str,
    llm_client: LLMProviderClient,
    batch_size: int,
) -> Dict[str, str]:
    """Classify claims via LLM in batches, with offline fallback per batch.

    Returns:
        Dict mapping claim_id -> classification label.
    """
    all_classifications: Dict[str, str] = {}

    for i in range(0, len(claims), batch_size):
        batch = claims[i: i + batch_size]
        try:
            batch_results = _classify_batch_llm(batch, product_name, llm_client)
            all_classifications.update(batch_results)
        except Exception as exc:
            logger.warning(
                "classify_batch_llm_failed",
                batch_index=i,
                error=str(exc),
                message="Falling back to offline heuristics for this batch",
            )
            # Fallback: offline heuristics for this batch
            offline_results = _classify_offline(batch)
            all_classifications.update(offline_results)

    return all_classifications


def _classify_batch_llm(
    batch: List[Dict[str, Any]],
    product_name: str,
    llm_client: LLMProviderClient,
) -> Dict[str, str]:
    """Classify a single batch via LLM.

    Returns:
        Dict mapping claim_id -> classification label.

    Raises:
        LLMError: On API failure
        json.JSONDecodeError: On malformed response
    """
    # Build minimal JSON for claims
    claims_json_list = []
    for c in batch:
        claims_json_list.append({
            "claim_id": c["claim_id"],
            "claim_text": c.get("claim_text", ""),
            "claim_kind": c.get("claim_kind", "feature"),
        })

    claims_json_str = json.dumps(claims_json_list, indent=2, ensure_ascii=False)

    user_content = USER_PROMPT_TEMPLATE.format(
        claim_count=len(batch),
        product_name=product_name,
        claims_json=claims_json_str,
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

    response = llm_client.chat_completion(
        messages,
        call_id=f"classify_claims_batch_{batch[0]['claim_id'][:8]}",
        temperature=0.0,
        max_tokens=2048,
        response_format={"type": "json_object"},
    )

    content = response["content"]

    # Strip markdown fences if present
    content = _strip_markdown_fences(content)

    parsed = json.loads(content)

    # Handle both array and object-with-array responses
    if isinstance(parsed, dict):
        # LLM might wrap in {"classifications": [...]} or similar
        items = None
        for v in parsed.values():
            if isinstance(v, list):
                items = v
                break
        if items is None:
            raise json.JSONDecodeError(
                "LLM response has no list of classifications", content, 0,
            )
    elif isinstance(parsed, list):
        items = parsed
    else:
        raise json.JSONDecodeError(
            "LLM response is not a list or dict", content, 0,
        )

    # Build result dict
    valid_labels = {"user_facing", "internal_detail", "developer_instruction"}
    results: Dict[str, str] = {}
    for item in items:
        cid = item.get("claim_id", "")
        label = item.get("classification", "user_facing")
        if cid and label in valid_labels:
            results[cid] = label
        elif cid:
            # Invalid label -> default to user_facing (safe)
            results[cid] = "user_facing"

    return results


def _strip_markdown_fences(content: str) -> str:
    """Strip markdown code fences from LLM response."""
    content = content.strip()
    if content.startswith("```json"):
        content = content[7:]
    elif content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    return content.strip()


# --------------------------------------------------------------------------- #
# Cache helpers
# --------------------------------------------------------------------------- #


def _compute_cache_key(
    repo_url: str,
    repo_sha: str,
    claim_ids: List[str],
    llm_model: str,
) -> str:
    """Compute deterministic cache key for classification results.

    Components: repo_url | repo_sha | sorted_claim_ids | model | CLASSIFY_SCHEMA_VERSION
    """
    sorted_ids = "|".join(sorted(claim_ids))
    data = f"{repo_url}|{repo_sha}|{sorted_ids}|{llm_model}|{CLASSIFY_SCHEMA_VERSION}"
    return hashlib.sha256(data.encode()).hexdigest()


def _try_cache_load(
    cache_dir: Optional[Path],
    repo_url: str,
    repo_sha: str,
    claims: List[Dict[str, Any]],
    llm_client: LLMProviderClient,
) -> Optional[Dict[str, str]]:
    """Try to load classification results from cache.

    Returns:
        Dict mapping claim_id -> label, or None if cache miss.
    """
    if cache_dir is None:
        return None

    claim_ids = [c["claim_id"] for c in claims]
    llm_model = getattr(llm_client, "model", "unknown")
    cache_key = _compute_cache_key(repo_url, repo_sha, claim_ids, llm_model)
    cache_file = cache_dir / f"{cache_key}.json"

    if not cache_file.exists():
        return None

    try:
        with open(cache_file, "r", encoding="utf-8") as f:
            cache_data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None

    if cache_data.get("schema_version") != CLASSIFY_SCHEMA_VERSION:
        return None

    cached_classifications = cache_data.get("classifications", {})

    # Validate all claim IDs are present
    if not all(cid in cached_classifications for cid in claim_ids):
        return None

    logger.info("claim_classification_cache_hit", cache_key=cache_key[:16])
    return cached_classifications


def _save_cache(
    cache_dir: Optional[Path],
    repo_url: str,
    repo_sha: str,
    claims: List[Dict[str, Any]],
    llm_client: LLMProviderClient,
    classifications: Dict[str, str],
) -> None:
    """Save classification results to cache."""
    if cache_dir is None:
        return

    claim_ids = [c["claim_id"] for c in claims]
    llm_model = getattr(llm_client, "model", "unknown")
    cache_key = _compute_cache_key(repo_url, repo_sha, claim_ids, llm_model)

    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"{cache_key}.json"

    cache_data = {
        "cache_version": "1.0",
        "schema_version": CLASSIFY_SCHEMA_VERSION,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "repo_url": repo_url,
        "repo_sha": repo_sha,
        "llm_model": llm_model,
        "classifications": classifications,
    }

    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2, sort_keys=True)
    except OSError as exc:
        logger.warning(
            "claim_classification_cache_write_failed",
            error=str(exc),
        )
