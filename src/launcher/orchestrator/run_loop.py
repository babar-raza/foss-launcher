"""Main execution entry point for the v2 pipeline.

``execute_run`` is the single public function that takes a RunConfig and
returns an EvaluationReport.  It handles:

- Run directory creation (via ``create_run_skeleton``)
- Pipeline config loading
- Worker instantiation (via registry)
- Graph build and execution
- Resume-from support (Rule 3)
- Final report extraction
"""

from __future__ import annotations

import hashlib
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from launcher.io.artifact_store import ArtifactStore
from launcher.io.run_layout import RunLayout, create_run_skeleton, discover_latest_run
from launcher.models.evaluation import EvaluationReport, Verdict
from launcher.models.run_config import RunConfig
from launcher.state.event_log import generate_trace_id
from launcher.state.snapshot_manager import (
    create_initial_snapshot,
    replay_events,
    write_snapshot,
)

from .graph_builder import build_pipeline
from .state import PipelineGraphState
from .worker_contract import WorkerContract


@dataclass
class RunResult:
    """Result of a pipeline run, supporting partial execution."""

    report: EvaluationReport | None
    worker_outputs: dict[str, dict[str, Any]] = field(default_factory=dict)
    stopped_after: str = ""
    run_dir: str = ""
    pending_approval: bool = False
    langgraph_thread_id: str = ""

logger = logging.getLogger(__name__)

# Default paths relative to project root.
_DEFAULT_PIPELINE_CONFIG = Path("configs/pipeline.yaml")
_DEFAULT_SCHEMA_DIR = Path("specs/schemas")


# ---------------------------------------------------------------------------
# Worker registry helpers
# ---------------------------------------------------------------------------


def _discover_workers() -> dict[str, WorkerContract]:
    """Import and instantiate all registered workers.

    Workers register themselves via the ``launcher.workers`` package.
    Each sub-package (intake, understand, generate, evaluate, publish)
    exposes a factory function ``create_worker() -> WorkerContract``.

    Returns an empty dict if no workers are available yet (e.g. during
    early development or testing with mocks).
    """
    registry: dict[str, WorkerContract] = {}

    worker_modules = [
        ("launcher.workers.intake.worker", "intake"),
        ("launcher.workers.understand.worker", "understand"),
        ("launcher.workers.planner.worker", "planner"),
        ("launcher.workers.generate.worker", "generate"),
        ("launcher.workers.evaluate.worker", "evaluate"),
        ("launcher.workers.publish.worker", "publish"),
    ]

    for module_path, worker_name in worker_modules:
        try:
            import importlib

            mod = importlib.import_module(module_path)
            factory = getattr(mod, "create_worker", None)
            if factory is not None:
                worker = factory()
                registry[worker.name] = worker
                logger.info("Registered worker: %s", worker.name)
            else:
                logger.debug(
                    "Module %s has no create_worker(); skipping", module_path
                )
        except ImportError:
            logger.debug("Worker module %s not yet implemented; skipping", module_path)
        except Exception:
            logger.exception("Failed to load worker module %s", module_path)

    return registry


# ---------------------------------------------------------------------------
# Resume-from support (Rule 3)
# ---------------------------------------------------------------------------


