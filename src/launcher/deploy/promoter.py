"""Deploy promotion logic — accumulate best pages across runs."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import List

from pydantic import Field

from launcher.io.atomic import atomic_write_text
from launcher.io.hashing import sha256_file
from launcher.models.base import LauncherBaseModel
from launcher.models.evaluation import EvaluationReport, Grade

from .manifest import DeployManifest, DeployedPage, load_manifest, save_manifest

logger = logging.getLogger(__name__)

GRADE_RANK: dict[Grade, int] = {
    Grade.A: 5,
    Grade.B: 4,
    Grade.C: 3,
    Grade.D: 2,
    Grade.F: 1,
}


def grade_ge(candidate: Grade, incumbent: Grade) -> bool:
    """True if candidate grade is equal or better than incumbent."""
    return GRADE_RANK[candidate] >= GRADE_RANK[incumbent]


# Backward-compatible alias (tests imported the original private name)
_grade_ge = grade_ge


class PromotionAction(str, Enum):
    """Actions taken during page promotion decisions."""

    PROMOTED = "promoted"
    SKIPPED_GRADE_LOW = "skipped_grade_low"
    SKIPPED_NO_IMPROVEMENT = "skipped_no_improvement"
    SKIPPED_SAME_HASH = "skipped_same_hash"
    SKIPPED_MISSING_FILE = "skipped_missing_file"


class PagePromotionResult(LauncherBaseModel):
    """Result of promotion decision for a single page."""

    content_path: str
    action: PromotionAction
    old_grade: str = ""
    new_grade: str = ""
    source_run_id: str = ""


class PromotionReport(LauncherBaseModel, frozen=False):
    """Summary of a promote_run operation."""

    run_id: str
    total_pages_in_run: int = 0
    promoted: int = 0
    skipped_grade_low: int = 0
    skipped_no_improvement: int = 0
    skipped_same_hash: int = 0
    skipped_missing_file: int = 0
    details: List[PagePromotionResult] = Field(default_factory=list)


def _find_eval_report(run_dir: Path) -> Path | None:
    """Locate the evaluation report, checking both known paths.

    Prefers the root-level file (written by run_loop.py) over the
    evaluate worker's summary in the evaluation/ subdirectory.
    """
    root_report = run_dir / "evaluation_report.json"
    if root_report.exists():
        return root_report
    summary = run_dir / "evaluation" / "evaluation_summary.json"
    if summary.exists():
        return summary
    return None


def is_run_complete(run_dir: Path) -> bool:
    """Check if a run directory has evaluation results and content."""
    if not _find_eval_report(run_dir):
        return False
    content_dir = run_dir / "content_bundle" / "pages"
    if not content_dir.is_dir():
        return False
    return any(content_dir.rglob("*.md"))


def _resolve_content_file(run_dir: Path, content_path: str) -> Path | None:
    """Find the markdown file for a content_path in the run's content bundle.

    Note: _index pages have _index as part of content_path (e.g.,
    "products.aspose.org/cells/_index") so the .md suffix appending
    resolves them directly.
    """
    pages_dir = run_dir / "content_bundle" / "pages"
    candidate = pages_dir / (content_path + ".md")
    if candidate.exists():
        return candidate
    return None


def promote_run(
    run_dir: Path,
    deploy_dir: Path,
    *,
    min_grade: Grade = Grade.C,
    dry_run: bool = False,
    snapshots_dir: Path | None = None,
    phase_store_dir: Path | None = None,
) -> PromotionReport:
    """Promote qualifying pages from a run to the deploy directory.

    Args:
        run_dir: Path to the completed run directory.
        deploy_dir: Path to the deploy/ output directory.
        min_grade: Minimum grade to allow promotion (default: C).
        dry_run: If True, report what would change without writing files.
        snapshots_dir: Explicit path for IR snapshot store. When None, falls
            back to deploy_dir.parent / "snapshots" with an INFO log.
        phase_store_dir: Explicit path for phase JSON store. When None, falls
            back to deploy_dir.parent / "phase_store" with an INFO log.

    Returns:
        PromotionReport summarizing actions taken.
    """
    run_id = run_dir.name
    report = PromotionReport(run_id=run_id)

    if not is_run_complete(run_dir):
        logger.warning("Run %s is incomplete — skipping promotion", run_id)
        return report

    # Load evaluation report
    eval_path = _find_eval_report(run_dir)
    if eval_path is None:
        logger.error("No evaluation report found in %s", run_dir)
        return report
    try:
        raw = json.loads(eval_path.read_text(encoding="utf-8"))
        eval_report = EvaluationReport.model_validate(raw)
    except Exception:
        logger.error("Cannot parse %s", eval_path, exc_info=True)
        return report

    report.total_pages_in_run = len(eval_report.pages)

    if not eval_report.pages:
        logger.info("Run %s has no evaluated pages — nothing to promote", run_id)
        return report

    # Load or create manifest
    manifest_path = deploy_dir / "manifest.json"
    manifest = load_manifest(manifest_path) if not dry_run or manifest_path.exists() else DeployManifest()

    now = datetime.now(timezone.utc).isoformat()

    for page_eval in eval_report.pages:
        content_path = page_eval.content_path or page_eval.slug
        if not content_path:
            continue

        grade = page_eval.grade

        # Check minimum grade FIRST — avoids file I/O + SHA256 for rejected pages
        if not grade_ge(grade, min_grade):
            report.skipped_grade_low += 1
            report.details.append(PagePromotionResult(
                content_path=content_path,
                action=PromotionAction.SKIPPED_GRADE_LOW,
                new_grade=grade.value,
                source_run_id=run_id,
            ))
            continue

        # Find source file
        source_file = _resolve_content_file(run_dir, content_path)
        if source_file is None:
            logger.warning("Content file not found for %s in %s", content_path, run_dir)
            report.skipped_missing_file += 1
            report.details.append(PagePromotionResult(
                content_path=content_path,
                action=PromotionAction.SKIPPED_MISSING_FILE,
                new_grade=grade.value,
                source_run_id=run_id,
            ))
            continue

        source_hash = sha256_file(source_file)

        # Check against existing deployment
        existing = manifest.pages.get(content_path)
        if existing is not None:
            # Same content — skip
            if existing.sha256 == source_hash:
                report.skipped_same_hash += 1
                report.details.append(PagePromotionResult(
                    content_path=content_path,
                    action=PromotionAction.SKIPPED_SAME_HASH,
                    old_grade=existing.grade.value,
                    new_grade=grade.value,
                    source_run_id=run_id,
                ))
                continue

            # Grade must be equal or better to promote
            if not grade_ge(grade, existing.grade):
                report.skipped_no_improvement += 1
                report.details.append(PagePromotionResult(
                    content_path=content_path,
                    action=PromotionAction.SKIPPED_NO_IMPROVEMENT,
                    old_grade=existing.grade.value,
                    new_grade=grade.value,
                    source_run_id=run_id,
                ))
                continue

        # Promote this page
        deploy_file = content_path + ".md"
        dest_path = deploy_dir / deploy_file

        if not dry_run:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_text(
                dest_path,
                source_file.read_text(encoding="utf-8"),
                validate_boundary=deploy_dir,
            )

        manifest.pages[content_path] = DeployedPage(
            content_path=content_path,
            deploy_file=deploy_file,
            source_run_id=run_id,
            grade=grade,
            sha256=source_hash,
            promoted_at=now,
        )

        old_grade = existing.grade.value if existing else ""
        report.promoted += 1
        report.details.append(PagePromotionResult(
            content_path=content_path,
            action=PromotionAction.PROMOTED,
            old_grade=old_grade,
            new_grade=grade.value,
            source_run_id=run_id,
        ))

    # Save manifest
    if not dry_run and report.promoted > 0:
        manifest.last_promotion = now
        manifest.promotion_count += 1
        deploy_dir.mkdir(parents=True, exist_ok=True)
        save_manifest(manifest_path, manifest)

    # Auto-promote phase snapshots when pages were promoted
    if not dry_run and report.promoted > 0:
        _auto_promote_phase_snapshots(
            run_dir, deploy_dir, min_grade,
            snapshots_dir=snapshots_dir,
            phase_store_dir=phase_store_dir,
        )

    return report


def _auto_promote_phase_snapshots(
    run_dir: Path,
    deploy_dir: Path,
    min_grade: Grade,
    *,
    snapshots_dir: Path | None = None,
    phase_store_dir: Path | None = None,
) -> None:
    """Hook: promote IR snapshots and phase JSONs after a successful promote_run().

    Uses explicit snapshots_dir / phase_store_dir when provided.
    Falls back to deploy_dir.parent heuristic with a warning (TC-3906-H5).
    Reads family/platform from the run's run_config.json.
    Silently skips if run_config.json is missing or malformed.
    """
    from launcher.deploy.phase_promoter import promote_phase_snapshots

    if snapshots_dir is None:
        snapshots_dir = deploy_dir.parent / "snapshots"
        logger.info(
            "snapshots_dir not specified — defaulting to %s (deploy_dir.parent heuristic)",
            snapshots_dir,
        )
    if phase_store_dir is None:
        phase_store_dir = deploy_dir.parent / "phase_store"
        logger.info(
            "phase_store_dir not specified — defaulting to %s (deploy_dir.parent heuristic)",
            phase_store_dir,
        )

    run_config_path = run_dir / "run_config.json"
    if not run_config_path.exists():
        logger.debug("No run_config.json in %s — skipping phase snapshot promotion", run_dir)
        return

    try:
        rc = json.loads(run_config_path.read_text(encoding="utf-8"))
        family = rc.get("family", "")
        platform = rc.get("platform", "")
    except Exception:
        logger.warning("Cannot read run_config.json in %s", run_dir, exc_info=True)
        return

    if not family or not platform:
        logger.warning("Missing family/platform in run_config.json for %s", run_dir)
        return

    try:
        phase_report = promote_phase_snapshots(
            run_dir=run_dir,
            snapshots_dir=snapshots_dir,
            phase_store_dir=phase_store_dir,
            family=family,
            platform=platform,
            min_grade=min_grade,
        )
        logger.info(
            "Phase snapshots: promoted=%d phase_jsons_updated=%s",
            phase_report.ir_promoted,
            phase_report.phase_jsons_updated,
        )
    except Exception:
        logger.error("Phase snapshot promotion failed for %s", run_dir, exc_info=True)


def backfill_runs(
    runs_root: Path,
    family: str,
    platform: str,
    deploy_dir: Path,
    *,
    min_grade: Grade = Grade.C,
    dry_run: bool = False,
    snapshots_dir: Path | None = None,
    phase_store_dir: Path | None = None,
) -> list[PromotionReport]:
    """Scan all runs for a family/platform and promote best pages.

    Processes runs oldest-first so newer runs with equal grades win.
    """
    if not runs_root.is_dir():
        logger.warning("Runs root %s does not exist", runs_root)
        return []

    # Collect matching, complete runs
    candidates: list[tuple[float, Path]] = []
    for entry in runs_root.iterdir():
        if not entry.is_dir():
            continue
        config_file = entry / "run_config.json"
        if not config_file.exists():
            continue
        try:
            raw = json.loads(config_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if raw.get("family") != family or raw.get("platform") != platform:
            continue
        if not is_run_complete(entry):
            logger.debug("Skipping incomplete run: %s", entry.name)
            continue
        candidates.append((entry.stat().st_mtime, entry))

    # Sort oldest first
    candidates.sort(key=lambda t: t[0])

    reports: list[PromotionReport] = []
    for _mtime, run_dir in candidates:
        report = promote_run(
            run_dir, deploy_dir, min_grade=min_grade, dry_run=dry_run,
            snapshots_dir=snapshots_dir, phase_store_dir=phase_store_dir,
        )
        reports.append(report)
        if report.promoted > 0:
            logger.info("Promoted %d page(s) from %s", report.promoted, run_dir.name)

    return reports
