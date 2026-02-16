"""Feedback Store for continuous content quality improvement.

Records W5.5 review outcomes (scores, issues, fixes applied) and provides
pattern-based recommendations for future content generation.

Persistence: NDJSON file at {run_dir}/feedback/reviews.ndjson
Each record is a ReviewOutcome — one per page per review round.

Usage:
    store = FeedbackStore(feedback_dir)
    store.record_review(outcome)
    patterns = store.get_common_issues("docs")
    strategy = store.suggest_strategy("w5", "faq")
"""

from __future__ import annotations

import json
import os
from collections import Counter
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ReviewOutcome:
    """Single page review result from W5.5 ContentReviewer.

    Attributes:
        run_id: Run identifier
        page_slug: Page being reviewed
        section: Content section (docs, blog, kb, etc.)
        page_role: Generator role (faq, tutorial, etc.)
        round_number: Review round (1, 2, ...)
        content_quality: Score 1-5
        technical_accuracy: Score 1-5
        usability: Score 1-5
        routing: PASS, NEEDS_CHANGES, or REJECT
        errors: List of error messages
        warnings: List of warning messages
        fixes_applied: List of auto-fix function names that were applied
        product_family: Product family (e.g., "3d")
        product_name: Product name
    """

    run_id: str = ""
    page_slug: str = ""
    section: str = ""
    page_role: str = ""
    round_number: int = 1
    content_quality: int = 0
    technical_accuracy: int = 0
    usability: int = 0
    routing: str = ""
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    fixes_applied: List[str] = field(default_factory=list)
    product_family: str = ""
    product_name: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ReviewOutcome:
        return cls(
            run_id=data.get("run_id", ""),
            page_slug=data.get("page_slug", ""),
            section=data.get("section", ""),
            page_role=data.get("page_role", ""),
            round_number=data.get("round_number", 1),
            content_quality=data.get("content_quality", 0),
            technical_accuracy=data.get("technical_accuracy", 0),
            usability=data.get("usability", 0),
            routing=data.get("routing", ""),
            errors=data.get("errors", []),
            warnings=data.get("warnings", []),
            fixes_applied=data.get("fixes_applied", []),
            product_family=data.get("product_family", ""),
            product_name=data.get("product_name", ""),
        )

    @property
    def avg_score(self) -> float:
        """Average of the three dimension scores."""
        scores = [self.content_quality, self.technical_accuracy, self.usability]
        valid = [s for s in scores if s > 0]
        return sum(valid) / len(valid) if valid else 0.0

    @property
    def passed(self) -> bool:
        return self.routing == "PASS"


@dataclass
class CommonIssue:
    """A frequently occurring issue pattern.

    Attributes:
        message: Issue message pattern (normalized)
        count: Number of occurrences
        sections: Sections where this issue occurs
        page_roles: Page roles where this issue occurs
        suggested_fix: Suggested fix function name (if known)
    """

    message: str
    count: int = 0
    sections: List[str] = field(default_factory=list)
    page_roles: List[str] = field(default_factory=list)
    suggested_fix: str = ""


