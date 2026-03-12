"""Heal CLI — LLM-driven iterative healing of failing content pages."""
from __future__ import annotations

import asyncio
import datetime
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Optional

import typer

from launcher.models.evaluation import (
    EvaluationReport, HealAction, HealDecision, HealResult, HealStep, ReportMetrics,
)
from launcher.io.run_lock import RunLock, RunAlreadyActiveError
from launcher.util.budget_tracker import BudgetTracker, BudgetExceededError

logger = logging.getLogger(__name__)

heal_app = typer.Typer(name="heal", help="Iterative LLM-driven content healing")

_DIAGNOSTICIAN_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "heal_diagnostician.txt"
_DEFAULT_MAX_STEPS = 10
_DEFAULT_MIN_CONFIDENCE = 0.6
_DEFAULT_REGRESSION_THRESHOLD = 0.05  # 5% D+F rate increase = regression

# Valid execution modes for the heal CLI
_VALID_MODES: frozenset[str] = frozenset({"full", "worker", "diagnose"})

# HO-04: Grade severity order for adaptive page prioritization (F=worst → A=best)
_GRADE_SEVERITY: dict[str, int] = {"F": 0, "D": 1, "C": 2, "B": 3, "A": 4}

# Full budget dict required by BudgetTracker
_DEFAULT_BUDGETS = {
    "max_tokens": 200_000,
    "max_runtime_s": 1800,
    "max_llm_calls": 50,
    "max_llm_tokens": 200_000,
    "max_file_writes": 200,
    "max_patch_attempts": 20,
}

# Rolling history compression: last _FULL_STEPS steps shown as full JSON; older compressed.
_FULL_STEPS: int = 3

# Conservative estimate for HealDecision JSON response token count (TC-3868-H5).
_ESTIMATED_OUTPUT_TOKENS: int = 512

# Session-level timeout: derived from budget's max_runtime_s for single source of truth.
_SESSION_TIMEOUT_S: int = _DEFAULT_BUDGETS["max_runtime_s"]


def _load_eval_report(run_dir: Path) -> EvaluationReport | None:
    """Load the latest evaluation checkpoint from run_dir."""
    cp_path = run_dir / "evaluate_checkpoint.json"
    if not cp_path.exists():
        return None
    try:
        data = json.loads(cp_path.read_text(encoding="utf-8"))
        return EvaluationReport.model_validate(data)
    except Exception as exc:
        logger.warning("Cannot load eval report from %s: %s", cp_path, exc)
        return None


def _extract_metrics(report: EvaluationReport) -> ReportMetrics:
    """Extract ReportMetrics snapshot from an EvaluationReport."""
    total = len(report.pages) or 1
    grades: dict[str, int] = {}
    critical = high = medium = total_findings = 0
    for pe in report.pages:
        g = pe.grade.value
        grades[g] = grades.get(g, 0) + 1
        for f in pe.findings:
            total_findings += 1
            if f.severity == "critical":
                critical += 1
            elif f.severity == "high":
                high += 1
            elif f.severity == "medium":
                medium += 1
    ab = (grades.get("A", 0) + grades.get("B", 0)) / total
    df = (grades.get("D", 0) + grades.get("F", 0)) / total
    # TC-3880 Wave 2 (H8): c_rate tracks Grade C pages for heal loop visibility.
    c_rate = grades.get("C", 0) / total
    return ReportMetrics(
        critical_count=critical,
        high_count=high,
        medium_count=medium,
        grades=grades,
        ab_rate=ab,
        df_rate=df,
        c_rate=c_rate,
        total_findings=total_findings,
        total_pages=total,
    )


def _min_meaningful_delta(total_pages: int) -> float:
    """Return the minimum meaningful metric change for a run of total_pages.

    TC-3880 Wave 2 (H5): Symmetric threshold prevents noise-driven improvement
    declarations for small runs. For a 20-page run, 1/20 = 5% is the minimum
    meaningful change (one page flip). Clamped to [2%, 10%].
    """
    return max(0.02, min(0.10, 1.0 / max(total_pages, 1)))


def _detect_termination_condition(
    history: list["HealStep"],
    total_pages: int,
    min_steps: int = 2,
) -> str | None:
    """Detect convergence, oscillation, or plateau to exit heal loop early.

    TC-3880 Wave 2 (H7): Prevents infinite heal loops when no further improvement
    is possible. Three termination signals:
      - convergence: last 3 df_rates span < delta (metrics are flat)
      - oscillation: last 3 df_rates alternate direction (A→B→A pattern)
      - plateau: last 5 outcomes are all "unchanged"

    Returns None when no termination condition is met, or the condition name as str.
    Requires at least min_steps completed steps before checking.
    """
    if len(history) < min_steps:
        return None

    delta = _min_meaningful_delta(total_pages)

    # Plateau: last 5 consecutive "unchanged" outcomes
    if len(history) >= 5:
        last5 = history[-5:]
        if all(s.outcome == "unchanged" for s in last5):
            return "plateau"

    # Convergence: last 3 df_rates span < delta
    if len(history) >= 3:
        last3_df = [s.after_metrics.df_rate for s in history[-3:] if s.after_metrics is not None]
        if len(last3_df) == 3 and (max(last3_df) - min(last3_df)) < delta:
            return "converged"

        # Oscillation: last 3 df_rates alternate direction (↓↑ or ↑↓)
        if len(last3_df) == 3:
            d1 = last3_df[1] - last3_df[0]
            d2 = last3_df[2] - last3_df[1]
            if (d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0):
                if abs(d1) >= delta or abs(d2) >= delta:  # only if swings are meaningful
                    return "oscillating"

    return None


