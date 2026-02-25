"""Review dimension checkers package.

TC-2534: Deterministic checkers (RD-02 through RD-08, RD-10, RD-12).
TC-2535: LLM-based checkers (RD-01, RD-09, RD-11) with offline fallback.
"""

from __future__ import annotations

from .deterministic import (
    check_contradiction,
    check_slug_quality,
    check_code_fence_integrity,
    check_prompt_leak,
    check_structure_compliance,
    check_heading_hierarchy,
    check_claim_coverage,
    check_seo_meta,
    check_link_integrity,
)
from .llm_based import (
    check_hallucination,
    check_readability,
    check_code_example_quality,
)

__all__ = [
    "check_contradiction",
    "check_slug_quality",
    "check_code_fence_integrity",
    "check_prompt_leak",
    "check_structure_compliance",
    "check_heading_hierarchy",
    "check_claim_coverage",
    "check_seo_meta",
    "check_link_integrity",
    "check_hallucination",
    "check_readability",
    "check_code_example_quality",
]
