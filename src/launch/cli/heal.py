"""Self-driving healing iteration for converging runs to green gates.

Implements the deterministic healing loop:
  triage -> resume from recommended worker -> re-validate -> repeat (bounded)

No LLM required. All decisions are rule-based via the triage recommendation engine.
Audit trail written to artifacts/heal_plan.json and events.ndjson.

TC-2950: Implement `launch heal` command.
Spec: plans/enhancements/self-drive-governance.md
"""

from __future__ import annotations

import json
import logging
import re
import shutil
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Event type constants (local, following _EVENT_RUN_RESUMED pattern in run_loop.py) ──
_EVENT_HEAL_STEP_STARTED = "HEAL_STEP_STARTED"
_EVENT_HEAL_STEP_COMPLETED = "HEAL_STEP_COMPLETED"
_EVENT_HEAL_STEP_REGRESSED = "HEAL_STEP_REGRESSED"
_EVENT_HEAL_STOPPED = "HEAL_STOPPED"

# Worker priority order for aggressive mode (earlier pipeline = lower number = preferred)
_WORKER_ORDER: Dict[str, int] = {
    "W1": 1, "W2": 2, "W3": 3, "W4": 4, "W5": 5,
    "W6": 6, "W7": 7, "W8": 8, "W9": 9, "W10": 10, "W11": 11,
}

_FROM_WORKER_RE = re.compile(r"--from-worker\s+(\S+)")

# ── Checkpoint constants (TC-3510) ─────────────────────────────────────────────
_CHECKPOINT_DIR_NAME = "_heal_checkpoints"
_CHECKPOINT_ARTIFACTS = ["validation_report.json", "heal_plan.json"]
_CHECKPOINT_CONTENT_DIRS = ["work/site/content", "drafts"]


# ── Data models ───────────────────────────────────────────────────────────────


@dataclass
class HealStep:
    """Record of a single healing iteration step."""

    step_idx: int
    chosen_worker: str
    reason: str
    triage_snapshot: List[Dict[str, str]]
    failed_gate_count_before: int
    failed_gate_count_after: int = -1
    exit_code: int = -1
    notes: str = ""


@dataclass
class HealResult:
    """Complete healing iteration audit trail."""

    run_id: str
    mode: str
    max_steps: int
    steps: List[HealStep] = field(default_factory=list)
    stop_reason: str = ""
    final_failed_gate_count: int = -1
    started_at_utc: str = ""
    finished_at_utc: str = ""


# ── Helper functions ──────────────────────────────────────────────────────────


def _win_path(p: Path) -> Path:
    """Prefix path with \\\\?\\\\ on Windows to bypass MAX_PATH (260-char) limit.

    Idempotent: paths already prefixed are returned unchanged.
    No-op on Linux/macOS.

    TC-3570: Required for checkpoint create/restore on deep blog content paths.
    """
    if sys.platform != "win32":
        return p
    s = str(p.resolve())
    if s.startswith("\\\\?\\"):
        return Path(s)
    if s.startswith("\\\\"):
        # UNC path (e.g. \\server\share) → \\?\UNC\server\share
        return Path("\\\\?\\UNC\\" + s[2:])
    return Path("\\\\?\\" + s)


def extract_worker_from_recommendation(rec: Dict[str, str]) -> str:
    """Extract the --from-worker value from a triage recommendation command string."""
    command = rec.get("command", "")
    match = _FROM_WORKER_RE.search(command)
    if match:
        return match.group(1)
    return ""


def count_failed_gates(report: Dict[str, Any]) -> int:
    """Count gates with ok=false in a validation report."""
    return sum(1 for g in report.get("gates", []) if not g.get("ok", True))


def _deprioritize_w5(
    recommendations: List[Dict[str, str]],
    failed_gate_count: int,
) -> List[Dict[str, str]]:
    """Reorder recommendations to put W5 last when ≤4 gates are failing.

    W5 carries high regression risk (cascades into W8 patch invalidation).
    When only a few gates are failing, conservative fixes (W10/W8/W6) are
    tried first.

    Args:
        recommendations: Triage recommendations in priority order.
        failed_gate_count: Current number of failing gates.

    Returns:
        Reordered recommendations (W5 moved to end when ≤4 failing gates).
    """
    if failed_gate_count > 4:
        return recommendations  # Many gates failing — W5 stays in position

    w5_recs = [r for r in recommendations if extract_worker_from_recommendation(r) == "W5"]
    non_w5_recs = [r for r in recommendations if extract_worker_from_recommendation(r) != "W5"]
    return non_w5_recs + w5_recs


