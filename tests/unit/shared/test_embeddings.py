"""Unit tests for launcher.shared.embeddings (TC-3774).

Tests both the TF-IDF deterministic path (ported from v1) and the
EmbeddingIndex/EmbeddingClient infrastructure.
"""
from __future__ import annotations

import json
import math
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import MagicMock, patch

import pytest

from launcher.shared.embeddings import (
    EmbeddingClient,
    EmbeddingIndex,
    compute_idf,
    compute_tf,
    compute_tfidf_similarity,
    compute_tfidf_vector,
    cosine_similarity,
    cosine_similarity_dense,
    embed_texts,
    get_similarity_scorer,
    precompute_token_cache,
    tokenize,
)


# ---------------------------------------------------------------------------
# Tokenization tests (ported from v1 test_w2_embeddings.py)
# ---------------------------------------------------------------------------


class TestTokenize:
    def test_basic(self):
        result = tokenize("Hello world this is a test document")
        assert "hello" in result
        assert "world" in result
        assert "test" in result
        assert "document" in result

    def test_empty(self):
        assert tokenize("") == []
        assert tokenize(None) == []  # type: ignore[arg-type]

    def test_stopword_removal(self):
        result = tokenize("the and or of a an in is to for")
        assert result == []

    def test_short_word_removal(self):
        result = tokenize("go do it be me we")
        assert result == []

    def test_preserves_order(self):
        result = tokenize("python java rust golang")
        assert result == ["python", "java", "rust", "golang"]

    def test_lowercases(self):
        result = tokenize("Python Java RUST")
        assert result == ["python", "java", "rust"]

    def test_handles_special_chars(self):
        result = tokenize("hello-world foo_bar baz.qux")
        assert "hello" in result
        assert "world" in result
        # \w+ treats underscore as word char, so "foo_bar" is one token
        assert "foo_bar" in result


# ---------------------------------------------------------------------------
# TF computation
# ---------------------------------------------------------------------------


class TestComputeTF:
    def test_basic(self):
        tokens = ["python", "java", "python"]
        tf = compute_tf(tokens)
        assert abs(tf["python"] - 2 / 3) < 1e-9
        assert abs(tf["java"] - 1 / 3) < 1e-9

    def test_empty(self):
        assert compute_tf([]) == {}

    def test_single_token(self):
        tf = compute_tf(["hello"])
        assert tf == {"hello": 1.0}


# ---------------------------------------------------------------------------
# IDF computation
# ---------------------------------------------------------------------------


class TestComputeIDF:
    def test_basic(self):
        docs = [["python", "java"], ["python", "rust"]]
        idf = compute_idf(docs)
        # python in both docs: log(1 + 2/2) = log(2)
        assert abs(idf["python"] - math.log(2)) < 1e-9
        # java in 1 doc: log(1 + 2/1) = log(3)
        assert abs(idf["java"] - math.log(3)) < 1e-9

    def test_empty(self):
        assert compute_idf([]) == {}

    def test_single_doc(self):
        idf = compute_idf([["hello", "world"]])
        # Both in 1/1 doc: log(1 + 1/1) = log(2)
        assert abs(idf["hello"] - math.log(2)) < 1e-9

    def test_smoothing_prevents_zero(self):
        """Terms in all docs get log(2) not 0."""
        docs = [["shared"], ["shared"]]
        idf = compute_idf(docs)
        assert idf["shared"] > 0


# ---------------------------------------------------------------------------
# TF-IDF vector
# ---------------------------------------------------------------------------


class TestComputeTFIDFVector:
    def test_basic(self):
        tokens = ["python", "java"]
        idf = {"python": 1.0, "java": 2.0}
        vec = compute_tfidf_vector(tokens, idf)
        assert abs(vec["python"] - 0.5) < 1e-9  # tf=0.5 * idf=1.0
        assert abs(vec["java"] - 1.0) < 1e-9  # tf=0.5 * idf=2.0


# ---------------------------------------------------------------------------
# Cosine similarity (sparse)
# ---------------------------------------------------------------------------


class TestCosineSimilarity:
    def test_identical(self):
        vec = {"a": 1.0, "b": 2.0}
        assert abs(cosine_similarity(vec, vec) - 1.0) < 1e-9

    def test_orthogonal(self):
        v1 = {"a": 1.0}
        v2 = {"b": 1.0}
        assert cosine_similarity(v1, v2) == 0.0

    def test_partial_overlap(self):
        v1 = {"a": 1.0, "b": 1.0}
        v2 = {"a": 1.0, "c": 1.0}
        sim = cosine_similarity(v1, v2)
        assert 0.0 < sim < 1.0

    def test_empty(self):
        assert cosine_similarity({}, {"a": 1.0}) == 0.0
        assert cosine_similarity({"a": 1.0}, {}) == 0.0
        assert cosine_similarity({}, {}) == 0.0


