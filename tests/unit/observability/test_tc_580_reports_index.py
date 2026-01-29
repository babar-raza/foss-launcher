"""
Test suite for TC-580: Reports Index Generation.

Tests reports index generation, metadata extraction, and filtering.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.launch.observability.reports_index import (
    ReportMetadata,
    ReportsIndex,
    generate_reports_index,
)


@pytest.fixture
def temp_reports_dir(tmp_path: Path) -> Path:
    """Create temporary reports directory structure."""
    reports_dir = tmp_path / "reports" / "agents"
    reports_dir.mkdir(parents=True)
    return reports_dir


def test_reports_index_empty_directory(temp_reports_dir: Path):
    """Test generating index from empty reports directory."""
    index = generate_reports_index(temp_reports_dir)

    assert index.total_reports == 0
    assert len(index.reports) == 0
    assert index.generated_at  # Should have timestamp


def test_reports_index_nonexistent_directory(tmp_path: Path):
    """Test generating index from nonexistent directory."""
    nonexistent = tmp_path / "does_not_exist"
    index = generate_reports_index(nonexistent)

    assert index.total_reports == 0
    assert len(index.reports) == 0


def test_reports_index_single_report(temp_reports_dir: Path):
    """Test generating index with single report."""
    # Create agent directory
    agent_dir = temp_reports_dir / "TEST_AGENT"
    agent_dir.mkdir()

    # Create taskcard directory
    tc_dir = agent_dir / "TC-100"
    tc_dir.mkdir()

    # Create report.md
    report_path = tc_dir / "report.md"
    report_path.write_text(
        "# TC-100 Report\n\nTests: 10/10 passing\n\nAll tests passed.",
        encoding="utf-8",
    )

    # Create self_review.md
    self_review_path = tc_dir / "self_review.md"
    self_review_path.write_text(
        "# Self Review\n\nQuality Score: 4.8/5\n\nExcellent implementation.",
        encoding="utf-8",
    )

    # Generate index
    index = generate_reports_index(temp_reports_dir)

    assert index.total_reports == 1
    assert len(index.reports) == 1

    report = index.reports[0]
    assert report.taskcard_id == "TC-100"
    assert report.agent_name == "TEST_AGENT"
    assert report.status == "complete"
    assert report.test_count == 10
    assert report.test_pass_count == 10
    assert report.quality_score == 4.8


def test_reports_index_multiple_reports(temp_reports_dir: Path):
    """Test generating index with multiple reports."""
    # Create multiple agents and taskcards
    agents = ["AGENT_A", "AGENT_B", "AGENT_C"]
    taskcards = ["TC-100", "TC-200"]

    for agent in agents:
        agent_dir = temp_reports_dir / agent
        agent_dir.mkdir()

        for tc_id in taskcards:
            tc_dir = agent_dir / tc_id
            tc_dir.mkdir()

            report_path = tc_dir / "report.md"
            report_path.write_text(f"# {tc_id} Report\n\n20/20 tests passing", encoding="utf-8")

            self_review_path = tc_dir / "self_review.md"
            self_review_path.write_text("Score: 5.0/5", encoding="utf-8")

    # Generate index
    index = generate_reports_index(temp_reports_dir)

    assert index.total_reports == 6  # 3 agents * 2 taskcards
    assert len(index.reports) == 6

    # Check sorting (by agent, then taskcard)
    agent_names = [r.agent_name for r in index.reports]
    assert agent_names == sorted(agent_names)


def test_reports_index_test_count_extraction_patterns(temp_reports_dir: Path):
    """Test various test count patterns in report.md."""
    test_cases = [
        ("15/15 passing", 15, 15),
        ("Tests: 20/20", 20, 20),
        ("Test Results: 8/10", 10, 8),
        ("5 of 10 tests pass", 10, 5),
        ("No matches here", 0, 0),
    ]

    for idx, (content, expected_total, expected_pass) in enumerate(test_cases):
        agent_dir = temp_reports_dir / f"AGENT_{idx}"
        agent_dir.mkdir()

        tc_dir = agent_dir / f"TC-{idx}"
        tc_dir.mkdir()

        report_path = tc_dir / "report.md"
        report_path.write_text(f"# Report\n\n{content}", encoding="utf-8")

        self_review_path = tc_dir / "self_review.md"
        self_review_path.write_text("Score: 4.0/5", encoding="utf-8")

    index = generate_reports_index(temp_reports_dir)

    for idx, (_, expected_total, expected_pass) in enumerate(test_cases):
        report = next(r for r in index.reports if r.taskcard_id == f"TC-{idx}")
        assert report.test_count == expected_total, f"Failed for pattern {idx}"
        assert report.test_pass_count == expected_pass, f"Failed for pattern {idx}"


def test_reports_index_quality_score_extraction_patterns(temp_reports_dir: Path):
    """Test various quality score patterns in self_review.md."""
    test_cases = [
        ("Score: 4.8/5", 4.8),
        ("Quality: 5.0/5", 5.0),
        ("Overall: 3.5/5", 3.5),
        ("Rating: 4.2/5", 4.2),
        ("No score here", 0.0),
    ]

    for idx, (content, expected_score) in enumerate(test_cases):
        agent_dir = temp_reports_dir / f"AGENT_{idx}"
        agent_dir.mkdir()

        tc_dir = agent_dir / f"TC-{idx}"
        tc_dir.mkdir()

        report_path = tc_dir / "report.md"
        report_path.write_text("# Report\n\n10/10 tests passing", encoding="utf-8")

        self_review_path = tc_dir / "self_review.md"
        self_review_path.write_text(f"# Self Review\n\n{content}", encoding="utf-8")

    index = generate_reports_index(temp_reports_dir)

    for idx, (_, expected_score) in enumerate(test_cases):
        report = next(r for r in index.reports if r.taskcard_id == f"TC-{idx}")
        assert report.quality_score == expected_score, f"Failed for pattern {idx}"


def test_reports_index_status_determination(temp_reports_dir: Path):
    """Test status determination based on file presence and content."""
    test_cases = [
        (True, True, "success", "complete"),
        (True, False, "success", "in_progress"),
        (False, True, "success", "in_progress"),  # Changed: has_review=True so it's included
        (True, True, "FAILED", "failed"),
        (True, True, "ERROR", "failed"),
    ]

    for idx, (has_report, has_review, content_keyword, expected_status) in enumerate(test_cases):
        agent_dir = temp_reports_dir / f"AGENT_{idx}"
        agent_dir.mkdir()

        tc_dir = agent_dir / f"TC-{idx}"
        tc_dir.mkdir()

        if has_report:
            report_path = tc_dir / "report.md"
            report_path.write_text(f"# Report\n\n{content_keyword}\n\n10/10 tests", encoding="utf-8")

        if has_review:
            self_review_path = tc_dir / "self_review.md"
            self_review_path.write_text("Score: 4.0/5", encoding="utf-8")

    index = generate_reports_index(temp_reports_dir)

    for idx, (has_report, has_review, _, expected_status) in enumerate(test_cases):
        # Skip case if neither file exists (won't be in index)
        if not has_report and not has_review:
            continue
        report = next(r for r in index.reports if r.taskcard_id == f"TC-{idx}")
        assert report.status == expected_status, f"Failed for case {idx}"


def test_report_metadata_to_dict(temp_reports_dir: Path):
    """Test ReportMetadata serialization to dict."""
    metadata = ReportMetadata(
        taskcard_id="TC-100",
        agent_name="TEST_AGENT",
        status="complete",
        test_count=10,
        test_pass_count=10,
        quality_score=4.8,
        created_at="2024-01-01T00:00:00Z",
        updated_at="2024-01-01T01:00:00Z",
        report_path="reports/agents/TEST_AGENT/TC-100/report.md",
        self_review_path="reports/agents/TEST_AGENT/TC-100/self_review.md",
    )

    result = metadata.to_dict()

    assert isinstance(result, dict)
    assert result["taskcard_id"] == "TC-100"
    assert result["agent_name"] == "TEST_AGENT"
    assert result["status"] == "complete"
    assert result["test_count"] == 10
    assert result["test_pass_count"] == 10
    assert result["quality_score"] == 4.8


def test_reports_index_to_dict(temp_reports_dir: Path):
    """Test ReportsIndex serialization to dict."""
    # Create sample report
    agent_dir = temp_reports_dir / "TEST_AGENT"
    agent_dir.mkdir()
    tc_dir = agent_dir / "TC-100"
    tc_dir.mkdir()

    report_path = tc_dir / "report.md"
    report_path.write_text("# Report\n\n10/10 passing", encoding="utf-8")

    self_review_path = tc_dir / "self_review.md"
    self_review_path.write_text("Score: 4.8/5", encoding="utf-8")

    # Generate index
    index = generate_reports_index(temp_reports_dir)
    result = index.to_dict()

    assert isinstance(result, dict)
    assert "generated_at" in result
    assert result["total_reports"] == 1
    assert isinstance(result["reports"], list)
    assert len(result["reports"]) == 1


def test_reports_index_to_json(temp_reports_dir: Path):
    """Test ReportsIndex serialization to JSON."""
    # Create sample report
    agent_dir = temp_reports_dir / "TEST_AGENT"
    agent_dir.mkdir()
    tc_dir = agent_dir / "TC-100"
    tc_dir.mkdir()

    report_path = tc_dir / "report.md"
    report_path.write_text("# Report\n\n10/10 passing", encoding="utf-8")

    self_review_path = tc_dir / "self_review.md"
    self_review_path.write_text("Score: 4.8/5", encoding="utf-8")

    # Generate index
    index = generate_reports_index(temp_reports_dir)
    json_str = index.to_json()

    # Verify valid JSON
    parsed = json.loads(json_str)
    assert parsed["total_reports"] == 1
    assert len(parsed["reports"]) == 1


def test_reports_index_deterministic_ordering(temp_reports_dir: Path):
    """Test that reports are sorted deterministically."""
    # Create reports in non-alphabetical order
    agents_and_tasks = [
        ("AGENT_C", "TC-300"),
        ("AGENT_A", "TC-200"),
        ("AGENT_B", "TC-100"),
        ("AGENT_A", "TC-100"),
    ]

    for agent, tc_id in agents_and_tasks:
        agent_dir = temp_reports_dir / agent
        agent_dir.mkdir(exist_ok=True)

        tc_dir = agent_dir / tc_id
        tc_dir.mkdir(exist_ok=True)

        report_path = tc_dir / "report.md"
        report_path.write_text("# Report\n\n10/10 passing", encoding="utf-8")

        self_review_path = tc_dir / "self_review.md"
        self_review_path.write_text("Score: 4.0/5", encoding="utf-8")

    # Generate index
    index = generate_reports_index(temp_reports_dir)

    # Verify sorting
    expected_order = [
        ("AGENT_A", "TC-100"),
        ("AGENT_A", "TC-200"),
        ("AGENT_B", "TC-100"),
        ("AGENT_C", "TC-300"),
    ]

    actual_order = [(r.agent_name, r.taskcard_id) for r in index.reports]
    assert actual_order == expected_order


def test_reports_index_skip_non_tc_directories(temp_reports_dir: Path):
    """Test that non-TC directories are skipped."""
    agent_dir = temp_reports_dir / "TEST_AGENT"
    agent_dir.mkdir()

    # Create valid TC directory
    tc_dir = agent_dir / "TC-100"
    tc_dir.mkdir()
    (tc_dir / "report.md").write_text("# Report\n\n10/10 passing", encoding="utf-8")
    (tc_dir / "self_review.md").write_text("Score: 4.0/5", encoding="utf-8")

    # Create invalid directories
    (agent_dir / "notes").mkdir()
    (agent_dir / "drafts").mkdir()
    (agent_dir / "README.md").write_text("# README", encoding="utf-8")

    # Generate index
    index = generate_reports_index(temp_reports_dir)

    # Should only find TC-100
    assert index.total_reports == 1
    assert index.reports[0].taskcard_id == "TC-100"


def test_reports_index_missing_self_review(temp_reports_dir: Path):
    """Test report with missing self_review.md."""
    agent_dir = temp_reports_dir / "TEST_AGENT"
    agent_dir.mkdir()

    tc_dir = agent_dir / "TC-100"
    tc_dir.mkdir()

    # Only create report.md
    report_path = tc_dir / "report.md"
    report_path.write_text("# Report\n\n10/10 passing", encoding="utf-8")

    # Generate index
    index = generate_reports_index(temp_reports_dir)

    assert index.total_reports == 1
    report = index.reports[0]
    assert report.status == "in_progress"
    assert report.quality_score == 0.0


def test_reports_index_missing_report(temp_reports_dir: Path):
    """Test report with missing report.md."""
    agent_dir = temp_reports_dir / "TEST_AGENT"
    agent_dir.mkdir()

    tc_dir = agent_dir / "TC-100"
    tc_dir.mkdir()

    # Only create self_review.md
    self_review_path = tc_dir / "self_review.md"
    self_review_path.write_text("Score: 4.8/5", encoding="utf-8")

    # Generate index
    index = generate_reports_index(temp_reports_dir)

    assert index.total_reports == 1
    report = index.reports[0]
    assert report.status == "in_progress"
    assert report.test_count == 0
    assert report.test_pass_count == 0


def test_reports_index_both_files_missing(temp_reports_dir: Path):
    """Test that directories with no report files are skipped."""
    agent_dir = temp_reports_dir / "TEST_AGENT"
    agent_dir.mkdir()

    tc_dir = agent_dir / "TC-100"
    tc_dir.mkdir()

    # Don't create any files

    # Generate index
    index = generate_reports_index(temp_reports_dir)

    # Should skip this directory
    assert index.total_reports == 0


def test_reports_index_quality_score_clamping(temp_reports_dir: Path):
    """Test that quality scores are clamped to 0.0-5.0."""
    test_cases = [
        ("Score: 6.5/5", 5.0),  # Clamp to max
        ("Score: -1.0/5", 0.0),  # Clamp to min (after extraction fails)
    ]

    for idx, (content, expected_score) in enumerate(test_cases):
        agent_dir = temp_reports_dir / f"AGENT_{idx}"
        agent_dir.mkdir()

        tc_dir = agent_dir / f"TC-{idx}"
        tc_dir.mkdir()

        report_path = tc_dir / "report.md"
        report_path.write_text("# Report\n\n10/10 tests", encoding="utf-8")

        self_review_path = tc_dir / "self_review.md"
        self_review_path.write_text(content, encoding="utf-8")

    index = generate_reports_index(temp_reports_dir)

    for idx, (_, expected_score) in enumerate(test_cases):
        report = next(r for r in index.reports if r.taskcard_id == f"TC-{idx}")
        assert report.quality_score == expected_score, f"Failed for case {idx}"


def test_reports_index_relative_paths(temp_reports_dir: Path):
    """Test that report paths are relative to project root."""
    agent_dir = temp_reports_dir / "TEST_AGENT"
    agent_dir.mkdir()

    tc_dir = agent_dir / "TC-100"
    tc_dir.mkdir()

    report_path = tc_dir / "report.md"
    report_path.write_text("# Report\n\n10/10 passing", encoding="utf-8")

    self_review_path = tc_dir / "self_review.md"
    self_review_path.write_text("Score: 4.8/5", encoding="utf-8")

    # Generate index
    index = generate_reports_index(temp_reports_dir)

    report = index.reports[0]
    # Paths should be relative and use forward slashes
    assert "TEST_AGENT" in report.report_path
    assert "TC-100" in report.report_path
    assert report.report_path.endswith("report.md")
    assert report.self_review_path.endswith("self_review.md")
