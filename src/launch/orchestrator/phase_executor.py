"""Phase group executor — compose resume calls into logical pipeline phases.

Maps the 11-worker pipeline (W1-W11) into 6 logical phase groups (P1-P6)
and provides sequential execution of individual phases or contiguous ranges.

Phase groups:
- P1: W1-W2  (Repo ingestion + facts)
- P2: W3-W4  (Snippets + page planning)
- P3: W5-W6  (Drafting + SEO)
- P4: W7-W8  (Review + linking)
- P5: W9-W10 (Validation + fixing)
- P6: W11    (PR/packaging)

Each phase calls ``execute_run_from_node()`` for the first worker in its
group.  The LangGraph pipeline naturally executes subsequent workers in
sequence until it reaches a state boundary.

Spec references:
- specs/43_resumable_pipeline.md (RESUME_NODE_MAP, execute_run_from_node)
- specs/21_worker_contracts.md (Worker I/O contracts / phase boundaries)
- specs/40_storage_model.md (Artifact paths per worker)
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from launch.models.event import Event
from launch.state.event_log import (
    append_event,
    generate_event_id,
    generate_span_id,
    generate_trace_id,
)

from .phase_verifier import PhaseVerificationResult
from .run_loop import RunResult, execute_run_from_node

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Mapping of phase identifiers to the worker aliases they contain.
#: Tuples are ordered — the first element is the graph entry point for the phase.
PHASE_GROUPS: Dict[str, tuple] = {
    "P1": ("W1", "W2"),
    "P2": ("W3", "W4"),
    "P3": ("W5", "W6"),
    "P4": ("W7", "W8"),
    "P5": ("W9", "W10"),
    "P6": ("W11",),
}

#: Ordered list of phase identifiers (for range iteration).
_PHASE_ORDER: List[str] = ["P1", "P2", "P3", "P4", "P5", "P6"]

#: Event type constants for phase boundary events.
EVENT_PHASE_STARTED = "PHASE_STARTED"
EVENT_PHASE_COMPLETED = "PHASE_COMPLETED"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class PhaseResult:
    """Result of executing a single phase group.

    Designed for JSON serialisation so downstream taskcards (TC-2504)
    can aggregate results into ``phase_report.json``.
    """

    phase_id: str
    workers: List[str] = field(default_factory=list)
    ok: bool = True
    error: Optional[str] = None
    started_at_utc: str = ""
    finished_at_utc: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Return a plain dict suitable for ``json.dumps``."""
        return asdict(self)


# ---------------------------------------------------------------------------
# Phase-level event helpers
# ---------------------------------------------------------------------------


def _emit_phase_event(
    run_dir: Path,
    run_id: str,
    event_type: str,
    payload: Dict[str, Any],
    trace_id: str,
    parent_span_id: str,
) -> None:
    """Emit a PHASE_STARTED / PHASE_COMPLETED event to events.ndjson.

    Follows the same pattern used by ``run_loop.py`` for RUN_STATE_CHANGED events.
    """
    event = Event(
        event_id=generate_event_id(),
        run_id=run_id,
        ts=datetime.now(timezone.utc).isoformat(),
        type=event_type,
        payload=payload,
        trace_id=trace_id,
        span_id=generate_span_id(),
        parent_span_id=parent_span_id,
    )
    try:
        append_event(run_dir / "events.ndjson", event)
    except Exception:
        logger.warning("Failed to emit %s event for %s", event_type, run_id)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def execute_phase_group(
    run_id: str,
    run_dir: Path,
    run_config: Dict[str, Any],
    phase_id: str,
) -> PhaseResult:
    """Execute a single phase group by delegating to ``execute_run_from_node()``.

    Args:
        run_id:     Existing run identifier.
        run_dir:    Existing run directory with prior artifacts.
        run_config: Validated run configuration dict.
        phase_id:   Phase identifier (``"P1"`` through ``"P6"``).

    Returns:
        :class:`PhaseResult` with status, timing, and worker list.

    Raises:
        ValueError: If *phase_id* is not a valid key in :data:`PHASE_GROUPS`.
    """
    if phase_id not in PHASE_GROUPS:
        valid = ", ".join(_PHASE_ORDER)
        raise ValueError(
            f"Unknown phase_id '{phase_id}'. Valid phases: {valid}"
        )

    workers = list(PHASE_GROUPS[phase_id])
    entry_worker = workers[0]

    # Timing and trace context
    started_at = datetime.now(timezone.utc).isoformat()
    trace_id = generate_trace_id()
    parent_span_id = generate_span_id()

    # Emit PHASE_STARTED event
    _emit_phase_event(
        run_dir=run_dir,
        run_id=run_id,
        event_type=EVENT_PHASE_STARTED,
        payload={
            "phase_id": phase_id,
            "workers": workers,
            "entry_worker": entry_worker,
        },
        trace_id=trace_id,
        parent_span_id=parent_span_id,
    )

    logger.info(
        "phase_group_started phase=%s workers=%s entry=%s",
        phase_id,
        workers,
        entry_worker,
    )

    result = PhaseResult(
        phase_id=phase_id,
        workers=workers,
        started_at_utc=started_at,
    )

    try:
        run_result: RunResult = execute_run_from_node(
            run_id=run_id,
            run_dir=run_dir,
            run_config=run_config,
            from_worker=entry_worker,
        )
        # Treat non-zero exit codes as failure
        if run_result.exit_code != 0:
            result.ok = False
            result.error = (
                f"Phase {phase_id} finished with exit_code={run_result.exit_code} "
                f"(final_state={run_result.final_state})"
            )
    except Exception as exc:
        result.ok = False
        result.error = f"{type(exc).__name__}: {exc}"

    result.finished_at_utc = datetime.now(timezone.utc).isoformat()

    # Emit PHASE_COMPLETED event
    _emit_phase_event(
        run_dir=run_dir,
        run_id=run_id,
        event_type=EVENT_PHASE_COMPLETED,
        payload={
            "phase_id": phase_id,
            "ok": result.ok,
            "error": result.error,
            "workers": workers,
        },
        trace_id=trace_id,
        parent_span_id=parent_span_id,
    )

    logger.info(
        "phase_group_completed phase=%s ok=%s elapsed=%s..%s",
        phase_id,
        result.ok,
        result.started_at_utc,
        result.finished_at_utc,
    )

    return result


