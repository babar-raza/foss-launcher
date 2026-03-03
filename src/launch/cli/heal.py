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
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

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

# TC-3633: Per-worker checkpoint scope map.
# Maps worker ID → list of extra content dirs to snapshot beyond artifacts/.
# None = skip checkpoint entirely (worker is read-only w.r.t. content dirs).
# Workers absent from this map default to _CHECKPOINT_CONTENT_DIRS (full scope).
_WORKER_CHECKPOINT_SCOPES: Dict[str, Optional[List[str]]] = {
    "W2": [],       # facts/evidence: only writes artifacts/
    "W3": [],       # snippets: only writes artifacts/
    "W4": [],       # ia_planner: only writes artifacts/
    "W5": ["drafts"],           # section_writer: produces draft content
    "W6": ["work/site/content"],  # seo_optimizer: modifies site content
    "W7": ["drafts"],           # content_reviewer: may update drafts
    "W8": ["work/site/content"],  # linker_and_patcher: patches site content
    "W9": None,     # validator: read-only (writes only validation_report.json in artifacts/)
    "W10": ["work/site/content"],  # fixer: patches site content
}

# TC-3641: Safety gates always executed during heal selective gate filtering.
# These gates detect side-effects that any worker can cause, regardless of which
# gates originally failed.  See specs/50_healing_cost_reduction.md §5.3.
_HEAL_SAFETY_GATES: frozenset = frozenset({
    "gate_1_schema_validation",
    "gate_truth_layer_completeness",
    "gate_4_frontmatter_required_fields",
    "gate_11_template_token_lint",
    "gate_13_hugo_build",
    "gate_s1_xss_prevention",
    "gate_s2_sensitive_data_leak",
})

# TC-3620: Critical artifacts that a crashing worker may have deleted mid-execution.
# Restored from checkpoint ONLY when absent from run_dir (never overwrites existing).
# validation_report.json is intentionally excluded — disk truth must be preserved.
_REQUIRED_HEAL_ARTIFACTS: List[str] = [
    "artifacts/patch_bundle.json",
    "artifacts/page_plan.json",
    "artifacts/draft_manifest.json",
]


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
    outcome: Literal["improved", "regressed", "unchanged", "skipped"] = "unchanged"
    # TC-3614: Stable recommendation id — derived from triage rule name + worker,
    # independent of human-readable reason text.  Used as quarantine key.
    recommendation_id: str = ""
    # TC-3614: Per-step issue metrics for "progress without gate flip" auditability.
    # Populated from compute_report_metrics() before/after each step.
    before_metrics: Optional[Dict[str, Any]] = None
    after_metrics: Optional[Dict[str, Any]] = None
    # TC-3633: Wall-clock timing (seconds) for each expensive phase.
    # checkpoint_seconds: time for _create_checkpoint() — 0.0 if skipped (W9 / checkpoint failed)
    # execution_seconds: time for execute_run_from_node() — worker + W9 combined
    # restore_seconds: time for _restore_checkpoint() — 0.0 if no regression occurred
    checkpoint_seconds: float = 0.0
    execution_seconds: float = 0.0
    restore_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable dict with stable keys.

        Defensive: coerces triage_snapshot entries to plain dicts with string
        values so that any unexpected object shape (the TC-3613 failure mode)
        never causes a TypeError in json.dumps().
        """
        safe_snapshot: List[Dict[str, str]] = []
        for entry in self.triage_snapshot:
            if isinstance(entry, dict):
                safe_snapshot.append({str(k): str(v) for k, v in entry.items()})
            else:
                safe_snapshot.append({"_raw": str(entry)})
        return {
            "step_idx": self.step_idx,
            "chosen_worker": self.chosen_worker,
            "reason": self.reason,
            "recommendation_id": self.recommendation_id,  # TC-3614
            "triage_snapshot": safe_snapshot,
            "failed_gate_count_before": self.failed_gate_count_before,
            "failed_gate_count_after": self.failed_gate_count_after,
            "exit_code": self.exit_code,
            "notes": self.notes,
            "outcome": self.outcome,
            "before_metrics": self.before_metrics,  # TC-3614: None if not computed
            "after_metrics": self.after_metrics,  # TC-3614: None if not computed
            "checkpoint_seconds": self.checkpoint_seconds,  # TC-3633
            "execution_seconds": self.execution_seconds,  # TC-3633
            "restore_seconds": self.restore_seconds,  # TC-3633
        }


@dataclass
class HealResult:
    """Complete healing iteration audit trail."""

    run_id: str
    mode: str
    max_steps: int
    steps: List[HealStep] = field(default_factory=list)
    stop_reason: str = ""
    final_failed_gate_count: int = -1
    # TC-3613: baseline gate count at session start — set before the main loop.
    # Used by CLI wrappers to determine non-regressive exit code (final ≤ initial → 0).
    initial_failed_gate_count: int = -1
    started_at_utc: str = ""
    finished_at_utc: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable dict with stable keys.

        Delegates to HealStep.to_dict() for defensive step serialization.
        TC-3613: Prevents object-shape mismatches in triage_snapshot from
        propagating as serialization exceptions.
        """
        return {
            "schema_version": "1.0",
            "run_id": self.run_id,
            "mode": self.mode,
            "max_steps": self.max_steps,
            "initial_failed_gate_count": self.initial_failed_gate_count,
            "steps": [s.to_dict() for s in self.steps],
            "stop_reason": self.stop_reason,
            "final_failed_gate_count": self.final_failed_gate_count,
            "started_at_utc": self.started_at_utc,
            "finished_at_utc": self.finished_at_utc,
        }


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


