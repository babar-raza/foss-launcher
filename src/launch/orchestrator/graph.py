"""Orchestrator state graph definition using LangGraph.

Implements the state machine and transitions per specs/11_state_and_events.md
and specs/28_coordination_and_handoffs.md.

Spec references:
- specs/11_state_and_events.md (State model and transitions)
- specs/28_coordination_and_handoffs.md (Coordination model)
- specs/21_worker_contracts.md (Worker inputs/outputs)
"""

from __future__ import annotations

from typing import Annotated, Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from launch.models.state import (
    RUN_STATE_CANCELLED,
    RUN_STATE_CLONED_INPUTS,
    RUN_STATE_CREATED,
    RUN_STATE_DONE,
    RUN_STATE_DRAFT_READY,
    RUN_STATE_DRAFTING,
    RUN_STATE_FACTS_READY,
    RUN_STATE_FAILED,
    RUN_STATE_FIXING,
    RUN_STATE_INGESTED,
    RUN_STATE_LINKING,
    RUN_STATE_PLAN_READY,
    RUN_STATE_PR_OPENED,
    RUN_STATE_READY_FOR_PR,
    RUN_STATE_VALIDATING,
)


class OrchestratorState(TypedDict):
    """State passed through the orchestrator graph.

    This represents the mutable state that flows through the graph nodes.
    Immutable run state is persisted in snapshot.json and events.ndjson.
    """

    run_id: str
    run_state: str
    run_dir: str
    run_config: Dict[str, Any]
    snapshot: Dict[str, Any]
    issues: List[Dict[str, Any]]
    fix_attempts: int
    current_issue: Optional[Dict[str, Any]]


def build_orchestrator_graph() -> StateGraph:
    """Build the orchestrator state graph.

    Returns:
        LangGraph StateGraph defining the orchestrator workflow

    Spec reference: specs/11_state_and_events.md:14-29 (states)
    """
    # Create state graph
    graph = StateGraph(OrchestratorState)

    # Add nodes for each state (nodes are workers or orchestrator actions)
    graph.add_node("clone_inputs", clone_inputs_node)
    graph.add_node("ingest", ingest_node)
    graph.add_node("build_facts", build_facts_node)
    graph.add_node("plan_pages", plan_pages_node)
    graph.add_node("draft_sections", draft_sections_node)
    graph.add_node("link_and_patch", link_and_patch_node)
    graph.add_node("validate", validate_node)
    graph.add_node("fix", fix_node)
    graph.add_node("open_pr", open_pr_node)
    graph.add_node("finalize", finalize_node)
    graph.add_node("fail", fail_node)

    # Set entry point
    graph.set_entry_point("clone_inputs")

    # Define transitions (binding per state model)
    graph.add_edge("clone_inputs", "ingest")
    graph.add_edge("ingest", "build_facts")
    graph.add_edge("build_facts", "plan_pages")
    graph.add_edge("plan_pages", "draft_sections")
    graph.add_edge("draft_sections", "link_and_patch")
    graph.add_edge("link_and_patch", "validate")

    # Conditional: validation -> fix or ready_for_pr
    graph.add_conditional_edges(
        "validate",
        decide_after_validation,
        {
            "fix": "fix",
            "ready_for_pr": "open_pr",
            "failed": "fail",
        },
    )

    # Fix loop: fix -> validate
    graph.add_edge("fix", "validate")

    # PR -> finalize -> END
    graph.add_edge("open_pr", "finalize")
    graph.add_edge("finalize", END)
    graph.add_edge("fail", END)

    return graph


# Node implementations (stub for TC-300, full implementation in worker taskcards)


def clone_inputs_node(state: OrchestratorState) -> OrchestratorState:
    """Clone inputs (product repo, site repo, workflows repo).

    Stub for TC-300. Full implementation in TC-401 (W1 RepoScout).
    """
    state["run_state"] = RUN_STATE_CLONED_INPUTS
    return state


