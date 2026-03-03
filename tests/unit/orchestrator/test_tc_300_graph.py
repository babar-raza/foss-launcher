"""Unit tests for TC-300: Orchestrator graph wiring.

Tests:
- Graph construction and node connectivity
- State transitions
- Conditional routing (validation -> fix/ready_for_pr/failed)
- Stop-the-line behavior on blockers

Spec references:
- specs/11_state_and_events.md (State model)
- specs/28_coordination_and_handoffs.md (Loop policy)
"""

import json
from unittest.mock import patch, MagicMock

import pytest

from launch.orchestrator.graph import (
    DRIVE_GOAL_DRAFT,
    DRIVE_GOAL_KEY,
    DRIVE_GOAL_PR,
    DRIVE_GOAL_VALIDATE,
    OrchestratorState,
    build_orchestrator_graph,
    decide_after_validation,
    _is_review_required,
    review_content_node,
    decide_after_review,
    RUN_STATE_FAILED,
)


def test_build_graph_succeeds():
    """Test that orchestrator graph builds without errors."""
    graph = build_orchestrator_graph()
    assert graph is not None

    # Compile to ensure no structural errors
    compiled = graph.compile()
    assert compiled is not None


def test_initial_state_structure():
    """Test that initial state has required fields."""
    state: OrchestratorState = {
        "run_id": "test_run_001",
        "run_state": "CREATED",
        "run_dir": "/tmp/runs/test_run_001",
        "run_config": {"max_fix_attempts": 3},
        "snapshot": {},
        "issues": [],
        "fix_attempts": 0,
        "current_issue": None,
    }

    assert state["run_id"] == "test_run_001"
    assert state["run_state"] == "CREATED"
    assert state["fix_attempts"] == 0


def test_decide_after_validation_no_issues():
    """Test validation decision when no issues exist (happy path)."""
    state: OrchestratorState = {
        "run_id": "test_run",
        "run_state": "VALIDATING",
        "run_dir": "/tmp/runs/test_run",
        "run_config": {"max_fix_attempts": 3},
        "snapshot": {},
        "issues": [],  # No issues
        "fix_attempts": 0,
        "current_issue": None,
    }

    decision = decide_after_validation(state)
    assert decision == "ready_for_pr"


def test_decide_after_validation_with_blocker():
    """Test validation decision when blocker issues exist."""
    state: OrchestratorState = {
        "run_id": "test_run",
        "run_state": "VALIDATING",
        "run_dir": "/tmp/runs/test_run",
        "run_config": {"max_fix_attempts": 3},
        "snapshot": {},
        "issues": [
            {"issue_id": "issue-001", "severity": "blocker", "message": "Test blocker"}
        ],
        "fix_attempts": 0,
        "current_issue": None,
    }

    decision = decide_after_validation(state)
    assert decision == "fix"
    assert state["current_issue"]["issue_id"] == "issue-001"


def test_decide_after_validation_max_attempts_exceeded():
    """Test validation decision when fix attempts exhausted."""
    state: OrchestratorState = {
        "run_id": "test_run",
        "run_state": "VALIDATING",
        "run_dir": "/tmp/runs/test_run",
        "run_config": {"max_fix_attempts": 3},
        "snapshot": {},
        "issues": [
            {"issue_id": "issue-001", "severity": "blocker", "message": "Test blocker"}
        ],
        "fix_attempts": 3,  # Exhausted
        "current_issue": None,
    }

    decision = decide_after_validation(state)
    assert decision == "failed"


def test_decide_after_validation_deterministic_ordering():
    """Test that first blocker is always selected (deterministic)."""
    state: OrchestratorState = {
        "run_id": "test_run",
        "run_state": "VALIDATING",
        "run_dir": "/tmp/runs/test_run",
        "run_config": {"max_fix_attempts": 3},
        "snapshot": {},
        "issues": [
            {"issue_id": "issue-001", "severity": "blocker", "message": "First blocker"},
            {"issue_id": "issue-002", "severity": "blocker", "message": "Second blocker"},
        ],
        "fix_attempts": 0,
        "current_issue": None,
    }

    decision = decide_after_validation(state)
    assert decision == "fix"
    # Should select first blocker (deterministic ordering)
    assert state["current_issue"]["issue_id"] == "issue-001"


