#!/usr/bin/env python3
"""Quality Benchmark: Measure and grade pilot output quality.

Runs a pilot (or inspects existing output), measures quality across
multiple dimensions, and produces a graded report card.

Usage:
    # Grade an existing run directory
    python scripts/quality_benchmark.py --run-dir runs/r_2026_... --output baselines/3d.json

    # Run a pilot and grade it
    python scripts/quality_benchmark.py --pilot pilot-aspose-3d-foss-python --output baselines/3d.json

    # Compare two baselines
    python scripts/quality_benchmark.py --compare baselines/before.json baselines/after.json

    # Grade all existing run dirs
    python scripts/quality_benchmark.py --run-dir runs/r_xxx --run-dir runs/r_yyy
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def get_repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


# ── Metrics Collection ────────────────────────────────────────────────────


def collect_artifact_metrics(run_dir: Path) -> Dict[str, Any]:
    """Collect metrics from all artifacts in a run directory."""
    artifacts_dir = run_dir / "artifacts"
    metrics: Dict[str, Any] = {"artifacts_found": [], "artifacts_missing": []}

    expected = [
        "product_facts.json", "page_plan.json", "snippet_catalog.json",
        "draft_manifest.json", "validation_report.json",
    ]
    for name in expected:
        path = artifacts_dir / name
        if path.exists():
            metrics["artifacts_found"].append(name)
        else:
            metrics["artifacts_missing"].append(name)

    # Optional artifacts
    for name in ["review_report.json", "product_profile.json", "evidence_map.json"]:
        path = artifacts_dir / name
        if path.exists():
            metrics["artifacts_found"].append(name)

    return metrics


def collect_product_facts_metrics(run_dir: Path) -> Dict[str, Any]:
    """Metrics from product_facts.json."""
    path = run_dir / "artifacts" / "product_facts.json"
    if not path.exists():
        return {"available": False}

    data = json.loads(path.read_text(encoding="utf-8"))
    claims = data.get("claims", [])
    claim_groups = data.get("claim_groups", {})

    # Count claims by kind
    kind_counts: Dict[str, int] = {}
    for c in claims:
        kind = c.get("claim_kind", "unknown")
        kind_counts[kind] = kind_counts.get(kind, 0) + 1

    # Count claims per group
    group_counts = {k: len(v) for k, v in claim_groups.items()}

    # Check enrichment quality
    enriched = sum(1 for c in claims if c.get("enrichment"))
    with_citations = sum(1 for c in claims if c.get("citations"))

    return {
        "available": True,
        "product_name": data.get("product_name", ""),
        "total_claims": len(claims),
        "claims_by_kind": dict(sorted(kind_counts.items())),
        "claims_by_group": dict(sorted(group_counts.items())),
        "enriched_claims": enriched,
        "enrichment_rate": round(enriched / max(len(claims), 1), 2),
        "claims_with_citations": with_citations,
        "workflows_count": len(data.get("workflows", [])),
        "supported_formats": len(data.get("supported_formats", [])),
        "has_positioning": bool(data.get("positioning", {}).get("short_description")),
    }


def collect_page_plan_metrics(run_dir: Path) -> Dict[str, Any]:
    """Metrics from page_plan.json."""
    path = run_dir / "artifacts" / "page_plan.json"
    if not path.exists():
        return {"available": False}

    data = json.loads(path.read_text(encoding="utf-8"))
    pages = data.get("pages", [])

    # Count by section
    section_counts: Dict[str, int] = {}
    role_counts: Dict[str, int] = {}
    for p in pages:
        sec = p.get("section", "unknown")
        section_counts[sec] = section_counts.get(sec, 0) + 1
        role = p.get("page_role", "unknown")
        role_counts[role] = role_counts.get(role, 0) + 1

    # Check claim assignments
    pages_with_claims = sum(1 for p in pages if p.get("required_claim_ids"))
    total_assigned_claims = sum(len(p.get("required_claim_ids", [])) for p in pages)
    pages_with_snippets = sum(1 for p in pages if p.get("required_snippet_tags"))
    pages_with_cross_links = sum(1 for p in pages if p.get("cross_links"))

    return {
        "available": True,
        "launch_tier": data.get("launch_tier", ""),
        "total_pages": len(pages),
        "pages_by_section": dict(sorted(section_counts.items())),
        "pages_by_role": dict(sorted(role_counts.items())),
        "pages_with_claims": pages_with_claims,
        "total_assigned_claims": total_assigned_claims,
        "avg_claims_per_page": round(total_assigned_claims / max(len(pages), 1), 1),
        "pages_with_snippets": pages_with_snippets,
        "pages_with_cross_links": pages_with_cross_links,
    }


def collect_draft_metrics(run_dir: Path) -> Dict[str, Any]:
    """Metrics from draft files."""
    drafts_dir = run_dir / "drafts"
    if not drafts_dir.exists():
        return {"available": False}

    # Also try draft_manifest.json for structured data
    manifest_path = run_dir / "artifacts" / "draft_manifest.json"
    manifest = None
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    # Scan actual draft files
    draft_files: List[Path] = []
    for ext in ("*.md", "*.markdown"):
        draft_files.extend(drafts_dir.rglob(ext))

    total_words = 0
    total_lines = 0
    total_headings = 0
    total_code_blocks = 0
    total_claim_markers_visible = 0
    total_claim_markers_html = 0
    relative_links = 0
    absolute_links = 0
    empty_sections = 0
    pages_below_150_words = 0
    pages_below_300_words = 0
    word_counts: List[int] = []
    issues: List[str] = []

    for draft_path in sorted(draft_files):
        content = draft_path.read_text(encoding="utf-8", errors="replace")
        lines = content.split("\n")

        # Strip frontmatter for body analysis
        body = content
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                body = parts[2]

        body_words = len(body.split())
        total_words += body_words
        total_lines += len(lines)
        word_counts.append(body_words)

        if body_words < 150:
            pages_below_150_words += 1
        if body_words < 300:
            pages_below_300_words += 1

        # Count headings
        headings = [l for l in lines if l.startswith("#")]
        total_headings += len(headings)

        # Count code blocks
        code_fences = len(re.findall(r"^```", content, re.MULTILINE))
        total_code_blocks += code_fences // 2

        # Visible claim markers (bad — should be stripped)
        visible_markers = len(re.findall(r"\[claim:\s*\w+\]", content))
        fullwidth_markers = len(re.findall(r"\u3010\w+\u3011", content))
        # Bare hex IDs in square brackets (not markdown links) — e.g. [085581a6815c]
        bare_hex_markers = len(re.findall(r"(?<!\()\[[a-f0-9]{6,}\](?!\()", content))
        total_claim_markers_visible += visible_markers + fullwidth_markers + bare_hex_markers

        # HTML claim markers (good — these are hidden)
        html_markers = len(re.findall(r"<!--\s*claim:\s*\w+\s*-->", content))
        total_claim_markers_html += html_markers

        # Link analysis
        links = re.findall(r"\[([^\]]*)\]\(([^)]+)\)", content)
        for _text, href in links:
            if href.startswith("http://") or href.startswith("https://"):
                absolute_links += 1
            elif href.startswith("./") or href.startswith("../") or (not href.startswith("#") and not href.startswith("/")):
                relative_links += 1

        # Empty sections (heading followed by another heading with no content)
        for i in range(len(lines) - 1):
            if lines[i].startswith("#") and lines[i + 1].startswith("#"):
                empty_sections += 1

        # Issue detection
        rel_path = str(draft_path.relative_to(run_dir))
        if visible_markers + fullwidth_markers > 0:
            issues.append(f"{rel_path}: {visible_markers + fullwidth_markers} visible claim markers")
        if body_words < 50:
            issues.append(f"{rel_path}: very short ({body_words} words)")

    avg_words = round(sum(word_counts) / max(len(word_counts), 1)) if word_counts else 0
    median_words = sorted(word_counts)[len(word_counts) // 2] if word_counts else 0

    return {
        "available": True,
        "total_drafts": len(draft_files),
        "total_words": total_words,
        "avg_words_per_page": avg_words,
        "median_words_per_page": median_words,
        "min_words": min(word_counts) if word_counts else 0,
        "max_words": max(word_counts) if word_counts else 0,
        "pages_below_150_words": pages_below_150_words,
        "pages_below_300_words": pages_below_300_words,
        "total_headings": total_headings,
        "total_code_blocks": total_code_blocks,
        "visible_claim_markers": total_claim_markers_visible,
        "html_claim_markers": total_claim_markers_html,
        "relative_links": relative_links,
        "absolute_links": absolute_links,
        "empty_sections": empty_sections,
        "issues": issues,
    }


def collect_validation_metrics(run_dir: Path) -> Dict[str, Any]:
    """Metrics from validation_report.json."""
    path = run_dir / "artifacts" / "validation_report.json"
    if not path.exists():
        return {"available": False}

    data = json.loads(path.read_text(encoding="utf-8"))

    issues = data.get("issues", [])
    severity_counts: Dict[str, int] = {}
    for issue in issues:
        sev = issue.get("severity", "unknown")
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    gates = data.get("gates", [])
    gates_passed = sum(1 for g in gates if g.get("ok"))
    gates_failed = sum(1 for g in gates if not g.get("ok"))

    return {
        "available": True,
        "ok": data.get("ok", False),
        "total_issues": len(issues),
        "severity_counts": severity_counts,
        "gates_total": len(gates),
        "gates_passed": gates_passed,
        "gates_failed": gates_failed,
        "failed_gate_names": [g["name"] for g in gates if not g.get("ok")],
    }


def collect_review_metrics(run_dir: Path) -> Dict[str, Any]:
    """Metrics from review_report.json (W5.5 ContentReviewer)."""
    path = run_dir / "artifacts" / "review_report.json"
    if not path.exists():
        return {"available": False}

    data = json.loads(path.read_text(encoding="utf-8"))

    return {
        "available": True,
        "overall_status": data.get("overall_status", ""),
        "dimension_scores": data.get("dimension_scores", {}),
        "pages_reviewed": data.get("pages_reviewed", 0),
        "pages_passed": data.get("pages_passed", 0),
        "pages_failed": data.get("pages_failed", 0),
        "severity_counts": data.get("severity_counts", {}),
    }


def collect_profile_metrics(run_dir: Path) -> Dict[str, Any]:
    """Metrics from product_profile.json (Phase 4)."""
    path = run_dir / "artifacts" / "product_profile.json"
    if not path.exists():
        return {"available": False}

    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        "available": True,
        "product_category": data.get("product_category", ""),
        "content_tone": data.get("content_tone", ""),
        "complexity_level": data.get("complexity_level", ""),
        "primary_audience": data.get("primary_audience", []),
        "key_differentiators": len(data.get("key_differentiators", [])),
        "maturity": data.get("maturity", ""),
    }


def collect_timing_metrics(run_dir: Path) -> Dict[str, Any]:
    """Timing metrics from events.ndjson."""
    path = run_dir / "events.ndjson"
    if not path.exists():
        return {"available": False}

    events = []
    for line in path.read_text(encoding="utf-8", errors="replace").strip().split("\n"):
        line = line.strip()
        if line:
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    if not events:
        return {"available": False, "event_count": 0}

    # Find worker timings
    worker_starts: Dict[str, str] = {}
    worker_durations: Dict[str, float] = {}

    for evt in events:
        etype = evt.get("type", "")
        payload = evt.get("payload", {})
        ts = evt.get("ts", "")

        if etype == "WORK_ITEM_STARTED":
            worker = payload.get("worker", "")
            if worker:
                worker_starts[worker] = ts
        elif etype == "WORK_ITEM_FINISHED":
            worker = payload.get("worker", "")
            if worker and worker in worker_starts:
                try:
                    start = datetime.datetime.fromisoformat(worker_starts[worker].replace("Z", "+00:00"))
                    end = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    worker_durations[worker] = round((end - start).total_seconds(), 1)
                except (ValueError, TypeError):
                    pass

    # Total run time
    total_seconds = None
    if events:
        try:
            first_ts = events[0].get("ts", "")
            last_ts = events[-1].get("ts", "")
            start = datetime.datetime.fromisoformat(first_ts.replace("Z", "+00:00"))
            end = datetime.datetime.fromisoformat(last_ts.replace("Z", "+00:00"))
            total_seconds = round((end - start).total_seconds(), 1)
        except (ValueError, TypeError):
            pass

    return {
        "available": True,
        "event_count": len(events),
        "total_seconds": total_seconds,
        "worker_durations": dict(sorted(worker_durations.items())),
    }


# ── Grading ───────────────────────────────────────────────────────────────


def compute_grades(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Compute letter grades from metrics."""
    grades: Dict[str, Any] = {}

    # 1. Pipeline Health (did it complete?)
    artifacts = metrics.get("artifacts", {})
    found = len(artifacts.get("artifacts_found", []))
    missing = len(artifacts.get("artifacts_missing", []))
    if missing == 0 and found >= 5:
        grades["pipeline_health"] = "A"
    elif missing <= 1:
        grades["pipeline_health"] = "B"
    elif missing <= 2:
        grades["pipeline_health"] = "C"
    else:
        grades["pipeline_health"] = "F"

    # 2. Facts Quality (are claims rich and diverse?)
    facts = metrics.get("product_facts", {})
    if facts.get("available"):
        total = facts.get("total_claims", 0)
        kinds = len(facts.get("claims_by_kind", {}))
        enrichment = facts.get("enrichment_rate", 0)
        has_pos = facts.get("has_positioning", False)

        score = 0
        if total >= 100:
            score += 3
        elif total >= 50:
            score += 2
        elif total >= 20:
            score += 1
        if kinds >= 6:
            score += 2
        elif kinds >= 4:
            score += 1
        if enrichment >= 0.5:
            score += 2
        elif enrichment >= 0.2:
            score += 1
        if has_pos:
            score += 1

        grades["facts_quality"] = _score_to_grade(score, 8)
    else:
        grades["facts_quality"] = "F"

    # 3. Content Volume (enough content per page?)
    drafts = metrics.get("drafts", {})
    if drafts.get("available"):
        avg = drafts.get("avg_words_per_page", 0)
        thin_pages = drafts.get("pages_below_150_words", 0)
        total_drafts = drafts.get("total_drafts", 0)
        thin_rate = thin_pages / max(total_drafts, 1)

        score = 0
        if avg >= 500:
            score += 3
        elif avg >= 300:
            score += 2
        elif avg >= 150:
            score += 1
        if thin_rate <= 0.1:
            score += 3
        elif thin_rate <= 0.3:
            score += 2
        elif thin_rate <= 0.5:
            score += 1
        if drafts.get("total_code_blocks", 0) >= total_drafts:
            score += 1  # At least 1 code block per page
        if drafts.get("total_headings", 0) >= total_drafts * 3:
            score += 1  # At least 3 headings per page

        grades["content_volume"] = _score_to_grade(score, 8)
    else:
        grades["content_volume"] = "F"

    # 4. Content Hygiene (no marker leaks, no empty sections)
    if drafts.get("available"):
        score = 8  # Start at max, deduct
        visible = drafts.get("visible_claim_markers", 0)
        empty = drafts.get("empty_sections", 0)
        relative = drafts.get("relative_links", 0)

        if visible > 0:
            score -= min(visible, 4)  # Each leak costs 1 point
        if empty > 5:
            score -= 2
        elif empty > 0:
            score -= 1
        if relative > 5:
            score -= 2
        elif relative > 0:
            score -= 1

        grades["content_hygiene"] = _score_to_grade(max(score, 0), 8)
    else:
        grades["content_hygiene"] = "F"

    # 5. Validation Gates
    validation = metrics.get("validation", {})
    if validation.get("available"):
        if validation.get("ok"):
            blockers = validation.get("severity_counts", {}).get("blocker", 0)
            errors = validation.get("severity_counts", {}).get("error", 0)
            if blockers == 0 and errors == 0:
                grades["validation"] = "A"
            elif blockers == 0:
                grades["validation"] = "B"
            else:
                grades["validation"] = "C"
        else:
            failed = validation.get("gates_failed", 0)
            if failed <= 2:
                grades["validation"] = "C"
            elif failed <= 4:
                grades["validation"] = "D"
            else:
                grades["validation"] = "F"
    else:
        grades["validation"] = "N/A"

    # 6. Review Quality (W5.5 scores)
    review = metrics.get("review", {})
    if review.get("available"):
        scores = review.get("dimension_scores", {})
        if scores:
            avg_score = sum(scores.values()) / len(scores)
            if avg_score >= 4.5:
                grades["review_quality"] = "A"
            elif avg_score >= 4.0:
                grades["review_quality"] = "B"
            elif avg_score >= 3.0:
                grades["review_quality"] = "C"
            elif avg_score >= 2.0:
                grades["review_quality"] = "D"
            else:
                grades["review_quality"] = "F"
        else:
            grades["review_quality"] = "N/A"
    else:
        grades["review_quality"] = "N/A"

    # Overall grade (weighted average)
    grade_values = {"A": 4, "B": 3, "C": 2, "D": 1, "F": 0}
    scored_grades = {k: grade_values.get(v, 0) for k, v in grades.items() if v != "N/A"}
    if scored_grades:
        avg = sum(scored_grades.values()) / len(scored_grades)
        if avg >= 3.5:
            grades["overall"] = "A"
        elif avg >= 2.5:
            grades["overall"] = "B"
        elif avg >= 1.5:
            grades["overall"] = "C"
        elif avg >= 0.5:
            grades["overall"] = "D"
        else:
            grades["overall"] = "F"
    else:
        grades["overall"] = "N/A"

    return grades


