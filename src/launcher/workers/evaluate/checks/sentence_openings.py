"""Check: sentence_openings — detect repetitive sentence opening patterns (TC-PROSE-01).

Flags runs of 3+ consecutive sentences that start with the same 2-word pattern
(e.g. "You can", "The library", "This method"). This mechanical repetition is
a hallmark of generated prose.
"""
from __future__ import annotations

import re

from launcher.models.evaluation import Finding

_CODE_FENCE_RE = re.compile(r"```[\s\S]*?```", re.DOTALL)
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")

_EXEMPT_ROLES: frozenset[str] = frozenset({
    "api_reference", "reference_object_page",
})

# Minimum run of same-opening sentences to flag.
_MIN_RUN = 3


def _extract_opening(sentence: str) -> str:
    """Extract the first 2 words of a sentence as a lowercase key."""
    words = sentence.strip().split()[:2]
    return " ".join(w.lower().strip("*`") for w in words)


def check_sentence_openings(
    content: str,
    slug: str,
    *,
    page_role: str = "",
) -> list[Finding]:
    """Detect repetitive sentence opening patterns.

    Args:
        content: Rendered markdown content.
        slug: Page slug for Finding location.
        page_role: Page role (reference roles are exempt).

    Returns:
        List of MEDIUM Findings for detected repetition.
    """
    if page_role in _EXEMPT_ROLES:
        return []

    # Strip frontmatter and code blocks
    body = re.sub(r"^---\n.*?\n---\n?", "", content, flags=re.DOTALL)
    body = _CODE_FENCE_RE.sub("", body)
    # Strip headings
    body = re.sub(r"^#{1,6}\s+.+$", "", body, flags=re.MULTILINE)
    # Strip list items (they naturally start with same patterns)
    body = re.sub(r"^\s*[-*]\s+", "", body, flags=re.MULTILINE)
    # Strip inline code for cleaner word extraction
    body = re.sub(r"`[^`]+`", "CODE", body)

    sentences = _SENTENCE_SPLIT.split(body)
    sentences = [s.strip() for s in sentences if len(s.strip().split()) >= 4]

    if len(sentences) < _MIN_RUN:
        return []

    findings: list[Finding] = []
    openings = [_extract_opening(s) for s in sentences]

    # Scan for runs of _MIN_RUN+ consecutive same openings
    run_start = 0
    while run_start < len(openings):
        run_len = 1
        while (
            run_start + run_len < len(openings)
            and openings[run_start + run_len] == openings[run_start]
            and openings[run_start]  # skip empty openings
        ):
            run_len += 1

        if run_len >= _MIN_RUN:
            pattern = openings[run_start]
            sample = sentences[run_start][:60]
            findings.append(Finding(
                check="sentence_openings",
                message=(
                    f"{run_len} consecutive sentences start with \"{pattern}\" "
                    f"(e.g. \"{sample}...\") — vary sentence openings"
                ),
                severity="low",
                location=slug,
            ))

        run_start += max(run_len, 1)

    return findings