def _is_improved(before: ReportMetrics, after: ReportMetrics, threshold: float) -> bool:
    """Return True if metrics improved meaningfully.

    TC-3880 Wave 2 (H5): Uses symmetric delta derived from total page count
    rather than a hardcoded 1% threshold, preventing noise-driven declarations.
    Improvement signals: df_rate decreased OR ab_rate increased OR c_rate decreased.
    """
    delta = _min_meaningful_delta(before.total_pages or after.total_pages or 1)
    df_improved = after.df_rate < before.df_rate - delta
    ab_improved = after.ab_rate > before.ab_rate + delta
    # TC-3880 Wave 2 (H8): Grade C improvement as third signal.
    c_improved = after.c_rate < before.c_rate - delta
    return df_improved or ab_improved or c_improved


def _compress_heal_step(step: HealStep) -> str:
    """Compress a HealStep to a single-line summary string."""
    return (
        f"step={step.step_idx} worker={step.decision.action.worker} "
        f"outcome={step.outcome} confidence={step.decision.confidence:.2f}"
    )


def _build_diagnostician_prompt(
    report: EvaluationReport,
    history: list[HealStep],
    quarantine: list[dict],
    budget_summary: dict,
) -> str:
    """Build a diagnostician prompt from current state.

    Uses rolling compression: last 3 steps as full JSON, older steps as
    compressed 1-line summaries. This keeps prompt length bounded as steps grow.
    """
    if _DIAGNOSTICIAN_PROMPT_PATH.exists():
        system = _DIAGNOSTICIAN_PROMPT_PATH.read_text(encoding="utf-8")
    else:
        system = "You are a content quality diagnostician. Analyze the evaluation report and recommend one healing action."

    # Grade distribution
    grades: dict[str, int] = {}
    for pe in report.pages:
        g = pe.grade.value
        grades[g] = grades.get(g, 0) + 1

    # TC-3880 Wave 2 (H8): Include D/F pages first, then C pages (cap at 15 total).
    # Previously only D/F pages were shown, making Grade C pages invisible to heal.
    failing_df = [
        {"slug": pe.slug, "grade": pe.grade.value,
         "top_checks": sorted({f.check for f in pe.findings if f.severity in ("critical", "high")})[:3]}
        for pe in report.pages
        if pe.grade.value in ("D", "F")
    ]
    failing_c = [
        {"slug": pe.slug, "grade": pe.grade.value,
         "top_checks": sorted({f.check for f in pe.findings if f.severity == "medium"})[:3]}
        for pe in report.pages
        if pe.grade.value == "C"
    ]
    failing = (failing_df + failing_c)[:15]  # cap at 15 total (F→D→C order)

    total_pages = len(report.pages)
    c_rate = grades.get("C", 0) / max(total_pages, 1)
    eval_summary = json.dumps({
        "grade_distribution": grades,
        "failing_pages": failing,
        "total_pages": total_pages,
        "c_rate": round(c_rate, 3),
    }, separators=(",", ":"))  # compact JSON

    # Rolling compression: last _FULL_STEPS steps full, older steps compressed
    if len(history) <= _FULL_STEPS:
        full_steps = history
        compressed_steps: list[str] = []
    else:
        full_steps = history[-_FULL_STEPS:]
        compressed_steps = [_compress_heal_step(s) for s in history[:-_FULL_STEPS]]

    history_parts: list[str] = []
    if compressed_steps:
        history_parts.append("EARLIER (compressed): " + "; ".join(compressed_steps))
    if full_steps:
        recent_json = json.dumps([
            {
                "step": s.step_idx,
                "worker": s.decision.action.worker,
                "outcome": s.outcome,
                "confidence": s.decision.confidence,
            }
            for s in full_steps
        ], separators=(",", ":"))
        history_parts.append(f"RECENT (full): {recent_json}")

    history_summary = "\n".join(history_parts) if history_parts else "[]"

    quarantine_summary = json.dumps(quarantine[:5], separators=(",", ":"))
    budget_str = json.dumps({
        k: v for k, v in budget_summary.items()
        if k in ("elapsed_s", "counters")
    }, separators=(",", ":"))

    return (
        f"SYSTEM:\n{system}\n\n"
        f"EVAL:\n{eval_summary}\n\n"
        f"HISTORY:\n{history_summary}\n\n"
        f"QUARANTINE:\n{quarantine_summary}\n\n"
        f"BUDGET:\n{budget_str}\n\n"
        "Respond with ONLY the JSON HealDecision object."
    )


