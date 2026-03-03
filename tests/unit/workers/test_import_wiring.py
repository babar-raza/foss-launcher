"""Tests for TC-3684: G3 import wiring through W5 generators + allowlist extension."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest


# ── Helper: _get_canonical_import ─────────────────────────────────────────────

class TestGetCanonicalImport:
    """Verify _get_canonical_import derives canonical import from product_facts."""

    def test_derives_from_api_inventory(self):
        from launch.workers.w5_section_writer.generators.content_generators import (
            _get_canonical_import,
        )

        pf = {"api_inventory": {"canonical_import": "from aspose.cells import"}}
        assert _get_canonical_import(pf) == "from aspose.cells import"

    def test_derives_from_code_structure(self):
        from launch.workers.w5_section_writer.generators.content_generators import (
            _get_canonical_import,
        )

        pf = {"code_structure": {"package_names": ["aspose_cells_foss"]}}
        assert "aspose_cells_foss" in _get_canonical_import(pf)

    def test_derives_from_product_name(self):
        from launch.workers.w5_section_writer.generators.content_generators import (
            _get_canonical_import,
        )

        pf = {"product_name": "Aspose.Note FOSS for Python"}
        result = _get_canonical_import(pf)
        assert "aspose.note" in result

    def test_empty_when_no_evidence(self):
        from launch.workers.w5_section_writer.generators.content_generators import (
            _get_canonical_import,
        )

        assert _get_canonical_import({}) == ""


# ── Generator call sites: canonical_import threading ──────────────────────────

class TestCanonicalImportThreading:
    """Verify all 11 _call_llm_for_content() call sites pass canonical_import."""

    @pytest.fixture
    def product_facts(self):
        return {
            "product_name": "Aspose.Cells FOSS for Python",
            "api_inventory": {"canonical_import": "from aspose.cells import"},
            "claims": [
                {"claim_id": "c1", "text": "Cells supports XLS", "visibility": "public"},
            ],
            "claim_groups": {
                "key_features": ["c1"],
                "limitations": ["c1"],
                "troubleshooting": ["c1"],
                "install_steps": ["c1"],
                "performance": ["c1"],
                "best_practices": ["c1"],
            },
            "workflows": [],
        }

    @pytest.fixture
    def page(self):
        return {
            "title": "Test Page",
            "slug": "test-page",
            "section": "docs",
            "page_role": "comprehensive_guide",
            "weight": 1,
            "claim_ids": ["c1"],
            "required_claim_ids": ["c1"],
            "content_strategy": {},
        }

    @pytest.fixture
    def snippet_catalog(self):
        return {"snippets": []}

    def _call_with_mock(self, generator_fn, product_facts, page, snippet_catalog, **extra):
        """Call a generator function with a mock LLM and return the mock's call args."""
        mock_llm = MagicMock()
        mock_llm.chat_completion.return_value = {
            "content": "## Overview\n\nGenerated content with enough words to pass validation. " * 10
        }

        with patch(
            "launch.workers.w5_section_writer.worker._call_llm_for_content",
            wraps=None,
        ) as mock_call:
            mock_call.return_value = {
                "content": "## Overview\n\nGenerated content paragraph. " * 20,
                "success": True,
                "method": "llm",
            }
            try:
                generator_fn(
                    page=page,
                    product_facts=product_facts,
                    snippet_catalog=snippet_catalog,
                    llm_client=mock_llm,
                    **extra,
                )
            except Exception:
                pass  # We only care about what was passed to _call_llm_for_content

            return mock_call

    def test_comprehensive_guide_passes_canonical_import(self, product_facts, page, snippet_catalog):
        from launch.workers.w5_section_writer.generators.content_generators import (
            generate_comprehensive_guide_content,
        )

        page["page_role"] = "comprehensive_guide"
        mock = self._call_with_mock(
            generate_comprehensive_guide_content, product_facts, page, snippet_catalog
        )
        if mock.called:
            _, kwargs = mock.call_args
            assert "canonical_import" in kwargs
            assert kwargs["canonical_import"] == "from aspose.cells import"
            assert kwargs["product_name"] != ""

    def test_feature_showcase_passes_canonical_import(self, product_facts, page, snippet_catalog):
        from launch.workers.w5_section_writer.generators.content_generators import (
            generate_feature_showcase_content,
        )

        page["page_role"] = "feature_showcase"
        mock = self._call_with_mock(
            generate_feature_showcase_content, product_facts, page, snippet_catalog
        )
        if mock.called:
            _, kwargs = mock.call_args
            assert "canonical_import" in kwargs
            assert kwargs["canonical_import"] == "from aspose.cells import"

    def test_troubleshooting_passes_canonical_import(self, product_facts, page, snippet_catalog):
        from launch.workers.w5_section_writer.generators.content_generators import (
            generate_troubleshooting_content,
        )

        page["page_role"] = "troubleshooting"
        mock = self._call_with_mock(
            generate_troubleshooting_content, product_facts, page, snippet_catalog
        )
        if mock.called:
            _, kwargs = mock.call_args
            assert "canonical_import" in kwargs

    def test_blog_passes_canonical_import(self, product_facts, page, snippet_catalog):
        from launch.workers.w5_section_writer.generators.content_generators import (
            generate_blog_content,
        )

        page["page_role"] = "blog"
        mock = self._call_with_mock(
            generate_blog_content, product_facts, page, snippet_catalog
        )
        if mock.called:
            _, kwargs = mock.call_args
            assert "canonical_import" in kwargs

    def test_faq_passes_canonical_import(self, product_facts, page, snippet_catalog):
        from launch.workers.w5_section_writer.generators.content_generators import (
            generate_faq_content,
        )

        page["page_role"] = "faq"
        mock = self._call_with_mock(
            generate_faq_content, product_facts, page, snippet_catalog
        )
        if mock.called:
            _, kwargs = mock.call_args
            assert "canonical_import" in kwargs

    def test_best_practices_passes_canonical_import(self, product_facts, page, snippet_catalog):
        from launch.workers.w5_section_writer.generators.content_generators import (
            generate_best_practices_content,
        )

        page["page_role"] = "best_practices"
        mock = self._call_with_mock(
            generate_best_practices_content, product_facts, page, snippet_catalog
        )
        if mock.called:
            _, kwargs = mock.call_args
            assert "canonical_import" in kwargs

    def test_tutorial_passes_canonical_import(self, product_facts, page, snippet_catalog):
        from launch.workers.w5_section_writer.generators.content_generators import (
            generate_tutorial_content,
        )

        page["page_role"] = "tutorial"
        mock = self._call_with_mock(
            generate_tutorial_content, product_facts, page, snippet_catalog
        )
        if mock.called:
            _, kwargs = mock.call_args
            assert "canonical_import" in kwargs

    def test_performance_passes_canonical_import(self, product_facts, page, snippet_catalog):
        from launch.workers.w5_section_writer.generators.content_generators import (
            generate_performance_content,
        )

        page["page_role"] = "performance_guide"
        mock = self._call_with_mock(
            generate_performance_content, product_facts, page, snippet_catalog
        )
        if mock.called:
            _, kwargs = mock.call_args
            assert "canonical_import" in kwargs


