"""Shared utilities for W5.5 ContentReviewer worker.

This module provides shared utilities used across W5.5 ContentReviewer modules
to maintain a single source of truth and avoid duplication.

TC-1100-P1: W5.5 ContentReviewer Phase 1 - Core Review Logic
Pattern: Based on W2 _shared.py (src/launch/workers/w2_facts_builder/_shared.py)
"""

# Stopwords for text analysis (shared with W2)
# Used for content density calculations and text processing
STOPWORDS = frozenset({
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'from', 'as', 'is', 'are', 'was', 'were', 'be',
    'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
    'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this',
    'that', 'these', 'those', 'it', 'its',
})


def calculate_flesch_kincaid_grade(text: str) -> float:
    """Calculate Flesch-Kincaid Grade Level for text.

    The Flesch-Kincaid Grade Level formula:
    0.39 * (words / sentences) + 11.8 * (syllables / words) - 15.59

    This estimates the U.S. school grade level needed to understand the text.
    Target grade levels:
    - 8-10: Middle school (ideal for documentation)
    - 11-12: High school
    - 13-16: College
    - >16: College graduate (too complex)

    Args:
        text: Input text to analyze

    Returns:
        Flesch-Kincaid grade level (float)
        Returns 0.0 if text is too short to analyze

    Spec reference: abstract-hugging-kite.md:346 (Check 2: Readability Score)
    """
    if not text or len(text.strip()) < 10:
        return 0.0

    # Count sentences (simple heuristic: split on . ! ?)
    import re
    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
    num_sentences = len(sentences)

    if num_sentences == 0:
        return 0.0

    # Count words (split on whitespace, filter empty)
    words = [w for w in text.split() if w.strip()]
    num_words = len(words)

    if num_words == 0:
        return 0.0

    # Count syllables (simple heuristic: count vowel groups)
    num_syllables = 0
    for word in words:
        # Remove non-alphabetic characters
        word_clean = re.sub(r'[^a-zA-Z]', '', word).lower()
        if not word_clean:
            continue

        # Count vowel groups (simplified syllable counting)
        syllable_count = len(re.findall(r'[aeiouy]+', word_clean))

        # Adjust for silent e at end
        if word_clean.endswith('e'):
            syllable_count = max(1, syllable_count - 1)

        # Every word has at least 1 syllable
        syllable_count = max(1, syllable_count)
        num_syllables += syllable_count

    # Calculate Flesch-Kincaid Grade Level
    # 0.39 * (words / sentences) + 11.8 * (syllables / words) - 15.59
    avg_words_per_sentence = num_words / num_sentences
    avg_syllables_per_word = num_syllables / num_words

    grade_level = (0.39 * avg_words_per_sentence) + (11.8 * avg_syllables_per_word) - 15.59

    # Clamp to reasonable range (0-20)
    return max(0.0, min(20.0, grade_level))
