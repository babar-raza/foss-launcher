"""Tests for run_config loading and validation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from launcher.io.run_config import ConfigError, load_and_validate_run_config


@pytest.fixture
def repo_root(tmp_path: Path) -> Path:
    schemas_dir = tmp_path / "specs" / "schemas"
    schemas_dir.mkdir(parents=True)
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {
            "family": {"type": "string"},
            "platform": {"type": "string"},
        },
        "required": ["family"],
    }
    (schemas_dir / "run_config.schema.json").write_text(json.dumps(schema), encoding="utf-8")
    return tmp_path


def test_load_valid_config(repo_root: Path) -> None:
    config_file = repo_root / "config.yaml"
    config_file.write_text("family: cells\nplatform: python\n", encoding="utf-8")
    result = load_and_validate_run_config(repo_root, config_file)
    assert result["family"] == "cells"


def test_missing_config_raises(repo_root: Path) -> None:
    with pytest.raises(ConfigError, match="run_config not found"):
        load_and_validate_run_config(repo_root, repo_root / "nonexistent.yaml")


def test_missing_schema_raises(tmp_path: Path) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text("family: cells\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="schema missing"):
        load_and_validate_run_config(tmp_path, config_file)


def test_invalid_config_raises(repo_root: Path) -> None:
    config_file = repo_root / "bad.yaml"
    config_file.write_text("platform: python\n", encoding="utf-8")  # missing required "family"
    with pytest.raises(ConfigError, match="validation failed"):
        load_and_validate_run_config(repo_root, config_file)
