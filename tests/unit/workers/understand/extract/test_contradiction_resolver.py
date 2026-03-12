"""Tests for _contradiction_resolver.py -- TC-HAL-01/02/03."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from launcher.models.claims import Claim
from launcher.workers.understand.extract._contradiction_resolver import resolve_contradictions


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_claim(text: str, kind: str = "api", visibility: str = "public") -> Claim:
    return Claim(
        claim_id="CLM-test-001",
        text=text,
        kind=kind,
        evidence=[],
        visibility=visibility,
        claim_source="llm",
    )


def _make_api_surface(class_briefs=None, enums=None, api_identifiers=None):
    """Build a minimal ApiSurface mock."""
    surface = MagicMock()
    surface.class_briefs = class_briefs or []
    surface.enums = enums or []
    surface.api_identifiers = api_identifiers or []
    surface.format_matrix = []
    return surface


def _make_class_brief(name: str, methods=None, properties=None, enums=None):
    brief = MagicMock()
    brief.name = name
    brief.methods = methods or []
    brief.properties = properties or []
    brief.enums = enums or []
    return brief


def _make_enum_record(name: str, members: list[str]):
    enum_rec = MagicMock()
    enum_rec.name = name
    enum_members = []
    for m in members:
        em = MagicMock()
        em.name = m
        enum_members.append(em)
    enum_rec.members = enum_members
    return enum_rec


# ---------------------------------------------------------------------------
# TC-HAL-01: Method/property type check
# ---------------------------------------------------------------------------

class TestMethodPropertyCheck:
    def test_property_as_method_downgraded(self):
        """Claim calling a property as method -> downgraded to internal."""
        brief = _make_class_brief("Node", methods=[], properties=["parent_nodes"])
        api_surface = _make_api_surface(
            class_briefs=[brief],
            api_identifiers=["Node", "parent_nodes"],
        )
        claim = _make_claim("You can call node.parent_nodes() to get parents.")
        resolved, log = resolve_contradictions([claim], api_surface)
        assert len(resolved) == 1
        assert resolved[0].visibility == "internal"
        assert any(e["type"] == "method_property_mismatch" for e in log)

    def test_method_as_method_passes(self):
        """Claim calling a method correctly -> NOT downgraded."""
        brief = _make_class_brief("Node", methods=["add_child_node"], properties=[])
        api_surface = _make_api_surface(
            class_briefs=[brief],
            api_identifiers=["Node", "add_child_node"],
        )
        claim = _make_claim("Call node.add_child_node() to add a child.")
        resolved, log = resolve_contradictions([claim], api_surface)
        assert resolved[0].visibility == "public"
        assert not any(e["type"] == "method_property_mismatch" for e in log)

    def test_property_in_both_method_and_property_passes(self):
        """If name is in both methods and properties, treat as method -> passes."""
        brief = _make_class_brief("Node", methods=["name"], properties=["name"])
        api_surface = _make_api_surface(
            class_briefs=[brief],
            api_identifiers=["Node", "name"],
        )
        claim = _make_claim("Call node.name() to get the name.")
        resolved, log = resolve_contradictions([claim], api_surface)
        assert resolved[0].visibility == "public"

    def test_no_api_surface_no_crash(self):
        """api_surface=None -> no exception, claims unchanged."""
        claim = _make_claim("Call foo.bar() to do something.")
        resolved, log = resolve_contradictions([claim], None)
        assert len(resolved) == 1
        assert resolved[0].visibility == "public"

    def test_short_name_not_flagged(self):
        """Names with len <= 2 are not flagged even if in property_ids."""
        brief = _make_class_brief("Node", methods=[], properties=["xy"])
        api_surface = _make_api_surface(class_briefs=[brief], api_identifiers=["Node", "xy"])
        claim = _make_claim("You can call node.xy() here.", kind="feature")
        resolved, log = resolve_contradictions([claim], api_surface)
        assert not any(e["type"] == "method_property_mismatch" for e in log)

    def test_empty_property_ids_no_check(self):
        """No properties defined -> check 2b never fires."""
        brief = _make_class_brief("Node", methods=["run"], properties=[])
        api_surface = _make_api_surface(class_briefs=[brief], api_identifiers=["Node", "run"])
        claim = _make_claim("Call run() to execute.")
        resolved, log = resolve_contradictions([claim], api_surface)
        assert not any(e["type"] == "method_property_mismatch" for e in log)


# ---------------------------------------------------------------------------
# TC-HAL-02: Lowercase API identifier check
# ---------------------------------------------------------------------------

class TestLowercaseApiCheck:
    def test_unknown_lowercase_api_downgraded(self):
        """api-kind claim with unknown dot-notation identifier -> downgraded."""
        api_surface = _make_api_surface(api_identifiers=["Node", "scene"])
        claim = _make_claim("Set entity.visible = True to show it.", kind="api")
        resolved, log = resolve_contradictions([claim], api_surface)
        assert resolved[0].visibility == "internal"
        assert any(e["type"] == "unknown_lowercase_api" for e in log)

    def test_known_lowercase_api_passes(self):
        """api-kind claim with known identifier -> not downgraded."""
        api_surface = _make_api_surface(api_identifiers=["Node", "scene", "visible"])
        claim = _make_claim("Set entity.visible = True to show it.", kind="api")
        resolved, log = resolve_contradictions([claim], api_surface)
        assert resolved[0].visibility == "public"

    def test_feature_kind_not_checked(self):
        """feature-kind claim with unknown dot identifier -> NOT downgraded."""
        api_surface = _make_api_surface(api_identifiers=["Node"])
        claim = _make_claim("The library supports entity.visible property.", kind="feature")
        resolved, log = resolve_contradictions([claim], api_surface)
        assert resolved[0].visibility == "public"
        assert not any(e["type"] == "unknown_lowercase_api" for e in log)

    def test_short_identifier_skipped(self):
        """api-kind claim with short (< 3 char) identifier -> skipped."""
        api_surface = _make_api_surface(api_identifiers=["Node"])
        # "id" is 2 chars -> skipped
        claim = _make_claim("Access obj.id for the identifier.", kind="api")
        resolved, log = resolve_contradictions([claim], api_surface)
        assert not any(e["type"] == "unknown_lowercase_api" for e in log)

    def test_no_api_ids_no_check(self):
        """Empty api_ids -> check 2c skipped entirely."""
        api_surface = _make_api_surface(api_identifiers=[])
        # Clear class_briefs too so api_ids stays empty
        api_surface.class_briefs = []
        claim = _make_claim("Set entity.unknown_prop = True.", kind="api")
        resolved, log = resolve_contradictions([claim], api_surface)
        assert not any(e["type"] == "unknown_lowercase_api" for e in log)

    def test_no_dot_refs_no_check(self):
        """api-kind claim with no dot notation -> not flagged."""
        api_surface = _make_api_surface(api_identifiers=["Node"])
        claim = _make_claim("Use the Node class to create scenes.", kind="api")
        resolved, log = resolve_contradictions([claim], api_surface)
        assert not any(e["type"] == "unknown_lowercase_api" for e in log)


# ---------------------------------------------------------------------------
# TC-HAL-03: Enum member verification
# ---------------------------------------------------------------------------

class TestEnumMemberCheck:
    def test_unknown_enum_member_downgraded(self):
        """Claim references FileFormat.OBJ where OBJ not in FileFormat enum -> downgraded."""
        enum_rec = _make_enum_record("FileFormat", ["FBX", "GLTF"])
        api_surface = _make_api_surface(enums=[enum_rec])
        claim = _make_claim("Use FileFormat.OBJ for OBJ format.", kind="api")
        resolved, log = resolve_contradictions([claim], api_surface)
        assert resolved[0].visibility == "internal"
        assert any(e["type"] == "enum_member_unknown" for e in log)

    def test_known_enum_member_passes(self):
        """Claim references FileFormat.FBX where FBX IS in FileFormat enum -> passes."""
        enum_rec = _make_enum_record("FileFormat", ["FBX", "GLTF"])
        api_surface = _make_api_surface(enums=[enum_rec])
        claim = _make_claim("Use FileFormat.FBX for FBX format.")
        resolved, log = resolve_contradictions([claim], api_surface)
        assert resolved[0].visibility == "public"
        assert not any(e["type"] == "enum_member_unknown" for e in log)

    def test_non_enum_class_not_checked(self):
        """ClassName.MEMBER where ClassName not in enum_member_map -> not downgraded."""
        api_surface = _make_api_surface(enums=[])  # no enums
        claim = _make_claim("Use Scene.STATIC for static scenes.")
        resolved, log = resolve_contradictions([claim], api_surface)
        assert not any(e["type"] == "enum_member_unknown" for e in log)

    def test_empty_enum_map_no_crash(self):
        """Empty enum_member_map -> no change, no crash."""
        api_surface = _make_api_surface(enums=[])
        claim = _make_claim("Use FileFormat.FBX to export.")
        resolved, log = resolve_contradictions([claim], api_surface)
        assert resolved[0].visibility == "public"

    def test_enum_in_class_briefs_also_checked(self):
        """Enum nested in class_briefs.enums is also indexed."""
        inner_enum = _make_enum_record("FileFormat", ["FBX"])
        brief = _make_class_brief("Scene", enums=[inner_enum])
        # Include FileFormat in api_identifiers so Check 2 (api_existence) does NOT fire first.
        api_surface = _make_api_surface(
            class_briefs=[brief],
            enums=[],
            api_identifiers=["FileFormat", "Scene"],
        )
        claim = _make_claim("Use FileFormat.OBJ to export.")
        resolved, log = resolve_contradictions([claim], api_surface)
        # "OBJ" not in FileFormat enum (which only has "FBX")
        assert resolved[0].visibility == "internal"
        assert any(e["type"] == "enum_member_unknown" for e in log)

    def test_none_api_surface_no_crash(self):
        """api_surface=None -> no crash."""
        claim = _make_claim("Use FileFormat.FBX for export.")
        resolved, log = resolve_contradictions([claim], None)
        assert resolved[0].visibility == "public"
        assert not any(e["type"] == "enum_member_unknown" for e in log)

    def test_enum_member_case_insensitive(self):
        """Enum member stored in mixed case is matched case-insensitively."""
        enum_rec = _make_enum_record("SaveFormat", ["Fbx", "Gltf"])
        api_surface = _make_api_surface(enums=[enum_rec])
        # The regex looks for ALL_CAPS, but the stored name is lowercased
        claim = _make_claim("Use SaveFormat.FBX for saving.")
        resolved, log = resolve_contradictions([claim], api_surface)
        # FBX -> lower = 'fbx'; enum member 'Fbx' -> lower = 'fbx' -> matches -> passes
        assert resolved[0].visibility == "public"

    def test_log_includes_known_members_sample(self):
        """Contradiction log evidence includes sample of known members."""
        enum_rec = _make_enum_record("FileFormat", ["FBX", "GLTF", "OBJ"])
        api_surface = _make_api_surface(enums=[enum_rec])
        claim = _make_claim("Use FileFormat.UNKNOWN for export.")
        resolved, log = resolve_contradictions([claim], api_surface)
        assert resolved[0].visibility == "internal"
        entry = next(e for e in log if e["type"] == "enum_member_unknown")
        assert "enum_member_map" in entry["evidence"]


# ---------------------------------------------------------------------------
# Edge cases / integration across checks
# ---------------------------------------------------------------------------

class TestResolveContradictionsGeneral:
    def test_empty_claims_list(self):
        """Empty input returns empty output, no crash."""
        resolved, log = resolve_contradictions([], None)
        assert resolved == []
        assert log == []

    def test_already_internal_claim_not_double_logged(self):
        """A claim already marked internal passes through unchanged."""
        claim = _make_claim("Some text.", visibility="internal")
        resolved, log = resolve_contradictions([claim], None)
        assert resolved[0].visibility == "internal"
        assert len(log) == 0

    def test_first_check_fires_skips_subsequent(self):
        """Once a claim is modified by an earlier check, later checks are skipped."""
        # Set up format matrix to trigger Check 1
        fmt_rec = MagicMock()
        fmt_rec.name = "FBX"
        fmt_rec.extension = ".fbx"
        fmt_rec.can_export = False
        fmt_rec.can_import = True

        # Also set up an enum that would fire Check 2d
        enum_rec = _make_enum_record("FileFormat", ["GLTF"])
        api_surface = _make_api_surface(enums=[enum_rec])
        api_surface.format_matrix = [fmt_rec]

        # This claim triggers Check 1 (FBX can_export=False) AND would trigger Check 2d
        claim = _make_claim("You can save to FBX using FileFormat.UNKNOWN.")
        resolved, log = resolve_contradictions([claim], api_surface)
        # Only one log entry (from Check 1, not Check 2d)
        assert len(log) == 1
        assert log[0]["type"] == "format_capability"
