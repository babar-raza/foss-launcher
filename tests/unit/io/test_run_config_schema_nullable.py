"""Regression tests: run_config.schema.json nullable field alignment.

TC-SCHEMA-NULL fixed a crash where RunConfig.model_dump(mode="json") produced
{"telemetry": null} but run_config.schema.json declared "type": "object" for telemetry.
The intake worker's input validation raised before any worker code ran.

SR-02 hardens these tests:
- Hard-fail if schema file missing (replaces silent skipif that looked like a pass).
- Adds YAML-loading path coverage via load_and_validate_run_config.
- Asserts output is always a dict (validates SR-01 revert: output is not Optional).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from launcher.io.run_config import load_and_validate_run_config
from launcher.io.schema_validation import load_schema, validate
from launcher.models.run_config import RunConfig

# Resolve repo root from this file's location: tests/unit/io/ is 3 levels below root.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCHEMA_PATH = _REPO_ROOT / "specs" / "schemas" / "run_config.schema.json"


def test_default_runconfig_serialization_passes_schema() -> None:
    """A minimal RunConfig (all optional fields at None) must pass schema validation.

    Regression for TC-SCHEMA-NULL: before the fix this raised:
        Schema validation failed:
        - test_default_runconfig: telemetry: None is not of type 'object'
    """
    if not _SCHEMA_PATH.exists():
        pytest.fail(
            f"Schema file not found — path drift? Expected: {_SCHEMA_PATH}\n"
            "If the schema was moved, update _REPO_ROOT resolution in this test."
        )

    cfg = RunConfig(
        family="cells",
        platform="python",
        repo_url="https://github.com/example/repo",
    )
    data = cfg.model_dump(mode="json")

    # Fields that were the root cause of the crash must serialize as null.
    assert data["telemetry"] is None, "telemetry should serialize as null (Optional)"
    assert data["llm"] is None, "llm should serialize as null (Optional)"
    # output is NOT Optional — it must always serialize as a dict, never null (SR-01).
    assert isinstance(data["output"], dict), (
        "output must always be a dict; RunConfig.output is not Optional"
    )

    schema = load_schema(_SCHEMA_PATH)
    # Must not raise. Before TC-SCHEMA-NULL this raised on telemetry: null.
    validate(data, schema, context="test_default_runconfig_serialization")


def test_yaml_with_null_telemetry_passes_schema(tmp_path: Path) -> None:
    """load_and_validate_run_config must accept a YAML config with telemetry: null.

    Covers the YAML-loading path: raw YAML dict -> schema validation inside
    load_and_validate_run_config (io/run_config.py). Without TC-SCHEMA-NULL this
    path also raised on the schema validation step.
    """
    if not _SCHEMA_PATH.exists():
        pytest.fail(
            f"Schema file not found — path drift? Expected: {_SCHEMA_PATH}\n"
            "If the schema was moved, update _REPO_ROOT resolution in this test."
        )

    config_file = tmp_path / "run_config.yaml"
    config_file.write_text(
        "family: cells\n"
        "platform: python\n"
        "repo_url: https://github.com/example/repo\n"
        "telemetry: null\n",
        encoding="utf-8",
    )

    # Must not raise — before TC-SCHEMA-NULL this raised on telemetry: null
    # during the schema validation step inside load_and_validate_run_config.
    data = load_and_validate_run_config(_REPO_ROOT, config_file)
    assert data.get("telemetry") is None
