"""TC-2512 / TC-2513 / TC-2517: Unit tests for family capabilities extraction.

Tests that:
- family_capabilities.schema.json is valid JSON Schema (TC-2512)
- _extract_family_capabilities() deterministically extracts family-specific
  SEO keywords, formats, conversion pairs, clusters, and domain keywords
  from product_facts (TC-2513)
- _validate_conversion_pairs() rejects malformed and self-conversion pairs (TC-2517)
- Format extraction from claim text works correctly

Spec references:
- specs/schemas/family_capabilities.schema.json (Schema definition)
- TC-2512 taskcard (Family Capabilities Schema)
- TC-2513 taskcard (W2 Extraction)
- TC-2517 taskcard (Conversion-pair validation)
"""

from __future__ import annotations

import json
import pytest
from pathlib import Path
from typing import Any, Dict, List


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_product_facts(**overrides) -> Dict[str, Any]:
    """Build a minimal product_facts dict with optional overrides."""
    base: Dict[str, Any] = {
        "product_name": "TestProduct",
        "product_family": "",
        "product_slug": "test-product",
        "claims": [],
        "claim_groups": {},
        "supported_formats": [],
    }
    base.update(overrides)
    return base


def _claim(
    claim_id: str,
    text: str,
    kind: str = "feature",
) -> Dict[str, Any]:
    """Build a minimal claim dict."""
    return {
        "claim_id": claim_id,
        "claim_text": text,
        "claim_kind": kind,
    }


# ---------------------------------------------------------------------------
# TC-2512: Schema validity
# ---------------------------------------------------------------------------


class TestSchemaValid:
    """family_capabilities.schema.json must be valid JSON Schema."""

    def test_schema_valid(self):
        schema_path = (
            Path(__file__).parent.parent.parent.parent
            / "specs" / "schemas" / "family_capabilities.schema.json"
        )
        assert schema_path.exists(), f"Schema file not found: {schema_path}"
        with open(schema_path, "r", encoding="utf-8") as f:
            schema = json.load(f)

        # Structural checks
        assert schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema"
        assert schema.get("$id") == "family_capabilities.schema.json"
        assert schema.get("type") == "object"
        assert "required" in schema
        assert "properties" in schema

        # Required fields
        required = schema["required"]
        for field in [
            "schema_version", "family", "keyword",
            "supported_formats", "conversion_pairs",
            "feature_clusters", "domain_keywords",
        ]:
            assert field in required, f"Missing required field: {field}"

        # Optional fields exist in properties
        props = schema["properties"]
        assert "slug_template_overrides" in props
        assert "evidence_refs" in props

    def test_schema_parseable_by_jsonschema(self):
        """If jsonschema is available, validate the schema itself."""
        try:
            import jsonschema
        except ImportError:
            pytest.skip("jsonschema not installed")

        schema_path = (
            Path(__file__).parent.parent.parent.parent
            / "specs" / "schemas" / "family_capabilities.schema.json"
        )
        with open(schema_path, "r", encoding="utf-8") as f:
            schema = json.load(f)

        # Should not raise
        jsonschema.Draft202012Validator.check_schema(schema)


# ---------------------------------------------------------------------------
# TC-2513: Family capabilities extraction
# ---------------------------------------------------------------------------


class TestExtractCellsFamily:
    """Extraction from a cells-like product_facts."""

    def test_extract_cells_family(self):
        from launch.workers.w2_facts_builder.worker import _extract_family_capabilities

        facts = _make_product_facts(
            product_name="Aspose.Cells for Python",
            product_family="cells",
            product_slug="aspose-cells-python",
            claims=[
                _claim("c1", "Load XLSX spreadsheets using Python", "format"),
                _claim("c2", "Save workbook as CSV format", "format"),
                _claim("c3", "Convert XLSX to PDF documents", "feature"),
                _claim("c4", "Supports pivot tables and formulas", "feature"),
            ],
            claim_groups={
                "key_features": ["c4"],
                "conversion_pairs": [["XLSX", "PDF"], ["XLSX", "CSV"]],
                "install_steps": [],
            },
        )

        result = _extract_family_capabilities(facts, run_config={"family": "cells"})

        assert result["schema_version"] == "1.0"
        assert result["family"] == "cells"
        assert result["keyword"] == "spreadsheets"
        assert "XLSX" in result["supported_formats"]["load"]
        assert "CSV" in result["supported_formats"]["save"]
        assert len(result["conversion_pairs"]) == 2
        assert ["XLSX", "CSV"] in result["conversion_pairs"]
        assert ["XLSX", "PDF"] in result["conversion_pairs"]
        assert "key_features" in result["feature_clusters"]
        assert "workbook" in result["domain_keywords"]
        assert "spreadsheet" in result["domain_keywords"]