def execute_phase_range(
    run_id: str,
    run_dir: Path,
    run_config: Dict[str, Any],
    start_phase: str,
    end_phase: str,
) -> List[PhaseResult]:
    """Execute a contiguous range of phase groups sequentially.

    Iterates from *start_phase* through *end_phase* (inclusive), calling
    :func:`execute_phase_group` for each.  Stops on the first failure
    (fail-fast).

    Args:
        run_id:      Existing run identifier.
        run_dir:     Existing run directory with prior artifacts.
        run_config:  Validated run configuration dict.
        start_phase: First phase to execute (e.g. ``"P1"``).
        end_phase:   Last phase to execute (e.g. ``"P3"``).

    Returns:
        List of :class:`PhaseResult` objects (one per executed phase).

    Raises:
        ValueError: If either phase identifier is unknown or if
            *end_phase* precedes *start_phase*.
    """
    # Validate both identifiers
    for pid in (start_phase, end_phase):
        if pid not in PHASE_GROUPS:
            valid = ", ".join(_PHASE_ORDER)
            raise ValueError(
                f"Unknown phase_id '{pid}'. Valid phases: {valid}"
            )

    start_idx = _PHASE_ORDER.index(start_phase)
    end_idx = _PHASE_ORDER.index(end_phase)

    if end_idx < start_idx:
        raise ValueError(
            f"Invalid phase range: end_phase '{end_phase}' precedes "
            f"start_phase '{start_phase}'. "
            f"Phase order is: {', '.join(_PHASE_ORDER)}"
        )

    results: List[PhaseResult] = []
    for idx in range(start_idx, end_idx + 1):
        phase_id = _PHASE_ORDER[idx]
        phase_result = execute_phase_group(
            run_id=run_id,
            run_dir=run_dir,
            run_config=run_config,
            phase_id=phase_id,
        )
        results.append(phase_result)

        if not phase_result.ok:
            logger.warning(
                "phase_range_stopped phase=%s error=%s",
                phase_id,
                phase_result.error,
            )
            break

    return results


# ---------------------------------------------------------------------------
# Report writer (TC-2504)
# ---------------------------------------------------------------------------


def write_phase_report(
    run_dir: Path,
    run_id: str,
    phase_results: List[PhaseResult],
    verification_results: List[PhaseVerificationResult],
    started_at_utc: str,
    finished_at_utc: str,
) -> Path:
    """Write ``phase_report.json`` to the run artifacts directory.

    Aggregates phase execution results and artifact verification results
    into a single integrity report.  Uses :func:`atomic_write_json` for
    crash safety (TC-2470 pattern).

    Args:
        run_dir: Run directory (``artifacts/`` subdirectory will be created
            if it does not already exist).
        run_id: Run identifier (e.g. ``"r_20260225T120000Z"``).
        phase_results: Phase execution results from
            :func:`execute_phase_range` or individual
            :func:`execute_phase_group` calls.
        verification_results: Verification results from
            :func:`~launch.orchestrator.phase_verifier.verify_phase_range`.
        started_at_utc: ISO-8601 UTC timestamp when execution started.
        finished_at_utc: ISO-8601 UTC timestamp when execution finished.

    Returns:
        Absolute :class:`~pathlib.Path` to the written
        ``phase_report.json`` file.
    """
    from launch.io.atomic import atomic_write_json

    phases_ok = all(pr.ok for pr in phase_results)
    verifications_ok = all(vr.ok for vr in verification_results)
    overall_ok = phases_ok and verifications_ok

    report: Dict[str, Any] = {
        "run_id": run_id,
        "run_dir": str(run_dir),
        "overall_ok": overall_ok,
        "started_at_utc": started_at_utc,
        "finished_at_utc": finished_at_utc,
        "phases_executed": [pr.to_dict() for pr in phase_results],
        "verifications": [vr.to_dict() for vr in verification_results],
    }

    dest = run_dir / "artifacts" / "phase_report.json"
    atomic_write_json(dest, report, enforcement_mode="disabled")

    logger.info(
        "phase_report_written path=%s overall_ok=%s phases=%d verifications=%d",
        dest,
        overall_ok,
        len(phase_results),
        len(verification_results),
    )

    return dest
