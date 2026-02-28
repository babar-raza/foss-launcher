"""Tests for two-layer state store (TC-3250).

Covers:
- Interpretation signature determinism
- RAW layer find/hydrate/publish
- DERIVED layer find/hydrate/publish
- Cache invalidation behavior (sig change, sig match, partial publish)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from launch.provenance import ENGINE_VERSION, compute_interpretation_signature
from launch.state_store.store import (
    STORE_DERIVED_MISS_SIGNATURE,
    STORE_HYDRATE_DERIVED_USED,
    STORE_HYDRATE_RAW_USED,
    find_derived_artifact_set,
    find_raw_artifact_set,
    get_derived_dir,
    get_raw_dir,
    hydrate_from_derived,
    hydrate_from_raw,
    publish_derived_artifacts,
    publish_raw_artifacts,
    publish_run_artifacts,
)


SHA = "abc123def456abc123def456abc123def456abc1"
SHA2 = "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef"


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def _make_run_config(
    ruleset_version: str = "ruleset.v1",
    templates_version: str = "templates.v1",
) -> dict:
    return {
        "family": "cells",
        "target_platform": "python",
        "product_slug": "aspose-cells-python",
        "ruleset_version": ruleset_version,
        "templates_version": templates_version,
    }


# ---------------------------------------------------------------------------
# TestInterpretationSignature
# ---------------------------------------------------------------------------

class TestInterpretationSignature:
    def test_signature_stable_same_inputs(self) -> None:
        """Same config → same sig (determinism)."""
        rc = _make_run_config()
        sig1 = compute_interpretation_signature(rc)
        sig2 = compute_interpretation_signature(rc)
        assert sig1 == sig2

    def test_signature_changes_on_ruleset_version(self) -> None:
        """Different ruleset_version → different sig."""
        sig_a = compute_interpretation_signature(_make_run_config(ruleset_version="ruleset.v1"))
        sig_b = compute_interpretation_signature(_make_run_config(ruleset_version="ruleset.v2"))
        assert sig_a != sig_b

    def test_signature_changes_on_templates_version(self) -> None:
        """Different templates_version → different sig."""
        sig_a = compute_interpretation_signature(_make_run_config(templates_version="templates.v1"))
        sig_b = compute_interpretation_signature(_make_run_config(templates_version="templates.v2"))
        assert sig_a != sig_b

    def test_signature_is_12_chars(self) -> None:
        """Signature must be exactly 12 hex characters."""
        sig = compute_interpretation_signature(_make_run_config())
        assert len(sig) == 12
        assert all(c in "0123456789abcdef" for c in sig)

    def test_engine_version_constant_defined(self) -> None:
        """ENGINE_VERSION must be a non-empty string."""
        assert isinstance(ENGINE_VERSION, str)
        assert len(ENGINE_VERSION) > 0


# ---------------------------------------------------------------------------
# TestRawLayer
# ---------------------------------------------------------------------------

class TestRawLayer:
    def test_get_raw_dir(self, tmp_path: Path) -> None:
        store_root = tmp_path / "store"
        key = Path("cells/python")
        raw_dir = get_raw_dir(store_root, key, SHA)
        assert raw_dir == store_root / "cells" / "python" / "raw" / SHA

    def test_find_raw_set_found(self, tmp_path: Path) -> None:
        """find_raw_artifact_set returns path when w1/ has JSON files."""
        store_root = tmp_path / "store"
        key = Path("cells/python")
        w1_dir = get_raw_dir(store_root, key, SHA) / "w1"
        _write_json(w1_dir / "repo_inventory.json", {"repo_sha": SHA})

        result = find_raw_artifact_set(store_root, key, SHA)
        assert result == get_raw_dir(store_root, key, SHA)

    def test_find_raw_set_missing_dir(self, tmp_path: Path) -> None:
        """find_raw_artifact_set returns None when raw/ dir doesn't exist."""
        store_root = tmp_path / "store"
        key = Path("cells/python")
        result = find_raw_artifact_set(store_root, key, SHA)
        assert result is None

    def test_find_raw_set_empty_w1(self, tmp_path: Path) -> None:
        """find_raw_artifact_set returns None when w1/ exists but is empty."""
        store_root = tmp_path / "store"
        key = Path("cells/python")
        w1_dir = get_raw_dir(store_root, key, SHA) / "w1"
        w1_dir.mkdir(parents=True)
        result = find_raw_artifact_set(store_root, key, SHA)
        assert result is None

    def test_hydrate_from_raw(self, tmp_path: Path) -> None:
        """hydrate_from_raw copies w1/*.json into run_dir/artifacts/."""
        store_root = tmp_path / "store"
        key = Path("cells/python")
        w1_dir = get_raw_dir(store_root, key, SHA) / "w1"
        _write_json(w1_dir / "repo_inventory.json", {"repo_sha": SHA, "kind": "raw"})
        _write_json(w1_dir / "discovered_docs.json", {"docs": []})

        run_dir = tmp_path / "run"
        count = hydrate_from_raw(run_dir, get_raw_dir(store_root, key, SHA))

        assert count == 2
        assert (run_dir / "artifacts" / "repo_inventory.json").exists()
        assert (run_dir / "artifacts" / "discovered_docs.json").exists()

    def test_hydrate_from_raw_skip_existing(self, tmp_path: Path) -> None:
        """hydrate_from_raw does not overwrite pre-existing files in run_dir."""
        store_root = tmp_path / "store"
        key = Path("cells/python")
        w1_dir = get_raw_dir(store_root, key, SHA) / "w1"
        _write_json(w1_dir / "repo_inventory.json", {"repo_sha": SHA, "kind": "raw"})

        run_dir = tmp_path / "run"
        (run_dir / "artifacts").mkdir(parents=True)
        _write_json(run_dir / "artifacts" / "repo_inventory.json", {"kind": "pre-existing"})

        count = hydrate_from_raw(run_dir, get_raw_dir(store_root, key, SHA))
        assert count == 0  # skipped

    def test_publish_and_find_raw_round_trip(self, tmp_path: Path) -> None:
        """publish_raw_artifacts → find_raw_artifact_set round-trip."""
        store_root = tmp_path / "store"
        key = Path("cells/python")

        run_dir = tmp_path / "run"
        _write_json(run_dir / "artifacts" / "repo_inventory.json", {"repo_sha": SHA})
        _write_json(run_dir / "artifacts" / "discovered_docs.json", {"docs": []})
        # W2 file should NOT be picked up by publish_raw_artifacts
        _write_json(run_dir / "artifacts" / "product_facts.json", {"version": "v1"})

        count = publish_raw_artifacts(store_root, key, SHA, run_dir)
        assert count == 2  # only W1 files

        result = find_raw_artifact_set(store_root, key, SHA)
        assert result is not None
        assert (result / "w1" / "repo_inventory.json").exists()
        assert not (result / "w1" / "product_facts.json").exists()


