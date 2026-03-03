"""Unit tests for canonical import injection (TC-3674).

Tests the RichContext canonical_import field, derivation logic, and
system prompt injection in _call_llm_for_content.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from launch.workers.w5_section_writer.rich_context import (
    RichContext,
    _derive_canonical_import,
    _extract_api_index,
    build_rich_context,
)


# ── _derive_canonical_import tests ───────────────────────────────────────


class TestDeriveCanonicalImport:
    """TC-3674: _derive_canonical_import() resolves in correct order."""

    def test_explicit_canonical_import_wins(self):
        pf = {
            "api_inventory": {
                "canonical_import": "from aspose.cells import Workbook",
            },
            "code_structure": {"package_names": ["aspose.cells"]},
            "product_name": "Aspose.Cells FOSS for Python",
        }
        assert _derive_canonical_import(pf) == "from aspose.cells import Workbook"

    def test_package_names_fallback(self):
        pf = {
            "code_structure": {"package_names": ["aspose.note"]},
            "product_name": "Aspose.Note FOSS for Python",
        }
        assert _derive_canonical_import(pf) == "from aspose.note import"

    def test_package_name_string_fallback(self):
        pf = {
            "code_structure": {"package_name": "aspose.words"},
            "product_name": "Aspose.Words FOSS for Python",
        }
        assert _derive_canonical_import(pf) == "from aspose.words import"

    def test_product_name_derivation(self):
        pf = {
            "product_name": "Aspose.Cells FOSS for Python",
        }
        assert _derive_canonical_import(pf) == "from aspose.cells import"

    def test_product_name_note(self):
        pf = {
            "product_name": "Aspose.Note FOSS for Python",
        }
        assert _derive_canonical_import(pf) == "from aspose.note import"

    def test_empty_product_facts_returns_empty(self):
        assert _derive_canonical_import({}) == ""

    def test_no_dotted_product_name_returns_empty(self):
        pf = {"product_name": "SomeProduct for Python"}
        assert _derive_canonical_import(pf) == ""

    def test_uppercase_package_name_skipped(self):
        """Package names starting with uppercase (e.g. 'List') are Python type reprs."""
        pf = {
            "code_structure": {"package_names": ["List"]},
            "product_name": "Aspose.Cells FOSS for Python",
        }
        # Should fall through to product_name derivation
        assert _derive_canonical_import(pf) == "from aspose.cells import"

    def test_api_inventory_not_dict_handled(self):
        pf = {
            "api_inventory": "not a dict",
            "product_name": "Aspose.Cells FOSS for Python",
        }
        assert _derive_canonical_import(pf) == "from aspose.cells import"


# ── _extract_api_index tests ─────────────────────────────────────────────


class TestExtractApiIndex:
    """TC-3674: _extract_api_index() extracts public surface."""

    def test_returns_public_surface(self):
        pf = {
            "api_inventory": {
                "public_surface": {
                    "classes": ["Workbook", "Worksheet"],
                    "functions": ["load_workbook"],
                },
            },
        }
        idx = _extract_api_index(pf)
        assert "classes" in idx
        assert "Workbook" in idx["classes"]

    def test_missing_api_inventory_returns_empty(self):
        assert _extract_api_index({}) == {}

    def test_missing_public_surface_returns_empty(self):
        pf = {"api_inventory": {"version": "1.0"}}
        assert _extract_api_index(pf) == {}

    def test_non_dict_api_inventory_returns_empty(self):
        pf = {"api_inventory": "broken"}
        assert _extract_api_index(pf) == {}


# ── RichContext field tests ──────────────────────────────────────────────


class TestRichContextCanonicalFields:
    """TC-3674: RichContext has canonical_import and api_index fields."""

    def test_default_canonical_import_empty(self):
        ctx = RichContext()
        assert ctx.canonical_import == ""

    def test_default_api_index_empty(self):
        ctx = RichContext()
        assert ctx.api_index == {}

    def test_canonical_import_in_prompt_vars(self):
        ctx = RichContext(canonical_import="from aspose.cells import")
        pvars = ctx.to_prompt_vars()
        assert pvars["canonical_import"] == "from aspose.cells import"

    def test_build_rich_context_populates_canonical_import(self):
        page = {"page_role": "landing", "primary_focus": "test"}
        product_facts = {
            "product_name": "Aspose.Cells FOSS for Python",
            "code_structure": {"package_names": ["aspose.cells"]},
        }
        ctx = build_rich_context(page, product_facts, {})
        assert ctx.canonical_import == "from aspose.cells import"

    def test_build_rich_context_populates_api_index(self):
        page = {"page_role": "api_reference"}
        product_facts = {
            "product_name": "Aspose.Cells FOSS for Python",
            "api_inventory": {
                "public_surface": {"classes": ["Workbook"]},
            },
        }
        ctx = build_rich_context(page, product_facts, {})
        assert ctx.api_index == {"classes": ["Workbook"]}


# ── System prompt injection tests ────────────────────────────────────────


class TestSystemPromptInjection:
    """TC-3674: _call_llm_for_content injects canonical import into system prompt."""

    def test_canonical_import_in_system_prompt(self):
        """When canonical_import is provided, the system prompt includes it."""
        from launch.workers.w5_section_writer.worker import _call_llm_for_content

        mock_client = MagicMock()
        mock_client.chat_completion.return_value = {
            "content": "Generated content " * 30,  # >100 words
        }

        _call_llm_for_content(
            prompt="Generate content about spreadsheets.",
            claims=[],
            snippets=[],
            llm_client=mock_client,
            canonical_import="from aspose.cells import",
            product_name="Aspose.Cells FOSS for Python",
        )

        # Verify system message contains canonical import
        call_args = mock_client.chat_completion.call_args
        messages = call_args[1].get("messages") or call_args[0][0] if call_args[0] else call_args[1]["messages"]
        system_msg = messages[0]["content"]
        assert "from aspose.cells import" in system_msg
        assert "Aspose.Cells FOSS for Python" in system_msg

    def test_no_canonical_import_no_injection(self):
        """When canonical_import is empty, no import constraint in system prompt."""
        from launch.workers.w5_section_writer.worker import _call_llm_for_content

        mock_client = MagicMock()
        mock_client.chat_completion.return_value = {
            "content": "Generated content " * 30,
        }

        _call_llm_for_content(
            prompt="Generate content.",
            claims=[],
            snippets=[],
            llm_client=mock_client,
            # No canonical_import or product_name
        )

        call_args = mock_client.chat_completion.call_args
        messages = call_args[1].get("messages") or call_args[0][0] if call_args[0] else call_args[1]["messages"]
        system_msg = messages[0]["content"]
        assert "MANDATORY: Use ONLY this import" not in system_msg

    def test_no_llm_client_returns_deterministic(self):
        """Without LLM client, returns deterministic fallback."""
        from launch.workers.w5_section_writer.worker import _call_llm_for_content

        result = _call_llm_for_content(
            prompt="Test",
            claims=[],
            snippets=[],
            llm_client=None,
            canonical_import="from aspose.cells import",
        )
        assert result["method"] == "deterministic"
        assert result["success"] is False
