"""TC-1041: Code analysis module for W2 FactsBuilder.

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
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # Fallback for Python 3.10
    except ImportError:
        tomllib = None

logger = logging.getLogger(__name__)


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


def analyze_python_file(file_path: Path) -> Dict[str, Any]:
    """Analyze Python file using AST.

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

    classes = []
    functions = []
    constants = {}

    for node in ast.iter_child_nodes(tree):
        # Extract public classes and their methods
        if isinstance(node, ast.ClassDef):
            if not node.name.startswith('_'):
                # Build method details
                method_names = []
                method_details = []
                class_has_public = False
                for child in ast.iter_child_nodes(node):
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if not child.name.startswith('_'):
                            functions.append(f"{node.name}.{child.name}")
                            method_names.append(child.name)
                            method_details.append({
                                "name": child.name,
                                "signature": f"{child.name}{_extract_signature(child)}",
                                "docstring": ast.get_docstring(child) or "",
                                "return_type": _extract_return_annotation(child),
                            })
                            class_has_public = True
                # For auto-generated bindings where all methods are private,
                # include dunder methods (__init__, __enter__, etc.) as indicators
                if not class_has_public:
                    for child in ast.iter_child_nodes(node):
                        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            if child.name.startswith('__') and child.name.endswith('__'):
                                functions.append(f"{node.name}.{child.name}")
                                method_names.append(child.name)

                classes.append({
                    "name": node.name,
                    "docstring": ast.get_docstring(node) or "",
                    "bases": [_format_base(b) for b in node.bases if _format_base(b)],
                    "module": file_path.stem,
                    "methods": method_names,
                    "method_details": method_details,
                })

        # Extract public module-level functions
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith('_'):
                functions.append(node.name)

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

    # Analyze files in parallel
    all_classes = []
    all_functions = []
    all_constants = {}
    parsing_failures = 0

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {}
        for file_path in source_files:
            future = executor.submit(analyze_file_safe, file_path)
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

    # Fallback: try setup.py if no manifest data found from pyproject.toml/package.json
    if not manifest_data:
        setup_py_path = repo_dir / "setup.py"
        if setup_py_path.exists():
            manifest_data = parse_setup_py(setup_py_path)
            # Normalize install_requires → dependencies for consistency
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

    # Detect public entrypoints
    source_roots = detect_source_roots(repo_dir)
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
            "functions": sorted(set(all_functions)),
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


def discover_source_files(repo_dir: Path, max_files: int) -> List[Path]:
    """Discover source files, prioritizing src/ > lib/ > tests/."""
    candidates = []
    for ext in [".py", ".js", ".cs"]:
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
    """Find manifest files."""
    manifests = []
    for name in ["pyproject.toml", "package.json", "*.csproj"]:
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


def analyze_file_safe(file_path: Path) -> Dict[str, Any]:
    """Analyze file with error handling."""
    ext = file_path.suffix.lower()
    if ext == ".py":
        return analyze_python_file(file_path)
    elif ext == ".js":
        return analyze_javascript_file(file_path)
    elif ext == ".cs":
        return analyze_csharp_file(file_path)
    return {}


# ---------------------------------------------------------------------------
# TC-1605: Extract limitation claims from source code patterns
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
        r"#\s*(?:TODO|FIXME)[:\s]+(.+)$", re.MULTILINE | re.IGNORECASE
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

    for py_file in sorted(repo_dir.rglob("*.py")):
        if _should_skip(py_file.parent):
            continue

        try:
            source = py_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        # --- AST pass: NotImplementedError with string message ---
        try:
            tree = ast.parse(source, filename=str(py_file))
        except SyntaxError:
            tree = None

        if tree is not None:
            for node in ast.walk(tree):
                if not isinstance(node, ast.Raise):
                    continue
                exc = node.exc
                if exc is None:
                    continue
                # Match: raise NotImplementedError("msg")
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
                        _add_claim(claim_text, "fact", py_file, node.lineno)

        # --- Regex pass: TODO / FIXME comments ---
        for match in todo_fixme_re.finditer(source):
            comment_text = match.group(1).strip()
            if not comment_text:
                continue
            # Compute line number from char offset
            lineno = source[: match.start()].count("\n") + 1
            claim_text = f"{product_name} has a known issue: {comment_text}"
            _add_claim(claim_text, "inference", py_file, lineno)

    return claims
