"""Plan bundle — output of the Planner worker."""
from __future__ import annotations

from typing import Any, Literal

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
    maintenance_action: Literal["create", "update", "enhance", "no-change", ""] = Field(
        default="",
        description="TC-5168: Action from maintenance planner (empty string = create mode, no filtering applied).",
    )
    evidence_score: float = Field(
        default=1.0,
        description="TC-FIX-214: Numeric evidence quality score (0-1) from page evidence index.",
    )
    evidence_sufficient: bool = Field(
        default=True,
        description="TC-FIX-214: Whether the page has sufficient evidence for generation.",
    )
    evidence_missing: list[str] = Field(
        default_factory=list,
        description="TC-FIX-214: List of missing evidence signals.",
    )


class GenerationContext(LauncherBaseModel):
    """TC-4318: Context bundle passed from planner to generate worker."""

    claims: list[Any] = Field(default_factory=list)
    snippets: list[Any] = Field(default_factory=list)
    product: dict[str, Any] = Field(default_factory=dict)
    richness_tier: str = "A"
    api_surface: dict[str, Any] = Field(default_factory=dict)
    product_evidence: dict[str, Any] = Field(default_factory=dict)


class PlanBundle(LauncherBaseModel):
    """Complete output of the Planner worker."""

    pages: list[PlannedPage] = Field(default_factory=list)
    claim_assignment_index: dict[str, list[str]] = Field(default_factory=dict)


class PageAction(LauncherBaseModel):
    """TC-5168: Per-page action decision from the maintenance planner."""

    content_path: str
    action: Literal["create", "update", "enhance", "no-change"]
    reason: str = ""


class MaintenancePlan(LauncherBaseModel):
    """TC-5168: Output of the maintenance planner — per-page action decisions."""

    family: str
    platform: str
    planned_at: str
    actions: list[PageAction] = Field(default_factory=list)
