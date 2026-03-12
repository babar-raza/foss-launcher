"""Tests for specs/schemas/frontmatter.schema.json (V2AC-04)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

SCHEMA_PATH = Path(__file__).parent.parent.parent / "specs" / "schemas" / "frontmatter.schema.json"


@pytest.fixture(scope="module")
def schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


class TestFrontmatterSchemaExists:
    def test_schema_file_exists(self) -> None:
        assert SCHEMA_PATH.exists(), f"frontmatter.schema.json not found at {SCHEMA_PATH}"

    def test_schema_is_valid_json(self, schema: dict) -> None:
        assert isinstance(schema, dict)

    def test_schema_has_required_fields(self, schema: dict) -> None:
        required = schema.get("required", [])
        assert "title" in required
        assert "date" in required
        assert "lastmod" in required

    def test_schema_has_new_fields(self, schema: dict) -> None:
        properties = schema.get("properties", {})
        for field in ("date", "lastmod", "datePublished", "dateModified", "reading_time"):
            assert field in properties, f"'{field}' not in frontmatter schema properties"

    def test_date_field_has_pattern(self, schema: dict) -> None:
        date_prop = schema["properties"]["date"]
        assert "pattern" in date_prop
        import re
        pattern = re.compile(date_prop["pattern"])
        assert pattern.match("2026-03-08T12:00:00Z")
        assert not pattern.match("2026-03-08")

    def test_reading_time_is_positive_integer(self, schema: dict) -> None:
        rt_prop = schema["properties"]["reading_time"]
        assert rt_prop.get("type") == "integer"
        assert rt_prop.get("minimum", 0) >= 1

    def test_description_max_length(self, schema: dict) -> None:
        desc_prop = schema["properties"].get("description", {})
        assert desc_prop.get("maxLength", 999) <= 160

    def test_additional_properties_allowed(self, schema: dict) -> None:
        # additionalProperties must be true so Hugo custom fields aren't rejected
        assert schema.get("additionalProperties") is True
