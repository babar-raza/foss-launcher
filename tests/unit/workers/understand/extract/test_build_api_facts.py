"""Tests for TC-4251: _build_api_facts handles EnumMember Pydantic models correctly.

Regression guard: before TC-4251, _build_api_facts called member.get("name", "")
on EnumMember objects (Pydantic models, not dicts), which raised AttributeError.
Fixed to use getattr(member, "name", "").
"""
from __future__ import annotations

from launcher.models.product import (
    ApiSurface,
    ClassBrief,
    EnumMember,
    EnumRecord,
    ProductIdentity,
)
from launcher.workers.understand.extract._entry import _build_api_facts


def _make_product() -> ProductIdentity:
    return ProductIdentity(
        family="cells",
        platform="python",
        display_name="TestProduct",
        canonical_import="test_pkg",
        repo_url="https://github.com/test/repo",
    )


def _make_api_surface(class_briefs: list[ClassBrief]) -> ApiSurface:
    return ApiSurface(
        public_classes=[cb.name for cb in class_briefs],
        import_allowlist=["test_pkg"],
        confidence="high",
        class_briefs=class_briefs,
    )


class TestBuildApiFactsEnumMember:
    """TC-4251: EnumMember Pydantic models must not raise AttributeError."""

    def test_enum_member_pydantic_model_no_crash(self) -> None:
        """EnumMember Pydantic model in api_surface must be handled without AttributeError.

        Regression: before TC-4251, member.get("name", "") raised AttributeError
        because EnumMember is a Pydantic model with a .name attribute, not a dict.
        """
        enum_member = EnumMember(name="XlsBinary", value="2")
        enum_record = EnumRecord(name="FileFormatType", members=[enum_member])
        class_brief = ClassBrief(name="Workbook", enums=[enum_record])
        api_surface = _make_api_surface([class_brief])
        product = _make_product()

        # Must not raise AttributeError: 'EnumMember' object has no attribute 'get'
        facts = _build_api_facts(api_surface, product)

        fact_ids = [f.fact_id for f in facts]
        assert any("FileFormatType.XlsBinary" in fid for fid in fact_ids), (
            f"Expected fact ID containing 'FileFormatType.XlsBinary' in {fact_ids}"
        )

    def test_multiple_enum_members_all_extracted(self) -> None:
        """Multiple EnumMember objects in one EnumRecord must all produce facts."""
        members = [
            EnumMember(name="Ascending", value="0"),
            EnumMember(name="Descending", value="1"),
            EnumMember(name="Natural", value="2"),
        ]
        enum_record = EnumRecord(name="SortOrder", members=members)
        class_brief = ClassBrief(name="SortOptions", enums=[enum_record])
        api_surface = _make_api_surface([class_brief])
        product = _make_product()

        facts = _build_api_facts(api_surface, product)
        fact_ids = [f.fact_id for f in facts]

        for name in ("Ascending", "Descending", "Natural"):
            assert any(f"SortOrder.{name}" in fid for fid in fact_ids), (
                f"Expected 'SortOrder.{name}' in fact IDs: {fact_ids}"
            )

    def test_empty_enum_members_no_crash(self) -> None:
        """Empty members list must produce no enum_member facts and not crash."""
        enum_record = EnumRecord(name="EmptyEnum", members=[])
        class_brief = ClassBrief(name="SomeClass", enums=[enum_record])
        api_surface = _make_api_surface([class_brief])
        product = _make_product()

        facts = _build_api_facts(api_surface, product)
        enum_facts = [f for f in facts if f.member_type == "enum_member"]
        assert enum_facts == [], f"Expected no enum member facts for empty members, got {enum_facts}"

    def test_fact_member_type_is_enum_member(self) -> None:
        """Each fact produced from EnumRecord.members must have member_type='enum_member'."""
        enum_record = EnumRecord(name="Status", members=[EnumMember(name="Active")])
        class_brief = ClassBrief(name="License", enums=[enum_record])
        api_surface = _make_api_surface([class_brief])
        product = _make_product()

        facts = _build_api_facts(api_surface, product)
        enum_facts = [f for f in facts if f.member_type == "enum_member"]

        assert len(enum_facts) == 1
        assert enum_facts[0].member_name == "Active"
        assert enum_facts[0].class_name == "Status"
        assert enum_facts[0].signature == "Status.Active"
