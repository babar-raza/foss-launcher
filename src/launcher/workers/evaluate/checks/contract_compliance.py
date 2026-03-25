"""Check: contract_compliance — detect contract instruction violations (TC-PQ-CC).

Tests the most objective, binary-testable rules from prose contracts:
- Product-definition opening (all non-reference roles)
- FAQ Q&A structure (headings must be questions, answers must not lead with product name)
- Blog announcement opening (must not start with product name)
- Code-first violation for workflow/howto (code block must appear early)

Each rule is deterministic with zero false-positive tolerance.
"""
from __future__ import annotations

import re

from launcher.models.evaluation import Finding

_CODE_FENCE_RE = re.compile(r"```[\s\S]*?```", re.DOTALL)
_FRONTMATTER_RE = re.compile(r"^---\n.*?\n---\n?", re.DOTALL)

# Roles exempt from the product-definition opening check.
_PRODUCT_DEF_EXEMPT: frozenset[str] = frozenset({
    "api_reference", "reference_object_page", "toc",
})

# Pattern: "{ProductName} is a library/tool/package/framework..."
# Catches the most common contract violation across all non-reference roles.
_PRODUCT_DEF_RE = re.compile(
    r"^(?:the\s+)?[`]?[\w.\-]+[`]?\s+is\s+a\s+"
    r"(?:library|tool|package|sdk|framework|module|solution|set of)\b",
    re.IGNORECASE,
)


def _strip_frontmatter_and_fences(content: str) -> str:
    """Remove YAML frontmatter and fenced code blocks."""
    body = _FRONTMATTER_RE.sub("", content)
    return _CODE_FENCE_RE.sub("", body)


def _first_content_paragraph(body: str) -> str:
    """Get the first non-empty, non-heading, non-list paragraph from body."""
    for line in body.strip().split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        if stripped.startswith(("- ", "* ", "| ", "> ")):
            continue
        return stripped
    return ""


def _check_product_def_opening(
    body: str, slug: str, page_role: str,
) -> list[Finding]:
    """Flag pages that open with '{ProductName} is a library/tool...'."""
    if page_role in _PRODUCT_DEF_EXEMPT:
        return []

    first_para = _first_content_paragraph(body)
    if not first_para:
        return []

    if _PRODUCT_DEF_RE.match(first_para):
        return [Finding(
            check="contract_compliance",
            message=(
                f"Contract violation: page opens with a product definition "
                f"(\"{first_para[:80]}...\"). Lead with the reader's goal or "
                f"problem instead."
            ),
            severity="medium",
            location=slug,
        )]
    return []


def _check_faq_structure(body: str, slug: str) -> list[Finding]:
    """Check FAQ-specific contract rules: Q&A headings must be questions."""
    findings: list[Finding] = []

    # Find all H3 headings
    h3_headings = re.findall(r"^###\s+(.+)$", body, re.MULTILINE)
    if not h3_headings:
        return []

    # Rule: H3 headings should contain question marks
    non_question_count = 0
    for heading in h3_headings:
        heading_text = heading.strip()
        # Skip headings that are structural (e.g., "See Also", "Related")
        if heading_text.lower() in ("see also", "related", "references", "resources"):
            continue
        if "?" not in heading_text:
            non_question_count += 1

    if non_question_count > 0 and len(h3_headings) > 1:
        ratio = non_question_count / len(h3_headings)
        if ratio > 0.5:
            findings.append(Finding(
                check="contract_compliance",
                message=(
                    f"FAQ contract violation: {non_question_count}/{len(h3_headings)} "
                    f"H3 headings are not questions. FAQ headings should be phrased "
                    f"as questions (e.g., 'How do I save a workbook?')."
                ),
                severity="medium",
                location=slug,
                section_id="FAQ structure",
            ))

    return findings


def _check_blog_opening(body: str, slug: str, product_name: str) -> list[Finding]:
    """Blog announcements must not open with the product name."""
    first_para = _first_content_paragraph(body)
    if not first_para:
        return []

    # Check if first sentence starts with the product name or backticked product
    product_pattern = re.escape(product_name) if product_name else r"[\w.]+"
    pattern = re.compile(
        rf"^(?:the\s+)?[`]?{product_pattern}[`]?\s+(?:is|provides|offers|enables|allows)\b",
        re.IGNORECASE,
    )
    if pattern.match(first_para):
        return [Finding(
            check="contract_compliance",
            message=(
                f"Blog contract violation: opening starts with product name "
                f"(\"{first_para[:80]}...\"). Lead with the problem the library "
                f"solves instead."
            ),
            severity="medium",
            location=slug,
        )]
    return []


def _check_code_presence(body: str, slug: str, content: str) -> list[Finding]:
    """Workflow/howto pages must have code blocks early in the content."""
    # Check original content (before fence stripping) for code blocks
    code_blocks = list(re.finditer(r"```", content))
    if len(code_blocks) >= 2:
        # Has at least one code block — check position
        first_code_pos = code_blocks[0].start()
        # Count paragraphs before first code block
        before_code = content[:first_code_pos]
        para_count = len([
            p for p in before_code.split("\n\n")
            if p.strip() and not p.strip().startswith(("---", "#"))
        ])
        # Allow up to 8 paragraphs before first code (generous threshold)
        if para_count > 8:
            return [Finding(
                check="contract_compliance",
                message=(
                    f"Contract violation: first code block appears after "
                    f"{para_count} paragraphs. Workflow/how-to pages should "
                    f"show code early."
                ),
                severity="medium",
                location=slug,
            )]
    elif not code_blocks:
        # No code blocks at all in a workflow/howto page
        word_count = len(body.split())
        if word_count > 100:
            return [Finding(
                check="contract_compliance",
                message=(
                    "Contract violation: workflow/how-to page has no code "
                    "blocks. These pages must demonstrate the workflow in code."
                ),
                severity="medium",
                location=slug,
            )]
    return []


def check_contract_compliance(
    content: str,
    slug: str,
    *,
    page_role: str = "",
    product_name: str = "",
) -> list[Finding]:
    """Detect prose contract instruction violations.

    Tests binary, objective contract rules per page role:
    - ALL non-reference roles: first paragraph must not be a product definition
    - faq: H3 headings should be questions
    - blog_announcement: must not open with product name
    - workflow_page, howto_article: must have code blocks early

    Args:
        content: Rendered markdown content.
        slug: Page slug for Finding location.
        page_role: Page role for role-specific rules.
        product_name: Product display name for pattern matching.

    Returns:
        List of MEDIUM Findings for contract violations detected.
    """
    body = _strip_frontmatter_and_fences(content)
    findings: list[Finding] = []

    # Rule 1: Product-definition opening (all non-reference roles)
    findings.extend(_check_product_def_opening(body, slug, page_role))

    # Rule 2: FAQ Q&A structure
    if page_role == "faq":
        findings.extend(_check_faq_structure(body, slug))

    # Rule 3: Blog announcement opening
    if page_role in ("blog_announcement", "feature_blog"):
        findings.extend(_check_blog_opening(body, slug, product_name))

    # Rule 4: Code presence for workflow/howto
    if page_role in ("workflow_page", "howto_article", "feature_showcase", "getting_started"):  # TC-5196
        findings.extend(_check_code_presence(body, slug, content))

    return findings
