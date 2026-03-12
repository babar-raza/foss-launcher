"""Unit tests for GoldenConfig in RunConfig (TC-3875)."""
from __future__ import annotations

import pytest

from launcher.models.run_config import GoldenConfig, RunConfig


_BASE_CONFIG = {
    "family": "cells",
    "platform": "python",
    "repo_url": "https://github.com/example/repo",
}


class TestGoldenConfigDefaults:
    def test_disabled_by_default(self) -> None:
        gc = GoldenConfig()
        assert gc.enabled is False

    def test_default_dir(self) -> None:
        gc = GoldenConfig()
        assert gc.dir == "golden/"

    def test_enabled_from_kwargs(self) -> None:
        gc = GoldenConfig(enabled=True, dir="golden/")
        assert gc.enabled is True
        assert gc.dir == "golden/"


class TestGoldenConfigDictCompat:
    """GoldenConfig.get() must behave like dict.get() for legacy code paths."""

    def test_get_enabled_true(self) -> None:
        gc = GoldenConfig(enabled=True)
        assert gc.get("enabled") is True

    def test_get_enabled_false(self) -> None:
        gc = GoldenConfig(enabled=False)
        assert gc.get("enabled") is False

    def test_get_dir_default(self) -> None:
        gc = GoldenConfig()
        assert gc.get("dir") == "golden/"

    def test_get_dir_custom(self) -> None:
        gc = GoldenConfig(enabled=True, dir="custom_golden/")
        assert gc.get("dir", "golden/") == "custom_golden/"

    def test_get_missing_key_returns_default(self) -> None:
        gc = GoldenConfig()
        assert gc.get("nonexistent_key", "fallback") == "fallback"

    def test_get_missing_key_returns_none(self) -> None:
        gc = GoldenConfig()
        assert gc.get("nonexistent_key") is None


class TestRunConfigGoldenField:
    def test_golden_defaults_disabled(self) -> None:
        config = RunConfig.model_validate(_BASE_CONFIG)
        assert config.golden.enabled is False
        assert config.golden.dir == "golden/"

    def test_golden_enabled_via_yaml_dict(self) -> None:
        data = {**_BASE_CONFIG, "golden": {"enabled": True, "dir": "golden/"}}
        config = RunConfig.model_validate(data)
        assert config.golden.enabled is True
        assert config.golden.dir == "golden/"

    def test_golden_custom_dir(self) -> None:
        data = {**_BASE_CONFIG, "golden": {"enabled": True, "dir": "my_golden/"}}
        config = RunConfig.model_validate(data)
        assert config.golden.dir == "my_golden/"

    def test_golden_get_works_on_config_golden(self) -> None:
        """Simulates generate worker: getattr(context.config, 'golden', {}).get('enabled')"""
        data = {**_BASE_CONFIG, "golden": {"enabled": True}}
        config = RunConfig.model_validate(data)
        golden_cfg = getattr(config, "golden", {}) or {}
        assert golden_cfg.get("enabled") is True
        assert golden_cfg.get("dir", "golden/") == "golden/"

    def test_golden_get_works_disabled(self) -> None:
        config = RunConfig.model_validate(_BASE_CONFIG)
        golden_cfg = getattr(config, "golden", {}) or {}
        assert not golden_cfg.get("enabled")

    def test_golden_extra_ignore_does_not_drop_golden(self) -> None:
        """extra='ignore' should NOT drop the golden field since it is declared."""
        data = {**_BASE_CONFIG, "golden": {"enabled": True}, "unknown_extra": "dropped"}
        config = RunConfig.model_validate(data)
        assert config.golden.enabled is True
