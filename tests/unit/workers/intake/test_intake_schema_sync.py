"""SR-01: Verify IntakeBundle pydantic model stays in sync with intake_bundle.schema.json.

If a field is added to IntakeBundle but not to the schema (or vice versa), this test
catches the drift before it can cause a pipeline crash at runtime.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest


_SCHEMA_PATH = Path(__file__).parents[4] / "specs" / "schemas" / "intake_bundle.schema.json"


def _load_schema() -> dict:
    with open(_SCHEMA_PATH) as f:
        return json.load(f)


def _bundle_as_dict(**overrides) -> dict:
    from launcher.models.intake import IntakeBundle
    bundle = IntakeBundle(
        family="slides",
        platform="cpp",
        display_name="Aspose.Slides.Foss",
        canonical_import="Aspose::Slides::Foss",
        repo_url="https://github.com/test/repo",
        launch_tier="full",
        **overrides,
    )
    return bundle.model_dump()


class TestIntakeSchemaSyncDefaultValues:
    """SR-01: IntakeBundle with all-default TC-5321 fields validates against schema."""

    def test_defaults_validate_against_schema(self) -> None:
        """SR-01: Default IntakeBundle (all fields at defaults) must pass schema validation."""
        import jsonschema
        schema = _load_schema()
        data = _bundle_as_dict()
        # Should not raise
        jsonschema.validate(instance=data, schema=schema)

    def test_tc5321_fields_with_values_validate(self) -> None:
        """SR-01: TC-5321 fields set to non-default values must also pass schema validation."""
        import jsonschema
        schema = _load_schema()
        data = _bundle_as_dict(
            acquisition_confidence="high",
            import_confidence="medium",
            canonical_import_candidates=["Aspose::Slides::Foss", "Aspose::Slides"],
            repo_signals={"readme_present": True, "is_empty_clone": False},
            field_provenance={"canonical_import": "families_yaml", "display_name": "config_override"},
            is_fresh_clone=True,
        )
        jsonschema.validate(instance=data, schema=schema)

    def test_schema_rejects_unknown_top_level_field(self) -> None:
        """SR-01: schema has additionalProperties=false — unknown fields must be rejected."""
        import jsonschema
        schema = _load_schema()
        data = _bundle_as_dict()
        data["unknown_future_field_xyz"] = "should_fail"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=data, schema=schema)
