"""GO/NO-GO criteria evaluation."""
from __future__ import annotations

from launcher.models.evaluation import EvaluationReport, GoCriteria, Grade, Verdict
from launcher.workers.evaluate.grader import EDITORIAL_CRITICAL_CHECKS


def evaluate_go_criteria(report: EvaluationReport) -> tuple[Verdict, list[GoCriteria]]:
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
    # Pages with off-topic content or hollow coverage should never get GO.
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
