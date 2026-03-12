"""Tests for deploy promotion logic."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from launcher.deploy.manifest import DeployManifest, DeployedPage, load_manifest, save_manifest
from launcher.deploy.promoter import (
    GRADE_RANK,
    PromotionReport,
    _find_eval_report,
    grade_ge,
    backfill_runs,
    is_run_complete,
    promote_run,
)
from launcher.models.evaluation import Grade


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_run(
    tmp_path: Path,
    run_name: str,
    pages: list[dict],
    *,
    family: str = "cells",
    platform: str = "python",
    eval_location: str = "root",
) -> Path:
    """Create a minimal run directory with eval report and content files.

    Args:
        eval_location: Where to write the eval report.
            "root" — {run_dir}/evaluation_report.json (default)
            "subdir" — {run_dir}/evaluation/evaluation_summary.json
            "both" — both locations
    """
    run_dir = tmp_path / "runs" / run_name
    run_dir.mkdir(parents=True)

    # run_config.json
    (run_dir / "run_config.json").write_text(
        json.dumps({"family": family, "platform": platform}), encoding="utf-8"
    )

    # evaluation report
    eval_pages = []
    for p in pages:
        eval_pages.append({
            "slug": p.get("slug", p["content_path"].split("/")[-1]),
            "content_path": p["content_path"],
            "grade": p["grade"],
            "findings": [],
            "check_results": {},
        })
    eval_report = {
        "verdict": "NO_GO",
        "pages": eval_pages,
        "quality": {},
        "gates": [],
        "root_cause_diagnosis": [],
        "go_criteria": [],
    }
    eval_json = json.dumps(eval_report)
    if eval_location in ("root", "both"):
        (run_dir / "evaluation_report.json").write_text(eval_json, encoding="utf-8")
    if eval_location in ("subdir", "both"):
        eval_dir = run_dir / "evaluation"
        eval_dir.mkdir(parents=True, exist_ok=True)
        (eval_dir / "evaluation_summary.json").write_text(eval_json, encoding="utf-8")

    # Content files
    pages_dir = run_dir / "content_bundle" / "pages"
    for p in pages:
        content_path = p["content_path"]
        md_file = pages_dir / (content_path + ".md")
        md_file.parent.mkdir(parents=True, exist_ok=True)
        md_file.write_text(p.get("content", f"# {content_path}\n\nContent."), encoding="utf-8")

    return run_dir


# ---------------------------------------------------------------------------
# Grade comparison
# ---------------------------------------------------------------------------

class TestGradeComparison:
    def test_grade_rank_ordering(self):
        assert GRADE_RANK[Grade.A] > GRADE_RANK[Grade.B]
        assert GRADE_RANK[Grade.B] > GRADE_RANK[Grade.C]
        assert GRADE_RANK[Grade.C] > GRADE_RANK[Grade.D]
        assert GRADE_RANK[Grade.D] > GRADE_RANK[Grade.F]

    def test_grade_ge_same(self):
        assert grade_ge(Grade.B, Grade.B)

    def test_grade_ge_better(self):
        assert grade_ge(Grade.A, Grade.C)

    def test_grade_ge_worse(self):
        assert not grade_ge(Grade.D, Grade.B)


# ---------------------------------------------------------------------------
# Run completeness
# ---------------------------------------------------------------------------

class TestIsRunComplete:
    def test_complete_run(self, tmp_path: Path):
        run_dir = _create_run(tmp_path, "run1", [
            {"content_path": "docs.aspose.org/cells/test", "grade": "B"},
        ])
        assert is_run_complete(run_dir)

    def test_missing_eval_report(self, tmp_path: Path):
        run_dir = tmp_path / "runs" / "run2"
        run_dir.mkdir(parents=True)
        pages_dir = run_dir / "content_bundle" / "pages"
        pages_dir.mkdir(parents=True)
        (pages_dir / "test.md").write_text("content", encoding="utf-8")
        assert not is_run_complete(run_dir)

    def test_missing_content(self, tmp_path: Path):
        run_dir = tmp_path / "runs" / "run3"
        run_dir.mkdir(parents=True)
        (run_dir / "evaluation_report.json").write_text("{}", encoding="utf-8")
        assert not is_run_complete(run_dir)

    def test_empty_content_dir(self, tmp_path: Path):
        run_dir = tmp_path / "runs" / "run4"
        run_dir.mkdir(parents=True)
        (run_dir / "evaluation_report.json").write_text("{}", encoding="utf-8")
        (run_dir / "content_bundle" / "pages").mkdir(parents=True)
        assert not is_run_complete(run_dir)

    def test_complete_run_with_summary_only(self, tmp_path: Path):
        """Run with only evaluation/evaluation_summary.json is detected as complete."""
        run_dir = _create_run(tmp_path, "summary_only", [
            {"content_path": "docs.aspose.org/cells/test", "grade": "B"},
        ], eval_location="subdir")
        assert is_run_complete(run_dir)

    def test_root_eval_report_preferred_over_summary(self, tmp_path: Path):
        """When both files exist, _find_eval_report returns the root one."""
        run_dir = _create_run(tmp_path, "both", [
            {"content_path": "docs.aspose.org/cells/test", "grade": "B"},
        ], eval_location="both")
        found = _find_eval_report(run_dir)
        assert found is not None
        assert found.name == "evaluation_report.json"

    def test_find_eval_report_returns_none_when_missing(self, tmp_path: Path):
        """No eval file at all returns None."""
        run_dir = tmp_path / "runs" / "empty"
        run_dir.mkdir(parents=True)
        assert _find_eval_report(run_dir) is None


# ---------------------------------------------------------------------------
# promote_run from summary path
# ---------------------------------------------------------------------------

class TestPromoteFromSummary:
    def test_promote_from_summary_only(self, tmp_path: Path):
        """promote_run works when only evaluation/evaluation_summary.json exists."""
        deploy_dir = tmp_path / "deploy"
        run_dir = _create_run(tmp_path, "run_summary", [
            {"content_path": "docs.aspose.org/cells/python/install", "grade": "B"},
            {"content_path": "docs.aspose.org/cells/python/start", "grade": "A"},
        ], eval_location="subdir")

        report = promote_run(run_dir, deploy_dir)
        assert report.promoted == 2
        assert report.total_pages_in_run == 2
        assert (deploy_dir / "docs.aspose.org/cells/python/install.md").exists()

    def test_backfill_finds_summary_only_runs(self, tmp_path: Path):
        """backfill_runs includes runs that only have the summary file."""
        deploy_dir = tmp_path / "deploy"
        runs_root = tmp_path / "runs"

        _create_run(tmp_path, "run_with_summary", [
            {"content_path": "docs.aspose.org/cells/python/page", "grade": "B"},
        ], eval_location="subdir")

        reports = backfill_runs(runs_root, "cells", "python", deploy_dir)
        assert len(reports) == 1
        assert reports[0].promoted == 1


# ---------------------------------------------------------------------------
# promote_run
# ---------------------------------------------------------------------------

class TestPromoteRun:
    def test_promote_new_pages(self, tmp_path: Path):
        deploy_dir = tmp_path / "deploy"
        run_dir = _create_run(tmp_path, "run1", [
            {"content_path": "docs.aspose.org/cells/python/install", "grade": "B"},
            {"content_path": "docs.aspose.org/cells/python/start", "grade": "A"},
        ])

        report = promote_run(run_dir, deploy_dir)
        assert report.promoted == 2
        assert (deploy_dir / "docs.aspose.org/cells/python/install.md").exists()
        assert (deploy_dir / "docs.aspose.org/cells/python/start.md").exists()
        assert (deploy_dir / "manifest.json").exists()

    def test_min_grade_filter(self, tmp_path: Path):
        deploy_dir = tmp_path / "deploy"
        run_dir = _create_run(tmp_path, "run1", [
            {"content_path": "docs.aspose.org/cells/python/good", "grade": "B"},
            {"content_path": "docs.aspose.org/cells/python/bad", "grade": "D"},
        ])

        report = promote_run(run_dir, deploy_dir, min_grade=Grade.C)
        assert report.promoted == 1
        assert report.skipped_grade_low == 1

    def test_no_downgrade(self, tmp_path: Path):
        deploy_dir = tmp_path / "deploy"

        # First run: promote with grade A
        run1 = _create_run(tmp_path, "run1", [
            {"content_path": "docs.aspose.org/cells/python/page", "grade": "A", "content": "# Good\n\nExcellent."},
        ])
        promote_run(run1, deploy_dir)

        # Second run: same page with worse grade
        run2 = _create_run(tmp_path, "run2", [
            {"content_path": "docs.aspose.org/cells/python/page", "grade": "C", "content": "# Worse\n\nMediocre."},
        ])
        report = promote_run(run2, deploy_dir)
        assert report.promoted == 0
        assert report.skipped_no_improvement == 1

        # Verify content is still from run1
        content = (deploy_dir / "docs.aspose.org/cells/python/page.md").read_text(encoding="utf-8")
        assert "Excellent" in content

    def test_upgrade(self, tmp_path: Path):
        deploy_dir = tmp_path / "deploy"

        # First run: grade C
        run1 = _create_run(tmp_path, "run1", [
            {"content_path": "docs.aspose.org/cells/python/page", "grade": "C", "content": "# OK"},
        ])
        promote_run(run1, deploy_dir)

        # Second run: grade A
        run2 = _create_run(tmp_path, "run2", [
            {"content_path": "docs.aspose.org/cells/python/page", "grade": "A", "content": "# Great"},
        ])
        report = promote_run(run2, deploy_dir)
        assert report.promoted == 1

        content = (deploy_dir / "docs.aspose.org/cells/python/page.md").read_text(encoding="utf-8")
        assert "Great" in content

    def test_idempotent_same_hash(self, tmp_path: Path):
        deploy_dir = tmp_path / "deploy"
        run_dir = _create_run(tmp_path, "run1", [
            {"content_path": "docs.aspose.org/cells/python/page", "grade": "B"},
        ])

        report1 = promote_run(run_dir, deploy_dir)
        assert report1.promoted == 1

        report2 = promote_run(run_dir, deploy_dir)
        assert report2.promoted == 0
        assert report2.skipped_same_hash == 1

    def test_dry_run(self, tmp_path: Path):
        deploy_dir = tmp_path / "deploy"
        run_dir = _create_run(tmp_path, "run1", [
            {"content_path": "docs.aspose.org/cells/python/page", "grade": "B"},
        ])

        report = promote_run(run_dir, deploy_dir, dry_run=True)
        assert report.promoted == 1
        assert not deploy_dir.exists()

    def test_incomplete_run_skipped(self, tmp_path: Path):
        deploy_dir = tmp_path / "deploy"
        run_dir = tmp_path / "runs" / "incomplete"
        run_dir.mkdir(parents=True)

        report = promote_run(run_dir, deploy_dir)
        assert report.promoted == 0
        assert report.total_pages_in_run == 0

    def test_missing_content_file_skipped(self, tmp_path: Path):
        deploy_dir = tmp_path / "deploy"
        run_dir = tmp_path / "runs" / "run1"
        run_dir.mkdir(parents=True)

        # Create eval report referencing a page that doesn't exist on disk
        eval_report = {
            "verdict": "NO_GO",
            "pages": [{"slug": "ghost", "content_path": "docs.aspose.org/ghost", "grade": "A", "findings": [], "check_results": {}}],
            "quality": {}, "gates": [], "root_cause_diagnosis": [], "go_criteria": [],
        }
        (run_dir / "evaluation_report.json").write_text(json.dumps(eval_report), encoding="utf-8")
        # Create a dummy md so is_run_complete passes
        pages_dir = run_dir / "content_bundle" / "pages"
        pages_dir.mkdir(parents=True)
        (pages_dir / "dummy.md").write_text("x", encoding="utf-8")

        report = promote_run(run_dir, deploy_dir)
        assert report.skipped_missing_file == 1
        assert report.promoted == 0


# ---------------------------------------------------------------------------
# backfill_runs
# ---------------------------------------------------------------------------

class TestBackfillRuns:
    def test_backfill_multiple_runs(self, tmp_path: Path):
        deploy_dir = tmp_path / "deploy"
        runs_root = tmp_path / "runs"

        # Run 1: page with grade C
        _create_run(tmp_path, "run_old", [
            {"content_path": "docs.aspose.org/cells/python/page", "grade": "C", "content": "# Old"},
        ])

        # Run 2: same page with grade A
        _create_run(tmp_path, "run_new", [
            {"content_path": "docs.aspose.org/cells/python/page", "grade": "A", "content": "# New"},
        ])

        reports = backfill_runs(runs_root, "cells", "python", deploy_dir)
        assert len(reports) == 2

        # A-graded content must win regardless of processing order
        manifest = load_manifest(deploy_dir / "manifest.json")
        entry = manifest.pages["docs.aspose.org/cells/python/page"]
        assert entry.grade == Grade.A

        content = (deploy_dir / "docs.aspose.org/cells/python/page.md").read_text(encoding="utf-8")
        assert "New" in content

    def test_backfill_filters_by_family(self, tmp_path: Path):
        deploy_dir = tmp_path / "deploy"
        runs_root = tmp_path / "runs"

        _create_run(tmp_path, "cells_run", [
            {"content_path": "docs.aspose.org/cells/python/page", "grade": "B"},
        ], family="cells", platform="python")

        _create_run(tmp_path, "slides_run", [
            {"content_path": "docs.aspose.org/slides/python/page", "grade": "A"},
        ], family="slides", platform="python")

        reports = backfill_runs(runs_root, "cells", "python", deploy_dir)
        assert len(reports) == 1
        assert reports[0].run_id == "cells_run"

    def test_backfill_skips_incomplete(self, tmp_path: Path):
        deploy_dir = tmp_path / "deploy"
        runs_root = tmp_path / "runs"

        # Complete run
        _create_run(tmp_path, "complete", [
            {"content_path": "docs.aspose.org/cells/python/page", "grade": "B"},
        ])

        # Incomplete run (no eval report)
        incomplete = runs_root / "incomplete"
        incomplete.mkdir(parents=True)
        (incomplete / "run_config.json").write_text(
            json.dumps({"family": "cells", "platform": "python"}), encoding="utf-8"
        )

        reports = backfill_runs(runs_root, "cells", "python", deploy_dir)
        assert len(reports) == 1

    def test_backfill_nonexistent_root(self, tmp_path: Path):
        reports = backfill_runs(tmp_path / "nope", "cells", "python", tmp_path / "deploy")
        assert reports == []


# ---------------------------------------------------------------------------
# Atomic write behavior
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_promote_index_page(self, tmp_path: Path):
        """_index content paths must resolve to _index.md files."""
        deploy_dir = tmp_path / "deploy"
        run_dir = _create_run(tmp_path, "run1", [
            {"content_path": "products.aspose.org/cells/_index", "grade": "B"},
        ])
        report = promote_run(run_dir, deploy_dir)
        assert report.promoted == 1
        assert (deploy_dir / "products.aspose.org/cells/_index.md").exists()

    def test_promote_slug_fallback(self, tmp_path: Path):
        """When content_path is empty, slug is used as key."""
        deploy_dir = tmp_path / "deploy"
        run_dir = tmp_path / "runs" / "run1"
        run_dir.mkdir(parents=True)
        eval_report = {
            "verdict": "NO_GO",
            "pages": [{"slug": "docs.aspose.org/cells/python/install", "content_path": "", "grade": "B", "findings": [], "check_results": {}}],
            "quality": {}, "gates": [], "root_cause_diagnosis": [], "go_criteria": [],
        }
        (run_dir / "evaluation_report.json").write_text(json.dumps(eval_report), encoding="utf-8")
        pages_dir = run_dir / "content_bundle" / "pages"
        md_file = pages_dir / "docs.aspose.org/cells/python/install.md"
        md_file.parent.mkdir(parents=True, exist_ok=True)
        md_file.write_text("# Install", encoding="utf-8")

        report = promote_run(run_dir, deploy_dir)
        assert report.promoted == 1


class TestCLISmoke:
    def test_status_no_manifest(self, tmp_path: Path):
        from typer.testing import CliRunner
        from launcher.cli.main import app

        runner = CliRunner()
        result = runner.invoke(app, ["deploy", "status", "--deploy-dir", str(tmp_path / "empty")])
        assert "No deploy manifest found" in result.output

    def test_diff_shows_promotable(self, tmp_path: Path):
        from typer.testing import CliRunner
        from launcher.cli.main import app

        runner = CliRunner()
        run_dir = _create_run(tmp_path, "run1", [
            {"content_path": "docs.aspose.org/cells/python/page", "grade": "B"},
        ])
        result = runner.invoke(app, ["deploy", "diff", str(run_dir), "--deploy-dir", str(tmp_path / "deploy")])
        assert "would be promoted" in result.output


class TestPromotionReportPersistence:
    def test_report_persist_roundtrip(self, tmp_path: Path):
        """Promotion report can be serialized to disk and loaded back."""
        deploy_dir = tmp_path / "deploy"
        run_dir = _create_run(tmp_path, "run_persist", [
            {"content_path": "docs.aspose.org/cells/python/page", "grade": "B"},
        ])

        report = promote_run(run_dir, deploy_dir)
        assert report.promoted == 1

        # Write report to disk (simulates what run_loop / CLI does)
        report_path = deploy_dir / "promotion_report.json"
        report_data = report.model_dump(mode="json")
        report_path.write_text(json.dumps(report_data), encoding="utf-8")

        # Read back and verify
        loaded = json.loads(report_path.read_text(encoding="utf-8"))
        assert loaded["run_id"] == "run_persist"
        assert loaded["promoted"] == 1
        assert loaded["total_pages_in_run"] == 1

    def test_promotion_report_contains_details(self, tmp_path: Path):
        """Promotion report details list has entries for every evaluated page."""
        deploy_dir = tmp_path / "deploy"
        run_dir = _create_run(tmp_path, "run_details", [
            {"content_path": "docs.aspose.org/cells/python/a", "grade": "A"},
            {"content_path": "docs.aspose.org/cells/python/b", "grade": "B"},
            {"content_path": "docs.aspose.org/cells/python/c", "grade": "D"},
        ])

        report = promote_run(run_dir, deploy_dir, min_grade=Grade.C)
        report_data = report.model_dump(mode="json")

        assert report_data["promoted"] == 2
        assert report_data["total_pages_in_run"] == 3
        assert report_data["skipped_grade_low"] == 1
        assert len(report_data["details"]) == 3

        actions = {d["content_path"]: d["action"] for d in report_data["details"]}
        assert actions["docs.aspose.org/cells/python/a"] == "promoted"
        assert actions["docs.aspose.org/cells/python/b"] == "promoted"
        assert actions["docs.aspose.org/cells/python/c"] == "skipped_grade_low"


class TestAtomicWriteBehavior:
    def test_promotion_uses_atomic_write(self, tmp_path: Path):
        """Promoted files go through atomic write — no .tmp files remain on success."""
        deploy_dir = tmp_path / "deploy"
        run_dir = _create_run(tmp_path, "run_atomic", [
            {"content_path": "docs.aspose.org/cells/python/page", "grade": "B"},
        ])

        report = promote_run(run_dir, deploy_dir)
        assert report.promoted == 1
        assert (deploy_dir / "docs.aspose.org/cells/python/page.md").exists()

        # No .tmp files should remain anywhere under deploy/
        tmp_files = list(deploy_dir.rglob("*.tmp"))
        assert tmp_files == [], f"Leftover .tmp files: {tmp_files}"


class TestPerformanceShortCircuit:
    def test_grade_check_before_file_io(self, tmp_path: Path, monkeypatch):
        """SHA256 is never computed for pages below min_grade."""
        from unittest.mock import MagicMock

        import launcher.deploy.promoter as promoter_mod

        deploy_dir = tmp_path / "deploy"
        run_dir = _create_run(tmp_path, "run_perf", [
            {"content_path": "docs.aspose.org/cells/python/bad", "grade": "F"},
        ])

        mock_hash = MagicMock(side_effect=AssertionError("sha256_file should not be called"))
        monkeypatch.setattr(promoter_mod, "sha256_file", mock_hash)

        report = promote_run(run_dir, deploy_dir, min_grade=Grade.C)
        assert report.skipped_grade_low == 1
        assert report.promoted == 0
        mock_hash.assert_not_called()
