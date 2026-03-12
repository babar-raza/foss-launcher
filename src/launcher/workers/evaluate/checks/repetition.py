"""Check 9: Intra-page content repetition detection."""
from __future__ import annotations

import logging
import re
import string

from launcher.models.evaluation import Finding
from launcher.shared.jaccard import STOPWORDS, jaccard_similarity, strip_code_blocks, strip_frontmatter

logger = logging.getLogger(__name__)

_MAX_SENTENCES = 60

# Reference page roles are intentionally repetitive (same code example per overload).
# Jaccard and code-block duplicate checks are suppressed for these roles.
_REFERENCE_ROLES: frozenset[str] = frozenset({"api_reference", "reference_object_page"})

# Abbreviations that end with a period but don't end a sentence
_ABBREVS = re.compile(
    r"\b(e\.g|i\.e|etc|vs|Dr|Mr|Ms|Mrs|Prof|Inc|Ltd|Jr|Sr|St|Fig|Vol|No)\.\s",
    re.IGNORECASE,
)
_SENTINEL = "\u2588"  # block character used as sentinel


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences, handling abbreviations, decimals, and URLs."""
    # Protect abbreviations
    protected = _ABBREVS.sub(lambda m: m.group(1) + _SENTINEL + " ", text)
    # Protect decimals: "3.14" -> "3∎14"
    protected = re.sub(r"(\d)\.(\d)", rf"\1{_SENTINEL}\2", protected)
    # Protect dotted identifiers without spaces: "docs.aspose.com" -> "docs∎aspose∎com"
    protected = re.sub(r"([a-z])\.([a-z])", rf"\1{_SENTINEL}\2", protected)

    # Split on ". " or ".\n"
    raw = re.split(r"\.\s", protected)

    sentences: list[str] = []
    for s in raw:
        # Restore sentinels
        s = s.replace(_SENTINEL, ".").strip()
        if len(s.split()) >= 5:
            sentences.append(s)

    return sentences[:_MAX_SENTENCES]


def _word_set(sentence: str) -> set[str]:
    """Lowercase word set with punctuation stripped, stopwords removed."""
    translator = str.maketrans("", "", string.punctuation)
    words = sentence.lower().translate(translator).split()
    return {w for w in words if w and w not in STOPWORDS}


def check_repetition(content: str, slug: str, *, page_role: str = "") -> list[Finding]:
    """Detect intra-page content repetition.

    Args:
        content: Raw markdown content including frontmatter.
        slug: Page slug for finding location attribution.
        page_role: Hugo page role (e.g. "api_reference"). Reference roles are exempt
            from code-block duplication and Jaccard near-duplicate checks because API
            reference docs repeat the same example for each overload by design.
    """
    logger.debug("[repetition] Evaluating %s (role=%s)", slug, page_role or "prose")
    findings: list[Finding] = []

    body_raw = strip_frontmatter(content)

    # -- Code-block duplication (runs on raw body before stripping) --
    # Skipped for reference page roles: repeated code examples per overload are by design.
    if page_role in _REFERENCE_ROLES:
        logger.debug("[repetition] Skipping code-block/Jaccard checks for reference page: %s", slug)
    if page_role not in _REFERENCE_ROLES:
        code_blocks = re.findall(r"```\w*\n(.*?)```", body_raw, re.DOTALL)
        normalized_blocks = [b.strip() for b in code_blocks if b.strip().count("\n") >= 2]
        seen_blocks: dict[str, int] = {}
        for block in normalized_blocks:
            seen_blocks[block] = seen_blocks.get(block, 0) + 1
        for block_text, count in seen_blocks.items():
            if count >= 2:
                preview = block_text[:80].replace("\n", " ")
                findings.append(
                    Finding(
                        check="repetition",
                        message=f"Code block repeated {count} times: {preview}...",
                        severity="high",
                        location=slug,
                    )
                )

    body = strip_code_blocks(body_raw)
    sentences = _split_sentences(body)

    if len(sentences) < 2:
        logger.debug("[repetition] Skipping %s — fewer than 2 sentences", slug)
        return findings

    # Exact duplicate detection
    # Reference pages tolerate more repetition (overload descriptions share sentence stems).
    seen: dict[str, int] = {}
    for s in sentences:
        normalised = " ".join(s.lower().split())
        seen[normalised] = seen.get(normalised, 0) + 1

    exact_dupes = sum(c - 1 for c in seen.values() if c > 1)
    exact_threshold = 10 if page_role in _REFERENCE_ROLES else 3

    if exact_dupes >= exact_threshold:
        findings.append(
            Finding(
                check="repetition",
                message=f"Found {exact_dupes} exact duplicate sentences",
                severity="high",
                location=slug,
            )
        )

    # Near-duplicate detection via Jaccard similarity.
    # Skipped for reference roles: constructor overload pairs are mathematically
    # guaranteed to exceed 0.7 Jaccard (differ only in one parameter name/type).
    if page_role not in _REFERENCE_ROLES:
        word_sets = [_word_set(s) for s in sentences]
        total_pairs = 0
        near_dupe_pairs = 0

        for i in range(len(word_sets)):
            for j in range(i + 1, len(word_sets)):
                total_pairs += 1
                if jaccard_similarity(word_sets[i], word_sets[j]) >= 0.7:
                    near_dupe_pairs += 1

        # TC-3882 Wave 4 (E6): Tightened thresholds — MEDIUM 30%→20%, HIGH 50%→40%.
        # 6-sentence minimum guard already applied by len(sentences) < 2 check above
        # (extended here to 6 to prevent false positives on short pages).
        if len(sentences) < 6:
            logger.debug("[repetition] Skipping near-duplicate rate check for %s — fewer than 6 sentences", slug)
        elif total_pairs > 0:
            rate = near_dupe_pairs / total_pairs
            if rate > 0.4:
                findings.append(
                    Finding(
                        check="repetition",
                        message=f"Near-duplicate sentence rate {rate:.0%} exceeds 40%",
                        severity="high",
                        location=slug,
                    )
                )
            elif rate > 0.2:
                findings.append(
                    Finding(
                        check="repetition",
                        message=f"Near-duplicate sentence rate {rate:.0%} exceeds 20%",
                        severity="medium",
                        location=slug,
                    )
                )

        # Per-section near-duplicate detection — emit section_id for targeted heal.
        # Also skipped for reference roles (same reasoning as above).
        sections = re.split(r"\n(?=## )", body_raw)
        for raw_section in sections[1:]:  # skip preamble before first ##
            heading_match = re.match(r"## (.+)", raw_section)
            if not heading_match:
                continue
            section_heading = heading_match.group(1).strip()
            section_body = strip_code_blocks(strip_frontmatter(raw_section))
            section_sentences = _split_sentences(section_body)
            if len(section_sentences) < 4:
                continue
            section_word_sets = [_word_set(s) for s in section_sentences]
            s_total, s_near = 0, 0
            for i in range(len(section_word_sets)):
                for j in range(i + 1, len(section_word_sets)):
                    s_total += 1
                    if jaccard_similarity(section_word_sets[i], section_word_sets[j]) >= 0.7:
                        s_near += 1
            if s_total > 0 and s_near / s_total > 0.5:
                findings.append(
                    Finding(
                        check="repetition",
                        message=f"Section '{section_heading}' has near-duplicate sentence rate {s_near/s_total:.0%}",
                        severity="medium",
                        location=f"{slug}:section",
                        section_id=section_heading,
                    )
                )

    logger.debug("[repetition] Found %d findings for %s", len(findings), slug)
    return findings
