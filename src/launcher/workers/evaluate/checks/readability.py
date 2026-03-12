"""Readability scoring check — Flesch-Kincaid grade level."""
from __future__ import annotations

import re

from launcher.models.evaluation import Finding

_VOWELS = re.compile(r"[aeiouAEIOU]")
_SENTENCE_ENDINGS = re.compile(r"[.!?]+")
_ALPHA_WORD = re.compile(r"[a-zA-Z]+")
_CODE_FENCE = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE = re.compile(r"`[^`]+`")

# TC-3878 Wave 0 (E2): Page roles where FK grade is irrelevant because the prose is
# intentionally dense with API identifiers, type names, and parameter lists.
# These roles skip FK entirely and only emit long-sentence LOW findings.
_REFERENCE_ROLES: frozenset[str] = frozenset({
    "api_reference",
    "class_reference",
    "method_reference",
    "namespace_reference",
})


def _extract_body(page_ir: object) -> str:
    """Extract prose body text from page_ir, stripping code blocks."""
    parts = []
    for section in (getattr(page_ir, "sections", []) or []):
        for block in (getattr(section, "blocks", []) or []):
            block_type = getattr(block, "type", "")
            # Handle both string and enum type
            if hasattr(block_type, "value"):
                block_type = block_type.value
            if block_type in ("paragraph", "text", "prose"):
                content = getattr(block, "content", "") or ""
                if content:
                    parts.append(content)
    body = " ".join(parts)
    body = _CODE_FENCE.sub(" ", body)
    body = _INLINE_CODE.sub(" ", body)
    return body.strip()


def _extract_body_from_markdown(content: str) -> str:
    """Extract prose text from raw markdown, stripping frontmatter and code blocks."""
    # Strip frontmatter
    body = re.sub(r"^---\n.*?\n---\n?", "", content, flags=re.DOTALL)
    # Strip code fences
    body = _CODE_FENCE.sub(" ", body)
    # Strip inline code
    body = _INLINE_CODE.sub(" ", body)
    # Strip headings
    body = re.sub(r"^#{1,6}\s+.+$", "", body, flags=re.MULTILINE)
    # Strip HTML tags
    body = re.sub(r"<[^>]+>", " ", body)
    return body.strip()


def _split_sentences(text: str) -> list[str]:
    parts = _SENTENCE_ENDINGS.split(text)
    return [p.strip() for p in parts if p.strip()]


def _split_words(text: str) -> list[str]:
    """Extract alphabetic-only words (no numbers, punctuation, mixed tokens).

    Uses [a-zA-Z]+ regex — excludes version numbers, URLs, identifiers.
    For v2 English-only content, this is correct behavior.
    """
    return _ALPHA_WORD.findall(text)


def _count_syllables(word: str) -> int:
    """Estimate syllable count for *word* using vowel cluster counting."""
    word = re.sub(r"[^a-zA-Z]", "", word.lower())
    if not word:
        return 1
    # Strip common silent endings
    word = re.sub(r"e$", "", word)
    count = len(_VOWELS.findall(word))
    return max(1, count)


def _flesch_kincaid_grade(text: str) -> float:
    """Compute Flesch-Kincaid Grade Level for *text*."""
    sentences = _split_sentences(text)
    words = _split_words(text)
    if not sentences or not words:
        return 0.0
    syllables = sum(_count_syllables(w) for w in words)
    asl = len(words) / len(sentences)   # avg sentence length
    asw = syllables / len(words)        # avg syllables per word
    return 0.39 * asl + 11.8 * asw - 15.59


