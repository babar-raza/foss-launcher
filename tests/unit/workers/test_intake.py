"""Tests for the Intake worker.

TC-4057 additions:
- Platform coverage: go, rust, php, ruby, kotlin, swift, cpp no longer get Python defaults
- Provenance tracking: field_provenance in artifact + 4-tuple return from _resolve_identity
- Unknown platform warning
"""
from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TYPE_CHECKING
from unittest.mock import patch, MagicMock

import pytest

from launcher.models.intake import IntakeBundle
from launcher.models.run_config import RunConfig
from launcher.orchestrator.worker_contract import SelfReviewResult, WorkerContext
from launcher.workers.intake.worker import (
    IntakeWorker,
    _resolve_identity,
    _resolve_tier,
    create_worker,
)


# ===================================================================
# Fixtures
# ===================================================================


@pytest.fixture
def cells_config() -> RunConfig:
    return RunConfig(
        family="cells",
        platform="python",
        repo_url="https://github.com/aspose/aspose-cells-foss-python",
        launch_tier="auto",
    )


@pytest.fixture
def cells_config_explicit_tier() -> RunConfig:
    return RunConfig(
        family="cells",
        platform="python",
        repo_url="https://github.com/aspose/aspose-cells-foss-python",
        launch_tier="full",
    )


@pytest.fixture
def worker() -> IntakeWorker:
    return create_worker()


def _mock_clone(tmp_path: Path):
    """Return a mock for clone_repo_cached that creates a real directory."""
    repo_dir = tmp_path / "work" / "clone_cache" / "abc123"
    repo_dir.mkdir(parents=True, exist_ok=True)
    return patch(
        "launcher.workers.intake.worker.clone_repo_cached",
        return_value=(repo_dir, "a" * 40, True),
    )


@pytest.fixture
def context(cells_config: RunConfig, tmp_path: Path) -> WorkerContext:
    return WorkerContext(
        run_id="test-run-001",
        run_dir=tmp_path,
        config=cells_config,
    )


@pytest.fixture
def context_explicit_tier(cells_config_explicit_tier: RunConfig, tmp_path: Path) -> WorkerContext:
    return WorkerContext(
        run_id="test-run-002",
        run_dir=tmp_path,
        config=cells_config_explicit_tier,
    )


# ===================================================================
# Identity resolution
# ===================================================================


