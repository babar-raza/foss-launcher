"""Phase C -- Plan: deterministic page plan with claim assignment."""
from __future__ import annotations

import hashlib
import logging
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from launcher.models.product import ApiSurface
    from launcher.models.understanding import ProductEvidence

import yaml

from launcher.content.template_loader import resolve_content_path
from launcher.workers.generate.seo_metadata import SEO_STOP_WORDS
from launcher.shared.slug_engine import (
    extract_slug_core,
    derive_evidence_aware_slug,
    derive_semantic_slug,
    extract_family_keyword,
    refine_slugs_batch,
    score_blog_workflow,
    validate_slug_quality,
    validate_slug_safety,
)
from launcher.models.claims import Claim, Snippet
from launcher.models.product import ProductIdentity, RichnessResult, RichnessTier
from launcher.models.plan import PlannedPage

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_TIER_MAP: dict[RichnessTier, str] = {
    RichnessTier.A: "full",
    RichnessTier.B: "core",
    RichnessTier.C: "minimal",
}

# Tier inclusion order (a "core" run includes "minimal" tiers too).
_TIER_INCLUDES: dict[str, set[str]] = {
    "minimal": {"minimal"},
    "core": {"minimal", "core"},
    "full": {"minimal", "core", "full"},
}

# Maps claim kind -> set of page_roles that are eligible to receive the claim.
# Claims whose kind is not listed here go into a catch-all bucket.
# TC-4031: Topic-category keyword filter — maps topic_category → required words.
# When a page has topic_category set, claims must contain at least one keyword
# from the matching set to be assigned. Pages without a topic_category entry
# are unaffected (all eligible claims are accepted).
_TOPIC_KEYWORDS: dict[str, set[str]] = {
    "load_file": {"load", "open", "read", "import", "parse"},
    "save_file": {"save", "write", "export", "output"},
    "convert_formats": {"convert", "transform", "pdf", "xlsx", "csv"},
    "formula_calculation": {"formula", "calculat", "comput", "function", "sum"},
    "spreadsheet_ops": {"spreadsheet", "sheet", "cell", "row", "column", "workbook"},
    "troubleshoot": {"error", "exception", "fix", "debug", "workaround"},
    "optimize_performance": {"performance", "memory", "speed", "optimiz"},
}

_KIND_TO_ROLES: dict[str, set[str]] = {
    "feature": {
        "landing", "feature_showcase", "feature_blog",
        "comprehensive_guide", "blog_announcement",
    },
    "api": {
        "api_reference", "reference_object_page", "comprehensive_guide",
    },
    "install": {
        "workflow_page", "landing", "blog_announcement",
    },
    "workflow": {
        "workflow_page", "tutorial", "howto_article",
    },
    "format": {
        "format_conversion", "feature_showcase",
    },
    "troubleshoot": {
        "troubleshooting", "faq", "howto_article",
    },
    "troubleshooting": {
        "troubleshooting", "faq", "howto_article",
    },
    "faq": {
        "faq", "troubleshooting",
    },
    "performance": {
        "performance_guide", "best_practices", "comprehensive_guide",
    },
    "config": {
        "workflow_page", "comprehensive_guide", "howto_article",
    },
    "integration": {
        "feature_showcase", "workflow_page", "comprehensive_guide",
    },
    "example": {
        "tutorial", "howto_article", "workflow_page",
        "feature_showcase", "comprehensive_guide",
    },
    "tutorial": {
        "tutorial", "howto_article", "workflow_page",
    },
    "use_case": {
        "feature_showcase", "howto_article", "tutorial",
    },
    "best_practice": {
        "best_practices", "comprehensive_guide",
    },
    "compatibility": {
        "landing", "faq", "troubleshooting",
    },
    "license": {
        "landing", "faq",
    },
    "limitation": {
        "faq", "troubleshooting",
    },
    "computation": {
        "workflow_page", "howto_article", "comprehensive_guide",
    },
}

# Claim kind sets for scenario detection (TC-HYBRID-09)
_TUTORIAL_KINDS: frozenset[str] = frozenset({"tutorial", "example", "workflow"})
_MIGRATION_SIGNALS: frozenset[str] = frozenset({"migrate", "migration", "convert from", "upgrade from", "replace"})
_COMPARISON_SIGNALS: frozenset[str] = frozenset({"vs", "versus", "compare", "comparison", "better than", "alternative"})


def detect_primary_scenario(claims: "list[Claim]") -> str:
    """Detect the dominant scenario from claim kinds and text signals.

    Returns one of: "tutorial", "migration", "evaluation", "announcement", "default".

    Used to set skeleton_variant on blog pages so they get a scenario-specific
    skeleton rather than the generic feature_blog template (TC-HYBRID-09).
    """
    if not claims:
        return "default"

    total = len(claims)
    kind_counts: dict[str, int] = {}
    for claim in claims:
        kind_counts[claim.kind] = kind_counts.get(claim.kind, 0) + 1

    tutorial_count = sum(kind_counts.get(k, 0) for k in _TUTORIAL_KINDS)
    feature_count = kind_counts.get("feature", 0)

    # Tutorial: ≥30% tutorial/example/workflow claims
    if tutorial_count / total >= 0.30:
        return "tutorial"

    # Migration: any claims with migration-like text signals
    migration_text_count = sum(
        1 for c in claims
        if any(sig in c.text.lower() for sig in _MIGRATION_SIGNALS)
    )
    if migration_text_count / total >= 0.20:
        return "migration"

    # Evaluation/comparison: ≥20% feature/compatibility with comparison signals
    comparison_text_count = sum(
        1 for c in claims
        if c.kind in {"feature", "compatibility"}
        and any(sig in c.text.lower() for sig in _COMPARISON_SIGNALS)
    )
    if comparison_text_count / total >= 0.20:
        return "evaluation"

    # Announcement: ≥40% feature claims, no tutorial/workflow signals
    if feature_count / total >= 0.40 and tutorial_count == 0:
        return "announcement"

    return "default"


_BLOG_ROLES: frozenset[str] = frozenset({"feature_blog", "blog_announcement"})


def _set_blog_variants(pages: "list[dict[str, Any]]", scenario: str) -> None:
    """Set skeleton_variant on blog pages based on detected scenario (TC-HYBRID-09).

    Only sets the variant when:
    1. The page_role is in _BLOG_ROLES
    2. The page does not already have a non-default skeleton_variant
    3. The scenario is not "default"
    4. The (page_role, scenario) pair is registered in SKELETON_VARIANTS
    """
    if scenario == "default":
        return

    from launcher.shared.page_skeletons import SKELETON_VARIANTS

    for page in pages:
        if page.get("page_role") not in _BLOG_ROLES:
            continue
        # Don't override an already-set variant
        existing = page.get("skeleton_variant")
        if existing and existing != "default":
            continue
        role = page["page_role"]
        if (role, scenario) in SKELETON_VARIANTS:
            page["skeleton_variant"] = scenario
            logger.info(
                "Scenario variant: page_id=%s role=%s scenario=%s",
                page.get("page_id", "?"), role, scenario,
            )


# ---------------------------------------------------------------------------
# TC-4231: Claim relevance scoring
# ---------------------------------------------------------------------------

def _relevance_score(claim_text: str, page_slug: str, page_title: str) -> float:
    """Score a claim's relevance to a page using keyword overlap.

    Uses string overlap between the claim text and the page slug + title words.
    Only words with length > 3 are considered to avoid noise from stop-words.

    Returns a non-negative float; higher is more relevant.
    """
    slug_words = set(re.split(r"[-/]", page_slug.lower()))
    title_words = set(page_title.lower().split())
    combined = slug_words | title_words
    claim_lower = claim_text.lower()
    matches = sum(1 for w in combined if len(w) > 3 and w in claim_lower)
    return float(matches)


def _apply_relevance_filter(
    page_claim_ids: list[str],
    claim_by_id: dict[str, "Claim"],
    page_slug: str,
    page_title: str,
    *,
    max_claims: int | None = None,
) -> list[str]:
    """Filter and re-rank page claims by relevance to the page slug/title.

    TC-4231: Keeps the top ``max_claims`` most relevant claims per page.
    If the page already has ≤ ``max_claims`` claims, it is returned unchanged.
    When ``max_claims`` is None, ``_MAX_RELEVANCE_CLAIMS_PER_PAGE`` is used.

    Fallback: if after relevance filtering the page would have < 5 claims
    AND the original list had ≥ 5, the top-5 by claim_id (deterministic) are
    kept to prevent starvation on pages with sparse vocabulary match.

    The sort is stable: equal-scoring claims retain their original order
    (stable sort on list index ensures determinism under PYTHONHASHSEED=0).
    """
    if max_claims is None:
        max_claims = _MAX_RELEVANCE_CLAIMS_PER_PAGE  # resolved at call time
    if len(page_claim_ids) <= max_claims:
        return page_claim_ids

    # Score each claim; use enumerate index as secondary key for stability
    scored: list[tuple[float, int, str]] = []
    for idx, cid in enumerate(page_claim_ids):
        claim = claim_by_id.get(cid)
        text = claim.text if claim else ""
        score = _relevance_score(text, page_slug, page_title)
        scored.append((score, idx, cid))

    # Sort by score DESC, then by original index ASC (deterministic tiebreak)
    scored.sort(key=lambda t: (-t[0], t[1]))

    filtered_ids = [cid for _, _, cid in scored[:max_claims]]

    # Starvation guard: if filtering wiped out nearly all claims, keep top-5
    _STARVATION_THRESHOLD = 5
    if len(filtered_ids) < _STARVATION_THRESHOLD and len(page_claim_ids) >= _STARVATION_THRESHOLD:
        # Fallback: take first 5 by original order (most deterministic)
        filtered_ids = page_claim_ids[:_STARVATION_THRESHOLD]

    return filtered_ids


