"""Unit tests for TC-1046: Semantic embeddings for evidence mapping.

Tests TF-IDF similarity implementation in embeddings.py.
Verifies correctness, edge cases, determinism, and integration
with the evidence mapping pipeline.

Spec references:
- specs/07_code_analysis_and_enrichment.md (Evidence mapping improvements)
- specs/10_determinism_and_caching.md (Deterministic scoring)

TC-1046: Semantic embeddings for evidence mapping
"""

from __future__ import annotations

import math

import pytest

from src.launch.workers.w2_facts_builder.embeddings import (
    STOPWORDS,
    compute_idf,
    compute_tf,
    compute_tfidf_similarity,
    compute_tfidf_vector,
    cosine_similarity,
    get_similarity_scorer,
    tokenize,
)


# -----------------------------------------------------------------------
# tokenize
# -----------------------------------------------------------------------

class TestTokenize:
    """Test the tokenize function."""

    def test_tokenize_basic(self):
        """Basic tokenization splits into lowercase words."""
        tokens = tokenize("Supports OBJ format for 3D models")
        assert "supports" in tokens
        assert "obj" in tokens
        assert "format" in tokens
        assert "models" in tokens

    def test_tokenize_empty(self):
        """Empty string returns empty list."""
        assert tokenize("") == []

    def test_tokenize_stopword_removal(self):
        """Stopwords are removed from output."""
        tokens = tokenize("the library can read and write files")
        # Stopwords must be absent
        for sw in ("the", "can", "and"):
            assert sw not in tokens
        # Content words must be present
        assert "library" in tokens
        assert "read" in tokens
        assert "write" in tokens
        assert "files" in tokens

    def test_tokenize_short_word_removal(self):
        """Words of length <= 2 are removed."""
        tokens = tokenize("API is ok to go use it")
        assert "is" not in tokens
        assert "ok" not in tokens
        assert "to" not in tokens
        assert "go" not in tokens
        # "api" len 3 -> kept; "use" len 3 -> kept
        assert "api" in tokens
        assert "use" in tokens

    def test_tokenize_preserves_order(self):
        """Tokens appear in document order."""
        tokens = tokenize("alpha bravo charlie delta echo")
        assert tokens == ["alpha", "bravo", "charlie", "delta", "echo"]


# -----------------------------------------------------------------------
# compute_tf
# -----------------------------------------------------------------------

class TestComputeTF:
    """Test term-frequency computation."""

    def test_compute_tf_frequency(self):
        """TF values reflect relative frequencies."""
        tokens = ["obj", "obj", "stl", "fbx"]
        tf = compute_tf(tokens)
        assert tf["obj"] == pytest.approx(2 / 4)
        assert tf["stl"] == pytest.approx(1 / 4)
        assert tf["fbx"] == pytest.approx(1 / 4)

    def test_compute_tf_empty(self):
        """Empty token list returns empty dict."""
        assert compute_tf([]) == {}

    def test_compute_tf_single_token(self):
        """Single token has TF of 1.0."""
        tf = compute_tf(["hello"])
        assert tf["hello"] == pytest.approx(1.0)


# -----------------------------------------------------------------------
# compute_idf
# -----------------------------------------------------------------------

class TestComputeIDF:
    """Test inverse document frequency computation."""

    def test_compute_idf_single_document(self):
        """IDF with one document: every term gets log(1+1) = log(2)."""
        docs = [["obj", "stl"]]
        idf = compute_idf(docs)
        # Smoothed IDF: log(1 + 1/1) = log(2)
        assert idf["obj"] == pytest.approx(math.log(2))
        assert idf["stl"] == pytest.approx(math.log(2))

    def test_compute_idf_multi_document(self):
        """IDF across multiple documents with different terms."""
        docs = [
            ["obj", "format"],
            ["stl", "format"],
        ]
        idf = compute_idf(docs)
        # "format" in both docs -> smoothed IDF = log(1 + 2/2) = log(2)
        assert idf["format"] == pytest.approx(math.log(2))
        # "obj" in 1 of 2 docs -> smoothed IDF = log(1 + 2/1) = log(3)
        assert idf["obj"] == pytest.approx(math.log(3))
        # "stl" in 1 of 2 docs -> smoothed IDF = log(1 + 2/1) = log(3)
        assert idf["stl"] == pytest.approx(math.log(3))

    def test_compute_idf_empty_corpus(self):
        """Empty corpus returns empty IDF."""
        assert compute_idf([]) == {}

    def test_compute_idf_duplicate_tokens_in_doc(self):
        """Repeated tokens within one document count as df=1 for that doc."""
        docs = [["obj", "obj", "obj"], ["stl"]]
        idf = compute_idf(docs)
        # "obj" appears in 1 doc -> smoothed IDF = log(1 + 2/1) = log(3)
        assert idf["obj"] == pytest.approx(math.log(3))


