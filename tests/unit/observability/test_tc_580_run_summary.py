"""
Test suite for TC-580: Run Summary Generation.

Tests run summary generation, timeline extraction, and evidence validation.
"""

import json
from pathlib import Path

import pytest

from src.launch.observability.run_summary import (
    RunSummary,
    TimelineEvent,
    generate_run_summary,
    validate_evidence_completeness,
)


@pytest.fixture
def temp_run_dir(tmp_path: Path) -> Path:
    """Create temporary run directory with sample data."""
    run_dir = tmp_path / "runs" / "test-run-123"
    run_dir.mkdir(parents=True)

    # Create snapshot
    snapshot = {
        "run_id": "test-run-123",
        "run_state": "DONE",
        "created_at": "2024-01-01T10:00:00Z",
        "updated_at": "2024-01-01T10:30:00Z",
        "work_items": [
            {"worker": "W1", "status": "completed"},
            {"worker": "W2", "status": "completed"},
            {"worker": "W3", "status": "in_progress"},
        ],
    }
    (run_dir / "snapshot.json").write_text(json.dumps(snapshot, indent=2), encoding="utf-8")

    return run_dir


def test_generate_run_summary_basic(temp_run_dir: Path):
    """Test basic run summary generation."""
    summary = generate_run_summary(temp_run_dir)

    assert summary.run_id == "test-run-123"
    assert summary.status == "DONE"
    assert summary.started_at == "2024-01-01T10:00:00Z"
    assert summary.completed_at == "2024-01-01T10:30:00Z"
    assert summary.workers_total == 3
    assert summary.workers_completed == 2


def test_generate_run_summary_no_snapshot(tmp_path: Path):
    """Test run summary generation with missing snapshot."""
    run_dir = tmp_path / "runs" / "test-run"
    run_dir.mkdir(parents=True)

    with pytest.raises(FileNotFoundError):
        generate_run_summary(run_dir)


def test_generate_run_summary_duration_calculation(temp_run_dir: Path):
    """Test duration calculation from timestamps."""
    summary = generate_run_summary(temp_run_dir)

    # 10:00:00 to 10:30:00 = 1800 seconds (30 minutes)
    assert summary.duration_seconds == 1800.0


def test_generate_run_summary_with_validation(temp_run_dir: Path):
    """Test summary generation with validation report."""
    # Create validation report
    artifacts_dir = temp_run_dir / "artifacts"
    artifacts_dir.mkdir()

    validation_report = {
        "ok": True,
        "gates": [],
    }
    (artifacts_dir / "validation_report.json").write_text(
        json.dumps(validation_report, indent=2),
        encoding="utf-8",
    )

    summary = generate_run_summary(temp_run_dir)

    assert summary.validation_passed is True


def test_generate_run_summary_validation_failed(temp_run_dir: Path):
    """Test summary with failed validation."""
    artifacts_dir = temp_run_dir / "artifacts"
    artifacts_dir.mkdir()

    validation_report = {
        "ok": False,
        "gates": [],
    }
    (artifacts_dir / "validation_report.json").write_text(
        json.dumps(validation_report, indent=2),
        encoding="utf-8",
    )

    summary = generate_run_summary(temp_run_dir)

    assert summary.validation_passed is False


def test_generate_run_summary_with_pr(temp_run_dir: Path):
    """Test summary generation with PR URL."""
    artifacts_dir = temp_run_dir / "artifacts"
    artifacts_dir.mkdir()

    pr_data = {
        "pr_url": "https://github.com/org/repo/pull/123",
        "branch": "launch/test-run-123",
    }
    (artifacts_dir / "pr.json").write_text(json.dumps(pr_data, indent=2), encoding="utf-8")

    summary = generate_run_summary(temp_run_dir)

    assert summary.pr_url == "https://github.com/org/repo/pull/123"


def test_generate_run_summary_no_pr(temp_run_dir: Path):
    """Test summary without PR URL."""
    summary = generate_run_summary(temp_run_dir)

    assert summary.pr_url is None