class TestResolveIdentity:
    # SR-04: Clear module-level cache between tests so patching _FAMILIES_YAML works correctly.
    def setup_method(self):
        from launcher.workers.intake.worker import _clear_families_cache
        _clear_families_cache()

    def teardown_method(self):
        from launcher.workers.intake.worker import _clear_families_cache
        _clear_families_cache()

    def test_resolve_from_families_yaml(self):
        """Should derive display_name and canonical_import from families.yaml."""
        display_name, canonical_import, runtime_import, provenance = _resolve_identity("cells", "python")
        assert "Cells" in display_name or "cells" in display_name.lower()
        assert canonical_import  # non-empty

    def test_resolve_unknown_family_fallback(self, tmp_path: Path):
        """Unknown family should produce a generic (non-Aspose) fallback with inferred_default provenance.
        TC-4060: default no longer embeds 'Aspose' brand."""
        with patch("launcher.shared.identity._FAMILIES_YAML", tmp_path / "nonexistent.yaml"):
            display_name, canonical_import, runtime_import, provenance = _resolve_identity("unknown", "python")
        assert "Unknown" in display_name
        assert "Aspose" not in display_name, "inferred_default must not embed Aspose brand"
        # TC-4060: default is now {family}_foss, not aspose_{family}_foss
        assert canonical_import == "unknown_foss"
        assert provenance["display_name"] == "inferred_default"
        assert provenance["canonical_import"] == "inferred_default"

    def test_resolve_note_family(self):
        display_name, canonical_import, runtime_import, provenance = _resolve_identity("note", "python")
        assert "Note" in display_name
        assert canonical_import  # non-empty

    def test_resolve_runtime_import_cells(self):
        """cells Python family should derive runtime_import aspose.cells."""
        _, _, runtime_import, _ = _resolve_identity("cells", "python")
        assert runtime_import == "aspose.cells"

    def test_resolve_runtime_import_3d_override(self):
        """3d Python family should use runtime_import_overrides -> aspose.threed."""
        _, _, runtime_import, _ = _resolve_identity("3d", "python")
        assert runtime_import == "aspose.threed"

    def test_resolve_runtime_import_empty_for_node(self):
        """Node platform has no runtime_import_tpl, so runtime_import should be empty."""
        _, _, runtime_import, _ = _resolve_identity("cells", "node")
        assert runtime_import == ""

    # ---- TC-4057: provenance tracking ----------------------------------------

    def test_provenance_families_yaml_for_known_family_platform(self):
        """Known family + known platform → both fields marked 'families_yaml'."""
        _, _, _, provenance = _resolve_identity("cells", "python")
        assert provenance["display_name"] == "families_yaml"
        assert provenance["canonical_import"] == "families_yaml"

    def test_provenance_inferred_default_when_no_yaml(self, tmp_path: Path):
        """No families.yaml → all fields 'inferred_default'."""
        with patch("launcher.shared.identity._FAMILIES_YAML", tmp_path / "missing.yaml"):
            _, _, _, provenance = _resolve_identity("cells", "python")
        assert provenance["display_name"] == "inferred_default"
        assert provenance["canonical_import"] == "inferred_default"
        assert provenance["runtime_import"] == "inferred_default"

    def test_provenance_families_yaml_fallback_for_unlisted_platform(self):
        """Listed family but unlisted platform → canonical_import provenance = 'families_yaml_fallback'."""
        # Use a made-up platform not in families.yaml
        _, canonical_import, _, provenance = _resolve_identity("cells", "cobol")
        assert provenance["canonical_import"] == "families_yaml_fallback"
        # The import should be the Python-shaped fallback (since no template exists)
        assert "cells" in canonical_import.lower()

    # ---- TC-4057: platform coverage -------------------------------------------

    def test_go_platform_not_python_shaped(self):
        """Go repos must NOT get the Python-shaped 'aspose_{family}_foss' canonical_import."""
        _, canonical_import, _, provenance = _resolve_identity("cells", "go")
        assert "aspose_cells_foss" != canonical_import, (
            "Go platform got Python-shaped canonical_import — families.yaml missing go entry"
        )
        assert provenance["canonical_import"] == "families_yaml"

    def test_rust_platform_not_python_shaped(self):
        """Rust repos must NOT get 'aspose_{family}_foss' as canonical_import."""
        _, canonical_import, _, provenance = _resolve_identity("cells", "rust")
        # Rust uses 'aspose_{family}' without '_foss' suffix
        assert canonical_import == "aspose_cells", (
            f"Expected 'aspose_cells' for rust, got {canonical_import!r}"
        )
        assert provenance["canonical_import"] == "families_yaml"

    def test_php_platform_import_not_python_shaped(self):
        """PHP repos must NOT get Python-shaped canonical_import."""
        _, canonical_import, _, provenance = _resolve_identity("cells", "php")
        assert "aspose_cells_foss" != canonical_import
        assert "Aspose" in canonical_import or "aspose" in canonical_import.lower()
        assert provenance["canonical_import"] == "families_yaml"

    def test_ruby_platform_import_not_python_shaped(self):
        """Ruby repos must NOT get Python-shaped canonical_import."""
        _, canonical_import, _, provenance = _resolve_identity("cells", "ruby")
        assert "aspose_cells_foss" != canonical_import
        assert provenance["canonical_import"] == "families_yaml"

    def test_kotlin_platform_import(self):
        """Kotlin repos use com.aspose.{family} pattern."""
        _, canonical_import, _, provenance = _resolve_identity("cells", "kotlin")
        assert "com.aspose" in canonical_import
        assert provenance["canonical_import"] == "families_yaml"

    def test_swift_platform_import(self):
        """Swift repos use Aspose{Family} pattern."""
        _, canonical_import, _, provenance = _resolve_identity("cells", "swift")
        assert "Aspose" in canonical_import
        assert provenance["canonical_import"] == "families_yaml"

    def test_cpp_platform_import(self):
        """C++ repos use Aspose::{Family} pattern."""
        _, canonical_import, _, provenance = _resolve_identity("cells", "cpp")
        assert "Aspose" in canonical_import
        assert provenance["canonical_import"] == "families_yaml"

    def test_typescript_platform_import(self):
        """TypeScript repos use @aspose/{family} pattern (same as node)."""
        _, canonical_import, _, provenance = _resolve_identity("cells", "typescript")
        assert "@aspose" in canonical_import
        assert provenance["canonical_import"] == "families_yaml"

    def test_dotnet_platform_import(self):
        """dotnet platform uses Aspose.{Family} pattern."""
        _, canonical_import, _, provenance = _resolve_identity("cells", "dotnet")
        assert "Aspose." in canonical_import
        assert provenance["canonical_import"] == "families_yaml"

    def test_java_platform_import(self):
        """Java platform uses com.aspose.{family} pattern."""
        _, canonical_import, _, provenance = _resolve_identity("cells", "java")
        assert "com.aspose" in canonical_import
        assert provenance["canonical_import"] == "families_yaml"

    # ---- TC-4057: unknown platform warning ------------------------------------

    def test_unknown_platform_emits_warning(self, caplog):
        """Platform not in families.yaml should emit a WARNING log."""
        import logging
        with caplog.at_level(logging.WARNING, logger="launcher.shared.identity"):
            _, _, _, provenance = _resolve_identity("cells", "cobol")
        assert any("not found in families.yaml" in record.message for record in caplog.records), (
            "Expected WARNING about unknown platform, got none"
        )


# ===================================================================
# Tier resolution
# ===================================================================


class TestResolveTier:
    def test_auto_maps_to_core(self):
        assert _resolve_tier("auto") == "core"

    def test_explicit_full_passes_through(self):
        assert _resolve_tier("full") == "full"

    def test_explicit_minimal_passes_through(self):
        assert _resolve_tier("minimal") == "minimal"

    def test_explicit_core_passes_through(self):
        assert _resolve_tier("core") == "core"


# ===================================================================
# Worker run
# ===================================================================


