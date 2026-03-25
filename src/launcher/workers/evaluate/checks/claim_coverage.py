"""Deterministic claim coverage check — verifies assigned claims are addressed in content.

TC-3880 Wave 2 (E4/F4): Deterministic check to surface pages that silently drop claims.
Phase B LLM review (optional) is the only other safety net for claim coverage, but it
is skipped in heal fast-path mode. This check ensures claim gaps are always visible.

Algorithm:
  1. Extract key terms from each claim: strip stopwords, keep tokens ≥4 chars,
     sort by length (longest first), take top 5 per claim.
  2. A claim is "covered" if 3-of-5 key terms appear anywhere in the page body
     (frontmatter and code blocks stripped to avoid false positives from imports).
  3. Severity based on fraction of uncovered claims:
     - CRITICAL: all claims uncovered (page is completely off-topic)
     - HIGH:     >50% of claims uncovered
     - MEDIUM:   2-3 claims uncovered
     - LOW:      1 claim uncovered
"""
from __future__ import annotations

import re
from typing import Sequence

from launcher.models.evaluation import Finding

# Stop-words stripped before key-term extraction
_STOP_WORDS: frozenset[str] = frozenset({
    "a", "an", "the", "and", "or", "of", "to", "in", "for", "on", "with",
    "at", "by", "from", "as", "is", "are", "was", "be", "it", "its",
    "this", "that", "can", "will", "may", "not", "also", "how", "what",
    "when", "where", "which", "use", "used", "using",
})

# Minimum meaningful token length for key-term extraction
_MIN_TERM_LEN: int = 4

# Number of key terms extracted per claim
_TERMS_PER_CLAIM: int = 5

# Number of key terms that must appear in body for a claim to be "covered"
_COVERAGE_THRESHOLD: int = 3

# Patterns for stripping frontmatter and code blocks before coverage scan
_FRONTMATTER_RE = re.compile(r"^---[\s\S]*?^---\s*\n", re.MULTILINE)
_CODE_FENCE_RE = re.compile(r"```[^\n]*\n[\s\S]*?```", re.DOTALL)


def _extract_key_terms(claim_text: str) -> list[str]:
    """Extract top key terms from a claim text string.

    Strips stop-words and short tokens, returns top _TERMS_PER_CLAIM tokens
    sorted by length descending (longest = most specific = best coverage signal).
    """
    tokens = re.sub(r"[^a-z0-9\s]", "", claim_text.lower()).split()
    meaningful = [t for t in tokens if len(t) >= _MIN_TERM_LEN and t not in _STOP_WORDS]
    # Sort by length descending, dedup preserving order
    seen: set[str] = set()
    unique = []
    for t in sorted(meaningful, key=len, reverse=True):
        if t not in seen:
            seen.add(t)
            unique.append(t)
    return unique[:_TERMS_PER_CLAIM]


def _strip_non_prose(content: str) -> str:
    """Strip frontmatter and code blocks from content before coverage scan.

    This prevents false positives from incidental mentions in code comments
    or false negatives from content being entirely inside code blocks.
    """
    body = _FRONTMATTER_RE.sub("", content, count=1)
    body = _CODE_FENCE_RE.sub("", body)
    return body.lower()


# Minimum number of claims for CRITICAL severity on full-miss (TC-EV-03).
# Pages with fewer assigned claims are "thin" — all-uncovered becomes HIGH not CRITICAL.
_THIN_CLAIM_THRESHOLD: int = 3


def _extract_claim_context(body: str, terms: list[str], window: int = 100) -> str:
    """Extract context windows around all occurrences of key terms in body.

    Returns a string containing the text surrounding each term match, with
    all windows concatenated by a space. Returns empty string when no term
    is found.

    TC-5136 / TC-PA-02: Used by _verify_claim_depth and multi-term window tests.
    """
    if not body or not terms:
        return ""
    segments: list[str] = []
    for term in terms:
        idx = body.lower().find(term.lower())
        while idx != -1:
            start = max(0, idx - window)
            end = min(len(body), idx + len(term) + window)
            segments.append(body[start:end])
            idx = body.lower().find(term.lower(), idx + 1)
    return " ".join(segments)


def _verify_claim_depth(claim: str, context: str) -> float:
    """Compute depth score: fraction of claim key terms present as whole words in context.

    Uses word-boundary matching to avoid counting "format" in "formats" as a match.
    A score > 0.20 indicates the context substantively addresses the claim
    rather than just casually mentioning its keywords.

    TC-5136: Used for Pass 2 depth verification after Pass 1 keyword coverage.
    """
    if not claim or not context:
        return 0.0
    terms = _extract_key_terms(claim)
    if not terms:
        return 0.0
    ctx_lower = context.lower()
    matched = sum(
        1 for t in terms
        if re.search(rf"\b{re.escape(t)}\b", ctx_lower)
    )
    return matched / len(terms)


def check_claim_coverage(
    content: str,
    slug: str,
    claim_texts: Sequence[str],
) -> list[Finding]:
    """Check that assigned claims are covered in page content.

    Returns an empty list when:
    - No claim_texts provided (field not populated — graceful degradation)
    - All claims are covered

    Returns Finding(s) when claims are not covered in the page body.

    TC-EV-03: Pages with <_THIN_CLAIM_THRESHOLD claims that are all uncovered
    are downgraded from CRITICAL to HIGH (thin claim assignment protection).
    """
    if not claim_texts:
        return []

    body = _strip_non_prose(content)
    uncovered: list[str] = []

    for claim_text in claim_texts:
        terms = _extract_key_terms(claim_text)
        if not terms:
            continue  # claim has no meaningful tokens — skip
        covered_terms = sum(1 for t in terms if t in body)
        if covered_terms < _COVERAGE_THRESHOLD:
            uncovered.append(claim_text)

    if not uncovered:
        return []

    total = len(claim_texts)
    n = len(uncovered)
    fraction = n / total

    if fraction >= 1.0:
        # TC-EV-03: Thin assignment protection — <3 claims all-uncovered → HIGH
        if total < _THIN_CLAIM_THRESHOLD:
            severity = "high"
            msg = (
                f"Page does not address any of its {total} assigned claims "
                f"(downgraded from CRITICAL: thin claim assignment with "
                f"{total} claim{'s' if total != 1 else ''}). "
                f"Content may be off-topic or placeholder-only."
            )
        else:
            severity = "critical"
            msg = (
                f"Page does not address any of its {total} assigned claims. "
                f"The content appears completely off-topic or is placeholder-only."
            )
    elif fraction > 0.5:
        severity = "high"
        msg = (
            f"{n}/{total} assigned claims ({fraction:.0%}) are not covered in the page body. "
            f"Uncovered: {', '.join(c[:60] for c in uncovered[:3])}"
            + (" ..." if n > 3 else "")
        )
    elif n >= 2:
        severity = "medium"
        msg = (
            f"{n}/{total} assigned claims are not covered in the page body. "
            f"Uncovered: {', '.join(c[:60] for c in uncovered[:2])}"
            + (" ..." if n > 2 else "")
        )
    else:
        severity = "low"
        msg = (
            f"1/{total} assigned claim is not covered in the page body: "
            f"{uncovered[0][:80]}"
        )

    return [Finding(
        check="claim_coverage",
        message=msg,
        severity=severity,
        location=slug,
        uncovered_claim_texts=uncovered,
    )]