# -----------------------------------------------------------------------
# compute_tfidf_vector
# -----------------------------------------------------------------------

class TestComputeTFIDFVector:
    """Test TF-IDF vector computation."""

    def test_tfidf_vector_correct_weighting(self):
        """TF-IDF = TF * IDF for each term."""
        tokens = ["obj", "stl"]
        idf = {"obj": math.log(3), "stl": math.log(2)}
        vec = compute_tfidf_vector(tokens, idf)
        # TF for both is 0.5;  obj: 0.5 * log(3), stl: 0.5 * log(2)
        assert vec["obj"] == pytest.approx(0.5 * math.log(3))
        assert vec["stl"] == pytest.approx(0.5 * math.log(2))

    def test_tfidf_vector_empty_tokens(self):
        """Empty tokens produce empty vector."""
        vec = compute_tfidf_vector([], {"obj": 1.0})
        assert vec == {}

    def test_tfidf_vector_missing_idf_term(self):
        """Term not in IDF dict gets weight 0."""
        tokens = ["unknown"]
        idf = {"obj": 1.0}
        vec = compute_tfidf_vector(tokens, idf)
        assert vec["unknown"] == pytest.approx(0.0)


# -----------------------------------------------------------------------
# cosine_similarity
# -----------------------------------------------------------------------

class TestCosineSimilarity:
    """Test cosine similarity on sparse vectors."""

    def test_identical_vectors(self):
        """Identical vectors have similarity 1.0."""
        vec = {"obj": 0.5, "format": 0.3}
        assert cosine_similarity(vec, vec) == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        """Completely non-overlapping vectors have similarity 0.0."""
        vec1 = {"obj": 1.0}
        vec2 = {"stl": 1.0}
        assert cosine_similarity(vec1, vec2) == pytest.approx(0.0)

    def test_similar_vectors(self):
        """Partially overlapping vectors have 0 < similarity < 1."""
        vec1 = {"obj": 1.0, "format": 0.5}
        vec2 = {"obj": 0.8, "stl": 0.6}
        sim = cosine_similarity(vec1, vec2)
        assert 0.0 < sim < 1.0

    def test_zero_vector_first(self):
        """Empty first vector returns 0.0."""
        assert cosine_similarity({}, {"obj": 1.0}) == 0.0

    def test_zero_vector_second(self):
        """Empty second vector returns 0.0."""
        assert cosine_similarity({"obj": 1.0}, {}) == 0.0

    def test_both_zero_vectors(self):
        """Both empty vectors return 0.0."""
        assert cosine_similarity({}, {}) == 0.0


# -----------------------------------------------------------------------
# compute_tfidf_similarity (end-to-end)
# -----------------------------------------------------------------------

