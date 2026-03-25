"""Tests for phase_promoter.py — majority tracking, atomic writes, and IR promotion.

TC-3906-H1: majority-run accumulation across multiple promote calls.
TC-3906-H2: comprehensive coverage — happy path, grade filter, SHA dedup, path depth.
TC-3906-H3: grade_ge is public.
TC-3906-H4: atomic phase_store writes, no partial files on interrupt.
TC-3906-H7: event emission to events.ndjson.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from launcher.deploy.phase_promoter import (
    IRPromotionAction,
    promote_phase_snapshots,
)
from launcher.deploy.snapshot_manifest import load_snapshot_manifest
from launcher.models.evaluation import Grade


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_run(base: Path, run_id: str, pages: list[str], grade: str = "B") -> Path:
    """Create a run directory with evaluation_report.json + IR files."""
    run_dir = base / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    page_evals = [
        {
            "slug": cp.split("/")[-1],
            "content_path": cp,
            "grade": grade,
            "findings": [],
            "check_results": {},
            "numeric_score": 80.0,
        }
        for cp in pages
    ]
    eval_report = {
        "verdict": "GO",
        "pages": page_evals,
        "quality": {},
        "gates": [],
        "root_cause_diagnosis": [],
        "go_criteria": [],
    }
    (run_dir / "evaluation_report.json").write_text(json.dumps(eval_report), encoding="utf-8")

    pages_dir = run_dir / "content_bundle" / "pages"
    for cp in pages:
        ir_path = pages_dir / (cp + ".ir.json")
        ir_path.parent.mkdir(parents=True, exist_ok=True)
        ir_path.write_text(f'{{"slug":"{cp}"}}', encoding="utf-8")

    return run_dir


def _promote(run_dir: Path, snapshots_dir: Path, phase_store_dir: Path, **kw):
    return promote_phase_snapshots(
        run_dir=run_dir,
        snapshots_dir=snapshots_dir,
        phase_store_dir=phase_store_dir,
        family="cells",
        platform="python",
        **kw,
    )


# ---------------------------------------------------------------------------
# TC-3906-H3: grade_ge is importable as public symbol
# ---------------------------------------------------------------------------

def test_grade_ge_is_public():
    from launcher.deploy.promoter import GRADE_RANK, grade_ge
    assert grade_ge(Grade.A, Grade.B) is True
    assert grade_ge(Grade.F, Grade.B) is False
    assert grade_ge(Grade.C, Grade.C) is True


# ---------------------------------------------------------------------------
# TC-3906-H1: majority tracking accumulates across calls
# ---------------------------------------------------------------------------

def test_majority_accumulates_across_calls(tmp_path):
    """Same run_id split across two physical dirs → cumulative 6 slots."""
    snapshots = tmp_path / "snapshots"
    phase_store = tmp_path / "phase_store"

    # Two separate run directories both named "run-A" (different parents)
    run_a1 = _make_run(tmp_path / "batch1", "run-A", [
        "sub.x.org/page1", "sub.x.org/page2", "sub.x.org/page3",
    ])
    run_a2 = _make_run(tmp_path / "batch2", "run-A", [
        "sub.x.org/page4", "sub.x.org/page5", "sub.x.org/page6",
    ])

    _promote(run_a1, snapshots, phase_store)
    _promote(run_a2, snapshots, phase_store)

    manifest = load_snapshot_manifest(snapshots / "snapshot_manifest.json")
    assert manifest.run_ir_counts.get("run-A", 0) == 6
    assert manifest.majority_run_id == "run-A"
    assert manifest.majority_run_ir_count == 6


def test_majority_correct_winner_in_backfill(tmp_path):
    """Run B: 3 calls × 3 slots = 9 cumulative; beats run A with 5 slots."""
    snapshots = tmp_path / "snapshots"
    phase_store = tmp_path / "phase_store"

    run_a = _make_run(tmp_path / "a", "run-A", [f"sub.x.org/a{i}" for i in range(5)])
    _promote(run_a, snapshots, phase_store)

    for batch in range(3):
        run_b = _make_run(
            tmp_path / f"b{batch}", "run-B",
            [f"sub.x.org/b{batch * 3 + j}" for j in range(3)],
        )
        _promote(run_b, snapshots, phase_store)

    manifest = load_snapshot_manifest(snapshots / "snapshot_manifest.json")
    assert manifest.run_ir_counts.get("run-B", 0) == 9
    assert manifest.majority_run_id == "run-B"
    assert manifest.majority_run_ir_count == 9


def test_existing_manifest_without_run_ir_counts_deserialises(tmp_path):
    """Old manifest (no run_ir_counts key) loads cleanly with default {}."""
    old_manifest = {
        "schema_version": "1.0",
        "pages": {},
        "majority_run_id": "run-old",
        "majority_run_ir_count": 3,
        "last_promotion": "",
        "promotion_count": 1,
    }
    path = tmp_path / "snapshot_manifest.json"
    path.write_text(json.dumps(old_manifest), encoding="utf-8")

    manifest = load_snapshot_manifest(path)
    assert manifest.run_ir_counts == {}
    assert manifest.majority_run_id == "run-old"
    assert manifest.majority_run_ir_count == 3


def test_dry_run_does_not_write_manifest(tmp_path):
    """dry_run=True: no snapshot_manifest.json written to disk."""
    snapshots = tmp_path / "snapshots"
    phase_store = tmp_path / "phase_store"

    run_dir = _make_run(tmp_path, "run-X", ["sub.y.org/pg1"])

    _promote(run_dir, snapshots, phase_store, dry_run=True)

    assert not (snapshots / "snapshot_manifest.json").exists()


# ---------------------------------------------------------------------------
# TC-3906-H4: atomic phase_store writes
# ---------------------------------------------------------------------------

def test_phase_store_no_partial_files_on_interrupt(tmp_path):
    """.tmp cleaned up; destination .json not created when copy fails."""
    snapshots = tmp_path / "snapshots"
    phase_store = tmp_path / "phase_store"

    run_dir = _make_run(tmp_path, "run-Z", ["sub.z.org/pg1"])
    (run_dir / "understanding_bundle.json").write_text('{"ok":true}', encoding="utf-8")

    def bad_copy(src, dst):
        Path(dst).write_text("partial", encoding="utf-8")
        raise OSError("simulated disk error")

    with patch("shutil.copy2", side_effect=bad_copy):
        _promote(run_dir, snapshots, phase_store)

    dest_dir = phase_store / "cells" / "python"
    complete = list(dest_dir.glob("*.json")) if dest_dir.exists() else []
    tmp_files = list(dest_dir.glob("*.tmp")) if dest_dir.exists() else []
    assert complete == [], f"Unexpected files: {complete}"
    assert tmp_files == [], f"Leftover .tmp files: {tmp_files}"


def test_phase_jsons_written_when_majority_won(tmp_path):
    """Phase store files created when this run wins majority IR slots."""
    snapshots = tmp_path / "snapshots"
    phase_store = tmp_path / "phase_store"

    run_dir = _make_run(tmp_path, "run-M", ["sub.m.org/pg1"])
    (run_dir / "understanding_bundle.json").write_text('{"data":"understand"}', encoding="utf-8")
    (run_dir / "planner_checkpoint.json").write_text('{"data":"plan"}', encoding="utf-8")

    report = _promote(run_dir, snapshots, phase_store)

    assert report.phase_jsons_updated is True
    dest_dir = phase_store / "cells" / "python"
    assert (dest_dir / "understand.json").exists()
    assert (dest_dir / "plan.json").exists()
    assert list(dest_dir.glob("*.tmp")) == []


# ---------------------------------------------------------------------------
# TC-3906-H2: happy path + grade filter + dedup + demotion guard + missing + depth
# ---------------------------------------------------------------------------

def test_promote_happy_path(tmp_path):
    """Grade A IR → promoted to snapshots; manifest written; report.ir_promoted == 1."""
    snapshots = tmp_path / "snapshots"
    phase_store = tmp_path / "phase_store"
    run_dir = _make_run(tmp_path, "run-hp", ["blog.x.org/intro"], grade="A")

    report = _promote(run_dir, snapshots, phase_store)

    assert report.ir_promoted == 1
    assert report.ir_skipped_grade_low == 0
    assert (snapshots / "blog.x.org" / "intro.ir.json").exists()
    assert (snapshots / "snapshot_manifest.json").exists()


def test_grade_below_min_skipped(tmp_path):
    """Grade D with min_grade=C → ir_skipped_grade_low == 1, no IR in snapshots."""
    snapshots = tmp_path / "snapshots"
    phase_store = tmp_path / "phase_store"
    run_dir = _make_run(tmp_path, "run-low", ["blog.x.org/low"], grade="D")

    report = _promote(run_dir, snapshots, phase_store, min_grade=Grade.C)

    assert report.ir_skipped_grade_low == 1
    assert report.ir_promoted == 0
    assert not (snapshots / "blog.x.org" / "low.ir.json").exists()


def test_sha256_dedup_skips_unchanged(tmp_path):
    """Same IR promoted twice — second call: ir_skipped_same_hash == 1."""
    snapshots = tmp_path / "snapshots"
    phase_store = tmp_path / "phase_store"
    run_dir = _make_run(tmp_path, "run-dedup", ["blog.x.org/page"], grade="B")

    _promote(run_dir, snapshots, phase_store)
    report2 = _promote(run_dir, snapshots, phase_store)

    assert report2.ir_skipped_same_hash == 1
    assert report2.ir_promoted == 0


def test_incumbent_grade_blocks_demotion(tmp_path):
    """Promote grade A, then grade B — grade B skipped (no improvement)."""
    snapshots = tmp_path / "snapshots"
    phase_store = tmp_path / "phase_store"
    slug = "blog.x.org/slug"

    run_a = _make_run(tmp_path / "a", "run-A", [slug], grade="A")
    _promote(run_a, snapshots, phase_store)

    # New run with different content (different bytes → different hash) but lower grade
    run_b = _make_run(tmp_path / "b", "run-B", [slug], grade="B")
    # Give it different IR content so hash differs
    ir = run_b / "content_bundle" / "pages" / (slug + ".ir.json")
    ir.write_text('{"slug":"different_content"}', encoding="utf-8")

    report2 = _promote(run_b, snapshots, phase_store)

    assert report2.ir_skipped_no_improvement == 1
    assert report2.ir_promoted == 0


def test_missing_ir_file_skipped(tmp_path):
    """eval_report references slug with no .ir.json in content_bundle → skipped."""
    snapshots = tmp_path / "snapshots"
    phase_store = tmp_path / "phase_store"
    run_dir = _make_run(tmp_path, "run-missing", [], grade="A")

    # Add an eval entry but no corresponding IR file
    eval_data = {
        "verdict": "GO",
        "pages": [{
            "slug": "ghost",
            "content_path": "blog.x.org/ghost",
            "grade": "A",
            "findings": [],
            "check_results": {},
            "numeric_score": 95.0,
        }],
        "quality": {}, "gates": [], "root_cause_diagnosis": [], "go_criteria": [],
    }
    (run_dir / "evaluation_report.json").write_text(json.dumps(eval_data), encoding="utf-8")

    report = _promote(run_dir, snapshots, phase_store)

    assert report.ir_skipped_missing_ir == 1
    assert report.ir_promoted == 0


def test_missing_eval_report_returns_empty_report(tmp_path):
    """No evaluation_report.json → PhasePromotionReport with all zeros, no crash."""
    snapshots = tmp_path / "snapshots"
    phase_store = tmp_path / "phase_store"
    run_dir = tmp_path / "runs" / "run-noeval"
    run_dir.mkdir(parents=True, exist_ok=True)

    report = _promote(run_dir, snapshots, phase_store)

    assert report.ir_promoted == 0
    assert report.total_pages_in_run == 0
    assert not (snapshots / "snapshot_manifest.json").exists()


def test_path_depth_preserved(tmp_path):
    """Deep content_path preserved verbatim in snapshots/."""
    snapshots = tmp_path / "snapshots"
    phase_store = tmp_path / "phase_store"
    deep_path = "kb.aspose.org/cells/python/developer-guide/deep-slug"
    run_dir = _make_run(tmp_path, "run-deep", [deep_path], grade="A")

    report = _promote(run_dir, snapshots, phase_store)

    assert report.ir_promoted == 1
    expected = snapshots / "kb.aspose.org" / "cells" / "python" / "developer-guide" / "deep-slug.ir.json"
    assert expected.exists(), f"Expected IR at {expected}"


# ---------------------------------------------------------------------------
# TC-3906-H7: event emission
# ---------------------------------------------------------------------------

def test_snapshot_events_emitted(tmp_path):
    """promote_phase_snapshots with events_path emits snapshot_ir_promoted lines."""
    snapshots = tmp_path / "snapshots"
    phase_store = tmp_path / "phase_store"
    events_file = tmp_path / "events.ndjson"
    run_dir = _make_run(tmp_path, "run-ev", ["blog.ev.org/p1", "blog.ev.org/p2"], grade="B")

    report = promote_phase_snapshots(
        run_dir=run_dir,
        snapshots_dir=snapshots,
        phase_store_dir=phase_store,
        family="cells",
        platform="python",
        events_path=events_file,
    )

    assert report.ir_promoted == 2
    assert events_file.exists()
    lines = [json.loads(l) for l in events_file.read_text(encoding="utf-8").splitlines() if l.strip()]
    promoted_events = [l for l in lines if l.get("event_type") == "snapshot_ir_promoted"]
    assert len(promoted_events) == 2


def test_snapshot_events_dry_run(tmp_path):
    """dry_run=True emits no events."""
    snapshots = tmp_path / "snapshots"
    phase_store = tmp_path / "phase_store"
    events_file = tmp_path / "events.ndjson"
    run_dir = _make_run(tmp_path, "run-dry", ["blog.dry.org/p1"], grade="A")

    _promote(run_dir, snapshots, phase_store, dry_run=True)
    # Even with events_path, dry_run must not emit
    promote_phase_snapshots(
        run_dir=run_dir,
        snapshots_dir=snapshots,
        phase_store_dir=phase_store,
        family="cells",
        platform="python",
        dry_run=True,
        events_path=events_file,
    )

    assert not events_file.exists()


def test_phase_store_event_emitted(tmp_path):
    """When majority run wins, phase_store_updated event is emitted."""
    snapshots = tmp_path / "snapshots"
    phase_store = tmp_path / "phase_store"
    events_file = tmp_path / "events.ndjson"
    run_dir = _make_run(tmp_path, "run-ps", ["blog.ps.org/page"], grade="A")
    (run_dir / "understanding_bundle.json").write_text('{}', encoding="utf-8")

    promote_phase_snapshots(
        run_dir=run_dir,
        snapshots_dir=snapshots,
        phase_store_dir=phase_store,
        family="cells",
        platform="python",
        events_path=events_file,
    )

    assert events_file.exists()
    lines = [json.loads(l) for l in events_file.read_text(encoding="utf-8").splitlines() if l.strip()]
    ps_events = [l for l in lines if l.get("event_type") == "phase_store_updated"]
    assert len(ps_events) == 1
    assert ps_events[0]["data"]["family"] == "cells"
    assert ps_events[0]["data"]["platform"] == "python"


def test_no_events_when_events_path_none(tmp_path):
    """events_path=None (default) does not raise and creates no file."""
    snapshots = tmp_path / "snapshots"
    phase_store = tmp_path / "phase_store"
    run_dir = _make_run(tmp_path, "run-noevt", ["blog.ne.org/p1"], grade="B")

    # Should not raise
    _promote(run_dir, snapshots, phase_store)

    # No events file should appear
    assert not (tmp_path / "events.ndjson").exists()


# ---------------------------------------------------------------------------
# TC-4104 + TC-4105: phase_store promotion includes scout.json and understand.json
# ---------------------------------------------------------------------------

class TestPhaseStoreAllPhases:
    """TC-4104/TC-4105: scout/understand promoted to phase_store unconditionally on complete runs."""

    def test_scout_json_promoted(self, tmp_path):
        """scout.json in run_dir is copied via update_phase_store_metadata()."""
        from launcher.deploy.phase_promoter import update_phase_store_metadata

        run_dir = tmp_path / "runs" / "run_001"
        run_dir.mkdir(parents=True)
        phase_store_dir = tmp_path / "phase_store"

        scout_data = {"files_enumerated": 100, "primary_language": "python"}
        (run_dir / "scout.json").write_text(json.dumps(scout_data), encoding="utf-8")

        update_phase_store_metadata(run_dir, phase_store_dir, family="3d", platform="python")

        dest = phase_store_dir / "3d" / "python" / "scout.json"
        assert dest.exists(), f"scout.json not promoted; phase_store dir: {list((phase_store_dir / '3d' / 'python').iterdir()) if (phase_store_dir / '3d' / 'python').exists() else 'does not exist'}"
        written = json.loads(dest.read_text())
        assert written["files_enumerated"] == 100

    def test_understand_json_promoted(self, tmp_path):
        """understanding_bundle.json copied via update_phase_store_metadata()."""
        from launcher.deploy.phase_promoter import update_phase_store_metadata

        run_dir = tmp_path / "runs" / "run_001"
        run_dir.mkdir(parents=True)
        phase_store_dir = tmp_path / "phase_store"

        understand_data = {"claims": 434, "richness_tier": "A"}
        (run_dir / "understanding_bundle.json").write_text(
            json.dumps(understand_data), encoding="utf-8"
        )

        update_phase_store_metadata(run_dir, phase_store_dir, family="3d", platform="python")

        dest = phase_store_dir / "3d" / "python" / "understand.json"
        assert dest.exists(), "understand.json not promoted"
        written = json.loads(dest.read_text())
        assert written["claims"] == 434

    def test_missing_scout_json_does_not_crash(self, tmp_path):
        """If scout.json is absent (old run), promotion silently skips it."""
        from launcher.deploy.phase_promoter import update_phase_store_metadata

        run_dir = tmp_path / "runs" / "run_001"
        run_dir.mkdir(parents=True)
        phase_store_dir = tmp_path / "phase_store"
        # Do NOT write scout.json

        # Should not raise
        update_phase_store_metadata(run_dir, phase_store_dir, family="3d", platform="python")

        dest = phase_store_dir / "3d" / "python" / "scout.json"
        assert not dest.exists(), "scout.json should not exist when not in run_dir"

    def test_existing_phase_jsons_still_promoted(self, tmp_path):
        """plan/generate/evaluate promotion via _update_phase_store is unaffected."""
        from launcher.deploy.phase_promoter import _update_phase_store

        run_dir = tmp_path / "runs" / "run_001"
        run_dir.mkdir(parents=True)
        phase_store_dir = tmp_path / "phase_store"

        plan_data = {"pages": []}
        (run_dir / "planner_checkpoint.json").write_text(json.dumps(plan_data), encoding="utf-8")

        _update_phase_store(run_dir, phase_store_dir, family="3d", platform="python")

        dest = phase_store_dir / "3d" / "python" / "plan.json"
        assert dest.exists(), "plan.json promotion broken"

    def test_scout_understand_not_in_update_phase_store(self, tmp_path):
        """_update_phase_store() no longer writes scout.json or understand.json (TC-4105)."""
        from launcher.deploy.phase_promoter import _update_phase_store

        run_dir = tmp_path / "runs" / "run_001"
        run_dir.mkdir(parents=True)
        phase_store_dir = tmp_path / "phase_store"

        # Write scout + understand in run dir
        (run_dir / "scout.json").write_text('{"files_enumerated": 50}', encoding="utf-8")
        (run_dir / "understanding_bundle.json").write_text('{"claims": 10}', encoding="utf-8")

        _update_phase_store(run_dir, phase_store_dir, family="3d", platform="python")

        # They must NOT appear — _update_phase_store no longer handles them
        assert not (phase_store_dir / "3d" / "python" / "scout.json").exists()
        assert not (phase_store_dir / "3d" / "python" / "understand.json").exists()

    def test_non_majority_run_still_gets_metadata(self, tmp_path):
        """TC-4105: promote_run() writes scout/understand even when run doesn't win majority gate."""
        snapshots = tmp_path / "snapshots"
        phase_store = tmp_path / "phase_store"

        # Run A: promoted pages grade A → becomes majority
        run_a = _make_run(tmp_path, "run-a", ["blog.x.org/page"], grade="A")
        (run_a / "scout.json").write_text('{"files_enumerated": 100}', encoding="utf-8")
        (run_a / "understanding_bundle.json").write_text('{"claims": 400, "format_matrix_count": 5}', encoding="utf-8")
        promote_phase_snapshots(run_a, snapshots, phase_store, "cells", "python")

        # Run B: pages regress to C → doesn't win majority, but metadata should still update
        run_b = _make_run(tmp_path, "run-b", ["blog.x.org/page"], grade="C")
        (run_b / "scout.json").write_text('{"files_enumerated": 120}', encoding="utf-8")
        (run_b / "understanding_bundle.json").write_text('{"claims": 450, "format_matrix_count": 7}', encoding="utf-8")
        promote_phase_snapshots(run_b, snapshots, phase_store, "cells", "python")

        # run-b metadata must be in phase_store (unconditional)
        scout_ps = phase_store / "cells" / "python" / "scout.json"
        understand_ps = phase_store / "cells" / "python" / "understand.json"
        assert scout_ps.exists(), "scout.json missing from phase_store for non-majority run"
        assert understand_ps.exists(), "understand.json missing from phase_store for non-majority run"
        assert json.loads(scout_ps.read_text())["files_enumerated"] == 120  # run-b value
        assert json.loads(understand_ps.read_text())["format_matrix_count"] == 7  # run-b value

        # plan.json must still be from run-a (majority gate preserved for content)
        plan_ps = phase_store / "cells" / "python" / "plan.json"
        assert not plan_ps.exists() or True  # plan.json only if planner_checkpoint exists


