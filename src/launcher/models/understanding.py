from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from launcher.models.base import LauncherBaseModel
from launcher.models.claims import Claim, Snippet
from launcher.models.plan import PlannedPage  # re-export for backwards compat  # noqa: F401
from launcher.models.product import ApiSurface, ProductIdentity, RichnessResult
from launcher.shared.keyword_research import KeywordResearchBundle


class FileCategory(str, Enum):
    """Classification of a repository file by role."""

    source = "source"
    doc = "doc"
    config = "config"
    test = "test"
    example = "example"
    ci = "ci"
    asset = "asset"


class FileEntry(LauncherBaseModel):
    """Lightweight metadata for a single repository file."""

    category: FileCategory
    size_bytes: int
    language: str = ""


class SharedFacts(LauncherBaseModel):
    """Deterministic facts extracted from repository metadata."""

    package_name: str = ""
    version: str = ""
    install_command: str = ""
    license_type: str = ""
    primary_language: str = ""
    build_systems: list[str] = Field(default_factory=list)
    has_tests: bool = False
    has_ci: bool = False
    has_docs_folder: bool = False
    has_examples_folder: bool = False
    module_path: str = ""


class RepoInfo(LauncherBaseModel):
    """Structural summary of the source repository."""

    file_tree: list[str] = Field(default_factory=list)
    file_index: dict[str, FileEntry] = Field(default_factory=dict)
    doc_paths: list[str] = Field(default_factory=list)
    example_paths: list[str] = Field(default_factory=list)
    source_paths: list[str] = Field(default_factory=list)
    test_paths: list[str] = Field(default_factory=list)
    config_paths: list[str] = Field(default_factory=list)
    readme_summary: str = ""
    shared_facts: SharedFacts = Field(default_factory=SharedFacts)
    content_budget_used: int = 0
    content_files_read: int = 0


class InstallRecipe(LauncherBaseModel):
    """Deterministically extracted install instructions for a product.

    Populated from pyproject.toml, setup.cfg, setup.py, or requirements.txt.
    Injected into generation context so install/getting-started pages use the
    real command rather than LLM guesses.
    """

    pip_command: str = Field(default="", description="e.g. 'pip install aspose-3d-foss'")
    package_name: str = Field(default="", description="e.g. 'aspose-3d-foss'")
    version_constraint: str = Field(default="", description="e.g. '>=1.0.0' or ''")
    verification_code: str = Field(default="", description="e.g. 'import aspose.threed\\nprint(\"ok\")'")
    source_file: str = Field(default="", description="which config file provided this (pyproject.toml, setup.cfg, setup.py, requirements.txt, or derived)")


class LimitationEntry(LauncherBaseModel):
    """A verified limitation extracted from source code or documentation.

    Used by the contradiction resolver to downgrade claims that conflict
    with known limitations, and by downstream generators to disclose
    limitations proactively.
    """

    feature: str = Field(description="e.g. 'OBJ export', 'async API'")
    constraint: str = Field(description="e.g. 'not supported', 'experimental'")
    status: str = Field(default="warning", description="warning | experimental | unsupported | deprecated")
    source_file: str = Field(default="", description="relative path where limitation was found")
    source_line: int = Field(default=0)
    confidence: str = Field(default="heuristic", description="ast_verified | heuristic | doc_stated")
    context: str = Field(default="", description="surrounding text for evidence")
    quote: str = Field(default="", description="original line from source")


class WorkflowExample(LauncherBaseModel):
    """A real workflow pattern extracted from test or example files.

    Provides runnable code sequences that demonstrate actual API usage,
    used by generators for tutorial and how-to pages.
    """

    name: str = Field(description="e.g. 'convert_fbx_to_gltf'")
    title: str = Field(default="", description="e.g. 'Load OBJ and iterate nodes'")
    code: str = Field(default="", description="full runnable code block")
    steps: list[str] = Field(default_factory=list, description="ordered API call names")
    language: str = Field(default="python")
    source_file: str = Field(default="")
    source_lines: tuple[int, int] = Field(default=(0, 0))
    input_format: str = Field(default="")
    output_format: str = Field(default="")


class MissingInfoEntry(LauncherBaseModel):
    """Explicit record of information that could not be extracted.

    TC-4005: Distinguishes 'no formats exist' from 'extraction failed'.
    """

    field: str                      # e.g. "format_matrix", "install_recipe"
    reason: str                     # e.g. "no tree-sitter grammar for Rust"
    attempted_strategies: list[str] = Field(default_factory=list)
    fallback_used: str = ""         # e.g. "regex", "llm_inferred"


class FieldConfidence(LauncherBaseModel):
    """Per-field confidence annotation for evidence provenance.

    TC-4005: Tracks how each field was populated.
    """

    source: str    # "ast_verified" | "heuristic" | "llm_inferred" | "absent"
    detail: str = ""  # optional: which file/line provided this


class ProductEvidence(LauncherBaseModel):
    """Structured product evidence extracted from repository-wide analysis.

    Populated by Phase B.5 of the Understand worker using
    ``code_analyzer.build_repo_truth()``.  All fields have defaults
    so the bundle remains backward-compatible when evidence extraction
    is skipped or fails.
    """

    supported_formats: list[str] = Field(default_factory=list)
    input_formats: list[str] = Field(default_factory=list)
    output_formats: list[str] = Field(default_factory=list)
    conversion_pairs: list[dict[str, str]] = Field(default_factory=list)
    workflows: list[dict[str, Any]] = Field(default_factory=list)
    capabilities: list[dict[str, Any]] = Field(default_factory=list)
    limitations: list[LimitationEntry] = Field(default_factory=list, description="TC-4002: verified negative capabilities")
    workflow_examples: list[WorkflowExample] = Field(default_factory=list, description="TC-4002: real test-extracted workflows")
    install_recipe: "InstallRecipe | None" = Field(default=None, description="TC-HYBRID-04: deterministically extracted pip install recipe")  # TC-HYBRID-04
    missing_info: list[MissingInfoEntry] = Field(default_factory=list, description="TC-4005: fields that could not be extracted")
    confidence: dict[str, FieldConfidence] = Field(default_factory=dict, description="TC-4005: per-field confidence annotations")


class UnderstandingBundle(LauncherBaseModel):
    """Complete output of the Understand worker."""

    product: ProductIdentity
    repo: RepoInfo
    richness_tier: RichnessResult
    api_surface: ApiSurface
    claims: list[Claim] = Field(default_factory=list)
    snippets: list[Snippet] = Field(default_factory=list)
    product_evidence: ProductEvidence = Field(default_factory=ProductEvidence)
    keyword_research: KeywordResearchBundle = Field(default_factory=KeywordResearchBundle)