# ── TC-3600: Report metrics for convergence-aware progress ───────────────


@dataclass(frozen=True)
class ReportMetrics:
    """Snapshot of a validation report's health indicators.

    Used by the heal loop to detect improvement even when gate counts
    are unchanged (e.g. multi-issue gates where one issue was fixed but
    the gate still fails).
    """

    failed_gate_ids: frozenset
    failed_gate_count: int
    open_critical_issue_count: int  # severity in {blocker, error}
    open_total_issue_count: int


def compute_report_metrics(report: Dict[str, Any]) -> ReportMetrics:
    """Extract health metrics from a validation report.

    Args:
        report: Parsed validation_report.json dict.

    Returns:
        ReportMetrics snapshot.
    """
    gates = report.get("gates", [])
    issues = report.get("issues", [])

    failed_ids = frozenset(
        g.get("name", "")
        for g in gates
        if not g.get("ok", True)
    )

    critical_count = sum(
        1 for iss in issues
        if iss.get("severity", "").lower() in ("blocker", "error")
    )

    return ReportMetrics(
        failed_gate_ids=failed_ids,
        failed_gate_count=len(failed_ids),
        open_critical_issue_count=critical_count,
        open_total_issue_count=len(issues),
    )


def _metrics_to_dict(m: Optional[ReportMetrics]) -> Optional[Dict[str, Any]]:
    """Convert a ReportMetrics snapshot to a JSON-serializable dict.

    TC-3614: Used to persist per-step metrics in heal_plan.json so that
    "progress without gate flip" (issue-count drop) is auditable from the
    plan artifact alone.

    Returns None if m is None (step had no metrics snapshot).
    """
    if m is None:
        return None
    return {
        "failed_gate_count": m.failed_gate_count,
        "failed_gate_ids": sorted(m.failed_gate_ids),  # sorted for determinism
        "open_critical_issue_count": m.open_critical_issue_count,
        "open_total_issue_count": m.open_total_issue_count,
    }