def _build_resume_state(
    run_dir: Path,
    resume_from: str,
    run_id: str,
    config: RunConfig,
) -> PipelineGraphState:
    """Build initial graph state for a resumed run.

    Loads checkpoint files from the run directory up to (but not including)
    ``resume_from`` so that the graph can skip already-completed workers.
    """
    store = ArtifactStore(run_dir=run_dir)
    worker_outputs: dict[str, dict[str, Any]] = {}

    # Pipeline order — load checkpoints for workers before resume_from.
    worker_order = ["intake", "understand", "planner", "generate", "evaluate", "publish"]

    for wname in worker_order:
        if wname == resume_from:
            break
        checkpoint_name = f"{wname}_checkpoint.json"
        if store.exists(checkpoint_name):
            worker_outputs[wname] = store.load_json(
                checkpoint_name, validate_schema=False
            )
            logger.info("Loaded checkpoint for %s from previous run", wname)
            # Integrity check: warn if artifact was manually edited
            try:
                from launcher.resilience.checkpoint import load_worker_checkpoint
                # Find the latest WorkerCheckpoint for this worker by scanning
                # the worker_checkpoints/ directory for files named {worker}_*.json
                wcp = None
                cp_dir = run_dir / "worker_checkpoints"
                if cp_dir.is_dir():
                    candidates = sorted(cp_dir.glob(f"{wname}_*.json"), reverse=True)
                    if candidates:
                        wcp = load_worker_checkpoint(run_dir, candidates[0].stem)
                if wcp is not None:
                    artifact_path = run_dir / checkpoint_name
                    if artifact_path.is_file():
                        current_hash = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
                        if current_hash != wcp.content_hash:
                            logger.warning(
                                "Checkpoint artifact for '%s' has been manually edited "
                                "(stored hash: %s, current: %s). Resume may produce "
                                "inconsistent results.",
                                wname, wcp.content_hash[:8], current_hash[:8],
                            )
            except Exception:
                logger.debug(
                    "Could not load worker checkpoint for %s; skipping integrity check", wname
                )

    if not worker_outputs and resume_from != "intake":
        logger.warning(
            "No checkpoints found before '%s' in %s — resume may re-run all workers",
            resume_from,
            run_dir,
        )

    return PipelineGraphState(
        run_id=run_id,
        run_dir=str(run_dir),
        config=config.model_dump(mode="json"),
        current_worker="",
        worker_outputs=worker_outputs,
        re_run_count=0,
        max_re_runs=2,
        verdict="",
        errors=[],
        heal_metadata={},
    )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def _write_final_snapshot(layout: RunLayout, run_id: str) -> None:
    """Materialize snapshot from event log and write to disk."""
    try:
        final_snap = replay_events(layout.events_file, run_id)
        write_snapshot(layout.snapshot_file, final_snap)
    except Exception:
        logger.warning("Failed to write final snapshot for run %s", run_id, exc_info=True)


def _update_telemetry_run(
    telemetry_client: Any | None,
    event_id: str,
    status: str,
    start_time: float,
    *,
    error_summary: str = "",
    output_summary: str = "",
    items_discovered: int | None = None,
    items_succeeded: int | None = None,
) -> None:
    """Update the parent telemetry run (non-fatal)."""
    if telemetry_client is None:
        return
    try:
        end_iso = datetime.now(timezone.utc).isoformat()
        duration_ms = int((time.time() - start_time) * 1000)
        telemetry_client.update_run(
            event_id=event_id,
            status=status,
            end_time=end_iso,
            duration_ms=duration_ms,
            error_summary=error_summary or None,
            output_summary=output_summary or None,
            items_discovered=items_discovered,
            items_succeeded=items_succeeded,
        )
    except Exception:
        logger.warning("Telemetry run update failed (non-fatal)", exc_info=True)


def _flush_telemetry(telemetry_client: Any | None) -> None:
    """Flush telemetry outbox (non-fatal)."""
    if telemetry_client is None:
        return
    try:
        telemetry_client.flush_outbox()
    except Exception:
        logger.warning("Telemetry outbox flush failed (non-fatal)", exc_info=True)


async def _stream_execute(
    compiled_graph: Any,
    initial_state: "PipelineGraphState",
    *,
    stream_progress: bool = False,
    lg_config: dict | None = None,
) -> dict[str, Any]:
    """Execute the graph, optionally printing per-worker progress to stderr.

    When stream_progress=False (default): delegates to ainvoke() unchanged.
    When stream_progress=True: uses astream_events(), prints worker start/done lines.
    """
    if not stream_progress:
        return await compiled_graph.ainvoke(initial_state, config=lg_config or {})

    import sys
    import time as _time

    _SKIP: frozenset[str] = frozenset(["__heal_router__", "__re_run__", "LangGraph"])
    _starts: dict[str, float] = {}
    final_state: dict[str, Any] = {}

    async for event in compiled_graph.astream_events(
        initial_state, version="v2", config=lg_config or {}
    ):
        etype = event.get("event", "")
        name = event.get("name", "")

        if etype == "on_chain_end" and name == "LangGraph":
            out = event.get("data", {}).get("output", {})
            if isinstance(out, dict):
                final_state = out

        if name in _SKIP or not name:
            continue
        if etype == "on_chain_start":
            _starts[name] = _time.monotonic()
            print(f"  [{name}] starting...", file=sys.stderr, flush=True)
        elif etype == "on_chain_end":
            elapsed = _time.monotonic() - _starts.get(name, _time.monotonic())
            print(f"  [{name}] done ({elapsed:.1f}s)", file=sys.stderr, flush=True)

    return final_state


