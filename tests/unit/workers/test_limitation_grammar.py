"""Tests for limitation claim grammar normalization (Plan A1).

Verifies that NotImplementedError messages are normalized before
being composed into limitation claims, preventing fused grammar like
'does not yet support X is not implemented'.
"""
from launch.workers.w2_facts_builder.code_analyzer import _normalize_limitation_msg


class TestNormalizeLimitationMsg:
    """Test _normalize_limitation_msg strips redundant suffixes."""

    def test_strips_is_not_implemented(self):
        assert _normalize_limitation_msg(
            "FBX animation keyframes is not implemented"
        ) == "FBX animation keyframes"

    def test_strips_not_yet_supported(self):
        assert _normalize_limitation_msg(
            "GLTF export not yet supported"
        ) == "GLTF export"

    def test_strips_is_not_implemented_for_class(self):
        assert _normalize_limitation_msg(
            "get_entity_renderer_key is not implemented for Camera"
        ) == "get_entity_renderer_key"

    def test_strips_not_implemented(self):
        assert _normalize_limitation_msg(
            "optimize not implemented"
        ) == "optimize"

    def test_strips_not_yet_available(self):
        assert _normalize_limitation_msg(
            "height_map constructor is not yet available"
        ) == "height_map constructor"

    def test_preserves_clean_msg(self):
        assert _normalize_limitation_msg("custom shaders") == "custom shaders"

    def test_preserves_feature_name_only(self):
        assert _normalize_limitation_msg("do_boolean") == "do_boolean"

    def test_empty_after_strip(self):
        """If msg becomes empty after stripping, return empty string."""
        assert _normalize_limitation_msg("is not implemented") == ""

    def test_strips_trailing_period(self):
        assert _normalize_limitation_msg(
            "clear is not implemented."
        ) == "clear"
