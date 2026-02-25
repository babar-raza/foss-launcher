"""Tests for review aggregator and taskcard generator (TC-2536, TC-2537, TC-2538).

Covers:
- Aggregator weighted scoring
- Quality tier classification
- Summary generation
- Taskcard generation from failing dimensions
- Schema compliance
- Edge cases (empty run, missing artifacts)
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List

import pytest

from launch.review.rubric import (
    DIMENSIONS,
    DimensionResult,
    Issue,
    classify_tier,
    compute_weighted_score,
)
from launch.review.aggregator import ReviewAggregator, write_review_artifacts
from launch.review.taskcard_generator import TaskcardGenerator, TaskcardDraft


# ── Fixtures ──────────────────────────────────────────────────────────────

def _make_run_dir(tmp_path: Path, pages: Dict[str, str] | None = None) -> Path:
    """Create a synthetic run directory with optional pages."""
    run_dir = tmp_path / "r_test"
    pages_dir = run_dir / "work" / "pages"
    pages_dir.mkdir(parents=True)
    artifacts_dir = run_dir / "artifacts"
    artifacts_dir.mkdir(parents=True)

    if pages:
        for name, content in pages.items():
            (pages_dir / name).write_text(content, encoding="utf-8")

    return run_dir


def _good_page_content() -> str:
    return (
        "---\n"
        "title: \"Convert PDF to Excel in Python - Complete Guide\"\n"
        "description: \"Learn how to convert PDF files to Excel spreadsheets using Python with Aspose.Cells library.\"\n"
        "keywords: \"python, pdf, excel, convert, aspose, cells\"\n"
        "---\n"
        "\n"
        "# Convert PDF to Excel in Python\n"
        "\n"
        "## Introduction\n"
        "\n"
        "This guide shows how to convert PDF to Excel.\n"
        "\n"
        "## Main Content\n"
        "\n"
        "Use the following code:\n"
        "\n"
        "```python\n"
        "import aspose.cells as ac\n"
        "\n"
        "workbook = ac.Workbook('input.pdf')\n"
        "workbook.save('output.xlsx')\n"
        "```\n"
        "\n"
        "## Conclusion\n"
        "\n"
        "You have successfully converted PDF to Excel.\n"
    )


def _bad_page_content() -> str:
    return (
        "# Bad Page\n"
        "\n"
        "#### Skipped heading levels\n"
        "\n"
        "You are a helpful assistant.\n"
        "\n"
        "```\n"
        "unclosed code block with no language tag\n"
        "\n"
        "[[CLAIM_123]] leaked marker.\n"
    )


# ── Rubric utility tests ─────────────────────────────────────────────────

class TestClassifyTier:
    """Quality tier classification."""

    def test_excellent(self):
        assert classify_tier(9.5) == "Excellent"
        assert classify_tier(8.0) == "Excellent"

    def test_good(self):
        assert classify_tier(7.5) == "Good"
        assert classify_tier(6.0) == "Good"

    def test_needs_work(self):
        assert classify_tier(5.0) == "Needs Work"
        assert classify_tier(4.0) == "Needs Work"

    def test_poor(self):
        assert classify_tier(3.9) == "Poor"
        assert classify_tier(0.0) == "Poor"


class TestWeightedScore:
    """Weighted average score computation."""

    def test_all_tens(self):
        scores = {d.dimension_id: 10 for d in DIMENSIONS}
        result = compute_weighted_score(scores)
        assert abs(result - 10.0) < 0.01

    def test_all_zeros(self):
        scores = {d.dimension_id: 0 for d in DIMENSIONS}
        result = compute_weighted_score(scores)
        assert abs(result - 0.0) < 0.01

    def test_mixed_scores(self):
        scores = {d.dimension_id: 5 for d in DIMENSIONS}
        result = compute_weighted_score(scores)
        assert abs(result - 5.0) < 0.01

    def test_skip_llm_renormalization(self):
        scores = {d.dimension_id: 10 for d in DIMENSIONS}
        result = compute_weighted_score(scores, skip_llm=True)
        assert abs(result - 10.0) < 0.01  # All same score, so skip doesn't change average

    def test_empty_scores(self):
        result = compute_weighted_score({})
        assert result == 0.0

    def test_weights_sum_to_one(self):
        total = sum(d.weight for d in DIMENSIONS)
        assert abs(total - 1.0) < 1e-9


# ── Aggregator tests ─────────────────────────────────────────────────────

class TestAggregator:
    """Review aggregator integration tests."""

    def test_good_content_scores_high(self, tmp_path):
        run_dir = _make_run_dir(tmp_path, {"good-page.md": _good_page_content()})
        agg = ReviewAggregator(run_dir, skip_llm=True)
        report = agg.run()

        assert report["schema_version"] == "2.0"
        assert report["pages_reviewed"] == 1
        assert report["overall_score"] >= 5.0
        assert report["overall_tier"] in ("Excellent", "Good", "Needs Work")
        assert len(report["dimensions"]) == 12

    def test_bad_content_scores_lower(self, tmp_path):
        run_dir = _make_run_dir(tmp_path, {"bad-page.md": _bad_page_content()})
        agg = ReviewAggregator(run_dir, skip_llm=True)
        report = agg.run()

        assert report["pages_reviewed"] == 1
        # Bad content should score lower than good content
        assert report["overall_score"] < 8.0

    def test_empty_run_dir(self, tmp_path):
        run_dir = _make_run_dir(tmp_path)
        agg = ReviewAggregator(run_dir, skip_llm=True)
        report = agg.run()

        assert report["pages_reviewed"] == 0
        assert report["overall_score"] == 0.0
        assert report["overall_tier"] == "Poor"

    def test_skip_llm_flag(self, tmp_path):
        run_dir = _make_run_dir(tmp_path, {"page.md": _good_page_content()})
        agg = ReviewAggregator(run_dir, skip_llm=True)
        report = agg.run()

        assert report["skip_llm"] is True

    def test_multiple_pages(self, tmp_path):
        run_dir = _make_run_dir(tmp_path, {
            "good.md": _good_page_content(),
            "bad.md": _bad_page_content(),
        })
        agg = ReviewAggregator(run_dir, skip_llm=True)
        report = agg.run()

        assert report["pages_reviewed"] == 2
        # Score should be between good and bad
        assert 0.0 <= report["overall_score"] <= 10.0

    def test_write_artifacts(self, tmp_path):
        run_dir = _make_run_dir(tmp_path, {"page.md": _good_page_content()})
        agg = ReviewAggregator(run_dir, skip_llm=True)
        report = agg.run()

        output_dir = tmp_path / "output"
        write_review_artifacts(report, output_dir)

        assert (output_dir / "review_report.json").exists()
        assert (output_dir / "review_summary.md").exists()

        # Verify JSON is valid
        report_json = json.loads((output_dir / "review_report.json").read_text(encoding="utf-8"))
        assert report_json["schema_version"] == "2.0"

    def test_summary_contains_table(self, tmp_path):
        run_dir = _make_run_dir(tmp_path, {"page.md": _good_page_content()})
        agg = ReviewAggregator(run_dir, skip_llm=True)
        report = agg.run()

        summary = report["summary"]
        assert "## Per-Page Scores" in summary
        assert "## Dimension Summary" in summary
        assert "| Page |" in summary

    def test_dimension_summaries_structure(self, tmp_path):
        run_dir = _make_run_dir(tmp_path, {"page.md": _good_page_content()})
        agg = ReviewAggregator(run_dir, skip_llm=True)
        report = agg.run()

        for ds in report["dimensions"]:
            assert "dimension_id" in ds
            assert "name" in ds
            assert "type" in ds
            assert "weight" in ds
            assert "avg_score" in ds
            assert "min_score" in ds
            assert "pages_below_threshold" in ds
            assert ds["avg_score"] >= 0.0
            assert ds["avg_score"] <= 10.0


# ── Taskcard generator tests ─────────────────────────────────────────────

def _make_review_report(page_scores: List[Dict[str, int]]) -> Dict[str, Any]:
    """Build a synthetic review report with given per-page dimension scores."""
    pages = []
    for idx, scores_dict in enumerate(page_scores):
        dim_scores = []
        for dim in DIMENSIONS:
            score = scores_dict.get(dim.dimension_id, 10)
            dim_scores.append({
                "dimension_id": dim.dimension_id,
                "score": score,
                "issues": [{"severity": "error", "message": f"Score {score} on {dim.name}"}] if score < 6 else [],
            })
        pages.append({
            "path": f"page-{idx}.md",
            "page_score": 7.0,
            "tier": "Good",
            "dimension_scores": dim_scores,
        })

    return {
        "schema_version": "2.0",
        "run_dir": "test_run",
        "reviewed_at": "2026-02-25T00:00:00Z",
        "overall_score": 7.0,
        "overall_tier": "Good",
        "pages_reviewed": len(pages),
        "dimensions": [],
        "pages": pages,
        "summary": "Test summary",
    }


class TestTaskcardGenerator:
    """Taskcard generation from review reports."""

    def test_all_scores_above_threshold(self):
        report = _make_review_report([{d.dimension_id: 8 for d in DIMENSIONS}])
        gen = TaskcardGenerator(report)
        drafts = gen.generate()
        assert len(drafts) == 0

    def test_one_dimension_below_threshold(self):
        scores = {d.dimension_id: 8 for d in DIMENSIONS}
        scores["RD-04"] = 3  # Code fence integrity below 6
        report = _make_review_report([scores])
        gen = TaskcardGenerator(report)
        drafts = gen.generate()
        assert len(drafts) == 1
        assert drafts[0].dimension_id == "RD-04"
        assert "Code fence" in drafts[0].title

    def test_multiple_dimensions_below_threshold(self):
        scores = {d.dimension_id: 8 for d in DIMENSIONS}
        scores["RD-04"] = 3
        scores["RD-05"] = 2
        scores["RD-07"] = 4
        report = _make_review_report([scores])
        gen = TaskcardGenerator(report)
        drafts = gen.generate()
        assert len(drafts) == 3
        dim_ids = {d.dimension_id for d in drafts}
        assert dim_ids == {"RD-04", "RD-05", "RD-07"}

    def test_threshold_exactly_six_no_taskcard(self):
        scores = {d.dimension_id: 6 for d in DIMENSIONS}
        report = _make_review_report([scores])
        gen = TaskcardGenerator(report)
        drafts = gen.generate()
        assert len(drafts) == 0  # 6 is not below threshold

    def test_empty_report(self):
        report = _make_review_report([])
        gen = TaskcardGenerator(report)
        drafts = gen.generate()
        assert len(drafts) == 0

    def test_taskcard_has_valid_markdown(self):
        scores = {d.dimension_id: 8 for d in DIMENSIONS}
        scores["RD-05"] = 2
        report = _make_review_report([scores])
        gen = TaskcardGenerator(report)
        drafts = gen.generate()
        assert len(drafts) == 1
        md = drafts[0].markdown
        assert md.startswith("---\n")
        assert "## Objective" in md
        assert "## Affected pages" in md
        assert "## Suggested fix" in md

    def test_taskcard_maps_to_correct_worker(self):
        scores = {d.dimension_id: 8 for d in DIMENSIONS}
        scores["RD-10"] = 3
        report = _make_review_report([scores])
        gen = TaskcardGenerator(report)
        drafts = gen.generate()
        assert len(drafts) == 1
        assert drafts[0].worker == "W6"

    def test_affected_pages_sorted(self):
        scores = {d.dimension_id: 8 for d in DIMENSIONS}
        scores["RD-04"] = 3
        # Two pages with the same failing dimension
        report = _make_review_report([scores, scores])
        gen = TaskcardGenerator(report)
        drafts = gen.generate()
        assert len(drafts) == 1
        paths = [p["path"] for p in drafts[0].affected_pages]
        assert paths == sorted(paths)


# ── DimensionResult tests ────────────────────────────────────────────────

class TestDimensionResult:
    """DimensionResult data class."""

    def test_score_clamping_high(self):
        r = DimensionResult("RD-01", "Test", 15)
        assert r.score == 10

    def test_score_clamping_low(self):
        r = DimensionResult("RD-01", "Test", -5)
        assert r.score == 0

    def test_score_rounding(self):
        r = DimensionResult("RD-01", "Test", 7.6)
        assert r.score == 8

    def test_to_dict(self):
        r = DimensionResult("RD-01", "Test", 8,
            [Issue("error", "Bad thing")])
        d = r.to_dict()
        assert d["dimension_id"] == "RD-01"
        assert d["score"] == 8
        assert len(d["issues"]) == 1
