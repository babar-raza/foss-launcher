"""Orchestrator run loop for single-run execution.

Implements single-run execution flow with state persistence, event logging,
and worker invocation per specs/28_coordination_and_handoffs.md.

CRITICAL CONSTRAINT: Implements SINGLE-RUN path ONLY.
Batch execution is blocked by OQ-BATCH-001.

Spec references:
- specs/28_coordination_and_handoffs.md (Coordination model)
- specs/11_state_and_events.md (State transitions and events)
- specs/21_worker_contracts.md (Worker I/O contracts)
- specs/43_resumable_pipeline.md (Resumable execution — TC-2399)
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

from launch.io.run_layout import create_run_skeleton
from launch.io.run_lock import RunAlreadyActiveError, RunLock  # noqa: F401
from launch.models.event import (
    EVENT_RUN_CREATED,
    EVENT_RUN_STATE_CHANGED,
    EVENT_TASKCARD_VALIDATED,
    Event,
)
from launch.models.state import (
    RUN_STATE_CLONED_INPUTS,
    RUN_STATE_CREATED,
    RUN_STATE_DRAFT_READY,
    RUN_STATE_FACTS_READY,
    RUN_STATE_INGESTED,
    RUN_STATE_LINKING,
    RUN_STATE_PLAN_READY,
    RUN_STATE_READY_FOR_PR,
    RUN_STATE_VALIDATING,
    Snapshot,
)
from launch.state.event_log import append_event, generate_event_id, generate_span_id, generate_trace_id
from launch.state.snapshot_manager import create_initial_snapshot, replay_events, write_snapshot

from launch.io.atomic import atomic_write_json

from .graph import OrchestratorState, build_orchestrator_graph


def _write_run_summary(
    run_id: str,
    run_dir: Path,
    run_config: Any,
    final_state: str,
    exit_code: int,
    started_at: str,
) -> None:
    """Write machine-readable run summary artifact (TC-2472).

    This provides a structured alternative to text-based stdout parsing
    in scripts/run_pilot.py.
    """
    product_slug = (
        run_config.get("product_slug", "")
        if isinstance(run_config, dict)
        else getattr(run_config, "product_slug", "")
    )
    summary = {
        "schema_version": "1.0",
        "run_id": run_id,
        "run_dir": str(run_dir),
        "final_state": final_state,
        "exit_code": exit_code,
        "product_slug": product_slug,
        "started_at_utc": started_at,
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    summary_path = run_dir / "artifacts" / "run_summary.json"
    try:
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_json(summary_path, summary)
    except Exception:
        logger.warning("Failed to write run_summary.json")

# TC-2399: Event type constant for resumable execution.
# Defined here (not in models/event.py) to respect TC-250 shared-library ownership.
_EVENT_RUN_RESUMED = "RUN_RESUMED"

# TC-2399: Mapping of worker aliases → (graph_node, pre_run_state, required_paths).
# "required_paths" are cumulative — each entry includes ALL paths needed from W1 onward.
# See specs/43_resumable_pipeline.md for the authoritative table.
RESUME_NODE_MAP: Dict[str, Tuple[str, str, List[str]]] = {
    # Short aliases
    "W1":  ("clone_inputs",   RUN_STATE_CREATED,        []),
    "W2":  ("ingest",         RUN_STATE_CLONED_INPUTS,  [
        "work/repo/.git",
        "artifacts/repo_inventory.json",
        "artifacts/frontmatter_contract.json",
    ]),
    "W3":  ("build_facts",    RUN_STATE_INGESTED,       [
        "artifacts/repo_inventory.json",
        "artifacts/frontmatter_contract.json",
    ]),
    "W4":  ("plan_pages",     RUN_STATE_FACTS_READY,    [
        "artifacts/repo_inventory.json",
        "artifacts/frontmatter_contract.json",
        "artifacts/product_facts.json",
        "artifacts/snippet_catalog.json",
    ]),
    "W5":  ("draft_sections", RUN_STATE_PLAN_READY,     [
        "artifacts/repo_inventory.json",
        "artifacts/frontmatter_contract.json",
        "artifacts/product_facts.json",
        "artifacts/snippet_catalog.json",
        "artifacts/page_plan.json",
    ]),
    "W6":  ("optimize_seo",   RUN_STATE_DRAFT_READY,    [
        "artifacts/page_plan.json",
        "artifacts/draft_manifest.json",
    ]),
    "W7":  ("review_content", RUN_STATE_DRAFT_READY,    [
        "artifacts/page_plan.json",
        "artifacts/draft_manifest.json",
    ]),
    "W8":  ("link_and_patch", RUN_STATE_DRAFT_READY,    [
        "artifacts/page_plan.json",
        "artifacts/draft_manifest.json",
    ]),
    "W9":  ("validate",       RUN_STATE_LINKING,        [
        "artifacts/page_plan.json",
        "artifacts/patch_bundle.json",
    ]),
    "W10": ("fix",            RUN_STATE_VALIDATING,     [
        "artifacts/patch_bundle.json",
        "artifacts/validation_report.json",
    ]),
    "W11": ("open_pr",        RUN_STATE_READY_FOR_PR,   [
        "artifacts/patch_bundle.json",
    ]),
    # Full node-name aliases (identical tuples)
    "clone_inputs":   ("clone_inputs",   RUN_STATE_CREATED,        []),
    "ingest":         ("ingest",         RUN_STATE_CLONED_INPUTS,  [
        "work/repo/.git",
        "artifacts/repo_inventory.json",
        "artifacts/frontmatter_contract.json",
    ]),
    "build_facts":    ("build_facts",    RUN_STATE_INGESTED,       [
        "artifacts/repo_inventory.json",
        "artifacts/frontmatter_contract.json",
    ]),
    "plan_pages":     ("plan_pages",     RUN_STATE_FACTS_READY,    [
        "artifacts/repo_inventory.json",
        "artifacts/frontmatter_contract.json",
        "artifacts/product_facts.json",
        "artifacts/snippet_catalog.json",
    ]),
    "draft_sections": ("draft_sections", RUN_STATE_PLAN_READY,     [
        "artifacts/repo_inventory.json",
        "artifacts/frontmatter_contract.json",
        "artifacts/product_facts.json",
        "artifacts/snippet_catalog.json",
        "artifacts/page_plan.json",
    ]),
    "optimize_seo":   ("optimize_seo",   RUN_STATE_DRAFT_READY,    [
        "artifacts/page_plan.json",
        "artifacts/draft_manifest.json",
    ]),
    "review_content": ("review_content", RUN_STATE_DRAFT_READY,    [
        "artifacts/page_plan.json",
        "artifacts/draft_manifest.json",
    ]),
    "link_and_patch": ("link_and_patch", RUN_STATE_DRAFT_READY,    [
        "artifacts/page_plan.json",
        "artifacts/draft_manifest.json",
    ]),
    "validate":       ("validate",       RUN_STATE_LINKING,        [
        "artifacts/page_plan.json",
        "artifacts/patch_bundle.json",
    ]),
    "fix":            ("fix",            RUN_STATE_VALIDATING,     [
        "artifacts/patch_bundle.json",
        "artifacts/validation_report.json",
    ]),
    "open_pr":        ("open_pr",        RUN_STATE_READY_FOR_PR,   [
        "artifacts/patch_bundle.json",
    ]),
}


class RunResult:
    """Result of a run execution."""

    def __init__(
        self,
        run_id: str,
        final_state: str,
        exit_code: int,
        snapshot: Optional[Snapshot] = None,
    ):
        self.run_id = run_id
        self.final_state = final_state
        self.exit_code = exit_code
        self.snapshot = snapshot


def execute_run(
    run_id: str,
    run_dir: Path,
    run_config: Dict[str, Any],
) -> RunResult:
    """Execute a single run through the orchestrator graph.

    CRITICAL: This implements SINGLE-RUN execution only.
    Batch execution is blocked by OQ-BATCH-001 and must raise NotImplementedError.

    Args:
        run_id: Unique run identifier
        run_dir: Path to RUN_DIR (runs/<run_id>/)
        run_config: Validated run configuration

    Returns:
        RunResult with final state and exit code

    Spec references:
    - specs/28_coordination_and_handoffs.md:9-29 (control plane)
    - specs/11_state_and_events.md:14-29 (state model)
    """
    # TC-2472: Capture start time for run_summary.json
    _started_at = datetime.now(timezone.utc).isoformat()

    # Create run skeleton (RUN_DIR structure)
    create_run_skeleton(run_dir)

    # Initialize trace context
    trace_id = generate_trace_id()
    parent_span_id = generate_span_id()

    # Emit RUN_CREATED event
    run_created_event = Event(
        event_id=generate_event_id(),
        run_id=run_id,
        ts=datetime.now(timezone.utc).isoformat(),
        type=EVENT_RUN_CREATED,
        payload={
            "run_id": run_id,
            "run_config": run_config,
        },
        trace_id=trace_id,
        span_id=generate_span_id(),
        parent_span_id=parent_span_id,
    )
    append_event(run_dir / "events.ndjson", run_created_event)

    # Create initial snapshot
    snapshot = create_initial_snapshot(run_id)
    write_snapshot(run_dir / "snapshot.json", snapshot)

    # Layer 1: Validate taskcard before run execution (early detection)
    validation_profile = run_config.get("validation_profile", "local")
    taskcard_id = run_config.get("taskcard_id")

    if validation_profile == "prod" and not taskcard_id:
        # Production runs require taskcard
        raise ValueError(
            "Production runs require 'taskcard_id' in run_config. "
            "This enforces write fence policy per specs/34_strict_compliance_guarantees.md. "
            "Set validation_profile='local' for local development."
        )

    if taskcard_id:
        # Validate taskcard exists and is active
        from launch.util.taskcard_loader import load_taskcard
        from launch.util.taskcard_validation import validate_taskcard_active

        repo_root = run_dir.parent.parent
        try:
            taskcard = load_taskcard(taskcard_id, repo_root)
            validate_taskcard_active(taskcard)
        except Exception as e:
            raise ValueError(
                f"Taskcard validation failed for {taskcard_id}: {e}\n"
                f"Ensure taskcard exists in plans/taskcards/ and has active status "
                f"(In-Progress or Done)."
            ) from e

        # Emit TASKCARD_VALIDATED event
        taskcard_event = Event(
            event_id=generate_event_id(),
            run_id=run_id,
            ts=datetime.now(timezone.utc).isoformat(),
            type=EVENT_TASKCARD_VALIDATED,
            payload={
                "taskcard_id": taskcard_id,
                "taskcard_status": taskcard.get("status"),
                "allowed_paths_count": len(taskcard.get("allowed_paths", [])),
            },
            trace_id=trace_id,
            span_id=generate_span_id(),
            parent_span_id=parent_span_id,
        )
        append_event(run_dir / "events.ndjson", taskcard_event)

    # TC-2443: Initialize worker-level caching (no-op when caching.enabled=false, the default).
    from launch.workers._shared.worker_cache import load_cache_config as _load_cache_config
    _worker_cache = _load_cache_config(run_dir, run_config)

    # Build orchestrator graph
    graph = build_orchestrator_graph()
    compiled_graph = graph.compile()

    # Initialize graph state
    initial_state: OrchestratorState = {
        "run_id": run_id,
        "run_state": RUN_STATE_CREATED,
        "run_dir": str(run_dir),
        "run_config": run_config,
        "snapshot": snapshot.to_dict(),
        "issues": [],
        "fix_attempts": 0,
        "current_issue": None,
        "redraft_attempts": 0,  # TC-2363: W7 → W5 selective re-draft loop counter
        "seo_degraded": False,  # TC-2381: True if W6 used deterministic fallback
        "degraded_pages": [],  # TC-2381: Pages with SEO quality warnings
        "abort_pages": [],  # TC-2381: Pages excluded from PR due to FATAL SEO errors
    }

    # Execute graph (streaming through states)
    final_state_dict: Optional[OrchestratorState] = None
    previous_run_state = RUN_STATE_CREATED  # Track previous state for correct old_state emission

    _limit = _compute_recursion_limit(run_config)
    for state_update in compiled_graph.stream(initial_state, {"recursion_limit": _limit}):
        # state_update is a dict with node name as key
        for node_name, node_output in state_update.items():
            final_state_dict = node_output

            # TC-2443: Record node completion in cache (no-op when disabled).
            # Full skip-on-hit logic lives in individual graph nodes; here we
            # record the output so reruns can detect unchanged workers.
            if _worker_cache.enabled:
                try:
                    _artifacts_dir = run_dir / "artifacts"
                    _output_paths = list(_artifacts_dir.glob("*.json")) if _artifacts_dir.exists() else []
                    _out_hash = _worker_cache.compute_input_hash(_output_paths)
                    _worker_cache.record(node_name, _out_hash, _out_hash)
                except Exception as _cache_err:
                    logger.debug("[Cache] Failed to record node %s: %s", node_name, _cache_err)

            # Emit state change event if state changed
            new_run_state = node_output.get("run_state")
            if new_run_state and new_run_state != previous_run_state:
                state_change_event = Event(
                    event_id=generate_event_id(),
                    run_id=run_id,
                    ts=datetime.now(timezone.utc).isoformat(),
                    type=EVENT_RUN_STATE_CHANGED,
                    payload={
                        "old_state": previous_run_state,
                        "new_state": new_run_state,
                    },
                    trace_id=trace_id,
                    span_id=generate_span_id(),
                    parent_span_id=parent_span_id,
                )
                append_event(run_dir / "events.ndjson", state_change_event)

                # Update previous state tracker
                previous_run_state = new_run_state

                # Replay events to reconstruct snapshot (ensures snapshot = f(events))
                snapshot = replay_events(run_dir / "events.ndjson", run_id)
                write_snapshot(run_dir / "snapshot.json", snapshot)

    # Determine exit code
    final_run_state = final_state_dict["run_state"] if final_state_dict else RUN_STATE_CREATED
    exit_code = _determine_exit_code(final_run_state)

    _append_run_manifest(run_id, run_dir, run_config, final_run_state)

    # TC-2472: Write machine-readable run summary
    _write_run_summary(run_id, run_dir, run_config, final_run_state, exit_code, _started_at)

    return RunResult(
        run_id=run_id,
        final_state=final_run_state,
        exit_code=exit_code,
        snapshot=snapshot,
    )


def _determine_exit_code(final_state: str) -> int:
    """Determine exit code from final run state.

    Args:
        final_state: Final run state

    Returns:
        Exit code per specs/01_system_contract.md:146-151
    """
    if final_state == "DONE":
        return 0
    elif final_state == "FAILED":
        return 2
    elif final_state == "CANCELLED":
        return 1
    else:
        return 5  # Unexpected internal error


def _append_run_manifest(
    run_id: str,
    run_dir: Path,
    run_config: Dict[str, Any],
    final_state: str,
) -> None:
    """Append a single-line JSON entry to runs/manifest.jsonl.

    Records run metadata for persistence and archival tooling.
    Failures are logged but never propagate -- manifest is best-effort.

    Args:
        run_id: Unique run identifier
        run_dir: Path to RUN_DIR (runs/<run_id>/)
        run_config: Validated run configuration
        final_state: Final run state string (e.g. DONE, FAILED)
    """
    try:
        # Count deep content files (non-index .md files under drafts/)
        drafts_dir = run_dir / "drafts"
        deep_content_count = 0
        if drafts_dir.exists():
            for md_file in drafts_dir.glob("**/*.md"):
                if md_file.stem not in ("index", "_index"):
                    deep_content_count += 1

        entry = {
            "run_id": run_id,
            "pilot": run_config.get("product_slug", ""),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "status": final_state,
            "output_dir": str(run_dir),
            "deep_content_files": deep_content_count,
        }

        manifest_path = run_dir.parent / "manifest.jsonl"
        with open(manifest_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        logger.info("Appended manifest entry for run %s (%d content files)", run_id, deep_content_count)
    except Exception:
        logger.warning("Failed to append run manifest for %s", run_id, exc_info=True)


def _validate_resume_artifacts(run_dir: Path, required_paths: List[str]) -> None:
    """Validate all artifacts required by a resume entry point exist in run_dir.

    Checks every path in required_paths (relative to run_dir). Directories are
    validated as directories; all other paths are validated as files.

    Args:
        run_dir: Existing run directory.
        required_paths: Relative paths that must exist (from RESUME_NODE_MAP).

    Raises:
        ValueError: If any required paths are missing. Message lists ALL missing paths.

    Spec reference: specs/43_resumable_pipeline.md §Artifact Pre-validation
    """
    missing: List[str] = []
    for rel_path in required_paths:
        abs_path = run_dir / rel_path
        if rel_path.endswith("/") or not abs_path.suffix:
            # Treat as directory if no file extension (e.g. "work/repo")
            if not abs_path.exists():
                missing.append(rel_path)
        else:
            if not abs_path.is_file():
                missing.append(rel_path)
    if missing:
        raise ValueError(
            f"Cannot resume from '{run_dir}': missing required artifact(s):\n"
            + "\n".join(f"  - {p}" for p in missing)
        )


def _compute_recursion_limit(run_config: Dict[str, Any]) -> int:
    """Compute LangGraph recursion_limit from run_config loop parameters.

    The worst-case node visit count is:
        10 + 4 * max_redraft_attempts + 2 * max_fix_attempts
    We add a safety buffer of 15 and enforce a floor of 50.

    TC-2960: Prevents GraphRecursionError when max_fix_attempts > 6.
    """
    max_fix = run_config.get("max_fix_attempts", 3)
    max_redraft = run_config.get("max_redraft_attempts", 1)
    computed = 10 + 4 * max_redraft + 2 * max_fix + 15
    return max(50, computed)


def execute_run_from_node(
    run_id: str,
    run_dir: Path,
    run_config: Dict[str, Any],
    from_worker: str,
) -> RunResult:
    """Resume pipeline execution from a specific graph node using existing run_dir artifacts.

    Takes artifacts already produced by a prior run and re-enters the LangGraph pipeline
    at the specified worker. Earlier workers are skipped entirely.

    Key differences from execute_run():
    - Does NOT call create_run_skeleton() — run_dir already exists.
    - Does NOT emit RUN_CREATED — already in events.ndjson.
    - Emits RUN_RESUMED before graph.stream().
    - Uses build_orchestrator_graph(start_node=node_name).
    - Sets initial run_state to the pre-execution state for from_worker.

    Args:
        run_id: Run identifier (run_dir.name).
        run_dir: Existing run directory containing prior artifacts.
        run_config: Validated run configuration (loaded from run_dir/run_config.yaml).
        from_worker: Worker alias or node name (e.g. "W5" or "draft_sections").

    Returns:
        RunResult with final state and exit code.

    Raises:
        ValueError: If from_worker alias is unknown or required artifacts are missing.

    Spec reference: specs/43_resumable_pipeline.md (TC-2399)
    """
    # Resolve alias
    if from_worker not in RESUME_NODE_MAP:
        valid = sorted(k for k in RESUME_NODE_MAP if k.startswith("W") and k[1:].isdigit())
        raise ValueError(
            f"Unknown --from-worker alias '{from_worker}'. "
            f"Valid aliases: {', '.join(valid)} (and full node names)."
        )
    node_name, pre_run_state, required_paths = RESUME_NODE_MAP[from_worker]

    # Validate required artifacts exist (read-only — safe outside the lock)
    _validate_resume_artifacts(run_dir, required_paths)

    with RunLock(run_dir, worker=from_worker):
        return _execute_run_from_node_locked(run_id, run_dir, run_config, from_worker, node_name, pre_run_state)


def _execute_run_from_node_locked(
    run_id: str,
    run_dir: Path,
    run_config: Dict[str, Any],
    from_worker: str,
    node_name: str,
    pre_run_state: str,
) -> "RunResult":
    """Inner body of execute_run_from_node(), called while RunLock is held."""
    # TC-2472: Capture start time for run_summary.json
    _started_at = datetime.now(timezone.utc).isoformat()

    # Initialize trace context
    trace_id = generate_trace_id()
    parent_span_id = generate_span_id()

    # Load existing snapshot (may be absent for very early partial runs)
    snapshot_path = run_dir / "snapshot.json"
    if snapshot_path.exists():
        try:
            with open(snapshot_path, encoding="utf-8") as f:
                snapshot_dict = json.load(f)
        except Exception:
            snapshot_dict = {}
    else:
        snapshot_dict = {}

    # Emit RUN_RESUMED event (appended to existing events.ndjson)
    resumed_event = Event(
        event_id=generate_event_id(),
        run_id=run_id,
        ts=datetime.now(timezone.utc).isoformat(),
        type=_EVENT_RUN_RESUMED,
        payload={
            "from_worker_alias": from_worker,
            "from_node": node_name,
            "initial_run_state": pre_run_state,
        },
        trace_id=trace_id,
        span_id=generate_span_id(),
        parent_span_id=parent_span_id,
    )
    append_event(run_dir / "events.ndjson", resumed_event)

    # Build graph with dynamic entry point
    graph = build_orchestrator_graph(start_node=node_name)
    compiled_graph = graph.compile()

    # Initialize graph state — identical to execute_run() except run_state
    # IMPORTANT: run_config is passed by reference and may contain transient
    # underscore-prefixed keys (_drive_goal, _current_issue, _heal_gate_filter)
    # injected by callers (heal.py, main.py).  Do NOT re-validate run_config
    # against the JSON schema here — schema has additionalProperties:false and
    # would reject these runtime keys.  See specs/50_healing_cost_reduction.md §5.8.
    initial_state: OrchestratorState = {
        "run_id": run_id,
        "run_state": pre_run_state,
        "run_dir": str(run_dir),
        "run_config": run_config,
        "snapshot": snapshot_dict,
        "issues": [],
        "fix_attempts": 0,
        "current_issue": None,
        "redraft_attempts": 0,
        "seo_degraded": False,
        "degraded_pages": [],
        "abort_pages": [],
    }

    # Execute graph (streaming through states) — identical to execute_run()
    final_state_dict: Optional[OrchestratorState] = None
    previous_run_state = pre_run_state
    snapshot: Optional[Snapshot] = None  # set on first state transition

    _limit = _compute_recursion_limit(run_config)
    for state_update in compiled_graph.stream(initial_state, {"recursion_limit": _limit}):
        for node_name_out, node_output in state_update.items():
            final_state_dict = node_output

            new_run_state = node_output.get("run_state")
            if new_run_state and new_run_state != previous_run_state:
                state_change_event = Event(
                    event_id=generate_event_id(),
                    run_id=run_id,
                    ts=datetime.now(timezone.utc).isoformat(),
                    type=EVENT_RUN_STATE_CHANGED,
                    payload={
                        "old_state": previous_run_state,
                        "new_state": new_run_state,
                    },
                    trace_id=trace_id,
                    span_id=generate_span_id(),
                    parent_span_id=parent_span_id,
                )
                append_event(run_dir / "events.ndjson", state_change_event)
                previous_run_state = new_run_state

                snapshot = replay_events(run_dir / "events.ndjson", run_id)
                write_snapshot(run_dir / "snapshot.json", snapshot)

    final_run_state = final_state_dict["run_state"] if final_state_dict else pre_run_state
    exit_code = _determine_exit_code(final_run_state)

    _append_run_manifest(run_id, run_dir, run_config, final_run_state)

    # TC-2472: Write machine-readable run summary
    _write_run_summary(run_id, run_dir, run_config, final_run_state, exit_code, _started_at)

    return RunResult(
        run_id=run_id,
        final_state=final_run_state,
        exit_code=exit_code,
        snapshot=snapshot,
    )


# BLOCKED: OQ-BATCH-001 (Batch execution semantics)
def execute_batch(batch_manifest: Dict[str, Any]) -> None:
    """Execute multiple runs with bounded concurrency.

    BLOCKED: OQ-BATCH-001 (Batch execution semantics)

    Args:
        batch_manifest: Batch configuration (shape undefined)

    Raises:
        NotImplementedError: Always (blocked by OQ-BATCH-001)

    Spec reference: OPEN_QUESTIONS.md:66-74
    """
    raise NotImplementedError(
        "Batch execution not implemented - blocked by OQ-BATCH-001. "
        "See OPEN_QUESTIONS.md for details on required batch execution semantics."
    )
