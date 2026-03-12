from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .base import LauncherBaseModel


class EvidenceAnchor(LauncherBaseModel):
    """Points to a concrete location in source that backs a claim."""

    source_file: str
    line_start: int | None = None
    line_end: int | None = None
    snippet: str = ""


class Claim(LauncherBaseModel):
    """A single factual claim extracted from repository evidence."""

    claim_id: str
    text: str
    kind: str
    evidence: list[EvidenceAnchor] = Field(default_factory=list)
    visibility: Literal["public", "internal"] = "public"
    tier_relevance: str = "all"
    confidence: float = 1.0  # Evidence strength: docstring=1.0, llm=0.75, deterministic=0.5, llm_fallback=0.35 [TC-HAL-06]
    claim_source: Literal["llm", "deterministic", "docstring", "llm_fallback"] = "llm"


class Snippet(LauncherBaseModel):
    """A code snippet associated with one or more claims."""

    code: str
    language: str = "python"
    source_type: Literal["extracted", "generated", "synthetic"] = "extracted"
    # "synthetic" has no producer after TC-4062; retained for backward-compat with old bundles
    # TC-4063: Provenance — mirrors EvidenceAnchor on Claim for traceability
    source_file: str = ""
    line_start: int | None = None  # Always None for fenced blocks (TC-4063/SNP-06)
    line_end: int | None = None    # Always None for fenced blocks (TC-4063/SNP-06)
    claim_ids: list[str] = Field(default_factory=list)
