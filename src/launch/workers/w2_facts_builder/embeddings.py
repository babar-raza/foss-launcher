"""TC-1046: Semantic similarity for evidence mapping.

Provides TF-IDF-based text similarity as an improvement over Jaccard.
Uses Python stdlib only (no numpy, scipy, sklearn).

The TF-IDF approach weights terms by their importance across a pair of
documents, giving higher weight to discriminative terms and lower weight
to common terms.  Cosine similarity on TF-IDF vectors captures semantic
overlap more accurately than raw word-set Jaccard.

Spec references:
- specs/07_code_analysis_and_enrichment.md (Evidence mapping improvements)
- specs/03_product_facts_and_evidence.md (Evidence priority and structure)
- specs/10_determinism_and_caching.md (Deterministic scoring)

TC-1046: Semantic embeddings for evidence mapping
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any, Callable, Dict, List, Optional, Tuple

from ._shared import STOPWORDS


# ---------------------------------------------------------------------------
# Tokenisation
# ---------------------------------------------------------------------------

def tokenize(text: str) -> List[str]:
    """Tokenize text into lowercase words, removing stopwords and short tokens.

    Args:
        text: Raw text string.

    Returns:
        List of cleaned tokens (lowercase, no stopwords, length > 2).
    """
    if not text:
        return []
    words = re.findall(r'\w+', text.lower())
    return [w for w in words if w not in STOPWORDS and len(w) > 2]


# ---------------------------------------------------------------------------
# TF-IDF building blocks
# ---------------------------------------------------------------------------

def compute_tf(tokens: List[str]) -> Dict[str, float]:
    """Compute term frequency for a token list.

    TF(t) = count(t) / total_tokens

    Args:
        tokens: List of tokens from a single document.

    Returns:
        Dictionary mapping each token to its term frequency.
    """
    if not tokens:
        return {}
    counts = Counter(tokens)
    total = len(tokens)
    return {term: count / total for term, count in counts.items()}


def compute_idf(documents: List[List[str]]) -> Dict[str, float]:
    """Compute inverse document frequency across a corpus.

    Uses a smoothed IDF formula: IDF(t) = log(1 + N / df(t)).

    The ``1 +`` smoothing ensures that terms appearing in every document
    still receive a small positive weight rather than collapsing to zero.
    This is critical for pairwise (2-document) corpora where the standard
    formula ``log(N/df)`` would zero-out every shared term, making the
    cosine similarity unable to detect overlap.

    Args:
        documents: List of token-lists, one per document.

    Returns:
        Dictionary mapping each token to its IDF value (always > 0).
    """
    if not documents:
        return {}

    n_docs = len(documents)
    # Document frequency: how many documents contain each term
    df: Counter[str] = Counter()
    for doc_tokens in documents:
        # Use set to count each term at most once per document
        unique_tokens = set(doc_tokens)
        for token in unique_tokens:
            df[token] += 1

    idf: Dict[str, float] = {}
    for term, freq in df.items():
        # Smoothed IDF: log(1 + N/df).  Terms in all docs get
        # log(1 + 1) = log(2) instead of 0, preserving overlap signal.
        # Terms in fewer docs get a higher weight, providing discrimination.
        idf[term] = math.log(1.0 + n_docs / freq)

    return idf


def compute_tfidf_vector(
    tokens: List[str],
    idf: Dict[str, float],
) -> Dict[str, float]:
    """Compute a sparse TF-IDF vector for a single document.

    Args:
        tokens: Token list for the document.
        idf: Pre-computed IDF dictionary from the corpus.

    Returns:
        Sparse vector as {term: tfidf_weight}.
    """
    tf = compute_tf(tokens)
    return {term: tf_val * idf.get(term, 0.0) for term, tf_val in tf.items()}


# ---------------------------------------------------------------------------
# Similarity
# ---------------------------------------------------------------------------

def cosine_similarity(vec1: Dict[str, float], vec2: Dict[str, float]) -> float:
    """Compute cosine similarity between two sparse vectors.

    cos(v1, v2) = (v1 . v2) / (||v1|| * ||v2||)

    Args:
        vec1: First sparse vector {term: weight}.
        vec2: Second sparse vector {term: weight}.

    Returns:
        Similarity in [0.0, 1.0].  Returns 0.0 for zero-magnitude vectors.
    """
    if not vec1 or not vec2:
        return 0.0

    # Dot product -- iterate over the smaller vector for efficiency
    if len(vec1) > len(vec2):
        vec1, vec2 = vec2, vec1

    dot = 0.0
    for term, w1 in vec1.items():
        w2 = vec2.get(term)
        if w2 is not None:
            dot += w1 * w2

    if dot == 0.0:
        return 0.0

    # Magnitudes
    mag1 = math.sqrt(sum(w * w for w in vec1.values()))
    mag2 = math.sqrt(sum(w * w for w in vec2.values()))

    if mag1 == 0.0 or mag2 == 0.0:
        return 0.0

    sim = dot / (mag1 * mag2)
    # Clamp to [0, 1] to guard against floating-point overshoot
    return max(0.0, min(1.0, sim))


# ---------------------------------------------------------------------------
# End-to-end TF-IDF similarity
# ---------------------------------------------------------------------------

def compute_tfidf_similarity(
    text1: str,
    text2: str,
    _tokens2_cache: Optional[Tuple[List[str], frozenset]] = None,
) -> float:
    """Compute TF-IDF cosine similarity between two texts.

    This is the main API consumed by ``map_evidence.compute_text_similarity``.

    Performance optimizations for large-scale evidence mapping:
    1. Accepts pre-tokenized text2 via ``_tokens2_cache`` to avoid
       re-tokenizing the same document for every claim.
    2. Fast Jaccard pre-check skips pairs with no/trivial word overlap.

    Args:
        text1: First text (typically claim text — short).
        text2: Second text (typically document content — large).
        _tokens2_cache: Optional pre-computed (tokens_list, token_set) for text2.
            When provided, text2 is ignored and the cache is used directly.

    Returns:
        Similarity in [0.0, 1.0].
    """
    tokens1 = tokenize(text1)
    if not tokens1:
        return 0.0

    # Use pre-tokenized cache for text2 if provided (avoids re-tokenizing
    # large documents thousands of times during evidence mapping).
    if _tokens2_cache is not None:
        tokens2, set2 = _tokens2_cache
    else:
        tokens2 = tokenize(text2)
        set2 = frozenset(tokens2)

    if not tokens2:
        return 0.0

    # Fast pre-check: if no word overlap at all, return 0.0 immediately.
    set1 = set(tokens1)
    intersection = set1 & set2
    if not intersection:
        return 0.0

    # Fast path: identical token bags -> similarity is 1.0.
    if Counter(tokens1) == Counter(tokens2):
        return 1.0

    # For small overlaps on large documents, use fast Jaccard to avoid
    # expensive TF-IDF computation.
    jaccard = len(intersection) / len(set1 | set2)
    if jaccard < 0.01:
        return jaccard

    # Build corpus of two documents
    corpus = [tokens1, tokens2]
    idf = compute_idf(corpus)

    vec1 = compute_tfidf_vector(tokens1, idf)
    vec2 = compute_tfidf_vector(tokens2, idf)

    return cosine_similarity(vec1, vec2)


def precompute_token_cache(text: str) -> Optional[Tuple[List[str], frozenset]]:
    """Pre-tokenize a document for repeated similarity comparisons.

    Call this once per document, then pass the result as ``_tokens2_cache``
    to ``compute_tfidf_similarity`` for each claim comparison.

    Args:
        text: Document text to pre-tokenize.

    Returns:
        Tuple of (token_list, token_frozenset) or None if empty.
    """
    tokens = tokenize(text)
    if not tokens:
        return None
    return (tokens, frozenset(tokens))


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def get_similarity_scorer(
    llm_client: Optional[Any] = None,
) -> Callable[[str, str], float]:
    """Return the appropriate similarity scoring function.

    In offline mode (no *llm_client*) the TF-IDF scorer is returned.
    When an LLM client is provided the TF-IDF scorer is still returned
    (embedding-API integration is out of scope for TC-1046).

    Args:
        llm_client: Optional LLM client instance.

    Returns:
        A callable ``(text1, text2) -> float`` similarity scorer.
    """
    # TC-1046: Always return TF-IDF scorer.  Future TCs may add an
    # LLM-embedding path when llm_client is provided.
    return compute_tfidf_similarity
