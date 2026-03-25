"""Check: content_utility — detect copy-paste filler patterns (TC-D-04).

Flags pages where ≥3 consecutive lines start with the same filler phrase.
Common patterns: "The library supports X format", "This provides X",
"Aspose.X allows you to". These are symptoms of round-robin claim injection
producing mechanical, template-like prose.
"""
from __future__ import annotations

import re

from launcher.models.evaluation import Finding

_CODE_FENCE_RE = re.compile(r"```[\s\S]*?```", re.DOTALL)

# Filler phrase prefixes to detect (case-insensitive)
_FILLER_PREFIXES: list[str] = [
    "the library supports",
    "the library provides",
    "the library allows",
    "this library supports",
    "this library provides",
    "this provides",
    "this supports",
    "this allows you to",
    "you can use",
    "it supports",
    "it provides",
    "it allows",
]

# Minimum consecutive lines with same prefix to trigger
_MIN_CONSECUTIVE = 3


def check_content_utility(
    content: str,
    slug: str,
) -> list[Finding]:
    """Detect copy-paste filler patterns in content.

    Args:
        content: Rendered markdown content.
        slug: Page slug for Finding location.

    Returns:
        List of MEDIUM Findings for filler patterns detected.
    """
    normalised = content.replace("\r\n", "\n").replace("\r", "\n")
    body = re.sub(r"^---\n.*?\n---\n?", "", normalised, flags=re.DOTALL)

    # Remove code blocks — filler in code is a different problem
    body_no_code = _CODE_FENCE_RE.sub("", body)

    lines = body_no_code.split("\n")

    findings: list[Finding] = []

    # Check for consecutive lines matching filler prefixes
    for prefix in _FILLER_PREFIXES:
        consecutive = 0
        max_consecutive = 0
        for line in lines:
            stripped = line.strip().lower()
            if stripped.startswith(prefix):
                consecutive += 1
                max_consecutive = max(max_consecutive, consecutive)
            else:
                consecutive = 0

        if max_consecutive >= _MIN_CONSECUTIVE:
            findings.append(Finding(
                check="content_utility",
                message=(
                    f"Copy-paste filler: {max_consecutive} consecutive lines "
                    f"start with '{prefix}' — content should be specific, "
                    f"not repetitive template text"
                ),
                severity="medium",
                location=slug,
            ))

    # Also check for generic repetitive bullet patterns
    # (e.g., "- Supports X\n- Supports Y\n- Supports Z\n- Supports W")
    bullet_consecutive = 0
    max_bullet_run = 0
    last_bullet_prefix = ""
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(("- ", "* ")):
            # Get first 2 words after bullet
            words = stripped[2:].strip().split()[:2]
            prefix_str = " ".join(words).lower()
            if prefix_str == last_bullet_prefix and prefix_str:
                bullet_consecutive += 1
                max_bullet_run = max(max_bullet_run, bullet_consecutive)
            else:
                bullet_consecutive = 1
                last_bullet_prefix = prefix_str
        else:
            bullet_consecutive = 0
            last_bullet_prefix = ""

    if max_bullet_run >= 4:
        findings.append(Finding(
            check="content_utility",
            message=(
                f"Repetitive bullet list: {max_bullet_run} consecutive bullets "
                f"share the same prefix — vary sentence structure"
            ),
            severity="medium",
            location=slug,
        ))

    return findings