def _score_to_grade(score: int, max_score: int) -> str:
    ratio = score / max(max_score, 1)
    if ratio >= 0.85:
        return "A"
    elif ratio >= 0.7:
        return "B"
    elif ratio >= 0.5:
        return "C"
    elif ratio >= 0.3:
        return "D"
    return "F"


# ── Report Generation ─────────────────────────────────────────────────────


def generate_benchmark(run_dir: Path) -> Dict[str, Any]:
    """Generate a complete benchmark report for a run directory."""
    run_dir = run_dir.resolve()

    if not run_dir.exists():
        return {"error": f"Run directory not found: {run_dir}"}

    report = {
        "benchmark_version": "1.0",
        "timestamp": datetime.datetime.now(datetime.UTC).isoformat() + "Z",
        "run_dir": str(run_dir),
    }

    # Collect all metrics
    report["artifacts"] = collect_artifact_metrics(run_dir)
    report["product_facts"] = collect_product_facts_metrics(run_dir)
    report["page_plan"] = collect_page_plan_metrics(run_dir)
    report["drafts"] = collect_draft_metrics(run_dir)
    report["validation"] = collect_validation_metrics(run_dir)
    report["review"] = collect_review_metrics(run_dir)
    report["profile"] = collect_profile_metrics(run_dir)
    report["timing"] = collect_timing_metrics(run_dir)

    # Compute grades
    report["grades"] = compute_grades(report)

    return report


