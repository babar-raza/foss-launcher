"""Plan bundle — output of the Planner worker."""
from __future__ import annotations

from typing import Any

from pydantic import Field

from launcher.models.base import LauncherBaseModel


class PlannedPage(LauncherBaseModel):
    """A page planned for generation with its claim/snippet assignments."""

    page_id: str
    page_role: str
    title: str
    skeleton: list[str] = Field(default_factory=list)
    skeleton_variant: str = "default"
    assigned_claims: list[str] = Field(default_factory=list)
    assigned_snippets: list[int] = Field(default_factory=list)
    frontmatter: dict[str, Any] = Field(default_factory=dict)
    content_path: str = ""
    seo_keywords: list[str] = Field(default_factory=list)
    mandatory: bool = True
    target_class: str = ""
    claim_saturation: float = Field(
        default=1.0,
        description="TC-3876: Ratio of assigned claims to skeleton sections. <0.5 = thin page.",
    )
    richness_tier: str = Field(
        default="A",
        description="TC-3876: Richness tier (A/B/C) propagated from planner for tier-aware generation.",
    )
    code_evidence_sparse: bool = Field(
        default=False,
        description="TR-01: True when example_files + extracted_snippets < 3 (TC-3903). "
                    "Orthogonal to richness_tier — triggers EVIDENCE ABSENT prompt instruction "
                    "in section_prompt regardless of page_role.",
    )
    golden_unmatched_sections: list[str] = Field(
        default_factory=list,
        description="TC-3881 Wave 3 (G7): Section headings with no golden counterpart.",
    )


class PlanBundle(LauncherBaseModel):
    """Complete output of the Planner worker."""

    pages: list[PlannedPage] = Field(default_factory=list)
    claim_assignment_index: dict[str, list[str]] = Field(default_factory=dict)
