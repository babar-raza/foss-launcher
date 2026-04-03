"""Check: extraction_quality — fire finding when API extraction is thin (TC-5308)."""
from __future__ import annotations

from typing import Any

from launcher.models.evaluation import Finding

_THIN_THRESHOLD = 0.35
_EMPTY_THRESHOLD = 0.10


def check_extraction_quality(
    slug: str,
    content: str,
    location: str,
    *,
    extraction_completeness: Any | None = None,
) -> list[Finding]:
    """Fire a Finding when API extraction is below quality thresholds.

    TC-5308: Surfaces thin extraction so the grader reflects the root cause
    of inaccurate or hollow content.
    """
    if extraction_completeness is None:
        return []

    score = getattr(extraction_completeness, "overall_completeness", None)
    if score is None:
        return []

    api_class_count = getattr(extraction_completeness, "api_class_count", 0)
    api_method_count = getattr(extraction_completeness, "api_method_count", 0)
    missing_signals = getattr(extraction_completeness, "missing_signals", [])

    if score <= _EMPTY_THRESHOLD or (api_class_count == 0 and api_method_count == 0):
        return [Finding(
            check="extraction_quality",
            message=(
                f"API extraction is empty or near-empty "
                f"(overall_completeness={score:.2f}, classes={api_class_count}, "
                f"methods={api_method_count}). Generated content cannot be accurate. "
                f"Missing signals: {missing_signals}"
            ),
            severity="high",
            location=location,
        )]

    if score < _THIN_THRESHOLD:
        return [Finding(
            check="extraction_quality",
            message=(
                f"API extraction is thin "
                f"(overall_completeness={score:.2f}, classes={api_class_count}, "
                f"methods={api_method_count}). Content may lack specificity. "
                f"Missing signals: {missing_signals}"
            ),
            severity="medium",
            location=location,
        )]

    return []
