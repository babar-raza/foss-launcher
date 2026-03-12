"""Phase snapshot promotion — IR store + phase_store updater.

Promotes best-grade PageIR files from a run into snapshots/ (mirroring
deploy/ path-for-path) and updates phase_store/ with run-level phase
JSONs from the dominant run.

Path invariants (never deviate):
    snapshots_dir / (content_path + ".ir.json")  — IR destination
    phase_store_dir / family / platform / *.json  — phase JSON destination

TC-3906
TC-3906-H7: event emission to events.ndjson
"""

from __future__ import annotations

import json
import logging
import os
import shutil
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import List

from pydantic import Field

from launcher.io.atomic import atomic_write_text
from launcher.io.hashing import sha256_file
from launcher.models.base import LauncherBaseModel
from launcher.models.evaluation import EvaluationReport, Grade

from .promoter import GRADE_RANK, grade_ge  # TC-3906-H3: grade_ge is now public
from .snapshot_manifest import (
    SnapshotIREntry,
    SnapshotManifest,
    load_snapshot_manifest,
    save_snapshot_manifest,
)

logger = logging.getLogger(__name__)


class IRPromotionAction(str, Enum):
    """Actions taken during IR promotion decisions."""

    PROMOTED = "promoted"
    SKIPPED_GRADE_LOW = "skipped_grade_low"
    SKIPPED_NO_IMPROVEMENT = "skipped_no_improvement"
    SKIPPED_SAME_HASH = "skipped_same_hash"
    SKIPPED_MISSING_IR = "skipped_missing_ir"


class IRPromotionResult(LauncherBaseModel):
    """Result of promotion decision for a single page IR."""

    content_path: str
    action: IRPromotionAction
    old_grade: str = ""
    new_grade: str = ""
    source_run_id: str = ""


class PhasePromotionReport(LauncherBaseModel, frozen=False):
    """Summary of a promote_phase_snapshots operation."""

    run_id: str
    total_pages_in_run: int = 0
    ir_promoted: int = 0
    ir_skipped_grade_low: int = 0
    ir_skipped_no_improvement: int = 0
    ir_skipped_same_hash: int = 0
    ir_skipped_missing_ir: int = 0
    phase_jsons_updated: bool = False
    details: List[IRPromotionResult] = Field(default_factory=list)


def _emit_event(events_path: Path, event_type: str, run_id: str, ts: str, data: dict) -> None:
    """Append a single event to events.ndjson, logging errors silently.

    TC-3906-H7: snapshot promotion audit trail.
    """
    try:
        from launcher.models.event import Event
        from launcher.state.event_log import append_event

        event = Event(event_type=event_type, run_id=run_id, timestamp=ts, data=data)
        events_path.parent.mkdir(parents=True, exist_ok=True)
        append_event(events_path, event)
    except Exception:
        logger.warning(
            "Failed to emit event %s to %s", event_type, events_path, exc_info=True
        )


def _resolve_ir_file(run_dir: Path, content_path: str) -> Path | None:
    """Find the .ir.json file for a content_path in the run's content bundle."""
    candidate = run_dir / "content_bundle" / "pages" / (content_path + ".ir.json")
    return candidate if candidate.exists() else None


def _find_eval_report(run_dir: Path) -> Path | None:
    """Locate the evaluation report in the run directory."""
    root_report = run_dir / "evaluation_report.json"
    if root_report.exists():
        return root_report
    summary = run_dir / "evaluation" / "evaluation_summary.json"
    return summary if summary.exists() else None


def _update_phase_store_metadata(
    run_dir: Path,
    phase_store_dir: Path,
    family: str,
    platform: str,
) -> None:
    """Copy pipeline metadata phase JSONs unconditionally on every complete run.

    Scout and Understand phase JSONs are infrastructure metadata (files_enumerated,
    format_matrix_count, claims), NOT content quality indicators. They must be updated
    on every complete run, regardless of whether the run wins the majority-run gate.
    TC-4105
    """
    from launcher.io.run_layout import RunLayout

    layout = RunLayout(run_dir=run_dir)

    metadata_sources: dict[str, Path] = {
        "scout.json": run_dir / "scout.json",
        "understand.json": layout.understanding_bundle,
    }

    dest_dir = phase_store_dir / family / platform
    dest_dir.mkdir(parents=True, exist_ok=True)

    for dest_name, src in metadata_sources.items():
        if not src.exists():
            logger.debug("Metadata phase file not found, skipping: %s", src.name)
            continue
        dest = dest_dir / dest_name
        tmp = dest.with_suffix(".tmp")
        try:
            shutil.copy2(src, tmp)
            os.replace(tmp, dest)
            logger.debug("Updated metadata phase_store %s from %s", dest_name, src.name)
        except Exception:
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
            logger.warning("Failed to copy %s to metadata phase_store", src.name, exc_info=True)