# Roles that are structural-only and do not receive claim assignments.
_NO_CLAIM_ROLES: frozenset[str] = frozenset({"toc"})

# Robots directives by page_role (SR-04 / TC-3824).
# Structural/navigation roles are crawlable but not indexed.
# IMPORTANT: Unknown roles default to "noindex, nofollow" (safe default).
# When adding a new page_role to specs/rulesets/ruleset.yaml, also add it here.
_ROBOTS_BY_ROLE: dict[str, str] = {
    # Indexable content roles
    "landing":               "index, follow",
    "workflow_page":         "index, follow",
    "api_reference":         "index, follow",
    "faq":                   "index, follow",
    "troubleshooting":       "index, follow",
    "feature_showcase":      "index, follow",
    "howto_article":         "index, follow",
    "blog_announcement":     "index, follow",
    "feature_blog":          "index, follow",
    "reference_object_page": "index, follow",
    # Navigation/structural — crawlable but not indexed
    "toc":                   "noindex, follow",
}
# Safe default for any role not in _ROBOTS_BY_ROLE (new, unknown, or misspelled).
# Prevents accidental public indexing of pages with unrecognised roles.
_ROBOTS_SAFE_DEFAULT: str = "noindex, nofollow"

# TC-3871: Minimum eligible claims (visible, correct kind) required before
# an optional policy page is included in the plan.  Pages that lack enough
# relevant claims would produce thin, low-quality content.
# Keyed by policy.kind; _DEFAULT_MIN_CLAIMS_OPTIONAL is used as fallback.
_MIN_CLAIMS_OPTIONAL: dict[str, int] = {
    "topic_cluster": 5,
    "feature_showcase": 4,
    "deep_dive": 3,
    "per_module": 2,  # already claim-gated in _expand_per_module
}
_DEFAULT_MIN_CLAIMS_OPTIONAL = 3

# Maximum number of pages a single claim may be assigned to.
_MAX_CLAIM_PAGES = 2

# Maximum claims assigned to any single page (prevents bloat).
_MAX_CLAIMS_PER_PAGE = 12

# TC-4231: Maximum claims per page after relevance filtering.
# Applied as a safety net above _MAX_CLAIMS_PER_PAGE when the latter is relaxed.
# Configured here so operators can tune without touching assignment logic.
_MAX_RELEVANCE_CLAIMS_PER_PAGE = 50

# Minimum claims for a content page to be viable.
_MIN_CLAIMS_CONTENT_PAGE = 2

# Minimum claims mentioning a class for it to warrant a dedicated per_module page.
_MIN_CLAIMS_PER_CLASS = 2

# Minimum class name length for word-boundary matching (avoid false positives).
_MIN_CLASS_NAME_LEN = 3

# Default ruleset path relative to the project root.
_DEFAULT_RULESET = Path(__file__).resolve().parents[4] / "specs" / "rulesets" / "ruleset.yaml"


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_plan(
    product: ProductIdentity,
    richness: RichnessResult,
    claims: list[Claim],
    snippets: list[Snippet],
    *,
    ruleset_path: Path | None = None,
    product_evidence: ProductEvidence | None = None,
    llm_client: Any = None,
    keyword_bundle: Any = None,
    api_surface: ApiSurface | None = None,
    gemini_client: Any = None,
    page_evidence_index: "dict | None" = None,
) -> tuple[list[PlannedPage], dict[str, list[str]]]:
    """Build deterministic page plan from ruleset + claims.

    Returns
    -------
    tuple of (pages, claim_assignment_index)
        *pages* is the ordered list of PlannedPage objects.
        *claim_assignment_index* maps ``claim_id`` to the list of
        ``page_id`` values where that claim was assigned.
    """
    # 1. Load ruleset
    ruleset = _load_ruleset(ruleset_path)

    # 2. Enumerate mandatory pages for this family
    tier_letter = richness.tier.value  # "A", "B", or "C"
    code_evidence_sparse = richness.code_evidence_sparse  # TR-01: carry forward to PlannedPage
    pages = _enumerate_mandatory_pages(
        ruleset, product, richness, tier_letter,
        product_evidence=product_evidence, snippets=snippets,
    )

    # 3. Apply tier-driven optional expansion
    pages = _apply_optional_expansion(
        pages, ruleset, richness, claims, product, tier_letter,
        product_evidence=product_evidence,
        api_surface=api_surface,
    )

    # 3b. Disambiguate duplicate page_ids from evidence-derived slugs
    pages = _disambiguate_slugs(pages)

    # 3c. Slug quality gate — reject nonsensical/garbled slugs (TC-3820)
    pages = _quality_check_slugs(pages, product)

    # 3d. Re-disambiguate after quality gate may have introduced collisions (SR-01)
    pages = _disambiguate_slugs(pages)

    # TC-HYBRID-09: detect primary scenario and set blog page variants
    scenario = detect_primary_scenario(claims or [])
    if scenario != "default":
        logger.info("[Planner] Detected primary scenario: %s", scenario)
    _set_blog_variants(pages, scenario)

    # 4. Assign skeletons to pages
    pages = _assign_skeletons(pages)

    # 5. Assign claims to pages (mandatory pages get priority)
    pages, claim_index = _assign_claims(
        pages, claims, snippets,
        product_name=product.display_name,
        keyword_bundle=keyword_bundle,
        richness_tier=tier_letter,           # TC-3876: propagate tier to PlannedPage
        code_evidence_sparse=code_evidence_sparse,  # TR-01: propagate sparse flag
    )

    # 5b. Density-based page pruning (TC-3817 Change B)
    #     Optional pages with insufficient content density are pruned.
    pages, claim_index = _prune_thin_pages(pages, claim_index, snippets)

    # 5c. TC-4218: Post-title deduplication.
    #     Run after pruning so we only operate on surviving pages.
    #     Validate each title and append slug-derived suffix when titles collide.
    pages = _dedup_and_validate_titles(pages, product_name=product.display_name)

    # 6. Build frontmatter and SEO keywords
    pages = _build_frontmatter(pages, product)

    # 6b. Optional slug refinement via Gemini (preferred) or LLM fallback
    if gemini_client is not None:
        pages = _refine_page_slugs(pages, gemini_client=gemini_client, product=product)
    elif llm_client is not None:
        pages = _refine_page_slugs(pages, llm_client=llm_client)

    # TC-4250: Evidence gate — skip non-mandatory pages with evidence_sufficient=False
    pages = _apply_evidence_gate(pages, page_evidence_index)

    # 7. Self-review checks
    _validate_plan(pages, claims)

    return pages, claim_index


# ---------------------------------------------------------------------------
# 1. Ruleset loading
# ---------------------------------------------------------------------------


def _load_ruleset(path: Path | None = None) -> dict[str, Any]:
    """Load and parse ``specs/rulesets/ruleset.yaml``."""
    path = path or _DEFAULT_RULESET
    if not path.exists():
        raise FileNotFoundError(f"Ruleset not found: {path}")
    with open(path, "r", encoding="utf-8") as fh:
        ruleset = yaml.safe_load(fh)
    logger.debug("Loaded ruleset v%s from %s", ruleset.get("version"), path)
    return ruleset


# ---------------------------------------------------------------------------
# 2. Mandatory page enumeration
# ---------------------------------------------------------------------------


def _expand_slug(slug_template: str, product: ProductIdentity) -> str:
    """Expand ``{family}`` and ``{platform}`` placeholders in slugs."""
    return slug_template.replace("{family}", product.family).replace(
        "{platform}", product.platform
    )


def _tier_value(tier_name: str) -> int:
    """Return an ordinal for tier comparison (minimal=0, core=1, full=2)."""
    return {"minimal": 0, "core": 1, "full": 2}.get(tier_name, 0)