class TestIntakeWorkerRun:
    @pytest.mark.asyncio
    async def test_produces_intake_bundle(self, worker: IntakeWorker, context: WorkerContext, tmp_path: Path):
        from launcher.models.base import LauncherBaseModel
        with _mock_clone(tmp_path):
            result = await worker.run(LauncherBaseModel(), context)
        assert isinstance(result, IntakeBundle)

    @pytest.mark.asyncio
    async def test_family_and_platform_preserved(self, worker: IntakeWorker, context: WorkerContext, tmp_path: Path):
        from launcher.models.base import LauncherBaseModel
        with _mock_clone(tmp_path):
            result = await worker.run(LauncherBaseModel(), context)
        assert result.family == "cells"
        assert result.platform == "python"

    @pytest.mark.asyncio
    async def test_repo_url_preserved(self, worker: IntakeWorker, context: WorkerContext, tmp_path: Path):
        from launcher.models.base import LauncherBaseModel
        with _mock_clone(tmp_path):
            result = await worker.run(LauncherBaseModel(), context)
        assert result.repo_url == "https://github.com/aspose/aspose-cells-foss-python"

    @pytest.mark.asyncio
    async def test_display_name_populated(self, worker: IntakeWorker, context: WorkerContext, tmp_path: Path):
        from launcher.models.base import LauncherBaseModel
        with _mock_clone(tmp_path):
            result = await worker.run(LauncherBaseModel(), context)
        assert result.display_name
        assert "Cells" in result.display_name

    @pytest.mark.asyncio
    async def test_canonical_import_populated(self, worker: IntakeWorker, context: WorkerContext, tmp_path: Path):
        from launcher.models.base import LauncherBaseModel
        with _mock_clone(tmp_path):
            result = await worker.run(LauncherBaseModel(), context)
        assert result.canonical_import

    @pytest.mark.asyncio
    async def test_auto_tier_resolved(self, worker: IntakeWorker, context: WorkerContext, tmp_path: Path):
        from launcher.models.base import LauncherBaseModel
        with _mock_clone(tmp_path):
            result = await worker.run(LauncherBaseModel(), context)
        assert result.launch_tier == "core"

    @pytest.mark.asyncio
    async def test_explicit_tier_preserved(self, worker: IntakeWorker, context_explicit_tier: WorkerContext, tmp_path: Path):
        from launcher.models.base import LauncherBaseModel
        with _mock_clone(tmp_path):
            result = await worker.run(LauncherBaseModel(), context_explicit_tier)
        assert result.launch_tier == "full"

    @pytest.mark.asyncio
    async def test_discovered_at_populated(self, worker: IntakeWorker, context: WorkerContext, tmp_path: Path):
        from launcher.models.base import LauncherBaseModel
        with _mock_clone(tmp_path):
            result = await worker.run(LauncherBaseModel(), context)
        assert result.discovered_at
        from datetime import datetime
        datetime.fromisoformat(result.discovered_at)

    @pytest.mark.asyncio
    async def test_repo_sha_populated(self, worker: IntakeWorker, context: WorkerContext, tmp_path: Path):
        from launcher.models.base import LauncherBaseModel
        with _mock_clone(tmp_path):
            result = await worker.run(LauncherBaseModel(), context)
        assert result.repo_sha == "a" * 40

    @pytest.mark.asyncio
    async def test_repo_dir_populated(self, worker: IntakeWorker, context: WorkerContext, tmp_path: Path):
        from launcher.models.base import LauncherBaseModel
        with _mock_clone(tmp_path):
            result = await worker.run(LauncherBaseModel(), context)
        assert result.repo_dir
        assert Path(result.repo_dir).is_dir()

    @pytest.mark.asyncio
    async def test_clone_exception_raises_runtime_error(self, worker: IntakeWorker, context: WorkerContext):
        """TC-4056 Fix 1: Clone failure raises RuntimeError immediately — no silent broken bundle."""
        from launcher.models.base import LauncherBaseModel
        with patch(
            "launcher.workers.intake.worker.clone_repo_cached",
            side_effect=subprocess.CalledProcessError(128, "git clone"),
        ):
            with pytest.raises(RuntimeError, match=r"\[Intake\] Clone failed"):
                await worker.run(LauncherBaseModel(), context)

    @pytest.mark.asyncio
    async def test_clone_completed_event_emitted(self, worker: IntakeWorker, context: WorkerContext, tmp_path: Path):
        """Successful clone emits a clone_completed event."""
        from launcher.models.base import LauncherBaseModel
        context.emit_event = MagicMock()
        with _mock_clone(tmp_path):
            await worker.run(LauncherBaseModel(), context)
        clone_events = [
            call for call in context.emit_event.call_args_list
            if call[0][0] == "clone_completed"
        ]
        assert len(clone_events) == 1
        payload = clone_events[0][0][1]
        assert payload["repo_sha"] == "a" * 40
        assert payload["fresh"] is True

    @pytest.mark.asyncio
    async def test_no_clone_event_on_failure(self, worker: IntakeWorker, context: WorkerContext):
        """TC-4056 Fix 1: Clone failure raises before any event is emitted."""
        from launcher.models.base import LauncherBaseModel
        context.emit_event = MagicMock()
        with patch(
            "launcher.workers.intake.worker.clone_repo_cached",
            side_effect=subprocess.CalledProcessError(128, "git clone"),
        ):
            with pytest.raises(RuntimeError):
                await worker.run(LauncherBaseModel(), context)
        clone_events = [
            call for call in context.emit_event.call_args_list
            if call[0][0] == "clone_completed"
        ]
        assert len(clone_events) == 0

    @pytest.mark.asyncio
    async def test_artifact_contains_field_provenance(
        self, worker: IntakeWorker, context: WorkerContext, tmp_path: Path
    ):
        """TC-4057: intake_bundle.json must contain field_provenance so human reviewers
        can tell which fields were families.yaml-derived vs. inferred defaults."""
        from launcher.models.base import LauncherBaseModel
        import json

        written: dict[str, Any] = {}

        def _capture_write(name: str, data: Any):
            if name == "intake_bundle.json":
                written.update(data)

        context.store.write_json = _capture_write
        with _mock_clone(tmp_path):
            await worker.run(LauncherBaseModel(), context)

        assert "field_provenance" in written, "intake_bundle.json missing field_provenance key"
        prov = written["field_provenance"]
        assert "display_name" in prov
        assert "canonical_import" in prov
        # For known family+platform (cells/python), both should be families_yaml
        assert prov["display_name"] == "families_yaml"
        assert prov["canonical_import"] == "families_yaml"

    @pytest.mark.asyncio
    async def test_config_override_recorded_in_provenance(
        self, worker: IntakeWorker, tmp_path: Path
    ):
        """TC-4057: When RunConfig explicitly sets display_name, provenance must reflect 'config_override'."""
        from launcher.models.base import LauncherBaseModel

        config = RunConfig(
            family="cells",
            platform="python",
            repo_url="https://github.com/aspose/cells",
            display_name="My Custom Display Name",
        )
        ctx = WorkerContext(run_id="t", run_dir=tmp_path, config=config)

        written: dict[str, Any] = {}

        def _capture_write(name: str, data: Any):
            if name == "intake_bundle.json":
                written.update(data)

        ctx.store.write_json = _capture_write

        with _mock_clone(tmp_path):
            result = await worker.run(LauncherBaseModel(), ctx)

        assert result.display_name == "My Custom Display Name"
        assert written.get("field_provenance", {}).get("display_name") == "config_override"


