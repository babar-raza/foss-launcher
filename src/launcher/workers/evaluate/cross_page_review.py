"""Cross-page consistency review (TC-HYBRID-08).

Detects contradicting format capability claims across evaluated pages.
Only runs on NO_GO verdicts to avoid overhead on healthy runs.
"""
from __future__ import annotations

import re
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from launcher.models.evaluation import Finding

logger = logging.getLogger(__name__)

# Format extensions to scan for (must be upper-case in output)
_FORMAT_NAMES: frozenset[str] = frozenset({
    "OBJ", "FBX", "GLTF", "GLB", "STL", "3DS", "DAE", "PLY", "DRC",
    "PDF", "DOCX", "XLSX", "PPTX", "HTML", "PNG", "JPG", "JPEG", "SVG",
    "ZIP", "CSV", "JSON", "XML", "YAML",
})

# Patterns that signal "format CAN be exported/saved"
_EXPORT_POSITIVE_RE = re.compile(
    r'\b(?:can (?:be )?(?:export|save|write|output)|supports? (?:export|saving|writing|output)'
    r'|(?:export|save|write|output) (?:to|as|in))',
    re.IGNORECASE,
)

# Patterns that signal "format CANNOT be exported/saved"
_EXPORT_NEGATIVE_RE = re.compile(
    r'\b(?:cannot (?:be )?(?:export|save|write|output)|does not support (?:export|saving|writing|output)'
    r'|not (?:support(?:ed)?|available)(?: for)? (?:export|saving)|(?:export|save) (?:is )?not supported)',
    re.IGNORECASE,
)

# Patterns that signal "format CAN be imported/loaded"
_IMPORT_POSITIVE_RE = re.compile(
    r'\b(?:can (?:be )?(?:import|load|read)|supports? (?:import|loading|reading)'
    r'|(?:import|load|read) (?:from|as|in))',
    re.IGNORECASE,
)

# Patterns that signal "format CANNOT be imported/loaded"
_IMPORT_NEGATIVE_RE = re.compile(
    r'\b(?:cannot (?:be )?(?:import|load|read)|does not support (?:import|loading|reading)'
    r'|not (?:support(?:ed)?|available)(?: for)? (?:import|loading)|(?:import|load) (?:is )?not supported)',
    re.IGNORECASE,
)

# Qualification words that soften a negative claim — if present after the
# negation match, treat the statement as "unknown" rather than "no".
_QUALIFICATION_RE = re.compile(
    r'\b(?:without|yet|directly|currently|unless|natively|by default)\b',
    re.IGNORECASE,
)

_MAX_PAGE_PAIRS: int = 20


def _extract_format_claims(content: str) -> dict[str, dict[str, str]]:
    """Extract format capability claims from content.

    Returns: {format_name: {"export": "yes"|"no"|"unknown", "import": "yes"|"no"|"unknown"}}
    """
    results: dict[str, dict[str, str]] = {}

    for line in content.splitlines():
        # Skip code blocks and headings
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("#") or stripped.startswith("    "):
            continue

        line_upper = line.upper()
        for fmt in _FORMAT_NAMES:
            if fmt not in line_upper:
                continue
            # Check if line mentions this format as a word boundary
            if not re.search(r'\b' + fmt + r'\b', line_upper):
                continue

            if fmt not in results:
                results[fmt] = {"export": "unknown", "import": "unknown"}

            if _EXPORT_POSITIVE_RE.search(line):
                results[fmt]["export"] = "yes"
            elif _EXPORT_NEGATIVE_RE.search(line):
                # Qualified negatives (e.g. "cannot export without conversion")
                # are ambiguous — treat as unknown, not flat "no".
                if _QUALIFICATION_RE.search(line):
                    pass  # leave as "unknown"
                else:
                    results[fmt]["export"] = "no"

            if _IMPORT_POSITIVE_RE.search(line):
                results[fmt]["import"] = "yes"
            elif _IMPORT_NEGATIVE_RE.search(line):
                if _QUALIFICATION_RE.search(line):
                    pass  # leave as "unknown"
                else:
                    results[fmt]["import"] = "no"

    return results


def run_cross_page_review(
    content_map: dict[str, str],
) -> "list[Finding]":
    """Scan all pages for contradicting format capability claims.

    Args:
        content_map: slug -> markdown content for each evaluated page

    Returns:
        List of HIGH-severity Finding objects for each contradiction found.
    """
    from launcher.models.evaluation import Finding

    if not content_map:
        return []

    # Extract format claims per page
    page_claims: dict[str, dict[str, dict[str, str]]] = {}
    for slug, content in content_map.items():
        claims = _extract_format_claims(content)
        if claims:
            page_claims[slug] = claims

    if len(page_claims) < 2:
        return []

    findings: list[Finding] = []
    seen_contradictions: set[tuple[str, str, frozenset[str]]] = set()
    pair_count = 0

    slugs = list(page_claims.keys())
    for i, slug_a in enumerate(slugs):
        for slug_b in slugs[i + 1:]:
            if pair_count >= _MAX_PAGE_PAIRS:
                logger.debug("cross_page_review: pair cap reached (%d)", _MAX_PAGE_PAIRS)
                return findings
            pair_count += 1

            claims_a = page_claims[slug_a]
            claims_b = page_claims[slug_b]

            for fmt in set(claims_a) & set(claims_b):
                for capability in ("export", "import"):
                    val_a = claims_a[fmt].get(capability, "unknown")
                    val_b = claims_b[fmt].get(capability, "unknown")

                    if val_a == "unknown" or val_b == "unknown":
                        continue
                    if val_a == val_b:
                        continue

                    # Contradiction found
                    key = (fmt, capability, frozenset([slug_a, slug_b]))
                    if key in seen_contradictions:
                        continue
                    seen_contradictions.add(key)

                    findings.append(Finding(
                        check="cross_page_consistency",
                        message=(
                            f"Format {fmt} {capability} capability contradicts across pages: "
                            f"'{slug_a}' says {val_a}, '{slug_b}' says {val_b}"
                        ),
                        severity="high",
                        location=f"{slug_a} vs {slug_b}",
                    ))
                    logger.info(
                        "cross_page_review contradiction: %s %s — %s=%s vs %s=%s",
                        fmt, capability, slug_a, val_a, slug_b, val_b,
                    )

    return findings
