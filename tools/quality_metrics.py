#!/usr/bin/env python3
"""Quality Metrics Tool (WS-D).

Scans a run_dir and computes per-defect-family metrics for quality gates G1-G7.
Reuses the canonical gate implementations from w9_validator/gates/ for detection.

Defect families:
  G1: LLM artifact phrases ("When working with...", "In this article, we will...")
  G2: Intra-page repetition (near-duplicate paragraphs, Jaccard > 0.65)
  G3: Hallucinated APIs (non-canonical import patterns in code fences)
  G4: Structural chaos (duplicate H2, trailing heading punct, See Also not last)
  G5: Product name errors ("Aspire.Cells" instead of "Aspose.Cells")
  G6: Permalink collisions (duplicate frontmatter permalinks)
  G7: Spec leakage (binary/internal terms on user-facing pages)

Output:
  quality_metrics.json  -- machine-readable metrics
  quality_metrics.md    -- human-readable summary table

Usage:
  PYTHONHASHSEED=0 python tools/quality_metrics.py \\
      --run-dir runs/r_baseline_cells \\
      --out-dir reports/quality/baseline/r_baseline_cells

Exit codes:
  0 - Metrics computed successfully
  1 - Fatal error (missing run_dir, I/O failure)
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

# Fix Windows console encoding to avoid UnicodeEncodeError on non-ASCII output.
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger("quality_metrics")

# ---------------------------------------------------------------------------
# Gate module imports
# ---------------------------------------------------------------------------
# Ensure the project root is on sys.path so gate modules resolve.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.launch.workers.w9_validator.gates import (  # noqa: E402
    gate_llm_artifact_phrases,
    gate_intra_page_repetition,
    gate_api_import_allowlist,
    gate_section_structure,
    gate_product_name_integrity,
    gate_permalink_uniqueness,
    gate_spec_leakage,
)

# ---------------------------------------------------------------------------
# Gate registry: ordered list of (key, label, gate_module)
# ---------------------------------------------------------------------------
_GATE_REGISTRY: List[Tuple[str, str, Any]] = [
    ("G1_artifact_phrases", "G1: LLM artifact phrases", gate_llm_artifact_phrases),
    ("G2_intra_page_repetition", "G2: Intra-page repetition", gate_intra_page_repetition),
    ("G3_api_import_violations", "G3: API import violations", gate_api_import_allowlist),
    ("G4_structure_violations", "G4: Structural violations", gate_section_structure),
    ("G5_product_name_errors", "G5: Product name errors", gate_product_name_integrity),
    ("G6_permalink_collisions", "G6: Permalink collisions", gate_permalink_uniqueness),
    ("G7_spec_leakage", "G7: Spec leakage", gate_spec_leakage),
]

# Validation profile used when calling gates (permissive; we want counts, not blocking).
_PROFILE = "local"


# ---------------------------------------------------------------------------
# Core metric computation
# ---------------------------------------------------------------------------

def _collect_md_files(run_dir: Path) -> List[Path]:
    """Return sorted list of markdown files under run_dir/work/site/.

    Sorting ensures deterministic ordering regardless of filesystem traversal.
    """
    site_dir = run_dir / "work" / "site"
    if not site_dir.exists():
        logger.warning("Site directory does not exist: %s", site_dir)
        return []
    return sorted(site_dir.rglob("*.md"))


def _files_from_issues(issues: List[Dict[str, Any]]) -> List[str]:
    """Extract a sorted, deduplicated list of file paths from gate issues."""
    paths: Set[str] = set()
    for issue in issues:
        location = issue.get("location", {})
        path = location.get("path", "")
        if path:
            paths.add(path)
    return sorted(paths)


def compute_metrics(run_dir: Path) -> Dict[str, Any]:
    """Compute per-defect-family quality metrics for a run directory.

    Calls each gate's execute_gate() function and aggregates the results
    into a structured metrics dictionary.

    Args:
        run_dir: Absolute path to the run directory.

    Returns:
        Metrics dictionary matching the quality_metrics.json schema.
    """
    run_dir = run_dir.resolve()
    md_files = _collect_md_files(run_dir)
    total_files = len(md_files)

    logger.info("Scanning %d markdown files in %s", total_files, run_dir)

    metrics: Dict[str, Dict[str, Any]] = {}
    all_files_with_issues: Set[str] = set()

    for key, label, gate_module in _GATE_REGISTRY:
        logger.info("Running gate: %s", label)
        try:
            _passed, issues = gate_module.execute_gate(run_dir, _PROFILE)
        except Exception:
            logger.exception("Gate %s raised an exception", key)
            issues = []

        file_list = _files_from_issues(issues)
        count = len(issues)
        files_affected = len(file_list)

        metrics[key] = {
            "count": count,
            "files_affected": files_affected,
            "file_list": file_list,
        }

        all_files_with_issues.update(file_list)
        logger.info("  %s: %d issues in %d files", key, count, files_affected)

    total_issues = sum(m["count"] for m in metrics.values())
    total_files_with_issues = len(all_files_with_issues)
    files_clean = max(0, total_files - total_files_with_issues)

    result: Dict[str, Any] = {
        "run_dir": str(run_dir),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_files": total_files,
        "metrics": metrics,
        "summary": {
            "total_issues": total_issues,
            "total_files_with_issues": total_files_with_issues,
            "files_clean": files_clean,
        },
    }
    return result


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------

def write_json(metrics: Dict[str, Any], out_dir: Path) -> Path:
    """Write quality_metrics.json to out_dir.

    Args:
        metrics: The computed metrics dictionary.
        out_dir: Output directory (created if absent).

    Returns:
        Path to the written JSON file.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "quality_metrics.json"
    out_path.write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    logger.info("Wrote %s", out_path)
    return out_path


