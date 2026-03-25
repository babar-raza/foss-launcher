"""Tests for snapshot_manifest.py — SnapshotManifest, load, save.

TC-3906-H2: comprehensive test coverage.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from launcher.deploy.snapshot_manifest import (
    SnapshotIREntry,
    SnapshotManifest,
    load_snapshot_manifest,
    save_snapshot_manifest,
)
from launcher.models.evaluation import Grade


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _valid_entry(content_path: str = "sub.x.org/slug") -> SnapshotIREntry:
    return SnapshotIREntry(
        content_path=content_path,
        snapshot_file=content_path + ".ir.json",
        source_run_id="run-001",
        grade=Grade.B,
        sha256="a" * 64,
        promoted_at="2026-01-01T00:00:00+00:00",
    )


# ---------------------------------------------------------------------------
# Test 1: defaults
# ---------------------------------------------------------------------------

def test_empty_manifest_defaults():
    m = SnapshotManifest()
    assert m.schema_version == "1.1"  # TC-FIX-215: bumped for quality-weighted fields
    assert m.pages == {}
    assert m.majority_run_id == ""
    assert m.majority_run_ir_count == 0
    assert m.majority_run_quality_score == 0.0  # TC-FIX-215
    assert m.run_ir_counts == {}
    assert m.run_quality_scores == {}  # TC-FIX-215
    assert m.last_promotion == ""
    assert m.promotion_count == 0


# ---------------------------------------------------------------------------
# Test 2: save and load roundtrip
# ---------------------------------------------------------------------------

def test_save_and_load_roundtrip(tmp_path):
    m = SnapshotManifest(
        majority_run_id="run-42",
        majority_run_ir_count=7,
        run_ir_counts={"run-42": 7},
        last_promotion="2026-03-09T12:00:00+00:00",
        promotion_count=3,
    )
    entry = _valid_entry("kb.aspose.org/cells/python/overview")
    m.pages["kb.aspose.org/cells/python/overview"] = entry

    path = tmp_path / "snapshot_manifest.json"
    save_snapshot_manifest(path, m)
    assert path.exists()

    loaded = load_snapshot_manifest(path)
    assert loaded.majority_run_id == "run-42"
    assert loaded.majority_run_ir_count == 7
    assert loaded.run_ir_counts == {"run-42": 7}
    assert loaded.promotion_count == 3
    assert "kb.aspose.org/cells/python/overview" in loaded.pages
    assert loaded.pages["kb.aspose.org/cells/python/overview"].grade == Grade.B


# ---------------------------------------------------------------------------
# Test 3: missing file returns empty
# ---------------------------------------------------------------------------

def test_load_missing_file_returns_empty(tmp_path):
    path = tmp_path / "does_not_exist.json"
    m = load_snapshot_manifest(path)
    assert m == SnapshotManifest()


# ---------------------------------------------------------------------------
# Test 4: corrupt file backs up and returns empty
# ---------------------------------------------------------------------------

def test_load_corrupt_file_backs_up_and_returns_empty(tmp_path):
    path = tmp_path / "snapshot_manifest.json"
    path.write_text("THIS IS NOT JSON {{{", encoding="utf-8")

    m = load_snapshot_manifest(path)

    assert m == SnapshotManifest()
    # Original gone, backup created
    assert not path.exists()
    bak = path.with_suffix(".json.bak")
    assert bak.exists()
    assert bak.read_text(encoding="utf-8") == "THIS IS NOT JSON {{{"


# ---------------------------------------------------------------------------
# Test 5: save validates schema — valid manifest works
# ---------------------------------------------------------------------------

def test_save_validates_schema_valid(tmp_path):
    """Saving a valid manifest does not raise."""
    m = SnapshotManifest()
    m.pages["blog.x.org/slug"] = _valid_entry("blog.x.org/slug")
    path = tmp_path / "snapshot_manifest.json"
    save_snapshot_manifest(path, m)  # must not raise
    assert path.exists()


# ---------------------------------------------------------------------------
# Test 6: invalid sha256 rejected by schema validation on save
# ---------------------------------------------------------------------------

def test_snapshot_ir_entry_sha256_pattern(tmp_path):
    """Saving a manifest with invalid sha256 raises (schema pattern ^[a-f0-9]{64}$)."""
    m = SnapshotManifest()
    m.pages["blog.x.org/slug"] = SnapshotIREntry(
        content_path="blog.x.org/slug",
        snapshot_file="blog.x.org/slug.ir.json",
        source_run_id="run-001",
        grade=Grade.A,
        sha256="NOT_VALID_HEX",   # fails schema pattern
        promoted_at="2026-01-01T00:00:00+00:00",
    )
    path = tmp_path / "snapshot_manifest.json"
    with pytest.raises(Exception):
        save_snapshot_manifest(path, m)
