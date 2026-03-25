"""Tests for the intake scheduler.

Covers priority sorting, batch processing, dry-run mode,
dedup, state persistence, and classification integration.

TC: TC-2543, TC-2545
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from launcher.intake.config_loader import OrgConfig, PlatformRule
from launcher.intake.repo_classifier import ClassifierConfig
from launcher.intake.scheduler import _resolve_platform, _sort_repos, schedule


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _make_repo(
    full_name: str = "org/Repo",
    stars: int = 10,
    language: str = "Python",
    license_spdx: str = "MIT",
    pushed_at: str = "2026-02-01T00:00:00Z",
    html_url: str | None = None,
    description: str = "A test repo",
    size: int = 500,
) -> dict:
    if html_url is None:
        html_url = f"https://github.com/{full_name}"
    return {
        "id": hash(full_name) % 10**8,
        "name": full_name.split("/")[1] if "/" in full_name else full_name,
        "full_name": full_name,
        "html_url": html_url,
        "description": description,
        "stargazers_count": stars,
        "language": language,
        "license": {"spdx_id": license_spdx, "name": license_spdx},
        "pushed_at": pushed_at,
        "default_branch": "main",
        "size": size,
        "owner": {"login": full_name.split("/")[0], "type": "Organization"},
        "topics": [],
    }


# ---------------------------------------------------------------------------
# Tests: _sort_repos
# ---------------------------------------------------------------------------


class TestSortRepos:
    def test_sort_by_stars_desc(self):
        repos = [
            _make_repo(full_name="org/Low", stars=1),
            _make_repo(full_name="org/High", stars=100),
            _make_repo(full_name="org/Mid", stars=50),
        ]
        sorted_repos = _sort_repos(repos, sort_by="stars", sort_order="desc")
        assert sorted_repos[0]["full_name"] == "org/High"
        assert sorted_repos[1]["full_name"] == "org/Mid"
        assert sorted_repos[2]["full_name"] == "org/Low"

    def test_sort_by_stars_asc(self):
        repos = [
            _make_repo(full_name="org/Low", stars=1),
            _make_repo(full_name="org/High", stars=100),
        ]
        sorted_repos = _sort_repos(repos, sort_by="stars", sort_order="asc")
        assert sorted_repos[0]["full_name"] == "org/Low"

    def test_sort_by_name(self):
        repos = [
            _make_repo(full_name="org/Zebra"),
            _make_repo(full_name="org/Alpha"),
        ]
        sorted_repos = _sort_repos(repos, sort_by="name", sort_order="asc")
        assert sorted_repos[0]["full_name"] == "org/Alpha"

    def test_sort_by_pushed_at(self):
        repos = [
            _make_repo(full_name="org/Old", pushed_at="2024-01-01T00:00:00Z"),
            _make_repo(full_name="org/New", pushed_at="2026-02-01T00:00:00Z"),
        ]
        sorted_repos = _sort_repos(repos, sort_by="pushed_at", sort_order="desc")
        assert sorted_repos[0]["full_name"] == "org/New"


# ---------------------------------------------------------------------------
# Tests: schedule
# ---------------------------------------------------------------------------


class TestSchedule:
    @pytest.fixture(autouse=True)
    def _mock_inspection(self, monkeypatch, tmp_path):
        """Mock inspect_repo to avoid network calls (git clone).

        SR-01: scheduler unit tests must not hit the network.
        """
        def _fake_inspect_repo(repo, *, work_dir, platform=None, **kw):
            return {
                "repo": repo,
                "platform": platform or "python",
                "family": "cells",
                "display_name": "Test",
                "canonical_import": "aspose_cells_foss",
                "runtime_import": "",
                "shared_facts": {
                    "primary_language": platform or "python",
                    "package_name": "aspose-cells-foss",
                },
                "acquisition": {
                    "repo_sha": "abc123",
                    "repo_signals": {
                        "readme_present": True,
                        "detected_manifest_files": ["pyproject.toml"],
                    },
                },
                "scout": {},
            }

        def _fake_write_artifact(path, **kw):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("{}", encoding="utf-8")

        monkeypatch.setattr(
            "launcher.phase1.onboarding.inspect_repo", _fake_inspect_repo,
        )
        monkeypatch.setattr(
            "launcher.phase1.onboarding.write_inspection_artifact", _fake_write_artifact,
        )

    def test_basic_schedule(self, tmp_path):
        repos = [_make_repo(full_name="org/A", stars=50)]
        output_dir = tmp_path / "configs"

        report = schedule(repos, output_dir=output_dir, artifact_dir=tmp_path / "artifacts", batch_size=5)

        assert report["summary"]["total_scanned"] == 1
        assert report["summary"]["eligible"] == 1
        assert report["summary"]["processed"] == 1
        assert len(report["processed"]) == 1
        assert report["processed"][0]["action"] == "generated"

    def test_dry_run(self, tmp_path):
        repos = [_make_repo(full_name="org/A")]
        output_dir = tmp_path / "configs"

        report = schedule(repos, output_dir=output_dir, artifact_dir=tmp_path / "artifacts", dry_run=True)

        assert report["dry_run"] is True
        assert report["processed"][0]["action"] == "would_generate"
        # No files written in dry-run
        assert not output_dir.exists() or not list(output_dir.glob("*.yaml"))

    def test_batch_size_limits(self, tmp_path):
        repos = [
            _make_repo(full_name=f"org/Repo{i}", stars=i)
            for i in range(10)
        ]
        output_dir = tmp_path / "configs"

        report = schedule(repos, output_dir=output_dir, artifact_dir=tmp_path / "artifacts", batch_size=3)

        assert report["summary"]["processed"] == 3

    def test_ineligible_repos_excluded(self, tmp_path):
        repos = [
            _make_repo(full_name="org/NoLicense", license_spdx=None),
        ]
        repos[0]["license"] = None
        output_dir = tmp_path / "configs"

        report = schedule(repos, output_dir=output_dir, artifact_dir=tmp_path / "artifacts")

        assert report["summary"]["eligible"] == 0
        assert report["summary"]["ineligible"] == 1
        assert report["summary"]["processed"] == 0

    def test_dedup_skips_existing(self, tmp_path):
        repos = [_make_repo(full_name="org/A")]
        output_dir = tmp_path / "configs"

        # First schedule — creates config
        schedule(repos, output_dir=output_dir, artifact_dir=tmp_path / "artifacts")

        # Second schedule — should skip
        report = schedule(repos, output_dir=output_dir, artifact_dir=tmp_path / "artifacts")
        assert report["summary"]["skipped_dedup"] == 1
        assert report["summary"]["processed"] == 0

    def test_state_persistence(self, tmp_path):
        repos = [_make_repo(full_name="org/A")]
        output_dir = tmp_path / "configs"
        state_dir = tmp_path / "state"

        report = schedule(
            repos, output_dir=output_dir, artifact_dir=tmp_path / "artifacts", state_dir=state_dir
        )

        # Check report file
        report_path = state_dir / "intake_report.json"
        assert report_path.exists()
        with open(report_path) as f:
            saved_report = json.load(f)
        assert saved_report["summary"]["processed"] == 1

        # Check schedule state
        state_path = state_dir / "schedule_state.json"
        assert state_path.exists()
        with open(state_path) as f:
            state = json.load(f)
        assert "org/A" in state["processed_repos"]

    def test_sort_by_stars(self, tmp_path):
        repos = [
            _make_repo(full_name="org/Low", stars=1),
            _make_repo(full_name="org/High", stars=100),
        ]
        output_dir = tmp_path / "configs"

        report = schedule(
            repos, output_dir=output_dir, artifact_dir=tmp_path / "artifacts", sort_by="stars", sort_order="desc", batch_size=1
        )

        # Should process the highest-star repo first
        assert report["processed"][0]["stars"] == 100

    def test_mixed_classifications(self, tmp_path):
        """TC-4071: Default config is language-neutral. needs_review requires explicit language config."""
        repos = [
            _make_repo(full_name="org/Good", stars=50),
            _make_repo(full_name="org/Bad", stars=0),
            _make_repo(full_name="org/AlsoGood", language="JavaScript"),  # eligible under new default
        ]
        # Make "Bad" ineligible by removing license
        repos[1]["license"] = None
        output_dir = tmp_path / "configs"

        report = schedule(repos, output_dir=output_dir, artifact_dir=tmp_path / "artifacts")

        # TC-4071: require_python default is now False — JavaScript repo is eligible
        assert report["summary"]["eligible"] == 2
        assert report["summary"]["ineligible"] == 1
        assert report["summary"]["needs_review"] == 0
        assert len(report["classifications"]) == 3

    def test_mixed_classifications_with_explicit_python_requirement(self, tmp_path):
        """Explicit require_python=True still works for Python-only use cases."""
        from launcher.intake.repo_classifier import ClassifierConfig
        repos = [
            _make_repo(full_name="org/Good", stars=50, language="Python"),
            _make_repo(full_name="org/Bad", stars=0),
            _make_repo(full_name="org/NeedsReview", language="JavaScript"),
        ]
        repos[1]["license"] = None
        output_dir = tmp_path / "configs"

        report = schedule(
            repos,
            output_dir=output_dir,
            artifact_dir=tmp_path / "artifacts",
            classifier_config=ClassifierConfig(require_python=True),
        )

        assert report["summary"]["eligible"] == 1
        assert report["summary"]["ineligible"] == 1
        assert report["summary"]["needs_review"] == 1

    def test_platform_in_report(self, tmp_path):
        repos = [_make_repo(full_name="org/Aspose.Cells-FOSS-for-Python")]
        output_dir = tmp_path / "configs"

        report = schedule(repos, output_dir=output_dir, artifact_dir=tmp_path / "artifacts", dry_run=True)

        assert report["processed"][0]["platform"] == "python"

    def test_non_python_platform(self, tmp_path):
        repos = [_make_repo(full_name="org/Aspose.Cells-FOSS-for-Java", language="Java")]
        repos[0]["name"] = "Aspose.Cells-FOSS-for-Java"
        output_dir = tmp_path / "configs"

        report = schedule(
            repos, output_dir=output_dir, artifact_dir=tmp_path / "artifacts", dry_run=True, default_platform="java",
            classifier_config=ClassifierConfig(require_python=False),
        )

        assert len(report["processed"]) == 1
        assert report["processed"][0]["platform"] == "java"

    def test_org_configs_platform_rule_override(self, tmp_path):
        """platform_rules in org_configs override auto-detection."""
        repos = [_make_repo(
            full_name="myorg/SomeCustomRepo",
            language="Python",
        )]
        output_dir = tmp_path / "configs"
        org_configs = {
            "myorg": OrgConfig(
                name="myorg",
                platform_rules=[
                    PlatformRule(name_pattern="*custom*", platform="rust"),
                ],
            ),
        }

        report = schedule(
            repos, output_dir=output_dir, artifact_dir=tmp_path / "artifacts", dry_run=True,
            org_configs=org_configs,
        )

        assert report["processed"][0]["platform"] == "rust"

    def test_org_configs_no_rule_match_falls_to_autodetect(self, tmp_path):
        """When no platform_rule matches, auto-detection kicks in."""
        repos = [_make_repo(
            full_name="myorg/Aspose.Cells-FOSS-for-Java",
            language="Java",
        )]
        repos[0]["name"] = "Aspose.Cells-FOSS-for-Java"
        output_dir = tmp_path / "configs"
        org_configs = {
            "myorg": OrgConfig(
                name="myorg",
                platform_rules=[
                    PlatformRule(name_pattern="*something-else*", platform="go"),
                ],
            ),
        }

        report = schedule(
            repos, output_dir=output_dir, artifact_dir=tmp_path / "artifacts", dry_run=True,
            classifier_config=ClassifierConfig(require_python=False),
            org_configs=org_configs,
        )

        # Auto-detection from repo name "for-Java" -> java
        assert report["processed"][0]["platform"] == "java"

    def test_org_configs_default_platform_used_as_fallback(self, tmp_path):
        """Org default_platform is the last resort when auto-detection also fails."""
        repos = [_make_repo(
            full_name="myorg/GenericLib",
            language="",  # no language to detect
        )]
        output_dir = tmp_path / "configs"
        org_configs = {
            "myorg": OrgConfig(
                name="myorg",
                default_platform="kotlin",
            ),
        }

        report = schedule(
            repos, output_dir=output_dir, artifact_dir=tmp_path / "artifacts", dry_run=True,
            org_configs=org_configs,
            classifier_config=ClassifierConfig(require_python=False),
        )

        assert report["processed"][0]["platform"] == "kotlin"


# ---------------------------------------------------------------------------
# Tests: _resolve_platform
# ---------------------------------------------------------------------------


class TestResolvePlatform:
    def test_no_org_configs_uses_autodetect(self):
        repo = _make_repo(full_name="org/Aspose.Cells-FOSS-for-Python")
        assert _resolve_platform(repo) == "python"

    def test_rule_match_overrides_autodetect(self):
        repo = _make_repo(full_name="myorg/CustomRepo", language="Python")
        org_configs = {
            "myorg": OrgConfig(
                name="myorg",
                platform_rules=[PlatformRule("*custom*", "go")],
            ),
        }
        assert _resolve_platform(repo, org_configs=org_configs) == "go"

    def test_no_rule_match_falls_to_autodetect(self):
        repo = _make_repo(full_name="myorg/Aspose.3D-FOSS-for-Java")
        repo["name"] = "Aspose.3D-FOSS-for-Java"
        org_configs = {
            "myorg": OrgConfig(
                name="myorg",
                platform_rules=[PlatformRule("*no-match*", "rust")],
            ),
        }
        assert _resolve_platform(repo, org_configs=org_configs) == "java"

    def test_org_default_platform_used_when_no_autodetect(self):
        repo = _make_repo(full_name="myorg/PlainLib", language="")
        org_configs = {
            "myorg": OrgConfig(name="myorg", default_platform="swift"),
        }
        assert _resolve_platform(repo, org_configs=org_configs) == "swift"

    def test_caller_default_platform_when_no_org_config(self):
        repo = _make_repo(full_name="unknownorg/PlainLib", language="")
        assert _resolve_platform(repo, default_platform="dotnet") == "dotnet"
