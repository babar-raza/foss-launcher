"""Unit tests for ir_regenerate — TC-3911 (double-suffix fix).

Key assertion: slug.ir.json → slug.md  (NOT slug.ir.md).
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from launcher.shared.ir_regenerate import regenerate_from_snapshots

# Minimal valid PageIR dict (all required fields, defaults for optional).
_MINIMAL_IR = {
    "page_id": "test-page",
    "page_role": "guide",
    "title": "Test Page",
    "frontmatter": {},
    "sections": [],
}


def _write_ir(path: Path, data: dict | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data or _MINIMAL_IR), encoding="utf-8")


# ---------------------------------------------------------------------------
# Path transformation tests
# ---------------------------------------------------------------------------


def test_path_flat(tmp_path):
    """slug.ir.json must produce slug.md, NOT slug.ir.md."""
    snapshots = tmp_path / "snapshots"
    output = tmp_path / "out"
    _write_ir(snapshots / "guide.ir.json")

    with patch("launcher.shared.ir_regenerate.render_page", return_value="# Guide\n"):
        written = regenerate_from_snapshots(snapshots, output)

    assert written == [output / "guide.md"], f"Got: {written}"
    assert (output / "guide.md").exists()
    assert not (output / "guide.ir.md").exists()


def test_path_nested(tmp_path):
    """sub/dir/page.ir.json → sub/dir/page.md (directory structure preserved)."""
    snapshots = tmp_path / "snapshots"
    output = tmp_path / "out"
    _write_ir(snapshots / "sub" / "dir" / "page.ir.json")

    with patch("launcher.shared.ir_regenerate.render_page", return_value="# Page\n"):
        written = regenerate_from_snapshots(snapshots, output)

    expected = output / "sub" / "dir" / "page.md"
    assert written == [expected], f"Got: {written}"
    assert expected.exists()
    assert not (output / "sub" / "dir" / "page.ir.md").exists()


def test_multiple_files_all_transformed(tmp_path):
    """Multiple .ir.json files all get correct .md paths."""
    snapshots = tmp_path / "snapshots"
    output = tmp_path / "out"
    _write_ir(snapshots / "a.ir.json")
    _write_ir(snapshots / "sub" / "b.ir.json")

    with patch("launcher.shared.ir_regenerate.render_page", return_value="x"):
        written = regenerate_from_snapshots(snapshots, output)

    paths = {p.name for p in written}
    assert paths == {"a.md", "b.md"}
    assert not any(p.name.endswith(".ir.md") for p in written)


# ---------------------------------------------------------------------------
# Exclusion / edge-case tests
# ---------------------------------------------------------------------------


def test_non_ir_excluded(tmp_path):
    """snapshot_manifest.json (plain .json) must NOT be processed."""
    snapshots = tmp_path / "snapshots"
    snapshots.mkdir()
    (snapshots / "snapshot_manifest.json").write_text('{"version": 1}', encoding="utf-8")

    written = regenerate_from_snapshots(snapshots, tmp_path / "out")

    assert written == []
    assert not (tmp_path / "out" / "snapshot_manifest.md").exists()


def test_missing_snapshots_dir_returns_empty(tmp_path):
    """Non-existent snapshots_dir returns [] without raising."""
    written = regenerate_from_snapshots(tmp_path / "nonexistent", tmp_path / "out")
    assert written == []


def test_bad_json_skipped(tmp_path):
    """An IR file with invalid JSON is skipped; other files still processed."""
    snapshots = tmp_path / "snapshots"
    output = tmp_path / "out"
    _write_ir(snapshots / "good.ir.json")
    bad = snapshots / "bad.ir.json"
    bad.parent.mkdir(parents=True, exist_ok=True)
    bad.write_text("not valid json {{{{", encoding="utf-8")

    with patch("launcher.shared.ir_regenerate.render_page", return_value="ok"):
        written = regenerate_from_snapshots(snapshots, output)

    # Only the good file is written
    assert len(written) == 1
    assert written[0].name == "good.md"
