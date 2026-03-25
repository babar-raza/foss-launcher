"""Shared registry of patterns that must never appear in published content.

TC-5152: Centralises forbidden-pattern detection and stripping so that both
the IR renderer (strip pass) and the evaluator (forbidden_content check)
operate from a single source of truth.

Each entry is a ``ForbiddenPattern`` with:
- ``regex``: compiled regex
- ``category``: human-readable classification
- ``severity``: evaluator severity if the pattern survives to final content
- ``description``: short message for Finding output
"""
from __future__ import annotations

import re
from typing import NamedTuple


class ForbiddenPattern(NamedTuple):
    """A pattern that must never appear in published content."""

    regex: re.Pattern[str]
    category: str
    severity: str
    description: str


# ---------------------------------------------------------------------------
# Pattern registry
# ---------------------------------------------------------------------------
# NOTE: Order does not matter — all patterns are checked independently.

FORBIDDEN_PATTERNS: list[ForbiddenPattern] = [
    # Pipeline artifact: hallucinated identifier stripped by _identifier_repair.py
    ForbiddenPattern(
        regex=re.compile(r"\[identifier omitted\]", re.IGNORECASE),
        category="hallucinated_identifier",
        severity="critical",
        description="Identifier repair artifact: hallucinated API identifier was stripped",
    ),
    # Internal metadata: snippet traceability comment leaked into output
    ForbiddenPattern(
        regex=re.compile(r"#\s*source:\s*snippet_\d+"),
        category="internal_metadata",
        severity="high",
        description="Internal traceability comment leaked into published content",
    ),
    # Claim ID leak: bare CLM-family-hash prefix in prose
    ForbiddenPattern(
        regex=re.compile(r"CLM-[a-z]+-[a-f0-9]+:"),
        category="claim_id_leak",
        severity="critical",
        description="Internal claim ID leaked into published content",
    ),
    # Claim citation bracket leak: [CLM-...] references
    ForbiddenPattern(
        regex=re.compile(r"\[CLM-[^\]]*\]"),
        category="claim_id_leak",
        severity="critical",
        description="Internal claim citation leaked into published content",
    ),
    # Template placeholder: content generation marker
    ForbiddenPattern(
        regex=re.compile(r"\[Content to be generated\]", re.IGNORECASE),
        category="template_placeholder",
        severity="critical",
        description="Template placeholder was not replaced during generation",
    ),
    # Template placeholder: instructional length hint
    ForbiddenPattern(
        regex=re.compile(r"\b\d+-\d+\s+sentences\b"),
        category="template_placeholder",
        severity="high",
        description="Template length instruction leaked into published content",
    ),
    # Placeholder URL: example.com domain
    ForbiddenPattern(
        regex=re.compile(r"docs\.example\.com"),
        category="placeholder_url",
        severity="high",
        description="Placeholder URL (docs.example.com) in published content",
    ),
    # Placeholder link: (link-to-...) pattern
    ForbiddenPattern(
        regex=re.compile(r"\(link-to-[a-z-]+\)"),
        category="placeholder_link",
        severity="high",
        description="Placeholder link reference in published content",
    ),
    # LLM reasoning leak: confidence percentage in prose (TC-5154 SR-05)
    ForbiddenPattern(
        regex=re.compile(r"\b\d+%\s*confidence\b", re.IGNORECASE),
        category="llm_reasoning_leak",
        severity="high",
        description="LLM reasoning artifact (confidence percentage) in published content",
    ),
    # Template placeholder: generic section opener from skeleton (TC-5154 SR-05)
    ForbiddenPattern(
        regex=re.compile(r"\bWhat this library provides\b", re.IGNORECASE),
        category="template_placeholder",
        severity="high",
        description="Template section header leaked into published content",
    ),
    # TC-QG-01: Section ID leak
    ForbiddenPattern(
        regex=re.compile(r"\bsection_id[:\s]", re.IGNORECASE),
        category="internal_metadata",
        severity="high",
        description="Internal section_id reference leaked into published content",
    ),
    # TC-QG-01: Block type leak
    ForbiddenPattern(
        regex=re.compile(r"\bblock_type[:\s]", re.IGNORECASE),
        category="internal_metadata",
        severity="high",
        description="Internal block_type reference leaked into published content",
    ),
]


def scan_forbidden(content: str) -> list[tuple[str, str, str, int]]:
    """Scan content for forbidden patterns.

    Returns a list of ``(category, severity, description, count)`` tuples,
    one per pattern type that matched at least once.
    """
    results: list[tuple[str, str, str, int]] = []
    for pat in FORBIDDEN_PATTERNS:
        matches = pat.regex.findall(content)
        if matches:
            results.append((pat.category, pat.severity, pat.description, len(matches)))
    return results


def strip_forbidden(content: str) -> str:
    """Remove all forbidden patterns from content.

    Applies each pattern's regex as a substitution.  Line-only patterns
    (internal_metadata) remove the entire line; inline patterns remove
    the matched text only.
    """
    for pat in FORBIDDEN_PATTERNS:
        if pat.category == "internal_metadata":
            # Remove entire lines matching this pattern
            content = re.sub(
                r"^.*" + pat.regex.pattern + r".*\n?",
                "",
                content,
                flags=re.MULTILINE,
            )
        else:
            content = pat.regex.sub("", content)
    return content
