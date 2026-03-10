"""Format truth gate (TC-HYBRID-06).

Verifies that format names mentioned prominently in generated content are
backed by extracted evidence in the FormatRecord matrix. Flags formats that
appear 2+ times in prose but have zero test evidence (test_count=0 AND no
capability flags set).
"""
from __future__ import annotations

import re
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from launcher.models.product import ApiSurface

from launcher.models.evaluation import Finding

logger = logging.getLogger(__name__)

# Fallback pattern when no format_matrix is available
_FALLBACK_FORMAT_MENTION_RE = re.compile(
    r'\b(OBJ|FBX|GLTF|GLB|STL|DAE|USD|USDZ|DXF|PLY|'
    r'PDF|DOCX|XLSX|PPTX|HTML|RTF|CSV|ODS|PNG|JPEG|JPG|BMP|TIFF|SVG|WEBP|'
    r'ONE|ONETOC2|IGES|STEP|IFC|DWG)\b',
    re.IGNORECASE,
)


def _build_format_mention_re(format_matrix: list) -> re.Pattern:
    """Build a regex dynamically from format_matrix names and extensions.

    Falls back to hardcoded pattern when the matrix is empty or produces
    no usable names.
    """
    names: set[str] = set()
    for fr in format_matrix:
        if fr.name:
            names.add(re.escape(fr.name.upper()))
        if fr.extension:
            ext = fr.extension.lstrip(".").upper()
            if ext:
                names.add(re.escape(ext))
    if not names:
        return _FALLBACK_FORMAT_MENTION_RE
    pattern = r'\b(' + '|'.join(sorted(names)) + r')\b'
    return re.compile(pattern, re.IGNORECASE)


def check_format_truth(
    content: str,
    slug: str,
    *,
    api_surface: "ApiSurface | None" = None,
) -> "list[Finding]":
    """Check that format names mentioned in content are backed by evidence.

    Only fires when a format:
    1. Is mentioned prominently in prose (>=2 occurrences outside code blocks)
    2. Exists in format_matrix (don't penalise unknown formats)
    3. Has test_count=0 AND can_import=False AND can_export=False (zero evidence)

    This gate is informational (LOW severity) — not blocking.

    Args:
        content: Generated markdown content.
        slug: Page slug for Finding location.
        api_surface: ApiSurface with format_matrix from TC-HYBRID-03.

    Returns:
        List of LOW-severity Findings for prominently-mentioned zero-evidence
        formats. Returns [] when api_surface is None or format_matrix empty.
    """
    if api_surface is None:
        return []

    format_matrix = getattr(api_surface, "format_matrix", [])
    if not format_matrix:
        return []

    # Build zero-evidence set: formats in the matrix with no capability and no tests
    zero_evidence_formats: set[str] = set()
    known_formats: set[str] = set()
    for fr in format_matrix:
        name_upper = fr.name.upper()
        known_formats.add(name_upper)
        if fr.extension:
            ext_upper = fr.extension.lstrip(".").upper()
            if ext_upper:
                known_formats.add(ext_upper)

        has_evidence = (
            fr.test_count > 0
            or fr.can_import
            or fr.can_export
            or bool(fr.source_evidence)
        )
        if not has_evidence:
            zero_evidence_formats.add(name_upper)
            if fr.extension:
                ext_upper = fr.extension.lstrip(".").upper()
                if ext_upper:
                    zero_evidence_formats.add(ext_upper)

    # Count format mentions in prose only (skip code blocks)
    prose_lines: list[str] = []
    in_code_block = False
    for line in content.split("\n"):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if not in_code_block and not line.startswith("    "):
            prose_lines.append(stripped)

    prose = "\n".join(prose_lines)
    # Build regex dynamically from format_matrix; fall back to hardcoded list
    _format_re = _build_format_mention_re(format_matrix)
    format_mention_counts: dict[str, int] = {}
    for m in _format_re.finditer(prose):
        fmt = m.group(1).upper()
        format_mention_counts[fmt] = format_mention_counts.get(fmt, 0) + 1

    findings: list[Finding] = []
    for fmt, count in format_mention_counts.items():
        if count < 2:
            continue  # Only flag prominently mentioned formats (2+ mentions)
        if fmt not in known_formats:
            continue  # Not in format_matrix at all — don't penalise
        if fmt not in zero_evidence_formats:
            continue  # Format has evidence — OK

        findings.append(Finding(
            check="format_unsupported_claim",
            message=(
                f"Format {fmt} mentioned {count} times in prose "
                f"but has zero test evidence in extracted format matrix"
            ),
            severity="low",
            location=slug,
        ))

    if findings:
        logger.info(
            "format_truth: slug=%s low_evidence_formats=%d", slug, len(findings)
        )

    return findings