def choose_worker(
    recommendations: List[Dict[str, str]],
    mode: str,
    top_k: int,
    history: List[HealStep],
) -> Optional[Tuple[str, str]]:
    """Select the next (worker, reason) pair from triage recommendations.

    Args:
        recommendations: Triage recommendations [{command, reason}].
        mode: "strict" or "aggressive".
        top_k: Maximum number of recommendations to consider.
        history: Prior heal steps.

    Returns:
        (worker, reason) tuple, or None if stuck/no valid choice.
    """
    if not recommendations:
        return None

    candidates = recommendations[:top_k]

    if mode == "strict":
        # Strict: pick the first recommendation that hasn't crashed (exit_code=2)
        for candidate in candidates:
            worker = extract_worker_from_recommendation(candidate)
            reason = candidate.get("reason", "")
            if not worker:
                continue
            if _had_execution_error(history, worker):
                continue
            return (worker, reason)
        return None

    # Aggressive: try the first candidate; if it was already tried without
    # improvement in the last step, try the next candidate instead.
    for candidate in candidates:
        worker = extract_worker_from_recommendation(candidate)
        reason = candidate.get("reason", "")
        if not worker:
            continue
        if _was_tried_without_improvement(history, worker, reason):
            continue
        return (worker, reason)

    return None


def _was_tried_without_improvement(
    history: List[HealStep],
    worker: str,
    reason: str,
) -> bool:
    """Check if this (worker, reason) was tried in the last step with no gate improvement.

    Regressed steps (TC-3510: notes contains "regressed:") are excluded because
    the checkpoint restore returns the state to the pre-step baseline.
    """
    if not history:
        return False
    last = history[-1]
    if last.notes.startswith("regressed:"):
        # TC-3510: Regression was rolled back — don't count as "tried without improvement"
        return False
    return (
        last.chosen_worker == worker
        and last.reason == reason
        and last.failed_gate_count_after >= last.failed_gate_count_before
    )


def _had_execution_error(history: List[HealStep], worker: str) -> bool:
    """Check if this worker had exit_code=2 (execution error) in any prior step."""
    return any(
        step.chosen_worker == worker and step.exit_code == 2
        for step in history
    )


def is_stuck(history: List[HealStep], worker: str, reason: str) -> bool:
    """Detect stuck state: same (worker, reason) repeated with no improvement.

    Returns True if the same (worker, reason) pair appears in history AND
    the failed gate count did not decrease between those occurrences.

    Regressed steps (TC-3510: notes contains "regressed:") are excluded from
    stuck detection because the checkpoint restore returns the state to the
    pre-step baseline.
    """
    for step in history:
        if step.notes.startswith("regressed:"):
            # TC-3510: After regression+restore the state is back to baseline;
            # do not count these as "tried without improvement" for stuck detection.
            continue
        if (
            step.chosen_worker == worker
            and step.reason == reason
            and step.failed_gate_count_after >= step.failed_gate_count_before
        ):
            return True
    return False


# ── Event emission ────────────────────────────────────────────────────────────


def _emit_event(
    events_file: Path,
    run_id: str,
    event_type: str,
    payload: Dict[str, Any],
) -> None:
    """Append a heal event to events.ndjson."""
    from launch.models.event import Event
    from launch.state.event_log import (
        append_event,
        generate_event_id,
        generate_span_id,
        generate_trace_id,
    )

    event = Event(
        event_id=generate_event_id(),
        run_id=run_id,
        ts=datetime.now(timezone.utc).isoformat(),
        type=event_type,
        payload=payload,
        trace_id=generate_trace_id(),
        span_id=generate_span_id(),
    )
    append_event(events_file, event)


# ── Checkpoint helpers (TC-3510) ──────────────────────────────────────────────