def is_improvement(before: ReportMetrics, after: ReportMetrics) -> bool:
    """Return True if *after* is strictly better than *before* on any axis
    without being worse on any other axis.

    Improvement axes (any one suffices):
      - failed_gate_count decreased
      - failed_gate_ids is a strict subset (no new gates appeared)
      - open_critical_issue_count decreased
      - open_total_issue_count decreased

    Worsening guard (any one vetoes):
      - failed_gate_ids gained new members
      - open_critical_issue_count increased
    """
    new_gates = after.failed_gate_ids - before.failed_gate_ids
    if new_gates:
        return False  # New gate failures appeared — not an improvement
    if after.open_critical_issue_count > before.open_critical_issue_count:
        return False  # Critical issues increased — not an improvement

    return (
        after.failed_gate_count < before.failed_gate_count
        or (after.failed_gate_ids < before.failed_gate_ids)  # strict subset
        or after.open_critical_issue_count < before.open_critical_issue_count
        or after.open_total_issue_count < before.open_total_issue_count
    )


def is_regression(before: ReportMetrics, after: ReportMetrics) -> bool:
    """Return True if *after* is worse than *before* on any critical axis.

    Regression axes (any one triggers):
      - failed_gate_count increased
      - failed_gate_ids gained new members
      - open_critical_issue_count increased
    """
    if after.failed_gate_count > before.failed_gate_count:
        return True
    new_gates = after.failed_gate_ids - before.failed_gate_ids
    if new_gates:
        return True
    if after.open_critical_issue_count > before.open_critical_issue_count:
        return True
    return False


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


def _get_quarantine_key(candidate: Dict[str, str], worker: str) -> str:
    """Return the stable quarantine key for a recommendation candidate.

    TC-3614: Use the recommendation's stable ``id`` field (derived from the
    triage rule name + worker) rather than the human-readable ``reason`` text.
    Falls back to a safe derived key and emits a warning if ``id`` is absent
    (should not happen after TC-3614 lands, but protects during mixed deploys).
    """
    rec_id = candidate.get("id", "")
    if rec_id:
        return rec_id
    # Backward-compat / defensive path — id missing from older recommendation
    fallback = f"missing-id:{worker}"
    logger.warning(
        "[Heal] Recommendation for worker %s has no stable 'id' field; "
        "using fallback quarantine key %r. Update triage.py to TC-3614.",
        worker,
        fallback,
    )
    return fallback


# ── TC-3620: Disk-truth helpers ───────────────────────────────────────────────


def _try_load_report(run_dir: Path) -> Optional[Dict[str, Any]]:
    """Load validation_report.json from disk; return None on any read error.

    TC-3620: Wraps load_validation_report() with broad exception suppression
    so callers can use a simple ``is not None`` check instead of try/except.
    Catches FileNotFoundError (report absent), json.JSONDecodeError (corrupted
    report), UnicodeDecodeError, OSError, and any other unexpected read error
    to prevent a secondary exception from masking the original worker exception
    in the heal loop's exception handler.
    """
    from launch.cli.triage import load_validation_report
    try:
        return load_validation_report(run_dir)
    except FileNotFoundError:
        return None
    except Exception as exc:
        logger.warning("[Heal] Could not read validation_report.json: %s", exc)
        return None


def _sync_from_disk(
    run_dir: Path,
) -> Tuple[Optional[Dict[str, Any]], Optional[int], Optional[ReportMetrics]]:
    """Load report from disk and compute metrics.

    TC-3620 OBS-1/OBS-5: Returns (report, failed_count, metrics) from disk,
    or (None, None, None) if the report is absent.

    Used at three points in run_heal_loop():
      1. Top of each main-loop iteration (detect stale internal state).
      2. Exception path (disk truth wins even after worker crash).
      3. Finalization (guarantee final_failed_gate_count matches disk).
    """
    report = _try_load_report(run_dir)
    if report is None:
        return None, None, None
    count = count_failed_gates(report)
    metrics = compute_report_metrics(report)
    return report, count, metrics


