"""Build a LangGraph StateGraph from pipeline.yaml and registered workers.

This module is the heart of Rule 9 (config-driven pipeline): the YAML
file defines topology, and this builder wires it into a compiled graph
with schema validation at every boundary, event emission, checkpoint
writes, and conditional re-run routing.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from langgraph.graph import END, StateGraph

from launcher.io.schema_validation import load_schema, validate
from launcher.models.base import LauncherBaseModel
from launcher.models.run_config import RunConfig

from .state import PipelineGraphState
from .worker_contract import SelfReviewResult, WorkerContext, WorkerContract

# Map worker names to their expected input model types.
# Workers that read from context.config (not input_data) use None.
_WORKER_INPUT_MODELS: dict[str, type[LauncherBaseModel] | None] = {}


def _resolve_input_model(worker_name: str) -> type[LauncherBaseModel] | None:
    """Lazily resolve the input model for a worker."""
    if worker_name in _WORKER_INPUT_MODELS:
        return _WORKER_INPUT_MODELS[worker_name]

    model: type[LauncherBaseModel] | None = None
    try:
        if worker_name == "intake":
            model = RunConfig
        elif worker_name == "understand":
            from launcher.models.intake import IntakeBundle
            model = IntakeBundle
        elif worker_name == "planner":
            from launcher.models.understanding import UnderstandingBundle
            model = UnderstandingBundle
        elif worker_name == "generate":
            from launcher.models.plan import PlanBundle
            model = PlanBundle
        elif worker_name == "evaluate":
            from launcher.models.content import ContentManifest
            model = ContentManifest
        elif worker_name == "publish":
            from launcher.models.evaluation import EvaluationReport
            model = EvaluationReport
    except ImportError:
        pass

    _WORKER_INPUT_MODELS[worker_name] = model
    return model

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal representation of a pipeline.yaml worker entry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WorkerEntry:
    """Parsed representation of one entry in pipeline.yaml ``pipeline:``."""

    name: str
    input_schema: str
    output_schema: str
    checkpoint: bool = True
    optional: bool = False
    requires_verdict: str = ""
    re_run_targets: list[str] = field(default_factory=list)
    max_re_runs: int = 2


@dataclass(frozen=True)
class PipelineTopology:
    """Complete parsed pipeline.yaml."""

    version: str
    workers: list[WorkerEntry]
    defaults: dict[str, Any]


# ---------------------------------------------------------------------------
# YAML loader
# ---------------------------------------------------------------------------


def load_pipeline_config(config_path: Path) -> PipelineTopology:
    """Parse ``pipeline.yaml`` into a ``PipelineTopology``."""
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    if raw.get("version") != "2.0":
        raise ValueError(
            f"Unsupported pipeline version: {raw.get('version')} (expected 2.0)"
        )

    defaults = raw.get("defaults", {})
    workers: list[WorkerEntry] = []

    for entry in raw["pipeline"]:
        workers.append(
            WorkerEntry(
                name=entry["worker"],
                input_schema=entry["input_schema"],
                output_schema=entry["output_schema"],
                checkpoint=entry.get("checkpoint", True),
                optional=entry.get("optional", False),
                requires_verdict=entry.get("requires_verdict", ""),
                re_run_targets=entry.get("re_run_targets", []),
                max_re_runs=entry.get("max_re_runs", defaults.get("max_re_runs", 2)),
            )
        )

    return PipelineTopology(
        version=raw["version"],
        workers=workers,
        defaults=defaults,
    )


# ---------------------------------------------------------------------------
# Schema-validated node wrapper
# ---------------------------------------------------------------------------


def _resolve_schema(schema_name: str, schema_dir: Path) -> dict[str, Any] | None:
    """Load a JSON schema file, or return None if it doesn't exist yet."""
    schema_path = schema_dir / schema_name
    if schema_path.is_file():
        return load_schema(schema_path)
    logger.warning("Schema file not found, skipping validation: %s", schema_path)
    return None


def _find_input_data(
    state: PipelineGraphState,
    entry: WorkerEntry,
    worker_order: list[str],
) -> dict[str, Any]:
    """Resolve the input dict for a worker from the graph state.

    The input is the output of the immediate predecessor worker.
    Only searches workers that precede this one in the pipeline order.
    """
    # Find position of current worker in order.
    try:
        idx = worker_order.index(entry.name)
    except ValueError:
        idx = len(worker_order)

    # Walk backwards through workers before this one.
    for prev_name in reversed(worker_order[:idx]):
        if prev_name in state["worker_outputs"]:
            return state["worker_outputs"][prev_name]

    # Fallback: first worker reads from config.
    return state["config"]


