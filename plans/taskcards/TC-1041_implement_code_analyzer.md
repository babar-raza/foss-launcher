---
id: TC-1041
title: Implement code analyzer module
status: Draft
created: 2026-02-07
updated: 2026-02-07
owner: Agent-B
phase: Phase 1 - Code Analysis
spec_ref: 46d7ac2dd11d8cf92e49fb3d27b8d7aa6f9c2785
ruleset_version: ruleset.v1
templates_version: templates.v1
allowed_paths:
  - src/launch/workers/w2_facts_builder/code_analyzer.py
  - tests/unit/workers/test_w2_code_analyzer.py
---

# TC-1041: Implement code analyzer module

## Objective

Implement the code analyzer module (`code_analyzer.py`) that performs AST parsing, manifest parsing, and constant extraction to populate `api_surface_summary`, `code_structure`, and `positioning` fields in `product_facts.json`.

This is Phase 1 of W2 intelligence enhancements.

## Required spec references

- `specs/07_code_analysis_and_enrichment.md` — Code analysis specification (NEW, from TC-1040)
- `specs/03_product_facts_and_evidence.md` — ProductFacts requirements (updated in TC-1040)
- `specs/schemas/product_facts.schema.json` — ProductFacts schema (updated in TC-1040)

## Scope

### In scope
1. Create `src/launch/workers/w2_facts_builder/code_analyzer.py` with:
   - `analyze_repository_code()` — Main entry point
   - `analyze_python_file()` — Python AST parsing
   - `analyze_javascript_file()` — JavaScript regex-based parsing (MVP)
   - `analyze_csharp_file()` — C# regex-based parsing (MVP)
   - `parse_pyproject_toml()` — pyproject.toml manifest parsing
   - `parse_package_json()` — package.json manifest parsing
   - `extract_positioning_from_readme()` — README positioning extraction
   - Helper functions for constant extraction, API surface, code structure

2. Implement Python AST parsing:
   - Extract public classes (no `_` prefix)
   - Extract public functions (no `_` prefix)
   - Extract constants (`UPPERCASE` variables with `ast.literal_eval`)
   - Graceful error handling for syntax errors

3. Implement manifest parsing:
   - pyproject.toml: Use `tomllib` (Python 3.11+) or `toml` package
   - package.json: Use `json.loads()`
   - Extract: name, version, description, dependencies, entrypoints

4. Implement positioning extraction:
   - Parse README.md first 2000 chars
   - Extract tagline from first H1 (`# Tagline`)
   - Extract description from next non-empty line
   - Fallback to manifest description if no README

5. Create unit tests:
   - `tests/unit/workers/test_w2_code_analyzer.py`
   - Test Python AST extraction (classes, functions, constants)
   - Test manifest parsing (pyproject.toml, package.json)
   - Test syntax error handling (graceful fallback)
   - Test positioning extraction
   - Test performance (< 3 seconds for 100 files)

### Out of scope
- Integration into W2 worker (TC-1042)
- Workflow enrichment (TC-1043, TC-1044)
- LLM claim enrichment (TC-1045, TC-1046)
- Pilot verification (TC-1049)

## Inputs

- `specs/07_code_analysis_and_enrichment.md` — Implementation specification
- `specs/schemas/product_facts.schema.json` — Output schema
- W3 SnippetCurator code (reference for AST parsing patterns)

## Outputs

1. NEW `src/launch/workers/w2_facts_builder/code_analyzer.py` (~500-700 lines)
2. NEW `tests/unit/workers/test_w2_code_analyzer.py` (~300-400 lines)
3. Evidence bundle: `reports/agents/agent_b/TC-1041/evidence.md`
4. Self-review: `reports/agents/agent_b/TC-1041/self_review.md`

## Allowed paths

- `src/launch/workers/w2_facts_builder/code_analyzer.py` (NEW)
- `tests/unit/workers/test_w2_code_analyzer.py` (NEW)

### Allowed paths rationale
Single-purpose module creation with corresponding tests. No modifications to shared libraries or existing W2 worker code (handled in TC-1042).

## Preconditions / dependencies

- **Depends on:** TC-1040 (specs must be updated first)
- Python 3.11+ available (for `tomllib`) or `toml` package installed
- AST module available (stdlib)

## Implementation steps

### Step 1: Create code_analyzer.py skeleton

