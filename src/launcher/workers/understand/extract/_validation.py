"""Post-LLM claim validation, normalization, deduplication, and contamination filtering."""
from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path
from typing import Any

from launcher.models.claims import Claim, EvidenceAnchor
from launcher.models.product import ApiSurface, ProductIdentity
from launcher.workers.understand.extract._filters import _is_junk_claim, _is_off_topic
from launcher.workers.understand.extract._linking import _assign_tier_relevance

logger = logging.getLogger(__name__)

# Jaccard similarity threshold for deduplication
_DEDUP_THRESHOLD = 0.85

# Phase C: Stable sort key for deduplication — ensures high-confidence claims survive
# regardless of LLM output ordering across reruns.
_SOURCE_PRIORITY: dict[str, int] = {
    "docstring": 0,         # highest priority (ground truth)
    "llm_corroborated": 1,  # TC-UND-210: LLM claim corroborated by docstring evidence
    "llm": 2,
    "deterministic": 3,
    "deterministic_fallback": 3,  # TC-UND-211: same priority as deterministic (same extraction method)
    "llm_fallback": 4,      # lowest priority
}

# TC-HAL-06: Confidence values by claim source (evidence strength)
# TC-5171: Exported as public CONFIDENCE_BY_SOURCE so the histogram in worker.py
#           derives its bucket keys directly from this dict (single source of truth).
# TC-UND-210: llm_corroborated — LLM claim whose API identifier is also backed by docstring
CONFIDENCE_BY_SOURCE: dict[str, float] = {
    "docstring": 1.0,
    "llm_corroborated": 0.85,  # TC-UND-210: corroborated by docstring evidence
    "llm": 0.75,
    "deterministic": 0.65,  # TC-FIX-02: raised from 0.5 to give margin above TC-4225 threshold
    "llm_sparse_grounding": 0.55,  # BBN-02: sparse bounded-mode fallback (above TC-4225 threshold)
    "deterministic_fallback": 0.60,  # TC-UND-211: deterministic extraction used as LLM substitute (survives U-2)
    "llm_fallback": 0.35,
}
# Private alias preserved for backward compatibility with existing tests/imports
_CONFIDENCE_BY_SOURCE = CONFIDENCE_BY_SOURCE

# BBN-02: When bounded-description mode is active but api_facts are fewer than this
# threshold, unbound LLM claims get confidence=0.55 (llm_sparse_grounding) instead of
# 0.35 (llm_fallback), preventing near-total claim collapse on lean repos.
_SPARSE_FACTS_THRESHOLD: int = 10

# Keywords indicating a claim is about a third-party technology, not the product.
# A claim is considered contaminated if it contains one of these keywords
# WITHOUT also mentioning the product family name.
_CONTAMINANT_KEYWORDS: frozenset[str] = frozenset({
    "docling", "django", "flask", "scikit-learn", "sklearn",
    "tensorflow", "pytorch", "fastapi", "uvicorn", "langchain",
    "huggingface", "transformers", "mlx-vlm", "granite",
    "streamlit", "gradio", "celery", "gunicorn",
})

def _load_extra_keywords() -> frozenset[str]:
    """Load extra contamination keywords from configs/contamination_keywords.yaml.

    The config file is optional. If absent or malformed, an empty frozenset is
    returned so the hardcoded _CONTAMINANT_KEYWORDS baseline remains intact
    (TC-4211: graceful fallback).

    Expected file format:
        keywords:
          - aiohttp
          - pydantic
    """
    try:
        # Resolve from this file: src/launcher/workers/understand/extract/_validation.py
        # parents: [extract/, understand/, workers/, launcher/, src/, project_root]
        config_path = Path(__file__).resolve().parents[5] / "configs" / "contamination_keywords.yaml"
        if not config_path.exists():
            return frozenset()
        import yaml  # deferred to avoid import cycle risk
        data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return frozenset()
        kws = data.get("keywords", [])
        if not isinstance(kws, list):
            return frozenset()
        return frozenset(str(k).lower() for k in kws if k)
    except Exception:
        return frozenset()