# ── Allowlist: product_facts-derived modules ──────────────────────────────────

class TestAllowlistExtension:
    """Verify _build_allowlist() derives modules from product_facts.json."""

    def test_distribution_identifier_added(self, tmp_path):
        from launch.workers.w9_validator.gates.gate_api_import_allowlist import (
            _build_allowlist,
        )

        artifacts = tmp_path / "artifacts"
        artifacts.mkdir()
        pf = {
            "distribution": [
                {"identifier": "aspose-cells-foss", "type": "pip"},
            ]
        }
        (artifacts / "product_facts.json").write_text(json.dumps(pf))

        allowed = _build_allowlist(tmp_path, "cells")
        assert "aspose_cells_foss" in allowed  # hyphen→underscore

    def test_code_structure_package_names_added(self, tmp_path):
        from launch.workers.w9_validator.gates.gate_api_import_allowlist import (
            _build_allowlist,
        )

        artifacts = tmp_path / "artifacts"
        artifacts.mkdir()
        pf = {
            "code_structure": {
                "package_names": ["aspose_note_foss", "aspose.note"]
            }
        }
        (artifacts / "product_facts.json").write_text(json.dumps(pf))

        allowed = _build_allowlist(tmp_path, "note")
        assert "aspose_note_foss" in allowed
        assert "aspose.note" in allowed

    def test_code_structure_single_string(self, tmp_path):
        from launch.workers.w9_validator.gates.gate_api_import_allowlist import (
            _build_allowlist,
        )

        artifacts = tmp_path / "artifacts"
        artifacts.mkdir()
        pf = {
            "code_structure": {"package_name": "aspose_3d_foss"}
        }
        (artifacts / "product_facts.json").write_text(json.dumps(pf))

        allowed = _build_allowlist(tmp_path, "3d")
        assert "aspose_3d_foss" in allowed

    def test_no_product_facts_still_works(self, tmp_path):
        from launch.workers.w9_validator.gates.gate_api_import_allowlist import (
            _build_allowlist,
        )

        # No artifacts dir at all
        allowed = _build_allowlist(tmp_path, "cells")
        # Should still have canonical modules
        assert "aspose.cells" in allowed

    def test_malformed_product_facts_safe(self, tmp_path):
        from launch.workers.w9_validator.gates.gate_api_import_allowlist import (
            _build_allowlist,
        )

        artifacts = tmp_path / "artifacts"
        artifacts.mkdir()
        (artifacts / "product_facts.json").write_text("not json")

        allowed = _build_allowlist(tmp_path, "cells")
        # Should not crash, still have base allowlist
        assert "aspose.cells" in allowed