def test_decide_after_validation_with_error_severity():
    """Test validation decision routes to 'fix' when issues have severity 'error'."""
    state: OrchestratorState = {
        "run_id": "test_run",
        "run_state": "VALIDATING",
        "run_dir": "/tmp/runs/test_run",
        "run_config": {"max_fix_attempts": 3},
        "snapshot": {},
        "issues": [
            {"issue_id": "issue-010", "severity": "error", "message": "Gate 17 formatting error"}
        ],
        "fix_attempts": 0,
        "current_issue": None,
    }

    decision = decide_after_validation(state)
    assert decision == "fix"
    assert state["current_issue"]["issue_id"] == "issue-010"


def test_decide_after_validation_warn_only_ready_for_pr():
    """Test validation decision returns 'ready_for_pr' when only warn issues remain."""
    state: OrchestratorState = {
        "run_id": "test_run",
        "run_state": "VALIDATING",
        "run_dir": "/tmp/runs/test_run",
        "run_config": {"max_fix_attempts": 3},
        "snapshot": {},
        "issues": [
            {"issue_id": "issue-020", "severity": "warn", "message": "Minor style warning"},
            {"issue_id": "issue-021", "severity": "warn", "message": "Another warning"},
        ],
        "fix_attempts": 0,
        "current_issue": None,
    }

    decision = decide_after_validation(state)
    assert decision == "ready_for_pr"


def test_decide_after_validation_mixed_error_and_warn():
    """Test that error issues trigger 'fix' even when warn issues also present."""
    state: OrchestratorState = {
        "run_id": "test_run",
        "run_state": "VALIDATING",
        "run_dir": "/tmp/runs/test_run",
        "run_config": {"max_fix_attempts": 3},
        "snapshot": {},
        "issues": [
            {"issue_id": "issue-030", "severity": "warn", "message": "Warning"},
            {"issue_id": "issue-031", "severity": "error", "message": "Error issue"},
            {"issue_id": "issue-032", "severity": "warn", "message": "Another warning"},
        ],
        "fix_attempts": 0,
        "current_issue": None,
    }

    decision = decide_after_validation(state)
    assert decision == "fix"
    # Should select the error issue (first fixable in list order)
    assert state["current_issue"]["issue_id"] == "issue-031"


def test_decide_after_validation_selects_first_fixable_in_list_order():
    """Both blocker and error are fixable; first in list order is selected."""
    state: OrchestratorState = {
        "run_id": "test_run",
        "run_state": "VALIDATING",
        "run_dir": "/tmp/runs/test_run",
        "run_config": {"max_fix_attempts": 3},
        "snapshot": {},
        "issues": [
            {"issue_id": "issue-040", "severity": "error", "message": "Error issue"},
            {"issue_id": "issue-041", "severity": "blocker", "message": "Blocker issue"},
        ],
        "fix_attempts": 0,
        "current_issue": None,
    }

    decision = decide_after_validation(state)
    assert decision == "fix"
    # Both error and blocker are fixable; function picks first in list order.
    # (W9 sorts blockers before errors, so in practice blockers come first.)
    assert state["current_issue"]["issue_id"] == "issue-040"


def test_decide_after_validation_uppercase_blocker_backward_compat():
    """TC-3630/P0: Uppercase 'BLOCKER' is normalized and still matched as fixable."""
    state: OrchestratorState = {
        "run_id": "test_run",
        "run_state": "VALIDATING",
        "run_dir": "/tmp/runs/test_run",
        "run_config": {"max_fix_attempts": 3},
        "snapshot": {},
        "issues": [
            {"issue_id": "issue-compat", "severity": "BLOCKER", "message": "Legacy uppercase"}
        ],
        "fix_attempts": 0,
        "current_issue": None,
    }
    decision = decide_after_validation(state)
    assert decision == "fix"
    assert state["current_issue"]["issue_id"] == "issue-compat"