def _restore_missing_from_checkpoint(
    run_dir: Path,
    checkpoint_dir: Path,
    rel_paths: Optional[List[str]] = None,
) -> List[str]:
    """Restore only missing artifacts from checkpoint — never overwrites existing files.

    TC-3620 OBS-2 mitigation: a crashing worker may have partially deleted
    critical artifacts (e.g. patch_bundle.json) that are needed by subsequent
    steps.  This helper restores them from the pre-step snapshot without
    clobbering the (potentially green) validation_report.json.

    ``rel_paths`` defaults to ``_REQUIRED_HEAL_ARTIFACTS`` when not provided.

    Returns:
        List of relative paths that were restored.
    """
    targets = rel_paths if rel_paths is not None else _REQUIRED_HEAL_ARTIFACTS
    restored: List[str] = []
    for rel in targets:
        dst = run_dir / rel
        if dst.exists():
            continue  # already present — disk truth wins, do NOT overwrite
        src = checkpoint_dir / rel
        if not src.exists():
            continue  # not in checkpoint either — nothing to restore
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(_win_path(src), _win_path(dst))
            restored.append(rel)
            logger.info("[Heal] Restored missing artifact from checkpoint: %s", rel)
        except Exception as exc:
            logger.warning("[Heal] Failed to restore %s from checkpoint: %s", rel, exc)
    return restored


def choose_worker(
    recommendations: List[Dict[str, str]],
    mode: str,
    top_k: int,
    history: List[HealStep],
    quarantined: Optional[set] = None,
) -> Optional[Tuple[str, str]]:
    """Select the next (worker, reason) pair from triage recommendations.

    Args:
        recommendations: Triage recommendations [{command, reason, id}].
        mode: "strict" or "aggressive".
        top_k: Maximum number of recommendations to consider.
        history: Prior heal steps.
        quarantined: TC-3600/TC-3614 — set of (worker, rec_id) tuples that
            regressed and should not be retried.  The key is the stable
            recommendation ``id`` (not reason text) so that rewording a label
            never silently disables quarantine.

    Returns:
        (worker, reason) tuple, or None if stuck/no valid choice.
    """
    if not recommendations:
        return None

    _quarantined = quarantined or set()
    candidates = recommendations[:top_k]

    if mode == "strict":
        # Strict: pick the first recommendation that hasn't crashed (exit_code=2)
        for candidate in candidates:
            worker = extract_worker_from_recommendation(candidate)
            reason = candidate.get("reason", "")
            if not worker:
                continue
            # TC-3614: Quarantine key is now (worker, rec_id), not (worker, reason).
            rec_id = _get_quarantine_key(candidate, worker)
            if (worker, rec_id) in _quarantined:
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
        # TC-3614: Quarantine key is now (worker, rec_id), not (worker, reason).
        rec_id = _get_quarantine_key(candidate, worker)
        if (worker, rec_id) in _quarantined:
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

    Steps with outcome "regressed" (TC-3510) are excluded because the checkpoint
    restore returns the state to the pre-step baseline. Steps with outcome
    "improved" (TC-3600) are excluded because they made measurable progress
    (issue-count drop).
    """
    if not history:
        return False
    last = history[-1]
    if last.outcome == "regressed":
        # TC-3510: Regression was rolled back — don't count as "tried without improvement"
        return False
    if last.outcome == "improved":
        # TC-3600: Issue-count improvement — step made progress (not "without improvement")
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

    Steps with outcome "regressed" (TC-3510) are excluded from stuck detection
    because the checkpoint restore returns the state to the pre-step baseline.
    Steps with outcome "improved" (TC-3600) are excluded because they made
    measurable progress (issue-count drop).
    """
    for step in history:
        if step.outcome == "regressed":
            # TC-3510: After regression+restore the state is back to baseline;
            # do not count these as "tried without improvement" for stuck detection.
            continue
        if step.outcome == "improved":
            # TC-3600: Issue-count improvement detected — the step made progress
            # even if gate count stayed flat.  Do not count as "no improvement".
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


