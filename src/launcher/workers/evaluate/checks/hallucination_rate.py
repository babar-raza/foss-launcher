"""Hallucination rate check — TC-HAL-09.

Measures the fraction of page-assigned claims that have low confidence
(confidence < 0.5). High rates indicate the page was generated using
unverified or fallback-sourced claims.
"""
from __future__ import annotations

import logging
import re
from typing import Any

from launcher.models.evaluation import Finding

logger = logging.getLogger(__name__)

_HALLUCINATION_THRESHOLD = 0.05   # 5% max
_HIGH_THRESHOLD = 0.10             # 10% = CRITICAL
_CONFIDENCE_GATE = 0.5             # below this = low confidence


def check_hallucination_rate(
    claim_ids_used: "list[str]",
    claims_by_id: "dict[str, Any]",
) -> "tuple[list[dict[str, Any]], float]":
    """Check hallucination rate for a page.

    Args:
        claim_ids_used: List of claim IDs assigned to this page.
        claims_by_id: Mapping from claim_id to Claim object.

    Returns:
        (findings_dicts, hallucination_rate)
        findings_dicts use the same format as other deterministic checks.
    """
    if not claim_ids_used:
        return [], 0.0

    low_confidence_ids = [
        cid for cid in claim_ids_used
        if getattr(claims_by_id.get(cid), 'confidence', 1.0) < _CONFIDENCE_GATE
    ]

    rate = len(low_confidence_ids) / len(claim_ids_used)

    findings = []
    if rate > _HALLUCINATION_THRESHOLD:
        severity = "critical" if rate > _HIGH_THRESHOLD else "high"
        findings.append({
            "check": "hallucination_rate",
            "message": (
                f"Hallucination rate {rate:.1%} exceeds {_HALLUCINATION_THRESHOLD:.0%} threshold. "
                f"{len(low_confidence_ids)}/{len(claim_ids_used)} claims have "
                f"confidence < {_CONFIDENCE_GATE}."
            ),
            "severity": severity,
            "location": "claims",
        })
        logger.warning(
            "hallucination_rate [TC-HAL-09]: FAIL rate=%.3f low_conf=%d total=%d",
            rate, len(low_confidence_ids), len(claim_ids_used),
        )
    else:
        logger.debug("hallucination_rate [TC-HAL-09]: PASS rate=%.3f", rate)

    return findings, rate


# ---------------------------------------------------------------------------
# Content grounding & claim authenticity checks (TC-5154 / TC-5131)
# ---------------------------------------------------------------------------

_STOPWORDS = frozenset(
    "the and or of to in for on with at by from is it its a an as be was "
    "were are been has have had do does did this that these those will can "
    "may could should would not no but if so all each every some any such "
    "use using used only also than then into library".split()
)

_TRIGGER_VERBS = {"supports", "provides", "enables", "offers"}

_GROUNDING_THRESHOLD = 0.30  # >30% ungrounded → HIGH
_GROUNDING_MIN_TERMS = 2
_MAX_MEDIUM_FINDINGS = 5
_AUTHENTICITY_CONFIDENCE_GATE = 0.75


def _strip_frontmatter(text: str) -> str:
    """Remove YAML frontmatter delimited by --- lines."""
    return re.sub(r"^---\n.*?\n---\n?", "", text, flags=re.DOTALL)


def _strip_code_blocks(text: str) -> str:
    """Remove fenced code blocks."""
    return re.sub(r"```[^\n]*\n.*?```", "", text, flags=re.DOTALL)


def _meaningful_tokens(text: str) -> list[str]:
    """Extract lowercase tokens that are not stopwords and len >= 4."""
    return [
        t for t in re.findall(r"[a-zA-Z]+", text.lower())
        if len(t) >= 4 and t not in _STOPWORDS
    ]


