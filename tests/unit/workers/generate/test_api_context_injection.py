"""Tests for TC-HYBRID-07: typed API context injection in section prompts."""
from __future__ import annotations

import pytest

from launcher.models.product import (
    ClassBrief,
    EnumMember,
    EnumRecord,
    MethodParam,
    MethodSignature,
    PropertyRecord,
)
from launcher.workers.generate.section_prompt import (
    _API_BLOCK_MAX_CHARS,
    _build_typed_method_sig,
    _format_api_surface,
    _get_top_level_enums,
)


# ---------------------------------------------------------------------------
# _build_typed_method_sig tests
# ---------------------------------------------------------------------------


class TestBuildTypedMethodSig:
    """TC-HYBRID-07: _build_typed_method_sig helper."""

    def test_typed_method_sig_with_params_and_return(self):
        sig = MethodSignature(
            name="load",
            parameters=[
                MethodParam(name="path", type_annotation="str"),
                MethodParam(name="options", type_annotation="LoadOptions"),
            ],
            return_type="Scene",
        )
        result = _build_typed_method_sig(sig)
        assert result == "load(path: str, options: LoadOptions) -> Scene"

    def test_typed_method_sig_no_return(self):
        sig = MethodSignature(
            name="load",
            parameters=[MethodParam(name="path", type_annotation="str")],
            return_type="",
        )
        result = _build_typed_method_sig(sig)
        assert result == "load(path: str)"

    def test_typed_method_sig_static(self):
        sig = MethodSignature(
            name="create",
            parameters=[],
            return_type="Scene",
            is_static=True,
        )
        result = _build_typed_method_sig(sig)
        assert result == "[static] create() -> Scene"

    def test_typed_method_sig_no_params(self):
        sig = MethodSignature(name="close", parameters=[], return_type="")
        result = _build_typed_method_sig(sig)
        assert result == "close()"

    def test_typed_method_sig_param_without_annotation(self):
        """Params with no type_annotation should fall back to bare name."""
        sig = MethodSignature(
            name="process",
            parameters=[MethodParam(name="data", type_annotation="")],
            return_type="None",
        )
        result = _build_typed_method_sig(sig)
        assert result == "process(data) -> None"


# ---------------------------------------------------------------------------
# _format_api_surface typed method/property tests
# ---------------------------------------------------------------------------


