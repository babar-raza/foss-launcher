"""Review report aggregator (TC-2536).

Orchestrates all 12 dimension checkers across every generated page in a
run directory, computes per-page and overall scores via weighted average,
and produces ``review_report.json`` + ``review_summary.md`` artifacts.

Usage:
    from launch.review.aggregator import ReviewAggregator

    agg = ReviewAggregator(run_dir, skip_llm=True)
    report = agg.run()
    # report is a dict conforming to review_report.schema.json
"""

from __future__ import annotations

import datetime
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from .rubric import (
    DIMENSIONS,
    DimensionResult,
    Issue,
    classify_tier,
    compute_weighted_score,
)
from .dimensions.deterministic import (
    check_code_fence_integrity,
    check_claim_coverage,
    check_contradiction,
    check_heading_hierarchy,
    check_link_integrity,
    check_prompt_leak,
    check_seo_meta,
    check_slug_quality,
    check_structure_compliance,
)
from .dimensions.llm_based import (
    check_code_example_quality,
    check_hallucination,
    check_readability,
)

logger = logging.getLogger(__name__)


class ReviewAggregator:
    """Runs all 12 dimension checkers on every page and aggregates results."""

    def __init__(
        self,
        run_dir: str | Path,
        skip_llm: bool = False,
        llm_client: Any = None,
    ) -> None:
        self.run_dir = Path(run_dir)
        self.skip_llm = skip_llm
        self.llm_client = llm_client if not skip_llm else None

    # ------------------------------------------------------------------
    # Discovery & loading
    # ------------------------------------------------------------------

    def _discover_pages(self) -> List[Path]:
        """Find all markdown files under work/pages/ in the run directory."""
        pages_dir = self.run_dir / "work" / "pages"
        if not pages_dir.exists():
            # Fallback: look directly in run_dir for .md files
            md_files = sorted(self.run_dir.glob("**/*.md"))
            return md_files
        return sorted(pages_dir.glob("**/*.md"))

    def _load_artifact(self, name: str) -> Optional[Dict[str, Any]]:
        """Load a JSON artifact from artifacts/ directory."""
        path = self.run_dir / "artifacts" / name
        if not path.exists():
            logger.debug("Artifact not found: %s", path)
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load artifact %s: %s", name, e)
            return None

    def _load_context(self) -> Dict[str, Any]:
        """Load supporting artifacts needed by dimension checkers."""
        return {
            "page_plan": self._load_artifact("page_plan.json"),
            "product_facts": self._load_artifact("product_facts.json"),
            "shared_facts": self._load_artifact("shared_facts.json"),
        }

    # ------------------------------------------------------------------
    # Per-page checking
    # ------------------------------------------------------------------

    def _get_page_role(
        self, page_path: Path, page_plan: Optional[Dict[str, Any]]
    ) -> str:
        """Determine the page_role for a given page from page_plan."""
        if not page_plan:
            return "default"
        pages = page_plan.get("pages", [])
        stem = page_path.stem
        for p in pages:
            if p.get("slug", "") == stem or stem in p.get("output_path", ""):
                return p.get("page_role", "default")
        return "default"

    def _get_assigned_claims(
        self, page_path: Path, page_plan: Optional[Dict[str, Any]]
    ) -> List[str]:
        """Get assigned claim IDs for a page from page_plan."""
        if not page_plan:
            return []
        pages = page_plan.get("pages", [])
        stem = page_path.stem
        for p in pages:
            if p.get("slug", "") == stem or stem in p.get("output_path", ""):
                return p.get("assigned_claims", [])
        return []

    def _get_slug(self, page_path: Path) -> str:
        """Derive slug from page path."""
        return page_path.stem

    def _check_page(
        self,
        page_path: Path,
        content: str,
        context: Dict[str, Any],
        known_pages: Set[str],
    ) -> Dict[str, Any]:
        """Run all applicable dimension checkers on one page.

        Returns a page_result dict conforming to the schema.
        """
        page_plan = context.get("page_plan")
        product_facts = context.get("product_facts")
        shared_facts = context.get("shared_facts")

        page_role = self._get_page_role(page_path, page_plan)
        assigned_claims = self._get_assigned_claims(page_path, page_plan)
        slug = self._get_slug(page_path)
        claims_list = None
        if product_facts:
            claims_list = product_facts.get("claims", [])

        results: List[DimensionResult] = []

        # RD-01: Hallucination (LLM)
        if not self.skip_llm:
            try:
                results.append(check_hallucination(
                    content, product_facts, claims_list, self.llm_client,
                ))
            except Exception as e:
                logger.warning("RD-01 checker failed on %s: %s", page_path.name, e)
                results.append(DimensionResult("RD-01", "Hallucination", 0,
                    [Issue("error", f"Checker error: {e}")]))
        else:
            results.append(DimensionResult("RD-01", "Hallucination", 5,
                [Issue("info", "LLM review not available -- using neutral fallback score")],
                evidence="LLM review not available"))

        # RD-02: Contradiction (computed at run level, not per-page; use placeholder)
        # Contradiction check needs all pages, so we pass score=10 per-page
        # and override at aggregation level.
        results.append(DimensionResult("RD-02", "Contradiction", 10,
            evidence="Cross-page check -- see run-level results."))

        # RD-03: Slug quality
        try:
            results.append(check_slug_quality(slug))
        except Exception as e:
            logger.warning("RD-03 checker failed on %s: %s", page_path.name, e)
            results.append(DimensionResult("RD-03", "Slug quality", 0,
                [Issue("error", f"Checker error: {e}")]))

        # RD-04: Code fence integrity
        try:
            results.append(check_code_fence_integrity(content))
        except Exception as e:
            logger.warning("RD-04 checker failed on %s: %s", page_path.name, e)
            results.append(DimensionResult("RD-04", "Code fence integrity", 0,
                [Issue("error", f"Checker error: {e}")]))

        # RD-05: Prompt leak
        try:
            results.append(check_prompt_leak(content))
        except Exception as e:
            logger.warning("RD-05 checker failed on %s: %s", page_path.name, e)
            results.append(DimensionResult("RD-05", "Prompt leak", 0,
                [Issue("error", f"Checker error: {e}")]))

        # RD-06: Structure compliance
        try:
            results.append(check_structure_compliance(content, page_role))
        except Exception as e:
            logger.warning("RD-06 checker failed on %s: %s", page_path.name, e)
            results.append(DimensionResult("RD-06", "Structure compliance", 0,
                [Issue("error", f"Checker error: {e}")]))

        # RD-07: Heading hierarchy
        try:
            results.append(check_heading_hierarchy(content))
        except Exception as e:
            logger.warning("RD-07 checker failed on %s: %s", page_path.name, e)
            results.append(DimensionResult("RD-07", "Heading hierarchy", 0,
                [Issue("error", f"Checker error: {e}")]))

        # RD-08: Claim coverage
        try:
            results.append(check_claim_coverage(content, assigned_claims))
        except Exception as e:
            logger.warning("RD-08 checker failed on %s: %s", page_path.name, e)
            results.append(DimensionResult("RD-08", "Claim coverage", 0,
                [Issue("error", f"Checker error: {e}")]))

        # RD-09: Readability (LLM)
        if not self.skip_llm:
            try:
                results.append(check_readability(content, self.llm_client))
            except Exception as e:
                logger.warning("RD-09 checker failed on %s: %s", page_path.name, e)
                results.append(DimensionResult("RD-09", "Readability", 0,
                    [Issue("error", f"Checker error: {e}")]))
        else:
            results.append(DimensionResult("RD-09", "Readability", 5,
                [Issue("info", "LLM review not available -- using neutral fallback score")],
                evidence="LLM review not available"))

        # RD-10: SEO title/meta
        try:
            results.append(check_seo_meta(content))
        except Exception as e:
            logger.warning("RD-10 checker failed on %s: %s", page_path.name, e)
            results.append(DimensionResult("RD-10", "SEO title/meta", 0,
                [Issue("error", f"Checker error: {e}")]))

        # RD-11: Code example quality (LLM)
        if not self.skip_llm:
            try:
                results.append(check_code_example_quality(
                    content, product_facts, self.llm_client,
                ))
            except Exception as e:
                logger.warning("RD-11 checker failed on %s: %s", page_path.name, e)
                results.append(DimensionResult("RD-11", "Code example quality", 0,
                    [Issue("error", f"Checker error: {e}")]))
        else:
            results.append(DimensionResult("RD-11", "Code example quality", 5,
                [Issue("info", "LLM review not available -- using neutral fallback score")],
                evidence="LLM review not available"))

        # RD-12: Link integrity
        try:
            results.append(check_link_integrity(content, known_pages))
        except Exception as e:
            logger.warning("RD-12 checker failed on %s: %s", page_path.name, e)
            results.append(DimensionResult("RD-12", "Link integrity", 0,
                [Issue("error", f"Checker error: {e}")]))

        # Compute per-page weighted score
        dim_scores = {r.dimension_id: r.score for r in results}
        page_score = compute_weighted_score(dim_scores, self.skip_llm)
        tier = classify_tier(page_score)

        rel_path = str(page_path.relative_to(self.run_dir)) if self.run_dir in page_path.parents or page_path.parent == self.run_dir else page_path.name

        return {
            "path": rel_path.replace("\\", "/"),
            "page_score": round(page_score, 2),
            "tier": tier,
            "dimension_scores": [r.to_dict() for r in results],
        }

    # ------------------------------------------------------------------
    # Run-level checks
    # ------------------------------------------------------------------

    def _run_contradiction_check(
        self,
        all_pages: List[Dict[str, str]],
        shared_facts: Optional[Dict[str, Any]],
    ) -> DimensionResult:
        """Run RD-02 contradiction check at the run level (cross-page)."""
        try:
            return check_contradiction(all_pages, shared_facts)
        except Exception as e:
            logger.warning("RD-02 run-level check failed: %s", e)
            return DimensionResult("RD-02", "Contradiction", 0,
                [Issue("error", f"Checker error: {e}")])

    # ------------------------------------------------------------------
    # Aggregation
    # ------------------------------------------------------------------

    def run(self) -> Dict[str, Any]:
        """Execute the full review and return a schema-conformant report dict."""
        md_files = self._discover_pages()
        context = self._load_context()

        # Build known pages set for link checking
        known_pages: Set[str] = {p.stem for p in md_files}

        # Load all page contents
        all_page_data: List[Dict[str, str]] = []
        for f in md_files:
            try:
                content = f.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            all_page_data.append({"path": str(f), "content": content})

        # Run per-page checks
        page_results: List[Dict[str, Any]] = []
        for f in md_files:
            try:
                content = f.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            result = self._check_page(f, content, context, known_pages)
            page_results.append(result)

        # Run cross-page contradiction check
        shared_facts = context.get("shared_facts")
        contradiction_result = self._run_contradiction_check(all_page_data, shared_facts)

        # Override RD-02 scores in page results with run-level score
        for pr in page_results:
            for ds in pr["dimension_scores"]:
                if ds["dimension_id"] == "RD-02":
                    ds["score"] = contradiction_result.score
                    ds["issues"] = [i.to_dict() for i in contradiction_result.issues]
                    if contradiction_result.evidence:
                        ds["evidence"] = contradiction_result.evidence

        # Recompute page scores after RD-02 override
        for pr in page_results:
            dim_scores = {ds["dimension_id"]: ds["score"] for ds in pr["dimension_scores"]}
            pr["page_score"] = round(compute_weighted_score(dim_scores, self.skip_llm), 2)
            pr["tier"] = classify_tier(pr["page_score"])

        # Compute dimension summaries
        dimension_summaries = self._compute_dimension_summaries(page_results)

        # Compute overall score
        if page_results:
            overall_score = round(
                sum(pr["page_score"] for pr in page_results) / len(page_results), 2
            )
        else:
            overall_score = 0.0

        overall_tier = classify_tier(overall_score)

        # Generate summary text
        summary = self._generate_summary_text(
            page_results, dimension_summaries, overall_score, overall_tier,
        )

        return {
            "schema_version": "2.0",
            "run_dir": str(self.run_dir).replace("\\", "/"),
            "reviewed_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "overall_score": overall_score,
            "overall_tier": overall_tier,
            "pages_reviewed": len(page_results),
            "dimensions": dimension_summaries,
            "pages": page_results,
            "summary": summary,
            "skip_llm": self.skip_llm,
        }

    def _compute_dimension_summaries(
        self, page_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Compute aggregate dimension statistics across all pages."""
        from .rubric import DIMENSIONS

        summaries = []
        for dim in DIMENSIONS:
            scores: List[int] = []
            for pr in page_results:
                for ds in pr["dimension_scores"]:
                    if ds["dimension_id"] == dim.dimension_id:
                        scores.append(ds["score"])
                        break

            avg = round(sum(scores) / len(scores), 2) if scores else 0.0
            min_score = min(scores) if scores else 0
            below = sum(1 for s in scores if s < 6)

            summaries.append({
                "dimension_id": dim.dimension_id,
                "name": dim.name,
                "type": dim.dim_type,
                "weight": dim.weight,
                "avg_score": avg,
                "min_score": min_score,
                "pages_below_threshold": below,
            })

        return summaries

    def _generate_summary_text(
        self,
        page_results: List[Dict[str, Any]],
        dimension_summaries: List[Dict[str, Any]],
        overall_score: float,
        overall_tier: str,
    ) -> str:
        """Generate human-readable markdown summary."""
        run_name = self.run_dir.name
        lines = [
            f"# Review Summary",
            f"",
            f"**Run**: {run_name}",
            f"**Overall Score**: {overall_score} / 10 ({overall_tier})",
            f"**Pages Reviewed**: {len(page_results)}",
            f"**Mode**: {'Deterministic only (--skip-llm)' if self.skip_llm else 'Full (deterministic + LLM)'}",
            f"",
            f"## Per-Page Scores",
            f"",
            f"| Page | Score | Tier | Top Issues |",
            f"|------|-------|------|-----------|",
        ]

        for pr in page_results:
            page_name = pr["path"].rsplit("/", 1)[-1] if "/" in pr["path"] else pr["path"]
            # Find top issues (dimensions with score < 6)
            top_issues_parts = []
            for ds in pr["dimension_scores"]:
                if ds["score"] < 6:
                    top_issues_parts.append(f"{ds['dimension_id']}: {ds['score']}/10")
            top_issues = "; ".join(top_issues_parts[:3]) if top_issues_parts else "None"
            lines.append(f"| {page_name} | {pr['page_score']} | {pr['tier']} | {top_issues} |")

        lines.extend([
            f"",
            f"## Dimension Summary",
            f"",
            f"| Dimension | Avg Score | Min Score | Pages < 6 |",
            f"|-----------|-----------|-----------|-----------|",
        ])

        for ds in dimension_summaries:
            lines.append(
                f"| {ds['dimension_id']} {ds['name']} | {ds['avg_score']} | "
                f"{ds['min_score']} | {ds['pages_below_threshold']} |"
            )

        # Actionable issues
        actionable = []
        for pr in page_results:
            page_name = pr["path"].rsplit("/", 1)[-1] if "/" in pr["path"] else pr["path"]
            for ds in pr["dimension_scores"]:
                if ds["score"] < 6:
                    for issue in ds["issues"]:
                        actionable.append(
                            f"- {page_name}: {ds['dimension_id']} -- {issue['message']}"
                        )

        if actionable:
            lines.extend([
                f"",
                f"## Actionable Issues (Score < 6)",
                f"",
            ])
            lines.extend(actionable[:20])  # Limit to 20 for readability
            if len(actionable) > 20:
                lines.append(f"- ... and {len(actionable) - 20} more")

        return "\n".join(lines)


def write_review_artifacts(
    report: Dict[str, Any],
    output_dir: str | Path,
) -> None:
    """Write review_report.json and review_summary.md to the output directory.

    Args:
        report: Report dict from ReviewAggregator.run().
        output_dir: Directory to write artifacts to.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    report_path = out / "review_report.json"
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    summary_path = out / "review_summary.md"
    summary_path.write_text(report["summary"] + "\n", encoding="utf-8")

    logger.info("Review artifacts written to %s", out)
