"""Tests for ir_regenerate.py — regenerate_from_snapshots.

TC-3906-H2: comprehensive coverage.
TC-3911: double-suffix fix verified (slug.ir.json → slug.md, not slug.ir.md).
"""

from __future__ import annotations

import json
from pathlib import Path

from launcher.shared.ir_regenerate import regenerate_from_snapshots


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _minimal_page_ir(slug: str = "test-slug") -> dict:
    """Minimal valid PageIR dict with all _REQUIRED_FM_KEYS."""
    return {
        "page_id": slug,
        "page_role": "overview",
        "title": "Test Page",
        "frontmatter": {
            "title": "Test Page",
            "slug": slug,
            "type": "docs",
            "url": f"/cells/python/{slug}/",
            "weight": 10,
            "family": "cells",
            "platform": "python",
            "page_role": "overview",
        },
        "sections": [],
    }


def _write_ir(snapshots_dir: Path, content_path: str, ir_data: dict | None = None) -> Path:
    """Write a .ir.json file at snapshots_dir / (content_path + '.ir.json')."""
    ir_path = snapshots_dir / (content_path + ".ir.json")
    ir_path.parent.mkdir(parents=True, exist_ok=True)
    data = ir_data if ir_data is not None else _minimal_page_ir(content_path.split("/")[-1])
    ir_path.write_text(json.dumps(data), encoding="utf-8")
    return ir_path


# ---------------------------------------------------------------------------
# Test 1: happy path
# ---------------------------------------------------------------------------

def test_regenerate_happy_path(tmp_path):
    """Valid IR → .md written with YAML frontmatter."""
    snapshots = tmp_path / "snapshots"
    output = tmp_path / "output"
    content_path = "blog.aspose.org/overview"

    _write_ir(snapshots, content_path)

    written = regenerate_from_snapshots(snapshots, output)

    assert len(written) == 1
    md_path = output / (content_path + ".md")
    assert md_path.exists()
    content = md_path.read_text(encoding="utf-8")
    assert content.startswith("---")
    assert "title:" in content


# ---------------------------------------------------------------------------
# Test 2: path preserved verbatim (TC-3911 double-suffix fix)
# ---------------------------------------------------------------------------

def test_path_preserved_verbatim(tmp_path):
    """Deep path: slug.ir.json → slug.md (NOT slug.ir.md)."""
    snapshots = tmp_path / "snapshots"
    output = tmp_path / "output"
    content_path = "kb.aspose.org/cells/python/developer-guide/deep-slug"

    _write_ir(snapshots, content_path)

    written = regenerate_from_snapshots(snapshots, output)

    assert len(written) == 1
    expected = output / "kb.aspose.org" / "cells" / "python" / "developer-guide" / "deep-slug.md"
    assert expected in written
    assert expected.exists()
    # Verify no double-suffix artifact
    wrong = output / "kb.aspose.org" / "cells" / "python" / "developer-guide" / "deep-slug.ir.md"
    assert not wrong.exists()


# ---------------------------------------------------------------------------
# Test 3: missing snapshots dir returns empty list
# ---------------------------------------------------------------------------

def test_missing_snapshots_dir_returns_empty(tmp_path):
    """Non-existent snapshots_dir → returns [], no crash."""
    written = regenerate_from_snapshots(tmp_path / "no_such_dir", tmp_path / "output")
    assert written == []


# ---------------------------------------------------------------------------
# Test 4: corrupt IR file skipped, valid file written
# ---------------------------------------------------------------------------

def test_corrupt_ir_file_skipped(tmp_path):
    """One corrupt + one valid IR → len(written) == 1, no crash."""
    snapshots = tmp_path / "snapshots"
    output = tmp_path / "output"

    # Valid IR
    _write_ir(snapshots, "blog.x.org/valid")

    # Corrupt IR (invalid JSON)
    bad_path = snapshots / "blog.x.org" / "bad.ir.json"
    bad_path.parent.mkdir(parents=True, exist_ok=True)
    bad_path.write_text("NOT_JSON{{{{", encoding="utf-8")

    written = regenerate_from_snapshots(snapshots, output)

    assert len(written) == 1
    assert (output / "blog.x.org" / "valid.md").exists()
    assert not (output / "blog.x.org" / "bad.md").exists()


# ---------------------------------------------------------------------------
# Test 5: FrontmatterError skipped, remaining pages written
# ---------------------------------------------------------------------------

def test_frontmatter_error_skipped(tmp_path):
    """IR with None frontmatter value → FrontmatterError → skipped."""
    snapshots = tmp_path / "snapshots"
    output = tmp_path / "output"

    # Valid IR
    _write_ir(snapshots, "blog.x.org/good")

    # IR with None value in frontmatter → render_page raises FrontmatterError
    bad_fm_ir = _minimal_page_ir("bad")
    bad_fm_ir["frontmatter"]["title"] = None   # None triggers FrontmatterError
    _write_ir(snapshots, "blog.x.org/bad", bad_fm_ir)

    written = regenerate_from_snapshots(snapshots, output)

    assert len(written) == 1
    assert (output / "blog.x.org" / "good.md").exists()
    assert not (output / "blog.x.org" / "bad.md").exists()


# ---------------------------------------------------------------------------
# Test 6: snapshot_manifest.json not processed
# ---------------------------------------------------------------------------

def test_snapshot_manifest_json_not_processed(tmp_path):
    """snapshot_manifest.json is NOT matched by *.ir.json glob — not output as .md."""
    snapshots = tmp_path / "snapshots"
    output = tmp_path / "output"
    snapshots.mkdir(parents=True, exist_ok=True)

    # Place a snapshot_manifest.json (plain .json extension, not .ir.json)
    (snapshots / "snapshot_manifest.json").write_text('{"schema_version":"1.0","pages":{}}', encoding="utf-8")

    # Also one valid IR so we confirm the function runs
    _write_ir(snapshots, "blog.x.org/real")

    written = regenerate_from_snapshots(snapshots, output)

    assert len(written) == 1
    assert not (output / "snapshot_manifest.md").exists()


# ---------------------------------------------------------------------------
# Test 7: return value contains absolute paths
# ---------------------------------------------------------------------------

def test_returns_list_of_written_paths(tmp_path):
    """Return value contains absolute Path objects for written .md files."""
    snapshots = tmp_path / "snapshots"
    output = tmp_path / "output"
    _write_ir(snapshots, "blog.x.org/page1")
    _write_ir(snapshots, "blog.x.org/page2")

    written = regenerate_from_snapshots(snapshots, output)

    assert len(written) == 2
    for p in written:
        assert isinstance(p, Path)
        assert p.is_absolute()
        assert p.suffix == ".md"
        assert p.exists()