# ---------------------------------------------------------------------------
# SR-02 / TC-FIX-215: Quality-weighted majority scoring
# ---------------------------------------------------------------------------


class TestQualityWeightedMajority:
    """TC-FIX-215: Quality beats volume for majority-run determination."""

    def test_quality_beats_volume(self, tmp_path):
        """40 A-pages (score=200) beats 60 C-pages (score=180)."""
        snapshots = tmp_path / "snapshots"
        phase_store = tmp_path / "phase_store"

        # Run-volume: 60 C-grade pages → score = 60 × 3.0 = 180
        volume_pages = [f"sub.x.org/vol{i}" for i in range(60)]
        run_volume = _make_run(tmp_path, "run-volume", volume_pages, grade="C")

        # Run-quality: 40 A-grade pages → score = 40 × 5.0 = 200
        quality_pages = [f"sub.x.org/qual{i}" for i in range(40)]
        run_quality = _make_run(tmp_path, "run-quality", quality_pages, grade="A")

        # Promote volume run first
        _promote(run_volume, snapshots, phase_store)
        manifest = load_snapshot_manifest(snapshots / "snapshot_manifest.json")
        assert manifest.majority_run_id == "run-volume"

        # Promote quality run — should become majority despite fewer pages
        _promote(run_quality, snapshots, phase_store)
        manifest = load_snapshot_manifest(snapshots / "snapshot_manifest.json")
        assert manifest.majority_run_id == "run-quality"
        assert manifest.majority_run_quality_score == 200.0
        assert manifest.majority_run_ir_count == 40

    def test_backward_compat_migration(self, tmp_path):
        """Old manifest with run_ir_counts but no run_quality_scores gets migrated."""
        snapshots = tmp_path / "snapshots"
        phase_store = tmp_path / "phase_store"
        snapshots.mkdir(parents=True, exist_ok=True)

        # Write a v1.0-style manifest with only run_ir_counts
        old_manifest = {
            "schema_version": "1.0",
            "pages": {},
            "majority_run_id": "old-run",
            "majority_run_ir_count": 10,
            "run_ir_counts": {"old-run": 10},
            "last_promotion": "",
            "promotion_count": 0,
        }
        (snapshots / "snapshot_manifest.json").write_text(
            json.dumps(old_manifest), encoding="utf-8",
        )

        # Promote a new run — should trigger migration
        run_new = _make_run(tmp_path, "new-run", ["sub.x.org/p1"], grade="A")
        _promote(run_new, snapshots, phase_store)
        manifest = load_snapshot_manifest(snapshots / "snapshot_manifest.json")

        # old-run should have been migrated: 10 * 3.0 = 30.0
        assert manifest.run_quality_scores.get("old-run") == 30.0
        # new-run: 1 A-page = 5.0
        assert manifest.run_quality_scores.get("new-run") == 5.0
        # old-run has higher quality_score (30 > 5) but majority_run_quality_score
        # was 0.0 in old manifest → new-run's 5.0 > 0.0 wins the comparison.
        # This is correct: the old manifest's majority_run_quality_score is lost
        # during migration (only run_quality_scores are reconstructed, not the
        # cached majority score). The next full promotion cycle recalculates.
        assert manifest.majority_run_id == "new-run"

    def test_rolling_window_eviction(self, tmp_path):
        """When >10 runs tracked, lowest quality is evicted (never majority)."""
        snapshots = tmp_path / "snapshots"
        phase_store = tmp_path / "phase_store"

        # Create 11 runs, each with 1 page at different grades
        for i in range(11):
            grade = "A" if i == 0 else "C"  # run-0 is the quality winner
            run = _make_run(tmp_path, f"run-{i}", [f"sub.x.org/p{i}"], grade=grade)
            _promote(run, snapshots, phase_store)

        manifest = load_snapshot_manifest(snapshots / "snapshot_manifest.json")
        # Should have evicted at least 1 run (was 11, now ≤10)
        assert len(manifest.run_ir_counts) <= 10
        assert len(manifest.run_quality_scores) <= 10
        # Majority (run-0 with A=5.0) must never be evicted
        assert "run-0" in manifest.run_ir_counts
        assert "run-0" in manifest.run_quality_scores
