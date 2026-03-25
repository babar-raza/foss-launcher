"""Check: heading_echo — detect paragraphs that merely restate the heading (TC-PROSE-01).

Flags sections where the first paragraph is just a paraphrase of the heading
with no additional information. This is a common generated-prose anti-pattern.
"""
from __future__ import annotations

import re

from launcher.models.evaluation import Finding

_CODE_FENCE_RE = re.compile(r"```[\s\S]*?```", re.DOTALL)

# Maximum word count for a paragraph to be considered a potential echo.
_MAX_ECHO_WORDS = 25

# Minimum Jaccard similarity between heading tokens and paragraph tokens
# to consider it an echo.
_JACCARD_THRESHOLD = 0.55


def _tokenize(text: str) -> set[str]:
    """Extract lowercase word tokens, stripping backticks and punctuation."""
    cleaned = re.sub(r"`[^`]+`", "", text)
    cleaned = re.sub(r"[^\w\s]", " ", cleaned)
    return {w.lower() for w in cleaned.split() if len(w) > 2}


def _jaccard(a: set[str], b: set[str]) -> float:
    """Jaccard similarity between two token sets."""
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def check_heading_echo(
    content: str,
    slug: str,
) -> list[Finding]:
    """Detect paragraphs that merely restate their heading.

    Args:
        content: Rendered markdown content.
        slug: Page slug for Finding location.

    Returns:
        List of MEDIUM Findings for heading echo patterns.
    """
    # Strip frontmatter and code blocks
    body = re.sub(r"^---\n.*?\n---\n?", "", content, flags=re.DOTALL)
    body = _CODE_FENCE_RE.sub("", body)

    findings: list[Finding] = []

    # Split into sections by ## heading
    sections = re.split(r"^(#{2,3}\s+.+)$", body, flags=re.MULTILINE)

    # sections is [preamble, heading1, content1, heading2, content2, ...]
    i = 1
    while i < len(sections) - 1:
        heading_raw = sections[i].strip()
        heading_text = re.sub(r"^#{2,3}\s+", "", heading_raw).strip()
        section_body = sections[i + 1]

        # Get first non-empty prose paragraph
        paragraphs = re.split(r"\n\s*\n", section_body.strip())
        first_para = ""
        for para in paragraphs:
            stripped = para.strip()
            if not stripped:
                continue
            if stripped.startswith(("#", "|", "```", "{{", "- ", "* ")):
                continue
            first_para = stripped
            break

        if first_para:
            para_words = len(first_para.split())
            if para_words <= _MAX_ECHO_WORDS:
                heading_tokens = _tokenize(heading_text)
                para_tokens = _tokenize(first_para)
                similarity = _jaccard(heading_tokens, para_tokens)

                if similarity >= _JACCARD_THRESHOLD:
                    findings.append(Finding(
                        check="heading_echo",
                        message=(
                            f"Section \"{heading_text}\" opening paragraph restates "
                            f"the heading (similarity={similarity:.2f}): "
                            f"\"{first_para[:80]}...\" — add information beyond the heading"
                        ),
                        severity="medium",
                        location=slug,
                        section_id=heading_text,
                    ))

        i += 2

    return findings