# ===================================================================
# Self-review
# ===================================================================


class TestIntakeWorkerSelfReview:
    @pytest.mark.asyncio
    async def test_valid_bundle_passes(self, worker: IntakeWorker, tmp_path: Path):
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        # A real clone is never empty — add a sentinel file so the non-empty check passes
        (repo_dir / ".clone_sha").write_text("abc123", encoding="utf-8")
        bundle = IntakeBundle(
            family="cells",
            platform="python",
            repo_url="https://github.com/aspose/cells",
            display_name="Aspose.Cells FOSS for Python",
            canonical_import="aspose_cells_foss",
            launch_tier="core",
            repo_dir=str(repo_dir),
        )
        result = await worker.self_review(bundle)
        assert result.passed

    @pytest.mark.asyncio
    async def test_empty_display_name_fails(self, worker: IntakeWorker, tmp_path: Path):
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        bundle = IntakeBundle(
            family="cells",
            platform="python",
            repo_url="https://github.com/aspose/cells",
            display_name="",
            canonical_import="aspose_cells_foss",
            launch_tier="core",
            repo_dir=str(repo_dir),
        )
        result = await worker.self_review(bundle)
        assert not result.passed

    @pytest.mark.asyncio
    async def test_empty_canonical_import_fails(self, worker: IntakeWorker, tmp_path: Path):
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        bundle = IntakeBundle(
            family="cells",
            platform="python",
            repo_url="https://github.com/aspose/cells",
            display_name="Aspose.Cells FOSS",
            canonical_import="",
            launch_tier="core",
            repo_dir=str(repo_dir),
        )
        result = await worker.self_review(bundle)
        assert not result.passed

    @pytest.mark.asyncio
    async def test_empty_repo_dir_fails(self, worker: IntakeWorker):
        bundle = IntakeBundle(
            family="cells",
            platform="python",
            repo_url="https://github.com/aspose/cells",
            display_name="Aspose.Cells FOSS",
            canonical_import="aspose_cells_foss",
            launch_tier="core",
            repo_dir="",
        )
        result = await worker.self_review(bundle)
        assert not result.passed

    @pytest.mark.asyncio
    async def test_non_intake_bundle_fails(self, worker: IntakeWorker):
        from launcher.models.base import LauncherBaseModel
        result = await worker.self_review(LauncherBaseModel())
        assert not result.passed


# ===================================================================
# Worker factory
# ===================================================================


class TestCreateWorker:
    def test_creates_intake_worker(self):
        w = create_worker()
        assert isinstance(w, IntakeWorker)
        assert w.name == "intake"


# ===================================================================
# SR-01: _FAMILIES_YAML path is __file__-relative (not CWD-relative)
# ===================================================================


class TestFamiliesYamlPathResolution:
    """SR-01: families.yaml must resolve correctly regardless of CWD."""

    def test_resolve_identity_from_arbitrary_cwd(self, tmp_path):
        """SR-01: _resolve_identity returns families_yaml provenance even when CWD is /tmp."""
        import os
        from launcher.workers.intake.worker import _clear_families_cache, _resolve_identity

        _clear_families_cache()
        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            result = _resolve_identity("cells", "python")
            assert result.provenance["display_name"] == "families_yaml", (
                f"Expected families_yaml provenance but got {result.provenance!r}. "
                "_FAMILIES_YAML path is likely still CWD-relative."
            )
        finally:
            os.chdir(old_cwd)
            _clear_families_cache()


# ===================================================================
# SR-03: _resolve_identity returns IdentityResolution NamedTuple
# ===================================================================


class TestIdentityResolutionNamedTuple:
    """SR-03: _resolve_identity returns a NamedTuple supporting attribute access."""

    def setup_method(self):
        from launcher.workers.intake.worker import _clear_families_cache
        _clear_families_cache()

    def teardown_method(self):
        from launcher.workers.intake.worker import _clear_families_cache
        _clear_families_cache()

    def test_resolve_identity_returns_named_tuple(self):
        """SR-03: attribute access works (r.display_name) and equals positional (r[0])."""
        from launcher.workers.intake.worker import IdentityResolution, _resolve_identity

        r = _resolve_identity("cells", "python")
        assert isinstance(r, IdentityResolution), f"Expected IdentityResolution, got {type(r)}"
        # Attribute access must equal positional access
        assert r.display_name == r[0]
        assert r.canonical_import == r[1]
        assert r.runtime_import == r[2]
        assert r.provenance == r[3]

    def test_positional_unpack_still_works(self):
        """SR-03: positional unpacking must remain backward-compatible."""
        from launcher.workers.intake.worker import _resolve_identity

        display_name, canonical_import, runtime_import, provenance = _resolve_identity(
            "cells", "python"
        )
        assert display_name
        assert canonical_import
        assert isinstance(provenance, dict)


# ===================================================================
# SR-04: families.yaml is read at most once per process (module-level cache)
# ===================================================================


