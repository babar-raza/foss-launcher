"""Re-evaluate existing content in all runs using current check logic.

This script re-runs the evaluate checks (repetition, safety, etc.) against
existing content files without re-generating them. It updates the
evaluation_report.json so that deploy backfill picks the correct grades.

Usage:
    .venv/Scripts/python.exe scripts/reeval_runs.py [--family cells] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from launcher.models.evaluation import EvaluationReport, Grade, PageEvaluation
from launcher.workers.evaluate.checks.repetition import check_repetition
from launcher.workers.evaluate.checks.safety import check_safety
from launcher.workers.evaluate.checks.structure import check_structure
from launcher.workers.evaluate.checks.density import check_density
from launcher.workers.evaluate.checks.seo import check_seo
from launcher.workers.evaluate.checks.frontmatter import check_frontmatter
from launcher.workers.evaluate.checks.code import check_code
from launcher.workers.evaluate.checks.product_names import check_product_names
from launcher.workers.evaluate.checks.reference_completeness import check_reference_completeness
from launcher.workers.evaluate.checks.semantic_structure import check_semantic_structure
from launcher.workers.evaluate.checks.spec_leakage import check_spec_leakage
from launcher.workers.evaluate.checks.slug_safety import check_slug_safety
from launcher.workers.evaluate.grader import grade_page

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("reeval")

# All non-LLM checks
_CHECKS = [
    check_repetition,
    check_safety,
    check_structure,
    check_density,
    check_seo,
    check_frontmatter,
    check_code,
    check_product_names,
    check_reference_completeness,
    check_semantic_structure,
    check_spec_leakage,
    check_slug_safety,
]


def _find_content_pages(run_dir: Path) -> list[tuple[str, str]]:
    """Find all markdown pages in a run's content_bundle."""
    pages_dir = run_dir / "content_bundle" / "pages"
    if not pages_dir.exists():
        return []
    results = []
    for md in sorted(pages_dir.rglob("*.md")):
        content_path = str(md.relative_to(pages_dir)).replace("\\", "/")
        try:
            content = md.read_text(encoding="utf-8")
            results.append((content_path, content))
        except Exception:
            pass
    return results


def _evaluate_page(content: str, slug: str) -> PageEvaluation:
    """Run all non-LLM checks on a single page and grade it."""
    all_findings = []
    for check_fn in _CHECKS:
        try:
            findings = check_fn(content, slug)
            all_findings.extend(findings)
        except Exception as exc:
            logger.debug("Check %s failed on %s: %s", check_fn.__name__, slug, exc)

    grade = grade_page(all_findings)
    return PageEvaluation(
        slug=slug,
        content_path="",
        grade=grade,
        findings=all_findings,
        check_results={},
    )


def reeval_run(run_dir: Path, dry_run: bool = False) -> dict | None:
    """Re-evaluate a single run. Returns grade summary or None."""
    pages = _find_content_pages(run_dir)
    if not pages:
        return None

    # Check for existing eval report
    eval_path = run_dir / "evaluation_report.json"

    page_evals = []
    for content_path, content in pages:
        slug = Path(content_path).stem
        pe = _evaluate_page(content, slug)
        page_evals.append(pe)

    # Build grade distribution
    grades: dict[str, int] = {}
    for pe in page_evals:
        g = pe.grade.value
        grades[g] = grades.get(g, 0) + 1

    if dry_run:
        logger.info("[DRY] %s: %d pages, grades=%s", run_dir.name, len(pages), grades)
        return grades

    # Build a minimal evaluation report
    report_data = {
        "verdict": "GO" if grades.get("D", 0) + grades.get("F", 0) < len(pages) * 0.5 else "NO_GO",
        "pages": [pe.model_dump(mode="json") for pe in page_evals],
        "quality": {
            "pages_by_grade": grades,
            "avg_word_count": 0,
        },
        "go_criteria": [],
        "root_cause_diagnosis": [],
    }

    eval_path.write_text(json.dumps(report_data, indent=2), encoding="utf-8")
    logger.info("Updated %s: %d pages, grades=%s", run_dir.name, len(pages), grades)
    return grades


def main():
    parser = argparse.ArgumentParser(description="Re-evaluate runs with current checks")
    parser.add_argument("--family", default="", help="Filter by family (e.g., cells)")
    parser.add_argument("--runs-root", default="runs", help="Root directory")
    parser.add_argument("--dry-run", action="store_true", help="Preview without updating")
    args = parser.parse_args()

    runs_root = Path(args.runs_root)
    updated = 0
    skipped = 0

    for run_dir in sorted(runs_root.iterdir()):
        if not run_dir.is_dir() or run_dir.name == "deploy":
            continue

        # Filter by family if specified
        if args.family and args.family not in run_dir.name:
            # Also check run_manifest
            manifest_path = run_dir / "run_manifest.json"
            if manifest_path.exists():
                try:
                    m = json.loads(manifest_path.read_text())
                    if m.get("family") != args.family:
                        continue
                except Exception:
                    continue
            else:
                continue

        result = reeval_run(run_dir, dry_run=args.dry_run)
        if result is not None:
            updated += 1
        else:
            skipped += 1

    logger.info("Done: %d runs updated, %d skipped", updated, skipped)


if __name__ == "__main__":
    main()