def test_generate_run_summary_with_events(temp_run_dir: Path):
    """Test summary generation with event timeline."""
    events = [
        '{"type": "RUN_CREATED", "ts": "2024-01-01T10:00:00Z", "payload": {}}',
        '{"type": "WORK_ITEM_STARTED", "ts": "2024-01-01T10:05:00Z", "payload": {"worker": "W1"}}',
        '{"type": "WORK_ITEM_FINISHED", "ts": "2024-01-01T10:10:00Z", "payload": {"worker": "W1"}}',
        '{"type": "RUN_COMPLETED", "ts": "2024-01-01T10:30:00Z", "payload": {}}',
    ]
    (temp_run_dir / "events.ndjson").write_text("\n".join(events), encoding="utf-8")

    summary = generate_run_summary(temp_run_dir)

    assert len(summary.timeline) == 4
    assert summary.timeline[0].event_type == "RUN_CREATED"
    assert summary.timeline[1].event_type == "WORK_ITEM_STARTED"
    assert summary.timeline[1].worker == "W1"


def test_generate_run_summary_empty_events(temp_run_dir: Path):
    """Test summary with empty events file."""
    (temp_run_dir / "events.ndjson").write_text("", encoding="utf-8")

    summary = generate_run_summary(temp_run_dir)

    assert len(summary.timeline) == 0


def test_run_summary_to_dict(temp_run_dir: Path):
    """Test RunSummary serialization to dict."""
    summary = generate_run_summary(temp_run_dir)
    result = summary.to_dict()

    assert isinstance(result, dict)
    assert result["run_id"] == "test-run-123"
    assert result["status"] == "DONE"
    assert "timeline" in result
    assert isinstance(result["timeline"], list)


def test_run_summary_to_markdown(temp_run_dir: Path):
    """Test RunSummary markdown generation."""
    summary = generate_run_summary(temp_run_dir)
    markdown = summary.to_markdown()

    assert "# Run Summary: test-run-123" in markdown
    assert "Status**: DONE" in markdown
    assert "Duration**: 1800.00s" in markdown
    assert "Workers**: 2/3 completed" in markdown


def test_run_summary_markdown_with_pr(temp_run_dir: Path):
    """Test markdown includes PR URL when present."""
    artifacts_dir = temp_run_dir / "artifacts"
    artifacts_dir.mkdir()

    pr_data = {"pr_url": "https://github.com/org/repo/pull/123"}
    (artifacts_dir / "pr.json").write_text(json.dumps(pr_data), encoding="utf-8")

    summary = generate_run_summary(temp_run_dir)
    markdown = summary.to_markdown()

    assert "https://github.com/org/repo/pull/123" in markdown


def test_run_summary_markdown_timeline(temp_run_dir: Path):
    """Test markdown includes timeline events."""
    events = [
        '{"type": "RUN_CREATED", "ts": "2024-01-01T10:00:00Z", "payload": {}}',
        '{"type": "RUN_COMPLETED", "ts": "2024-01-01T10:30:00Z", "payload": {}}',
    ]
    (temp_run_dir / "events.ndjson").write_text("\n".join(events), encoding="utf-8")

    summary = generate_run_summary(temp_run_dir)
    markdown = summary.to_markdown()

    assert "## Timeline" in markdown
    assert "RUN_CREATED" in markdown
    assert "RUN_COMPLETED" in markdown


def test_timeline_event_to_dict():
    """Test TimelineEvent serialization to dict."""
    event = TimelineEvent(
        timestamp="2024-01-01T10:00:00Z",
        event_type="WORK_ITEM_STARTED",
        worker="W1",
        message="Started worker: W1",
    )

    result = event.to_dict()

    assert isinstance(result, dict)
    assert result["timestamp"] == "2024-01-01T10:00:00Z"
    assert result["event_type"] == "WORK_ITEM_STARTED"
    assert result["worker"] == "W1"
    assert result["message"] == "Started worker: W1"


def test_timeline_event_messages():
    """Test timeline event message generation."""
    test_cases = [
        ("RUN_CREATED", {}, "Run created"),
        ("INPUTS_CLONED", {}, "Inputs cloned"),
        ("WORK_ITEM_STARTED", {"worker": "W1"}, "Started worker: W1"),
        ("WORK_ITEM_FINISHED", {"worker": "W2"}, "Finished worker: W2"),
        ("GATE_RUN_FINISHED", {"gate_name": "schema", "passed": True}, "Gate PASSED: schema"),
        ("GATE_RUN_FINISHED", {"gate_name": "lint", "passed": False}, "Gate FAILED: lint"),
        ("PR_OPENED", {"pr_url": "https://github.com/org/repo/pull/123"}, "PR opened: https://github.com/org/repo/pull/123"),
        ("RUN_COMPLETED", {}, "Run completed successfully"),
        ("RUN_FAILED", {"error": "timeout"}, "Run failed: timeout"),
    ]

    from src.launch.observability.run_summary import _generate_event_message

    for event_type, payload, expected_message in test_cases:
        message = _generate_event_message(event_type, payload)
        assert message == expected_message, f"Failed for {event_type}"