def print_report_card(report: Dict[str, Any]) -> None:
    """Print a human-readable report card."""
    print("=" * 60)
    print("  QUALITY BENCHMARK REPORT CARD")
    print("=" * 60)

    if "error" in report:
        print(f"\n  ERROR: {report['error']}\n")
        return

    # Product info
    facts = report.get("product_facts", {})
    if facts.get("available"):
        print(f"\n  Product: {facts.get('product_name', 'Unknown')}")
    plan = report.get("page_plan", {})
    if plan.get("available"):
        print(f"  Launch Tier: {plan.get('launch_tier', 'N/A')}")
        print(f"  Total Pages: {plan.get('total_pages', 0)}")

    # Grades
    grades = report.get("grades", {})
    overall = grades.get("overall", "N/A")
    print(f"\n  OVERALL GRADE: {overall}")
    print("-" * 60)

    grade_labels = {
        "pipeline_health": "Pipeline Health",
        "facts_quality": "Facts Quality",
        "content_volume": "Content Volume",
        "content_hygiene": "Content Hygiene",
        "validation": "Validation Gates",
        "review_quality": "Review Quality (W5.5)",
    }
    for key, label in grade_labels.items():
        grade = grades.get(key, "N/A")
        print(f"  {label:<28s} {grade}")

    # Key metrics
    print("\n" + "-" * 60)
    print("  KEY METRICS")
    print("-" * 60)

    if facts.get("available"):
        print(f"  Claims: {facts.get('total_claims', 0)} "
              f"({len(facts.get('claims_by_kind', {}))} kinds)")
        print(f"  Enrichment rate: {facts.get('enrichment_rate', 0):.0%}")
        print(f"  Workflows: {facts.get('workflows_count', 0)}")

    drafts = report.get("drafts", {})
    if drafts.get("available"):
        print(f"  Drafts: {drafts.get('total_drafts', 0)} files")
        print(f"  Words: {drafts.get('total_words', 0):,} total, "
              f"{drafts.get('avg_words_per_page', 0)} avg/page")
        print(f"  Code blocks: {drafts.get('total_code_blocks', 0)}")
        print(f"  Headings: {drafts.get('total_headings', 0)}")

    # Issues
    print("\n" + "-" * 60)
    print("  ISSUES")
    print("-" * 60)

    if drafts.get("available"):
        vm = drafts.get("visible_claim_markers", 0)
        rl = drafts.get("relative_links", 0)
        es = drafts.get("empty_sections", 0)
        thin = drafts.get("pages_below_150_words", 0)

        if vm > 0:
            print(f"  [FAIL] {vm} visible claim marker(s) leaked into content")
        else:
            print(f"  [PASS] No visible claim markers")

        if rl > 0:
            print(f"  [WARN] {rl} relative link(s) found (should be absolute)")
        else:
            print(f"  [PASS] All links are absolute")

        if es > 0:
            print(f"  [WARN] {es} empty section(s) (heading with no content)")
        else:
            print(f"  [PASS] No empty sections")

        if thin > 0:
            print(f"  [WARN] {thin} page(s) below 150 words")
        else:
            print(f"  [PASS] All pages have adequate content")

    validation = report.get("validation", {})
    if validation.get("available"):
        if validation.get("ok"):
            print(f"  [PASS] All {validation.get('gates_total', 0)} validation gates passed")
        else:
            failed = validation.get("failed_gate_names", [])
            print(f"  [FAIL] {len(failed)} gate(s) failed: {', '.join(failed)}")

    review = report.get("review", {})
    if review.get("available"):
        status = review.get("overall_status", "")
        scores = review.get("dimension_scores", {})
        print(f"  [{'PASS' if status == 'PASS' else 'WARN'}] "
              f"W5.5 Review: {status}")
        if scores:
            parts = [f"{k}={v}" for k, v in sorted(scores.items())]
            print(f"    Scores: {', '.join(parts)}")

    # Specific draft issues
    draft_issues = drafts.get("issues", []) if drafts.get("available") else []
    if draft_issues:
        print(f"\n  Draft issues ({len(draft_issues)}):")
        for issue in draft_issues[:10]:
            print(f"    - {issue}")
        if len(draft_issues) > 10:
            print(f"    ... and {len(draft_issues) - 10} more")

    # Timing
    timing = report.get("timing", {})
    if timing.get("available"):
        total = timing.get("total_seconds")
        if total:
            print(f"\n  Total run time: {total:.0f}s ({total/60:.1f}m)")
        durations = timing.get("worker_durations", {})
        if durations:
            print("  Worker durations:")
            for worker, dur in durations.items():
                print(f"    {worker}: {dur:.1f}s")

    print("\n" + "=" * 60)


