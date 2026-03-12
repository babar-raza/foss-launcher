from __future__ import annotations

from pydantic import BaseModel, Field

from launcher.models.base import LauncherBaseModel
from launcher.models.product import ApiSurface
from launcher.models.understanding import ProductEvidence


class GeneratedPage(LauncherBaseModel):
    """A single page produced by the Generate worker."""

    slug: str
    page_role: str
    section: str
    content_path: str = ""
    template_used: str = ""
    variant: str = "standard"
    ir_path: str = ""
    md_path: str = ""
    claim_ids_used: list[str] = Field(default_factory=list)
    word_count: int = 0
    code_block_count: int = 0
    # TC-3880 Wave 2 (F4): Claim text bodies for deterministic coverage check.
    # Populated by generate worker at page completion. Empty if claims unavailable.
    claim_texts: list[str] = Field(default_factory=list)
    assigned_claim_count: int = 0


class CrossLink(LauncherBaseModel):
    """A directed link between two pages."""

    source: str
    target: str
    anchor_text: str = ""
    url: str = ""
    link_type: str = "see_also"


class GenerationStats(LauncherBaseModel):
    """Aggregate statistics for one generation run."""

    total_pages: int = 0
    llm_calls: int = 0
    fallback_count: int = 0
    duration_seconds: float = 0.0


class ContentManifest(LauncherBaseModel):
    """Complete output of the Generate worker."""

    pages: list[GeneratedPage] = Field(default_factory=list)
    cross_links: list[CrossLink] = Field(default_factory=list)
    generation_stats: GenerationStats = Field(default_factory=GenerationStats)
    # TC-HO-09: Embed understand-worker outputs so Evaluate reads from graph state
    # instead of disk side-loads. Both fields have defaults so existing callers
    # that construct ContentManifest without these fields continue to work.
    api_surface: ApiSurface = Field(
        default_factory=lambda: ApiSurface(
            public_classes=[], import_allowlist=[], confidence="low"
        ),
        description=(
            "TC-HO-09: ApiSurface from the Understand worker, embedded for schema-validated "
            "graph-state delivery to the Evaluate worker. Defaults to empty ApiSurface "
            "(confidence=low, no classes) when the Generate worker did not populate it "
            "(backward compatibility)."
        ),
    )
    product_evidence: ProductEvidence = Field(
        default_factory=ProductEvidence,
        description=(
            "TC-HO-09: ProductEvidence from the Understand worker, embedded for schema-validated "
            "graph-state delivery to the Evaluate worker. Defaults to empty ProductEvidence when "
            "the Generate worker did not populate it (backward compatibility)."
        ),
    )
