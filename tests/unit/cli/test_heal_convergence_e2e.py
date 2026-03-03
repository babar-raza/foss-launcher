"""TC-3610: Integration-level proof that launch heal correctly:

1) Targets the intended issue via _current_issue wiring (graph.py → W10)
2) Detects progress even when failed gate count stays flat (multi-issue gates)
3) Quarantines regressors to avoid thrashing

All tests are fast (mocked resume, no network, no LLM) and deterministic.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, call, patch

import pytest

from launch.cli.heal import (
    HealResult,
    HealStep,
    ReportMetrics,
    choose_worker,
    compute_report_metrics,
    count_failed_gates,
    extract_worker_from_recommendation,
    is_improvement,
    is_regression,
    run_heal_loop,
    write_heal_plan,
)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_gate(name: str, ok: bool = True) -> Dict[str, Any]:
    return {"name": name, "ok": ok}


def _make_issue(
    gate: str,
    severity: str = "error",
    error_code: str = "",
    message: str = "test issue",
    issue_id: str = "",
    path: str = "",
) -> Dict[str, Any]:
    iid = issue_id or f"{gate}_{severity}_{error_code or 'nocode'}"
    issue: Dict[str, Any] = {
        "issue_id": iid,
        "gate": gate,
        "severity": severity,
        "message": message,
        "status": "OPEN",
    }
    if error_code:
        issue["error_code"] = error_code
    if path:
        issue["path"] = path
    return issue


def _make_report(
    gates: List[Dict[str, Any]],
    issues: List[Dict[str, Any]],
    ok: bool | None = None,
) -> Dict[str, Any]:
    if ok is None:
        ok = all(g["ok"] for g in gates)
    return {
        "schema_version": "1.0",
        "ok": ok,
        "profile": "local",
        "gates": gates,
        "issues": issues,
    }


def _write_report(run_dir: Path, report: Dict[str, Any]) -> Path:
    artifacts = run_dir / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    report_path = artifacts / "validation_report.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")
    return report_path


def _make_rec(worker: str, reason: str = "test", rec_id: str = "") -> Dict[str, str]:
    """Build a triage recommendation dict with a stable id field.

    TC-3614: If rec_id is not provided, derives one deterministically from
    worker + reason so that different reasons produce different quarantine keys.
    """
    import re as _re
    slug = _re.sub(r"[^a-zA-Z0-9]+", "_", reason.lower())[:25].strip("_")
    stable_id = rec_id or f"triage:{slug}->{worker}"
    return {
        "command": f"launch resume --run-dir /tmp --from-worker {worker}",
        "reason": reason,
        "id": stable_id,
    }


def _setup_run_dir(tmp_path: Path, report: Dict[str, Any] | None = None) -> Path:
    run_dir = tmp_path / "runs" / "r_e2e"
    run_dir.mkdir(parents=True)
    (run_dir / "artifacts").mkdir()
    (run_dir / "events.ndjson").write_text("", encoding="utf-8")
    if report is not None:
        _write_report(run_dir, report)
    return run_dir


def _mock_run_result(exit_code: int = 0) -> MagicMock:
    result = MagicMock()
    result.exit_code = exit_code
    result.final_state = "DONE" if exit_code == 0 else "FAILED"
    result.run_id = "r_e2e"
    return result


# ── Fixture Reports ──────────────────────────────────────────────────────────


def _multi_issue_single_gate_report(issue_count: int = 3) -> Dict[str, Any]:
    """gate_17 fails with N formatting issues. gate_4 fails with 1 issue.

    Total: 2 failed gates, N+1 issues.
    Key property: fixing one FQ issue drops total issue count without
    changing the failed gate count (gate_17 still fails with N-1 issues).
    """
    issues = []
    for i in range(issue_count):
        code = ["FQ-1", "FQ-3", "FQ-4"][i % 3]
        issues.append(_make_issue(
            gate="gate_17_formatting_quality",
            severity="error",
            error_code=code,
            message=f"Formatting issue #{i+1}",
            issue_id=f"g17_fq_{i}",
            path=f"content/page_{i}.md",
        ))
    issues.append(_make_issue(
        gate="gate_4_frontmatter_required_fields",
        severity="error",
        error_code="FM_MISSING",
        message="Missing required frontmatter field: title",
        issue_id="g4_fm_0",
        path="content/page_0.md",
    ))
    return _make_report(
        gates=[
            _make_gate("gate_17_formatting_quality", ok=False),
            _make_gate("gate_4_frontmatter_required_fields", ok=False),
            _make_gate("gate_1_schema_validation"),
            _make_gate("gate_5_cross_page_link_validity"),
        ],
        issues=issues,
    )


def _reduced_issue_report(issue_count: int = 2) -> Dict[str, Any]:
    """Same 2 failed gates but fewer issues on gate_17.

    Simulates W10 fixing one FQ issue: gate still fails but issue count dropped.
    """
    issues = []
    for i in range(issue_count):
        code = ["FQ-1", "FQ-3", "FQ-4"][i % 3]
        issues.append(_make_issue(
            gate="gate_17_formatting_quality",
            severity="error",
            error_code=code,
            message=f"Formatting issue #{i+1}",
            issue_id=f"g17_fq_{i}",
            path=f"content/page_{i}.md",
        ))
    issues.append(_make_issue(
        gate="gate_4_frontmatter_required_fields",
        severity="error",
        error_code="FM_MISSING",
        message="Missing required frontmatter field: title",
        issue_id="g4_fm_0",
        path="content/page_0.md",
    ))
    return _make_report(
        gates=[
            _make_gate("gate_17_formatting_quality", ok=False),
            _make_gate("gate_4_frontmatter_required_fields", ok=False),
            _make_gate("gate_1_schema_validation"),
            _make_gate("gate_5_cross_page_link_validity"),
        ],
        issues=issues,
    )


def _regressed_report() -> Dict[str, Any]:
    """3 failed gates (one MORE than baseline). Simulates a regression."""
    return _make_report(
        gates=[
            _make_gate("gate_17_formatting_quality", ok=False),
            _make_gate("gate_4_frontmatter_required_fields", ok=False),
            _make_gate("gate_scaffold_leak", ok=False),  # NEW failure
            _make_gate("gate_1_schema_validation"),
        ],
        issues=[
            _make_issue("gate_17_formatting_quality", "error", "FQ-1", issue_id="g17_0"),
            _make_issue("gate_4_frontmatter_required_fields", "error", "FM_MISSING", issue_id="g4_0"),
            _make_issue("gate_scaffold_leak", "error", "SCAFFOLD_LEAK", issue_id="scaffold_0"),
        ],
    )


def _all_pass_report() -> Dict[str, Any]:
    return _make_report(
        gates=[
            _make_gate("gate_17_formatting_quality"),
            _make_gate("gate_4_frontmatter_required_fields"),
            _make_gate("gate_1_schema_validation"),
            _make_gate("gate_5_cross_page_link_validity"),
        ],
        issues=[],
    )


# ══════════════════════════════════════════════════════════════════════════════
# BEHAVIOR A: current_issue honored — W10 fixes the orchestrator-selected issue
# ══════════════════════════════════════════════════════════════════════════════


class TestCurrentIssueTargeting:
    """Prove that fix_node() injects _current_issue into run_config and
    W10's execute_fixer() reads it to select the correct issue."""

    def test_fix_node_injects_current_issue_into_run_config(self):
        """fix_node() should shallow-copy run_config and inject _current_issue."""
        from launch.orchestrator.graph import fix_node

        target_issue = {"issue_id": "g17_fq_0", "gate": "gate_17", "severity": "error"}

        captured_run_config: List[Dict[str, Any]] = []

        class FakeInvoker:
            def invoke_worker(self, worker, inputs, outputs, run_config):
                captured_run_config.append(dict(run_config))

        state: Dict[str, Any] = {
            "run_id": "r_test",
            "run_dir": Path("/fake"),
            "run_config": {"product_slug": "test"},
            "run_state": "VALIDATING",
            "fix_attempts": 0,
            "current_issue": target_issue,
        }

        with patch("launch.orchestrator.graph._create_worker_invoker", return_value=FakeInvoker()):
            fix_node(state)

        assert len(captured_run_config) == 1
        injected = captured_run_config[0]
        assert "_current_issue" in injected
        assert injected["_current_issue"]["issue_id"] == "g17_fq_0"
        # Original run_config must NOT be mutated
        assert "_current_issue" not in state["run_config"]

    def test_fix_node_no_current_issue_does_not_inject(self):
        """When current_issue is None, _current_issue should not be in run_config."""
        from launch.orchestrator.graph import fix_node

        captured_run_config: List[Dict[str, Any]] = []

        class FakeInvoker:
            def invoke_worker(self, worker, inputs, outputs, run_config):
                captured_run_config.append(dict(run_config))

        state: Dict[str, Any] = {
            "run_id": "r_test",
            "run_dir": Path("/fake"),
            "run_config": {"product_slug": "test"},
            "run_state": "VALIDATING",
            "fix_attempts": 0,
            "current_issue": None,
        }

        with patch("launch.orchestrator.graph._create_worker_invoker", return_value=FakeInvoker()):
            fix_node(state)

        assert len(captured_run_config) == 1
        assert "_current_issue" not in captured_run_config[0]

    def test_execute_fixer_reads_current_issue_from_run_config(self, tmp_path):
        """execute_fixer() falls back to run_config['_current_issue'] when
        current_issue kwarg is None."""
        from launch.workers.w10_fixer.worker import select_issue_to_fix

        target_issue = {"issue_id": "g17_fq_0", "gate": "gate_17", "severity": "error"}
        report = _multi_issue_single_gate_report(issue_count=3)

        # select_issue_to_fix should return the targeted issue
        selected = select_issue_to_fix(report, current_issue=target_issue)
        assert selected is not None
        assert selected["issue_id"] == "g17_fq_0"

    def test_select_issue_to_fix_raises_on_missing_issue_id(self):
        """select_issue_to_fix() raises FixerIssueNotFoundError for unknown ID."""
        from launch.workers.w10_fixer.worker import (
            FixerIssueNotFoundError,
            select_issue_to_fix,
        )

        bogus_issue = {"issue_id": "nonexistent_123", "gate": "gate_17", "severity": "error"}
        report = _multi_issue_single_gate_report(issue_count=2)

        with pytest.raises(FixerIssueNotFoundError, match="nonexistent_123"):
            select_issue_to_fix(report, current_issue=bogus_issue)