def print_comparison(before: Dict[str, Any], after: Dict[str, Any]) -> None:
    """Print a side-by-side comparison of two benchmarks."""
    print("=" * 70)
    print("  QUALITY BENCHMARK COMPARISON")
    print("=" * 70)

    # Grade comparison
    bg = before.get("grades", {})
    ag = after.get("grades", {})

    print(f"\n  {'Dimension':<28s} {'Before':<10s} {'After':<10s} {'Delta'}")
    print("-" * 70)

    grade_values = {"A": 4.0, "B": 3.0, "C": 2.0, "D": 1.0, "F": 0.0, "N/A": None}

    for key in ["overall", "pipeline_health", "facts_quality", "content_volume",
                 "content_hygiene", "validation", "review_quality"]:
        b = bg.get(key, "N/A")
        a = ag.get(key, "N/A")
        bv = grade_values.get(b)
        av = grade_values.get(a)
        if bv is not None and av is not None:
            delta = av - bv
            arrow = "+" if delta > 0 else ("-" if delta < 0 else "=")
            print(f"  {key:<28s} {b:<10s} {a:<10s} {arrow}")
        else:
            print(f"  {key:<28s} {b:<10s} {a:<10s}")

    # Key metric deltas
    print("\n" + "-" * 70)
    print(f"  {'Metric':<36s} {'Before':<12s} {'After':<12s} {'Change'}")
    print("-" * 70)

    comparisons = [
        ("Total claims", "product_facts.total_claims"),
        ("Enrichment rate", "product_facts.enrichment_rate"),
        ("Total pages", "page_plan.total_pages"),
        ("Avg words/page", "drafts.avg_words_per_page"),
        ("Pages below 150 words", "drafts.pages_below_150_words"),
        ("Visible claim markers", "drafts.visible_claim_markers"),
        ("Relative links", "drafts.relative_links"),
        ("Empty sections", "drafts.empty_sections"),
        ("Code blocks", "drafts.total_code_blocks"),
        ("Validation issues", "validation.total_issues"),
    ]

    for label, path in comparisons:
        parts = path.split(".")
        bval = before
        aval = after
        for p in parts:
            bval = bval.get(p, {}) if isinstance(bval, dict) else {}
            aval = aval.get(p, {}) if isinstance(aval, dict) else {}

        if isinstance(bval, (int, float)) and isinstance(aval, (int, float)):
            delta = aval - bval
            sign = "+" if delta > 0 else ""
            # Format based on type
            if isinstance(bval, float):
                print(f"  {label:<36s} {bval:<12.2f} {aval:<12.2f} {sign}{delta:.2f}")
            else:
                print(f"  {label:<36s} {str(bval):<12s} {str(aval):<12s} {sign}{delta}")
        else:
            print(f"  {label:<36s} {'N/A':<12s} {'N/A':<12s}")

    print("\n" + "=" * 70)