# ---------------------------------------------------------------------------
# Cosine similarity (dense)
# ---------------------------------------------------------------------------


class TestCosineSimilarityDense:
    def test_identical(self):
        vec = [1.0, 2.0, 3.0]
        assert abs(cosine_similarity_dense(vec, vec) - 1.0) < 1e-9

    def test_orthogonal(self):
        v1 = [1.0, 0.0]
        v2 = [0.0, 1.0]
        assert abs(cosine_similarity_dense(v1, v2)) < 1e-9

    def test_different_lengths(self):
        assert cosine_similarity_dense([1.0], [1.0, 2.0]) == 0.0

    def test_empty(self):
        assert cosine_similarity_dense([], [1.0]) == 0.0


# ---------------------------------------------------------------------------
# End-to-end TF-IDF similarity
# ---------------------------------------------------------------------------


class TestComputeTFIDFSimilarity:
    def test_identical_texts(self):
        text = "Python library for spreadsheet manipulation"
        assert compute_tfidf_similarity(text, text) == 1.0

    def test_no_overlap(self):
        assert compute_tfidf_similarity("python java rust", "cat dog fish") == 0.0

    def test_partial_overlap(self):
        t1 = "Python library for spreadsheet manipulation"
        t2 = "Python package for data processing and spreadsheet export"
        sim = compute_tfidf_similarity(t1, t2)
        assert 0.0 < sim < 1.0

    def test_with_cache(self):
        t1 = "Python spreadsheet library"
        t2 = "Python data processing and spreadsheet tools"
        cache = precompute_token_cache(t2)
        sim_cached = compute_tfidf_similarity(t1, "", _tokens2_cache=cache)
        sim_direct = compute_tfidf_similarity(t1, t2)
        assert abs(sim_cached - sim_direct) < 1e-9

    def test_empty_text(self):
        assert compute_tfidf_similarity("", "hello world test") == 0.0
        assert compute_tfidf_similarity("hello world test", "") == 0.0

    def test_determinism(self):
        """Same inputs must produce same output (PYTHONHASHSEED=0)."""
        t1 = "Python library for document conversion"
        t2 = "Java SDK for file format manipulation and conversion"
        s1 = compute_tfidf_similarity(t1, t2)
        s2 = compute_tfidf_similarity(t1, t2)
        assert s1 == s2


# ---------------------------------------------------------------------------
# Precompute token cache
# ---------------------------------------------------------------------------


class TestPrecomputeTokenCache:
    def test_basic(self):
        cache = precompute_token_cache("Python library for data processing")
        assert cache is not None
        tokens, fset = cache
        assert isinstance(tokens, list)
        assert isinstance(fset, frozenset)
        assert "python" in fset

    def test_empty(self):
        assert precompute_token_cache("") is None
        assert precompute_token_cache("the and or") is None


# ---------------------------------------------------------------------------
# EmbeddingIndex
# ---------------------------------------------------------------------------


class TestEmbeddingIndex:
    def test_add_and_len(self):
        idx = EmbeddingIndex()
        idx.add("a", [1.0, 0.0])
        idx.add("b", [0.0, 1.0])
        assert len(idx) == 2

    def test_keys_sorted(self):
        idx = EmbeddingIndex()
        idx.add("z", [1.0])
        idx.add("a", [2.0])
        assert idx.keys() == ["a", "z"]

    def test_similarity_dense(self):
        idx = EmbeddingIndex()
        idx.add("a", [1.0, 0.0])
        idx.add("b", [1.0, 0.0])
        assert abs(idx.similarity("a", "b") - 1.0) < 1e-9

    def test_similarity_sparse(self):
        idx = EmbeddingIndex()
        idx.add("a", {"python": 1.0, "java": 0.5})
        idx.add("b", {"python": 1.0, "rust": 0.5})
        sim = idx.similarity("a", "b")
        assert 0.0 < sim < 1.0

    def test_similarity_missing_key(self):
        idx = EmbeddingIndex()
        idx.add("a", [1.0])
        assert idx.similarity("a", "missing") == 0.0

    def test_most_similar(self):
        idx = EmbeddingIndex()
        idx.add("q", [1.0, 0.0, 0.0])
        idx.add("a", [0.9, 0.1, 0.0])
        idx.add("b", [0.0, 0.0, 1.0])
        results = idx.most_similar("q", top_k=2)
        assert len(results) >= 1
        assert results[0][0] == "a"

    def test_save_load_roundtrip(self):
        idx = EmbeddingIndex()
        idx.add("claim:abc", [0.1, 0.2, 0.3])
        idx.add("doc:readme:0", [0.4, 0.5, 0.6])

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "index.json"
            idx.save(path)

            loaded = EmbeddingIndex.load(path)
            assert len(loaded) == 2
            assert loaded.keys() == ["claim:abc", "doc:readme:0"]
            assert loaded.get("claim:abc") == [0.1, 0.2, 0.3]

    def test_save_deterministic(self):
        """Two saves of the same data must produce identical bytes."""
        idx = EmbeddingIndex()
        idx.add("b", [2.0])
        idx.add("a", [1.0])

        with tempfile.TemporaryDirectory() as tmp:
            p1 = Path(tmp) / "a.json"
            p2 = Path(tmp) / "b.json"
            idx.save(p1)
            idx.save(p2)
            assert p1.read_bytes() == p2.read_bytes()