# ══════════════════════════════════════════════════════════════════════════════
# BEHAVIOR B: progress without gate flip — issue count drops, gate count stays
# ══════════════════════════════════════════════════════════════════════════════


class TestProgressWithoutGateFlip:
    """Prove that is_improvement() detects progress when total issue count
    drops even though failed gate count stays the same."""

    def test_metrics_detect_issue_drop_as_improvement(self):
        """Directly: same 2 failed gates, but total issues 4→3 = improvement."""
        before = ReportMetrics(
            failed_gate_ids=frozenset({"gate_17", "gate_4"}),
            failed_gate_count=2,
            open_critical_issue_count=4,
            open_total_issue_count=4,
        )
        after = ReportMetrics(
            failed_gate_ids=frozenset({"gate_17", "gate_4"}),
            failed_gate_count=2,
            open_critical_issue_count=3,
            open_total_issue_count=3,
        )
        assert is_improvement(before, after) is True
        assert is_regression(before, after) is False

    def test_metrics_flat_gate_flat_issues_is_not_improvement(self):
        """Same gates, same issue count = NOT improvement."""
        before = ReportMetrics(
            failed_gate_ids=frozenset({"gate_17", "gate_4"}),
            failed_gate_count=2,
            open_critical_issue_count=4,
            open_total_issue_count=4,
        )
        after = ReportMetrics(
            failed_gate_ids=frozenset({"gate_17", "gate_4"}),
            failed_gate_count=2,
            open_critical_issue_count=4,
            open_total_issue_count=4,
        )
        assert is_improvement(before, after) is False
        assert is_regression(before, after) is False

    def test_heal_loop_continues_on_issue_drop_without_gate_flip(self, tmp_path):
        """Full loop: gate_17 + gate_4 both fail; W10 fixes one issue (4→3)
        but both gates still fail. Heal should record improvement and continue,
        not stop as stuck."""
        baseline = _multi_issue_single_gate_report(issue_count=3)  # 4 total issues
        reduced = _reduced_issue_report(issue_count=2)  # 3 total issues

        run_dir = _setup_run_dir(tmp_path, baseline)
        call_count = {"n": 0}

        def mock_execute(run_id, rd, rc, worker):
            call_count["n"] += 1
            if call_count["n"] == 1:
                # Step 0: W10 fixes one FQ issue (4→3 issues, still 2 failed gates)
                _write_report(rd, reduced)
            else:
                # Step 1: W10 fixes remaining issues → all pass
                _write_report(rd, _all_pass_report())
            return _mock_run_result(0)

        recs = [
            _make_rec("W10", "Scaffold/prompt leak or formatting issues (W10 auto-fixable)"),
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
                run_id="r_e2e",
                run_dir=run_dir,
                run_config={"pilot": "test"},
                max_steps=5,
                mode="strict",
            )

        # Must have taken 2 steps (not stopped at 1 as "stuck")
        assert len(result.steps) == 2, (
            f"Expected 2 steps but got {len(result.steps)}: "
            f"stop_reason={result.stop_reason}"
        )
        assert result.stop_reason == "all_gates_pass"
        assert result.final_failed_gate_count == 0

        # Step 0: failed gates unchanged (2→2) but issues dropped (4→3)
        step0 = result.steps[0]
        assert step0.failed_gate_count_before == 2
        assert step0.failed_gate_count_after == 2
        # Step was NOT marked as regressed
        assert "regressed" not in step0.notes

    def test_compute_report_metrics_counts_correctly(self):
        """compute_report_metrics extracts correct counts from report dict."""
        report = _multi_issue_single_gate_report(issue_count=3)
        m = compute_report_metrics(report)
        assert m.failed_gate_count == 2
        assert m.failed_gate_ids == frozenset({
            "gate_17_formatting_quality",
            "gate_4_frontmatter_required_fields",
        })
        assert m.open_total_issue_count == 4  # 3 FQ + 1 FM
        assert m.open_critical_issue_count == 4  # all are "error" severity


