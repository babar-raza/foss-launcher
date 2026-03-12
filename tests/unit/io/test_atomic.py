"""Tests for atomic file operations."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from launcher.io.atomic import atomic_write_json, atomic_write_text


class TestAtomicWriteText:
    def test_basic_write(self, tmp_path: Path) -> None:
        target = tmp_path / "test.txt"
        atomic_write_text(target, "hello world")
        assert target.read_text(encoding="utf-8") == "hello world"

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        target = tmp_path / "sub" / "dir" / "test.txt"
        atomic_write_text(target, "deep")
        assert target.read_text(encoding="utf-8") == "deep"

    def test_overwrites_existing(self, tmp_path: Path) -> None:
        target = tmp_path / "test.txt"
        target.write_text("old", encoding="utf-8")
        atomic_write_text(target, "new")
        assert target.read_text(encoding="utf-8") == "new"

    def test_rejects_path_traversal(self, tmp_path: Path) -> None:
        bad_path = tmp_path / ".." / "escape.txt"
        with pytest.raises(ValueError, match="Path traversal"):
            atomic_write_text(bad_path, "malicious")

    def test_boundary_enforcement(self, tmp_path: Path) -> None:
        boundary = tmp_path / "allowed"
        boundary.mkdir()
        target = boundary / "ok.txt"
        atomic_write_text(target, "in boundary", validate_boundary=boundary)
        assert target.exists()

    def test_boundary_rejection(self, tmp_path: Path) -> None:
        boundary = tmp_path / "allowed"
        boundary.mkdir()
        outside = tmp_path / "forbidden" / "bad.txt"
        with pytest.raises(ValueError, match="outside boundary"):
            atomic_write_text(outside, "escape", validate_boundary=boundary)

    def test_no_tmp_file_left_on_success(self, tmp_path: Path) -> None:
        target = tmp_path / "test.txt"
        atomic_write_text(target, "clean")
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert len(tmp_files) == 0


class TestAtomicWriteJson:
    def test_basic_write(self, tmp_path: Path) -> None:
        target = tmp_path / "test.json"
        data = {"key": "value", "number": 42}
        atomic_write_json(target, data)
        loaded = json.loads(target.read_text(encoding="utf-8"))
        assert loaded == data

    def test_deterministic_output(self, tmp_path: Path) -> None:
        """sort_keys=True ensures deterministic JSON output."""
        data = {"z": 1, "a": 2, "m": 3}
        f1 = tmp_path / "a.json"
        f2 = tmp_path / "b.json"
        atomic_write_json(f1, data)
        atomic_write_json(f2, data)
        assert f1.read_bytes() == f2.read_bytes()

    def test_sorted_keys(self, tmp_path: Path) -> None:
        target = tmp_path / "sorted.json"
        atomic_write_json(target, {"z": 1, "a": 2})
        content = target.read_text(encoding="utf-8")
        assert content.index('"a"') < content.index('"z"')

    def test_rejects_path_traversal(self, tmp_path: Path) -> None:
        bad_path = tmp_path / ".." / "escape.json"
        with pytest.raises(ValueError, match="Path traversal"):
            atomic_write_json(bad_path, {"bad": True})