class TestExtract3dFamily:
    """Extraction from a 3d-like product_facts."""

    def test_extract_3d_family(self):
        from launch.workers.w2_facts_builder.worker import _extract_family_capabilities

        facts = _make_product_facts(
            product_name="Aspose.3D for Python",
            product_family="3d",
            product_slug="aspose-3d-python",
            claims=[
                _claim("c1", "Load OBJ 3D models from file", "format"),
                _claim("c2", "Export scene to FBX format", "format"),
                _claim("c3", "Import STL mesh data", "format"),
                _claim("c4", "Save as GLTF for web rendering", "format"),
            ],
            claim_groups={
                "key_features": ["c1", "c2"],
                "conversion_pairs": [["OBJ", "FBX"], ["STL", "GLTF"]],
            },
        )

        result = _extract_family_capabilities(facts, run_config={"family": "3d"})

        assert result["family"] == "3d"
        assert result["keyword"] == "3d-models"
        assert "OBJ" in result["supported_formats"]["load"]
        assert "FBX" in result["supported_formats"]["save"]
        assert "STL" in result["supported_formats"]["load"]
        assert len(result["conversion_pairs"]) == 2
        # Domain keywords for 3d
        assert "mesh" in result["domain_keywords"]
        assert "scene" in result["domain_keywords"]


class TestExtractNoteFamily:
    """Extraction from a note-like product_facts."""

    def test_extract_note_family(self):
        from launch.workers.w2_facts_builder.worker import _extract_family_capabilities

        facts = _make_product_facts(
            product_name="Aspose.Note for Python",
            product_family="note",
            product_slug="aspose-note-python",
            claims=[
                _claim("c1", "Load ONE notebook files", "format"),
                _claim("c2", "Save notebook as PDF", "format"),
                _claim("c3", "Read and parse OneNote pages", "feature"),
            ],
            claim_groups={
                "key_features": ["c3"],
                "limitations": ["c99"],
            },
        )

        result = _extract_family_capabilities(facts, run_config={"family": "note"})

        assert result["family"] == "note"
        assert result["keyword"] == "notebooks"
        assert "ONE" in result["supported_formats"]["load"]
        assert "PDF" in result["supported_formats"]["save"]
        assert "notebook" in result["domain_keywords"]
        assert "page" in result["domain_keywords"]


class TestUnknownFamilyFallback:
    """Unknown family produces valid output with generic keyword."""

    def test_unknown_family_fallback(self):
        from launch.workers.w2_facts_builder.worker import _extract_family_capabilities

        facts = _make_product_facts(
            product_name="SomeLib",
            product_family="unknown_product",
            product_slug="somelib",
            claims=[
                _claim("c1", "Processes data efficiently", "feature"),
            ],
            claim_groups={
                "key_features": ["c1"],
            },
        )

        result = _extract_family_capabilities(facts, run_config={"family": "unknown_product"})

        assert result["schema_version"] == "1.0"
        assert result["family"] == "unknown_product"
        assert result["keyword"] == "files"  # fallback keyword
        assert result["supported_formats"]["load"] == []
        assert result["supported_formats"]["save"] == []
        assert result["conversion_pairs"] == []
        assert result["domain_keywords"] == []  # no domain keywords for unknown
        # Still has feature_clusters from non-empty claim_groups
        assert "key_features" in result["feature_clusters"]

    def test_empty_family_infers_from_slug(self):
        from launch.workers.w2_facts_builder.worker import _extract_family_capabilities

        facts = _make_product_facts(
            product_name="Aspose.Cells for Python",
            product_family="",
            product_slug="aspose-cells-python",
        )

        result = _extract_family_capabilities(facts, run_config={})

        # Should infer "cells" from slug
        assert result["family"] == "cells"
        assert result["keyword"] == "spreadsheets"


# ---------------------------------------------------------------------------
# TC-2517: Conversion-pair validation
# ---------------------------------------------------------------------------