class TestFormatApiSurfaceTypedContext:
    """TC-HYBRID-07: _format_api_surface uses typed fields when available."""

    def test_format_api_surface_uses_typed_methods(self):
        """When typed_methods present, output contains param types and return type."""
        briefs = [
            ClassBrief(
                name="Scene",
                typed_methods=[
                    MethodSignature(
                        name="load",
                        parameters=[MethodParam(name="path", type_annotation="str")],
                        return_type="Scene",
                    )
                ],
            )
        ]
        result = _format_api_surface(["Scene"], class_briefs=briefs)
        assert "load(path: str) -> Scene" in result

    def test_format_api_surface_falls_back_to_methods(self):
        """When typed_methods is empty, falls back to plain methods list."""
        briefs = [
            ClassBrief(
                name="Document",
                methods=["load", "save", "close"],
                typed_methods=[],  # explicitly empty
            )
        ]
        result = _format_api_surface(["Document"], class_briefs=briefs)
        assert "load" in result
        assert "save" in result
        assert "close" in result
        # Should not have typed-sig format (no param: Type patterns)
        assert "load(path: str)" not in result

    def test_format_api_surface_includes_typed_properties(self):
        """typed_properties with type_annotation and is_readonly renders correctly."""
        briefs = [
            ClassBrief(
                name="Node",
                typed_properties=[
                    PropertyRecord(
                        name="root_node",
                        type_annotation="Node",
                        is_readonly=True,
                    ),
                    PropertyRecord(
                        name="unit_scale",
                        type_annotation="float",
                        is_readonly=False,
                    ),
                ],
            )
        ]
        result = _format_api_surface(["Node"], class_briefs=briefs)
        assert "root_node: Node (read-only)" in result
        assert "unit_scale: float" in result
        # read-only should not appear for non-readonly property
        assert "unit_scale: float (read-only)" not in result

    def test_format_api_surface_falls_back_to_plain_properties(self):
        """When typed_properties is empty, uses plain properties list."""
        briefs = [
            ClassBrief(
                name="Document",
                properties=["pages", "title"],
                typed_properties=[],
            )
        ]
        result = _format_api_surface(["Document"], class_briefs=briefs)
        assert "pages" in result
        assert "title" in result

    def test_format_api_surface_includes_enum_members(self):
        """Per-class enum members appear in output."""
        briefs = [
            ClassBrief(
                name="Scene",
                enums=[
                    EnumRecord(
                        name="FileFormat",
                        members=[
                            EnumMember(name="FBX"),
                            EnumMember(name="OBJ"),
                            EnumMember(name="GLTF"),
                        ],
                    )
                ],
            )
        ]
        result = _format_api_surface(["Scene"], class_briefs=briefs)
        assert "FileFormat" in result
        assert "FBX" in result
        assert "OBJ" in result
        assert "GLTF" in result

    def test_format_api_surface_top_level_enums(self):
        """Top-level enums block appears when enums passed to _format_api_surface."""
        briefs = [ClassBrief(name="Loader")]
        top_enums = [
            EnumRecord(
                name="CompressionLevel",
                members=[
                    EnumMember(name="NONE"),
                    EnumMember(name="FAST"),
                    EnumMember(name="BEST"),
                ],
            )
        ]
        result = _format_api_surface(["Loader"], class_briefs=briefs, enums=top_enums)
        assert "Top-level enums:" in result
        assert "CompressionLevel" in result
        assert "NONE" in result
        assert "FAST" in result
        assert "BEST" in result

    def test_format_api_surface_hard_cap(self):
        """Output > 4000 chars gets truncated with '... (API surface truncated)' marker."""
        # Build a brief with many long method signatures to exceed the cap
        long_methods = [
            MethodSignature(
                name=f"method_{i:03d}",
                parameters=[
                    MethodParam(name="param_a", type_annotation="VeryLongTypeName"),
                    MethodParam(name="param_b", type_annotation="AnotherLongTypeName"),
                ],
                return_type="SomeReturnType",
            )
            for i in range(100)
        ]
        briefs = [ClassBrief(name=f"Class{i}", typed_methods=long_methods) for i in range(20)]
        public_classes = [f"Class{i}" for i in range(20)]
        result = _format_api_surface(public_classes, class_briefs=briefs)
        assert "... (API surface truncated)" in result
        assert len(result) <= _API_BLOCK_MAX_CHARS + len("\n  ... (API surface truncated)")


# ---------------------------------------------------------------------------
# _get_top_level_enums tests
# ---------------------------------------------------------------------------


class TestGetTopLevelEnums:
    """TC-HYBRID-07: _get_top_level_enums deduplication helper."""

    def test_get_top_level_enums_deduplicates(self):
        """Same enum name in multiple briefs appears only once."""
        enum = EnumRecord(
            name="FileFormat",
            members=[EnumMember(name="FBX"), EnumMember(name="OBJ")],
        )
        briefs = [
            ClassBrief(name="ClassA", enums=[enum]),
            ClassBrief(name="ClassB", enums=[enum]),
        ]
        result = _get_top_level_enums(briefs)
        names = [e.name for e in result]
        assert names.count("FileFormat") == 1

    def test_get_top_level_enums_empty_when_no_briefs(self):
        assert _get_top_level_enums(None) == []
        assert _get_top_level_enums([]) == []

    def test_get_top_level_enums_collects_all_unique(self):
        briefs = [
            ClassBrief(
                name="ClassA",
                enums=[EnumRecord(name="EnumA", members=[EnumMember(name="X")])],
            ),
            ClassBrief(
                name="ClassB",
                enums=[EnumRecord(name="EnumB", members=[EnumMember(name="Y")])],
            ),
        ]
        result = _get_top_level_enums(briefs)
        assert len(result) == 2
        names = {e.name for e in result}
        assert names == {"EnumA", "EnumB"}