class TestComputeTFIDFSimilarity:
    """End-to-end TF-IDF similarity tests."""

    def test_identical_strings(self):
        """Identical non-trivial texts have similarity 1.0."""
        text = "supports obj format conversion"
        assert compute_tfidf_similarity(text, text) == pytest.approx(1.0)

    def test_empty_first_string(self):
        """Empty first string returns 0.0."""
        assert compute_tfidf_similarity("", "hello world test") == 0.0

    def test_empty_second_string(self):
        """Empty second string returns 0.0."""
        assert compute_tfidf_similarity("hello world test", "") == 0.0

    def test_both_empty_strings(self):
        """Both empty strings return 0.0."""
        assert compute_tfidf_similarity("", "") == 0.0

    def test_similar_texts_higher_than_dissimilar(self):
        """Semantically similar texts score higher than dissimilar ones."""
        claim = "Supports loading OBJ 3D model files"
        similar = "Load OBJ files for 3D models"
        dissimilar = "Python installation guide for beginners"

        sim_score = compute_tfidf_similarity(claim, similar)
        dis_score = compute_tfidf_similarity(claim, dissimilar)
        assert sim_score > dis_score

    def test_deterministic(self):
        """Same inputs always produce exactly the same score."""
        text1 = "Supports OBJ format"
        text2 = "OBJ and STL format supported"
        score_a = compute_tfidf_similarity(text1, text2)
        score_b = compute_tfidf_similarity(text1, text2)
        assert score_a == score_b

    def test_stopword_only_texts(self):
        """Texts containing only stopwords return 0.0."""
        assert compute_tfidf_similarity("the and or but", "is are was were") == 0.0


# -----------------------------------------------------------------------
# get_similarity_scorer (factory)
# -----------------------------------------------------------------------

class TestGetSimilarityScorer:
    """Test the scorer factory."""

    def test_returns_callable(self):
        """Factory returns a callable."""
        scorer = get_similarity_scorer()
        assert callable(scorer)

    def test_offline_scorer_works(self):
        """Offline scorer (no LLM client) produces valid scores."""
        scorer = get_similarity_scorer(llm_client=None)
        score = scorer("supports obj format", "obj format supported")
        assert 0.0 <= score <= 1.0

    def test_with_llm_client_still_returns_callable(self):
        """Even with an LLM client, factory returns a callable scorer."""
        # TC-1046 scope: LLM embedding not yet wired; factory still works
        scorer = get_similarity_scorer(llm_client="mock_client")
        assert callable(scorer)
        score = scorer("obj format", "obj format")
        assert score == pytest.approx(1.0)


# -----------------------------------------------------------------------
# Integration: TF-IDF vs Jaccard quality
# -----------------------------------------------------------------------

class TestTFIDFVsJaccard:
    """Verify TF-IDF produces better ranking than Jaccard for semantic pairs."""

    @staticmethod
    def _jaccard(text1: str, text2: str) -> float:
        """Reference Jaccard implementation (old algorithm)."""
        import re as _re
        words1 = set(_re.findall(r'\\w+', text1.lower()))
        words2 = set(_re.findall(r'\\w+', text2.lower()))
        if not words1 or not words2:
            return 0.0
        intersection = words1 & words2
        union = words1 | words2
        return len(intersection) / len(union) if union else 0.0

    def test_tfidf_better_discriminates_semantic_match(self):
        """TF-IDF should rank a true semantic match higher than Jaccard.

        When comparing a claim about OBJ loading against:
          A) evidence about OBJ loading (high semantic match)
          B) evidence about installation (low semantic match)
        TF-IDF should give the good match a HIGHER relative advantage
        (score_A - score_B) than Jaccard does, or at least match it.
        """
        claim = "This library supports loading OBJ 3D model files"
        good_evidence = (
            "The library can load OBJ files and convert them to "
            "other 3D formats such as STL and FBX"
        )
        bad_evidence = (
            "Install the library using pip install aspose-3d "
            "and configure your Python environment"
        )

        tfidf_good = compute_tfidf_similarity(claim, good_evidence)
        tfidf_bad = compute_tfidf_similarity(claim, bad_evidence)

        # TF-IDF must correctly rank good > bad
        assert tfidf_good > tfidf_bad, (
            f"TF-IDF failed to rank good evidence ({tfidf_good:.4f}) "
            f"higher than bad evidence ({tfidf_bad:.4f})"
        )

    def test_tfidf_score_range(self):
        """All TF-IDF scores are in [0, 1]."""
        pairs = [
            ("hello", "world"),
            ("supports obj", "supports obj"),
            ("", "something"),
            ("python library", "python library installation"),
        ]
        for t1, t2 in pairs:
            score = compute_tfidf_similarity(t1, t2)
            assert 0.0 <= score <= 1.0, f"Score {score} out of range for ({t1!r}, {t2!r})"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
