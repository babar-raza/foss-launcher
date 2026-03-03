"""TC-3674: Deterministic page-role skeleton templates.

Each page role defines an ordered list of H2 sections that represent the
canonical document structure.  The LLM generates prose WITHIN sections but
cannot add, remove, or reorder them.

The skeleton is the single source of truth for document structure — it
enforces the spec contract at specs/07_section_templates.md §Skeleton-First
Page Structure.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, NamedTuple, Optional


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


class SkeletonSection(NamedTuple):
    """One section in a page-role skeleton."""

    heading: str          # Exact H2 text (without the '## ' prefix)
    level: int            # Heading level (2 for H2, 3 for H3, etc.)
    required: bool        # True = validation error if missing
    content_hint: str     # Guidance for LLM on what to write
    min_words: int        # Minimum word count for this section (0 = no minimum)
    max_words: int        # Maximum word count hint (0 = no maximum)


# ---------------------------------------------------------------------------
# Skeleton registry — one entry per canonical page_role (17 roles)
# ---------------------------------------------------------------------------

PAGE_ROLE_SKELETONS: Dict[str, List[SkeletonSection]] = {

    # ── Products / Marketing ──────────────────────────────────────────

    "landing": [
        SkeletonSection("Overview", 2, True,
                        "Product introduction and key value proposition", 50, 150),
        SkeletonSection("Key Features", 2, True,
                        "Feature bullet list with brief descriptions", 100, 300),
        SkeletonSection("Quick Start", 2, True,
                        "Minimal code example to get started", 50, 200),
        SkeletonSection("See Also", 2, True,
                        "Links to getting started, docs, API reference", 0, 100),
    ],

    "toc": [
        SkeletonSection("Overview", 2, True,
                        "Brief description of what this section covers", 30, 100),
        SkeletonSection("Pages in This Section", 2, True,
                        "List of child pages with one-line descriptions", 30, 300),
        SkeletonSection("See Also", 2, False,
                        "Links to related sections", 0, 100),
    ],

    # ── Docs ──────────────────────────────────────────────────────────

    "comprehensive_guide": [
        SkeletonSection("Introduction", 2, True,
                        "What this guide covers and prerequisites", 50, 150),
        SkeletonSection("Core Concepts", 2, True,
                        "Key concepts the reader needs to understand", 100, 400),
        SkeletonSection("Implementation", 2, True,
                        "Step-by-step implementation with code examples", 200, 600),
        SkeletonSection("Advanced Usage", 2, False,
                        "Advanced patterns and configurations", 100, 300),
        SkeletonSection("Troubleshooting", 2, False,
                        "Common issues and solutions", 50, 200),
        SkeletonSection("See Also", 2, True,
                        "Related guides and references", 0, 100),
    ],

    "workflow_page": [
        SkeletonSection("Overview", 2, True,
                        "What this workflow accomplishes", 30, 100),
        SkeletonSection("Prerequisites", 2, True,
                        "Required setup and knowledge", 30, 100),
        SkeletonSection("Steps", 2, True,
                        "Numbered steps with code examples", 100, 400),
        SkeletonSection("Result", 2, True,
                        "Expected output or verification", 30, 100),
        SkeletonSection("See Also", 2, False,
                        "Related workflows and guides", 0, 100),
    ],

    "feature_showcase": [
        SkeletonSection("Overview", 2, True,
                        "Feature purpose and benefits", 50, 150),
        SkeletonSection("How It Works", 2, True,
                        "Technical explanation with examples", 100, 300),
        SkeletonSection("Code Example", 2, True,
                        "Complete runnable code demonstrating the feature", 50, 300),
        SkeletonSection("See Also", 2, False,
                        "Related features and documentation", 0, 100),
    ],

    "troubleshooting": [
        SkeletonSection("Common Issues", 2, True,
                        "Problem-solution pairs with symptoms, causes, and fixes", 100, 400),
        SkeletonSection("Error Messages", 2, False,
                        "Error code explanations and resolutions", 50, 200),
        SkeletonSection("Getting Help", 2, True,
                        "Support channels and resources", 30, 100),
        SkeletonSection("See Also", 2, False,
                        "Related troubleshooting and documentation", 0, 100),
    ],

    # ── Reference ─────────────────────────────────────────────────────

    "api_reference": [
        SkeletonSection("Overview", 2, True,
                        "Class or module purpose in 1-3 sentences", 30, 100),
        SkeletonSection("Installation", 2, True,
                        "pip install command using canonical import", 30, 100),
        SkeletonSection("API Summary", 2, True,
                        "Table of classes, methods, or functions with brief descriptions", 50, 400),
        SkeletonSection("Example", 2, True,
                        "Runnable code example using canonical import", 50, 300),
        SkeletonSection("See Also", 2, False,
                        "Related classes, modules, and guides", 0, 100),
    ],

    "reference_object_page": [
        SkeletonSection("Overview", 2, True,
                        "Class or function purpose in 1-3 sentences", 30, 100),
        SkeletonSection("Constructor", 2, False,
                        "Constructor signature and parameters table", 50, 200),
        SkeletonSection("Properties", 2, False,
                        "Property table: name, type, description", 50, 400),
        SkeletonSection("Methods", 2, True,
                        "Method table: signature, return type, description", 50, 400),
        SkeletonSection("Example", 2, True,
                        "Runnable code example using canonical import", 50, 300),
        SkeletonSection("See Also", 2, False,
                        "Related classes and guides", 0, 100),
    ],

    # ── KB ────────────────────────────────────────────────────────────

    "faq": [
        SkeletonSection("Frequently Asked Questions", 2, True,
                        "Q&A pairs as H3 sub-sections — each question is an H3", 100, 600),
        SkeletonSection("See Also", 2, True,
                        "Related documentation and guides", 0, 100),
    ],

    "best_practices": [
        SkeletonSection("Overview", 2, True,
                        "What best practices this page covers", 30, 100),
        SkeletonSection("Recommendations", 2, True,
                        "Categorized best practice recommendations with rationale", 100, 400),
        SkeletonSection("Common Mistakes", 2, False,
                        "Anti-patterns and how to avoid them", 50, 200),
        SkeletonSection("See Also", 2, False,
                        "Related best practices and guides", 0, 100),
    ],

    "tutorial": [
        SkeletonSection("Prerequisites", 2, True,
                        "What you need before starting", 30, 100),
        SkeletonSection("Steps", 2, True,
                        "Numbered steps with code examples", 100, 400),
        SkeletonSection("Code Example", 2, True,
                        "Complete working example", 50, 300),
        SkeletonSection("Next Steps", 2, True,
                        "What to learn next with links", 30, 100),
        SkeletonSection("See Also", 2, True,
                        "Related tutorials and documentation", 0, 100),
    ],

    "howto_article": [
        SkeletonSection("Goal", 2, True,
                        "What the reader will accomplish", 20, 60),
        SkeletonSection("Prerequisites", 2, True,
                        "Required setup and knowledge", 30, 100),
        SkeletonSection("Steps", 2, True,
                        "Numbered steps with code examples", 100, 400),
        SkeletonSection("Code Example", 2, True,
                        "Complete working example", 50, 300),
        SkeletonSection("Common Mistakes", 2, False,
                        "Pitfalls and how to avoid them", 30, 150),
        SkeletonSection("When To Use", 2, False,
                        "Scenarios where this approach is appropriate", 30, 100),
        SkeletonSection("See Also", 2, False,
                        "Related how-to articles", 0, 100),
    ],

    # ── Blog ──────────────────────────────────────────────────────────

    "blog_announcement": [
        SkeletonSection("Introduction", 2, True,
                        "What is new and why it matters", 50, 200),
        SkeletonSection("Key Highlights", 2, True,
                        "Feature highlights or changes", 100, 300),
        SkeletonSection("Getting Started", 2, True,
                        "How to try it with a code example", 50, 200),
        SkeletonSection("See Also", 2, False,
                        "Links to documentation and changelog", 0, 100),
    ],

    "blog": [
        SkeletonSection("Introduction", 2, True,
                        "What is new and why it matters", 50, 200),
        SkeletonSection("Key Highlights", 2, True,
                        "Feature highlights or changes", 100, 300),
        SkeletonSection("Getting Started", 2, True,
                        "How to try it with a code example", 50, 200),
        SkeletonSection("See Also", 2, False,
                        "Links to documentation and changelog", 0, 100),
    ],

    "feature_blog": [
        SkeletonSection("Introduction", 2, True,
                        "Feature overview and why it matters", 50, 200),
        SkeletonSection("Key Highlights", 2, True,
                        "Feature details and benefits", 100, 300),
        SkeletonSection("Getting Started", 2, True,
                        "How to use the feature with code example", 50, 200),
        SkeletonSection("See Also", 2, False,
                        "Links to documentation and related features", 0, 100),
    ],

    # ── Specialized ───────────────────────────────────────────────────

    "format_conversion": [
        SkeletonSection("Overview", 2, True,
                        "What conversion this page covers", 30, 100),
        SkeletonSection("Prerequisites", 2, True,
                        "Required setup and input format requirements", 30, 100),
        SkeletonSection("Steps", 2, True,
                        "Step-by-step conversion with code", 100, 400),
        SkeletonSection("Code Example", 2, True,
                        "Complete runnable conversion example", 50, 300),
        SkeletonSection("See Also", 2, False,
                        "Related conversions and documentation", 0, 100),
    ],

    "performance_guide": [
        SkeletonSection("Overview", 2, True,
                        "What performance aspects this guide covers", 30, 100),
        SkeletonSection("Optimization Strategies", 2, True,
                        "Specific optimization techniques with benchmarks", 100, 400),
        SkeletonSection("Code Example", 2, True,
                        "Optimized code example", 50, 300),
        SkeletonSection("Common Pitfalls", 2, False,
                        "Performance anti-patterns to avoid", 50, 200),
        SkeletonSection("See Also", 2, False,
                        "Related performance and optimization guides", 0, 100),
    ],
}


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def get_skeleton(page_role: str) -> Optional[List[SkeletonSection]]:
    """Return the skeleton for a page role, or None if not registered.

    Args:
        page_role: One of the 17 canonical page roles.

    Returns:
        List of SkeletonSection in canonical order, or None.
    """
    return PAGE_ROLE_SKELETONS.get(page_role)


def get_required_headings(page_role: str) -> List[str]:
    """Return just the required heading texts for a page role.

    Args:
        page_role: One of the 17 canonical page roles.

    Returns:
        List of heading strings that are marked required, in order.
    """
    skeleton = get_skeleton(page_role)
    if skeleton is None:
        return []
    return [s.heading for s in skeleton if s.required]


def render_skeleton_markdown(skeleton: List[SkeletonSection]) -> str:
    """Render a skeleton as markdown headings with FILL markers.

    Used to inject skeleton structure into LLM prompts so the LLM
    knows the expected section order.

    Args:
        skeleton: List of SkeletonSection.

    Returns:
        Markdown string with headings and ``<!-- FILL: hint -->`` markers.
    """
    lines: List[str] = []
    for section in skeleton:
        prefix = "#" * section.level
        req_tag = " (required)" if section.required else " (optional)"
        lines.append(f"{prefix} {section.heading}")
        lines.append(f"<!-- FILL: {section.content_hint}{req_tag} -->")
        lines.append("")
    return "\n".join(lines)


def validate_against_skeleton(
    content: str,
    skeleton: List[SkeletonSection],
) -> List[Dict[str, Any]]:
    """Validate generated content against a skeleton template.

    Checks:
    1. All required sections are present (case-insensitive heading match).
    2. "See Also" (if present in skeleton) is the last H2.
    3. No duplicate H2 headings.

    Args:
        content: Generated markdown content.
        skeleton: Expected skeleton sections.

    Returns:
        List of issue dicts: ``{"type": "error"|"warning", "message": str}``.
        Empty list means content passes validation.
    """
    issues: List[Dict[str, Any]] = []

    # Extract H2 headings from content (ignore code fences)
    h2_headings = _extract_h2_headings(content)
    h2_lower = [h.lower().strip() for h in h2_headings]

    # 1. Check required sections are present
    for section in skeleton:
        if not section.required:
            continue
        if section.heading.lower() not in h2_lower:
            issues.append({
                "type": "error",
                "message": f"Missing required section: ## {section.heading}",
            })

    # 2. Check "See Also" is last H2 (if skeleton defines it and content has it)
    skeleton_has_see_also = any(
        s.heading.lower() == "see also" for s in skeleton
    )
    if skeleton_has_see_also and "see also" in h2_lower:
        last_idx = len(h2_lower) - 1
        see_also_indices = [i for i, h in enumerate(h2_lower) if h == "see also"]
        if see_also_indices:
            last_see_also = see_also_indices[-1]
            if last_see_also != last_idx:
                issues.append({
                    "type": "error",
                    "message": "\"See Also\" must be the last H2 section",
                })

    # 3. Check for duplicate H2 headings
    seen: Dict[str, int] = {}
    for h in h2_lower:
        seen[h] = seen.get(h, 0) + 1
    for heading, count in seen.items():
        if count > 1:
            issues.append({
                "type": "error",
                "message": f"Duplicate H2 heading: \"{heading}\" appears {count} times",
            })

    return issues


def _extract_h2_headings(content: str) -> List[str]:
    """Extract H2 heading texts from markdown, skipping code fences.

    Args:
        content: Markdown content.

    Returns:
        List of H2 heading texts (without the ``## `` prefix).
    """
    headings: List[str] = []
    in_fence = False

    for line in content.split("\n"):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        # Match ## Heading but not ### Heading
        m = re.match(r"^##\s+(.+)$", line)
        if m and not line.lstrip().startswith("###"):
            headings.append(m.group(1).strip())

    return headings
