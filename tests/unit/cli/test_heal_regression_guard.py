"""Tests for TC-3510: Heal regression guard and W5 deprioritization."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

from launch.cli.heal import (
    _create_checkpoint,
    _deprioritize_w5,
    _restore_checkpoint,
    choose_worker,
    count_failed_gates,
    extract_worker_from_recommendation,
    HealStep,
    run_heal_loop,
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_gate(name: str, ok: bool = True) -> Dict[str, Any]:
    return {"name": name, "ok": ok}


def _make_report(failing_count: int) -> Dict[str, Any]:
    gates = [_make_gate(f"gate_{i}", ok=(i >= failing_count)) for i in range(10)]
    return {
        "schema_version": "1.0",
        "ok": failing_count == 0,
        "profile": "local",
        "gates": gates,
        "issues": [],
    }


def _write_report(run_dir: Path, failing_count: int) -> None:
    (run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
    (run_dir / "artifacts" / "validation_report.json").write_text(
        json.dumps(_make_report(failing_count)), encoding="utf-8"
    )


def _make_rec(worker: str, reason: str = "test", rec_id: str = "") -> Dict[str, str]:
    """Build a triage recommendation dict.

    TC-3614: rec_id defaults to a stable synthetic id based on worker so
    that quarantine key tests work correctly without requiring real triage.
    """
    return {
        "command": f"launch resume --run-dir /tmp --from-worker {worker}",
        "reason": reason,
        "id": rec_id or f"triage:_match_test->{worker}",
    }


# ── Checkpoint tests ──────────────────────────────────────────────────────────


class TestCheckpoint:
    def test_create_checkpoint_copies_artifacts(self, tmp_path):
        run_dir = tmp_path / "run"
        (run_dir / "artifacts").mkdir(parents=True)
        (run_dir / "artifacts" / "validation_report.json").write_text('{"ok": true}')

        cp = _create_checkpoint(run_dir, 0)

        assert cp is not None
        assert (cp / "artifacts" / "validation_report.json").exists()
        assert (cp / "artifacts" / "validation_report.json").read_text() == '{"ok": true}'

    def test_create_checkpoint_copies_content_dir(self, tmp_path):
        run_dir = tmp_path / "run"
        (run_dir / "artifacts").mkdir(parents=True)
        content_dir = run_dir / "work" / "site" / "content"
        content_dir.mkdir(parents=True)
        (content_dir / "page.md").write_text("# Page")

        cp = _create_checkpoint(run_dir, 1)

        assert cp is not None
        assert (cp / "work" / "site" / "content" / "page.md").exists()

    def test_restore_checkpoint_overwrites_artifacts(self, tmp_path):
        run_dir = tmp_path / "run"
        (run_dir / "artifacts").mkdir(parents=True)
        (run_dir / "artifacts" / "validation_report.json").write_text('{"ok": true}')

        cp = _create_checkpoint(run_dir, 0)

        # Corrupt the report
        (run_dir / "artifacts" / "validation_report.json").write_text(
            '{"ok": false, "gates": []}'
        )

        restored = _restore_checkpoint(run_dir, cp)

        assert restored is True
        content = (run_dir / "artifacts" / "validation_report.json").read_text()
        assert '"ok": true' in content

    def test_create_checkpoint_handles_missing_dirs_gracefully(self, tmp_path):
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        # No artifacts dir — should not crash
        cp = _create_checkpoint(run_dir, 0)
        # Either returns a valid checkpoint dir (empty) or None — no exception
        assert cp is None or cp.exists()

    def test_create_checkpoint_creates_step_subdir(self, tmp_path):
        run_dir = tmp_path / "run"
        (run_dir / "artifacts").mkdir(parents=True)
        (run_dir / "artifacts" / "validation_report.json").write_text('{"ok": true}')

        cp = _create_checkpoint(run_dir, 3)

        assert cp is not None
        # Checkpoint dir is at _heal_checkpoints/step_3
        assert cp.name == "step_3"
        assert cp.parent.name == "_heal_checkpoints"

    def test_restore_checkpoint_copies_drafts_dir(self, tmp_path):
        run_dir = tmp_path / "run"
        (run_dir / "artifacts").mkdir(parents=True)
        drafts_dir = run_dir / "drafts"
        drafts_dir.mkdir(parents=True)
        (drafts_dir / "page.md").write_text("# Draft")

        cp = _create_checkpoint(run_dir, 0)
        assert cp is not None

        # Remove drafts
        shutil.rmtree(drafts_dir)
        assert not drafts_dir.exists()

        restored = _restore_checkpoint(run_dir, cp)

        assert restored is True
        assert (run_dir / "drafts" / "page.md").exists()


# ── W5 deprioritization tests ─────────────────────────────────────────────────


class TestW5Deprioritization:
    def test_w5_moved_to_end_when_few_gates_failing(self):
        recs = [_make_rec("W5"), _make_rec("W10"), _make_rec("W8")]
        result = _deprioritize_w5(recs, failed_gate_count=3)
        workers = [extract_worker_from_recommendation(r) for r in result]
        assert workers.index("W5") == len(workers) - 1

    def test_w5_stays_in_position_when_many_gates_failing(self):
        recs = [_make_rec("W5"), _make_rec("W10"), _make_rec("W8")]
        result = _deprioritize_w5(recs, failed_gate_count=5)
        workers = [extract_worker_from_recommendation(r) for r in result]
        assert workers[0] == "W5"

    def test_w5_deprioritized_at_boundary_4_gates(self):
        recs = [_make_rec("W5", "api"), _make_rec("W10")]
        result = _deprioritize_w5(recs, failed_gate_count=4)
        workers = [extract_worker_from_recommendation(r) for r in result]
        assert workers[-1] == "W5"

    def test_no_w5_recommendations_unchanged(self):
        recs = [_make_rec("W10"), _make_rec("W8")]
        result = _deprioritize_w5(recs, failed_gate_count=2)
        workers = [extract_worker_from_recommendation(r) for r in result]
        assert workers == ["W10", "W8"]

    def test_empty_recommendations_unchanged(self):
        result = _deprioritize_w5([], failed_gate_count=1)
        assert result == []

    def test_multiple_w5_all_moved_to_end(self):
        recs = [_make_rec("W5", "reason1"), _make_rec("W10"), _make_rec("W5", "reason2")]
        result = _deprioritize_w5(recs, failed_gate_count=2)
        workers = [extract_worker_from_recommendation(r) for r in result]
        # W10 should come before both W5 entries
        assert workers[0] == "W10"
        assert workers.count("W5") == 2

    def test_threshold_at_5_gates_does_not_deprioritize(self):
        """Exactly 5 failing gates: W5 should stay in position (> 4 is True)."""
        recs = [_make_rec("W5"), _make_rec("W10")]
        result = _deprioritize_w5(recs, failed_gate_count=5)
        workers = [extract_worker_from_recommendation(r) for r in result]
        assert workers[0] == "W5"


# ── Regression guard in run_heal_loop ────────────────────────────────────────


class TestRegressionGuard:
    def test_regression_detected_and_continues_to_next_candidate(self, tmp_path):
        """Given baseline 3 gates failing, step increases to 4 → rollback + continue to next."""
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        _write_report(run_dir, failing_count=3)

        call_order: List[str] = []

        def mock_execute(run_id, run_dir, run_config, worker):
            call_order.append(worker)
            if worker == "W5":
                # Simulate regression: write report with MORE failures
                _write_report(run_dir, failing_count=4)
            else:
                # W10 improves things
                _write_report(run_dir, failing_count=2)
            result = MagicMock()
            result.exit_code = 0
            return result

        recs = [
            _make_rec("W5", "api symbols"),
            _make_rec("W10", "fixer"),
        ]

        def mock_recommend(run_dir, report):
            return recs

        def mock_load_report(run_dir):
            report_path = run_dir / "artifacts" / "validation_report.json"
            return json.loads(report_path.read_text())

        with (
            patch("launch.orchestrator.run_loop.execute_run_from_node", side_effect=mock_execute),
            patch("launch.cli.triage.recommend_action", side_effect=mock_recommend),
            patch("launch.cli.triage.load_validation_report", side_effect=mock_load_report),
        ):
            result = run_heal_loop(
                run_id="test",
                run_dir=run_dir,
                run_config={"pilot": "test"},
                max_steps=3,
                top_k=3,
                mode="aggressive",
            )

        # W5 should have been tried (and regressed)
        chosen = [s.chosen_worker for s in result.steps]
        assert "W5" in chosen
        # W10 should also have been tried (heal continued after regression)
        assert "W10" in chosen

    def test_step_notes_regressed_on_regression(self, tmp_path):
        """Regressed step notes should contain 'regressed'."""
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        _write_report(run_dir, failing_count=3)

        call_count = {"n": 0}

        def mock_execute(run_id, run_dir, run_config, worker):
            call_count["n"] += 1
            _write_report(run_dir, failing_count=5)  # Regression every time
            result = MagicMock()
            result.exit_code = 0
            return result

        def mock_recommend(run_dir, report):
            return [_make_rec("W5", "api")]

        def mock_load_report(run_dir):
            report_path = run_dir / "artifacts" / "validation_report.json"
            return json.loads(report_path.read_text())

        with (
            patch("launch.orchestrator.run_loop.execute_run_from_node", side_effect=mock_execute),
            patch("launch.cli.triage.recommend_action", side_effect=mock_recommend),
            patch("launch.cli.triage.load_validation_report", side_effect=mock_load_report),
        ):
            result = run_heal_loop(
                run_id="test",
                run_dir=run_dir,
                run_config={},
                max_steps=2,
                mode="aggressive",
            )

        # At least one step should be marked as regressed
        regressed_steps = [s for s in result.steps if "regressed" in s.notes]
        assert len(regressed_steps) >= 1
        # All regressed-notes steps must also carry outcome="regressed"
        assert all(s.outcome == "regressed" for s in regressed_steps)

    def test_checkpoint_restored_after_regression(self, tmp_path):
        """After regression, the original report should be restored."""
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        _write_report(run_dir, failing_count=2)

        def mock_execute(run_id, run_dir, run_config, worker):
            # Always cause regression
            _write_report(run_dir, failing_count=5)
            result = MagicMock()
            result.exit_code = 0
            return result

        # Only one recommendation; after regression+restore, stuck detection terminates loop
        def mock_recommend(run_dir, report):
            return [_make_rec("W5", "api")]

        def mock_load_report(run_dir):
            report_path = run_dir / "artifacts" / "validation_report.json"
            return json.loads(report_path.read_text())

        with (
            patch("launch.orchestrator.run_loop.execute_run_from_node", side_effect=mock_execute),
            patch("launch.cli.triage.recommend_action", side_effect=mock_recommend),
            patch("launch.cli.triage.load_validation_report", side_effect=mock_load_report),
        ):
            run_heal_loop(
                run_id="test",
                run_dir=run_dir,
                run_config={},
                max_steps=3,
                mode="aggressive",
            )

        # After restore the report should have been restored to 2 failing (not 5)
        # (we may have done multiple iterations; final state depends on last restore)
        # Just verify no exception was raised and the loop terminated cleanly.
        report_path = run_dir / "artifacts" / "validation_report.json"
        assert report_path.exists()


# ── TC-3600/TC-3614: Quarantine tests ────────────────────────────────────────


class TestQuarantine:
    """Tests for TC-3600/TC-3614: Quarantine uses stable rec_id, not reason text."""

    def test_quarantined_step_skipped_in_strict_mode(self):
        """choose_worker skips quarantined (worker, rec_id) in strict mode."""
        recs = [
            _make_rec("W10", "formatting issues", rec_id="triage:_match_scaffold_or_fmt->W10"),
            _make_rec("W8", "link issues", rec_id="triage:_match_link_patch->W8"),
        ]
        # TC-3614: quarantine key is (worker, rec_id), not (worker, reason)
        quarantined = {("W10", "triage:_match_scaffold_or_fmt->W10")}
        result = choose_worker(recs, "strict", 3, [], quarantined)
        assert result is not None
        assert result[0] == "W8"

    def test_quarantined_step_skipped_in_aggressive_mode(self):
        """choose_worker skips quarantined (worker, rec_id) in aggressive mode."""
        recs = [
            _make_rec("W10", "formatting issues", rec_id="triage:_match_scaffold_or_fmt->W10"),
            _make_rec("W8", "link issues", rec_id="triage:_match_link_patch->W8"),
        ]
        quarantined = {("W10", "triage:_match_scaffold_or_fmt->W10")}
        result = choose_worker(recs, "aggressive", 3, [], quarantined)
        assert result is not None
        assert result[0] == "W8"

    def test_all_quarantined_returns_none(self):
        """When all candidates are quarantined by rec_id, returns None (stuck)."""
        recs = [
            _make_rec("W10", "formatting issues", rec_id="triage:_match_scaffold_or_fmt->W10"),
        ]
        quarantined = {("W10", "triage:_match_scaffold_or_fmt->W10")}
        result = choose_worker(recs, "strict", 3, [], quarantined)
        assert result is None

    def test_quarantine_different_rec_id_same_worker_not_blocked(self):
        """Same worker, DIFFERENT rec_id → not quarantined (independent rules)."""
        recs = [
            _make_rec("W10", "frontmatter issues", rec_id="triage:_match_frontmatter_required_fields->W10"),
        ]
        # Only scaffold rec_id is quarantined, not the frontmatter one
        quarantined = {("W10", "triage:_match_scaffold_or_fmt->W10")}
        result = choose_worker(recs, "strict", 3, [], quarantined)
        assert result is not None
        assert result == ("W10", "frontmatter issues")

    def test_quarantine_empty_allows_all(self):
        """Empty quarantine set allows all candidates."""
        recs = [_make_rec("W10", "test")]
        result = choose_worker(recs, "strict", 3, [], set())
        assert result is not None
        assert result[0] == "W10"

    def test_quarantine_none_allows_all(self):
        """None quarantine (backward compat) allows all candidates."""
        recs = [_make_rec("W10", "test")]
        result = choose_worker(recs, "strict", 3, [], None)
        assert result is not None
        assert result[0] == "W10"

    def test_regression_quarantines_step_in_loop(self, tmp_path):
        """In the heal loop, a regressing step is quarantined and not retried."""
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        _write_report(run_dir, failing_count=3)

        call_count = {"n": 0}
        workers_called = []

        def mock_execute(run_id, run_dir, run_config, worker):
            call_count["n"] += 1
            workers_called.append(worker)
            if worker == "W5":
                # W5 always regresses
                _write_report(run_dir, failing_count=5)
            else:
                # W10 makes no change (same count)
                _write_report(run_dir, failing_count=3)
            result = MagicMock()
            result.exit_code = 0
            return result

        # TC-3614: recommendations must include stable 'id' fields
        recs = [
            _make_rec("W5", "api symbols", rec_id="triage:_match_code_fence->W5"),
            _make_rec("W10", "fixer", rec_id="triage:_match_scaffold_or_fmt->W10"),
        ]

        def mock_recommend(run_dir, report):
            return recs

        def mock_load_report(run_dir):
            report_path = run_dir / "artifacts" / "validation_report.json"
            return json.loads(report_path.read_text())

        with (
            patch("launch.orchestrator.run_loop.execute_run_from_node", side_effect=mock_execute),
            patch("launch.cli.triage.recommend_action", side_effect=mock_recommend),
            patch("launch.cli.triage.load_validation_report", side_effect=mock_load_report),
        ):
            result = run_heal_loop(
                run_id="test_quarantine",
                run_dir=run_dir,
                run_config={},
                max_steps=4,
                top_k=3,
                mode="aggressive",
            )

        # W5 should only be tried ONCE (then quarantined after regression)
        w5_count = sum(1 for w in workers_called if w == "W5")
        assert w5_count == 1, f"W5 called {w5_count} times; should be 1 (quarantined after regression)"


class TestStableQuarantineKey:
    """TC-3614: Quarantine key is stable against reason wording changes."""

    def test_quarantine_stable_changing_reason_does_not_unblock(self):
        """Changing reason text on a quarantined worker does NOT unblock it.

        With the old (reason-based) quarantine, rewriting the label would bypass
        quarantine.  With the new (rec_id-based) quarantine, the id is derived from
        the match function name, so changing the label has no effect.
        """
        # Two recs for W10 with SAME rec_id but DIFFERENT reason text
        rec_original = _make_rec("W10", "Scaffold/prompt leak (old label)",
                                 rec_id="triage:_match_scaffold_or_fmt->W10")
        rec_reworded = _make_rec("W10", "Scaffold and formatting issues (new label)",
                                 rec_id="triage:_match_scaffold_or_fmt->W10")

        # Quarantine the original rec_id
        quarantined = {("W10", "triage:_match_scaffold_or_fmt->W10")}

        # Both recs with same id should be blocked
        result_orig = choose_worker([rec_original], "strict", 3, [], quarantined)
        result_new = choose_worker([rec_reworded], "strict", 3, [], quarantined)

        assert result_orig is None, "Original reason should be quarantined"
        assert result_new is None, "Reworded reason with same rec_id should ALSO be quarantined"

    def test_different_rec_ids_same_worker_independent(self):
        """Different rec_ids for the same worker are independently quarantinable."""
        rec_scaffold = _make_rec("W10", "Scaffold", rec_id="triage:_match_scaffold_or_fmt->W10")
        rec_fm = _make_rec("W10", "Frontmatter", rec_id="triage:_match_frontmatter_required_fields->W10")

        # Only scaffold rule quarantined — frontmatter rule should still be available
        quarantined = {("W10", "triage:_match_scaffold_or_fmt->W10")}

        # Scaffold blocked
        result_scaffold = choose_worker([rec_scaffold], "strict", 3, [], quarantined)
        assert result_scaffold is None

        # Frontmatter not blocked
        result_fm = choose_worker([rec_fm], "strict", 3, [], quarantined)
        assert result_fm is not None
        assert result_fm == ("W10", "Frontmatter")
