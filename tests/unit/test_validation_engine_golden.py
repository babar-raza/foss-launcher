"""Golden comparison: legacy vs registry validation engine.

Runs both engines on the same minimal fixture and asserts that the
validation_report.json output is semantically identical.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

# Path to the checked-in minimal fixture (stable across environments)
_FIXTURES_DIR = Path(__file__).resolve().parents[2] / "tests" / "fixtures"
_MINIMAL_RUN_FIXTURE = _FIXTURES_DIR / "minimal_validation_run"


@pytest.fixture()
def golden_run_dir(tmp_path: Path) -> Path:
    """Create a minimal but complete run_dir for validator execution.

    The fixture includes just enough structure for all 31 gates to
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

    # repo_truth.json — deterministic ground-truth facts
    rt = {
        "schema_version": "1.0",
        "license": {"spdx_id": "", "name": "", "source": ""},
        "python_requires": {"min": "", "spec": "", "source": ""},
        "package_name": {"value": "aspose-3d", "source": "manifest"},
        "import_roots": {"values": [], "source": "code_analysis"},
    }
    (artifacts / "repo_truth.json").write_text(
        json.dumps(rt, indent=2), encoding="utf-8"
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


# =======================================================================
# TC-2432: Pilot-scale golden fixture + equivalence tests
# =======================================================================


@pytest.fixture()
def pilot_scale_run_dir(tmp_path: Path) -> Path:
    """Pilot-scale run_dir: 7 pages, 20 claims, 3 claim_groups."""
    run_dir = tmp_path / "runs" / "pilot_run"
    run_dir.mkdir(parents=True)
    artifacts = run_dir / "artifacts"
    artifacts.mkdir()
    docs_dir = run_dir / "work" / "site" / "content" / "docs" / "3d" / "en" / "python"
    kb_dir   = run_dir / "work" / "site" / "content" / "kb"   / "3d" / "en"
    prod_dir = run_dir / "work" / "site" / "content" / "products" / "3d" / "en"
    blog_dir = run_dir / "work" / "site" / "content" / "blog" / "3d" / "en"
    for d in (docs_dir, kb_dir, prod_dir, blog_dir):
        d.mkdir(parents=True)
    (run_dir / "events.ndjson").write_text("", encoding="utf-8")
    claim_ids = [f"claim_{str(i).zfill(3)}" for i in range(1, 21)]
    kinds = [
        "feature", "feature", "feature", "feature", "feature",
        "feature", "feature", "api", "api", "api",
        "api", "quickstart", "quickstart", "quickstart",
        "tutorial", "tutorial", "tutorial", "concept", "concept", "concept",
    ]
    claims = [
        {
            "claim_id": cid,
            "claim_text": f"Aspose.3D {kind} claim {cid}: robust file handling.",
            "claim_kind": kind,
            "truth_status": "verified",
            "citations": ["README.md"],
        }
        for cid, kind in zip(claim_ids, kinds)
    ]
    pf = {
        "product_name": "Aspose.3D for Python",
        "product_slug": "3d",
        "repo_url": "https://github.com/aspose-3d/Aspose.3D-for-Python",
        "claims": claims,
        "claim_groups": {
            "key_features": claim_ids[0:7],
            "api_surface": claim_ids[7:11],
            "guides": claim_ids[11:17],
        },
        "workflows": [],
    }
    (artifacts / "product_facts.json").write_text(
        json.dumps(pf, indent=2), encoding="utf-8"
    )
    pages = [
        {"slug": "getting-started",
         "output_path": "content/docs/3d/en/python/getting-started.md",
         "page_role": "tutorial", "section": "getting-started",
         "content_strategy": {"scenario_coverage": "all"},
         "required_claim_ids": claim_ids[0:3]},
        {"slug": "api-reference",
         "output_path": "content/docs/3d/en/python/api-reference.md",
         "page_role": "reference", "section": "api",
         "content_strategy": {"scenario_coverage": "api"},
         "required_claim_ids": claim_ids[7:11]},
        {"slug": "overview",
         "output_path": "content/kb/3d/en/overview.md",
         "page_role": "overview", "section": "knowledge-base",
         "content_strategy": {"scenario_coverage": "intro"},
         "required_claim_ids": claim_ids[3:6]},
        {"slug": "product-page",
         "output_path": "content/products/3d/en/product-page.md",
         "page_role": "landing", "section": "products",
         "content_strategy": {"scenario_coverage": "all"},
         "required_claim_ids": claim_ids[0:5]},
        {"slug": "quickstart-guide",
         "output_path": "content/docs/3d/en/python/quickstart-guide.md",
         "page_role": "quickstart", "section": "quickstart",
         "content_strategy": {"scenario_coverage": "quickstart"},
         "required_claim_ids": claim_ids[11:14]},
        {"slug": "advanced-features",
         "output_path": "content/kb/3d/en/advanced-features.md",
         "page_role": "tutorial", "section": "advanced",
         "content_strategy": {"scenario_coverage": "advanced"},
         "required_claim_ids": claim_ids[14:17]},
        {"slug": "release-notes",
         "output_path": "content/blog/3d/en/release-notes.md",
         "page_role": "blog", "section": "blog",
         "content_strategy": {"scenario_coverage": "news"},
         "required_claim_ids": claim_ids[17:20]},
    ]
    pp = {"product_slug": "3d", "pages": pages}
    (artifacts / "page_plan.json").write_text(json.dumps(pp, indent=2), encoding="utf-8")
    _nl = chr(10)
    long_prose = (
        "Aspose.3D for Python is a comprehensive library for working with " +
        "three-dimensional content. It supports FBX, OBJ, STL, GLTF and many " +
        "other formats. The API allows you to create, load, modify, and save " +
        "3D scenes programmatically without requiring external tools." + _nl + _nl +
        "The library handles materials, textures, animations, and skeletal " +
        "rigs. You can merge scenes, extract mesh data, apply transformations, " +
        "and export to web-friendly formats with minimal boilerplate code." + _nl
    )
    def _page(title: str, desc: str, url: str, body: str) -> str:
        slug = title.lower().replace(" ", "-")
        _nl = chr(10)
        parts = [
            "---" + _nl,
            "title: " + chr(34) + title + chr(34) + _nl,
            "description: " + chr(34) + desc + chr(34) + _nl,
            "date: 2026-01-15" + _nl,
            "slug: " + chr(34) + slug + chr(34) + _nl,
            "categories: [python, 3d]" + _nl,
            "url: " + chr(34) + url + chr(34) + _nl,
            "type: docs" + _nl,
            "weight: 1" + _nl,
            "---" + _nl + _nl,
            body + _nl,
        ]
        return "".join(parts)
    (docs_dir / "getting-started.md").write_text(
        _page("Getting Started", "Get started with Aspose.3D for Python", "/3d/python/getting-started/",
              long_prose + chr(10) + "## Code Example" + chr(10) + chr(10) + "Install with pip." + chr(10) + chr(10) + "".join("<!-- claim: " + x + " -->" + chr(10) for x in claim_ids[0:3])),
        encoding="utf-8",
    )
    (docs_dir / "api-reference.md").write_text(
        _page("API Reference", "Full API reference for Aspose.3D Python", "/3d/python/api-reference/",
              long_prose + chr(10) + "## API Details" + chr(10) + chr(10) + "See the class hierarchy." + chr(10) + chr(10) + "".join("<!-- claim: " + x + " -->" + chr(10) for x in claim_ids[7:11])),
        encoding="utf-8",
    )
    (kb_dir / "overview.md").write_text(
        _page("Overview", "Overview of Aspose.3D capabilities", "/kb/3d/overview/",
              long_prose + "".join("<!-- claim: " + x + " -->" + chr(10) for x in claim_ids[3:6])),
        encoding="utf-8",
    )
    (prod_dir / "product-page.md").write_text(
        _page("Product Page", "Aspose.3D product overview and licensing", "/products/3d/",
              long_prose + "This page describes pricing and licensing tiers." + chr(10)),
        encoding="utf-8",
    )
    (docs_dir / "quickstart-guide.md").write_text(
        _page("Quickstart Guide", "Quickstart guide for Aspose.3D Python", "/3d/python/quickstart/",
              "## Install" + chr(10) + chr(10) + "Run installer command to begin." + chr(10) + chr(10) + long_prose + "".join("<!-- claim: " + x + " -->" + chr(10) for x in claim_ids[11:14])),
        encoding="utf-8",
    )
    (kb_dir / "advanced-features.md").write_text(
        _page("Advanced Features", "Advanced Aspose.3D features for power users", "/kb/3d/advanced/",
              long_prose + "".join("<!-- claim: " + x + " -->" + chr(10) for x in claim_ids[14:17])),
        encoding="utf-8",
    )
    (blog_dir / "release-notes.md").write_text(
        _page("Release Notes", "Release notes for Aspose.3D latest version", "/blog/3d/release-notes/",
              "## Whats New" + chr(10) + chr(10) + long_prose + "".join("<!-- claim: " + x + " -->" + chr(10) for x in claim_ids[17:20])),
        encoding="utf-8",
    )
    _ini = (
        "[tool.pytest.ini_options]" + chr(10)
        + "PYTHONHASHSEED = " + chr(34) + "0" + chr(34) + chr(10)
    )
    (tmp_path / "pyproject.toml").write_text(_ini, encoding="utf-8")
    return run_dir


def _run_engine_pilot(
    run_dir: Path,
    run_config: dict,
    engine: str,
    monkeypatch: pytest.MonkeyPatch,
) -> dict:
    """Run execute_validator with specified engine, nulling LLM client."""
    monkeypatch.setenv("LAUNCH_VALIDATION_ENGINE", engine)
    try:
        from launch.validation_engine.context import GateContext
        monkeypatch.setattr(GateContext, "get_llm_client", lambda self: None)
    except Exception:
        pass
    (run_dir / "events.ndjson").write_text("", encoding="utf-8")
    from launch.workers.w9_validator.worker import execute_validator
    return execute_validator(run_dir, run_config)


class TestGoldenComparisonPilotScale:
    """Pilot-scale (7 pages, 20 claims) legacy vs registry equivalence."""

    def test_gate_names_match_at_pilot_scale(
        self, pilot_scale_run_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        rc = {"validation_profile": "local"}
        legacy   = _run_engine_pilot(pilot_scale_run_dir, rc, "legacy",   monkeypatch)
        registry = _run_engine_pilot(pilot_scale_run_dir, rc, "registry", monkeypatch)
        assert [g["name"] for g in legacy["gates"]] == [g["name"] for g in registry["gates"]]

    def test_gate_ok_values_match_at_pilot_scale(
        self, pilot_scale_run_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        rc = {"validation_profile": "local"}
        legacy   = _run_engine_pilot(pilot_scale_run_dir, rc, "legacy",   monkeypatch)
        registry = _run_engine_pilot(pilot_scale_run_dir, rc, "registry", monkeypatch)
        for lg, rg in zip(legacy["gates"], registry["gates"]):
            assert lg["ok"] == rg["ok"]

    def test_overall_ok_matches_at_pilot_scale(
        self, pilot_scale_run_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        rc = {"validation_profile": "local"}
        legacy   = _run_engine_pilot(pilot_scale_run_dir, rc, "legacy",   monkeypatch)
        registry = _run_engine_pilot(pilot_scale_run_dir, rc, "registry", monkeypatch)
        assert legacy["ok"] == registry["ok"]

    def test_issue_ids_match_at_pilot_scale(
        self, pilot_scale_run_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        rc = {"validation_profile": "local"}
        legacy   = _run_engine_pilot(pilot_scale_run_dir, rc, "legacy",   monkeypatch)
        registry = _run_engine_pilot(pilot_scale_run_dir, rc, "registry", monkeypatch)
        assert (
            [i["issue_id"] for i in legacy["issues"]]
            == [i["issue_id"] for i in registry["issues"]]
        )

    def test_issue_severities_match_at_pilot_scale(
        self, pilot_scale_run_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        rc = {"validation_profile": "local"}
        legacy   = _run_engine_pilot(pilot_scale_run_dir, rc, "legacy",   monkeypatch)
        registry = _run_engine_pilot(pilot_scale_run_dir, rc, "registry", monkeypatch)
        assert (
            [(i["issue_id"], i["severity"]) for i in legacy["issues"]]
            == [(i["issue_id"], i["severity"]) for i in registry["issues"]]
        )

    def test_issue_count_matches_at_pilot_scale(
        self, pilot_scale_run_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        rc = {"validation_profile": "local"}
        legacy   = _run_engine_pilot(pilot_scale_run_dir, rc, "legacy",   monkeypatch)
        registry = _run_engine_pilot(pilot_scale_run_dir, rc, "registry", monkeypatch)
        assert len(legacy["issues"]) == len(registry["issues"])

    def test_artifact_block_cascade_missing_page_plan_both_engines(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Both engines cascade-skip artifact-block gates when page_plan absent."""
        run_dir = tmp_path / "runs" / "no_plan"
        run_dir.mkdir(parents=True)
        (run_dir / "artifacts").mkdir()
        (run_dir / "work" / "site" / "content").mkdir(parents=True)
        (run_dir / "events.ndjson").write_text("", encoding="utf-8")
        pf = {
            "product_name": "Aspose.3D",
            "product_slug": "3d",
            "repo_url": "https://github.com/aspose-3d/Aspose.3D-for-Python",
            "claims": [], "claim_groups": {}, "workflows": [],
        }
        (run_dir / "artifacts" / "product_facts.json").write_text(
            json.dumps(pf), encoding="utf-8"
        )
        _ini = (
            "[tool.pytest.ini_options]" + chr(10)
            + "PYTHONHASHSEED = " + chr(34) + "0" + chr(34) + chr(10)
        )
        (tmp_path / "pyproject.toml").write_text(_ini, encoding="utf-8")
        rc = {"validation_profile": "local"}
        legacy   = _run_engine_pilot(run_dir, rc, "legacy",   monkeypatch)
        registry = _run_engine_pilot(run_dir, rc, "registry", monkeypatch)
        assert legacy["ok"] == registry["ok"]

    def test_artifact_block_cascade_missing_product_facts_both_engines(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Both engines handle missing product_facts consistently."""
        run_dir = tmp_path / "runs" / "no_facts"
        run_dir.mkdir(parents=True)
        (run_dir / "artifacts").mkdir()
        (run_dir / "work" / "site" / "content").mkdir(parents=True)
        (run_dir / "events.ndjson").write_text("", encoding="utf-8")
        pp = {"product_slug": "3d", "pages": []}
        (run_dir / "artifacts" / "page_plan.json").write_text(
            json.dumps(pp), encoding="utf-8"
        )
        _ini = (
            "[tool.pytest.ini_options]" + chr(10)
            + "PYTHONHASHSEED = " + chr(34) + "0" + chr(34) + chr(10)
        )
        (tmp_path / "pyproject.toml").write_text(_ini, encoding="utf-8")
        rc = {"validation_profile": "local"}
        legacy   = _run_engine_pilot(run_dir, rc, "legacy",   monkeypatch)
        registry = _run_engine_pilot(run_dir, rc, "registry", monkeypatch)
        assert legacy["ok"] == registry["ok"]


# =======================================================================
# TC-2431 / Agent A: Checked-in fixture equivalence + callable validation
# =======================================================================


@pytest.fixture()
def checked_in_run_dir(tmp_path: Path) -> Path:
    """Copy the checked-in minimal fixture to a temp location for execution.

    Uses ``tests/fixtures/minimal_validation_run/`` as the source of truth.
    The copy lives under ``tmp_path`` so the validator can write
    ``artifacts/validation_report.json`` without modifying the source fixture.

    A ``pyproject.toml`` with ``PYTHONHASHSEED=0`` is created at ``tmp_path``
    so that gate_t_test_determinism passes.
    """
    run_dir = tmp_path / "runs" / "run_001"
    run_dir.mkdir(parents=True)

    # Copy all fixture files into the run_dir
    for item in _MINIMAL_RUN_FIXTURE.iterdir():
        dest = run_dir / item.name
        if item.is_dir():
            shutil.copytree(str(item), str(dest))
        else:
            shutil.copy2(str(item), str(dest))

    # Reset events.ndjson (the fixture ships with an empty file, but reset
    # to be safe in case the fixture is re-used across test invocations)
    (run_dir / "events.ndjson").write_text("", encoding="utf-8")

    # gate_t_test_determinism checks pyproject.toml at the repo-root level
    # (parent of the "runs/" directory)
    (tmp_path / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\nenv = ["PYTHONHASHSEED=0"]\n',
        encoding="utf-8",
    )

    return run_dir


class TestCheckedInFixtureEquivalence:
    """Legacy vs registry must produce identical output on the stable checked-in fixture.

    This class complements TestGoldenComparison (which uses procedurally-built
    tmp fixtures) by verifying against a *static*, version-controlled run_dir.
    The fixture is deterministic across environments and CI runs.
    """

    def test_fixture_files_present(self) -> None:
        """Checked-in fixture has all required files."""
        assert (_MINIMAL_RUN_FIXTURE / "artifacts" / "product_facts.json").exists(), \
            "Missing: tests/fixtures/minimal_validation_run/artifacts/product_facts.json"
        assert (_MINIMAL_RUN_FIXTURE / "artifacts" / "page_plan.json").exists(), \
            "Missing: tests/fixtures/minimal_validation_run/artifacts/page_plan.json"
        assert (_MINIMAL_RUN_FIXTURE / "events.ndjson").exists(), \
            "Missing: tests/fixtures/minimal_validation_run/events.ndjson"
        md_dir = (
            _MINIMAL_RUN_FIXTURE / "work" / "site" / "content" / "docs" / "3d" / "en" / "python"
        )
        md_files = list(md_dir.glob("*.md"))
        assert md_files, f"No markdown files found in {md_dir}"

    def test_gate_names_and_order_match(
        self,
        checked_in_run_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Both engines produce gates in identical order on the checked-in fixture."""
        rc = {"validation_profile": "local"}
        legacy   = _run_engine_pilot(checked_in_run_dir, rc, "legacy",   monkeypatch)
        registry = _run_engine_pilot(checked_in_run_dir, rc, "registry", monkeypatch)

        legacy_names   = [g["name"] for g in legacy["gates"]]
        registry_names = [g["name"] for g in registry["gates"]]

        assert legacy_names == registry_names, (
            f"Gate name/order mismatch on checked-in fixture:\n"
            f"  legacy:   {legacy_names}\n"
            f"  registry: {registry_names}"
        )

    def test_gate_ok_values_match(
        self,
        checked_in_run_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Gate ok values are identical between engines on the checked-in fixture."""
        rc = {"validation_profile": "local"}
        legacy   = _run_engine_pilot(checked_in_run_dir, rc, "legacy",   monkeypatch)
        registry = _run_engine_pilot(checked_in_run_dir, rc, "registry", monkeypatch)

        for lg, rg in zip(legacy["gates"], registry["gates"]):
            assert lg["ok"] == rg["ok"], (
                f"Gate {lg['name']}: legacy ok={lg['ok']}, registry ok={rg['ok']}"
            )

    def test_overall_ok_matches(
        self,
        checked_in_run_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Overall ok value matches between engines on the checked-in fixture."""
        rc = {"validation_profile": "local"}
        legacy   = _run_engine_pilot(checked_in_run_dir, rc, "legacy",   monkeypatch)
        registry = _run_engine_pilot(checked_in_run_dir, rc, "registry", monkeypatch)
        assert legacy["ok"] == registry["ok"]

    def test_issue_ids_match(
        self,
        checked_in_run_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Issue IDs are identical between engines on the checked-in fixture."""
        rc = {"validation_profile": "local"}
        legacy   = _run_engine_pilot(checked_in_run_dir, rc, "legacy",   monkeypatch)
        registry = _run_engine_pilot(checked_in_run_dir, rc, "registry", monkeypatch)

        legacy_ids   = [i["issue_id"] for i in legacy["issues"]]
        registry_ids = [i["issue_id"] for i in registry["issues"]]

        assert legacy_ids == registry_ids, (
            f"Issue ID mismatch:\n"
            f"  legacy:   {legacy_ids}\n"
            f"  registry: {registry_ids}"
        )

    def test_registry_engine_reports_33_gates(
        self,
        checked_in_run_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Registry engine produces 41 gate results (truth enforcement + Phase 1/2 gates)."""
        rc = {"validation_profile": "local"}
        registry = _run_engine_pilot(checked_in_run_dir, rc, "registry", monkeypatch)
        assert len(registry["gates"]) == 41, (
            f"Expected 41 gates, got {len(registry['gates'])}: "
            f"{[g['name'] for g in registry['gates']]}"
        )


class TestCallableValidationTool:
    """tools/extract_validation_gates.py --check-callables resolves all 37 gates."""

    def test_check_callables_returns_true(self) -> None:
        """All 37 gate callables resolve without error."""
        from tools.extract_validation_gates import check_callables
        registry_path = (
            Path(__file__).resolve().parents[2]
            / "src" / "launch" / "validation_engine" / "gates_registry.yaml"
        )
        assert check_callables(registry_path) is True

    def test_check_callables_detects_bad_module(self, tmp_path: Path) -> None:
        """check_callables returns False when a module cannot be imported."""
        import yaml

        fake_registry = {
            "gates": [
                {
                    "gate_id": "gate_bad",
                    "display_name": "Bad",
                    "order": 1,
                    "module": "launch.workers.w9_validator.gates.nonexistent_module_xyz",
                    "callable_name": "execute_gate",
                    "runner_type": "execute_gate",
                }
            ]
        }
        registry_path = tmp_path / "bad_registry.yaml"
        registry_path.write_text(yaml.dump(fake_registry), encoding="utf-8")

        from tools.extract_validation_gates import check_callables
        assert check_callables(registry_path) is False

    def test_check_callables_detects_missing_attribute(self, tmp_path: Path) -> None:
        """check_callables returns False when the named attribute is absent."""
        import yaml

        fake_registry = {
            "gates": [
                {
                    "gate_id": "gate_bad_attr",
                    "display_name": "Bad Attr",
                    "order": 1,
                    "module": "launch.workers.w9_validator.worker",
                    "callable_name": "nonexistent_function_xyz_abc",
                    "runner_type": "inline_fn",
                }
            ]
        }
        registry_path = tmp_path / "bad_attr_registry.yaml"
        registry_path.write_text(yaml.dump(fake_registry), encoding="utf-8")

        from tools.extract_validation_gates import check_callables
        assert check_callables(registry_path) is False
