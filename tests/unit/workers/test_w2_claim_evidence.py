"""TC-3230: Tests for claim_evidence.py — claim-level chunk evidence mapping.

Covers:
- classify_evidence_type (4 tests)
- score_claim_chunk_relevance (5 tests)
- _truncate_excerpt (3 tests)
- build_claim_evidence_chunks (8 tests)
- enrich_evidence_map_with_chunks (4 tests)
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import pytest

from launch.workers.w2_facts_builder.claim_evidence import (
    TOP_K_CHUNKS_PER_CLAIM,
    MAX_EXCERPT_CHARS,
    classify_evidence_type,
    score_claim_chunk_relevance,
    _truncate_excerpt,
    build_claim_evidence_chunks,
    enrich_evidence_map_with_chunks,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_claim(
    claim_id: str = "abc123",
    claim_text: str = "Supports OBJ format import",
    claim_kind: str = "format",
    source_priority: int = 5,
) -> Dict[str, Any]:
    return {
        "claim_id": claim_id,
        "claim_text": claim_text,
        "claim_kind": claim_kind,
        "source_priority": source_priority,
        "truth_status": "fact",
        "citations": [],
    }


def _make_chunk(
    chunk_id: str = "ch001",
    file_path: str = "README.md",
    text: str = "This library supports OBJ format import and export.",
    heading_context: str = "Features",
) -> Dict[str, Any]:
    return {
        "chunk_id": chunk_id,
        "file_path": file_path,
        "text": text,
        "heading_context": heading_context,
        "token_count": len(text.split()),
    }


# ---------------------------------------------------------------------------
# TestClassifyEvidenceType
# ---------------------------------------------------------------------------


class TestClassifyEvidenceType:
    """Test evidence_type classification from file paths."""

    def test_readme_detection(self):
        assert classify_evidence_type("README.md") == "readme"
        assert classify_evidence_type("docs/README.rst") == "readme"

    def test_python_source(self):
        assert classify_evidence_type("src/aspose/scene.py") == "code_docstring"
        assert classify_evidence_type("stubs/aspose/scene.pyi") == "code_docstring"

    def test_manifest_detection(self):
        assert classify_evidence_type("pyproject.toml") == "manifest"
        assert classify_evidence_type("setup.py") == "manifest"
        assert classify_evidence_type("package.json") == "manifest"

    def test_doc_default(self):
        assert classify_evidence_type("docs/tutorial.md") == "doc"
        assert classify_evidence_type("CHANGELOG.rst") == "doc"
        assert classify_evidence_type("notes.txt") == "doc"


# ---------------------------------------------------------------------------
# TestScoreClaimChunkRelevance
# ---------------------------------------------------------------------------


class TestScoreClaimChunkRelevance:
    """Test scoring formula matches map_evidence pattern."""

    def test_identical_text_high_score(self):
        text = "Supports OBJ format import"
        score = score_claim_chunk_relevance(text, "format", text)
        assert score > 0.5

    def test_unrelated_text_low_score(self):
        score = score_claim_chunk_relevance(
            "Supports OBJ format import",
            "format",
            "The weather is sunny today in Barcelona",
        )
        assert score < 0.3

    def test_source_priority_affects_base(self):
        text = "Supports OBJ format import"
        chunk = "Library supports OBJ file format"
        score_high = score_claim_chunk_relevance(text, "format", chunk, source_priority=1)
        score_low = score_claim_chunk_relevance(text, "format", chunk, source_priority=7)
        assert score_high > score_low

    def test_deterministic_same_inputs(self):
        text = "Supports OBJ format import"
        chunk = "Library supports OBJ file format"
        s1 = score_claim_chunk_relevance(text, "format", chunk, source_priority=3)
        s2 = score_claim_chunk_relevance(text, "format", chunk, source_priority=3)
        assert s1 == s2

    def test_score_capped_at_one(self):
        # Even with perfect overlap and high priority, score <= 1.0
        text = "aspose cells"
        score = score_claim_chunk_relevance(text, "feature", text, source_priority=1)
        assert score <= 1.0


# ---------------------------------------------------------------------------
# TestTruncateExcerpt
# ---------------------------------------------------------------------------


class TestTruncateExcerpt:
    """Test excerpt truncation to max_chars."""

    def test_short_text_unchanged(self):
        assert _truncate_excerpt("Hello world") == "Hello world"

    def test_long_text_truncated_at_word(self):
        text = "word " * 200  # 1000 chars
        result = _truncate_excerpt(text, max_chars=50)
        assert len(result) <= 53  # 50 + "..."
        assert result.endswith("...")

    def test_exactly_max_chars(self):
        text = "a" * MAX_EXCERPT_CHARS
        assert _truncate_excerpt(text) == text


# ---------------------------------------------------------------------------
# TestBuildClaimEvidenceChunks
# ---------------------------------------------------------------------------


class TestBuildClaimEvidenceChunks:
    """Test the main builder function."""

    def test_basic_mapping(self):
        claims = [_make_claim()]
        chunks = [_make_chunk()]
        result = build_claim_evidence_chunks(claims, chunks)

        assert result["schema_version"] == "1.0"
        assert len(result["entries"]) == 1
        entry = result["entries"][0]
        assert entry["claim_id"] == "abc123"
        assert len(entry["evidence_chunks"]) >= 1

    def test_top_k_cap_enforced(self):
        claims = [_make_claim()]
        # Create 10 relevant chunks
        chunks = [
            _make_chunk(
                chunk_id=f"ch{i:03d}",
                text=f"Supports OBJ format import variant {i}",
            )
            for i in range(10)
        ]
        result = build_claim_evidence_chunks(claims, chunks)

        entry = result["entries"][0]
        assert len(entry["evidence_chunks"]) <= TOP_K_CHUNKS_PER_CLAIM

    def test_excerpt_max_chars_enforced(self):
        claims = [_make_claim()]
        long_text = "word " * 200  # well over 500 chars
        chunks = [_make_chunk(text=long_text)]
        result = build_claim_evidence_chunks(claims, chunks)

        for entry in result["entries"]:
            for chunk in entry["evidence_chunks"]:
                assert len(chunk["excerpt"]) <= MAX_EXCERPT_CHARS + 3  # +3 for "..."

    def test_deterministic_output(self):
        claims = [
            _make_claim(claim_id="z_last", claim_text="Last claim"),
            _make_claim(claim_id="a_first", claim_text="First claim"),
        ]
        chunks = [_make_chunk()]

        r1 = build_claim_evidence_chunks(claims, chunks)
        r2 = build_claim_evidence_chunks(claims, chunks)

        assert json.dumps(r1, sort_keys=True) == json.dumps(r2, sort_keys=True)
        # Sorted by claim_id
        assert r1["entries"][0]["claim_id"] == "a_first"
        assert r1["entries"][1]["claim_id"] == "z_last"

    def test_empty_chunks_no_crash(self):
        claims = [_make_claim()]
        result = build_claim_evidence_chunks(claims, [])
        assert result["metadata"]["claims_with_chunks"] == 0

    def test_empty_claims_no_crash(self):
        chunks = [_make_chunk()]
        result = build_claim_evidence_chunks([], chunks)
        assert result["metadata"]["total_claims"] == 0
        assert result["entries"] == []

    def test_min_score_filtering(self):
        claims = [_make_claim(claim_text="quantum physics entanglement")]
        chunks = [_make_chunk(text="The weather is sunny today")]
        # High min_score should filter everything
        result = build_claim_evidence_chunks(claims, chunks, min_score=0.99)
        entry = result["entries"][0]
        assert entry["evidence_chunks"] == []

    def test_schema_validation(self):
        """Output validates against claim_evidence_chunks.schema.json."""
        claims = [_make_claim()]
        chunks = [_make_chunk()]
        result = build_claim_evidence_chunks(claims, chunks)

        schema_path = (
            Path(__file__).resolve().parents[3]
            / "specs" / "schemas" / "claim_evidence_chunks.schema.json"
        )
        if schema_path.exists():
            try:
                import jsonschema
                schema = json.loads(schema_path.read_text(encoding="utf-8"))
                jsonschema.validate(result, schema)
            except ImportError:
                pass  # jsonschema not installed — skip validation


# ---------------------------------------------------------------------------
# TestEnrichEvidenceMapWithChunks
# ---------------------------------------------------------------------------


class TestEnrichEvidenceMapWithChunks:
    """Test backward-compatible evidence_map enrichment."""

    def _make_evidence_map(self) -> Dict[str, Any]:
        return {
            "schema_version": "1.0.0",
            "repo_url": "https://github.com/example/repo",
            "repo_sha": "abc123",
            "claims": [
                {
                    "claim_id": "c1",
                    "claim_text": "Supports OBJ",
                    "claim_kind": "format",
                    "truth_status": "fact",
                    "citations": [],
                },
                {
                    "claim_id": "c2",
                    "claim_text": "Has Scene class",
                    "claim_kind": "api",
                    "truth_status": "fact",
                    "citations": [],
                },
            ],
            "contradictions": [],
        }

    def _make_ce_artifact(self) -> Dict[str, Any]:
        return {
            "schema_version": "1.0",
            "entries": [
                {
                    "claim_id": "c1",
                    "evidence_chunks": [
                        {"chunk_id": "ch1", "score": 0.85,
                         "file_path": "README.md", "heading_context": "Formats",
                         "excerpt": "Supports OBJ format", "evidence_type": "readme"},
                    ],
                },
                {
                    "claim_id": "c2",
                    "evidence_chunks": [],
                },
            ],
            "metadata": {"total_claims": 2, "claims_with_chunks": 1, "avg_chunks_per_claim": 0.5},
        }

    def test_adds_evidence_chunks_field(self):
        em = self._make_evidence_map()
        ce = self._make_ce_artifact()
        result = enrich_evidence_map_with_chunks(em, ce)
        c1 = next(c for c in result["claims"] if c["claim_id"] == "c1")
        assert "evidence_chunks" in c1
        assert c1["evidence_chunks"][0]["chunk_id"] == "ch1"

    def test_existing_fields_preserved(self):
        em = self._make_evidence_map()
        ce = self._make_ce_artifact()
        result = enrich_evidence_map_with_chunks(em, ce)
        assert result["schema_version"] == "1.0.0"
        assert result["repo_url"] == "https://github.com/example/repo"
        for claim in result["claims"]:
            assert "claim_text" in claim
            assert "truth_status" in claim

    def test_claims_without_chunks_no_field(self):
        em = self._make_evidence_map()
        ce = self._make_ce_artifact()
        result = enrich_evidence_map_with_chunks(em, ce)
        c2 = next(c for c in result["claims"] if c["claim_id"] == "c2")
        # c2 had empty evidence_chunks — no field added
        assert "evidence_chunks" not in c2

    def test_schema_still_validates(self):
        """evidence_map with evidence_chunks still passes schema validation."""
        em = self._make_evidence_map()
        ce = self._make_ce_artifact()
        result = enrich_evidence_map_with_chunks(em, ce)

        schema_path = (
            Path(__file__).resolve().parents[3]
            / "specs" / "schemas" / "evidence_map.schema.json"
        )
        if schema_path.exists():
            try:
                import jsonschema
                schema = json.loads(schema_path.read_text(encoding="utf-8"))
                jsonschema.validate(result, schema)
            except ImportError:
                pass  # jsonschema not installed
