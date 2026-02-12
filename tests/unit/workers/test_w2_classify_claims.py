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