class TestFamiliesYamlCache:
    """SR-04: _load_families_data() caches the YAML — one file read per process."""

    def setup_method(self):
        from launcher.workers.intake.worker import _clear_families_cache
        _clear_families_cache()

    def teardown_method(self):
        from launcher.workers.intake.worker import _clear_families_cache
        _clear_families_cache()

    def test_families_yaml_read_once_per_process(self):
        """SR-04: two calls to _resolve_identity open families.yaml at most once."""
        from unittest.mock import patch, mock_open
        import builtins
        from launcher.workers.intake.worker import _clear_families_cache, _resolve_identity
        import yaml

        _clear_families_cache()
        real_open = builtins.open
        open_call_count = []

        def counting_open(file, *args, **kwargs):
            if "families.yaml" in str(file):
                open_call_count.append(1)
            return real_open(file, *args, **kwargs)

        with patch("builtins.open", side_effect=counting_open):
            _resolve_identity("cells", "python")
            _resolve_identity("note", "java")

        assert len(open_call_count) <= 1, (
            f"families.yaml was opened {len(open_call_count)} times across 2 calls; expected ≤1"
        )

    def test_clear_cache_resets_on_next_call(self):
        """SR-04: after _clear_families_cache, next call reads the file again."""
        from unittest.mock import patch
        import builtins
        from launcher.workers.intake.worker import _clear_families_cache, _resolve_identity

        open_calls = []
        real_open = builtins.open

        def counting_open(file, *args, **kwargs):
            if "families.yaml" in str(file):
                open_calls.append(1)
            return real_open(file, *args, **kwargs)

        _clear_families_cache()
        with patch("builtins.open", side_effect=counting_open):
            _resolve_identity("cells", "python")
        count_before = len(open_calls)

        _clear_families_cache()
        with patch("builtins.open", side_effect=counting_open):
            _resolve_identity("cells", "python")
        count_after = len(open_calls)

        assert count_after > count_before, (
            "Expected a new file read after _clear_families_cache, but open was not called again"
        )


# ===================================================================
# TC-4060: Acquisition confidence + repo signals + clone hardening
# ===================================================================


class TestAcquisitionConfidence:
    """TC-4060: _compute_acquisition_confidence returns correct trust signal."""

    def test_all_families_yaml_is_high(self):
        from launcher.workers.intake.worker import _compute_acquisition_confidence
        prov = {
            "display_name": "families_yaml",
            "canonical_import": "families_yaml",
            "runtime_import": "families_yaml",
        }
        assert _compute_acquisition_confidence(prov) == "high"

    def test_config_override_only_is_high(self):
        from launcher.workers.intake.worker import _compute_acquisition_confidence
        prov = {
            "display_name": "config_override",
            "canonical_import": "config_override",
            "runtime_import": "config_override",
        }
        assert _compute_acquisition_confidence(prov) == "high"

    def test_families_yaml_fallback_is_medium(self):
        from launcher.workers.intake.worker import _compute_acquisition_confidence
        prov = {
            "display_name": "families_yaml",
            "canonical_import": "families_yaml_fallback",
            "runtime_import": "inferred_default",
        }
        # inferred_default present → low
        assert _compute_acquisition_confidence(prov) == "low"

    def test_any_inferred_default_is_low(self):
        from launcher.workers.intake.worker import _compute_acquisition_confidence
        prov = {
            "display_name": "families_yaml_fallback",
            "canonical_import": "families_yaml_fallback",
            "runtime_import": "families_yaml_fallback",
        }
        assert _compute_acquisition_confidence(prov) == "medium"

    def test_mixed_fallback_only_is_medium(self):
        from launcher.workers.intake.worker import _compute_acquisition_confidence
        prov = {
            "display_name": "families_yaml",
            "canonical_import": "families_yaml_fallback",
            "runtime_import": "families_yaml",
        }
        assert _compute_acquisition_confidence(prov) == "medium"


class TestBuildRepoSignals:
    """TC-4060: _build_repo_signals returns correct structural signals."""

    def test_empty_dir_is_empty_clone(self, tmp_path: Path):
        from launcher.workers.intake.worker import _build_repo_signals
        empty = tmp_path / "empty_repo"
        empty.mkdir()
        signals = _build_repo_signals(empty)
        assert signals["is_empty_clone"] is True
        assert signals["readme_present"] is False
        assert signals["files_estimated"] == 0

    def test_dir_with_readme_md(self, tmp_path: Path):
        from launcher.workers.intake.worker import _build_repo_signals
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "README.md").write_text("# Test", encoding="utf-8")
        (repo / "setup.py").write_text("", encoding="utf-8")
        signals = _build_repo_signals(repo)
        assert signals["readme_present"] is True
        assert signals["is_empty_clone"] is False
        assert signals["files_estimated"] >= 2

    def test_nonexistent_dir_returns_empty(self, tmp_path: Path):
        from launcher.workers.intake.worker import _build_repo_signals
        signals = _build_repo_signals(tmp_path / "nonexistent")
        assert signals["is_empty_clone"] is True
        assert signals["readme_present"] is False

    def test_readme_rst_detected(self, tmp_path: Path):
        from launcher.workers.intake.worker import _build_repo_signals
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "README.rst").write_text("test", encoding="utf-8")
        signals = _build_repo_signals(repo)
        assert signals["readme_present"] is True

    def test_files_estimated_capped_at_100(self, tmp_path: Path):
        """PH-03: cap is 100, not 200 — matches TC-4060 Step 4 spec."""
        from launcher.workers.intake.worker import _build_repo_signals
        repo = tmp_path / "repo"
        repo.mkdir()
        for i in range(150):
            (repo / f"file_{i}.py").write_text("", encoding="utf-8")
        signals = _build_repo_signals(repo)
        assert signals["files_estimated"] == 100, (
            f"Expected files_estimated==100 for 150-file repo, got {signals['files_estimated']}"
        )


