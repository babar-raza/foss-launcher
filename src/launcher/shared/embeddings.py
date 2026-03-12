"""TC-3774: Semantic similarity with TF-IDF fallback and API embeddings.

Provides two tiers of text similarity:
1. TF-IDF-based (deterministic, pure stdlib, always available) -- ported from v1
2. API-based neural embeddings via qwen3-embedding-8b (when configured)

The TF-IDF approach weights terms by their importance across a pair of
documents, giving higher weight to discriminative terms and lower weight
to common terms.  Cosine similarity on TF-IDF vectors captures semantic
overlap more accurately than raw word-set Jaccard.

Spec references:
- specs/03_product_facts_and_evidence.md (Evidence mapping improvements)
- specs/10_determinism_and_caching.md (Deterministic scoring)
- specs/34_strict_compliance_guarantees.md (Guarantee D: Network allowlist)
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import re
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from launcher.shared.jaccard import STOPWORDS

logger = logging.getLogger(__name__)

# Maximum texts per API embedding batch request
_EMBEDDING_BATCH_SIZE = 32


# ---------------------------------------------------------------------------
# Tokenisation (ported from v1 TC-1046)
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
# TF-IDF building blocks (ported from v1 TC-1046)
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
# Similarity (ported from v1 TC-1046)
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


def cosine_similarity_dense(vec1: List[float], vec2: List[float]) -> float:
    """Compute cosine similarity between two dense vectors.

    Args:
        vec1: First dense vector.
        vec2: Second dense vector (must be same length).

    Returns:
        Similarity in [0.0, 1.0].  Returns 0.0 for zero-magnitude vectors.
    """
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0

    dot = sum(a * b for a, b in zip(vec1, vec2))
    if dot == 0.0:
        return 0.0

    mag1 = math.sqrt(sum(a * a for a in vec1))
    mag2 = math.sqrt(sum(b * b for b in vec2))

    if mag1 == 0.0 or mag2 == 0.0:
        return 0.0

    sim = dot / (mag1 * mag2)
    return max(0.0, min(1.0, sim))


# ---------------------------------------------------------------------------
# End-to-end TF-IDF similarity (ported from v1 TC-1046)
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
        text1: First text (typically claim text -- short).
        text2: Second text (typically document content -- large).
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
# API-based embedding client
# ---------------------------------------------------------------------------

class EmbeddingClient:
    """Client for OpenAI-compatible /v1/embeddings endpoint.

    Uses ``launcher.clients.http.http_post`` for network allowlist compliance
    (Guarantee D).
    """

    def __init__(
        self,
        base_url: str,
        model: str = "qwen3-embedding-8b",
        api_key: Optional[str] = None,
        timeout: int = 30,
    ):
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._api_key = api_key or os.environ.get("litellm_key", "")
        self._timeout = timeout

    def _headers(self) -> Dict[str, str]:
        h: Dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            h["Authorization"] = f"Bearer {self._api_key}"
        return h

    def is_available(self) -> bool:
        """Probe the embedding endpoint with a trivial request.

        Run once per pipeline invocation to decide API vs TF-IDF for the run.
        """
        from launcher.clients.http import http_post

        try:
            resp = http_post(
                f"{self._base_url}/embeddings",
                json={"model": self._model, "input": ["probe"]},
                headers=self._headers(),
                timeout=min(self._timeout, 10),
            )
            return resp.status_code == 200
        except Exception as exc:
            logger.debug("embedding_probe_failed: %s", exc)
            return False

    def embed(self, texts: List[str], call_id: str = "") -> List[List[float]]:
        """Batch embed texts via the API.

        Splits into batches of ``_EMBEDDING_BATCH_SIZE`` to respect API limits.

        Args:
            texts: List of texts to embed.
            call_id: Optional identifier for logging/telemetry.

        Returns:
            List of embedding vectors (one per input text).

        Raises:
            RuntimeError: If the API call fails.
        """
        from launcher.clients.http import http_post

        all_vectors: List[List[float]] = []

        for batch_start in range(0, len(texts), _EMBEDDING_BATCH_SIZE):
            batch = texts[batch_start:batch_start + _EMBEDDING_BATCH_SIZE]

            resp = http_post(
                f"{self._base_url}/embeddings",
                json={"model": self._model, "input": batch},
                headers=self._headers(),
                timeout=self._timeout,
            )

            if resp.status_code != 200:
                raise RuntimeError(
                    f"Embedding API returned {resp.status_code}: {resp.text[:200]}"
                )

            data = resp.json()
            # OpenAI-compatible response: {"data": [{"embedding": [...], "index": N}, ...]}
            items = sorted(data.get("data", []), key=lambda x: x.get("index", 0))
            for item in items:
                all_vectors.append(item["embedding"])

        if len(all_vectors) != len(texts):
            raise RuntimeError(
                f"Embedding count mismatch: got {len(all_vectors)}, expected {len(texts)}"
            )

        return all_vectors


# ---------------------------------------------------------------------------
# Embedding index (in-memory vector store)
# ---------------------------------------------------------------------------

class EmbeddingIndex:
    """In-memory keyed vector store with cosine similarity lookup.

    Supports both dense vectors (from API) and sparse dicts (from TF-IDF).
    Serializes to JSON for deterministic artifact storage.
    """

    def __init__(self) -> None:
        self._vectors: Dict[str, Any] = {}  # key -> list[float] or dict[str, float]
        self._is_dense: bool = True

    def __len__(self) -> int:
        return len(self._vectors)

    def add(self, key: str, vector: Any) -> None:
        """Store a keyed vector (dense list or sparse dict)."""
        self._vectors[key] = vector
        if isinstance(vector, dict):
            self._is_dense = False

    def keys(self) -> list[str]:
        """Return all stored keys in sorted order."""
        return sorted(self._vectors.keys())

    def get(self, key: str) -> Any:
        """Return the vector for a key, or None."""
        return self._vectors.get(key)

    def similarity(self, key_a: str, key_b: str) -> float:
        """Compute cosine similarity between two stored vectors."""
        vec_a = self._vectors.get(key_a)
        vec_b = self._vectors.get(key_b)
        if vec_a is None or vec_b is None:
            return 0.0

        if isinstance(vec_a, list) and isinstance(vec_b, list):
            return cosine_similarity_dense(vec_a, vec_b)
        elif isinstance(vec_a, dict) and isinstance(vec_b, dict):
            return cosine_similarity(vec_a, vec_b)
        return 0.0

    def most_similar(
        self,
        query_key: str,
        candidates: Optional[List[str]] = None,
        top_k: int = 5,
    ) -> List[Tuple[str, float]]:
        """Find the top-k most similar keys to query_key.

        Args:
            query_key: Key to compare against.
            candidates: Optional subset of keys to search. Defaults to all keys.
            top_k: Number of results to return.

        Returns:
            List of (key, score) tuples sorted by descending similarity.
        """
        if query_key not in self._vectors:
            return []

        search_keys = candidates if candidates is not None else list(self._vectors.keys())
        scores: List[Tuple[str, float]] = []
        for key in search_keys:
            if key == query_key:
                continue
            score = self.similarity(query_key, key)
            if score > 0.0:
                scores.append((key, score))

        scores.sort(key=lambda x: (-x[1], x[0]))
        return scores[:top_k]

    def save(self, path: Path) -> None:
        """Save index to JSON (deterministic: sorted keys)."""
        data = {
            "version": "1.0.0",
            "is_dense": self._is_dense,
            "count": len(self._vectors),
            "vectors": {k: self._vectors[k] for k in sorted(self._vectors.keys())},
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=None, sort_keys=True, separators=(",", ":"))

    @classmethod
    def load(cls, path: Path) -> "EmbeddingIndex":
        """Load index from JSON."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        index = cls()
        index._is_dense = data.get("is_dense", True)
        for key, vec in data.get("vectors", {}).items():
            index._vectors[key] = vec
        return index