1.1. Create file: `src/launch/workers/w2_facts_builder/code_analyzer.py`

1.2. Add module docstring and imports:
```python
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
```

### Step 2: Implement Python AST parsing

2.1. Implement `analyze_python_file()`:
```python
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
```

### Step 3: Implement JavaScript/C# regex parsing

3.1. Implement `analyze_javascript_file()`:
```python
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
```

3.2. Implement `analyze_csharp_file()`:
```python
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
```

### Step 4: Implement manifest parsing

4.1. Implement `parse_pyproject_toml()`:
```python
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
```

4.2. Implement `parse_package_json()`:
```python
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
```

### Step 5: Implement positioning extraction

5.1. Implement `extract_positioning_from_readme()`:
```python
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
```

### Step 6: Implement main entry point

6.1. Implement `analyze_repository_code()`:
```python
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
    source_files = _discover_source_files(repo_dir, max_files)

    # Discover manifests
    manifests = _discover_manifests(repo_dir)

    # Discover README
    readme_path = _find_readme(repo_dir)

    # Analyze files in parallel
    all_classes = []
    all_functions = []
    all_constants = {}
    parsing_failures = 0

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {}
        for file_path in source_files:
            future = executor.submit(_analyze_file_safe, file_path)
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

    # Build result
    return {
        "api_surface": {
            "classes": sorted(set(all_classes)),
            "functions": sorted(set(all_functions)),
            "modules": [],  # TODO: Extract from __init__.py imports
        },
        "code_structure": {
            "source_roots": _detect_source_roots(repo_dir),
            "public_entrypoints": ["__init__.py"],  # TODO: Detect dynamically
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
```

### Step 7: Implement helper functions

7.1. Implement helper functions:
```python
def _discover_source_files(repo_dir: Path, max_files: int) -> List[Path]:
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

def _discover_manifests(repo_dir: Path) -> List[Path]:
    """Find manifest files."""
    manifests = []
    for name in ["pyproject.toml", "package.json", "*.csproj"]:
        manifests.extend(repo_dir.glob(name))
    return manifests

def _find_readme(repo_dir: Path) -> Optional[Path]:
    """Find README file."""
    for name in ["README.md", "README.rst", "README.txt", "README"]:
        readme = repo_dir / name
        if readme.exists():
            return readme
    return None

def _detect_source_roots(repo_dir: Path) -> List[str]:
    """Detect source code root directories."""
    roots = []
    for candidate in ["src/", "lib/", "pkg/"]:
        if (repo_dir / candidate).exists():
            roots.append(candidate)
    return roots or ["."]  # Fallback to repo root

def _analyze_file_safe(file_path: Path) -> Dict[str, Any]:
    """Analyze file with error handling."""
    ext = file_path.suffix.lower()
    if ext == ".py":
        return analyze_python_file(file_path)
    elif ext == ".js":
        return analyze_javascript_file(file_path)
    elif ext == ".cs":
        return analyze_csharp_file(file_path)
    return {}
```

### Step 8: Create unit tests