def _call_llm_sync(prompt: str, run_dir: Path) -> str | None:
    """Call LLM synchronously. Returns raw response string or None."""
    import os
    try:
        from launcher.clients.llm_provider import LLMProviderClient
        api_key = os.environ.get("litellm_key", "")
        base_url = os.environ.get("FOSS_LAUNCHER_LLM_BASE_URL", "https://llm.professionalize.com/v1")
        if not api_key:
            logger.warning("[heal] No LLM API key — skipping diagnostician call")
            return None
        provider = LLMProviderClient(
            api_base_url=base_url,
            model="qwen3-next",
            run_dir=run_dir,
            api_key=api_key,
            temperature=0.0,
        )
        messages = [{"role": "user", "content": prompt}]
        result = provider.chat_completion(messages, max_tokens=1024)
        return result.get("content") if isinstance(result, dict) else str(result)
    except Exception as exc:
        logger.warning("[heal] LLM call failed: %s", exc)
        return None


def _parse_heal_decision(response: str, min_confidence: float) -> HealDecision | None:
    """Parse and validate a HealDecision from LLM response string."""
    try:
        # Strip markdown code fences if present
        text = response.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        data = json.loads(text)
        decision = HealDecision.model_validate(data)
        if decision.confidence < min_confidence:
            logger.info(
                "[heal] Decision rejected: confidence %.2f < threshold %.2f",
                decision.confidence, min_confidence,
            )
            return None
        return decision
    except Exception as exc:
        logger.warning("[heal] Cannot parse HealDecision: %s", exc)
        return None


def _write_heal_plan(
    run_dir: Path,
    steps: list[HealStep],
    stop_reason: str,
    initial_metrics: ReportMetrics,
    final_metrics: ReportMetrics,
) -> HealResult:
    """Write heal_plan.json atomically. Returns the HealResult written."""
    from launcher.io.atomic import atomic_write_json
    result = HealResult(
        run_id=run_dir.name,
        steps=steps,
        stop_reason=stop_reason,
        initial_metrics=initial_metrics,
        final_metrics=final_metrics,
        total_fixes=sum(1 for s in steps if s.outcome == "improved"),
        total_regressions=sum(1 for s in steps if s.outcome == "regressed"),
        total_tokens=sum(s.tokens_used for s in steps),
        avg_confidence=sum(s.decision.confidence for s in steps) / max(len(steps), 1),
        engineering_only_findings=[],
    )
    atomic_write_json(run_dir / "heal_plan.json", result.model_dump(mode="json"))
    return result


def _write_quarantine(run_dir: Path, quarantine: list[dict]) -> None:
    """Write heal_quarantine.json atomically."""
    from launcher.io.atomic import atomic_write_json
    atomic_write_json(run_dir / "heal_quarantine.json", quarantine)


def _load_quarantine(run_dir: Path) -> list[dict]:
    """Load existing quarantine file if present."""
    q_path = run_dir / "heal_quarantine.json"
    if not q_path.exists():
        return []
    try:
        return json.loads(q_path.read_text(encoding="utf-8"))
    except Exception:
        return []


def _backup_artifact_files(run_dir: Path, step_idx: int, target_slugs: list[str]) -> list[Path]:
    """Back up content .md and .ir.json files for target_slugs before a re-run.

    TC-3881 Wave 3 (H1): Full artifact backup so regression can be rolled back.
    Returns list of backup files created.
    """
    backed_up: list[Path] = []
    tag = f"heal_bak_{step_idx}"

    def _safe_backup(src: Path) -> None:
        if src.exists():
            bak = src.with_suffix(src.suffix + f".{tag}")
            import shutil
            shutil.copy2(src, bak)
            backed_up.append(bak)

    # Back up checkpoint JSONs
    for ckpt_name in ("generate_checkpoint.json", "evaluate_checkpoint.json"):
        _safe_backup(run_dir / ckpt_name)

    # Back up per-slug files — search content and evaluation dirs
    for slug in target_slugs:
        safe_slug = slug.replace("/", "_").replace("\\", "_").strip("_") or slug
        for subdir in ("content", "evaluation/pages", ""):
            base = run_dir / subdir if subdir else run_dir
            for ext in (".md", ".ir.json", f".eval.json"):
                candidate = base / f"{safe_slug}{ext}"
                _safe_backup(candidate)

    return backed_up


def _restore_artifact_files(run_dir: Path, step_idx: int) -> None:
    """Restore backed-up artifact files from a previous _backup_artifact_files call.

    TC-3881 Wave 3 (H1): Called when regression is detected to undo the re-run.
    """
    tag = f".heal_bak_{step_idx}"
    restored = 0
    try:
        import shutil
        for bak in run_dir.rglob(f"*{tag}"):
            # Original path = bak without the ".heal_bak_N" suffix
            original = bak.with_name(bak.name[: -len(tag)])
            shutil.copy2(bak, original)
            bak.unlink()
            restored += 1
        logger.info("[heal] Artifact rollback complete: %d files restored (step %d)", restored, step_idx)
    except Exception as exc:
        logger.error("[heal] Artifact rollback failed: %s", exc)


def _cleanup_backup_files(run_dir: Path, step_idx: int) -> None:
    """Delete backup files without restoring (success path)."""
    tag = f".heal_bak_{step_idx}"
    for bak in run_dir.rglob(f"*{tag}"):
        try:
            bak.unlink()
        except Exception:
            pass


