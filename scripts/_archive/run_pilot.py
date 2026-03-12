"""ARCHIVED — do not use.

This script has been superseded by the CLI ``launch run`` command.

Use instead:
    .venv/Scripts/python.exe -m launcher.cli.main run configs/pilots/foo.yaml
    .venv/Scripts/python.exe -m launcher.cli.main run configs/pilots/foo.yaml --resume-from evaluate
    .venv/Scripts/python.exe -m launcher.cli.main run configs/pilots/foo.yaml --stop-after understand
    .venv/Scripts/python.exe -m launcher.cli.main run configs/pilots/foo.yaml --dry-run

Why archived:
- Duplicated orchestration logic from ``orchestrator/run_loop.py``
- Drifted from production path (missing heal_metadata, telemetry, LangGraph routing,
  schema validation at graph edges)
- ``launch run`` accepts the same <config.yaml> positional argument

See: src/launcher/cli/main.py
"""
# fmt: off
# ruff: noqa
# Original source preserved below for reference only.
# ──────────────────────────────────────────────────────────────────────────────

"""Direct pilot runner for Phase 6 quality validation.

Calls workers sequentially with proper typed models, bypassing the
LangGraph graph builder. This avoids DictProxy/isinstance issues and
gives clear output at each stage.

Usage:
    .venv/Scripts/python.exe scripts/run_pilot.py configs/pilots/aspose-cells-foss-python.yaml
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

import yaml

from launcher.io.run_layout import discover_latest_run
from launcher.models.run_config import RunConfig
from launcher.orchestrator.worker_contract import WorkerContext


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("pilot_runner")


async def run_pilot(config_path: str, resume_from: str = "", run_id: str = "") -> None:
    """Run a pilot end-to-end with proper typed worker calls."""
    # Load config
    raw = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    config = RunConfig(**raw)

    if run_id and not resume_from:
        raise SystemExit("--run-id requires --resume-from (to avoid corrupting an existing run)")

    # Resolve run directory (hybrid resume)
    runs_root = Path("runs")
    if resume_from and not run_id:
        discovered = discover_latest_run(runs_root, config.family, config.platform)
        if discovered is None:
            raise SystemExit(
                f"No previous run found for {config.family}/{config.platform} under {runs_root}"
            )
        run_dir = discovered
        run_id = discovered.name
        logger.info("Auto-discovered previous run for resume: %s", run_id)
    elif run_id:
        run_dir = runs_root / run_id
        if not run_dir.exists():
            raise SystemExit(f"Run directory not found: {run_dir}")
    else:
        from launcher.util.run_id import generate_run_id

        for _attempt in range(3):
            run_id = generate_run_id(config.family, config.platform)
            run_dir = runs_root / run_id
            if not run_dir.exists():
                break
            logger.warning("Run ID collision, retrying: %s", run_id)
        else:
            raise SystemExit(
                f"Failed to generate unique run ID after 3 attempts under {runs_root}"
            )

    run_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 60)
    logger.info("Pilot run: %s/%s", config.family, config.platform)
    logger.info("Run ID: %s", run_id)
    logger.info("Run dir: %s", run_dir)
    logger.info("LLM: %s", config.llm.primary.model if config.llm else "none")
    logger.info("=" * 60)

    ctx = WorkerContext(
        run_id=run_id,
        run_dir=run_dir,
        config=config,
        llm_config=config.llm,
    )

    # Save config
    (run_dir / "run_config.json").write_text(
        json.dumps(config.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )

    # Run manifest (skip on resume to preserve original created_utc)
    if not resume_from:
        (run_dir / "run_manifest.json").write_text(
            json.dumps({
                "run_id": run_id,
                "family": config.family,
                "platform": config.platform,
                "created_utc": datetime.now(timezone.utc).isoformat(),
                "config_path": config_path,
            }, indent=2),
            encoding="utf-8",
        )

    start = time.monotonic()

    # ── W0: Intake ─────────────────────────────────────────────────
    if resume_from not in ("understand", "planner", "generate", "evaluate", "publish"):
        logger.info("─── W0: Intake ───")
        from launcher.workers.intake.worker import IntakeWorker

        w0 = IntakeWorker()
        intake_bundle = await w0.run(config, ctx)  # type: ignore[arg-type]

        sr = await w0.self_review(intake_bundle)
        logger.info("Intake self-review: passed=%s findings=%d", sr.passed, len(sr.findings))

        # Checkpoint
        (run_dir / "intake_checkpoint.json").write_text(
            json.dumps(intake_bundle.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )
        logger.info(
            "Intake: display=%s import=%s tier=%s sha=%s",
            intake_bundle.display_name,
            intake_bundle.canonical_import,
            intake_bundle.launch_tier,
            intake_bundle.repo_sha[:8] if intake_bundle.repo_sha else "(empty)",
        )
    else:
        logger.info("─── Resuming: loading intake checkpoint ───")
        from launcher.models.intake import IntakeBundle
        cp = json.loads((run_dir / "intake_checkpoint.json").read_text(encoding="utf-8"))
        intake_bundle = IntakeBundle.model_validate(cp)

    # ── W1: Understand ──────────────────────────────────────────────
    if resume_from not in ("planner", "generate", "evaluate", "publish"):
        logger.info("─── W1: Understand ───")
        from launcher.workers.understand.worker import UnderstandWorker

        w1 = UnderstandWorker()
        bundle = await w1.run(intake_bundle, ctx)

        # Self-review
        sr = await w1.self_review(bundle)
        logger.info("Understand self-review: passed=%s findings=%d", sr.passed, len(sr.findings))
        if sr.findings:
            for f in sr.findings:
                logger.info("  %s", f)

        # Checkpoint
        checkpoint = bundle.model_dump(mode="json")
        (run_dir / "understand_checkpoint.json").write_text(
            json.dumps(checkpoint, indent=2, default=str),
            encoding="utf-8",
        )

        logger.info(
            "Understand: %d claims, %d snippets, tier=%s",
            len(bundle.claims), len(bundle.snippets),
            bundle.richness_tier.tier.value,
        )
    else:
        logger.info("─── Resuming: loading understand checkpoint ───")
        from launcher.models.understanding import UnderstandingBundle
        cp = json.loads((run_dir / "understand_checkpoint.json").read_text(encoding="utf-8"))
        bundle = UnderstandingBundle.model_validate(cp)

    # ── W1.5: Planner ───────────────────────────────────────────────
    if resume_from not in ("generate", "evaluate", "publish"):
        logger.info("─── W1.5: Planner ───")
        from launcher.workers.planner.worker import PlannerWorker

        wp = PlannerWorker()
        plan_bundle = await wp.run(bundle, ctx)

        sr = await wp.self_review(plan_bundle)
        logger.info("Planner self-review: passed=%s findings=%d", sr.passed, len(sr.findings))

        # Checkpoint
        (run_dir / "planner_checkpoint.json").write_text(
            json.dumps(plan_bundle.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )

        logger.info(
            "Planner: %d pages planned",
            len(plan_bundle.pages),
        )
    else:
        logger.info("─── Resuming: loading planner checkpoint ───")
        from launcher.models.plan import PlanBundle
        cp = json.loads((run_dir / "planner_checkpoint.json").read_text(encoding="utf-8"))
        plan_bundle = PlanBundle.model_validate(cp)

    # ── W2: Generate ────────────────────────────────────────────────
    if resume_from not in ("evaluate", "publish"):
        logger.info("─── W2: Generate ───")
        from launcher.workers.generate.worker import GenerateWorker

        w2 = GenerateWorker()
        manifest = await w2.run(plan_bundle, ctx)

        sr = await w2.self_review(manifest)
        logger.info("Generate self-review: passed=%s", sr.passed)

        # Checkpoint
        (run_dir / "generate_checkpoint.json").write_text(
            json.dumps(manifest.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )

        logger.info(
            "Generate: %d pages, %d LLM calls, %d fallbacks",
            manifest.generation_stats.total_pages,
            manifest.generation_stats.llm_calls,
            manifest.generation_stats.fallback_count,
        )
    else:
        logger.info("─── Resuming: loading generate checkpoint ───")
        from launcher.models.content import ContentManifest
        cp = json.loads((run_dir / "generate_checkpoint.json").read_text(encoding="utf-8"))
        manifest = ContentManifest.model_validate(cp)

    # ── W3: Evaluate ────────────────────────────────────────────────
    if resume_from not in ("publish",):
        logger.info("─── W3: Evaluate ───")
        from launcher.workers.evaluate.worker import EvaluateWorker

        w3 = EvaluateWorker()
        report = await w3.run(manifest, ctx)

        sr = await w3.self_review(report)
        logger.info("Evaluate self-review: passed=%s", sr.passed)

        # Checkpoint
        (run_dir / "evaluate_checkpoint.json").write_text(
            json.dumps(report.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )

        # Print report
        logger.info("")
        logger.info("═══ EVALUATION REPORT ═══")
        logger.info("Verdict: %s", report.verdict.value)
        logger.info("Pages: %d", len(report.pages))
        logger.info("Grades: %s", report.quality.pages_by_grade)
        logger.info("Avg words: %.0f", report.quality.avg_word_count)

        for c in report.go_criteria:
            status = "PASS" if c.passed else "FAIL"
            logger.info("  [%s] %s: %s (threshold: %s)", status, c.criterion, c.actual, c.threshold)

        if report.root_cause_diagnosis:
            logger.info("")
            logger.info("Root causes:")
            for d in report.root_cause_diagnosis:
                logger.info("  - %s -> %s (%d pages)", d.issue[:80], d.responsible_worker, len(d.affected_pages))

        # Per-page summary
        logger.info("")
        logger.info("Per-page grades:")
        for p in report.pages:
            finding_summary = ", ".join(
                f"{f.check}:{f.severity}" for f in p.findings[:3]
            )
            logger.info("  [%s] %s  %s", p.grade.value, p.slug, finding_summary or "(clean)")
    else:
        from launcher.models.evaluation import EvaluationReport
        cp = json.loads((run_dir / "evaluate_checkpoint.json").read_text(encoding="utf-8"))
        report = EvaluationReport.model_validate(cp)

    # ── W4: Publish ──────────────────────────────────────────────
    logger.info("─── W4: Publish ───")
    from launcher.workers.publish.worker import PublishWorker

    w4 = PublishWorker()
    publish_bundle = await w4.run(report, ctx)

    sr = await w4.self_review(publish_bundle)
    logger.info("Publish self-review: passed=%s findings=%d", sr.passed, len(sr.findings))

    # Checkpoint
    (run_dir / "publish_checkpoint.json").write_text(
        json.dumps(publish_bundle.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )

    logger.info(
        "Publish: %d patches, published_at=%s",
        len(publish_bundle.patches),
        publish_bundle.published_at or "(none)",
    )

    # ── Auto-promote to deploy/ (matches run_loop.py behavior) ──
    try:
        from launcher.deploy.promoter import promote_run as _promote_run

        deploy_dir = run_dir.parent / "deploy"
        promo = _promote_run(run_dir, deploy_dir)
        if promo.promoted > 0:
            logger.info("Auto-promoted %d page(s) to %s", promo.promoted, deploy_dir)
        (run_dir / "promotion_report.json").write_text(
            json.dumps(promo.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )
    except Exception:
        logger.warning("Auto-promotion failed (non-fatal)", exc_info=True)

    elapsed = time.monotonic() - start
    logger.info("")
    logger.info("Total time: %.1fs", elapsed)
    logger.info("Run dir: %s", run_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Direct pilot runner")
    parser.add_argument(
        "config",
        nargs="?",
        default="configs/pilots/aspose-cells-foss-python.yaml",
        help="Path to pilot config YAML",
    )
    parser.add_argument("--resume-from", default="", help="Resume from worker (e.g. 'evaluate')")
    parser.add_argument("--run-id", default="", help="Explicit run ID to reuse")
    args = parser.parse_args()
    asyncio.run(run_pilot(args.config, args.resume_from, args.run_id))
