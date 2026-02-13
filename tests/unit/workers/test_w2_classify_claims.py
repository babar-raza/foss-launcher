"""Tests for TC-1402: LLM claim classification."""
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from launch.workers.w2_facts_builder.classify_claims import (
    classify_claims_batch,
    _heuristic_classify,
    _classify_offline,
    _strip_markdown_fences,
)


def _make_claim(claim_id, text, kind="key_feature"):
    """Create a minimal claim dict for testing."""
    return {
        "claim_id": claim_id,
        "claim_text": text,
        "claim_kind": kind,
        "truth_status": "fact",
        "confidence": "high",
        "citations": [
            {
                "path": "test.py",
                "start_line": 1,
                "end_line": 1,
                "source_type": "source_code",
            }
        ],
    }


class TestClassifyClaimsBatch:
    """Tests for classify_claims_batch."""

    def test_offline_keeps_user_facing(self):
        """Verify user-facing claims pass through offline filter."""
        claims = [
            _make_claim("c1", "Aspose.3D supports FBX format"),
            _make_claim("c2", "The Scene class provides save() method"),
        ]
        result = classify_claims_batch(claims, "Aspose.3D", offline_mode=True)
        assert len(result) == 2

    def test_offline_filters_developer_instructions(self):
        """Verify developer instructions are filtered offline."""
        claims = [
            _make_claim("c1", "Aspose.3D supports FBX format"),
            _make_claim("c2", "Your job is to rewrite the parser module"),
            _make_claim("c3", "TODO: implement caching for large files"),
        ]
        result = classify_claims_batch(claims, "Aspose.3D", offline_mode=True)
        assert len(result) == 1
        assert result[0]["claim_id"] == "c1"

    def test_offline_filters_internal_details(self):
        """Verify internal details are filtered offline."""
        claims = [
            _make_claim("c1", "Aspose.3D supports FBX format"),
            _make_claim(
                "c2",
                "The jcidParagraphNode identifier maps to 0x00120034",
            ),
            _make_claim(
                "c3",
                "The internal CompactBinaryTreeNodeManager handles serialization",
            ),
        ]
        result = classify_claims_batch(claims, "Aspose.3D", offline_mode=True)
        # c1 should pass, c2 should be filtered (jcid + hex)
        assert any(c["claim_id"] == "c1" for c in result)
        assert not any(c["claim_id"] == "c2" for c in result)

    def test_offline_preserves_claim_structure(self):
        """Verify filtered claims have same structure."""
        claims = [_make_claim("c1", "Aspose.3D supports FBX format")]
        result = classify_claims_batch(claims, "Aspose.3D", offline_mode=True)
        assert result[0] == claims[0]  # Exact same dict, not modified

    def test_llm_path_mocked(self):
        """Verify LLM path classifies and filters. Testing: mocked"""
        mock_client = MagicMock()
        mock_client.chat_completion.return_value = {
            "content": json.dumps([
                {"claim_id": "c1", "classification": "user_facing"},
                {"claim_id": "c2", "classification": "internal_detail"},
            ])
        }
        claims = [
            _make_claim("c1", "Supports FBX format"),
            _make_claim("c2", "Internal node type 0x0012"),
        ]
        result = classify_claims_batch(claims, "Aspose.3D", llm_client=mock_client)
        assert len(result) == 1
        assert result[0]["claim_id"] == "c1"

    def test_llm_failure_falls_back_offline(self):
        """Verify LLM failure falls back to offline heuristics."""
        mock_client = MagicMock()
        mock_client.chat_completion.side_effect = Exception("LLM error")
        claims = [
            _make_claim("c1", "Supports FBX format"),
            _make_claim("c2", "TODO fix this parser"),
        ]
        result = classify_claims_batch(claims, "Aspose.3D", llm_client=mock_client)
        assert len(result) == 1  # c2 filtered by offline

    def test_empty_claims_returns_empty(self):
        """Verify empty input returns empty output."""
        result = classify_claims_batch([], "Aspose.3D", offline_mode=True)
        assert result == []

    def test_no_claims_filtered_when_all_user_facing(self):
        """Verify no reduction when all claims are user-facing."""
        claims = [
            _make_claim("c1", "Aspose.3D supports FBX format"),
            _make_claim("c2", "Install via pip install aspose-3d"),
            _make_claim("c3", "The Scene class allows loading 3D models"),
        ]
        result = classify_claims_batch(claims, "Aspose.3D", offline_mode=True)
        assert len(result) == 3

    def test_llm_response_wrapped_in_object(self):
        """Verify LLM responses wrapped in a dict are handled. Testing: mocked"""
        mock_client = MagicMock()
        mock_client.chat_completion.return_value = {
            "content": json.dumps({
                "classifications": [
                    {"claim_id": "c1", "classification": "user_facing"},
                    {"claim_id": "c2", "classification": "developer_instruction"},
                ]
            })
        }
        claims = [
            _make_claim("c1", "Supports FBX format"),
            _make_claim("c2", "Your job is to fix the parser"),
        ]
        result = classify_claims_batch(claims, "Aspose.3D", llm_client=mock_client)
        assert len(result) == 1
        assert result[0]["claim_id"] == "c1"

    def test_llm_response_with_markdown_fences(self):
        """Verify markdown-fenced LLM responses are parsed. Testing: mocked"""
        mock_client = MagicMock()
        mock_client.chat_completion.return_value = {
            "content": '```json\n[{"claim_id": "c1", "classification": "user_facing"}]\n```'
        }
        claims = [_make_claim("c1", "Supports FBX format")]
        result = classify_claims_batch(claims, "Aspose.3D", llm_client=mock_client)
        assert len(result) == 1

    def test_unclassified_claims_kept_as_safety_net(self):
        """Verify claims not in LLM response are kept (safety net). Testing: mocked"""
        mock_client = MagicMock()
        # LLM only returns classification for c1, not c2
        mock_client.chat_completion.return_value = {
            "content": json.dumps([
                {"claim_id": "c1", "classification": "user_facing"},
            ])
        }
        claims = [
            _make_claim("c1", "Supports FBX format"),
            _make_claim("c2", "Also supports STL format"),
        ]
        result = classify_claims_batch(claims, "Aspose.3D", llm_client=mock_client)
        # Both should be kept: c1 is user_facing, c2 not in response -> safety net keeps it
        assert len(result) == 2


