from __future__ import annotations

from enum import Enum
from typing import Any, Literal

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
    # TC-4030: richer pyproject.toml fields cached to avoid re-parsing downstream
    description: str = ""
    python_requires: str = ""
    dependencies: list[str] = Field(default_factory=list)
    entrypoints: list[str] = Field(default_factory=list)


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
    skipped_paths: list[str] = Field(
        default_factory=list,
        description=(
            "TC-4056: Paths that were not read because the budget was exhausted "
            "(reason: budget_exceeded, doc_cap_reached, source_reserve, or "
            "file_too_large_for_remaining_budget). Does NOT include files that were "
            "truncated (per_file_cap) — those ARE in repo_content, just shortened. "
            "Populated by Scout so downstream workers know what was missed."
        ),
    )
    important_files_skipped: int = Field(
        default=0,
        description=(
            "TC-4236: Count of files with importance rank >= 4 (TC-4234 base + size bonus) "
            "that were skipped due to budget exhaustion (reason: budget_exceeded or "
            "file_too_large_for_remaining_budget). Non-zero indicates quality loss; "
            "ScoutWorker self-review emits a medium-severity warning."
        ),
    )


class InstallRecipe(LauncherBaseModel):
    """Deterministically extracted install instructions for a product.

    Populated from pyproject.toml, setup.cfg, setup.py, requirements.txt,
    package.json, go.mod, Cargo.toml, *.csproj, Gemfile, or composer.json.
    Injected into generation context so install/getting-started pages use the
    real command rather than LLM guesses.

    TC-4084: Field renamed from pip_command → install_command to remove Python bias.
    Supports multi-platform install commands (pip, npm, go get, cargo, dotnet, gem, composer).
    """

    install_command: str = Field(
        default="",
        description="Install command, e.g. 'pip install aspose-3d-foss' or 'npm install @aspose/cells'",
    )
    package_name: str = Field(default="", description="e.g. 'aspose-3d-foss' or '@aspose/cells'")
    version_constraint: str = Field(default="", description="e.g. '>=1.0.0' or ''")
    verification_code: str = Field(default="", description="e.g. 'import aspose.threed\\nprint(\"ok\")'")
    source_file: str = Field(default="", description="which config file provided this (pyproject.toml, package.json, go.mod, Cargo.toml, *.csproj, or derived)")

    # TC-4084: pip_command kept as backward-compat property for serialized artifacts
    # and callers that have not yet been updated. Remove when all callers are updated.
    @property
    def pip_command(self) -> str:
        """Backward-compat alias for install_command (TC-4084). Use install_command instead."""
        return self.install_command


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
    format_evidence_source: Literal["ast_verified", "heuristic", "absent"] = Field(
        default="heuristic",
        description=(
            "TC-4061/PH-02: How format lists (supported_formats, input_formats, output_formats) "
            "were populated. 'ast_verified' = extracted from source AST and verified; "
            "'heuristic' = regex/pattern matching with uncertain coverage; "
            "'absent' = no formats found in the repository."
        ),
    )


# ── TC-4242: ExtractionDatabase — structured, fact-based evidence ─────────────

class ApiFact(LauncherBaseModel):
    """A single verified API member fact extracted by AST/tree-sitter analysis."""

    fact_id: str = ""                   # "AF-{family}-{platform}-{class}.{member}-{hash6}"
    class_name: str = ""                # "Workbook"
    member_name: str = ""               # "save"
    member_type: Literal["method", "property", "enum_member", "class"] = "method"
    signature: str = ""                 # "def save(self, path: str, format: SaveFormat) -> None"
    docstring: str = ""                 # full docstring text
    return_type: str = ""
    parameters: list[dict[str, str]] = Field(default_factory=list)  # [{"name": "path", "type": "str", "default": ""}]
    is_static: bool = False
    is_readonly: bool = False           # for properties
    source_file: str = ""
    source_line: int = 0
    confidence: float = 1.0            # 1.0 AST-extracted, 0.9 heuristic


