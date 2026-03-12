"""Check 4: Content density check."""
from __future__ import annotations

import logging
import re

from launcher.models.evaluation import Finding

logger = logging.getLogger(__name__)

_MIN_WORD_COUNT = 100  # minimum for content pages (Tier A default / backward compat)
_MIN_SECTION_WORDS = 20  # minimum per section (Tier A default / backward compat)

# TC-HO-08B: Tier-aware density thresholds.
# Tier C repos have limited evidence — reduced minimums prevent false-positive findings
# on legitimately sparse content.  Tuple: (page_min_words, section_min_words).
_TIER_DENSITY: dict[str, tuple[int, int]] = {
    "A": (100, 20),
    "B": (80, 15),
    "C": (50, 10),
}

# Canonical placeholder strings checked in both reference and prose paths.
# Define once here so both code paths stay in sync automatically.
_PLACEHOLDER_STRINGS: tuple[str, ...] = (
    "[content to be generated]",
    "[todo]",
    "[tbd]",
    "[placeholder]",
    "lorem ipsum",
)

# TC-3895: Contextual referral-placeholder patterns.
# Matches natural-language deferrals that leave sections hollow despite looking like prose.
# Each pattern is anchored/bounded to avoid matching legitimate cross-references.
_REFERRAL_PATTERNS: tuple[re.Pattern, ...] = (
    re.compile(r"for (?:more )?details[,.]?\s+see\s+the\b", re.IGNORECASE),
    re.compile(r"refer(?:ence)? to (?:the )?(?:official\s+)?(?:\w+\s+){0,3}documentation", re.IGNORECASE),
    re.compile(r"see (?:the )?(?:official\s+)?(?:\w+\s+){0,3}documentation\s*(?:for|\.|\Z)", re.IGNORECASE),
    re.compile(r"for (?:more )?information[,.]?\s+(?:please\s+)?(?:see|visit|refer)\b", re.IGNORECASE),
    re.compile(r"(?:please\s+)?consult (?:the\s+)?(?:official\s+)?docs?\b", re.IGNORECASE),
)


def check_density(
    content: str, slug: str, *, page_role: str = "", richness_tier: str = "A"
) -> list[Finding]:
    """Check word count thresholds and empty sections.

    Reference pages (``api_reference``, ``reference_object_page``) and TOC pages
    skip the word-count and per-section density thresholds — sparse prose is
    expected for method stubs and navigation pages. Placeholder detection always
    runs regardless of page role, because placeholders are never acceptable.

    TC-HO-08B: ``richness_tier`` (one of "A", "B", "C") selects lower thresholds
    for repos with limited documentation.  Defaults to "A" for backward compatibility.
    """
    # TC-HO-08B: resolve tier-aware thresholds
    _page_min, _section_min = _TIER_DENSITY.get(richness_tier, _TIER_DENSITY["A"])

    findings: list[Finding] = []
    body = re.sub(r"^---\n.*?\n---\n?", "", content, flags=re.DOTALL)

    # Strip code blocks for word counting
    prose = re.sub(r"```.*?```", "", body, flags=re.DOTALL)
    words = prose.split()
    word_count = len(words)

    # Hoist lower_body once — used by both the reference path and the prose path.
    lower_body = body.lower()

    # Skip word-count threshold for TOC and reference pages.
    # Reference method stubs (e.g. Dispose()) have sparse prose by design;
    # placeholder detection still runs — placeholders are always wrong.
    _SKIP_WORD_COUNT = page_role in ("toc", "api_reference", "reference_object_page")

    if _SKIP_WORD_COUNT:
        logger.debug(
            "[density] Skipping word-count threshold for %s (page_role=%r)", slug, page_role
        )
        for ph in _PLACEHOLDER_STRINGS:
            if ph in lower_body:
                findings.append(
                    Finding(
                        check="density",
                        message=f"Placeholder text found: '{ph}'",
                        severity="high",
                        location=slug,
                    )
                )
        return findings

    if word_count < _page_min:
        findings.append(
            Finding(
                check="density",
                message=f"Page has {word_count} words (minimum {_page_min})",
                severity="high" if word_count < 50 else "medium",
                location=slug,
            )
        )

    # Check for placeholder text
    for ph in _PLACEHOLDER_STRINGS:
        if ph in lower_body:
            findings.append(
                Finding(
                    check="density",
                    message=f"Placeholder text found: '{ph}'",
                    severity="high",
                    location=slug,
                )
            )

    # Check per-section density and referral placeholders
    sections = re.split(r"^##\s+", body, flags=re.MULTILINE)
    for i, section in enumerate(sections[1:], 1):  # skip before first heading
        heading = section.split("\n", 1)[0].strip()
        section_prose = re.sub(r"```.*?```", "", section, flags=re.DOTALL)
        section_words = len(section_prose.split())
        if section_words < _section_min:
            findings.append(
                Finding(
                    check="density",
                    message=f"Section '{heading}' has only {section_words} words",
                    severity="low",
                    location=f"{slug}:section-{i}",
                    section_id=heading,
                )
            )

        # TC-3895: Detect documentation-referral placeholders in section prose.
        # One finding per section — stop at first match to avoid duplicate findings.
        for pattern in _REFERRAL_PATTERNS:
            if pattern.search(section_prose):
                findings.append(
                    Finding(
                        check="density",
                        message=(
                            f"Section '{heading}' contains a documentation-referral placeholder "
                            f"(matches pattern '{pattern.pattern[:50]}'). "
                            "Write the actual content inline instead of deferring to docs."
                        ),
                        severity="high",
                        location=f"{slug}:section-{i}",
                        section_id=heading,
                    )
                )
                break  # one finding per section is sufficient

    return findings
