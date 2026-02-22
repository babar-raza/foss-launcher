"""Unit tests for resumable pipeline execution.

TC-2399: launch resume command and RESUME_NODE_MAP.
Spec reference: specs/43_resumable_pipeline.md
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Set

import pytest

from launch.models.state import (
    RUN_STATE_CLONED_INPUTS,
    RUN_STATE_CREATED,
    RUN_STATE_DRAFT_READY,
    RUN_STATE_FACTS_READY,
    RUN_STATE_INGESTED,
    RUN_STATE_LINKING,
    RUN_STATE_PLAN_READY,
    RUN_STATE_READY_FOR_PR,
    RUN_STATE_VALIDATING,
)
from launch.orchestrator.run_loop import RESUME_NODE_MAP, _validate_resume_artifacts

# ---------------------------------------------------------------------------
# All valid run_state values allowed as pre_run_state in RESUME_NODE_MAP
# ---------------------------------------------------------------------------
_VALID_STATES: Set[str] = {
    RUN_STATE_CREATED,
    RUN_STATE_CLONED_INPUTS,
    RUN_STATE_INGESTED,
    RUN_STATE_FACTS_READY,
    RUN_STATE_PLAN_READY,
    RUN_STATE_DRAFT_READY,
    RUN_STATE_LINKING,
    RUN_STATE_VALIDATING,
    RUN_STATE_READY_FOR_PR,
}

_EXPECTED_SHORT_ALIASES = {f"W{i}" for i in range(1, 12)}  # W1..W11
_EXPECTED_NODE_NAMES = {
    "clone_inputs",
    "ingest",
    "build_facts",
    "plan_pages",
    "draft_sections",
    "optimize_seo",
    "review_content",
    "link_and_patch",
    "validate",
    "fix",
    "open_pr",
}


# ---------------------------------------------------------------------------
# Test 1: all 22 aliases are present (11 short + 11 node names)
# ---------------------------------------------------------------------------
class TestResumeNodeMapCompleteness:
    def test_short_aliases_present(self) -> None:
        """All W1–W11 short aliases must be in RESUME_NODE_MAP."""
        missing = _EXPECTED_SHORT_ALIASES - RESUME_NODE_MAP.keys()
        assert not missing, f"Missing short aliases: {sorted(missing)}"

    def test_node_name_aliases_present(self) -> None:
        """All full graph node name aliases must be in RESUME_NODE_MAP."""
        missing = _EXPECTED_NODE_NAMES - RESUME_NODE_MAP.keys()
        assert not missing, f"Missing node name aliases: {sorted(missing)}"

    def test_total_alias_count(self) -> None:
        """Exactly 22 aliases (11 short + 11 node names) must be present."""
        assert len(RESUME_NODE_MAP) == 22, (
            f"Expected 22 entries in RESUME_NODE_MAP, got {len(RESUME_NODE_MAP)}. "
            f"Keys: {sorted(RESUME_NODE_MAP.keys())}"
        )


# ---------------------------------------------------------------------------
# Test 2: each pre_run_state is a known RUN_STATE_* constant
# ---------------------------------------------------------------------------
class TestResumeNodeMapStatesValid:
    def test_all_pre_run_states_are_valid(self) -> None:
        """Every pre_run_state in RESUME_NODE_MAP must be a known RUN_STATE_* constant."""
        invalid = {}
        for alias, (node, state, _) in RESUME_NODE_MAP.items():
            if state not in _VALID_STATES:
                invalid[alias] = state
        assert not invalid, (
            f"Invalid pre_run_state values found: {invalid}. "
            f"Valid states: {_VALID_STATES}"
        )

    def test_short_and_node_aliases_agree(self) -> None:
        """Short alias Wn and its corresponding node name must map to identical tuples."""
        short_to_node = {
            "W1": "clone_inputs",
            "W2": "ingest",
            "W3": "build_facts",
            "W4": "plan_pages",
            "W5": "draft_sections",
            "W6": "optimize_seo",
            "W7": "review_content",
            "W8": "link_and_patch",
            "W9": "validate",
            "W10": "fix",
            "W11": "open_pr",
        }
        for short, node_name in short_to_node.items():
            short_tuple = RESUME_NODE_MAP[short]
            node_tuple = RESUME_NODE_MAP[node_name]
            assert short_tuple == node_tuple, (
                f"Alias '{short}' and '{node_name}' disagree: {short_tuple} != {node_tuple}"
            )


# ---------------------------------------------------------------------------
# Test 3: artifact validation passes when all required files exist
# ---------------------------------------------------------------------------
class TestArtifactValidationPass:
    def test_no_required_artifacts(self, tmp_path: Path) -> None:
        """W1 / clone_inputs requires no artifacts — should pass on empty dir."""
        _validate_resume_artifacts(tmp_path, [])  # must not raise

    def test_all_required_artifacts_present(self, tmp_path: Path) -> None:
        """When all required artifacts exist, validation passes."""
        required = [
            "artifacts/page_plan.json",
            "artifacts/product_facts.json",
        ]
        for rel in required:
            p = tmp_path / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("{}", encoding="utf-8")

        _validate_resume_artifacts(tmp_path, required)  # must not raise

    def test_directory_artifact_present(self, tmp_path: Path) -> None:
        """Directory artifacts (e.g. 'work/repo') validate as directories."""
        (tmp_path / "work" / "repo").mkdir(parents=True)
        _validate_resume_artifacts(tmp_path, ["work/repo"])  # must not raise


# ---------------------------------------------------------------------------
# Test 4: artifact validation fails and reports ALL missing paths
# ---------------------------------------------------------------------------
class TestArtifactValidationFail:
    def test_single_missing_file_raises(self, tmp_path: Path) -> None:
        """Missing artifact raises ValueError with the missing path in the message."""
        with pytest.raises(ValueError) as exc_info:
            _validate_resume_artifacts(
                tmp_path, ["artifacts/page_plan.json"]
            )
        assert "artifacts/page_plan.json" in str(exc_info.value)

    def test_all_missing_paths_reported(self, tmp_path: Path) -> None:
        """All missing artifacts are listed in the error — not just the first."""
        required = [
            "artifacts/page_plan.json",
            "artifacts/product_facts.json",
            "artifacts/snippet_catalog.json",
        ]
        # Create only the first one — other two are missing
        p = tmp_path / "artifacts" / "page_plan.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("{}", encoding="utf-8")

        with pytest.raises(ValueError) as exc_info:
            _validate_resume_artifacts(tmp_path, required)

        msg = str(exc_info.value)
        assert "artifacts/product_facts.json" in msg
        assert "artifacts/snippet_catalog.json" in msg
        # The existing one should NOT appear as missing
        assert msg.count("artifacts/page_plan.json") == 0 or "page_plan.json" not in msg.split("missing")[1]


# ---------------------------------------------------------------------------
# Test 5: build_orchestrator_graph() accepts non-default entry points
# ---------------------------------------------------------------------------
class TestBuildGraphCustomEntryPoint:
    def test_default_entry_point_compiles(self) -> None:
        """build_orchestrator_graph() without args compiles (backward-compat guard)."""
        from launch.orchestrator.graph import build_orchestrator_graph

        graph = build_orchestrator_graph()
        compiled = graph.compile()
        assert compiled is not None

    def test_custom_entry_draft_sections(self) -> None:
        """build_orchestrator_graph('draft_sections') compiles without error."""
        from launch.orchestrator.graph import build_orchestrator_graph

        graph = build_orchestrator_graph(start_node="draft_sections")
        compiled = graph.compile()
        assert compiled is not None

    def test_custom_entry_validate(self) -> None:
        """build_orchestrator_graph('validate') compiles without error."""
        from launch.orchestrator.graph import build_orchestrator_graph

        graph = build_orchestrator_graph(start_node="validate")
        compiled = graph.compile()
        assert compiled is not None


# ---------------------------------------------------------------------------
# Test 6: CLI resume command rejects unknown worker aliases
# ---------------------------------------------------------------------------
class TestResumeCLIUnknownWorker:
    def test_unknown_worker_exits_1(self, tmp_path: Path) -> None:
        """resume command with unknown --from-worker alias exits with code 1."""
        from typer.testing import CliRunner

        from launch.cli.main import app

        # Create a minimal run_dir with run_config.yaml so the path check passes
        run_dir = tmp_path / "runs" / "test-run-id"
        run_dir.mkdir(parents=True)
        (run_dir / "run_config.yaml").write_text(
            "product_slug: test\ngithub_ref: main\nsite_ref: default_branch\n"
            "validation_profile: local\n",
            encoding="utf-8",
        )

        runner = CliRunner()
        result = runner.invoke(
            app,
            ["resume", "--run-dir", str(run_dir), "--from-worker", "WBAD"],
        )
        assert result.exit_code == 1
        assert "WBAD" in result.output or "WBAD" in str(result.exception or "")

    def test_unknown_worker_lists_valid_aliases(self, tmp_path: Path) -> None:
        """Error message for unknown alias includes at least W1 and W11 as valid options."""
        from typer.testing import CliRunner

        from launch.cli.main import app

        run_dir = tmp_path / "runs" / "test-run-id"
        run_dir.mkdir(parents=True)
        (run_dir / "run_config.yaml").write_text(
            "product_slug: test\ngithub_ref: main\nsite_ref: default_branch\n"
            "validation_profile: local\n",
            encoding="utf-8",
        )

        runner = CliRunner()
        result = runner.invoke(
            app,
            ["resume", "--run-dir", str(run_dir), "--from-worker", "W99"],
        )
        assert result.exit_code == 1
        # Output should mention valid aliases
        assert "W1" in result.output
