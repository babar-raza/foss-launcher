"""Tests for gate_kb_howto_evidence (Spec v1.1 J6).

Validates that conversion how-to drafts only reference evidenced formats.
"""

from __future__ import annotations

import json
import pytest
from pathlib import Path

from src.launch.workers.w9_validator.gates.gate_kb_howto_evidence import (
    execute_gate,
)


@pytest.fixture
def tmp_run(tmp_path):
    (tmp_path / "artifacts").mkdir()
    (tmp_path / "drafts" / "kb").mkdir(parents=True)
    return tmp_path


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


def _write_page_plan(run_dir: Path, pages: list) -> None:
    _write_json(run_dir / "artifacts" / "page_plan.json", {"pages": pages})


def _write_product_facts(run_dir: Path, supported_formats: list) -> None:
    _write_json(run_dir / "artifacts" / "product_facts.json", {
        "product_name": "TestProduct",
        "claims": [],
        "supported_formats": supported_formats,
    })


def _conversion_page(slug: str = "how-to-convert-formats") -> dict:
    return {
        "section": "kb",
        "slug": slug,
        "page_role": "howto_article",
        "content_strategy": {"is_conversion_howto": True},
    }


# ── Skips ────────────────────────────────────────────────────────────────────

class TestGateKbHowtoEvidenceSkips:
    def test_no_artifacts_skips(self, tmp_path):
        ok, issues = execute_gate(tmp_path, "local")
        assert ok is True
        assert issues == []

    def test_no_drafts_dir_skips(self, tmp_run):
        import shutil
        shutil.rmtree(tmp_run / "drafts")
        _write_page_plan(tmp_run, [_conversion_page()])
        _write_product_facts(tmp_run, [])
        ok, issues = execute_gate(tmp_run, "local")
        assert ok is True
        assert issues == []


# ── Pass ─────────────────────────────────────────────────────────────────────

class TestGateKbHowtoEvidencePass:
    def test_only_evidenced_formats_mentioned(self, tmp_run):
        _write_product_facts(tmp_run, [
            {"format": "FBX", "status": "implemented", "claim_id": "c1"},
            {"format": "OBJ", "status": "implemented", "claim_id": "c2"},
        ])
        _write_page_plan(tmp_run, [_conversion_page()])
        draft = tmp_run / "drafts" / "kb" / "how-to-convert-formats.md"
        draft.write_text(
            "Convert FBX to OBJ format using TestProduct.",
            encoding="utf-8",
        )
        ok, issues = execute_gate(tmp_run, "local")
        assert ok is True
        assert issues == []

    def test_non_conversion_pages_ignored(self, tmp_run):
        _write_product_facts(tmp_run, [])
        _write_page_plan(tmp_run, [
            {
                "section": "kb",
                "slug": "how-to-open-a-file",
                "page_role": "howto_article",
                "content_strategy": {},
            },
        ])
        draft = tmp_run / "drafts" / "kb" / "how-to-open-a-file.md"
        draft.write_text("Open XYZ files.", encoding="utf-8")
        ok, issues = execute_gate(tmp_run, "local")
        assert ok is True
        assert issues == []

    def test_no_supported_formats_no_warning(self, tmp_run):
        """When product_facts has no formats, nothing to compare against."""
        _write_product_facts(tmp_run, [])
        _write_page_plan(tmp_run, [_conversion_page()])
        draft = tmp_run / "drafts" / "kb" / "how-to-convert-formats.md"
        draft.write_text("Convert documents.", encoding="utf-8")
        ok, issues = execute_gate(tmp_run, "local")
        assert ok is True
        assert issues == []

    def test_case_insensitive_matching(self, tmp_run):
        """Draft says 'fbx', product_facts has 'FBX' -> no issue."""
        _write_product_facts(tmp_run, [
            {"format": "FBX", "status": "implemented", "claim_id": "c1"},
        ])
        _write_page_plan(tmp_run, [_conversion_page()])
        draft = tmp_run / "drafts" / "kb" / "how-to-convert-formats.md"
        draft.write_text(
            "Import an .fbx file and convert it.",
            encoding="utf-8",
        )
        ok, issues = execute_gate(tmp_run, "local")
        assert ok is True
        assert issues == []


# ── Warn ─────────────────────────────────────────────────────────────────────

class TestGateKbHowtoEvidenceWarn:
    def test_hallucinated_format_warns(self, tmp_run):
        _write_product_facts(tmp_run, [
            {"format": "FBX", "status": "implemented", "claim_id": "c1"},
        ])
        _write_page_plan(tmp_run, [_conversion_page()])
        draft = tmp_run / "drafts" / "kb" / "how-to-convert-formats.md"
        draft.write_text(
            "Convert FBX to STL format. Also supports GLTF file conversion.",
            encoding="utf-8",
        )
        ok, issues = execute_gate(tmp_run, "local")
        # warn-only gate: always passes
        assert ok is True
        assert len(issues) >= 1
        assert any("STL" in i["message"] for i in issues)

    def test_multiple_hallucinated_formats(self, tmp_run):
        _write_product_facts(tmp_run, [
            {"format": "OBJ", "status": "implemented", "claim_id": "c1"},
        ])
        _write_page_plan(tmp_run, [_conversion_page()])
        draft = tmp_run / "drafts" / "kb" / "how-to-convert-formats.md"
        draft.write_text(
            "Convert ABC format to XYZ file using OBJ intermediary.",
            encoding="utf-8",
        )
        ok, issues = execute_gate(tmp_run, "local")
        assert ok is True
        warn_msgs = " ".join(i["message"] for i in issues)
        assert "ABC" in warn_msgs or "XYZ" in warn_msgs
