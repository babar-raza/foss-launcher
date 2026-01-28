"""Orchestrator state graph definition using LangGraph.

Implements the state machine and transitions per specs/11_state_and_events.md
and specs/28_coordination_and_handoffs.md.

Spec references:
- specs/11_state_and_events.md (State model and transitions)
- specs/28_coordination_and_handoffs.md (Coordination model)
- specs/21_worker_contracts.md (Worker inputs/outputs)
"""

from __future__ import annotations

from pathlib import Path
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
from launch.state.event_log import generate_span_id, generate_trace_id

from .worker_invoker import WorkerInvoker


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


# Node implementations (TC-300: Real worker invocation)


def _create_worker_invoker(state: OrchestratorState) -> WorkerInvoker:
    """Create WorkerInvoker from orchestrator state.

    Helper function to create WorkerInvoker instance with proper context.

    Args:
        state: Orchestrator state containing run context

    Returns:
        WorkerInvoker instance
    """
    run_id = state["run_id"]
    run_dir = Path(state["run_dir"])
    # Generate trace context (could be persisted in state, but generating is deterministic)
    trace_id = generate_trace_id()
    parent_span_id = generate_span_id()
    return WorkerInvoker(run_id, run_dir, trace_id, parent_span_id)


def clone_inputs_node(state: OrchestratorState) -> OrchestratorState:
    """Clone inputs (product repo, site repo, workflows repo).

    TC-300: Invokes W1 RepoScout.
    Per specs/state-graph.md:45-51 (Node 1: clone_inputs).
    """
    invoker = _create_worker_invoker(state)

    # Invoke W1 RepoScout
    invoker.invoke_worker(
        worker="W1.RepoScout",
        inputs=[],  # No inputs for first worker
        outputs=[
            "repo_inventory.json",
            "frontmatter_contract.json",
            "site_context.json",
            "hugo_facts.json",
        ],
        run_config=state["run_config"],
    )

    state["run_state"] = RUN_STATE_CLONED_INPUTS
    return state


def ingest_node(state: OrchestratorState) -> OrchestratorState:
    """Ingest repo and produce repo_inventory.json.

    TC-300: No-op (reserved for future ingestion steps).
    Per specs/state-graph.md:55-62 (Node 2: ingest_repo).
    """
    # No worker invocation - reserved for future use
    # Deterministic state transition only
    state["run_state"] = RUN_STATE_INGESTED
    return state


def build_facts_node(state: OrchestratorState) -> OrchestratorState:
    """Build product facts and evidence map.

    TC-300: Invokes W2 FactsBuilder → W3 SnippetCurator (ordered).
    Per specs/state-graph.md:66-74 (Node 3: build_facts).
    """
    invoker = _create_worker_invoker(state)

    # Invoke W2 FactsBuilder
    invoker.invoke_worker(
        worker="W2.FactsBuilder",
        inputs=["repo_inventory.json"],
        outputs=["product_facts.json", "evidence_map.json"],
        run_config=state["run_config"],
    )

    # Invoke W3 SnippetCurator (ordered after W2)
    invoker.invoke_worker(
        worker="W3.SnippetCurator",
        inputs=["product_facts.json", "evidence_map.json"],
        outputs=["snippet_catalog.json"],
        run_config=state["run_config"],
    )

    state["run_state"] = RUN_STATE_FACTS_READY
    return state


def plan_pages_node(state: OrchestratorState) -> OrchestratorState:
    """Plan pages (page_plan.json).

    TC-300: Invokes W4 IAPlanner.
    Per specs/state-graph.md:76-81 (Node 4: build_plan).
    """
    invoker = _create_worker_invoker(state)

    # Invoke W4 IAPlanner
    invoker.invoke_worker(
        worker="W4.IAPlanner",
        inputs=["product_facts.json", "evidence_map.json", "snippet_catalog.json"],
        outputs=["page_plan.json"],
        run_config=state["run_config"],
    )

    state["run_state"] = RUN_STATE_PLAN_READY
    return state


