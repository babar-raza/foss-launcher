"""Check: code_workflow — verify code blocks contain complete workflows (TC-D-04).

Code blocks in code-required page roles must contain ≥3 meaningful statements
(not just import + constructor). A code block with only `import X; obj = X()`
is a stub that provides no value to the reader.

Implements the MVC rubric from reports/evaluator-reliability/rubrics.md:
- howto_article: 150 words prose + 1 code block + 3 steps
- reference_object_page: 50 words + class brief + 1 method example
- getting_started: 100 words + install/usage command + basic usage
"""
from __future__ import annotations

import re

from launcher.models.evaluation import Finding

_CODE_FENCE_RE = re.compile(r"```[^\n]*\n([\s\S]*?)```", re.DOTALL)

# Page roles where code blocks are expected to demonstrate workflows
_CODE_REQUIRED_ROLES: frozenset[str] = frozenset({
    "api_reference", "reference_object_page", "howto_article",
    "getting_started", "installation", "developer_guide",
    "feature_overview",
})

# Minimum meaningful statements in a code block to not flag it.
# A "meaningful statement" is a non-blank, non-comment, non-import-only line
# that does something (assignment, method call, print, return, etc.).
_MIN_MEANINGFUL_STATEMENTS = 3

# Lines that don't count as meaningful
_TRIVIAL_LINE_RE = re.compile(
    r"^\s*(?:#.*|$|from\s+\S+\s+import\s+|import\s+)"
)


def _count_meaningful_statements(code: str) -> int:
    """Count lines that are not imports, comments, or blank."""
    count = 0
    for line in code.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        if _TRIVIAL_LINE_RE.match(stripped):
            continue
        count += 1
    return count


def check_code_completeness_workflow(
    content: str,
    slug: str,
    *,
    page_role: str = "",
) -> list[Finding]:
    """Verify code blocks in code-required roles contain complete workflows.

    Args:
        content: Rendered markdown content.
        slug: Page slug for Finding location.
        page_role: Page role string (e.g. "howto_article").

    Returns:
        List of MEDIUM Findings for stub code blocks.
    """
    if page_role not in _CODE_REQUIRED_ROLES:
        return []

    normalised = content.replace("\r\n", "\n").replace("\r", "\n")
    # Strip frontmatter
    body = re.sub(r"^---\n.*?\n---\n?", "", normalised, flags=re.DOTALL)

    findings: list[Finding] = []
    code_blocks = list(_CODE_FENCE_RE.finditer(body))

    if not code_blocks:
        # No code blocks at all in a code-required role
        findings.append(Finding(
            check="code_completeness_workflow",
            message=(
                f"No code blocks found in {page_role} page — "
                f"code-required roles must include at least one code example"
            ),
            severity="high",
            location=slug,
        ))
        return findings

    stub_count = 0
    for m in code_blocks:
        code_body = m.group(1)
        if not code_body.strip():
            continue  # Empty blocks caught by check_empty_code_blocks
        stmts = _count_meaningful_statements(code_body)
        if stmts < _MIN_MEANINGFUL_STATEMENTS:
            stub_count += 1

    if stub_count > 0:
        findings.append(Finding(
            check="code_completeness_workflow",
            message=(
                f"{stub_count} code block(s) have fewer than "
                f"{_MIN_MEANINGFUL_STATEMENTS} meaningful statements — "
                f"code examples should demonstrate complete workflows"
            ),
            severity="medium",
            location=slug,
        ))

    return findings
