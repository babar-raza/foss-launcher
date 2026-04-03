#!/usr/bin/env python3
"""TC-PROSE-01 Phase 5: Reproducible prose quality benchmark.

Runs all 6 deterministic prose checks on a fixed set of pages and produces
a JSON report with per-page scores and aggregate metrics.

Usage:
    python scripts/prose_benchmark.py <content_dir> [--pages scripts/prose_benchmark_pages.json] [--out prose_benchmark.json]

Arguments:
    content_dir   Directory containing generated .md files (e.g., a run output dir).

Options:
    --pages       Path to benchmark page list JSON (default: scripts/prose_benchmark_pages.json).
    --out         Output path for benchmark JSON (default: prose_benchmark.json).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add src to path so we can import launcher modules.
_SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from launcher.models.evaluation import Finding
from launcher.workers.evaluate.checks.prose_lead import check_prose_lead
from launcher.workers.evaluate.checks.sentence_openings import check_sentence_openings
from launcher.workers.evaluate.checks.explanation_gap import check_explanation_gap
from launcher.workers.evaluate.checks.paragraph_monotony import check_paragraph_monotony
from launcher.workers.evaluate.checks.heading_echo import check_heading_echo
from launcher.workers.evaluate.checks.low_specificity import check_low_specificity
from launcher.workers.evaluate.prose_scorer import compute_prose_score


def _extract_frontmatter(content: str) -> dict[str, str]:
    """Extract YAML frontmatter as a simple key-value dict."""
    m = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not m:
        return {}
    result = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            result[key.strip()] = val.strip().strip('"').strip("'")
    return result


def _infer_product_name(path: Path) -> str:
    """Try to infer product name from directory structure."""
    parts = path.parts
    for i, part in enumerate(parts):
        if part in ("3d", "cells", "words", "pdf", "slides", "email",
                     "cad", "html", "imaging", "barcode", "ocr", "zip",
                     "tasks", "diagram", "note", "page", "psd", "svg",
                     "tex", "font"):
            return f"Aspose.{part.capitalize()}"
    return "Aspose"


def run_checks(content: str, slug: str, page_role: str, product_name: str) -> list[Finding]:
    """Run all 6 deterministic prose checks on a page."""
    findings: list[Finding] = []
    findings.extend(check_prose_lead(content, slug, page_role=page_role, product_name=product_name))
    findings.extend(check_sentence_openings(content, slug, page_role=page_role))
    findings.extend(check_explanation_gap(content, slug, page_role=page_role))
    findings.extend(check_paragraph_monotony(content, slug))
    findings.extend(check_heading_echo(content, slug))
    findings.extend(check_low_specificity(content, slug, page_role=page_role))
    return findings


def benchmark_page(md_path: Path) -> dict:
    """Benchmark a single markdown file."""
    content = md_path.read_text(encoding="utf-8", errors="replace")
    fm = _extract_frontmatter(content)
    slug = fm.get("slug", md_path.stem)
    page_role = fm.get("page_role", fm.get("type", "howto_article"))
    product_name = _infer_product_name(md_path)

    findings = run_checks(content, slug, page_role, product_name)
    prose_score = compute_prose_score(findings)

    return {
        "slug": slug,
        "path": str(md_path),
        "role": page_role,
        "prose_score": round(prose_score, 1),
        "finding_count": len(findings),
        "findings": [
            {"check": f.check, "severity": f.severity, "message": f.message[:120]}
            for f in findings
        ],
    }


def collect_pages(content_dir: Path, pages_file: Path | None) -> list[Path]:
    """Collect markdown files to benchmark.

    If pages_file is given, only benchmark pages listed there.
    Otherwise, benchmark all .md files in content_dir.
    """
    if pages_file and pages_file.is_file():
        page_list = json.loads(pages_file.read_text(encoding="utf-8"))
        paths = []
        for entry in page_list:
            # Each entry can be a relative path or a slug pattern.
            p = content_dir / entry if isinstance(entry, str) else content_dir / entry.get("path", "")
            if p.is_file():
                paths.append(p)
            else:
                # Try glob pattern match.
                matches = list(content_dir.glob(f"**/{p.name}"))
                paths.extend(matches)
        return paths

    # No page list — collect all .md files.
    return sorted(content_dir.rglob("*.md"))


def main():
    parser = argparse.ArgumentParser(description="TC-PROSE-01 prose quality benchmark")
    parser.add_argument("content_dir", type=Path, help="Directory with generated .md files")
    parser.add_argument("--pages", type=Path, default=None, help="Benchmark page list JSON")
    parser.add_argument("--out", type=Path, default=Path("prose_benchmark.json"), help="Output path")
    args = parser.parse_args()

    if not args.content_dir.is_dir():
        print(f"Error: {args.content_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    if args.pages is None:
        default_pages = Path(__file__).parent / "prose_benchmark_pages.json"
        if default_pages.is_file():
            args.pages = default_pages

    md_files = collect_pages(args.content_dir, args.pages)
    if not md_files:
        print(f"No .md files found in {args.content_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"Benchmarking {len(md_files)} pages...")

    page_results = []
    for md_path in md_files:
        result = benchmark_page(md_path)
        page_results.append(result)

    # Aggregate metrics.
    scores = [p["prose_score"] for p in page_results]
    scores_sorted = sorted(scores)
    mid = len(scores_sorted) // 2
    median_score = (
        (scores_sorted[mid - 1] + scores_sorted[mid]) / 2
        if len(scores_sorted) % 2 == 0
        else scores_sorted[mid]
    )

    # Count issues by check.
    check_counts: dict[str, int] = {}
    for p in page_results:
        for f in p["findings"]:
            check_counts[f["check"]] = check_counts.get(f["check"], 0) + 1
    top_issues = sorted(check_counts.items(), key=lambda x: -x[1])

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "page_count": len(page_results),
        "pages": page_results,
        "aggregate": {
            "median_score": round(median_score, 1),
            "mean_score": round(sum(scores) / len(scores), 1),
            "pages_above_80": sum(1 for s in scores if s >= 80),
            "pages_below_40": sum(1 for s in scores if s < 40),
            "top_issues": [{"check": c, "count": n} for c, n in top_issues[:10]],
        },
    }

    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nResults written to {args.out}")
    print(f"  Pages: {len(page_results)}")
    print(f"  Median prose score: {median_score:.0f}")
    print(f"  Mean prose score: {sum(scores) / len(scores):.0f}")
    print(f"  Pages >= 80: {sum(1 for s in scores if s >= 80)}")
    print(f"  Pages < 40: {sum(1 for s in scores if s < 40)}")
    if top_issues:
        print(f"  Top issue: {top_issues[0][0]} ({top_issues[0][1]} occurrences)")


if __name__ == "__main__":
    main()
