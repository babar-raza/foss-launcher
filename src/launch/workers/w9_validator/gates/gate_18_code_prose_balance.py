"""Gate 18: Code-Prose Balance Check.

For page roles that must include code examples (tutorial, feature_showcase,
comprehensive_guide, api_reference), verifies that there is at least one code
block per 400 words of body prose.  Pages that fail receive a warn-level G18-001
issue.  The gate always passes (warn-only — no blocker/error severity).

RCA context: Gates previously did not check whether code-heavy page types actually
contain code.  A tutorial page could pass all gates with zero code examples.

TC-2371: Gate 18 Code-Prose Balance (RCA Part 4-E)

Per specs/09_validation_gates.md.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List


# Roles where code examples are required
CODE_REQUIRED_ROLES = frozenset({
    "tutorial",
    "feature_showcase",
    "comprehensive_guide",
    "api_reference",
})

# One code block required per this many prose words
WORDS_PER_CODE_BLOCK = 400


def run_gate_18(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Execute Gate 18: Code-Prose Balance Check.

    For each page whose role requires code examples, counts the number of fenced
    code blocks and the number of prose words.  If the ratio is insufficient
    (fewer than 1 block per 400 prose words, minimum 1 block required), a
    warn-level G18-001 issue is emitted.

    Args:
        pages: List of page dicts with keys ``path``, ``content``, ``page_role``.
               This is the same list built for Gate 16 in worker.py.

    Returns:
        List of issue dicts (severity ``warn`` only — gate always passes).
    """
    issues: List[Dict[str, Any]] = []

    for page in pages:
        role = page.get("page_role", "")
        if role not in CODE_REQUIRED_ROLES:
            continue

        content = page.get("content", "")
        path = page.get("path", "")

        body = _strip_frontmatter(content)

        # Count fenced code blocks: opening ``` lines.
        # Divide by 2 (open + close fence = 1 block).
        fence_openers = sum(
            1 for line in body.splitlines()
            if line.strip().startswith("```")
        )
        actual_blocks = fence_openers // 2

        # Count prose words (body with code blocks stripped)
        body_no_code = _strip_code_blocks(body)
        word_count = len(body_no_code.split())

        required_blocks = max(1, word_count // WORDS_PER_CODE_BLOCK)

        if actual_blocks < required_blocks:
            issues.append({
                "issue_id": f"gate18_code_prose_{_slug(path)}",
                "gate": "gate_18_code_prose_balance",
                "severity": "warn",
                "message": (
                    f"Code-prose balance: {actual_blocks} code block(s) for "
                    f"{word_count} prose words "
                    f"(≥{required_blocks} expected for {role!r})"
                ),
                "error_code": "G18-001",
                "location": {"path": path, "line": 1},
                "status": "OPEN",
            })

    return issues


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _strip_frontmatter(content: str) -> str:
    """Remove YAML frontmatter (--- ... ---) from the top of content."""
    if not content.startswith("---"):
        return content
    end = content.find("\n---", 3)
    if end == -1:
        return content
    return content[end + 4:]


def _strip_code_blocks(content: str) -> str:
    """Replace fenced code block lines with blank lines to preserve line count."""
    lines = content.split("\n")
    result: List[str] = []
    in_block = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_block = not in_block
            result.append("")
        elif in_block:
            result.append("")
        else:
            result.append(line)
    return "\n".join(result)


def _slug(path: str) -> str:
    """Derive a short deterministic slug from a file path."""
    import os
    stem = os.path.splitext(os.path.basename(path))[0]
    return re.sub(r"[^a-zA-Z0-9_-]", "_", stem)[:40]
