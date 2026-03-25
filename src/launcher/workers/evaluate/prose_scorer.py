"""TC-PROSE-01 Phase 4: Composite prose quality scorer.

Computes a 0-100 prose score from deterministic + LLM prose findings.
Used for reporting and the soft GO criteria gate.
"""
from __future__ import annotations

from launcher.models.evaluation import Finding

# Check names that contribute to the prose score.
_PROSE_CHECK_NAMES: frozenset[str] = frozenset({
    "prose_lead",
    "sentence_openings",
    "explanation_gap",
    "paragraph_monotony",
    "heading_echo",
    "low_specificity",
    "prose_quality",
    "contract_compliance",  # TC-PQ-CC
})

# Penalty weights by severity and source.
_DET_MEDIUM_PENALTY = 8
_DET_LOW_PENALTY = 2
_LLM_MEDIUM_PENALTY = 5
_LLM_LOW_PENALTY = 1

# The LLM prose check name (to distinguish from deterministic checks).
_LLM_CHECK = "prose_quality"


def compute_prose_score(findings: list[Finding]) -> float:
    """Compute a composite prose quality score from prose-related findings.

    Scoring:
    - Start at 100
    - Each MEDIUM deterministic prose finding: -8
    - Each LOW deterministic prose finding: -2
    - Each MEDIUM LLM prose_quality finding: -5
    - Each LOW LLM prose_quality finding: -1
    - Floor at 0

    Only findings whose ``check`` is in ``_PROSE_CHECK_NAMES`` are considered.

    Args:
        findings: All findings for a page (prose and non-prose).

    Returns:
        Prose score in [0.0, 100.0].
    """
    score = 100.0

    for f in findings:
        if f.check not in _PROSE_CHECK_NAMES:
            continue

        is_llm = f.check == _LLM_CHECK

        if f.severity == "medium":
            score -= _LLM_MEDIUM_PENALTY if is_llm else _DET_MEDIUM_PENALTY
        elif f.severity == "low":
            score -= _LLM_LOW_PENALTY if is_llm else _DET_LOW_PENALTY

    return max(0.0, score)
