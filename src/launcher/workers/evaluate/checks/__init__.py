"""Deterministic evaluation checks (Phase A)."""
from __future__ import annotations

from .api_allowlist import check_api_allowlist  # TC-REG-301
from .api_verification import check_api_identifiers  # TC-HYBRID-05
from .artifacts import check_artifacts, check_opener_boilerplate
from .contradiction import check_contradiction  # TC-HYBRID-06
from .format_truth import check_format_truth    # TC-HYBRID-06
from .claim_coverage import check_claim_coverage  # TC-3880 Wave 2 (E4)
from .claim_leakage import check_claim_leakage
from .code import check_code
from .density import check_density
from .frontmatter import check_frontmatter
from .install_recipe import check_install_recipe  # TC-HO-02
from .limitations import check_limitations_contradiction  # TC-HO-01
from .product_names import check_product_names
from .repetition import check_repetition
from .safety import check_safety
from .semantic_structure import check_semantic_structure
from .seo import check_seo
from .spec_leakage import check_spec_leakage
from .reference_completeness import check_reference_completeness
from .structure import (  # TC-EVAL-500: added section_order, terminal_section, duplicate_sections
    check_structure,
    check_golden_spec_from_markdown,
    check_section_order,
    check_terminal_section,
    check_duplicate_sections,
)
from .readability import check_readability, check_readability_from_markdown
from .route_consistency import check_route_consistency  # TC-4037
# --- TC-EVAL-500: Wire disconnected checks (Wave 1 — critical) ---
from .forbidden_content import check_forbidden_content
from .content_utility import check_content_utility
from .link_validity import check_link_validity
from .code_workflow import check_code_completeness_workflow
from .faq_structure import check_faq_structure
from .contract_compliance import check_contract_compliance
# --- TC-EVAL-500: Wire disconnected checks (Wave 2 — quality) ---
from .golden_conformance import check_golden_conformance
from .heading_echo import check_heading_echo
from .prose_lead import check_prose_lead
from .sentence_openings import check_sentence_openings
from .paragraph_monotony import check_paragraph_monotony
from .explanation_gap import check_explanation_gap
from .low_specificity import check_low_specificity
# --- TC-EVAL-500: hallucination_rate additional functions ---
from .hallucination_rate import check_content_grounding
# --- TC-EVAL-502: New checks ---
from .code_platform import check_code_platform, check_ecosystem_contamination  # TC-5329
from .unsourced_metrics import check_unsourced_metrics
from .content_viability import check_content_viability
from .extraction_quality import check_extraction_quality  # TC-5308

__all__ = [
    "check_api_allowlist",
    "check_api_identifiers",
    "check_artifacts",
    "check_opener_boilerplate",
    "check_claim_coverage",
    "check_code_completeness_workflow",
    "check_content_grounding",
    "check_content_utility",
    "check_contract_compliance",
    "check_contradiction",
    "check_density",
    "check_duplicate_sections",
    "check_explanation_gap",
    "check_faq_structure",
    "check_forbidden_content",
    "check_format_truth",
    "check_frontmatter",
    "check_golden_conformance",
    "check_golden_spec_from_markdown",
    "check_heading_echo",
    "check_install_recipe",
    "check_limitations_contradiction",
    "check_link_validity",
    "check_low_specificity",
    "check_claim_leakage",
    "check_code",
    "check_paragraph_monotony",
    "check_product_names",
    "check_prose_lead",
    "check_readability",
    "check_readability_from_markdown",
    "check_reference_completeness",
    "check_repetition",
    "check_route_consistency",
    "check_safety",
    "check_section_order",
    "check_semantic_structure",
    "check_sentence_openings",
    "check_seo",
    "check_spec_leakage",
    "check_structure",
    "check_terminal_section",
    "check_code_platform",
    "check_ecosystem_contamination",
    "check_unsourced_metrics",
    "check_content_viability",
    "check_extraction_quality",
]
