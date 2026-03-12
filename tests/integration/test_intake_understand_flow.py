"""Integration test: Intake → Understand data flow (IT-01).

Verifies that IntakeWorker output feeds correctly into UnderstandWorker
using real worker classes (only clone_repo_cached is mocked).
"""
from __future__ import annotations

import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest

from launcher.models.base import LauncherBaseModel
from launcher.models.intake import IntakeBundle
from launcher.models.run_config import RunConfig
from launcher.orchestrator.worker_contract import WorkerContext
from launcher.workers.intake.worker import IntakeWorker
from launcher.workers.scout.worker import ScoutWorker
from launcher.workers.understand.worker import UnderstandWorker


def _populate_fake_repo(repo_dir: Path) -> None:
    """Create a minimal but realistic repo structure for Scout to process."""
    repo_dir.mkdir(parents=True, exist_ok=True)

    # Source files
    src = repo_dir / "src" / "aspose_cells_foss"
    src.mkdir(parents=True)
    (src / "__init__.py").write_text(
        'from .core import Workbook\n__all__ = ["Workbook"]\n'
    )
    (src / "core.py").write_text(textwrap.dedent("""\
        class Workbook:
            \"\"\"Main workbook class for spreadsheet operations.\"\"\"
            def load(self, path: str) -> None:
                \"\"\"Load a workbook from the given file path.\"\"\"
                pass
            def save(self, path: str) -> None:
                \"\"\"Save the workbook to the given file path.\"\"\"
                pass
    """))

    # README
    (repo_dir / "README.md").write_text(textwrap.dedent("""\
        # Aspose.Cells FOSS for Python

        A library for reading and writing spreadsheet files in Python.

        ## Features

        - Supports reading and writing XLSX spreadsheet files with full fidelity
        - Handles large spreadsheets with streaming mode for memory efficiency
        - Convert spreadsheets between XLSX, CSV, and other formats easily

        ## Installation

        - Install via pip install aspose-cells-foss
    """))

    # Doc files
    docs = repo_dir / "docs"
    docs.mkdir()
    (docs / "guide.md").write_text(
        "# Getting Started\n\n- Install via pip\n- Load a workbook\n"
    )

    # Example files
    examples = repo_dir / "examples"
    examples.mkdir()
    (examples / "basic.py").write_text(
        "from aspose_cells_foss import Workbook\nwb = Workbook()\n"
    )


@pytest.fixture
def fake_repo(tmp_path: Path) -> Path:
    repo_dir = tmp_path / "work" / "clone_cache" / "abc123"
    _populate_fake_repo(repo_dir)
    return repo_dir


@pytest.fixture
def run_config() -> RunConfig:
    return RunConfig(
        family="cells",
        platform="python",
        repo_url="https://github.com/aspose/aspose-cells-foss-python",
        launch_tier="auto",
    )


class TestIntakeToUnderstandFlow:
    """Happy path: Intake → Understand produces valid UnderstandingBundle."""

    @pytest.mark.asyncio
    async def test_intake_to_understand_produces_understanding_bundle(
        self, tmp_path: Path, fake_repo: Path, run_config: RunConfig,
    ) -> None:
        context = WorkerContext(
            run_id="integration-001", run_dir=tmp_path, config=run_config,
        )

        # Step 1: Run IntakeWorker with mocked clone
        intake_worker = IntakeWorker()
        with patch(
            "launcher.workers.intake.worker.clone_repo_cached",
            return_value=(fake_repo, "a" * 40, True),
        ):
            intake_bundle = await intake_worker.run(LauncherBaseModel(), context)

        # Verify IntakeBundle
        assert isinstance(intake_bundle, IntakeBundle)
        assert intake_bundle.repo_sha == "a" * 40
        assert intake_bundle.repo_dir
        assert Path(intake_bundle.repo_dir).is_dir()

        # Step 2: Run ScoutWorker with intake output (TC-4076: Scout now separate)
        scout_context = WorkerContext(
            run_id="integration-001", run_dir=tmp_path, config=run_config,
        )
        scout_worker = ScoutWorker()
        scout_bundle = await scout_worker.run(intake_bundle, scout_context)

        from launcher.models.scout import ScoutBundle
        assert isinstance(scout_bundle, ScoutBundle)
        assert len(scout_bundle.repo_info.file_tree) > 0

        # Step 3: Run UnderstandWorker with ScoutBundle output
        understand_context = WorkerContext(
            run_id="integration-001", run_dir=tmp_path, config=run_config,
        )
        # Transfer repo_content set by Scout to the Understand context
        understand_context.repo_content = scout_context.repo_content
        understand_worker = UnderstandWorker()
        understanding_bundle = await understand_worker.run(scout_bundle, understand_context)

        # Verify UnderstandingBundle
        from launcher.models.understanding import UnderstandingBundle
        assert isinstance(understanding_bundle, UnderstandingBundle)
        assert len(understanding_bundle.repo.file_tree) > 0
        assert len(understanding_bundle.claims) > 0
        assert understand_context.repo_dir == fake_repo


