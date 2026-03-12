"""Slug safety check for the evaluation pipeline.

Ported from v1 Gate 19 -- detects malformed slugs that would produce
broken URLs or SEO-harmful paths.

TC-3780: Created for v2.
"""

from __future__ import annotations

from typing import Any

from launcher.shared.slug_engine import validate_slug_safety


def check_slug_safety(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Run slug safety validation across all pages.

    Returns list of findings (empty = all slugs safe).
    """
    findings: list[dict[str, Any]] = []
    for page in pages:
        slug = page.get("frontmatter", {}).get("slug", "") or page.get("slug", "")
        if not slug:
            continue
        issues = validate_slug_safety(slug)
        for issue in issues:
            findings.append({
                "category": "slug_safety",
                "page_id": page.get("page_id", ""),
                "slug": slug,
                "message": issue,
                "severity": "high",
            })
    return findings
