"""Golden comparison: legacy vs registry validation engine.

Runs both engines on the same minimal fixture and asserts that the
validation_report.json output is semantically identical.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture()
def golden_run_dir(tmp_path: Path) -> Path:
    """Create a minimal but complete run_dir for validator execution.

    The fixture includes just enough structure for all 28 gates to
    execute (most will produce no issues on this minimal input).
    """
    # Two levels deep so repo_root = tmp_path
    run_dir = tmp_path / "runs" / "run_001"
    run_dir.mkdir(parents=True)

    artifacts = run_dir / "artifacts"
    artifacts.mkdir()

    site = run_dir / "work" / "site"
    content = site / "content" / "docs" / "3d" / "en" / "python"
    content.mkdir(parents=True)

    # events.ndjson (empty)
    (run_dir / "events.ndjson").write_text("", encoding="utf-8")

    # product_facts.json — minimal valid
    pf = {
        "product_name": "Aspose.3D for Python",
        "product_slug": "3d",
        "repo_url": "https://github.com/aspose-3d/Aspose.3D-for-Python",
        "claims": [
            {
                "claim_id": "claim_001",
                "claim_text": "Aspose.3D supports FBX format.",
                "claim_kind": "feature",
                "truth_status": "verified",
                "citations": ["README.md"],
            }
        ],
        "claim_groups": {"key_features": ["claim_001"]},
        "workflows": [],
    }
    (artifacts / "product_facts.json").write_text(
        json.dumps(pf, indent=2), encoding="utf-8"
    )

    # page_plan.json — one page
    pp = {
        "product_slug": "3d",
        "pages": [
            {
                "slug": "getting-started",
                "output_path": "content/docs/3d/en/python/getting-started.md",
                "page_role": "tutorial",
                "section": "getting-started",
                "content_strategy": {"scenario_coverage": "all"},
                "required_claim_ids": ["claim_001"],
            }
        ],
    }
    (artifacts / "page_plan.json").write_text(
        json.dumps(pp, indent=2), encoding="utf-8"
    )

    # Markdown page
    md = (
        "---\n"
        'title: "Getting Started"\n'
        'description: "Get started with Aspose.3D"\n'
        'url: "/3d/python/getting-started/"\n'
        "type: docs\n"
        "weight: 1\n"
        "---\n\n"
        "## Introduction\n\n"
        "Aspose.3D for Python is a powerful 3D document processing library "
        "that supports FBX format and many other features for working with "
        "three-dimensional content in Python applications.\n\n"
        "## Getting Started\n\n"
        "Install the library using pip:\n\n"
        "```python\n"
        "pip install aspose-3d\n"
        "```\n\n"
        "Then import and use it:\n\n"
        "```python\n"
        "import aspose.threed as a3d\n"
        "scene = a3d.Scene()\n"
        "scene.save('output.fbx')\n"
        "```\n\n"
        "## Features\n\n"
        "Aspose.3D supports FBX format for loading and saving 3D scenes. "
        "The library provides a rich API for manipulating 3D objects, "
        "materials, and animations. You can convert between formats, "
        "create scenes programmatically, and extract data from existing "
        "3D files with minimal code.\n\n"
        "<!-- claim: claim_001 -->\n"
    )
    (content / "getting-started.md").write_text(md, encoding="utf-8")

    # pyproject.toml stub (for gate_t_test_determinism)
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[tool.pytest.ini_options]\nenv = ["PYTHONHASHSEED=0"]\n',
        encoding="utf-8",
    )

    return run_dir


def _run_engine(
    run_dir: Path, run_config: dict, engine: str, monkeypatch: pytest.MonkeyPatch
) -> dict:
    """Run execute_validator with the specified engine and return the report."""
    monkeypatch.setenv("LAUNCH_VALIDATION_ENGINE", engine)

    # Reset events.ndjson to avoid contamination
    events_path = run_dir / "events.ndjson"
    events_path.write_text("", encoding="utf-8")

    from launch.workers.w9_validator.worker import execute_validator

    return execute_validator(run_dir, run_config)


class TestGoldenComparison:
    """Legacy vs registry engine must produce identical outputs."""

    def test_gate_names_and_order_match(
        self,
        golden_run_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        run_config = {"validation_profile": "local"}

        legacy_report = _run_engine(
            golden_run_dir, run_config, "legacy", monkeypatch
        )
        registry_report = _run_engine(
            golden_run_dir, run_config, "registry", monkeypatch
        )

        legacy_names = [g["name"] for g in legacy_report["gates"]]
        registry_names = [g["name"] for g in registry_report["gates"]]

        assert legacy_names == registry_names, (
            f"Gate name/order mismatch:\n"
            f"  legacy:   {legacy_names}\n"
            f"  registry: {registry_names}"
        )

    def test_gate_ok_values_match(
        self,
        golden_run_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        run_config = {"validation_profile": "local"}

        legacy_report = _run_engine(
            golden_run_dir, run_config, "legacy", monkeypatch
        )
        registry_report = _run_engine(
            golden_run_dir, run_config, "registry", monkeypatch
        )

        for lg, rg in zip(
            legacy_report["gates"], registry_report["gates"]
        ):
            assert lg["ok"] == rg["ok"], (
                f"Gate {lg['name']}: legacy ok={lg['ok']}, "
                f"registry ok={rg['ok']}"
            )

    def test_overall_ok_matches(
        self,
        golden_run_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        run_config = {"validation_profile": "local"}

        legacy_report = _run_engine(
            golden_run_dir, run_config, "legacy", monkeypatch
        )
        registry_report = _run_engine(
            golden_run_dir, run_config, "registry", monkeypatch
        )

        assert legacy_report["ok"] == registry_report["ok"]

    def test_issue_ids_match(
        self,
        golden_run_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        run_config = {"validation_profile": "local"}

        legacy_report = _run_engine(
            golden_run_dir, run_config, "legacy", monkeypatch
        )
        registry_report = _run_engine(
            golden_run_dir, run_config, "registry", monkeypatch
        )

        legacy_ids = [i["issue_id"] for i in legacy_report["issues"]]
        registry_ids = [i["issue_id"] for i in registry_report["issues"]]

        assert legacy_ids == registry_ids, (
            f"Issue ID mismatch:\n"
            f"  legacy:   {legacy_ids}\n"
            f"  registry: {registry_ids}"
        )

    def test_issue_severities_match(
        self,
        golden_run_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        run_config = {"validation_profile": "local"}

        legacy_report = _run_engine(
            golden_run_dir, run_config, "legacy", monkeypatch
        )
        registry_report = _run_engine(
            golden_run_dir, run_config, "registry", monkeypatch
        )

        legacy_sevs = [
            (i["issue_id"], i["severity"]) for i in legacy_report["issues"]
        ]
        registry_sevs = [
            (i["issue_id"], i["severity"]) for i in registry_report["issues"]
        ]

        assert legacy_sevs == registry_sevs

    def test_issue_count_matches(
        self,
        golden_run_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        run_config = {"validation_profile": "local"}

        legacy_report = _run_engine(
            golden_run_dir, run_config, "legacy", monkeypatch
        )
        registry_report = _run_engine(
            golden_run_dir, run_config, "registry", monkeypatch
        )

        assert len(legacy_report["issues"]) == len(registry_report["issues"])
