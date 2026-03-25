"""Check: permalink_uniqueness -- cross-page URL collision detection (TC-QG-01)."""
from __future__ import annotations

from launcher.models.evaluation import Finding


def check_permalink_uniqueness(
    pages: list[dict],  # list of {slug, url, section, page_role, page_id}
) -> list[Finding]:
    """Detect duplicate URLs/slugs across pages.

    Returns CRITICAL for exact URL collision.
    Returns HIGH for slug collision across different sections.

    TC-QG-01.
    """
    findings: list[Finding] = []

    # Group by url
    url_groups: dict[str, list[dict]] = {}
    for page in pages:
        url = page.get("url", "")
        if url:
            url_groups.setdefault(url, []).append(page)

    for url, group in url_groups.items():
        if len(group) > 1:
            slugs = [p.get("slug", "?") for p in group]
            findings.append(
                Finding(
                    check="permalink_uniqueness",
                    message=(
                        f"URL collision: {len(group)} pages share URL '{url}': "
                        f"{', '.join(slugs)}"
                    ),
                    severity="critical",
                    location=url,
                )
            )

    # Group by slug across different sections
    slug_groups: dict[str, list[dict]] = {}
    for page in pages:
        slug = page.get("slug", "")
        if slug:
            slug_groups.setdefault(slug, []).append(page)

    for slug, group in slug_groups.items():
        sections = {p.get("section", "") for p in group}
        if len(group) > 1 and len(sections) > 1:
            section_list = sorted(s for s in sections if s)
            findings.append(
                Finding(
                    check="permalink_uniqueness",
                    message=(
                        f"Slug collision across sections: '{slug}' appears in "
                        f"{', '.join(section_list)}"
                    ),
                    severity="high",
                    location=slug,
                )
            )

    return findings