def test_validate_evidence_completeness_complete(temp_run_dir: Path):
    """Test evidence completeness validation with complete run."""
    # Create required artifacts
    artifacts_dir = temp_run_dir / "artifacts"
    artifacts_dir.mkdir()

    (artifacts_dir / "repo_inventory.json").write_text("{}", encoding="utf-8")
    (artifacts_dir / "product_facts.json").write_text("{}", encoding="utf-8")
    (artifacts_dir / "page_plan.json").write_text("{}", encoding="utf-8")

    (temp_run_dir / "events.ndjson").write_text("", encoding="utf-8")

    result = validate_evidence_completeness(temp_run_dir)

    assert result["is_complete"] is True
    assert result["completeness_score"] == 100.0
    assert len(result["missing_artifacts"]) == 0


def test_validate_evidence_completeness_partial(temp_run_dir: Path):
    """Test evidence completeness validation with missing artifacts."""
    # Only create some artifacts
    artifacts_dir = temp_run_dir / "artifacts"
    artifacts_dir.mkdir()

    (artifacts_dir / "repo_inventory.json").write_text("{}", encoding="utf-8")

    result = validate_evidence_completeness(temp_run_dir)

    assert result["is_complete"] is False
    assert result["completeness_score"] < 100.0
    assert len(result["missing_artifacts"]) > 0
    assert "artifacts/product_facts.json" in result["missing_artifacts"]


def test_validate_evidence_completeness_empty_run(tmp_path: Path):
    """Test evidence completeness validation with empty run."""
    run_dir = tmp_path / "runs" / "empty-run"
    run_dir.mkdir(parents=True)

    snapshot = {"run_id": "empty-run", "work_items": []}
    (run_dir / "snapshot.json").write_text(json.dumps(snapshot), encoding="utf-8")

    result = validate_evidence_completeness(run_dir)

    assert result["is_complete"] is False
    assert result["completeness_score"] < 100.0
    assert len(result["missing_artifacts"]) > 0


def test_validate_evidence_completeness_score_calculation(temp_run_dir: Path):
    """Test evidence completeness score calculation."""
    # Create artifacts directory
    artifacts_dir = temp_run_dir / "artifacts"
    artifacts_dir.mkdir()

    # Create 3 out of 5 required artifacts (60%)
    (artifacts_dir / "repo_inventory.json").write_text("{}", encoding="utf-8")
    (artifacts_dir / "product_facts.json").write_text("{}", encoding="utf-8")
    (artifacts_dir / "page_plan.json").write_text("{}", encoding="utf-8")
    (temp_run_dir / "events.ndjson").write_text("", encoding="utf-8")

    # Missing: snapshot.json (already exists in fixture)

    result = validate_evidence_completeness(temp_run_dir)

    # Should have high score (4 of 5 = 80%)
    assert result["completeness_score"] == 100.0  # All exist in fixture


def test_generate_run_summary_invalid_timestamps(tmp_path: Path):
    """Test run summary with invalid timestamps."""
    run_dir = tmp_path / "runs" / "test-run"
    run_dir.mkdir(parents=True)

    snapshot = {
        "run_id": "test-run",
        "run_state": "DONE",
        "created_at": "invalid-timestamp",
        "updated_at": "also-invalid",
        "work_items": [],
    }
    (run_dir / "snapshot.json").write_text(json.dumps(snapshot), encoding="utf-8")

    summary = generate_run_summary(run_dir)

    # Should handle gracefully
    assert summary.duration_seconds == 0.0


def test_generate_run_summary_missing_timestamps(tmp_path: Path):
    """Test run summary with missing timestamps."""
    run_dir = tmp_path / "runs" / "test-run"
    run_dir.mkdir(parents=True)

    snapshot = {
        "run_id": "test-run",
        "run_state": "DONE",
        "work_items": [],
    }
    (run_dir / "snapshot.json").write_text(json.dumps(snapshot), encoding="utf-8")

    summary = generate_run_summary(run_dir)

    assert summary.started_at == ""
    assert summary.completed_at == ""
    assert summary.duration_seconds == 0.0