def _top_tokens(text: str, n: int = 5) -> list[str]:
    """Return up to *n* longest unique meaningful tokens from *text*."""
    if not text:
        return []
    tokens = _meaningful_tokens(text)
    # Deduplicate while preserving order by length (longest first)
    seen: set[str] = set()
    unique: list[str] = []
    for t in sorted(tokens, key=len, reverse=True):
        if t not in seen:
            seen.add(t)
            unique.append(t)
    return unique[:n]


def _extract_assertions(prose: str) -> list[str]:
    """Extract sentences containing trigger verbs from prose."""
    sentences = re.split(r"(?<=[.!?])\s+", prose)
    results: list[str] = []
    for s in sentences:
        s_lower = s.lower()
        if any(v in s_lower for v in _TRIGGER_VERBS):
            results.append(s)
    return results


def _is_grounded(assertion: str, claim_texts: list[str]) -> bool:
    """Check if assertion terms overlap sufficiently with any claim."""
    # Exclude trigger verbs from assertion tokens — they are structural, not content
    a_tokens = [t for t in _meaningful_tokens(assertion) if t not in _TRIGGER_VERBS]
    if not a_tokens:
        return True  # No meaningful terms → skip (treat as grounded)
    required = min(_GROUNDING_MIN_TERMS, len(a_tokens))

    for claim in claim_texts:
        c_tokens = set(_meaningful_tokens(claim))
        matches = sum(1 for t in a_tokens if t in c_tokens)
        if matches >= required:
            return True
    return False


def check_content_grounding(
    content: str,
    claim_texts: list[str],
    *,
    slug: str = "",
) -> list[Finding]:
    """Check that prose assertions are grounded in assigned claims."""
    if not content or not claim_texts:
        return []

    prose = _strip_code_blocks(_strip_frontmatter(content))
    assertions = _extract_assertions(prose)
    if not assertions:
        return []

    ungrounded: list[str] = []
    for a in assertions:
        # Skip assertions with no meaningful non-trigger tokens
        content_tokens = [t for t in _meaningful_tokens(a) if t not in _TRIGGER_VERBS]
        if not content_tokens:
            continue
        if not _is_grounded(a, claim_texts):
            ungrounded.append(a)

    if not ungrounded:
        return []

    total_meaningful = sum(
        1 for a in assertions
        if [t for t in _meaningful_tokens(a) if t not in _TRIGGER_VERBS]
    )
    rate = len(ungrounded) / total_meaningful if total_meaningful else 0.0

    if rate > _GROUNDING_THRESHOLD:
        return [
            Finding(
                check="content_grounding",
                message=(
                    f"{len(ungrounded)}/{total_meaningful} prose assertions "
                    f"({rate:.0%}) lack grounding in assigned claims"
                ),
                severity="high",
                location=slug,
            )
        ]

    # MEDIUM findings, capped
    findings: list[Finding] = []
    for a in ungrounded[:_MAX_MEDIUM_FINDINGS]:
        findings.append(
            Finding(
                check="content_grounding",
                message=f"Ungrounded assertion: {a[:120]}",
                severity="medium",
                location=slug,
            )
        )
    return findings


def check_claim_authenticity(
    claim_ids_used: list[str],
    claims_by_id: dict,
    content: str,
    *,
    slug: str = "",
) -> list[Finding]:
    """Check that high-confidence claims are reflected in page prose."""
    if not claim_ids_used or not claims_by_id or not content:
        return []

    prose = _strip_code_blocks(_strip_frontmatter(content)).lower()

    findings: list[Finding] = []
    for cid in claim_ids_used:
        claim = claims_by_id.get(cid)
        if claim is None:
            continue
        confidence = getattr(claim, "confidence", 1.0)
        if confidence < _AUTHENTICITY_CONFIDENCE_GATE:
            continue

        text = getattr(claim, "text", "")
        tokens = _top_tokens(text)
        if not tokens:
            continue

        # Check if at least one key token appears in prose
        if not any(t in prose for t in tokens):
            findings.append(
                Finding(
                    check="claim_authenticity",
                    message=f"Claim {cid} key terms absent from page prose",
                    severity="medium",
                    location=slug,
                )
            )

    return findings
