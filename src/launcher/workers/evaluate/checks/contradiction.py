"""Format contradiction gate (TC-HYBRID-06).

Scans generated text for format capability claims and cross-references
against the FormatRecord matrix from ApiSurface.
"""
from __future__ import annotations

import re
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from launcher.models.product import ApiSurface

from launcher.models.evaluation import Finding

logger = logging.getLogger(__name__)

# Patterns that claim export capability — group 1 is the format name when capturable
_EXPORT_CLAIM_PATTERNS = [
    re.compile(
        r'\b(?:can|supports?|allows?|enables?)\s+(?:export(?:ing)?|sav(?:e|ing))\s+(?:to\s+)?(\w+)',
        re.IGNORECASE,
    ),
    re.compile(
        r'\bexport(?:ing)?\s+(?:to\s+)?(\w+)\s+(?:is\s+)?supported',
        re.IGNORECASE,
    ),
    re.compile(
        r'(\w+)\s+(?:format\s+)?(?:can\s+be\s+)?export(?:ed)?',
        re.IGNORECASE,
    ),
]

# Patterns that claim import capability
_IMPORT_CLAIM_PATTERNS = [
    re.compile(
        r'\b(?:can|supports?|allows?|enables?)\s+(?:import(?:ing)?|load(?:ing)?|read(?:ing)?)\s+(?:from\s+)?(\w+)',
        re.IGNORECASE,
    ),
    re.compile(
        r'\bimport(?:ing)?\s+(?:from\s+)?(\w+)\s+(?:is\s+)?supported',
        re.IGNORECASE,
    ),
    re.compile(
        r'(\w+)\s+(?:format\s+)?(?:can\s+be\s+)?(?:import|load|read)(?:ed)?',
        re.IGNORECASE,
    ),
]


def check_contradiction(
    content: str,
    slug: str,
    *,
    api_surface: "ApiSurface | None" = None,
) -> "list[Finding]":
    """Check for format capability claims that contradict the FormatRecord matrix.

    For each format in api_surface.format_matrix, scans the generated content
    for explicit capability claims and flags contradictions.

    Args:
        content: Generated markdown content.
        slug: Page slug for Finding location.
        api_surface: ApiSurface with format_matrix from TC-HYBRID-03.

    Returns:
        List of Findings. MEDIUM severity when text contradicts format matrix.
        Returns [] when api_surface is None or format_matrix is empty.
    """
    if api_surface is None:
        return []

    format_matrix = getattr(api_surface, "format_matrix", [])
    if not format_matrix:
        return []

    # Build format name → FormatRecord lookup (by name and by extension)
    fmt_lookup: dict[str, object] = {}
    for fr in format_matrix:
        fmt_lookup[fr.name.upper()] = fr
        if fr.extension:
            ext_upper = fr.extension.lstrip(".").upper()
            if ext_upper:
                fmt_lookup[ext_upper] = fr

    findings: list[Finding] = []

    # Scan prose lines (skip code blocks and headings)
    in_code_block = False
    for line in content.split("\n"):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        if not stripped or stripped.startswith("#"):
            continue
        # Skip indented code (4-space style)
        if line.startswith("    "):
            continue

        line_upper = line.upper()

        for fmt_name, fmt_record in fmt_lookup.items():
            if fmt_name not in line_upper:
                continue

            # Check for export contradiction
            if not fmt_record.can_export:
                for pat in _EXPORT_CLAIM_PATTERNS:
                    m = pat.search(line)
                    if m:
                        captured = m.group(1).upper() if m.lastindex else ""
                        # The captured word must itself be a known format name
                        # to avoid false positives like "Data can be exported".
                        captured_is_format = captured in fmt_lookup if captured else False
                        if captured_is_format and fmt_name in captured:
                            findings.append(Finding(
                                check="format_contradiction_export",
                                message=(
                                    f"Content claims {fmt_name} can be exported, "
                                    f"but FormatRecord.can_export=False"
                                ),
                                severity="medium",
                                location=slug,
                            ))
                            break  # one finding per format per line

            # Check for import contradiction
            if not fmt_record.can_import:
                for pat in _IMPORT_CLAIM_PATTERNS:
                    m = pat.search(line)
                    if m:
                        captured = m.group(1).upper() if m.lastindex else ""
                        captured_is_format = captured in fmt_lookup if captured else False
                        if captured_is_format and fmt_name in captured:
                            findings.append(Finding(
                                check="format_contradiction_import",
                                message=(
                                    f"Content claims {fmt_name} can be imported/loaded, "
                                    f"but FormatRecord.can_import=False"
                                ),
                                severity="medium",
                                location=slug,
                            ))
                            break  # one finding per format per line

    # Deduplicate by (check, message) key
    seen: set[str] = set()
    unique: list[Finding] = []
    for f in findings:
        key = f"{f.check}:{f.message}"
        if key not in seen:
            seen.add(key)
            unique.append(f)

    if unique:
        logger.info("format_contradiction: slug=%s findings=%d", slug, len(unique))

    return unique
