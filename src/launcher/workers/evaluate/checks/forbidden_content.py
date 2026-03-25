"""Check: forbidden_content — detect pipeline-internal strings in published content (TC-5152).

Uses the shared ``forbidden_patterns`` registry to scan rendered markdown for
patterns that must never appear in published pages.  Each detected pattern
produces a Finding at the severity defined in the registry.

This check is a superset of ``placeholder_content`` (TC-4305) — it covers
all patterns from that check plus additional categories (claim IDs,
template placeholders, placeholder URLs/links).
"""
from __future__ import annotations

import logging

from launcher.models.evaluation import Finding
from launcher.shared.forbidden_patterns import scan_forbidden

logger = logging.getLogger(__name__)


def check_forbidden_content(content: str, slug: str) -> list[Finding]:
    """Scan rendered markdown for forbidden pipeline artifacts.

    Args:
        content: Rendered markdown content.
        slug: Page slug for Finding location.

    Returns:
        List of Findings, one per distinct forbidden pattern type detected.
    """
    findings: list[Finding] = []

    for category, severity, description, count in scan_forbidden(content):
        logger.debug(
            "forbidden_content: found %d occurrence(s) of '%s' in slug=%s",
            count, category, slug,
        )
        findings.append(Finding(
            check="forbidden_content",
            message=f"{description} ({count} occurrence{'s' if count != 1 else ''})",
            severity=severity,
            location=slug,
        ))

    return findings
