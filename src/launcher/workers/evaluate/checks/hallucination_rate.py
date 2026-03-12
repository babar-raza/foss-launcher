"""Hallucination rate check — TC-HAL-09.

Measures the fraction of page-assigned claims that have low confidence
(confidence < 0.5). High rates indicate the page was generated using
unverified or fallback-sourced claims.
"""
from __future__ import annotations

import logging
from typing import Any

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
