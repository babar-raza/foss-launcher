"""Tests for state store library (TC-3010, TC-3060, TC-3070)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from launch.state_store import (
    find_artifact_set,
    get_store_key,
    get_store_root,
    hydrate_run_dir,
    list_available_shas,
    publish_run_artifacts,
    publish_worker_artifacts,
    read_provenance,
    write_provenance,
)
from launch.state_store.store import StoreConflictError, _safe_copy_file


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


class TestGetStoreRoot:
    def test_default(self) -> None:
        root = get_store_root({})
        assert root == Path(".foss_state")

    def test_custom(self) -> None:
        root = get_store_root({"autopilot": {"state_store_root": "/custom/path"}})
        assert root == Path("/custom/path")

    def test_empty_custom_uses_default(self) -> None:
        root = get_store_root({"autopilot": {"state_store_root": ""}})
        assert root == Path(".foss_state")


class TestGetStoreKey:
    def test_basic(self) -> None:
        config = {
            "family": "3d",
            "target_platform": "python",
            "product_slug": "aspose-3d-python",
        }
        key = get_store_key(config)
        assert key == Path("3d/python")

    def test_missing_fields(self) -> None:
        key = get_store_key({})
        assert key == Path("unknown/unknown")


class TestListAvailableShas:
    def test_no_store_dir(self, tmp_path: Path) -> None:
        assert list_available_shas(tmp_path, Path("x/y/z")) == []

    def test_with_shas(self, tmp_path: Path) -> None:
        key = Path("fam/plat/slug")
        (tmp_path / key / "artifacts" / "sha_bbb").mkdir(parents=True)
        (tmp_path / key / "artifacts" / "sha_aaa").mkdir(parents=True)
        result = list_available_shas(tmp_path, key)
        assert result == ["sha_aaa", "sha_bbb"]  # sorted


class TestFindArtifactSet:
    def test_not_found(self, tmp_path: Path) -> None:
        assert find_artifact_set(tmp_path, Path("x"), "sha1") is None

    def test_found_with_worker_dir(self, tmp_path: Path) -> None:
        key = Path("fam/plat/slug")
        sha_dir = tmp_path / key / "artifacts" / "sha1" / "w1"
        sha_dir.mkdir(parents=True)
        _write_json(sha_dir / "repo_inventory.json", {"test": True})
        result = find_artifact_set(tmp_path, key, "sha1")
        assert result is not None
        assert result.name == "sha1"

    def test_found_with_w5_dir(self, tmp_path: Path) -> None:
        """find_artifact_set recognizes W5 worker dir (TC-3060)."""
        key = Path("fam/plat")
        sha_dir = tmp_path / key / "artifacts" / "sha1" / "w5"
        sha_dir.mkdir(parents=True)
        _write_json(sha_dir / "draft_manifest.json", {"pages": []})
        result = find_artifact_set(tmp_path, key, "sha1")
        assert result is not None

    def test_empty_sha_dir_returns_none(self, tmp_path: Path) -> None:
        key = Path("fam/plat/slug")
        (tmp_path / key / "artifacts" / "sha1").mkdir(parents=True)
        assert find_artifact_set(tmp_path, key, "sha1") is None


class TestPublishWorkerArtifacts:
    def test_publish_json_files(self, tmp_path: Path) -> None:
        store_root = tmp_path / "store"
        key = Path("fam/plat/slug")
        src = tmp_path / "src_artifacts"
        src.mkdir()
        _write_json(src / "repo_inventory.json", {"schema_version": "1.0"})
        _write_json(src / "other.json", {"data": True})

        count = publish_worker_artifacts(store_root, key, "sha1", "w1", src)
        assert count == 2
        assert (
            store_root / key / "artifacts" / "sha1" / "w1" / "repo_inventory.json"
        ).exists()

    def test_skip_non_publishable_worker(self, tmp_path: Path) -> None:
        count = publish_worker_artifacts(tmp_path, Path("k"), "sha", "w10", tmp_path)
        assert count == 0

    def test_w5_publishable(self, tmp_path: Path) -> None:
        """W5 is now publishable (TC-3060)."""
        store_root = tmp_path / "store"
        key = Path("fam/plat")
        src = tmp_path / "src_artifacts"
        src.mkdir()
        _write_json(src / "draft_manifest.json", {"pages": []})
        count = publish_worker_artifacts(store_root, key, "sha1", "w5", src)
        assert count == 1
        assert (
            store_root / key / "artifacts" / "sha1" / "w5" / "draft_manifest.json"
        ).exists()

    def test_w8_publishable(self, tmp_path: Path) -> None:
        """W8 is now publishable (TC-3060)."""
        store_root = tmp_path / "store"
        key = Path("fam/plat")
        src = tmp_path / "src_artifacts"
        src.mkdir()
        _write_json(src / "patch_bundle.json", {"patches": []})
        count = publish_worker_artifacts(store_root, key, "sha1", "w8", src)
        assert count == 1

    def test_w9_publishable(self, tmp_path: Path) -> None:
        """W9 is now publishable (TC-3060)."""
        store_root = tmp_path / "store"
        key = Path("fam/plat")
        src = tmp_path / "src_artifacts"
        src.mkdir()
        _write_json(src / "validation_report.json", {"gates": []})
        count = publish_worker_artifacts(store_root, key, "sha1", "w9", src)
        assert count == 1

    def test_w6_w7_w10_w11_not_publishable(self, tmp_path: Path) -> None:
        """W6/W7/W10/W11 remain non-publishable (TC-3060)."""
        for worker in ("w6", "w7", "w10", "w11"):
            count = publish_worker_artifacts(
                tmp_path, Path("k"), "sha", worker, tmp_path
            )
            assert count == 0, f"{worker} should not be publishable"


class TestPublishRunArtifacts:
    def test_publish_maps_to_workers(self, tmp_path: Path) -> None:
        """publish_run_artifacts publishes only W5/W8/W9 to legacy layout (TC-3250).

        W1 artifacts go to the RAW layer (publish_raw_artifacts).
        W2/W3/W4 artifacts go to the DERIVED layer (publish_derived_artifacts).
        """
        store_root = tmp_path / "store"
        key = Path("fam/plat/slug")
        run_dir = tmp_path / "run"
        arts = run_dir / "artifacts"
        arts.mkdir(parents=True)
        _write_json(arts / "repo_inventory.json", {"schema_version": "1.0"})
        _write_json(arts / "product_facts.json", {"schema_version": "1.0"})
        _write_json(arts / "page_plan.json", {"schema_version": "1.0"})
        # W9 artifact — still published via legacy layout
        _write_json(arts / "validation_report.json", {"gates": []})

        count = publish_run_artifacts(store_root, key, "sha1", run_dir)
        assert count == 1  # only W9 — W1/W2/W4 are handled by new two-layer publishers
        assert (
            store_root / key / "artifacts" / "sha1" / "w9" / "validation_report.json"
        ).exists()
        # W1/W2/W4 NOT in legacy layout (handled by raw/derived layers)
        assert not (
            store_root / key / "artifacts" / "sha1" / "w1" / "repo_inventory.json"
        ).exists()
        assert not (
            store_root / key / "artifacts" / "sha1" / "w2" / "product_facts.json"
        ).exists()
        assert not (
            store_root / key / "artifacts" / "sha1" / "w4" / "page_plan.json"
        ).exists()
        # Manifest updated
        manifest = json.loads(
            (store_root / key / "manifest.json").read_text(encoding="utf-8")
        )
        assert manifest["best_sha"] == "sha1"

    def test_publish_w5_w8_artifacts(self, tmp_path: Path) -> None:
        """W5 and W8 artifacts are published via publish_run_artifacts (TC-3060)."""
        store_root = tmp_path / "store"
        key = Path("fam/plat")
        run_dir = tmp_path / "run"
        arts = run_dir / "artifacts"
        arts.mkdir(parents=True)
        _write_json(arts / "draft_manifest.json", {"pages": []})
        _write_json(arts / "patch_bundle.json", {"patches": []})

        count = publish_run_artifacts(store_root, key, "sha1", run_dir)
        assert count == 2
        assert (
            store_root / key / "artifacts" / "sha1" / "w5" / "draft_manifest.json"
        ).exists()
        assert (
            store_root / key / "artifacts" / "sha1" / "w8" / "patch_bundle.json"
        ).exists()

    def test_publish_w2_w3_skipped_in_legacy_function(self, tmp_path: Path) -> None:
        """W2/W3 artifacts are NOT published by publish_run_artifacts (TC-3250).

        These go to the DERIVED layer via publish_derived_artifacts.
        """
        store_root = tmp_path / "store"
        key = Path("fam/plat")
        run_dir = tmp_path / "run"
        arts = run_dir / "artifacts"
        arts.mkdir(parents=True)
        _write_json(arts / "code_analysis.json", {"classes": []})
        _write_json(arts / "code_understanding.json", {"profiles": []})
        _write_json(arts / "code_snippets.json", {"snippets": []})
        _write_json(arts / "doc_snippets.json", {"snippets": []})

        count = publish_run_artifacts(store_root, key, "sha1", run_dir)
        assert count == 0  # W2/W3 are now DERIVED layer — not handled here
        assert not (
            store_root / key / "artifacts" / "sha1" / "w2" / "code_analysis.json"
        ).exists()
        assert not (
            store_root / key / "artifacts" / "sha1" / "w3" / "code_snippets.json"
        ).exists()


class TestCollisionDetection:
    def test_identical_content_ok(self, tmp_path: Path) -> None:
        src = tmp_path / "src.json"
        dst = tmp_path / "dst.json"
        src.write_text('{"a":1}', encoding="utf-8")
        dst.write_text('{"a":1}', encoding="utf-8")
        _safe_copy_file(src, dst, tmp_path / "conflicts")  # Should not raise

    def test_different_content_raises(self, tmp_path: Path) -> None:
        src = tmp_path / "src.json"
        dst = tmp_path / "out" / "src.json"
        dst.parent.mkdir()
        src.write_text('{"a":1}', encoding="utf-8")
        dst.write_text('{"a":2}', encoding="utf-8")
        with pytest.raises(StoreConflictError, match="Content mismatch"):
            _safe_copy_file(src, dst, tmp_path / "conflicts")
        assert (tmp_path / "conflicts" / "src.json").exists()


class TestHydrateRunDir:
    def test_copies_artifacts(self, tmp_path: Path) -> None:
        # Set up store artifact set
        sha_dir = tmp_path / "store_sha"
        w1 = sha_dir / "w1"
        w1.mkdir(parents=True)
        _write_json(w1 / "repo_inventory.json", {"from": "store"})
        w4 = sha_dir / "w4"
        w4.mkdir(parents=True)
        _write_json(w4 / "page_plan.json", {"from": "store"})

        run_dir = tmp_path / "run"
        run_dir.mkdir()
        count = hydrate_run_dir(run_dir, sha_dir)
        assert count == 2
        assert (run_dir / "artifacts" / "repo_inventory.json").exists()
        assert (run_dir / "artifacts" / "page_plan.json").exists()

    def test_hydrates_w5_w8_w9(self, tmp_path: Path) -> None:
        """Hydration copies W5/W8/W9 artifacts (TC-3060)."""
        sha_dir = tmp_path / "store_sha"
        for worker, name, data in [
            ("w5", "draft_manifest.json", {"pages": []}),
            ("w8", "patch_bundle.json", {"patches": []}),
            ("w9", "validation_report.json", {"gates": []}),
        ]:
            w_dir = sha_dir / worker
            w_dir.mkdir(parents=True)
            _write_json(w_dir / name, data)

        run_dir = tmp_path / "run"
        run_dir.mkdir()
        count = hydrate_run_dir(run_dir, sha_dir)
        assert count == 3
        assert (run_dir / "artifacts" / "draft_manifest.json").exists()
        assert (run_dir / "artifacts" / "patch_bundle.json").exists()
        assert (run_dir / "artifacts" / "validation_report.json").exists()

    def test_skips_existing(self, tmp_path: Path) -> None:
        sha_dir = tmp_path / "store_sha" / "w1"
        sha_dir.mkdir(parents=True)
        _write_json(sha_dir / "repo_inventory.json", {"from": "store"})

        run_dir = tmp_path / "run"
        _write_json(run_dir / "artifacts" / "repo_inventory.json", {"from": "run"})

        count = hydrate_run_dir(run_dir, sha_dir.parent)
        assert count == 0  # Skipped because already exists
        # Original preserved
        data = json.loads(
            (run_dir / "artifacts" / "repo_inventory.json").read_text(encoding="utf-8")
        )
        assert data["from"] == "run"


class TestManifestUpdate:
    def test_manifest_created_on_publish(self, tmp_path: Path) -> None:
        """Manifest updated when W5/W8/W9 artifacts are published (TC-3250).

        W1/W2/W3/W4 artifacts no longer go through publish_run_artifacts,
        so W5/W8/W9 are used to trigger manifest creation.
        """
        store_root = tmp_path / "store"
        key = Path("fam/plat/slug")
        run_dir = tmp_path / "run"
        arts = run_dir / "artifacts"
        arts.mkdir(parents=True)
        _write_json(arts / "validation_report.json", {"ok": True})  # W9

        publish_run_artifacts(store_root, key, "sha_abc", run_dir)

        manifest_path = store_root / key / "manifest.json"
        assert manifest_path.exists()
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert data["best_sha"] == "sha_abc"
        assert "sha_abc" in data["available_shas"]


class TestWriteProvenance:
    """TC-3070: provenance.json write/read round-trip."""

    def test_write_creates_file(self, tmp_path: Path) -> None:
        """write_provenance creates provenance.json at correct path."""
        store_root = tmp_path / "store"
        key = Path("fam/plat")
        prov = {
            "schema_version": "1.0",
            "repo_sha": "abc123",
            "ruleset_version": "ruleset.v1_1",
            "templates_version": "templates.v1",
        }
        result_path = write_provenance(store_root, key, "abc123", prov)
        assert result_path.exists()
        assert result_path == store_root / key / "artifacts" / "abc123" / "provenance.json"
        data = json.loads(result_path.read_text(encoding="utf-8"))
        assert data["ruleset_version"] == "ruleset.v1_1"

    def test_read_returns_dict(self, tmp_path: Path) -> None:
        """read_provenance returns parsed dict when file exists."""
        store_root = tmp_path / "store"
        key = Path("fam/plat")
        prov = {
            "schema_version": "1.0",
            "repo_sha": "sha1",
            "ruleset_version": "rv1",
            "templates_version": "tv1",
        }
        write_provenance(store_root, key, "sha1", prov)
        artifact_set = store_root / key / "artifacts" / "sha1"
        result = read_provenance(artifact_set)
        assert result is not None
        assert result["ruleset_version"] == "rv1"
        assert result["templates_version"] == "tv1"

    def test_read_missing_returns_none(self, tmp_path: Path) -> None:
        """read_provenance returns None when provenance.json is absent."""
        artifact_set = tmp_path / "nonexistent"
        artifact_set.mkdir(parents=True)
        assert read_provenance(artifact_set) is None

    def test_read_corrupt_returns_none(self, tmp_path: Path) -> None:
        """read_provenance returns None when provenance.json is corrupt."""
        artifact_set = tmp_path / "store_sha"
        artifact_set.mkdir(parents=True)
        (artifact_set / "provenance.json").write_text("NOT JSON{{", encoding="utf-8")
        assert read_provenance(artifact_set) is None

    def test_write_idempotent(self, tmp_path: Path) -> None:
        """Writing provenance twice with same data overwrites cleanly."""
        store_root = tmp_path / "store"
        key = Path("fam/plat")
        prov = {"schema_version": "1.0", "repo_sha": "s", "ruleset_version": "rv", "templates_version": "tv"}
        write_provenance(store_root, key, "s", prov)
        write_provenance(store_root, key, "s", prov)
        data = read_provenance(store_root / key / "artifacts" / "s")
        assert data == prov
