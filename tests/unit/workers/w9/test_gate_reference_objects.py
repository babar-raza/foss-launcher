"""Tests for gate_reference_objects (Spec v1.1 J4).

Validates that when API classes exist in product_facts, the reference section
of page_plan.json includes at least one reference_object_page beyond api-overview.
"""

from __future__ import annotations

import json
import pytest
from pathlib import Path

from src.launch.workers.w9_validator.gates.gate_reference_objects import execute_gate


@pytest.fixture
def tmp_run(tmp_path):
    (tmp_path / "artifacts").mkdir()
    return tmp_path


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


def _write_page_plan(run_dir: Path, pages: list) -> None:
    _write_json(run_dir / "artifacts" / "page_plan.json", {"pages": pages})


def _write_product_facts(run_dir: Path, classes: list = None, functions: list = None) -> None:
    data = {
        "product_name": "TestProduct",
        "claims": [],
        "api_surface_summary": {
            "classes": classes or [],
            "functions": functions or [],
        },
    }
    _write_json(run_dir / "artifacts" / "product_facts.json", data)


class TestGateReferenceObjectsGracefulSkips:
    def test_no_page_plan_skips(self, tmp_run):
        _write_product_facts(tmp_run, classes=["Document"])
        ok, issues = execute_gate(tmp_run, "local")
        assert ok is True
        assert issues == []

    def test_no_product_facts_skips(self, tmp_run):
        _write_page_plan(tmp_run, [])
        ok, issues = execute_gate(tmp_run, "local")
        assert ok is True
        assert issues == []

    def test_no_api_classes_skips(self, tmp_run):
        """Gate skips gracefully when no API classes in product_facts."""
        _write_product_facts(tmp_run, classes=[])
        _write_page_plan(tmp_run, [
            {"section": "reference", "page_role": "api_reference", "slug": "api-overview"},
        ])
        ok, issues = execute_gate(tmp_run, "local")
        assert ok is True
        assert issues == []

    def test_invalid_product_facts_fails(self, tmp_run):
        (tmp_run / "artifacts" / "product_facts.json").write_text("NOT JSON", encoding="utf-8")
        _write_page_plan(tmp_run, [])
        ok, issues = execute_gate(tmp_run, "local")
        assert ok is False

    def test_invalid_page_plan_fails(self, tmp_run):
        _write_product_facts(tmp_run, classes=["Document"])
        (tmp_run / "artifacts" / "page_plan.json").write_text("BAD JSON", encoding="utf-8")
        ok, issues = execute_gate(tmp_run, "local")
        assert ok is False


class TestGateReferenceObjectsPass:
    def test_reference_object_page_present_passes(self, tmp_run):
        _write_product_facts(tmp_run, classes=["Document", "License"])
        _write_page_plan(tmp_run, [
            {"section": "reference", "page_role": "api_reference", "slug": "api-overview"},
            {"section": "reference", "page_role": "reference_object_page", "slug": "document"},
        ])
        ok, issues = execute_gate(tmp_run, "local")
        assert ok is True
        assert issues == []

    def test_class_reference_alias_counts(self, tmp_run):
        """``class_reference`` role alias is accepted."""
        _write_product_facts(tmp_run, classes=["Workbook"])
        _write_page_plan(tmp_run, [
            {"section": "reference", "page_role": "api_reference", "slug": "api-overview"},
            {"section": "reference", "page_role": "class_reference", "slug": "workbook"},
        ])
        ok, issues = execute_gate(tmp_run, "local")
        assert ok is True

    def test_multiple_object_pages_pass(self, tmp_run):
        _write_product_facts(tmp_run, classes=["Notebook", "Page", "Section"])
        _write_page_plan(tmp_run, [
            {"section": "reference", "page_role": "api_reference", "slug": "api-overview"},
            {"section": "reference", "page_role": "reference_object_page", "slug": "notebook"},
            {"section": "reference", "page_role": "reference_object_page", "slug": "page"},
        ])
        ok, issues = execute_gate(tmp_run, "local")
        assert ok is True


class TestGateReferenceObjectsWarn:
    def test_no_object_pages_with_api_classes_warns(self, tmp_run):
        """When API classes exist but no object pages, gate warns (not hard fail)."""
        _write_product_facts(tmp_run, classes=["Scene", "Mesh", "Light"])
        _write_page_plan(tmp_run, [
            {"section": "reference", "page_role": "api_reference", "slug": "api-overview"},
        ])
        ok, issues = execute_gate(tmp_run, "local")
        # warn-only: gate returns True but has issues
        assert ok is True
        assert len(issues) == 1
        assert issues[0]["severity"] == "warn"
        assert "reference_object_page" in issues[0]["message"]
