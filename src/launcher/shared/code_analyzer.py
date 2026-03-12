"""Code analysis module for W2 FactsBuilder.

Extracts structured information from source code using AST parsing (Python),
regex patterns (JavaScript/C#), and manifest parsing (pyproject.toml, package.json).

Outputs:
- api_surface: {classes: [], functions: [], modules: []}
- code_structure: {source_roots: [], public_entrypoints: [], package_names: []}
- constants: {version: str, supported_formats: [str]}
- positioning: {tagline: str, short_description: str}

Spec: specs/07_code_analysis_and_enrichment.md
"""

from __future__ import annotations

import ast
import json
import re
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # Fallback for Python 3.10
    except ImportError:
        tomllib = None

logger = logging.getLogger(__name__)


def _compute_import_path(file_path: Path, repo_dir: Path, source_roots: List[str]) -> str:
    """Compute the full dotted import path for a Python file.

    Walks up from *file_path* toward the nearest source root, building a
    dotted module path from each directory that contains an ``__init__.py``.

    Args:
        file_path: Absolute path to a ``.py`` file.
        repo_dir: Repository root directory.
        source_roots: Source root directories (e.g. ``["src/"]``).

    Returns:
        Dotted import path (e.g. ``"aspose.threed.scene"``).
        Falls back to ``file_path.stem`` when resolution fails.
    """
    resolved_roots: List[Path] = []
    for root_str in source_roots:
        candidate = (repo_dir / root_str.rstrip("/")).resolve()
        resolved_roots.append(candidate)
    if not resolved_roots:
        resolved_roots = [repo_dir.resolve()]

    resolved_file = file_path.resolve()

    best_root: Optional[Path] = None
    for root in resolved_roots:
        try:
            resolved_file.relative_to(root)
            if best_root is None or len(root.parts) > len(best_root.parts):
                best_root = root
        except ValueError:
            continue

    if best_root is None:
        return file_path.stem

    try:
        rel = resolved_file.relative_to(best_root)
    except ValueError:
        return file_path.stem

    parts = list(rel.parts)
    if parts and parts[-1].endswith(".py"):
        parts[-1] = parts[-1][:-3]
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    if not parts:
        return file_path.stem

    return ".".join(parts)


def _build_export_reachability(
    init_exports: Dict[str, List[str]],
    source_files: Optional[List[Path]],
    repo_dir: Path,
    source_roots: List[str],
) -> Tuple[Set[str], str]:
    """Build the set of symbols reachable from package root __init__.py.

    Determines which classification heuristic to use:
    1. If the ROOT ``__init__.py`` has ``__all__``, use that (high confidence).
    2. Otherwise, union all ``__init__.py`` exports (medium — underscore convention).

    Returns:
        ``(reachable_symbols, source_hint)`` where *source_hint* is
        ``"__all__"`` if root had ``__all__``, ``"underscore_convention"``
        if using fallback, or ``"none"`` if no init exports at all.
    """
    if not init_exports:
        return set(), "none"

    # Find the root package __init__.py (shortest import path)
    root_module = min(init_exports.keys(), key=lambda k: k.count("."))

    # Check if root used __all__ (Strategy 1 in _extract_modules_from_init)
    root_had_all = False
    if source_files:
        for fp in source_files:
            if fp.name == "__init__.py":
                imp_path = _compute_import_path(fp, repo_dir, source_roots)
                if imp_path == root_module:
                    try:
                        content = fp.read_text(encoding="utf-8")
                        tree = ast.parse(content)
                        for node in ast.walk(tree):
                            if isinstance(node, ast.Assign):
                                for target in node.targets:
                                    if (
                                        isinstance(target, ast.Name)
                                        and target.id == "__all__"
                                    ):
                                        root_had_all = True
                    except Exception:
                        pass
                    break

    if root_had_all:
        root_exports = init_exports.get(root_module, [])
        return set(root_exports), "__all__"

    # No __all__ at root: union all init exports as reachable set
    all_exports: Set[str] = set()
    for exports in init_exports.values():
        all_exports.update(exports)
    return all_exports, "underscore_convention"


# ---------------------------------------------------------------------------
# repo_truth.json: Deterministic ground-truth extraction
# ---------------------------------------------------------------------------

_LICENSE_PATTERNS: List[Tuple[str, str, str]] = [
    (r"MIT License", "MIT", "MIT License"),
    (r"Apache License[\s\S]{0,40}Version 2\.0", "Apache-2.0", "Apache License 2.0"),
    (r"GNU GENERAL PUBLIC LICENSE[\s\S]{0,40}Version 3", "GPL-3.0-only", "GNU GPL v3"),
    (r"GNU GENERAL PUBLIC LICENSE[\s\S]{0,40}Version 2", "GPL-2.0-only", "GNU GPL v2"),
    (r"BSD 3-Clause", "BSD-3-Clause", "BSD 3-Clause License"),
    (r"BSD 2-Clause", "BSD-2-Clause", "BSD 2-Clause License"),
    (r"Mozilla Public License[\s\S]{0,40}2\.0", "MPL-2.0", "Mozilla Public License 2.0"),
    (r"GNU LESSER GENERAL PUBLIC LICENSE", "LGPL-3.0-only", "GNU LGPL v3"),
    (r"The Unlicense", "Unlicense", "The Unlicense"),
    (r"ISC License", "ISC", "ISC License"),
]

_LICENSE_FILENAMES = ("LICENSE", "LICENSE.md", "LICENSE.txt", "LICENCE", "LICENCE.md", "COPYING")


def _parse_license_file(repo_dir: Path) -> Dict[str, str]:
    """Parse LICENSE/COPYING file to determine SPDX identifier.

    Scans the first 2000 characters of common license files for known patterns.
    Returns ``{spdx_id, name, source}`` where *source* describes the file found.
    """
    for name in _LICENSE_FILENAMES:
        license_path = repo_dir / name
        if license_path.exists():
            try:
                content = license_path.read_text(encoding="utf-8", errors="ignore")[:2000]
                for pattern, spdx_id, display_name in _LICENSE_PATTERNS:
                    if re.search(pattern, content, re.IGNORECASE):
                        return {
                            "spdx_id": spdx_id,
                            "name": display_name,
                            "source": f"LICENSE file ({name})",
                        }
                return {"spdx_id": "", "name": "", "source": f"LICENSE file ({name}) — unrecognized"}
            except Exception:
                pass
    return {"spdx_id": "", "name": "", "source": ""}


def _first_sentence(text: str, max_len: int = 120) -> str:
    """Extract the first sentence from a docstring, capped at max_len chars.

    Reusable helper extracted from _extract_capabilities inline logic.
    """
    if not text:
        return ""
    first_line = text.split("\n")[0].strip()
    dot_pos = first_line.find(". ")
    if dot_pos > 0:
        first_line = first_line[: dot_pos + 1]
    return first_line[:max_len]


def _extract_capabilities(
    repo_dir: Path,
    code_analysis: Dict[str, Any],
) -> List[Dict[str, str]]:
    """Extract capability statements from README features sections and class docstrings.

    Looks for ``## Features``, ``## Key Features``, or ``## Capabilities`` headings
    in README.md, then extracts bullet lines.  Also extracts the first sentence of
    docstrings from the top 10 classes in *code_analysis*.

    Args:
        repo_dir: Repository root directory.
        code_analysis: Result dict from :func:`analyze_repository_code`.

    Returns:
        List of ``{"text": str, "source": str}`` dicts (max 20, deduplicated).
    """
    capabilities: List[Dict[str, str]] = []
    seen_texts: Set[str] = set()

    def _add(text: str, source: str, evidence: Optional[Dict[str, Any]] = None) -> None:
        text = text.strip()
        if not text or text in seen_texts:
            return
        seen_texts.add(text)
        entry: Dict[str, Any] = {"text": text, "source": source}
        if evidence:
            entry["evidence"] = evidence  # file+line pointer
        capabilities.append(entry)

    # --- README features sections ---
    _FEATURE_HEADING_RE = re.compile(
        r"^#{2}\s+(?:key\s+)?(?:features|capabilities)\s*$",
        re.IGNORECASE,
    )
    readme_path: Optional[Path] = None
    try:
        for candidate in repo_dir.iterdir():
            if candidate.is_file() and candidate.name.lower() == "readme.md":
                readme_path = candidate
                break
    except Exception:
        pass

    if readme_path is not None:
        try:
            content = readme_path.read_text(encoding="utf-8", errors="ignore")
            lines = content.split("\n")
            in_section = False
            for line_idx, line in enumerate(lines, start=1):
                stripped = line.strip()
                if _FEATURE_HEADING_RE.match(stripped):
                    in_section = True
                    continue
                if in_section:
                    # Stop at next heading
                    if stripped.startswith("#"):
                        in_section = False
                        continue
                    # Extract bullet lines
                    if stripped.startswith("- ") or stripped.startswith("* "):
                        bullet_text = stripped[2:].strip()
                        if bullet_text:
                            try:
                                readme_rel = str(readme_path.relative_to(repo_dir)).replace("\\", "/")
                            except ValueError:
                                readme_rel = readme_path.name
                            _add(
                                bullet_text, "readme",
                                evidence={"file": readme_rel, "line": line_idx},  #
                            )
        except Exception:
            pass

    # --- Class docstrings (top 10 classes, first sentence) ---
    classes = code_analysis.get("api_surface", {}).get("classes", [])
    for cls in classes[:10]:
        if not isinstance(cls, dict):
            continue
        docstring = cls.get("docstring", "")
        if not docstring:
            continue
        # Use _first_sentence() helper (same logic, now reusable)
        first_sentence = _first_sentence(docstring)
        if first_sentence:
            cls_source = cls.get("source_file", "")
            cls_line = cls.get("start_line", 0)
            _add(
                first_sentence,
                f"docstring:{cls.get('name', '')}",
                evidence={"file": cls_source, "line": cls_line} if cls_source else None,  #
            )

    return capabilities[:20]