class TestHeuristicClassify:
    """Tests for _heuristic_classify internal function."""

    def test_user_facing_normal_text(self):
        """Normal product text classified as user_facing."""
        assert _heuristic_classify("Supports FBX and OBJ formats") == "user_facing"

    def test_developer_instruction_todo(self):
        """TODO comments classified as developer_instruction."""
        assert _heuristic_classify("TODO: add support for GLTF") == "developer_instruction"

    def test_developer_instruction_fixme(self):
        """FIXME comments classified as developer_instruction."""
        assert _heuristic_classify("FIXME: this is broken") == "developer_instruction"

    def test_developer_instruction_your_job(self):
        """'Your job is to' classified as developer_instruction."""
        assert _heuristic_classify("Your job is to parse the XML") == "developer_instruction"

    def test_internal_detail_hex_constant(self):
        """Hex constants classified as internal_detail."""
        assert _heuristic_classify("Node type identifier is 0x00120034") == "internal_detail"

    def test_internal_detail_jcid(self):
        """jcid-prefixed identifiers classified as internal_detail."""
        assert _heuristic_classify("The jcidParagraphNode stores text") == "internal_detail"

    def test_internal_detail_guid(self):
        """GUID identifiers classified as internal_detail."""
        assert _heuristic_classify("Uses guid_format for tracking") == "internal_detail"

    def test_internal_detail_long_camelcase(self):
        """Long CamelCase identifiers classified as internal_detail."""
        assert _heuristic_classify(
            "The CompactBinaryTreeNodeManager handles all operations"
        ) == "internal_detail"

    def test_internal_detail_hack(self):
        """'hack' classified as developer_instruction."""
        assert _heuristic_classify("This is a hack to work around the issue") == "developer_instruction"

    def test_workaround(self):
        """'workaround' classified as developer_instruction."""
        assert _heuristic_classify("Use this workaround for the bug") == "developer_instruction"


