"""Tests for the intake config loader.

Covers YAML loading, validation, defaults, platform rules,
org filtering, and error handling.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from launch.intake.config_loader import (
    IntakeConfig,
    IntakeConfigError,
    OrgConfig,
    PlatformRule,
    ScannerConfig,
    load_intake_config,
    repo_matches_org_filters,
    resolve_platform_for_repo,
    resolve_token,
)


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _write_config(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "intake_config.yaml"
    path.write_text(yaml.dump(data), encoding="utf-8")
    return path


def _minimal_config() -> dict:
    return {
        "schema_version": "1.1",
        "organizations": [
            {"name": "aspose-3d-foss"},
        ],
    }


# ---------------------------------------------------------------------------
# Tests: load_intake_config
# ---------------------------------------------------------------------------


class TestLoadIntakeConfig:
    def test_minimal_config(self, tmp_path):
        path = _write_config(tmp_path, _minimal_config())
        cfg = load_intake_config(path)
        assert cfg.schema_version == "1.1"
        assert len(cfg.organizations) == 1
        assert cfg.organizations[0].name == "aspose-3d-foss"
        assert cfg.organizations[0].default_platform == "python"

    def test_schema_version_1_0(self, tmp_path):
        data = _minimal_config()
        data["schema_version"] = "1.0"
        path = _write_config(tmp_path, data)
        cfg = load_intake_config(path)
        assert cfg.schema_version == "1.0"

    def test_invalid_schema_version(self, tmp_path):
        data = _minimal_config()
        data["schema_version"] = "2.0"
        path = _write_config(tmp_path, data)
        with pytest.raises(IntakeConfigError, match="Unsupported schema_version"):
            load_intake_config(path)

    def test_missing_file(self, tmp_path):
        with pytest.raises(IntakeConfigError, match="not found"):
            load_intake_config(tmp_path / "nonexistent.yaml")

    def test_invalid_yaml(self, tmp_path):
        path = tmp_path / "bad.yaml"
        path.write_text(": [invalid: yaml", encoding="utf-8")
        with pytest.raises(IntakeConfigError, match="YAML parse error"):
            load_intake_config(path)

    def test_not_a_mapping(self, tmp_path):
        path = tmp_path / "bad.yaml"
        path.write_text("- item1\n- item2\n", encoding="utf-8")
        with pytest.raises(IntakeConfigError, match="must be a YAML mapping"):
            load_intake_config(path)

    def test_missing_organizations(self, tmp_path):
        data = {"schema_version": "1.1"}
        path = _write_config(tmp_path, data)
        with pytest.raises(IntakeConfigError, match="organizations"):
            load_intake_config(path)

    def test_empty_organizations(self, tmp_path):
        data = {"schema_version": "1.1", "organizations": []}
        path = _write_config(tmp_path, data)
        with pytest.raises(IntakeConfigError, match="non-empty"):
            load_intake_config(path)

    def test_org_missing_name(self, tmp_path):
        data = {"schema_version": "1.1", "organizations": [{"default_platform": "python"}]}
        path = _write_config(tmp_path, data)
        with pytest.raises(IntakeConfigError, match="name is required"):
            load_intake_config(path)

    def test_full_config_with_platform_rules(self, tmp_path):
        data = {
            "schema_version": "1.1",
            "organizations": [
                {
                    "name": "myorg",
                    "default_platform": "java",
                    "include_patterns": ["*-FOSS-*"],
                    "exclude_patterns": ["*-deprecated*"],
                    "platform_rules": [
                        {"name_pattern": "*-for-Python", "platform": "python"},
                        {"name_pattern": "*-for-.NET", "platform": "dotnet"},
                    ],
                },
            ],
            "scanner": {"per_page": 50, "activity_months": 6},
            "classifier": {"min_stars": 5, "require_readme": False},
            "scheduler": {"batch_size": 10, "sort_by": "pushed_at"},
            "generator": {"output_dir": "out/pilots"},
            "state_dir": "custom_state",
        }
        path = _write_config(tmp_path, data)
        cfg = load_intake_config(path)

        assert cfg.organizations[0].name == "myorg"
        assert cfg.organizations[0].default_platform == "java"
        assert cfg.organizations[0].include_patterns == ["*-FOSS-*"]
        assert cfg.organizations[0].exclude_patterns == ["*-deprecated*"]
        assert len(cfg.organizations[0].platform_rules) == 2
        assert cfg.organizations[0].platform_rules[0].platform == "python"

        assert cfg.scanner.per_page == 50
        assert cfg.scanner.activity_months == 6
        assert cfg.classifier.min_stars == 5
        assert cfg.classifier.require_readme is False
        assert cfg.scheduler.batch_size == 10
        assert cfg.scheduler.sort_by == "pushed_at"
        assert cfg.generator.output_dir == "out/pilots"
        assert cfg.state_dir == "custom_state"

    def test_invalid_default_platform(self, tmp_path):
        data = {
            "schema_version": "1.1",
            "organizations": [{"name": "org", "default_platform": "brainfuck"}],
        }
        path = _write_config(tmp_path, data)
        with pytest.raises(IntakeConfigError, match="invalid platform"):
            load_intake_config(path)

    def test_invalid_rule_platform(self, tmp_path):
        data = {
            "schema_version": "1.1",
            "organizations": [
                {
                    "name": "org",
                    "platform_rules": [{"name_pattern": "*", "platform": "cobol"}],
                },
            ],
        }
        path = _write_config(tmp_path, data)
        with pytest.raises(IntakeConfigError, match="invalid platform"):
            load_intake_config(path)

    def test_defaults_applied(self, tmp_path):
        path = _write_config(tmp_path, _minimal_config())
        cfg = load_intake_config(path)

        assert cfg.scanner.per_page == 100
        assert cfg.scanner.rate_limit_delay_s == 1.0
        assert cfg.scanner.max_pages == 10
        assert cfg.scanner.activity_months == 12
        assert cfg.scanner.github_token_env == "GITHUB_TOKEN"
        assert cfg.classifier.min_stars == 0
        assert cfg.classifier.require_readme is True
        assert cfg.scheduler.batch_size == 5
        assert cfg.scheduler.sort_by == "stars"
        assert cfg.generator.output_dir == "configs/pilots"
        assert cfg.state_dir == "intake"


# ---------------------------------------------------------------------------
# Tests: resolve_token
# ---------------------------------------------------------------------------


class TestResolveToken:
    def test_token_from_env(self, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test123")
        token = resolve_token(ScannerConfig())
        assert token == "ghp_test123"

    def test_no_token(self, monkeypatch):
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        token = resolve_token(ScannerConfig())
        assert token is None

    def test_custom_env_var(self, monkeypatch):
        monkeypatch.setenv("MY_TOKEN", "custom_val")
        token = resolve_token(ScannerConfig(github_token_env="MY_TOKEN"))
        assert token == "custom_val"


# ---------------------------------------------------------------------------
# Tests: resolve_platform_for_repo
# ---------------------------------------------------------------------------


class TestResolvePlatformForRepo:
    def test_no_rules_returns_default(self):
        org = OrgConfig(name="myorg", default_platform="java")
        assert resolve_platform_for_repo("SomeRepo", org) == "java"

    def test_matching_rule(self):
        org = OrgConfig(
            name="myorg",
            default_platform="python",
            platform_rules=[
                PlatformRule(name_pattern="*-for-Java", platform="java"),
                PlatformRule(name_pattern="*-for-.NET", platform="dotnet"),
            ],
        )
        assert resolve_platform_for_repo("Aspose.Cells-FOSS-for-Java", org) == "java"

    def test_first_rule_wins(self):
        org = OrgConfig(
            name="myorg",
            platform_rules=[
                PlatformRule(name_pattern="*", platform="ruby"),
                PlatformRule(name_pattern="*-for-Java", platform="java"),
            ],
        )
        assert resolve_platform_for_repo("Aspose.Cells-FOSS-for-Java", org) == "ruby"

    def test_case_insensitive_match(self):
        org = OrgConfig(
            name="myorg",
            platform_rules=[
                PlatformRule(name_pattern="*-for-python", platform="python"),
            ],
        )
        assert resolve_platform_for_repo("Aspose.Cells-FOSS-for-Python", org) == "python"


# ---------------------------------------------------------------------------
# Tests: repo_matches_org_filters
# ---------------------------------------------------------------------------


class TestRepoMatchesOrgFilters:
    def test_default_includes_all(self):
        org = OrgConfig(name="myorg")
        assert repo_matches_org_filters("anything", org) is True

    def test_include_pattern(self):
        org = OrgConfig(name="myorg", include_patterns=["*-FOSS-*"])
        assert repo_matches_org_filters("Aspose.Cells-FOSS-for-Python", org) is True
        assert repo_matches_org_filters("Aspose.Cells", org) is False

    def test_exclude_pattern(self):
        org = OrgConfig(
            name="myorg",
            include_patterns=["*"],
            exclude_patterns=["*-deprecated*"],
        )
        assert repo_matches_org_filters("Aspose.Cells-FOSS", org) is True
        assert repo_matches_org_filters("old-deprecated-lib", org) is False

    def test_case_insensitive(self):
        org = OrgConfig(name="myorg", include_patterns=["*foss*"])
        assert repo_matches_org_filters("Aspose.Cells-FOSS-for-Python", org) is True
