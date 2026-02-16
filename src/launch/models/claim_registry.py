"""ClaimKindRegistry: Single source of truth for claim kind routing and grouping.

Replaces duplicated if/elif routing chains in W2 (lines 464-506, 1421-1438)
and positional slicing in W4 (lines 2880-2898).

Usage:
    from launch.models.claim_registry import REGISTRY

    group_key = REGISTRY.route_claim(claim)              # replaces if/elif chains
    groups = REGISTRY.build_claim_groups(claims)          # replaces double-build
    selected = REGISTRY.select_claims_for_page(           # replaces positional slicing
        claims, section="docs", page_role="comprehensive_guide"
    )
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set


@dataclass(frozen=True)
class ClaimKindDef:
    """Definition of a single claim kind."""

    # The claim_groups key this kind routes to (e.g., "key_features")
    group: str

    # Maximum claims in this group (for capping)
    cap: int = 15

    # Which sections this kind is most relevant to
    section_affinities: tuple = ()

    # Which page_roles this kind is most relevant to
    page_role_affinities: tuple = ()

    # Alias normalization (e.g., "key_feature" -> "feature")
    aliases: tuple = ()

    # Sub-routing keywords for workflow disambiguation
    sub_route_keywords: Optional[Dict[str, tuple]] = None


# ── Registry Data ──────────────────────────────────────────────────────────

# Workflow sub-routing: text keywords that distinguish workflow sub-types
_WORKFLOW_SUB_ROUTES = {
    "install_steps": ("install", "setup", "pip install", "npm install"),
    "quickstart_steps": ("getting started", "quickstart", "quick start", "first", "begin"),
    # Default: "workflow_claims" (no keywords match)
}

# Canonical claim kind definitions
_CLAIM_KINDS: Dict[str, ClaimKindDef] = {
    "feature": ClaimKindDef(
        group="key_features",
        cap=25,
        section_affinities=("products", "docs", "reference"),
        page_role_affinities=("toc", "feature_showcase", "comprehensive_guide"),
        aliases=("key_feature",),
    ),
    "api": ClaimKindDef(
        group="key_features",
        cap=25,
        section_affinities=("reference", "docs"),
        page_role_affinities=("comprehensive_guide", "feature_showcase"),
        aliases=("api_reference",),
    ),
    "workflow": ClaimKindDef(
        group="workflow_claims",
        cap=12,
        section_affinities=("docs",),
        page_role_affinities=("comprehensive_guide", "workflow"),
        sub_route_keywords=_WORKFLOW_SUB_ROUTES,
    ),
    "limitation": ClaimKindDef(
        group="limitations",
        cap=15,
        section_affinities=("kb", "docs"),
        page_role_affinities=("troubleshooting", "faq"),
    ),
    "compatibility": ClaimKindDef(
        group="compatibility_notes",
        cap=10,
        section_affinities=("docs", "reference"),
        page_role_affinities=("comprehensive_guide",),
    ),
    "use_case": ClaimKindDef(
        group="use_cases",
        cap=15,
        section_affinities=("products", "blog"),
        page_role_affinities=("feature_showcase", "blog"),
    ),
    "faq": ClaimKindDef(
        group="faq",
        cap=15,
        section_affinities=("kb",),
        page_role_affinities=("faq",),
    ),
    "best_practice": ClaimKindDef(
        group="best_practices",
        cap=15,
        section_affinities=("docs", "kb"),
        page_role_affinities=("best_practices",),
    ),
    "performance": ClaimKindDef(
        group="performance",
        cap=10,
        section_affinities=("docs",),
        page_role_affinities=("performance", "best_practices"),
    ),
    "tutorial": ClaimKindDef(
        group="tutorials",
        cap=10,
        section_affinities=("docs", "blog"),
        page_role_affinities=("tutorial",),
    ),
    "troubleshooting": ClaimKindDef(
        group="troubleshooting",
        cap=15,
        section_affinities=("kb",),
        page_role_affinities=("troubleshooting", "faq"),
    ),
    "format": ClaimKindDef(
        group="_skip",  # Format claims go to supported_formats, not claim_groups
        cap=0,
    ),
}

# Install/quickstart are sub-groups of workflow, not top-level kinds.
# They get their own group keys but are routed via workflow sub-routing.
_WORKFLOW_SUBGROUPS: Dict[str, ClaimKindDef] = {
    "install_steps": ClaimKindDef(
        group="install_steps",
        cap=15,
        section_affinities=("docs",),
        page_role_affinities=("comprehensive_guide", "tutorial"),
    ),
    "quickstart_steps": ClaimKindDef(
        group="quickstart_steps",
        cap=10,
        section_affinities=("docs",),
        page_role_affinities=("tutorial", "comprehensive_guide"),
    ),
}


# ── Section → Group Priority Map ──────────────────────────────────────────
# For select_claims_for_page: which groups to pull claims from per section,
# in priority order.

_SECTION_CLAIM_PRIORITIES: Dict[str, List[str]] = {
    "products": ["key_features", "use_cases", "compatibility_notes"],
    "docs": ["key_features", "install_steps", "workflow_claims", "quickstart_steps", "tutorials"],
    "reference": ["key_features", "compatibility_notes"],
    "kb": ["faq", "troubleshooting", "limitations", "best_practices", "install_steps"],
    "blog": ["key_features", "use_cases", "tutorials", "install_steps", "workflow_claims"],
}

# Page role → group overrides (more specific than section)
_PAGE_ROLE_CLAIM_PRIORITIES: Dict[str, List[str]] = {
    "toc": ["key_features"],
    "comprehensive_guide": ["key_features", "install_steps", "workflow_claims", "quickstart_steps"],
    "feature_showcase": ["key_features", "use_cases"],
    "troubleshooting": ["troubleshooting", "install_steps", "limitations"],
    "faq": ["faq", "troubleshooting", "limitations"],
    "best_practices": ["best_practices", "performance"],
    "tutorial": ["tutorials", "install_steps", "quickstart_steps", "workflow_claims"],
    "performance": ["performance", "best_practices"],
    "blog": ["key_features", "use_cases", "tutorials"],
    "workflow": ["workflow_claims", "quickstart_steps", "install_steps"],
    # Round 12: Missing page_role mappings (TC-1701)
    "landing": ["key_features", "use_cases", "compatibility_notes"],
    "api_reference": ["key_features", "compatibility_notes", "limitations"],
    "blog_announcement": ["key_features", "use_cases", "tutorials"],
    "performance_guide": ["performance", "best_practices", "limitations"],
}

# Max claims per page role (spec 08: TOC gets 0-2, others vary)
_PAGE_ROLE_MAX_CLAIMS: Dict[str, int] = {
    "toc": 2,
    "products": 5,
    "docs": 8,
    "reference": 5,
    "kb": 5,
    "blog": 20,
    "comprehensive_guide": 8,
    "feature_showcase": 10,
    "troubleshooting": 10,
    "faq": 15,
    "best_practices": 10,
    "tutorial": 8,
    "performance": 8,
    "workflow": 8,
}


class ClaimKindRegistry:
    """Central registry for claim kind definitions.

    Provides three key operations:
    1. route_claim(claim) -> group_key: Determine which claim_group a claim belongs to
    2. build_claim_groups(claims) -> dict: Build the full claim_groups dict in one pass
    3. select_claims_for_page(claim_groups, section, page_role) -> list: Pick claims for a page
    """

    def __init__(self, kinds: Optional[Dict[str, ClaimKindDef]] = None):
        self._kinds = kinds or dict(_CLAIM_KINDS)
        # Build alias lookup
        self._alias_map: Dict[str, str] = {}
        for canonical, defn in self._kinds.items():
            for alias in defn.aliases:
                self._alias_map[alias] = canonical

    def normalize_kind(self, raw_kind: str) -> str:
        """Normalize a claim_kind string to its canonical form."""
        return self._alias_map.get(raw_kind, raw_kind)

    def get_definition(self, kind: str) -> Optional[ClaimKindDef]:
        """Get the definition for a canonical kind, or None."""
        canonical = self.normalize_kind(kind)
        return self._kinds.get(canonical)

    def route_claim(
        self,
        claim: Dict[str, Any],
        *,
        is_low_quality: bool = False,
    ) -> Optional[str]:
        """Determine which claim_group key a claim should be routed to.

        Args:
            claim: Claim dict with at least 'claim_id', 'claim_kind', 'claim_text'.
            is_low_quality: If True, feature/api claims are skipped (not routed).

        Returns:
            The group key (e.g., "key_features"), or None if the claim should be skipped.
        """
        raw_kind = claim.get("claim_kind", "feature")
        canonical = self.normalize_kind(raw_kind)
        defn = self._kinds.get(canonical)

        if defn is None:
            # Unknown kind: route to key_features if not low quality
            if is_low_quality:
                return None
            return "key_features"

        # Skip format claims (they go to supported_formats, not claim_groups)
        if defn.group == "_skip":
            return None

        # Feature/API: gate by source quality
        if canonical in ("feature", "api") and is_low_quality:
            return None

        # Workflow: sub-route by text keywords
        if defn.sub_route_keywords:
            claim_text = claim.get("claim_text", "").lower()
            for sub_group, keywords in defn.sub_route_keywords.items():
                if any(kw in claim_text for kw in keywords):
                    return sub_group
            # Default to the main group
            return defn.group

        return defn.group

    def build_claim_groups(
        self,
        claims: List[Dict[str, Any]],
        *,
        is_low_quality_fn=None,
    ) -> Dict[str, List[str]]:
        """Build the complete claim_groups dict from a list of claims in one pass.

        Args:
            claims: List of claim dicts.
            is_low_quality_fn: Optional callable(claim) -> bool for quality gating.

        Returns:
            Dict mapping group keys to sorted, capped lists of claim IDs.
        """
        # Collect claims into groups
        groups: Dict[str, List[str]] = {}
        for defn in self._kinds.values():
            if defn.group != "_skip":
                groups.setdefault(defn.group, [])
        # Also include workflow subgroups
        for sub_group in _WORKFLOW_SUBGROUPS:
            groups.setdefault(sub_group, [])

        routed_ids: Set[str] = set()

        for claim in claims:
            cid = claim.get("claim_id", "")
            if not cid or cid in routed_ids:
                continue

            is_lq = is_low_quality_fn(claim) if is_low_quality_fn else False
            group_key = self.route_claim(claim, is_low_quality=is_lq)

            if group_key and group_key in groups:
                groups[group_key].append(cid)
                routed_ids.add(cid)

        # Apply caps (sorted, deduplicated)
        caps = {defn.group: defn.cap for defn in self._kinds.values() if defn.group != "_skip"}
        caps.update({k: v.cap for k, v in _WORKFLOW_SUBGROUPS.items()})

        result = {}
        for key, ids in groups.items():
            cap = caps.get(key, 15)
            result[key] = sorted(set(ids))[:cap] if cap > 0 else sorted(set(ids))

        return result

    def select_claims_for_page(
        self,
        claim_groups: Dict[str, List[str]],
        section: str,
        page_role: str,
        *,
        max_claims: Optional[int] = None,
        exclude_ids: Optional[Set[str]] = None,
        min_claims: int = 1,
    ) -> List[str]:
        """Select claims for a specific page based on section and page_role semantics.

        Replaces W4's positional slicing (key_features[2:7][:5]) with semantic selection.

        Args:
            claim_groups: The claim_groups dict from product_facts.
            section: Section name (e.g., "docs", "products", "kb").
            page_role: Page role (e.g., "toc", "comprehensive_guide", "faq").
            max_claims: Override max claims (default from _PAGE_ROLE_MAX_CLAIMS).
            exclude_ids: Claim IDs already used on other pages (for exclusivity).

        Returns:
            List of claim IDs selected for this page.
        """
        if max_claims is None:
            # Try page_role first, then section, then default
            max_claims = _PAGE_ROLE_MAX_CLAIMS.get(
                page_role,
                _PAGE_ROLE_MAX_CLAIMS.get(section, 5),
            )

        exclude = exclude_ids or set()

        # Determine which groups to pull from, in priority order
        # Page role is more specific than section
        priorities = _PAGE_ROLE_CLAIM_PRIORITIES.get(page_role)
        if not priorities:
            priorities = _SECTION_CLAIM_PRIORITIES.get(section, ["key_features"])

        selected: List[str] = []
        for group_key in priorities:
            if len(selected) >= max_claims:
                break
            group_ids = claim_groups.get(group_key, [])
            for cid in group_ids:
                if cid in exclude and cid not in selected:
                    continue
                if cid not in selected:
                    selected.append(cid)
                    if len(selected) >= max_claims:
                        break

        # Round 12 (TC-1701): min_claims guarantee — if we got fewer than
        # min_claims, pull from ANY group ignoring exclude_ids.
        if len(selected) < min_claims:
            all_ids = [
                cid
                for group_key in priorities
                for cid in claim_groups.get(group_key, [])
                if cid not in selected
            ]
            for cid in all_ids:
                if len(selected) >= min_claims:
                    break
                selected.append(cid)

        return selected

    def select_claims_semantic(
        self,
        claim_groups: Dict[str, List[str]],
        claims_dict: Dict[str, Dict[str, Any]],
        section: str,
        page_role: str,
        *,
        target_audience: Optional[str] = None,
        exclude_ids: Optional[Set[str]] = None,
        max_claims: Optional[int] = None,
        min_claims: int = 1,
    ) -> List[str]:
        """Select claims with audience filtering and relevance weighting.

        Extends select_claims_for_page with:
        - Audience-level filtering (beginner/intermediate/advanced)
        - Confidence weighting (higher confidence preferred)
        - Exclude-ids propagation for cross-page deduplication

        Args:
            claim_groups: The claim_groups dict from product_facts.
            claims_dict: Mapping of claim_id -> claim dict (for metadata access).
            section: Section name (e.g., "docs", "products", "kb").
            page_role: Page role (e.g., "comprehensive_guide", "tutorial").
            target_audience: Audience level filter (e.g., "beginner").
            exclude_ids: Claim IDs already used on other pages.
            max_claims: Override max claims.
            min_claims: Minimum claims to return (default=1).

        Returns:
            List of claim IDs selected for this page.
        """
        # Start with base selection
        base = self.select_claims_for_page(
            claim_groups,
            section,
            page_role,
            max_claims=max_claims * 2 if max_claims else None,
            exclude_ids=exclude_ids,
            min_claims=0,
        )

        # Apply audience filtering if requested
        if target_audience and claims_dict:
            audience_map = {
                "beginner": {"beginner", "intermediate"},
                "intermediate": {"beginner", "intermediate", "advanced"},
                "advanced": {"intermediate", "advanced"},
            }
            allowed = audience_map.get(target_audience, {"beginner", "intermediate", "advanced"})

            filtered = []
            for cid in base:
                claim = claims_dict.get(cid, {})
                audience_level = claim.get("audience_level", "intermediate")
                if audience_level in allowed:
                    filtered.append(cid)
            base = filtered

        # Apply confidence weighting: sort by confidence (high > medium > low)
        if claims_dict:
            confidence_order = {"high": 0, "medium": 1, "low": 2}
            base.sort(
                key=lambda cid: confidence_order.get(
                    claims_dict.get(cid, {}).get("confidence", "high"), 1
                )
            )

        # Apply max_claims cap
        if max_claims is None:
            max_claims = _PAGE_ROLE_MAX_CLAIMS.get(
                page_role,
                _PAGE_ROLE_MAX_CLAIMS.get(section, 5),
            )
        result = base[:max_claims]

        # min_claims guarantee: pull from any group if needed
        if len(result) < min_claims:
            priorities = _PAGE_ROLE_CLAIM_PRIORITIES.get(page_role)
            if not priorities:
                priorities = _SECTION_CLAIM_PRIORITIES.get(section, ["key_features"])
            all_ids = [
                cid
                for group_key in priorities
                for cid in claim_groups.get(group_key, [])
                if cid not in result
            ]
            for cid in all_ids:
                if len(result) >= min_claims:
                    break
                result.append(cid)

        return result

    @property
    def all_group_keys(self) -> List[str]:
        """Return all valid claim group keys."""
        keys = set()
        for defn in self._kinds.values():
            if defn.group != "_skip":
                keys.add(defn.group)
        for sub_group in _WORKFLOW_SUBGROUPS:
            keys.add(sub_group)
        return sorted(keys)

    @property
    def all_kinds(self) -> List[str]:
        """Return all canonical claim kind names."""
        return sorted(self._kinds.keys())


# ── Singleton ──────────────────────────────────────────────────────────────

REGISTRY = ClaimKindRegistry()
