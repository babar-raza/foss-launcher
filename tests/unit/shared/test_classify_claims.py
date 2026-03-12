"""Tests for claim classification (capability #1)."""
from __future__ import annotations

import pytest

from launcher.shared.classify_claims import classify_claim, filter_claims
from launcher.models.claims import Claim


class TestClassifyClaim:
    def test_user_facing_feature(self) -> None:
        assert classify_claim("Supports converting PDF to XLSX format") == "user_facing"

    def test_user_facing_install(self) -> None:
        assert classify_claim("Install the library using pip install aspose-cells") == "user_facing"

    def test_developer_instruction_todo(self) -> None:
        assert classify_claim("TODO: refactor this module to use async") == "developer_instruction"

    def test_developer_instruction_your_job(self) -> None:
        assert classify_claim("Your job is to generate the documentation") == "developer_instruction"

    def test_developer_instruction_fixme(self) -> None:
        assert classify_claim("FIXME: handle edge case for empty input") == "developer_instruction"

    def test_internal_hex_constant(self) -> None:
        assert classify_claim("The header starts with 0xFF00AA magic bytes") == "internal_detail"

    def test_internal_jcid_identifier(self) -> None:
        assert classify_claim("Uses jcidReadOnlyPersistablePropertyContainerForAuthor") == "internal_detail"

    def test_internal_section_reference(self) -> None:
        assert classify_claim("See section 2.6.7 for the binary format") == "internal_detail"

    def test_internal_rfc_language(self) -> None:
        assert classify_claim("The field MUST be set to null") == "internal_detail"

    def test_internal_byte_spec(self) -> None:
        assert classify_claim("gctxid (20 bytes): the global context identifier") == "internal_detail"

    def test_internal_high_stopword_ratio(self) -> None:
        assert classify_claim("it is the one that is in the for") == "internal_detail"

    def test_internal_long_camelcase(self) -> None:
        assert classify_claim("Uses ObjectDeclarationRevisionWithRefCountBody") == "internal_detail"

    def test_internal_code_density(self) -> None:
        text = "get_cell_value set_row_height apply_style create_workbook format_range"
        assert classify_claim(text) == "internal_detail"

    def test_user_facing_normal_sentence(self) -> None:
        assert classify_claim("The library provides comprehensive support for spreadsheet manipulation") == "user_facing"


class TestFilterClaims:
    def _make_claim(self, text: str, claim_id: str = "CLM-test-001") -> Claim:
        return Claim(claim_id=claim_id, text=text, kind="feature")

    def test_keeps_user_facing(self) -> None:
        claims = [self._make_claim("Supports PDF export")]
        result = filter_claims(claims)
        assert len(result) == 1
        assert result[0].visibility == "public"

    def test_retags_internal_as_internal(self) -> None:
        claims = [self._make_claim("See section 2.6.7 for the binary format")]
        result = filter_claims(claims)
        assert len(result) == 1
        assert result[0].visibility == "internal"

    def test_retags_developer_as_internal(self) -> None:
        claims = [self._make_claim("TODO: fix this later")]
        result = filter_claims(claims)
        assert len(result) == 1
        assert result[0].visibility == "internal"

    def test_does_not_mutate_input(self) -> None:
        original = self._make_claim("TODO: refactor")
        claims = [original]
        result = filter_claims(claims)
        assert original.visibility == "public"
        assert result[0].visibility == "internal"

    def test_mixed_list(self) -> None:
        claims = [
            self._make_claim("Supports PDF export", "CLM-001"),
            self._make_claim("TODO: refactor this", "CLM-002"),
            self._make_claim("0xFF00AA magic bytes", "CLM-003"),
            self._make_claim("Easy to install via pip", "CLM-004"),
        ]
        result = filter_claims(claims)
        public = [c for c in result if c.visibility == "public"]
        internal = [c for c in result if c.visibility == "internal"]
        assert len(public) == 2
        assert len(internal) == 2

    def test_empty_list(self) -> None:
        assert filter_claims([]) == []


class TestInternalContentTermSync:
    """All 10 synced spec_leakage terms must be caught by classify_claim (H-03).

    NOTE: "binary format" removed (TC-3882) — false positive on legitimate file-format tables.
    NOTE: "implementation detail" removed (TC-3884) — false positive on developer documentation.
    """

    @pytest.mark.parametrize("term", [
        "file format specification",
        "internal api",
        "internal method",
        "private field",
        "wire protocol",
        "serialization format",
        "byte offset",
        "memory layout",
        "vtable",
        "opcode",
    ])
    def test_internal_content_term(self, term: str) -> None:
        text = f"The library uses {term} for processing"
        assert classify_claim(text) == "internal_detail"

    def test_private_module_reference(self) -> None:
        assert classify_claim("from aspose._internal import x") == "internal_detail"

    def test_binary_formatting_not_matched(self) -> None:
        """Word boundary: 'binary formatting' must not trigger 'binary format'."""
        assert classify_claim("Support for binary formatting options") == "user_facing"