def _update_phase_store(
    run_dir: Path,
    phase_store_dir: Path,
    family: str,
    platform: str,
) -> None:
    """Copy run-level phase JSONs to phase_store/{family}/{platform}/ atomically.

    Source filenames are derived from RunLayout (single source of truth).
    Each file is written via a temp-file + os.replace() to avoid partial writes.
    Only called for the majority run (most IR slots won). TC-3906-H4
    Note: scout.json and understand.json are handled by _update_phase_store_metadata()
    which is called unconditionally for all complete runs. TC-4105
    """
    from launcher.io.run_layout import RunLayout

    layout = RunLayout(run_dir=run_dir)

    # Canonical source → destination name mapping, derived from RunLayout
    # scout.json + understand.json intentionally excluded — see _update_phase_store_metadata()
    phase_sources: dict[str, Path] = {
        "plan.json": run_dir / "planner_checkpoint.json",
        "generate.json": run_dir / "generate_checkpoint.json",
        "evaluate.json": run_dir / "evaluate_checkpoint.json",
    }

    dest_dir = phase_store_dir / family / platform
    dest_dir.mkdir(parents=True, exist_ok=True)

    for dest_name, src in phase_sources.items():
        if not src.exists():
            logger.debug("Phase file not found, skipping: %s", src.name)
            continue
        dest = dest_dir / dest_name
        tmp = dest.with_suffix(".tmp")
        try:
            shutil.copy2(src, tmp)
            os.replace(tmp, dest)
            logger.debug("Updated phase_store %s from %s", dest_name, src.name)
        except Exception:
            if tmp.exists():
                tmp.unlink(missing_ok=True)
            logger.warning("Failed to copy %s to phase_store", src.name, exc_info=True)