# Merged keyword set: hardcoded baseline + any extras loaded from config.
# Frozen at module import time; add new frameworks to configs/contamination_keywords.yaml
# without touching this file (TC-4211).
_EFFECTIVE_CONTAMINANT_KEYWORDS: frozenset[str] = (
    _CONTAMINANT_KEYWORDS | _load_extra_keywords()
)

# GitHub issue/PR patterns that indicate changelog entries, not product claims
_CHANGELOG_PATTERN = re.compile(
    r"\(\s*#\d{3,}\s*\)|"           # (#1234)
    r"\[#\d{3,}\]\(https://github", # [#1234](https://github...)
    re.IGNORECASE,
)

_PRIVATE_PYTHON_API_RE = re.compile(r"(?<!\w)_[A-Za-z]\w*")
# TC-PLT-213: C++/C# also use underscore prefix for internal/private members
_PRIVATE_CPP_API_RE = re.compile(r"(?<!\w)_[A-Z]\w*")
# Java uses package-private (no modifier) but we detect common internal patterns
_PRIVATE_JAVA_API_RE = re.compile(r"(?<!\w)(?:internal|impl)\.\w+", re.IGNORECASE)


def _references_private_api(text: str, product: ProductIdentity) -> bool:
    """Return True when a claim references a private/internal API token for the platform."""
    platform = product.platform
    if platform == "python":
        return bool(_PRIVATE_PYTHON_API_RE.search(text))
    if platform in ("cpp", "dotnet"):
        return bool(_PRIVATE_CPP_API_RE.search(text))
    if platform == "java":
        return bool(_PRIVATE_JAVA_API_RE.search(text))
    return False


# Keep old name as alias for backward compatibility with any external callers
_references_private_python_api = _references_private_api


def _filter_contaminated_claims(
    claims: list[Claim],
    product: ProductIdentity,
) -> list[Claim]:
    """Remove claims about unrelated third-party technologies.

    A claim is removed if:
    1. It contains a contaminant keyword (e.g., 'docling', 'django')
       WITHOUT the product family name in the same claim text, OR
    2. It looks like a changelog entry (GitHub issue references).

    Claims that mention both the product and a third-party tech are kept
    (e.g., "use Django with Aspose.Cells to generate reports").
    """
    family_lower = product.family.lower()
    display_lower = product.display_name.lower()
    canonical_lower = (product.canonical_import or "").lower()

    # Generic words that appear in display names but are not product-specific
    _GENERIC_WORDS = {"foss", "for", "via", "net", "python", "java", "node", "ruby",
                      "the", "and", "with", "open", "source", "free", "library"}

    # Product terms that, if present, indicate the claim is about OUR product
    product_terms = {family_lower, display_lower}
    if canonical_lower:
        product_terms.add(canonical_lower)
    # Add the brand name (e.g., "aspose" from "Aspose.Cells")
    brand = display_lower.split(".")[0].split()[0] if "." in display_lower else ""
    if brand and brand not in _GENERIC_WORDS:
        product_terms.add(brand)

    filtered: list[Claim] = []
    for claim in claims:
        text_lower = claim.text.lower()

        # Check for changelog entries
        if _CHANGELOG_PATTERN.search(claim.text):
            continue

        # Check for contaminant keywords (TC-4211: use merged set including config-loaded extras)
        has_contaminant = any(kw in text_lower for kw in _EFFECTIVE_CONTAMINANT_KEYWORDS)
        if has_contaminant:
            # Keep the claim only if it also mentions the product
            has_product = any(pt in text_lower for pt in product_terms)
            if not has_product:
                continue

        filtered.append(claim)
    return filtered


def _sanitize_raw_claim(raw: Any) -> dict[str, Any] | None:
    """TC-5138: Coerce malformed LLM claim dicts into a safe shape, or return None to skip.

    Handles: null text, missing keys, null evidence, wrong types in evidence items.
    """
    if not isinstance(raw, dict):
        return None
    text = raw.get("text")
    if text is None or not isinstance(text, str) or not text.strip():
        return None
    # Coerce evidence
    evidence = raw.get("evidence")
    if not isinstance(evidence, list):
        evidence = []
    sanitized_evidence: list[dict[str, Any]] = []
    for item in evidence:
        if not isinstance(item, dict):
            continue
        if item.get("source_file") is None:
            item["source_file"] = ""
        if item.get("snippet") is None:
            item["snippet"] = ""
        sanitized_evidence.append(item)
    raw["evidence"] = sanitized_evidence
    # Coerce kind
    if not raw.get("kind") or not isinstance(raw.get("kind"), str):
        raw["kind"] = "feature"
    return raw