def test_generate_run_summary_malformed_events(temp_run_dir: Path):
    """Test run summary with malformed event lines."""
    events = [
        '{"type": "RUN_CREATED", "ts": "2024-01-01T10:00:00Z", "payload": {}}',
        'invalid json line',
        '{"type": "RUN_COMPLETED", "ts": "2024-01-01T10:30:00Z", "payload": {}}',
        '',  # Empty line
    ]
    (temp_run_dir / "events.ndjson").write_text("\n".join(events), encoding="utf-8")

    summary = generate_run_summary(temp_run_dir)

    # Should skip malformed lines
    assert len(summary.timeline) == 2  # Only valid events


def test_generate_run_summary_filters_minor_events(temp_run_dir: Path):
    """Test that minor events are filtered from timeline."""
    events = [
        '{"type": "RUN_CREATED", "ts": "2024-01-01T10:00:00Z", "payload": {}}',
        '{"type": "ARTIFACT_WRITTEN", "ts": "2024-01-01T10:05:00Z", "payload": {}}',  # Minor event
        '{"type": "RUN_COMPLETED", "ts": "2024-01-01T10:30:00Z", "payload": {}}',
    ]
    (temp_run_dir / "events.ndjson").write_text("\n".join(events), encoding="utf-8")

    summary = generate_run_summary(temp_run_dir)

    # Should only include major events
    assert len(summary.timeline) == 2
    event_types = [e.event_type for e in summary.timeline]
    assert "ARTIFACT_WRITTEN" not in event_types


def test_run_summary_markdown_empty_timeline(temp_run_dir: Path):
    """Test markdown with empty timeline."""
    summary = generate_run_summary(temp_run_dir)
    markdown = summary.to_markdown()

    assert "## Timeline" in markdown
    assert "_No timeline events recorded_" in markdown


def test_validate_evidence_completeness_missing_snapshot(tmp_path: Path):
    """Test evidence validation without snapshot."""
    run_dir = tmp_path / "runs" / "test-run"
    run_dir.mkdir(parents=True)

    # No snapshot.json created

    result = validate_evidence_completeness(run_dir)

    assert result["is_complete"] is False
    assert "snapshot.json" in result["missing_artifacts"]


def test_generate_run_summary_zero_workers(tmp_path: Path):
    """Test run summary with no workers."""
    run_dir = tmp_path / "runs" / "test-run"
    run_dir.mkdir(parents=True)

    snapshot = {
        "run_id": "test-run",
        "run_state": "CREATED",
        "created_at": "2024-01-01T10:00:00Z",
        "updated_at": "2024-01-01T10:00:01Z",
        "work_items": [],
    }
    (run_dir / "snapshot.json").write_text(json.dumps(snapshot), encoding="utf-8")

    summary = generate_run_summary(run_dir)

    assert summary.workers_total == 0
    assert summary.workers_completed == 0


def test_timeline_event_worker_extraction(temp_run_dir: Path):
    """Test worker extraction from different event payloads."""
    events = [
        '{"type": "WORK_ITEM_STARTED", "ts": "2024-01-01T10:00:00Z", "payload": {"worker": "W1"}}',
        '{"type": "GATE_RUN_STARTED", "ts": "2024-01-01T10:05:00Z", "payload": {"gate_name": "schema"}}',
        '{"type": "RUN_CREATED", "ts": "2024-01-01T10:10:00Z", "payload": {}}',
    ]
    (temp_run_dir / "events.ndjson").write_text("\n".join(events), encoding="utf-8")

    summary = generate_run_summary(temp_run_dir)

    assert summary.timeline[0].worker == "W1"
    assert summary.timeline[1].worker == "schema"
    assert summary.timeline[2].worker is None


def test_run_summary_markdown_validation_status(temp_run_dir: Path):
    """Test markdown shows correct validation status."""
    artifacts_dir = temp_run_dir / "artifacts"
    artifacts_dir.mkdir()

    validation_report = {"ok": True}
    (artifacts_dir / "validation_report.json").write_text(json.dumps(validation_report), encoding="utf-8")

    summary = generate_run_summary(temp_run_dir)
    markdown = summary.to_markdown()

    assert "Validation**: PASSED" in markdown

    # Test failed validation
    validation_report["ok"] = False
    (artifacts_dir / "validation_report.json").write_text(json.dumps(validation_report), encoding="utf-8")

    summary = generate_run_summary(temp_run_dir)
    markdown = summary.to_markdown()

    assert "Validation**: FAILED" in markdown