# ══════════════════════════════════════════════════════════════════════════════
# BEHAVIOR C: quarantine prevents thrash — regressor skipped on re-try
# ══════════════════════════════════════════════════════════════════════════════


class TestQuarantinePreventsTrash:
    """Prove that after a regression, the (worker, reason) pair is quarantined
    and choose_worker() skips it in subsequent iterations."""

    def test_regression_adds_to_quarantine_and_skips(self, tmp_path):
        """Full loop scenario:
        - Step 0: W10/formatting regresses → quarantined + rolled back
        - Step 1: W10/frontmatter is tried (different reason, not quarantined)
        - W10/formatting is NEVER retried
        """
        baseline = _multi_issue_single_gate_report(issue_count=3)
        run_dir = _setup_run_dir(tmp_path, baseline)

        workers_and_reasons: List[tuple] = []

        def mock_execute(run_id, rd, rc, worker):
            # Determine reason from call order
            reason = "unknown"
            if len(workers_and_reasons) == 0:
                reason = "Scaffold/prompt leak or formatting issues (W10 auto-fixable)"
            elif len(workers_and_reasons) == 1:
                reason = "Frontmatter required fields missing (W10 auto-fixable)"
            workers_and_reasons.append((worker, reason))

            if len(workers_and_reasons) == 1:
                # Step 0: W10/formatting causes regression (new gate appears)
                _write_report(rd, _regressed_report())
            else:
                # Step 1+: W10/frontmatter fixes everything
                _write_report(rd, _all_pass_report())
            return _mock_run_result(0)

        # Two different W10 recommendations with different reasons
        recs = [
            _make_rec("W10", "Scaffold/prompt leak or formatting issues (W10 auto-fixable)"),
            _make_rec("W10", "Frontmatter required fields missing (W10 auto-fixable)"),
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
                run_id="r_quarantine",
                run_dir=run_dir,
                run_config={"pilot": "test"},
                max_steps=4,
                top_k=3,
                mode="aggressive",
            )

        # Step 0 must be marked as regressed
        assert len(result.steps) >= 2
        step0 = result.steps[0]
        assert "regressed" in step0.notes
        assert step0.outcome == "regressed"

        # The formatting reason should appear exactly ONCE (quarantined after regression)
        formatting_steps = [
            s for s in result.steps
            if s.reason == "Scaffold/prompt leak or formatting issues (W10 auto-fixable)"
        ]
        assert len(formatting_steps) == 1, (
            f"Formatting reason tried {len(formatting_steps)} times; "
            "expected 1 (quarantined after regression)"
        )

    def test_all_candidates_quarantined_stops_loop(self, tmp_path):
        """When all recommendations are quarantined, loop stops with 'stuck'."""
        baseline = _multi_issue_single_gate_report(issue_count=2)
        run_dir = _setup_run_dir(tmp_path, baseline)

        def mock_execute(run_id, rd, rc, worker):
            # Always regress
            _write_report(rd, _regressed_report())
            return _mock_run_result(0)

        # Only one recommendation — once quarantined, nothing left
        recs = [
            _make_rec("W10", "formatting fix"),
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
                run_id="r_all_quarantined",
                run_dir=run_dir,
                run_config={},
                max_steps=4,
                mode="aggressive",
            )

        # Loop must stop (stuck or no viable choice)
        assert result.stop_reason in ("stuck", "no_recommendation"), (
            f"Expected stuck/no_recommendation but got {result.stop_reason}"
        )
        # W10/formatting tried exactly once
        w10_formatting = [
            s for s in result.steps
            if s.chosen_worker == "W10" and s.reason == "formatting fix"
        ]
        assert len(w10_formatting) == 1

    def test_quarantine_does_not_block_different_reason(self):
        """Quarantine is (worker, rec_id)-specific — same worker, different rec_id is eligible.

        TC-3614: Quarantine key is (worker, rec_id), NOT (worker, reason).
        Only the quarantined rec_id is blocked; other rec_ids for the same worker remain eligible.
        """
        recs = [
            _make_rec("W10", "formatting issues"),
            _make_rec("W10", "frontmatter issues"),
        ]
        # TC-3614: quarantine key uses the stable rec_id, not the reason text
        quarantined = {("W10", recs[0]["id"])}  # quarantine formatting rec_id only
        result = choose_worker(recs, "aggressive", 3, [], quarantined)
        assert result is not None
        assert result == ("W10", "frontmatter issues")