def _validate_and_normalize_claims(
    raw_claims: list[dict[str, Any]],
    product: ProductIdentity,
    api_surface: ApiSurface,
    file_tree: "frozenset[str] | None" = None,
    drop_log: "list[dict] | None" = None,
) -> list[Claim]:
    """Post-LLM engineering: filter, deduplicate, normalize claims.

    Steps:
    1. Filter to visibility=public only
    2. Normalize text (collapse whitespace, lowercase for hashing)
    3. Generate stable claim_ids: CLM-{family}-{hash[:6]}
    4. Deduplicate by Jaccard similarity > 0.85
    5. Assign tier_relevance based on content
    """
    family_slug = re.sub(r"[^a-z0-9]", "-", product.family.lower()).strip("-")

    _MAX_DROP_LOG = 500

    def _record_drop(text: str, stage: str, reason: str,
                     confidence: float | None = None,
                     claim_source: str | None = None) -> None:
        """Append a drop record to drop_log if provided and not yet at cap."""
        if drop_log is None:
            return
        if len(drop_log) >= _MAX_DROP_LOG:
            return
        drop_log.append({
            "claim_text_prefix": text[:80],
            "drop_stage": stage,
            "drop_reason": reason,
            "confidence_before": confidence,
            "claim_source": claim_source,
        })

    # Step 0: Sanitize malformed LLM dicts (TC-5138)
    raw_claims = [s for c in raw_claims if (s := _sanitize_raw_claim(c)) is not None]

    # Step 1: Filter internal claims (raw visibility flag)
    raw_internal = [c for c in raw_claims if c.get("visibility", "public") == "internal"]
    for c in raw_internal:
        _record_drop(c.get("text", ""), "visibility_filter", "raw claim visibility=internal",
                     c.get("confidence"), c.get("claim_source"))
    public_claims = [
        c for c in raw_claims
        if c.get("visibility", "public") == "public"
    ]

    # Step 2-3: Normalize and build Claim objects with stable IDs
    normalized: list[Claim] = []
    filtered_short = 0
    filtered_junk = 0
    filtered_private_api = 0
    for raw in public_claims:
        text = raw.get("text", "").strip()
        if not text:
            continue
        if len(text) < 15:
            filtered_short += 1
            _record_drop(text, "length_filter", f"text too short ({len(text)} chars)",
                         raw.get("confidence"), raw.get("claim_source"))
            continue
        if _is_junk_claim(text):
            filtered_junk += 1
            _record_drop(text, "junk_filter", "junk claim (code-like, changelog, emoji, or high stop-word ratio)",
                         raw.get("confidence"), raw.get("claim_source"))
            continue
        if _references_private_api(text, product):
            filtered_private_api += 1
            _record_drop(text, "private_api_filter", f"references private API ({product.platform})",
                         raw.get("confidence"), raw.get("claim_source"))
            continue

        kind = raw.get("kind", "feature")

        # Determine visibility: off-topic claims become internal (will be filtered later)
        visibility = "public"
        if _is_off_topic(text, product):
            visibility = "internal"
            _record_drop(text, "off_topic_filter", "claim reclassified as internal (off-topic: mentions third-party tech without product keywords)",
                         raw.get("confidence"), raw.get("claim_source"))

        # Generate stable claim_id from normalized text
        norm_text = _normalize_text(text, product.display_name)
        claim_hash = hashlib.sha256(
            f"{norm_text}|{kind}".encode("utf-8")
        ).hexdigest()[:6]
        claim_id = f"CLM-{family_slug}-{claim_hash}"

        # Build evidence anchors
        evidence: list[EvidenceAnchor] = []
        _invalid_evidence_paths = 0
        for ev in raw.get("evidence", []):
            if isinstance(ev, dict):
                src_file = ev.get("source_file", "")
                # P2-C: Validate that source_file exists in file_tree
                # Exempt pseudo-paths: "docstring:ClassName" used by deterministic harvesting
                if (file_tree and src_file
                        and not src_file.startswith("docstring:")
                        and src_file not in file_tree):
                    logger.debug(
                        "evidence_invalid_path: source_file=%r not in file_tree; "
                        "marking as unknown for claim_id will be %r",
                        src_file, claim_id,  # claim_id may not be assigned yet; use text hash
                    )
                    src_file = "unknown"
                    _invalid_evidence_paths += 1
                evidence.append(EvidenceAnchor(
                    source_file=src_file,
                    line_start=ev.get("line_start"),
                    line_end=ev.get("line_end"),
                    snippet=ev.get("snippet", ""),
                ))
        if _invalid_evidence_paths > 0:
            logger.info(
                "evidence_validation: %d evidence anchors had invalid paths (not in file_tree)",
                _invalid_evidence_paths,
            )

        # Assign tier_relevance
        tier_relevance = _assign_tier_relevance(text, kind, api_surface)

        claim_source = raw.get("claim_source", "llm")

        # TC-HAL-06: Assign confidence by claim source (evidence strength)
        confidence = _CONFIDENCE_BY_SOURCE.get(claim_source, 0.75)

        normalized.append(Claim(
            claim_id=claim_id,
            text=text,
            kind=kind,
            evidence=evidence,
            visibility=visibility,
            tier_relevance=tier_relevance,
            confidence=confidence,
            claim_source=claim_source,
        ))

    # Phase C: Sort by confidence DESC before dedup so high-confidence claims survive
    # regardless of LLM output ordering. Tiebreak: source priority, then text (stable).
    normalized.sort(key=lambda c: (
        -c.confidence,
        _SOURCE_PRIORITY.get(c.claim_source, 99),
        c.text,
    ))

    # Step 4: Deduplicate by Jaccard similarity
    deduplicated = _deduplicate_claims(normalized, drop_log=drop_log)

    internal_count = sum(1 for c in deduplicated if c.visibility == "internal")
    logger.info(
        "claim_normalize_stats input=%d kept=%d filtered_junk=%d filtered_short=%d filtered_private_api=%d off_topic=%d deduplicated=%d",
        len(raw_claims),
        len(deduplicated),
        filtered_junk,
        filtered_short,
        filtered_private_api,
        internal_count,
        len(normalized) - len(deduplicated),
    )
    return deduplicated


