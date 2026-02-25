"""Quality review agent for generated content.

TC-2533: 12-dimension quality rubric for manual review of pipeline output.
Dimensions cover hallucination, contradiction, slug quality, code fences,
prompt leaks, structure compliance, heading hierarchy, claim coverage,
readability, SEO metadata, code example quality, and link integrity.
"""

from __future__ import annotations

__all__ = [
    "rubric",
    "aggregator",
    "taskcard_generator",
]
