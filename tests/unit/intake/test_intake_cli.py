"""Tests for the intake CLI commands.

Covers argument parsing and basic command behavior with mocked
scanner/classifier/generator backends.

TC: TC-2544, TC-2545
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from launch.cli.main import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# Fixture: realistic repo for mocked scan results
# ---------------------------------------------------------------------------


def _make_repo(
    name: str = "MyRepo",
    full_name: str = "myorg/MyRepo",
    html_url: str = "https://github.com/myorg/MyRepo",
    stars: int = 10,
    language: str = "Python",
    license_spdx: str = "MIT",
) -> dict:
    return {
        "id": 12345,
        "name": name,
        "full_name": full_name,
        "html_url": html_url,
        "description": "A test repo",
        "stargazers_count": stars,
        "language": language,
        "license": {"spdx_id": license_spdx, "name": license_spdx},
        "pushed_at": "2026-02-01T00:00:00Z",
        "default_branch": "main",
        "size": 500,
        "owner": {"login": "myorg", "type": "Organization"},
        "topics": [],
    }


# ---------------------------------------------------------------------------
# Tests: launch intake scan
# ---------------------------------------------------------------------------


class TestIntakeScan:
    @patch("launch.intake.org_scanner.scan_orgs")
    def test_scan_basic(self, mock_scan_orgs):
        repos = [_make_repo()]
        mock_scan_orgs.return_value = repos

        result = runner.invoke(app, ["intake", "scan", "--orgs", "myorg", "--dry-run"])
        assert result.exit_code == 0
        assert "Discovered 1 repos" in result.stdout

    def test_scan_empty_orgs(self):
        result = runner.invoke(app, ["intake", "scan", "--orgs", ""])
        assert result.exit_code == 1

    @patch("launch.intake.org_scanner.scan_orgs")
    def test_scan_multiple_orgs(self, mock_scan_orgs):
        mock_scan_orgs.return_value = [_make_repo()]

        result = runner.invoke(app, ["intake", "scan", "--orgs", "org1,org2", "--dry-run"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Tests: launch intake classify
# ---------------------------------------------------------------------------


class TestIntakeClassify:
    @patch("launch.intake.org_scanner.scan_org")
    def test_classify_found(self, mock_scan_org):
        mock_scan_org.return_value = [_make_repo()]

        result = runner.invoke(
            app, ["intake", "classify", "--repo", "https://github.com/myorg/MyRepo"]
        )
        assert result.exit_code == 0
        assert "eligible" in result.stdout

    @patch("launch.intake.org_scanner.scan_org")
    def test_classify_not_found(self, mock_scan_org):
        mock_scan_org.return_value = []

        result = runner.invoke(
            app, ["intake", "classify", "--repo", "https://github.com/myorg/Missing"]
        )
        assert result.exit_code == 1

    def test_classify_invalid_url(self):
        result = runner.invoke(
            app, ["intake", "classify", "--repo", "not-a-url"]
        )
        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# Tests: launch intake generate
# ---------------------------------------------------------------------------


class TestIntakeGenerate:
    @patch("launch.intake.org_scanner.scan_org")
    def test_generate_basic(self, mock_scan_org, tmp_path):
        mock_scan_org.return_value = [_make_repo()]

        result = runner.invoke(
            app, [
                "intake", "generate",
                "--repo", "https://github.com/myorg/MyRepo",
                "--output", str(tmp_path),
            ]
        )
        assert result.exit_code == 0
        assert "Generated" in result.stdout

    @patch("launch.intake.org_scanner.scan_org")
    def test_generate_not_found(self, mock_scan_org, tmp_path):
        mock_scan_org.return_value = []

        result = runner.invoke(
            app, [
                "intake", "generate",
                "--repo", "https://github.com/myorg/Missing",
                "--output", str(tmp_path),
            ]
        )
        assert result.exit_code == 1

    def test_generate_invalid_url(self, tmp_path):
        result = runner.invoke(
            app, [
                "intake", "generate",
                "--repo", "not-a-url",
                "--output", str(tmp_path),
            ]
        )
        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# Tests: config file loading
# ---------------------------------------------------------------------------


class TestIntakeConfigLoading:
    @patch("launch.intake.org_scanner.scan_orgs")
    def test_scan_from_config_file(self, mock_scan_orgs, tmp_path):
        """--config loads orgs from file when --orgs not given."""
        mock_scan_orgs.return_value = [_make_repo()]

        config_data = {
            "schema_version": "1.1",
            "organizations": [{"name": "myorg"}],
        }
        config_path = tmp_path / "intake.yaml"
        import yaml
        config_path.write_text(yaml.dump(config_data), encoding="utf-8")

        result = runner.invoke(
            app, ["intake", "scan", "--config", str(config_path), "--dry-run"]
        )
        assert result.exit_code == 0
        assert "Discovered" in result.stdout

    @patch("launch.intake.org_scanner.scan_orgs")
    def test_scan_orgs_override_config(self, mock_scan_orgs, tmp_path):
        """--orgs overrides config file organizations."""
        mock_scan_orgs.return_value = [_make_repo()]

        config_data = {
            "schema_version": "1.1",
            "organizations": [{"name": "config-org"}],
        }
        config_path = tmp_path / "intake.yaml"
        import yaml
        config_path.write_text(yaml.dump(config_data), encoding="utf-8")

        result = runner.invoke(
            app, [
                "intake", "scan",
                "--orgs", "override-org",
                "--config", str(config_path),
                "--dry-run",
            ]
        )
        assert result.exit_code == 0
        # Verify the override org was passed, not the config org
        call_args = mock_scan_orgs.call_args
        assert "override-org" in call_args[0][0]

    @patch("launch.cli.main._repo_root")
    def test_scan_no_orgs_no_config(self, mock_repo_root, tmp_path):
        """No --orgs and no config file should fail with clear message."""
        mock_repo_root.return_value = tmp_path
        result = runner.invoke(app, ["intake", "scan", "--dry-run"])
        assert result.exit_code == 1
        assert "No organizations" in result.stdout

    def test_scan_bad_config_file(self, tmp_path):
        """Invalid config file should produce error."""
        bad_config = tmp_path / "bad.yaml"
        bad_config.write_text("not_valid: [broken", encoding="utf-8")
        result = runner.invoke(
            app, ["intake", "scan", "--config", str(bad_config), "--dry-run"]
        )
        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# Tests: launch intake onboard
# ---------------------------------------------------------------------------


class TestIntakeOnboard:
    @patch("launch.intake.org_scanner.scan_orgs")
    def test_onboard_basic_dry_run(self, mock_scan_orgs, tmp_path):
        """Dry-run onboard prints summary without writing files."""
        mock_scan_orgs.return_value = [_make_repo()]

        result = runner.invoke(
            app, [
                "intake", "onboard",
                "--orgs", "myorg",
                "--dry-run",
                "--output", str(tmp_path),
            ]
        )
        assert result.exit_code == 0
        assert "Onboard Summary" in result.stdout
        assert "Dry-run mode" in result.stdout
        assert not list(tmp_path.glob("*.yaml"))

    @patch("launch.intake.org_scanner.scan_orgs")
    def test_onboard_generates_configs(self, mock_scan_orgs, tmp_path):
        """Non-dry-run onboard writes config files."""
        mock_scan_orgs.return_value = [_make_repo()]

        result = runner.invoke(
            app, [
                "intake", "onboard",
                "--orgs", "myorg",
                "--output", str(tmp_path),
            ]
        )
        assert result.exit_code == 0
        assert "Success" in result.stdout
        yamls = list(tmp_path.glob("*.yaml"))
        assert len(yamls) >= 1

    @patch("launch.intake.org_scanner.scan_orgs")
    def test_onboard_batch_size(self, mock_scan_orgs, tmp_path):
        """--batch-size limits how many repos are processed."""
        repos = [
            _make_repo(
                name=f"Repo{i}",
                full_name=f"myorg/Repo{i}",
                html_url=f"https://github.com/myorg/Repo{i}",
            )
            for i in range(5)
        ]
        mock_scan_orgs.return_value = repos

        result = runner.invoke(
            app, [
                "intake", "onboard",
                "--orgs", "myorg",
                "--batch-size", "2",
                "--dry-run",
                "--output", str(tmp_path),
            ]
        )
        assert result.exit_code == 0
        assert "Processed" in result.stdout

    @patch("launch.intake.org_scanner.scan_orgs")
    def test_onboard_org_override(self, mock_scan_orgs, tmp_path):
        """--orgs overrides config file organizations."""
        mock_scan_orgs.return_value = [_make_repo()]

        config_data = {
            "schema_version": "1.1",
            "organizations": [{"name": "config-org"}],
        }
        config_path = tmp_path / "intake.yaml"
        import yaml
        config_path.write_text(yaml.dump(config_data), encoding="utf-8")

        result = runner.invoke(
            app, [
                "intake", "onboard",
                "--orgs", "override-org",
                "--config", str(config_path),
                "--dry-run",
                "--output", str(tmp_path / "out"),
            ]
        )
        assert result.exit_code == 0
        call_args = mock_scan_orgs.call_args
        assert "override-org" in call_args[0][0]

    @patch("launch.intake.org_scanner.scan_orgs")
    def test_onboard_dedup(self, mock_scan_orgs, tmp_path):
        """Repos with existing configs are skipped on second run."""
        mock_scan_orgs.return_value = [_make_repo()]
        output_dir = tmp_path / "pilots"

        # First run creates config
        runner.invoke(
            app, [
                "intake", "onboard",
                "--orgs", "myorg",
                "--output", str(output_dir),
            ]
        )

        # Second run should skip (dedup)
        result = runner.invoke(
            app, [
                "intake", "onboard",
                "--orgs", "myorg",
                "--output", str(output_dir),
            ]
        )
        assert result.exit_code == 0
        assert "Skipped (dedup)" in result.stdout

    @patch("launch.cli.main._repo_root")
    def test_onboard_no_orgs_no_config(self, mock_repo_root, tmp_path):
        """No --orgs and no config file should fail."""
        mock_repo_root.return_value = tmp_path
        result = runner.invoke(
            app, ["intake", "onboard", "--dry-run", "--output", str(tmp_path)]
        )
        assert result.exit_code == 1
        assert "No organizations" in result.stdout

    @patch("launch.intake.org_scanner.scan_orgs")
    def test_onboard_no_repos_discovered(self, mock_scan_orgs, tmp_path):
        """Empty scan result prints warning and exits 0."""
        mock_scan_orgs.return_value = []

        result = runner.invoke(
            app, [
                "intake", "onboard",
                "--orgs", "empty-org",
                "--dry-run",
                "--output", str(tmp_path),
            ]
        )
        assert result.exit_code == 0
        assert "No repos discovered" in result.stdout

    @patch("launch.intake.org_scanner.scan_orgs")
    def test_onboard_scanner_error(self, mock_scan_orgs, tmp_path):
        """Scanner errors produce exit code 1."""
        from launch.intake.org_scanner import ScannerError
        mock_scan_orgs.side_effect = ScannerError("API down")

        result = runner.invoke(
            app, [
                "intake", "onboard",
                "--orgs", "myorg",
                "--output", str(tmp_path),
            ]
        )
        assert result.exit_code == 1
        assert "Scanner failed" in result.stdout

    @patch("launch.intake.org_scanner.scan_orgs")
    def test_onboard_from_config_file(self, mock_scan_orgs, tmp_path):
        """Config file provides orgs, scheduler, and classifier settings."""
        mock_scan_orgs.return_value = [_make_repo()]

        config_data = {
            "schema_version": "1.1",
            "organizations": [{"name": "myorg"}],
            "scheduler": {"batch_size": 3, "sort_by": "stars", "sort_order": "desc"},
            "classifier": {"min_stars": 0},
        }
        config_path = tmp_path / "intake.yaml"
        import yaml
        config_path.write_text(yaml.dump(config_data), encoding="utf-8")

        result = runner.invoke(
            app, [
                "intake", "onboard",
                "--config", str(config_path),
                "--dry-run",
                "--output", str(tmp_path / "out"),
            ]
        )
        assert result.exit_code == 0
        assert "Onboard Summary" in result.stdout

    @patch("launch.intake.org_scanner.scan_orgs")
    def test_onboard_verbose(self, mock_scan_orgs, tmp_path):
        """--verbose flag does not break the command."""
        mock_scan_orgs.return_value = [_make_repo()]

        result = runner.invoke(
            app, [
                "intake", "onboard",
                "--orgs", "myorg",
                "--dry-run",
                "--verbose",
                "--output", str(tmp_path),
            ]
        )
        assert result.exit_code == 0