class TestArtifactAcquisitionConfidence:
    """TC-4060: intake_bundle.json contains acquisition_confidence and repo_signals."""

    def setup_method(self):
        from launcher.workers.intake.worker import _clear_families_cache
        _clear_families_cache()

    def teardown_method(self):
        from launcher.workers.intake.worker import _clear_families_cache
        _clear_families_cache()

    @pytest.mark.asyncio
    async def test_artifact_contains_acquisition_confidence(
        self, worker: "IntakeWorker", context: "WorkerContext", tmp_path: Path
    ):
        from launcher.models.base import LauncherBaseModel
        written: dict = {}

        def _capture(name: str, data):
            if name == "intake_bundle.json":
                written.update(data)

        context.store.write_json = _capture

        with _mock_clone(tmp_path):
            await worker.run(LauncherBaseModel(), context)

        assert "acquisition_confidence" in written, "acquisition_confidence missing from artifact"
        assert written["acquisition_confidence"] in ("high", "medium", "low")

    @pytest.mark.asyncio
    async def test_artifact_contains_repo_signals(
        self, worker: "IntakeWorker", context: "WorkerContext", tmp_path: Path
    ):
        from launcher.models.base import LauncherBaseModel
        written: dict = {}

        def _capture(name: str, data):
            if name == "intake_bundle.json":
                written.update(data)

        context.store.write_json = _capture

        with _mock_clone(tmp_path):
            await worker.run(LauncherBaseModel(), context)

        assert "repo_signals" in written, "repo_signals missing from artifact"
        rs = written["repo_signals"]
        assert "readme_present" in rs
        assert "is_empty_clone" in rs
        assert "files_estimated" in rs

    @pytest.mark.asyncio
    async def test_known_platform_yields_high_confidence(
        self, worker: "IntakeWorker", context: "WorkerContext", tmp_path: Path
    ):
        """cells/python is in families.yaml → acquisition_confidence should be 'high'."""
        from launcher.models.base import LauncherBaseModel
        written: dict = {}

        def _capture(name: str, data):
            if name == "intake_bundle.json":
                written.update(data)

        context.store.write_json = _capture

        with _mock_clone(tmp_path):
            await worker.run(LauncherBaseModel(), context)

        assert written.get("acquisition_confidence") == "high"


class TestFamiliesYamlFallbackWarning:
    """TC-4060: Warning fires on families_yaml_fallback provenance too, not just inferred_default."""

    def setup_method(self):
        from launcher.workers.intake.worker import _clear_families_cache
        _clear_families_cache()

    def teardown_method(self):
        from launcher.workers.intake.worker import _clear_families_cache
        _clear_families_cache()

    @pytest.mark.asyncio
    async def test_warning_fires_on_families_yaml_fallback_for_nonpython(
        self, worker: "IntakeWorker", tmp_path: Path, caplog
    ):
        """TC-4060: When platform is families_yaml_fallback and not python, warning must fire."""
        import logging
        from launcher.models.base import LauncherBaseModel

        # Use a platform not in families.yaml → provenance will be families_yaml_fallback
        config = RunConfig(
            family="cells",
            platform="cobol",  # not in families.yaml
            repo_url="https://github.com/example/cells-cobol",
        )
        ctx = WorkerContext(run_id="t-warn", run_dir=tmp_path, config=config)

        with caplog.at_level(logging.WARNING, logger="launcher.workers.intake.worker"):
            with _mock_clone(tmp_path):
                await worker.run(LauncherBaseModel(), ctx)

        messages = [r.message for r in caplog.records]
        assert any(
            "not matched in families.yaml" in m or "not found in families.yaml" in m
            for m in messages
        ), f"Expected canonical_import warning for unlisted platform, got: {messages}"