class FeedbackStore:
    """Persistent store for W5.5 review feedback.

    Records review outcomes and provides pattern-based recommendations.
    Thread-safe for append operations (NDJSON append-only).
    """

    REVIEWS_FILE = "reviews.ndjson"

    def __init__(self, feedback_dir: Path):
        """Initialize FeedbackStore.

        Args:
            feedback_dir: Directory for feedback files
        """
        self.feedback_dir = Path(feedback_dir)
        self._reviews_path = self.feedback_dir / self.REVIEWS_FILE

    def record_review(self, outcome: ReviewOutcome) -> None:
        """Append a review outcome to the store.

        Args:
            outcome: Review outcome to record
        """
        self.feedback_dir.mkdir(parents=True, exist_ok=True)
        line = json.dumps(outcome.to_dict(), sort_keys=True, ensure_ascii=False) + "\n"
        with open(self._reviews_path, "a", encoding="utf-8") as f:
            f.write(line)

    def load_reviews(
        self,
        *,
        section: Optional[str] = None,
        page_role: Optional[str] = None,
        product_family: Optional[str] = None,
    ) -> List[ReviewOutcome]:
        """Load review outcomes with optional filtering.

        Args:
            section: Filter by section (e.g., "docs")
            page_role: Filter by page role (e.g., "faq")
            product_family: Filter by product family (e.g., "3d")

        Returns:
            List of matching ReviewOutcome objects
        """
        if not self._reviews_path.exists():
            return []

        reviews = []
        with open(self._reviews_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    outcome = ReviewOutcome.from_dict(data)
                    if section and outcome.section != section:
                        continue
                    if page_role and outcome.page_role != page_role:
                        continue
                    if product_family and outcome.product_family != product_family:
                        continue
                    reviews.append(outcome)
                except (json.JSONDecodeError, KeyError):
                    continue  # Skip malformed lines

        return reviews

    def get_common_issues(
        self,
        section: Optional[str] = None,
        min_count: int = 2,
    ) -> List[CommonIssue]:
        """Get frequently occurring issues across reviews.

        Args:
            section: Filter by section
            min_count: Minimum occurrence count to include

        Returns:
            List of CommonIssue sorted by frequency (descending)
        """
        reviews = self.load_reviews(section=section)

        # Count error messages
        error_counter: Counter = Counter()
        error_sections: Dict[str, set] = {}
        error_roles: Dict[str, set] = {}

        for review in reviews:
            for error in review.errors:
                normalized = _normalize_issue_message(error)
                error_counter[normalized] += 1
                error_sections.setdefault(normalized, set()).add(review.section)
                error_roles.setdefault(normalized, set()).add(review.page_role)

            for warning in review.warnings:
                normalized = _normalize_issue_message(warning)
                error_counter[normalized] += 1
                error_sections.setdefault(normalized, set()).add(review.section)
                error_roles.setdefault(normalized, set()).add(review.page_role)

        issues = []
        for msg, count in error_counter.most_common():
            if count < min_count:
                continue
            issues.append(CommonIssue(
                message=msg,
                count=count,
                sections=sorted(error_sections.get(msg, set())),
                page_roles=sorted(error_roles.get(msg, set())),
            ))

        return issues

    def get_pass_rate(
        self,
        section: Optional[str] = None,
        page_role: Optional[str] = None,
    ) -> float:
        """Get the PASS rate for a given section/role combination.

        Args:
            section: Filter by section
            page_role: Filter by page role

        Returns:
            Pass rate as a float between 0.0 and 1.0
        """
        reviews = self.load_reviews(section=section, page_role=page_role)
        if not reviews:
            return 0.0
        passed = sum(1 for r in reviews if r.passed)
        return passed / len(reviews)

    def get_avg_scores(
        self,
        section: Optional[str] = None,
        page_role: Optional[str] = None,
    ) -> Dict[str, float]:
        """Get average dimension scores.

        Args:
            section: Filter by section
            page_role: Filter by page role

        Returns:
            Dict with "content_quality", "technical_accuracy", "usability" averages
        """
        reviews = self.load_reviews(section=section, page_role=page_role)
        if not reviews:
            return {"content_quality": 0.0, "technical_accuracy": 0.0, "usability": 0.0}

        cq = [r.content_quality for r in reviews if r.content_quality > 0]
        ta = [r.technical_accuracy for r in reviews if r.technical_accuracy > 0]
        u = [r.usability for r in reviews if r.usability > 0]

        return {
            "content_quality": sum(cq) / len(cq) if cq else 0.0,
            "technical_accuracy": sum(ta) / len(ta) if ta else 0.0,
            "usability": sum(u) / len(u) if u else 0.0,
        }

    def suggest_strategy(
        self,
        worker: str,
        content_type: str,
    ) -> Dict[str, Any]:
        """Suggest LLM strategy adjustments based on historical outcomes.

        Args:
            worker: Worker name (e.g., "w5")
            content_type: Content type (e.g., "faq", "tutorial")

        Returns:
            Dict with strategy suggestions:
            {
                "temperature_adjustment": float,  # +/- from default
                "quality_focus": str,  # dimension needing most improvement
                "avoid_patterns": List[str],  # common issue patterns to avoid
            }
        """
        reviews = self.load_reviews(page_role=content_type)
        if not reviews:
            return {
                "temperature_adjustment": 0.0,
                "quality_focus": "",
                "avoid_patterns": [],
            }

        # Find weakest dimension
        scores = self.get_avg_scores(page_role=content_type)
        weakest = min(scores, key=scores.get)

        # Get common issues for this content type
        common = self.get_common_issues()
        role_issues = [
            ci for ci in common
            if content_type in ci.page_roles
        ]
        avoid = [ci.message for ci in role_issues[:5]]

        # Suggest temperature adjustment
        pass_rate = self.get_pass_rate(page_role=content_type)
        temp_adj = 0.0
        if pass_rate < 0.5:
            temp_adj = -0.1  # Lower temperature for more consistent output
        elif pass_rate > 0.9:
            temp_adj = 0.05  # Can afford slightly more creative output

        return {
            "temperature_adjustment": temp_adj,
            "quality_focus": weakest if scores[weakest] < 4.0 else "",
            "avoid_patterns": avoid,
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get overall feedback store statistics.

        Returns:
            Dict with total_reviews, pass_rate, avg_scores, etc.
        """
        reviews = self.load_reviews()
        if not reviews:
            return {
                "total_reviews": 0,
                "pass_rate": 0.0,
                "avg_scores": {},
                "sections": [],
                "page_roles": [],
            }

        sections = sorted(set(r.section for r in reviews if r.section))
        page_roles = sorted(set(r.page_role for r in reviews if r.page_role))

        return {
            "total_reviews": len(reviews),
            "pass_rate": sum(1 for r in reviews if r.passed) / len(reviews),
            "avg_scores": self.get_avg_scores(),
            "sections": sections,
            "page_roles": page_roles,
        }


def _normalize_issue_message(msg: str) -> str:
    """Normalize an issue message for pattern matching.

    Strips line numbers, file paths, and UUIDs to group similar issues.
    """
    import re

    # Strip line numbers
    msg = re.sub(r'\bline\s+\d+', 'line N', msg, flags=re.IGNORECASE)
    # Strip file paths
    msg = re.sub(r'[/\\][\w./\\-]+\.(?:md|py|json)', '<file>', msg)
    # Strip UUIDs
    msg = re.sub(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '<uuid>', msg)
    # Strip claim IDs (hex strings 8+ chars)
    msg = re.sub(r'\b[0-9a-f]{8,}\b', '<id>', msg)

    return msg.strip()
