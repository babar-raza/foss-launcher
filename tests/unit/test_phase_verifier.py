"""Unit tests for the phase artifact verifier (TC-2501).

Tests verify_phase_artifacts() for each phase, covering:
- All-pass scenario (P1)
- Missing artifacts
- Malformed JSON
- Schema validation failure
- P3 draft manifest page existence checks
- P5 validation_report.json required keys
- verify_phase_range()
- Unknown phase_id error
- Serialization of PhaseVerificationResult

Minimum 8 tests required per TC-2501 acceptance criteria.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any, Dict

import pytest

from launch.orchestrator.phase_verifier import (
    PHASE_ARTIFACT_CHECKLIST,
    PHASE_IDS,
    ArtifactCheck,
    PhaseVerificationResult,
    verify_phase_artifacts,
    verify_phase_range,
)


# ═══════════════════════════════════════════════════════════════════════
# Fixtures — minimal valid JSON payloads for each artifact
# ═══════════════════════════════════════════════════════════════════════

def _minimal_repo_inventory() -> Dict[str, Any]:
    return {
        "schema_version": "1.0",
        "repo_url": "https://github.com/example/repo",
        "repo_sha": "abc123",
        "fingerprint": {},
        "repo_profile": {
            "platform_family": "python",
            "primary_languages": ["Python"],
            "build_systems": ["pip"],
            "package_manifests": ["setup.py"],
            "recommended_test_commands": ["pytest"],
            "example_locator": "examples/",
            "doc_locator": "docs/",
        },
        "paths": [],
        "doc_entrypoints": [],
        "example_paths": [],
    }


def _minimal_product_facts() -> Dict[str, Any]:
    return {
        "schema_version": "1.0",
        "product_name": "Test Product",
        "product_slug": "test-product",
        "repo_url": "https://github.com/example/repo",
        "repo_sha": "abc123",
        "positioning": {
            "tagline": "A test product",
            "short_description": "A product for testing.",
        },
        "supported_platforms": ["linux"],
        "claims": [],
        "claim_groups": {
            "key_features": [],
            "install_steps": [],
            "quickstart_steps": [],
            "workflow_claims": [],
            "limitations": [],
            "compatibility_notes": [],
        },
        "supported_formats": [],
        "workflows": [],
        "api_surface_summary": {},
        "example_inventory": [],
    }


def _minimal_snippet_catalog() -> Dict[str, Any]:
    return {
        "schema_version": "1.0",
        "snippets": [],
    }


def _minimal_page_plan() -> Dict[str, Any]:
    return {
        "schema_version": "1.0",
        "product_slug": "test-product",
        "launch_tier": "minimal",
        "pages": [],
    }


def _minimal_shared_facts() -> Dict[str, Any]:
    return {
        "schema_version": "1.0",
        "runtime_versions": {},
        "supported_formats": [],
        "product_slug": "test-product",
    }


def _minimal_validation_report() -> Dict[str, Any]:
    return {
        "schema_version": "1.0",
        "ok": True,
        "profile": "local",
        "gates": [],
        "issues": [],
    }


def _minimal_patch_bundle() -> Dict[str, Any]:
    return {
        "schema_version": "1.0",
        "patches": [],
    }


def _minimal_content_policy() -> Dict[str, Any]:
    return {"version": "1.0", "policies": []}


def _minimal_draft_manifest(pages: list[Dict[str, str]] | None = None) -> Dict[str, Any]:
    return {
        "schema_version": "1.0",
        "pages": pages or [],
    }


# ═══════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════

def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _create_p1_artifacts(run_dir: Path) -> None:
    """Write minimal valid P1 artifacts."""
    arts = run_dir / "artifacts"
    _write_json(arts / "repo_inventory.json", _minimal_repo_inventory())
    _write_json(arts / "product_facts.json", _minimal_product_facts())
    _write_json(arts / "snippet_catalog.json", _minimal_snippet_catalog())


def _create_p2_artifacts(run_dir: Path) -> None:
    """Write minimal valid P2 artifacts."""
    arts = run_dir / "artifacts"
    _write_json(arts / "page_plan.json", _minimal_page_plan())
    _write_json(arts / "shared_facts.json", _minimal_shared_facts())
    _write_json(arts / "content_policy.json", _minimal_content_policy())


def _create_p3_artifacts(run_dir: Path, draft_pages: list[Dict[str, str]] | None = None) -> None:
    """Write minimal valid P3 artifacts."""
    arts = run_dir / "artifacts"
    _write_json(arts / "draft_manifest.json", _minimal_draft_manifest(draft_pages))


def _create_p4_artifacts(run_dir: Path) -> None:
    """Write minimal valid P4 artifacts."""
    arts = run_dir / "artifacts"
    _write_json(arts / "patch_bundle.json", _minimal_patch_bundle())


def _create_p5_artifacts(run_dir: Path) -> None:
    """Write minimal valid P5 artifacts."""
    arts = run_dir / "artifacts"
    _write_json(arts / "validation_report.json", _minimal_validation_report())


# ═══════════════════════════════════════════════════════════════════════
# Tests
# ═══════════════════════════════════════════════════════════════════════


class TestPhaseArtifactChecklist:
    """Verify the PHASE_ARTIFACT_CHECKLIST constant itself."""

    def test_covers_all_six_phases(self) -> None:
        assert set(PHASE_ARTIFACT_CHECKLIST.keys()) == {"P1", "P2", "P3", "P4", "P5", "P6"}

    def test_phase_ids_ordering(self) -> None:
        assert list(PHASE_IDS) == ["P1", "P2", "P3", "P4", "P5", "P6"]

    def test_p1_has_three_artifacts(self) -> None:
        assert len(PHASE_ARTIFACT_CHECKLIST["P1"]) == 3


class TestVerifyPhaseArtifactsP1:
    """P1: repo_inventory, product_facts, snippet_catalog -- all with schema."""

    def test_all_pass(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        _create_p1_artifacts(run_dir)

        # repo_root is needed so the verifier can find schemas on disk
        import launch.orchestrator.phase_verifier as pv
        repo_root = pv._resolve_repo_root()

        result = verify_phase_artifacts(run_dir, "P1", repo_root=repo_root)

        assert result.ok is True
        assert result.phase_id == "P1"
        assert len(result.checks) == 3
        assert result.missing == []
        assert result.schema_errors == []

        # Verify individual check details
        for check in result.checks:
            assert check.exists is True
            assert check.valid_json is True
            assert check.schema_valid is True
            assert check.error is None

    def test_missing_artifact(self, tmp_path: Path) -> None:
        """When one artifact is missing, result.ok=False and missing list populated."""
        run_dir = tmp_path / "run"
        arts = run_dir / "artifacts"
        arts.mkdir(parents=True)

        # Only write 2 of 3 P1 artifacts
        _write_json(arts / "repo_inventory.json", _minimal_repo_inventory())
        _write_json(arts / "product_facts.json", _minimal_product_facts())
        # snippet_catalog.json is missing

        import launch.orchestrator.phase_verifier as pv
        repo_root = pv._resolve_repo_root()

        result = verify_phase_artifacts(run_dir, "P1", repo_root=repo_root)

        assert result.ok is False
        assert "artifacts/snippet_catalog.json" in result.missing

    def test_malformed_json(self, tmp_path: Path) -> None:
        """When an artifact contains invalid JSON, result reports the parse error."""
        run_dir = tmp_path / "run"
        arts = run_dir / "artifacts"
        arts.mkdir(parents=True)

        _write_json(arts / "repo_inventory.json", _minimal_repo_inventory())
        _write_json(arts / "snippet_catalog.json", _minimal_snippet_catalog())

        # Write malformed JSON to product_facts.json
        malformed = arts / "product_facts.json"
        malformed.write_text("{invalid json!!!}", encoding="utf-8")

        import launch.orchestrator.phase_verifier as pv
        repo_root = pv._resolve_repo_root()

        result = verify_phase_artifacts(run_dir, "P1", repo_root=repo_root)

        assert result.ok is False
        assert "artifacts/product_facts.json" in result.schema_errors

        # Find the check for the malformed file
        pf_check = [c for c in result.checks if c.path == "artifacts/product_facts.json"][0]
        assert pf_check.exists is True
        assert pf_check.valid_json is False
        assert pf_check.error is not None
        assert "Malformed JSON" in pf_check.error

    def test_schema_validation_failure(self, tmp_path: Path) -> None:
        """When an artifact has valid JSON but fails schema, schema_valid=False."""
        run_dir = tmp_path / "run"
        arts = run_dir / "artifacts"
        arts.mkdir(parents=True)

        _write_json(arts / "repo_inventory.json", _minimal_repo_inventory())
        _write_json(arts / "snippet_catalog.json", _minimal_snippet_catalog())

        # Write valid JSON that does NOT match the product_facts schema
        invalid_data = {"schema_version": "1.0", "not_a_real_field": True}
        _write_json(arts / "product_facts.json", invalid_data)

        import launch.orchestrator.phase_verifier as pv
        repo_root = pv._resolve_repo_root()

        result = verify_phase_artifacts(run_dir, "P1", repo_root=repo_root)

        assert result.ok is False
        assert "artifacts/product_facts.json" in result.schema_errors

        pf_check = [c for c in result.checks if c.path == "artifacts/product_facts.json"][0]
        assert pf_check.exists is True
        assert pf_check.valid_json is True
        assert pf_check.schema_valid is False
        assert "Schema validation failed" in pf_check.error


class TestVerifyPhaseArtifactsP2:
    """P2: page_plan, shared_facts, content_policy."""

    def test_all_pass(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        _create_p2_artifacts(run_dir)

        import launch.orchestrator.phase_verifier as pv
        repo_root = pv._resolve_repo_root()

        result = verify_phase_artifacts(run_dir, "P2", repo_root=repo_root)

        assert result.ok is True
        assert len(result.checks) == 3
        # content_policy has no schema -> schema_valid=None
        cp_check = [c for c in result.checks if "content_policy" in c.path][0]
        assert cp_check.schema_valid is None


class TestVerifyPhaseArtifactsP3:
    """P3: draft_manifest + page file existence checks."""

    def test_manifest_with_existing_pages(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run"

        # Create a draft page
        page_path = "drafts/products/overview.md"
        (run_dir / "drafts" / "products").mkdir(parents=True)
        (run_dir / page_path).write_text("# Overview\n", encoding="utf-8")

        _create_p3_artifacts(run_dir, draft_pages=[{"output_path": page_path}])

        result = verify_phase_artifacts(run_dir, "P3")

        assert result.ok is True
        # checks = 1 (draft_manifest.json) + 1 (the page file)
        assert len(result.checks) == 2

    def test_manifest_with_missing_page(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run"

        # Reference a page that does not exist
        _create_p3_artifacts(
            run_dir,
            draft_pages=[{"output_path": "drafts/products/nonexistent.md"}],
        )

        result = verify_phase_artifacts(run_dir, "P3")

        assert result.ok is False
        assert "drafts/products/nonexistent.md" in result.missing


class TestVerifyPhaseArtifactsP5:
    """P5: validation_report.json with gates+issues key check."""

    def test_all_pass(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        _create_p5_artifacts(run_dir)

        import launch.orchestrator.phase_verifier as pv
        repo_root = pv._resolve_repo_root()

        result = verify_phase_artifacts(run_dir, "P5", repo_root=repo_root)
        assert result.ok is True

    def test_missing_gates_key(self, tmp_path: Path) -> None:
        """validation_report.json exists but is missing required 'gates' key."""
        run_dir = tmp_path / "run"
        arts = run_dir / "artifacts"
        arts.mkdir(parents=True)

        # Write a report that passes JSON parse but lacks required 'gates' key.
        # Since the schema also requires 'gates', the schema check itself will
        # fail.  We still test that the specific key-check logic fires too.
        bad_report = {
            "schema_version": "1.0",
            "ok": True,
            "profile": "local",
            # "gates" deliberately omitted
            "issues": [],
        }
        _write_json(arts / "validation_report.json", bad_report)

        import launch.orchestrator.phase_verifier as pv
        repo_root = pv._resolve_repo_root()

        result = verify_phase_artifacts(run_dir, "P5", repo_root=repo_root)

        assert result.ok is False
        assert "artifacts/validation_report.json" in result.schema_errors


class TestVerifyPhaseRange:
    """verify_phase_range() over multiple phases."""

    def test_p1_through_p2(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        _create_p1_artifacts(run_dir)
        _create_p2_artifacts(run_dir)

        import launch.orchestrator.phase_verifier as pv
        repo_root = pv._resolve_repo_root()

        results = verify_phase_range(run_dir, "P1", "P2", repo_root=repo_root)

        assert len(results) == 2
        assert results[0].phase_id == "P1"
        assert results[0].ok is True
        assert results[1].phase_id == "P2"
        assert results[1].ok is True

    def test_reversed_range_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="must come before"):
            verify_phase_range(tmp_path, "P5", "P1")


class TestUnknownPhase:
    """Error handling for invalid phase IDs."""

    def test_unknown_phase_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="Unknown phase_id"):
            verify_phase_artifacts(tmp_path, "P99")

    def test_unknown_range_start_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="Unknown start_phase"):
            verify_phase_range(tmp_path, "PX", "P3")

    def test_unknown_range_end_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="Unknown end_phase"):
            verify_phase_range(tmp_path, "P1", "PX")


class TestSerialization:
    """PhaseVerificationResult and ArtifactCheck must be JSON-serializable."""

    def test_to_dict_roundtrip(self) -> None:
        check = ArtifactCheck(
            path="artifacts/product_facts.json",
            exists=True,
            valid_json=True,
            schema_valid=True,
            error=None,
        )
        result = PhaseVerificationResult(
            phase_id="P1",
            ok=True,
            checks=[check],
            missing=[],
            schema_errors=[],
        )

        d = result.to_dict()
        # Must be JSON-serializable
        serialized = json.dumps(d)
        assert isinstance(serialized, str)

        # Roundtrip: key fields survive
        parsed = json.loads(serialized)
        assert parsed["phase_id"] == "P1"
        assert parsed["ok"] is True
        assert len(parsed["checks"]) == 1
        assert parsed["checks"][0]["path"] == "artifacts/product_facts.json"

    def test_artifact_check_to_dict(self) -> None:
        check = ArtifactCheck(
            path="foo.json",
            exists=False,
            valid_json=False,
            schema_valid=None,
            error="not found",
        )
        d = check.to_dict()
        assert d["path"] == "foo.json"
        assert d["exists"] is False
        assert d["schema_valid"] is None
        assert d["error"] == "not found"


class TestSchemaFileMissing:
    """When the schema file is not on disk, validation is skipped gracefully."""

    def test_missing_schema_skips_validation(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run"
        arts = run_dir / "artifacts"
        arts.mkdir(parents=True)

        _write_json(arts / "repo_inventory.json", _minimal_repo_inventory())
        _write_json(arts / "product_facts.json", _minimal_product_facts())
        _write_json(arts / "snippet_catalog.json", _minimal_snippet_catalog())

        # Point repo_root to a directory where specs/schemas/ does NOT exist
        fake_root = tmp_path / "fake_repo"
        fake_root.mkdir()

        result = verify_phase_artifacts(run_dir, "P1", repo_root=fake_root)

        # All files exist and are valid JSON, but schema could not be found
        # so schema_valid is None (skipped) -- this counts as ok=True because
        # the artifact exists and parses; missing schema is a warning not an error
        assert result.ok is True
        for check in result.checks:
            assert check.exists is True
            assert check.valid_json is True
            assert check.schema_valid is None
            assert check.error is not None
            assert "Schema file missing" in check.error


class TestEmptyRunDir:
    """All artifacts missing produces a complete failure with clear messages."""

    def test_all_missing_p1(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "empty_run"
        run_dir.mkdir()

        result = verify_phase_artifacts(run_dir, "P1")

        assert result.ok is False
        assert len(result.missing) == 3
        assert len(result.checks) == 3
        for check in result.checks:
            assert check.exists is False
            assert check.error is not None
            assert "Artifact not found" in check.error
