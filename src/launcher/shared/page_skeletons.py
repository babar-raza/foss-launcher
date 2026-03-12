"""Deterministic page-role skeleton templates.

Each page role defines an ordered list of H2 sections that represent the
canonical document structure.  The LLM generates prose WITHIN sections but
cannot add, remove, or reorder them.

The skeleton is the single source of truth for document structure -- it
enforces the spec contract at specs/07_section_templates.md.
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
# Skeleton registry -- one entry per canonical page_role (17 roles)
# ---------------------------------------------------------------------------

PAGE_ROLE_SKELETONS: Dict[str, List[SkeletonSection]] = {

    # -- Products / Marketing --

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

    # -- Docs --

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
                        "What this workflow accomplishes", 50, 200),
        SkeletonSection("Key Features", 2, True,
                        "Key features as a bulleted list", 100, 300),
        SkeletonSection("Prerequisites", 2, True,
                        "Required setup and knowledge", 30, 100),
        SkeletonSection("Code Examples", 2, True,
                        "Runnable code examples", 50, 300),
        SkeletonSection("Notes and Best Practices", 2, False,
                        "Notes, remarks, and best practices", 30, 200),
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

    # -- Reference --

    "api_reference": [
        SkeletonSection("Overview", 2, True,
                        "Class or module purpose in 1-3 sentences", 30, 100),
        SkeletonSection("Constructors", 2, False,
                        "Constructor signatures and parameters", 50, 200),
        SkeletonSection("Properties", 2, False,
                        "Property table: name, type, description", 50, 400),
        SkeletonSection("Methods", 2, True,
                        "Method table: signature, return type, description", 50, 400),
        SkeletonSection("Code Examples", 2, True,
                        "Runnable code example using canonical import", 50, 300),
        SkeletonSection("Remarks", 2, False,
                        "Notes, remarks, and best practices", 30, 200),
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

    # -- KB --

    "faq": [
        SkeletonSection("Frequently Asked Questions", 2, True,
                        "Q&A pairs as H3 sub-sections -- each question is an H3", 100, 600),
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
        SkeletonSection("Problem", 2, True,
                        "What the reader will accomplish", 20, 60),
        SkeletonSection("Prerequisites", 2, True,
                        "Required setup and knowledge", 30, 100),
        SkeletonSection("Solution Steps", 2, True,
                        "Step-by-step instructions with code", 100, 400),
        SkeletonSection("Code Example", 2, True,
                        "Complete working example", 50, 300),
        SkeletonSection("Troubleshooting", 2, False,
                        "Common issues and solutions", 50, 200),
        SkeletonSection("See Also", 2, False,
                        "Related how-to articles", 0, 100),
    ],

    # -- Blog --

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

    # -- Specialized --

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
# Topic-aware skeleton variants (TC-3799)
# ---------------------------------------------------------------------------

# Maps ruleset topic_category values to skeleton variant tags.
TOPIC_CATEGORY_MAP: Dict[str, str] = {
    "load_file": "load_file",
    "save_file": "save_file",
    "convert_formats": "convert_formats",
    "troubleshoot": "troubleshoot",
    "optimize_performance": "optimize_performance",
}

# Maps slug substrings to topic tags for pages without explicit topic_category.
# Checked in order; first match wins.  Matching uses segment boundaries
# (start-of-string or hyphen) to avoid false positives like "uninstall".
SLUG_TOPIC_PATTERNS: List[tuple[str, str]] = [
    ("install", "install"),
    ("getting-started", "getting_started"),
    ("spreadsheet-operation", "data_operations"),
    ("notebook-manipulation", "data_operations"),
    ("document-editing", "data_operations"),
    ("pdf-manipulation", "data_operations"),
    ("slide-manipulation", "data_operations"),
    ("model-loading", "data_operations"),
    ("form-filling", "data_operations"),
    ("presentation-creation", "data_operations"),
    ("formula-calculation", "computation"),
    ("rendering", "computation"),
    ("mail-merge", "computation"),
    ("document-conversion", "convert_formats"),
]

# Differentiated skeletons keyed by (page_role, topic_tag).
# Only non-default variants are stored here; defaults live in PAGE_ROLE_SKELETONS.
SKELETON_VARIANTS: Dict[tuple[str, str], List[SkeletonSection]] = {

    # -- workflow_page variants --

    ("workflow_page", "install"): [
        SkeletonSection("System Requirements", 2, True,
                        "Minimum Python version, OS compatibility, and system dependencies", 30, 100),
        SkeletonSection("Installation", 2, True,
                        "pip install command and alternative installation methods", 50, 200),
        SkeletonSection("Verify Installation", 2, True,
                        "Short script to verify the install succeeded and print version", 30, 100),
        SkeletonSection("Quick Start", 2, True,
                        "Minimal working code example after installation", 50, 200),
        SkeletonSection("See Also", 2, False,
                        "Links to getting started guide and documentation", 0, 100),
    ],

    ("workflow_page", "getting_started"): [
        SkeletonSection("Overview", 2, True,
                        "What the reader will build or achieve by the end of this guide", 50, 150),
        SkeletonSection("Prerequisites", 2, True,
                        "Required installation, environment setup, and prior knowledge", 30, 100),
        SkeletonSection("First Steps", 2, True,
                        "Minimal step-by-step walkthrough to create something "
                        "useful — load a file, produce output, or call a core API", 100, 400),
        SkeletonSection("Code Example", 2, True,
                        "Complete runnable starter example the reader can copy and run", 50, 300),
        SkeletonSection("Next Steps", 2, True,
                        "Where to go from here: links to tutorials, guides, and API reference", 30, 100),
        SkeletonSection("See Also", 2, False,
                        "Links to installation guide and documentation index", 0, 100),
    ],

    ("workflow_page", "data_operations"): [
        SkeletonSection("Overview", 2, True,
                        "What data operations this page covers and when to use them", 50, 150),
        SkeletonSection("Working with Data", 2, True,
                        "Core data manipulation operations: reading, writing, modifying "
                        "cells/sheets/elements with code examples for each", 150, 400),
        SkeletonSection("Code Examples", 2, True,
                        "Complete runnable examples showing typical data workflows", 50, 300),
        SkeletonSection("Notes and Best Practices", 2, False,
                        "Performance tips, memory management, and common pitfalls", 30, 200),
        SkeletonSection("See Also", 2, False,
                        "Related data operation guides and API reference", 0, 100),
    ],

    ("workflow_page", "computation"): [
        SkeletonSection("Overview", 2, True,
                        "What computation or processing this page covers", 50, 150),
        SkeletonSection("Core Concepts", 2, True,
                        "Key concepts: engines, models, or algorithms the user must "
                        "understand before implementing", 80, 300),
        SkeletonSection("Implementation", 2, True,
                        "Step-by-step implementation with code for each stage", 100, 400),
        SkeletonSection("Code Examples", 2, True,
                        "Complete end-to-end runnable example", 50, 300),
        SkeletonSection("See Also", 2, False,
                        "Related computation guides and advanced topics", 0, 100),
    ],

    # -- howto_article variants --

    ("howto_article", "load_file"): [
        SkeletonSection("Problem", 2, True,
                        "State concisely: loading a specific file type into the library", 20, 60),
        SkeletonSection("Prerequisites", 2, True,
                        "Required installation and import statements", 30, 80),
        SkeletonSection("Loading the File", 2, True,
                        "Show how to load the file with code — cover file paths, "
                        "streams, and load options", 100, 350),
        SkeletonSection("Code Example", 2, True,
                        "Complete runnable example: load, inspect, print summary", 50, 300),
        SkeletonSection("Supported Formats", 2, False,
                        "Table of supported input formats: format name, extension, notes", 30, 150),
        SkeletonSection("See Also", 2, False,
                        "Related: saving, converting, and format-specific guides", 0, 100),
    ],

    ("howto_article", "save_file"): [
        SkeletonSection("Problem", 2, True,
                        "State concisely: saving or exporting to a specific format", 20, 60),
        SkeletonSection("Prerequisites", 2, True,
                        "Required installation and a loaded document/workbook", 30, 80),
        SkeletonSection("Saving the File", 2, True,
                        "Show how to save with code — cover format selection, "
                        "save options, and output paths", 100, 350),
        SkeletonSection("Code Example", 2, True,
                        "Complete runnable example: create/load, modify, save", 50, 300),
        SkeletonSection("Output Options", 2, False,
                        "Available output formats and configuration parameters", 30, 150),
        SkeletonSection("See Also", 2, False,
                        "Related: loading, converting, and format-specific guides", 0, 100),
    ],

    ("howto_article", "convert_formats"): [
        SkeletonSection("Problem", 2, True,
                        "State concisely: converting between two specific formats", 20, 60),
        SkeletonSection("Prerequisites", 2, True,
                        "Required installation and input file", 30, 80),
        SkeletonSection("Conversion Steps", 2, True,
                        "Step-by-step: load source, configure options, save to target "
                        "format with code at each step", 100, 400),
        SkeletonSection("Code Example", 2, True,
                        "Complete runnable conversion example end-to-end", 50, 300),
        SkeletonSection("Supported Formats", 2, False,
                        "Table of supported conversion pairs: from, to, notes", 30, 150),
        SkeletonSection("See Also", 2, False,
                        "Related conversion guides and format documentation", 0, 100),
    ],

    ("howto_article", "troubleshoot"): [
        SkeletonSection("Problem", 2, True,
                        "State the error or unexpected behavior the reader encounters", 20, 60),
        SkeletonSection("Symptoms", 2, True,
                        "Observable symptoms: error messages, stack traces, or "
                        "incorrect output the reader will recognize", 50, 150),
        SkeletonSection("Root Cause", 2, True,
                        "Explain why the problem occurs — reference specific API "
                        "behavior, configuration, or environment issues", 50, 200),
        SkeletonSection("Solution Steps", 2, True,
                        "Step-by-step fix with code at each step", 100, 400),
        SkeletonSection("Code Example", 2, True,
                        "Complete working example demonstrating the fix", 50, 300),
        SkeletonSection("See Also", 2, False,
                        "Related troubleshooting articles and FAQ", 0, 100),
    ],

    ("howto_article", "optimize_performance"): [
        SkeletonSection("Problem", 2, True,
                        "State the performance issue: slow processing, high memory, etc.", 20, 60),
        SkeletonSection("Prerequisites", 2, True,
                        "Required setup and baseline measurement approach", 30, 100),
        SkeletonSection("Optimization Steps", 2, True,
                        "Concrete optimization techniques with before/after code "
                        "examples for each technique", 100, 400),
        SkeletonSection("Code Example", 2, True,
                        "Complete optimized example with timing/measurement code", 50, 300),
        SkeletonSection("Benchmarks", 2, False,
                        "Show measurable improvements: timing comparisons, memory "
                        "reduction, or throughput gains", 30, 150),
        SkeletonSection("See Also", 2, False,
                        "Related performance guides and best practices", 0, 100),
    ],

    # -- api_reference index variant (used when per_module sub-pages exist) --

    ("api_reference", "index"): [
        SkeletonSection("Overview", 2, True,
                        "What this library provides — 1-3 sentences", 30, 100),
        SkeletonSection("Public API", 2, True,
                        "Table of public classes with one-line descriptions "
                        "and links to dedicated reference pages", 50, 400),
        SkeletonSection("Common Patterns", 2, False,
                        "Brief examples of the most common usage patterns", 50, 200),
        SkeletonSection("See Also", 2, False,
                        "Links to getting started and tutorials", 0, 100),
    ],

    # -- feature_blog scenario variants (TC-HYBRID-09) --

    ("feature_blog", "tutorial"): [
        SkeletonSection("Introduction", 2, True,
                        "What this tutorial covers and what the reader will build", 50, 200),
        SkeletonSection("Prerequisites", 2, True,
                        "Required packages, tools, and setup steps", 50, 150),
        SkeletonSection("Step-by-Step Guide", 2, True,
                        "Sequential numbered steps with code at each step", 200, 600),
        SkeletonSection("Code Example", 2, True,
                        "Complete, runnable code example demonstrating the feature", 100, 400),
        SkeletonSection("Result", 2, False,
                        "What the output looks like and how to verify success", 30, 150),
        SkeletonSection("See Also", 2, False,
                        "Links to API reference and related tutorials", 0, 100),
    ],

    ("feature_blog", "migration"): [
        SkeletonSection("Introduction", 2, True,
                        "What is changing and why this migration is beneficial", 50, 200),
        SkeletonSection("Why Migrate", 2, True,
                        "Benefits and motivation for migrating from the old approach", 100, 300),
        SkeletonSection("Migration Steps", 2, True,
                        "Step-by-step migration procedure with before/after examples", 200, 600),
        SkeletonSection("Code Comparison", 2, False,
                        "Side-by-side comparison of old and new code", 100, 400),
        SkeletonSection("Validation", 2, False,
                        "How to verify the migration succeeded", 50, 200),
        SkeletonSection("See Also", 2, False,
                        "Links to changelog and compatibility guide", 0, 100),
    ],
}


def _slug_matches_pattern(slug: str, pattern: str) -> bool:
    """Check if *pattern* appears in *slug* at a segment boundary.

    A segment boundary is the start/end of the string or a hyphen.
    This prevents ``"install"`` from matching ``"uninstall"`` while still
    matching ``"installation"`` and ``"install-guide"``.
    """
    idx = slug.find(pattern)
    if idx < 0:
        return False
    # Left boundary: start of string or preceded by hyphen
    if idx > 0 and slug[idx - 1] != "-":
        return False
    return True


def resolve_topic_tag(
    page_role: str,
    topic_category: Optional[str] = None,
    slug: str = "",
) -> str:
    """Determine the skeleton variant tag from available signals.

    Priority:
    1. Explicit ``topic_category`` from the ruleset
    2. Well-known slug pattern matching
    3. ``"default"`` fallback
    """
    # 1. Direct topic_category mapping
    if topic_category and topic_category in TOPIC_CATEGORY_MAP:
        return TOPIC_CATEGORY_MAP[topic_category]

    # 2. Slug-based inference (segment-boundary matching)
    if slug:
        slug_lower = slug.lower()
        for pattern, tag in SLUG_TOPIC_PATTERNS:
            if _slug_matches_pattern(slug_lower, pattern):
                return tag

    return "default"


def resolve_skeleton(
    page_role: str,
    topic_tag: str = "default",
) -> List[SkeletonSection]:
    """Look up skeleton by ``(page_role, topic_tag)``.

    Falls back to ``PAGE_ROLE_SKELETONS[page_role]`` when no variant is
    registered for the given tag, then to a single generic section.
    """
    if topic_tag != "default":
        variant = SKELETON_VARIANTS.get((page_role, topic_tag))
        if variant:
            return variant

    # Default: use the canonical skeleton for this role
    default = PAGE_ROLE_SKELETONS.get(page_role)
    if default is not None:
        return default

    # Ultimate fallback
    return [SkeletonSection("Content", 2, True, "Page content", 50, 500)]


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
