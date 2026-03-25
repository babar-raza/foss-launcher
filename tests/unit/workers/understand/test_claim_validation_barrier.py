"""TC-5138: Tests for claim dict validation barrier.

Verifies that malformed LLM output (null values, wrong types, missing keys)
is handled gracefully without crashing the pipeline.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from launcher.models.claims import Claim, EvidenceAnchor


# ── EvidenceAnchor model_validator tests ───────────────────────────────


class TestEvidenceAnchorCoercion:
    """Verify the @model_validator(mode='before') on EvidenceAnchor."""

    def test_snippet_none_coerced_to_empty(self):
        """LLM returns 'snippet': null — should coerce to ''."""
        anchor = EvidenceAnchor(source_file="file.java", snippet=None)
        assert anchor.snippet == ""

    def test_snippet_missing_uses_default(self):
        """Missing snippet key uses field default ''."""
        anchor = EvidenceAnchor(source_file="file.java")
        assert anchor.snippet == ""

    def test_snippet_valid_string_preserved(self):
        """Normal snippet is preserved."""
        anchor = EvidenceAnchor(source_file="file.java", snippet="Scene scene = new Scene();")
        assert anchor.snippet == "Scene scene = new Scene();"

    def test_source_file_none_coerced_to_empty(self):
        """LLM returns 'source_file': null — should coerce to ''."""
        anchor = EvidenceAnchor(source_file=None, snippet="code")
        assert anchor.source_file == ""

    def test_line_start_string_coerced_to_int(self):
        """LLM returns line_start as string — should coerce to int."""
        anchor = EvidenceAnchor(source_file="f.java", line_start="42")
        assert anchor.line_start == 42

    def test_line_start_invalid_string_coerced_to_none(self):
        """LLM returns unparseable line_start — should coerce to None."""
        anchor = EvidenceAnchor(source_file="f.java", line_start="abc")
        assert anchor.line_start is None

    def test_line_end_none_preserved(self):
        """None line_end is valid and preserved."""
        anchor = EvidenceAnchor(source_file="f.java", line_end=None)
        assert anchor.line_end is None

    def test_dict_input_with_all_nulls(self):
        """Dict with all nullable fields null — should construct successfully."""
        anchor = EvidenceAnchor.model_validate({
            "source_file": None,
            "line_start": None,
            "line_end": None,
            "snippet": None,
        })
        assert anchor.source_file == ""
        assert anchor.snippet == ""
        assert anchor.line_start is None
        assert anchor.line_end is None


# ── _sanitize_raw_claim tests ──────────────────────────────────────────


class TestSanitizeRawClaim:
    """Verify _sanitize_raw_claim normalises untrusted dicts."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from launcher.workers.understand.extract._validation import _sanitize_raw_claim
        self.sanitize = _sanitize_raw_claim

    def test_valid_claim_passes_through(self):
        raw = {
            "text": "Scene.open() loads a 3D file.",
            "kind": "api",
            "evidence": [{"source_file": "Scene.java", "snippet": "open()"}],
        }
        result = self.sanitize(raw)
        assert result is not None
        assert result["text"] == "Scene.open() loads a 3D file."

    def test_null_text_returns_none(self):
        raw = {"text": None, "kind": "api", "evidence": []}
        assert self.sanitize(raw) is None

    def test_missing_text_returns_none(self):
        raw = {"kind": "api", "evidence": []}
        assert self.sanitize(raw) is None

    def test_null_evidence_coerced_to_empty_list(self):
        raw = {"text": "A claim.", "kind": "api", "evidence": None}
        result = self.sanitize(raw)
        assert result is not None
        assert result["evidence"] == []

    def test_missing_evidence_coerced_to_empty_list(self):
        raw = {"text": "A claim.", "kind": "api"}
        result = self.sanitize(raw)
        assert result is not None
        assert result["evidence"] == []

    def test_null_snippet_in_evidence_coerced(self):
        raw = {
            "text": "A claim.",
            "kind": "api",
            "evidence": [{"source_file": "f.java", "snippet": None}],
        }
        result = self.sanitize(raw)
        assert result["evidence"][0]["snippet"] == ""

    def test_null_source_file_in_evidence_coerced(self):
        raw = {
            "text": "A claim.",
            "kind": "api",
            "evidence": [{"source_file": None, "snippet": "code"}],
        }
        result = self.sanitize(raw)
        assert result["evidence"][0]["source_file"] == ""

    def test_null_kind_coerced_to_feature(self):
        raw = {"text": "A claim.", "kind": None, "evidence": []}
        result = self.sanitize(raw)
        assert result["kind"] == "feature"

    def test_missing_kind_coerced_to_feature(self):
        raw = {"text": "A claim.", "evidence": []}
        result = self.sanitize(raw)
        assert result["kind"] == "feature"

    def test_non_dict_input_returns_none(self):
        assert self.sanitize("not a dict") is None
        assert self.sanitize(42) is None
        assert self.sanitize(None) is None

    def test_non_dict_evidence_items_filtered(self):
        raw = {
            "text": "A claim.",
            "kind": "api",
            "evidence": ["not a dict", {"source_file": "f.java", "snippet": "ok"}],
        }
        result = self.sanitize(raw)
        assert len(result["evidence"]) == 1
        assert result["evidence"][0]["source_file"] == "f.java"


# ── Integration: _validate_and_normalize_claims with malformed input ───


class TestValidateNormalizeWithMalformedInput:
    """Verify that _validate_and_normalize_claims handles malformed dicts
    without crashing the pipeline."""

    @pytest.fixture()
    def _deps(self):
        from unittest.mock import MagicMock
        from launcher.models.product import ProductIdentity, ApiSurface
        self.product = MagicMock(spec=ProductIdentity)
        self.product.family = "3d"
        self.product.platform = "java"
        self.product.display_name = "Aspose.3D"
        self.product.canonical_import = "com.aspose.threed"
        self.api_surface = MagicMock(spec=ApiSurface)
        self.api_surface.class_briefs = []
        self.api_surface.public_classes = []

    def test_mixed_valid_and_null_claims(self, _deps):
        from launcher.workers.understand.extract._validation import (
            _validate_and_normalize_claims,
        )
        raw_claims = [
            # Valid claim
            {
                "text": "Scene.open() loads a 3D model file in the supported format.",
                "kind": "api",
                "evidence": [{"source_file": "Scene.java", "snippet": "open()"}],
            },
            # Null text — should be skipped
            {
                "text": None,
                "kind": "api",
                "evidence": [],
            },
            # Valid claim with null snippet in evidence
            {
                "text": "The library supports importing OBJ files with full geometry support.",
                "kind": "format",
                "evidence": [{"source_file": "README.md", "snippet": None}],
            },
        ]
        claims = _validate_and_normalize_claims(
            raw_claims, self.product, self.api_surface,
        )
        # Should get 2 valid claims (null-text one skipped)
        assert len(claims) == 2
        # Second claim's evidence should have coerced snippet
        assert claims[1].evidence[0].snippet == ""