def _make_worker_node(
    entry: WorkerEntry,
    worker: WorkerContract,
    schema_dir: Path,
    worker_order: list[str],
    telemetry_client: Any | None = None,
    telemetry_trace_id: str = "",
):
    """Return a LangGraph node function for *worker*."""

    input_schema = _resolve_schema(entry.input_schema, schema_dir)
    output_schema = _resolve_schema(entry.output_schema, schema_dir)

    async def _node(state: PipelineGraphState) -> dict[str, Any]:
        """Execute one worker node in the pipeline graph.

        Exit paths (in order):
        1. Skip — output already in worker_outputs AND re_run_count == 0 (resume mode).
           Populated by _build_resume_state() from {worker}_checkpoint.json files.
        2. Skip — prior worker left errors in state["errors"].
        3. Full execution — validate input → run → self_review → validate output → checkpoint.
        """
        worker_name = entry.name
        run_dir = Path(state["run_dir"])

        logger.info("[%s] Starting worker: %s", state["run_id"], worker_name)

        # -- build context ---------------------------------------------------
        run_config = RunConfig.model_validate(state["config"])
        schemas_dir_path = schema_dir if schema_dir.is_dir() else None
        # TC-3881 Wave 3 (H9, H10): Extract heal_target_pages and eval_fast_path
        # from heal_metadata so evaluate worker can skip non-target pages and
        # skip Phase B LLM review on non-final heal steps.
        _hm = state.get("heal_metadata") or {}
        _heal_target_pages: list[str] | None = _hm.get("target_pages") or None
        _eval_fast_path: bool = bool(_hm.get("eval_fast_path", False))
        ctx = WorkerContext(
            run_id=state["run_id"],
            run_dir=run_dir,
            config=run_config,
            schemas_dir=schemas_dir_path,
            telemetry_client=telemetry_client,
            telemetry_trace_id=telemetry_trace_id,
            heal_metadata=_hm,
            heal_target_pages=_heal_target_pages,
            eval_fast_path=_eval_fast_path,
        )

        # -- skip if output already cached (resume mode, first pass only) -------
        # worker_outputs is populated by _build_resume_state() (run_loop.py) from
        # {worker}_checkpoint.json files before the graph executes on resume.
        #
        # Guard: re_run_count == 0 only.
        # When re_run_count > 0, the evaluate→__re_run__→generate loop is active;
        # worker_outputs may hold a stale first-pass output and MUST NOT block the
        # re-run target from producing fresh output.
        #
        # NOTE: _build_resume_state always initialises re_run_count=0 (run_loop.py).
        # If a caller sets re_run_count > 0 in the initial state, this guard is silently
        # disabled — all workers will execute regardless of worker_outputs content.
        #
        # Value guard: key existence alone is not sufficient — a None value means the
        # checkpoint was never valid. Only a non-None dict is trusted for skip.
        _cached_output = (state.get("worker_outputs") or {}).get(worker_name)
        if state.get("re_run_count", 0) == 0 and _cached_output is not None:
            logger.info(
                "[%s] Skipping %s — cached output found in worker_outputs",
                state["run_id"], worker_name,
            )
            ctx.emit_event(
                "worker_skipped",
                {
                    "worker": worker_name,
                    "reason": "resume_checkpoint",
                    "re_run_count": state.get("re_run_count", 0),
                },
                worker=worker_name,
            )
            return {"current_worker": worker_name}

        # -- skip if predecessor left errors (no valid output to consume) ----
        if state["errors"]:
            logger.warning(
                "[%s] Skipping %s due to prior errors: %s",
                state["run_id"], worker_name, state["errors"],
            )
            return {
                "current_worker": worker_name,
                "errors": state["errors"],
            }

        # -- resolve input ---------------------------------------------------
        input_dict = _find_input_data(state, entry, worker_order)

        # -- validate input against schema -----------------------------------
        if input_schema is not None:
            validate(input_dict, input_schema, context=f"{worker_name}.input")

        # -- emit worker_started event ---------------------------------------
        ctx.emit_event(
            "worker_started",
            {"worker": worker_name, "re_run_count": state["re_run_count"]},
            worker=worker_name,
        )

        # -- invoke worker ---------------------------------------------------
        try:
            # Deserialise input_dict into the worker's expected model type
            # so isinstance checks inside worker.run() succeed.
            input_model_cls = _resolve_input_model(worker_name)
            if input_model_cls is not None:
                try:
                    typed_input = input_model_cls.model_validate(input_dict)
                except Exception:
                    typed_input = _DictProxy.model_validate(input_dict)  # type: ignore[assignment]
            else:
                typed_input = _DictProxy.model_validate(input_dict)  # type: ignore[assignment]

            output_model = await worker.run(
                typed_input,  # type: ignore[arg-type]
                ctx,
            )
        except Exception as exc:
            logger.exception("[%s] Worker %s failed", state["run_id"], worker_name)
            return {
                "current_worker": worker_name,
                "errors": [*state["errors"], f"{worker_name}: {exc!s}"],
            }

        # -- self-review (Rule 1) -------------------------------------------
        review: SelfReviewResult = await worker.self_review(output_model)
        if not review.passed:
            logger.warning(
                "[%s] Self-review FAILED for %s: %s",
                state["run_id"],
                worker_name,
                review.findings,
            )
            return {
                "current_worker": worker_name,
                "errors": [
                    *state["errors"],
                    f"{worker_name}: self-review failed: {review.findings}",
                ],
            }

        # -- serialise output ------------------------------------------------
        output_dict: dict[str, Any]
        if isinstance(output_model, LauncherBaseModel):
            output_dict = output_model.model_dump(mode="json")
        elif isinstance(output_model, dict):
            output_dict = output_model
        else:
            output_dict = json.loads(output_model.model_dump_json())  # type: ignore[union-attr]

        # -- validate output against schema ----------------------------------
        if output_schema is not None:
            validate(output_dict, output_schema, context=f"{worker_name}.output")

        # -- checkpoint (if enabled) -----------------------------------------
        if entry.checkpoint:
            artifact_file = f"{worker_name}_checkpoint.json"
            ctx.store.write_json(artifact_file, output_dict)
            artifact_path = run_dir / artifact_file
            content_hash = ""
            checkpoint_id = ""
            try:
                from launcher.resilience.checkpoint import write_worker_checkpoint
                wcp = write_worker_checkpoint(
                    run_dir=run_dir,
                    worker=worker_name,
                    artifact_path=artifact_path,
                )
                content_hash = wcp.content_hash
                checkpoint_id = wcp.checkpoint_id
            except Exception:
                logger.warning(
                    "[%s] Worker checkpoint write failed for %s",
                    state["run_id"],
                    worker_name,
                )
            ctx.emit_event(
                "checkpoint_written",
                {
                    "worker": worker_name,
                    "artifact_path": str(artifact_path),
                    "content_hash": content_hash,
                    "checkpoint_id": checkpoint_id,
                },
                worker=worker_name,
            )

        # -- emit worker_completed event -------------------------------------
        ctx.emit_event(
            "worker_completed",
            {
                "worker": worker_name,
                "self_review_passed": review.passed,
                "self_review_metrics": review.metrics,
            },
            worker=worker_name,
        )

        logger.info("[%s] Worker %s completed", state["run_id"], worker_name)

        # -- update graph state ----------------------------------------------
        updated_outputs = {**state["worker_outputs"], worker_name: output_dict}
        result: dict[str, Any] = {
            "current_worker": worker_name,
            "worker_outputs": updated_outputs,
        }

        # Propagate verdict from evaluate worker to top-level state
        # so _should_re_run can read it for conditional routing.
        if worker_name == "evaluate" and "verdict" in output_dict:
            result["verdict"] = output_dict["verdict"]

        return result

    _node.__name__ = f"node_{entry.name}"
    _node.__qualname__ = f"node_{entry.name}"
    return _node