# ---------------------------------------------------------------------------
# TestDerivedLayer
# ---------------------------------------------------------------------------

class TestDerivedLayer:
    def _sig(self) -> str:
        return compute_interpretation_signature(_make_run_config())

    def test_get_derived_dir(self, tmp_path: Path) -> None:
        store_root = tmp_path / "store"
        key = Path("cells/python")
        sig = "abc123def456"
        derived_dir = get_derived_dir(store_root, key, SHA, sig)
        assert derived_dir == store_root / "cells" / "python" / "derived" / SHA / sig

    def test_find_derived_set_found(self, tmp_path: Path) -> None:
        """find_derived_artifact_set returns path when w2/ has JSON files + sig matches."""
        store_root = tmp_path / "store"
        key = Path("cells/python")
        sig = self._sig()
        w2_dir = get_derived_dir(store_root, key, SHA, sig) / "w2"
        _write_json(w2_dir / "product_facts.json", {"version": "v1"})

        result = find_derived_artifact_set(store_root, key, SHA, sig)
        assert result == get_derived_dir(store_root, key, SHA, sig)

    def test_find_derived_set_missing_dir(self, tmp_path: Path) -> None:
        """find_derived_artifact_set returns None when derived/ doesn't exist."""
        store_root = tmp_path / "store"
        key = Path("cells/python")
        result = find_derived_artifact_set(store_root, key, SHA, self._sig())
        assert result is None

    def test_find_derived_set_wrong_sig(self, tmp_path: Path) -> None:
        """find_derived_artifact_set returns None when sig doesn't match stored sig."""
        store_root = tmp_path / "store"
        key = Path("cells/python")
        sig_a = "aaaaaaaaaaaa"
        sig_b = "bbbbbbbbbbbb"

        w2_dir = get_derived_dir(store_root, key, SHA, sig_a) / "w2"
        _write_json(w2_dir / "product_facts.json", {"version": "v1"})

        # Looking for sig_b — should not find sig_a's artifacts
        result = find_derived_artifact_set(store_root, key, SHA, sig_b)
        assert result is None

    def test_find_derived_set_w3_fallback(self, tmp_path: Path) -> None:
        """find_derived_artifact_set finds set if only w3/ is present (not w2)."""
        store_root = tmp_path / "store"
        key = Path("cells/python")
        sig = self._sig()
        w3_dir = get_derived_dir(store_root, key, SHA, sig) / "w3"
        _write_json(w3_dir / "snippet_catalog.json", {"snippets": []})

        result = find_derived_artifact_set(store_root, key, SHA, sig)
        assert result is not None

    def test_hydrate_from_derived(self, tmp_path: Path) -> None:
        """hydrate_from_derived copies w2/w3/w4 files into run_dir/artifacts/."""
        store_root = tmp_path / "store"
        key = Path("cells/python")
        sig = self._sig()
        derived_dir = get_derived_dir(store_root, key, SHA, sig)
        _write_json(derived_dir / "w2" / "product_facts.json", {"version": "v1"})
        _write_json(derived_dir / "w3" / "snippet_catalog.json", {"snippets": []})
        _write_json(derived_dir / "w4" / "page_plan.json", {"pages": []})

        run_dir = tmp_path / "run"
        count = hydrate_from_derived(run_dir, derived_dir)

        assert count == 3
        assert (run_dir / "artifacts" / "product_facts.json").exists()
        assert (run_dir / "artifacts" / "snippet_catalog.json").exists()
        assert (run_dir / "artifacts" / "page_plan.json").exists()

    def test_publish_and_find_derived_round_trip(self, tmp_path: Path) -> None:
        """publish_derived_artifacts → find_derived_artifact_set round-trip."""
        store_root = tmp_path / "store"
        key = Path("cells/python")
        sig = self._sig()

        run_dir = tmp_path / "run"
        _write_json(run_dir / "artifacts" / "product_facts.json", {"version": "v1"})
        _write_json(run_dir / "artifacts" / "snippet_catalog.json", {"snippets": []})
        _write_json(run_dir / "artifacts" / "page_plan.json", {"pages": []})
        # W1 file should NOT be published to derived
        _write_json(run_dir / "artifacts" / "repo_inventory.json", {"repo_sha": SHA})

        count = publish_derived_artifacts(store_root, key, SHA, sig, run_dir)
        assert count == 3  # only W2/W3/W4 files

        result = find_derived_artifact_set(store_root, key, SHA, sig)
        assert result is not None
        derived_dir = get_derived_dir(store_root, key, SHA, sig)
        assert (derived_dir / "w2" / "product_facts.json").exists()
        assert (derived_dir / "w3" / "snippet_catalog.json").exists()
        assert (derived_dir / "w4" / "page_plan.json").exists()
        assert not (derived_dir / "w1" / "repo_inventory.json").exists()