def test_graph_execution_smoke_test():
    """Smoke test: execute graph with stub workers (no actual work)."""
    mock_invoker = MagicMock()
    mock_invoker.invoke_worker.return_value = {}

    with patch("launch.orchestrator.graph._create_worker_invoker", return_value=mock_invoker):
        graph = build_orchestrator_graph()
        compiled = graph.compile()

        initial_state: OrchestratorState = {
            "run_id": "smoke_test",
            "run_state": "CREATED",
            "run_dir": "/tmp/runs/smoke_test",
            "run_config": {"max_fix_attempts": 3, "review_enabled": False},
            "snapshot": {},
            "issues": [],  # No issues, should go straight to PR
            "fix_attempts": 0,
            "current_issue": None,
        }

        # Execute graph (should complete without errors)
        final_state = None
        for state_update in compiled.stream(initial_state):
            for node_name, node_output in state_update.items():
                final_state = node_output

    # Verify final state reached DONE
    assert final_state is not None
    assert final_state["run_state"] == "DONE"


def test_graph_execution_with_fix_loop():
    """Test graph execution with validation failure and fix loop."""
    mock_invoker = MagicMock()
    mock_invoker.invoke_worker.return_value = {}

    with patch("launch.orchestrator.graph._create_worker_invoker", return_value=mock_invoker):
        graph = build_orchestrator_graph()
        compiled = graph.compile()

        initial_state: OrchestratorState = {
            "run_id": "fix_loop_test",
            "run_state": "CREATED",
            "run_dir": "/tmp/runs/fix_loop_test",
            "run_config": {"max_fix_attempts": 3, "review_enabled": False},
            "snapshot": {},
            "issues": [
                {"issue_id": "issue-001", "severity": "blocker", "message": "Test blocker"}
            ],
            "fix_attempts": 0,
            "current_issue": None,
        }

        # Execute graph (should attempt fix and eventually fail due to stub workers)
        final_state = None
        state_history = []
        for state_update in compiled.stream(initial_state):
            for node_name, node_output in state_update.items():
                final_state = node_output
                state_history.append(node_output["run_state"])

    # Verify fix was attempted
    assert "FIXING" in state_history
    # Verify final state is FAILED (stub fix doesn't resolve issues)
    assert final_state["run_state"] == "FAILED"


# ── TC-3080: Goal-aware routing tests ────────────────────────────────────────


def _make_state(
    issues=None, fix_attempts=0, _drive_goal=None, run_state="VALIDATING",
):
    """Build minimal OrchestratorState for decide_after_validation tests."""
    rc = {"max_fix_attempts": 3}
    if _drive_goal is not None:
        rc[DRIVE_GOAL_KEY] = _drive_goal
    state: OrchestratorState = {
        "run_id": "test_run",
        "run_state": run_state,
        "run_dir": "/tmp/runs/test_run",
        "run_config": rc,
        "snapshot": {},
        "issues": issues if issues is not None else [],
        "fix_attempts": fix_attempts,
        "current_issue": None,
    }
    return state


_BLOCKER_ISSUE = {"issue_id": "blk-1", "severity": "blocker", "message": "blocker"}
_WARN_ISSUE = {"issue_id": "wrn-1", "severity": "warn", "message": "warning"}


def test_goal_validate_stops_with_blockers():
    """goal=validate always returns 'stop', even with fixable issues."""
    state = _make_state(issues=[_BLOCKER_ISSUE], _drive_goal=DRIVE_GOAL_VALIDATE)
    assert decide_after_validation(state) == "stop"


def test_goal_validate_stops_no_issues():
    """goal=validate returns 'stop' even when all gates pass."""
    state = _make_state(issues=[], _drive_goal=DRIVE_GOAL_VALIDATE)
    assert decide_after_validation(state) == "stop"


def test_goal_draft_no_issues_stops():
    """goal=draft with no issues returns 'stop' (no PR)."""
    state = _make_state(issues=[], _drive_goal=DRIVE_GOAL_DRAFT)
    assert decide_after_validation(state) == "stop"


def test_goal_draft_fixable_returns_fix():
    """goal=draft with fixable issues still enters fix loop."""
    state = _make_state(issues=[_BLOCKER_ISSUE], fix_attempts=0, _drive_goal=DRIVE_GOAL_DRAFT)
    assert decide_after_validation(state) == "fix"
    assert state["current_issue"]["issue_id"] == "blk-1"


