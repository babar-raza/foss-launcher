"""Check: explanation_gap — detect code blocks without surrounding context (TC-PROSE-01).

Flags code blocks that appear with insufficient prose explanation before AND after
them. Code should be introduced (what it does) and followed up (what result to expect).
"""
from __future__ import annotations

import re

from launcher.models.evaluation import Finding

_FRONTMATTER_RE = re.compile(r"^---\n.*?\n---\n?", re.DOTALL)
_CODE_FENCE_RE = re.compile(r"(```[^\n]*\n[\s\S]*?```)", re.DOTALL)

# Roles where code-first is acceptable.
_LOW_SEVERITY_ROLES: frozenset[str] = frozenset({
    "api_reference", "reference_object_page", "toc",
})

# Minimum prose words expected around a code block.
_MIN_CONTEXT_WORDS = 12


def _word_count(text: str) -> int:
    """Count non-trivial words in text."""
    cleaned = re.sub(r"`[^`]+`", "", text)  # strip inline code
    cleaned = re.sub(r"^#{1,6}\s+", "", cleaned, flags=re.MULTILINE)  # strip headings
    cleaned = re.sub(r"^\s*[-*]\s+", "", cleaned, flags=re.MULTILINE)  # strip bullets
    words = cleaned.split()
    return len([w for w in words if len(w) > 1])


def check_explanation_gap(
    content: str,
    slug: str,
    *,
    page_role: str = "",
) -> list[Finding]:
    """Detect code blocks with insufficient surrounding prose context.

    Args:
        content: Rendered markdown content.
        slug: Page slug for Finding location.
        page_role: Page role (affects severity).

    Returns:
        List of Findings for unexplained code blocks.
    """
    body = _FRONTMATTER_RE.sub("", content)

    # Split content into alternating [text, code, text, code, ...] segments
    parts = _CODE_FENCE_RE.split(body)

    if len(parts) < 3:
        # No code blocks or only one segment
        return []

    severity = "low" if page_role in _LOW_SEVERITY_ROLES else "medium"
    findings: list[Finding] = []
    code_idx = 0

    for i, part in enumerate(parts):
        if not part.startswith("```"):
            continue

        code_idx += 1

        # Get prose before this code block
        before_text = parts[i - 1] if i > 0 else ""
        # Take last 3 lines of the before-text
        before_lines = before_text.strip().split("\n")
        before_context = "\n".join(before_lines[-3:]) if before_lines else ""
        before_words = _word_count(before_context)

        # Get prose after this code block
        after_text = parts[i + 1] if i + 1 < len(parts) else ""
        # Take first 3 lines of the after-text
        after_lines = after_text.strip().split("\n")
        after_context = "\n".join(after_lines[:3]) if after_lines else ""
        after_words = _word_count(after_context)

        if before_words < _MIN_CONTEXT_WORDS and after_words < _MIN_CONTEXT_WORDS:
            findings.append(Finding(
                check="explanation_gap",
                message=(
                    f"Code block #{code_idx} has insufficient context: "
                    f"{before_words} words before, {after_words} words after "
                    f"(need >= {_MIN_CONTEXT_WORDS} in at least one). "
                    f"Explain what the code does and what result to expect"
                ),
                severity=severity,
                location=slug,
            ))

    return findings
