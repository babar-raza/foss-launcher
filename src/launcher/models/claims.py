from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from .base import LauncherBaseModel


class EvidenceAnchor(LauncherBaseModel):
    """Points to a concrete location in source that backs a claim."""

    source_file: str
    line_start: int | None = None
    line_end: int | None = None
    snippet: str = ""

    @model_validator(mode="before")
    @classmethod
    def _coerce_nulls(cls, values: Any) -> Any:  # noqa: ANN401
        """TC-5138: LLM output often contains null for string fields — coerce gracefully."""
        if not isinstance(values, dict):
            return values
        if values.get("source_file") is None:
            values["source_file"] = ""
        if values.get("snippet") is None:
            values["snippet"] = ""
        # Coerce line_start from string to int when possible
        ls = values.get("line_start")
        if isinstance(ls, str):
            try:
                values["line_start"] = int(ls)
            except (ValueError, TypeError):
                values["line_start"] = None
        return values


class Claim(LauncherBaseModel):
    """A single factual claim extracted from repository evidence."""

    claim_id: str
    text: str
    kind: str
    evidence: list[EvidenceAnchor] = Field(default_factory=list)
    visibility: Literal["public", "internal"] = "public"
    tier_relevance: Literal["full", "core", "all"] = "all"
    confidence: float = 1.0  # Evidence strength: docstring=1.0, llm_corroborated=0.85, llm=0.75, deterministic=0.65, deterministic_fallback=0.60, llm_sparse_grounding=0.55, llm_fallback=0.35 [TC-HAL-06, TC-5171, TC-UND-210, TC-UND-211]
    claim_source: Literal["llm", "deterministic", "docstring", "llm_fallback", "llm_sparse_grounding", "llm_corroborated", "deterministic_fallback"] = "llm"


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
    syntax_valid: bool = Field(
        default=True,
        description="TC-FIX-214: Whether the snippet code is syntactically valid.",
    )
    snippet_id: str = ""
