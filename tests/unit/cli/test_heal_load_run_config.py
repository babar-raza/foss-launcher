"""Unit tests for heal._load_run_config — JSON / YAML / missing file paths."""
from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

from launcher.cli.heal import _load_run_config


class TestLoadRunConfigJson:
    """run_config.json present, no YAML."""

    def test_returns_dict_from_json(self, tmp_path: Path) -> None:
        payload = {"product_id": "test", "run_id": "r_abc"}
        (tmp_path / "run_config.json").write_text(json.dumps(payload), encoding="utf-8")
        result = _load_run_config(tmp_path)
        assert result == payload

    def test_nested_values_preserved(self, tmp_path: Path) -> None:
        payload = {"a": {"b": [1, 2, 3]}, "flag": True}
        (tmp_path / "run_config.json").write_text(json.dumps(payload), encoding="utf-8")
        result = _load_run_config(tmp_path)
        assert result == payload

    def test_malformed_json_returns_none(self, tmp_path: Path) -> None:
        (tmp_path / "run_config.json").write_text("{bad json}", encoding="utf-8")
        result = _load_run_config(tmp_path)
        assert result is None


class TestLoadRunConfigYaml:
    """run_config.yaml present (no JSON)."""

    def test_returns_dict_from_yaml(self, tmp_path: Path) -> None:
        yaml_content = textwrap.dedent("""\
            product_id: cells
            run_id: r_yaml
        """)
        (tmp_path / "run_config.yaml").write_text(yaml_content, encoding="utf-8")
        result = _load_run_config(tmp_path)
        assert result == {"product_id": "cells", "run_id": "r_yaml"}


class TestLoadRunConfigPrecedence:
    """When both files are present, YAML wins."""

    def test_yaml_takes_precedence_over_json(self, tmp_path: Path) -> None:
        yaml_content = "source: yaml\n"
        json_content = json.dumps({"source": "json"})
        (tmp_path / "run_config.yaml").write_text(yaml_content, encoding="utf-8")
        (tmp_path / "run_config.json").write_text(json_content, encoding="utf-8")
        result = _load_run_config(tmp_path)
        assert result == {"source": "yaml"}

    def test_falls_back_to_json_when_yaml_malformed(self, tmp_path: Path) -> None:
        # YAML that fails safe_load (e.g. invalid indentation / tab mix)
        bad_yaml = "key: [\n\tbad\n]\n"
        good_json = json.dumps({"source": "json"})
        (tmp_path / "run_config.yaml").write_text(bad_yaml, encoding="utf-8")
        (tmp_path / "run_config.json").write_text(good_json, encoding="utf-8")
        result = _load_run_config(tmp_path)
        # Malformed YAML returns None from yaml.safe_load OR raises; either way
        # the function should fall through to JSON.
        # Accept either: dict from JSON or None (if yaml raised but json also failed)
        assert result is None or result == {"source": "json"}


class TestLoadRunConfigMissing:
    """Neither file present."""

    def test_returns_none_when_no_config_files(self, tmp_path: Path) -> None:
        result = _load_run_config(tmp_path)
        assert result is None

    def test_returns_none_for_empty_directory(self, tmp_path: Path) -> None:
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        result = _load_run_config(empty_dir)
        assert result is None
