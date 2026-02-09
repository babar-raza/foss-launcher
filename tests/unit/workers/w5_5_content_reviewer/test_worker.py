"""Integration test for execute_content_reviewer entry point.

TC-1103: W5.5 ContentReviewer test hardening.
"""
import json
import pytest
from pathlib import Path

from launch.workers.w5_5_content_reviewer.worker import (
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
