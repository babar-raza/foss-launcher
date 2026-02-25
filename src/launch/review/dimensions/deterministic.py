"""Deterministic dimension checkers (TC-2534).

Nine fully deterministic checkers -- no LLM calls, no randomness.
Each function accepts page content (and optional context) and returns
a ``DimensionResult``.

Public API:
    check_contradiction(pages, shared_facts)    -> DimensionResult  (RD-02)
    check_slug_quality(slug)                    -> DimensionResult  (RD-03)
    check_code_fence_integrity(content)         -> DimensionResult  (RD-04)
    check_prompt_leak(content)                  -> DimensionResult  (RD-05)
    check_structure_compliance(content, page_role, templates) -> DimensionResult (RD-06)
    check_heading_hierarchy(content)            -> DimensionResult  (RD-07)
    check_claim_coverage(content, assigned_claims) -> DimensionResult (RD-08)
    check_seo_meta(content)                     -> DimensionResult  (RD-10)
    check_link_integrity(content, known_pages)  -> DimensionResult  (RD-12)
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set

from ..rubric import DimensionResult, Issue

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _parse_frontmatter(content: str) -> Dict[str, str]:
    """Extract simple key: value pairs from YAML frontmatter."""
    m = _FRONTMATTER_RE.match(content)
    if not m:
        return {}
    result: Dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            result[key.strip()] = val.strip().strip('"').strip("'")
    return result


def _strip_frontmatter(content: str) -> str:
    """Return content with YAML frontmatter removed."""
    m = _FRONTMATTER_RE.match(content)
    return content[m.end():] if m else content


def _extract_headings(content: str) -> List[Dict[str, Any]]:
    """Extract headings with their level and line number."""
    body = _strip_frontmatter(content)
    headings: List[Dict[str, Any]] = []
    for i, line in enumerate(body.splitlines()):
        m = re.match(r"^(#{1,6})\s+(.+)", line)
        if m:
            headings.append({
                "level": len(m.group(1)),
                "text": m.group(2).strip(),
                "line": i,
            })
    return headings


# ---------------------------------------------------------------------------
# RD-02: Contradiction
# ---------------------------------------------------------------------------

# Patterns to extract version-like references
_VERSION_RE = re.compile(
    r"(?:Python|python)\s+(\d+\.\d+(?:\.\d+)?)",
)
_PACKAGE_RE = re.compile(
    r"pip\s+install\s+([\w\-]+)",
)


def check_contradiction(
    pages: List[Dict[str, str]],
    shared_facts: Optional[Dict[str, Any]] = None,
) -> DimensionResult:
    """RD-02: Cross-page version/name mismatches.

    Args:
        pages: List of dicts with 'path' and 'content' keys.
        shared_facts: Optional shared_facts.json data for canonical values.

    Returns:
        DimensionResult with score 10 - (contradiction_count * 2), clamped.
    """
    issues: List[Issue] = []

    # Collect version and package references per page
    version_refs: Dict[str, Set[str]] = {}  # page_path -> set of versions
    package_refs: Dict[str, Set[str]] = {}  # page_path -> set of packages

    for page in pages:
        path = page.get("path", "unknown")
        content = page.get("content", "")

        versions = set(_VERSION_RE.findall(content))
        if versions:
            version_refs[path] = versions

        packages = set(_PACKAGE_RE.findall(content))
        if packages:
            package_refs[path] = packages

    # Check for cross-page version contradictions
    all_versions: Set[str] = set()
    for vs in version_refs.values():
        all_versions.update(vs)

    if len(all_versions) > 1:
        # Multiple different Python versions referenced -- potential contradiction
        issues.append(Issue(
            severity="error",
            message=f"Multiple Python versions referenced across pages: {sorted(all_versions)}",
        ))

    # Check for cross-page package name contradictions
    all_packages: Set[str] = set()
    for ps in package_refs.values():
        all_packages.update(ps)

    # Only flag if different package names appear that look like the same product
    # (e.g., aspose-cells vs aspose_cells)
    normalized: Dict[str, Set[str]] = {}
    for pkg in all_packages:
        norm = pkg.lower().replace("-", "_")
        if norm not in normalized:
            normalized[norm] = set()
        normalized[norm].add(pkg)
    for norm, variants in normalized.items():
        if len(variants) > 1:
            issues.append(Issue(
                severity="error",
                message=f"Package name variants: {sorted(variants)}",
            ))

    # Check against shared_facts canonical values
    if shared_facts:
        canonical_python = shared_facts.get("min_python_version", "")
        if canonical_python and all_versions:
            for v in all_versions:
                # If page says a version lower than canonical minimum
                try:
                    page_parts = [int(x) for x in v.split(".")]
                    canon_parts = [int(x) for x in canonical_python.split(".")]
                    if page_parts < canon_parts:
                        issues.append(Issue(
                            severity="error",
                            message=f"Version {v} contradicts canonical minimum {canonical_python}",
                        ))
                except (ValueError, IndexError):
                    pass

    contradiction_count = len(issues)
    score = max(0, min(10, 10 - contradiction_count * 2))
    return DimensionResult(
        dimension_id="RD-02",
        name="Contradiction",
        score=score,
        issues=issues,
        evidence=f"Found {contradiction_count} contradiction(s) across {len(pages)} pages.",
    )


# ---------------------------------------------------------------------------
# RD-03: Slug quality
# ---------------------------------------------------------------------------

_CONSECUTIVE_HYPHENS = re.compile(r"--+")
_NON_SLUG_CHARS = re.compile(r"[^a-z0-9\-]")


def check_slug_quality(slug: str) -> DimensionResult:
    """RD-03: SEO-friendliness of a page slug.

    Checks: length 3-60, lowercase, no consecutive hyphens,
    no leading/trailing hyphens, no special characters.
    """
    issues: List[Issue] = []
    if not slug:
        return DimensionResult(
            dimension_id="RD-03",
            name="Slug quality",
            score=0,
            issues=[Issue(severity="error", message="Empty slug")],
        )

    violation_count = 0

    if len(slug) < 3:
        issues.append(Issue(severity="error", message=f"Slug too short ({len(slug)} chars, min 3)"))
        violation_count += 1

    if len(slug) > 60:
        issues.append(Issue(severity="warning", message=f"Slug too long ({len(slug)} chars, max 60)"))
        violation_count += 1

    if slug != slug.lower():
        issues.append(Issue(severity="error", message="Slug contains uppercase characters"))
        violation_count += 1

    if _CONSECUTIVE_HYPHENS.search(slug):
        issues.append(Issue(severity="warning", message="Slug contains consecutive hyphens"))
        violation_count += 1

    if slug.startswith("-") or slug.endswith("-"):
        issues.append(Issue(severity="warning", message="Slug has leading/trailing hyphens"))
        violation_count += 1

    if _NON_SLUG_CHARS.search(slug):
        issues.append(Issue(severity="error", message="Slug contains non-slug characters"))
        violation_count += 1

    score = max(0, min(10, 10 - violation_count * 2))
    return DimensionResult(
        dimension_id="RD-03",
        name="Slug quality",
        score=score,
        issues=issues,
        evidence=f"Slug '{slug}' has {violation_count} violation(s).",
    )


# ---------------------------------------------------------------------------
# RD-04: Code fence integrity
# ---------------------------------------------------------------------------

_CODE_FENCE_OPEN = re.compile(r"^```(\w*)\s*$", re.MULTILINE)
_CODE_FENCE_CLOSE = re.compile(r"^```\s*$", re.MULTILINE)


def check_code_fence_integrity(content: str) -> DimensionResult:
    """RD-04: Complete, properly fenced, language tag present.

    Checks for unclosed fences, missing language tags, empty code blocks.
    """
    issues: List[Issue] = []
    body = _strip_frontmatter(content)
    lines = body.splitlines()

    issue_count = 0
    in_fence = False
    fence_start_line = 0
    fence_lang = ""
    fence_content_lines = 0

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not in_fence:
            m = re.match(r"^```(\w*)\s*$", stripped)
            if m:
                in_fence = True
                fence_start_line = i
                fence_lang = m.group(1)
                fence_content_lines = 0
                if not fence_lang:
                    issues.append(Issue(
                        severity="warning",
                        message="Code fence missing language tag",
                        line=i,
                    ))
                    issue_count += 1
        else:
            if stripped == "```":
                # Closing fence
                if fence_content_lines == 0:
                    issues.append(Issue(
                        severity="warning",
                        message="Empty code block",
                        line=fence_start_line,
                    ))
                    issue_count += 1
                in_fence = False
            else:
                fence_content_lines += 1

    if in_fence:
        issues.append(Issue(
            severity="error",
            message=f"Unclosed code fence starting at line {fence_start_line}",
            line=fence_start_line,
        ))
        issue_count += 1

    score = max(0, min(10, 10 - issue_count * 2))
    return DimensionResult(
        dimension_id="RD-04",
        name="Code fence integrity",
        score=score,
        issues=issues,
        evidence=f"Found {issue_count} code fence issue(s).",
    )


# ---------------------------------------------------------------------------
# RD-05: Prompt leak
# ---------------------------------------------------------------------------

_PROMPT_LEAK_PATTERNS = [
    re.compile(r"\bYou\s+are\s+a\b", re.IGNORECASE),
    re.compile(r"^System:\s", re.MULTILINE),
    re.compile(r"^###\s+Instructions\s*$", re.MULTILINE),
    re.compile(r"^IMPORTANT:\s", re.MULTILINE),
    re.compile(r"\[\[CLAIM_", re.IGNORECASE),
    re.compile(r"\[\[SNIPPET_", re.IGNORECASE),
    re.compile(r"^##\s+Product\s+Context\s*$", re.MULTILINE),
    re.compile(r"^##\s+Output\s+Rules\s*$", re.MULTILINE),
    re.compile(r"\bdo\s+not\s+mention\s+(?:that\s+)?you\s+are\s+an?\s+AI\b", re.IGNORECASE),
    re.compile(r"\bwrite\s+in\s+(?:the\s+)?style\s+of\b", re.IGNORECASE),
    re.compile(r"\bfollowing\s+(?:the\s+)?instructions\b", re.IGNORECASE),
    re.compile(r"^#{1,2}\s+Source\s+Material\s*$", re.MULTILINE),
    re.compile(r"^#{1,2}\s+CRITICAL\s+Rules?\s*$", re.MULTILINE),
    re.compile(r"^#{1,2}\s+FORMATTING\s+RULES\s*$", re.MULTILINE),
]


def check_prompt_leak(content: str) -> DimensionResult:
    """RD-05: Detect system prompt fragments leaked into generated content.

    Score is 10 if clean, 0 if any leak is found. Prompt leaks are
    high-severity because they expose internal system behavior.
    """
    issues: List[Issue] = []
    body = _strip_frontmatter(content)

    # Skip content inside code fences (legitimate code may contain these patterns)
    in_fence = False
    prose_lines: List[str] = []
    for line in body.splitlines():
        stripped = line.strip()
        if re.match(r"^```", stripped):
            in_fence = not in_fence
            continue
        if not in_fence:
            prose_lines.append(line)
    prose = "\n".join(prose_lines)

    for pattern in _PROMPT_LEAK_PATTERNS:
        m = pattern.search(prose)
        if m:
            issues.append(Issue(
                severity="error",
                message=f"Prompt leak detected: '{m.group()}'",
                location=m.group(),
            ))

    score = 10 if not issues else 0
    return DimensionResult(
        dimension_id="RD-05",
        name="Prompt leak",
        score=score,
        issues=issues,
        evidence=f"{'No prompt leaks detected.' if not issues else f'Found {len(issues)} prompt leak(s).'}",
    )


# ---------------------------------------------------------------------------
# RD-06: Structure compliance
# ---------------------------------------------------------------------------

# Default required sections per page_role (subset of section_templates.yaml)
_DEFAULT_TEMPLATES: Dict[str, List[str]] = {
    "tutorial": ["prerequisites", "installation", "basic_usage", "code_examples", "next_steps"],
    "api_reference": ["overview", "class_reference", "method_reference", "parameters", "examples"],
    "feature_showcase": ["overview", "capabilities", "code_examples", "integration_guide"],
    "troubleshooting": ["common_issues", "solutions", "debugging_steps"],
    "faq": ["frequently_asked_questions"],
    "landing": ["introduction", "key_features", "quick_start", "documentation_links"],
    "comprehensive_guide": ["overview", "installation", "getting_started", "advanced_features", "best_practices"],
    "best_practices": ["recommendations", "code_examples", "rationale"],
    "performance": ["overview", "optimization_techniques", "benchmarks", "code_examples"],
    "blog": ["introduction", "main_content", "conclusion"],
    "getting_started": ["prerequisites", "installation", "first_example", "next_steps"],
    "howto_article": ["goal", "when_to_use", "prerequisites", "steps", "code_example", "see_also"],
    "format_conversion": ["supported_formats", "conversion_steps", "code_examples"],
    "default": ["introduction", "main_content"],
}


def _normalize_heading(text: str) -> str:
    """Normalize a heading text for fuzzy matching against required sections."""
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def check_structure_compliance(
    content: str,
    page_role: str = "default",
    templates: Optional[Dict[str, List[str]]] = None,
) -> DimensionResult:
    """RD-06: Required sections present and in correct order.

    Args:
        content: Full page markdown content.
        page_role: The role of this page (e.g., 'tutorial', 'blog').
        templates: Custom templates mapping; falls back to built-in defaults.

    Returns:
        DimensionResult with score = 10 * (present_required / total_required).
    """
    tmpl = templates or _DEFAULT_TEMPLATES
    required_sections = tmpl.get(page_role, tmpl.get("default", []))

    if not required_sections:
        return DimensionResult(
            dimension_id="RD-06",
            name="Structure compliance",
            score=10,
            issues=[],
            evidence="No required sections defined for this page role.",
        )

    headings = _extract_headings(content)
    heading_norms = [_normalize_heading(h["text"]) for h in headings]

    issues: List[Issue] = []
    present_count = 0

    for section in required_sections:
        norm = _normalize_heading(section)
        # Fuzzy match: check if any heading contains the required section name
        found = any(norm in h or h in norm for h in heading_norms)
        if found:
            present_count += 1
        else:
            issues.append(Issue(
                severity="warning",
                message=f"Required section '{section}' not found",
            ))

    total = len(required_sections)
    score = round(10 * present_count / total) if total > 0 else 10

    return DimensionResult(
        dimension_id="RD-06",
        name="Structure compliance",
        score=score,
        issues=issues,
        evidence=f"{present_count}/{total} required sections present for role '{page_role}'.",
    )


# ---------------------------------------------------------------------------
# RD-07: Heading hierarchy
# ---------------------------------------------------------------------------

def check_heading_hierarchy(content: str) -> DimensionResult:
    """RD-07: H1->H2->H3 monotonic descent, no skipped levels.

    A heading that skips a level (e.g., H1 followed by H3 with no H2)
    is a violation.  Score = 10 - (skip_count * 3), clamped.
    """
    headings = _extract_headings(content)
    issues: List[Issue] = []
    skip_count = 0

    if not headings:
        return DimensionResult(
            dimension_id="RD-07",
            name="Heading hierarchy",
            score=10,
            issues=[],
            evidence="No headings found.",
        )

    prev_level = headings[0]["level"]
    for h in headings[1:]:
        level = h["level"]
        # Going deeper: check for skipped levels (e.g., H1->H3 skips H2)
        if level > prev_level and level - prev_level > 1:
            issues.append(Issue(
                severity="error",
                message=f"Heading level skip: H{prev_level} -> H{level} ('{h['text']}')",
                line=h["line"],
            ))
            skip_count += 1
        prev_level = level

    score = max(0, min(10, 10 - skip_count * 3))
    return DimensionResult(
        dimension_id="RD-07",
        name="Heading hierarchy",
        score=score,
        issues=issues,
        evidence=f"Found {skip_count} heading level skip(s) in {len(headings)} headings.",
    )


# ---------------------------------------------------------------------------
# RD-08: Claim coverage
# ---------------------------------------------------------------------------

_CLAIM_ID_RE = re.compile(r"\b(C-\d+)\b")


def check_claim_coverage(
    content: str,
    assigned_claims: Optional[List[str]] = None,
) -> DimensionResult:
    """RD-08: Percentage of assigned claims actually used in content.

    Args:
        content: Full page markdown content.
        assigned_claims: List of claim IDs assigned to this page (from page_plan).

    Returns:
        DimensionResult with score = 10 * (claims_used / claims_assigned).
    """
    if not assigned_claims:
        return DimensionResult(
            dimension_id="RD-08",
            name="Claim coverage",
            score=10,
            issues=[],
            evidence="No claims assigned to this page.",
        )

    # Find claim IDs mentioned in content (via claim markers or references)
    found_claims = set(_CLAIM_ID_RE.findall(content))

    # Also check for claim content (the actual claim text is often embedded)
    used = found_claims & set(assigned_claims)
    missing = set(assigned_claims) - found_claims

    issues: List[Issue] = []
    for claim_id in sorted(missing):
        issues.append(Issue(
            severity="warning",
            message=f"Assigned claim {claim_id} not referenced in content",
        ))

    total = len(assigned_claims)
    used_count = total - len(missing)
    score = round(10 * used_count / total) if total > 0 else 10

    return DimensionResult(
        dimension_id="RD-08",
        name="Claim coverage",
        score=score,
        issues=issues,
        evidence=f"{used_count}/{total} assigned claims referenced in content.",
    )


# ---------------------------------------------------------------------------
# RD-10: SEO title/meta
# ---------------------------------------------------------------------------

def check_seo_meta(content: str) -> DimensionResult:
    """RD-10: Frontmatter title/description/keywords completeness.

    Checks:
    - title present + 20-60 chars
    - description present + 50-160 chars
    - keywords present + 3-10 items
    Score = 10 * (checks_passed / total_checks).
    """
    fm = _parse_frontmatter(content)
    issues: List[Issue] = []
    checks_passed = 0
    total_checks = 6  # 3 presence + 3 length

    # Title
    title = fm.get("title", "")
    if title:
        checks_passed += 1
        if 20 <= len(title) <= 60:
            checks_passed += 1
        else:
            issues.append(Issue(
                severity="warning",
                message=f"Title length {len(title)} chars (ideal: 20-60)",
            ))
    else:
        issues.append(Issue(severity="error", message="Missing title in frontmatter"))

    # Description
    desc = fm.get("description", "")
    if desc:
        checks_passed += 1
        if 50 <= len(desc) <= 160:
            checks_passed += 1
        else:
            issues.append(Issue(
                severity="warning",
                message=f"Description length {len(desc)} chars (ideal: 50-160)",
            ))
    else:
        issues.append(Issue(severity="error", message="Missing description in frontmatter"))

    # Keywords
    keywords_raw = fm.get("keywords", "")
    if keywords_raw:
        checks_passed += 1
        # Keywords can be comma-separated or YAML list
        kw_list = [k.strip() for k in keywords_raw.split(",") if k.strip()]
        if 3 <= len(kw_list) <= 10:
            checks_passed += 1
        else:
            issues.append(Issue(
                severity="warning",
                message=f"Keywords count {len(kw_list)} (ideal: 3-10)",
            ))
    else:
        issues.append(Issue(severity="warning", message="Missing keywords in frontmatter"))

    score = round(10 * checks_passed / total_checks) if total_checks > 0 else 0

    return DimensionResult(
        dimension_id="RD-10",
        name="SEO title/meta",
        score=score,
        issues=issues,
        evidence=f"{checks_passed}/{total_checks} SEO meta checks passed.",
    )


# ---------------------------------------------------------------------------
# RD-12: Link integrity
# ---------------------------------------------------------------------------

_MD_LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")


def check_link_integrity(
    content: str,
    known_pages: Optional[Set[str]] = None,
) -> DimensionResult:
    """RD-12: No broken internal cross-references.

    Args:
        content: Full page markdown content.
        known_pages: Set of known page file stems/slugs in the run.

    Returns:
        DimensionResult with score = 10 - (broken_count * 3), clamped.
    """
    if known_pages is None:
        known_pages = set()

    body = _strip_frontmatter(content)
    links = _MD_LINK_RE.findall(body)

    issues: List[Issue] = []
    broken_count = 0

    for link_text, href in links:
        # Skip external links
        if href.startswith(("http://", "https://", "mailto:", "#")):
            continue

        # Internal link -- check if target exists in known pages
        # Strip leading/trailing slashes, anchors, and extensions
        target = href.split("#")[0].strip("/")
        target_stem = target.rsplit(".", 1)[0] if "." in target else target
        target_slug = target_stem.rsplit("/", 1)[-1] if "/" in target_stem else target_stem

        if known_pages and target_slug and target_slug not in known_pages:
            issues.append(Issue(
                severity="error",
                message=f"Broken internal link: [{link_text}]({href})",
            ))
            broken_count += 1

    score = max(0, min(10, 10 - broken_count * 3))
    return DimensionResult(
        dimension_id="RD-12",
        name="Link integrity",
        score=score,
        issues=issues,
        evidence=f"Found {broken_count} broken link(s) out of {len(links)} total.",
    )