def _readability_findings_from_grade(fk_grade: float, word_count: int) -> list[dict]:
    """Return raw finding dicts for a given FK grade.

    Thresholds (TC-3878 Wave 0 calibration — raised from original TC-SEO-20 spec):
      FK > 22  → severity "high"   (severely complex — escalated; was >20)
      FK > 18  → severity "medium" (too complex for most readers; was >16)
      FK < 6   → severity "low"    (too simple for technical audience)
    Only the 'too simple' threshold requires >=100 words (insufficient data guard).
    Raising the thresholds prevents false MEDIUM findings on technical docs
    whose natural FK range is 14–18 (API prose with long parameter names).
    """
    if fk_grade > 22.0:
        return [{
            "check": "readability",
            "message": (
                f"Prose is severely complex (Flesch-Kincaid grade {fk_grade:.1f}, "
                "threshold: \u226422.0). Simplify sentences and vocabulary."
            ),
            "severity": "high",
            "location": "body",
        }]
    if fk_grade > 18.0:
        return [{
            "check": "readability",
            "message": (
                f"Prose may be too complex (Flesch-Kincaid grade {fk_grade:.1f}, "
                "threshold: \u226418.0). Consider shorter sentences and simpler vocabulary."
            ),
            "severity": "medium",
            "location": "body",
        }]
    if fk_grade < 6.0 and word_count >= 100:
        return [{
            "check": "readability",
            "message": (
                f"Prose may be too simple for a technical audience "
                f"(Flesch-Kincaid grade {fk_grade:.1f}, threshold: \u22656.0)."
            ),
            "severity": "low",
            "location": "body",
        }]
    return []


def _long_sentence_finding(sentences: list[str], location: str = "body") -> list[dict]:
    """Return a low-severity finding if >40% of sentences exceed 30 words.

    Spec: TC-SEO-20 — 'Also flag: >40% sentences exceed 30 words → low'
    Only applied when there are >=3 sentences (avoids false positives on stub pages).
    """
    if len(sentences) < 3:
        return []
    long_count = sum(
        1 for s in sentences
        if len(_ALPHA_WORD.findall(s)) > 30
    )
    if not sentences:
        return []
    ratio = long_count / len(sentences)
    if ratio > 0.40:
        return [{
            "check": "readability",
            "message": (
                f"{long_count}/{len(sentences)} sentences exceed 30 words "
                f"({ratio:.0%}). Break long sentences for readability."
            ),
            "severity": "low",
            "location": location,
        }]
    return []


def check_readability(page_ir: object) -> list[dict]:
    """Return findings (as dicts) for pages outside the readable FK grade range.

    Thresholds (TC-3878 Wave 0):
      FK > 22 → severity "high"   (severely complex)
      FK > 18 → severity "medium" (complex)
      FK < 6  → severity "low"    (too simple for technical audience)
    Returns empty list for pages with < 100 words (insufficient content).
    This variant returns plain dicts for use in non-Finding contexts.
    """
    body = _extract_body(page_ir)
    if not body:
        return []
    words = _split_words(body)
    if len(words) < 100:
        return []
    sentences = _split_sentences(body)
    fk_grade = _flesch_kincaid_grade(body)
    findings = _readability_findings_from_grade(fk_grade, len(words))
    findings.extend(_long_sentence_finding(sentences))
    return findings


def check_readability_from_markdown(
    content: str, slug: str = "", page_role: str = ""
) -> list[Finding]:
    """Check readability from raw markdown content string.

    Thresholds (TC-3878 Wave 0):
      FK > 22 → severity "high"   (severely complex)
      FK > 18 → severity "medium" (complex)
      FK < 6  → severity "low"    (too simple for technical audience)
    Returns empty list for pages with < 100 words.

    For page_role in _REFERENCE_ROLES (api_reference, class_reference, etc.):
    FK grade is skipped entirely — reference prose is legitimately dense with
    API identifiers. Only long-sentence LOW findings are emitted.
    """
    body = _extract_body_from_markdown(content)
    if not body:
        return []
    words = _split_words(body)
    if len(words) < 100:
        return []
    sentences = _split_sentences(body)
    raw: list[dict] = []
    if page_role not in _REFERENCE_ROLES:
        fk_grade = _flesch_kincaid_grade(body)
        raw.extend(_readability_findings_from_grade(fk_grade, len(words)))
    raw.extend(_long_sentence_finding(sentences))
    return [
        Finding(
            check=d["check"],
            message=d["message"],
            severity=d["severity"],
            location=slug or d["location"],
        )
        for d in raw
    ]
