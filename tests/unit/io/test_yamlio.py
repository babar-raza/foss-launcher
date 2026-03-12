"""Tests for YAML I/O operations."""

from __future__ import annotations

from pathlib import Path

import pytest

from launcher.io.yamlio import dump_yaml, load_yaml


def test_load_yaml_basic(tmp_path: Path) -> None:
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text("key: value\ncount: 42\n", encoding="utf-8")
    result = load_yaml(yaml_file)
    assert result == {"key": "value", "count": 42}


def test_load_yaml_empty_returns_empty_dict(tmp_path: Path) -> None:
    yaml_file = tmp_path / "empty.yaml"
    yaml_file.write_text("", encoding="utf-8")
    assert load_yaml(yaml_file) == {}


def test_load_yaml_null_returns_empty_dict(tmp_path: Path) -> None:
    yaml_file = tmp_path / "null.yaml"
    yaml_file.write_text("null\n", encoding="utf-8")
    assert load_yaml(yaml_file) == {}


def test_load_yaml_non_dict_raises(tmp_path: Path) -> None:
    yaml_file = tmp_path / "list.yaml"
    yaml_file.write_text("- one\n- two\n", encoding="utf-8")
    with pytest.raises(TypeError, match="Expected YAML mapping"):
        load_yaml(yaml_file)


def test_load_yaml_nested(tmp_path: Path) -> None:
    yaml_file = tmp_path / "nested.yaml"
    yaml_file.write_text("parent:\n  child: value\n", encoding="utf-8")
    result = load_yaml(yaml_file)
    assert result == {"parent": {"child": "value"}}


def test_dump_yaml_basic() -> None:
    data = {"key": "value", "count": 42}
    result = dump_yaml(data)
    assert "key: value" in result
    assert "count: 42" in result


def test_dump_yaml_roundtrip(tmp_path: Path) -> None:
    data = {"name": "test", "items": [1, 2, 3], "nested": {"a": "b"}}
    yaml_file = tmp_path / "rt.yaml"
    yaml_file.write_text(dump_yaml(data), encoding="utf-8")
    loaded = load_yaml(yaml_file)
    assert loaded == data
