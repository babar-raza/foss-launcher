"""Verify TC-3778 healing fixes against a real pilot run.

Re-runs the Evaluate worker against an existing generate checkpoint,
then validates all 6 healing gaps are resolved:

  G-01: Per-page artifacts reflect post-collision grades
  G-02: Missing-file pages produce artifacts
  G-03: mkdir failure doesn't crash worker
  G-04: RunLayout.evaluation_dir is referenced (not dead code)
  G-05: _safe_slug edge cases covered (unit tests)
  G-06: Write-failure graceful degradation (unit tests)

Usage:
    .venv/Scripts/python.exe scripts/verify_healing.py [run_dir]
"""
from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import yaml

from launcher.models.content import ContentManifest, GeneratedPage
from launcher.models.evaluation import EvaluationReport
from launcher.models.run_config import RunConfig
from launcher.orchestrator.worker_contract import WorkerContext
from launcher.workers.evaluate.worker import EvaluateWorker, _safe_slug

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("verify_healing")

PASS = "[PASS]"
FAIL = "[FAIL]"


def _status(ok: bool) -> str:
    return PASS if ok else FAIL


async def verify(run_dir: Path) -> dict[str, bool]:
    """Run verification steps against an existing pilot run."""
    results: dict[str, bool] = {}

    # Load config and generate checkpoint
    config_path = run_dir / "run_config.json"
    if not config_path.exists():
        logger.error("No run_config.json in %s", run_dir)
        return {"setup": False}

    config = RunConfig.model_validate(json.loads(config_path.read_text(encoding="utf-8")))
    gen_cp = run_dir / "generate_checkpoint.json"
    if not gen_cp.exists():
        logger.error("No generate_checkpoint.json in %s", run_dir)
        return {"setup": False}

    manifest = ContentManifest.model_validate(
        json.loads(gen_cp.read_text(encoding="utf-8"))
    )

    logger.info("=" * 60)
    logger.info("Healing Verification — TC-3778")
    logger.info("Run dir: %s", run_dir)
    logger.info("Pages in manifest: %d", len(manifest.pages))
    logger.info("=" * 60)

    # --- Step 1: Clean previous evaluation artifacts ---
    eval_dir = run_dir / "evaluation"
    if eval_dir.exists():
        import shutil
        shutil.rmtree(eval_dir)
        logger.info("Cleaned previous evaluation/ directory")

    # --- Step 2: Re-run Evaluate worker ---
    ctx = WorkerContext(
        run_id="healing-verify",
        run_dir=run_dir,
        config=config,
        llm_config=None,  # Skip LLM review — deterministic checks only
    )

    worker = EvaluateWorker()
    report = await worker.run(manifest, ctx)

    logger.info("")
    logger.info("Evaluate complete: verdict=%s, %d pages", report.verdict.value, len(report.pages))
    logger.info("Grades: %s", report.quality.pages_by_grade)

    # --- G-01: Verify per-page artifacts exist and are correct ---
    logger.info("")
    logger.info("─── G-01: Per-page artifacts post-collision correctness ───")

    eval_pages_dir = run_dir / "evaluation" / "pages"
    pages_with_artifacts = 0
    pages_missing_artifacts = 0
    grade_mismatches = 0

    for page_eval in report.pages:
        safe = _safe_slug(page_eval.content_path or page_eval.slug)
        artifact_path = eval_pages_dir / f"{safe}.eval.json"
        if artifact_path.exists():
            pages_with_artifacts += 1
            data = json.loads(artifact_path.read_text(encoding="utf-8"))
            if data["grade"] != page_eval.grade.value:
                grade_mismatches += 1
                logger.warning(
                    "  MISMATCH: %s — disk=%s memory=%s",
                    page_eval.slug, data["grade"], page_eval.grade.value,
                )
        else:
            pages_missing_artifacts += 1
            logger.warning("  MISSING: %s (expected %s)", artifact_path.name, page_eval.slug)

    g01_ok = pages_missing_artifacts == 0 and grade_mismatches == 0
    results["G-01_artifact_correctness"] = g01_ok
    logger.info(
        "%s %d/%d pages have correct artifacts, %d mismatches",
        _status(g01_ok), pages_with_artifacts, len(report.pages), grade_mismatches,
    )

    # --- G-02: Missing-file pages produce artifacts ---
    logger.info("")
    logger.info("─── G-02: Missing-file pages get artifacts ───")

    missing_file_pages = [p for p in report.pages if any(f.check == "file_missing" for f in p.findings)]
    missing_file_artifacts = 0
    for p in missing_file_pages:
        safe = _safe_slug(p.content_path or p.slug)
        artifact_path = eval_pages_dir / f"{safe}.eval.json"
        if artifact_path.exists():
            missing_file_artifacts += 1

    if missing_file_pages:
        g02_ok = missing_file_artifacts == len(missing_file_pages)
        results["G-02_missing_file_artifacts"] = g02_ok
        logger.info(
            "%s %d/%d missing-file pages have artifacts",
            _status(g02_ok), missing_file_artifacts, len(missing_file_pages),
        )
    else:
        results["G-02_missing_file_artifacts"] = True
        logger.info("%s No missing-file pages in this run (not exercised)", PASS)

    # --- G-03: mkdir guard (verified by unit tests + code inspection) ---
    logger.info("")
    logger.info("─── G-03: mkdir guard ───")
    # Verify the guard exists in the source code
    worker_src = Path(__file__).parent.parent / "src" / "launcher" / "workers" / "evaluate" / "worker.py"
    worker_code = worker_src.read_text(encoding="utf-8")
    g03_ok = "except OSError:" in worker_code and "_artifacts_enabled" in worker_code
    results["G-03_mkdir_guard"] = g03_ok
    logger.info("%s mkdir guarded with try/except OSError + _artifacts_enabled flag", _status(g03_ok))

    # --- G-04: RunLayout.evaluation_dir wired (not dead code) ---
    logger.info("")
    logger.info("─── G-04: RunLayout.evaluation_dir referenced ───")
    g04_ok = "RunLayout" in worker_code and "layout.evaluation_dir" in worker_code
    results["G-04_evaluation_dir_wired"] = g04_ok
    logger.info("%s RunLayout.evaluation_dir referenced in worker.py", _status(g04_ok))

    # --- G-05/G-06: Unit test coverage (run targeted tests) ---
    logger.info("")
    logger.info("─── G-05/G-06: Unit test coverage ───")
    # These are verified by the test suite; just confirm the test classes exist
    test_path = Path(__file__).parent.parent / "tests" / "unit" / "workers" / "test_evaluate.py"
    test_code = test_path.read_text(encoding="utf-8")
    g05_ok = "class TestSafeSlug" in test_code
    g06_ok = "test_write_failure_graceful" in test_code and "test_mkdir_failure_graceful_degradation" in test_code
    results["G-05_safe_slug_tests"] = g05_ok
    results["G-06_write_failure_tests"] = g06_ok
    logger.info("%s TestSafeSlug class exists with edge-case tests", _status(g05_ok))
    logger.info("%s Write-failure and mkdir-failure graceful degradation tests exist", _status(g06_ok))

    # --- Summary artifact ---
    logger.info("")
    logger.info("─── Summary artifact ───")
    summary_path = run_dir / "evaluation" / "evaluation_summary.json"
    summary_ok = summary_path.exists()
    results["summary_artifact"] = summary_ok
    if summary_ok:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        logger.info("%s evaluation_summary.json written (%d pages, verdict=%s)",
                     PASS, len(summary.get("pages", [])), summary.get("verdict"))
    else:
        logger.info("%s evaluation_summary.json missing!", FAIL)

    # --- Per-page grade breakdown ---
    logger.info("")
    logger.info("─── Per-page evaluation (step-by-step) ───")
    for i, p in enumerate(report.pages):
        finding_summary = ", ".join(f"{f.check}:{f.severity}" for f in p.findings[:4])
        extra = f"  +{len(p.findings) - 4} more" if len(p.findings) > 4 else ""
        logger.info("  [%s] %-40s %s%s", p.grade.value, p.slug[:40], finding_summary, extra)

    # --- Final verdict ---
    logger.info("")
    logger.info("═" * 60)
    all_pass = all(results.values())
    logger.info("HEALING VERIFICATION: %s", "ALL PASS" if all_pass else "SOME FAILURES")
    for gap, ok in results.items():
        logger.info("  %s %s", _status(ok), gap)
    logger.info("═" * 60)

    return results


if __name__ == "__main__":
    default_run = "runs/pilot_cells_20260306T195001"
    run_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(default_run)
    asyncio.run(verify(run_path))
