"""Check: prose_lead — detect generic/weak section opening sentences (TC-PROSE-01).

Flags sections that open with formulaic patterns like:
- "{Product} is a library that..."
- "In this section..."
- "When working with..."
- "You can use..."

These patterns produce dull, mechanical prose that fails to engage the reader.
"""
from __future__ import annotations

import re

from launcher.models.evaluation import Finding

_CODE_FENCE_RE = re.compile(r"```[\s\S]*?```", re.DOTALL)

# Roles where terse openings are acceptable (API reference pages).
_EXEMPT_ROLES: frozenset[str] = frozenset({
    "api_reference", "reference_object_page", "toc",
})

# Generic opener patterns (case-insensitive). Tested against the first
# paragraph of prose following each ## heading.
_GENERIC_OPENERS: list[re.Pattern[str]] = [
    # "{Product} is a library/tool/package/SDK/framework that..."
    re.compile(
        r"^.{0,60}\bis\s+a\s+(?:library|tool|package|sdk|framework|module)\s+(?:that|which|for)\b",
        re.IGNORECASE,
    ),
    # "In this section we will / you will / we..."
    re.compile(r"^in\s+this\s+section\b", re.IGNORECASE),
    # "When working with..."
    re.compile(r"^when\s+working\s+with\b", re.IGNORECASE),
    # "This section covers / provides / describes..."
    re.compile(
        r"^this\s+section\s+(?:covers|provides|describes|explains|shows|demonstrates)\b",
        re.IGNORECASE,
    ),
]


def check_prose_lead(
    content: str,
    slug: str,
    *,
    page_role: str = "",
    product_name: str = "",
) -> list[Finding]:
    """Detect generic/weak opening sentences in sections.

    Args:
        content: Rendered markdown content.
        slug: Page slug for Finding location.
        page_role: Page role (reference roles are exempt).
        product_name: Product display name (unused in current patterns but
            available for future product-specific pattern matching).

    Returns:
        List of MEDIUM Findings for generic lead sentences detected.
    """
    if page_role in _EXEMPT_ROLES:
        return []

    # Strip frontmatter and code blocks
    body = re.sub(r"^---\n.*?\n---\n?", "", content, flags=re.DOTALL)
    body = _CODE_FENCE_RE.sub("", body)

    findings: list[Finding] = []

    # Split into sections by ## heading
    sections = re.split(r"^(#{2}\s+.+)$", body, flags=re.MULTILINE)

    # sections is [preamble, heading1, content1, heading2, content2, ...]
    i = 1
    while i < len(sections) - 1:
        heading = sections[i].strip().lstrip("#").strip()
        section_body = sections[i + 1]

        # Get first non-empty paragraph (skip blank lines and sub-headings)
        lines = section_body.strip().split("\n")
        first_para = ""
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("#"):
                continue
            if stripped.startswith(("- ", "* ", "| ")):
                continue
            first_para = stripped
            break

        if first_para:
            for pattern in _GENERIC_OPENERS:
                if pattern.search(first_para):
                    findings.append(Finding(
                        check="prose_lead",
                        message=(
                            f"Generic opening in section \"{heading}\": "
                            f"\"{first_para[:80]}...\" — lead with the reader's "
                            f"task or problem instead"
                        ),
                        severity="low",
                        location=slug,
                        section_id=heading,
                    ))
                    break  # one finding per section

        i += 2

    return findings
