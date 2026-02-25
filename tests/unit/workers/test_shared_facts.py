"""TC-2478 / TC-2479: Unit tests for shared facts extraction and gate 20 source-of-truth check.

Tests that _extract_shared_facts() deterministically extracts canonical facts
from product_facts and that gate 20 G20-004 detects version contradictions
against the shared_facts source of truth.

Spec references:
- specs/schemas/shared_facts.schema.json (Schema definition)
- TC-2478 taskcard (Shared Fact Sheet Artifact)
- TC-2479 taskcard (W5 Fact Consumption + Gate 20 Strengthening)
"""

from __future__ import annotations

import json
import pytest
from pathlib import Path
from typing import Any, Dict

from launch.workers.w4_ia_planner.worker import _extract_shared_facts


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_product_facts(**overrides) -> Dict[str, Any]:
    """Build a minimal product_facts dict with optional overrides."""
    base: Dict[str, Any] = {
        "product_name": "Aspose.3D for Python",
        "product_slug": "aspose-3d-python",
        "claims": [],
        "claim_groups": {},
        "code_structure": {},
        "supported_formats": [],
        "supported_platforms": [],
    }
    base.update(overrides)
    return base


def _claim(claim_id: str, text: str) -> Dict[str, Any]:
    """Build a minimal claim dict."""
    return {"claim_id": claim_id, "claim_text": text}


# ---------------------------------------------------------------------------
# TC-2478: _extract_shared_facts tests
# ---------------------------------------------------------------------------


class TestExtractSharedFactsBasic:
    """Basic extraction from product_facts with a Python 3.8 claim."""

    def test_extract_shared_facts_basic(self):
        facts = _make_product_facts(
            claims=[
                _claim("c1", "Supports Python 3.8 and above"),
            ],
            code_structure={"package_name": "aspose.threed"},
        )
        result = _extract_shared_facts(facts)

        assert result["schema_version"] == "1.0"
        assert result["runtime_versions"]["python"]["minimum"] == "3.8"
        assert result["runtime_versions"]["python"]["all_mentioned"] == ["3.8"]
        assert result["package_name"] == "aspose.threed"
        assert result["product_display_name"] == "Aspose.3D for Python"
        assert result["product_slug"] == "aspose-3d-python"

    def test_extract_shared_facts_no_version(self):
        """No Python claims -> empty minimum."""
        facts = _make_product_facts(
            claims=[
                _claim("c1", "Provides 3D model loading capabilities"),
            ],
        )
        result = _extract_shared_facts(facts)

        assert result["runtime_versions"]["python"]["minimum"] == ""
        assert result["runtime_versions"]["python"]["all_mentioned"] == []

    def test_extract_shared_facts_multiple_versions(self):
        """Claims mention 3.8 and 3.10 -> minimum = '3.8'."""
        facts = _make_product_facts(
            claims=[
                _claim("c1", "Requires Python 3.8 for basic usage"),
                _claim("c2", "Works with Python 3.10 for async features"),
            ],
        )
        result = _extract_shared_facts(facts)

        assert result["runtime_versions"]["python"]["minimum"] == "3.8"
        assert result["runtime_versions"]["python"]["all_mentioned"] == ["3.8", "3.10"]

    def test_extract_shared_facts_pip_command(self):
        """Install claim with pip install aspose-3d -> extracted."""
        facts = _make_product_facts(
            claims=[
                _claim("inst1", "Install via pip install aspose-3d"),
            ],
            claim_groups={"install_steps": ["inst1"]},
        )
        result = _extract_shared_facts(facts)

        assert result["installation_method"] == "pip install aspose-3d"


