"""Check: link_validity — detect broken and placeholder links (TC-D-04).

Flags pages containing links to example.com, placeholder URLs (link-to-*),
empty href targets, or docs.example.com patterns. These are symptoms of
LLM-generated placeholder links that were not replaced by engineering.
"""
from __future__ import annotations

import re

from launcher.models.evaluation import Finding

_CODE_FENCE_RE = re.compile(r"```[\s\S]*?```", re.DOTALL)

# Markdown link pattern: [text](url)
_MD_LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]*)\)")

# Patterns that indicate broken/placeholder links
_BROKEN_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"example\.com", re.IGNORECASE), "example.com placeholder"),
    (re.compile(r"link-to-", re.IGNORECASE), "link-to-* placeholder"),
    (re.compile(r"placeholder", re.IGNORECASE), "placeholder URL"),
    (re.compile(r"your-.*-here", re.IGNORECASE), "your-*-here placeholder"),
    (re.compile(r"TODO", re.IGNORECASE), "TODO in URL"),
    (re.compile(r"^#?$"), "empty URL"),
    # TC-LINK-01: Subdomain prefix in URL path — should be site-relative.
    (re.compile(r"^/(?:docs|kb|products|reference|blog)\.aspose\.org/"), "subdomain prefix in URL path"),
]


def check_link_validity(
    content: str,
    slug: str,
) -> list[Finding]:
    """Detect broken and placeholder links in content.

    Args:
        content: Rendered markdown content.
        slug: Page slug for Finding location.

    Returns:
        List of HIGH Findings for broken/placeholder links.
    """
    normalised = content.replace("\r\n", "\n").replace("\r", "\n")
    body = re.sub(r"^---\n.*?\n---\n?", "", normalised, flags=re.DOTALL)

    # Remove code blocks — links in code examples are not the same issue
    body_no_code = _CODE_FENCE_RE.sub("", body)

    findings: list[Finding] = []
    broken_count = 0

    for m in _MD_LINK_RE.finditer(body_no_code):
        link_text = m.group(1)
        url = m.group(2).strip()

        for pattern, description in _BROKEN_PATTERNS:
            if pattern.search(url):
                broken_count += 1
                if broken_count <= 3:  # Cap individual reports
                    findings.append(Finding(
                        check="link_validity",
                        message=(
                            f"Broken link: [{link_text[:40]}]({url[:60]}) — "
                            f"{description}"
                        ),
                        severity="high",
                        location=slug,
                    ))
                break

    if broken_count > 3:
        findings.append(Finding(
            check="link_validity",
            message=(
                f"{broken_count} broken/placeholder links found in total — "
                f"all links must point to real URLs"
            ),
            severity="high",
            location=slug,
        ))

    return findings