def test_goal_draft_exhausted_returns_failed():
    """goal=draft with exhausted fix attempts returns 'failed' (exit 2)."""
    state = _make_state(issues=[_BLOCKER_ISSUE], fix_attempts=3, _drive_goal=DRIVE_GOAL_DRAFT)
    assert decide_after_validation(state) == "failed"


def test_goal_draft_warnings_only_stops():
    """goal=draft with only warnings returns 'stop' (no PR)."""
    state = _make_state(issues=[_WARN_ISSUE], _drive_goal=DRIVE_GOAL_DRAFT)
    assert decide_after_validation(state) == "stop"


def test_goal_pr_no_issues_ready_for_pr():
    """goal=pr with no issues behaves identically to no goal."""
    state = _make_state(issues=[], _drive_goal=DRIVE_GOAL_PR)
    assert decide_after_validation(state) == "ready_for_pr"


def test_no_drive_goal_unchanged():
    """No _drive_goal (launch run/resume) preserves existing behavior."""
    state = _make_state(issues=[])
    assert decide_after_validation(state) == "ready_for_pr"


# ── TC-3600: fix_node injects _current_issue into run_config ─────────────


def test_fix_node_passes_current_issue_to_w10():
    """TC-3600: fix_node injects _current_issue into the run_config passed to W10."""
    from launch.orchestrator.graph import fix_node

    captured_run_configs = []
    mock_invoker = MagicMock()

    def _capture_invoke(**kwargs):
        captured_run_configs.append(kwargs.get("run_config", {}))
        return {}

    mock_invoker.invoke_worker.side_effect = _capture_invoke

    test_issue = {"issue_id": "issue-42", "severity": "blocker", "gate": "gate_4"}
    state: OrchestratorState = {
        "run_id": "tc3600_test",
        "run_state": "VALIDATING",
        "run_dir": "/tmp/runs/tc3600_test",
        "run_config": {"max_fix_attempts": 3},
        "snapshot": {},
        "issues": [test_issue],
        "fix_attempts": 0,
        "current_issue": test_issue,
        "redraft_attempts": 0,
        "seo_degraded": False,
        "degraded_pages": [],
        "abort_pages": [],
    }

    with patch("launch.orchestrator.graph._create_worker_invoker", return_value=mock_invoker):
        fix_node(state)

    assert len(captured_run_configs) == 1
    assert captured_run_configs[0].get("_current_issue") == test_issue


def test_fix_node_no_current_issue_omits_key():
    """TC-3600: fix_node does not inject _current_issue when state has no current_issue."""
    from launch.orchestrator.graph import fix_node

    captured_run_configs = []
    mock_invoker = MagicMock()

    def _capture_invoke(**kwargs):
        captured_run_configs.append(kwargs.get("run_config", {}))
        return {}

    mock_invoker.invoke_worker.side_effect = _capture_invoke

    state: OrchestratorState = {
        "run_id": "tc3600_test_none",
        "run_state": "VALIDATING",
        "run_dir": "/tmp/runs/tc3600_test_none",
        "run_config": {"max_fix_attempts": 3},
        "snapshot": {},
        "issues": [],
        "fix_attempts": 0,
        "current_issue": None,
        "redraft_attempts": 0,
        "seo_degraded": False,
        "degraded_pages": [],
        "abort_pages": [],
    }

    with patch("launch.orchestrator.graph._create_worker_invoker", return_value=mock_invoker):
        fix_node(state)

    assert len(captured_run_configs) == 1
    assert "_current_issue" not in captured_run_configs[0]


def test_fix_node_does_not_mutate_original_run_config():
    """TC-3600: fix_node shallow-copies run_config; original is not mutated."""
    from launch.orchestrator.graph import fix_node

    mock_invoker = MagicMock()
    mock_invoker.invoke_worker.return_value = {}

    original_config = {"max_fix_attempts": 3}
    test_issue = {"issue_id": "issue-99", "severity": "error", "gate": "gate_17"}
    state: OrchestratorState = {
        "run_id": "tc3600_test_nomut",
        "run_state": "VALIDATING",
        "run_dir": "/tmp/runs/tc3600_test_nomut",
        "run_config": original_config,
        "snapshot": {},
        "issues": [test_issue],
        "fix_attempts": 0,
        "current_issue": test_issue,
        "redraft_attempts": 0,
        "seo_degraded": False,
        "degraded_pages": [],
        "abort_pages": [],
    }

    with patch("launch.orchestrator.graph._create_worker_invoker", return_value=mock_invoker):
        fix_node(state)

    # Original run_config should NOT have _current_issue
    assert "_current_issue" not in original_config