class _DictProxy(LauncherBaseModel):
    """Thin wrapper so dict input can be passed as LauncherBaseModel.

    Workers that need a concrete type should validate/parse inside their
    own ``run()`` method.  This proxy simply carries the raw dict through
    the abstract interface.

    Note: model_config override allows extra fields since this is a
    pass-through container.
    """

    model_config = {"extra": "allow", "frozen": False}  # type: ignore[assignment]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> _DictProxy:
        return cls.model_validate(data)


# ---------------------------------------------------------------------------
# Conditional edge helpers
# ---------------------------------------------------------------------------


def _make_should_re_run(max_re_runs: int):
    """Factory for the evaluate→re-run conditional edge function.

    Captures ``max_re_runs`` from the pipeline topology (WorkerEntry) so
    that the routing decision is consistent with pipeline.yaml rather than
    the state field (which always defaults to 2 in run_loop.py).

    Returns the name of the next node: a re-run target, 'publish', or END.
    """

    def _should_re_run(state: PipelineGraphState) -> str:
        verdict = state.get("verdict", "")
        re_run_count = state.get("re_run_count", 0)

        if verdict == "GO":
            return "publish"

        if re_run_count < max_re_runs and verdict == "NO_GO":
            return "__re_run__"

        # Exhausted re-runs (or max_re_runs==0) or unexpected verdict -> end
        return END

    return _should_re_run