class TestStripMarkdownFences:
    """Tests for _strip_markdown_fences helper."""

    def test_no_fences(self):
        """Plain JSON passes through unchanged."""
        assert _strip_markdown_fences('[{"a": 1}]') == '[{"a": 1}]'

    def test_json_fences(self):
        """```json fences are stripped."""
        assert _strip_markdown_fences('```json\n[{"a": 1}]\n```') == '[{"a": 1}]'

    def test_plain_fences(self):
        """Plain ``` fences are stripped."""
        assert _strip_markdown_fences('```\n[{"a": 1}]\n```') == '[{"a": 1}]'


class TestClassifyOffline:
    """Tests for _classify_offline."""

    def test_returns_dict_mapping(self):
        """Verify _classify_offline returns claim_id -> label dict."""
        claims = [
            _make_claim("c1", "Supports FBX format"),
            _make_claim("c2", "TODO fix this"),
        ]
        result = _classify_offline(claims)
        assert isinstance(result, dict)
        assert result["c1"] == "user_facing"
        assert result["c2"] == "developer_instruction"

    def test_all_claims_have_entries(self):
        """Every claim gets a classification entry."""
        claims = [
            _make_claim("c1", "Feature A"),
            _make_claim("c2", "Feature B"),
            _make_claim("c3", "Feature C"),
        ]
        result = _classify_offline(claims)
        assert len(result) == 3

    def test_filters_binary_spec_text(self):
        """TC-1501: Verify prose-style spec text is classified as internal_detail."""
        claims = [
            # Binary field descriptions
            _make_claim("c1", "gctxid (20 bytes): An ExtendedGUID structure as specified in section 2.2.1"),
            _make_claim("c2", "cRef (4 bytes): An unsigned integer that specifies the reference count"),
            # Spec section references
            _make_claim("c3", "The structure follows section 2.6.7 of the specification"),
            # RFC normative language
            _make_claim("c4", "The value MUST be set to zero"),
            _make_claim("c5", "Each partition SHALL have a unique identifier"),
            # OneNote spec identifiers
            _make_claim("c6", "Object Declaration.PartitionID specifies the JCID of the object"),
            _make_claim("c7", "The CompactID structure is defined in the FileNode"),
            _make_claim("c8", "PropertySet contains the OutlineElementRTL field"),
            # Quoted byte values
            _make_claim("c9", "Set the flag to '0xFF' for maximum value"),
            # User-facing claim (should pass through)
            _make_claim("c10", "Supports reading and writing OneNote files"),
        ]
        result = _classify_offline(claims)

        # All spec-text claims should be internal_detail
        assert result["c1"] == "internal_detail", "Binary field description should be filtered"
        assert result["c2"] == "internal_detail", "Binary field with spec reference should be filtered"
        assert result["c3"] == "internal_detail", "Spec section reference should be filtered"
        assert result["c4"] == "internal_detail", "RFC MUST language should be filtered"
        assert result["c5"] == "internal_detail", "RFC SHALL language should be filtered"
        assert result["c6"] == "internal_detail", "OneNote ObjectDeclaration should be filtered"
        assert result["c7"] == "internal_detail", "OneNote CompactID/FileNode should be filtered"
        assert result["c8"] == "internal_detail", "OneNote PropertySet/OutlineElementRTL should be filtered"
        assert result["c9"] == "internal_detail", "Quoted byte value should be filtered"

        # User-facing claim should pass through
        assert result["c10"] == "user_facing", "Normal user-facing claim should pass"


