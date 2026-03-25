"""GO/NO-GO criteria evaluation."""
from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Any

from launcher.models.evaluation import EvaluationReport, GoCriteria, Grade, Verdict
from launcher.workers.evaluate.grader import EDITORIAL_CRITICAL_CHECKS

# TC-2500: Conformance gate thresholds
_MEDIAN_CONFORMANCE_THRESHOLD = 0.50
_LOW_CONFORMANCE_CUTOFF = 0.35
_LOW_CONFORMANCE_RATE_MAX = 0.15
_REGRESSION_MAX_DROP_PP = 10.0  # max drop in percentage points


def evaluate_go_criteria(
    report: EvaluationReport,
    *,
    baseline_path: "Path | None" = None,
) -> tuple[Verdict, list[GoCriteria]]:
    """Evaluate GO/NO-GO criteria against the report.

    Returns (verdict, criteria_results).
    """
    results: list[GoCriteria] = []
    all_pass = True

    # Critical findings
    crit_count = _count_critical(report)
    crit_pass = crit_count == 0
    results.append(GoCriteria(
        criterion="CRITICAL findings",
        threshold="0",
        actual=str(crit_count),
        passed=crit_pass,
    ))
    if not crit_pass:
        all_pass = False

    # A+B rate
    ab = _ab_rate(report)
    ab_pass = ab >= 0.50
    results.append(GoCriteria(
        criterion="A+B rate",
        threshold=">= 50%",
        actual=f"{ab:.0%}",
        passed=ab_pass,
    ))
    if not ab_pass:
        all_pass = False

    # D+F rate
    df = _df_rate(report)
    df_pass = df <= 0.30
    results.append(GoCriteria(
        criterion="D+F rate",
        threshold="<= 30%",
        actual=f"{df:.0%}",
        passed=df_pass,
    ))
    if not df_pass:
        all_pass = False

    # TC-4031 Wave 4G: Editorial-critical HIGH rate ≤ 15%
    ec_rate = _editorial_critical_rate(report)
    ec_pass = ec_rate <= 0.15
    results.append(GoCriteria(
        criterion="Editorial-critical HIGH rate",
        threshold="<= 15%",
        actual=f"{ec_rate:.0%}",
        passed=ec_pass,
    ))
    if not ec_pass:
        all_pass = False

    # TC-2500: Conformance gates (only when pages have conformance_score)
    conf_scores = [
        p.conformance_score for p in report.pages
        if p.conformance_score is not None
    ]
    if conf_scores:
        # Gate 1: Median conformance >= threshold
        median = statistics.median(conf_scores)
        median_pass = median >= _MEDIAN_CONFORMANCE_THRESHOLD
        results.append(GoCriteria(
            criterion="Median conformance score",
            threshold=f">= {_MEDIAN_CONFORMANCE_THRESHOLD:.2f}",
            actual=f"{median:.3f}",
            passed=median_pass,
        ))
        if not median_pass:
            all_pass = False

        # Gate 2: Low-conformance page rate <= threshold
        n_low = sum(1 for s in conf_scores if s < _LOW_CONFORMANCE_CUTOFF)
        low_rate = n_low / len(conf_scores) if conf_scores else 0.0
        low_pass = low_rate <= _LOW_CONFORMANCE_RATE_MAX
        results.append(GoCriteria(
            criterion="Low-conformance page rate",
            threshold=f"<= {_LOW_CONFORMANCE_RATE_MAX:.0%}",
            actual=f"{low_rate:.0%}",
            passed=low_pass,
        ))
        if not low_pass:
            all_pass = False

        # Gate 3: Conformance regression gate (vs baseline)
        if baseline_path is not None:
            try:
                baseline = json.loads(Path(baseline_path).read_text(encoding="utf-8"))
                baseline_median = baseline.get("median_conformance")
                if baseline_median is not None:
                    delta_pp = (median - baseline_median) * 100.0
                    reg_pass = delta_pp >= -_REGRESSION_MAX_DROP_PP
                    results.append(GoCriteria(
                        criterion="Conformance regression gate",
                        threshold=f"<= -{_REGRESSION_MAX_DROP_PP:.0f}pp drop",
                        actual=f"{delta_pp:+.1f}pp",
                        passed=reg_pass,
                    ))
                    if not reg_pass:
                        all_pass = False
            except Exception:
                pass  # No baseline available — skip regression gate

    verdict = Verdict.GO if all_pass else Verdict.NO_GO
    return verdict, results


def _count_critical(report: EvaluationReport) -> int:
    return sum(1 for p in report.pages for f in p.findings if f.severity == "critical")


def _ab_rate(report: EvaluationReport) -> float:
    if not report.pages:
        return 0.0
    ab = sum(1 for p in report.pages if p.grade in (Grade.A, Grade.B))
    return ab / len(report.pages)


def _df_rate(report: EvaluationReport) -> float:
    if not report.pages:
        return 0.0
    df = sum(1 for p in report.pages if p.grade in (Grade.D, Grade.F))
    return df / len(report.pages)


def _editorial_critical_rate(report: EvaluationReport) -> float:
    """Fraction of pages with ≥1 editorial-critical HIGH finding (TC-4031 Wave 4G)."""
    if not report.pages:
        return 0.0
    ec_pages = sum(
        1 for p in report.pages
        if any(
            f.severity == "high" and f.check in EDITORIAL_CRITICAL_CHECKS
            for f in p.findings
        )
    )
    return ec_pages / len(report.pages)