class TestCloneTimestamp:
    """TC-4060: clone.py writes .clone_timestamp and logs cache age."""

    def test_timestamp_written_after_fresh_clone(self, tmp_path: Path):
        """Fresh clone must write .clone_timestamp alongside .clone_sha."""
        from launcher.workers.intake.clone import clone_repo_cached, _CLONE_TIMESTAMP_MARKER

        cache_dir = tmp_path / ".clone_cache" / "abc"
        cache_dir.mkdir(parents=True)
        sha = "b" * 40

        with patch("launcher.workers.intake.clone.check_remote_sha", return_value=sha), \
             patch("launcher.workers.intake.clone.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            # Simulate the clone by writing expected files
            def _fake_run(cmd, **kw):
                # Simulate git clone writing a sentinel file
                (cache_dir / ".clone_sha").write_text(sha, encoding="utf-8")
                return MagicMock(returncode=0)
            mock_run.side_effect = _fake_run

            # patch _get_cache_dir to return our known cache_dir
            with patch("launcher.workers.intake.clone._get_cache_dir", return_value=cache_dir):
                with patch("launcher.workers.intake.clone._get_repo_sha", return_value=sha):
                    result = clone_repo_cached(
                        "https://github.com/test/repo",
                        family="test",
                        platform="python",
                        work_dir=tmp_path / "work",
                    )

        ts_file = cache_dir / _CLONE_TIMESTAMP_MARKER
        assert ts_file.exists(), ".clone_timestamp not written after clone"
        ts_content = ts_file.read_text(encoding="utf-8").strip()
        from datetime import datetime
        datetime.fromisoformat(ts_content)  # must be valid ISO timestamp

    def test_force_refresh_discards_existing_cache(self, tmp_path: Path):
        """force_refresh=True must trigger re-clone even when cache exists with matching SHA."""
        from launcher.workers.intake.clone import clone_repo_cached

        # Pre-populate a cache hit
        cache_dir = tmp_path / ".clone_cache" / "abc"
        cache_dir.mkdir(parents=True)
        sha = "c" * 40
        (cache_dir / ".clone_sha").write_text(sha, encoding="utf-8")
        sentinel = cache_dir / "sentinel.txt"
        sentinel.write_text("old", encoding="utf-8")

        clone_called = []

        def _fake_run(cmd, **kw):
            if "clone" in cmd:
                clone_called.append(True)
                # Re-create cache_dir as fresh clone
                cache_dir.mkdir(parents=True, exist_ok=True)
                (cache_dir / ".clone_sha").write_text(sha, encoding="utf-8")
            return MagicMock(returncode=0)

        with patch("launcher.workers.intake.clone.check_remote_sha", return_value=sha), \
             patch("launcher.workers.intake.clone.subprocess.run", side_effect=_fake_run), \
             patch("launcher.workers.intake.clone._get_cache_dir", return_value=cache_dir), \
             patch("launcher.workers.intake.clone._get_repo_sha", return_value=sha):
            clone_repo_cached(
                "https://github.com/test/repo",
                family="test",
                platform="python",
                work_dir=tmp_path / "work",
                force_refresh=True,
            )

        assert clone_called, "git clone was not called when force_refresh=True"

    def test_stale_cache_logs_warning(self, tmp_path: Path, caplog):
        """TC-4060: Cache older than 7 days must log a WARNING."""
        import logging
        from datetime import timedelta
        from launcher.workers.intake.clone import _log_cache_age, _CLONE_TIMESTAMP_MARKER

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        stale_ts = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        (cache_dir / _CLONE_TIMESTAMP_MARKER).write_text(stale_ts, encoding="utf-8")

        with caplog.at_level(logging.WARNING, logger="launcher.workers.intake.clone"):
            _log_cache_age(cache_dir, "https://github.com/test/repo")

        assert any("days old" in r.message for r in caplog.records), (
            "Expected stale cache WARNING but got none"
        )


# ===================================================================
# TC-4072: self_review — Python-shaped canonical_import detection
# ===================================================================


class TestSelfReviewTC4072:
    """TC-4072: self_review detects Python-shaped import on non-Python platforms."""

    @pytest.mark.asyncio
    async def test_python_shaped_import_fails_for_typescript(self, worker: "IntakeWorker", tmp_path: Path):
        """TC-4072: canonical_import ending with '_foss' on a TypeScript platform → high finding."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        (repo_dir / ".clone_sha").write_text("abc", encoding="utf-8")
        bundle = IntakeBundle(
            family="cells",
            platform="typescript",
            repo_url="https://github.com/test/cells-ts",
            display_name="Aspose.Cells FOSS for TypeScript",
            canonical_import="cells_foss",  # Python-shaped — wrong for TypeScript
            launch_tier="core",
            repo_dir=str(repo_dir),
        )
        result = await worker.self_review(bundle)
        assert not result.passed, "Expected self_review to fail for Python-shaped import on TypeScript"
        high_findings = [f for f in result.findings if f.get("severity") == "high" and f.get("category") == "identity"]
        assert high_findings, "Expected a high-severity identity finding"
        assert any("Python-shaped" in f["message"] or "_foss" in f["message"] for f in high_findings)

    @pytest.mark.asyncio
    async def test_correct_typescript_import_passes(self, worker: "IntakeWorker", tmp_path: Path):
        """TC-4072: TypeScript with @aspose/cells canonical_import passes self_review."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        (repo_dir / ".clone_sha").write_text("abc", encoding="utf-8")
        bundle = IntakeBundle(
            family="cells",
            platform="typescript",
            repo_url="https://github.com/test/cells-ts",
            display_name="Aspose.Cells FOSS for TypeScript",
            canonical_import="@aspose/cells",  # correct TypeScript import
            launch_tier="core",
            repo_dir=str(repo_dir),
        )
        result = await worker.self_review(bundle)
        # No high-severity identity finding for Python-shaped import
        high_identity = [f for f in result.findings if f.get("severity") == "high" and f.get("category") == "identity"]
        assert not high_identity, f"Unexpected high identity findings: {high_identity}"

    @pytest.mark.asyncio
    async def test_python_empty_runtime_import_is_medium_not_blocking(self, worker: "IntakeWorker", tmp_path: Path):
        """TC-4072: Python platform with empty runtime_import → medium finding, still passes."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        (repo_dir / ".clone_sha").write_text("abc", encoding="utf-8")
        bundle = IntakeBundle(
            family="cells",
            platform="python",
            repo_url="https://github.com/test/cells-py",
            display_name="Aspose.Cells FOSS for Python",
            canonical_import="aspose_cells_foss",
            runtime_import="",  # empty
            launch_tier="core",
            repo_dir=str(repo_dir),
        )
        result = await worker.self_review(bundle)
        # Medium finding present but does NOT block (passed=True if no HIGH)
        medium_findings = [f for f in result.findings if f.get("severity") == "medium"]
        assert medium_findings, "Expected medium finding for empty runtime_import on Python"
        assert result.passed, "Empty runtime_import on Python should NOT block (medium only)"

    @pytest.mark.asyncio
    async def test_python_platform_not_flagged_for_foss_suffix(self, worker: "IntakeWorker", tmp_path: Path):
        """TC-4072: Python platform with _foss suffix canonical_import does NOT trigger Python-shaped check."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        (repo_dir / ".clone_sha").write_text("abc", encoding="utf-8")
        bundle = IntakeBundle(
            family="cells",
            platform="python",
            repo_url="https://github.com/test/cells-py",
            display_name="Aspose.Cells FOSS for Python",
            canonical_import="aspose_cells_foss",
            runtime_import="aspose.cells",
            launch_tier="core",
            repo_dir=str(repo_dir),
        )
        result = await worker.self_review(bundle)
        # No high identity finding (python + _foss is correct)
        high_identity = [f for f in result.findings if f.get("severity") == "high" and f.get("category") == "identity"]
        assert not high_identity, f"Python with _foss should not trigger identity high: {high_identity}"
        assert result.passed


# ===================================================================
# TC-4072: _build_repo_signals — manifest file detection
# ===================================================================


class TestBuildRepoSignalsManifestDetection:
    """TC-4072: _build_repo_signals detects manifest files and infers language."""

    def test_package_json_detected(self, tmp_path: Path):
        from launcher.workers.intake.worker import _build_repo_signals
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "package.json").write_text('{"name": "@aspose/cells"}', encoding="utf-8")
        signals = _build_repo_signals(repo)
        assert "package.json" in signals["detected_manifest_files"]
        assert signals["inferred_language"] == "node/typescript"

    def test_pyproject_toml_detected(self, tmp_path: Path):
        from launcher.workers.intake.worker import _build_repo_signals
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "pyproject.toml").write_text("[project]\nname = 'aspose-cells'", encoding="utf-8")
        signals = _build_repo_signals(repo)
        assert "pyproject.toml" in signals["detected_manifest_files"]
        assert signals["inferred_language"] == "python"

    def test_go_mod_detected(self, tmp_path: Path):
        from launcher.workers.intake.worker import _build_repo_signals
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "go.mod").write_text("module github.com/aspose/cells-go", encoding="utf-8")
        signals = _build_repo_signals(repo)
        assert "go.mod" in signals["detected_manifest_files"]
        assert signals["inferred_language"] == "go"

    def test_cargo_toml_detected(self, tmp_path: Path):
        from launcher.workers.intake.worker import _build_repo_signals
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "Cargo.toml").write_text('[package]\nname = "aspose-cells"', encoding="utf-8")
        signals = _build_repo_signals(repo)
        assert "Cargo.toml" in signals["detected_manifest_files"]
        assert signals["inferred_language"] == "rust"

    def test_csproj_detected(self, tmp_path: Path):
        from launcher.workers.intake.worker import _build_repo_signals
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "Aspose.Cells.csproj").write_text("<Project/>", encoding="utf-8")
        signals = _build_repo_signals(repo)
        assert "Aspose.Cells.csproj" in signals["detected_manifest_files"]
        assert signals["inferred_language"] == "dotnet"

    def test_no_manifest_yields_empty_language(self, tmp_path: Path):
        from launcher.workers.intake.worker import _build_repo_signals
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "README.md").write_text("# test", encoding="utf-8")
        (repo / "main.go").write_text("package main", encoding="utf-8")
        signals = _build_repo_signals(repo)
        assert signals["detected_manifest_files"] == []
        assert signals["inferred_language"] == ""

    def test_existing_signals_still_present(self, tmp_path: Path):
        """TC-4072: new fields don't break existing readme_present/is_empty_clone/files_estimated."""
        from launcher.workers.intake.worker import _build_repo_signals
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "README.md").write_text("# test", encoding="utf-8")
        (repo / "pyproject.toml").write_text("[project]", encoding="utf-8")
        signals = _build_repo_signals(repo)
        assert "readme_present" in signals
        assert "is_empty_clone" in signals
        assert "files_estimated" in signals
        assert "detected_manifest_files" in signals
        assert "inferred_language" in signals
        assert signals["readme_present"] is True
        assert signals["is_empty_clone"] is False


