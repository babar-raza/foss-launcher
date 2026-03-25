"""Tests for the intake CLI commands.

Covers argument parsing and basic command behavior with mocked
scanner/classifier/generator backends.

TC: TC-2544, TC-2545
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from launcher.cli.main import app

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


def _make_inspection(repo: dict, platform: str = "python") -> dict:
    return {
        "repo": repo,
        "repo_url": repo["html_url"],
        "acquisition": {
            "repo_signals": {
                "readme_present": True,
                "is_empty_clone": False,
                "detected_manifest_files": ["pyproject.toml" if platform == "python" else "pom.xml"],
            }
        },
        "shared_facts": {
            "package_name": "myrepo" if platform == "python" else "org.example:demo",
            "license_type": "MIT",
            "primary_language": platform,
        },
        "platform": platform,
    }


# ---------------------------------------------------------------------------
# Tests: launch intake scan
# ---------------------------------------------------------------------------


class TestIntakeScan:
    @patch("launcher.intake.org_scanner.scan_orgs")
    def test_scan_basic(self, mock_scan_orgs):
        repos = [_make_repo()]
        mock_scan_orgs.return_value = repos

        result = runner.invoke(app, ["intake", "scan", "--orgs", "myorg", "--dry-run"])
        assert result.exit_code == 0
        assert "Discovered 1 repos" in result.stdout

    def test_scan_empty_orgs(self):
        result = runner.invoke(app, ["intake", "scan", "--orgs", ""])
        assert result.exit_code == 1

    @patch("launcher.intake.org_scanner.scan_orgs")
    def test_scan_multiple_orgs(self, mock_scan_orgs):
        mock_scan_orgs.return_value = [_make_repo()]

        result = runner.invoke(app, ["intake", "scan", "--orgs", "org1,org2", "--dry-run"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Tests: launch intake classify
# ---------------------------------------------------------------------------


class TestIntakeClassify:
    @patch("launcher.phase1.inspection.inspect_repo")
    @patch("launcher.intake.org_scanner.scan_org")
    def test_classify_found(self, mock_scan_org, mock_inspect_repo):
        mock_scan_org.return_value = [_make_repo()]
        mock_inspect_repo.return_value = {
            "repo": _make_repo(),
            "repo_url": "https://github.com/myorg/MyRepo",
            "acquisition": {
                "repo_signals": {
                    "readme_present": True,
                    "is_empty_clone": False,
                    "detected_manifest_files": ["pyproject.toml"],
                }
            },
            "shared_facts": {"package_name": "myrepo", "license_type": "MIT", "primary_language": "python"},
            "platform": "python",
        }

        result = runner.invoke(
            app, ["intake", "classify", "--repo", "https://github.com/myorg/MyRepo"]
        )
        assert result.exit_code == 0
        assert "eligible" in result.stdout

    @patch("launcher.intake.org_scanner.scan_org")
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
    @patch("launcher.phase1.inspection.inspect_repo")
    @patch("launcher.intake.org_scanner.scan_org")
    def test_generate_basic(self, mock_scan_org, mock_inspect_repo, tmp_path):
        mock_scan_org.return_value = [_make_repo()]
        mock_inspect_repo.return_value = {
            "repo": _make_repo(),
            "repo_url": "https://github.com/myorg/MyRepo",
            "acquisition": {
                "repo_signals": {
                    "readme_present": True,
                    "is_empty_clone": False,
                    "detected_manifest_files": ["pyproject.toml"],
                }
            },
            "shared_facts": {"package_name": "myrepo", "license_type": "MIT", "primary_language": "python"},
            "platform": "python",
        }

        result = runner.invoke(
            app, [
                "intake", "generate",
                "--repo", "https://github.com/myorg/MyRepo",
                "--output", str(tmp_path),
            ]
        )
        assert result.exit_code == 0
        assert "Generated" in result.stdout

    @patch("launcher.intake.org_scanner.scan_org")
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
    @patch("launcher.intake.org_scanner.scan_orgs")
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

    @patch("launcher.intake.org_scanner.scan_orgs")
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

    @patch("launcher.cli.intake._repo_root")
    def test_scan_no_orgs_no_config(self, mock_repo_root, tmp_path):
        """No --orgs and no config file should fail with clear message."""
        mock_repo_root.return_value = tmp_path
        result = runner.invoke(app, ["intake", "scan", "--dry-run"])
        assert result.exit_code == 1
        assert "No organizations" in result.output

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
    @patch("launcher.phase1.onboarding.inspect_repo")
    @patch("launcher.intake.org_scanner.scan_orgs")
    def test_onboard_basic_dry_run(self, mock_scan_orgs, mock_inspect_repo, tmp_path):
        """Dry-run onboard prints summary without writing files."""
        repo = _make_repo()
        mock_scan_orgs.return_value = [repo]
        mock_inspect_repo.return_value = _make_inspection(repo)

        result = runner.invoke(
            app, [
                "intake", "onboard",
                "--orgs", "myorg",
                "--dry-run",
                "--output", str(tmp_path),
            ]
        )
        assert result.exit_code == 0
        assert "Total scanned" in result.output
        assert "Dry-run mode" in result.stdout
        assert "artifact:" in result.stdout
        assert not list(tmp_path.glob("*.yaml"))
        mock_inspect_repo.assert_called_once()

    @patch("launcher.phase1.onboarding.inspect_repo")
    @patch("launcher.intake.org_scanner.scan_orgs")
    def test_onboard_generates_configs(self, mock_scan_orgs, mock_inspect_repo, tmp_path):
        """Non-dry-run onboard writes config files."""
        repo = _make_repo()
        mock_scan_orgs.return_value = [repo]
        mock_inspect_repo.return_value = _make_inspection(repo)

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

    @patch("launcher.phase1.onboarding.inspect_repo")
    @patch("launcher.intake.org_scanner.scan_orgs")
    def test_onboard_batch_size(self, mock_scan_orgs, mock_inspect_repo, tmp_path):
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
        mock_inspect_repo.side_effect = [_make_inspection(repo) for repo in repos]

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

    @patch("launcher.phase1.onboarding.inspect_repo")
    @patch("launcher.intake.org_scanner.scan_orgs")
    def test_onboard_org_override(self, mock_scan_orgs, mock_inspect_repo, tmp_path):
        """--orgs overrides config file organizations."""
        repo = _make_repo()
        mock_scan_orgs.return_value = [repo]
        mock_inspect_repo.return_value = _make_inspection(repo)

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

    @patch("launcher.phase1.onboarding.inspect_repo")
    @patch("launcher.intake.org_scanner.scan_orgs")
    def test_onboard_dedup(self, mock_scan_orgs, mock_inspect_repo, tmp_path):
        """Repos with existing configs are skipped on second run."""
        repo = _make_repo()
        mock_scan_orgs.return_value = [repo]
        mock_inspect_repo.return_value = _make_inspection(repo)
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

    @patch("launcher.cli.intake._repo_root")
    def test_onboard_no_orgs_no_config(self, mock_repo_root, tmp_path):
        """No --orgs and no config file should fail."""
        mock_repo_root.return_value = tmp_path
        result = runner.invoke(
            app, ["intake", "onboard", "--dry-run", "--output", str(tmp_path)]
        )
        assert result.exit_code == 1
        assert "No organizations" in result.output

    @patch("launcher.intake.org_scanner.scan_orgs")
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

    @patch("launcher.intake.org_scanner.scan_orgs")
    def test_onboard_scanner_error(self, mock_scan_orgs, tmp_path):
        """Scanner errors produce exit code 1."""
        from launcher.intake.org_scanner import ScannerError
        mock_scan_orgs.side_effect = ScannerError("API down")

        result = runner.invoke(
            app, [
                "intake", "onboard",
                "--orgs", "myorg",
                "--output", str(tmp_path),
            ]
        )
        assert result.exit_code == 1
        assert "Scanner failed" in result.output

    @patch("launcher.phase1.onboarding.inspect_repo")
    @patch("launcher.intake.org_scanner.scan_orgs")
    def test_onboard_from_config_file(self, mock_scan_orgs, mock_inspect_repo, tmp_path):
        """Config file provides orgs, scheduler, and classifier settings."""
        repo = _make_repo()
        mock_scan_orgs.return_value = [repo]
        mock_inspect_repo.return_value = _make_inspection(repo)

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
        assert "Total scanned" in result.output

    @patch("launcher.phase1.onboarding.inspect_repo")
    @patch("launcher.intake.org_scanner.scan_orgs")
    def test_onboard_verbose(self, mock_scan_orgs, mock_inspect_repo, tmp_path):
        """--verbose flag does not break the command."""
        repo = _make_repo()
        mock_scan_orgs.return_value = [repo]
        mock_inspect_repo.return_value = _make_inspection(repo)

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

    @patch("launcher.phase1.onboarding.inspect_repo")
    @patch("launcher.intake.org_scanner.scan_orgs")
    def test_onboard_ineligible_repo_not_generated(self, mock_scan_orgs, mock_inspect_repo, tmp_path):
        """Ineligible repos remain visible in the summary but are not generated."""
        repo = _make_repo()
        mock_scan_orgs.return_value = [repo]
        inspection = _make_inspection(repo)
        inspection["acquisition"]["repo_signals"]["readme_present"] = False
        mock_inspect_repo.return_value = inspection

        result = runner.invoke(
            app,
            [
                "intake", "onboard",
                "--orgs", "myorg",
                "--dry-run",
                "--output", str(tmp_path),
            ],
        )

        assert result.exit_code == 0
        assert "Ineligible" in result.stdout
        assert "Processed" in result.stdout
        assert "would_generate" not in result.stdout

    # ------------------------------------------------------------------
    # TC-5173: scan_state.json persistence
    # ------------------------------------------------------------------

    @patch("launcher.cli.intake._repo_root")
    @patch("launcher.phase1.onboarding.inspect_repo")
    @patch("launcher.intake.org_scanner.requests.get")
    def test_onboard_persists_scan_state(self, mock_get, mock_inspect, mock_repo_root, tmp_path):
        """TC-5173: intake onboard (non-dry-run) writes scan_state.json with discovered repos."""
        import json as _json

        def _resp(json_data=None):
            m = MagicMock()
            m.status_code = 200
            m.json.return_value = json_data or []
            m.headers = {}
            m.text = ""
            return m

        repo = _make_repo()
        mock_get.return_value = _resp(json_data=[repo])
        mock_inspect.return_value = _make_inspection(repo)
        mock_repo_root.return_value = tmp_path

        result = runner.invoke(
            app,
            ["intake", "onboard", "--orgs", "myorg", "--output", str(tmp_path / "pilots")],
        )
        assert result.exit_code == 0, result.output

        scan_state = tmp_path / "intake" / "scan_state.json"
        assert scan_state.exists(), "scan_state.json must be written on non-dry-run onboard"
        state = _json.loads(scan_state.read_text(encoding="utf-8"))
        assert "myorg/MyRepo" in state["seen_repos"]
        assert "last_scan_ts" in state

    @patch("launcher.cli.intake._repo_root")
    @patch("launcher.phase1.onboarding.inspect_repo")
    @patch("launcher.intake.org_scanner.requests.get")
    def test_onboard_no_duplicate_seen_repos_on_rerun(self, mock_get, mock_inspect, mock_repo_root, tmp_path):
        """TC-5173: re-running intake onboard doesn't duplicate seen_repos entries."""
        import json as _json

        def _resp(json_data=None):
            m = MagicMock()
            m.status_code = 200
            m.json.return_value = json_data or []
            m.headers = {}
            m.text = ""
            return m

        repo = _make_repo()
        mock_inspect.return_value = _make_inspection(repo)
        mock_repo_root.return_value = tmp_path
        output_dir = tmp_path / "pilots"

        mock_get.return_value = _resp(json_data=[repo])
        runner.invoke(app, ["intake", "onboard", "--orgs", "myorg", "--output", str(output_dir)])

        # Second run: same repo already in seen_repos → scan_org skips it
        mock_get.return_value = _resp(json_data=[repo])
        runner.invoke(app, ["intake", "onboard", "--orgs", "myorg", "--output", str(output_dir)])

        state = _json.loads((tmp_path / "intake" / "scan_state.json").read_text(encoding="utf-8"))
        assert state["seen_repos"].count("myorg/MyRepo") == 1

    @patch("launcher.cli.intake._repo_root")
    @patch("launcher.phase1.onboarding.inspect_repo")
    @patch("launcher.intake.org_scanner.requests.get")
    def test_onboard_creates_scan_state_if_absent(self, mock_get, mock_inspect, mock_repo_root, tmp_path):
        """TC-5173: intake onboard creates scan_state.json from scratch when file absent."""
        import json as _json

        def _resp(json_data=None):
            m = MagicMock()
            m.status_code = 200
            m.json.return_value = json_data or []
            m.headers = {}
            m.text = ""
            return m

        repo = _make_repo()
        mock_get.return_value = _resp(json_data=[repo])
        mock_inspect.return_value = _make_inspection(repo)
        mock_repo_root.return_value = tmp_path

        assert not (tmp_path / "intake" / "scan_state.json").exists()

        result = runner.invoke(
            app,
            ["intake", "onboard", "--orgs", "myorg", "--output", str(tmp_path / "pilots")],
        )
        assert result.exit_code == 0, result.output
        scan_state = tmp_path / "intake" / "scan_state.json"
        assert scan_state.exists()
        state = _json.loads(scan_state.read_text(encoding="utf-8"))
        assert len(state["seen_repos"]) >= 1