def _enumerate_mandatory_pages(
    ruleset: dict[str, Any],
    product: ProductIdentity,
    richness: RichnessResult,
    tier_letter: str,
    *,
    product_evidence: ProductEvidence | None = None,
    snippets: list[Snippet] | None = None,
) -> list[dict[str, Any]]:
    """Create page dicts for every mandatory entry in each section."""
    resolved_tier = _TIER_MAP[richness.tier]
    resolved_tier_val = _tier_value(resolved_tier)
    pages: list[dict[str, Any]] = []

    sections: dict[str, Any] = ruleset.get("sections", {})
    for section_name, section_cfg in sections.items():
        mandatory_entries: list[dict[str, Any]] = section_cfg.get("mandatory", [])
        for entry in mandatory_entries:
            # Honour tier_minimum: skip pages that require a higher tier
            tier_min = entry.get("tier_minimum")
            if tier_min and _tier_value(tier_min) > resolved_tier_val:
                logger.debug(
                    "Skipping page %s/%s (requires tier %s, have %s)",
                    section_name, entry["slug"], tier_min, resolved_tier,
                )
                continue

            slug = _expand_slug(entry["slug"], product)
            page_role = entry["page_role"]

            # Evidence-aware slug enrichment for KB how-to pages
            if product_evidence is not None and entry.get("topic_category"):
                title_for_slug = _generate_title(slug, page_role)
                ev_slug = derive_evidence_aware_slug(
                    title_for_slug, product.family,
                    product_evidence, platform=product.platform,
                )
                if ev_slug and ev_slug != slug:
                    safety_issues = validate_slug_safety(ev_slug)
                    if not safety_issues:
                        logger.debug("Enriched KB slug: %s -> %s", slug, ev_slug)
                        slug = ev_slug
                    else:
                        logger.debug(
                            "Rejected unsafe evidence slug %r for %s/%s: %s",
                            ev_slug, section_name, slug, "; ".join(safety_issues),
                        )

            # Blog workflow slug enrichment for feature_blog pages
            if (
                product_evidence is not None
                and section_name == "blog"
                and page_role == "feature_blog"
            ):
                # Convert pydantic Snippet objects to dicts for score_blog_workflow
                snippet_dicts = [
                    {"claim_ids": s.claim_ids, "tags": []}
                    for s in (snippets or [])
                ]
                wf = score_blog_workflow(
                    product_evidence, snippet_dicts,
                    product.family, product.platform,
                )
                if wf.get("score", 0) > 0:
                    blog_slug = wf["slug"]
                    safety_issues = validate_slug_safety(blog_slug)
                    if not safety_issues:
                        logger.debug(
                            "Enriched blog slug: %s -> %s (score=%d)",
                            slug, blog_slug, wf["score"],
                        )
                        slug = blog_slug
                    else:
                        logger.debug(
                            "Rejected unsafe blog slug %r: %s",
                            blog_slug, "; ".join(safety_issues),
                        )

            page_id = _generate_page_id(section_name, slug)

            cp = resolve_content_path(
                section_name, page_role, slug,
                product.family, product.platform, tier_letter,
            )
            pages.append({
                "section": section_name,
                "page_id": page_id,
                "page_role": page_role,
                "slug": slug,
                "content_path": cp,
                "mandatory": True,
                "folder_index": entry.get("folder_index", False),
                "topic_category": entry.get("topic_category"),
            })

    # Apply family_overrides (additional_mandatory)
    overrides = ruleset.get("family_overrides", {})
    family_override = overrides.get(product.family, {})
    for section_name, section_override in family_override.items():
        additional: list[dict[str, Any]] = section_override.get(
            "additional_mandatory", []
        )
        for entry in additional:
            slug = _expand_slug(entry["slug"], product)
            page_role = entry["page_role"]
            page_id = _generate_page_id(section_name, slug)
            cp = resolve_content_path(
                section_name, page_role, slug,
                product.family, product.platform, tier_letter,
            )
            pages.append({
                "section": section_name,
                "page_id": page_id,
                "page_role": page_role,
                "slug": slug,
                "content_path": cp,
                "mandatory": True,
                "folder_index": entry.get("folder_index", False),
                "topic_category": entry.get("topic_category"),
            })

    logger.info(
        "Enumerated %d mandatory pages for family=%s tier=%s",
        len(pages), product.family, resolved_tier,
    )
    return pages


# ---------------------------------------------------------------------------
# 3a. Helpers for claim-gated per_module expansion
# ---------------------------------------------------------------------------

def _class_name_to_slug(cls_name: str) -> str:
    """Convert a CamelCase class name to a kebab-case slug.

    Examples:
        WorksheetCollection → worksheet-collection
        PDFDocument         → pdf-document
        HTMLParser          → html-parser
        Workbook            → workbook
    """
    # Split on CamelCase boundaries, handling consecutive uppercase (acronyms)
    parts = re.sub(
        r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])",
        "-",
        cls_name,
    )
    slug = parts.lower().strip("-")
    # Remove characters that aren't alphanumeric or hyphens
    slug = re.sub(r"[^a-z0-9-]", "", slug)
    # Collapse multiple hyphens
    slug = re.sub(r"-{2,}", "-", slug)

    if not slug:
        slug = f"ref-{hashlib.md5(cls_name.encode()).hexdigest()[:8]}"

    safety_issues = validate_slug_safety(slug)
    if safety_issues:
        logger.debug("Rejected class slug %r: %s", slug, "; ".join(safety_issues))
        slug = f"ref-{hashlib.md5(cls_name.encode()).hexdigest()[:8]}"

    return slug


def _build_class_claim_index(
    claims: list[Claim],
    public_classes: list[str],
) -> dict[str, list[str]]:
    """Map each public class to claim IDs that reference it by name.

    Uses word-boundary matching on claim text.  Skips class names shorter
    than ``_MIN_CLASS_NAME_LEN`` to avoid false positives (e.g. "Pr"
    matching "provides").
    """
    index: dict[str, list[str]] = {cls: [] for cls in public_classes}
    eligible_claims = [
        c for c in claims
        if c.kind in {"api", "feature", "example"} and c.visibility != "internal"
    ]
    # Pre-compile patterns for classes long enough to match safely
    patterns: list[tuple[str, re.Pattern[str]]] = []
    for cls in public_classes:
        if len(cls) >= _MIN_CLASS_NAME_LEN:
            patterns.append((cls, re.compile(rf"\b{re.escape(cls)}\b", re.IGNORECASE)))

    for claim in eligible_claims:
        for cls, pat in patterns:
            if pat.search(claim.text):
                index[cls].append(claim.claim_id)

    return index


# ---------------------------------------------------------------------------
# 3. Optional expansion
# ---------------------------------------------------------------------------


def _apply_optional_expansion(
    pages: list[dict[str, Any]],
    ruleset: dict[str, Any],
    richness: RichnessResult,
    claims: list[Claim],
    product: ProductIdentity | None = None,
    tier_letter: str = "B",
    *,
    product_evidence: ProductEvidence | None = None,
    api_surface: ApiSurface | None = None,
) -> list[dict[str, Any]]:
    """Add optional pages based on tier budget and claim volume."""
    resolved_tier = _TIER_MAP[richness.tier]
    sections = ruleset.get("sections", {})

    for section_name, section_cfg in sections.items():
        policies: list[dict[str, Any]] = section_cfg.get("optional_policies", [])
        for policy in policies:
            kind = policy.get("kind", "")

            # Trigger-based policies (e.g. topic_cluster)
            trigger = policy.get("trigger")
            if trigger:
                if not _evaluate_trigger(trigger, claims):
                    continue

            # Tier-budget policies
            tier_budget = policy.get("tier_budget")
            if tier_budget:
                budget = tier_budget.get(resolved_tier, 0)
            else:
                budget = policy.get("max_pages", 1)

            if budget <= 0:
                continue

            # TC-3871: Claim-volume gate — skip optional page when claim pool
            # for its role is below the minimum threshold.  This prevents
            # adding placeholder-quality pages to lean repos.
            # Note: per_module has its own claim gate in _expand_per_module.
            if kind != "per_module":
                page_role = _policy_kind_to_role(kind)
                eligible_kinds: set[str] = set()
                for ck, roles in _KIND_TO_ROLES.items():
                    if page_role in roles:
                        eligible_kinds.add(ck)
                eligible_claim_count = sum(
                    1 for c in claims
                    if c.visibility != "internal"
                    and (not eligible_kinds or c.kind in eligible_kinds)
                )
                min_required = _MIN_CLAIMS_OPTIONAL.get(kind, _DEFAULT_MIN_CLAIMS_OPTIONAL)
                if eligible_claim_count < min_required:
                    logger.info(
                        "optional_skipped: kind=%s eligible_claims=%d < min=%d (tier=%s)",
                        kind, eligible_claim_count, min_required, resolved_tier,
                    )
                    continue

            # ----- Claim-gated path for per_module -----
            if kind == "per_module":
                pages = _expand_per_module(
                    pages, section_name, budget, claims, product,
                    tier_letter, api_surface=api_surface,
                )
                continue

            # ----- Default path for other optional policies -----
            for i in range(budget):
                slug = _derive_optional_slug(
                    kind, i, budget, product, product_evidence, claims,
                )
                page_id = _generate_page_id(section_name, slug)

                # Skip if a page with this id already exists
                if any(p["page_id"] == page_id for p in pages):
                    continue

                # Map policy kind to a page_role
                page_role = _policy_kind_to_role(kind)

                family = product.family if product else ""
                platform = product.platform if product else ""
                cp = resolve_content_path(
                    section_name, page_role, slug,
                    family, platform, tier_letter,
                )
                pages.append({
                    "section": section_name,
                    "page_id": page_id,
                    "page_role": page_role,
                    "slug": slug,
                    "content_path": cp,
                    "mandatory": False,
                    "folder_index": False,
                    "topic_category": None,
                })

    logger.info("After optional expansion: %d total pages", len(pages))
    return pages