def _create_checkpoint(run_dir: Path, step_idx: int) -> Optional[Path]:
    """Snapshot key artifacts before a heal step for potential rollback.

    Copies artifacts/ + work/site/content/ + drafts/ into
    run_dir/_heal_checkpoints/step_{step_idx}/.

    Returns checkpoint path, or None if snapshot failed.
    """
    checkpoint_dir = run_dir / _CHECKPOINT_DIR_NAME / f"step_{step_idx}"
    try:
        # TC-3570: Use _win_path() to bypass Windows MAX_PATH (260-char) limit
        _win_path(checkpoint_dir).mkdir(parents=True, exist_ok=True)
        # Copy artifacts directory
        artifacts_src = run_dir / "artifacts"
        artifacts_dst = checkpoint_dir / "artifacts"
        if artifacts_src.exists():
            if artifacts_dst.exists():
                shutil.rmtree(_win_path(artifacts_dst))
            shutil.copytree(_win_path(artifacts_src), _win_path(artifacts_dst))
        # Copy content dirs
        for dirname in _CHECKPOINT_CONTENT_DIRS:
            src = run_dir / dirname
            dst = checkpoint_dir / dirname
            if src.exists():
                if dst.exists():
                    shutil.rmtree(_win_path(dst))
                shutil.copytree(_win_path(src), _win_path(dst))
        return checkpoint_dir
    except Exception as exc:
        logger.warning("[Heal] Checkpoint creation failed at step %d: %s", step_idx, exc)
        return None


def _restore_checkpoint(run_dir: Path, checkpoint_dir: Path) -> bool:
    """Restore run_dir from a previously created checkpoint.

    Overwrites artifacts/ + work/site/content/ + drafts/ from checkpoint.
    Returns True on success, False on failure.
    """
    try:
        # TC-3570: Use _win_path() to bypass Windows MAX_PATH (260-char) limit
        # Restore artifacts
        artifacts_src = checkpoint_dir / "artifacts"
        artifacts_dst = run_dir / "artifacts"
        if artifacts_src.exists():
            if artifacts_dst.exists():
                shutil.rmtree(_win_path(artifacts_dst))
            shutil.copytree(_win_path(artifacts_src), _win_path(artifacts_dst))
        # Restore content dirs
        for dirname in _CHECKPOINT_CONTENT_DIRS:
            src = checkpoint_dir / dirname
            dst = run_dir / dirname
            if src.exists():
                if dst.exists():
                    shutil.rmtree(_win_path(dst))
                shutil.copytree(_win_path(src), _win_path(dst))
        return True
    except Exception as exc:
        logger.warning("[Heal] Checkpoint restore failed: %s", exc)
        return False


# ── Artifact write ────────────────────────────────────────────────────────────


def write_heal_plan(run_dir: Path, result: HealResult) -> Path:
    """Write heal_plan.json artifact to run_dir/artifacts/."""
    from launch.io.atomic import atomic_write_json

    data = {
        "schema_version": "1.0",
        "run_id": result.run_id,
        "mode": result.mode,
        "max_steps": result.max_steps,
        "steps": [asdict(s) for s in result.steps],
        "stop_reason": result.stop_reason,
        "final_failed_gate_count": result.final_failed_gate_count,
        "started_at_utc": result.started_at_utc,
        "finished_at_utc": result.finished_at_utc,
    }
    artifacts_dir = run_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    out_path = artifacts_dir / "heal_plan.json"
    atomic_write_json(out_path, data)
    return out_path


# ── Main healing loop ─────────────────────────────────────────────────────────


