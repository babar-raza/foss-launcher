"""PagePlan model for W4 IAPlanner output artifact.

Typed container for the page_plan.json artifact produced by W4 IAPlanner.
Contains the information architecture plan with page entries, cross-links,
content strategies, and launch tier data.

Spec references:
- specs/schemas/page_plan.schema.json (Schema definition)
- specs/06_page_planning.md (Page planning algorithm)
- specs/21_worker_contracts.md:157-176 (W4 IAPlanner contract)
- specs/10_determinism_and_caching.md (Deterministic serialization)

TC-1031: Typed Artifact Models -- Worker Models
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .base import Artifact


class ClaimQuota:
    """Claim quota for a page's content strategy.

    Per specs/schemas/page_plan.schema.json#content_strategy/claim_quota.
    """

    def __init__(
        self,
        min_claims: int = 0,
        max_claims: int = 999,
    ):
        self.min_claims = min_claims
        self.max_claims = max_claims

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary with stable field ordering."""
        return {
            "max": self.max_claims,
            "min": self.min_claims,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ClaimQuota:
        """Deserialize from dictionary."""
        return cls(
            min_claims=data.get("min", 0),
            max_claims=data.get("max", 999),
        )


class ContentStrategy:
    """Content distribution and overlap prevention rules for a page.

    Per specs/schemas/page_plan.schema.json#content_strategy.
    """

    def __init__(
        self,
        primary_focus: Optional[str] = None,
        forbidden_topics: Optional[List[str]] = None,
        claim_quota: Optional[ClaimQuota] = None,
        child_pages: Optional[List[str]] = None,
        scenario_coverage: Optional[str] = None,
    ):
        self.primary_focus = primary_focus
        self.forbidden_topics = forbidden_topics or []
        self.claim_quota = claim_quota
        self.child_pages = child_pages or []
        self.scenario_coverage = scenario_coverage

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary with stable field ordering."""
        result: Dict[str, Any] = {}
        if self.primary_focus is not None:
            result["primary_focus"] = self.primary_focus
        if self.forbidden_topics:
            result["forbidden_topics"] = sorted(self.forbidden_topics)
        if self.claim_quota is not None:
            result["claim_quota"] = self.claim_quota.to_dict()
        if self.child_pages:
            result["child_pages"] = self.child_pages
        if self.scenario_coverage is not None:
            result["scenario_coverage"] = self.scenario_coverage
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ContentStrategy:
        """Deserialize from dictionary."""
        claim_quota_data = data.get("claim_quota")
        return cls(
            primary_focus=data.get("primary_focus"),
            forbidden_topics=data.get("forbidden_topics", []),
            claim_quota=(
                ClaimQuota.from_dict(claim_quota_data)
                if claim_quota_data is not None
                else None
            ),
            child_pages=data.get("child_pages", []),
            scenario_coverage=data.get("scenario_coverage"),
        )


class LaunchTierAdjustment:
    """Log entry for a launch tier adjustment.

    Per specs/schemas/page_plan.schema.json#launch_tier_adjustments/items.
    """

    def __init__(
        self,
        adjustment: str,
        reason: str,
        from_tier: Optional[str] = None,
        to_tier: Optional[str] = None,
        signal: Optional[str] = None,
    ):
        self.adjustment = adjustment
        self.reason = reason
        self.from_tier = from_tier
        self.to_tier = to_tier
        self.signal = signal

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary with stable field ordering."""
        result: Dict[str, Any] = {
            "adjustment": self.adjustment,
            "reason": self.reason,
        }
        if self.from_tier is not None:
            result["from_tier"] = self.from_tier
        if self.to_tier is not None:
            result["to_tier"] = self.to_tier
        if self.signal is not None:
            result["signal"] = self.signal
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> LaunchTierAdjustment:
        """Deserialize from dictionary."""
        return cls(
            adjustment=data["adjustment"],
            reason=data["reason"],
            from_tier=data.get("from_tier"),
            to_tier=data.get("to_tier"),
            signal=data.get("signal"),
        )


class PageEntry:
    """A single page in the page plan.

    Per specs/schemas/page_plan.schema.json#pages/items.
    """

    def __init__(
        self,
        section: str,
        slug: str,
        output_path: str,
        url_path: str,
        title: str,
        purpose: str,
        required_headings: Optional[List[str]] = None,
        required_claim_ids: Optional[List[str]] = None,
        required_snippet_tags: Optional[List[str]] = None,
        cross_links: Optional[List[str]] = None,
        # Optional fields
        template_path: Optional[str] = None,
        template_variant: Optional[str] = None,
        seo_keywords: Optional[List[str]] = None,
        forbidden_topics: Optional[List[str]] = None,
        token_mappings: Optional[Dict[str, str]] = None,
        page_role: Optional[str] = None,
        content_strategy: Optional[ContentStrategy] = None,
    ):
        self.section = section
        self.slug = slug
        self.output_path = output_path
        self.url_path = url_path
        self.title = title
        self.purpose = purpose
        self.required_headings = required_headings or []
        self.required_claim_ids = required_claim_ids or []
        self.required_snippet_tags = required_snippet_tags or []
        self.cross_links = cross_links or []
        # Optional
        self.template_path = template_path
        self.template_variant = template_variant
        self.seo_keywords = seo_keywords
        self.forbidden_topics = forbidden_topics
        self.token_mappings = token_mappings
        self.page_role = page_role
        self.content_strategy = content_strategy

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary with stable field ordering."""
        result: Dict[str, Any] = {
            "cross_links": sorted(self.cross_links),
            "output_path": self.output_path,
            "purpose": self.purpose,
            "required_claim_ids": sorted(self.required_claim_ids),
            "required_headings": self.required_headings,
            "required_snippet_tags": sorted(self.required_snippet_tags),
            "section": self.section,
            "slug": self.slug,
            "title": self.title,
            "url_path": self.url_path,
        }
        if self.template_path is not None:
            result["template_path"] = self.template_path
        if self.template_variant is not None:
            result["template_variant"] = self.template_variant
        if self.seo_keywords is not None:
            result["seo_keywords"] = sorted(self.seo_keywords)
        if self.forbidden_topics is not None:
            result["forbidden_topics"] = sorted(self.forbidden_topics)
        if self.token_mappings is not None:
            result["token_mappings"] = self.token_mappings
        if self.page_role is not None:
            result["page_role"] = self.page_role
        if self.content_strategy is not None:
            result["content_strategy"] = self.content_strategy.to_dict()
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PageEntry:
        """Deserialize from dictionary."""
        content_strategy_data = data.get("content_strategy")
        return cls(
            section=data["section"],
            slug=data["slug"],
            output_path=data["output_path"],
            url_path=data["url_path"],
            title=data["title"],
            purpose=data["purpose"],
            required_headings=data.get("required_headings", []),
            required_claim_ids=data.get("required_claim_ids", []),
            required_snippet_tags=data.get("required_snippet_tags", []),
            cross_links=data.get("cross_links", []),
            template_path=data.get("template_path"),
            template_variant=data.get("template_variant"),
            seo_keywords=data.get("seo_keywords"),
            forbidden_topics=data.get("forbidden_topics"),
            token_mappings=data.get("token_mappings"),
            page_role=data.get("page_role"),
            content_strategy=(
                ContentStrategy.from_dict(content_strategy_data)
                if content_strategy_data is not None
                else None
            ),
        )


class PagePlan(Artifact):
    """Page plan artifact produced by W4 IAPlanner.

    Contains the information architecture plan with page entries, cross-links,
    and content distribution strategy metadata.
    Per specs/schemas/page_plan.schema.json.
    """

    VALID_LAUNCH_TIERS = {"minimal", "standard", "rich"}
    VALID_SECTIONS = {"products", "docs", "reference", "kb", "blog"}
    VALID_PAGE_ROLES = {
        "landing", "toc", "comprehensive_guide", "workflow_page",
        "feature_showcase", "troubleshooting", "api_reference",
    }

    def __init__(
        self,
        schema_version: str,
        product_slug: str,
        launch_tier: str,
        pages: Optional[List[PageEntry]] = None,
        # Optional fields
        launch_tier_adjustments: Optional[List[LaunchTierAdjustment]] = None,
        inferred_product_type: Optional[str] = None,
        evidence_volume: Optional[Dict[str, Any]] = None,
        effective_quotas: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(schema_version)
        self.product_slug = product_slug
        self.launch_tier = launch_tier
        self.pages = pages or []
        # Optional
        self.launch_tier_adjustments = launch_tier_adjustments or []
        self.inferred_product_type = inferred_product_type
        self.evidence_volume = evidence_volume
        self.effective_quotas = effective_quotas

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary with stable field ordering."""
        result = super().to_dict()
        result.update({
            "launch_tier": self.launch_tier,
            "pages": [p.to_dict() for p in self.pages],
            "product_slug": self.product_slug,
        })

        if self.launch_tier_adjustments:
            result["launch_tier_adjustments"] = [
                a.to_dict() for a in self.launch_tier_adjustments
            ]
        if self.inferred_product_type is not None:
            result["inferred_product_type"] = self.inferred_product_type
        if self.evidence_volume is not None:
            result["evidence_volume"] = self.evidence_volume
        if self.effective_quotas is not None:
            result["effective_quotas"] = self.effective_quotas

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PagePlan:
        """Deserialize from dictionary."""
        pages_data = data.get("pages", [])
        pages = [PageEntry.from_dict(p) for p in pages_data]

        adjustments_data = data.get("launch_tier_adjustments", [])
        adjustments = [LaunchTierAdjustment.from_dict(a) for a in adjustments_data]

        return cls(
            schema_version=data.get("schema_version", "1.0"),
            product_slug=data["product_slug"],
            launch_tier=data["launch_tier"],
            pages=pages,
            launch_tier_adjustments=adjustments,
            inferred_product_type=data.get("inferred_product_type"),
            evidence_volume=data.get("evidence_volume"),
            effective_quotas=data.get("effective_quotas"),
        )

    def validate(self) -> bool:
        """Validate required fields and types.

        Returns:
            True if valid, raises ValueError otherwise.
        """
        if not self.product_slug:
            raise ValueError("product_slug is required and must be non-empty")
        if self.launch_tier not in self.VALID_LAUNCH_TIERS:
            raise ValueError(
                f"launch_tier must be one of {self.VALID_LAUNCH_TIERS}, "
                f"got '{self.launch_tier}'"
            )
        if not isinstance(self.pages, list):
            raise ValueError("pages must be a list")
        for page in self.pages:
            if page.section not in self.VALID_SECTIONS:
                raise ValueError(
                    f"page section must be one of {self.VALID_SECTIONS}, "
                    f"got '{page.section}'"
                )
            if page.page_role is not None and page.page_role not in self.VALID_PAGE_ROLES:
                raise ValueError(
                    f"page_role must be one of {self.VALID_PAGE_ROLES}, "
                    f"got '{page.page_role}'"
                )
        return True