def _make_post_evaluate_router(max_re_runs: int):
    """Replace _make_should_re_run: routes to __advisor__ when NO_GO (below ceiling).

    GO -> "publish"
    NO_GO + re_run_count < max_re_runs AND max_re_runs > 0 -> "__advisor__"
    Otherwise -> END (ceiling reached, or feature disabled when max_re_runs == 0)
    """
    def _post_evaluate(state: "PipelineGraphState") -> str:
        if state.get("verdict") == "GO":
            return "publish"
        re_run_count = state.get("re_run_count", 0)
        if max_re_runs > 0 and re_run_count < max_re_runs:
            return "__advisor__"
        return END

    return _post_evaluate


def _make_advisor_route(workers: dict):
    """Route __advisor__ output: heal_generate -> __re_run__, publish -> publish, else END.

    NOTE: "heal_upstream" excluded in v1. Only heal_generate, publish, stop.
    """
    def _advisor_route(state: "PipelineGraphState") -> str:
        routing = (state.get("advisor_decision") or {}).get("routing", "stop")
        if routing == "heal_generate":
            return "__re_run__"
        if routing == "publish":
            return "publish" if "publish" in workers else END
        return END  # "stop" or any unknown value

    return _advisor_route


def _verdict_gate(state: PipelineGraphState) -> str:
    """Guard for publish: only proceed when verdict is GO."""
    if state.get("verdict", "") == "GO":
        return "publish"
    return END


# ---------------------------------------------------------------------------
# Graph builder — the main public API
# ---------------------------------------------------------------------------