class TestConversionPairsWellFormed:
    """Validate conversion pair rules."""

    def test_no_self_conversions(self):
        from launch.workers.w2_facts_builder.worker import _validate_conversion_pairs

        pairs = [["XLSX", "XLSX"], ["PDF", "PDF"], ["CSV", "XLSX"]]
        result = _validate_conversion_pairs(pairs)

        # Self-conversions removed
        assert len(result) == 1
        assert result[0] == ["CSV", "XLSX"]

    def test_pairs_have_two_elements(self):
        from launch.workers.w2_facts_builder.worker import _validate_conversion_pairs

        pairs = [
            ["XLSX", "PDF"],        # valid
            ["CSV"],                 # invalid: 1 element
            ["A", "B", "C"],        # invalid: 3 elements
            [],                      # invalid: 0 elements
            ["DOC", "DOCX"],        # valid
        ]
        result = _validate_conversion_pairs(pairs)

        assert len(result) == 2
        assert ["DOC", "DOCX"] in result
        assert ["XLSX", "PDF"] in result

    def test_deterministic_sort(self):
        from launch.workers.w2_facts_builder.worker import _validate_conversion_pairs

        pairs = [["PDF", "DOC"], ["CSV", "XLSX"], ["DOC", "PDF"]]
        result = _validate_conversion_pairs(pairs)

        # Sorted by (source, target)
        assert result == [["CSV", "XLSX"], ["DOC", "PDF"], ["PDF", "DOC"]]

    def test_dedup_conversion_pairs(self):
        from launch.workers.w2_facts_builder.worker import _validate_conversion_pairs

        pairs = [["XLSX", "PDF"], ["XLSX", "PDF"], ["CSV", "PDF"]]
        result = _validate_conversion_pairs(pairs)

        assert len(result) == 2

    def test_case_normalized(self):
        from launch.workers.w2_facts_builder.worker import _validate_conversion_pairs

        pairs = [["xlsx", "pdf"], ["Xlsx", "Pdf"]]
        result = _validate_conversion_pairs(pairs)

        # Both normalize to same pair, so deduplicated
        assert len(result) == 1
        assert result[0] == ["XLSX", "PDF"]

    def test_empty_elements_rejected(self):
        from launch.workers.w2_facts_builder.worker import _validate_conversion_pairs

        pairs = [["", "PDF"], ["XLSX", ""], ["", ""]]
        result = _validate_conversion_pairs(pairs)

        assert result == []

    def test_non_list_items_rejected(self):
        from launch.workers.w2_facts_builder.worker import _validate_conversion_pairs

        pairs = ["not_a_pair", 42, None, ["A", "B"]]
        result = _validate_conversion_pairs(pairs)

        assert len(result) == 1
        assert result[0] == ["A", "B"]


# ---------------------------------------------------------------------------
# TC-2513: Deterministic output
# ---------------------------------------------------------------------------


class TestDeterministicOutput:
    """Same input must produce same output across multiple calls."""

    def test_deterministic_output(self):
        from launch.workers.w2_facts_builder.worker import _extract_family_capabilities

        facts = _make_product_facts(
            product_name="Aspose.Cells for Python",
            product_family="cells",
            product_slug="aspose-cells-python",
            claims=[
                _claim("c3", "Export data to CSV files", "format"),
                _claim("c1", "Load XLSX workbooks", "format"),
                _claim("c2", "Convert XLSX to PDF", "feature"),
            ],
            claim_groups={
                "key_features": ["c2", "c1"],
                "conversion_pairs": [["XLSX", "CSV"], ["XLSX", "PDF"]],
                "use_cases": ["c3"],
            },
        )
        config = {"family": "cells"}

        result1 = _extract_family_capabilities(facts, run_config=config)
        result2 = _extract_family_capabilities(facts, run_config=config)

        assert json.dumps(result1, sort_keys=True) == json.dumps(result2, sort_keys=True)

    def test_deterministic_unordered_claims(self):
        """Claim order should not affect output."""
        from launch.workers.w2_facts_builder.worker import _extract_family_capabilities

        claims_a = [
            _claim("c1", "Load OBJ models", "format"),
            _claim("c2", "Save FBX scenes", "format"),
        ]
        claims_b = [
            _claim("c2", "Save FBX scenes", "format"),
            _claim("c1", "Load OBJ models", "format"),
        ]
        config = {"family": "3d"}

        facts_a = _make_product_facts(
            product_family="3d", product_slug="aspose-3d-python", claims=claims_a
        )
        facts_b = _make_product_facts(
            product_family="3d", product_slug="aspose-3d-python", claims=claims_b
        )

        result_a = _extract_family_capabilities(facts_a, run_config=config)
        result_b = _extract_family_capabilities(facts_b, run_config=config)

        assert result_a["supported_formats"] == result_b["supported_formats"]
        assert result_a["conversion_pairs"] == result_b["conversion_pairs"]


# ---------------------------------------------------------------------------
# TC-2513: Format extraction from claims
# ---------------------------------------------------------------------------


