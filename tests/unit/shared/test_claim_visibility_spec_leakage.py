"""Tests for spec leakage prevention in claim visibility classification.

TC-3804: Tests for extract_claims.classify_claim_visibility (dead code in v2,
    kept for coverage of the v1 path).
TC-3828: Tests for classify_claims.classify_claim (live v2 path) — adds
    RFC-2119 keywords, spec phrases, binary identifiers, encoding terms,
    hex threshold fix, and cross-sync with spec_leakage._INTERNAL_TERMS.
"""
from __future__ import annotations

import pytest

from launcher.shared.classify_claims import classify_claim_visibility


class TestInternalContentTerms:
    """All 10 terms from spec_leakage.py _INTERNAL_TERMS must be caught.

    NOTE: "binary format" was removed (TC-3882) — it produced false positives on legitimate
    user-facing content like "Excel Binary (.xlsb) is a binary format for performance".
    NOTE: "implementation detail" was removed (TC-3884) — it produced false positives on
    legitimate developer documentation like "rather than implementation details".
    NOTE: "file format specification" was removed (TC-3893) — it produced false positives for
    Aspose libraries that legitimately reference public format specs (OneNote, Excel, etc.).
    """

    @pytest.mark.parametrize("term", [
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
    def test_internal_term_classified_internal(self, term: str) -> None:
        text = f"The library uses {term} for processing"
        assert classify_claim_visibility(text, "feature") == "internal"


class TestPrivateModuleReferences:
    """Claims referencing private modules must be classified as internal."""

    def test_underscore_internal_module(self) -> None:
        text = "Don't import from aspose.slides_foss._internal"
        assert classify_claim_visibility(text, "feature") == "internal"

    def test_underscore_private_module(self) -> None:
        text = "The aspose.cells._private module contains helpers"
        assert classify_claim_visibility(text, "feature") == "internal"

    def test_private_implementation_phrase(self) -> None:
        text = "This is a private implementation of the converter"
        assert classify_claim_visibility(text, "feature") == "internal"


class TestPublicClaimsUnchanged:
    """Normal product claims must remain public — no false positives."""

    def test_format_support_claim(self) -> None:
        text = "The library supports XLSX, CSV, and PDF formats"
        assert classify_claim_visibility(text, "feature") == "public"

    def test_conversion_claim(self) -> None:
        text = "Supports converting XLSX to PDF format"
        assert classify_claim_visibility(text, "feature") == "public"

    def test_install_claim(self) -> None:
        text = "Install the library using pip install aspose-cells"
        assert classify_claim_visibility(text, "feature") == "public"

    def test_api_usage_claim(self) -> None:
        text = "Create a workbook and add data to cells"
        assert classify_claim_visibility(text, "feature") == "public"


class TestBoundaryFalsePositives:
    """Word-boundary matching must not trigger on substring overlaps (H-02)."""

    def test_binary_formatting_not_binary_format(self) -> None:
        text = "Support for binary formatting options in cells"
        assert classify_claim_visibility(text, "feature") == "public"

    def test_serialization_formatters_not_serialization_format(self) -> None:
        text = "Use serialization formatters for custom output"
        assert classify_claim_visibility(text, "feature") == "public"

    def test_implementation_details_no_longer_blocked(self) -> None:
        """TC-3884: 'implementation details' removed — legitimate developer documentation use.

        Example: 'for implementation details, see the API reference'
        """
        text = "The implementation details are documented in the guide"
        assert classify_claim_visibility(text, "feature") == "public"

    def test_export_binary_without_format(self) -> None:
        text = "Export data in binary"
        assert classify_claim_visibility(text, "feature") == "public"

    def test_opcodes_plural_still_internal(self) -> None:
        text = "The library processes opcodes efficiently"
        assert classify_claim_visibility(text, "feature") == "internal"

    def test_case_insensitive_match_opcode(self) -> None:
        """Case-insensitive matching still works for retained terms."""
        text = "The library handles OPCODE sequences efficiently"
        assert classify_claim_visibility(text, "feature") == "internal"

    def test_binary_format_no_longer_blocked(self) -> None:
        """TC-3882: 'binary format' removed — legitimate use in file-format tables is now public.

        Example: 'Excel Binary (.xlsb) is a binary format for performance'
        """
        text = "Excel Binary (.xlsb) is a binary format for performance"
        assert classify_claim_visibility(text, "feature") == "public"

    def test_binary_format_in_troubleshooting_context(self) -> None:
        """TC-3882: 'non-Excel binary formats like .xlsb' is legitimate user content."""
        text = "non-Excel binary formats like .xlsb may not be fully supported"
        assert classify_claim_visibility(text, "feature") == "public"


# ---------------------------------------------------------------------------
# TC-3828: classify_claims.classify_claim (live v2 path)
# ---------------------------------------------------------------------------

from launcher.shared.classify_claims import classify_claim  # noqa: E402


class TestRFC2119Keywords:
    """RFC-2119 uppercase normative keywords → internal_detail (TC-3828)."""

    @pytest.mark.parametrize("text", [
        "This MUST NOT be used in production environments",
        "The REQUIRED field stores the document ID",
        "Callers SHOULD NOT pass null values here",
        "The value MAY NOT exceed the maximum limit",
        "Support for OPTIONAL parameters is available",
        "Using RECOMMENDED settings improves performance",
        "The parser SHALL validate the input",
        "Fields MUST contain a valid GUID",
    ])
    def test_rfc2119_classified_internal(self, text: str) -> None:
        assert classify_claim(text) == "internal_detail"

    @pytest.mark.parametrize("text", [
        "This is a must-have feature for enterprise users",
        "May release includes new spreadsheet features",
        "The feature should work seamlessly with Excel",
        # All-caps hyphenated forms — hyphen creates word boundary but (?!-) blocks match
        "MUST-HAVE enterprise features for power users",
        "SHOULD-HAVE been considered in the initial design",
        "RECOMMENDED-BY the standards body for compliance",
    ])
    def test_rfc2119_false_positive_guard(self, text: str) -> None:
        """Lowercase, month, and all-caps hyphenated forms are not RFC-2119."""
        assert classify_claim(text) == "user_facing"


class TestSpecLanguagePhrases:
    """Specification language phrases → internal_detail (TC-3828)."""

    @pytest.mark.parametrize("text", [
        "As specified in this specification, the value is encoded",
        "Per the specification, all fields are required",
        "This is a normative reference to the schema definition",
        "The conformance requirement applies to all implementations",
        "See informative reference section 4.2 for examples",
    ])
    def test_spec_phrase_classified_internal(self, text: str) -> None:
        assert classify_claim(text) == "internal_detail"


class TestBinaryIdentifiers:
    """Binary format identifiers → internal_detail (TC-3828)."""

    @pytest.mark.parametrize("text", [
        "The FNDX value is stored in the header block",
        "IsFileData flag indicates whether the stream is a file",
        "The Object Data BLOB contains serialized page content",
        "stored as unsigned 32-bit integer in little-endian byte order",
    ])
    def test_binary_id_classified_internal(self, text: str) -> None:
        assert classify_claim(text) == "internal_detail"


class TestEncodingProtocolTerms:
    """Encoding and protocol terms → internal_detail (TC-3828)."""

    @pytest.mark.parametrize("text", [
        "Values are stored in little-endian byte order",
        "Uses big-endian encoding for network compatibility",
        "Text is encoded using cp1252 character set",
        "UUID format follows RFC 4122 specification",
    ])
    def test_encoding_term_classified_internal(self, text: str) -> None:
        assert classify_claim(text) == "internal_detail"


class TestHexThreshold:
    """Hex threshold fix: 4+ digits flagged, 2-digit user-facing (TC-3828)."""

    def test_four_digit_hex_internal(self) -> None:
        assert classify_claim("The constant 0xFFFF is reserved for internal use") == "internal_detail"

    def test_four_digit_hex_0042_internal(self) -> None:
        assert classify_claim("Binary marker 0x0042 signals end of block") == "internal_detail"

    def test_two_digit_hex_not_flagged(self) -> None:
        """0xFF is a common user-facing code example — must NOT be flagged."""
        # Note: quoted hex like '0xFF' is still flagged by the quoted-hex pattern.
        # Unquoted 0xFF (2 digits) must be user_facing after the threshold fix.
        result = classify_claim("Use 0xFF as the fill value for empty cells")
        # This should NOT be classified as internal_detail by the hex pattern alone.
        # (Other heuristics may still classify it, but the hex pattern itself won't fire.)
        assert result == "user_facing"


class TestCrossSync:
    """Every term in spec_leakage._INTERNAL_TERMS must be caught by classify_claim (TC-3828)."""

    def test_all_internal_terms_caught(self) -> None:
        """Cross-sync: spec_leakage._INTERNAL_TERMS ⊆ classify_claims._INTERNAL_PATTERNS."""
        from launcher.workers.evaluate.checks.spec_leakage import _INTERNAL_TERMS

        failures = []
        for term in _INTERNAL_TERMS:
            text = f"The library uses {term} for processing"
            result = classify_claim(text)
            if result == "user_facing":
                failures.append(term)

        assert not failures, (
            f"classify_claim did not catch these spec_leakage terms: {failures}. "
            "Add matching patterns to classify_claims._INTERNAL_PATTERNS."
        )
