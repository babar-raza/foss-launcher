"""Deterministic repo profiling from repo_inventory data.

No LLM, no network. Pure deterministic computation.
Produces repo_profile.json artifact.

Schema version: 2.0 (TC-2448)
"""
from __future__ import annotations
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SOURCE_TYPE_WEIGHTS: Dict[str, float] = {
    "readme": 0.6,
    "api_doc": 0.9,
    "example": 0.85,
    "changelog": 0.7,
    "test": 0.8,
    "generic_doc": 0.5,
    "unknown": 0.3,
}

# Extensions that indicate code (not domain-specific binary assets)
_CODE_EXTENSIONS = frozenset([
    ".py", ".cs", ".java", ".ts", ".js", ".jsx", ".tsx",
    ".go", ".rs", ".cpp", ".c", ".h", ".hpp", ".rb", ".php",
    ".swift", ".kt", ".scala", ".r",
])

# Extensions that indicate documentation / config (not domain-specific assets)
_DOC_EXTENSIONS = frozenset([
    ".md", ".markdown", ".rst", ".txt", ".html", ".htm",
    ".xml", ".json", ".yaml", ".yml", ".toml", ".ini",
    ".cfg", ".conf", ".properties",
])

# Extensions that are common image/web assets (not domain-specific)
_WEB_EXTENSIONS = frozenset([
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico",
    ".css", ".scss", ".less",
])

# Known CI/CD paths (has_ci detection)
_CI_PATHS = frozenset([
    ".travis.yml", ".travis.yaml",
    "Jenkinsfile",
    ".circleci/config.yml",
    "appveyor.yml", ".appveyor.yml",
    "azure-pipelines.yml",
])

# Known manifest filenames (build_signals)
_MANIFEST_NAMES = frozenset([
    "pyproject.toml", "setup.py", "setup.cfg", "requirements.txt",
    "package.json", "package-lock.json", "pom.xml", "build.gradle",
    "Makefile", "CMakeLists.txt", "Cargo.toml", "go.mod",
    "composer.json", "Gemfile", "build.sbt",
])


def compute_docs_depth(doc_paths: List[str], example_paths: List[str]) -> int:
    """Total documentation + example file count as depth signal."""
    return len(doc_paths) + len(example_paths)


def compute_api_surface(paths: List[str]) -> int:
    """Count non-test source files in known API languages."""
    api_extensions = {".py", ".cs", ".java", ".ts", ".go", ".rs"}
    test_markers = {"test", "spec", "mock", "fixture"}
    count = 0
    for p in paths:
        pp = Path(p)
        if pp.suffix in api_extensions:
            if not any(m in pp.stem.lower() for m in test_markers):
                count += 1
    return count


def _infer_source_type(path: str) -> str:
    p = path.lower()
    if "readme" in p:
        return "readme"
    if "example" in p or "sample" in p:
        return "example"
    if "test" in p or "spec" in p:
        return "test"
    if "changelog" in p or "history" in p:
        return "changelog"
    return "generic_doc"


def score_citation_quality(
    citations: List[Any],
    source_weights: Dict[str, float],
) -> float:
    """Compute [0,1] quality score for a claim's citations. Returns max weight."""
    if not citations:
        return 0.0
    scores = []
    for cit in citations:
        if isinstance(cit, dict):
            src_type = cit.get("source_type", "unknown")
        else:
            src_type = _infer_source_type(str(cit))
        scores.append(source_weights.get(src_type, 0.3))
    return max(scores) if scores else 0.0


# ---------------------------------------------------------------------------
# TC-2448: New signal helpers (all pure, all deterministic)
# ---------------------------------------------------------------------------

def _compute_docs_signals(
    paths: List[str],
    doc_entrypoints: List[str],
    doc_details: List[Dict[str, Any]],
    docs_depth: int,
) -> Dict[str, Any]:
    """Compute docs-related signals from repo paths and doc metadata."""
    path_set_lower = {p.lower() for p in paths}
    # README detection — any path whose last component starts with "readme"
    has_readme = any(
        Path(p).name.lower().startswith("readme")
        for p in paths
    )
    # README size from doc_entrypoint_details
    readme_size_bytes = 0
    for detail in doc_details:
        detail_path = detail.get("path", "")
        if Path(detail_path).name.lower().startswith("readme"):
            readme_size_bytes = max(readme_size_bytes, detail.get("file_size_bytes", 0))
    # Docs folder presence
    has_docs_folder = any(
        p.startswith("docs/") or "/docs/" in p
        for p in paths
    )
    # Markdown file count
    markdown_file_count = sum(
        1 for p in paths if p.lower().endswith(".md") or p.lower().endswith(".markdown")
    )
    return {
        "has_readme": has_readme,
        "readme_size_bytes": readme_size_bytes,
        "has_docs_folder": has_docs_folder,
        "markdown_file_count": markdown_file_count,
        "docs_depth_score": docs_depth,
    }


def _compute_examples_signals(
    paths: List[str],
    example_paths: List[str],
) -> Dict[str, Any]:
    """Compute example-related signals from repo paths."""
    has_examples_folder = any(
        p.startswith("examples/") or p.startswith("samples/")
        or "/examples/" in p or "/samples/" in p
        for p in paths
    )
    # Code extensions in example_paths
    code_exts = sorted({
        Path(p).suffix.lower()
        for p in example_paths
        if Path(p).suffix
    })
    return {
        "has_examples_folder": has_examples_folder,
        "example_file_count": len(example_paths),
        "code_extensions": code_exts,
    }


