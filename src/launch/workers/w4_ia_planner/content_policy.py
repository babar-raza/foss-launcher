"""Content policy engine for optional page evidence gating.

Only activates when run_config["policy"] key is present.
Mandatory pages are NEVER evaluated by this policy.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

DEFAULT_MIN_SCORE = 0.5
_SCORE_NORMALIZATION_DIVISOR = 30.0

@dataclass
class PolicyDecision:
    candidate_slug: str
    section: str
    raw_score: float
    normalized_score: float
    accepted: bool
    rejection_reason: Optional[str]
    is_dry_run: bool

@dataclass
class ContentPolicy:
    min_score: float
    dry_run_optional: bool
    decisions: List[PolicyDecision] = field(default_factory=list)

    def evaluate(self, candidate: Dict[str, Any], section: str) -> PolicyDecision:
        raw = float(candidate.get("quality_score", 0))
        normalized = min(raw / _SCORE_NORMALIZATION_DIVISOR, 1.0)
        accepted = normalized >= self.min_score
        rejection_reason = (
            f"normalized_score={normalized:.3f} < threshold={self.min_score}"
            if not accepted else None
        )
        decision = PolicyDecision(
            candidate_slug=candidate.get("slug", "?"),
            section=section,
            raw_score=raw,
            normalized_score=normalized,
            accepted=accepted,
            rejection_reason=rejection_reason,
            is_dry_run=self.dry_run_optional,
        )
        self.decisions.append(decision)
        return decision

    def to_artifact(self) -> Dict[str, Any]:
        accepted_list = [d for d in self.decisions if d.accepted]
        rejected_list = [d for d in self.decisions if not d.accepted]
        return {
            "schema_version": "1.0",
            "policy": {
                "optional_content_min_score": self.min_score,
                "dry_run_optional": self.dry_run_optional,
            },
            "summary": {
                "total_candidates": len(self.decisions),
                "accepted": len(accepted_list),
                "rejected": len(rejected_list),
            },
            "decisions": sorted([
                {
                    "slug": d.candidate_slug,
                    "section": d.section,
                    "normalized_score": round(d.normalized_score, 4),
                    "accepted": d.accepted,
                    "rejection_reason": d.rejection_reason,
                    "is_dry_run": d.is_dry_run,
                }
                for d in self.decisions
            ], key=lambda x: (x["section"], x["slug"])),
        }

def load_policy_config(run_config: Dict[str, Any]) -> Optional[ContentPolicy]:
    """Returns None if no policy key present — zero behavior change."""
    if "policy" not in run_config:
        return None
    policy_cfg = run_config["policy"]
    if policy_cfg is None:
        return None
    return ContentPolicy(
        min_score=float(policy_cfg.get("optional_content_min_score", DEFAULT_MIN_SCORE)),
        dry_run_optional=bool(policy_cfg.get("dry_run_optional", False)),
    )
