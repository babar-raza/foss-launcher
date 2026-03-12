"""Deterministic evaluation checks (Phase A)."""
from __future__ import annotations

from .api_verification import check_api_identifiers  # TC-HYBRID-05
from .artifacts import check_artifacts
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
from .structure import check_structure, check_golden_spec_from_markdown
from .readability import check_readability, check_readability_from_markdown
from .route_consistency import check_route_consistency  # TC-4037

__all__ = [
    "check_api_identifiers",
    "check_artifacts",
    "check_claim_coverage",
    "check_contradiction",
    "check_format_truth",
    "check_claim_leakage",
    "check_code",
    "check_density",
    "check_frontmatter",
    "check_golden_spec_from_markdown",
    "check_install_recipe",
    "check_limitations_contradiction",
    "check_product_names",
    "check_readability",
    "check_readability_from_markdown",
    "check_reference_completeness",
    "check_repetition",
    "check_route_consistency",
    "check_safety",
    "check_semantic_structure",
    "check_seo",
    "check_spec_leakage",
    "check_structure",
]
