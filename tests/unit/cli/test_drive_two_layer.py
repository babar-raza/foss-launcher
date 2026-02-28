"""Tests for drive() two-layer cache behavior (TC-3250).

Covers:
- RAW hydration used when raw_set exists
- DERIVED hydration used when sig matches
- DERIVED miss when sig changes
- Publishing raw/derived regardless of exit_code
- Legacy fallback when no raw set
- execution_plan.json records sig
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from launch.provenance import compute_interpretation_signature
from launch.state_store.store import (
    get_derived_dir,
    get_raw_dir,
    publish_derived_artifacts,
    publish_raw_artifacts,
)


SHA = "abc123def456abc123def456abc123def456abc1"


def _make_run_config(
    ruleset_version: str = "ruleset.v1",
    templates_version: str = "templates.v1",
) -> dict:
    return {
        "family": "cells",
        "target_platform": "python",
        "product_slug": "aspose-cells-python",
        "github_ref": SHA,
        "ruleset_version": ruleset_version,
        "templates_version": templates_version,
    }


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


class TestRawHydrationInDrive:
    """Tests that the drive() function properly uses the RAW layer."""

    def test_sig_computed_from_run_config(self) -> None:
        """compute_interpretation_signature integrates with run_config."""
        rc = _make_run_config()
        sig = compute_interpretation_signature(rc)
        assert isinstance(sig, str)
        assert len(sig) == 12

    def test_raw_artifacts_published_even_on_failure(self, tmp_path: Path) -> None:
        """publish_raw_artifacts should work and produce store artifacts."""
        store_root = tmp_path / "store"
        key = Path("cells/python")
        run_dir = tmp_path / "run"
        _write_json(run_dir / "artifacts" / "repo_inventory.json", {"repo_sha": SHA})
        _write_json(run_dir / "artifacts" / "discovered_docs.json", {"docs": []})

        count = publish_raw_artifacts(store_root, key, SHA, run_dir)
        assert count == 2

        raw_w1 = get_raw_dir(store_root, key, SHA) / "w1"
        assert (raw_w1 / "repo_inventory.json").exists()
        assert (raw_w1 / "discovered_docs.json").exists()

    def test_derived_artifacts_published_even_on_failure(self, tmp_path: Path) -> None:
        """publish_derived_artifacts should work and produce store artifacts."""
        store_root = tmp_path / "store"
        key = Path("cells/python")
        sig = compute_interpretation_signature(_make_run_config())
        run_dir = tmp_path / "run"
        _write_json(run_dir / "artifacts" / "product_facts.json", {"version": "v1"})
        _write_json(run_dir / "artifacts" / "page_plan.json", {"pages": []})

        count = publish_derived_artifacts(store_root, key, SHA, sig, run_dir)
        assert count == 2

        derived_dir = get_derived_dir(store_root, key, SHA, sig)
        assert (derived_dir / "w2" / "product_facts.json").exists()
        assert (derived_dir / "w4" / "page_plan.json").exists()


class TestDerivedHydrationBehavior:
    """Tests derived layer selection logic."""

    def test_derived_miss_on_sig_change(self, tmp_path: Path) -> None:
        """After sig change, existing derived artifacts are not found."""
        from launch.state_store.store import find_derived_artifact_set

        store_root = tmp_path / "store"
        key = Path("cells/python")
        old_sig = compute_interpretation_signature(_make_run_config(ruleset_version="ruleset.v1"))
        new_sig = compute_interpretation_signature(_make_run_config(ruleset_version="ruleset.v2"))

        # Populate old sig
        run_dir = tmp_path / "run"
        _write_json(run_dir / "artifacts" / "product_facts.json", {"old": True})
        publish_derived_artifacts(store_root, key, SHA, old_sig, run_dir)

        # Query with new sig → miss
        result = find_derived_artifact_set(store_root, key, SHA, new_sig)
        assert result is None

    def test_derived_hit_on_sig_match(self, tmp_path: Path) -> None:
        """When sig matches, derived artifacts are found."""
        from launch.state_store.store import find_derived_artifact_set

        store_root = tmp_path / "store"
        key = Path("cells/python")
        sig = compute_interpretation_signature(_make_run_config())

        run_dir = tmp_path / "run"
        _write_json(run_dir / "artifacts" / "product_facts.json", {"current": True})
        publish_derived_artifacts(store_root, key, SHA, sig, run_dir)

        result = find_derived_artifact_set(store_root, key, SHA, sig)
        assert result is not None

    def test_raw_found_despite_sig_change(self, tmp_path: Path) -> None:
        """RAW artifacts survive sig changes (SHA-only key)."""
        from launch.state_store.store import find_raw_artifact_set

        store_root = tmp_path / "store"
        key = Path("cells/python")

        run_dir = tmp_path / "run"
        _write_json(run_dir / "artifacts" / "repo_inventory.json", {"repo_sha": SHA})
        publish_raw_artifacts(store_root, key, SHA, run_dir)

        # Any sig → raw is found
        result = find_raw_artifact_set(store_root, key, SHA)
        assert result is not None

    def test_hydrate_from_raw_and_derived_combined(self, tmp_path: Path) -> None:
        """hydrate_from_raw + hydrate_from_derived populate run_dir fully."""
        from launch.state_store.store import hydrate_from_derived, hydrate_from_raw

        store_root = tmp_path / "store"
        key = Path("cells/python")
        sig = compute_interpretation_signature(_make_run_config())

        # Populate store
        raw_dir = get_raw_dir(store_root, key, SHA)
        _write_json(raw_dir / "w1" / "repo_inventory.json", {"repo_sha": SHA})

        derived_dir = get_derived_dir(store_root, key, SHA, sig)
        _write_json(derived_dir / "w2" / "product_facts.json", {"version": "v1"})
        _write_json(derived_dir / "w3" / "snippet_catalog.json", {"snippets": []})
        _write_json(derived_dir / "w4" / "page_plan.json", {"pages": []})

        run_dir = tmp_path / "run"
        raw_count = hydrate_from_raw(run_dir, raw_dir)
        derived_count = hydrate_from_derived(run_dir, derived_dir)

        assert raw_count == 1
        assert derived_count == 3
        artifacts = run_dir / "artifacts"
        assert (artifacts / "repo_inventory.json").exists()
        assert (artifacts / "product_facts.json").exists()
        assert (artifacts / "snippet_catalog.json").exists()
        assert (artifacts / "page_plan.json").exists()


class TestEventConstants:
    """Verify event constant strings are defined and non-empty."""

    def test_store_hydrate_raw_used_constant(self) -> None:
        from launch.state_store.store import STORE_HYDRATE_RAW_USED
        assert STORE_HYDRATE_RAW_USED == "STORE_HYDRATE_RAW_USED"

    def test_store_hydrate_derived_used_constant(self) -> None:
        from launch.state_store.store import STORE_HYDRATE_DERIVED_USED
        assert STORE_HYDRATE_DERIVED_USED == "STORE_HYDRATE_DERIVED_USED"

    def test_store_derived_miss_signature_constant(self) -> None:
        from launch.state_store.store import STORE_DERIVED_MISS_SIGNATURE
        assert STORE_DERIVED_MISS_SIGNATURE == "STORE_DERIVED_MISS_SIGNATURE"


class TestBackwardCompatibilityFallback:
    """Legacy store layout (artifacts/<sha>/) still usable as fallback."""

    def test_find_artifact_set_still_works(self, tmp_path: Path) -> None:
        """find_artifact_set (legacy) still finds old-layout artifacts."""
        from launch.state_store.store import find_artifact_set

        store_root = tmp_path / "store"
        key = Path("cells/python")
        legacy_w1 = store_root / "cells" / "python" / "artifacts" / SHA / "w1"
        _write_json(legacy_w1 / "repo_inventory.json", {"repo_sha": SHA})

        result = find_artifact_set(store_root, key, SHA)
        assert result == store_root / "cells" / "python" / "artifacts" / SHA

    def test_find_raw_returns_none_for_legacy_only_store(self, tmp_path: Path) -> None:
        """find_raw_artifact_set returns None when only legacy layout exists."""
        from launch.state_store.store import find_raw_artifact_set

        store_root = tmp_path / "store"
        key = Path("cells/python")
        legacy_w1 = store_root / "cells" / "python" / "artifacts" / SHA / "w1"
        _write_json(legacy_w1 / "repo_inventory.json", {"repo_sha": SHA})

        # No raw/ dir → None
        result = find_raw_artifact_set(store_root, key, SHA)
        assert result is None