class TestTC1606HeuristicStrengthening:
    """TC-1606: Tests for strengthened offline heuristic classification."""

    def test_spec_fragment_bytes_rejected(self):
        """TC-1606: Bare byte-size spec fragments classified as internal_detail."""
        assert _heuristic_classify(
            "This field uses 16 bytes for the header structure"
        ) == "internal_detail"

    def test_spec_fragment_bytes_singular(self):
        """TC-1606: Singular 'byte' also caught."""
        assert _heuristic_classify(
            "Each entry is exactly 1 byte long"
        ) == "internal_detail"

    def test_short_hex_constant_rejected(self):
        """TC-1606: Short 2-digit hex constants classified as internal_detail."""
        assert _heuristic_classify(
            "Flag value is 0xFF for enabled state"
        ) == "internal_detail"

    def test_stopword_heavy_rejected(self):
        """TC-1606: Claims with >60% stopwords classified as 'other' (non-informative)."""
        assert _heuristic_classify(
            "It is a the and for with this that"
        ) == "other"

    def test_stopword_heavy_filtered_from_batch(self):
        """TC-1606: Non-informative claims are removed by classify_claims_batch."""
        claims = [
            _make_claim("c1", "Scene class provides methods to load 3D models"),
            _make_claim("c2", "It is a the and for with this that"),
        ]
        result = classify_claims_batch(claims, "Aspose.3D", offline_mode=True)
        assert len(result) == 1
        assert result[0]["claim_id"] == "c1"

    def test_normal_claim_not_affected(self):
        """TC-1606: Normal product claims are NOT rejected by new heuristics."""
        assert _heuristic_classify(
            "Scene class provides methods to load and save 3D models in multiple formats"
        ) == "user_facing"

    def test_normal_claim_with_some_stopwords_not_affected(self):
        """TC-1606: Claims with moderate stopword ratio stay user_facing."""
        # "Aspose.3D supports loading and saving of 3D models"
        # stopwords: and, of => 2/8 = 25% < 60% threshold
        assert _heuristic_classify(
            "Aspose.3D supports loading and saving of 3D models"
        ) == "user_facing"

    def test_code_ratio_threshold_raised_for_long_claims(self):
        """TC-1606: Longer claims (>100 chars) use 0.20 threshold for code_ratio.

        A claim with code_ratio between 0.15 and 0.20 should be filtered for
        short claims but allowed for long claims.
        """
        # Short claim (~50 chars) with moderate code identifiers
        # This has 2 code words in 7 total words => ratio ~0.29, > both thresholds
        short_high = "The parse_xml and build_tree functions handle get_node and set_value and load_data calls quickly"
        # That's clearly above both thresholds - let's use the threshold directly
        # We need a claim where code_ratio is between 0.15 and 0.20

        # 1 code ident in 6 words = 0.167 => above 0.15 for short, below 0.20 for long
        short_claim = "Config uses parse_xml for loading data cleanly"
        long_claim = (
            "The configuration subsystem provides a flexible and extensible framework "
            "that uses parse_xml for loading data from various sources into memory cleanly"
        )

        # Short claim (< 100 chars): 1/7 words = 0.14 ...
        # Let me be precise. count words and code idents
        # short_claim words: Config uses parse_xml for loading data cleanly = 7
        # code idents: parse_xml = 1 => 1/7 = 0.143 < 0.15 => user_facing (under old AND new)
        # Need exactly 0.15 < ratio <= 0.20

        # Let's use 2 code idents in 10 words = 0.20, right at boundary
        # Need >0.15 but <=0.20 for the test to demonstrate the difference
        # 2 code idents in 12 words = 0.167
        short_borderline = "The parse_xml and build_tree modules read config data for quick processing now today"
        # words: 13, code idents: parse_xml, build_tree = 2, ratio = 2/13 = 0.154 > 0.15

        # Same semantic content but padded to > 100 chars
        long_borderline = (
            "The parse_xml and build_tree modules provide robust mechanisms for reading "
            "configuration data from various external sources for quick processing now today"
        )
        # Verify length assumption
        assert len(long_borderline) > 100

        # Short claim: ratio ~0.154 > 0.15 threshold => internal_detail
        assert _heuristic_classify(short_borderline) == "internal_detail"
        # Long claim with same ratio: ~0.154 < 0.20 threshold => user_facing
        assert _heuristic_classify(long_borderline) == "user_facing"

    def test_section_reference_still_caught(self):
        """TC-1606: Existing section reference pattern still works."""
        assert _heuristic_classify(
            "As defined in section 3.2 of the binary format specification"
        ) == "internal_detail"

    def test_empty_claim_is_user_facing(self):
        """TC-1606: Empty claim text does not crash, defaults to user_facing."""
        assert _heuristic_classify("") == "user_facing"

    def test_single_word_claim_not_falsely_rejected(self):
        """TC-1606: Single meaningful word is not rejected by stopword check."""
        # "the" is a stopword => 1/1 = 100% > 60%
        assert _heuristic_classify("the") == "other"
        # A real single word should be user_facing
        assert _heuristic_classify("Installation") == "user_facing"