class TestResumeWithStaleRepoDir:
    """Failure path: stale repo_dir at Understand entry raises ValueError.

    TC-4076: UnderstandWorker now takes ScoutBundle, not IntakeBundle.
    """

    @pytest.mark.asyncio
    async def test_resume_with_stale_repo_dir_fails_cleanly(
        self, tmp_path: Path, run_config: RunConfig,
    ) -> None:
        # Simulate a resumed run where the cached clone dir was deleted
        from launcher.models.scout import ScoutBundle
        stale_bundle = ScoutBundle(
            family="cells",
            platform="python",
            repo_url="https://github.com/aspose/aspose-cells-foss-python",
            display_name="Aspose.Cells FOSS for Python",
            canonical_import="aspose_cells_foss",
            launch_tier="core",
            repo_dir=str(tmp_path / "deleted_clone_dir"),
            repo_sha="a" * 40,
        )

        context = WorkerContext(
            run_id="integration-resume", run_dir=tmp_path, config=run_config,
        )
        understand_worker = UnderstandWorker()

        with pytest.raises(ValueError, match="repo_dir does not exist"):
            await understand_worker.run(stale_bundle, context)


# ===================================================================
# SR-07: Verify on-disk artifacts contain provenance + skip_reason_counts
# ===================================================================


class TestIntakeArtifactProvenance:
    """SR-07: intake_bundle.json must contain field_provenance for traceability."""

    @pytest.mark.asyncio
    async def test_intake_artifact_contains_field_provenance(
        self, tmp_path: Path, fake_repo: Path, run_config: RunConfig,
    ) -> None:
        """SR-07: intake_bundle.json written by IntakeWorker includes field_provenance key."""
        import json
        from launcher.workers.intake.worker import _clear_families_cache

        _clear_families_cache()
        context = WorkerContext(
            run_id="sr07-provenance", run_dir=tmp_path, config=run_config,
        )
        intake_worker = IntakeWorker()

        with patch(
            "launcher.workers.intake.worker.clone_repo_cached",
            return_value=(fake_repo, "b" * 40, True),
        ):
            await intake_worker.run(LauncherBaseModel(), context)

        artifact_path = tmp_path / "intake_bundle.json"
        assert artifact_path.exists(), "intake_bundle.json was not written"

        with open(artifact_path, encoding="utf-8") as f:
            artifact = json.load(f)

        assert "field_provenance" in artifact, (
            f"intake_bundle.json missing 'field_provenance'. Keys present: {list(artifact.keys())}"
        )
        provenance = artifact["field_provenance"]
        assert "display_name" in provenance, "field_provenance missing 'display_name'"
        assert "canonical_import" in provenance, "field_provenance missing 'canonical_import'"
        assert provenance["display_name"] == "families_yaml", (
            f"Expected display_name provenance='families_yaml', got {provenance['display_name']!r}. "
            "_FAMILIES_YAML path may still be CWD-relative."
        )
        _clear_families_cache()


class TestUnderstandArtifactSkipReasonCounts:
    """SR-07: scout_inventory.json must contain skip_reason_counts for analysis."""

    @pytest.mark.asyncio
    async def test_scout_inventory_contains_skip_reason_counts(
        self, tmp_path: Path, fake_repo: Path, run_config: RunConfig,
    ) -> None:
        """SR-07: scout_inventory.json is already written by ScoutWorker."""
        import json
        from launcher.workers.intake.worker import _clear_families_cache

        _clear_families_cache()
        context = WorkerContext(
            run_id="sr07-scout", run_dir=tmp_path, config=run_config,
        )
        intake_worker = IntakeWorker()

        with patch(
            "launcher.workers.intake.worker.clone_repo_cached",
            return_value=(fake_repo, "c" * 40, True),
        ):
            intake_bundle = await intake_worker.run(LauncherBaseModel(), context)

        # TC-4076: Scout step runs between Intake and Understand
        scout_context = WorkerContext(
            run_id="sr07-scout", run_dir=tmp_path, config=run_config,
        )
        scout_worker = ScoutWorker()
        await scout_worker.run(intake_bundle, scout_context)

        scout_path = tmp_path / "scout_inventory.json"
        assert scout_path.exists(), "scout_inventory.json was not written"

        with open(scout_path, encoding="utf-8") as f:
            scout = json.load(f)

        assert "skip_reason_counts" in scout, (
            f"scout_inventory.json missing 'skip_reason_counts'. Keys present: {list(scout.keys())}"
        )
        assert isinstance(scout["skip_reason_counts"], dict), (
            f"skip_reason_counts must be a dict, got {type(scout['skip_reason_counts'])}"
        )
        assert "doc_paths" in scout, "scout_inventory.json must expose selected doc_paths"
        assert "example_paths" in scout, "scout_inventory.json must expose selected example_paths"
        _clear_families_cache()