def build_pipeline(
    config_path: Path,
    workers: dict[str, WorkerContract],
    *,
    schema_dir: Path | None = None,
    stop_after: str | None = None,
    telemetry_client: Any | None = None,
    telemetry_trace_id: str = "",
    checkpointer: Any | None = None,
    interrupt_before: list[str] | None = None,
) -> Any:
    """Read pipeline.yaml and build a compiled LangGraph StateGraph.

    Parameters
    ----------
    config_path:
        Path to ``pipeline.yaml``.
    workers:
        Mapping of worker name -> WorkerContract implementation.
    schema_dir:
        Directory containing JSON schema files.  If ``None``, derived
        from the ``defaults.schema_dir`` key in pipeline.yaml relative
        to the config file's parent.

    Returns
    -------
    A compiled LangGraph ``CompiledStateGraph`` ready for invocation.
    """
    topology = load_pipeline_config(config_path)

    # Resolve schema directory.
    if schema_dir is None:
        relative = topology.defaults.get("schema_dir", "specs/schemas")
        schema_dir = (config_path.parent.parent / relative).resolve()

    # Truncate pipeline if stop_after is set.
    if stop_after:
        worker_names = [e.name for e in topology.workers]
        if stop_after not in worker_names:
            raise ValueError(
                f"stop_after='{stop_after}' is not a valid worker. "
                f"Valid workers: {worker_names}"
            )
        cut = worker_names.index(stop_after) + 1
        topology = PipelineTopology(
            version=topology.version,
            workers=topology.workers[:cut],
            defaults=topology.defaults,
        )

    # Validate that every pipeline entry has a registered worker.
    for entry in topology.workers:
        if not entry.optional and entry.name not in workers:
            raise ValueError(
                f"Pipeline requires worker '{entry.name}' but it was not registered. "
                f"Registered workers: {sorted(workers.keys())}"
            )

    worker_order = [e.name for e in topology.workers]

    # -- Build the graph ----------------------------------------------------
    graph = StateGraph(PipelineGraphState)

    # Find the evaluate entry for re-run routing.
    evaluate_entry: WorkerEntry | None = None
    re_run_first_target: str | None = None

    # Pre-scan to find evaluate_entry before building nodes (needed for closure).
    for entry in topology.workers:
        if entry.re_run_targets:
            evaluate_entry = entry
            re_run_first_target = entry.re_run_targets[0] if entry.re_run_targets else None

    # Build the post-evaluate routing function with max_re_runs captured from topology.
    _post_evaluate_router = _make_post_evaluate_router(
        evaluate_entry.max_re_runs if evaluate_entry is not None else 0
    )

    # Reset for the node-building loop below.
    evaluate_entry = None
    re_run_first_target = None

    for entry in topology.workers:
        if entry.name not in workers:
            if entry.optional:
                continue
            # Already validated above; this is a safety net.
            raise ValueError(f"Missing required worker: {entry.name}")

        worker = workers[entry.name]
        node_fn = _make_worker_node(
            entry, worker, schema_dir, worker_order,
            telemetry_client=telemetry_client,
            telemetry_trace_id=telemetry_trace_id,
        )
        graph.add_node(entry.name, node_fn)

        if entry.re_run_targets:
            evaluate_entry = entry
            re_run_first_target = entry.re_run_targets[0] if entry.re_run_targets else None

    # -- Wire sequential edges ----------------------------------------------
    active_workers = [e.name for e in topology.workers if e.name in workers]

    # -- Heal bypass routing (H5.2) -----------------------------------------
    # When heal_metadata.responsible_worker == "generate", route past Understand
    # and Planner directly to Generate by loading their checkpoints from disk.
    _gen_idx = active_workers.index("generate") if "generate" in active_workers else -1
    _bypass_candidates: list[str] = (
        [w for w in active_workers[:_gen_idx] if w in ("understand", "planner")]
        if _gen_idx > 0
        else []
    )
    _has_heal_bypass = bool(_bypass_candidates)

    if _has_heal_bypass:

        async def _heal_router_node(state: PipelineGraphState) -> dict[str, Any]:
            """Entry node: load Understand/Planner checkpoints when heal bypass is active.

            This bypass (responsible_worker == 'generate') is an optimization: it routes
            via conditional edges past understand/planner entirely, avoiding even their ctx
            build overhead. Since TC-3869, the skip guard in _node() provides the same
            correctness guarantee for all resume_from values — this bypass is now partially
            redundant but kept for performance on the common generate-heal path.
            """
            heal_meta: dict[str, Any] = state.get("heal_metadata") or {}
            if heal_meta.get("responsible_worker") != "generate":
                return {}

            run_dir = Path(state["run_dir"])
            loaded: dict[str, Any] = {}

            for wname in _bypass_candidates:
                ckpt_file = run_dir / f"{wname}_checkpoint.json"
                if not ckpt_file.is_file():
                    logger.warning(
                        "[%s] Heal bypass: no checkpoint for %s — falling back to full pipeline",
                        state["run_id"],
                        wname,
                    )
                    loaded = {}
                    break
                try:
                    loaded[wname] = json.loads(ckpt_file.read_text(encoding="utf-8"))
                    logger.info(
                        "[%s] Heal bypass: loaded checkpoint for %s",
                        state["run_id"],
                        wname,
                    )
                except Exception:
                    logger.warning(
                        "[%s] Heal bypass: failed to read checkpoint for %s — falling back",
                        state["run_id"],
                        wname,
                    )
                    loaded = {}
                    break

            if not loaded:
                return {}

            # Emit worker_skipped events and inject checkpoint data.
            run_config = RunConfig.model_validate(state["config"])
            schemas_dir_path = schema_dir if schema_dir is not None and schema_dir.is_dir() else None
            _ctx = WorkerContext(
                run_id=state["run_id"],
                run_dir=run_dir,
                config=run_config,
                schemas_dir=schemas_dir_path,
                telemetry_client=telemetry_client,
                telemetry_trace_id=telemetry_trace_id,
                heal_metadata=heal_meta,
            )
            for wname in _bypass_candidates:
                _ctx.emit_event(
                    "worker_skipped",
                    {"worker": wname, "reason": "heal_bypass", "responsible_worker": "generate"},
                    worker=wname,
                )

            updated_outputs = {**state["worker_outputs"], **loaded}
            updated_heal_meta = {**heal_meta, "_bypass_active": True}
            return {
                "worker_outputs": updated_outputs,
                "heal_metadata": updated_heal_meta,
            }

        def _heal_route(state: PipelineGraphState) -> str:
            heal_meta: dict[str, Any] = state.get("heal_metadata") or {}
            if heal_meta.get("_bypass_active"):
                return "generate"
            return active_workers[0]

        graph.add_node("__heal_router__", _heal_router_node)
        graph.add_conditional_edges(
            "__heal_router__",
            _heal_route,
            {"generate": "generate", active_workers[0]: active_workers[0]},
        )
        graph.set_entry_point("__heal_router__")
    elif active_workers:
        # Set entry point.
        graph.set_entry_point(active_workers[0])

    for i, wname in enumerate(active_workers[:-1]):
        next_name = active_workers[i + 1]
        entry = next((e for e in topology.workers if e.name == wname), None)

        if entry and entry.re_run_targets:
            # Evaluate node -> conditional routing via post-evaluate router.
            # IMPORTANT: "__re_run__" must map to the "__re_run__" increment node,
            # NOT directly to re_run_first_target. The increment node bumps
            # re_run_count before routing to the target — bypassing it causes
            # re_run_count to stay 0 forever, triggering the skip guard on every
            # worker and producing an infinite loop (TC-3892).
            # When max_re_runs > 0, route through __advisor__ which then routes to
            # __re_run__ (heal_generate), publish, or END.
            _edge_map = {
                "publish": "publish" if "publish" in workers else END,
                END: END,
            }
            if evaluate_entry is not None and evaluate_entry.max_re_runs > 0:
                _edge_map["__advisor__"] = "__advisor__"
            graph.add_conditional_edges(wname, _post_evaluate_router, _edge_map)
        elif next_name == "publish" and any(
            e.requires_verdict for e in topology.workers if e.name == next_name
        ):
            # publish requires_verdict=GO -> conditional gate.
            graph.add_conditional_edges(
                wname,
                _verdict_gate,
                {"publish": "publish", END: END},
            )
        else:
            graph.add_edge(wname, next_name)

    # Terminal node -> END.
    if active_workers:
        last = active_workers[-1]
        # Only add edge to END if we haven't already set conditional edges.
        last_entry = next((e for e in topology.workers if e.name == last), None)
        if last_entry and not last_entry.re_run_targets:
            graph.add_edge(last, END)

    # -- Add the re-run increment node -------------------------------------
    if evaluate_entry and re_run_first_target:

        async def _re_run_increment(state: PipelineGraphState) -> dict[str, Any]:
            """Bump re_run_count before re-entering the loop."""
            new_count = state.get("re_run_count", 0) + 1
            logger.info(
                "[%s] Re-run #%d triggered (max %d)",
                state["run_id"],
                new_count,
                state.get("max_re_runs", 2),
            )
            return {"re_run_count": new_count}

        graph.add_node("__re_run__", _re_run_increment)
        graph.add_edge("__re_run__", re_run_first_target)

    # -- Add the __advisor__ LLM routing node (only when max_re_runs > 0) ---
    if evaluate_entry is not None and evaluate_entry.max_re_runs > 0:

        async def _advisor_node(state: "PipelineGraphState") -> dict:
            """LLM routing advisor — decides next step after NO_GO evaluation."""
            from launcher.orchestrator.pipeline_advisor import (
                call_pipeline_advisor,
                _static_fallback,
            )
            from launcher.models.evaluation import EvaluationReport

            run_dir_path = Path(state["run_dir"])
            re_run_count = state.get("re_run_count", 0)
            max_re = evaluate_entry.max_re_runs

            eval_output = (state.get("worker_outputs") or {}).get("evaluate")
            if not eval_output:
                advice = _static_fallback(re_run_count, max_re)
            else:
                try:
                    report = EvaluationReport.model_validate(eval_output)
                    advice = call_pipeline_advisor(report, re_run_count, max_re, run_dir_path)
                except Exception:
                    logger.warning("Advisor: failed to load eval report, using fallback")
                    advice = _static_fallback(re_run_count, max_re)

            # Merge into heal_metadata for downstream workers
            updated_heal = {
                **(state.get("heal_metadata") or {}),
                "advisor_routing": advice.routing,
                "target_pages": advice.target_pages,
                "strategy": advice.strategy,
                "priority_checks": advice.priority_checks,
            }

            return {
                "advisor_decision": advice.model_dump(mode="json"),
                "heal_metadata": updated_heal,
            }

        graph.add_node("__advisor__", _advisor_node)
        graph.add_conditional_edges(
            "__advisor__",
            _make_advisor_route(workers),
            {
                "__re_run__": "__re_run__",
                "publish": "publish" if "publish" in workers else END,
                END: END,
            },
        )

    # -- Compile and return --------------------------------------------------
    return graph.compile(
        checkpointer=checkpointer,
        interrupt_before=interrupt_before or [],
    )
