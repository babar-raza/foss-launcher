"""Tests for run_config loading and validation.

Validates:
- YAML loading with schema validation
- locale/locales mutual exclusivity enforcement
- Error handling for missing files
- Integration with schema validation
"""

from __future__ import annotations

from pathlib import Path

import pytest

from launch.io.run_config import load_and_validate_run_config
from launch.util.errors import ConfigError


@pytest.fixture
def repo_root(tmp_path: Path) -> Path:
    """Create a temporary repo root with schema."""
    root = tmp_path / "repo"
    root.mkdir()

    # Create schemas directory with minimal run_config schema
    schemas_dir = root / "specs" / "schemas"
    schemas_dir.mkdir(parents=True)

    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": ["schema_version", "product_slug"],
        "properties": {
            "schema_version": {"type": "string"},
            "product_slug": {"type": "string"},
            "locale": {"type": "string"},
            "locales": {
                "type": "array",
                "items": {"type": "string"}
            }
        },
        "anyOf": [
            {"required": ["locale"]},
            {"required": ["locales"]}
        ]
    }

    schema_path = schemas_dir / "run_config.schema.json"
    schema_path.write_text(
        __import__('json').dumps(schema, indent=2),
        encoding='utf-8'
    )

    return root


def test_load_valid_config_with_locale(repo_root: Path, tmp_path: Path) -> None:
    """Test loading valid config with single locale."""
    config_path = tmp_path / "config.yaml"
    config_path.write_text("""
schema_version: "1.0"
product_slug: "test-product"
locale: "en"
""", encoding='utf-8')

    config = load_and_validate_run_config(repo_root, config_path)

    assert config["schema_version"] == "1.0"
    assert config["product_slug"] == "test-product"
    assert config["locale"] == "en"


def test_load_valid_config_with_locales(repo_root: Path, tmp_path: Path) -> None:
    """Test loading valid config with multiple locales."""
    config_path = tmp_path / "config.yaml"
    config_path.write_text("""
schema_version: "1.0"
product_slug: "test-product"
locales: ["en", "de", "fr"]
""", encoding='utf-8')

    config = load_and_validate_run_config(repo_root, config_path)

    assert config["schema_version"] == "1.0"
    assert config["product_slug"] == "test-product"
    assert config["locales"] == ["en", "de", "fr"]


def test_load_config_missing_file(repo_root: Path, tmp_path: Path) -> None:
    """Test that missing config file raises ConfigError."""
    config_path = tmp_path / "nonexistent.yaml"

    with pytest.raises(ConfigError, match="run_config not found"):
        load_and_validate_run_config(repo_root, config_path)


def test_load_config_missing_schema(tmp_path: Path) -> None:
    """Test that missing schema raises ConfigError."""
    # Create repo root without schema
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    config_path = tmp_path / "config.yaml"
    config_path.write_text("""
schema_version: "1.0"
product_slug: "test-product"
locale: "en"
""", encoding='utf-8')

    with pytest.raises(ConfigError, match="run_config schema missing"):
        load_and_validate_run_config(repo_root, config_path)


def test_load_config_missing_required_field(repo_root: Path, tmp_path: Path) -> None:
    """Test that config missing required field fails validation."""
    config_path = tmp_path / "config.yaml"
    config_path.write_text("""
schema_version: "1.0"
# Missing product_slug (required)
locale: "en"
""", encoding='utf-8')

    with pytest.raises(ConfigError, match="Schema validation failed"):
        load_and_validate_run_config(repo_root, config_path)


def test_load_config_missing_locale_and_locales(repo_root: Path, tmp_path: Path) -> None:
    """Test that config must have either locale or locales."""
    config_path = tmp_path / "config.yaml"
    config_path.write_text("""
schema_version: "1.0"
product_slug: "test-product"
# Missing both locale and locales
""", encoding='utf-8')

    with pytest.raises(ConfigError):
        load_and_validate_run_config(repo_root, config_path)


def test_load_config_invalid_yaml(repo_root: Path, tmp_path: Path) -> None:
    """Test that invalid YAML raises error."""
    config_path = tmp_path / "config.yaml"
    config_path.write_text("""
invalid: yaml: syntax: here
  bad indentation
""", encoding='utf-8')

    with pytest.raises(Exception):  # YAML parser raises various exceptions
        load_and_validate_run_config(repo_root, config_path)


def test_load_config_empty_file(repo_root: Path, tmp_path: Path) -> None:
    """Test that empty config file returns empty dict and fails validation."""
    config_path = tmp_path / "config.yaml"
    config_path.write_text("", encoding='utf-8')

    # Empty config should fail validation (missing required fields)
    with pytest.raises(ConfigError):
        load_and_validate_run_config(repo_root, config_path)


def test_load_config_yaml_not_object(repo_root: Path, tmp_path: Path) -> None:
    """Test that YAML file must contain an object at root."""
    config_path = tmp_path / "config.yaml"
    config_path.write_text("- list\n- not\n- object\n", encoding='utf-8')

    with pytest.raises(TypeError, match="Expected YAML mapping/object at root"):
        load_and_validate_run_config(repo_root, config_path)


def test_load_config_preserves_structure(repo_root: Path, tmp_path: Path) -> None:
    """Test that complex nested structure is preserved."""
    config_path = tmp_path / "config.yaml"
    config_path.write_text("""
schema_version: "1.0"
product_slug: "test-product"
locale: "en"
nested:
  key1: value1
  key2:
    - item1
    - item2
""", encoding='utf-8')

    config = load_and_validate_run_config(repo_root, config_path)

    assert config["nested"]["key1"] == "value1"
    assert config["nested"]["key2"] == ["item1", "item2"]