# ---------------------------------------------------------------------------
# Tests: Intake telemetry event emission (SRI-10)
# ---------------------------------------------------------------------------


class TestIntakeTelemetry:
    """Verify intake commands emit telemetry events."""

    @patch("launcher.cli.intake._emit_intake_event")
    @patch("launcher.intake.org_scanner.scan_orgs")
    def test_scan_emits_event(self, mock_scan_orgs, mock_emit):
        """scan command emits intake_scan_complete event."""
        mock_scan_orgs.return_value = [_make_repo()]

        result = runner.invoke(app, ["intake", "scan", "--orgs", "myorg", "--dry-run"])
        assert result.exit_code == 0

        mock_emit.assert_called_once()
        call_args = mock_emit.call_args
        assert call_args[0][0] == "intake_scan_complete"
        data = call_args[0][1]
        assert data["org_count"] == 1
        assert data["repo_count"] == 1
        assert "elapsed_ms" in data
        assert data["dry_run"] is True

    @patch("launcher.phase1.onboarding.inspect_repo")
    @patch("launcher.cli.intake._emit_intake_event")
    @patch("launcher.intake.org_scanner.scan_orgs")
    def test_onboard_emits_event(self, mock_scan_orgs, mock_emit, mock_inspect_repo, tmp_path):
        """onboard command emits intake_onboard_complete event."""
        repo = _make_repo()
        mock_scan_orgs.return_value = [repo]
        mock_inspect_repo.return_value = _make_inspection(repo)

        result = runner.invoke(
            app, [
                "intake", "onboard",
                "--orgs", "myorg",
                "--dry-run",
                "--output", str(tmp_path),
            ]
        )
        assert result.exit_code == 0

        mock_emit.assert_called_once()
        call_args = mock_emit.call_args
        assert call_args[0][0] == "intake_onboard_complete"
        data = call_args[0][1]
        assert data["org_count"] == 1
        assert "total_scanned" in data
        assert "eligible" in data
        assert "processed" in data
        assert "elapsed_ms" in data
        assert data["dry_run"] is True

    @patch("launcher.cli.intake._emit_intake_event")
    @patch("launcher.intake.org_scanner.scan_orgs")
    def test_scan_event_not_emitted_on_error(self, mock_scan_orgs, mock_emit):
        """scan command does NOT emit event when scanner fails."""
        from launcher.intake.org_scanner import ScannerError
        mock_scan_orgs.side_effect = ScannerError("API down")

        result = runner.invoke(app, ["intake", "scan", "--orgs", "myorg"])
        assert result.exit_code == 1
        mock_emit.assert_not_called()

    def test_emit_intake_event_graceful_failure(self, tmp_path):
        """_emit_intake_event swallows exceptions without crashing."""
        from launcher.cli.intake import _emit_intake_event

        # Patch at the source module since it's a lazy import
        with patch("launcher.state.event_log.append_event", side_effect=OSError("disk full")):
            _emit_intake_event(
                "intake_scan_complete",
                {"test": True},
                state_dir=tmp_path,
            )
        # No exception raised = pass

    def test_emit_intake_event_writes_ndjson(self, tmp_path):
        """_emit_intake_event creates intake_events.ndjson with valid event."""
        import json
        from launcher.cli.intake import _emit_intake_event

        _emit_intake_event(
            "intake_scan_complete",
            {"org_count": 2, "repo_count": 5},
            state_dir=tmp_path,
        )

        events_file = tmp_path / "intake_events.ndjson"
        assert events_file.exists()
        line = events_file.read_text(encoding="utf-8").strip()
        event = json.loads(line)
        assert event["event_type"] == "intake_scan_complete"
        assert event["worker"] == "intake"
        assert event["data"]["org_count"] == 2
        assert event["data"]["repo_count"] == 5


