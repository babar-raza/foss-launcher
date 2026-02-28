"""TC-3230: Tests for truth_pack.py — token-safe truth pack builder.

Covers:
- build_truth_pack_min basic build (1 test)
- Caps enforcement: conversion_pairs, capabilities, limitations, api_classes (4 tests)
- Missing optional artifacts (1 test)
- Deterministic output (1 test)
- Schema validation (1 test)
- Token budget estimate (1 test)
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import pytest

from launch.workers.w2_facts_builder.truth_pack import (
    _MAX_API_CLASSES,
    _MAX_CAPABILITIES,
    _MAX_CONVERSION_PAIRS,
    _MAX_FORMATS,
    _MAX_LIMITATIONS,
    build_truth_pack_min,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_repo_truth(**overrides: Any) -> Dict[str, Any]:
    base: Dict[str, Any] = {
        "package_name": {"value": "aspose-cells"},
        "python_requires": {"min": "3.6", "spec": ">=3.6"},
        "license": {"spdx_id": "Proprietary", "name": "Aspose EULA"},
        "supported_formats": {"values": ["XLSX", "CSV", "PDF", "HTML"]},
        "input_formats": {"values": ["XLSX", "CSV"]},
        "output_formats": {"values": ["PDF", "HTML"]},
        "conversion_pairs": {"values": [
            {"source": "XLSX", "target": "PDF"},
            {"source": "CSV", "target": "XLSX"},
        ]},
        "capabilities": {"values": [
            {"text": "Read and write Excel files", "source": "readme", "evidence": {"file": "README.md", "line": 5}},
            {"text": "Convert spreadsheets to PDF", "source": "docstring", "evidence": {"file": "src/converter.py", "line": 42}},
        ]},
        "limitations": {"values": [
            {"text": "No macro support", "source_file": "README.md"},
        ]},
    }
    base.update(overrides)
    return base


def _make_api_index() -> Dict[str, Any]:
    return {
        "package_name": "aspose.cells",
        "modules": ["aspose.cells", "aspose.cells.charts"],
        "class_index": [
            {"name": "Workbook", "import_path": "aspose.cells.Workbook", "method_count": 15, "property_count": 5},
            {"name": "Worksheet", "import_path": "aspose.cells.Worksheet", "method_count": 22, "property_count": 8},
            {"name": "Cell", "import_path": "aspose.cells.Cell", "method_count": 10, "property_count": 3},
        ],
        "function_index": [
            {"name": "create_workbook", "signature": "create_workbook(path: str) -> Workbook", "return_type": "Workbook"},
        ],
        "symbol_count": 50,
    }


def _make_product_facts() -> Dict[str, Any]:
    return {
        "product_name": "Aspose.Cells for Python",
        "claims": [
            {"claim_id": "inst1", "claim_text": "Install via pip install aspose-cells", "claim_kind": "install"},
        ],
        "claim_groups": {
            "install_steps": ["inst1"],
        },
        "code_structure": {
            "package_names": ["aspose-cells"],
        },
        "supported_formats": [
            {"format": "XLSX", "status": "implemented"},
            {"format": "CSV", "status": "implemented"},
        ],
    }


# ---------------------------------------------------------------------------
# TestBuildTruthPackMin
# ---------------------------------------------------------------------------


class TestBuildTruthPackMin:
    """Test truth_pack_min builder."""

    def test_basic_build(self):
        repo_truth = _make_repo_truth()
        result = build_truth_pack_min(repo_truth)

        assert result["schema_version"] == "1.0"
        assert result["canonical_facts"]["package_name"] == "aspose-cells"
        assert result["canonical_facts"]["python_requires_min"] == "3.6"
        assert result["canonical_facts"]["license_spdx"] == "Proprietary"
        assert len(result["formats"]["supported"]) == 4
        assert len(result["conversion_pairs"]) == 2
        assert len(result["capabilities"]) == 2
        assert len(result["limitations"]) == 1

    def test_conversion_pairs_capped_at_10(self):
        pairs = [{"source": f"FMT{i}", "target": f"OUT{i}"} for i in range(20)]
        repo_truth = _make_repo_truth(conversion_pairs={"values": pairs})
        result = build_truth_pack_min(repo_truth)
        assert len(result["conversion_pairs"]) <= _MAX_CONVERSION_PAIRS

    def test_capabilities_capped_at_10(self):
        caps = [{"text": f"Capability {i}", "source": "readme", "evidence": {}} for i in range(20)]
        repo_truth = _make_repo_truth(capabilities={"values": caps})
        result = build_truth_pack_min(repo_truth)
        assert len(result["capabilities"]) <= _MAX_CAPABILITIES

    def test_limitations_capped_at_5(self):
        lims = [{"text": f"Limitation {i}", "source_file": "README.md"} for i in range(10)]
        repo_truth = _make_repo_truth(limitations={"values": lims})
        result = build_truth_pack_min(repo_truth)
        assert len(result["limitations"]) <= _MAX_LIMITATIONS

    def test_api_classes_capped_at_5(self):
        api_index = _make_api_index()
        api_index["class_index"] = [
            {"name": f"Class{i}", "import_path": f"mod.Class{i}", "method_count": i}
            for i in range(10)
        ]
        result = build_truth_pack_min(_make_repo_truth(), api_index=api_index)
        assert len(result["api_summary"]["top_classes"]) <= _MAX_API_CLASSES

    def test_missing_optional_artifacts(self):
        """Build with only repo_truth (no product_facts / api_index)."""
        repo_truth = _make_repo_truth()
        result = build_truth_pack_min(repo_truth)
        assert result["api_summary"] == {}
        assert result["canonical_facts"]["package_name"] == "aspose-cells"

    def test_deterministic_output(self):
        repo_truth = _make_repo_truth()
        api_index = _make_api_index()
        pf = _make_product_facts()

        r1 = build_truth_pack_min(repo_truth, product_facts=pf, api_index=api_index)
        r2 = build_truth_pack_min(repo_truth, product_facts=pf, api_index=api_index)

        assert json.dumps(r1, sort_keys=True) == json.dumps(r2, sort_keys=True)

    def test_schema_validation(self):
        """Output validates against truth_pack_min.schema.json."""
        repo_truth = _make_repo_truth()
        api_index = _make_api_index()
        result = build_truth_pack_min(repo_truth, api_index=api_index)

        schema_path = (
            Path(__file__).resolve().parents[3]
            / "specs" / "schemas" / "truth_pack_min.schema.json"
        )
        if schema_path.exists():
            try:
                import jsonschema
                schema = json.loads(schema_path.read_text(encoding="utf-8"))
                jsonschema.validate(result, schema)
            except ImportError:
                pass  # jsonschema not installed

    def test_token_budget_estimate(self):
        """Serialized output stays under ~2000 tokens (rough word count)."""
        repo_truth = _make_repo_truth()
        api_index = _make_api_index()
        pf = _make_product_facts()

        result = build_truth_pack_min(repo_truth, product_facts=pf, api_index=api_index)
        serialized = json.dumps(result, indent=2)
        # Rough token estimate: ~0.75 tokens per word (JSON has punctuation overhead)
        word_count = len(serialized.split())
        estimated_tokens = int(word_count * 0.75)
        # Should be well under 2000 tokens for typical repo
        assert estimated_tokens < 2000, f"Estimated {estimated_tokens} tokens exceeds budget"

    def test_fallback_package_name_from_product_facts(self):
        """Package name falls back to product_facts.code_structure when repo_truth lacks it."""
        repo_truth = {"package_name": {}, "python_requires": {}, "license": {}}
        pf = _make_product_facts()
        result = build_truth_pack_min(repo_truth, product_facts=pf)
        assert result["canonical_facts"]["package_name"] == "aspose-cells"

    def test_fallback_install_method_from_claims(self):
        """Installation method extracted from install_steps claims."""
        repo_truth = _make_repo_truth()
        pf = _make_product_facts()
        result = build_truth_pack_min(repo_truth, product_facts=pf)
        assert "pip install" in result["canonical_facts"]["installation_method"]

    def test_fallback_formats_from_product_facts(self):
        """Formats fall back to product_facts when repo_truth has none."""
        repo_truth = {"package_name": {"value": "pkg"}, "python_requires": {}, "license": {}}
        pf = _make_product_facts()
        result = build_truth_pack_min(repo_truth, product_facts=pf)
        assert len(result["formats"]["supported"]) >= 2
