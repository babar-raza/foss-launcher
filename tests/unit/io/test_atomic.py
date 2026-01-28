"""Tests for atomic file operations.

Validates:
- Atomic write behavior (temp file + rename)
- Stable JSON serialization (deterministic output)
- Path validation integration
- Byte-for-byte determinism per specs/10_determinism_and_caching.md
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from launch.io.atomic import atomic_write_json, atomic_write_text
from launch.util.path_validation import PathValidationError


def test_atomic_write_text_basic(tmp_path: Path) -> None:
    """Test basic atomic text write."""
    target = tmp_path / "test.txt"
    content = "Hello, World!\n"

    atomic_write_text(target, content)

    assert target.exists()
    assert target.read_text(encoding='utf-8') == content


def test_atomic_write_text_creates_parent_dirs(tmp_path: Path) -> None:
    """Test that atomic write creates parent directories."""
    target = tmp_path / "subdir" / "nested" / "test.txt"
    content = "Test content"

    atomic_write_text(target, content)

    assert target.exists()
    assert target.read_text(encoding='utf-8') == content


def test_atomic_write_text_overwrites_existing(tmp_path: Path) -> None:
    """Test that atomic write overwrites existing files."""
    target = tmp_path / "test.txt"
    target.write_text("old content", encoding='utf-8')

    new_content = "new content"
    atomic_write_text(target, new_content)

    assert target.read_text(encoding='utf-8') == new_content


def test_atomic_write_text_no_temp_file_left(tmp_path: Path) -> None:
    """Test that no temporary file is left after write."""
    target = tmp_path / "test.txt"
    content = "Test content"

    atomic_write_text(target, content)

    # Check that no .tmp files remain
    tmp_files = list(tmp_path.glob("*.tmp"))
    assert len(tmp_files) == 0


def test_atomic_write_text_boundary_validation(tmp_path: Path) -> None:
    """Test that boundary validation is enforced."""
    boundary = tmp_path / "allowed"
    boundary.mkdir()

    # Inside boundary - should succeed
    target_inside = boundary / "test.txt"
    atomic_write_text(target_inside, "content", validate_boundary=boundary)
    assert target_inside.exists()

    # Outside boundary - should fail
    target_outside = tmp_path / "forbidden" / "test.txt"
    with pytest.raises(PathValidationError):
        atomic_write_text(target_outside, "content", validate_boundary=boundary)


def test_atomic_write_json_basic(tmp_path: Path) -> None:
    """Test basic atomic JSON write."""
    target = tmp_path / "test.json"
    data = {"key": "value", "number": 42}

    atomic_write_json(target, data)

    assert target.exists()
    loaded = json.loads(target.read_text(encoding='utf-8'))
    assert loaded == data


def test_atomic_write_json_deterministic_stable_keys(tmp_path: Path) -> None:
    """Test that JSON output is deterministic with sorted keys.

    Per specs/10_determinism_and_caching.md: stable ordering everywhere.
    """
    target1 = tmp_path / "test1.json"
    target2 = tmp_path / "test2.json"

    # Write the same data in different key order
    data1 = {"z": 3, "a": 1, "m": 2}
    data2 = {"a": 1, "m": 2, "z": 3}

    atomic_write_json(target1, data1)
    atomic_write_json(target2, data2)

    # Both files should be byte-identical
    bytes1 = target1.read_bytes()
    bytes2 = target2.read_bytes()
    assert bytes1 == bytes2


def test_atomic_write_json_stable_format(tmp_path: Path) -> None:
    """Test that JSON follows the stable format contract.

    Per specs/10_determinism_and_caching.md and taskcard:
    - sorted keys
    - 2-space indent
    - trailing newline
    - UTF-8 encoding
    - no BOM
    """
    target = tmp_path / "test.json"
    data = {"b": 2, "a": 1, "nested": {"z": 26, "y": 25}}

    atomic_write_json(target, data)

    content = target.read_text(encoding='utf-8')

    # Verify format
    assert content.endswith('\n'), "Must have trailing newline"
    assert '\t' not in content, "Must use spaces, not tabs"

    # Verify sorted keys (a before b, y before z)
    assert content.index('"a"') < content.index('"b"')
    assert content.index('"y"') < content.index('"z"')

    # Verify 2-space indent
    lines = content.split('\n')
    # Find a nested line
    nested_line = [line for line in lines if '"y"' in line][0]
    # Count leading spaces
    leading_spaces = len(nested_line) - len(nested_line.lstrip(' '))
    assert leading_spaces == 4, "Nested keys should have 4 spaces (2-space indent × 2 levels)"

    # Verify no BOM
    raw_bytes = target.read_bytes()
    assert not raw_bytes.startswith(b'\xef\xbb\xbf'), "Must not have UTF-8 BOM"


def test_atomic_write_json_byte_identical_repeat_writes(tmp_path: Path) -> None:
    """Test that writing the same data twice produces byte-identical output.

    Critical for determinism requirement (specs/10_determinism_and_caching.md).
    """
    target = tmp_path / "test.json"
    data = {
        "product": "Aspose.Words",
        "version": "24.1",
        "features": ["pdf", "docx", "html"],
        "config": {"locale": "en", "timeout": 30}
    }

    # Write once
    atomic_write_json(target, data)
    hash1 = target.read_bytes()

    # Write again
    atomic_write_json(target, data)
    hash2 = target.read_bytes()

    # Must be byte-identical
    assert hash1 == hash2


def test_atomic_write_json_unicode_no_escaping(tmp_path: Path) -> None:
    """Test that Unicode characters are not escaped (ensure_ascii=False)."""
    target = tmp_path / "test.json"
    data = {"name": "Документация", "emoji": "🚀"}

    atomic_write_json(target, data)

    content = target.read_text(encoding='utf-8')
    # Unicode should be preserved, not escaped
    assert "Документация" in content
    assert "🚀" in content
    assert "\\u" not in content


def test_atomic_write_json_empty_object(tmp_path: Path) -> None:
    """Test writing an empty JSON object."""
    target = tmp_path / "empty.json"
    data = {}

    atomic_write_json(target, data)

    content = target.read_text(encoding='utf-8')
    assert content == '{}\n'


def test_atomic_write_json_complex_nested_structure(tmp_path: Path) -> None:
    """Test that complex nested structures are deterministic."""
    target = tmp_path / "complex.json"
    data = {
        "z_last": [{"b": 2, "a": 1}, {"d": 4, "c": 3}],
        "a_first": {"nested": {"z": 26, "a": 1}},
        "m_middle": [3, 1, 2]  # arrays preserve order
    }

    atomic_write_json(target, data)

    content = target.read_text(encoding='utf-8')
    loaded = json.loads(content)

    # Verify structure preserved
    assert loaded == data

    # Verify key order (a before m before z at root)
    assert content.index('"a_first"') < content.index('"m_middle"')
    assert content.index('"m_middle"') < content.index('"z_last"')

    # Verify array order preserved
    assert loaded["m_middle"] == [3, 1, 2]


def test_atomic_write_json_boundary_validation(tmp_path: Path) -> None:
    """Test that boundary validation is enforced for JSON writes."""
    boundary = tmp_path / "allowed"
    boundary.mkdir()

    data = {"test": "data"}

    # Inside boundary - should succeed
    target_inside = boundary / "test.json"
    atomic_write_json(target_inside, data, validate_boundary=boundary)
    assert target_inside.exists()

    # Outside boundary - should fail
    target_outside = tmp_path / "forbidden" / "test.json"
    with pytest.raises(PathValidationError):
        atomic_write_json(target_outside, data, validate_boundary=boundary)
