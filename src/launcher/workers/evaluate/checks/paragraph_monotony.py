"""Check: paragraph_monotony — detect runs of same-length short paragraphs (TC-PROSE-01).

Flags 4+ consecutive paragraphs that are each 1-2 sentences long (10-40 words each).
This catches the "list of facts without narrative flow" pattern common in generated prose.
"""
from __future__ import annotations

import re

from launcher.models.evaluation import Finding

_CODE_FENCE_RE = re.compile(r"```[\s\S]*?```", re.DOTALL)
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")

# A paragraph is "short" if it has this many words or fewer.
_SHORT_PARAGRAPH_MAX_WORDS = 40
_SHORT_PARAGRAPH_MIN_WORDS = 8  # below this is likely a fragment, not a paragraph

# Minimum consecutive short paragraphs to flag.
_MIN_RUN = 4


def check_paragraph_monotony(
    content: str,
    slug: str,
) -> list[Finding]:
    """Detect runs of same-length short paragraphs.

    Args:
        content: Rendered markdown content.
        slug: Page slug for Finding location.

    Returns:
        List of LOW Findings for detected monotony patterns.
    """
    # Strip frontmatter and code blocks
    body = re.sub(r"^---\n.*?\n---\n?", "", content, flags=re.DOTALL)
    body = _CODE_FENCE_RE.sub("\n\n", body)

    # Split into paragraphs by blank lines
    raw_paragraphs = re.split(r"\n\s*\n", body)

    # Filter to actual prose paragraphs (skip headings, list items, tables)
    paragraphs: list[str] = []
    for para in raw_paragraphs:
        stripped = para.strip()
        if not stripped:
            continue
        # Skip headings
        if stripped.startswith("#"):
            continue
        # Skip tables
        if stripped.startswith("|"):
            continue
        # Skip shortcodes
        if stripped.startswith("{{"):
            continue
        # Skip list-only paragraphs
        lines = stripped.split("\n")
        if all(l.strip().startswith(("- ", "* ", "1.", "2.", "3.")) for l in lines if l.strip()):
            continue
        paragraphs.append(stripped)

    if len(paragraphs) < _MIN_RUN:
        return []

    findings: list[Finding] = []

    # Check for runs of short paragraphs
    run_start = 0
    while run_start < len(paragraphs):
        word_count = len(paragraphs[run_start].split())
        is_short = _SHORT_PARAGRAPH_MIN_WORDS <= word_count <= _SHORT_PARAGRAPH_MAX_WORDS

        if not is_short:
            run_start += 1
            continue

        run_len = 1
        while run_start + run_len < len(paragraphs):
            wc = len(paragraphs[run_start + run_len].split())
            if _SHORT_PARAGRAPH_MIN_WORDS <= wc <= _SHORT_PARAGRAPH_MAX_WORDS:
                run_len += 1
            else:
                break

        if run_len >= _MIN_RUN:
            findings.append(Finding(
                check="paragraph_monotony",
                message=(
                    f"{run_len} consecutive short paragraphs (each 1-2 sentences) — "
                    f"vary paragraph length or combine related ideas into fuller paragraphs"
                ),
                severity="low",
                location=slug,
            ))

        run_start += max(run_len, 1)

    return findings