# ---------------------------------------------------------------------------
# TestCacheInvalidationBehavior
# ---------------------------------------------------------------------------

class TestCacheInvalidationBehavior:
    def test_raw_reused_when_sig_changes(self, tmp_path: Path) -> None:
        """RAW set is found regardless of sig — SHA-only key."""
        store_root = tmp_path / "store"
        key = Path("cells/python")

        # Publish with sig_a
        run_dir = tmp_path / "run"
        _write_json(run_dir / "artifacts" / "repo_inventory.json", {"repo_sha": SHA})
        publish_raw_artifacts(store_root, key, SHA, run_dir)

        # Look up with sig_b (different sig, same SHA)
        result = find_raw_artifact_set(store_root, key, SHA)
        assert result is not None, "RAW set should be found regardless of sig"

    def test_derived_not_reused_when_sig_changes(self, tmp_path: Path) -> None:
        """DERIVED set is not found when sig changes."""
        store_root = tmp_path / "store"
        key = Path("cells/python")
        sig_a = compute_interpretation_signature(_make_run_config(ruleset_version="ruleset.v1"))
        sig_b = compute_interpretation_signature(_make_run_config(ruleset_version="ruleset.v2"))

        run_dir = tmp_path / "run"
        _write_json(run_dir / "artifacts" / "product_facts.json", {"version": "v1"})
        publish_derived_artifacts(store_root, key, SHA, sig_a, run_dir)

        # Same SHA but different sig → should return None
        result = find_derived_artifact_set(store_root, key, SHA, sig_b)
        assert result is None, "DERIVED set must not be found when sig changes"

    def test_derived_reused_when_sig_matches(self, tmp_path: Path) -> None:
        """DERIVED set is found when sig matches."""
        store_root = tmp_path / "store"
        key = Path("cells/python")
        sig = compute_interpretation_signature(_make_run_config())

        run_dir = tmp_path / "run"
        _write_json(run_dir / "artifacts" / "product_facts.json", {"version": "v1"})
        publish_derived_artifacts(store_root, key, SHA, sig, run_dir)

        result = find_derived_artifact_set(store_root, key, SHA, sig)
        assert result is not None, "DERIVED set must be found when sig matches"

    def test_partial_success_raw_cached_without_w2(self, tmp_path: Path) -> None:
        """W1 artifacts published even when W2 files are absent (pipeline failed at W2)."""
        store_root = tmp_path / "store"
        key = Path("cells/python")
        sig = compute_interpretation_signature(_make_run_config())

        run_dir = tmp_path / "run"
        # Only W1 artifacts present (W2 never ran)
        _write_json(run_dir / "artifacts" / "repo_inventory.json", {"repo_sha": SHA})
        _write_json(run_dir / "artifacts" / "discovered_docs.json", {"docs": []})

        raw_count = publish_raw_artifacts(store_root, key, SHA, run_dir)
        derived_count = publish_derived_artifacts(store_root, key, SHA, sig, run_dir)

        assert raw_count == 2  # W1 files published
        assert derived_count == 0  # no W2/W3/W4 files → nothing to publish

        # RAW found; DERIVED not found
        assert find_raw_artifact_set(store_root, key, SHA) is not None
        assert find_derived_artifact_set(store_root, key, SHA, sig) is None

    def test_multiple_sigs_coexist_for_same_sha(self, tmp_path: Path) -> None:
        """Multiple derived sigs can coexist for the same repo_sha."""
        store_root = tmp_path / "store"
        key = Path("cells/python")
        sig_a = compute_interpretation_signature(_make_run_config(ruleset_version="ruleset.v1"))
        sig_b = compute_interpretation_signature(_make_run_config(ruleset_version="ruleset.v2"))

        run_dir = tmp_path / "run"
        _write_json(run_dir / "artifacts" / "product_facts.json", {"ver": "a"})
        publish_derived_artifacts(store_root, key, SHA, sig_a, run_dir)

        # Publish a different version under sig_b
        _write_json(run_dir / "artifacts" / "product_facts.json", {"ver": "b"})
        publish_derived_artifacts(store_root, key, SHA, sig_b, run_dir)

        # Both sigs findable
        assert find_derived_artifact_set(store_root, key, SHA, sig_a) is not None
        assert find_derived_artifact_set(store_root, key, SHA, sig_b) is not None