def draft_sections_node(state: OrchestratorState) -> OrchestratorState:
    """Draft sections in parallel.

    TC-300: Invokes W5 SectionWriter per section (fan-out).
    Per specs/state-graph.md:84-94 (Node 5: draft_sections).

    Note: For TC-300, we invoke sequentially. True parallelism can be added later.
    """
    invoker = _create_worker_invoker(state)

    state["run_state"] = RUN_STATE_DRAFTING

    # TODO: For TC-300, invoke once for all sections
    # Full fan-out implementation would read page_plan.json and invoke per section
    invoker.invoke_worker(
        worker="W5.SectionWriter",
        inputs=["page_plan.json", "product_facts.json", "evidence_map.json", "snippet_catalog.json"],
        outputs=["drafts/"],
        run_config=state["run_config"],
    )

    state["run_state"] = RUN_STATE_DRAFT_READY
    return state


def link_and_patch_node(state: OrchestratorState) -> OrchestratorState:
    """Link drafts and apply patches to site worktree.

    TC-300: Invokes W6 LinkerAndPatcher.
    Per specs/state-graph.md:96-101 (Node 6: merge_and_link).
    """
    invoker = _create_worker_invoker(state)

    # Invoke W6 LinkerAndPatcher
    invoker.invoke_worker(
        worker="W6.LinkerAndPatcher",
        inputs=["drafts/", "page_plan.json"],
        outputs=["patch_bundle.json", "reports/diff_report.md"],
        run_config=state["run_config"],
    )

    state["run_state"] = RUN_STATE_LINKING
    return state


def validate_node(state: OrchestratorState) -> OrchestratorState:
    """Run all validation gates.

    TC-300: Invokes W7 Validator.
    Per specs/state-graph.md:104-109 (Node 7: validate).
    """
    invoker = _create_worker_invoker(state)

    # Invoke W7 Validator
    result = invoker.invoke_worker(
        worker="W7.Validator",
        inputs=["patch_bundle.json"],
        outputs=["validation_report.json"],
        run_config=state["run_config"],
    )

    state["run_state"] = RUN_STATE_VALIDATING

    # Update issues from validation result
    # W7 should return issues in result or write to validation_report.json
    # For now, we'll rely on reading validation_report.json in decide_after_validation
    if "issues" in result:
        state["issues"] = result["issues"]
    else:
        # Fallback: preserve existing issues or empty
        if "issues" not in state:
            state["issues"] = []

    return state


def fix_node(state: OrchestratorState) -> OrchestratorState:
    """Fix exactly one issue.

    TC-300: Invokes W8 Fixer.
    Per specs/state-graph.md:112-129 (Node 8: fix_next).
    """
    invoker = _create_worker_invoker(state)

    state["run_state"] = RUN_STATE_FIXING
    state["fix_attempts"] += 1

    # Get current issue to fix (set by decide_after_validation)
    current_issue = state.get("current_issue")

    # Invoke W8 Fixer with the specific issue
    # TODO: Pass issue details to fixer via run_config or separate mechanism
    invoker.invoke_worker(
        worker="W8.Fixer",
        inputs=["validation_report.json", "patch_bundle.json"],
        outputs=["patch_bundle.json"],  # Updated patches
        run_config=state["run_config"],
    )

    return state


def open_pr_node(state: OrchestratorState) -> OrchestratorState:
    """Open PR via commit service.

    TC-300: Invokes W9 PRManager.
    Per specs/state-graph.md:132-137 (Node 9: open_pr).
    """
    invoker = _create_worker_invoker(state)

    # Invoke W9 PRManager
    invoker.invoke_worker(
        worker="W9.PRManager",
        inputs=["patch_bundle.json", "validation_report.json"],
        outputs=["pr_request_bundle.json"],  # May be PR URL or deferred bundle
        run_config=state["run_config"],
    )

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
