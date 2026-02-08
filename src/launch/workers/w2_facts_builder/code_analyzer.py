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


def analyze_python_file(file_path: Path) -> Dict[str, Any]:
    """Analyze Python file using AST.

    Returns:
        {
            "classes": ["ClassName1", ...],  # Public classes only
            "functions": ["function1", ...],  # Public functions only
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

    for node in ast.walk(tree):
        # Extract public classes
        if isinstance(node, ast.ClassDef):
            if not node.name.startswith('_'):
                classes.append(node.name)

        # Extract public functions
        elif isinstance(node, ast.FunctionDef):
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
        "classes": sorted(set(classes)),  # Deduplicate and sort
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

    # Build result
    return {
        "api_surface": {
            "classes": sorted(set(all_classes)),
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