# ---------------------------------------------------------------------------
# TestPublishRunArtifactsSkipsW1W4
# ---------------------------------------------------------------------------

class TestPublishRunArtifactsSkipsW1W4:
    """Verify that publish_run_artifacts no longer writes W1–W4 to legacy layout."""

    def test_w1_not_published_via_old_function(self, tmp_path: Path) -> None:
        """publish_run_artifacts must skip W1 artifacts (now handled by RAW layer)."""
        from launch.state_store.store import publish_run_artifacts

        store_root = tmp_path / "store"
        key = Path("cells/python")
        run_dir = tmp_path / "run"
        _write_json(run_dir / "artifacts" / "repo_inventory.json", {"repo_sha": SHA})

        count = publish_run_artifacts(store_root, key, SHA, run_dir)
        assert count == 0  # W1 artifact skipped

        legacy_path = store_root / "cells" / "python" / "artifacts" / SHA / "w1" / "repo_inventory.json"
        assert not legacy_path.exists()

    def test_w2_not_published_via_old_function(self, tmp_path: Path) -> None:
        """publish_run_artifacts must skip W2 artifacts (now handled by DERIVED layer)."""
        from launch.state_store.store import publish_run_artifacts

        store_root = tmp_path / "store"
        key = Path("cells/python")
        run_dir = tmp_path / "run"
        _write_json(run_dir / "artifacts" / "product_facts.json", {"version": "v1"})

        count = publish_run_artifacts(store_root, key, SHA, run_dir)
        assert count == 0

    def test_w5_still_published_via_old_function(self, tmp_path: Path) -> None:
        """publish_run_artifacts must still publish W5/W8/W9 to legacy layout."""
        from launch.state_store.store import publish_run_artifacts

        store_root = tmp_path / "store"
        key = Path("cells/python")
        run_dir = tmp_path / "run"
        _write_json(run_dir / "artifacts" / "draft_manifest.json", {"drafts": []})
        _write_json(run_dir / "artifacts" / "validation_report.json", {"ok": True})

        count = publish_run_artifacts(store_root, key, SHA, run_dir)
        assert count == 2  # W5 + W9 published to legacy layout

        assert (
            store_root / "cells" / "python" / "artifacts" / SHA / "w5" / "draft_manifest.json"
        ).exists()
        assert (
            store_root / "cells" / "python" / "artifacts" / SHA / "w9" / "validation_report.json"
        ).exists()


