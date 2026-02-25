"""Review rubric: base types, dimension registry, and scoring utilities.

TC-2533 / TC-2534: Defines the 12-dimension quality rubric used by the
manual review agent.  Each dimension has an ID, name, type (deterministic
or LLM), weight, and a checker function.

Weights (sum = 1.00):
    RD-01 Hallucination        0.15  (LLM)
    RD-02 Contradiction        0.10  (deterministic)
    RD-03 Slug quality         0.05  (deterministic)
    RD-04 Code fence integrity 0.10  (deterministic)
    RD-05 Prompt leak          0.15  (deterministic)
    RD-06 Structure compliance 0.10  (deterministic)
    RD-07 Heading hierarchy    0.05  (deterministic)
    RD-08 Claim coverage       0.10  (deterministic)
    RD-09 Readability          0.05  (LLM)
    RD-10 SEO title/meta       0.05  (deterministic)
    RD-11 Code example quality 0.05  (LLM)
    RD-12 Link integrity       0.05  (deterministic)
"""

from __future__ import annotations

import dataclasses
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Score constants
# ---------------------------------------------------------------------------

SCORE_EXCELLENT = 10
SCORE_GOOD = 7
SCORE_ACCEPTABLE = 5
SCORE_POOR = 2
SCORE_FAIL = 0

# Threshold below which a dimension triggers taskcard generation
TASKCARD_THRESHOLD = 6


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class Issue:
    """A single quality issue found by a dimension checker."""

    severity: str  # "info" | "warning" | "error"
    message: str
    location: str = ""
    line: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "severity": self.severity,
            "message": self.message,
        }
        if self.location:
            d["location"] = self.location
        if self.line is not None:
            d["line"] = self.line
        return d


@dataclasses.dataclass
class DimensionResult:
    """Result of a single dimension check on one page."""

    dimension_id: str
    name: str
    score: int  # 0-10, clamped
    issues: List[Issue] = dataclasses.field(default_factory=list)
    evidence: str = ""

    def __post_init__(self) -> None:
        # Clamp score to valid range
        self.score = max(0, min(10, round(self.score)))

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "dimension_id": self.dimension_id,
            "score": self.score,
            "issues": [i.to_dict() for i in self.issues],
        }
        if self.evidence:
            d["evidence"] = self.evidence
        return d


# ---------------------------------------------------------------------------
# Dimension metadata
# ---------------------------------------------------------------------------

@dataclasses.dataclass(frozen=True)
class DimensionMeta:
    """Static metadata for one review dimension."""

    dimension_id: str
    name: str
    dim_type: str  # "deterministic" | "llm"
    weight: float


# Canonical dimension registry -- order matches RD-01 through RD-12.
DIMENSIONS: List[DimensionMeta] = [
    DimensionMeta("RD-01", "Hallucination",        "llm",           0.15),
    DimensionMeta("RD-02", "Contradiction",         "deterministic", 0.10),
    DimensionMeta("RD-03", "Slug quality",          "deterministic", 0.05),
    DimensionMeta("RD-04", "Code fence integrity",  "deterministic", 0.10),
    DimensionMeta("RD-05", "Prompt leak",           "deterministic", 0.15),
    DimensionMeta("RD-06", "Structure compliance",  "deterministic", 0.10),
    DimensionMeta("RD-07", "Heading hierarchy",     "deterministic", 0.05),
    DimensionMeta("RD-08", "Claim coverage",        "deterministic", 0.10),
    DimensionMeta("RD-09", "Readability",           "llm",           0.05),
    DimensionMeta("RD-10", "SEO title/meta",        "deterministic", 0.05),
    DimensionMeta("RD-11", "Code example quality",  "llm",           0.05),
    DimensionMeta("RD-12", "Link integrity",        "deterministic", 0.05),
]

# Quick lookup by dimension_id
DIMENSION_MAP: Dict[str, DimensionMeta] = {d.dimension_id: d for d in DIMENSIONS}

# Verify weights sum to 1.0 (with floating point tolerance)
_weight_sum = sum(d.weight for d in DIMENSIONS)
assert abs(_weight_sum - 1.0) < 1e-9, f"Dimension weights must sum to 1.0, got {_weight_sum}"


# ---------------------------------------------------------------------------
# Quality tier classification
# ---------------------------------------------------------------------------

def classify_tier(score: float) -> str:
    """Classify a numeric score (0-10) into a quality tier.

    Returns:
        One of "Excellent", "Good", "Needs Work", "Poor".
    """
    if score >= 8.0:
        return "Excellent"
    if score >= 6.0:
        return "Good"
    if score >= 4.0:
        return "Needs Work"
    return "Poor"


def compute_weighted_score(
    dimension_scores: Dict[str, int],
    skip_llm: bool = False,
) -> float:
    """Compute a weighted average score from per-dimension scores.

    Args:
        dimension_scores: Mapping of dimension_id -> score (0-10).
        skip_llm: If True, exclude LLM dimensions and renormalize weights.

    Returns:
        Weighted average (0.0-10.0).
    """
    total_weight = 0.0
    weighted_sum = 0.0

    for dim in DIMENSIONS:
        if skip_llm and dim.dim_type == "llm":
            continue
        score = dimension_scores.get(dim.dimension_id)
        if score is None:
            continue
        weighted_sum += dim.weight * score
        total_weight += dim.weight

    if total_weight == 0.0:
        return 0.0
    return weighted_sum / total_weight
