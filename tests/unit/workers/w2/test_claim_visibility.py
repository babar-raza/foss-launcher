"""Unit tests for claim visibility classification (TC-3672).

Tests classify_claim_visibility() and the extended _is_spec_fragment().
"""

from __future__ import annotations

import pytest

from launch.workers.w2_facts_builder.extract_claims import (
    _is_spec_fragment,
    classify_claim_visibility,
)


# ── _is_spec_fragment() extended patterns (TC-3672) ──────────────────────


class TestIsSpecFragmentExtended:
    """TC-3672: Extended _is_spec_fragment() catches pilot-observed patterns."""

    def test_catches_jcid(self):
        assert _is_spec_fragment("The JCID field identifies the object type")

    def test_catches_compact_id(self):
        assert _is_spec_fragment("CompactID is used to reference objects in the file")

    def test_catches_fndx(self):
        assert _is_spec_fragment("FNDX structures store the file node index")

    def test_catches_object_declaration(self):
        assert _is_spec_fragment("Each ObjectDeclaration describes a data element")

    def test_catches_rg_indents(self):
        assert _is_spec_fragment("The rgIndents array stores indentation levels")

    def test_catches_free_chunk_list(self):
        assert _is_spec_fragment("The free chunk list tracks unused regions")

    def test_catches_hashed_chunk_list(self):
        assert _is_spec_fragment("Entries in the hashed chunk list provide lookup")

    def test_catches_transaction_log(self):
        assert _is_spec_fragment("The transaction log records write operations")

    def test_catches_hex_constants(self):
        assert _is_spec_fragment("The magic number is 0x00001234")

    def test_catches_long_hex(self):
        assert _is_spec_fragment("Header bytes: 0xDEADBEEF indicate corruption")

    def test_catches_spec_section_refs(self):
        assert _is_spec_fragment("See section 2.2.1.3 for details")

    def test_catches_little_endian(self):
        assert _is_spec_fragment("Values are stored in little-endian encoding")

    def test_catches_big_endian(self):
        assert _is_spec_fragment("Use big-endian byte order for network transfer")

    def test_does_not_catch_normal_feature(self):
        assert not _is_spec_fragment("Aspose.Note provides notebook manipulation features")

    def test_does_not_catch_normal_api(self):
        assert not _is_spec_fragment("The Workbook class provides methods to load files")

    def test_preserves_existing_rfc_detection(self):
        assert _is_spec_fragment("Implementations MUST support UTF-8 encoding")

    def test_preserves_existing_spec_phrases(self):
        assert _is_spec_fragment("This specification defines the binary format")


# ── classify_claim_visibility() ──────────────────────────────────────────


class TestClassifyClaimVisibility:
    """TC-3672: classify_claim_visibility() correctly tags public/internal."""

    def test_public_api_claim(self):
        assert classify_claim_visibility(
            "Aspose.Cells provides the Workbook class for spreadsheet operations",
            "api",
        ) == "public"

    def test_public_feature_claim(self):
        assert classify_claim_visibility(
            "Supports converting Excel files to PDF format",
            "feature",
        ) == "public"

    def test_public_limitation_claim(self):
        assert classify_claim_visibility(
            "Does not support password-protected files in the current version",
            "limitation",
        ) == "public"

    def test_internal_spec_fragment(self):
        assert classify_claim_visibility(
            "Implementations MUST support the OneNote revision store format",
            "feature",
        ) == "internal"

    def test_internal_hex_constant(self):
        assert classify_claim_visibility(
            "The file header starts with 0xE4525600 magic bytes",
            "format",
        ) == "internal"

    def test_internal_section_ref(self):
        assert classify_claim_visibility(
            "As described in section 2.4.1 of the MS-ONESTORE specification",
            "feature",
        ) == "internal"

    def test_internal_binary_format_term(self):
        assert classify_claim_visibility(
            "The JCID field in the header identifies the object type",
            "api",
        ) == "internal"

    def test_internal_patent_email(self):
        assert classify_claim_visibility(
            "Contact iplg@microsoft.com for licensing inquiries",
            "feature",
        ) == "internal"

    def test_internal_transaction_log(self):
        assert classify_claim_visibility(
            "The transaction log records all write operations in the file store",
            "format",
        ) == "internal"

    def test_normal_workflow_is_public(self):
        assert classify_claim_visibility(
            "Install via pip install aspose-note-foss",
            "workflow",
        ) == "public"

    def test_compatibility_is_public(self):
        assert classify_claim_visibility(
            "Compatible with Python 3.8 and above",
            "compatibility",
        ) == "public"
