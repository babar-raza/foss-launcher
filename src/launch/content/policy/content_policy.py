"""Evidence-based content policy engine.

Computes per-section ``SectionPolicy`` objects from repo artifacts, determining
how many optional pages each section may contain based on the richness of the
available evidence.

Feature flag: ``run_config.use_content_policy = true`` (default: ``false``).
When the flag is absent or false this module is never imported; existing
W4 behaviour is preserved exactly.

All computation is deterministic — no LLM calls, no I/O, no randomness.
The public ``EvidenceBasedPolicy.build()`` classmethod is a pure function.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Evidence score thresholds → optional_max_pages cap
# Sorted high→low; first matching threshold wins.
# ``None`` means "use the section cap unchanged" (no additional restriction).
# ---------------------------------------------------------------------------
_OPTIONAL_MAX_THRESHOLDS = [
    (0.80, None),  # score ≥ 0.80 → unrestricted (use section cap)
    (0.60, 4),
    (0.40, 3),
    (0.25, 2),
    (0.15, 1),
    (0.00, 0),
]

# ---------------------------------------------------------------------------
# Claim-kind → allowed optional page roles
# ---------------------------------------------------------------------------
_ROLES_BY_CLAIM_KIND: Dict[str, List[str]] = {
    "feature": ["comparison", "feature_showcase", "how-to", "tutorial"],
    "api": ["api_reference", "faq", "quickstart"],
    "workflow": ["how-to", "howto_article", "quickstart", "tutorial"],
    "limitation": ["faq", "troubleshooting"],
    "quickstart": ["quickstart", "tutorial"],
    "format": ["comparison", "how-to", "tutorial"],
    "performance": ["faq", "tutorial"],
    "compatibility": ["comparison", "faq"],
}

# Roles always included regardless of claim kinds
_DEFAULT_ROLES: List[str] = ["blog_post", "overview"]

# Section-level factor based on discovered topic count from topic_manifest
_SECTION_TOPIC_FACTORS = [
    (3, 1.00),   # 3+ topics → full score
    (1, 0.85),   # 1-2 topics → slight reduction
    (0, 0.70),   # 0 topics  → conservative
]


# ---------------------------------------------------------------------------
# Public data classes
# ---------------------------------------------------------------------------


@dataclass
class SectionPolicy:
    """Policy decision for a single section.

    ``mandatory_min_pages`` is passed through from the caller and is NEVER
    modified by the policy engine — it reflects the run_config guarantee.
    ``optional_max_pages`` is the computed cap for optional pages.
    """

    section: str
    mandatory_min_pages: int = 0
    optional_max_pages: int = 0
    evidence_score: float = 0.0
    allowed_optional_page_roles: List[str] = field(default_factory=list)
    reasons: List[str] = field(default_factory=list)


@dataclass
class _EvidenceProfile:
    """Internal intermediate: global evidence breakdown before per-section split."""

    claim_count: int = 0
    claim_kinds: Dict[str, int] = field(default_factory=dict)
    avg_citations_per_claim: float = 0.0
    high_confidence_count: int = 0
    snippet_count: int = 0
    doc_chunk_count: int = 0
    claim_group_count: int = 0
    repo_quality_tier: str = "standard"
    raw_score: float = 0.0
    score_breakdown: Dict[str, float] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Public class
# ---------------------------------------------------------------------------


class EvidenceBasedPolicy:
    """Per-section content policy computed from repo artifacts.

    Usage::

        policy = EvidenceBasedPolicy.build(
            sections=["docs", "kb", "blog"],
            product_facts=product_facts_dict,
            snippet_catalog=snippet_catalog_dict,
            topic_manifest=topic_manifest_dict,   # optional
            source_chunks=source_chunks_dict,     # optional
            repo_profile=repo_profile_dict,       # optional (Agent C)
            section_caps={"docs": 5, "kb": 3},   # from page_expansion config
            mandatory_mins={"docs": 2},           # from required_sections
        )

        section_pol = policy.for_section("docs")
        # section_pol.optional_max_pages → e.g. 3

        artifact = policy.to_artifact()
        # write to artifacts/content_policy.json
    """

    def __init__(self, section_policies: Dict[str, SectionPolicy]) -> None:
        self._policies = section_policies

    def for_section(self, section: str) -> SectionPolicy:
        """Return the policy for *section*.

        If the section was not included in ``build()``, a permissive default
        (no restriction) is returned so unknown sections are never blocked.
        """
        return self._policies.get(
            section,
            SectionPolicy(
                section=section,
                optional_max_pages=999,
                allowed_optional_page_roles=list(_DEFAULT_ROLES),
            ),
        )

    def to_artifact(self) -> Dict[str, Any]:
        """Serialise to ``content_policy.json`` artifact format."""
        sorted_policies = sorted(self._policies.values(), key=lambda p: p.section)
        total = len(sorted_policies)
        with_optional = sum(1 for p in sorted_policies if p.optional_max_pages > 0)
        suppressed = sum(1 for p in sorted_policies if p.optional_max_pages == 0)

        return {
            "schema_version": "2.0",
            "engine": "evidence_based_v2",
            "summary": {
                "total_sections": total,
                "sections_with_optional_pages": with_optional,
                "sections_suppressed": suppressed,
            },
            "sections": [
                {
                    "section": p.section,
                    "mandatory_min_pages": p.mandatory_min_pages,
                    "optional_max_pages": p.optional_max_pages,
                    "evidence_score": round(p.evidence_score, 4),
                    "allowed_optional_page_roles": sorted(p.allowed_optional_page_roles),
                    "reasons": p.reasons,
                }
                for p in sorted_policies
            ],
        }

    @classmethod
    def build(
        cls,
        sections: List[str],
        product_facts: Dict[str, Any],
        snippet_catalog: Dict[str, Any],
        topic_manifest: Optional[Dict[str, Any]] = None,
        source_chunks: Optional[Dict[str, Any]] = None,
        repo_profile: Optional[Dict[str, Any]] = None,
        section_caps: Optional[Dict[str, int]] = None,
        mandatory_mins: Optional[Dict[str, int]] = None,
    ) -> "EvidenceBasedPolicy":
        """Compute per-section policies from available artifacts.

        This is a **pure function** — all inputs are dicts, no I/O occurs.

        Args:
            sections: Sections to compute policies for (e.g. ["docs","kb","blog"]).
            product_facts: Full ``product_facts.json`` dict.
            snippet_catalog: Full ``snippet_catalog.json`` dict.
            topic_manifest: ``topic_manifest.json`` dict (optional).
            source_chunks: ``source_chunks.json`` dict (optional).
            repo_profile: ``repo_profile.json`` dict (optional, from Agent C).
            section_caps: Max optional pages per section from ``page_expansion`` config.
            mandatory_mins: Mandatory min pages per section from ``required_sections``.

        Returns:
            :class:`EvidenceBasedPolicy` with per-section decisions.
        """
        _section_caps = section_caps or {}
        _mandatory_mins = mandatory_mins or {}

        profile = _compute_global_profile(
            product_facts=product_facts,
            snippet_catalog=snippet_catalog,
            source_chunks=source_chunks,
            repo_profile=repo_profile,
        )

        allowed_roles = _derive_allowed_roles(profile.claim_kinds)

        policies: Dict[str, SectionPolicy] = {}
        for section in sections:
            section_score, reasons = _apply_section_factors(
                global_score=profile.raw_score,
                profile=profile,
                section=section,
                topic_manifest=topic_manifest,
            )

            cap = _section_caps.get(section, 999)
            mandatory_min = _mandatory_mins.get(section, 0)
            optional_max = _derive_optional_max(section_score, cap)

            # Safety: optional_max must never imply fewer pages than mandatory_min
            # (the policy controls OPTIONAL pages, mandatory are always guaranteed)
            # We just log a diagnostic here; W4 enforces the invariant separately.
            if optional_max < mandatory_min:
                logger.debug(
                    "[ContentPolicy] section=%s: optional_max=%d < mandatory_min=%d; "
                    "mandatory guarantee is handled by W4, not the policy engine.",
                    section,
                    optional_max,
                    mandatory_min,
                )

            policies[section] = SectionPolicy(
                section=section,
                mandatory_min_pages=mandatory_min,
                optional_max_pages=optional_max,
                evidence_score=round(section_score, 4),
                allowed_optional_page_roles=allowed_roles,
                reasons=reasons,
            )

            logger.debug(
                "[ContentPolicy] section=%s: evidence_score=%.3f optional_max=%d reasons=%s",
                section,
                section_score,
                optional_max,
                reasons,
            )

        return cls(policies)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _compute_global_profile(
    product_facts: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
    source_chunks: Optional[Dict[str, Any]],
    repo_profile: Optional[Dict[str, Any]],
) -> _EvidenceProfile:
    """Compute global evidence score components from artifacts."""
    profile = _EvidenceProfile()
    score = 0.0
    breakdown: Dict[str, float] = {}

    claims: List[Dict[str, Any]] = product_facts.get("claims", [])
    claim_groups: Dict[str, Any] = product_facts.get("claim_groups", {})
    snippets: List[Dict[str, Any]] = snippet_catalog.get("snippets", [])

    # --- Component 1: Claim volume (max 0.25) ---
    profile.claim_count = len(claims)
    c1 = _step(profile.claim_count, [(50, 0.25), (20, 0.20), (10, 0.15), (5, 0.10), (1, 0.05)])
    score += c1
    breakdown["claim_volume"] = c1

    # --- Component 2: Claim kind diversity (max 0.20) ---
    kind_counts: Dict[str, int] = {}
    for claim in claims:
        k = claim.get("claim_kind", "")
        if k:
            kind_counts[k] = kind_counts.get(k, 0) + 1
    profile.claim_kinds = kind_counts
    n_kinds = len(kind_counts)
    c2 = _step(n_kinds, [(5, 0.20), (3, 0.15), (2, 0.10), (1, 0.05)])
    score += c2
    breakdown["claim_diversity"] = c2

    # --- Component 3: Citation density (max 0.20) ---
    if claims:
        total_cit = sum(len(c.get("citations", [])) for c in claims)
        avg_cit = total_cit / len(claims)
    else:
        avg_cit = 0.0
    profile.avg_citations_per_claim = avg_cit
    # Step on float thresholds: manual comparison
    if avg_cit >= 3.0:
        c3 = 0.20
    elif avg_cit >= 2.0:
        c3 = 0.15
    elif avg_cit >= 1.0:
        c3 = 0.10
    elif avg_cit >= 0.5:
        c3 = 0.05
    else:
        c3 = 0.0
    score += c3
    breakdown["citation_density"] = c3

    # --- Component 4: High-confidence claims (max 0.10) ---
    high_conf = sum(1 for c in claims if c.get("confidence") == "high")
    profile.high_confidence_count = high_conf
    c4 = _step(high_conf, [(10, 0.10), (5, 0.07), (2, 0.04), (1, 0.02)])
    score += c4
    breakdown["high_confidence_claims"] = c4

    # --- Component 5: Snippet coverage (max 0.15) ---
    profile.snippet_count = len(snippets)
    c5 = _step(profile.snippet_count, [(20, 0.15), (10, 0.10), (5, 0.07), (1, 0.04)])
    score += c5
    breakdown["snippet_coverage"] = c5

    # --- Component 6: Doc chunk depth (max 0.10) ---
    if source_chunks is not None:
        chunk_count = source_chunks.get("count", len(source_chunks.get("chunks", [])))
    else:
        chunk_count = 0
    profile.doc_chunk_count = chunk_count
    c6 = _step(chunk_count, [(50, 0.10), (20, 0.07), (5, 0.04), (1, 0.02)])
    score += c6
    breakdown["doc_chunk_depth"] = c6

    # --- Component 7: Claim group richness (max 0.05) ---
    profile.claim_group_count = len(claim_groups)
    c7 = min(0.05, len(claim_groups) * 0.005)
    score += c7
    breakdown["claim_group_richness"] = round(c7, 4)

    # --- Repo quality tier multiplier ---
    if repo_profile is not None:
        tier = repo_profile.get("quality_tier", "standard")
    else:
        tier = "standard"
    profile.repo_quality_tier = tier
    tier_mult = {"rich": 1.0, "standard": 0.90, "minimal": 0.75}.get(tier, 0.90)

    raw = max(0.0, min(1.0, score * tier_mult))
    profile.raw_score = round(raw, 4)
    profile.score_breakdown = {k: round(v, 4) for k, v in breakdown.items()}

    return profile


def _apply_section_factors(
    global_score: float,
    profile: _EvidenceProfile,
    section: str,
    topic_manifest: Optional[Dict[str, Any]],
) -> tuple[float, List[str]]:
    """Scale global score by section-specific factors; return (score, reasons)."""
    reasons: List[str] = []

    # Section factor from topic_manifest.per_section_counts
    section_topic_count = 0
    if topic_manifest is not None:
        per_section = topic_manifest.get("per_section_counts", {})
        section_topic_count = per_section.get(section, 0)

        # Warning penalty: coverage_missing for this section
        warnings = topic_manifest.get("warnings", [])
        section_warnings = [
            w for w in warnings
            if isinstance(w, str) and section in w
        ]
        if section_warnings:
            reasons.append(f"topic_coverage_warnings:{len(section_warnings)}")
        warning_penalty = len(section_warnings) * 0.05
    else:
        warning_penalty = 0.0

    # Apply section topic factor
    section_factor = 0.70
    for min_count, factor in _SECTION_TOPIC_FACTORS:
        if section_topic_count >= min_count:
            section_factor = factor
            break

    if section_topic_count == 0:
        reasons.append("no_topics_discovered_for_section")

    section_score = max(0.0, min(1.0, (global_score - warning_penalty) * section_factor))

    # Build human-readable reasons
    if profile.claim_count == 0:
        reasons.append("no_claims_found")
    elif profile.claim_count < 5:
        reasons.append(f"low_claim_count:{profile.claim_count}")

    if len(profile.claim_kinds) <= 1:
        reasons.append(f"low_claim_diversity:{len(profile.claim_kinds)}_kinds")

    if profile.avg_citations_per_claim < 1.0:
        reasons.append(
            f"low_citation_density:{round(profile.avg_citations_per_claim, 2)}_per_claim"
        )

    if profile.snippet_count == 0:
        reasons.append("no_snippets_found")

    if profile.doc_chunk_count == 0:
        reasons.append("no_source_chunks")

    if profile.repo_quality_tier == "minimal":
        reasons.append("repo_quality_tier:minimal")

    score_label = (
        "good" if section_score >= 0.60
        else "moderate" if section_score >= 0.30
        else "low"
    )
    reasons.append(f"evidence_score_{score_label}:{round(section_score, 3)}")

    return round(section_score, 4), reasons


def _derive_optional_max(evidence_score: float, section_cap: int) -> int:
    """Map *evidence_score* to an optional-page cap, bounded by *section_cap*."""
    for threshold, max_pages in _OPTIONAL_MAX_THRESHOLDS:
        if evidence_score >= threshold:
            if max_pages is None:
                return section_cap
            return min(max_pages, section_cap)
    return 0  # Unreachable but satisfies type checker


def _derive_allowed_roles(claim_kinds: Dict[str, int]) -> List[str]:
    """Return sorted list of page roles evidenced by the claim kinds present."""
    roles: set = set(_DEFAULT_ROLES)
    for kind in claim_kinds:
        roles.update(_ROLES_BY_CLAIM_KIND.get(kind, []))
    return sorted(roles)


def _step(value: int, thresholds: List[tuple[int, float]]) -> float:
    """Return the first score whose threshold *value* meets or exceeds.

    *thresholds* is a list of ``(min_value, score)`` pairs, sorted high→low.
    Returns 0.0 if no threshold is met.
    """
    for min_val, score in thresholds:
        if value >= min_val:
            return score
    return 0.0
