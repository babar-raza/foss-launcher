"""TC-T-01: Fact manifest model — formal contract for engineering-verified facts.

Each page role has a set of required facts (install command, import path,
format list, etc.) that must appear verbatim in generated content. The
FactManifest tracks which facts are available and their verification status.
"""
from __future__ import annotations

from typing import Literal

from pydantic import Field

from .base import LauncherBaseModel


class FactEntry(LauncherBaseModel):
    """A single engineering-verified fact to inject into generated content."""

    fact_type: str  # e.g. "install_command", "canonical_import", "format_list"
    expected_content: str  # The exact text that must appear
    source: str = ""  # Where this fact came from (e.g. "knowledge/cells/python/install.md")
    match_pattern: str = ""  # Regex pattern to verify presence (optional)
    required: bool = True  # Whether this fact is mandatory


class RoleFactSpec(LauncherBaseModel):
    """Maps a page role to its required and optional facts."""

    role: str  # page_role name
    required_facts: list[str] = Field(default_factory=list)  # fact_type names that MUST appear
    optional_facts: list[str] = Field(default_factory=list)  # fact_type names that SHOULD appear


class FactVerificationResult(LauncherBaseModel):
    """Result of verifying a single fact against generated content."""

    fact_type: str
    status: Literal["present", "missing", "wrong", "not_applicable"] = "missing"
    expected: str = ""
    found: str = ""


class FactManifest(LauncherBaseModel):
    """Collection of facts available for a product/platform, with verification results."""

    family: str
    platform: str
    facts: list[FactEntry] = Field(default_factory=list)
    verification_results: list[FactVerificationResult] = Field(default_factory=list)

    def get_fact(self, fact_type: str) -> FactEntry | None:
        """Look up a fact by type."""
        for f in self.facts:
            if f.fact_type == fact_type:
                return f
        return None

    def get_required_facts_for_role(self, role: str) -> list[FactEntry]:
        """Return required facts for a given page role."""
        spec = FACT_REGISTRY.get(role)
        if not spec:
            return []
        return [f for f in self.facts if f.fact_type in spec.required_facts]


# ---------------------------------------------------------------------------
# FACT_REGISTRY: Maps all 17 page roles to required/optional fact types.
# ---------------------------------------------------------------------------

FACT_REGISTRY: dict[str, RoleFactSpec] = {
    "installation": RoleFactSpec(
        role="installation",
        required_facts=["install_command", "canonical_import"],
        optional_facts=["python_version", "system_requirements"],
    ),
    "getting_started": RoleFactSpec(
        role="getting_started",
        required_facts=["install_command", "canonical_import"],
        optional_facts=["verification_code"],
    ),
    "developer_guide": RoleFactSpec(
        role="developer_guide",
        required_facts=["canonical_import"],
        optional_facts=["format_list"],
    ),
    "howto_article": RoleFactSpec(
        role="howto_article",
        required_facts=["canonical_import"],
        optional_facts=["format_list"],
    ),
    "how_to_convert": RoleFactSpec(
        role="how_to_convert",
        required_facts=["canonical_import"],
        optional_facts=["format_list"],
    ),
    "faq": RoleFactSpec(
        role="faq",
        required_facts=[],
        optional_facts=["install_command", "format_list", "limitations"],
    ),
    "troubleshooting": RoleFactSpec(
        role="troubleshooting",
        required_facts=[],
        optional_facts=["install_command", "canonical_import"],
    ),
    "api_reference": RoleFactSpec(
        role="api_reference",
        required_facts=["canonical_import"],
        optional_facts=["api_surface"],
    ),
    "reference_object_page": RoleFactSpec(
        role="reference_object_page",
        required_facts=["canonical_import"],
        optional_facts=["api_surface"],
    ),
    "landing": RoleFactSpec(
        role="landing",
        required_facts=[],
        optional_facts=["install_command", "canonical_import", "format_list"],
    ),
    "blog_announcement": RoleFactSpec(
        role="blog_announcement",
        required_facts=["canonical_import"],
        optional_facts=["install_command", "format_list"],
    ),
    "feature_blog": RoleFactSpec(
        role="feature_blog",
        required_facts=["canonical_import"],
        optional_facts=[],
    ),
    "feature_overview": RoleFactSpec(
        role="feature_overview",
        required_facts=["canonical_import"],
        optional_facts=["format_list"],
    ),
    "toc": RoleFactSpec(
        role="toc",
        required_facts=[],
        optional_facts=[],
    ),
    "kb_index": RoleFactSpec(
        role="kb_index",
        required_facts=[],
        optional_facts=[],
    ),
    "workflow_page": RoleFactSpec(
        role="workflow_page",
        required_facts=["canonical_import"],
        optional_facts=[],
    ),
    "use_cases": RoleFactSpec(
        role="use_cases",
        required_facts=[],
        optional_facts=["canonical_import", "format_list"],
    ),
}
