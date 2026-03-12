"""Regression tests for understanding_bundle schema drift fixes."""
from __future__ import annotations

import json
from pathlib import Path

from launcher.io.schema_validation import validate
from launcher.models.product import ApiSurface, ProductIdentity, RichnessResult, RichnessTier
from launcher.models.understanding import RepoInfo, UnderstandingBundle


SCHEMA_PATH = Path(__file__).resolve().parents[2] / "specs" / "schemas" / "understanding_bundle.schema.json"


def _load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def test_schema_declares_repo_important_files_skipped() -> None:
    """Regression: TC-4236 model field was missing from the JSON schema.

    Root cause: understanding_bundle schema `repo` object had `additionalProperties: false`
    but omitted `important_files_skipped`, so valid Understand output crashed at orchestrator
    validation time.
    Fixed in: TC-4253
    """
    schema = _load_schema()
    repo_props = schema["properties"]["repo"]["properties"]

    assert "important_files_skipped" in repo_props
    assert repo_props["important_files_skipped"]["type"] == "integer"
    assert repo_props["important_files_skipped"]["default"] == 0


def test_regression_understanding_bundle_schema_accepts_important_files_skipped() -> None:
    """Regression: schema validation must accept `repo.important_files_skipped`.

    Root cause: the Pydantic model emitted the field but the JSON schema rejected it as an
    additional property.
    Fixed in: TC-4253
    """
    bundle = UnderstandingBundle(
        product=ProductIdentity(
            family="cells",
            platform="python",
            display_name="Aspose.Cells",
            canonical_import="aspose_cells_foss",
            repo_url="https://github.com/example/repo",
        ),
        repo=RepoInfo(
            file_tree=["README.md"],
            doc_paths=["README.md"],
            example_paths=[],
            readme_summary="summary",
            important_files_skipped=2,
        ),
        richness_tier=RichnessResult(
            tier=RichnessTier.A,
            score=90,
            reason="rich deterministic evidence",
        ),
        api_surface=ApiSurface(
            public_classes=[],
            import_allowlist=[],
            confidence="low",
        ),
    )

    validate(
        bundle.model_dump(mode="json"),
        _load_schema(),
        context="understanding_bundle.schema",
    )
