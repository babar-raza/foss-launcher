"""LangGraph state definition for the v2 pipeline.

The graph passes a single ``PipelineGraphState`` TypedDict through every
node.  Only JSON-serialisable primitives are allowed so that LangGraph
can checkpoint and resume transparently (Rule 3: resume-from support).
"""

from __future__ import annotations

from typing import Any, TypedDict


class PipelineGraphState(TypedDict):
    """Mutable state bag flowing through the LangGraph StateGraph.

    Every value must be JSON-serialisable (no Pydantic models, no Path
    objects). Workers receive deserialised models via the orchestrator
    wrapper; they never touch this dict directly.
    """

    # -- identity -----------------------------------------------------------
    run_id: str
    run_dir: str  # absolute path as string (Path is not serialisable)

    # -- config -------------------------------------------------------------
    config: dict[str, Any]  # serialised RunConfig

    # -- progress -----------------------------------------------------------
    current_worker: str
    worker_outputs: dict[str, dict[str, Any]]  # worker_name -> serialised output

    # -- re-run control (Rule 6) -------------------------------------------
    re_run_count: int
    max_re_runs: int

    # -- verdict (set by evaluate, read by publish) -------------------------
    verdict: str  # "GO" | "NO_GO" | "" (empty = not yet evaluated)

    # -- error accumulator --------------------------------------------------
    errors: list[str]

    # -- heal directives (set by heal CLI, read by workers) -------------------
    # Empty dict when not in heal mode. Must contain only JSON-serializable primitives.
    heal_metadata: dict[str, Any]

    # -- advisor decision (set by __advisor__ node, read by routing) ----------
    # Empty dict when advisor has not run. Serialised PipelineAdvice fields.
    advisor_decision: dict[str, Any]