def _expand_per_module(
    pages: list[dict[str, Any]],
    section_name: str,
    budget: int,
    claims: list[Claim],
    product: ProductIdentity | None,
    tier_letter: str,
    *,
    api_surface: ApiSurface | None = None,
) -> list[dict[str, Any]]:
    """Create per_module (reference_object_page) pages gated on claim evidence.

    Only creates pages for public classes that have at least
    ``_MIN_CLAIMS_PER_CLASS`` claims mentioning them.  When viable classes
    exist, the api_reference page in the same section is switched to the
    ``index`` skeleton variant.
    """
    public_classes = api_surface.public_classes if api_surface else []
    if not public_classes:
        logger.info("Skipping per_module: no public classes in api_surface")
        return pages

    class_claim_idx = _build_class_claim_index(claims, public_classes)

    # Viable = classes with enough claims to warrant a dedicated page
    viable = sorted(
        [(cls, cids) for cls, cids in class_claim_idx.items()
         if len(cids) >= _MIN_CLAIMS_PER_CLASS],
        key=lambda x: len(x[1]),
        reverse=True,
    )

    # Log which classes qualified and which fell below the threshold
    if viable:
        viable_desc = ", ".join(f"{cls}({len(cids)})" for cls, cids in viable[:10])
        below = [(c, ids) for c, ids in class_claim_idx.items()
                 if 0 < len(ids) < _MIN_CLAIMS_PER_CLASS]
        below_desc = ", ".join(f"{c}({len(ids)})" for c, ids in below[:5])
        logger.info("per_module selected: %s; below-threshold: %s",
                    viable_desc, below_desc or "none")

    actual_budget = min(budget, len(viable))
    if actual_budget == 0:
        logger.info(
            "Skipping per_module: no classes with >= %d claims (out of %d public classes)",
            _MIN_CLAIMS_PER_CLASS, len(public_classes),
        )
        return pages

    logger.info(
        "per_module: creating %d pages (budget=%d, viable=%d)",
        actual_budget, budget, len(viable),
    )

    family = product.family if product else ""
    platform = product.platform if product else ""
    page_role = "reference_object_page"

    for i in range(actual_budget):
        cls_name, _ = viable[i]
        slug = _class_name_to_slug(cls_name)
        page_id = _generate_page_id(section_name, slug)

        # Skip duplicates
        if any(p["page_id"] == page_id for p in pages):
            continue

        cp = resolve_content_path(
            section_name, page_role, slug,
            family, platform, tier_letter,
        )
        pages.append({
            "section": section_name,
            "page_id": page_id,
            "page_role": page_role,
            "slug": slug,
            "content_path": cp,
            "mandatory": False,
            "folder_index": False,
            "topic_category": None,
            "target_class": cls_name,
        })

    # Switch the api_reference page to index mode since sub-pages exist
    for page in pages:
        if page["page_role"] == "api_reference" and page.get("section") == section_name:
            page["skeleton_variant"] = "index"
            logger.debug("Switched api_reference page %s to index mode", page["page_id"])
            break

    return pages


def _derive_optional_slug(
    kind: str,
    index: int,
    budget: int,
    product: ProductIdentity | None,
    product_evidence: ProductEvidence | None,
    claims: list[Claim],
) -> str:
    """Derive a meaningful slug for optional pages.

    Uses claims relevant to this page kind to produce a semantic slug.
    Falls back to ``{kind}-{family_keyword}-{index+1}``.
    """
    if product_evidence is not None and product is not None:
        family_kw = extract_family_keyword(product.family)

        # Find claims relevant to this optional page's role
        role = _policy_kind_to_role(kind)
        eligible_kinds: set[str] = set()
        for claim_kind, roles in _KIND_TO_ROLES.items():
            if role in roles:
                eligible_kinds.add(claim_kind)

        relevant = [
            c for c in claims
            if c.kind in eligible_kinds and c.visibility != "internal"
        ]

        if relevant:
            # Try multiple claims until one produces a quality slug (TC-3820)
            start_idx = min(index, len(relevant) - 1)
            for try_idx in range(start_idx, min(start_idx + 3, len(relevant))):
                semantic = derive_semantic_slug(relevant[try_idx].text, max_length=35)
                if not semantic or semantic == "feature":
                    continue
                if family_kw not in semantic:
                    enriched = f"{semantic}-{family_kw}"
                    if len(enriched) <= 50:
                        semantic = enriched
                safety_issues = validate_slug_safety(semantic)
                quality_issues = validate_slug_quality(semantic, product.family)
                if not safety_issues and not quality_issues:
                    logger.debug("Optional slug derived: %s-%d -> %s", kind, index, semantic)
                    return semantic
                logger.debug(
                    "Rejected optional slug %r: safety=%s quality=%s",
                    semantic,
                    "; ".join(safety_issues) if safety_issues else "ok",
                    "; ".join(quality_issues) if quality_issues else "ok",
                )
            # All claims produced bad slugs — try extract_slug_core
            core = extract_slug_core(
                relevant[start_idx].text, product.family, product.platform,
            )
            if core:
                safety_issues = validate_slug_safety(core)
                quality_issues = validate_slug_quality(core, product.family)
                if not safety_issues and not quality_issues:
                    logger.debug("Optional slug from core: %s-%d -> %s", kind, index, core)
                    return core

        # Fallback with family keyword
        if budget > 1:
            return f"{kind}-{family_kw}-{index + 1}"
        return f"{kind}-{family_kw}"

    # No evidence: preserve original behavior
    if budget > 1:
        return f"{kind}-{index + 1}"
    return kind


def _evaluate_trigger(trigger: str, claims: list[Claim]) -> bool:
    """Evaluate a simple trigger expression like ``claim_count > 200``."""
    if "claim_count" in trigger:
        parts = trigger.split()
        if len(parts) == 3:
            _, op, threshold = parts
            count = len(claims)
            threshold_val = int(threshold)
            if op == ">":
                return count > threshold_val
            if op == ">=":
                return count >= threshold_val
            if op == "<":
                return count < threshold_val
    return False


def _policy_kind_to_role(kind: str) -> str:
    """Map an optional policy kind to the corresponding page_role."""
    mapping: dict[str, str] = {
        "topic_cluster": "comprehensive_guide",
        "per_module": "reference_object_page",
        "feature_showcase": "feature_showcase",
        "deep_dive": "feature_blog",
    }
    return mapping.get(kind, "workflow_page")


# ---------------------------------------------------------------------------
# 3b. Slug collision disambiguation
# ---------------------------------------------------------------------------