8.1. Create `tests/unit/workers/test_w2_code_analyzer.py`:
```python
"""TC-1041: Unit tests for code_analyzer module."""

import pytest
from pathlib import Path
from src.launch.workers.w2_facts_builder.code_analyzer import (
    analyze_python_file,
    analyze_javascript_file,
    analyze_csharp_file,
    parse_pyproject_toml,
    parse_package_json,
    extract_positioning_from_readme,
    analyze_repository_code,
)

def test_analyze_python_file_extracts_classes(tmp_path):
    """Test Python AST extracts public classes."""
    file_path = tmp_path / "test.py"
    file_path.write_text("""
class PublicClass:
    pass

class _PrivateClass:  # Should be excluded
    pass
    """)

    result = analyze_python_file(file_path)
    assert "PublicClass" in result["classes"]
    assert "_PrivateClass" not in result["classes"]

def test_analyze_python_file_extracts_constants(tmp_path):
    """Test Python AST extracts constants."""
    file_path = tmp_path / "test.py"
    file_path.write_text("""
__version__ = "1.2.3"
SUPPORTED_FORMATS = ["OBJ", "STL"]
    """)

    result = analyze_python_file(file_path)
    assert result["constants"]["__version__"] == "1.2.3"
    assert result["constants"]["SUPPORTED_FORMATS"] == ["OBJ", "STL"]

def test_analyze_python_file_handles_syntax_errors(tmp_path):
    """Test graceful fallback on syntax errors."""
    file_path = tmp_path / "broken.py"
    file_path.write_text("class Broken\n  invalid syntax")

    result = analyze_python_file(file_path)
    assert result["classes"] == []  # Should not crash

def test_parse_pyproject_toml(tmp_path):
    """Test pyproject.toml parsing."""
    file_path = tmp_path / "pyproject.toml"
    file_path.write_text("""
[project]
name = "test-package"
version = "1.0.0"
description = "A test package"
    """)

    result = parse_pyproject_toml(file_path)
    assert result["name"] == "test-package"
    assert result["version"] == "1.0.0"
    assert result["description"] == "A test package"

def test_extract_positioning_from_readme(tmp_path):
    """Test README positioning extraction."""
    file_path = tmp_path / "README.md"
    file_path.write_text("""
# Awesome 3D Library

A powerful library for 3D processing.
    """)

    result = extract_positioning_from_readme(file_path)
    assert result["tagline"] == "Awesome 3D Library"
    assert result["short_description"] == "A powerful library for 3D processing."

def test_analyze_repository_code_integration(tmp_path):
    """Test full repository analysis."""
    # Create synthetic repo
    (tmp_path / "src" / "__init__.py").parent.mkdir(parents=True)
    (tmp_path / "src" / "__init__.py").write_text("""
__version__ = "2.0.0"
SUPPORTED_FORMATS = ["OBJ", "STL"]

class Scene:
    pass
    """)

    (tmp_path / "README.md").write_text("# Test Package\n\nA test package.")

    result = analyze_repository_code(tmp_path, {}, "TestPackage")

    assert "Scene" in result["api_surface"]["classes"]
    assert result["constants"]["version"] == "2.0.0"
    assert "OBJ" in result["constants"]["supported_formats"]
    assert result["positioning"]["tagline"] == "Test Package"
```

### Step 9: Test and verify

9.1. Run unit tests:
```bash
.venv/Scripts/python.exe -m pytest tests/unit/workers/test_w2_code_analyzer.py -v
```

9.2. Verify performance (< 3 seconds for 100 files):
```bash
.venv/Scripts/python.exe -m pytest tests/unit/workers/test_w2_code_analyzer.py::test_performance_budget -v
```

## Failure modes

1. **Python AST parsing fails on valid Python 2 code**
   - Detection: SyntaxError exceptions logged
   - Resolution: Treat as graceful fallback, return empty result
   - Gate: Unit tests verify fallback behavior

2. **Regex patterns miss complex JavaScript/C# syntax**
   - Detection: API surface incomplete compared to manual inspection
   - Resolution: Document as known limitation, add esprima/Tree-sitter in future
   - Gate: Acceptance criteria specify "~80% coverage for JS/C#"

3. **Performance budget exceeded (> 3 seconds)**
   - Detection: Performance test fails
   - Resolution: Reduce max_files, increase timeout, optimize parallel processing
   - Gate: Performance test in test suite

## Task-specific review checklist

1. All public classes extracted (no `_` prefix)
2. All public functions extracted (no `_` prefix)
3. Constants extracted correctly (UPPERCASE, __version__)
4. Syntax errors handled gracefully (no crashes)
5. Manifest parsing works for pyproject.toml and package.json
6. README positioning extraction works
7. Performance budget met (< 3 seconds for 100 files)
8. All unit tests pass

## Deliverables

1. NEW `src/launch/workers/w2_facts_builder/code_analyzer.py` (~600 lines)
2. NEW `tests/unit/workers/test_w2_code_analyzer.py` (~350 lines)
3. Evidence bundle: `reports/agents/agent_b/TC-1041/evidence.md`
4. Self-review: `reports/agents/agent_b/TC-1041/self_review.md`

## Acceptance checks

- [ ] code_analyzer.py created with all functions implemented
- [ ] Python AST parsing works (classes, functions, constants)
- [ ] Manifest parsing works (pyproject.toml, package.json)
- [ ] Positioning extraction works (README)
- [ ] Syntax errors handled gracefully
- [ ] All unit tests pass (>= 10 tests)
- [ ] Performance budget met (< 3 seconds for 100 files)
- [ ] Evidence bundle includes test results

## Self-review

Will be completed by Agent B upon execution.