# ── TC-3630/P1: fix_node disk-recovery for resume-at-W10 ──────────────────


def test_fix_node_recovers_current_issue_from_disk(tmp_path):
    """TC-3630/P1: fix_node loads current_issue from validation_report.json when state has None."""
    from launch.orchestrator.graph import fix_node

    # Write a validation_report.json with mixed-severity issues
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()
    report = {
        "issues": [
            {"issue_id": "warn-1", "severity": "warn", "message": "just a warning",
             "status": "OPEN", "gate": "gate_1"},
            {"issue_id": "blk-1", "severity": "blocker", "message": "a blocker",
             "status": "OPEN", "gate": "gate_4", "error_code": "GATE_4_MISSING"},
            {"issue_id": "err-1", "severity": "error", "message": "an error",
             "status": "OPEN", "gate": "gate_17", "error_code": "G17_FQ1"},
        ]
    }
    (artifacts_dir / "validation_report.json").write_text(
        json.dumps(report), encoding="utf-8"
    )

    captured_run_configs = []
    mock_invoker = MagicMock()

    def _capture_invoke(**kwargs):
        captured_run_configs.append(kwargs.get("run_config", {}))
        return {}

    mock_invoker.invoke_worker.side_effect = _capture_invoke

    state: OrchestratorState = {
        "run_id": "p1_test",
        "run_state": "VALIDATING",
        "run_dir": str(tmp_path),
        "run_config": {"max_fix_attempts": 3},
        "snapshot": {},
        "issues": [],
        "fix_attempts": 0,
        "current_issue": None,
        "redraft_attempts": 0,
        "seo_degraded": False,
        "degraded_pages": [],
        "abort_pages": [],
    }

    with patch("launch.orchestrator.graph._create_worker_invoker", return_value=mock_invoker):
        fix_node(state)

    # Should have recovered blk-1 (first fixable issue in list order after warn)
    assert len(captured_run_configs) == 1
    injected = captured_run_configs[0].get("_current_issue")
    assert injected is not None
    assert injected["issue_id"] == "blk-1"
    # State should also be updated
    assert state["current_issue"]["issue_id"] == "blk-1"


def test_fix_node_no_report_on_disk_proceeds_gracefully(tmp_path):
    """TC-3630/P1: fix_node proceeds without injection when no validation_report.json exists."""
    from launch.orchestrator.graph import fix_node

    captured_run_configs = []
    mock_invoker = MagicMock()

    def _capture_invoke(**kwargs):
        captured_run_configs.append(kwargs.get("run_config", {}))
        return {}

    mock_invoker.invoke_worker.side_effect = _capture_invoke

    state: OrchestratorState = {
        "run_id": "p1_no_report",
        "run_state": "VALIDATING",
        "run_dir": str(tmp_path),
        "run_config": {"max_fix_attempts": 3},
        "snapshot": {},
        "issues": [],
        "fix_attempts": 0,
        "current_issue": None,
        "redraft_attempts": 0,
        "seo_degraded": False,
        "degraded_pages": [],
        "abort_pages": [],
    }

    with patch("launch.orchestrator.graph._create_worker_invoker", return_value=mock_invoker):
        fix_node(state)

    # No injection — proceeds gracefully
    assert len(captured_run_configs) == 1
    assert "_current_issue" not in captured_run_configs[0]
    assert state["current_issue"] is None