class TestExtractSharedFactsFormats:
    """Format extraction from supported_formats."""

    def test_extracts_sorted_unique_formats(self):
        facts = _make_product_facts(
            supported_formats=[
                {"format": "fbx"},
                {"format": "obj"},
                {"format": "fbx"},  # duplicate
                {"format": "stl"},
            ],
        )
        result = _extract_shared_facts(facts)
        assert result["supported_formats"] == ["FBX", "OBJ", "STL"]

    def test_extracts_formats_from_plain_strings(self):
        """Handles supported_formats as a list of plain strings."""
        facts = _make_product_facts(
            supported_formats=["OBJ", "STL", "FBX"],
        )
        result = _extract_shared_facts(facts)
        assert result["supported_formats"] == ["FBX", "OBJ", "STL"]

    def test_empty_formats_when_none(self):
        facts = _make_product_facts()
        result = _extract_shared_facts(facts)
        assert result["supported_formats"] == []


class TestExtractSharedFactsPackageName:
    """Package name extraction fallback to import statements in claims."""

    def test_fallback_to_import_in_claims(self):
        facts = _make_product_facts(
            claims=[
                _claim("c1", "Use import aspose.threed to access the library"),
            ],
            code_structure={},  # no package_name
        )
        result = _extract_shared_facts(facts)
        assert result["package_name"] == "aspose.threed"

    def test_code_structure_package_name_takes_precedence(self):
        facts = _make_product_facts(
            claims=[
                _claim("c1", "Use import aspose.threed to access the library"),
            ],
            code_structure={"package_name": "aspose_3d"},
        )
        result = _extract_shared_facts(facts)
        assert result["package_name"] == "aspose_3d"


class TestExtractSharedFactsVersionPatterns:
    """Edge cases for version pattern matching."""

    def test_version_with_gte_prefix(self):
        facts = _make_product_facts(
            claims=[_claim("c1", "Requires Python>=3.9")],
        )
        result = _extract_shared_facts(facts)
        assert result["runtime_versions"]["python"]["minimum"] == "3.9"

    def test_version_with_gt_prefix(self):
        facts = _make_product_facts(
            claims=[_claim("c1", "Requires Python>3.7")],
        )
        result = _extract_shared_facts(facts)
        assert result["runtime_versions"]["python"]["minimum"] == "3.7"

    def test_version_sorting_with_many(self):
        facts = _make_product_facts(
            claims=[
                _claim("c1", "Python 3.12 support added"),
                _claim("c2", "Minimum Python 3.7"),
                _claim("c3", "Tested on Python 3.9"),
            ],
        )
        result = _extract_shared_facts(facts)
        assert result["runtime_versions"]["python"]["minimum"] == "3.7"
        assert result["runtime_versions"]["python"]["all_mentioned"] == [
            "3.7", "3.9", "3.12"
        ]


# ---------------------------------------------------------------------------
# TC-2479: Gate 20 G20-004 source-of-truth check
# ---------------------------------------------------------------------------