# ---------------------------------------------------------------------------
# TestEdgeCaseResilience (SR-03)
# ---------------------------------------------------------------------------

class TestEdgeCaseResilience:
    """Edge-case boundary tests for two-layer store functions."""

    def test_find_raw_empty_w1_dir_returns_none(self, tmp_path: Path) -> None:
        """w1/ exists but contains no JSON → find_raw returns None."""
        store_root = tmp_path / "store"
        key = Path("cells/python")
        w1_dir = get_raw_dir(store_root, key, SHA) / "w1"
        w1_dir.mkdir(parents=True)
        # Empty directory
        result = find_raw_artifact_set(store_root, key, SHA)
        assert result is None

    def test_find_raw_non_json_files_ignored(self, tmp_path: Path) -> None:
        """w1/ has .txt but no .json → find_raw returns None."""
        store_root = tmp_path / "store"
        key = Path("cells/python")
        w1_dir = get_raw_dir(store_root, key, SHA) / "w1"
        w1_dir.mkdir(parents=True)
        (w1_dir / "notes.txt").write_text("not json", encoding="utf-8")
        result = find_raw_artifact_set(store_root, key, SHA)
        assert result is None

    def test_find_derived_empty_worker_dirs_returns_none(self, tmp_path: Path) -> None:
        """derived/<sha>/<sig>/w2,w3,w4 exist but empty → find_derived returns None."""
        store_root = tmp_path / "store"
        key = Path("cells/python")
        sig = compute_interpretation_signature(_make_run_config())
        derived_dir = get_derived_dir(store_root, key, SHA, sig)
        for w in ("w2", "w3", "w4"):
            (derived_dir / w).mkdir(parents=True)
        result = find_derived_artifact_set(store_root, key, SHA, sig)
        assert result is None

    def test_hydrate_raw_copies_corrupt_json_unchanged(self, tmp_path: Path) -> None:
        """Corrupt JSON in w1/ is copied verbatim (no crash, no validation)."""
        store_root = tmp_path / "store"
        key = Path("cells/python")
        w1_dir = get_raw_dir(store_root, key, SHA) / "w1"
        w1_dir.mkdir(parents=True)
        corrupt_content = "{invalid json content"
        (w1_dir / "repo_inventory.json").write_text(corrupt_content, encoding="utf-8")

        run_dir = tmp_path / "run"
        count = hydrate_from_raw(run_dir, get_raw_dir(store_root, key, SHA))
        assert count == 1
        copied = (run_dir / "artifacts" / "repo_inventory.json").read_text(encoding="utf-8")
        assert copied == corrupt_content

    def test_publish_derived_zero_files(self, tmp_path: Path) -> None:
        """publish_derived_artifacts with no W2/W3/W4 in run_dir → returns 0."""
        store_root = tmp_path / "store"
        key = Path("cells/python")
        sig = compute_interpretation_signature(_make_run_config())
        run_dir = tmp_path / "run"
        (run_dir / "artifacts").mkdir(parents=True)
        # Only W1 + W9 present (no W2/W3/W4)
        _write_json(run_dir / "artifacts" / "repo_inventory.json", {"sha": SHA})
        _write_json(run_dir / "artifacts" / "validation_report.json", {"ok": True})

        count = publish_derived_artifacts(store_root, key, SHA, sig, run_dir)
        assert count == 0

    def test_hydrate_derived_skips_existing_files(self, tmp_path: Path) -> None:
        """hydrate_from_derived does not overwrite pre-existing files."""
        store_root = tmp_path / "store"
        key = Path("cells/python")
        sig = compute_interpretation_signature(_make_run_config())
        derived_dir = get_derived_dir(store_root, key, SHA, sig)
        _write_json(derived_dir / "w2" / "product_facts.json", {"version": "new"})
        _write_json(derived_dir / "w4" / "page_plan.json", {"pages": ["new"]})

        run_dir = tmp_path / "run"
        (run_dir / "artifacts").mkdir(parents=True)
        # Pre-existing product_facts.json
        _write_json(run_dir / "artifacts" / "product_facts.json", {"version": "old"})

        count = hydrate_from_derived(run_dir, derived_dir)
        assert count == 1  # only page_plan.json copied; product_facts skipped

        # Verify pre-existing was NOT overwritten
        import json as _json
        pf = _json.loads(
            (run_dir / "artifacts" / "product_facts.json").read_text(encoding="utf-8")
        )
        assert pf["version"] == "old"


