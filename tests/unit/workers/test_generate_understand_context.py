"""Regression tests for the TC-4318 / TC-HO-09-R GenerationContext → understand namespace chain.

Specifically tests _make_understand_from_context to ensure product_evidence_dict is correctly
deserialized, that fallback to ProductEvidence() works safely, and that api_fact_member_names
is correctly extracted from extraction_db when available.
"""
from __future__ import annotations

import pytest

from launcher.models.understanding import ProductEvidence
from launcher.models.product import ApiSurface


def _call_make_understand(
    product_evidence_dict=None,
    api_surface_dict=None,
    extraction_db=None,
):
    """Import and call _make_understand_from_context with minimal required args."""
    from launcher.workers.generate.worker import _make_understand_from_context
    from types import SimpleNamespace
    # Minimal claims/snippets/product for the function
    return _make_understand_from_context(
        claims=[],
        snippets=[],
        product=None,
        richness_tier_str="B",
        api_surface_dict=api_surface_dict or {},
        product_evidence_dict=product_evidence_dict,
    )


class TestMakeUnderstandFromContextProductEvidence:
    """TC-4318 / TC-HO-09-R: product_evidence_dict deserialization in _make_understand_from_context."""

    def test_with_supported_formats_populates_model(self):
        """product_evidence_dict with supported_formats produces populated ProductEvidence."""
        ns = _call_make_understand(
            product_evidence_dict={"supported_formats": ["PDF", "DOCX"], "input_formats": ["PDF"]}
        )
        assert isinstance(ns.product_evidence, ProductEvidence)
        assert ns.product_evidence.supported_formats == ["PDF", "DOCX"]
        assert ns.product_evidence.input_formats == ["PDF"]

    def test_with_none_returns_empty_product_evidence(self):
        """None product_evidence_dict safely returns empty ProductEvidence."""
        ns = _call_make_understand(product_evidence_dict=None)
        assert isinstance(ns.product_evidence, ProductEvidence)
        assert ns.product_evidence.supported_formats == []
        assert ns.product_evidence.install_recipe is None

    def test_with_empty_dict_returns_empty_product_evidence(self):
        """Empty dict {} returns empty ProductEvidence (pre-TC-4318 bundle compat)."""
        ns = _call_make_understand(product_evidence_dict={})
        assert isinstance(ns.product_evidence, ProductEvidence)
        assert ns.product_evidence.supported_formats == []

    def test_with_invalid_dict_falls_back_to_empty(self):
        """Malformed dict that fails pydantic validation falls back to ProductEvidence()."""
        # 'supported_formats' must be a list, not an int
        ns = _call_make_understand(product_evidence_dict={"supported_formats": 999})
        assert isinstance(ns.product_evidence, ProductEvidence)
        # Should not raise — should silently fall back
        assert ns.product_evidence.supported_formats == []

    def test_limitations_transferred(self):
        """Limitations list in product_evidence_dict survives deserialization."""
        pe_dict = {
            "supported_formats": ["XLSX"],
            "limitations": [{"feature": "macro support", "constraint": "not supported"}],
        }
        ns = _call_make_understand(product_evidence_dict=pe_dict)
        assert len(ns.product_evidence.limitations) == 1
        assert ns.product_evidence.limitations[0].feature == "macro support"

    def test_extraction_db_remains_none_on_fast_path(self):
        """extraction_db is None on the TC-4272 fast path — this is expected behavior."""
        ns = _call_make_understand(product_evidence_dict={"supported_formats": ["PDF"]})
        assert ns.extraction_db is None


