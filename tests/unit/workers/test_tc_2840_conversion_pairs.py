"""TC-2840: Tests for _extract_top_conversion_pair type handling fix.

Verifies that conversion_pairs in all formats (nested list, dict, flat)
produce clean string tuples instead of Python repr() strings.
"""

from __future__ import annotations

import pytest

from src.launch.workers.w4_ia_planner.worker import _extract_top_conversion_pair


class TestExtractTopConversionPair:

    def test_nested_list_format(self):
        """W2 normalized: [["PDF","DOCX"], ["XLSX","CSV"]] → ("PDF","DOCX")."""
        facts = {"claim_groups": {"conversion_pairs": [["PDF", "DOCX"], ["XLSX", "CSV"]]}}
        assert _extract_top_conversion_pair(facts) == ("PDF", "DOCX")

    def test_nested_tuple_format(self):
        """Tuple variant: [("PDF","DOCX")] → ("PDF","DOCX")."""
        facts = {"claim_groups": {"conversion_pairs": [("PDF", "DOCX")]}}
        assert _extract_top_conversion_pair(facts) == ("PDF", "DOCX")

    def test_dict_format_source_target(self):
        """Dict with source/target: [{"source":"PDF","target":"DOCX"}] → ("PDF","DOCX")."""
        facts = {"claim_groups": {"conversion_pairs": [{"source": "PDF", "target": "DOCX"}]}}
        assert _extract_top_conversion_pair(facts) == ("PDF", "DOCX")

    def test_dict_format_from_to(self):
        """Dict with from/to: [{"from":"PDF","to":"DOCX"}] → ("PDF","DOCX")."""
        facts = {"claim_groups": {"conversion_pairs": [{"from": "PDF", "to": "DOCX"}]}}
        assert _extract_top_conversion_pair(facts) == ("PDF", "DOCX")

    def test_flat_list_format(self):
        """Legacy flat: ["PDF","DOCX"] → ("PDF","DOCX")."""
        facts = {"claim_groups": {"conversion_pairs": ["PDF", "DOCX"]}}
        assert _extract_top_conversion_pair(facts) == ("PDF", "DOCX")

    def test_empty_list(self):
        facts = {"claim_groups": {"conversion_pairs": []}}
        assert _extract_top_conversion_pair(facts) == ("", "")

    def test_missing_claim_groups(self):
        assert _extract_top_conversion_pair({}) == ("", "")

    def test_no_repr_leak(self):
        """The bug: [["it","a"]] should NOT produce ("['IT', 'A']")."""
        facts = {"claim_groups": {"conversion_pairs": [["it", "a"]]}}
        result = _extract_top_conversion_pair(facts)
        assert "[" not in result[0]
        assert "'" not in result[0]
        assert result == ("IT", "A")

    def test_case_upper(self):
        """All results should be uppercased."""
        facts = {"claim_groups": {"conversion_pairs": [["pdf", "docx"]]}}
        result = _extract_top_conversion_pair(facts)
        assert result == ("PDF", "DOCX")

    def test_single_element_nested_list(self):
        """Single-element nested list: [["PDF"]] — insufficient, return empty."""
        facts = {"claim_groups": {"conversion_pairs": [["PDF"]]}}
        result = _extract_top_conversion_pair(facts)
        assert result == ("", "")

    def test_single_flat_string(self):
        """Single flat string: ["PDF"] — insufficient, return empty."""
        facts = {"claim_groups": {"conversion_pairs": ["PDF"]}}
        result = _extract_top_conversion_pair(facts)
        assert result == ("", "")