def write_markdown(metrics: Dict[str, Any], out_dir: Path) -> Path:
    """Write quality_metrics.md human-readable summary to out_dir.

    Args:
        metrics: The computed metrics dictionary.
        out_dir: Output directory (created if absent).

    Returns:
        Path to the written Markdown file.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "quality_metrics.md"

    lines: List[str] = []
    lines.append("# Quality Metrics Report")
    lines.append("")
    lines.append(f"**Run directory:** `{metrics['run_dir']}`")
    lines.append(f"**Timestamp:** {metrics['timestamp']}")
    lines.append(f"**Total files scanned:** {metrics['total_files']}")
    lines.append("")

    # Summary
    summary = metrics["summary"]
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- **Total issues:** {summary['total_issues']}")
    lines.append(f"- **Files with issues:** {summary['total_files_with_issues']}")
    lines.append(f"- **Clean files:** {summary['files_clean']}")
    lines.append("")

    # Per-gate table
    lines.append("## Per-Gate Breakdown")
    lines.append("")
    lines.append("| Gate | Issues | Files Affected |")
    lines.append("|------|-------:|---------------:|")

    gate_labels = {
        "G1_artifact_phrases": "G1: LLM artifact phrases",
        "G2_intra_page_repetition": "G2: Intra-page repetition",
        "G3_api_import_violations": "G3: API import violations",
        "G4_structure_violations": "G4: Structural violations",
        "G5_product_name_errors": "G5: Product name errors",
        "G6_permalink_collisions": "G6: Permalink collisions",
        "G7_spec_leakage": "G7: Spec leakage",
    }

    for key in gate_labels:
        gate_data = metrics["metrics"].get(key, {"count": 0, "files_affected": 0})
        label = gate_labels[key]
        lines.append(
            f"| {label} | {gate_data['count']} | {gate_data['files_affected']} |"
        )

    lines.append("")
    lines.append("---")
    lines.append(f"*Generated by `tools/quality_metrics.py`*")
    lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Wrote %s", out_path)
    return out_path


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main(argv: List[str] | None = None) -> int:
    """CLI entry point.

    Args:
        argv: Command-line arguments (defaults to sys.argv[1:]).

    Returns:
        Exit code: 0 on success, 1 on error.
    """
    parser = argparse.ArgumentParser(
        description="Compute per-defect-family quality metrics for a FOSS launcher run.",
    )
    parser.add_argument(
        "--run-dir",
        required=True,
        type=Path,
        help="Path to the run directory (must contain work/site/).",
    )
    parser.add_argument(
        "--out-dir",
        required=True,
        type=Path,
        help="Output directory for quality_metrics.json and quality_metrics.md.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=False,
        help="Enable verbose (DEBUG) logging.",
    )

    args = parser.parse_args(argv)

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )

    run_dir: Path = args.run_dir.resolve()
    out_dir: Path = args.out_dir.resolve()

    if not run_dir.exists():
        logger.error("Run directory does not exist: %s", run_dir)
        return 1

    if not run_dir.is_dir():
        logger.error("Run directory is not a directory: %s", run_dir)
        return 1

    metrics = compute_metrics(run_dir)
    write_json(metrics, out_dir)
    write_markdown(metrics, out_dir)

    summary = metrics["summary"]
    logger.info(
        "Done: %d issues across %d files (%d clean)",
        summary["total_issues"],
        summary["total_files_with_issues"],
        summary["files_clean"],
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
