"""Tests for TC-2377: Quality Feedback Loop W9→W2/W4."""
import json
import pytest
from pathlib import Path


class TestSuggestActions:
    def _import_suggest(self):
        from launch.workers.w9_validator.worker import _suggest_actions_for_page
        return _suggest_actions_for_page

    def test_no_issues_no_actions(self):
        fn = self._import_suggest()
        assert fn([]) == []

    def test_density_errors_suggest_increase_claims(self):
        fn = self._import_suggest()
        issues = [
            {"error_code": "G7-001", "severity": "error", "message": "low density"},
            {"error_code": "G7-002", "severity": "error", "message": "low density 2"},
        ]
        actions = fn(issues)
        assert "increase_claim_count" in actions

    def test_single_density_error_no_action(self):
        fn = self._import_suggest()
        issues = [{"error_code": "G7-001", "severity": "error", "message": "low density"}]
        actions = fn(issues)
        assert "increase_claim_count" not in actions

    def test_api_errors_suggest_lower_threshold(self):
        fn = self._import_suggest()
        issues = [
            {"error_code": "G15-001", "severity": "error", "message": "hallucination 1"},
            {"error_code": "G15-002", "severity": "error", "message": "hallucination 2"},
        ]
        actions = fn(issues)
        assert "lower_snippet_threshold" in actions

    def test_warn_severity_not_counted(self):
        fn = self._import_suggest()
        issues = [
            {"error_code": "G7-001", "severity": "warn", "message": "low density"},
            {"error_code": "G7-002", "severity": "warn", "message": "low density 2"},
        ]
        actions = fn(issues)
        assert "increase_claim_count" not in actions


class TestEmitQualityFeedback:
    def test_writes_feedback_json(self, tmp_path):
        from launch.workers.w9_validator.worker import emit_quality_feedback
        run_dir = tmp_path / "run"
        (run_dir / "work").mkdir(parents=True)

        issues = [
            {"error_code": "G7-001", "severity": "error", "message": "low density",
             "location": {"path": "docs/index.md"}},
        ]
        emit_quality_feedback(run_dir=run_dir, all_issues=issues, page_paths=["docs/index.md"])

        feedback_path = run_dir / "work" / "quality_feedback.json"
        assert feedback_path.exists()
        data = json.loads(feedback_path.read_text())
        assert "run_id" in data
        assert "pages" in data
        assert len(data["pages"]) == 1

    def test_empty_issues_writes_valid_feedback(self, tmp_path):
        from launch.workers.w9_validator.worker import emit_quality_feedback
        run_dir = tmp_path / "run"
        (run_dir / "work").mkdir(parents=True)

        emit_quality_feedback(run_dir=run_dir, all_issues=[], page_paths=[])
        feedback_path = run_dir / "work" / "quality_feedback.json"
        assert feedback_path.exists()
        data = json.loads(feedback_path.read_text())
        assert data["pages"] == []

    def test_no_work_dir_still_works(self, tmp_path):
        from launch.workers.w9_validator.worker import emit_quality_feedback
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        # work/ does NOT exist — should create it
        emit_quality_feedback(run_dir=run_dir, all_issues=[], page_paths=[])
        assert (run_dir / "work" / "quality_feedback.json").exists()


class TestAdjustTopK:
    def test_no_feedback_returns_default(self):
        from launch.workers.w4_ia_planner.worker import adjust_top_k_from_feedback
        assert adjust_top_k_from_feedback("index", 10, {}) == 10

    def test_matching_page_with_action_increases_top_k(self):
        from launch.workers.w4_ia_planner.worker import adjust_top_k_from_feedback
        feedback = {"pages": [
            {"output_path": "docs/index.md", "suggested_actions": ["increase_claim_count"]}
        ]}
        result = adjust_top_k_from_feedback("index", 10, feedback)
        assert result == 13

    def test_max_top_k_capped_at_20(self):
        from launch.workers.w4_ia_planner.worker import adjust_top_k_from_feedback
        feedback = {"pages": [
            {"output_path": "docs/index.md", "suggested_actions": ["increase_claim_count"]}
        ]}
        result = adjust_top_k_from_feedback("index", 19, feedback)
        assert result == 20  # Capped at 20

    def test_no_matching_page_returns_default(self):
        from launch.workers.w4_ia_planner.worker import adjust_top_k_from_feedback
        feedback = {"pages": [
            {"output_path": "docs/other.md", "suggested_actions": ["increase_claim_count"]}
        ]}
        result = adjust_top_k_from_feedback("index", 10, feedback)
        assert result == 10

    def test_action_not_present_returns_default(self):
        from launch.workers.w4_ia_planner.worker import adjust_top_k_from_feedback
        feedback = {"pages": [
            {"output_path": "docs/index.md", "suggested_actions": ["lower_snippet_threshold"]}
        ]}
        result = adjust_top_k_from_feedback("index", 10, feedback)
        assert result == 10


class TestAdjustSnippetThreshold:
    def test_no_feedback_returns_default(self):
        from launch.workers.w2_facts_builder.worker import adjust_snippet_threshold_from_feedback
        assert adjust_snippet_threshold_from_feedback(0.5, {}) == 0.5

    def test_lower_snippet_action_reduces_threshold(self):
        from launch.workers.w2_facts_builder.worker import adjust_snippet_threshold_from_feedback
        feedback = {"pages": [
            {"output_path": "docs/index.md", "suggested_actions": ["lower_snippet_threshold"]}
        ]}
        result = adjust_snippet_threshold_from_feedback(0.5, feedback)
        assert abs(result - 0.45) < 0.001

    def test_threshold_capped_at_min_0_2(self):
        from launch.workers.w2_facts_builder.worker import adjust_snippet_threshold_from_feedback
        feedback = {"pages": [
            {"output_path": "docs/index.md", "suggested_actions": ["lower_snippet_threshold"]}
        ]}
        result = adjust_snippet_threshold_from_feedback(0.2, feedback)
        assert result == 0.2  # Capped at 0.2

    def test_no_matching_action_returns_default(self):
        from launch.workers.w2_facts_builder.worker import adjust_snippet_threshold_from_feedback
        feedback = {"pages": [
            {"output_path": "docs/index.md", "suggested_actions": ["increase_claim_count"]}
        ]}
        result = adjust_snippet_threshold_from_feedback(0.5, feedback)
        assert result == 0.5