# ---------------------------------------------------------------------------
# TC-5190: --force flag for intake generate (needs_review bypass)
# ---------------------------------------------------------------------------


class TestIntakeGenerateForce:
    """TC-5190: --force bypasses needs_review classification."""

    def _make_needs_review_inspection(self):
        """Return an inspection dict that triggers needs_review (is_template=True)."""
        return {
            "repo": {**_make_repo(), "is_template": True},
            "repo_url": "https://github.com/myorg/MyRepo",
            "acquisition": {
                "repo_signals": {
                    "readme_present": True,
                    "is_empty_clone": False,
                    "detected_manifest_files": ["pyproject.toml"],
                }
            },
            "shared_facts": {"package_name": "myrepo", "license_type": "MIT", "primary_language": "python"},
            "platform": "python",
        }

    @patch("launcher.phase1.inspection.inspect_repo")
    @patch("launcher.intake.org_scanner.scan_org")
    def test_force_bypasses_needs_review(self, mock_scan_org, mock_inspect_repo, tmp_path):
        """TC-5190: --force generates config even when classification=needs_review."""
        mock_scan_org.return_value = [_make_repo()]
        mock_inspect_repo.return_value = self._make_needs_review_inspection()

        result = runner.invoke(app, [
            "intake", "generate",
            "--repo", "https://github.com/myorg/MyRepo",
            "--output", str(tmp_path),
            "--force",
        ])
        assert result.exit_code == 0
        assert "force-generated" in result.stdout.lower() or "generated" in result.stdout.lower()

    @patch("launcher.phase1.inspection.inspect_repo")
    @patch("launcher.intake.org_scanner.scan_org")
    def test_without_force_needs_review_exits(self, mock_scan_org, mock_inspect_repo, tmp_path):
        """TC-5190: without --force, needs_review exits with code 1."""
        mock_scan_org.return_value = [_make_repo()]
        mock_inspect_repo.return_value = self._make_needs_review_inspection()

        result = runner.invoke(app, [
            "intake", "generate",
            "--repo", "https://github.com/myorg/MyRepo",
            "--output", str(tmp_path),
        ])
        assert result.exit_code == 1
        assert "not generated" in result.stdout.lower() or "needs_review" in result.stdout.lower()

    @patch("launcher.phase1.inspection.inspect_repo")
    @patch("launcher.intake.org_scanner.scan_org")
    def test_force_does_not_bypass_ineligible(self, mock_scan_org, mock_inspect_repo, tmp_path):
        """TC-5190: --force does NOT bypass ineligible classification."""
        mock_scan_org.return_value = [_make_repo()]
        # archived=True → ineligible
        inspection = {
            "repo": {**_make_repo(), "archived": True},
            "repo_url": "https://github.com/myorg/MyRepo",
            "acquisition": {
                "repo_signals": {
                    "readme_present": True,
                    "is_empty_clone": False,
                    "detected_manifest_files": ["pyproject.toml"],
                }
            },
            "shared_facts": {"package_name": "myrepo", "license_type": "MIT", "primary_language": "python"},
            "platform": "python",
        }
        mock_inspect_repo.return_value = inspection

        result = runner.invoke(app, [
            "intake", "generate",
            "--repo", "https://github.com/myorg/MyRepo",
            "--output", str(tmp_path),
            "--force",
        ])
        assert result.exit_code == 1
