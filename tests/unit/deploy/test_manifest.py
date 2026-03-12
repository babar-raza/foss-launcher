"""Tests for deploy manifest models and I/O."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from launcher.deploy.manifest import (
    DeployManifest,
    DeployedPage,
    load_manifest,
    save_manifest,
)
from launcher.models.evaluation import Grade


def _make_page(**overrides) -> DeployedPage:
    defaults = {
        "content_path": "docs.aspose.org/cells/python/developer-guide/installation",
        "deploy_file": "docs.aspose.org/cells/python/developer-guide/installation.md",
        "source_run_id": "run_001",
        "grade": Grade.B,
        "sha256": "a" * 64,
        "promoted_at": "2026-03-07T00:00:00+00:00",
    }
    defaults.update(overrides)
    return DeployedPage(**defaults)


class TestDeployedPage:
    def test_roundtrip(self):
        page = _make_page()
        data = page.model_dump(mode="json")
        restored = DeployedPage.model_validate(data)
        assert restored.content_path == page.content_path
        assert restored.grade == Grade.B
        assert restored.sha256 == "a" * 64


class TestDeployManifest:
    def test_empty_manifest(self):
        m = DeployManifest()
        assert m.schema_version == "1.0"
        assert m.pages == {}
        assert m.promotion_count == 0

    def test_manifest_with_pages(self):
        page = _make_page()
        m = DeployManifest(pages={"test": page})
        assert len(m.pages) == 1
        assert m.pages["test"].grade == Grade.B

    def test_manifest_is_mutable(self):
        m = DeployManifest()
        m.promotion_count = 5
        assert m.promotion_count == 5

    def test_roundtrip_json(self):
        page = _make_page()
        m = DeployManifest(pages={"k": page}, promotion_count=3, last_promotion="2026-01-01")
        data = m.model_dump(mode="json")
        restored = DeployManifest.model_validate(data)
        assert restored.promotion_count == 3
        assert restored.pages["k"].source_run_id == "run_001"


class TestLoadSaveManifest:
    def test_load_missing_file(self, tmp_path: Path):
        result = load_manifest(tmp_path / "nonexistent.json")
        assert isinstance(result, DeployManifest)
        assert result.pages == {}

    def test_save_and_load_roundtrip(self, tmp_path: Path):
        manifest_path = tmp_path / "manifest.json"
        page = _make_page()
        m = DeployManifest(pages={"install": page}, promotion_count=1)
        save_manifest(manifest_path, m)

        loaded = load_manifest(manifest_path)
        assert loaded.promotion_count == 1
        assert loaded.pages["install"].grade == Grade.B

    def test_load_corrupt_manifest(self, tmp_path: Path):
        manifest_path = tmp_path / "manifest.json"
        manifest_path.write_text("not valid json {{{", encoding="utf-8")

        result = load_manifest(manifest_path)
        assert isinstance(result, DeployManifest)
        assert result.pages == {}
        # Backup should exist
        assert (tmp_path / "manifest.json.bak").exists()

    def test_saved_manifest_is_valid_json(self, tmp_path: Path):
        manifest_path = tmp_path / "manifest.json"
        m = DeployManifest(pages={"x": _make_page()})
        save_manifest(manifest_path, m)

        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert raw["schema_version"] == "1.0"
        assert "x" in raw["pages"]

    def test_save_validates_schema(self, tmp_path: Path, monkeypatch):
        """Saving a manifest with an invalid grade value fails schema validation."""
        manifest_path = tmp_path / "manifest.json"
        m = DeployManifest(pages={"x": _make_page()})

        # Patch model_dump on the class to inject an invalid grade
        real_dump = DeployManifest.model_dump
        def _tampered_dump(self, **kwargs):
            data = real_dump(self, **kwargs)
            data["pages"]["x"]["grade"] = "X"  # invalid grade
            return data
        monkeypatch.setattr(DeployManifest, "model_dump", _tampered_dump)

        with pytest.raises(Exception):  # schema validation error
            save_manifest(manifest_path, m)