# ---------------------------------------------------------------------------
# embed_texts
# ---------------------------------------------------------------------------


class TestEmbedTexts:
    def test_tfidf_fallback(self):
        texts = {
            "claim:1": "Python spreadsheet library",
            "claim:2": "Java file conversion SDK",
        }
        idx = embed_texts(texts, client=None)
        assert idx is not None
        assert len(idx) == 2
        sim = idx.similarity("claim:1", "claim:2")
        assert isinstance(sim, float)

    def test_empty_texts(self):
        assert embed_texts({}) is None

    def test_api_with_mock(self):
        mock_client = MagicMock(spec=EmbeddingClient)
        mock_client.embed.return_value = [[0.1, 0.2], [0.3, 0.4]]

        texts = {"a": "hello world test", "b": "foo bar baz"}
        idx = embed_texts(texts, client=mock_client)
        assert idx is not None
        assert len(idx) == 2
        mock_client.embed.assert_called_once()

    def test_api_fallback_on_error(self):
        mock_client = MagicMock(spec=EmbeddingClient)
        mock_client.embed.side_effect = RuntimeError("API down")

        texts = {"a": "hello world test"}
        idx = embed_texts(texts, client=mock_client)
        # Should fall back to TF-IDF and still produce an index
        assert idx is not None


# ---------------------------------------------------------------------------
# EmbeddingClient
# ---------------------------------------------------------------------------


_PATCH_HTTP_POST = "launcher.clients.http._get_session"


def _mock_session_with_response(resp):
    """Create a mock session whose .post() returns resp."""
    session = MagicMock()
    session.post.return_value = resp
    return session


class TestEmbeddingClient:
    def test_is_available_success(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200

        client = EmbeddingClient(base_url="http://test:8080/v1", model="test-model")
        with patch(_PATCH_HTTP_POST, return_value=_mock_session_with_response(mock_resp)):
            with patch("launcher.clients.http._validate_url"):
                result = client.is_available()
        assert result is True

    def test_is_available_failure(self):
        client = EmbeddingClient(base_url="http://test:8080/v1", model="test-model")
        with patch("launcher.clients.http._validate_url"):
            with patch(_PATCH_HTTP_POST, side_effect=Exception("timeout")):
                result = client.is_available()
        assert result is False

    def test_embed_success(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": [
                {"embedding": [0.1, 0.2], "index": 0},
                {"embedding": [0.3, 0.4], "index": 1},
            ]
        }

        client = EmbeddingClient(base_url="http://test:8080/v1", model="test-model")
        with patch(_PATCH_HTTP_POST, return_value=_mock_session_with_response(mock_resp)):
            with patch("launcher.clients.http._validate_url"):
                vectors = client.embed(["hello", "world"])
        assert len(vectors) == 2
        assert vectors[0] == [0.1, 0.2]

    def test_embed_error_status(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"

        client = EmbeddingClient(base_url="http://test:8080/v1", model="test-model")
        with patch(_PATCH_HTTP_POST, return_value=_mock_session_with_response(mock_resp)):
            with patch("launcher.clients.http._validate_url"):
                with pytest.raises(RuntimeError, match="500"):
                    client.embed(["hello"])


# ---------------------------------------------------------------------------
# get_similarity_scorer
# ---------------------------------------------------------------------------


class TestGetSimilarityScorer:
    def test_no_config_returns_tfidf(self):
        scorer = get_similarity_scorer(None)
        assert scorer is compute_tfidf_similarity

    def test_config_without_embedding_returns_tfidf(self):
        mock_cfg = MagicMock()
        mock_cfg.embedding = None
        scorer = get_similarity_scorer(mock_cfg)
        assert scorer is compute_tfidf_similarity

    def test_tfidf_scorer_works(self):
        scorer = get_similarity_scorer(None)
        sim = scorer("python library test", "python library test")
        assert sim == 1.0
