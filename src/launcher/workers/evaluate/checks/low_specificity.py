"""Check: low_specificity — detect prose with only generic verbs and no concrete details (TC-PROSE-01).

Flags paragraphs where every sentence uses only generic verbs
(supports/provides/allows/enables/offers/helps) and contains no concrete
identifiers (backticked names, file extensions, numeric values).
"""
from __future__ import annotations

import re

from launcher.models.evaluation import Finding

_CODE_FENCE_RE = re.compile(r"```[\s\S]*?```", re.DOTALL)
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")

_EXEMPT_ROLES: frozenset[str] = frozenset({
    "api_reference", "reference_object_page", "toc",
})

# Generic verbs that don't convey specific information.
_GENERIC_VERBS: frozenset[str] = frozenset({
    "supports", "support", "supporting",
    "provides", "provide", "providing",
    "allows", "allow", "allowing",
    "enables", "enable", "enabling",
    "offers", "offer", "offering",
    "helps", "help", "helping",
    "includes", "include", "including",
    "features", "feature", "featuring",
    "handles", "handle", "handling",
    "facilitates", "facilitate", "facilitating",
})

# Patterns indicating concrete specificity.
_SPECIFICITY_PATTERNS = [
    re.compile(r"`[^`]+`"),                  # backticked identifiers
    re.compile(r"\.\w{2,5}\b"),              # file extensions (.xlsx, .csv, .py)
    re.compile(r"\b\d+\b"),                  # numeric values
    re.compile(r"[A-Z][a-z]+[A-Z]\w*"),      # PascalCase identifiers
    re.compile(r"\b\w+_\w+\b"),              # snake_case identifiers
    re.compile(r"\(\)"),                      # method call notation
]

# Minimum sentences in a paragraph to flag.
_MIN_SENTENCES = 3


def _has_specificity(text: str) -> bool:
    """Return True if text contains concrete technical details."""
    return any(pattern.search(text) for pattern in _SPECIFICITY_PATTERNS)


def _has_only_generic_verbs(sentence: str) -> bool:
    """Return True if the sentence's main verb is generic."""
    words = set(re.findall(r"\b[a-z]+\b", sentence.lower()))
    return bool(words & _GENERIC_VERBS)


def check_low_specificity(
    content: str,
    slug: str,
    *,
    page_role: str = "",
) -> list[Finding]:
    """Detect paragraphs that use only generic verbs without concrete details.

    Args:
        content: Rendered markdown content.
        slug: Page slug for Finding location.
        page_role: Page role (reference/toc roles exempt).

    Returns:
        List of MEDIUM Findings for low-specificity paragraphs.
    """
    if page_role in _EXEMPT_ROLES:
        return []

    # Strip frontmatter and code blocks
    body = re.sub(r"^---\n.*?\n---\n?", "", content, flags=re.DOTALL)
    body = _CODE_FENCE_RE.sub("\n\n", body)
    # Strip headings
    body = re.sub(r"^#{1,6}\s+.+$", "", body, flags=re.MULTILINE)

    # Split into paragraphs
    paragraphs = re.split(r"\n\s*\n", body)

    findings: list[Finding] = []

    for para in paragraphs:
        stripped = para.strip()
        if not stripped:
            continue
        # Skip lists and tables
        if stripped.startswith(("- ", "* ", "| ", "{{", "1.")):
            continue

        sentences = _SENTENCE_SPLIT.split(stripped)
        sentences = [s.strip() for s in sentences if len(s.split()) >= 4]

        if len(sentences) < _MIN_SENTENCES:
            continue

        # Check if ALL sentences use generic verbs AND paragraph lacks specificity
        all_generic = all(_has_only_generic_verbs(s) for s in sentences)
        no_specifics = not _has_specificity(stripped)

        if all_generic and no_specifics:
            findings.append(Finding(
                check="low_specificity",
                message=(
                    f"Low-specificity paragraph ({len(sentences)} sentences, all generic verbs, "
                    f"no concrete identifiers): \"{stripped[:80]}...\" — "
                    f"name specific classes, methods, formats, or outputs"
                ),
                severity="medium",
                location=slug,
            ))

    return findings