def _compute_api_signals(
    paths: List[str],
    api_surface: int,
) -> Dict[str, Any]:
    """Compute API-related signals from repo paths."""
    has_api_docs_folder = any(
        p.startswith("api/") or "/api/" in p
        or "/apidocs/" in p or "/api_docs/" in p
        for p in paths
    )
    has_type_stubs = any(p.endswith(".pyi") for p in paths)
    openapi_patterns = (
        "openapi.yaml", "openapi.yml", "openapi.json",
        "swagger.yaml", "swagger.yml", "swagger.json",
    )
    has_openapi_spec = any(
        Path(p).name.lower() in openapi_patterns
        for p in paths
    )
    return {
        "has_api_docs_folder": has_api_docs_folder,
        "has_type_stubs": has_type_stubs,
        "has_openapi_spec": has_openapi_spec,
        "api_surface_count": api_surface,
    }


def _compute_build_signals(
    paths: List[str],
    build_systems: List[str],
) -> Dict[str, Any]:
    """Compute build system signals from repo paths."""
    path_filenames = {Path(p).name for p in paths}
    detected_manifests = sorted(path_filenames & _MANIFEST_NAMES)
    # CI detection
    has_ci = any(
        p.startswith(".github/workflows/")
        or Path(p).name in _CI_PATHS
        or p in _CI_PATHS
        for p in paths
    )
    return {
        "build_systems": build_systems,
        "detected_manifests": detected_manifests,
        "has_ci": has_ci,
    }


def _compute_formats_signals(paths: List[str]) -> Dict[str, Any]:
    """Compute domain-specific file format signals from repo paths."""
    _skip = _CODE_EXTENSIONS | _DOC_EXTENSIONS | _WEB_EXTENSIONS | {""}
    domain_exts: Dict[str, int] = {}
    for p in paths:
        ext = Path(p).suffix.lower()
        if ext and ext not in _skip:
            domain_exts[ext] = domain_exts.get(ext, 0) + 1
    binary_asset_count = sum(domain_exts.values())
    return {
        "binary_asset_count": binary_asset_count,
        "domain_extensions": sorted(domain_exts.keys()),
    }


def _compute_language_breakdown(paths: List[str]) -> Dict[str, int]:
    """Count files by extension (top 15, sorted by count desc then ext asc)."""
    counter: Counter = Counter()
    for p in paths:
        ext = Path(p).suffix.lower().lstrip(".")
        if ext:
            counter[ext] += 1
    # Top 15 entries, then sort deterministically: count desc, ext asc
    top = sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))[:15]
    return dict(top)


def _compute_confidence_and_warnings(
    paths: List[str],
    doc_entrypoints: List[str],
    example_paths: List[str],
) -> Tuple[float, List[str]]:
    """Compute confidence score and coverage warnings."""
    warnings: List[str] = []
    confidence = 0.8  # baseline for repos with good data

    if not paths:
        confidence = 0.1
        warnings.append("no_paths")
        return round(confidence, 4), sorted(warnings)

    # Check for README
    has_readme = any(Path(p).name.lower().startswith("readme") for p in paths)
    if not has_readme:
        confidence -= 0.15
        warnings.append("no_readme")

    if not doc_entrypoints:
        confidence -= 0.15
        warnings.append("no_docs")

    if not example_paths:
        warnings.append("no_examples")

    return round(max(0.0, min(1.0, confidence)), 4), sorted(warnings)


# ---------------------------------------------------------------------------
# Main builder
# ---------------------------------------------------------------------------

def build_repo_profile_artifact(
    repo_inventory: Dict[str, Any],
) -> Dict[str, Any]:
    """Compute repo_profile.json from repo_inventory data.

    Deterministic: two identical calls return identical results.
    Schema version 2.0 (TC-2448): adds signal sub-objects.
    Backward compatible: all v1.0 top-level keys preserved.
    """
    paths = repo_inventory.get("paths", [])
    doc_paths = repo_inventory.get("doc_entrypoints", [])
    example_paths = repo_inventory.get("example_paths", [])
    doc_details = repo_inventory.get("doc_entrypoint_details", [])

    docs_depth = compute_docs_depth(doc_paths, example_paths)
    examples_count = len(example_paths)
    api_surface = compute_api_surface(paths)

    repo_profile_data = repo_inventory.get("repo_profile", {})
    primary_languages = sorted(repo_profile_data.get("primary_languages", []))
    build_systems = sorted(repo_profile_data.get("build_systems", []))

    # Quality tier heuristic (unchanged from v1.0)
    if docs_depth > 50 and examples_count > 10:
        quality_tier = "rich"
    elif docs_depth > 10 or examples_count > 3:
        quality_tier = "standard"
    else:
        quality_tier = "minimal"

    # TC-2448: New signal sub-objects
    docs_signals = _compute_docs_signals(paths, doc_paths, doc_details, docs_depth)
    examples_signals = _compute_examples_signals(paths, example_paths)
    api_signals = _compute_api_signals(paths, api_surface)
    build_signals = _compute_build_signals(paths, build_systems)
    formats_signals = _compute_formats_signals(paths)
    language_breakdown = _compute_language_breakdown(paths)
    confidence, warnings = _compute_confidence_and_warnings(paths, doc_paths, example_paths)

    return {
        # --- v1.0 top-level keys (preserved for backward compat) ---
        "schema_version": "2.0",
        "docs_depth": docs_depth,
        "examples_count": examples_count,
        "api_surface": api_surface,
        "languages": primary_languages,
        "build_systems": build_systems,
        "quality_tier": quality_tier,
        "source_type_weights": SOURCE_TYPE_WEIGHTS,
        # --- TC-2448 additions ---
        "language_breakdown": language_breakdown,
        "confidence": confidence,
        "warnings": warnings,
        "docs_signals": docs_signals,
        "examples_signals": examples_signals,
        "api_signals": api_signals,
        "build_signals": build_signals,
        "formats_signals": formats_signals,
    }