# ══════════════════════════════════════════════════════════════════════════════
# COMBINED E2E: Full scenario exercising all 3 behaviors in one sequence
# ══════════════════════════════════════════════════════════════════════════════


class TestCombinedConvergence:
    """End-to-end scenario that exercises all three behaviors in one heal run:
    1. Step 0: W10/formatting regresses → quarantine + rollback
    2. Step 1: W10/frontmatter fixes 1 issue (4→3) without gate flip → improvement
    3. Step 2: W10/frontmatter fixes remaining → all pass
    """

    def test_full_convergence_scenario(self, tmp_path):
        baseline = _multi_issue_single_gate_report(issue_count=3)  # 2 gates, 4 issues
        reduced = _reduced_issue_report(issue_count=2)  # 2 gates, 3 issues
        run_dir = _setup_run_dir(tmp_path, baseline)

        execute_count = {"n": 0}

        def mock_execute(run_id, rd, rc, worker):
            execute_count["n"] += 1
            n = execute_count["n"]
            if n == 1:
                # Step 0: W10/formatting causes regression (3 gates instead of 2)
                _write_report(rd, _regressed_report())
            elif n == 2:
                # Step 1: W10/frontmatter fixes one issue (still 2 gates, but 3 issues)
                _write_report(rd, reduced)
            else:
                # Step 2: W10/frontmatter fixes everything
                _write_report(rd, _all_pass_report())
            return _mock_run_result(0)

        recs = [
            _make_rec("W10", "Scaffold/prompt leak or formatting issues (W10 auto-fixable)"),
            _make_rec("W10", "Frontmatter required fields missing (W10 auto-fixable)"),
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
                run_id="r_combined",
                run_dir=run_dir,
                run_config={"pilot": "test"},
                max_steps=5,
                top_k=3,
                mode="aggressive",
            )

        # ── Assertions ──

        # Must reach all_gates_pass
        assert result.stop_reason == "all_gates_pass"
        assert result.final_failed_gate_count == 0

        # Must have 3 steps total
        assert len(result.steps) == 3, (
            f"Expected 3 steps but got {len(result.steps)}: "
            f"{[(s.chosen_worker, s.reason, s.notes) for s in result.steps]}"
        )

        # Step 0: Regression — quarantined + rolled back
        step0 = result.steps[0]
        assert step0.chosen_worker == "W10"
        assert "formatting" in step0.reason.lower()
        assert "regressed" in step0.notes
        assert step0.outcome == "regressed"

        # Step 1: Progress without gate flip — issue count dropped
        step1 = result.steps[1]
        assert step1.chosen_worker == "W10"
        assert "frontmatter" in step1.reason.lower()
        assert step1.failed_gate_count_before == 2
        assert step1.failed_gate_count_after == 2  # gates unchanged
        assert "regressed" not in step1.notes  # NOT a regression
        assert step1.outcome == "improved"

        # Step 2: All gates pass
        step2 = result.steps[2]
        assert step2.failed_gate_count_after == 0

        # Quarantine proof: formatting reason tried only once
        formatting_count = sum(
            1 for s in result.steps
            if "formatting" in s.reason.lower()
        )
        assert formatting_count == 1

        # heal_plan.json must exist
        plan_path = run_dir / "artifacts" / "heal_plan.json"
        assert plan_path.exists()
        plan = json.loads(plan_path.read_text())
        assert plan["stop_reason"] == "all_gates_pass"
        assert len(plan["steps"]) == 3

        # events.ndjson must have entries
        events_path = run_dir / "events.ndjson"
        events_text = events_path.read_text()
        assert "HEAL_STEP_STARTED" in events_text
        assert "HEAL_STEP_COMPLETED" in events_text
        assert "HEAL_STEP_REGRESSED" in events_text
        assert "HEAL_STOPPED" in events_text
