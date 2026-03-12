"""Check 11: Semantic structure validation."""
from __future__ import annotations

import logging
import re

from launcher.models.evaluation import Finding

logger = logging.getLogger(__name__)

# Reference page roles use H2 → H3 structure (e.g. ## Constructors → ### Method()).
# The empty-section check is suppressed: H2 sections with only H3 sub-headings and no
# intro prose are expected structure for API reference docs, not a quality defect.
_REFERENCE_ROLES: frozenset[str] = frozenset({"api_reference", "reference_object_page"})

_TERMINAL_HEADINGS = frozenset({
    "see also",
    "references",
    "related topics",
    "further reading",
    "related links",
})


def check_semantic_structure(
    content: str, slug: str, *, page_role: str = ""
) -> list[Finding]:
    """Validate semantic structure: duplicates, terminal sections, empty sections."""
    logger.debug("[semantic_structure] Evaluating %s", slug)
    findings: list[Finding] = []

    body = re.sub(r"^---\n.*?\n---\n?", "", content, flags=re.DOTALL)
    lines = body.split("\n")

    # Extract headings with line indices and levels
    headings: list[tuple[int, int, str]] = []  # (line_idx, level, text)
    for idx, line in enumerate(lines):
        m = re.match(r"^(#{2,3})\s+(.+)$", line)
        if m:
            headings.append((idx, len(m.group(1)), m.group(2).strip()))

    if not headings:
        logger.debug("[semantic_structure] No headings found, skipping for %s", slug)
        return findings

    # --- Duplicate section detection ---
    seen_by_level: dict[int, dict[str, int]] = {}
    for _, level, text in headings:
        normalised = text.lower().strip()
        level_seen = seen_by_level.setdefault(level, {})
        if normalised in level_seen:
            findings.append(
                Finding(
                    check="semantic_structure",
                    message=f"Duplicate H{level} heading: '{text}'",
                    severity="high",
                    location=slug,
                )
            )
        else:
            level_seen[normalised] = 1

    # --- Content after terminal sections ---
    for i, (line_idx, level, text) in enumerate(headings):
        normalised = text.lower().strip()
        if normalised not in _TERMINAL_HEADINGS:
            continue

        # Find next heading at the same or higher (lower number) level
        terminal_end = len(lines)
        for j in range(i + 1, len(headings)):
            if headings[j][1] <= level:
                terminal_end = headings[j][0]
                break

        # Check if there are further same-level headings after the terminal
        for j in range(i + 1, len(headings)):
            next_idx, next_level, next_text = headings[j]
            if next_level == level and next_idx >= terminal_end:
                # Substantive content after terminal section at same level
                section_start = next_idx + 1
                section_end = len(lines)
                for k in range(j + 1, len(headings)):
                    if headings[k][1] <= next_level:
                        section_end = headings[k][0]
                        break
                section_text = "\n".join(lines[section_start:section_end])
                # Strip links for word counting
                prose = re.sub(r"\[.*?\]\(.*?\)", "", section_text)
                prose = re.sub(r"https?://\S+", "", prose)
                word_count = len(prose.split())
                if word_count > 20:
                    findings.append(
                        Finding(
                            check="semantic_structure",
                            message=(
                                f"Substantive content ({word_count} words) in "
                                f"'{next_text}' after terminal section '{text}'"
                            ),
                            severity="high",
                            location=slug,
                        )
                    )
                break  # only flag the first violation per terminal heading

    # --- Empty sections ---
    # Skipped for reference pages: H2 sections (## Constructors, ## Properties, etc.)
    # go directly to H3 sub-headings with no intro prose — this is expected structure
    # for API reference docs and is not a quality defect.
    if page_role in _REFERENCE_ROLES:
        logger.debug("[semantic_structure] Skipping empty-section check for reference page: %s", slug)
    if page_role not in _REFERENCE_ROLES:
        for i, (line_idx, level, text) in enumerate(headings):
            # Find the next heading's line index
            if i + 1 < len(headings):
                next_line = headings[i + 1][0]
            else:
                next_line = len(lines)

            # Content between this heading and the next
            between = "\n".join(lines[line_idx + 1 : next_line]).strip()
            # H2 sections that go directly to H3 sub-headings are valid structure
            # (e.g. "## Optimization Steps" → "### Step 1", "### Step 2").
            # The sub-headings are the content. Same logic used for _REFERENCE_ROLES.
            # TC-3889.
            next_is_subsection = i + 1 < len(headings) and headings[i + 1][1] > level
            if not between and not next_is_subsection:
                findings.append(
                    Finding(
                        check="semantic_structure",
                        message=f"Empty section under heading: '{text}'",
                        severity="medium",
                        location=slug,
                    )
                )

    logger.debug("[semantic_structure] Found %d findings for %s", len(findings), slug)
    return findings