class TestGate20SourceOfTruth:
    """Test _check_against_source_of_truth from gate 20."""

    def test_no_issues_when_versions_match(self, tmp_path):
        from launch.workers.w9_validator.gates.gate_20_cross_page_consistency import (
            _check_against_source_of_truth,
        )
        shared_facts = {
            "runtime_versions": {"python": {"minimum": "3.8"}},
        }
        page = tmp_path / "page.md"
        page.write_text("Requires Python 3.8 or later.", encoding="utf-8")
        pages = [(page, page.read_text(encoding="utf-8"))]
        issues = _check_against_source_of_truth(pages, shared_facts)
        assert len(issues) == 0

    def test_flags_contradicting_version(self, tmp_path):
        from launch.workers.w9_validator.gates.gate_20_cross_page_consistency import (
            _check_against_source_of_truth,
        )
        shared_facts = {
            "runtime_versions": {"python": {"minimum": "3.8"}},
        }
        page = tmp_path / "page.md"
        page.write_text("Requires Python 3.11 or later.", encoding="utf-8")
        pages = [(page, page.read_text(encoding="utf-8"))]
        issues = _check_against_source_of_truth(pages, shared_facts)
        assert len(issues) == 1
        assert issues[0]["error_code"] == "G20-004"
        assert "3.11" in issues[0]["message"]
        assert "3.8" in issues[0]["message"]

    def test_allows_adjacent_minor_version(self, tmp_path):
        """Versions within 1 minor are tolerated (3.8 vs 3.9)."""
        from launch.workers.w9_validator.gates.gate_20_cross_page_consistency import (
            _check_against_source_of_truth,
        )
        shared_facts = {
            "runtime_versions": {"python": {"minimum": "3.8"}},
        }
        page = tmp_path / "page.md"
        page.write_text("Also tested with Python 3.9.", encoding="utf-8")
        pages = [(page, page.read_text(encoding="utf-8"))]
        issues = _check_against_source_of_truth(pages, shared_facts)
        assert len(issues) == 0

    def test_empty_canonical_min_skips_check(self, tmp_path):
        from launch.workers.w9_validator.gates.gate_20_cross_page_consistency import (
            _check_against_source_of_truth,
        )
        shared_facts = {
            "runtime_versions": {"python": {"minimum": ""}},
        }
        page = tmp_path / "page.md"
        page.write_text("Requires Python 3.11.", encoding="utf-8")
        pages = [(page, page.read_text(encoding="utf-8"))]
        issues = _check_against_source_of_truth(pages, shared_facts)
        assert len(issues) == 0

    def test_major_version_difference_flagged(self, tmp_path):
        from launch.workers.w9_validator.gates.gate_20_cross_page_consistency import (
            _check_against_source_of_truth,
        )
        shared_facts = {
            "runtime_versions": {"python": {"minimum": "3.8"}},
        }
        page = tmp_path / "page.md"
        page.write_text("Requires Python 2.7.", encoding="utf-8")
        pages = [(page, page.read_text(encoding="utf-8"))]
        issues = _check_against_source_of_truth(pages, shared_facts)
        assert len(issues) == 1
        assert issues[0]["error_code"] == "G20-004"


class TestGate20WithSharedFacts:
    """Integration: run_gate_20 with shared_facts.json on disk."""

    def test_run_gate_20_loads_shared_facts(self, tmp_path):
        from launch.workers.w9_validator.gates.gate_20_cross_page_consistency import (
            run_gate_20,
        )
        # Set up run_dir with shared_facts
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir()
        shared_facts = {
            "runtime_versions": {"python": {"minimum": "3.8"}},
        }
        (artifacts_dir / "shared_facts.json").write_text(
            json.dumps(shared_facts), encoding="utf-8"
        )

        # Create two md files — one with matching, one with contradicting version
        site_dir = tmp_path / "site"
        site_dir.mkdir()
        (site_dir / "page_ok.md").write_text(
            "---\ntitle: OK\n---\nRequires Python 3.8.", encoding="utf-8"
        )
        (site_dir / "page_bad.md").write_text(
            "---\ntitle: Bad\n---\nRequires Python 2.7.", encoding="utf-8"
        )

        md_files = list(site_dir.glob("*.md"))
        passed, issues = run_gate_20(md_files, run_dir=tmp_path)

        # Should fail due to G20-004 (Python 2.7 vs 3.8 canonical)
        g20_004_issues = [i for i in issues if i.get("error_code") == "G20-004"]
        assert len(g20_004_issues) >= 1
        assert not passed  # at least one error

    def test_run_gate_20_no_run_dir_graceful(self, tmp_path):
        """Gate 20 without run_dir still works (no G20-004 check)."""
        from launch.workers.w9_validator.gates.gate_20_cross_page_consistency import (
            run_gate_20,
        )
        site_dir = tmp_path / "site"
        site_dir.mkdir()
        (site_dir / "page1.md").write_text(
            "---\ntitle: A\n---\nUses Python 3.8.", encoding="utf-8"
        )
        (site_dir / "page2.md").write_text(
            "---\ntitle: B\n---\nUses Python 3.8.", encoding="utf-8"
        )
        md_files = list(site_dir.glob("*.md"))
        passed, issues = run_gate_20(md_files)
        # No G20-004 issues since no run_dir
        g20_004 = [i for i in issues if i.get("error_code") == "G20-004"]
        assert len(g20_004) == 0
