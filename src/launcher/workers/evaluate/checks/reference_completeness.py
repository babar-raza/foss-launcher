"""Reference completeness check for API reference pages (TC-3803)."""
from __future__ import annotations

import re

from launcher.models.evaluation import Finding

_REFERENCE_ROLES: set[str] = {"api_reference", "reference_object_page"}

_PIPE_ROW_RE = re.compile(r"^\|.+\|$", re.MULTILINE)
_JSON_ARRAY_RE = re.compile(r"\[\s*\{['\"]")
_HTML_LINK_RE = re.compile(r"<a\s+href=", re.IGNORECASE)
_FENCE_RE = re.compile(r"^```", re.MULTILINE)

# docfx-style parameter list: `` `paramName` TypeName `` on its own line.
# Standard format for auto-generated .NET API reference docs; accepted as a
# structural equivalent to a markdown table for parameter documentation.
_PARAM_LIST_RE = re.compile(r"^`\w[\w.\[\]*]*`\s+\[?\w", re.MULTILINE)


def _strip_fenced_blocks(text: str) -> str:
    """Remove fenced code blocks so checks don't match code content."""
    result: list[str] = []
    in_fence = False
    for line in text.split("\n"):
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence:
            result.append(line)
    return "\n".join(result)


def check_reference_completeness(
    content: str, slug: str, *, page_role: str = "",
) -> list[Finding]:
    """Check that reference pages have required structural elements.

    Accepts either markdown tables OR docfx-style parameter lists as evidence of
    structured parameter documentation. The golden reference format uses param-lists
    (`` `name` Type ``) rather than tables, so both forms are valid.
    """
    if page_role not in _REFERENCE_ROLES:
        return []

    findings: list[Finding] = []

    # Strip frontmatter using the standard regex (consistent with other checks).
    body = re.sub(r"^---\n.*?\n---\n?", "", content, flags=re.DOTALL)

    # Strip code fences so JSON in code blocks doesn't trigger false positives
    body_no_fences = _strip_fenced_blocks(body)

    # Check 1: At least one markdown table OR docfx-style parameter list.
    # The docfx param-list format (`paramName` TypeName) is the standard for
    # auto-generated .NET API reference docs — accepted as a structural equivalent.
    has_table = _PIPE_ROW_RE.search(body)
    has_param_list = _PARAM_LIST_RE.search(body)
    if not has_table and not has_param_list:
        findings.append(Finding(
            check="reference_completeness",
            message="Reference page has no markdown tables or parameter lists",
            severity="high",
            location=slug,
        ))

    # Check 2: At least one code fence.
    # TC-3882 Wave 4 (E5): Escalated to HIGH — reference pages without any code example
    # are structurally incomplete. Exception: abstract/base-class pages rarely have
    # instantiable examples; detect via keyword heuristics and emit LOW advisory instead.
    if not _FENCE_RE.search(body):
        _abstract_keywords = ("abstract", "base class", "interface", "cannot be instantiated")
        _body_lower = body.lower()
        _is_abstract = any(kw in _body_lower for kw in _abstract_keywords)
        if _is_abstract:
            findings.append(Finding(
                check="reference_completeness",
                message="Reference page has no code examples (abstract/base class — advisory only)",
                severity="low",
                location=slug,
            ))
        else:
            findings.append(Finding(
                check="reference_completeness",
                message="Reference page has no code examples",
                severity="high",
                location=slug,
            ))

    # Check 3: No raw JSON arrays (malformed table content)
    if _JSON_ARRAY_RE.search(body_no_fences):
        findings.append(Finding(
            check="reference_completeness",
            message="Reference page contains raw JSON array (should be markdown table)",
            severity="high",
            location=slug,
        ))

    # Check 4: No HTML anchor tags
    if _HTML_LINK_RE.search(body_no_fences):
        findings.append(Finding(
            check="reference_completeness",
            message="Reference page contains HTML anchor tags (should be markdown links)",
            severity="medium",
            location=slug,
        ))

    return findings
