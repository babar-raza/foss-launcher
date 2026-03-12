"""Root-cause diagnosis -- maps findings to responsible workers."""
from __future__ import annotations

from typing import TYPE_CHECKING

from launcher.models.evaluation import Finding, PageEvaluation, RootCauseDiagnosis

if TYPE_CHECKING:
    from launcher.models.evaluation import HealStep

# Map check names to responsible worker + phase
_CHECK_TO_WORKER: dict[str, tuple[str, str]] = {
    "frontmatter": ("understand", "C_plan"),
    "structure": ("generate", ""),
    "code": ("understand", "B_extract"),
    "density": ("generate", ""),
    "spec_leakage": ("understand", "B_extract"),
    "artifacts": ("generate", ""),
    "safety": ("generate", ""),
    "seo": ("understand", "C_plan"),
    "factual_accuracy": ("understand", "B_extract"),
    "canonical_import": ("understand", "B_extract"),
    "completeness": ("generate", ""),
    "heading_quality": ("generate", ""),
    "code_correctness": ("generate", ""),
    "content_density": ("generate", ""),
    "tone_and_style": ("generate", ""),
    "repetition": ("generate", ""),
    "product_names": ("generate", ""),
    "semantic_structure": ("generate", ""),
    "permalink": ("understand", "C_plan"),
    "api_consistency": ("understand", "B_extract"),
    "audience_appropriateness": ("generate", ""),
}


# Pipeline worker order for determining earliest responsible worker
_PIPELINE_ORDER = ["understand", "planner", "generate", "evaluate", "publish"]


def earliest_responsible_worker(
    diagnoses: list["RootCauseDiagnosis"],
) -> str:
    """Return the earliest pipeline worker responsible for any of the given diagnoses.

    'Earliest' means closest to the start of the pipeline (understand → planner → generate...).
    If no diagnoses match known workers, returns 'generate' as the safe default.
    """
    if not diagnoses:
        return "generate"
    found_workers = {d.responsible_worker for d in diagnoses if d.responsible_worker}
    for worker in _PIPELINE_ORDER:
        if worker in found_workers:
            return worker
    return "generate"


def diagnose_root_causes(
    page_evals: list[PageEvaluation],
    min_severity: str = "high",
) -> list[RootCauseDiagnosis]:
    """Group findings by responsible worker and produce diagnoses.

    TC-3880 Wave 2 (H8/H11): Accepts ``min_severity`` to include MEDIUM findings
    so Grade C pages (3+ MEDIUMs) are visible to the heal loop. Previously only
    high/critical findings were processed, leaving all Grade C pages with no
    diagnosis and no worker target.

    Args:
        page_evals: Pages from the evaluation report.
        min_severity: Minimum severity to include. Use ``"medium"`` to include Grade C
            pages. Defaults to ``"high"`` for backwards compatibility.
    """
    _SEVERITY_WEIGHT: dict[str, float] = {
        "critical": 3.0,
        "high": 2.0,
        "medium": 1.0,
        "low": 0.5,
    }
    if min_severity == "medium":
        _INCLUDE_SEVERITIES: frozenset[str] = frozenset({"critical", "high", "medium"})
    else:
        _INCLUDE_SEVERITIES = frozenset({"critical", "high"})

    # Collect findings per check
    issues_by_check: dict[str, list[tuple[str, Finding]]] = {}
    for page in page_evals:
        for finding in page.findings:
            if finding.severity in _INCLUDE_SEVERITIES:
                key = finding.check
                if key not in issues_by_check:
                    issues_by_check[key] = []
                issues_by_check[key].append((page.slug, finding))

    diagnoses: list[RootCauseDiagnosis] = []
    for check, slug_findings in issues_by_check.items():
        worker, phase = _CHECK_TO_WORKER.get(check, ("generate", ""))
        affected = sorted({sf[0] for sf in slug_findings})
        sample_msg = slug_findings[0][1].message
        weight = max(_SEVERITY_WEIGHT.get(sf[1].severity, 1.0) for sf in slug_findings)

        diagnoses.append(RootCauseDiagnosis(
            issue=f"{check}: {sample_msg} ({len(slug_findings)} occurrences)",
            responsible_worker=worker,
            responsible_phase=phase,
            root_cause=f"Check '{check}' found {len(slug_findings)} issues",
            fix=f"Re-run {worker} worker with tighter {check} constraints",
            affected_pages=affected,
            severity_weight=weight,
        ))

    # Sort by severity_weight descending (critical → high → medium)
    diagnoses.sort(key=lambda d: d.severity_weight, reverse=True)
    return diagnoses


# TC-3897: Checks that warrant escalation from generate → understand after repeated failures.
_ESCALATION_CHECKS: frozenset[str] = frozenset({
    "density", "content_density", "completeness", "artifacts",
})
_ESCALATION_THRESHOLD: int = 2  # consecutive unchanged generate steps before escalating


def escalate_diagnosis(
    prior_steps: "list[HealStep]",
    current_diagnoses: list[RootCauseDiagnosis],
) -> list[RootCauseDiagnosis]:
    """TC-3897: Escalate persistent density/completeness/artifacts to understand worker.

    When these checks route to generate but generate steps produce 'unchanged' outcomes
    for ESCALATION_THRESHOLD consecutive attempts, the root cause is likely thin claims
    rather than generation quality. Escalate to understand so more evidence is extracted.

    Args:
        prior_steps: Completed HealStep records from the current session.
        current_diagnoses: Diagnoses produced by diagnose_root_causes().

    Returns:
        Updated diagnoses list. Escalatable checks are re-routed to understand;
        others are returned unchanged.
    """
    # Count consecutive unchanged generate steps at the tail of history.
    generate_steps = [
        s for s in prior_steps
        if s.decision.action.worker == "generate"
    ]
    if len(generate_steps) < _ESCALATION_THRESHOLD:
        return current_diagnoses  # Not enough history to trigger escalation

    # Check that the last N generate steps were all unchanged (not improving)
    recent_generate = generate_steps[-_ESCALATION_THRESHOLD:]
    if not all(s.outcome == "unchanged" for s in recent_generate):
        return current_diagnoses  # At least one improved — no escalation needed

    escalated: list[RootCauseDiagnosis] = []
    did_escalate = False
    for diagnosis in current_diagnoses:
        # Extract check name from issue field (format: "{check}: {message} ({count} occurrences)")
        _check_name = diagnosis.issue.split(":")[0].strip()
        if _check_name in _ESCALATION_CHECKS and diagnosis.responsible_worker == "generate":
            escalated.append(
                RootCauseDiagnosis(
                    issue=diagnosis.issue,
                    responsible_worker="understand",
                    responsible_phase="B_extract",
                    root_cause=(
                        f"TC-3897: '{_check_name}' persisted after "
                        f"{_ESCALATION_THRESHOLD} unchanged generate steps — escalated to understand"
                    ),
                    fix="Re-run understand worker to extract deeper claims and richer evidence",
                    affected_pages=diagnosis.affected_pages,
                    severity_weight=diagnosis.severity_weight,
                )
            )
            did_escalate = True
        else:
            escalated.append(diagnosis)

    if did_escalate:
        import logging as _logging
        _logging.getLogger(__name__).info(
            "[diagnosis] TC-3897: Escalated density/completeness/artifacts to understand "
            "(generate was unchanged for %d consecutive steps)",
            _ESCALATION_THRESHOLD,
        )
    return escalated
