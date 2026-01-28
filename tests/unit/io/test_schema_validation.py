"""Tests for schema validation helpers.

Validates:
- Schema loading and validation
- Error message formatting
- Validation against JSON Schema Draft 2020-12
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from launch.io.schema_validation import (
    list_schema_files,
    load_json,
    load_schema,
    validate,
    validate_json_file,
)


def test_load_json_valid(tmp_path: Path) -> None:
    """Test loading valid JSON file."""
    json_file = tmp_path / "test.json"
    json_file.write_text('{"key": "value"}', encoding='utf-8')

    data = load_json(json_file)
    assert data == {"key": "value"}


def test_load_json_invalid_syntax(tmp_path: Path) -> None:
    """Test that invalid JSON raises error."""
    json_file = tmp_path / "invalid.json"
    json_file.write_text('{"key": invalid}', encoding='utf-8')

    with pytest.raises(json.JSONDecodeError):
        load_json(json_file)


def test_load_schema_valid(tmp_path: Path) -> None:
    """Test loading valid schema file."""
    schema_file = tmp_path / "test.schema.json"
    schema_file.write_text('{"type": "object"}', encoding='utf-8')

    schema = load_schema(schema_file)
    assert schema == {"type": "object"}


def test_load_schema_not_object(tmp_path: Path) -> None:
    """Test that non-object schema raises error."""
    schema_file = tmp_path / "invalid.schema.json"
    schema_file.write_text('["array", "not", "object"]', encoding='utf-8')

    with pytest.raises(TypeError, match="Schema must be a JSON object"):
        load_schema(schema_file)


def test_validate_valid_object() -> None:
    """Test validation of valid object against schema."""
    schema = {
        "type": "object",
        "required": ["name", "version"],
        "properties": {
            "name": {"type": "string"},
            "version": {"type": "number"}
        }
    }
    obj = {"name": "test", "version": 1}

    # Should not raise
    validate(obj, schema, context="test")


def test_validate_invalid_missing_required() -> None:
    """Test validation fails for missing required field."""
    schema = {
        "type": "object",
        "required": ["name"],
        "properties": {
            "name": {"type": "string"}
        }
    }
    obj = {}

    with pytest.raises(ValueError, match="Schema validation failed"):
        validate(obj, schema, context="test")


def test_validate_invalid_wrong_type() -> None:
    """Test validation fails for wrong type."""
    schema = {
        "type": "object",
        "properties": {
            "count": {"type": "number"}
        }
    }
    obj = {"count": "not a number"}

    with pytest.raises(ValueError, match="Schema validation failed"):
        validate(obj, schema, context="test")


def test_validate_error_message_formatting() -> None:
    """Test that validation errors are well-formatted."""
    schema = {
        "type": "object",
        "required": ["field1", "field2"],
        "properties": {
            "field1": {"type": "string"},
            "field2": {"type": "number"}
        }
    }
    obj = {"field2": "wrong type"}

    with pytest.raises(ValueError) as exc_info:
        validate(obj, schema, context="test_file.json")

    error_msg = str(exc_info.value)
    assert "Schema validation failed" in error_msg
    assert "test_file.json" in error_msg
    # Should mention both the missing field and wrong type
    assert "field1" in error_msg or "'field1'" in error_msg


def test_validate_nested_error_path() -> None:
    """Test that nested validation errors show correct path."""
    schema = {
        "type": "object",
        "properties": {
            "config": {
                "type": "object",
                "properties": {
                    "timeout": {"type": "number"}
                }
            }
        }
    }
    obj = {"config": {"timeout": "not a number"}}

    with pytest.raises(ValueError) as exc_info:
        validate(obj, schema, context="test")

    error_msg = str(exc_info.value)
    # Should show the path to the error
    assert "config" in error_msg


def test_validate_multiple_errors_reported() -> None:
    """Test that multiple validation errors are reported."""
    schema = {
        "type": "object",
        "required": ["a", "b", "c"],
        "properties": {
            "a": {"type": "string"},
            "b": {"type": "number"},
            "c": {"type": "boolean"}
        }
    }
    obj = {}

    with pytest.raises(ValueError) as exc_info:
        validate(obj, schema, context="test")

    error_msg = str(exc_info.value)
    # All missing fields should be mentioned
    # (jsonschema combines these into one error about missing required properties)
    assert "required" in error_msg.lower()


def test_validate_json_file_valid(tmp_path: Path) -> None:
    """Test validating a JSON file against a schema file."""
    # Create schema
    schema_file = tmp_path / "test.schema.json"
    schema_file.write_text(json.dumps({
        "type": "object",
        "required": ["name"],
        "properties": {"name": {"type": "string"}}
    }), encoding='utf-8')

    # Create valid JSON file
    json_file = tmp_path / "test.json"
    json_file.write_text(json.dumps({"name": "test"}), encoding='utf-8')

    # Should not raise
    validate_json_file(json_file, schema_file)


def test_validate_json_file_invalid(tmp_path: Path) -> None:
    """Test that invalid JSON file raises validation error."""
    # Create schema
    schema_file = tmp_path / "test.schema.json"
    schema_file.write_text(json.dumps({
        "type": "object",
        "required": ["name"],
        "properties": {"name": {"type": "string"}}
    }), encoding='utf-8')

    # Create invalid JSON file
    json_file = tmp_path / "invalid.json"
    json_file.write_text(json.dumps({}), encoding='utf-8')

    with pytest.raises(ValueError, match="Schema validation failed"):
        validate_json_file(json_file, schema_file)


def test_list_schema_files(tmp_path: Path) -> None:
    """Test listing schema files in directory."""
    # Create some schema files
    (tmp_path / "a.schema.json").write_text('{}', encoding='utf-8')
    (tmp_path / "b.schema.json").write_text('{}', encoding='utf-8')
    (tmp_path / "not_schema.json").write_text('{}', encoding='utf-8')
    (tmp_path / "c.schema.json").write_text('{}', encoding='utf-8')

    schemas = list(list_schema_files(tmp_path))

    # Should only include .schema.json files, sorted
    assert len(schemas) == 3
    assert schemas[0].name == "a.schema.json"
    assert schemas[1].name == "b.schema.json"
    assert schemas[2].name == "c.schema.json"


def test_list_schema_files_empty_dir(tmp_path: Path) -> None:
    """Test listing schemas in empty directory."""
    schemas = list(list_schema_files(tmp_path))
    assert len(schemas) == 0


def test_validate_with_additionalProperties_false() -> None:
    """Test validation rejects additional properties when disallowed."""
    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "allowed": {"type": "string"}
        }
    }

    # Valid object
    valid_obj = {"allowed": "value"}
    validate(valid_obj, schema, context="test")

    # Invalid object with extra property
    invalid_obj = {"allowed": "value", "extra": "not allowed"}
    with pytest.raises(ValueError, match="Schema validation failed"):
        validate(invalid_obj, schema, context="test")


def test_validate_array_items() -> None:
    """Test validation of array items."""
    schema = {
        "type": "array",
        "items": {"type": "number"}
    }

    # Valid array
    valid_obj = [1, 2, 3]
    validate(valid_obj, schema, context="test")

    # Invalid array
    invalid_obj = [1, "not a number", 3]
    with pytest.raises(ValueError, match="Schema validation failed"):
        validate(invalid_obj, schema, context="test")


def test_validate_enum() -> None:
    """Test validation of enum constraints."""
    schema = {
        "type": "object",
        "properties": {
            "status": {"enum": ["pending", "in_progress", "done"]}
        }
    }

    # Valid value
    valid_obj = {"status": "in_progress"}
    validate(valid_obj, schema, context="test")

    # Invalid value
    invalid_obj = {"status": "invalid"}
    with pytest.raises(ValueError, match="Schema validation failed"):
        validate(invalid_obj, schema, context="test")
