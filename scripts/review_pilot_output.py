#!/usr/bin/env python3
"""TC-2536: Review pilot output with 12-dimension quality rubric.

Usage:
    python scripts/review_pilot_output.py --run-dir <path> [--output <dir>] [--skip-llm] [--dry-run]

Options:
    --run-dir   Path to the pilot run directory to review.
    --output    Output directory for review artifacts (default: run_dir).
    --skip-llm  Run only deterministic dimensions (no LLM calls).
    --dry-run   Validate configuration only, do not write artifacts.

Exit codes:
    0 -- Review completed (informational; never fails the pipeline).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def get_repo_root() -> Path:
    """Get the repository root (parent of scripts/)."""
    return Path(__file__).resolve().parent.parent


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Review pilot output with 12-dimension quality rubric (TC-2536).",
    )
    parser.add_argument(
        "--run-dir",
        required=True,
        help="Path to the pilot run directory to review.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output directory for artifacts (default: same as run_dir).",
    )
    parser.add_argument(
        "--skip-llm",
        action="store_true",
        help="Skip LLM dimensions; run deterministic checks only.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate configuration only; do not write artifacts.",
    )
    args = parser.parse_args(argv)

    run_dir = Path(args.run_dir).resolve()
    if not run_dir.exists():
        print(f"ERROR: Run directory does not exist: {run_dir}", file=sys.stderr)
        return 1

    output_dir = Path(args.output).resolve() if args.output else run_dir

    # Ensure src/ is on sys.path
    repo_root = get_repo_root()
    src_path = str(repo_root / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

    from launch.review.aggregator import ReviewAggregator, write_review_artifacts

    print(f"Reviewing: {run_dir}")
    print(f"Mode:      {'deterministic only' if args.skip_llm else 'full (deterministic + LLM)'}")
    print()

    aggregator = ReviewAggregator(
        run_dir=run_dir,
        skip_llm=args.skip_llm,
    )

    report = aggregator.run()

    # Print summary to stdout
    print(report["summary"])
    print()
    print(f"Overall Score: {report['overall_score']} / 10 ({report['overall_tier']})")
    print(f"Pages Reviewed: {report['pages_reviewed']}")

    if args.dry_run:
        print("\n[dry-run] Artifacts not written.")
    else:
        write_review_artifacts(report, output_dir)
        print(f"\nArtifacts written to: {output_dir}")
        print(f"  - review_report.json")
        print(f"  - review_summary.md")

    return 0


if __name__ == "__main__":
    sys.exit(main())