class TestFormatExtractionFromClaims:
    """Formats are correctly extracted from claim text."""

    def test_format_extraction_load_direction(self):
        from launch.workers.w2_facts_builder.worker import _extract_formats_from_claims

        claims = [
            _claim("c1", "Read XLSX files from disk"),
            _claim("c2", "Load CSV data into memory"),
        ]
        result = _extract_formats_from_claims(claims)

        assert "XLSX" in result["load"]
        assert "CSV" in result["load"]
        assert result["save"] == []  # no save keywords

    def test_format_extraction_save_direction(self):
        from launch.workers.w2_facts_builder.worker import _extract_formats_from_claims

        claims = [
            _claim("c1", "Write output to PDF"),
            _claim("c2", "Export results as HTML"),
        ]
        result = _extract_formats_from_claims(claims)

        assert "PDF" in result["save"]
        assert "HTML" in result["save"]

    def test_format_extraction_both_directions(self):
        from launch.workers.w2_facts_builder.worker import _extract_formats_from_claims

        claims = [
            _claim("c1", "Load and save XLSX workbooks"),
        ]
        result = _extract_formats_from_claims(claims)

        assert "XLSX" in result["load"]
        assert "XLSX" in result["save"]

    def test_format_extraction_no_direction_defaults_to_both(self):
        from launch.workers.w2_facts_builder.worker import _extract_formats_from_claims

        claims = [
            _claim("c1", "Supports XLSX format natively"),
        ]
        result = _extract_formats_from_claims(claims)

        # No direction keywords -> added to both
        assert "XLSX" in result["load"]
        assert "XLSX" in result["save"]

    def test_format_extraction_evidence_refs(self):
        from launch.workers.w2_facts_builder.worker import _extract_formats_from_claims

        claims = [
            _claim("c1", "Read XLSX files"),
            _claim("c2", "No format mentioned here"),
            _claim("c3", "Save as PDF"),
        ]
        result = _extract_formats_from_claims(claims)

        assert sorted(result["format_claim_ids"]) == ["c1", "c3"]

    def test_format_extraction_empty_claims(self):
        from launch.workers.w2_facts_builder.worker import _extract_formats_from_claims

        result = _extract_formats_from_claims([])

        assert result["load"] == []
        assert result["save"] == []
        assert result["format_claim_ids"] == []

    def test_format_extraction_3d_formats(self):
        from launch.workers.w2_facts_builder.worker import _extract_formats_from_claims

        claims = [
            _claim("c1", "Import OBJ mesh files"),
            _claim("c2", "Export to FBX format"),
            _claim("c3", "Read and write STL binary data"),
            _claim("c4", "Save scenes in GLTF format"),
        ]
        result = _extract_formats_from_claims(claims)

        assert "OBJ" in result["load"]
        assert "FBX" in result["save"]
        assert "STL" in result["load"]
        assert "STL" in result["save"]
        assert "GLTF" in result["save"]


# ---------------------------------------------------------------------------
# TC-2513: Evidence refs
# ---------------------------------------------------------------------------


class TestEvidenceRefs:
    """Evidence refs track claim IDs used for extraction."""

    def test_evidence_refs_populated(self):
        from launch.workers.w2_facts_builder.worker import _extract_family_capabilities

        facts = _make_product_facts(
            product_family="cells",
            claims=[
                _claim("f1", "Load XLSX workbooks", "format"),
                _claim("f2", "Feature: pivot tables", "feature"),
            ],
            claim_groups={
                "key_features": ["f2"],
                "use_cases": ["f2"],
            },
        )

        result = _extract_family_capabilities(facts, run_config={"family": "cells"})

        assert "evidence_refs" in result
        assert "f1" in result["evidence_refs"]["format_claim_ids"]
        assert "f2" in result["evidence_refs"]["feature_claim_ids"]

    def test_evidence_refs_deduplicated(self):
        from launch.workers.w2_facts_builder.worker import _extract_family_capabilities

        facts = _make_product_facts(
            product_family="cells",
            claims=[],
            claim_groups={
                "key_features": ["c1", "c2"],
                "use_cases": ["c2", "c3"],  # c2 is in both groups
            },
        )

        result = _extract_family_capabilities(facts, run_config={"family": "cells"})

        # c2 should appear only once
        feature_ids = result["evidence_refs"]["feature_claim_ids"]
        assert len(feature_ids) == len(set(feature_ids))
        assert sorted(feature_ids) == ["c1", "c2", "c3"]


# ---------------------------------------------------------------------------
# TC-2513: Conversion-pair extraction from dict-format claim_groups
# ---------------------------------------------------------------------------


class TestConversionPairDictFormat:
    """conversion_pairs in claim_groups may be dicts with source/target keys."""

    def test_dict_format_pairs(self):
        from launch.workers.w2_facts_builder.worker import _extract_family_capabilities

        facts = _make_product_facts(
            product_family="cells",
            claims=[],
            claim_groups={
                "conversion_pairs": [
                    {"source": "xlsx", "target": "pdf"},
                    {"from": "csv", "to": "json"},
                ],
            },
        )

        result = _extract_family_capabilities(facts, run_config={"family": "cells"})

        assert ["CSV", "JSON"] in result["conversion_pairs"]
        assert ["XLSX", "PDF"] in result["conversion_pairs"]