def _normalize_text(text: str, product_name: str) -> str:
    """Normalize claim text for stable ID generation.

    Consistent with extract_claims.normalize_claim_text:
    - Trim, collapse whitespace, lowercase
    - Replace product name with token
    """
    result = text.strip()
    result = re.sub(r"\s+", " ", result)
    result = result.lower()
    if product_name:
        result = re.sub(
            re.escape(product_name.lower()),
            "{product_name}",
            result,
            flags=re.IGNORECASE,
        )
    return result


# ---------------------------------------------------------------------------
# UND-01: Post-resolution evidence quality filter
# ---------------------------------------------------------------------------

_EVIDENCE_RELEVANCE_STOPWORDS: frozenset[str] = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "and", "or", "but", "for", "of", "in", "to", "on", "at", "by",
    "with", "from", "as", "it", "its", "this", "that", "these", "those",
})


def _score_evidence_relevance(claim_text: str, snippet_text: str) -> float:
    """Score overlap between claim text and evidence snippet (0.0–1.0).

    Returns the fraction of claim significant words found in the snippet.
    """
    if not claim_text or not snippet_text:
        return 0.0
    claim_words = set(claim_text.lower().split()) - _EVIDENCE_RELEVANCE_STOPWORDS
    snippet_words = set(snippet_text.lower().split()) - _EVIDENCE_RELEVANCE_STOPWORDS
    if not claim_words:
        return 0.0
    return len(claim_words & snippet_words) / len(claim_words)