def _extract_workflows(
    repo_dir: Path,
    code_analysis: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Extract workflow entries from example/sample/demo directories.

    Scans ``examples/``, ``samples/``, and ``demo/`` directories for ``.py`` files,
    parses their imports, and matches them against known API classes from
    *code_analysis*.

    Args:
        repo_dir: Repository root directory.
        code_analysis: Result dict from :func:`analyze_repository_code`.

    Returns:
        Sorted list of ``{"name": str, "source_file": str, "api_classes_used": [str]}``
        dicts for files that import at least one known class.
    """
    # Build set of known class names
    known_classes: Set[str] = set()
    for cls in code_analysis.get("api_surface", {}).get("classes", []):
        if isinstance(cls, dict):
            known_classes.add(cls.get("name", ""))
        elif isinstance(cls, str):
            known_classes.add(cls)
    known_classes.discard("")

    if not known_classes:
        return []

    # Collect .py files from example directories
    example_dirs = ["examples", "samples", "demo"]
    py_files: List[Path] = []
    for dir_name in example_dirs:
        example_dir = repo_dir / dir_name
        if example_dir.is_dir():
            try:
                for f in sorted(example_dir.rglob("*.py")):
                    py_files.append(f)
                    if len(py_files) >= 50:
                        break
            except Exception:
                pass
        if len(py_files) >= 50:
            break

    workflows: List[Dict[str, Any]] = []
    for py_file in py_files:
        try:
            source = py_file.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(source, filename=str(py_file))
        except Exception:
            continue

        imported_names: Set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_names.add(alias.name.split(".")[-1])
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name != "*":
                        imported_names.add(alias.name)

        matched = sorted(known_classes & imported_names)
        if matched:
            try:
                rel_path = str(py_file.relative_to(repo_dir)).replace("\\", "/")
            except ValueError:
                rel_path = str(py_file).replace("\\", "/")
            workflows.append({
                "name": py_file.stem,
                "source_file": rel_path,
                "api_classes_used": matched,
            })

    return sorted(workflows, key=lambda w: w["name"])


def build_repo_truth(
    repo_dir: Path,
    manifest_data: Dict[str, Any],
    code_analysis: Dict[str, Any],
    source_roots: List[str],
) -> Dict[str, Any]:
    """Build deterministic repo_truth.json from source files.

    No LLM involved. Extracts:
    - license: from LICENSE/COPYING file header matching
    - python_requires: from manifest (pyproject.toml or setup.py)
    - package_name: from manifest
    - import_roots: from source root analysis
    """
    license_info = _parse_license_file(repo_dir)

    python_requires_raw = manifest_data.get("python_requires") or ""
    python_min = ""
    if python_requires_raw:
        m = re.match(r">=?\s*(\d+\.\d+)", python_requires_raw)
        if m:
            python_min = m.group(1)

    package_name = manifest_data.get("name") or ""
    import_roots_raw = code_analysis.get("code_structure", {}).get("source_roots", source_roots)

    # Determine python_requires source
    py_source = ""
    if python_requires_raw:
        py_source = "pyproject.toml" if manifest_data.get("_from_pyproject") else "setup.py"

    # Extract supported_formats from code analysis constants
    raw_formats = code_analysis.get("constants", {}).get("supported_formats", [])
    supported_formats = sorted(set(
        f.upper() if isinstance(f, str) else str(f)
        for f in raw_formats
    )) if raw_formats else []

    # Extract dependencies from manifest
    deps_raw = manifest_data.get("dependencies", [])
    if isinstance(deps_raw, dict):
        deps_raw = list(deps_raw.keys())
    dependencies = sorted(deps_raw) if isinstance(deps_raw, list) else []

    # Extract CLI entrypoints from manifest
    entrypoints_raw = manifest_data.get("entrypoints", [])
    entrypoints = sorted(entrypoints_raw) if isinstance(entrypoints_raw, list) else []

    # Phase 3A: Extract capabilities from README + docstrings (with evidence)
    capabilities_list = _extract_capabilities(repo_dir, code_analysis)

    # Phase 3B: Extract workflows from example directories
    workflows_list = _extract_workflows(repo_dir, code_analysis)

    # Phase 3C: Compute example coverage metric
    total_api_classes = len(code_analysis.get("api_surface", {}).get("classes", []))
    classes_with_examples_set: Set[str] = set()
    for wf in workflows_list:
        classes_with_examples_set.update(wf.get("api_classes_used", []))
    classes_with_examples = len(classes_with_examples_set)
    coverage_ratio = round(
        classes_with_examples / max(total_api_classes, 1), 2,
    )

    # Extract conversion_pairs, input/output formats, limitations
    conversion_pairs = _extract_conversion_pairs_deterministic(
        repo_dir, code_analysis, supported_formats,
    )
    input_formats, output_formats = _extract_input_output_formats(
        code_analysis, supported_formats,
    )
    limitations_list = _extract_limitation_summary(repo_dir, package_name or "")

    return {
        "schema_version": "1.0",
        "license": {
            "spdx_id": license_info.get("spdx_id", ""),
            "name": license_info.get("name", ""),
            "source": license_info.get("source", ""),
        },
        "python_requires": {
            "min": python_min,
            "spec": python_requires_raw,
            "source": py_source,
        },
        "package_name": {
            "value": package_name,
            "source": "manifest" if package_name else "",
        },
        "import_roots": {
            "values": import_roots_raw or [],
            "source": "code_analysis",
        },
        "supported_formats": {
            "values": supported_formats,
            "source": "code_constants" if supported_formats else "",
        },
        "input_formats": {  #
            "values": input_formats,
            "source": "code_analysis" if input_formats else "",
        },
        "output_formats": {  #
            "values": output_formats,
            "source": "code_analysis" if output_formats else "",
        },
        "conversion_pairs": {  #
            "values": conversion_pairs,
            "source": "code_analysis" if conversion_pairs else "",
        },
        "dependencies": {
            "values": dependencies,
            "source": "manifest" if dependencies else "",
        },
        "entrypoints": {
            "values": entrypoints,
            "source": "manifest" if entrypoints else "",
        },
        "capabilities": {
            "values": capabilities_list,
            "source": "readme+docstrings" if capabilities_list else "",
        },
        "limitations": {  #
            "values": limitations_list,
            "source": "source_code_patterns" if limitations_list else "",
        },
        "workflows": {
            "values": workflows_list,
            "source": "example_files" if workflows_list else "",
        },
        "example_coverage": {
            "ratio": coverage_ratio,
            "classes_with_examples": classes_with_examples,
            "total_api_classes": total_api_classes,
            "source": "example_files",
        },
    }


def build_api_inventory(
    code_analysis: Dict[str, Any],
    repo_dir: Path,
    source_roots: List[str],
    source_files: Optional[List[Path]] = None,
) -> Dict[str, Any]:
    """Build an API inventory artifact from code_analysis results.

    Enriches the existing code_analysis with full import paths and public
    surface heuristics.  Designed to be called after
    :func:`analyze_repository_code` and written as
    ``artifacts/api_inventory.json``.

    Args:
        code_analysis: Result dict from :func:`analyze_repository_code`.
        repo_dir: Repository root directory.
        source_roots: Source root directories (e.g. ``["src/"]``).
        source_files: Optional list of analyzed source files (for __all__ extraction).

    Returns:
        API inventory dict with ``package_name``, ``import_roots``, ``classes``,
        ``functions``, ``modules``, and ``public_surface`` fields.
    """
    api_surface = code_analysis.get("api_surface", {})
    code_structure = code_analysis.get("code_structure", {})

    package_names = code_structure.get("package_names", [])
    package_name = package_names[0] if package_names else ""

    # Build __all__ exports from __init__.py files
    init_exports: Dict[str, List[str]] = {}
    if source_files:
        for fp in source_files:
            if fp.name == "__init__.py":
                imp_path = _compute_import_path(fp, repo_dir, source_roots)
                exports = _extract_modules_from_init(fp)
                if exports:
                    init_exports[imp_path] = exports

    # Enrich classes with import paths
    enriched_classes = []
    for cls in api_surface.get("classes", []):
        if isinstance(cls, dict):
            cls_name = cls.get("name", "")
            module = cls.get("module", "")
            import_path = ""
            for init_mod, exports in init_exports.items():
                if cls_name in exports:
                    import_path = f"{init_mod}.{cls_name}"
                    break
            if not import_path and module:
                import_path = f"{module}.{cls_name}"

            enriched_classes.append({
                "name": cls_name,
                "kind": cls.get("kind", "class"),  # propagate kind
                "import_path": import_path,
                "module": module,
                "methods": cls.get("methods", []),
                "method_details": cls.get("method_details", []),
                "properties": cls.get("properties", []),
                "constructor": cls.get("constructor"),
                "class_constants": cls.get("class_constants", []),
                "bases": cls.get("bases", []),
                "source_file": cls.get("source_file", ""),
                "start_line": cls.get("start_line", 0),
                "docstring": cls.get("docstring", ""),  # preserve for api_index
            })
        elif isinstance(cls, str):
            enriched_classes.append({
                "name": cls,
                "kind": "class",  # explicit kind for string entries
                "import_path": cls,
                "module": "",
                "methods": [],
                "method_details": [],
                "properties": [],
                "constructor": None,
                "class_constants": [],
                "bases": [],
                "source_file": "",
                "start_line": 0,
            })

    # Determine public surface using export reachability
    all_exported, export_source = _build_export_reachability(
        init_exports, source_files, repo_dir, source_roots,
    )

    # Determine confidence level
    if export_source == "__all__":
        confidence = "high"
    elif export_source == "underscore_convention" and enriched_classes:
        confidence = "medium"
    else:
        confidence = "unknown"

    public_classes = []
    for cls in enriched_classes:
        name = cls["name"]
        import_path = cls.get("import_path", name)
        # Store import path (e.g. "aspose.threed.Scene") instead of bare name
        # to prevent collisions when different modules export same-named classes.
        label = import_path if import_path else name
        if all_exported and name in all_exported:
            public_classes.append(label)
        elif not all_exported and not name.startswith("_"):
            # Fallback: underscore convention when no export info available
            public_classes.append(label)

    public_functions = []
    for func in api_surface.get("functions", []):
        fname = func if isinstance(func, str) else func.get("name", "")
        if all_exported and fname.split(".")[0] in all_exported:
            public_functions.append(fname)
        elif not all_exported and not fname.startswith("_"):
            public_functions.append(fname)

    return {
        "package_name": package_name,
        "import_roots": source_roots,
        "classes": enriched_classes,
        "functions": sorted(set(api_surface.get("functions", []))),
        "function_details": api_surface.get("function_details", []),
        "modules": sorted(set(api_surface.get("modules", []))),
        "public_surface": {
            "classes": sorted(set(public_classes)),
            "functions": sorted(set(public_functions)),
            "confidence": confidence,
            "source": export_source,
        },
        "metadata": code_analysis.get("metadata", {}),
    }


def build_api_index(api_inventory: Dict[str, Any]) -> Dict[str, Any]:
    """Build a compact API index for token-efficient W5 prompt injection.

    Emits a lightweight summary with class_index (name, import_path,
    kind, method_count, property_count, docstring_snippet) and function_index
    (name, signature, return_type). Much smaller than the full api_inventory.

    Args:
        api_inventory: Full inventory dict from build_api_inventory().

    Returns:
        {package_name, modules, class_index, function_index, symbol_count}
    """
    class_index: List[Dict[str, Any]] = []
    for cls in api_inventory.get("classes", []):
        if not isinstance(cls, dict):
            continue
        raw_doc = cls.get("docstring", "")
        class_index.append({
            "name": cls.get("name", ""),
            "import_path": cls.get("import_path", ""),
            "kind": cls.get("kind", "class"),
            "method_count": len(cls.get("methods", [])),
            "property_count": len(cls.get("properties", [])),
            "docstring_snippet": _first_sentence(raw_doc, max_len=120),
        })

    function_index: List[Dict[str, Any]] = []
    for fn in api_inventory.get("function_details", []):
        if not isinstance(fn, dict):
            continue
        function_index.append({
            "name": fn.get("name", ""),
            "signature": fn.get("signature", ""),
            "return_type": fn.get("return_type", ""),
            "docstring_snippet": fn.get("docstring_snippet", ""),
        })

    return {
        "package_name": api_inventory.get("package_name", ""),
        "modules": api_inventory.get("modules", []),
        "class_index": class_index,
        "function_index": function_index,
        "symbol_count": len(class_index) + len(function_index),
    }


def _format_base(node) -> str:
    """Format an AST base class node to a string name."""
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Attribute):
        return f"{_format_base(node.value)}.{node.attr}"
    return ""


def _extract_signature(func_node) -> str:
    """Extract function signature as a string of parameters."""
    args = func_node.args
    params = []
    for arg in args.args:
        if arg.arg in ('self', 'cls'):
            continue
        annotation = ""
        if arg.annotation and hasattr(ast, 'unparse'):
            try:
                annotation = f": {ast.unparse(arg.annotation)}"
            except Exception:
                pass
        params.append(f"{arg.arg}{annotation}")
    return f"({', '.join(params)})"


def _extract_return_annotation(func_node) -> str:
    """Extract return type annotation as string."""
    if func_node.returns and hasattr(ast, 'unparse'):
        try:
            return ast.unparse(func_node.returns)
        except Exception:
            return ""
    return ""


def _property_binding_name(func_node) -> str:
    """Return the logical property name for @property/@x.setter accessors."""
    for decorator in func_node.decorator_list:
        if isinstance(decorator, ast.Name) and decorator.id == "property":
            return func_node.name
        if isinstance(decorator, ast.Attribute):
            if decorator.attr == "property":
                return func_node.name
            if decorator.attr in {"getter", "setter", "deleter"}:
                if isinstance(decorator.value, ast.Name):
                    return decorator.value.id
                if isinstance(decorator.value, ast.Attribute):
                    return decorator.value.attr
    return ""


def _is_property_setter(func_node) -> bool:
    """Return True when a function is decorated as a property setter."""
    return any(
        isinstance(decorator, ast.Attribute) and decorator.attr == "setter"
        for decorator in func_node.decorator_list
    )


def analyze_python_file(
    file_path: Path,
    repo_dir: Optional[Path] = None,
    source_roots: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Analyze Python file using AST.

    Args:
        file_path: Path to the Python file.
        repo_dir: Optional repo root for full import path resolution.
        source_roots: Optional source roots for import path resolution.

    Returns:
        {
            "classes": [{"name": str, "docstring": str, "bases": [str],
                         "module": str, "methods": [str],
                         "method_details": [{"name", "signature", "docstring", "return_type"}]}],
            "functions": ["function1", ...],  # Flat list (ClassName.method or standalone)
            "constants": {"__version__": "1.0", "SUPPORTED_FORMATS": [...]},
        }
    """
    try:
        content = file_path.read_text(encoding='utf-8', errors='ignore')
        tree = ast.parse(content, filename=str(file_path))
    except SyntaxError as e:
        logger.warning(f"Syntax error in {file_path}: {e}")
        return {"classes": [], "functions": [], "constants": {}}
    except Exception as e:
        logger.error(f"Failed to parse {file_path}: {e}")
        return {"classes": [], "functions": [], "constants": {}}

    # Compute full import path when repo_dir and source_roots are available
    if repo_dir and source_roots:
        module_name = _compute_import_path(file_path, repo_dir, source_roots)
    else:
        module_name = file_path.stem

    classes = []
    functions = []
    function_details = []
    constants = {}

    for node in ast.iter_child_nodes(tree):
        # Extract public classes and their methods
        if isinstance(node, ast.ClassDef):
            if not node.name.startswith('_'):
                # Build method details
                method_names = []
                method_details = []
                property_names = []
                property_detail_map = {}
                constructor_info = None
                class_constants = []
                class_has_public = False
                for child in ast.iter_child_nodes(node):
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        property_name = _property_binding_name(child)
                        is_property = bool(property_name)
                        if is_property and not property_name.startswith('_'):
                            if property_name not in property_names:
                                property_names.append(property_name)
                            _prop_type = _extract_return_annotation(child)
                            _prop_doc = ast.get_docstring(child) or ""
                            detail = property_detail_map.setdefault(property_name, {
                                "name": property_name,
                                "type_annotation": "",
                                "is_readonly": True,
                                "docstring_snippet": "",
                            })
                            if _prop_type and not detail["type_annotation"]:
                                detail["type_annotation"] = _prop_type
                            if _prop_doc and not detail["docstring_snippet"]:
                                detail["docstring_snippet"] = _first_sentence(_prop_doc, max_len=80)
                            if _is_property_setter(child):
                                detail["is_readonly"] = False
                            class_has_public = True
                        # Extract __init__ constructor parameters
                        if child.name == "__init__":
                            params = []
                            all_args = child.args.args
                            defaults = child.args.defaults
                            # defaults aligns to the LAST N entries of all_args
                            num_without_default = len(all_args) - len(defaults)
                            for idx, arg in enumerate(all_args):
                                if arg.arg in ('self', 'cls'):
                                    continue
                                annotation = ""
                                if arg.annotation and hasattr(ast, 'unparse'):
                                    try:
                                        annotation = ast.unparse(arg.annotation)
                                    except Exception:
                                        pass
                                default_str = ""
                                default_idx = idx - num_without_default
                                if default_idx >= 0 and default_idx < len(defaults):
                                    default_node = defaults[default_idx]
                                    if hasattr(ast, 'unparse'):
                                        try:
                                            default_str = ast.unparse(default_node)
                                        except Exception:
                                            pass
                                params.append({
                                    "name": arg.arg,
                                    "annotation": annotation,
                                    "default": default_str,
                                })
                            constructor_info = {"parameters": params}
                        if not child.name.startswith('_') and not is_property:
                            # Determine method kind from decorators
                            _method_kind = "method"
                            for _d in child.decorator_list:
                                if isinstance(_d, ast.Name):
                                    if _d.id == "classmethod":
                                        _method_kind = "classmethod"
                                        break
                                    elif _d.id == "staticmethod":
                                        _method_kind = "staticmethod"
                                        break
                            _raw_doc = ast.get_docstring(child) or ""
                            functions.append(f"{node.name}.{child.name}")
                            method_names.append(child.name)
                            # Extract structured parameters (TC-HYBRID-02)
                            _method_params = []
                            _all_args = child.args.args
                            _defaults = child.args.defaults
                            _num_without_default = len(_all_args) - len(_defaults)
                            for _pidx, _arg in enumerate(_all_args):
                                if _arg.arg in ('self', 'cls'):
                                    continue
                                _ann = ""
                                if _arg.annotation and hasattr(ast, 'unparse'):
                                    try:
                                        _ann = ast.unparse(_arg.annotation)
                                    except Exception:
                                        pass
                                _method_params.append({"name": _arg.arg, "type_annotation": _ann})
                            method_details.append({
                                "name": child.name,
                                "parameters": _method_params,
                                "signature": f"{child.name}{_extract_signature(child)}",
                                "docstring": _raw_doc,
                                "docstring_snippet": _first_sentence(_raw_doc, max_len=80),
                                "return_type": _extract_return_annotation(child),
                                "is_async": isinstance(child, ast.AsyncFunctionDef),
                                "start_line": child.lineno,
                                "kind": _method_kind,
                            })
                            class_has_public = True
                    # Extract class-level UPPERCASE constants (enum members)
                    elif isinstance(child, ast.Assign):
                        for target in child.targets:
                            if (
                                isinstance(target, ast.Name)
                                and not target.id.startswith("_")
                                and target.id.isupper()
                            ):
                                class_constants.append(target.id)
                # For auto-generated bindings where all methods are private,
                # include dunder methods (__init__, __enter__, etc.) as indicators
                if not class_has_public:
                    for child in ast.iter_child_nodes(node):
                        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            if child.name.startswith('__') and child.name.endswith('__'):
                                functions.append(f"{node.name}.{child.name}")
                                method_names.append(child.name)

                property_details = [
                    property_detail_map[name]
                    for name in property_names
                    if name in property_detail_map
                ]

                # Detect enum classes (inherits from Enum, IntEnum, etc.) (TC-HYBRID-02)
                _ENUM_BASES = {"Enum", "IntEnum", "StrEnum", "Flag", "IntFlag"}
                _is_enum_class = any(
                    (isinstance(b, ast.Name) and b.id in _ENUM_BASES) or
                    (isinstance(b, ast.Attribute) and b.attr in _ENUM_BASES)
                    for b in node.bases
                )
                _enum_members: list[dict] = []
                if _is_enum_class:
                    for _echild in ast.iter_child_nodes(node):
                        if isinstance(_echild, ast.Assign):
                            for _etgt in _echild.targets:
                                if isinstance(_etgt, ast.Name) and not _etgt.id.startswith("_"):
                                    try:
                                        _eval = ast.literal_eval(_echild.value)
                                        _val_str = str(_eval)
                                    except Exception:
                                        _val_str = ""
                                    _enum_members.append({"name": _etgt.id, "value": _val_str})

                # Compute relative source_file path
                src_file = ""
                if repo_dir:
                    try:
                        src_file = str(file_path.resolve().relative_to(repo_dir.resolve()))
                        src_file = src_file.replace("\\", "/")
                    except ValueError:
                        src_file = str(file_path)

                classes.append({
                    "name": node.name,
                    "kind": "class",  # explicit kind field
                    "docstring": ast.get_docstring(node) or "",
                    "bases": [_format_base(b) for b in node.bases if _format_base(b)],
                    "module": module_name,
                    "methods": method_names,
                    "method_details": method_details,
                    "properties": sorted(property_names),
                    "property_details": property_details,  # TC-HYBRID-02
                    "constructor": constructor_info,
                    "class_constants": sorted(class_constants),
                    "is_enum": _is_enum_class,              # TC-HYBRID-02
                    "enum_members": _enum_members,          # TC-HYBRID-02
                    "source_file": src_file,
                    "start_line": node.lineno,
                })

        # Extract public module-level functions
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith('_'):
                functions.append(node.name)
                _fn_doc = ast.get_docstring(node) or ""
                function_details.append({
                    "name": node.name,
                    "kind": "function",  # explicit kind field
                    "signature": f"{node.name}{_extract_signature(node)}",
                    "docstring": _fn_doc,
                    "docstring_snippet": _first_sentence(_fn_doc, max_len=80),
                    "return_type": _extract_return_annotation(node),
                    "start_line": node.lineno,
                })

        # Extract constants (UPPERCASE assignments)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    name = target.id
                    if name.isupper() or name.startswith('__'):  # __version__, SUPPORTED_FORMATS
                        try:
                            value = ast.literal_eval(node.value)
                            constants[name] = value
                        except (ValueError, TypeError):
                            pass  # Skip non-literal assignments

    return {
        "classes": classes,
        "functions": sorted(set(functions)),
        "function_details": function_details,
        "constants": constants,
    }


def analyze_javascript_file(file_path: Path) -> Dict[str, Any]:
    """Analyze JavaScript file using regex patterns (MVP).

    Covers ~80% of common cases. Future: Add esprima for full parsing.
    """
    try:
        content = file_path.read_text(encoding='utf-8', errors='ignore')
    except Exception as e:
        logger.error(f"Failed to read {file_path}: {e}")
        return {"classes": [], "functions": []}

    # Extract class definitions: class ClassName {
    classes = re.findall(r'\bclass\s+([A-Z][a-zA-Z0-9_]*)\s*\{', content)

    # Extract functions: function name( or const name = function
    functions = re.findall(r'\b(?:function|const|let)\s+([a-z][a-zA-Z0-9_]*)\s*[=\(]', content)

    return {
        "classes": sorted(set(classes)),
        "functions": sorted(set(functions)),
    }


def analyze_csharp_file(file_path: Path) -> Dict[str, Any]:
    """Analyze C# file using regex patterns (MVP).

    Extracts public API only. Future: Add Roslyn or Tree-sitter for full parsing.
    """
    try:
        content = file_path.read_text(encoding='utf-8', errors='ignore')
    except Exception as e:
        logger.error(f"Failed to read {file_path}: {e}")
        return {"classes": [], "functions": []}

    # Extract public classes: public class ClassName
    classes = re.findall(r'\bpublic\s+class\s+([A-Z][a-zA-Z0-9_]*)', content)

    # Extract public methods: public ReturnType MethodName(
    functions = re.findall(r'\bpublic\s+\w+\s+([A-Z][a-zA-Z0-9_]*)\s*\(', content)

    return {
        "classes": sorted(set(classes)),
        "functions": sorted(set(functions)),
    }


# ---------------------------------------------------------------------------
# setup.cfg manifest parser
# ---------------------------------------------------------------------------

def parse_setup_cfg(file_path: Path) -> Dict[str, Any]:
    """Parse setup.cfg manifest using configparser.

    Extracts [metadata] name/version/description/license,
    [options] python_requires/install_requires/packages,
    and [options.entry_points] console_scripts.

    Returns same shape as parse_pyproject_toml for uniform consumption.
    """
    if not Path(file_path).exists():
        return {}

    import configparser
    cfg = configparser.ConfigParser()
    try:
        cfg.read(str(file_path), encoding="utf-8")
    except Exception as e:
        logger.error(f"Failed to parse {file_path}: {e}")
        return {}

    meta = dict(cfg.items("metadata")) if cfg.has_section("metadata") else {}
    opts = dict(cfg.items("options")) if cfg.has_section("options") else {}

    # install_requires: may be multi-line; configparser joins with \n
    install_requires_raw = opts.get("install_requires", "")
    deps = [
        d.strip()
        for d in re.split(r"[\n;,]", install_requires_raw)
        if d.strip() and not d.strip().startswith("#")
    ]

    # console_scripts from [options.entry_points]
    entrypoints: List[str] = []
    ep_section = "options.entry_points"
    if cfg.has_section(ep_section):
        scripts_raw = cfg.get(ep_section, "console_scripts", fallback="")
        for line in scripts_raw.strip().splitlines():
            line = line.strip()
            if "=" in line:
                entrypoints.append(line.split("=")[0].strip())

    return {
        "name": meta.get("name") or None,
        "version": meta.get("version") or None,
        "description": meta.get("description") or None,
        "python_requires": opts.get("python_requires") or None,
        "dependencies": deps,
        "entrypoints": entrypoints,
        "_from_setup_cfg": True,
    }


# ---------------------------------------------------------------------------
# TypeScript file analyzer
# ---------------------------------------------------------------------------

_TS_EXPORT_CLASS_RE = re.compile(
    r"^\s*export\s+(?:default\s+)?(?:abstract\s+)?class\s+([A-Za-z_$][A-Za-z0-9_$]*)",
    re.MULTILINE,
)
_TS_EXPORT_INTERFACE_RE = re.compile(
    r"^\s*export\s+(?:default\s+)?interface\s+([A-Za-z_$][A-Za-z0-9_$]*)",
    re.MULTILINE,
)
_TS_EXPORT_TYPE_RE = re.compile(
    r"^\s*export\s+type\s+([A-Za-z_$][A-Za-z0-9_$]*)",
    re.MULTILINE,
)
_TS_EXPORT_ENUM_RE = re.compile(
    r"^\s*export\s+(?:const\s+)?enum\s+([A-Za-z_$][A-Za-z0-9_$]*)",
    re.MULTILINE,
)
_TS_EXPORT_FUNC_RE = re.compile(
    r"^\s*export\s+(?:default\s+)?(?:async\s+)?function\s+([a-z_$][A-Za-z0-9_$]*)",
    re.MULTILINE,
)
_TS_EXPORT_CONST_RE = re.compile(
    r"^\s*export\s+(?:const|let)\s+([a-z_$][A-Za-z0-9_$]*)",
    re.MULTILINE,
)


def analyze_typescript_file(file_path: Path) -> Dict[str, Any]:
    """Analyze TypeScript (.ts/.tsx) file using regex patterns (MVP).

    Extracts exported symbols with explicit kind field.
    Covers ~80% of common export patterns. Requires `export` keyword at
    line start to avoid false positives in comments or strings.
    """
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        logger.error(f"Failed to read {file_path}: {e}")
        return {"classes": [], "functions": []}

    classes: List[Dict[str, Any]] = []
    for m in _TS_EXPORT_CLASS_RE.finditer(content):
        classes.append({"name": m.group(1), "kind": "class", "methods": [], "bases": []})
    for m in _TS_EXPORT_INTERFACE_RE.finditer(content):
        classes.append({"name": m.group(1), "kind": "interface", "methods": [], "bases": []})
    for m in _TS_EXPORT_TYPE_RE.finditer(content):
        classes.append({"name": m.group(1), "kind": "type", "methods": [], "bases": []})
    for m in _TS_EXPORT_ENUM_RE.finditer(content):
        classes.append({"name": m.group(1), "kind": "enum", "methods": [], "bases": []})

    functions: List[str] = []
    for m in _TS_EXPORT_FUNC_RE.finditer(content):
        functions.append(m.group(1))
    for m in _TS_EXPORT_CONST_RE.finditer(content):
        functions.append(m.group(1))

    # Deduplicate by name, keeping first occurrence
    seen_names: set = set()
    deduped_classes: List[Dict[str, Any]] = []
    for cls in classes:
        if cls["name"] not in seen_names:
            seen_names.add(cls["name"])
            deduped_classes.append(cls)

    return {
        "classes": deduped_classes,
        "functions": sorted(set(functions)),
    }


# ---------------------------------------------------------------------------
# Go module + file analyzer
# ---------------------------------------------------------------------------

_GO_MODULE_RE = re.compile(r"^module\s+(\S+)", re.MULTILINE)
_GO_VERSION_RE = re.compile(r"^go\s+(\d+\.\d+(?:\.\d+)?)", re.MULTILINE)
_GO_STRUCT_RE = re.compile(r"^type\s+([A-Z][A-Za-z0-9_]*)\s+(?:struct|interface)\b", re.MULTILINE)
_GO_FUNC_RE = re.compile(r"^func\s+([A-Z][A-Za-z0-9_]*)\s*\(", re.MULTILINE)
_GO_METHOD_RE = re.compile(
    r"^func\s+\([^)]+\)\s+([A-Z][A-Za-z0-9_]*)\s*\(", re.MULTILINE
)


def parse_go_mod(file_path: Path) -> Dict[str, Any]:
    """Parse go.mod for module path and Go version.

    Returns {name, go_version, _from_go_mod}.
    """
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        logger.error(f"Failed to read {file_path}: {e}")
        return {}

    module_match = _GO_MODULE_RE.search(content)
    version_match = _GO_VERSION_RE.search(content)

    module_path = module_match.group(1) if module_match else ""
    # Use last segment as package name (e.g. "github.com/user/mylib" → "mylib")
    name = module_path.split("/")[-1] if module_path else ""

    return {
        "name": name or None,
        "module_path": module_path or None,
        "go_version": version_match.group(1) if version_match else None,
        "_from_go_mod": True,
    }


def analyze_go_file(file_path: Path) -> Dict[str, Any]:
    """Analyze Go (.go) file using regex patterns (MVP).

    Extracts exported (capitalized) types, functions, and methods.
    Per Go convention, exported identifiers start with an uppercase letter.
    """
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        logger.error(f"Failed to read {file_path}: {e}")
        return {"classes": [], "functions": []}

    # Exported struct/interface types → classes
    classes: List[Dict[str, Any]] = [
        {"name": m.group(1), "kind": "class", "methods": [], "bases": []}
        for m in _GO_STRUCT_RE.finditer(content)
    ]

    # Exported package-level functions
    funcs = [m.group(1) for m in _GO_FUNC_RE.finditer(content)]
    # Exported methods (receiver functions)
    methods = [m.group(1) for m in _GO_METHOD_RE.finditer(content)]

    return {
        "classes": classes,
        "functions": sorted(set(funcs + methods)),
    }


# ---------------------------------------------------------------------------
# Deterministic conversion pairs extraction
# ---------------------------------------------------------------------------

_CONVERSION_PAIR_RE = re.compile(
    r"(?:convert|transform|export|save)[\w_]*_?(?:to|from|2)_?([\w]+)",
    re.IGNORECASE,
)
_FORMAT_KEYWORD_RE = re.compile(
    r"\b([A-Z]{2,6})\b",  # uppercase 2-6 chars like OBJ, FBX, STL, PDF
)
_LOADER_PATTERN_RE = re.compile(
    r"(?:Load|Read|Import|Open)Options?\s*[(<]?\s*([A-Z][a-z]+)",
    re.IGNORECASE,
)
_SAVER_PATTERN_RE = re.compile(
    r"(?:Save|Write|Export)Options?\s*[(<]?\s*([A-Z][a-z]+)",
    re.IGNORECASE,
)


def _extract_conversion_pairs_deterministic(
    repo_dir: Path,
    code_analysis: Dict[str, Any],
    supported_formats: List[str],
) -> List[Dict[str, str]]:
    """Extract format conversion pairs deterministically from code and example filenames.

    Scans example filenames, class names, and SaveOptions/LoadOptions
    subclasses for evidence of (source_format, target_format) pairs.
    Returns sorted list of {source, target, evidence_file} dicts.
    No LLM involved.
    """
    pairs: Dict[tuple, str] = {}  # (source, target) -> evidence_file

    fmt_set = set(f.upper() for f in supported_formats)
    if not fmt_set:
        return []

    # --- Scan example filenames (e.g. convert_obj_to_stl.py) ---
    example_dirs = ["examples", "samples", "demo"]
    for dir_name in example_dirs:
        d = repo_dir / dir_name
        if not d.exists():
            continue
        for py_file in sorted(d.glob("**/*.py")):
            stem = py_file.stem.upper().replace("-", "_")
            for src_fmt in fmt_set:
                for tgt_fmt in fmt_set:
                    if src_fmt == tgt_fmt:
                        continue
                    # Match "XXX_TO_YYY" or "XXXXXXXXYYY" patterns in filename
                    if (f"{src_fmt}_TO_{tgt_fmt}" in stem
                            or f"{src_fmt}2{tgt_fmt}" in stem
                            or f"CONVERT_{src_fmt}_{tgt_fmt}" in stem):
                        key = (src_fmt, tgt_fmt)
                        if key not in pairs:
                            try:
                                rel = str(py_file.relative_to(repo_dir)).replace("\\", "/")
                            except ValueError:
                                rel = py_file.name
                            pairs[key] = rel

    # --- Scan class names for XxxExporter/XxxImporter/XxxConverter patterns ---
    classes = code_analysis.get("api_surface", {}).get("classes", [])
    for cls in classes:
        name = (cls.get("name", "") if isinstance(cls, dict) else str(cls)).upper()
        for fmt in fmt_set:
            if name.startswith(fmt) and any(
                name.endswith(suf)
                for suf in ("EXPORTER", "IMPORTER", "CONVERTER", "WRITER", "READER")
            ):
                if name.endswith("EXPORTER") or name.endswith("WRITER"):
                    # fmt → (unknown target); record as (fmt, *) placeholder
                    pass  # Skip one-sided without a known pair
                elif name.endswith("IMPORTER") or name.endswith("READER"):
                    pass

    result = [
        {"source": src, "target": tgt, "evidence_file": ev}
        for (src, tgt), ev in sorted(pairs.items())
    ]
    return result


def _extract_input_output_formats(
    code_analysis: Dict[str, Any],
    supported_formats: List[str],
) -> tuple:
    """Split supported_formats into input (load) and output (save) subsets.

    Scans class names for LoadOptions/SaveOptions patterns to
    determine direction. Falls back to bidirectional (both lists equal).
    Returns (input_formats, output_formats) as sorted lists.
    """
    classes = code_analysis.get("api_surface", {}).get("classes", [])
    input_fmts: set = set()
    output_fmts: set = set()

    fmt_set = set(f.upper() for f in supported_formats)

    for cls in classes:
        name = (cls.get("name", "") if isinstance(cls, dict) else str(cls)).upper()
        for fmt in fmt_set:
            if name.startswith(fmt):
                if any(name.endswith(suf) for suf in ("LOADOPTIONS", "READOPTIONS", "IMPORTOPTIONS")):
                    input_fmts.add(fmt)
                elif any(name.endswith(suf) for suf in ("SAVEOPTIONS", "WRITEOPTIONS", "EXPORTOPTIONS")):
                    output_fmts.add(fmt)

    # If no directional signal, treat all formats as bidirectional
    if not input_fmts and not output_fmts:
        return sorted(fmt_set), sorted(fmt_set)

    return sorted(input_fmts), sorted(output_fmts)


def _extract_limitation_summary(
    repo_dir: Path,
    product_name: str,
    cap: int = 30,
) -> List[Dict[str, Any]]:
    """Extract limitation summary from source code patterns for repo_truth.

    Reuses extract_code_limitations() results but returns a compact
    {text, source_file, start_line} list capped at `cap` entries, deduplicated.
    No claim IDs — those belong to the claims layer.
    """
    try:
        raw = extract_code_limitations(repo_dir, product_name)
    except Exception as e:
        logger.warning("limitation_extraction_failed: %s", e)
        return []

    seen: set = set()
    result: List[Dict[str, Any]] = []
    for lim in raw:
        text = lim.get("claim_text", "").strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        src = lim.get("citations", [{}])[0].get("path", "") if lim.get("citations") else ""
        line = lim.get("citations", [{}])[0].get("start_line", 0) if lim.get("citations") else 0
        result.append({"text": text, "source_file": src, "start_line": line})
        if len(result) >= cap:
            break
    return result


def parse_pyproject_toml(file_path: Path) -> Dict[str, Any]:
    """Parse pyproject.toml manifest.

    Returns:
        {name, version, description, dependencies, entrypoints}
    """
    if tomllib is None:
        logger.warning("tomllib/tomli not available, cannot parse pyproject.toml")
        return {}

    try:
        with open(file_path, 'rb') as f:
            data = tomllib.load(f)
    except Exception as e:
        logger.error(f"Failed to parse {file_path}: {e}")
        return {}

    project = data.get("project", {})

    return {
        "name": project.get("name"),
        "version": project.get("version"),
        "description": project.get("description"),
        "python_requires": project.get("requires-python"),
        "dependencies": project.get("dependencies", []),
        "entrypoints": list(project.get("scripts", {}).keys()),
    }


def parse_package_json(file_path: Path) -> Dict[str, Any]:
    """Parse package.json manifest.

    Returns:
        {name, version, description, dependencies}
    """
    try:
        data = json.loads(file_path.read_text())
    except Exception as e:
        logger.error(f"Failed to parse {file_path}: {e}")
        return {}

    return {
        "name": data.get("name"),
        "version": data.get("version"),
        "description": data.get("description"),
        "dependencies": list(data.get("dependencies", {}).keys()),
    }


def parse_setup_py(file_path: Path) -> Dict[str, Any]:
    """Parse setup.py manifest using AST (no exec/eval).

    Finds the ``setup()`` call in the module and extracts keyword arguments
    such as name, version, python_requires, install_requires, extras_require,
    and description.

    Args:
        file_path: Path to setup.py

    Returns:
        Dict with extracted fields, or empty dict on any error.
    """
    try:
        content = file_path.read_text(encoding='utf-8', errors='ignore')
        tree = ast.parse(content, filename=str(file_path))
    except Exception as e:
        logger.warning(f"Failed to parse {file_path}: {e}")
        return {}

    # Walk the AST to find the setup() call
    setup_call = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            # Match setup(...) or setuptools.setup(...)
            if isinstance(func, ast.Name) and func.id == 'setup':
                setup_call = node
                break
            elif isinstance(func, ast.Attribute) and func.attr == 'setup':
                setup_call = node
                break

    if setup_call is None:
        logger.warning(f"No setup() call found in {file_path}")
        return {}

    result: Dict[str, Any] = {}

    # Fields we want to extract as strings
    string_fields = ('name', 'version', 'python_requires', 'description')
    # Fields we want to extract as lists
    list_fields = ('install_requires',)
    # Fields we want to extract as dicts of lists
    dict_list_fields = ('extras_require',)

    for keyword in setup_call.keywords:
        key = keyword.arg
        if key is None:
            continue  # **kwargs expansion — skip

        value_node = keyword.value

        if key in string_fields:
            # Extract string value
            if isinstance(value_node, ast.Constant) and isinstance(value_node.value, str):
                result[key] = value_node.value
            elif isinstance(value_node, ast.Str):  # Python 3.7 compat
                result[key] = value_node.s

        elif key in list_fields:
            # Extract list of strings
            if isinstance(value_node, ast.List):
                items = []
                for elt in value_node.elts:
                    if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                        items.append(elt.value)
                    elif isinstance(elt, ast.Str):
                        items.append(elt.s)
                result[key] = items
            else:
                result[key] = []

        elif key in dict_list_fields:
            # Extract dict of string -> list[string]
            if isinstance(value_node, ast.Dict):
                extras: Dict[str, List[str]] = {}
                for k_node, v_node in zip(value_node.keys, value_node.values):
                    k_str = None
                    if isinstance(k_node, ast.Constant) and isinstance(k_node.value, str):
                        k_str = k_node.value
                    elif isinstance(k_node, ast.Str):
                        k_str = k_node.s
                    if k_str is None:
                        continue
                    v_list: List[str] = []
                    if isinstance(v_node, ast.List):
                        for elt in v_node.elts:
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                v_list.append(elt.value)
                            elif isinstance(elt, ast.Str):
                                v_list.append(elt.s)
                    extras[k_str] = v_list
                result[key] = extras

    return result


def extract_positioning_from_readme(readme_path: Path) -> Dict[str, str]:
    """Extract tagline and description from README.

    Reads first 2000 chars, extracts:
    - Tagline: First H1 heading (# Tagline)
    - Description: Next non-empty line after H1

    Returns:
        {tagline, short_description}
    """
    try:
        content = readme_path.read_text(encoding='utf-8')[:2000]
    except Exception as e:
        logger.warning(f"Failed to read README {readme_path}: {e}")
        return {}

    lines = content.split('\n')
    tagline = None
    description = None

    for i, line in enumerate(lines):
        if line.startswith('# '):
            tagline = line[2:].strip()
            # Find next non-empty line
            for j in range(i+1, min(i+10, len(lines))):
                desc_line = lines[j].strip()
                if desc_line and not desc_line.startswith('#'):
                    description = desc_line
                    break
            break

    return {
        "tagline": tagline or "",
        "short_description": description or "",
    }


def _extract_modules_from_init(init_path: Path) -> List[str]:
    """
    Extract module names from __init__.py.

    Strategy:
    1. Look for __all__ = [...] assignment
    2. Fallback: Extract from import statements
    3. Fallback: Return empty list

    Args:
        init_path: Path to __init__.py file

    Returns:
        List of module names (sorted)
    """
    try:
        content = init_path.read_text(encoding='utf-8')
        tree = ast.parse(content)

        # Strategy 1: Look for __all__ = [...]
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == '__all__':
                        try:
                            return sorted(ast.literal_eval(node.value))
                        except (ValueError, TypeError):
                            pass  # Couldn't evaluate, try next strategy

        # Strategy 2: Extract from imports
        modules = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    modules.add(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    modules.add(node.module.split('.')[0])
                for alias in node.names:
                    if alias.name != '*':
                        modules.add(alias.name)

        return sorted(modules) if modules else []

    except Exception as e:
        logger.debug(f"extract_modules_failed path={init_path} error={e}")
        return []


def _detect_public_entrypoints(repo_dir: Path, source_roots: List[str]) -> List[str]:
    """
    Detect public entrypoints from directory structure.

    Checks for:
    - __init__.py (package entrypoint)
    - __main__.py (direct execution entrypoint)
    - setup.py with entry_points section

    Args:
        repo_dir: Repository root directory
        source_roots: List of source root directories (as strings like "src/", "lib/")

    Returns:
        List of entrypoint identifiers (defaults to ["__init__.py"] if none found)
    """
    entrypoints = []

    for root_str in source_roots:
        # Convert source root string to Path (remove trailing slash)
        root_path = repo_dir / root_str.rstrip('/')

        # Check for __init__.py
        if (root_path / '__init__.py').exists():
            if '__init__.py' not in entrypoints:
                entrypoints.append('__init__.py')

        # Check for __main__.py
        if (root_path / '__main__.py').exists():
            if '__main__.py' not in entrypoints:
                entrypoints.append('__main__.py')

    # Check for setup.py with entry_points at repo root
    setup_py = repo_dir / 'setup.py'
    if setup_py.exists():
        try:
            content = setup_py.read_text(encoding='utf-8')
            if 'entry_points' in content:
                if 'setup.py (entry_points)' not in entrypoints:
                    entrypoints.append('setup.py (entry_points)')
        except Exception:
            pass

    return entrypoints if entrypoints else ['__init__.py']  # Default fallback


def analyze_repository_code(
    repo_dir: Path,
    repo_inventory: Dict[str, Any],
    product_name: str,
    max_files: int = 100,
    timeout_per_file_ms: int = 500,
) -> Dict[str, Any]:
    """Analyze repository code to extract structured information.

    Args:
        repo_dir: Repository root directory
        repo_inventory: Repository inventory from W1
        product_name: Product name
        max_files: Maximum files to analyze (default: 100)
        timeout_per_file_ms: Timeout per file in milliseconds (default: 500)

    Returns:
        {
            api_surface: {classes, functions, modules},
            code_structure: {source_roots, public_entrypoints, package_names},
            constants: {version, supported_formats},
            positioning: {tagline, short_description},
            metadata: {files_analyzed, parsing_failures},
        }

    Spec: specs/07_code_analysis_and_enrichment.md
    """
    # Discover source files (prioritize src/ > lib/ > tests/)
    source_files = discover_source_files(repo_dir, max_files)

    # Discover manifests
    manifests = discover_manifests(repo_dir)

    # Discover README
    readme_path = find_readme(repo_dir)

    # Detect source roots early so import paths can be resolved
    source_roots = detect_source_roots(repo_dir)

    # Analyze files in parallel
    all_classes = []
    all_functions = []
    all_constants = {}
    parsing_failures = 0

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {}
        for file_path in source_files:
            future = executor.submit(
                analyze_file_safe, file_path,
                repo_dir=repo_dir, source_roots=source_roots,
            )
            futures[future] = file_path

        for future in as_completed(futures):
            try:
                result = future.result(timeout=timeout_per_file_ms/1000)
                all_classes.extend(result.get("classes", []))
                all_functions.extend(result.get("functions", []))
                all_constants.update(result.get("constants", {}))
            except Exception as e:
                logger.warning(f"Failed to analyze {futures[future]}: {e}")
                parsing_failures += 1

    # Parse manifests
    manifest_data = {}
    for manifest_path in manifests:
        if manifest_path.name == "pyproject.toml":
            manifest_data = parse_pyproject_toml(manifest_path)
            break
        elif manifest_path.name == "package.json":
            manifest_data = parse_package_json(manifest_path)
            break
        elif manifest_path.name == "go.mod":
            manifest_data = parse_go_mod(manifest_path)  #
            break

    # Fallback: try setup.py if no manifest data found from pyproject.toml/package.json
    if not manifest_data:
        setup_py_path = repo_dir / "setup.py"
        if setup_py_path.exists():
            manifest_data = parse_setup_py(setup_py_path)
            # Normalize install_requires → dependencies for consistency
            if "install_requires" in manifest_data and "dependencies" not in manifest_data:
                manifest_data["dependencies"] = manifest_data["install_requires"]

    # Fallback to setup.cfg if no manifest data yet
    if not manifest_data:
        setup_cfg_path = repo_dir / "setup.cfg"
        if setup_cfg_path.exists():
            manifest_data = parse_setup_cfg(setup_cfg_path)
            if "install_requires" in manifest_data and "dependencies" not in manifest_data:
                manifest_data["dependencies"] = manifest_data["install_requires"]

    # Extract positioning from README
    positioning = {}
    if readme_path:
        positioning = extract_positioning_from_readme(readme_path)

    # Fallback to manifest description
    if not positioning.get("short_description") and manifest_data.get("description"):
        positioning["short_description"] = manifest_data["description"]

    # Extract modules from __init__.py files
    modules = []
    for file_path in source_files:
        if file_path.name == '__init__.py':
            extracted = _extract_modules_from_init(file_path)
            modules.extend(extracted)

    # Detect public entrypoints (source_roots already computed above)
    public_entrypoints = _detect_public_entrypoints(repo_dir, source_roots)

    # Deduplicate classes by name, preferring dicts over strings
    seen_classes: Dict[str, Any] = {}
    for cls in all_classes:
        if isinstance(cls, dict):
            name = cls["name"]
            if name not in seen_classes or isinstance(seen_classes[name], str):
                seen_classes[name] = cls
        else:
            name = cls
            if name not in seen_classes:
                seen_classes[name] = cls
    deduped_classes = sorted(
        seen_classes.values(),
        key=lambda c: c["name"] if isinstance(c, dict) else c,
    )

    # Build result
    return {
        "api_surface": {
            "classes": deduped_classes,
            "functions": sorted(set(
                f if isinstance(f, str) else f.get("name", "")
                for f in all_functions
                if (f if isinstance(f, str) else f.get("name"))
            )),
            "modules": sorted(set(modules)),
        },
        "code_structure": {
            "source_roots": source_roots,
            "public_entrypoints": public_entrypoints,
            "package_names": [manifest_data.get("name")] if manifest_data.get("name") else [],
        },
        "constants": {
            "version": manifest_data.get("version") or all_constants.get("__version__"),
            "supported_formats": all_constants.get("SUPPORTED_FORMATS", []),
        },
        "positioning": positioning,
        "metadata": {
            "files_analyzed": len(source_files),
            "parsing_failures": parsing_failures,
        },
    }


# Curated set of source code extensions for discovery.
# Excludes shell scripts (.sh, .bash, .zsh), PowerShell (.ps1, .psm1),
# and SQL (.sql) which are not compilable source code.
_SOURCE_EXTS: set[str] = {
    ".py", ".pyi", ".java", ".cs", ".js", ".mjs", ".cjs", ".jsx",
    ".ts", ".tsx", ".go", ".rs", ".rb", ".php", ".kt", ".kts",
    ".dart", ".scala", ".swift", ".c", ".cpp", ".cc", ".h", ".hpp",
}

# Extension to tree-sitter language name mapping for non-Python files.
_EXT_TO_LANG: dict[str, str] = {
    ".java": "java", ".cs": "csharp", ".js": "javascript",
    ".mjs": "javascript", ".cjs": "javascript", ".jsx": "javascript",
    ".ts": "typescript", ".tsx": "typescript", ".go": "go",
    ".php": "php", ".rs": "rust", ".rb": "ruby",
    ".kt": "kotlin", ".kts": "kotlin", ".dart": "dart",
    ".scala": "scala", ".swift": "swift", ".m": "objc",
    ".cpp": "cpp", ".cc": "cpp", ".hpp": "cpp",
    ".c": "c", ".h": "c",
}


def discover_source_files(repo_dir: Path, max_files: int) -> List[Path]:
    """Discover source files, prioritizing src/ > lib/ > tests/."""
    candidates = []
    for ext in _SOURCE_EXTS:
        candidates.extend(repo_dir.glob(f"**/*{ext}"))

    # Prioritize by directory
    def priority(path: Path):
        parts = path.parts
        if "src" in parts:
            return 1
        if "lib" in parts:
            return 2
        if "tests" in parts or "test" in parts:
            return 4
        return 3

    candidates.sort(key=priority)
    return candidates[:max_files]


def discover_manifests(repo_dir: Path) -> List[Path]:
    """Find manifest files.

    Added go.mod and setup.cfg to discovery.
    """
    manifests = []
    for name in ["pyproject.toml", "package.json", "go.mod", "setup.cfg",
                 "*.csproj", "pom.xml", "build.gradle", "build.gradle.kts",
                 "Cargo.toml", "composer.json", "*.gemspec", "Gemfile"]:
        manifests.extend(repo_dir.glob(name))
    return manifests


def find_readme(repo_dir: Path) -> Optional[Path]:
    """Find README file."""
    for name in ["README.md", "README.rst", "README.txt", "README"]:
        readme = repo_dir / name
        if readme.exists():
            return readme
    return None


def detect_source_roots(repo_dir: Path) -> List[str]:
    """Detect source code root directories."""
    roots = []
    for candidate in ["src/", "lib/", "pkg/"]:
        if (repo_dir / candidate).exists():
            roots.append(candidate)
    return roots or ["."]  # Fallback to repo root


def analyze_file_safe(
    file_path: Path,
    repo_dir: Optional[Path] = None,
    source_roots: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Analyze file with error handling.

    Args:
        file_path: Path to the source file.
        repo_dir: Optional repo root for import path resolution.
        source_roots: Optional source roots for import path resolution.
    """
    ext = file_path.suffix.lower()
    if ext in (".py", ".pyi"):
        return analyze_python_file(file_path, repo_dir=repo_dir, source_roots=source_roots)

    # For all non-Python languages, delegate to TreeSitterAnalyzer which
    # provides AST-level parsing via tree-sitter grammars.
    lang = _EXT_TO_LANG.get(ext)
    if lang and lang != "python":
        try:
            from launcher.shared.ts_analyzer import analyzer as _ts_analyzer
            result = _ts_analyzer.analyze_file(file_path, lang, repo_dir=repo_dir)
            return {
                "classes": result.classes,
                "functions": result.functions,
                "constants": result.constants,
                "imports": result.imports,
                "exports": result.exports,
                "module_path": result.module_path,
                "language": result.language,
            }
        except Exception:
            logger.debug("TreeSitterAnalyzer failed for %s, returning empty", file_path)
    return {}


# ---------------------------------------------------------------------------
# Extract limitation claims from source code patterns
# ---------------------------------------------------------------------------

import hashlib


def _compute_limitation_id(text: str, kind: str, product: str) -> str:
    """Compute a stable claim ID for a limitation claim.

    Uses the same approach as extract_claims.compute_claim_id but is
    self-contained to avoid circular imports.

    Args:
        text: Claim text (will be lowercased and stripped)
        kind: Claim kind (e.g. "limitation")
        product: Product name

    Returns:
        First 12 hex chars of SHA-256 hash
    """
    normalized = text.strip().lower()
    raw = f"{normalized}|{kind}|{product}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


_SKIP_DIRS = {"__pycache__", ".git", "test", "tests", ".tox", ".nox", "node_modules"}

_NOT_IMPL_SUFFIX_RE = re.compile(
    r'\s*(?:is\s+)?not\s+(?:yet\s+)?(?:implemented|supported|available)\s*'
    r'(?:for\s+\w+(?:\s+\w+)*)?\s*\.?$',
    re.IGNORECASE,
)


def _normalize_limitation_msg(msg: str) -> str:
    """Strip redundant 'is not implemented' suffixes from NotImplementedError messages.

    Prevents fused grammar like 'does not yet support X is not implemented'.
    Example: 'get_entity_renderer_key is not implemented for Camera' → 'get_entity_renderer_key'
    """
    return _NOT_IMPL_SUFFIX_RE.sub('', msg).strip()


def extract_code_limitations(
    repo_dir: Path,
    product_name: str,
) -> List[Dict[str, Any]]:
    """Extract limitation claims from source code patterns.

    Walks all ``.py`` files under *repo_dir* (skipping cache, VCS, and test
    directories) and looks for:

    1. ``raise NotImplementedError("message")`` -- AST-based extraction.
    2. ``# TODO: ...`` and ``# FIXME: ...`` comments -- regex-based extraction.

    Each match is turned into a limitation claim with ``claim_kind="limitation"``.
    Duplicate claim texts (case-insensitive) are deduplicated so only the first
    occurrence is kept.

    Args:
        repo_dir: Root of the cloned repository.
        product_name: Human-readable product name used in claim text.

    Returns:
        List of claim dicts, each containing:
        ``claim_id``, ``claim_text``, ``claim_kind``, ``truth_status``,
        ``confidence``, ``source_type``, ``source_priority``,
        ``source_relevance``, ``citations``.
    """
    todo_fixme_re = re.compile(
        r"(?:#|//)\s*(?:TODO|FIXME)[:\s]+(.+)$", re.MULTILINE | re.IGNORECASE
    )

    claims: List[Dict[str, Any]] = []
    seen_normalized: set = set()

    def _should_skip(dirpath: Path) -> bool:
        return any(part in _SKIP_DIRS for part in dirpath.parts)

    def _add_claim(
        claim_text: str,
        truth_status: str,
        file_path: Path,
        lineno: int,
    ) -> None:
        key = claim_text.strip().lower()
        if key in seen_normalized:
            return
        seen_normalized.add(key)

        try:
            rel_path = str(file_path.relative_to(repo_dir)).replace("\\", "/")
        except ValueError:
            rel_path = str(file_path).replace("\\", "/")

        claim_id = _compute_limitation_id(claim_text, "limitation", product_name)
        claims.append(
            {
                "claim_id": claim_id,
                "claim_text": claim_text,
                "claim_kind": "limitation",
                "truth_status": truth_status,
                "confidence": "medium",
                "source_type": "source_code",
                "source_priority": 2,
                "source_relevance": 70,
                "citations": [
                    {
                        "path": rel_path,
                        "start_line": lineno,
                        "end_line": lineno,
                        "source_type": "source_code",
                    }
                ],
            }
        )

    # Walk all source files (not just *.py) for TODO/FIXME comments.
    # Python files also get AST-based NotImplementedError extraction.
    source_files: list[Path] = []
    for ext in _SOURCE_EXTS:
        source_files.extend(repo_dir.rglob(f"*{ext}"))
    source_files.sort()

    for src_file in source_files:
        if _should_skip(src_file.parent):
            continue

        try:
            source = src_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        # --- AST pass: NotImplementedError with string message (Python only) ---
        if src_file.suffix in (".py", ".pyi"):
            try:
                tree = ast.parse(source, filename=str(src_file))
            except SyntaxError:
                tree = None

            if tree is not None:
                for node in ast.walk(tree):
                    if not isinstance(node, ast.Raise):
                        continue
                    exc = node.exc
                    if exc is None:
                        continue
                    if (
                        isinstance(exc, ast.Call)
                        and isinstance(exc.func, ast.Name)
                        and exc.func.id == "NotImplementedError"
                        and exc.args
                        and isinstance(exc.args[0], ast.Constant)
                        and isinstance(exc.args[0].value, str)
                    ):
                        msg = _normalize_limitation_msg(exc.args[0].value.strip())
                        if msg:
                            claim_text = f"{product_name} does not yet support {msg}"
                            _add_claim(claim_text, "fact", src_file, node.lineno)

        # --- Regex pass: TODO / FIXME comments (all languages) ---
        for match in todo_fixme_re.finditer(source):
            comment_text = match.group(1).strip()
            if not comment_text:
                continue
            lineno = source[: match.start()].count("\n") + 1
            claim_text = f"{product_name} has a known issue: {comment_text}"
            _add_claim(claim_text, "inference", src_file, lineno)

    return claims
