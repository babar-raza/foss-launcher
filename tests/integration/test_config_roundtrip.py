"""SRI-04: Integration test — generated config roundtrips through RunConfig.

Proves the full path: generate_config() -> YAML write -> RunConfig parse -> success.
"""
from __future__ import annotations

import yaml
import pytest

from launcher.intake.config_generator import generate_config, write_config
from launcher.models.run_config import RunConfig


def _mock_repo(**overrides) -> dict:
    """Build a realistic GitHub API repo dict."""
    base = {
        "id": 99999,
        "name": "Aspose.Cells-for-Python-via-.NET",
        "full_name": "aspose-cells-foss/Aspose.Cells-for-Python-via-.NET",
        "html_url": "https://github.com/aspose-cells-foss/Aspose.Cells-for-Python-via-.NET",
        "description": "Free and open-source spreadsheet library",
        "stargazers_count": 42,
        "language": "Python",
        "license": {"spdx_id": "MIT", "name": "MIT License"},
        "pushed_at": "2026-02-15T10:00:00Z",
        "default_branch": "main",
        "size": 1200,
        "owner": {"login": "aspose-cells-foss", "type": "Organization"},
        "topics": ["spreadsheet", "python", "aspose"],
    }
    base.update(overrides)
    return base


class TestConfigRoundtrip:
    """Generated configs must parse as valid RunConfig instances."""

    def test_roundtrip_default_template(self, tmp_path):
        """generate_config() -> YAML -> RunConfig with default template."""
        repo = _mock_repo()
        config = generate_config(repo)

        # Write to YAML
        yaml_path = tmp_path / "test_pilot.yaml"
        yaml_str = yaml.dump(config, default_flow_style=False, sort_keys=False)
        yaml_path.write_text(yaml_str, encoding="utf-8")

        # Read back and parse — RunConfig ignores extra fields
        raw = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        # Filter to only RunConfig fields
        rc = RunConfig(**{
            k: v for k, v in raw.items()
            if k in RunConfig.model_fields
        })

        assert rc.family == "cells"
        assert rc.platform == "python"
        assert rc.repo_url == repo["html_url"]
        assert rc.launch_tier == "auto"
        assert rc.validation_profile == "pilot"

    def test_roundtrip_via_write_config(self, tmp_path):
        """write_config() -> file -> RunConfig parse."""
        repo = _mock_repo()
        path = write_config(repo, tmp_path)
        assert path is not None
        assert path.exists()

        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        rc = RunConfig(**{
            k: v for k, v in raw.items()
            if k in RunConfig.model_fields
        })
        assert rc.family == "cells"
        assert rc.platform == "python"
        assert rc.llm is not None
        assert rc.llm.primary.model == "qwen3-next"

    def test_roundtrip_java_platform(self, tmp_path):
        """Java platform detection survives roundtrip."""
        repo = _mock_repo(
            name="Aspose.Cells-for-Java",
            html_url="https://github.com/aspose-cells-foss/Aspose.Cells-for-Java",
            language="Java",
        )
        config = generate_config(repo)

        yaml_str = yaml.dump(config, default_flow_style=False)
        raw = yaml.safe_load(yaml_str)
        rc = RunConfig(**{k: v for k, v in raw.items() if k in RunConfig.model_fields})

        assert rc.platform == "java"
        assert rc.family == "cells"

    def test_extended_fields_present_but_ignored(self):
        """Extended fields exist in generated config but don't break RunConfig."""
        repo = _mock_repo()
        config = generate_config(repo)

        # These extended fields should be present
        assert "github_ref" in config
        assert "product_slug" in config
        assert "product_name" in config
        assert "budgets" in config
        assert "telemetry" in config

        # RunConfig should parse without them
        core_fields = {k: v for k, v in config.items() if k in RunConfig.model_fields}
        rc = RunConfig(**core_fields)
        assert rc.family == "cells"

    def test_custom_template_roundtrip(self, tmp_path):
        """Custom template fields override defaults and survive roundtrip."""
        custom_template = {
            "family": "",
            "platform": "",
            "repo_url": "",
            "launch_tier": "minimal",
            "validation_profile": "production",
            "llm": {
                "primary": {
                    "base_url": "https://custom.example.com/v1",
                    "model": "custom-model",
                },
            },
            "output": {"goal": "pr", "run_dir": "custom_runs/"},
        }
        repo = _mock_repo()
        config = generate_config(repo, template=custom_template)

        yaml_str = yaml.dump(config, default_flow_style=False)
        raw = yaml.safe_load(yaml_str)
        rc = RunConfig(**{k: v for k, v in raw.items() if k in RunConfig.model_fields})

        assert rc.launch_tier == "minimal"
        assert rc.validation_profile == "production"
        assert rc.llm.primary.model == "custom-model"
        assert rc.output.goal == "pr"
