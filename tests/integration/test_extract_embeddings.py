"""Integration tests for extract.py Phase B.4 embedding index (TC-3775).

Validates that _build_embedding_index produces the embedding_index.json
artifact when called with realistic claims and doc contexts.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from launcher.models.claims import Claim, EvidenceAnchor, Snippet
from launcher.shared.embeddings import EmbeddingIndex


def _make_claim(claim_id: str, text: str, kind: str = "feature") -> Claim:
    return Claim(
        claim_id=claim_id,
        text=text,
        kind=kind,
        evidence=[],
        visibility="public",
        tier_relevance="all",
    )


def _make_context(run_dir: Path) -> MagicMock:
    """Build a minimal WorkerContext mock with run_dir and store."""
    ctx = MagicMock()
    ctx.run_dir = run_dir
    ctx.llm_config = None  # No embedding endpoint -> TF-IDF fallback
    store = MagicMock()
    store.artifacts_dir = run_dir / "artifacts"
    ctx.store = store
    return ctx


class TestBuildEmbeddingIndex:
    def test_produces_artifact(self):
        """Phase B.4 should write embedding_index.json with claim keys."""
        from launcher.workers.understand.extract import _build_embedding_index

        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            (run_dir / "artifacts").mkdir()

            claims = [
                _make_claim("c1", "Python library for spreadsheet manipulation"),
                _make_claim("c2", "Supports XLSX and CSV file formats"),
            ]
            doc_contexts = [
                {"path": "README.md", "content": "This is a Python library for working with spreadsheets. It supports XLSX, CSV, and ODS formats."},
            ]
            context = _make_context(run_dir)

            _build_embedding_index(claims, doc_contexts, context)

            artifact = run_dir / "artifacts" / "embedding_index.json"
            assert artifact.exists(), "embedding_index.json was not created"

            data = json.loads(artifact.read_text(encoding="utf-8"))
            assert "vectors" in data
            assert "claim:c1" in data["vectors"]
            assert "claim:c2" in data["vectors"]
            assert any(k.startswith("doc:") for k in data["vectors"])

    def test_empty_claims_skips(self):
        """No claims + no docs -> no artifact."""
        from launcher.workers.understand.extract import _build_embedding_index

        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            (run_dir / "artifacts").mkdir()

            context = _make_context(run_dir)
            _build_embedding_index([], [], context)

            artifact = run_dir / "artifacts" / "embedding_index.json"
            assert not artifact.exists()

    def test_index_loadable(self):
        """Saved index can be loaded and queried."""
        from launcher.workers.understand.extract import _build_embedding_index

        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            (run_dir / "artifacts").mkdir()

            claims = [
                _make_claim("c1", "Python spreadsheet library with formula support"),
                _make_claim("c2", "Java document conversion toolkit"),
            ]
            doc_contexts = [
                {"path": "docs/api.md", "content": "The Python spreadsheet library provides formula evaluation and cell styling capabilities."},
            ]
            context = _make_context(run_dir)

            _build_embedding_index(claims, doc_contexts, context)

            artifact = run_dir / "artifacts" / "embedding_index.json"
            idx = EmbeddingIndex.load(artifact)
            assert len(idx) >= 2

            # claim:c1 should be more similar to the doc about spreadsheets
            # than claim:c2 (Java conversion)
            sim_c1 = idx.similarity("claim:c1", "doc:docs/api.md:0")
            sim_c2 = idx.similarity("claim:c2", "doc:docs/api.md:0")
            assert sim_c1 > sim_c2, (
                f"Expected claim:c1 ({sim_c1:.3f}) > claim:c2 ({sim_c2:.3f}) "
                f"for spreadsheet doc similarity"
            )


class TestChunkText:
    def test_short_text_single_chunk(self):
        from launcher.workers.understand.extract import _chunk_text
        chunks = _chunk_text("short text")
        assert chunks == ["short text"]

    def test_empty(self):
        from launcher.workers.understand.extract import _chunk_text
        assert _chunk_text("") == []

    def test_long_text_splits(self):
        from launcher.workers.understand.extract import _chunk_text
        long_text = "Hello world. " * 100  # ~1300 chars
        chunks = _chunk_text(long_text, max_chars=200)
        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk) <= 250  # some tolerance for boundary splits
