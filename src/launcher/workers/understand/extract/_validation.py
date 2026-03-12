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

# TC-HAL-06: Confidence values by claim source (evidence strength)
_CONFIDENCE_BY_SOURCE: dict[str, float] = {
    "docstring": 1.0,
    "llm": 0.75,
    "deterministic": 0.5,
    "llm_fallback": 0.35,
}

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


def _references_private_python_api(text: str, product: ProductIdentity) -> bool:
    """Return True when a Python claim references a private underscore API token."""
    return product.platform == "python" and bool(_PRIVATE_PYTHON_API_RE.search(text))


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


def _validate_and_normalize_claims(
    raw_claims: list[dict[str, Any]],
    product: ProductIdentity,
    api_surface: ApiSurface,
    file_tree: "frozenset[str] | None" = None,
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

    # Step 1: Filter internal claims
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
            continue
        if _is_junk_claim(text):
            filtered_junk += 1
            continue
        if _references_private_python_api(text, product):
            filtered_private_api += 1
            continue

        kind = raw.get("kind", "feature")

        # Determine visibility: off-topic claims become internal
        visibility = "public"
        if _is_off_topic(text, product):
            visibility = "internal"

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

    # Step 4: Deduplicate by Jaccard similarity
    deduplicated = _deduplicate_claims(normalized)

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


def _deduplicate_claims(claims: list[Claim]) -> list[Claim]:
    """Remove near-duplicate claims using Jaccard similarity on word sets."""
    if not claims:
        return claims

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

        if not is_dup:
            kept.append(claim)
            kept_word_sets.append(words)

    return kept