def ingest_node(state: OrchestratorState) -> OrchestratorState:
    """Ingest repo and produce repo_inventory.json.

    Stub for TC-300. Full implementation in TC-400 (W1 RepoScout).
    """
    state["run_state"] = RUN_STATE_INGESTED
    return state


def build_facts_node(state: OrchestratorState) -> OrchestratorState:
    """Build product facts and evidence map.

    Stub for TC-300. Full implementation in TC-410 (W2 FactsBuilder).
    """
    state["run_state"] = RUN_STATE_FACTS_READY
    return state


def plan_pages_node(state: OrchestratorState) -> OrchestratorState:
    """Plan pages (page_plan.json).

    Stub for TC-300. Full implementation in TC-430 (W4 IAPlanner).
    """
    state["run_state"] = RUN_STATE_PLAN_READY
    return state


def draft_sections_node(state: OrchestratorState) -> OrchestratorState:
    """Draft sections in parallel.

    Stub for TC-300. Full implementation in TC-440 (W5 SectionWriter).
    """
    state["run_state"] = RUN_STATE_DRAFTING
    # Simulate drafting completion
    state["run_state"] = RUN_STATE_DRAFT_READY
    return state


def link_and_patch_node(state: OrchestratorState) -> OrchestratorState:
    """Link drafts and apply patches to site worktree.

    Stub for TC-300. Full implementation in TC-450 (W6 LinkerAndPatcher).
    """
    state["run_state"] = RUN_STATE_LINKING
    return state


def validate_node(state: OrchestratorState) -> OrchestratorState:
    """Run all validation gates.

    Stub for TC-300. Full implementation in TC-460 (W7 Validator).
    """
    state["run_state"] = RUN_STATE_VALIDATING
    # Stub: simulate validation result
    state["issues"] = []  # No issues for now
    return state


def fix_node(state: OrchestratorState) -> OrchestratorState:
    """Fix exactly one issue.

    Stub for TC-300. Full implementation in TC-470 (W8 Fixer).
    """
    state["run_state"] = RUN_STATE_FIXING
    state["fix_attempts"] += 1
    return state


def open_pr_node(state: OrchestratorState) -> OrchestratorState:
    """Open PR via commit service.

    Stub for TC-300. Full implementation in TC-480 (W9 PRManager).
    """
    state["run_state"] = RUN_STATE_PR_OPENED
    return state


def finalize_node(state: OrchestratorState) -> OrchestratorState:
    """Finalize run (mark DONE).

    Stub for TC-300. Writes final snapshot and flushes telemetry.
    """
    state["run_state"] = RUN_STATE_DONE
    return state


def fail_node(state: OrchestratorState) -> OrchestratorState:
    """Fail run (mark FAILED).

    Stub for TC-300. Writes failure summary and flushes telemetry.
    """
    state["run_state"] = RUN_STATE_FAILED
    return state


def decide_after_validation(state: OrchestratorState) -> str:
    """Decide next action after validation.

    Args:
        state: Current orchestrator state

    Returns:
        Next node name: "fix", "ready_for_pr", or "failed"

    Spec reference: specs/28_coordination_and_handoffs.md:71-84 (loop policy)
    """
    issues = state.get("issues", [])
    fix_attempts = state.get("fix_attempts", 0)
    max_fix_attempts = state.get("run_config", {}).get("max_fix_attempts", 3)

    # Check if all gates passed
    if not issues:
        return "ready_for_pr"

    # Check if we've exhausted fix attempts
    if fix_attempts >= max_fix_attempts:
        return "failed"

    # Check for blocker issues
    blockers = [issue for issue in issues if issue.get("severity") == "BLOCKER"]
    if blockers:
        # Select first blocker for fixing (deterministic ordering)
        state["current_issue"] = blockers[0]
        return "fix"

    # No blockers, ready for PR
    return "ready_for_pr"