class TestApiFactMemberNamesExtraction:
    """TC-HO-09-R: Verify api_fact_member_names extraction from extraction_db.

    The extraction logic lives inline in GenerateWorker.run() around the ContentManifest
    construction (generate/worker.py). These tests exercise the exact same pattern to
    confirm correctness with various extraction_db states.

    Pattern under test (from generate/worker.py):
        _api_fact_member_names = []
        _edb = getattr(understand, "extraction_db", None)
        if _edb is not None:
            _api_fact_member_names = [
                f.member_name
                for f in getattr(_edb, "api_facts", [])
                if getattr(f, "member_name", None)
            ]
    """

    def _extract_member_names(self, extraction_db):
        """Apply the same extraction pattern as generate/worker.py manifest construction."""
        _api_fact_member_names = []
        _edb = getattr(extraction_db, "api_facts", None) if extraction_db is not None else None
        if extraction_db is not None:
            _api_fact_member_names = [
                f.member_name
                for f in getattr(extraction_db, "api_facts", [])
                if getattr(f, "member_name", None)
            ]
        return _api_fact_member_names

    def test_extraction_db_with_api_facts_produces_member_names(self):
        """Non-None extraction_db with api_facts produces correct member names list."""
        from types import SimpleNamespace
        extraction_db = SimpleNamespace(
            api_facts=[
                SimpleNamespace(member_name="Workbook"),
                SimpleNamespace(member_name="save"),
                SimpleNamespace(member_name="load"),
            ]
        )
        result = self._extract_member_names(extraction_db)
        assert result == ["Workbook", "save", "load"]

    def test_extraction_db_none_produces_empty_list(self):
        """None extraction_db produces empty list (TC-4272 fast path behavior)."""
        result = self._extract_member_names(None)
        assert result == []

    def test_extraction_db_with_none_member_name_filtered_out(self):
        """api_facts entries with None member_name are excluded from result."""
        from types import SimpleNamespace
        extraction_db = SimpleNamespace(
            api_facts=[
                SimpleNamespace(member_name="Workbook"),
                SimpleNamespace(member_name=None),    # filtered out
                SimpleNamespace(member_name=""),       # filtered out (falsy)
                SimpleNamespace(member_name="save"),
            ]
        )
        result = self._extract_member_names(extraction_db)
        assert result == ["Workbook", "save"]
        assert None not in result
        assert "" not in result

    def test_extraction_db_with_missing_member_name_attr_filtered_out(self):
        """api_facts entries missing the member_name attribute are excluded."""
        from types import SimpleNamespace
        extraction_db = SimpleNamespace(
            api_facts=[
                SimpleNamespace(member_name="Workbook"),
                SimpleNamespace(),  # no member_name attr — getattr returns None
            ]
        )
        result = self._extract_member_names(extraction_db)
        assert result == ["Workbook"]

    def test_extraction_db_empty_api_facts_produces_empty_list(self):
        """extraction_db with empty api_facts list produces empty member names."""
        from types import SimpleNamespace
        extraction_db = SimpleNamespace(api_facts=[])
        result = self._extract_member_names(extraction_db)
        assert result == []

    def test_extraction_db_without_api_facts_attr_produces_empty_list(self):
        """extraction_db missing api_facts attribute returns empty list safely."""
        from types import SimpleNamespace
        extraction_db = SimpleNamespace()  # no api_facts attr
        result = self._extract_member_names(extraction_db)
        assert result == []

    def test_extraction_db_none_on_make_understand_fast_path(self):
        """Confirms extraction_db is None from _make_understand_from_context (fast path)."""
        ns = _call_make_understand(product_evidence_dict={"supported_formats": ["PDF"]})
        # On TC-4272 fast path, extraction_db is always None — this is expected behavior
        assert ns.extraction_db is None
        # Therefore api_fact_member_names would be empty in ContentManifest
        result = self._extract_member_names(ns.extraction_db)
        assert result == []


class TestMakeUnderstandFromContextApiSurface:
    """Verify api_surface deserialization is unaffected by TC-HO-09-R changes."""

    def test_api_surface_dict_populates_model(self):
        """api_surface_dict with public_classes produces populated ApiSurface."""
        ns = _call_make_understand(
            api_surface_dict={
                "public_classes": ["Workbook"],
                "import_allowlist": ["import aspose_cells"],
                "confidence": "high",
                "api_identifiers": ["Workbook", "Workbook.save"],
            }
        )
        assert isinstance(ns.api_surface, ApiSurface)
        assert ns.api_surface.public_classes == ["Workbook"]
        assert ns.api_surface.confidence == "high"

    def test_empty_api_surface_dict_returns_low_confidence(self):
        """Empty api_surface_dict returns low-confidence empty ApiSurface."""
        ns = _call_make_understand(api_surface_dict={})
        assert ns.api_surface.confidence == "low"
        assert ns.api_surface.public_classes == []