def _filter_weak_evidence(
    claims: list[Claim],
    *,
    sparse_facts: bool = False,
) -> list[Claim]:
    """UND-01: Reject claims with empty evidence; downgrade irrelevant evidence.

    - LLM claims where ALL evidence snippets are empty → rejected
    - LLM claims where no evidence snippet has >10% word overlap → downgraded to 0.35
      (or to 0.55 / llm_sparse_grounding when sparse_facts=True — BBN-02)
    - Deterministic/docstring claims exempt (they have inherent grounding)
    - Install-kind claims exempt (evidence is often just a version string)

    Args:
        claims: Normalized claims to filter.
        sparse_facts: When True, unbound LLM claims get confidence=0.55
            (``llm_sparse_grounding``) instead of 0.35 (``llm_fallback``).
            Set this when the extraction database has fewer than
            ``_SPARSE_FACTS_THRESHOLD`` api_facts — prevents near-total claim
            collapse on lean repos in bounded-description mode.  BBN-02.
    """
    result: list[Claim] = []
    rejected_empty = 0
    downgraded = 0
    sparse_elevated = 0

    for claim in claims:
        source = getattr(claim, "claim_source", "llm")
        # Deterministic and docstring claims have inherent grounding
        if source in ("deterministic", "docstring"):
            result.append(claim)
            continue
        # Install claims are exempt
        if claim.kind == "install":
            result.append(claim)
            continue

        evidence = claim.evidence or []

        # Check for all-empty evidence
        all_empty = all(
            not (getattr(e, "snippet", "") or "").strip()
            for e in evidence
        ) if evidence else True

        if all_empty and source == "llm":
            # LLM claim with zero evidence → reject
            rejected_empty += 1
            continue

        # Check relevance: does any evidence snippet share words with the claim?
        has_relevant = False
        for e in evidence:
            snippet_text = getattr(e, "snippet", "") or ""
            if _score_evidence_relevance(claim.text, snippet_text) > 0.10:
                has_relevant = True
                break

        if not has_relevant and evidence and source in ("llm", "llm_fallback"):
            if sparse_facts:
                # BBN-02: Sparse bounded-mode — floor at 0.55 so claims survive TC-4225.
                # Tagged llm_sparse_grounding for audit visibility.
                claim = claim.model_copy(update={
                    "confidence": 0.55,
                    "claim_source": "llm_sparse_grounding",
                })
                sparse_elevated += 1
            else:
                # Normal bounded-mode: downgrade to fallback level (below TC-4225 threshold)
                claim = claim.model_copy(update={"confidence": 0.35})
                downgraded += 1

        result.append(claim)

    if rejected_empty or downgraded or sparse_elevated:
        logger.info(
            "evidence_quality_filter [UND-01]: rejected_empty=%d downgraded_irrelevant=%d "
            "sparse_elevated=%d kept=%d (from %d)",
            rejected_empty, downgraded, sparse_elevated, len(result), len(claims),
        )

    return result


def _deduplicate_claims(
    claims: list[Claim],
    drop_log: "list[dict] | None" = None,
) -> list[Claim]:
    """Remove near-duplicate claims using Jaccard similarity on word sets.

    Claims must be pre-sorted by confidence DESC before calling (Phase C fix).
    This ensures the highest-confidence claim in each near-duplicate group survives.
    """
    if not claims:
        return claims

    _MAX_DROP_LOG = 500
    kept: list[Claim] = []
    kept_word_sets: list[set[str]] = []

    for claim in claims:
        words = set(claim.text.lower().split())
        if not words:
            continue

        is_dup = False
        for existing_words in kept_word_sets:
            intersection = words & existing_words
            union = words | existing_words
            if union and len(intersection) / len(union) > _DEDUP_THRESHOLD:
                is_dup = True
                break

        if is_dup:
            if drop_log is not None and len(drop_log) < _MAX_DROP_LOG:
                drop_log.append({
                    "claim_text_prefix": claim.text[:80],
                    "drop_stage": "jaccard_dedup",
                    "drop_reason": f"near-duplicate (Jaccard > {_DEDUP_THRESHOLD})",
                    "confidence_before": claim.confidence,
                    "claim_source": claim.claim_source,
                })
        else:
            kept.append(claim)
            kept_word_sets.append(words)

    return kept
