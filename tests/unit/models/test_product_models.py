"""Unit tests for typed API surface model classes (TC-HYBRID-02)."""
from __future__ import annotations

from launcher.models.product import (
    ApiSurface,
    ClassBrief,
    EnumMember,
    EnumRecord,
    MethodParam,
    MethodSignature,
    PropertyRecord,
)


def test_class_brief_typed_methods_default_empty():
    brief = ClassBrief(name="Foo")
    assert brief.typed_methods == []
    assert brief.typed_properties == []
    assert brief.enums == []


def test_method_signature_model():
    sig = MethodSignature(
        name="save",
        parameters=[MethodParam(name="path", type_annotation="str")],
        return_type="bool",
        is_static=False,
    )
    assert sig.name == "save"
    assert sig.parameters[0].type_annotation == "str"
    assert sig.return_type == "bool"


def test_method_param_default_type_annotation():
    param = MethodParam(name="value")
    assert param.type_annotation == ""


def test_method_signature_defaults():
    sig = MethodSignature(name="render")
    assert sig.parameters == []
    assert sig.return_type == ""
    assert sig.is_static is False
    assert sig.is_async is False
    assert sig.docstring_snippet == ""


def test_property_record_model():
    prop = PropertyRecord(name="width", type_annotation="int", is_readonly=True)
    assert prop.name == "width"
    assert prop.type_annotation == "int"
    assert prop.is_readonly is True


def test_property_record_defaults():
    prop = PropertyRecord(name="label")
    assert prop.type_annotation == ""
    assert prop.is_readonly is False
    assert prop.docstring_snippet == ""


def test_enum_record_model():
    record = EnumRecord(
        name="FileFormat",
        members=[EnumMember(name="OBJ", value="1"), EnumMember(name="FBX", value="2")],
    )
    assert len(record.members) == 2
    assert record.members[0].name == "OBJ"
    assert record.members[1].value == "2"


def test_enum_member_default_value():
    member = EnumMember(name="UNKNOWN")
    assert member.value == ""


def test_enum_record_defaults():
    record = EnumRecord(name="Status")
    assert record.members == []
    assert record.docstring_snippet == ""


def test_api_surface_enums_default_empty():
    surface = ApiSurface(
        public_classes=[], import_allowlist=[], confidence="low"
    )
    assert surface.enums == []


def test_class_brief_backward_compat():
    """Old fields (methods, properties) still work as name lists."""
    brief = ClassBrief(
        name="Widget",
        methods=["save", "load"],
        properties=["width", "height"],
    )
    assert "save" in brief.methods
    assert "width" in brief.properties
    # typed fields default empty
    assert brief.typed_methods == []
    assert brief.typed_properties == []


def test_api_surface_with_enums():
    surface = ApiSurface(
        public_classes=["MyEnum"],
        import_allowlist=["mylib"],
        confidence="medium",
        enums=[
            EnumRecord(
                name="MyEnum",
                members=[EnumMember(name="A", value="1")],
            )
        ],
    )
    assert len(surface.enums) == 1
    assert surface.enums[0].name == "MyEnum"
