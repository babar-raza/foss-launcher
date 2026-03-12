"""Check that generated content does not affirm known product limitations.

TC-HO-01: Emits LIMITATION_VIOLATED when page prose affirms a feature that
``product_evidence.limitations`` marks as ``unsupported`` or ``deprecated``.
"""
from __future__ import annotations

import logging
import re

from launcher.models.evaluation import Finding

logger = logging.getLogger(__name__)

# Statuses that indicate a feature is definitely NOT supported.
_BLOCKED_STATUSES: frozenset[str] = frozenset({"unsupported", "deprecated"})

# Words that negate a claim — if any appear in the same sentence/line,
# skip the affirmation match to avoid false positives like
# "this library does not support async".
_NEGATION_WORDS: frozenset[str] = frozenset({
    "not", "no", "never", "doesn't", "does not", "don't", "do not",
    "cannot", "can't", "won't", "will not", "isn't", "is not",
    "aren't", "are not", "wasn't", "wasn't", "weren't",
    "unsupported", "deprecated", "unavailable", "lack", "lacks",
    "missing", "absent", "limitation", "limitations",
})

# Affirmative language patterns indicating the feature is supported.
# The feature keyword will be substituted into these patterns at runtime.
_AFFIRMATION_TEMPLATES: list[str] = [
    r"\bsupports?\s+{feature}",
    r"\b{feature}\s+(?:is\s+)?supported",
    r"\bcan\s+(?:be\s+)?(?:used?\s+)?{feature}",
    r"\benables?\s+{feature}",
    r"\ballows?\s+{feature}",
    r"\buse\s+{feature}",
    r"\busing\s+{feature}",
    r"\b{feature}\s+(?:is\s+)?(?:now\s+)?available",
    r"\b{feature}\s+(?:mode|functionality|feature|support|api|calls?)\b",
    r"\bfully\s+supports?\s+{feature}",
    r"\b{feature}\s+(?:operations?|requests?|calls?)\b",
    r"\bprovides?\s+{feature}",
]


def _has_negation(line_lower: str) -> bool:
    """Return True if the line contains a negation word."""
    for word in _NEGATION_WORDS:
        if word in line_lower:
            return True
    return False


def _build_affirmation_patterns(feature: str) -> list[re.Pattern[str]]:
    """Build compiled regex patterns for a given feature keyword."""
    # Escape the feature for regex but preserve word boundaries
    escaped = re.escape(feature.lower())
    patterns = []
    for template in _AFFIRMATION_TEMPLATES:
        pattern_str = template.format(feature=escaped)
        patterns.append(re.compile(pattern_str, re.IGNORECASE))
    return patterns


def check_limitations_contradiction(
    content: str,
    slug: str,
    *,
    product_evidence: "dict | None" = None,
) -> "list[Finding]":
    """Emit LIMITATION_VIOLATED if content affirms a known unsupported/deprecated feature.

    Scans prose lines (code blocks excluded) for affirmative language about
    features listed in ``product_evidence["limitations"]`` where the limitation
    status is ``unsupported`` or ``deprecated``.

    A negation guard prevents false positives when the content correctly states
    that a feature is not supported (e.g., "does not support async").

    Args:
        content: Generated markdown content for the page.
        slug: Page slug for Finding location attribution.
        product_evidence: Dict loaded from understand_checkpoint.json. When None
            or empty, the check returns [] immediately.

    Returns:
        List of Findings. Each Finding has check="limitation_violated",
        severity="high". Returns [] when no violations found.
    """
    if not product_evidence:
        return []

    limitations_raw = product_evidence.get("limitations", [])
    if not limitations_raw:
        return []

    # Filter to only unsupported/deprecated limitations
    relevant: list[dict] = []
    for lim in limitations_raw:
        # Support both dict (from JSON checkpoint) and LimitationEntry model
        if hasattr(lim, "status"):
            status = lim.status
            feature = lim.feature
        else:
            status = lim.get("status", "warning")
            feature = lim.get("feature", "")
        if status in _BLOCKED_STATUSES and feature:
            relevant.append({"feature": feature, "status": status})

    if not relevant:
        return []

    # Strip code blocks from content before scanning prose
    prose = re.sub(r"```.*?```", "", content, flags=re.DOTALL)
    prose = re.sub(r"`[^`\n]+`", "", prose)

    findings: list[Finding] = []
    seen: set[str] = set()  # deduplicate by (feature, sentence)

    for lim in relevant:
        feature = lim["feature"]
        feature_lower = feature.lower()
        patterns = _build_affirmation_patterns(feature)

        for line in prose.split("\n"):
            stripped = line.strip()
            if not stripped:
                continue
            # Skip headings
            if stripped.startswith("#"):
                continue

            line_lower = stripped.lower()

            # Quick pre-filter: feature word must appear in line at all
            if feature_lower not in line_lower:
                continue

            # Negation guard: if any negation word is present, skip this line
            if _has_negation(line_lower):
                continue

            # Check affirmation patterns
            for pat in patterns:
                if pat.search(stripped):
                    dedup_key = f"{feature_lower}:{stripped[:80]}"
                    if dedup_key not in seen:
                        seen.add(dedup_key)
                        findings.append(Finding(
                            check="limitation_violated",
                            message=(
                                f"Content affirms '{feature}' which is {lim['status']}: "
                                f"\"{stripped[:120]}\""
                            ),
                            severity="high",
                            location=slug,
                        ))
                    break  # one finding per line per feature

    if findings:
        logger.warning(
            "[limitations_check] slug=%s violations=%d", slug, len(findings)
        )

    return findings
