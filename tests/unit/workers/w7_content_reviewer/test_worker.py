"""Integration test for execute_content_reviewer entry point.

TC-1103: W7 ContentReviewer test hardening.
"""
import json
import pytest
from pathlib import Path

from launch.workers.w7_content_reviewer.worker import (
    execute_content_reviewer,
    ContentReviewerArtifactMissingError,
    ContentReviewerValidationError,
)


class TestExecuteContentReviewer:
    """Test the full worker entry point."""

    @staticmethod
    def _setup_run_dir(tmp_path):
        """Create minimal run directory with required artifacts."""
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir(parents=True)
        drafts_dir = tmp_path / "drafts"
        drafts_dir.mkdir(parents=True)

        # Write minimal artifacts
        (artifacts_dir / "product_facts.json").write_text(
            json.dumps({
                "product_name": "TestProduct",
                "claims": [],
                "claim_groups": {},
            }),
            encoding="utf-8",
        )
        (artifacts_dir / "snippet_catalog.json").write_text(
            json.dumps({"snippets": []}),
            encoding="utf-8",
        )
        (artifacts_dir / "page_plan.json").write_text(
            json.dumps({
                "pages": [
                    {
                        "slug": "test",
                        "title": "Test",
                        "template": "feature.variant-standard",
                    }
                ]
            }),
            encoding="utf-8",
        )
        (artifacts_dir / "evidence_map.json").write_text(
            json.dumps({"evidence": [], "metadata": {}}),
            encoding="utf-8",
        )

        # Write a simple draft with valid frontmatter
        (drafts_dir / "test.md").write_text(
            "---\ntitle: Test\ndescription: A test page\nurl_path: /test/\nweight: 1\n---\n\n"
            "# Test Page\n\nThis is test content for the TestProduct library.\n",
            encoding="utf-8",
        )

        return tmp_path

    def test_returns_success(self, tmp_path):
        """Should return status=success for valid run dir."""
        run_dir = self._setup_run_dir(tmp_path)
        run_config = {"review_enabled": True, "offline_mode": True}
        result = execute_content_reviewer(run_dir, run_config)
        assert result["status"] == "success"
        assert result["overall_status"] in ("PASS", "NEEDS_CHANGES", "REJECT")
        assert result["pages_reviewed"] >= 1

    def test_writes_review_report(self, tmp_path):
        """Should write review_report.json to artifacts dir."""
        run_dir = self._setup_run_dir(tmp_path)
        run_config = {"review_enabled": True, "offline_mode": True}
        execute_content_reviewer(run_dir, run_config)
        report_path = run_dir / "artifacts" / "review_report.json"
        assert report_path.exists()
        report = json.loads(report_path.read_text(encoding="utf-8"))
        assert "overall_status" in report
        assert "dimension_scores" in report
        assert "issues" in report

    def test_review_report_has_three_dimensions(self, tmp_path):
        """review_report.json dimension_scores must cover all three dimensions."""
        run_dir = self._setup_run_dir(tmp_path)
        run_config = {"review_enabled": True, "offline_mode": True}
        execute_content_reviewer(run_dir, run_config)
        report_path = run_dir / "artifacts" / "review_report.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        expected_dims = sorted(["content_quality", "technical_accuracy", "usability"])
        assert sorted(report["dimension_scores"].keys()) == expected_dims

    def test_missing_run_dir_raises(self, tmp_path):
        """Should raise when run_dir doesn't exist."""
        with pytest.raises(ContentReviewerArtifactMissingError):
            execute_content_reviewer(tmp_path / "nonexistent", {})

    def test_review_enabled_uses_true_default_when_key_missing(self, tmp_path):
        """W7 should run review when review_enabled key missing (schema default true).

        This test verifies that the schema default (true) is respected when the key
        is not explicitly set in run_config.
        """
        run_dir = self._setup_run_dir(tmp_path)
        # Run with config missing review_enabled key
        run_config = {"offline_mode": True}  # No review_enabled key

        # Should NOT raise error (would fail if default was false and key missing)
        result = execute_content_reviewer(run_dir, run_config)

        # Verify review ran (artifacts created)
        assert result["status"] == "success"
        artifacts_dir = run_dir / "artifacts"
        assert (artifacts_dir / "review_report.json").exists()
        assert result["pages_reviewed"] >= 1

    def test_missing_artifact_raises(self, tmp_path):
        """Should raise when a required artifact file is missing."""
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir(parents=True)
        # Only write one artifact -- the rest are missing
        (artifacts_dir / "product_facts.json").write_text(
            json.dumps({"product_name": "X", "claims": []}),
            encoding="utf-8",
        )
        with pytest.raises(ContentReviewerArtifactMissingError):
            execute_content_reviewer(tmp_path, {"review_enabled": True})

    def test_missing_drafts_raises(self, tmp_path):
        """Should raise when drafts dir is missing."""
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir(parents=True)
        (artifacts_dir / "product_facts.json").write_text(
            json.dumps({"product_name": "X", "claims": [], "claim_groups": {}}),
            encoding="utf-8",
        )
        (artifacts_dir / "snippet_catalog.json").write_text(
            json.dumps({"snippets": []}),
            encoding="utf-8",
        )
        (artifacts_dir / "page_plan.json").write_text(
            json.dumps({"pages": []}),
            encoding="utf-8",
        )
        (artifacts_dir / "evidence_map.json").write_text(
            json.dumps({"evidence": [], "metadata": {}}),
            encoding="utf-8",
        )
        run_config = {"review_enabled": True}
        with pytest.raises(ContentReviewerArtifactMissingError):
            execute_content_reviewer(tmp_path, run_config)

    def test_empty_drafts_raises_validation_error(self, tmp_path):
        """Should raise ContentReviewerValidationError when drafts dir has no .md files."""
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir(parents=True)
        drafts_dir = tmp_path / "drafts"
        drafts_dir.mkdir(parents=True)
        (artifacts_dir / "product_facts.json").write_text(
            json.dumps({"product_name": "X", "claims": [], "claim_groups": {}}),
            encoding="utf-8",
        )
        (artifacts_dir / "snippet_catalog.json").write_text(
            json.dumps({"snippets": []}),
            encoding="utf-8",
        )
        (artifacts_dir / "page_plan.json").write_text(
            json.dumps({"pages": []}),
            encoding="utf-8",
        )
        (artifacts_dir / "evidence_map.json").write_text(
            json.dumps({"evidence": [], "metadata": {}}),
            encoding="utf-8",
        )
        run_config = {"review_enabled": True}
        with pytest.raises(ContentReviewerValidationError):
            execute_content_reviewer(tmp_path, run_config)

    def test_emits_telemetry_events(self, tmp_path):
        """Should write REVIEW_STARTED and REVIEW_COMPLETED events."""
        run_dir = self._setup_run_dir(tmp_path)
        run_config = {"review_enabled": True, "offline_mode": True}
        execute_content_reviewer(run_dir, run_config)
        events_path = run_dir / "events.ndjson"
        assert events_path.exists()
        events = [
            json.loads(line)
            for line in events_path.read_text(encoding="utf-8").strip().split("\n")
            if line.strip()
        ]
        event_types = [e.get("type", e.get("event_type")) for e in events]
        assert "REVIEW_STARTED" in event_types
        assert "REVIEW_COMPLETED" in event_types

    def test_recheck_after_autofix_improves_scores(self, tmp_path):
        """Auto-fixed issues should not count against dimension scores.

        The scoring architecture re-runs checks after auto-fixes, so
        successfully fixed issues disappear from the re-check results.
        """
        run_dir = self._setup_run_dir(tmp_path)

        # Write a draft with inline claim markers (auto-fixable errors)
        drafts_dir = run_dir / "drafts"
        content = (
            "---\ntitle: Test Page\ndescription: A test\nurl_path: /test/\nweight: 1\n---\n\n"
            "# Test Page\n\n"
            "This is content about TestProduct.\n\n"
            "Feature one works well. [claim: abc123def456]\n\n"
            "Feature two is fast. [claim: 789ghi012jkl]\n"
        )
        (drafts_dir / "test.md").write_text(content, encoding="utf-8")

        run_config = {"review_enabled": True, "offline_mode": True}
        result = execute_content_reviewer(run_dir, run_config)

        # The inline [claim:] markers should have been auto-fixed to <!-- claim_id: -->
        # and the re-check should show 0 claim_marker_format errors
        report_path = run_dir / "artifacts" / "review_report.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        claim_format_errors = [
            i for i in report.get("issues", [])
            if i.get("check") == "content_quality.claim_marker_format"
        ]
        assert claim_format_errors == [], (
            f"claim_marker_format errors should be 0 after auto-fix re-check: {claim_format_errors}"
        )