async def execute_run(
    config: RunConfig,
    *,
    pipeline_config_path: Path | None = None,
    schema_dir: Path | None = None,
    workers: dict[str, WorkerContract] | None = None,
    resume_from: str = "",
    stop_after: str = "",
    run_id: str = "",
    runs_root: Path | None = None,
    source_config_path: str = "",
    heal_metadata: dict | None = None,
    stream_progress: bool = False,
    use_langgraph_checkpoint: bool = False,
    interrupt_before_publish: bool = False,
    checkpointer_instance: Any | None = None,
    resume_langgraph_thread: str = "",
) -> RunResult:
    """Execute a full pipeline run and return the evaluation report.

    Parameters
    ----------
    config:
        The RunConfig for this execution.
    pipeline_config_path:
        Path to ``pipeline.yaml``.  Defaults to ``configs/pipeline.yaml``.
    schema_dir:
        Path to JSON schema directory.  Defaults to ``specs/schemas``.
    workers:
        Pre-built worker dict (for testing).  If ``None``, workers are
        discovered automatically from ``launcher.workers.*``.
    resume_from:
        If set, skip workers before this one and resume from checkpoints
        (Rule 3).
    run_id:
        Explicit run ID.  If empty, a new UUID-based ID is generated.
    runs_root:
        Root directory for run folders.  Defaults to ``runs/``.
    stream_progress:
        If ``True``, print per-worker start/done lines to stderr via
        ``astream_events()``.  Defaults to ``False`` (uses ``ainvoke()``).

    Returns
    -------
    RunResult — contains the evaluation report (if reached) and all worker outputs.
    """
    # -- Validate argument combinations ----------------------------------------
    if run_id and not resume_from:
        raise ValueError("run_id requires resume_from (to avoid corrupting an existing run)")

    # -- Validate resume_from against known pipeline workers ----------------
    # NOTE: _KNOWN_PIPELINE_WORKERS must be kept in sync with _build_resume_state's
    # worker_order list. If a new worker is added to the pipeline, update BOTH.
    _KNOWN_PIPELINE_WORKERS = ["intake", "understand", "planner", "generate", "evaluate", "publish"]
    if resume_from and resume_from not in _KNOWN_PIPELINE_WORKERS:
        raise ValueError(
            f"resume_from='{resume_from}' is not a known pipeline worker. "
            f"Valid values: {_KNOWN_PIPELINE_WORKERS}"
        )

    # TC-3916: Guard for LangGraph thread resume without checkpointer
    if resume_langgraph_thread and checkpointer_instance is None:
        raise ValueError(
            "resume_langgraph_thread requires checkpointer_instance — "
            "pass the same MemorySaver instance used during the interrupted run"
        )

    # -- Resolve runs root ----------------------------------------------------
    if runs_root is None:
        run_dir_base = Path(config.output.run_dir)
    else:
        run_dir_base = runs_root

    # -- Generate run identity (hybrid resume) --------------------------------
    if resume_from and not run_id:
        discovered = discover_latest_run(run_dir_base, config.family, config.platform)
        if discovered is None:
            raise ValueError(
                f"No previous run found for family={config.family} "
                f"platform={config.platform} under {run_dir_base}"
            )
        run_dir = discovered
        run_id = discovered.name
        logger.info("Auto-discovered previous run for resume: %s", run_id)
    elif not run_id:
        from launcher.util.run_id import generate_run_id

        for _attempt in range(3):
            run_id = generate_run_id(config.family, config.platform)
            run_dir = run_dir_base / run_id
            if not run_dir.exists():
                break
            logger.warning("Run ID collision, retrying: %s", run_id)
        else:
            raise ValueError(
                f"Failed to generate unique run ID after 3 attempts under {run_dir_base}"
            )
    else:
        run_dir = run_dir_base / run_id

    logger.info("Starting pipeline run: %s", run_id)

    # -- Create run directory (skip for existing dirs on resume) --------------
    if run_dir.exists():
        layout = RunLayout(run_dir=run_dir.resolve())
    else:
        layout = create_run_skeleton(run_dir)

    # -- Emit run_created event ----------------------------------------------
    store = ArtifactStore(run_dir=run_dir)
    store.emit_event(
        "run_created",
        {
            "run_id": run_id,
            "family": config.family,
            "platform": config.platform,
            "resume_from": resume_from,
        },
        run_id=run_id,
    )

    # -- Write initial snapshot (skip on resume to preserve existing state) ----
    if not resume_from:
        initial_snap = create_initial_snapshot(run_id)
        write_snapshot(layout.snapshot_file, initial_snap)

    # -- Write config snapshot -----------------------------------------------
    store.write_json("run_config.json", config.model_dump(mode="json"))

    # -- Write run manifest (skip on resume to preserve original created_utc) -
    if not resume_from:
        store.write_json("run_manifest.json", {
            "run_id": run_id,
            "family": config.family,
            "platform": config.platform,
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "config_path": source_config_path,
        })

    # -- Initialize telemetry (non-fatal) ------------------------------------
    telemetry_client = None
    telemetry_trace_id = generate_trace_id()
    telemetry_event_id = str(uuid.uuid4())
    run_start_time = time.time()
    start_iso = datetime.now(timezone.utc).isoformat()

    try:
        endpoint_url = os.environ.get("TELEMETRY_API_URL", "")
        if not endpoint_url and config.telemetry:
            endpoint_url = config.telemetry.endpoint_url

        if endpoint_url:
            from launcher.clients.telemetry import TelemetryClient

            auth_token = ""
            if config.telemetry and config.telemetry.auth_token_env:
                auth_token = os.environ.get(config.telemetry.auth_token_env, "")

            telemetry_client = TelemetryClient(
                endpoint_url=endpoint_url,
                run_dir=run_dir,
                auth_token=auth_token or None,
            )
            telemetry_client.create_run(
                run_id=run_id,
                agent_name="launcher.orchestrator",
                job_type="launch",
                start_time=start_iso,
                event_id=telemetry_event_id,
                status="running",
                product_family=config.family,
                platform=config.platform,
                git_repo=config.repo_url,
                context_json={"trace_id": telemetry_trace_id},
            )
            logger.info("Telemetry client initialized: %s", endpoint_url)
    except Exception:
        logger.warning("Telemetry initialization failed (non-fatal)", exc_info=True)
        telemetry_client = None

    # -- Resolve paths -------------------------------------------------------
    if pipeline_config_path is None:
        pipeline_config_path = _DEFAULT_PIPELINE_CONFIG
    if schema_dir is None:
        schema_dir = _DEFAULT_SCHEMA_DIR

    # -- Register workers ----------------------------------------------------
    if workers is None:
        workers = _discover_workers()

    if not workers:
        logger.warning(
            "No workers registered; the graph will be empty. "
            "Returning a NO_GO evaluation report."
        )
        return RunResult(report=EvaluationReport(verdict=Verdict.NO_GO), run_dir=str(run_dir))

    # -- TC-3916: Set up LangGraph checkpointer ------------------------------
    _checkpointer = checkpointer_instance
    if use_langgraph_checkpoint and _checkpointer is None:
        from langgraph.checkpoint.memory import MemorySaver
        _checkpointer = MemorySaver()
    _interrupt_before: list[str] = ["publish"] if interrupt_before_publish else []
    _lg_config: dict[str, Any] = (
        {"configurable": {"thread_id": run_id}} if _checkpointer else {}
    )

    # -- Build graph ---------------------------------------------------------
    compiled_graph = build_pipeline(
        pipeline_config_path,
        workers,
        schema_dir=schema_dir,
        stop_after=stop_after or None,
        telemetry_client=telemetry_client,
        telemetry_trace_id=telemetry_trace_id,
        checkpointer=_checkpointer,
        interrupt_before=_interrupt_before,
    )

    # -- Build initial state -------------------------------------------------
    # TC-3879 Wave 1 (H3): Thread heal_metadata from caller into pipeline state so workers
    # can use root_causes, priority_checks, target_pages, etc. during heal re-runs.
    _heal_meta: dict = heal_metadata or {}
    if resume_from:
        initial_state = _build_resume_state(run_dir, resume_from, run_id, config)
        # Overlay heal_metadata onto the resume state (resume state always starts with {})
        if _heal_meta:
            initial_state = {**initial_state, "heal_metadata": _heal_meta}
        logger.info("Resuming from worker: %s", resume_from)
    else:
        initial_state = PipelineGraphState(
            run_id=run_id,
            run_dir=str(run_dir),
            config=config.model_dump(mode="json"),
            current_worker="",
            worker_outputs={},
            re_run_count=0,
            max_re_runs=2,
            verdict="",
            errors=[],
            heal_metadata=_heal_meta,
        )

    # -- Execute graph -------------------------------------------------------
    try:
        final_state = await _stream_execute(
            compiled_graph,
            initial_state,
            stream_progress=stream_progress,
            lg_config=_lg_config,
        )

        # TC-3917: Detect publish interrupt — return early for approval
        if interrupt_before_publish and _checkpointer is not None:
            lg_state = await compiled_graph.aget_state(
                {"configurable": {"thread_id": run_id}}
            )
            if "publish" in (lg_state.next or ()):
                store.write_json("pending_approval.json", {
                    "run_id": run_id,
                    "pending_node": "publish",
                    "verdict": final_state.get("verdict", ""),
                })
                _write_final_snapshot(layout, run_id)
                return RunResult(
                    report=None,
                    worker_outputs=dict(final_state.get("worker_outputs", {})),
                    run_dir=str(run_dir),
                    pending_approval=True,
                    langgraph_thread_id=run_id,
                )

    except Exception:
        logger.exception("Pipeline execution failed for run %s", run_id)
        store.emit_event(
            "run_failed",
            {"run_id": run_id, "error": "pipeline execution failed"},
            run_id=run_id,
        )
        # Update telemetry run on failure (non-fatal)
        _update_telemetry_run(
            telemetry_client, telemetry_event_id, "failure",
            run_start_time, error_summary="pipeline execution failed",
        )
        _flush_telemetry(telemetry_client)
        _write_final_snapshot(layout, run_id)
        return RunResult(report=EvaluationReport(verdict=Verdict.NO_GO), run_dir=str(run_dir))

    # -- Collect all worker outputs ------------------------------------------
    all_outputs = dict(final_state.get("worker_outputs", {}))

    # -- Extract evaluation report (if present) ------------------------------
    eval_output = all_outputs.get("evaluate")
    if eval_output:
        try:
            report = EvaluationReport.model_validate(eval_output)
        except Exception:
            logger.exception("Failed to parse evaluation output")
            report = EvaluationReport(verdict=Verdict.NO_GO)
    else:
        report = None

    # -- Persist final report (if available) ---------------------------------
    if report is not None:
        store.write_json(
            "evaluation_report.json",
            report.model_dump(mode="json"),
        )

    # -- Log errors if any ---------------------------------------------------
    errors = final_state.get("errors", [])
    if errors:
        logger.warning("Run %s completed with %d error(s):", run_id, len(errors))
        for err in errors:
            logger.warning("  - %s", err)

    _write_final_snapshot(layout, run_id)

    # -- Auto-promote to deploy/ (non-fatal) ---------------------------------
    try:
        from launcher.deploy.promoter import promote_run as _promote_run

        # run_dir is runs/{run_id}; parent is runs/; parent.parent is project root
        project_root = run_dir.parent.parent
        deploy_dir = project_root / "deploy"
        promo = _promote_run(
            run_dir,
            deploy_dir,
            snapshots_dir=project_root / "snapshots",
            phase_store_dir=project_root / "phase_store",
        )
        if promo.promoted > 0:
            logger.info("Auto-promoted %d page(s) to %s", promo.promoted, deploy_dir)
        store.write_json("promotion_report.json", promo.model_dump(mode="json"))
    except Exception:
        logger.warning("Auto-promotion failed (non-fatal)", exc_info=True)

    # -- Derive pipeline metrics (non-fatal) ---------------------------------
    try:
        from launcher.shared.metrics_calculator import calculate_pipeline_metrics

        pipeline_metrics = calculate_pipeline_metrics(layout.events_file)
        store.write_json("pipeline_metrics.json", pipeline_metrics)
    except Exception:
        logger.warning("Pipeline metrics calculation failed (non-fatal)", exc_info=True)

    # -- Finalize telemetry (non-fatal) --------------------------------------
    status = "success" if not errors else "partial"
    _update_telemetry_run(
        telemetry_client, telemetry_event_id, status,
        run_start_time,
        output_summary=f"workers={sorted(all_outputs.keys())}",
        items_discovered=len(all_outputs),
        items_succeeded=len([w for w in all_outputs if w not in (errors or [])]),
    )
    _flush_telemetry(telemetry_client)

    logger.info(
        "Run %s finished. stopped_after=%s, workers_completed=%s",
        run_id,
        stop_after or "(full)",
        sorted(all_outputs.keys()),
    )
    return RunResult(
        report=report,
        worker_outputs=all_outputs,
        stopped_after=stop_after,
        run_dir=str(run_dir),
    )
