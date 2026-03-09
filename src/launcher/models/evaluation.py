from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

from launcher.models.base import LauncherBaseModel


class Verdict(str, Enum):
    """Final pipeline go/no-go verdict."""

    GO = "GO"
    NO_GO = "NO_GO"
    NEEDS_HUMAN_REVIEW = "NEEDS_HUMAN_REVIEW"


class Grade(str, Enum):
    """Quality grade for a single page."""

    A = "A"
    B = "B"
    C = "C"
    D = "D"
    F = "F"


class Finding(LauncherBaseModel):
    """A single issue discovered during evaluation."""

    check: str
    message: str
    severity: Literal["critical", "high", "medium", "low"] = "medium"
    location: str = ""
    section_id: str | None = None


class PageEvaluation(LauncherBaseModel):
    """Evaluation result for a single page."""

    slug: str
    content_path: str = ""
    grade: Grade
    findings: list[Finding] = Field(default_factory=list)
    check_results: dict[str, bool] = Field(default_factory=dict)
    # TC-3879 Wave 1 (E1): Continuous quality score in [0, 100].
    # 100 - (safety_crit_high×25) - (non_crit_high×10) - (medium×5) - (low×1), clamped [0, 100].
    numeric_score: float = 0.0


class QualitySummary(LauncherBaseModel):
    """Aggregate quality metrics across all pages."""

    pages_by_grade: dict[str, int] = Field(default_factory=dict)
    avg_word_count: float = 0.0
    claim_coverage: float = 0.0


class GateResult(LauncherBaseModel):
    """Result of a single gate check."""

    gate_id: str
    passed: bool
    issues: list[Finding] = Field(default_factory=list)
    severity: str = "medium"
    mode: str = "safety_critical"


class RootCauseDiagnosis(LauncherBaseModel):
    """Diagnosis linking an issue back to its responsible worker."""

    issue: str
    responsible_worker: str
    responsible_phase: str = ""
    root_cause: str = ""
    fix: str = ""
    affected_pages: list[str] = Field(default_factory=list)
    # TC-3880 Wave 2 (H8): Weight for sorting/prioritizing diagnoses.
    # critical=3.0, high=2.0, medium=1.0. Defaults to 1.0 (medium-equivalent).
    severity_weight: float = 1.0


class GoCriteria(LauncherBaseModel):
    """A single go/no-go criterion with threshold and actual value."""

    criterion: str
    threshold: str
    actual: str
    passed: bool


class EvaluationReport(LauncherBaseModel):
    """Complete output of the Evaluate worker."""

    verdict: Verdict
    pages: list[PageEvaluation] = Field(default_factory=list)
    quality: QualitySummary = Field(default_factory=QualitySummary)
    gates: list[GateResult] = Field(default_factory=list)
    root_cause_diagnosis: list[RootCauseDiagnosis] = Field(default_factory=list)
    go_criteria: list[GoCriteria] = Field(default_factory=list)


class HealAction(LauncherBaseModel):
    """The single healing action recommended by the LLM diagnostician."""

    worker: str  # "understand", "planner", or "generate"
    target_pages: list[str]
    strategy: str
    priority_checks: list[str]


class HealDecision(LauncherBaseModel):
    """LLM diagnostician output — schema-validated before use."""

    analysis: str
    root_causes: list[str]
    action: HealAction
    confidence: float  # 0.0-1.0
    stop_recommendation: bool
    stop_reason: str | None = None


class PipelineAdvice(LauncherBaseModel):
    """LLM pipeline advisor output — routing decision after a NO_GO evaluation.

    routing options:
      "publish"       — override NO_GO and publish (only when no critical/high findings)
      "heal_generate" — re-run generate on target_pages
      "stop"          — content unfixable, end pipeline

    NOTE: "heal_upstream" intentionally excluded in v1.
    Add it only after empirical data shows understanding re-runs improve grades.
    """

    routing: Literal["publish", "heal_generate", "stop"]
    analysis: str
    confidence: float = Field(ge=0.0, le=1.0)
    target_pages: list[str] = Field(default_factory=list)
    strategy: str = ""
    priority_checks: list[str] = Field(default_factory=list)
    stop_reason: str | None = None


class ReportMetrics(LauncherBaseModel):
    """Snapshot of grade/finding metrics for comparison across heal steps."""

    critical_count: int
    high_count: int
    # TC-3880 Wave 2 (H8): MEDIUM finding count for Grade C page tracking.
    medium_count: int = 0
    grades: dict[str, int]  # {"A": 2, "B": 8, ...}
    ab_rate: float
    df_rate: float
    # TC-3880 Wave 2 (H8): Grade C rate — enables heal loop to target C-grade pages.
    c_rate: float = 0.0
    total_findings: int
    # TC-3880 Wave 2 (H5): Total page count for computing _min_meaningful_delta.
    total_pages: int = 0


class HealStep(LauncherBaseModel):
    """Record of one heal iteration."""

    step_idx: int
    decision: HealDecision
    before_metrics: ReportMetrics
    after_metrics: ReportMetrics | None = None
    outcome: Literal[
        "improved", "regressed", "unchanged", "rejected",
        "schema_failure", "timeout",
        "budget_exceeded", "diagnose_only",
    ]
    checkpoint_id: str
    execution_seconds: float
    tokens_used: int
    mode: str = "worker"
    executed_mode: str = "worker"   # Actual mode that ran (may differ from mode on fallback)
    fallback_reason: str | None = None


class HealResult(LauncherBaseModel):
    """Complete record of a heal session."""

    run_id: str
    steps: list[HealStep]
    stop_reason: str  # "converged", "max_steps", "stuck", "llm_stop", "budget_exceeded", etc.
    initial_metrics: ReportMetrics
    final_metrics: ReportMetrics
    total_fixes: int
    total_regressions: int
    total_tokens: int
    avg_confidence: float
    engineering_only_findings: list[dict]
