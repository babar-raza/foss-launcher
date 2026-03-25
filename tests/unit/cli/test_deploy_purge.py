"""Unit tests for CLI 'deploy purge' command (TC-EVAL-503 / SR-01).

Tests the typer CLI command that removes low-grade pages from deploy/
and optionally from snapshots/.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from launcher.cli.deploy import deploy_app

runner = CliRunner()


def _create_manifest(deploy_dir: Path, pages: dict[str, dict]) -> Path:
    """Create a deploy manifest with the given page entries.

    pages: {content_path: {"grade": "A"|"B"|..., "deploy_file": "relative/path.md"}}
    """
    manifest = {
        "schema_version": "1.0",
        "pages": {},
        "last_promotion": "2026-03-24T00:00:00Z",
        "promotion_count": 1,
    }
    for cp, info in pages.items():
        manifest["pages"][cp] = {
            "content_path": cp,
            "deploy_file": info["deploy_file"],
            "source_run_id": "test_run",
            "grade": info["grade"],
            "sha256": "a" * 64,  # valid 64-char hex
            "promoted_at": "2026-03-24T00:00:00Z",
        }
    manifest_path = deploy_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return manifest_path


class TestDeployPurge:
    """Tests for the deploy purge CLI command."""

    def test_purge_removes_low_grade_pages(self, tmp_path: Path) -> None:
        """Pages below min-grade are deleted from disk and manifest."""
        deploy_dir = tmp_path / "deploy"
        deploy_dir.mkdir()

        # Create .md files
        (deploy_dir / "docs" / "good").mkdir(parents=True)
        (deploy_dir / "docs" / "bad").mkdir(parents=True)
        good_file = deploy_dir / "docs" / "good" / "page.md"
        bad_file = deploy_dir / "docs" / "bad" / "page.md"
        good_file.write_text("# Good page", encoding="utf-8")
        bad_file.write_text("# Bad page", encoding="utf-8")

        _create_manifest(deploy_dir, {
            "docs/good/page": {"grade": "A", "deploy_file": "docs/good/page.md"},
            "docs/bad/page": {"grade": "F", "deploy_file": "docs/bad/page.md"},
        })

        result = runner.invoke(deploy_app, [
            "purge", "--min-grade", "C", "--deploy-dir", str(deploy_dir),
        ])
        assert result.exit_code == 0
        assert "Purged 1 file(s)" in result.output

        # Good file still exists
        assert good_file.exists()
        # Bad file deleted
        assert not bad_file.exists()

        # Manifest updated
        updated = json.loads((deploy_dir / "manifest.json").read_text(encoding="utf-8"))
        assert "docs/good/page" in updated["pages"]
        assert "docs/bad/page" not in updated["pages"]

    def test_purge_dry_run_does_not_delete(self, tmp_path: Path) -> None:
        """Dry run mode previews but does not delete files or update manifest."""
        deploy_dir = tmp_path / "deploy"
        deploy_dir.mkdir()

        bad_file = deploy_dir / "page.md"
        bad_file.write_text("# Bad", encoding="utf-8")

        _create_manifest(deploy_dir, {
            "page": {"grade": "D", "deploy_file": "page.md"},
        })

        result = runner.invoke(deploy_app, [
            "purge", "--min-grade", "C", "--deploy-dir", str(deploy_dir), "--dry-run",
        ])
        assert result.exit_code == 0
        assert "[DRY RUN]" in result.output
        assert "Would purge 1 page(s)" in result.output

        # File still exists
        assert bad_file.exists()

        # Manifest unchanged
        manifest = json.loads((deploy_dir / "manifest.json").read_text(encoding="utf-8"))
        assert "page" in manifest["pages"]

    def test_purge_no_pages_below_threshold(self, tmp_path: Path) -> None:
        """When all pages meet the threshold, exits cleanly."""
        deploy_dir = tmp_path / "deploy"
        deploy_dir.mkdir()

        _create_manifest(deploy_dir, {
            "good/page": {"grade": "A", "deploy_file": "good/page.md"},
        })

        result = runner.invoke(deploy_app, [
            "purge", "--min-grade", "C", "--deploy-dir", str(deploy_dir),
        ])
        assert result.exit_code == 0
        assert "Nothing to purge" in result.output

    def test_purge_no_manifest(self, tmp_path: Path) -> None:
        """When no manifest exists, exits cleanly."""
        deploy_dir = tmp_path / "deploy"
        deploy_dir.mkdir()

        result = runner.invoke(deploy_app, [
            "purge", "--min-grade", "C", "--deploy-dir", str(deploy_dir),
        ])
        assert result.exit_code == 0
        assert "No deploy manifest" in result.output

    def test_purge_with_snapshots(self, tmp_path: Path) -> None:
        """Purge also removes from snapshots/ when --snapshots-dir is provided."""
        deploy_dir = tmp_path / "deploy"
        deploy_dir.mkdir()
        snapshots_dir = tmp_path / "snapshots"
        snapshots_dir.mkdir()

        bad_deploy = deploy_dir / "bad" / "page.md"
        bad_deploy.parent.mkdir(parents=True)
        bad_deploy.write_text("# Bad", encoding="utf-8")

        bad_snapshot = snapshots_dir / "bad" / "page.ir.json"
        bad_snapshot.parent.mkdir(parents=True)
        bad_snapshot.write_text("{}", encoding="utf-8")

        _create_manifest(deploy_dir, {
            "bad/page": {"grade": "F", "deploy_file": "bad/page.md"},
        })

        result = runner.invoke(deploy_app, [
            "purge", "--min-grade", "C",
            "--deploy-dir", str(deploy_dir),
            "--snapshots-dir", str(snapshots_dir),
        ])
        assert result.exit_code == 0
        assert not bad_deploy.exists()
        assert not bad_snapshot.exists()

    def test_purge_missing_file_warns(self, tmp_path: Path) -> None:
        """When manifest references a file that doesn't exist, warns but continues."""
        deploy_dir = tmp_path / "deploy"
        deploy_dir.mkdir()

        # Manifest references a file that doesn't exist on disk
        _create_manifest(deploy_dir, {
            "ghost/page": {"grade": "F", "deploy_file": "ghost/page.md"},
        })

        result = runner.invoke(deploy_app, [
            "purge", "--min-grade", "C", "--deploy-dir", str(deploy_dir),
        ])
        assert result.exit_code == 0
        assert "Warning: file not found" in result.output

        # Manifest should still be updated (entry removed)
        updated = json.loads((deploy_dir / "manifest.json").read_text(encoding="utf-8"))
        assert "ghost/page" not in updated["pages"]