def _save_rollback_snapshot(run_dir: Path, step_idx: int, metrics: "ReportMetrics") -> None:
    """Save a rollback snapshot of current metrics before a re-run.

    TC-3881 Wave 3 (H1): Metrics snapshot. Content files are backed up separately
    via _backup_artifact_files (called at call site with target_slugs).
    """
    snapshot_path = run_dir / f"heal_rollback_{step_idx}.json"
    snapshot_path.write_text(metrics.model_dump_json(), encoding="utf-8")


def _remove_rollback_snapshot(run_dir: Path, step_idx: int) -> None:
    """Remove the transient rollback snapshot file after step completion."""
    snapshot_path = run_dir / f"heal_rollback_{step_idx}.json"
    if snapshot_path.exists():
        snapshot_path.unlink()


def _write_diagnosis(run_dir: Path, steps: list["HealStep"]) -> None:
    """Write structured heal_diagnosis.json for --mode diagnose."""
    actions = []
    for step in steps:
        if step.decision.action is not None:
            actions.append({
                "rank": step.step_idx + 1,
                "worker": step.decision.action.worker,
                "target_pages": step.decision.action.target_pages,
                "strategy": step.decision.action.strategy,
                "priority_checks": step.decision.action.priority_checks,
                "root_causes": step.decision.root_causes,
                "confidence": step.decision.confidence,
                "llm_hint": step.decision.analysis[:200] if step.decision.analysis else "",
                "severity_weight": 3.0,
            })
    # Sort by confidence descending
    actions.sort(key=lambda a: a["confidence"], reverse=True)
    from launcher.io.atomic import atomic_write_json
    diagnosis = {
        "run_dir": str(run_dir),
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "total_steps": len(steps),
        "actions": actions,
    }
    atomic_write_json(run_dir / "heal_diagnosis.json", diagnosis)


