"""Tests for schema validation helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from launcher.io.schema_validation import (
    list_schema_files,
    load_json,
    load_schema,
    validate,
    validate_json_file,
)


@pytest.fixture
def simple_schema(tmp_path: Path) -> Path:
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "count": {"type": "integer"},
        },
        "required": ["name"],
    }
    path = tmp_path / "test.schema.json"
    path.write_text(json.dumps(schema), encoding="utf-8")
    return path


class TestLoadJson:
    def test_load_valid(self, tmp_path: Path) -> None:
        f = tmp_path / "data.json"
        f.write_text('{"key": "value"}', encoding="utf-8")
        assert load_json(f) == {"key": "value"}

    def test_load_list(self, tmp_path: Path) -> None:
        f = tmp_path / "data.json"
        f.write_text('[1, 2, 3]', encoding="utf-8")
        assert load_json(f) == [1, 2, 3]


class TestLoadSchema:
    def test_load_valid_schema(self, simple_schema: Path) -> None:
        schema = load_schema(simple_schema)
        assert "properties" in schema

    def test_non_dict_raises(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.json"
        f.write_text("[1, 2]", encoding="utf-8")
        with pytest.raises(TypeError, match="Schema must be a JSON object"):
            load_schema(f)


class TestValidate:
    def test_valid_data(self, simple_schema: Path) -> None:
        schema = load_schema(simple_schema)
        validate({"name": "test", "count": 5}, schema, context="test")

    def test_missing_required(self, simple_schema: Path) -> None:
        schema = load_schema(simple_schema)
        with pytest.raises(ValueError, match="Schema validation failed"):
            validate({"count": 5}, schema, context="test")

    def test_wrong_type(self, simple_schema: Path) -> None:
        schema = load_schema(simple_schema)
        with pytest.raises(ValueError, match="Schema validation failed"):
            validate({"name": "ok", "count": "not_int"}, schema, context="test")


class TestValidateJsonFile:
    def test_valid_file(self, tmp_path: Path, simple_schema: Path) -> None:
        data_file = tmp_path / "data.json"
        data_file.write_text('{"name": "test"}', encoding="utf-8")
        validate_json_file(data_file, simple_schema)

    def test_invalid_file(self, tmp_path: Path, simple_schema: Path) -> None:
        data_file = tmp_path / "bad.json"
        data_file.write_text('{"count": 5}', encoding="utf-8")
        with pytest.raises(ValueError, match="Schema validation failed"):
            validate_json_file(data_file, simple_schema)


class TestListSchemaFiles:
    def test_finds_schemas(self, tmp_path: Path) -> None:
        (tmp_path / "a.schema.json").write_text("{}", encoding="utf-8")
        (tmp_path / "b.schema.json").write_text("{}", encoding="utf-8")
        (tmp_path / "c.json").write_text("{}", encoding="utf-8")
        schemas = list(list_schema_files(tmp_path))
        assert len(schemas) == 2
        names = [s.name for s in schemas]
        assert "a.schema.json" in names
        assert "b.schema.json" in names

    def test_empty_dir(self, tmp_path: Path) -> None:
        assert list(list_schema_files(tmp_path)) == []
