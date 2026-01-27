"""Tests for YAML I/O operations.

Validates:
- Safe YAML loading
- YAML dumping with proper formatting
- Error handling for invalid YAML
"""

from __future__ import annotations

from pathlib import Path

import pytest

from launch.io.yamlio import dump_yaml, load_yaml


def test_load_yaml_basic(tmp_path: Path) -> None:
    """Test loading basic YAML file."""
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text("""
key: value
number: 42
""", encoding='utf-8')

    data = load_yaml(yaml_file)

    assert data == {"key": "value", "number": 42}


def test_load_yaml_nested(tmp_path: Path) -> None:
    """Test loading nested YAML structure."""
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text("""
root:
  nested:
    key: value
  list:
    - item1
    - item2
""", encoding='utf-8')

    data = load_yaml(yaml_file)

    assert data["root"]["nested"]["key"] == "value"
    assert data["root"]["list"] == ["item1", "item2"]


def test_load_yaml_empty_file(tmp_path: Path) -> None:
    """Test that empty YAML file returns empty dict."""
    yaml_file = tmp_path / "empty.yaml"
    yaml_file.write_text("", encoding='utf-8')

    data = load_yaml(yaml_file)

    assert data == {}


def test_load_yaml_null_content(tmp_path: Path) -> None:
    """Test that YAML file with null returns empty dict."""
    yaml_file = tmp_path / "null.yaml"
    yaml_file.write_text("null\n", encoding='utf-8')

    data = load_yaml(yaml_file)

    assert data == {}


def test_load_yaml_not_object(tmp_path: Path) -> None:
    """Test that YAML with non-object root raises TypeError."""
    yaml_file = tmp_path / "list.yaml"
    yaml_file.write_text("- item1\n- item2\n", encoding='utf-8')

    with pytest.raises(TypeError, match="Expected YAML mapping/object at root"):
        load_yaml(yaml_file)


def test_load_yaml_invalid_syntax(tmp_path: Path) -> None:
    """Test that invalid YAML syntax raises error."""
    yaml_file = tmp_path / "invalid.yaml"
    yaml_file.write_text("invalid: yaml: syntax:\n  bad\n", encoding='utf-8')

    with pytest.raises(Exception):  # yaml.YAMLError or similar
        load_yaml(yaml_file)


def test_load_yaml_preserves_types(tmp_path: Path) -> None:
    """Test that YAML types are preserved."""
    yaml_file = tmp_path / "types.yaml"
    yaml_file.write_text("""
string: "text"
number: 42
float: 3.14
bool: true
null_value: null
list: [1, 2, 3]
""", encoding='utf-8')

    data = load_yaml(yaml_file)

    assert isinstance(data["string"], str)
    assert isinstance(data["number"], int)
    assert isinstance(data["float"], float)
    assert isinstance(data["bool"], bool)
    assert data["null_value"] is None
    assert isinstance(data["list"], list)


def test_dump_yaml_basic() -> None:
    """Test dumping basic YAML."""
    data = {"key": "value", "number": 42}

    yaml_str = dump_yaml(data)

    assert "key: value" in yaml_str
    assert "number: 42" in yaml_str


def test_dump_yaml_nested() -> None:
    """Test dumping nested YAML structure."""
    data = {
        "root": {
            "nested": {"key": "value"},
            "list": ["item1", "item2"]
        }
    }

    yaml_str = dump_yaml(data)

    # Should be valid YAML
    assert "root:" in yaml_str
    assert "nested:" in yaml_str
    assert "key: value" in yaml_str


def test_dump_yaml_unicode() -> None:
    """Test that Unicode is preserved in YAML dump."""
    data = {"message": "Привет мир", "emoji": "🚀"}

    yaml_str = dump_yaml(data)

    # Unicode should be preserved (allow_unicode=True)
    assert "Привет мир" in yaml_str
    assert "🚀" in yaml_str


def test_dump_yaml_preserves_order() -> None:
    """Test that YAML dump preserves insertion order (not sorted).

    Note: This uses sort_keys=False per the implementation.
    """
    data = {"z": 1, "a": 2, "m": 3}

    yaml_str = dump_yaml(data)

    # Order should be preserved (z, a, m)
    z_pos = yaml_str.index("z:")
    a_pos = yaml_str.index("a:")
    m_pos = yaml_str.index("m:")

    assert z_pos < a_pos < m_pos


def test_dump_yaml_lists() -> None:
    """Test dumping lists in YAML."""
    data = {"items": ["first", "second", "third"]}

    yaml_str = dump_yaml(data)

    assert "items:" in yaml_str
    assert "- first" in yaml_str
    assert "- second" in yaml_str
    assert "- third" in yaml_str


def test_dump_yaml_empty_dict() -> None:
    """Test dumping empty dict."""
    data = {}

    yaml_str = dump_yaml(data)

    assert yaml_str.strip() == "{}"


def test_load_yaml_multiline_string(tmp_path: Path) -> None:
    """Test loading YAML with multiline string."""
    yaml_file = tmp_path / "multiline.yaml"
    yaml_file.write_text("""
description: |
  This is a multiline
  string in YAML
  that should be preserved.
""", encoding='utf-8')

    data = load_yaml(yaml_file)

    assert "This is a multiline" in data["description"]
    assert "string in YAML" in data["description"]
