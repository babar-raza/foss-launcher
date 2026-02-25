"""TC-2529/TC-2530/TC-2532: Tests for the quality feedback loop wiring.

Tests that:
- W2 adjust_snippet_threshold_from_feedback changes threshold when feedback present
- W4 adjust_top_k_from_feedback changes claim count when feedback present
- _emit_feedback_delta writes correct schema
- No-op when use_feedback=False or feedback file missing
- Boundary conditions (threshold at min/max, already-at-max claim counts)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import pytest

from launch.workers.w2_facts_builder.worker import (
    adjust_snippet_threshold_from_feedback,
    _emit_feedback_delta,
)
from launch.workers.w4_ia_planner.worker import (
    adjust_top_k_from_feedback,
    read_quality_feedback,
    _emit_w4_feedback_delta,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_feedback(
    pages: list[Dict[str, Any]] | None = None,
    run_id: str = "r_test",
) -> Dict[str, Any]:
    """Build a synthetic quality_feedback.json payload."""
    return {
        "run_id": run_id,
        "generated_at": "2026-02-25T00:00:00Z",
        "pages": pages or [],
    }


def _page_with_actions(output_path: str, actions: list[str]) -> Dict[str, Any]:
    return {
        "output_path": output_path,
        "error_count": len(actions),
        "warn_count": 0,
        "gate_issues": [],
        "suggested_actions": actions,
    }


# ===========================================================================
# TC-2529 / W2: adjust_snippet_threshold_from_feedback
# ===========================================================================

class TestW2SnippetThresholdAdjustment:
    """Verify adjust_snippet_threshold_from_feedback produces correct values."""

    def test_lowers_threshold_when_feedback_has_lower_action(self):
        """Threshold decreases by 0.05 when lower_snippet_threshold action present."""
        feedback = _make_feedback(pages=[
            _page_with_actions("/content/docs/page1/index.md", ["lower_snippet_threshold"]),
        ])
        result = adjust_snippet_threshold_from_feedback(0.5, feedback)
        assert result == pytest.approx(0.45)

    def test_no_change_when_no_lower_action(self):
        """Threshold stays at default when feedback has no lower_snippet_threshold action."""
        feedback = _make_feedback(pages=[
            _page_with_actions("/content/docs/page1/index.md", ["increase_claim_count"]),
        ])
        result = adjust_snippet_threshold_from_feedback(0.5, feedback)
        assert result == pytest.approx(0.5)

    def test_no_change_when_empty_feedback(self):
        """Threshold stays at default with empty feedback."""
        feedback = _make_feedback(pages=[])
        result = adjust_snippet_threshold_from_feedback(0.5, feedback)
        assert result == pytest.approx(0.5)

    def test_clamps_at_minimum_02(self):
        """Threshold never goes below 0.2 even with feedback."""
        feedback = _make_feedback(pages=[
            _page_with_actions("/p1", ["lower_snippet_threshold"]),
        ])
        result = adjust_snippet_threshold_from_feedback(0.2, feedback)
        assert result == pytest.approx(0.2)

    def test_idempotent_same_input(self):
        """Calling twice with same feedback produces identical output."""
        feedback = _make_feedback(pages=[
            _page_with_actions("/p1", ["lower_snippet_threshold"]),
        ])
        r1 = adjust_snippet_threshold_from_feedback(0.5, feedback)
        r2 = adjust_snippet_threshold_from_feedback(0.5, feedback)
        assert r1 == r2

    def test_multiple_pages_still_single_step(self):
        """Multiple pages with lower action still reduce by 0.05 (single step)."""
        feedback = _make_feedback(pages=[
            _page_with_actions("/p1", ["lower_snippet_threshold"]),
            _page_with_actions("/p2", ["lower_snippet_threshold"]),
            _page_with_actions("/p3", ["lower_snippet_threshold"]),
        ])
        result = adjust_snippet_threshold_from_feedback(0.5, feedback)
        # Single step reduction: 0.5 - 0.05 = 0.45 (not 0.35)
        assert result == pytest.approx(0.45)


# ===========================================================================
# TC-2529 / W4: adjust_top_k_from_feedback
# ===========================================================================

class TestW4ClaimCountAdjustment:
    """Verify adjust_top_k_from_feedback changes claim counts."""

    def test_increases_top_k_when_increase_action(self):
        """top_k increases by 3 when increase_claim_count action matches slug."""
        feedback = _make_feedback(pages=[
            _page_with_actions("/content/docs/getting-started/index.md", ["increase_claim_count"]),
        ])
        result = adjust_top_k_from_feedback("getting-started", 10, feedback)
        assert result == 13

    def test_no_change_when_slug_not_in_feedback(self):
        """top_k unchanged when page slug not in any feedback path."""
        feedback = _make_feedback(pages=[
            _page_with_actions("/content/docs/other-page/index.md", ["increase_claim_count"]),
        ])
        result = adjust_top_k_from_feedback("getting-started", 10, feedback)
        assert result == 10

    def test_no_change_when_no_increase_action(self):
        """top_k unchanged when feedback has no increase_claim_count action."""
        feedback = _make_feedback(pages=[
            _page_with_actions("/content/docs/getting-started/index.md", ["lower_snippet_threshold"]),
        ])
        result = adjust_top_k_from_feedback("getting-started", 10, feedback)
        assert result == 10

    def test_clamps_at_maximum_20(self):
        """top_k never exceeds 20 even with feedback."""
        feedback = _make_feedback(pages=[
            _page_with_actions("/content/docs/getting-started/index.md", ["increase_claim_count"]),
        ])
        result = adjust_top_k_from_feedback("getting-started", 19, feedback)
        assert result == 20  # 19 + 3 = 22, but clamped to 20

    def test_empty_feedback_no_change(self):
        """top_k unchanged with empty feedback."""
        feedback = _make_feedback(pages=[])
        result = adjust_top_k_from_feedback("any-slug", 10, feedback)
        assert result == 10


# ===========================================================================
# TC-2529 / W4: read_quality_feedback
# ===========================================================================

class TestReadQualityFeedback:
    """Verify read_quality_feedback file I/O."""

    def test_returns_empty_when_no_file(self, tmp_path: Path):
        """Returns empty dict when quality_feedback.json does not exist."""
        result = read_quality_feedback(tmp_path)
        assert result == {}

    def test_reads_valid_feedback(self, tmp_path: Path):
        """Returns parsed dict when quality_feedback.json exists."""
        work_dir = tmp_path / "work"
        work_dir.mkdir()
        feedback = _make_feedback(pages=[
            _page_with_actions("/p1", ["increase_claim_count"]),
        ])
        (work_dir / "quality_feedback.json").write_text(
            json.dumps(feedback), encoding="utf-8",
        )
        result = read_quality_feedback(tmp_path)
        assert result["run_id"] == "r_test"
        assert len(result["pages"]) == 1

    def test_returns_empty_on_malformed_json(self, tmp_path: Path):
        """Returns empty dict when quality_feedback.json contains invalid JSON."""
        work_dir = tmp_path / "work"
        work_dir.mkdir()
        (work_dir / "quality_feedback.json").write_text(
            "NOT VALID JSON {{{", encoding="utf-8",
        )
        result = read_quality_feedback(tmp_path)
        assert result == {}


# ===========================================================================
# TC-2530: _emit_feedback_delta (W2 helper)
# ===========================================================================

class TestEmitFeedbackDeltaW2:
    """Verify _emit_feedback_delta writes correct artifact."""

    def test_creates_new_delta_artifact(self, tmp_path: Path):
        """Creates feedback_delta.json with schema_version and one entry."""
        feedback = _make_feedback(pages=[
            _page_with_actions("/p1", ["lower_snippet_threshold"]),
        ])
        _emit_feedback_delta(
            run_dir=tmp_path,
            worker="W2",
            feedback=feedback,
            parameters_before={"similarity_threshold": 0.5},
            parameters_after={"similarity_threshold": 0.45},
        )
        delta_path = tmp_path / "artifacts" / "feedback_delta.json"
        assert delta_path.exists()
        data = json.loads(delta_path.read_text(encoding="utf-8"))
        assert data["schema_version"] == "1.0"
        assert len(data["entries"]) == 1
        entry = data["entries"][0]
        assert entry["worker"] == "W2"
        assert entry["feedback_source"] == "quality_feedback.json"
        assert entry["feedback_entries_read"] == 1
        assert len(entry["changes"]) == 1
        assert entry["changes"][0]["parameter"] == "similarity_threshold"
        assert entry["changes"][0]["old"] == 0.5
        assert entry["changes"][0]["new"] == 0.45

    def test_empty_changes_when_no_adjustment(self, tmp_path: Path):
        """Changes list is empty when before == after."""
        feedback = _make_feedback(pages=[])
        _emit_feedback_delta(
            run_dir=tmp_path,
            worker="W2",
            feedback=feedback,
            parameters_before={"similarity_threshold": 0.5},
            parameters_after={"similarity_threshold": 0.5},
        )
        delta_path = tmp_path / "artifacts" / "feedback_delta.json"
        data = json.loads(delta_path.read_text(encoding="utf-8"))
        assert data["entries"][0]["changes"] == []

    def test_appends_to_existing_delta(self, tmp_path: Path):
        """W4 entry appends to existing W2 entry."""
        feedback = _make_feedback(pages=[
            _page_with_actions("/p1", ["lower_snippet_threshold"]),
        ])
        # First call (W2)
        _emit_feedback_delta(
            run_dir=tmp_path,
            worker="W2",
            feedback=feedback,
            parameters_before={"similarity_threshold": 0.5},
            parameters_after={"similarity_threshold": 0.45},
        )
        # Second call simulating W4
        _emit_feedback_delta(
            run_dir=tmp_path,
            worker="W4",
            feedback=feedback,
            parameters_before={"claim_quota_max:getting-started": 10},
            parameters_after={"claim_quota_max:getting-started": 13},
        )
        delta_path = tmp_path / "artifacts" / "feedback_delta.json"
        data = json.loads(delta_path.read_text(encoding="utf-8"))
        assert len(data["entries"]) == 2
        assert data["entries"][0]["worker"] == "W2"
        assert data["entries"][1]["worker"] == "W4"


# ===========================================================================
# TC-2530: _emit_w4_feedback_delta
# ===========================================================================

class TestEmitFeedbackDeltaW4:
    """Verify _emit_w4_feedback_delta writes correct artifact."""

    def test_creates_delta_with_claim_changes(self, tmp_path: Path):
        """Creates feedback_delta.json with W4 claim count changes."""
        feedback = _make_feedback(pages=[
            _page_with_actions("/getting-started/", ["increase_claim_count"]),
        ])
        _emit_w4_feedback_delta(
            run_dir=tmp_path,
            feedback=feedback,
            parameters_before={"claim_quota_max:getting-started": 10},
            parameters_after={"claim_quota_max:getting-started": 13},
        )
        delta_path = tmp_path / "artifacts" / "feedback_delta.json"
        assert delta_path.exists()
        data = json.loads(delta_path.read_text(encoding="utf-8"))
        assert data["schema_version"] == "1.0"
        assert len(data["entries"]) == 1
        entry = data["entries"][0]
        assert entry["worker"] == "W4"
        assert entry["changes"][0]["old"] == 10
        assert entry["changes"][0]["new"] == 13


# ===========================================================================
# TC-2530: Schema validation of feedback_delta.json
# ===========================================================================

class TestFeedbackDeltaSchema:
    """Validate feedback_delta.json against its JSON schema."""

    def test_schema_file_exists(self):
        """Schema file exists at expected path."""
        schema_path = (
            Path(__file__).parent.parent.parent.parent
            / "specs" / "schemas" / "feedback_delta.schema.json"
        )
        assert schema_path.exists(), f"Schema not found: {schema_path}"

    def test_artifact_validates_against_schema(self, tmp_path: Path):
        """Generated feedback_delta.json validates against its schema."""
        try:
            import jsonschema
        except ImportError:
            pytest.skip("jsonschema not installed")

        schema_path = (
            Path(__file__).parent.parent.parent.parent
            / "specs" / "schemas" / "feedback_delta.schema.json"
        )
        schema = json.loads(schema_path.read_text(encoding="utf-8"))

        feedback = _make_feedback(pages=[
            _page_with_actions("/p1", ["lower_snippet_threshold"]),
        ])
        _emit_feedback_delta(
            run_dir=tmp_path,
            worker="W2",
            feedback=feedback,
            parameters_before={"similarity_threshold": 0.5},
            parameters_after={"similarity_threshold": 0.45},
        )
        delta_path = tmp_path / "artifacts" / "feedback_delta.json"
        data = json.loads(delta_path.read_text(encoding="utf-8"))

        jsonschema.validate(instance=data, schema=schema)
