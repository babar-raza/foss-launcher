"""Check: faq_structure — verify FAQ pages have Q&A format (TC-D-04).

FAQ pages must have ≥3 question headings (H3) each followed by ≥2-sentence
answers. A page with page_role "faq" that lacks Q&A structure is not an FAQ —
it's a text dump that provides no value.

Implements the MVC rubric from reports/evaluator-reliability/rubrics.md:
- faq: 100 words prose + 3 Q&A pairs
"""
from __future__ import annotations

import re

from launcher.models.evaluation import Finding

# Match H3 headings that look like questions (end with ? or start with question words)
_QUESTION_WORDS = {"how", "what", "why", "when", "where", "which", "can", "does", "is", "do", "will", "should"}
_HEADING_RE = re.compile(r"^(#{3})\s+(.+)$", re.MULTILINE)

# Minimum Q&A pairs for a valid FAQ page
_MIN_QA_PAIRS = 3

# Minimum sentences in an answer
_MIN_ANSWER_SENTENCES = 2

# Sentence-ending pattern (rough but sufficient for evaluation)
_SENTENCE_END_RE = re.compile(r"[.!?]\s|[.!?]$")


def _is_question_heading(text: str) -> bool:
    """Check if heading text looks like a question."""
    text_lower = text.strip().lower()
    if text_lower.endswith("?"):
        return True
    first_word = text_lower.split()[0] if text_lower.split() else ""
    return first_word in _QUESTION_WORDS


def _count_sentences(text: str) -> int:
    """Count approximate sentence count in text."""
    if not text.strip():
        return 0
    # Count sentence-ending punctuation
    ends = len(_SENTENCE_END_RE.findall(text))
    # At least 1 if there's any text
    return max(ends, 1) if text.strip() else 0


def check_faq_structure(
    content: str,
    slug: str,
    *,
    page_role: str = "",
) -> list[Finding]:
    """Verify FAQ pages have proper Q&A structure.

    Args:
        content: Rendered markdown content.
        slug: Page slug for Finding location.
        page_role: Page role string.

    Returns:
        List of Findings — HIGH if no Q&A structure, MEDIUM if too few pairs.
    """
    if page_role != "faq":
        return []

    normalised = content.replace("\r\n", "\n").replace("\r", "\n")
    body = re.sub(r"^---\n.*?\n---\n?", "", normalised, flags=re.DOTALL)

    # Find all H3 headings
    headings = list(_HEADING_RE.finditer(body))

    # Count question headings
    question_headings = [h for h in headings if _is_question_heading(h.group(2))]

    findings: list[Finding] = []

    if len(question_headings) == 0:
        findings.append(Finding(
            check="faq_structure",
            message=(
                "FAQ page has no question headings (H3) — "
                "FAQ pages must have Q&A pairs with question headings"
            ),
            severity="high",
            location=slug,
        ))
        return findings

    if len(question_headings) < _MIN_QA_PAIRS:
        findings.append(Finding(
            check="faq_structure",
            message=(
                f"FAQ page has only {len(question_headings)} question heading(s) "
                f"(minimum {_MIN_QA_PAIRS}) — add more Q&A pairs"
            ),
            severity="medium",
            location=slug,
        ))

    # Check that answers have sufficient depth
    thin_answers = 0
    for i, qh in enumerate(question_headings):
        # Get text between this heading and the next heading (or end)
        start = qh.end()
        # Find next heading of any level
        next_heading = re.search(r"^#{1,6}\s+", body[start:], re.MULTILINE)
        end = start + next_heading.start() if next_heading else len(body)
        answer_text = body[start:end].strip()

        # Remove code blocks from answer for sentence counting
        answer_prose = re.sub(r"```[\s\S]*?```", "", answer_text)
        sentences = _count_sentences(answer_prose)
        if sentences < _MIN_ANSWER_SENTENCES:
            thin_answers += 1

    if thin_answers > 0:
        findings.append(Finding(
            check="faq_structure",
            message=(
                f"{thin_answers} FAQ answer(s) have fewer than "
                f"{_MIN_ANSWER_SENTENCES} sentences — answers should be substantive"
            ),
            severity="medium",
            location=slug,
        ))

    return findings
