from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

from .base import LauncherBaseModel


class RichnessTier(str, Enum):
    """API surface richness classification."""

    A = "A"
    B = "B"
    C = "C"


class RichnessResult(LauncherBaseModel):
    """Result of richness classification for a repository."""

    tier: RichnessTier
    score: int
    reason: str
    code_evidence_sparse: bool = False
    """True when example_files + extracted_snippets < _CODE_EVIDENCE_SPARSE_THRESHOLD.

    Orthogonal to richness tier — a Tier B repo can be code-evidence-sparse if it
    has docs + tests + CI but zero executable examples (e.g. 3D TypeScript).
    Computed by :func:`~launcher.shared.surface_classifier.classify_richness_with_surface`.
    Defaults to ``False`` so existing :func:`classify_richness` callers are unaffected.
    """


class MethodParam(LauncherBaseModel):
    """A single method parameter with optional type annotation."""

    name: str
    type_annotation: str = ""   # e.g. "str", "int", "Vector3"


class MethodSignature(LauncherBaseModel):
    """Typed method signature extracted from source AST."""

    name: str
    parameters: list[MethodParam] = Field(default_factory=list)
    return_type: str = ""       # e.g. "bool", "None", "Scene"
    is_static: bool = False
    is_async: bool = False
    docstring_snippet: str = ""


class PropertyRecord(LauncherBaseModel):
    """Typed property extracted from source AST."""

    name: str
    type_annotation: str = ""  # e.g. "str", "bool"
    is_readonly: bool = False
    docstring_snippet: str = ""


class EnumMember(LauncherBaseModel):
    """A single enum member with exact source casing."""

    name: str                  # exact casing from source
    value: str = ""


class EnumRecord(LauncherBaseModel):
    """An enum class extracted from source."""

    name: str
    members: list[EnumMember] = Field(default_factory=list)
    docstring_snippet: str = ""


class FormatRecord(LauncherBaseModel):
    """A single file format with import/export capability from source evidence.

    Populated deterministically from test files and README format tables.
    Used by the contradiction gate (TC-HYBRID-06) to verify generated format claims.
    """

    name: str              # display name, e.g. "OBJ", "FBX", "GLTF"
    extension: str = ""    # file extension, e.g. ".obj", ".fbx"
    can_import: bool = False
    can_export: bool = False
    caveats: list[str] = Field(default_factory=list)
    test_count: int = 0    # number of test file references to this format
    source_evidence: str = ""  # "file:line" of extraction source


class ClassBrief(LauncherBaseModel):
    """Compact summary of a public class for prompt injection."""

    name: str
    docstring_snippet: str = ""
    methods: list[str] = Field(default_factory=list)
    properties: list[str] = Field(default_factory=list)
    # Typed members — populated when AST extraction succeeds (TC-HYBRID-02)
    typed_methods: list[MethodSignature] = Field(default_factory=list)
    typed_properties: list[PropertyRecord] = Field(default_factory=list)
    enums: list[EnumRecord] = Field(default_factory=list)


class ApiSurface(LauncherBaseModel):
    """Extracted API surface of a product repository."""

    public_classes: list[str]
    import_allowlist: list[str]
    confidence: Literal["high", "medium", "low"]
    api_identifiers: list[str] = Field(default_factory=list)
    class_briefs: list[ClassBrief] = Field(default_factory=list)
    enums: list[EnumRecord] = Field(default_factory=list)  # top-level enums (TC-HYBRID-02)
    format_matrix: list[FormatRecord] = Field(default_factory=list)  # TC-HYBRID-03


class RepoProfile(LauncherBaseModel):
    """Detailed repo profiling signals for evidence scoring and planning."""

    docs_depth: int = 0
    examples_count: int = 0
    api_surface_count: int = 0
    has_readme: bool = False
    readme_size_bytes: int = 0
    has_docs_folder: bool = False
    has_examples_folder: bool = False
    has_ci: bool = False
    has_tests: bool = False
    has_type_stubs: bool = False
    markdown_file_count: int = 0
    primary_language: str = ""
    build_systems: list[str] = Field(default_factory=list)
    language_breakdown: dict[str, int] = Field(default_factory=dict)
    confidence: float = 0.8
    warnings: list[str] = Field(default_factory=list)


class PlatformProfile(LauncherBaseModel):
    """Config-driven platform metadata resolved from families.yaml.

    Replaces hardcoded platform dicts scattered across extraction code.
    Adding a new platform = one entry in families.yaml + one adapter class.
    """

    platform: str              # "python", "dotnet", "java", "node", "typescript"
    lang_tag: str              # "python", "csharp", "java", "javascript", "typescript"
    import_tpl: str            # template for package name
    install_cmd: str           # template for install command
    runtime_import_tpl: str = ""
    runtime_import_overrides: dict[str, str] = Field(default_factory=dict)
    file_ext: str = ".py"
    doc_comment: str = "docstring"  # docstring/jsdoc/xmldoc/doxygen/javadoc
    ast_parser: str = "python_ast"  # python_ast/tree_sitter/regex
    import_stmt_tpl: str = ""       # "from {import_path} import {class}"
    # Resolved (not templated):
    package_name: str = ""     # "aspose-3d-foss" (resolved for specific family)
    import_path: str = ""      # "aspose.threed" (resolved for specific family)
    install_command: str = ""  # "pip install aspose-3d-foss" (resolved)


class ProductIdentity(LauncherBaseModel):
    """Canonical identity of a product within a family."""

    family: str
    platform: str
    display_name: str
    canonical_import: str
    runtime_import: str = ""
    """Python runtime module import path (e.g. ``'aspose.threed'`` for the 3D family).

    Separate from ``canonical_import`` which holds the pip package name
    (``aspose_3d_foss``).  Used for code generation and import validation.
    Only populated for Python platform — empty string for TypeScript/Java/.NET.
    Falls back to ``canonical_import`` when empty.
    """
    platform_profile: PlatformProfile | None = None
    repo_url: str
    repo_sha: str = ""