# ===================================================================
# P1-C: families.yaml missing — must log WARNING (TC-4088)
# ===================================================================


class TestFamiliesYamlMissingWarning:
    """P1-C: missing families.yaml must emit a WARNING, not silently return {}."""

    def test_families_yaml_missing_logs_warning(self, tmp_path, caplog):
        """P1-C: missing families.yaml should log a WARNING, not silently return {}."""
        import logging
        from launcher.shared.identity import _clear_families_cache, resolve_identity
        from unittest.mock import patch

        nonexistent = tmp_path / "nonexistent_families.yaml"
        _clear_families_cache()
        try:
            with patch("launcher.shared.identity._FAMILIES_YAML", nonexistent):
                _clear_families_cache()
                with caplog.at_level(logging.WARNING, logger="launcher.shared.identity"):
                    result = resolve_identity("testfamily", "python")
        finally:
            _clear_families_cache()

        # Should have logged a warning about missing file
        assert any(
            "families.yaml" in r.message and "not found" in r.message
            for r in caplog.records
        ), f"Expected families.yaml 'not found' warning, got: {[r.message for r in caplog.records]}"

    def test_families_yaml_missing_returns_defaults(self, tmp_path):
        """P1-C: missing families.yaml returns inferred defaults, not an error."""
        from launcher.shared.identity import _clear_families_cache, resolve_identity
        from unittest.mock import patch

        nonexistent = tmp_path / "no_such_file.yaml"
        _clear_families_cache()
        try:
            with patch("launcher.shared.identity._FAMILIES_YAML", nonexistent):
                _clear_families_cache()
                result = resolve_identity("myfamily", "python")
        finally:
            _clear_families_cache()

        # Should still return a valid IdentityResolution with inferred defaults
        assert result.display_name
        assert result.canonical_import
        assert all(v == "inferred_default" for v in result.provenance.values())

    def test_families_yaml_present_no_warning(self, tmp_path, caplog):
        """P1-C: when families.yaml exists, no 'not found' warning is emitted."""
        import logging
        import yaml
        from launcher.shared.identity import _clear_families_cache, resolve_identity
        from unittest.mock import patch

        # Create a minimal valid families.yaml
        families_yaml = tmp_path / "families.yaml"
        families_yaml.write_text(
            yaml.dump({"families": {}, "platforms": {}}), encoding="utf-8"
        )

        _clear_families_cache()
        try:
            with patch("launcher.shared.identity._FAMILIES_YAML", families_yaml):
                _clear_families_cache()
                with caplog.at_level(logging.WARNING, logger="launcher.shared.identity"):
                    result = resolve_identity("somefamily", "python")
        finally:
            _clear_families_cache()

        # Should NOT log a 'not found' warning (file exists)
        not_found_warnings = [
            r for r in caplog.records
            if "not found" in r.message and "families.yaml" in r.message
        ]
        assert not not_found_warnings, (
            f"Unexpected 'not found' warning when file exists: {[r.message for r in not_found_warnings]}"
        )