# ── Main ──────────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Quality Benchmark: Measure and grade pilot output quality"
    )
    parser.add_argument(
        "--run-dir", type=Path, action="append", dest="run_dirs",
        help="Run directory to benchmark (can specify multiple)"
    )
    parser.add_argument(
        "--pilot", type=str,
        help="Run a pilot first, then benchmark the output"
    )
    parser.add_argument(
        "--output", type=Path,
        help="Save benchmark JSON to this path"
    )
    parser.add_argument(
        "--compare", nargs=2, type=Path, metavar=("BEFORE", "AFTER"),
        help="Compare two benchmark JSON files"
    )

    args = parser.parse_args()

    # Handle comparison mode
    if args.compare:
        before = json.loads(args.compare[0].read_text(encoding="utf-8"))
        after = json.loads(args.compare[1].read_text(encoding="utf-8"))
        print_comparison(before, after)
        return 0

    # Handle pilot mode (run pilot, then benchmark)
    if args.pilot:
        repo_root = get_repo_root()
        sys.path.insert(0, str(repo_root / "src"))
        from run_pilot import run_pilot

        print(f"Running pilot: {args.pilot} ...")
        result = run_pilot(args.pilot)
        run_dir_str = result.get("run_dir")
        if not run_dir_str:
            print(f"ERROR: Pilot failed, no run directory")
            return 1

        run_dir = Path(run_dir_str)
        if not run_dir.is_absolute():
            run_dir = repo_root / run_dir

        report = generate_benchmark(run_dir)
        print_report_card(report)

        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False),
                encoding="utf-8",
            )
            print(f"\nBaseline saved to: {args.output}")

        return 0

    # Handle run-dir mode
    if not args.run_dirs:
        parser.print_help()
        return 1

    for run_dir in args.run_dirs:
        report = generate_benchmark(run_dir)
        print_report_card(report)

        if args.output and len(args.run_dirs) == 1:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False),
                encoding="utf-8",
            )
            print(f"\nBaseline saved to: {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