def _create_checkpoint(
    run_dir: Path,
    step_idx: int,
    content_dirs: Optional[List[str]] = None,
) -> Optional[Path]:
    """Snapshot key artifacts before a heal step for potential rollback.

    Copies artifacts/ + the directories listed in content_dirs into
    run_dir/_heal_checkpoints/step_{step_idx}/.

    TC-3633: content_dirs is per-worker scoped via _WORKER_CHECKPOINT_SCOPES.
    When None (default), falls back to _CHECKPOINT_CONTENT_DIRS for backward
    compatibility (full scope: work/site/content + drafts).

    Returns checkpoint path, or None if snapshot failed.
    """
    dirs_to_copy = content_dirs if content_dirs is not None else _CHECKPOINT_CONTENT_DIRS
    checkpoint_dir = run_dir / _CHECKPOINT_DIR_NAME / f"step_{step_idx}"
    try:
        # TC-3570: Use _win_path() to bypass Windows MAX_PATH (260-char) limit
        _win_path(checkpoint_dir).mkdir(parents=True, exist_ok=True)
        # Copy artifacts directory (always included)
        artifacts_src = run_dir / "artifacts"
        artifacts_dst = checkpoint_dir / "artifacts"
        if artifacts_src.exists():
            if artifacts_dst.exists():
                shutil.rmtree(_win_path(artifacts_dst))
            shutil.copytree(_win_path(artifacts_src), _win_path(artifacts_dst))
        # Copy worker-scoped content dirs (TC-3633)
        for dirname in dirs_to_copy:
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


