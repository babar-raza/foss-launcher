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

import pytest

from launch.orchestrator.graph import (
    OrchestratorState,
    build_orchestrator_graph,
    decide_after_validation,
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
            {"issue_id": "issue-001", "severity": "BLOCKER", "message": "Test blocker"}
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
            {"issue_id": "issue-001", "severity": "BLOCKER", "message": "Test blocker"}
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
            {"issue_id": "issue-001", "severity": "BLOCKER", "message": "First blocker"},
            {"issue_id": "issue-002", "severity": "BLOCKER", "message": "Second blocker"},
        ],
        "fix_attempts": 0,
        "current_issue": None,
    }

    decision = decide_after_validation(state)
    assert decision == "fix"
    # Should select first blocker (deterministic ordering)
    assert state["current_issue"]["issue_id"] == "issue-001"


def test_graph_execution_smoke_test():
    """Smoke test: execute graph with stub workers (no actual work)."""
    graph = build_orchestrator_graph()
    compiled = graph.compile()

    initial_state: OrchestratorState = {
        "run_id": "smoke_test",
        "run_state": "CREATED",
        "run_dir": "/tmp/runs/smoke_test",
        "run_config": {"max_fix_attempts": 3},
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
    graph = build_orchestrator_graph()
    compiled = graph.compile()

    initial_state: OrchestratorState = {
        "run_id": "fix_loop_test",
        "run_state": "CREATED",
        "run_dir": "/tmp/runs/fix_loop_test",
        "run_config": {"max_fix_attempts": 3},
        "snapshot": {},
        "issues": [
            {"issue_id": "issue-001", "severity": "BLOCKER", "message": "Test blocker"}
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
