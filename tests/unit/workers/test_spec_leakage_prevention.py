"""Tests for TC-3683: G7 spec leakage prevention."""

from __future__ import annotations

import textwrap

import pytest

from launch.workers._shared.content_sanitizer import strip_spec_leakage_terms
from launch.workers.w2_facts_builder.extract_claims import _is_spec_fragment
from launch.workers.w5_section_writer.generators.content_generators import (
    get_claims_by_ids,
)


# ── W2 classifier: backported G7 patterns ────────────────────────────────────

class TestW2ClassifierBackportedPatterns:
    """Verify 7 gate G7 patterns are now detected by _is_spec_fragment."""

    def test_object_data_blob(self):
        assert _is_spec_fragment("The Object Data BLOB contains binary payload")

    def test_rg_outline_indent_distance(self):
        assert _is_spec_fragment("Uses RgOutlineIndentDistance for rendering")

    def test_cp1252(self):
        assert _is_spec_fragment("Text encoded in cp1252 format")

    def test_rfc_4122(self):
        assert _is_spec_fragment("UUID format per RFC 4122")

    def test_c706(self):
        assert _is_spec_fragment("NDR encoding as specified in C706")

    def test_unsigned_bit_integer(self):
        assert _is_spec_fragment("Field is an unsigned 32-bit integer")

    def test_is_file_data(self):
        assert _is_spec_fragment("Check the IsFileData property")


# ── Sanitizer: strip_spec_leakage_terms ──────────────────────────────────────

class TestStripSpecLeakageTerms:
    """Tests for strip_spec_leakage_terms() sanitizer."""

    def test_removes_jcid_line(self):
        content = "Normal paragraph.\nThis mentions JCID internal format.\nAnother paragraph."
        result = strip_spec_leakage_terms(content)
        assert "JCID" not in result
        assert "Normal paragraph." in result
        assert "Another paragraph." in result

    def test_removes_hex_constant_line(self):
        content = "Overview.\nThe value 0xABCD1234 identifies the header.\nMore text."
        result = strip_spec_leakage_terms(content)
        assert "0xABCD1234" not in result
        assert "Overview." in result

    def test_removes_spec_section_reference(self):
        content = "As described in section 2.2.1.3, the format uses...\nNormal text."
        result = strip_spec_leakage_terms(content)
        assert "section 2.2.1.3" not in result
        assert "Normal text." in result

    def test_code_fence_protection(self):
        """Spec terms inside code fences should NOT be stripped."""
        content = textwrap.dedent("""\
            Normal text.

            ```python
            # JCID is used internally
            value = 0xABCD1234
            ```

            More normal text.""")
        result = strip_spec_leakage_terms(content)
        assert "JCID" in result  # Inside fence, preserved
        assert "0xABCD1234" in result  # Inside fence, preserved
        assert "Normal text." in result

    def test_frontmatter_protection(self):
        """Spec terms in frontmatter should NOT be stripped."""
        content = textwrap.dedent("""\
            ---
            title: "JCID Overview"
            ---

            This JCID is a spec term.
            Normal text.""")
        result = strip_spec_leakage_terms(content)
        assert 'title: "JCID Overview"' in result  # Frontmatter preserved
        assert "This JCID is a spec term" not in result  # Prose stripped
        assert "Normal text." in result

    def test_headings_preserved(self):
        """Headings should not be stripped even if they contain spec terms."""
        content = "## JCID Reference\n\nSome JCID details here.\n"
        result = strip_spec_leakage_terms(content)
        assert "## JCID Reference" in result
        assert "Some JCID details here." not in result

    def test_idempotent(self):
        content = "Text with JCID.\nNormal text.\nMore CompactID stuff."
        once = strip_spec_leakage_terms(content)
        twice = strip_spec_leakage_terms(once)
        assert once == twice

    def test_no_spec_terms_unchanged(self):
        content = "Regular programming content.\nPython is great.\n"
        assert strip_spec_leakage_terms(content) == content


# ── Visibility filter: get_claims_by_ids ─────────────────────────────────────

class TestVisibilityFilter:
    """Tests for get_claims_by_ids() visibility_filter parameter."""

    def test_no_filter_returns_all(self):
        product_facts = {
            "claims": [
                {"claim_id": "c1", "visibility": "public", "text": "public claim"},
                {"claim_id": "c2", "visibility": "internal", "text": "internal claim"},
            ]
        }
        result = get_claims_by_ids(product_facts, ["c1", "c2"])
        assert len(result) == 2

    def test_public_filter_excludes_internal(self):
        product_facts = {
            "claims": [
                {"claim_id": "c1", "visibility": "public", "text": "public claim"},
                {"claim_id": "c2", "visibility": "internal", "text": "JCID internal"},
            ]
        }
        result = get_claims_by_ids(product_facts, ["c1", "c2"], visibility_filter="public")
        assert len(result) == 1
        assert result[0]["claim_id"] == "c1"

    def test_missing_visibility_defaults_to_public(self):
        """Claims without visibility field should be treated as public."""
        product_facts = {
            "claims": [
                {"claim_id": "c1", "text": "no visibility field"},
            ]
        }
        result = get_claims_by_ids(product_facts, ["c1"], visibility_filter="public")
        assert len(result) == 1