def test_fix_node_disk_recovery_skips_when_current_issue_already_set(tmp_path):
    """TC-3630/P1: fix_node does NOT read disk when current_issue is already in state."""
    from launch.orchestrator.graph import fix_node

    # Write a report that would select blk-disk
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()
    report = {
        "issues": [
            {"issue_id": "blk-disk", "severity": "blocker", "message": "from disk",
             "status": "OPEN", "gate": "gate_4", "error_code": "GATE_4"},
        ]
    }
    (artifacts_dir / "validation_report.json").write_text(
        json.dumps(report), encoding="utf-8"
    )

    captured_run_configs = []
    mock_invoker = MagicMock()

    def _capture_invoke(**kwargs):
        captured_run_configs.append(kwargs.get("run_config", {}))
        return {}

    mock_invoker.invoke_worker.side_effect = _capture_invoke

    existing_issue = {"issue_id": "blk-state", "severity": "blocker", "gate": "gate_1"}
    state: OrchestratorState = {
        "run_id": "p1_already_set",
        "run_state": "VALIDATING",
        "run_dir": str(tmp_path),
        "run_config": {"max_fix_attempts": 3},
        "snapshot": {},
        "issues": [],
        "fix_attempts": 0,
        "current_issue": existing_issue,
        "redraft_attempts": 0,
        "seo_degraded": False,
        "degraded_pages": [],
        "abort_pages": [],
    }

    with patch("launch.orchestrator.graph._create_worker_invoker", return_value=mock_invoker):
        fix_node(state)

    # Should use the state-provided issue, NOT the disk one
    assert captured_run_configs[0]["_current_issue"]["issue_id"] == "blk-state"


# ── TC-3630/SR-03: Direct unit tests for _load_first_fixable_issue ─────────


def test_load_first_fixable_issue_corrupt_json(tmp_path):
    """SR-03/GAP-05: Helper returns None on corrupt JSON without raising."""
    from launch.orchestrator.graph import _load_first_fixable_issue

    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()
    (artifacts_dir / "validation_report.json").write_text(
        "NOT VALID JSON {{{", encoding="utf-8"
    )
    assert _load_first_fixable_issue(str(tmp_path)) is None


def test_load_first_fixable_issue_warn_only_report(tmp_path):
    """SR-03/GAP-05: Helper returns None when only warn/info issues exist."""
    from launch.orchestrator.graph import _load_first_fixable_issue

    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()
    report = {
        "issues": [
            {"issue_id": "w1", "severity": "warn", "message": "just a warning"},
            {"issue_id": "i1", "severity": "info", "message": "informational"},
        ]
    }
    (artifacts_dir / "validation_report.json").write_text(
        json.dumps(report), encoding="utf-8"
    )
    assert _load_first_fixable_issue(str(tmp_path)) is None


def test_load_first_fixable_issue_null_severity(tmp_path):
    """SR-03/GAP-05: null severity treated as non-fixable; blocker still found."""
    from launch.orchestrator.graph import _load_first_fixable_issue

    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()
    report = {
        "issues": [
            {"issue_id": "null-sev", "severity": None, "message": "null sev"},
            {"issue_id": "blk-1", "severity": "blocker", "message": "a blocker"},
        ]
    }
    (artifacts_dir / "validation_report.json").write_text(
        json.dumps(report), encoding="utf-8"
    )
    result = _load_first_fixable_issue(str(tmp_path))
    assert result is not None
    assert result["issue_id"] == "blk-1"


def test_load_first_fixable_issue_selects_first_fixable(tmp_path):
    """SR-03/GAP-04: Helper returns first fixable issue in list order."""
    from launch.orchestrator.graph import _load_first_fixable_issue

    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()
    report = {
        "issues": [
            {"issue_id": "w1", "severity": "warn", "message": "skip"},
            {"issue_id": "e1", "severity": "error", "message": "first fixable"},
            {"issue_id": "b1", "severity": "blocker", "message": "second fixable"},
        ]
    }
    (artifacts_dir / "validation_report.json").write_text(
        json.dumps(report), encoding="utf-8"
    )
    result = _load_first_fixable_issue(str(tmp_path))
    assert result is not None
    assert result["issue_id"] == "e1"


# ---------------------------------------------------------------------------
# TC-3617: _is_review_required() + review_content_node() halt behavior
# ---------------------------------------------------------------------------