def write_heal_plan(run_dir: Path, result: HealResult) -> Optional[Path]:
    """Write heal_plan.json artifact to run_dir/artifacts/.

    TC-3613: Uses result.to_dict() for defensive serialization so that
    object-shape mismatches in triage_snapshot never cause a TypeError.
    Returns None on failure (never raises) — the caller determines exit code
    independently from result fields, not from whether the file was written.
    """
    from launch.io.atomic import atomic_write_json

    artifacts_dir = run_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    out_path = artifacts_dir / "heal_plan.json"
    try:
        data = result.to_dict()
        atomic_write_json(out_path, data)
        return out_path
    except Exception as exc:
        logger.warning("[Heal] Failed to write heal_plan.json: %s", exc)
        return None


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
    from launch.orchestrator.graph import DRIVE_GOAL_DRAFT, DRIVE_GOAL_KEY, DRIVE_GOAL_VALIDATE
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
    # TC-3613: Record baseline for non-regressive exit code determination.
    result.initial_failed_gate_count = failed_count
    if failed_count == 0:
        _print("[green]All gates already pass. Nothing to heal.[/green]")
        result.stop_reason = "all_gates_pass"
        result.final_failed_gate_count = 0
        result.finished_at_utc = datetime.now(timezone.utc).isoformat()
        write_heal_plan(run_dir, result)
        return result

    _print(f"[blue]Starting heal loop:[/blue] {failed_count} failed gates, max {max_steps} steps, mode={mode}")

    # TC-3600: Quarantine set — (worker, rec_id) pairs that regressed.
    # TC-3614: Key is now stable recommendation_id, not reason text.
    # Quarantined candidates are skipped by choose_worker() for the
    # remainder of the session.
    quarantined: set = set()

    # TC-3600: Compute initial metrics snapshot for convergence-aware progress.
    metrics_before = compute_report_metrics(report)

    # TC-3641: Read opt-out flag for selective gate execution.
    _fast_validation = run_config.get("heal_fast_validation", True)
    # TC-3641: Track whether a partial-zero result needs final full validation.
    _needs_final_full = False

    # Main loop
    for step_idx in range(max_steps):
        # TC-3510: Initialize checkpoint to None at top of each iteration
        checkpoint: Optional[Path] = None

        # TC-3620 OBS-1/OBS-5: Sync internal state from disk at the top of
        # every iteration.  Internal failed_count can be stale when a prior
        # exception path did not update it (pre-TC-3620 bug).  Reading disk
        # here guarantees that triage, stuck-detection, and step recording
        # always operate on current data.
        _disk_rep, _disk_cnt, _disk_met = _sync_from_disk(run_dir)
        if _disk_rep is not None and _disk_cnt is not None:
            if _disk_cnt == 0:
                # TC-3641: Partial report green → defer to final full validation.
                if _disk_rep.get("partial", False):
                    logger.info("[Heal] Disk report green but partial — deferring to final full validation.")
                    _needs_final_full = True
                    break
                _print("[green]Disk report is green at iteration start — stopping.[/green]")
                result.stop_reason = "all_gates_pass"
                result.final_failed_gate_count = 0
                break
            if _disk_cnt != failed_count:
                logger.info(
                    "[Heal] Top-of-iteration disk sync: internal=%d, disk=%d; updating cache.",
                    failed_count, _disk_cnt,
                )
                failed_count = _disk_cnt
                metrics_before = _disk_met  # type: ignore[assignment]
                report = _disk_rep

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

        # Choose worker (TC-3600: pass quarantined set)
        choice = choose_worker(recommendations, mode, top_k, result.steps, quarantined)
        if choice is None:
            _print("[yellow]No viable worker choice (all candidates tried without improvement). Stopping.[/yellow]")
            result.stop_reason = "stuck"
            result.final_failed_gate_count = failed_count
            break

        worker, reason = choice

        # TC-3614: Extract stable recommendation_id from matched recommendation.
        # choose_worker() returns (worker, reason) but the matched candidate also
        # carries the stable "id" field needed for quarantine + HealStep audit.
        matched_rec = next(
            (r for r in recommendations
             if extract_worker_from_recommendation(r) == worker
             and r.get("reason") == reason),
            {},
        )
        rec_id = matched_rec.get("id") or f"missing-id:{worker}"

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
            recommendation_id=rec_id,  # TC-3614: stable quarantine / audit key
            before_metrics=_metrics_to_dict(metrics_before),  # TC-3614: snapshot before
        )

        if dry_run:
            step.notes = "dry-run"
            step.outcome = "skipped"
            step.failed_gate_count_after = failed_count
            step.exit_code = -1
            result.steps.append(step)
            _print(f"[dim]Step {step_idx}: would resume from {worker} ({reason}) — dry-run[/dim]")
            result.stop_reason = "dry_run"
            result.final_failed_gate_count = failed_count
            break

        # TC-3510: Checkpoint before executing step (for regression rollback)
        # TC-3570: STOP-THE-LINE — abort step if checkpoint fails (no rollback = unsafe)
        # TC-3633: Scope checkpoint to directories the chosen worker can actually mutate.
        _t_ckpt_start = time.monotonic()
        _ckpt_scopes = _WORKER_CHECKPOINT_SCOPES.get(worker, _CHECKPOINT_CONTENT_DIRS)
        if _ckpt_scopes is None:
            # Read-only worker (e.g., W9) — skip checkpoint creation
            checkpoint: Optional[Path] = None
        else:
            checkpoint = _create_checkpoint(run_dir, step_idx, content_dirs=_ckpt_scopes)
            if checkpoint is None:
                _print(
                    f"  [red]Step {step_idx}: checkpoint creation failed — "
                    "skipping (unsafe to proceed without rollback capability)[/red]"
                )
                continue
        step.checkpoint_seconds = time.monotonic() - _t_ckpt_start

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

        # TC-3633: Use goal=validate so decide_after_validation() returns "stop"
        # immediately — guaranteeing a single pass (chosen worker → W9 → stop).
        # This eliminates the orchestrator's internal fix sub-loop that fires when
        # goal=draft and there are fixable issues (would trigger repeated W10 passes).
        # The heal loop is the sole iteration controller.
        # TC-3620 OBS-2: Use a shallow copy to avoid mutating the caller's run_config dict.
        _rc2 = dict(run_config)
        _rc2[DRIVE_GOAL_KEY] = DRIVE_GOAL_VALIDATE
        # TC-3641: Inject selective gate filter — run only previously-failing
        # gates + safety gates.  Disabled by heal_fast_validation=false.
        if _fast_validation and metrics_before is not None:
            _filter_set = set(metrics_before.failed_gate_ids) | _HEAL_SAFETY_GATES
            _rc2["_heal_gate_filter"] = sorted(_filter_set)
        _t_exec_start = time.monotonic()
        try:
            run_result = execute_run_from_node(run_id, run_dir, _rc2, worker)
            step.exit_code = run_result.exit_code
        except Exception as e:
            logger.warning("Resume from %s failed: %s", worker, e)
            step.exit_code = 2
            step.notes = f"resume failed: {e}"

            # TC-3620 OBS-1: Disk-truth wins — read actual state even when
            # the worker raised an exception.  It may have already written a
            # green validation_report.json before crashing.
            _ex_rep, _ex_cnt, _ex_met = _sync_from_disk(run_dir)
            disk_count = _ex_cnt if _ex_cnt is not None else failed_count
            step.failed_gate_count_after = disk_count
            if _ex_met is not None:
                step.after_metrics = _metrics_to_dict(_ex_met)

            # TC-3620 OBS-2 mitigation: restore critical artifacts that the
            # crashing worker may have deleted from the run directory.
            if checkpoint is not None:
                _restore_missing_from_checkpoint(run_dir, checkpoint)

            result.steps.append(step)
            _emit_event(events_file, run_id, _EVENT_HEAL_STEP_COMPLETED, {
                "step_idx": step_idx,
                "chosen_worker": worker,
                "exit_code": 2,
                "failed_gate_count_before": failed_count,
                "failed_gate_count_after": disk_count,
            })

            if disk_count == 0:
                # Disk is green despite the exception — heal succeeded.
                step.outcome = "improved"
                _print("  [green]Worker raised but disk is green — heal succeeded.[/green]")
                result.stop_reason = "all_gates_pass"
                result.final_failed_gate_count = 0
                break
            if _ex_rep is not None and disk_count < failed_count:
                # Partial improvement: worker did useful work before crashing.
                # Update internal state so the next iteration is accurate.
                step.outcome = "improved"
                failed_count = disk_count
                metrics_before = _ex_met  # type: ignore[assignment]
                report = _ex_rep

            step.execution_seconds = time.monotonic() - _t_exec_start  # TC-3633
            _print(f"  [red]Resume failed: {e}[/red]")
            _print("  [yellow]Skipping to next recommendation...[/yellow]")
            continue  # TC-3210: skip to next recommendation instead of stopping

        step.execution_seconds = time.monotonic() - _t_exec_start  # TC-3633

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

        # TC-3600: Compute metrics-based progress snapshot
        metrics_after = compute_report_metrics(report)

        # TC-3614: Persist after-metrics in the step artifact for auditability.
        step.after_metrics = _metrics_to_dict(metrics_after)

        _emit_event(events_file, run_id, _EVENT_HEAL_STEP_COMPLETED, {
            "step_idx": step_idx,
            "chosen_worker": worker,
            "exit_code": step.exit_code,
            "failed_gate_count_before": failed_count,
            "failed_gate_count_after": new_failed_count,
        })

        _print(f"  Failed gates after: {new_failed_count}")

        # TC-3600: Use metrics-based comparison instead of gate-count-only.
        # is_improvement detects issue-count drops even when gate count is flat.
        if is_regression(metrics_before, metrics_after):
            # TC-3510: Regression detected — restore checkpoint and continue
            _print(f"  [red]Regression: {failed_count} → {new_failed_count}[/red]")
            step.notes = f"regressed: {failed_count} → {new_failed_count}"
            step.outcome = "regressed"
            result.steps.append(step)

            # TC-3614: Quarantine key is now (worker, rec_id), not (worker, reason).
            # rec_id is stable across reason wording changes.
            quarantined.add((worker, rec_id))

            _emit_event(events_file, run_id, _EVENT_HEAL_STEP_REGRESSED, {
                "step_idx": step_idx,
                "chosen_worker": worker,
                "failed_gate_count_before": failed_count,
                "failed_gate_count_after": new_failed_count,
            })

            if checkpoint is not None:
                _t_restore_start = time.monotonic()  # TC-3633
                restored = _restore_checkpoint(run_dir, checkpoint)
                step.restore_seconds = time.monotonic() - _t_restore_start  # TC-3633
                if restored:
                    _print("  [yellow]Checkpoint restored. Trying next recommendation...[/yellow]")
                    # Reload the report from restored checkpoint
                    try:
                        report = load_validation_report(run_dir)
                        failed_count = count_failed_gates(report)
                        metrics_before = compute_report_metrics(report)
                    except FileNotFoundError:
                        pass
                else:
                    _print("  [red]Checkpoint restore failed.[/red]")
            else:
                _print("  [yellow]No checkpoint available for restore.[/yellow]")
            continue  # Try next recommendation in next iteration
        elif is_improvement(metrics_before, metrics_after):
            # TC-3600: Mark step as improved so is_stuck() and
            # _was_tried_without_improvement() skip it (structured outcome field).
            step.notes = (
                f"issues {metrics_before.open_total_issue_count}"
                f" → {metrics_after.open_total_issue_count}"
            )
            step.outcome = "improved"
            _print(f"  [green]Improved: {failed_count} → {new_failed_count} gates"
                   f" (issues: {metrics_before.open_total_issue_count}"
                   f" → {metrics_after.open_total_issue_count})[/green]")
            result.steps.append(step)
            failed_count = new_failed_count
            metrics_before = metrics_after
        else:
            _print(f"  [yellow]No change: still {new_failed_count} failed[/yellow]")
            result.steps.append(step)
            # failed_count unchanged; metrics_before unchanged

        # Check if all gates pass now
        if failed_count == 0:
            # TC-3641: Partial report green → defer to final full validation.
            _report_partial = report.get("partial", False) if report else False
            if _report_partial:
                _needs_final_full = True
                break
            _print("\n[bold green]All gates pass! Healing complete.[/bold green]")
            result.stop_reason = "all_gates_pass"
            result.final_failed_gate_count = 0
            break
    else:
        # Loop exhausted max_steps
        _print(f"\n[yellow]Max steps ({max_steps}) reached.[/yellow]")
        result.stop_reason = "max_steps"
        result.final_failed_gate_count = failed_count

    # TC-3641: Final full validation when partial report showed 0 failures.
    # This is the Partial-Zero Rule (specs/50_healing_cost_reduction.md §5.6):
    # a partial-green result must be confirmed by a full 42-gate validation.
    if _fast_validation and _needs_final_full:
        _print("[blue]Running final full 42-gate validation...[/blue]")
        _rc_final = dict(run_config)
        _rc_final[DRIVE_GOAL_KEY] = DRIVE_GOAL_VALIDATE
        # No _heal_gate_filter → full validation
        try:
            execute_run_from_node(run_id, run_dir, _rc_final, "W9")
            report = load_validation_report(run_dir)
            _fin_full_count = count_failed_gates(report)
            if _fin_full_count == 0:
                _print("\n[bold green]Full validation confirms: all gates pass![/bold green]")
                result.stop_reason = "all_gates_pass"
                result.final_failed_gate_count = 0
            else:
                _print(f"\n[yellow]Full validation found {_fin_full_count} failures.[/yellow]")
                result.final_failed_gate_count = _fin_full_count
        except Exception as e:
            logger.warning("Final full validation failed: %s", e)

    # TC-3620: Final disk sync — guarantee final_failed_gate_count matches
    # disk truth.  Catches any residual divergence from exception paths that
    # may have updated internal state but not yet set result.final_failed_gate_count.
    _fin_rep, _fin_cnt, _ = _sync_from_disk(run_dir)
    if _fin_cnt is not None:
        if result.final_failed_gate_count != _fin_cnt:
            logger.info(
                "[Heal] Correcting final_failed_gate_count: %d → %d (disk truth).",
                result.final_failed_gate_count, _fin_cnt,
            )
            result.final_failed_gate_count = _fin_cnt
        if _fin_cnt == 0 and result.stop_reason != "all_gates_pass":
            result.stop_reason = "all_gates_pass"

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

    # Write heal_plan.json (TC-3613: defensive — never raises)
    plan_path = write_heal_plan(run_dir, result)
    if plan_path is not None:
        _print(f"\n[dim]Heal plan written to: {plan_path}[/dim]")
    else:
        _print("\n[yellow]Warning: heal_plan.json could not be written (serialization error logged)[/yellow]")

    return result