def _disambiguate_slugs(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Detect duplicate page_ids and append numeric suffixes to resolve them.

    When evidence-aware slug derivation produces the same slug for multiple
    pages, the first occurrence keeps its slug unchanged and subsequent
    duplicates receive ``-2``, ``-3``, etc.
    """
    seen: dict[str, int] = {}
    for page in pages:
        pid = page["page_id"]
        if pid in seen:
            seen[pid] += 1
            suffix = seen[pid]
            old_slug = page["slug"]
            new_slug = f"{old_slug}-{suffix}"
            new_pid = _generate_page_id(page["section"], new_slug)
            logger.debug(
                "Disambiguated slug collision: %s -> %s", pid, new_pid,
            )
            page["page_id"] = new_pid
            page["slug"] = new_slug
            if page.get("content_path") and old_slug in page["content_path"]:
                page["content_path"] = page["content_path"].replace(
                    old_slug, new_slug, 1,
                )
        else:
            seen[pid] = 1
    return pages


# ---------------------------------------------------------------------------
# 3c. Slug quality gate (TC-3820)
# ---------------------------------------------------------------------------


def _quality_check_slugs(
    pages: list[dict[str, Any]],
    product: ProductIdentity,
) -> list[dict[str, Any]]:
    """Reject nonsensical/garbled slugs and replace with structured alternatives.

    Runs ``validate_slug_quality()`` on each page's slug. When quality
    issues are found, attempts to reconstruct via ``extract_slug_core()``
    or falls back to a pattern based on page_role + family keyword.
    """
    family = product.family
    family_kw = extract_family_keyword(family)

    for page in pages:
        slug = page.get("slug", "")
        if not slug or slug == "_index":
            continue

        issues = validate_slug_quality(slug, family)
        if not issues:
            continue

        page_role = page.get("page_role", "")
        section = page.get("section", "")
        old_slug = slug

        # Attempt structured reconstruction from topic_category or page_role
        # (NOT from the bad slug -- that would be circular, SR-02)
        topic_text = page.get("topic_category", "") or page_role.replace("_", " ")
        core = extract_slug_core(topic_text, family, product.platform)

        if core:
            safety = validate_slug_safety(core)
            quality = validate_slug_quality(core, family)
            if not safety and not quality:
                slug = core
            else:
                slug = _slug_fallback(page_role, section, family_kw, product.platform)
        else:
            slug = _slug_fallback(page_role, section, family_kw, product.platform)

        if slug != old_slug:
            logger.debug(
                "Quality gate replaced slug: %s -> %s (issues: %s)",
                old_slug, slug, "; ".join(issues),
            )
            page["slug"] = slug
            page["page_id"] = _generate_page_id(section, slug)
            if page.get("content_path") and old_slug in page["content_path"]:
                page["content_path"] = page["content_path"].replace(
                    old_slug, slug, 1,
                )

    return pages


def _slug_fallback(
    page_role: str, section: str, family_kw: str, platform: str,
) -> str:
    """Generate a structured fallback slug based on page role and section."""
    if page_role == "feature_blog":
        return f"{family_kw}-features-{platform}"
    if page_role == "blog_announcement":
        return f"introducing-{family_kw}-{platform}"
    if section == "kb" and "howto" in page_role:
        return f"{page_role.replace('_', '-')}-{family_kw}-{platform}"
    if page_role in ("feature_showcase", "deep_dive", "topic_cluster"):
        return f"{page_role.replace('_', '-')}-{family_kw}"
    return f"{section}-{family_kw}-{platform}" if section else f"{family_kw}-{platform}"


# ---------------------------------------------------------------------------
# 4. Skeleton assignment
# ---------------------------------------------------------------------------


def _assign_skeletons(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Look up variant-aware skeleton for each page and set the skeleton field."""
    from launcher.shared.page_skeletons import SKELETON_VARIANTS, resolve_skeleton, resolve_topic_tag

    for page in pages:
        role = page["page_role"]
        # Honour pre-set skeleton_variant only if registered for this role
        preset_variant = page.get("skeleton_variant")
        if preset_variant and preset_variant != "default" and (role, preset_variant) in SKELETON_VARIANTS:
            topic_tag = preset_variant
        else:
            topic_tag = resolve_topic_tag(
                role,
                topic_category=page.get("topic_category"),
                slug=page.get("slug", ""),
            )
        skeleton_sections = resolve_skeleton(role, topic_tag)
        page["skeleton"] = [s.heading for s in skeleton_sections]
        page["skeleton_variant"] = topic_tag
        if topic_tag != "default":
            logger.info(
                "Variant skeleton: page_id=%s role=%s variant=%s headings=%s",
                page["page_id"], role, topic_tag,
                [s.heading for s in skeleton_sections],
            )
    return pages


# ---------------------------------------------------------------------------
# 5. Claim assignment
# ---------------------------------------------------------------------------


def _filter_claims_by_tier(
    claims: list[Claim], richness: RichnessResult,
) -> list[Claim]:
    """Filter claims by tier relevance and visibility."""
    resolved_tier = _TIER_MAP[richness.tier]
    allowed_relevance = _TIER_INCLUDES[resolved_tier]

    filtered: list[Claim] = []
    for claim in claims:
        # Exclude internal claims
        if claim.visibility == "internal":
            continue
        # Filter by tier_relevance
        rel = claim.tier_relevance
        if rel == "all":
            filtered.append(claim)
        elif rel == "core+" and resolved_tier in ("core", "full"):
            filtered.append(claim)
        elif rel == "full" and resolved_tier == "full":
            filtered.append(claim)
        elif rel in allowed_relevance:
            filtered.append(claim)
    return filtered


def _assign_claims(
    pages: list[dict[str, Any]],
    claims: list[Claim],
    snippets: list[Snippet],
    *,
    product_name: str = "",
    keyword_bundle: Any = None,
    richness_tier: str = "A",
    code_evidence_sparse: bool = False,  # TR-01: propagated from RichnessResult
) -> tuple[list[PlannedPage], dict[str, list[str]]]:
    """Assign claims to pages with exclusive partitioning.

    Each claim appears on at most ``_MAX_CLAIM_PAGES`` pages.
    Mandatory pages receive claims first, then optional pages.

    TC-3876: Computes ``claim_saturation`` (assigned_claims / skeleton_sections)
    and propagates ``richness_tier`` to every ``PlannedPage``.

    Returns
    -------
    tuple of (PlannedPage list, claim_assignment_index)
    """
    # Build snippet lookup: claim_id -> list of snippet indices
    snippet_index: dict[str, list[int]] = defaultdict(list)
    for idx, snip in enumerate(snippets):
        for cid in snip.claim_ids:
            snippet_index[cid].append(idx)

    # Track how many pages each claim has been assigned to
    claim_usage: dict[str, int] = defaultdict(int)

    # Sort pages: mandatory first, then optional (stable sort preserves order)
    sorted_pages = sorted(pages, key=lambda p: (not p["mandatory"],))

    # Build per-page claim lists
    page_claims: dict[str, list[str]] = {}
    page_snippets: dict[str, list[int]] = {}
    claim_assignment_index: dict[str, list[str]] = defaultdict(list)

    for page in sorted_pages:
        page_id = page["page_id"]
        role = page["page_role"]
        page_claims[page_id] = []
        page_snippets[page_id] = []

        if role in _NO_CLAIM_ROLES:
            continue

        # Find eligible claim kinds for this role
        eligible_kinds: set[str] = set()
        for kind, roles in _KIND_TO_ROLES.items():
            if role in roles:
                eligible_kinds.add(kind)

        # For per_module pages with a target_class, prioritize claims that
        # mention the class so the page gets the most relevant content first.
        target_class = page.get("target_class", "")
        if target_class and len(target_class) >= _MIN_CLASS_NAME_LEN:
            _tc_pat = re.compile(rf"\b{re.escape(target_class)}\b")
            ordered_claims = sorted(
                claims,
                key=lambda c: (0 if _tc_pat.search(c.text) else 1),
            )
        else:
            ordered_claims = claims

        # TC-4031: pre-compute topic-category keyword filter for this page
        _page_topic = page.get("topic_category")
        _topic_words: set[str] | None = _TOPIC_KEYWORDS.get(_page_topic) if _page_topic else None

        # Assign eligible claims that haven't exhausted their budget
        assigned_snippet_ids: set[int] = set()
        _topic_filtered_count = 0  # TC-4055: tracks eligible claims blocked by topic filter
        for claim in ordered_claims:
            # Per-page cap: stop when this page has enough claims
            if len(page_claims[page_id]) >= _MAX_CLAIMS_PER_PAGE:
                break
            if claim.visibility == "internal":
                continue
            if claim_usage[claim.claim_id] >= _MAX_CLAIM_PAGES:
                continue
            if claim.kind in eligible_kinds or not eligible_kinds:
                # TC-4031: topic filter — skip claims that don't match topic keywords
                if _topic_words and not any(w in claim.text.lower() for w in _topic_words):
                    _topic_filtered_count += 1
                    continue
                page_claims[page_id].append(claim.claim_id)
                claim_usage[claim.claim_id] += 1
                claim_assignment_index[claim.claim_id].append(page_id)

                # Assign associated snippets
                for snip_idx in snippet_index.get(claim.claim_id, []):
                    if snip_idx not in assigned_snippet_ids:
                        page_snippets[page_id].append(snip_idx)
                        assigned_snippet_ids.add(snip_idx)

        # TC-4055: Topic filter starvation guard — if the keyword filter produced 0 claims
        # AND eligible claims were blocked by the topic filter (not by eligible_kinds),
        # relax to eligible_kinds only and retry.
        if _topic_words and not page_claims[page_id] and _topic_filtered_count > 0:
            logger.warning(
                "[Planner] topic_filter_starvation slug=%s topic=%s candidates=%d — "
                "relaxing to eligible_kinds only",
                page.get("slug", page_id), _page_topic, len(ordered_claims),
            )
            page["_topic_filter_relaxed"] = True
            for claim in ordered_claims:
                if len(page_claims[page_id]) >= _MAX_CLAIMS_PER_PAGE:
                    break
                if claim.visibility == "internal":
                    continue
                if claim_usage[claim.claim_id] >= _MAX_CLAIM_PAGES:
                    continue
                if claim.kind in eligible_kinds or not eligible_kinds:
                    page_claims[page_id].append(claim.claim_id)
                    claim_usage[claim.claim_id] += 1
                    claim_assignment_index[claim.claim_id].append(page_id)
                    for snip_idx in snippet_index.get(claim.claim_id, []):
                        if snip_idx not in assigned_snippet_ids:
                            page_snippets[page_id].append(snip_idx)
                            assigned_snippet_ids.add(snip_idx)

    # Build claim lookup for evidence-aware titles
    claim_by_id: dict[str, Claim] = {c.claim_id: c for c in claims}

    # TC-4231: Apply relevance filter to each page's assigned claims.
    # This re-ranks and caps claims by keyword overlap with page slug/title,
    # ensuring the most relevant claims surface first when the cap is hit.
    for page in sorted_pages:
        pid = page["page_id"]
        raw_ids = page_claims.get(pid, [])
        if not raw_ids:
            continue
        filtered_ids = _apply_relevance_filter(
            raw_ids,
            claim_by_id,
            page_slug=page.get("slug", pid),
            page_title=page.get("title", ""),
            max_claims=_MAX_RELEVANCE_CLAIMS_PER_PAGE,
        )
        if len(filtered_ids) < len(raw_ids):
            logger.info(
                "claim_relevance_filter [TC-4231]: page=%s reduced claims %d -> %d",
                pid, len(raw_ids), len(filtered_ids),
            )
        page_claims[pid] = filtered_ids

    # Build PlannedPage objects
    result_pages: list[PlannedPage] = []
    for page in sorted_pages:
        pid = page["page_id"]
        assigned = page_claims.get(pid, [])
        title = _generate_evidence_aware_title(
            page["slug"], page["page_role"], assigned, claim_by_id,
            product_name=product_name,
            topic_category=page.get("topic_category", ""),
        )
        seo = _generate_seo_keywords(
            title, product_name,
            slug=page["slug"],
            keyword_bundle=keyword_bundle,
        )

        assigned = page_claims.get(pid, [])
        skeleton = page.get("skeleton", [])
        # TC-3876: Compute claim saturation (assigned claims / skeleton sections).
        # Saturations <0.5 indicate thin pages where SATURATION WARNING is injected.
        saturation = len(assigned) / max(1, len(skeleton)) if skeleton else 1.0

        planned = PlannedPage(
            page_id=pid,
            page_role=page["page_role"],
            title=title,
            skeleton=skeleton,
            skeleton_variant=page.get("skeleton_variant", "default"),
            assigned_claims=assigned,
            assigned_snippets=page_snippets.get(pid, []),
            frontmatter={},
            content_path=page.get("content_path", ""),
            seo_keywords=seo,
            mandatory=page["mandatory"],
            target_class=page.get("target_class", ""),
            claim_saturation=saturation,
            richness_tier=richness_tier,
            code_evidence_sparse=code_evidence_sparse,  # TR-01
        )
        result_pages.append(planned)

    return result_pages, dict(claim_assignment_index)


# ---------------------------------------------------------------------------
# 5c. TC-4218: Post-title deduplication and validation
# ---------------------------------------------------------------------------


def _dedup_and_validate_titles(
    pages: list[PlannedPage],
    *,
    product_name: str = "",
) -> list[PlannedPage]:
    """Deduplicate page titles and validate each one.

    Run AFTER pruning so that only surviving pages are considered.

    Algorithm:
    1. Count title occurrences across all pages.
    2. For pages sharing a title, append a slug-derived suffix using em-dash.
       If the suffixed titles still collide (same slug last segment),
       use the full slug path instead.
    3. Validate every title via ``_validate_title``.

    TC-4218: three title collisions exist in the 3d Python plan.json.

    ``PlannedPage`` is a frozen Pydantic model; we use ``model_copy(update=…)``
    to produce new objects with updated titles.
    """
    def _slug_from_page(page: PlannedPage) -> str:
        """Extract the slug portion from page_id (format: section/slug)."""
        return page.page_id.rsplit("/", 1)[-1]

    # First pass: append slug-derived suffix to duplicated titles.
    title_counts = Counter(p.title for p in pages)
    result: list[PlannedPage] = []
    for page in pages:
        if title_counts[page.title] > 1:
            raw_slug = _slug_from_page(page)
            suffix = raw_slug.replace("-", " ").replace("_", " ").title()
            # Remove trailing platform words from suffix too
            for platform_word in _PLATFORM_SUFFIX_WORDS:
                clean_word = platform_word.strip()
                if suffix.endswith(clean_word):
                    suffix = suffix[: -len(clean_word)]
            new_title = f"{page.title} \u2014 {suffix.strip()}"
            page = page.model_copy(update={"title": new_title})
        result.append(page)

    # Second pass: if suffix-based dedup still collides, use full page_id path.
    title_counts_after = Counter(p.title for p in result)
    result2: list[PlannedPage] = []
    for page in result:
        if title_counts_after[page.title] > 1:
            full_suffix = page.page_id.replace("/", " ").replace("-", " ").title()
            page = page.model_copy(update={"title": full_suffix})
        result2.append(page)

    # Third pass: validate every title.
    result3: list[PlannedPage] = []
    for page in result2:
        slug_hint = _slug_from_page(page)
        clean_title = _validate_title(page.title, slug=slug_hint, product_name=product_name)
        if clean_title != page.title:
            page = page.model_copy(update={"title": clean_title})
        result3.append(page)

    return result3


# ---------------------------------------------------------------------------
# 6. Frontmatter construction
# ---------------------------------------------------------------------------
# 5b. Density-based page pruning (TC-3817)
# ---------------------------------------------------------------------------

# Roles that are always kept regardless of content density.
_ALWAYS_KEEP_ROLES: frozenset[str] = frozenset({
    "install", "getting-started", "api-overview", "landing", "toc",
    "overview", "introduction", "installation",
    "reference_object_page",  # claim-gated in _expand_per_module, already quality-filtered
})

_MIN_PAGES = 8
_MAX_TOTAL_PAGES = 20  # hard cap on total pages regardless of claim count
_MAX_PAGES_PER_CLAIM_RATIO = 8  # soft cap: unique_claims / this value


def _prune_thin_pages(
    pages: list[PlannedPage],
    claim_index: dict[str, list[str]],
    snippets: list,
) -> tuple[list[PlannedPage], dict[str, list[str]]]:
    """Prune optional pages to match content budget.

    Uses two strategies:
    1. Page budget: total pages capped at unique_claims / 10 (min 8)
    2. Density: within budget, prefer pages with more exclusive claims

    Mandatory structural pages are always kept.
    Ensures at least _MIN_PAGES remain after pruning.
    """
    # Count unique claims across all pages
    all_claims: set[str] = set()
    for page in pages:
        all_claims.update(page.assigned_claims)

    # Page budget: content-proportional cap with hard maximum
    page_budget = min(
        _MAX_TOTAL_PAGES,
        max(_MIN_PAGES, len(all_claims) // _MAX_PAGES_PER_CLAIM_RATIO),
    )

    # Build snippet linkage: claim_id → snippet count
    snippet_claims: dict[str, int] = {}
    for s in snippets:
        for cid in getattr(s, "claim_ids", []):
            snippet_claims[cid] = snippet_claims.get(cid, 0) + 1

    # Count how many pages each claim appears on (exclusivity)
    claim_page_count: dict[str, int] = {}
    for page in pages:
        for cid in page.assigned_claims:
            claim_page_count[cid] = claim_page_count.get(cid, 0) + 1

    keep: list[PlannedPage] = []
    candidates: list[tuple[float, PlannedPage]] = []

    for page in pages:
        if page.mandatory or page.page_role in _ALWAYS_KEEP_ROLES:
            keep.append(page)
            continue

        # Density = exclusive claims (claims only on this page) + snippet bonus
        exclusive_claims = sum(
            1 for cid in page.assigned_claims
            if claim_page_count.get(cid, 0) <= 2
        )
        linked_snippets = sum(
            snippet_claims.get(cid, 0) for cid in page.assigned_claims
        )
        density = exclusive_claims + 0.5 * linked_snippets
        candidates.append((density, page))

    # Sort candidates by density (highest first) and fill up to budget
    candidates.sort(key=lambda x: x[0], reverse=True)
    while candidates and len(keep) < page_budget:
        _, page = candidates.pop(0)
        keep.append(page)

    pruned_count = len(pages) - len(keep)
    if pruned_count > 0:
        kept_ids = {p.page_id for p in keep}
        # Per-page pruning log for observability (AQ-06)
        for density_val, page in candidates:
            logger.info(
                "density_pruning: page=%s role=%s density=%.1f -> pruned",
                page.page_id, page.page_role, density_val,
            )
        # Clean up claim_index: remove references to pruned pages
        new_index: dict[str, list[str]] = {}
        for cid, pids in claim_index.items():
            filtered = [pid for pid in pids if pid in kept_ids]
            if filtered:
                new_index[cid] = filtered
        claim_index = new_index
        logger.info(
            "density_pruning: budget=%d removed=%d kept=%d (from %d unique claims)",
            page_budget, pruned_count, len(keep), len(all_claims),
        )

    return keep, claim_index


# ---------------------------------------------------------------------------


def _build_frontmatter(
    pages: list[PlannedPage],
    product: ProductIdentity,
) -> list[PlannedPage]:
    """Build Hugo frontmatter for each page."""
    result: list[PlannedPage] = []
    for weight, page in enumerate(pages, start=1):
        # Derive slug from content_path (last segment) or page_id
        if page.content_path:
            slug = page.content_path.rsplit("/", 1)[-1]
            url = f"/{page.content_path}/"
        else:
            slug = page.page_id.split("/", 1)[-1] if "/" in page.page_id else page.page_id
            url = _build_url(page.page_id)

        # Robots directive: deterministic from role/slug.
        # _index slug is always noindex (Hugo structural page); all other roles
        # use _ROBOTS_BY_ROLE lookup, defaulting to _ROBOTS_SAFE_DEFAULT for unknown roles.
        robots = (
            "noindex, follow"
            if slug == "_index"
            else _ROBOTS_BY_ROLE.get(page.page_role, _ROBOTS_SAFE_DEFAULT)
        )

        code_import = product.runtime_import or product.canonical_import

        fm: dict[str, Any] = {
            "title": page.title,
            "description": f"{page.title} for {product.display_name}",
            "slug": slug,
            "type": page.page_role,
            "url": url,
            "weight": weight,
            "family": product.family,
            "platform": product.platform,
            "display_name": product.display_name,
            "canonical_import": code_import,
            "page_role": page.page_role,
            "robots": robots,
        }

        # Rebuild with updated frontmatter (frozen model)
        updated = PlannedPage(
            page_id=page.page_id,
            page_role=page.page_role,
            title=page.title,
            skeleton=page.skeleton,
            skeleton_variant=page.skeleton_variant,
            assigned_claims=page.assigned_claims,
            assigned_snippets=page.assigned_snippets,
            frontmatter=fm,
            content_path=page.content_path,
            seo_keywords=page.seo_keywords,
            mandatory=page.mandatory,
            target_class=page.target_class,
        )
        result.append(updated)
    return result


def _refine_page_slugs(
    pages: list[PlannedPage],
    llm_client: Any = None,
    *,
    gemini_client: Any = None,
    product: ProductIdentity | None = None,
) -> list[PlannedPage]:
    """Refine page slugs via Gemini (preferred) or LLM batch call.

    When *gemini_client* is provided and available, uses
    ``gemini_client.refine_slugs()`` for slug refinement. Falls back to
    ``refine_slugs_batch(slugs, llm_client)`` when Gemini is unavailable.

    Updates only the frontmatter ``slug`` field; ``page_id`` and
    ``content_path`` remain unchanged.
    """
    slugs: list[str] = []
    indices: list[int] = []
    for i, page in enumerate(pages):
        fm_slug = page.frontmatter.get("slug", "")
        if page.page_role not in _NO_CLAIM_ROLES and fm_slug and fm_slug != "_index":
            slugs.append(fm_slug)
            indices.append(i)

    if not slugs:
        return pages

    # Gemini-first slug refinement
    refined: list[str] | None = None
    if gemini_client is not None and getattr(gemini_client, "available", False):
        try:
            family = product.family if product else ""
            platform = product.platform if product else ""
            refined = gemini_client.refine_slugs(slugs, family, platform)
            if refined and len(refined) != len(slugs):
                logger.debug("Gemini slug refinement returned wrong count, falling back")
                refined = None
        except Exception:
            logger.debug("Gemini slug refinement failed, falling back", exc_info=True)
            refined = None

    if refined is None:
        refined = refine_slugs_batch(slugs, llm_client)
    result = list(pages)
    for idx, new_slug in zip(indices, refined):
        page = result[idx]
        old_slug = page.frontmatter.get("slug", "")
        if new_slug and new_slug != old_slug:
            safety_issues = validate_slug_safety(new_slug)
            if safety_issues:
                logger.debug(
                    "Rejected unsafe LLM-refined slug %r (was %r): %s",
                    new_slug, old_slug, "; ".join(safety_issues),
                )
                continue
            fm = dict(page.frontmatter)
            fm["slug"] = new_slug
            if fm.get("url") and old_slug in fm["url"]:
                # Replace only the last path segment to avoid corrupting
                # earlier segments that may coincidentally match.
                url = fm["url"]
                last_sep = url.rfind("/", 0, url.rfind("/") if url.endswith("/") else len(url))
                if last_sep >= 0:
                    fm["url"] = url[:last_sep + 1] + url[last_sep + 1:].replace(old_slug, new_slug, 1)
                else:
                    fm["url"] = url.replace(old_slug, new_slug, 1)
            result[idx] = PlannedPage(
                page_id=page.page_id,
                page_role=page.page_role,
                title=page.title,
                skeleton=page.skeleton,
                skeleton_variant=page.skeleton_variant,
                assigned_claims=page.assigned_claims,
                assigned_snippets=page.assigned_snippets,
                frontmatter=fm,
                content_path=page.content_path,
                seo_keywords=page.seo_keywords,
                mandatory=page.mandatory,
                target_class=page.target_class,
            )
    return result


def _build_url(page_id: str) -> str:
    """Build a Hugo-compatible URL path from a page_id."""
    # page_id format: "section/slug" -> "/section/slug/"
    return f"/{page_id}/"


# ---------------------------------------------------------------------------
# TC-4250: Evidence gate
# ---------------------------------------------------------------------------


def _apply_evidence_gate(
    pages: list[PlannedPage],
    page_evidence_index: "dict | None",
) -> list[PlannedPage]:
    """Filter non-mandatory pages whose evidence score is insufficient.

    TC-4250: When ``page_evidence_index`` is provided (non-empty), any
    non-mandatory page whose role maps to a score with
    ``evidence_sufficient=False`` is excluded from the plan.  Mandatory pages
    are never removed — a warning is emitted instead.

    The index is keyed by ``page_role``.  Values may be any object that
    exposes an ``evidence_sufficient`` attribute (``PageEvidenceScore`` from
    TC-4249 or any ``SimpleNamespace``-compatible duck-type).

    Parameters
    ----------
    pages:
        The list of ``PlannedPage`` objects to filter (after claim assignment
        and density pruning).
    page_evidence_index:
        Mapping of ``page_role -> score`` object.  ``None`` or empty dict
        causes no-op (all pages kept).

    Returns
    -------
    list[PlannedPage]
        Filtered list (may be the same object if nothing was removed).
    """
    if not page_evidence_index:
        return pages

    pre_filter = len(pages)
    filtered: list[PlannedPage] = []
    for page in pages:
        role = page.page_role
        is_mandatory = page.mandatory
        score = page_evidence_index.get(role)
        if score is not None and not getattr(score, "evidence_sufficient", True):
            if not is_mandatory:
                logger.info(
                    "page_evidence_gate: skipping non-mandatory role=%s slug=%s missing=%s",
                    role, getattr(page, "slug", page.page_id), getattr(score, "missing", []),
                )
                continue
            else:
                logger.warning(
                    "page_evidence_gate: mandatory page role=%s has insufficient evidence: %s",
                    role, getattr(score, "missing", []),
                )
        filtered.append(page)

    removed = pre_filter - len(filtered)
    if removed > 0:
        logger.info("page_evidence_gate: removed %d non-mandatory pages", removed)
    return filtered


# ---------------------------------------------------------------------------
# 7. Validation
# ---------------------------------------------------------------------------


def _validate_plan(pages: list[PlannedPage], claims: list[Claim]) -> None:
    """Self-review: verify plan integrity.

    Checks:
    - Each content page has at least ``_MIN_CLAIMS_CONTENT_PAGE`` claims.
    - No permalink collisions.
    - Titles are meaningful (not empty, not template placeholders).
    """
    seen_urls: dict[str, str] = {}
    warnings = 0

    for page in pages:
        # Skip structural pages (toc) for claim-count checks
        if page.page_role not in _NO_CLAIM_ROLES and page.mandatory:
            if len(page.assigned_claims) < _MIN_CLAIMS_CONTENT_PAGE:
                logger.warning(
                    "Page %s (%s) has only %d claims (minimum %d)",
                    page.page_id, page.page_role,
                    len(page.assigned_claims), _MIN_CLAIMS_CONTENT_PAGE,
                )
                warnings += 1

        # Permalink collision check
        url = page.frontmatter.get("url", "")
        if url in seen_urls:
            logger.error(
                "Permalink collision: %s used by both %s and %s",
                url, seen_urls[url], page.page_id,
            )
        seen_urls[url] = page.page_id

        # Title sanity
        if not page.title or page.title.startswith("{"):
            logger.warning(
                "Page %s has a problematic title: %r",
                page.page_id, page.title,
            )
            warnings += 1

    # TC-4218: Title uniqueness assertion — duplicates are a publication blocker.
    title_counts = Counter(p.title for p in pages)
    duplicate_titles = [t for t, c in title_counts.items() if c > 1]
    if duplicate_titles:
        logger.error(
            "[TC-4218] HIGH — duplicate page titles detected after dedup pass: %s",
            duplicate_titles,
        )
        warnings += len(duplicate_titles)

    if warnings:
        logger.warning("Plan validation completed with %d warnings", warnings)
    else:
        logger.info("Plan validation passed: %d pages, 0 warnings", len(pages))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _generate_page_id(section: str, slug: str) -> str:
    """Deterministic page_id from section + slug.

    Format: ``{section}/{slug}`` which is also the Hugo content path.
    """
    return f"{section}/{slug}"


def _generate_title(slug: str, page_role: str) -> str:
    """Generate a human-readable title from a slug.

    Converts ``how-to-open-a-file`` -> ``How to Open a File``.
    Handles ``_index`` slugs by using the page_role as basis.
    """
    if slug == "_index":
        # Title for index pages based on role
        role_titles: dict[str, str] = {
            "landing": "Overview",
            "toc": "Table of Contents",
        }
        return role_titles.get(page_role, page_role.replace("_", " ").title())

    # Convert slug to title: replace hyphens, title-case
    words = slug.replace("-", " ").split()
    # Title case but keep small words lowercase (except first/last)
    small_words = {"a", "an", "the", "and", "but", "or", "for", "in", "on", "to", "of"}
    titled: list[str] = []
    for i, word in enumerate(words):
        if i == 0 or i == len(words) - 1 or word.lower() not in small_words:
            titled.append(word.capitalize())
        else:
            titled.append(word.lower())
    return " ".join(titled)


# TC-4031 Wave 2D: topic_category → human label for title formulas.
_TOPIC_LABELS: dict[str, str] = {
    "load_file": "Load Files",
    "save_file": "Save Files",
    "convert_formats": "Convert File Formats",
    "formula_calculation": "Work with Formulas",
    "spreadsheet_ops": "Spreadsheet Operations",
    "troubleshoot": "Fix Common Errors",
    "optimize_performance": "Optimize Performance",
    "notebook_ops": "Manage Notebooks",
    "document_editing": "Edit Documents",
    "mail_merge": "Perform Mail Merge",
    "pdf_ops": "Work with PDFs",
    "form_filling": "Fill Forms",
    "presentation_ops": "Create Presentations",
    "slide_ops": "Work with Slides",
    "rendering": "Render 3D Models",
    "model_loading": "Load 3D Models",
}

# Role-only title templates (no topic_category required).
_ROLE_TITLE_TEMPLATES: dict[str, str] = {
    "getting_started": "Getting Started with {product}",
    "faq": "{product} FAQ",
    "landing": "{product}",
    "api_reference": "{product} API Reference",
    "comprehensive_guide": "{product} Developer Guide",
    "best_practices": "{product} Best Practices",
}


_PLATFORM_SUFFIX_WORDS = (" Python", " Java", " Csharp", " Dotnet", " Node", " Net")


def _title_from_slug(slug: str) -> str:
    """Derive a human-readable title from a URL slug.

    Takes the last path segment, replaces hyphens/underscores with spaces,
    title-cases the result, and removes trailing platform/language suffixes.

    Examples
    --------
    >>> _title_from_slug("how-to-load-3d-models-python")
    'How To Load 3D Models'
    >>> _title_from_slug("docs/api/save-file")
    'Save File'
    """
    segment = slug.rsplit("/", 1)[-1]
    readable = segment.replace("-", " ").replace("_", " ").title()
    for suffix in _PLATFORM_SUFFIX_WORDS:
        if readable.endswith(suffix):
            readable = readable[: -len(suffix)]
    return readable.strip()


def _validate_title(title: str, slug: str = "", product_name: str = "") -> str:
    """Validate and sanitise a generated page title.

    Rules (applied in order):
    1. Strip trailing colon and surrounding whitespace.
    2. If title contains "demonstrating" (case-insensitive), derive from slug
       instead — description fragments must never appear as titles.
    3. If title length < 10 characters after cleaning, derive from slug.

    Returns
    -------
    str
        A corrected, publication-ready title.
    """
    # Rule 1: strip trailing colon
    title = title.rstrip(": \t")

    # Rule 2: reject description fragments containing "demonstrating"
    if "demonstrating" in title.lower():
        fallback = _title_from_slug(slug) if slug else title
        if product_name:
            return f"How to {fallback} with {product_name}"
        return fallback

    # Rule 3: minimum length
    if len(title) < 10:
        fallback = _title_from_slug(slug) if slug else title
        if fallback and len(fallback) >= 10:
            return fallback
        # If slug-derived is also too short, return whatever we have
        return title if title else fallback

    return title


def _generate_evidence_aware_title(
    slug: str,
    page_role: str,
    assigned_claim_ids: list[str],
    claim_by_id: dict[str, Claim],
    *,
    product_name: str = "",
    topic_category: str = "",
) -> str:
    """Generate a title using claim evidence when available.

    Falls back to slug-based title if no claims are assigned.
    Uses the top claim's text to derive a more meaningful title
    for optional/generated pages.

    TC-4031 Wave 2D: When product_name and topic_category are provided,
    uses deterministic role+topic formula for cleaner, consistent titles.
    """
    # TC-4031 Wave 2D: deterministic role+topic formula.
    if product_name and topic_category and topic_category in _TOPIC_LABELS:
        topic_label = _TOPIC_LABELS[topic_category]
        if page_role == "howto_article":
            return f"How to {topic_label} with {product_name}"
        if page_role in ("workflow_page", "tutorial"):
            return f"{topic_label} with {product_name}"

    # TC-4218: howto_article slug-derived fallback — never use description text.
    # When topic_category is missing or not in _TOPIC_LABELS, derive from slug.
    if page_role == "howto_article":
        readable = _title_from_slug(slug)
        if product_name:
            return f"How to {readable} with {product_name}"
        return f"How to {readable}"

    # Deterministic role-only formulas.
    if product_name and page_role in _ROLE_TITLE_TEMPLATES:
        return _ROLE_TITLE_TEMPLATES[page_role].format(product=product_name)

    base_title = _generate_title(slug, page_role)

    # Don't override structural pages or pages with explicit slugs
    if page_role in _NO_CLAIM_ROLES or slug == "_index":
        return base_title

    # Don't override titles derived from meaningful slugs (mandatory pages)
    # — slugs like "installation", "getting-started", "faq" already produce
    # good titles; overriding them with claim text makes them generic.
    _WELL_KNOWN_SLUGS = {
        "installation", "getting-started", "faq", "troubleshooting",
        "api-overview", "use-cases",
    }
    if slug in _WELL_KNOWN_SLUGS:
        return base_title

    # For pages with assigned claims, try to derive a better title
    if not assigned_claim_ids:
        return base_title

    # Use the first assigned claim to inform the title
    first_claim = claim_by_id.get(assigned_claim_ids[0])
    if not first_claim or len(first_claim.text) < 15:
        return base_title

    # Extract a concise title from the claim text (first sentence, capped)
    claim_text = first_claim.text.strip()
    # Take first sentence
    for sep in (".", "!", "?", ";"):
        idx = claim_text.find(sep)
        if idx > 0:
            claim_text = claim_text[:idx]
            break

    # Cap at 80 chars
    if len(claim_text) > 80:
        claim_text = claim_text[:77] + "..."

    # Title-case the result
    words = claim_text.split()
    if len(words) < 3:
        return base_title

    return " ".join(w.capitalize() if i == 0 else w for i, w in enumerate(words))


def _generate_seo_keywords(
    title: str,
    product_name: str,
    slug: str = "",
    keyword_bundle: Any = None,
) -> list[str]:
    """Generate 5-8 SEO keywords from research bundle + title + product.

    Priority:
    1. Per-page keywords from research bundle (if slug matches)
    2. Primary keywords from research bundle
    3. Family keyword from FAMILY_KEYWORD_MAP
    4. Significant words from title
    5. Product name
    Deduplicated, capped at 8.
    """
    seen: set[str] = set()
    keywords: list[str] = []

    def _add(kw: str) -> None:
        key = kw.lower().strip()
        if key and key not in seen:
            seen.add(key)
            keywords.append(kw.strip())

    # 1. Per-page keywords from research bundle.
    if keyword_bundle is not None:
        per_page = getattr(keyword_bundle, "per_page", {}) or {}
        if slug and slug in per_page:
            for kw in per_page[slug]:
                _add(kw)
        # 2. Primary keywords from research bundle.
        for kw in getattr(keyword_bundle, "primary_keywords", []) or []:
            _add(kw)

    # 3. Family keyword.
    # (imported at module level)
    family_kw = extract_family_keyword(
        product_name.split()[0].lower() if product_name else "",
    )
    if family_kw != "files":
        _add(family_kw)

    # 4. Product name.
    if product_name:
        _add(product_name.lower())

    # 5. Title-derived.
    if title and title.lower() not in ("overview", "table of contents"):
        _add(title.lower())
        words = title.lower().replace("-", " ").split()
        for w in words:
            if w not in SEO_STOP_WORDS and len(w) > 2:
                _add(w)

    return keywords[:8]