class TestReviewRequired:
    """TC-3617: review_required enforcement in ci/prod profiles."""

    def test_is_review_required_explicit_true(self):
        """Explicit review_required=True overrides profile."""
        rc = {"review_required": True, "validation_profile": "local"}
        assert _is_review_required(rc) is True

    def test_is_review_required_explicit_false(self):
        """Explicit review_required=False overrides profile."""
        rc = {"review_required": False, "validation_profile": "ci"}
        assert _is_review_required(rc) is False

    def test_is_review_required_ci_profile(self):
        """Inferred from ci profile when no explicit key."""
        rc = {"validation_profile": "ci"}
        assert _is_review_required(rc) is True

    def test_is_review_required_local_profile(self):
        """Inferred from local profile when no explicit key."""
        rc = {"validation_profile": "local"}
        assert _is_review_required(rc) is False

    def test_review_required_true_w7_exception_halts(self):
        """When review_required and W7 raises, pipeline halts (FAILED state)."""
        mock_invoker = MagicMock()
        mock_invoker.invoke_worker.side_effect = RuntimeError("W7 crashed")

        state: OrchestratorState = {
            "run_id": "tc3617_halt",
            "run_state": "DRAFT_READY",
            "run_dir": "/tmp/runs/tc3617_halt",
            "run_config": {
                "review_enabled": True,
                "review_required": True,
            },
            "snapshot": {},
            "issues": [],
            "fix_attempts": 0,
            "current_issue": None,
            "redraft_attempts": 0,
            "seo_degraded": False,
            "degraded_pages": [],
            "abort_pages": [],
        }

        with patch("launch.orchestrator.graph._create_worker_invoker", return_value=mock_invoker):
            result = review_content_node(state)

        assert result["run_state"] == RUN_STATE_FAILED

    def test_review_required_false_w7_exception_continues(self):
        """When review_required=False and W7 raises, pipeline continues."""
        mock_invoker = MagicMock()
        mock_invoker.invoke_worker.side_effect = RuntimeError("W7 crashed")

        state: OrchestratorState = {
            "run_id": "tc3617_continue",
            "run_state": "DRAFT_READY",
            "run_dir": "/tmp/runs/tc3617_continue",
            "run_config": {
                "review_enabled": True,
                "review_required": False,
            },
            "snapshot": {},
            "issues": [],
            "fix_attempts": 0,
            "current_issue": None,
            "redraft_attempts": 0,
            "seo_degraded": False,
            "degraded_pages": [],
            "abort_pages": [],
        }

        with patch("launch.orchestrator.graph._create_worker_invoker", return_value=mock_invoker):
            result = review_content_node(state)

        # Should NOT be FAILED — best-effort behavior preserved
        assert result["run_state"] != RUN_STATE_FAILED

    def test_review_required_true_non_pass_halts(self):
        """When review_required and W7 returns non-PASS, pipeline halts (FAILED state)."""
        mock_invoker = MagicMock()
        mock_invoker.invoke_worker.return_value = {
            "overall_status": "NEEDS_CHANGES",
            "pages_reviewed": 3,
            "pages_failed": 1,
        }

        state: OrchestratorState = {
            "run_id": "tc3617_nonpass",
            "run_state": "DRAFT_READY",
            "run_dir": "/tmp/runs/tc3617_nonpass",
            "run_config": {
                "review_enabled": True,
                "review_required": True,
            },
            "snapshot": {},
            "issues": [],
            "fix_attempts": 0,
            "current_issue": None,
            "redraft_attempts": 0,
            "seo_degraded": False,
            "degraded_pages": [],
            "abort_pages": [],
        }

        with patch("launch.orchestrator.graph._create_worker_invoker", return_value=mock_invoker):
            result = review_content_node(state)

        assert result["run_state"] == RUN_STATE_FAILED

    def test_decide_after_review_returns_failed_when_state_failed(self):
        """decide_after_review routes to 'failed' when run_state is FAILED."""
        state: OrchestratorState = {
            "run_id": "tc3617_decide_failed",
            "run_state": RUN_STATE_FAILED,
            "run_dir": "/tmp/runs/tc3617_decide_failed",
            "run_config": {"review_required": True},
            "snapshot": {},
            "issues": [],
            "fix_attempts": 0,
            "current_issue": None,
            "redraft_attempts": 0,
            "seo_degraded": False,
            "degraded_pages": [],
            "abort_pages": [],
        }
        route = decide_after_review(state)
        assert route == "failed"
