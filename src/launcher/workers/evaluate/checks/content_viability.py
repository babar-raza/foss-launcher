"""Check: content_viability — detect thin/dump content with no user value (TC-EVAL-502).

Catches pages that are essentially empty skeletons or stub content masquerading
as real documentation.  Severity: HIGH.
"""
from __future__ import annotations

import re

from launcher.models.evaluation import Finding

# Minimum substantive prose words (excluding frontmatter, headings, code blocks)
_MIN_PROSE_WORDS = 50

# Skeleton indicators — phrases that suggest template/placeholder content
_SKELETON_PATTERNS = [
    re.compile(r"\[content\s+to\s+be\s+generated\]", re.IGNORECASE),
    re.compile(r"\[TODO\b", re.IGNORECASE),
    re.compile(r"\[placeholder\]", re.IGNORECASE),
    re.compile(r"lorem\s+ipsum", re.IGNORECASE),
    re.compile(r"__BODY__", re.IGNORECASE),
    re.compile(r"__INTRO__", re.IGNORECASE),
]

_FRONTMATTER_RE = re.compile(r"^---\n.*?\n---\n", re.DOTALL)
_HEADING_RE = re.compile(r"^#{1,6}\s+.*$", re.MULTILINE)
_FENCE_BLOCK_RE = re.compile(r"```[\s\S]*?```", re.MULTILINE)


def _extract_prose(content: str) -> str:
    """Extract prose text (no frontmatter, headings, or code blocks)."""
    text = _FRONTMATTER_RE.sub("", content)
    text = _FENCE_BLOCK_RE.sub("", text)
    text = _HEADING_RE.sub("", text)
    return text.strip()


def check_content_viability(content: str, slug: str) -> list[Finding]:
    """Detect thin or skeleton content that provides no user value."""
    findings: list[Finding] = []

    # Check for skeleton patterns
    for pat in _SKELETON_PATTERNS:
        if pat.search(content):
            findings.append(Finding(
                check="content_viability",
                message=f"Skeleton/placeholder content detected: {pat.pattern}",
                severity="critical",
                location=slug,
            ))

    # Check prose word count
    prose = _extract_prose(content)
    word_count = len(prose.split())
    if word_count < _MIN_PROSE_WORDS:
        findings.append(Finding(
            check="content_viability",
            message=f"Thin content: only {word_count} prose words (minimum {_MIN_PROSE_WORDS})",
            severity="high",
            location=slug,
        ))

    return findings