def run_heal_loop(
    run_id: str,
    run_dir: Path,
    run_config: Dict[str, Any],
    max_steps: int = 5,
    top_k: int = 3,
    mode: str = "strict",
    dry_run: bool = False,
    console: Any = None,
) -> HealResult:
    """Execute the deterministic healing loop.

    1. Load or produce validation_report.json
    2. Triage → choose worker → resume → re-validate → repeat
    3. Stop when: all gates pass, stuck, max-steps, or no recommendation

    Args:
        run_id: Run identifier.
        run_dir: Existing run directory.
        run_config: Validated run configuration.
        max_steps: Maximum healing iterations.
        top_k: Number of triage recommendations to consider.
        mode: "strict" (top-1 only) or "aggressive" (try alternatives).
        dry_run: If True, record planned step but skip execution.
        console: Optional Rich Console for output.

    Returns:
        HealResult with complete audit trail.
    """
    from launch.cli.triage import load_validation_report, recommend_action
    from launch.orchestrator.run_loop import execute_run_from_node

    result = HealResult(
        run_id=run_id,
        mode=mode,
        max_steps=max_steps,
        started_at_utc=datetime.now(timezone.utc).isoformat(),
    )

    events_file = run_dir / "events.ndjson"

    def _print(msg: str) -> None:
        if console is not None:
            console.print(msg)

    # Step 0: Ensure validation_report.json exists
    try:
        report = load_validation_report(run_dir)
    except FileNotFoundError:
        _print("[yellow]No validation_report.json found. Running W9 to produce one...[/yellow]")
        try:
            execute_run_from_node(run_id, run_dir, run_config, "W9")
        except Exception as e:
            _print(f"[red]W9 execution failed: {e}[/red]")
            result.stop_reason = "resume_failed"
            result.final_failed_gate_count = -1
            result.finished_at_utc = datetime.now(timezone.utc).isoformat()
            write_heal_plan(run_dir, result)
            return result
        try:
            report = load_validation_report(run_dir)
        except FileNotFoundError:
            _print("[red]W9 did not produce validation_report.json. Cannot heal.[/red]")
            result.stop_reason = "resume_failed"
            result.final_failed_gate_count = -1
            result.finished_at_utc = datetime.now(timezone.utc).isoformat()
            write_heal_plan(run_dir, result)
            return result

    # Check if already passing
    failed_count = count_failed_gates(report)
    if failed_count == 0:
        _print("[green]All gates already pass. Nothing to heal.[/green]")
        result.stop_reason = "all_gates_pass"
        result.final_failed_gate_count = 0
        result.finished_at_utc = datetime.now(timezone.utc).isoformat()
        write_heal_plan(run_dir, result)
        return result

    _print(f"[blue]Starting heal loop:[/blue] {failed_count} failed gates, max {max_steps} steps, mode={mode}")

    # Main loop
    for step_idx in range(max_steps):
        # TC-3510: Initialize checkpoint to None at top of each iteration
        checkpoint: Optional[Path] = None

        # Triage
        recommendations = recommend_action(run_dir, report)

        # TC-3510: Deprioritize W5 when few gates are failing (high cascade risk)
        recommendations = _deprioritize_w5(recommendations, failed_count)

        # Check for no-recommendation / fallback-only
        if not recommendations:
            _print("[yellow]No recommendations from triage. Stopping.[/yellow]")
            result.stop_reason = "no_recommendation"
            result.final_failed_gate_count = failed_count
            break

        # Check if only W9 fallback (no specific fixable pattern)
        if (
            len(recommendations) == 1
            and extract_worker_from_recommendation(recommendations[0]) == "W9"
            and "general re-validation" in recommendations[0].get("reason", "").lower()
        ):
            _print("[yellow]Only general re-validation recommended. No fixable pattern detected. Stopping.[/yellow]")
            result.stop_reason = "no_recommendation"
            result.final_failed_gate_count = failed_count
            break

        # Choose worker
        choice = choose_worker(recommendations, mode, top_k, result.steps)
        if choice is None:
            _print("[yellow]No viable worker choice (all candidates tried without improvement). Stopping.[/yellow]")
            result.stop_reason = "stuck"
            result.final_failed_gate_count = failed_count
            break

        worker, reason = choice

        # Check stuck condition
        if is_stuck(result.steps, worker, reason):
            _print(
                f"[yellow]Stuck: ({worker}, {reason!r}) already tried without improvement. Stopping.[/yellow]"
            )
            result.stop_reason = "stuck"
            result.final_failed_gate_count = failed_count
            break

        # Build the step
        step = HealStep(
            step_idx=step_idx,
            chosen_worker=worker,
            reason=reason,
            triage_snapshot=recommendations[:top_k],
            failed_gate_count_before=failed_count,
        )

        if dry_run:
            step.notes = "dry-run"
            step.failed_gate_count_after = failed_count
            step.exit_code = -1
            result.steps.append(step)
            _print(f"[dim]Step {step_idx}: would resume from {worker} ({reason}) — dry-run[/dim]")
            result.stop_reason = "dry_run"
            result.final_failed_gate_count = failed_count
            break

        # TC-3510: Checkpoint before executing step (for regression rollback)
        # TC-3570: STOP-THE-LINE — abort step if checkpoint fails (no rollback = unsafe)
        checkpoint = _create_checkpoint(run_dir, step_idx)
        if checkpoint is None:
            _print(
                f"  [red]Step {step_idx}: checkpoint creation failed — "
                "skipping (unsafe to proceed without rollback capability)[/red]"
            )
            continue

        # Emit HEAL_STEP_STARTED
        _emit_event(events_file, run_id, _EVENT_HEAL_STEP_STARTED, {
            "step_idx": step_idx,
            "chosen_worker": worker,
            "reason": reason,
            "failed_gate_count": failed_count,
        })

        # Execute resume
        run_dir_str = str(run_dir).replace("\\", "/")
        cmd = f"launch resume --run-dir {run_dir_str} --from-worker {worker}"
        _print(f"\n[bold blue]Step {step_idx}:[/bold blue] {cmd}")
        _print(f"  Reason: {reason}")
        _print(f"  Failed gates before: {failed_count}")

        try:
            run_result = execute_run_from_node(run_id, run_dir, run_config, worker)
            step.exit_code = run_result.exit_code
        except Exception as e:
            logger.warning("Resume from %s failed: %s", worker, e)
            step.exit_code = 2
            step.notes = f"resume failed: {e}"
            step.failed_gate_count_after = failed_count
            result.steps.append(step)

            _emit_event(events_file, run_id, _EVENT_HEAL_STEP_COMPLETED, {
                "step_idx": step_idx,
                "chosen_worker": worker,
                "exit_code": 2,
                "failed_gate_count_before": failed_count,
                "failed_gate_count_after": failed_count,
            })

            _print(f"  [red]Resume failed: {e}[/red]")
            _print("  [yellow]Skipping to next recommendation...[/yellow]")
            continue  # TC-3210: skip to next recommendation instead of stopping

        # Reload validation report
        try:
            report = load_validation_report(run_dir)
        except FileNotFoundError:
            step.notes = "validation_report.json missing after resume"
            step.failed_gate_count_after = failed_count
            result.steps.append(step)
            _print("  [red]validation_report.json missing after resume[/red]")
            result.stop_reason = "resume_failed"
            result.final_failed_gate_count = failed_count
            break

        new_failed_count = count_failed_gates(report)
        step.failed_gate_count_after = new_failed_count

        _emit_event(events_file, run_id, _EVENT_HEAL_STEP_COMPLETED, {
            "step_idx": step_idx,
            "chosen_worker": worker,
            "exit_code": step.exit_code,
            "failed_gate_count_before": failed_count,
            "failed_gate_count_after": new_failed_count,
        })

        _print(f"  Failed gates after: {new_failed_count}")
        if new_failed_count < failed_count:
            _print(f"  [green]Improved: {failed_count} → {new_failed_count}[/green]")
            result.steps.append(step)
            failed_count = new_failed_count
        elif new_failed_count == failed_count:
            _print(f"  [yellow]No change: still {new_failed_count} failed[/yellow]")
            result.steps.append(step)
            # failed_count unchanged
        else:
            # TC-3510: Regression detected — restore checkpoint and continue
            _print(f"  [red]Regression: {failed_count} → {new_failed_count}[/red]")
            step.notes = f"regressed: {failed_count} → {new_failed_count}"
            result.steps.append(step)

            _emit_event(events_file, run_id, _EVENT_HEAL_STEP_REGRESSED, {
                "step_idx": step_idx,
                "chosen_worker": worker,
                "failed_gate_count_before": failed_count,
                "failed_gate_count_after": new_failed_count,
            })

            if checkpoint is not None:
                restored = _restore_checkpoint(run_dir, checkpoint)
                if restored:
                    _print("  [yellow]Checkpoint restored. Trying next recommendation...[/yellow]")
                    # Reload the report from restored checkpoint
                    try:
                        report = load_validation_report(run_dir)
                        failed_count = count_failed_gates(report)
                    except FileNotFoundError:
                        pass
                else:
                    _print("  [red]Checkpoint restore failed.[/red]")
            else:
                _print("  [yellow]No checkpoint available for restore.[/yellow]")
            continue  # Try next recommendation in next iteration

        # Check if all gates pass now
        if failed_count == 0:
            _print("\n[bold green]All gates pass! Healing complete.[/bold green]")
            result.stop_reason = "all_gates_pass"
            result.final_failed_gate_count = 0
            break
    else:
        # Loop exhausted max_steps
        _print(f"\n[yellow]Max steps ({max_steps}) reached.[/yellow]")
        result.stop_reason = "max_steps"
        result.final_failed_gate_count = failed_count

    # Finalize
    result.finished_at_utc = datetime.now(timezone.utc).isoformat()
    if result.final_failed_gate_count < 0:
        result.final_failed_gate_count = failed_count

    # Emit HEAL_STOPPED
    _emit_event(events_file, run_id, _EVENT_HEAL_STOPPED, {
        "stop_reason": result.stop_reason,
        "total_steps": len(result.steps),
        "final_failed_gate_count": result.final_failed_gate_count,
    })

    # Write heal_plan.json
    plan_path = write_heal_plan(run_dir, result)
    _print(f"\n[dim]Heal plan written to: {plan_path}[/dim]")

    return result
