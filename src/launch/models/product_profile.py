"""Product Profile model for holistic product understanding.

A ProductProfile provides a comprehensive view of a product for content generation.
Instead of generating content purely from individual claims, W5 generators receive
the profile to produce audience-aware, well-positioned content.

Built by W2b from extracted claims + README analysis + code understanding.
Consumed by W4 (page planning) and W5 (content generation).

Spec references:
- specs/03_product_facts_and_evidence.md (Product metadata)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .base import BaseModel


class ProductProfile(BaseModel):
    """Holistic product understanding for content generation.

    Captures what the product is, who it's for, how it positions itself,
    and what content tone/depth is appropriate.
    """

    def __init__(
        self,
        product_name: str,
        product_family: str = "",
        product_slug: str = "",
        product_category: str = "",
        short_description: str = "",
        primary_audience: Optional[List[str]] = None,
        key_differentiators: Optional[List[str]] = None,
        competitive_context: str = "",
        content_tone: str = "technical",
        complexity_level: str = "intermediate",
        supported_platforms: Optional[List[str]] = None,
        repo_url: str = "",
        license_type: str = "",
        maturity: str = "stable",
        claim_summary: Optional[Dict[str, int]] = None,
    ):
        """Initialize ProductProfile.

        Args:
            product_name: Full product name (e.g., "Aspose.3D for Python")
            product_family: Product family (e.g., "3d", "cells")
            product_slug: URL-safe slug (e.g., "aspose-3d-python")
            product_category: Category (e.g., "3D modeling library", "document processing SDK")
            short_description: One-line product description
            primary_audience: Target audience list (e.g., ["Python developers"])
            key_differentiators: What makes this product unique
            competitive_context: Market positioning summary
            content_tone: Content tone ("technical", "tutorial-friendly", "marketing")
            complexity_level: Target complexity ("beginner", "intermediate", "advanced")
            supported_platforms: Platform list (e.g., ["python", "java"])
            repo_url: Repository URL
            license_type: License identifier (e.g., "MIT", "Apache-2.0")
            maturity: Product maturity ("alpha", "beta", "stable", "mature")
            claim_summary: Claim count by kind (e.g., {"feature": 25, "workflow": 8})
        """
        self.product_name = product_name
        self.product_family = product_family
        self.product_slug = product_slug
        self.product_category = product_category
        self.short_description = short_description
        self.primary_audience = primary_audience or []
        self.key_differentiators = key_differentiators or []
        self.competitive_context = competitive_context
        self.content_tone = content_tone
        self.complexity_level = complexity_level
        self.supported_platforms = supported_platforms or []
        self.repo_url = repo_url
        self.license_type = license_type
        self.maturity = maturity
        self.claim_summary = claim_summary or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "product_name": self.product_name,
            "product_family": self.product_family,
            "product_slug": self.product_slug,
            "product_category": self.product_category,
            "short_description": self.short_description,
            "primary_audience": sorted(self.primary_audience),
            "key_differentiators": self.key_differentiators,
            "competitive_context": self.competitive_context,
            "content_tone": self.content_tone,
            "complexity_level": self.complexity_level,
            "supported_platforms": sorted(self.supported_platforms),
            "repo_url": self.repo_url,
            "license_type": self.license_type,
            "maturity": self.maturity,
            "claim_summary": dict(sorted(self.claim_summary.items())),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ProductProfile:
        return cls(
            product_name=data.get("product_name", ""),
            product_family=data.get("product_family", ""),
            product_slug=data.get("product_slug", ""),
            product_category=data.get("product_category", ""),
            short_description=data.get("short_description", ""),
            primary_audience=data.get("primary_audience", []),
            key_differentiators=data.get("key_differentiators", []),
            competitive_context=data.get("competitive_context", ""),
            content_tone=data.get("content_tone", "technical"),
            complexity_level=data.get("complexity_level", "intermediate"),
            supported_platforms=data.get("supported_platforms", []),
            repo_url=data.get("repo_url", ""),
            license_type=data.get("license_type", ""),
            maturity=data.get("maturity", "stable"),
            claim_summary=data.get("claim_summary", {}),
        )

    @classmethod
    def from_product_facts(
        cls,
        product_facts: Dict[str, Any],
        run_config: Optional[Dict[str, Any]] = None,
        code_analysis: Optional[Dict[str, Any]] = None,
    ) -> ProductProfile:
        """Build a ProductProfile from existing pipeline artifacts.

        Args:
            product_facts: product_facts.json content
            run_config: Run configuration (optional)
            code_analysis: code_analysis.json content (optional)

        Returns:
            ProductProfile instance
        """
        run_config = run_config or {}
        code_analysis = code_analysis or {}

        product_name = product_facts.get("product_name", "")
        product_family = product_facts.get("product_family", "") or run_config.get("family", "")
        product_slug = product_facts.get("product_slug", "") or run_config.get("product_slug", "")

        # Extract positioning from code_analysis
        positioning = code_analysis.get("positioning", {})
        short_description = (
            positioning.get("short_description", "")
            or positioning.get("tagline", "")
            or product_facts.get("product_description", "")
        )

        # Infer category from product family and claims
        product_category = _infer_category(product_family, product_facts)

        # Infer audience from claims
        primary_audience = _infer_audience(product_facts)

        # Extract key differentiators from key_features
        key_features = product_facts.get("claim_groups", {}).get("key_features", [])
        claims = product_facts.get("claims", [])
        claim_by_id = {c["claim_id"]: c for c in claims}
        key_differentiators = []
        for fid in key_features[:5]:
            claim = claim_by_id.get(fid, {})
            text = claim.get("enriched_text") or claim.get("claim_text", "")
            if text:
                key_differentiators.append(text)

        # License
        license_type = product_facts.get("license", "")

        # Supported platforms
        supported_platforms = []
        target_platform = run_config.get("target_platform", "")
        if target_platform:
            supported_platforms.append(target_platform)

        # Claim summary
        claim_summary = {}
        for claim in claims:
            kind = claim.get("claim_kind", "unknown")
            claim_summary[kind] = claim_summary.get(kind, 0) + 1

        # Infer content tone and complexity
        content_tone = _infer_tone(product_facts, run_config)
        complexity_level = _infer_complexity(product_facts)

        # Maturity
        maturity = "stable"
        if any("alpha" in str(c.get("claim_text", "")).lower() for c in claims[:20]):
            maturity = "alpha"
        elif any("beta" in str(c.get("claim_text", "")).lower() for c in claims[:20]):
            maturity = "beta"

        return cls(
            product_name=product_name,
            product_family=product_family,
            product_slug=product_slug,
            product_category=product_category,
            short_description=short_description,
            primary_audience=primary_audience,
            key_differentiators=key_differentiators,
            competitive_context="",
            content_tone=content_tone,
            complexity_level=complexity_level,
            supported_platforms=supported_platforms,
            repo_url=product_facts.get("repo_url", ""),
            license_type=license_type,
            maturity=maturity,
            claim_summary=claim_summary,
        )

    @property
    def has_rich_content(self) -> bool:
        """Whether the profile has enough data for rich content generation."""
        total = sum(self.claim_summary.values())
        return total >= 10 and len(self.key_differentiators) >= 2

    @property
    def audience_label(self) -> str:
        """Human-readable audience description."""
        if self.primary_audience:
            return ", ".join(self.primary_audience[:3])
        return "software developers"


def _infer_category(family: str, product_facts: Dict[str, Any]) -> str:
    """Infer product category from family and claims."""
    category_map = {
        "3d": "3D modeling and rendering library",
        "cells": "spreadsheet processing SDK",
        "words": "document processing SDK",
        "pdf": "PDF manipulation library",
        "slides": "presentation processing SDK",
        "email": "email processing library",
        "imaging": "image processing library",
        "barcode": "barcode generation and recognition SDK",
        "ocr": "optical character recognition library",
        "cad": "CAD file processing library",
        "note": "digital notebook processing library",
        "tasks": "project management file library",
        "diagram": "diagram processing library",
    }
    if family.lower() in category_map:
        return category_map[family.lower()]

    # Fallback: infer from product description
    description = product_facts.get("product_description", "").lower()
    if "library" in description:
        return "software library"
    if "sdk" in description:
        return "software development kit"
    return "software library"


def _infer_audience(product_facts: Dict[str, Any]) -> List[str]:
    """Infer target audience from claims and metadata."""
    audience = set()
    target_audience = product_facts.get("target_audience", "")
    if target_audience:
        audience.add(target_audience)

    who = product_facts.get("who_it_is_for", "")
    if who:
        audience.add(who)

    if not audience:
        audience.add("software developers")

    return sorted(audience)


def _infer_tone(product_facts: Dict[str, Any], run_config: Dict[str, Any]) -> str:
    """Infer appropriate content tone."""
    # Check for explicit config
    tone = run_config.get("content_tone", "")
    if tone:
        return tone

    # Tutorial-heavy products → tutorial-friendly
    claim_groups = product_facts.get("claim_groups", {})
    tutorials = len(claim_groups.get("tutorials", []))
    workflows = len(claim_groups.get("workflow_claims", []))
    if tutorials + workflows > 10:
        return "tutorial-friendly"

    return "technical"


def _infer_complexity(product_facts: Dict[str, Any]) -> str:
    """Infer target complexity level."""
    claims = product_facts.get("claims", [])
    if not claims:
        return "intermediate"

    # Check enrichment data for audience levels
    levels = [c.get("audience_level", "") for c in claims if c.get("audience_level")]
    if levels:
        from collections import Counter
        counts = Counter(levels)
        most_common = counts.most_common(1)[0][0]
        if most_common in ("beginner", "intermediate", "advanced"):
            return most_common

    return "intermediate"