def promote_phase_snapshots(
    run_dir: Path,
    snapshots_dir: Path,
    phase_store_dir: Path,
    family: str,
    platform: str,
    *,
    min_grade: Grade = Grade.C,
    dry_run: bool = False,
    events_path: Path | None = None,
) -> PhasePromotionReport:
    """Promote qualifying IR files from a run into the snapshots/ store.

    For each page in the run's evaluation_report.json:
    - Finds the .ir.json in content_bundle/pages/
    - Promotes to snapshots_dir/(content_path+".ir.json") if grade >= incumbent
    - SHA-256 dedup: skips unchanged content

    Majority tracking (TC-3906-H1):
    Per-run IR slot counts are accumulated in manifest.run_ir_counts across
    all calls. The run with the highest *cumulative* total becomes the majority
    run; its phase JSONs are written to phase_store/{family}/{platform}/.
    This is correct across backfill_runs() scenarios where a single run's slots
    are promoted in multiple separate calls.

    Path invariant: snapshots_dir / (content_path + ".ir.json") — always.

    Args:
        run_dir: Completed run directory with evaluation_report.json and content_bundle/.
        snapshots_dir: Root of the snapshots/ store.
        phase_store_dir: Root of the phase_store/ store.
        family: Product family (e.g. "cells").
        platform: Platform (e.g. "python").
        min_grade: Minimum grade to allow promotion (default: C).
        dry_run: If True, report what would change without writing files.
        events_path: Optional path to events.ndjson for audit trail. When None
            (default), no events are emitted — preserves backward compatibility.
            TC-3906-H7.

    Returns:
        PhasePromotionReport summarising actions taken.
    """
    run_id = run_dir.name
    report = PhasePromotionReport(run_id=run_id)

    eval_path = _find_eval_report(run_dir)
    if eval_path is None:
        logger.warning("No evaluation report in %s — skipping phase snapshot promotion", run_id)
        return report

    try:
        raw = json.loads(eval_path.read_text(encoding="utf-8"))
        eval_report = EvaluationReport.model_validate(raw)
    except Exception:
        logger.error("Cannot parse evaluation report at %s", eval_path, exc_info=True)
        return report

    report.total_pages_in_run = len(eval_report.pages)

    # TC-4105: Always update pipeline metadata phase JSONs (scout/understand) for any
    # complete run, regardless of majority-run gate. These are infrastructure metadata,
    # not content quality indicators.
    if not dry_run:
        _update_phase_store_metadata(run_dir, phase_store_dir, family, platform)

    if not eval_report.pages:
        return report

    manifest_path = snapshots_dir / "snapshot_manifest.json"
    manifest = (
        load_snapshot_manifest(manifest_path)
        if (not dry_run or manifest_path.exists())
        else SnapshotManifest()
    )

    now = datetime.now(timezone.utc).isoformat()
    ir_won_this_run = 0

    for page_eval in eval_report.pages:
        content_path = page_eval.content_path or page_eval.slug
        if not content_path:
            continue

        grade = page_eval.grade

        # Minimum grade gate
        if not grade_ge(grade, min_grade):
            report.ir_skipped_grade_low += 1
            report.details.append(IRPromotionResult(
                content_path=content_path,
                action=IRPromotionAction.SKIPPED_GRADE_LOW,
                new_grade=grade.value,
                source_run_id=run_id,
            ))
            continue

        # Find IR source file
        ir_source = _resolve_ir_file(run_dir, content_path)
        if ir_source is None:
            logger.warning("IR file not found for %s in %s", content_path, run_id)
            report.ir_skipped_missing_ir += 1
            report.details.append(IRPromotionResult(
                content_path=content_path,
                action=IRPromotionAction.SKIPPED_MISSING_IR,
                new_grade=grade.value,
                source_run_id=run_id,
            ))
            continue

        source_hash = sha256_file(ir_source)

        # Check against incumbent
        existing = manifest.pages.get(content_path)
        if existing is not None:
            if existing.sha256 == source_hash:
                report.ir_skipped_same_hash += 1
                report.details.append(IRPromotionResult(
                    content_path=content_path,
                    action=IRPromotionAction.SKIPPED_SAME_HASH,
                    old_grade=existing.grade.value,
                    new_grade=grade.value,
                    source_run_id=run_id,
                ))
                continue

            if not grade_ge(grade, existing.grade):
                report.ir_skipped_no_improvement += 1
                report.details.append(IRPromotionResult(
                    content_path=content_path,
                    action=IRPromotionAction.SKIPPED_NO_IMPROVEMENT,
                    old_grade=existing.grade.value,
                    new_grade=grade.value,
                    source_run_id=run_id,
                ))
                continue

        # Promote IR file
        # Path invariant: snapshots_dir / (content_path + ".ir.json") — always
        snapshot_file = content_path + ".ir.json"
        dest_path = snapshots_dir / snapshot_file

        old_grade = existing.grade.value if existing else ""

        if not dry_run:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_text(
                dest_path,
                ir_source.read_text(encoding="utf-8"),
                validate_boundary=snapshots_dir,
            )
            if events_path is not None:
                _emit_event(
                    events_path,
                    event_type="snapshot_ir_promoted",
                    run_id=run_id,
                    ts=now,
                    data={
                        "content_path": content_path,
                        "old_grade": old_grade or None,
                        "new_grade": grade.value,
                        "sha256": source_hash,
                        "snapshot_file": snapshot_file,
                    },
                )
        manifest.pages[content_path] = SnapshotIREntry(
            content_path=content_path,
            snapshot_file=snapshot_file,
            source_run_id=run_id,
            grade=grade,
            sha256=source_hash,
            promoted_at=now,
        )

        ir_won_this_run += 1
        report.ir_promoted += 1
        report.details.append(IRPromotionResult(
            content_path=content_path,
            action=IRPromotionAction.PROMOTED,
            old_grade=old_grade,
            new_grade=grade.value,
            source_run_id=run_id,
        ))

    # Accumulate per-run IR counts and determine majority run (TC-3906-H1 fix).
    # Correct across backfill: compare cumulative totals, not per-call counts.
    manifest.run_ir_counts[run_id] = manifest.run_ir_counts.get(run_id, 0) + ir_won_this_run
    run_total = manifest.run_ir_counts[run_id]
    if run_total > manifest.majority_run_ir_count:
        manifest.majority_run_id = run_id
        manifest.majority_run_ir_count = run_total
        if not dry_run:
            _update_phase_store(run_dir, phase_store_dir, family, platform)
            report.phase_jsons_updated = True
            logger.info(
                "Run %s is new majority run (%d IR slots cumulative) — phase_store updated",
                run_id, run_total,
            )
            if events_path is not None:
                _emit_event(
                    events_path,
                    event_type="phase_store_updated",
                    run_id=run_id,
                    ts=now,
                    data={
                        "family": family,
                        "platform": platform,
                        "ir_won_count": run_total,
                        "phase_files_written": [
                            "scout.json", "understand.json", "plan.json",
                            "generate.json", "evaluate.json",
                        ],
                    },
                )

    # Save manifest
    if not dry_run and report.ir_promoted > 0:
        manifest.last_promotion = now
        manifest.promotion_count += 1
        snapshots_dir.mkdir(parents=True, exist_ok=True)
        save_snapshot_manifest(manifest_path, manifest)

    logger.info(
        "Phase snapshot promotion for %s: promoted=%d skipped_grade=%d "
        "skipped_no_improvement=%d skipped_same=%d skipped_missing=%d",
        run_id,
        report.ir_promoted,
        report.ir_skipped_grade_low,
        report.ir_skipped_no_improvement,
        report.ir_skipped_same_hash,
        report.ir_skipped_missing_ir,
    )

    return report