def _load_run_config(run_dir: Path) -> "dict | None":
    """Load run config from run_dir.

    Probes ``run_config.yaml`` first (backward compat), then ``run_config.json``.
    Returns the raw dict or None when neither file is found or both are unreadable.
    """
    yaml_path = run_dir / "run_config.yaml"
    json_path = run_dir / "run_config.json"

    if yaml_path.exists():
        try:
            import yaml
            with open(yaml_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception as exc:
            logger.warning("[heal] Failed to load run_config.yaml: %s", exc)

    if json_path.exists():
        try:
            return json.loads(json_path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("[heal] Failed to load run_config.json: %s", exc)

    logger.warning("[heal] No run_config.yaml or run_config.json found in %s", run_dir)
    return None


async def _execute_worker_rerun(
    *,
    run_dir: Path,
    worker: str,
    step_idx: int,
    max_steps: int,
    budget: "BudgetTracker",
    mode: str,
    checkpoint_id: str,
    current_metrics: "ReportMetrics",
    decision: "HealDecision | None" = None,
) -> "tuple[ReportMetrics | None, str, str | None, str]":
    """Execute or simulate pipeline re-run.

    Returns (after_metrics, outcome, fallback_reason, executed_mode).
    - mode='diagnose': returns (None, 'diagnose_only', None, 'diagnose') — no execution
    - mode='worker': validates checkpoint hash; falls back to 'full' if invalid
    - mode='full': full pipeline re-run with rollback on regression

    TC-3879 Wave 1 (H3): decision is now passed through to build heal_metadata so
    workers receive root_causes, priority_checks, target_pages, and strategy.
    """
    if mode == "diagnose":
        return (None, "diagnose_only", None, "diagnose")

    # Budget gate: need at least 60s remaining before attempting re-run
    remaining = budget.remaining_for_step(step_idx, max_steps)
    if remaining.get("remaining_runtime_s", 0) < 60:
        return (current_metrics, "budget_exceeded", None, mode)

    # Load RunConfig dict — required for execute_run
    config_dict = _load_run_config(run_dir)
    if config_dict is None:
        logger.warning("[heal] run_config not found in %s; skipping re-execution", run_dir)
        return (current_metrics, "unchanged", "config_not_found", mode)

    actual_mode = mode
    fallback_reason: str | None = None

    if mode == "worker":
        # Validate checkpoint integrity before attempting targeted re-run
        try:
            from launcher.resilience.checkpoint import (
                load_worker_checkpoint,
                restore_worker_checkpoint,
            )
            cp = load_worker_checkpoint(run_dir, checkpoint_id) if checkpoint_id else None
            if cp is None or not restore_worker_checkpoint(run_dir, cp):
                logger.warning(
                    "[heal] Checkpoint %s invalid; falling back to full mode", checkpoint_id
                )
                actual_mode = "full"
                fallback_reason = "checkpoint_invalid"
        except Exception as exc:
            logger.warning("[heal] Checkpoint validation failed: %s; falling back to full", exc)
            actual_mode = "full"
            fallback_reason = "checkpoint_invalid"

    # TC-3881 Wave 3 (H1): Back up artifacts + metrics before re-run
    _save_rollback_snapshot(run_dir, step_idx, current_metrics)
    _target_slugs: list[str] = (decision.action.target_pages or []) if decision is not None else []
    _backup_artifact_files(run_dir, step_idx, _target_slugs)

    try:
        # Defer execute_run import to avoid circular imports at module load
        from launcher.orchestrator.run_loop import execute_run
        from launcher.models.run_config import RunConfig

        # Build RunConfig from the raw dict
        try:
            config = RunConfig.model_validate(config_dict)
        except Exception as exc:
            logger.warning("[heal] RunConfig validation failed: %s; skipping re-execution", exc)
            _remove_rollback_snapshot(run_dir, step_idx)
            return (current_metrics, "unchanged", str(exc), actual_mode)

        original_run_id = run_dir.name
        # TC-3879 Wave 1 (H3): Build heal_metadata from decision so workers receive
        # root_causes, priority_checks, target_pages, and strategy during re-generation.
        _heal_metadata: dict = {}
        if decision is not None:
            # TC-3882 Wave 4 (H2): Extract section-level failing locations for targeted regen.
            _failing_sections: dict[str, list[str]] = {}
            if decision.action.target_pages:
                try:
                    from launcher.models.evaluation import EvaluationReport as _EvalReport
                    _eval_path = run_dir / "evaluate_checkpoint.json"
                    if _eval_path.exists():
                        _eval_report = _EvalReport.model_validate_json(
                            _eval_path.read_text(encoding="utf-8")
                        )
                        _failing_sections = _extract_failing_sections(
                            _eval_report, decision.action.target_pages
                        )
                except Exception as _exc:
                    logger.debug("[heal] Could not extract failing sections: %s", _exc)

            _heal_metadata = {
                "responsible_worker": decision.action.worker,
                "target_pages": decision.action.target_pages,
                "priority_checks": decision.action.priority_checks,
                "root_causes": decision.root_causes,
                "strategy": decision.action.strategy,
                "heal_step": step_idx,
                "heal_max_steps": max_steps,  # TC-3882 (E8): for final-step detection
                "eval_fast_path": step_idx < max_steps - 1,
                "failing_section_ids": _failing_sections,  # TC-3882 (H2)
            }
        # Signature verified against run_loop.execute_run as of TC-3879-H3.
        # Accepted kwargs: resume_from, stop_after, run_id, runs_root, heal_metadata (all present).
        # If run_loop signature changes, update this call and TC-3879-H3 taskcard.
        result = await execute_run(
            config,
            resume_from=worker,
            stop_after="evaluate",
            run_id=original_run_id,
            runs_root=run_dir.parent,
            heal_metadata=_heal_metadata,
        )

        # Extract new metrics from re-run result
        if result is not None and hasattr(result, "report") and result.report is not None:
            after_metrics = _extract_metrics(result.report)
        else:
            after_metrics = current_metrics

        # TC-3880 Wave 2 (H5): Use symmetric delta based on total_pages.
        _delta = _min_meaningful_delta(current_metrics.total_pages or after_metrics.total_pages or 1)
        outcome: str
        if _is_improved(current_metrics, after_metrics, _delta):
            outcome = "improved"
        elif after_metrics.df_rate > current_metrics.df_rate + _delta:
            outcome = "regressed"
        else:
            outcome = "unchanged"

        if outcome == "regressed":
            logger.warning(
                "[heal] Step %d regressed (df_rate %.3f → %.3f); restoring artifacts.",
                step_idx,
                current_metrics.df_rate if current_metrics else 0.0,
                after_metrics.df_rate if after_metrics else 0.0,
            )
            _restore_artifact_files(run_dir, step_idx)  # TC-3881 (H1)
        else:
            _cleanup_backup_files(run_dir, step_idx)  # TC-3881 (H1)
        _remove_rollback_snapshot(run_dir, step_idx)

        return (after_metrics, outcome, fallback_reason, actual_mode)

    except BudgetExceededError:
        _cleanup_backup_files(run_dir, step_idx)
        _remove_rollback_snapshot(run_dir, step_idx)
        return (current_metrics, "budget_exceeded", fallback_reason, actual_mode)
    except Exception as exc:
        logger.error("[heal] Re-execution failed: %s", exc)
        _cleanup_backup_files(run_dir, step_idx)
        _remove_rollback_snapshot(run_dir, step_idx)
        return (current_metrics, "unchanged", str(exc), actual_mode)


def _extract_failing_sections(
    report: "EvaluationReport",
    target_pages: list[str],
) -> dict[str, list[str]]:
    """Extract section-level failing locations for targeted heal re-generation.

    TC-3882 Wave 4 (H2): Returns {slug: [section_headings]} for each target page.
    Only includes findings that can be attributed to a specific section
    (finding.location contains '##' or '/' path indicator, or section_id is set).

    Falls back to empty list for pages where findings have no section attribution —
    the generate worker will then regenerate the full page.
    """
    result: dict[str, list[str]] = {}
    target_set = set(target_pages)

    for pe in report.pages:
        if pe.slug not in target_set:
            continue
        section_ids: list[str] = []
        for f in pe.findings:
            if f.severity not in ("critical", "high", "medium"):
                continue
            # Prefer explicit section_id field
            if getattr(f, "section_id", None):
                section_ids.append(f.section_id)  # type: ignore[arg-type]
            # Fall back to location if it looks like a section reference
            elif f.location and ("##" in f.location or ":section" in f.location):
                # Extract section heading from location like "slug:section" or "## Heading"
                loc = f.location
                if ":section" in loc:
                    pass  # section_id would have been set; skip bare ":section"
                elif "##" in loc:
                    heading = loc.split("##", 1)[-1].strip()
                    if heading:
                        section_ids.append(heading)
        # Deduplicate while preserving order
        seen: set[str] = set()
        deduped: list[str] = []
        for sid in section_ids:
            if sid not in seen:
                seen.add(sid)
                deduped.append(sid)
        result[pe.slug] = deduped

    return result


def _prioritize_target_pages(
    report: EvaluationReport,
    budget: BudgetTracker,
    step_idx: int,
    max_steps: int,
) -> list[str]:
    """Return failing page slugs sorted F→D→C→B, capped by budget's calls_per_step.

    Sort key: grade severity (F=0 worst, A=4 best), then page_id ascending for determinism.
    Cap is max(1, calls_per_step) from remaining_for_step().
    """
    failing = [pe for pe in report.pages if pe.grade.value in ("F", "D", "C")]
    prioritized = sorted(
        failing,
        key=lambda pe: (_GRADE_SEVERITY.get(pe.grade.value, 99), pe.slug),
    )
    step_budget = budget.remaining_for_step(step_idx, max_steps)
    cap = max(1, step_budget.get("calls_per_step", 1))
    return [pe.slug for pe in prioritized[:cap]]


async def run_heal(
    run_dir: Path,
    dry_run: bool = False,
    max_steps: int = _DEFAULT_MAX_STEPS,
    min_confidence: float = _DEFAULT_MIN_CONFIDENCE,
    min_steps: int = 1,
    regression_threshold: float = _DEFAULT_REGRESSION_THRESHOLD,
    mode: str = "worker",
) -> HealResult | None:
    """Execute the LLM-driven heal loop.

    Returns HealResult on completion, None if heal cannot start
    (missing eval report, already locked, etc.).
    """
    run_dir = Path(run_dir).resolve()
    if not run_dir.is_dir():
        typer.echo(f"[heal] run_dir does not exist: {run_dir}", err=True)
        return None

    # Load eval report
    report = _load_eval_report(run_dir)
    if report is None:
        typer.echo(f"[heal] No evaluate_checkpoint.json in {run_dir}", err=True)
        return None

    initial_metrics = _extract_metrics(report)
    current_metrics = initial_metrics
    steps: list[HealStep] = []
    quarantine = _load_quarantine(run_dir)
    stop_reason = "max_steps"
    _heal_result: HealResult | None = None

    budget = BudgetTracker(budgets=_DEFAULT_BUDGETS)
    _session_start = time.monotonic()

    # Enable LLM disk cache for the heal session; restore original value on exit.
    _CACHE_VAR = "FOSS_LAUNCHER_LLM_CACHE"
    _prior_cache: str | None = os.environ.get(_CACHE_VAR)
    os.environ[_CACHE_VAR] = "1"
    logger.info("[heal] LLM disk cache enabled for heal session (%s=1)", _CACHE_VAR)

    try:
        with RunLock(run_dir, worker="heal"):
            for step_idx in range(max_steps):
                step_start = time.monotonic()

                # Session-level timeout guard
                if time.monotonic() - _session_start > _SESSION_TIMEOUT_S:
                    stop_reason = "session_timeout"
                    typer.echo(f"[heal] Session timeout ({_SESSION_TIMEOUT_S}s) at step {step_idx}")
                    break

                # Check budget
                try:
                    budget.check_runtime()
                except BudgetExceededError as exc:
                    stop_reason = "budget_exceeded"
                    typer.echo(f"[heal] Budget exceeded at step {step_idx}: {exc}")
                    break

                # TC-3880 Wave 2 (H7): Check for convergence/oscillation/plateau
                # before calling the LLM. Exit early if metrics are flat.
                _termination = _detect_termination_condition(
                    steps, initial_metrics.total_pages, min_steps=2
                )
                if _termination is not None:
                    stop_reason = _termination
                    typer.echo(
                        f"[heal] Termination condition '{_termination}' detected at step {step_idx} — exiting."
                    )
                    break

                # Build prompt
                budget_summary = budget.get_summary()
                prompt = _build_diagnostician_prompt(report, steps, quarantine, budget_summary)

                if dry_run:
                    typer.echo(f"[heal] DRY RUN step {step_idx}: prompt built ({len(prompt)} chars)")
                    typer.echo(f"[heal] Current metrics: D+F={current_metrics.df_rate:.1%}, A+B={current_metrics.ab_rate:.1%}")
                    # In dry-run, produce a synthetic decision for display
                    failing_pages = [pe.slug for pe in report.pages if pe.grade.value in ("D", "F")]
                    decision_dict = {
                        "analysis": "Dry-run mode: no LLM call made.",
                        "root_causes": ["dry_run"],
                        "action": {
                            "worker": "generate",
                            "target_pages": failing_pages[:3],
                            "strategy": "Dry-run placeholder strategy",
                            "priority_checks": [],
                        },
                        "confidence": 0.5,
                        "stop_recommendation": True,
                        "stop_reason": "dry_run",
                    }
                    typer.echo(json.dumps(decision_dict, indent=2))
                    stop_reason = "dry_run"
                    break

                # Call LLM
                raw_response = _call_llm_sync(prompt, run_dir)
                if raw_response is None:
                    typer.echo("[heal] LLM unavailable — stopping heal session")
                    stop_reason = "llm_unavailable"
                    break

                # Parse and validate decision
                decision = _parse_heal_decision(raw_response, min_confidence)
                if decision is None:
                    # Schema failure — record but continue if we have budget
                    step = HealStep(
                        step_idx=step_idx,
                        decision=HealDecision(
                            analysis="Failed to parse response",
                            root_causes=[],
                            action=HealAction(
                                worker="generate",
                                target_pages=[],
                                strategy="schema_failure",
                                priority_checks=[],
                            ),
                            confidence=0.0,
                            stop_recommendation=False,
                            stop_reason=None,
                        ),
                        before_metrics=current_metrics,
                        after_metrics=None,
                        outcome="schema_failure",
                        checkpoint_id="",
                        execution_seconds=time.monotonic() - step_start,
                        tokens_used=0,
                    )
                    steps.append(step)
                    continue

                # TC-3897: Engineering escalation override — before quarantine check.
                # If density/completeness/artifacts routed to generate but generate was
                # unchanged for N consecutive steps, re-route to understand so claims
                # are re-extracted with more depth.
                if decision.action.worker == "generate" and len(steps) >= 2:
                    try:
                        from launcher.workers.evaluate.diagnosis import (
                            diagnose_root_causes,
                            escalate_diagnosis,
                            earliest_responsible_worker,
                        )
                        _diagnoses = diagnose_root_causes(report.pages, min_severity="high")
                        _escalated = escalate_diagnosis(
                            prior_steps=steps,
                            current_diagnoses=_diagnoses,
                        )
                        _escalated_worker = earliest_responsible_worker(_escalated)
                        if _escalated_worker == "understand":
                            typer.echo(
                                f"[heal] Step {step_idx}: TC-3897 escalation — "
                                "overriding generate→understand (persistent density/artifacts)"
                            )
                            decision = decision.model_copy(
                                update={
                                    "action": decision.action.model_copy(
                                        update={
                                            "worker": "understand",
                                            "strategy": (
                                                "TC-3897: Escalated from generate after "
                                                f"{len(steps)} unchanged steps — "
                                                "re-extract claims with richer evidence"
                                            ),
                                        }
                                    )
                                }
                            )
                    except Exception as _exc:
                        logger.debug("[heal] TC-3897 escalation check failed: %s", _exc)

                # Check quarantine — TC-3882 Wave 4 (H6): Strike-count backoff.
                # 1 strike → skip 2 steps; 2 strikes → skip 5; ≥3 strikes → permanent.
                worker = decision.action.worker
                quarantine_key = f"{worker}:{','.join(sorted(decision.action.priority_checks))}"
                _q_entry = next((q for q in quarantine if q.get("key") == quarantine_key), None)
                if _q_entry is not None:
                    _next_eligible = _q_entry.get("next_eligible_step", 999)
                    if step_idx < _next_eligible:
                        typer.echo(
                            f"[heal] Step {step_idx}: action quarantined ({quarantine_key}), "
                            f"strikes={_q_entry.get('strikes', 1)}, "
                            f"eligible at step {_next_eligible}, skipping"
                        )
                        continue  # skip step, don't stop — try next iteration

                if decision.stop_recommendation and step_idx >= min_steps:
                    stop_reason = "llm_stop"
                    typer.echo(f"[heal] Step {step_idx}: LLM recommends stopping: {decision.stop_reason}")
                    break

                typer.echo(
                    f"[heal] Step {step_idx}: worker={worker}, "
                    f"confidence={decision.confidence:.2f}, "
                    f"strategy={decision.action.strategy[:60]}"
                )

                # Write checkpoint before execution
                cp_data = decision.model_dump(mode="json")
                cp_file = run_dir / f"heal_step_{step_idx}.json"
                cp_file.write_text(json.dumps(cp_data), encoding="utf-8")
                checkpoint_id = ""
                try:
                    from launcher.resilience.checkpoint import write_worker_checkpoint
                    wcp = write_worker_checkpoint(
                        run_dir=run_dir,
                        worker=f"heal_step_{step_idx}",
                        artifact_path=cp_file,
                    )
                    checkpoint_id = wcp.checkpoint_id
                except Exception:
                    checkpoint_id = ""

                # Execute or simulate pipeline re-run based on mode
                # TC-3879 Wave 1 (H3): Pass decision so heal_metadata is built and threaded.
                after_metrics_raw, outcome, fallback_reason, executed_mode = await _execute_worker_rerun(
                    run_dir=run_dir,
                    worker=worker,
                    step_idx=step_idx,
                    max_steps=max_steps,
                    budget=budget,
                    mode=mode,
                    checkpoint_id=checkpoint_id,
                    current_metrics=current_metrics,
                    decision=decision,
                )
                # after_metrics is None only for diagnose mode — keep current for metrics tracking
                after_metrics = after_metrics_raw if after_metrics_raw is not None else current_metrics

                tokens_used = len(prompt.split()) + _ESTIMATED_OUTPUT_TOKENS
                try:
                    budget.record_llm_call(input_tokens=len(prompt.split()), output_tokens=512)
                except Exception:
                    pass

                step = HealStep(
                    step_idx=step_idx,
                    decision=decision,
                    before_metrics=current_metrics,
                    after_metrics=after_metrics_raw,
                    outcome=outcome,
                    checkpoint_id=checkpoint_id,
                    execution_seconds=time.monotonic() - step_start,
                    tokens_used=tokens_used,
                    mode=mode,
                    executed_mode=executed_mode,
                    fallback_reason=fallback_reason,
                )
                steps.append(step)

                # Update quarantine if regression — TC-3882 (H6): strike-count backoff.
                if outcome == "regressed":
                    _existing_q = next((q for q in quarantine if q.get("key") == quarantine_key), None)
                    if _existing_q is None:
                        # First strike: skip next 2 steps
                        quarantine.append({
                            "key": quarantine_key,
                            "step": step_idx,
                            "strikes": 1,
                            "last_strategy": (decision.action.strategy or "")[:80],
                            "next_eligible_step": step_idx + 3,
                        })
                    else:
                        _existing_q["strikes"] = _existing_q.get("strikes", 1) + 1
                        _existing_q["step"] = step_idx
                        _existing_q["last_strategy"] = (decision.action.strategy or "")[:80]
                        _strikes = _existing_q["strikes"]
                        if _strikes == 2:
                            _existing_q["next_eligible_step"] = step_idx + 6  # skip 5 more
                        else:
                            _existing_q["next_eligible_step"] = 999  # permanent after 3+
                    _write_quarantine(run_dir, quarantine)

                # Advance rolling baseline so next step's before_metrics reflects current state
                if after_metrics_raw is not None:
                    current_metrics = after_metrics_raw

            # end for

    except RunAlreadyActiveError:
        typer.echo("[heal] Another heal process is already running on this run_dir", err=True)
        return None
    finally:
        # Restore prior FOSS_LAUNCHER_LLM_CACHE value
        if _prior_cache is None:
            os.environ.pop(_CACHE_VAR, None)
        else:
            os.environ[_CACHE_VAR] = _prior_cache

        # Always write heal_plan.json
        try:
            _heal_result = _write_heal_plan(run_dir, steps, stop_reason, initial_metrics, current_metrics)
            typer.echo(f"[heal] Wrote heal_plan.json ({len(steps)} steps, stop={stop_reason})")
        except Exception as exc:
            logger.warning("[heal] Failed to write heal_plan.json: %s", exc)
            _heal_result = None

        # Cleanup old checkpoints
        try:
            from launcher.resilience.checkpoint import cleanup_old_checkpoints
            cleanup_old_checkpoints(run_dir, keep_last_n=3)
        except Exception:
            pass

    return _heal_result


@heal_app.command()
def heal(
    run_dir: Path = typer.Argument(..., help="Path to a completed pipeline run directory"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print HealDecision without executing"),
    max_steps: int = typer.Option(_DEFAULT_MAX_STEPS, "--max-steps", help="Maximum heal iterations"),
    min_confidence: float = typer.Option(_DEFAULT_MIN_CONFIDENCE, "--min-confidence"),
    min_steps: int = typer.Option(1, "--min-steps", help="Minimum steps before stop_recommendation honored"),
    regression_threshold: float = typer.Option(_DEFAULT_REGRESSION_THRESHOLD, "--regression-threshold"),
    mode: str = typer.Option(
        "worker",
        "--mode",
        help=(
            "Execution mode: 'full' (full pipeline re-run with rollback), "
            "'worker' (targeted re-run, default), "
            "'diagnose' (no execution, writes heal_diagnosis.json)"
        ),
    ),
) -> None:
    """Run iterative LLM-driven healing on a completed pipeline run."""
    if mode not in _VALID_MODES:
        raise typer.BadParameter(
            f"--mode must be one of: {', '.join(sorted(_VALID_MODES))}"
        )
    result = asyncio.run(run_heal(
        run_dir=run_dir,
        dry_run=dry_run,
        max_steps=max_steps,
        min_confidence=min_confidence,
        min_steps=min_steps,
        regression_threshold=regression_threshold,
        mode=mode,
    ))
    if result is None:
        raise typer.Exit(code=1)

    # For diagnose mode: write heal_diagnosis.json and exit with code 2 if failing pages
    if mode == "diagnose" and result is not None:
        _write_diagnosis(Path(run_dir).resolve(), result.steps)
        typer.echo(f"[heal] Diagnosis complete: {len(result.steps)} steps analyzed")
        if result.final_metrics.df_rate > 0:
            raise typer.Exit(code=2)
        return

    typer.echo(
        f"[heal] Session complete: {result.total_fixes} fixes, "
        f"{result.total_regressions} regressions, stop={result.stop_reason}"
    )