# ---------------------------------------------------------------------------
# TestObservabilityLogging (SR-05)
# ---------------------------------------------------------------------------

class TestObservabilityLogging:
    """Verify debug log messages from two-layer store functions."""

    def test_publish_run_artifacts_logs_skip(self, tmp_path: Path, caplog) -> None:
        """publish_run_artifacts emits debug log when skipping W1/W2 artifacts."""
        import logging

        store_root = tmp_path / "store"
        key = Path("cells/python")
        run_dir = tmp_path / "run"
        _write_json(run_dir / "artifacts" / "repo_inventory.json", {"repo_sha": SHA})
        _write_json(run_dir / "artifacts" / "product_facts.json", {"v": "1"})

        with caplog.at_level(logging.DEBUG, logger="launch.state_store.store"):
            publish_run_artifacts(store_root, key, SHA, run_dir)

        skip_msgs = [r for r in caplog.records if "store_publish_skip_two_layer" in r.message]
        assert len(skip_msgs) == 2
        names = sorted(r.message.split(": ")[1].split(" -> ")[0] for r in skip_msgs)
        assert names == ["product_facts.json", "repo_inventory.json"]

    def test_find_derived_empty_dirs_logs_debug(self, tmp_path: Path, caplog) -> None:
        """find_derived_artifact_set logs debug when derived dirs exist but are empty."""
        import logging

        store_root = tmp_path / "store"
        key = Path("cells/python")
        sig = compute_interpretation_signature(_make_run_config())
        derived_dir = get_derived_dir(store_root, key, SHA, sig)
        for w in ("w2", "w3", "w4"):
            (derived_dir / w).mkdir(parents=True)

        with caplog.at_level(logging.DEBUG, logger="launch.state_store.store"):
            result = find_derived_artifact_set(store_root, key, SHA, sig)

        assert result is None
        empty_msgs = [r for r in caplog.records if "store_find_derived_empty" in r.message]
        assert len(empty_msgs) == 1
        assert SHA[:12] in empty_msgs[0].message