class FormatFact(LauncherBaseModel):
    """A single verified format support fact."""

    fact_id: str = ""                   # "FF-{family}-{platform}-{format_name}"
    format_name: str = ""               # "XLSX"
    extension: str = ""                 # ".xlsx"
    can_import: bool = False
    can_export: bool = False
    confidence: float = 1.0            # 1.0 enum, 0.9 docstring, 0.8 test, 0.7 readme, 0.6 heuristic
    evidence_source: str = ""          # "enum_declaration|method_signature|readme_table|test_file|extension_pattern"
    source_file: str = ""


class SnippetFact(LauncherBaseModel):
    """A code snippet with operation classification."""

    fact_id: str = ""                   # "SF-{family}-{platform}-{operation}-{hash6}"
    code: str = ""
    language: str = "python"
    operation_label: str = ""          # "load_file|save_file|convert|create|modify|query"
    input_format: str = ""
    output_format: str = ""
    demonstrates_class: str = ""       # primary API class used
    demonstrates_methods: list[str] = Field(default_factory=list)
    source_file: str = ""
    source_lines: tuple[int, int] = (0, 0)
    syntax_valid: bool = True
    confidence: float = 1.0           # 1.0 test file, 0.9 example file, 0.7 readme block


class LimitationFact(LauncherBaseModel):
    """A verified limitation or constraint."""

    fact_id: str = ""
    feature: str = ""
    constraint: str = ""
    status: str = "warning"           # warning|experimental|unsupported|deprecated
    source_file: str = ""
    source_line: int = 0
    confidence: float = 0.8           # 1.0 ast_verified, 0.8 doc_stated, 0.5 heuristic


class ExtractionCompleteness(LauncherBaseModel):
    """Measures how complete and reliable the extracted evidence is."""

    api_class_count: int = 0
    api_method_count: int = 0
    api_confidence: str = "low"       # "high|medium|low"
    format_count: int = 0
    format_confidence_avg: float = 0.0
    snippet_count: int = 0
    operation_coverage: list[str] = Field(default_factory=list)  # which operation types have snippets
    limitation_count: int = 0
    missing_signals: list[str] = Field(default_factory=list)  # "no_formats|thin_api|no_snippets|no_docstrings"
    overall_completeness: float = 0.0  # 0.0-1.0 evidence-quality score


class ExtractionDatabase(LauncherBaseModel):
    """Complete structured evidence extracted deterministically from the repository.

    This is the foundation for LLM-as-describer mode (TC-4242). The LLM receives
    this database and describes the verified facts rather than discovering new ones.
    """

    api_facts: list[ApiFact] = Field(default_factory=list)
    format_facts: list[FormatFact] = Field(default_factory=list)
    snippet_facts: list[SnippetFact] = Field(default_factory=list)
    limitation_facts: list[LimitationFact] = Field(default_factory=list)
    install_recipe: InstallRecipe | None = None
    missing_coverage: list[MissingInfoEntry] = Field(default_factory=list)
    completeness: ExtractionCompleteness = Field(default_factory=ExtractionCompleteness)


class PageEvidenceScore(LauncherBaseModel):
    """Evidence sufficiency score for a single page role.

    TC-4249: Computed by the Understand worker after claim/snippet assembly.
    Consumed by the Planner (TC-4250) to skip or downgrade pages with thin evidence.
    """
    page_role: str = ""
    claim_count: int = 0
    verified_claim_count: int = 0       # claims with confidence >= 0.80
    snippet_count: int = 0
    has_operation_snippets: bool = False # at least one load/save/convert snippet
    format_evidence_complete: bool = False  # format_facts present (for format pages)
    evidence_sufficient: bool = False
    missing: list[str] = []             # "no_verified_claims"|"no_snippets"|"no_format_evidence"


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
    extraction_db: ExtractionDatabase = Field(
        default_factory=ExtractionDatabase,
        description=(
            "TC-4242: Structured facts extracted deterministically from the repository. "
            "Empty until upstream extraction produces it. Foundation for LLM-as-describer mode."
        ),
    )
    page_evidence_index: dict[str, PageEvidenceScore] = Field(
        default_factory=dict,
        description=(
            "TC-4249: Per-page-role evidence sufficiency scores. "
            "Computed after claim/snippet assembly. Consumed by Planner to skip thin-evidence pages."
        ),
    )