# ---------------------------------------------------------------------------
# Batch embedding with transparent fallback
# ---------------------------------------------------------------------------

def embed_texts(
    texts: Dict[str, str],
    client: Optional[EmbeddingClient] = None,
) -> Optional[EmbeddingIndex]:
    """Embed a batch of keyed texts into an EmbeddingIndex.

    If ``client`` is provided, uses the API for dense embeddings.
    Otherwise, falls back to TF-IDF sparse vectors from the corpus.

    Args:
        texts: Mapping of {key: text_content}.
        client: Optional EmbeddingClient for API-based embeddings.

    Returns:
        EmbeddingIndex with all texts embedded, or None if texts is empty.
    """
    if not texts:
        return None

    index = EmbeddingIndex()

    if client is not None:
        # API path: batch embed all texts
        keys = sorted(texts.keys())
        text_list = [texts[k] for k in keys]
        try:
            vectors = client.embed(text_list, call_id="embed_texts")
            for key, vec in zip(keys, vectors):
                index.add(key, vec)
            logger.info("embed_texts_api: embedded %d texts", len(keys))
            return index
        except Exception as exc:
            logger.warning("embed_texts_api_failed, falling back to tfidf: %s", exc)
            # Fall through to TF-IDF

    # TF-IDF fallback: compute corpus-wide IDF, then per-text TF-IDF vectors
    keys = sorted(texts.keys())
    all_tokens: List[List[str]] = []
    for key in keys:
        all_tokens.append(tokenize(texts[key]))

    idf = compute_idf(all_tokens)

    for key, tokens in zip(keys, all_tokens):
        if tokens:
            vec = compute_tfidf_vector(tokens, idf)
            index.add(key, vec)

    logger.info("embed_texts_tfidf: embedded %d texts", len(index))
    return index if len(index) > 0 else None


# ---------------------------------------------------------------------------
# Factory (updated from v1 TC-1046)
# ---------------------------------------------------------------------------

def get_similarity_scorer(
    llm_config: Optional[Any] = None,
) -> Callable[[str, str], float]:
    """Return the appropriate similarity scoring function.

    When no llm_config or no embedding endpoint is configured, returns the
    TF-IDF scorer (deterministic, always available).

    Args:
        llm_config: Optional LLMConfig with embedding endpoint.

    Returns:
        A callable ``(text1, text2) -> float`` similarity scorer.
    """
    # Check if API embedding is available
    if llm_config is not None:
        embedding_cfg = getattr(llm_config, "embedding", None)
        if embedding_cfg is not None and embedding_cfg.base_url:
            api_key = os.environ.get(
                getattr(llm_config, "api_key_env", None) or "litellm_key", ""
            )
            client = EmbeddingClient(
                base_url=embedding_cfg.base_url,
                model=embedding_cfg.model,
                api_key=api_key,
            )
            if client.is_available():
                logger.info("Using API embedding scorer (model=%s)", embedding_cfg.model)

                def _api_scorer(text1: str, text2: str) -> float:
                    idx = embed_texts({"a": text1, "b": text2}, client=client)
                    if idx is None:
                        return 0.0
                    return idx.similarity("a", "b")

                return _api_scorer

    # Default: TF-IDF scorer (deterministic, no network)
    return compute_tfidf_similarity
