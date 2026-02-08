"""TC-1041: Unit tests for code_analyzer module."""

import pytest
from pathlib import Path
import time
from src.launch.workers.w2_facts_builder.code_analyzer import (
    analyze_python_file,
    analyze_javascript_file,
    analyze_csharp_file,
    parse_pyproject_toml,
    parse_package_json,
    extract_positioning_from_readme,
    analyze_repository_code,
    discover_source_files,
    discover_manifests,
    find_readme,
    detect_source_roots,
    analyze_file_safe,
)


def test_analyze_python_file_extracts_classes(tmp_path):
    """Test Python AST extracts public classes."""
    file_path = tmp_path / "test.py"
    file_path.write_text("""
class PublicClass:
    pass

class AnotherPublic:
    pass

class _PrivateClass:  # Should be excluded
    pass
    """)

    result = analyze_python_file(file_path)
    assert "AnotherPublic" in result["classes"]
    assert "PublicClass" in result["classes"]
    assert "_PrivateClass" not in result["classes"]
    assert len(result["classes"]) == 2


def test_analyze_python_file_extracts_functions(tmp_path):
    """Test Python AST extracts public functions."""
    file_path = tmp_path / "test.py"
    file_path.write_text("""
def public_function():
    pass

def another_public():
    pass

def _private_function():  # Should be excluded
    pass
    """)

    result = analyze_python_file(file_path)
    assert "another_public" in result["functions"]
    assert "public_function" in result["functions"]
    assert "_private_function" not in result["functions"]
    assert len(result["functions"]) == 2


def test_analyze_python_file_extracts_constants(tmp_path):
    """Test Python AST extracts constants."""
    file_path = tmp_path / "test.py"
    file_path.write_text("""
__version__ = "1.2.3"
SUPPORTED_FORMATS = ["OBJ", "STL", "FBX"]
MAX_SIZE = 1024
lowercase_var = "not_a_constant"  # Should be excluded
    """)

    result = analyze_python_file(file_path)
    assert result["constants"]["__version__"] == "1.2.3"
    assert result["constants"]["SUPPORTED_FORMATS"] == ["OBJ", "STL", "FBX"]
    assert result["constants"]["MAX_SIZE"] == 1024
    assert "lowercase_var" not in result["constants"]


def test_analyze_python_file_handles_syntax_errors(tmp_path):
    """Test graceful fallback on syntax errors."""
    file_path = tmp_path / "broken.py"
    file_path.write_text("class Broken\n  invalid syntax here!!!")

    result = analyze_python_file(file_path)
    assert result["classes"] == []  # Should not crash
    assert result["functions"] == []
    assert result["constants"] == {}


def test_analyze_python_file_skips_non_literal_constants(tmp_path):
    """Test that non-literal constants are skipped."""
    file_path = tmp_path / "test.py"
    file_path.write_text("""
VALID = "string"
INVALID = some_function_call()  # Cannot be evaluated
COMPLEX = [x for x in range(10)]  # Cannot be evaluated
    """)

    result = analyze_python_file(file_path)
    assert result["constants"]["VALID"] == "string"
    assert "INVALID" not in result["constants"]
    assert "COMPLEX" not in result["constants"]


def test_analyze_javascript_file_extracts_classes(tmp_path):
    """Test JavaScript regex extracts classes."""
    file_path = tmp_path / "test.js"
    file_path.write_text("""
class MyClass {
    constructor() {}
}

class AnotherClass {
    method() {}
}

function notAClass() {}
    """)

    result = analyze_javascript_file(file_path)
    assert "AnotherClass" in result["classes"]
    assert "MyClass" in result["classes"]
    assert len(result["classes"]) == 2


def test_analyze_javascript_file_extracts_functions(tmp_path):
    """Test JavaScript regex extracts functions."""
    file_path = tmp_path / "test.js"
    file_path.write_text("""
function myFunction() {}
const anotherFunc = function() {}
let yetAnother = () => {}
    """)

    result = analyze_javascript_file(file_path)
    assert "anotherFunc" in result["functions"]
    assert "myFunction" in result["functions"]
    assert "yetAnother" in result["functions"]


def test_analyze_csharp_file_extracts_classes(tmp_path):
    """Test C# regex extracts public classes."""
    file_path = tmp_path / "test.cs"
    file_path.write_text("""
public class MyClass {
    public void Method() {}
}

public class AnotherClass {
}

private class PrivateClass {  // Should be excluded
}
    """)

    result = analyze_csharp_file(file_path)
    assert "AnotherClass" in result["classes"]
    assert "MyClass" in result["classes"]
    assert "PrivateClass" not in result["classes"]


def test_analyze_csharp_file_extracts_methods(tmp_path):
    """Test C# regex extracts public methods."""
    file_path = tmp_path / "test.cs"
    file_path.write_text("""
public class MyClass {
    public void PublicMethod() {}
    public string AnotherMethod() {}
    private void PrivateMethod() {}  // Should be excluded
}
    """)

    result = analyze_csharp_file(file_path)
    assert "AnotherMethod" in result["functions"]
    assert "PublicMethod" in result["functions"]


def test_parse_pyproject_toml(tmp_path):
    """Test pyproject.toml parsing."""
    file_path = tmp_path / "pyproject.toml"
    file_path.write_text("""
[project]
name = "test-package"
version = "1.0.0"
description = "A test package"
dependencies = ["requests", "numpy"]

[project.scripts]
mycommand = "mypackage.main:run"
    """)

    result = parse_pyproject_toml(file_path)
    assert result["name"] == "test-package"
    assert result["version"] == "1.0.0"
    assert result["description"] == "A test package"
    assert "requests" in result["dependencies"]
    assert "numpy" in result["dependencies"]
    assert "mycommand" in result["entrypoints"]


def test_parse_pyproject_toml_missing_fields(tmp_path):
    """Test pyproject.toml with missing fields."""
    file_path = tmp_path / "pyproject.toml"
    file_path.write_text("""
[project]
name = "minimal-package"
    """)

    result = parse_pyproject_toml(file_path)
    assert result["name"] == "minimal-package"
    assert result["version"] is None
    assert result["dependencies"] == []


def test_parse_package_json(tmp_path):
    """Test package.json parsing."""
    file_path = tmp_path / "package.json"
    file_path.write_text("""
{
  "name": "test-package",
  "version": "2.0.0",
  "description": "A test JavaScript package",
  "dependencies": {
    "express": "^4.17.1",
    "lodash": "^4.17.21"
  }
}
    """)

    result = parse_package_json(file_path)
    assert result["name"] == "test-package"
    assert result["version"] == "2.0.0"
    assert result["description"] == "A test JavaScript package"
    assert "express" in result["dependencies"]
    assert "lodash" in result["dependencies"]


def test_extract_positioning_from_readme(tmp_path):
    """Test README positioning extraction."""
    file_path = tmp_path / "README.md"
    file_path.write_text("""
# Awesome 3D Library

A powerful library for 3D processing and manipulation.

## Features

- Feature 1
- Feature 2
    """)

    result = extract_positioning_from_readme(file_path)
    assert result["tagline"] == "Awesome 3D Library"
    assert result["short_description"] == "A powerful library for 3D processing and manipulation."


def test_extract_positioning_handles_empty_lines(tmp_path):
    """Test README extraction with empty lines after H1."""
    file_path = tmp_path / "README.md"
    file_path.write_text("""
# My Package


This is the description after empty lines.
    """)

    result = extract_positioning_from_readme(file_path)
    assert result["tagline"] == "My Package"
    assert result["short_description"] == "This is the description after empty lines."


def test_extract_positioning_no_h1(tmp_path):
    """Test README extraction without H1."""
    file_path = tmp_path / "README.md"
    file_path.write_text("""
This is just text without a heading.
    """)

    result = extract_positioning_from_readme(file_path)
    assert result["tagline"] == ""
    assert result["short_description"] == ""


def test_discover_source_files_prioritizes_src(tmp_path):
    """Test that source file discovery prioritizes src/ directory."""
    # Create files in different directories
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "lib").mkdir()

    (tmp_path / "src" / "main.py").write_text("# src file")
    (tmp_path / "tests" / "test.py").write_text("# test file")
    (tmp_path / "lib" / "lib.py").write_text("# lib file")
    (tmp_path / "root.py").write_text("# root file")

    files = discover_source_files(tmp_path, max_files=100)

    # src/ should come first
    assert files[0].name == "main.py"
    assert "src" in files[0].parts


def test_discover_manifests(tmp_path):
    """Test manifest discovery."""
    (tmp_path / "pyproject.toml").write_text("[project]")
    (tmp_path / "package.json").write_text("{}")

    manifests = discover_manifests(tmp_path)
    manifest_names = [m.name for m in manifests]

    assert "pyproject.toml" in manifest_names
    assert "package.json" in manifest_names


def test_find_readme(tmp_path):
    """Test README discovery."""
    (tmp_path / "README.md").write_text("# README")

    readme = find_readme(tmp_path)
    assert readme is not None
    assert readme.name == "README.md"


def test_find_readme_no_file(tmp_path):
    """Test README discovery when file doesn't exist."""
    readme = find_readme(tmp_path)
    assert readme is None


def test_detect_source_roots(tmp_path):
    """Test source root detection."""
    (tmp_path / "src").mkdir()
    (tmp_path / "lib").mkdir()

    roots = detect_source_roots(tmp_path)
    assert "src/" in roots
    assert "lib/" in roots


def test_detect_source_roots_fallback(tmp_path):
    """Test source root detection fallback to root."""
    roots = detect_source_roots(tmp_path)
    assert roots == ["."]


def test_analyze_file_safe_python(tmp_path):
    """Test safe file analysis for Python."""
    file_path = tmp_path / "test.py"
    file_path.write_text("class MyClass:\n    pass")

    result = analyze_file_safe(file_path)
    assert "MyClass" in result["classes"]


def test_analyze_file_safe_javascript(tmp_path):
    """Test safe file analysis for JavaScript."""
    file_path = tmp_path / "test.js"
    file_path.write_text("class MyClass {}")

    result = analyze_file_safe(file_path)
    assert "MyClass" in result["classes"]


def test_analyze_file_safe_unknown_extension(tmp_path):
    """Test safe file analysis for unknown extension."""
    file_path = tmp_path / "test.txt"
    file_path.write_text("some text")

    result = analyze_file_safe(file_path)
    assert result == {}


def test_analyze_repository_code_integration(tmp_path):
    """Test full repository analysis."""
    # Create synthetic repo
    src_dir = tmp_path / "src"
    src_dir.mkdir()

    (src_dir / "__init__.py").write_text("""
__version__ = "2.0.0"
SUPPORTED_FORMATS = ["OBJ", "STL"]

class Scene:
    pass

def load(path):
    pass
    """)

    (tmp_path / "README.md").write_text("# Test Package\n\nA test package for 3D processing.")

    (tmp_path / "pyproject.toml").write_text("""
[project]
name = "test-package"
version = "2.0.0"
description = "A test package"
    """)

    result = analyze_repository_code(tmp_path, {}, "TestPackage")

    # Check API surface
    assert "Scene" in result["api_surface"]["classes"]
    assert "load" in result["api_surface"]["functions"]

    # Check constants
    assert result["constants"]["version"] == "2.0.0"
    assert "OBJ" in result["constants"]["supported_formats"]

    # Check positioning
    assert result["positioning"]["tagline"] == "Test Package"
    assert "test package" in result["positioning"]["short_description"].lower()

    # Check code structure
    assert "src/" in result["code_structure"]["source_roots"]
    assert result["code_structure"]["package_names"] == ["test-package"]

    # Check metadata
    assert result["metadata"]["files_analyzed"] >= 1
    assert result["metadata"]["parsing_failures"] >= 0


def test_analyze_repository_code_fallback_to_manifest_description(tmp_path):
    """Test positioning fallback to manifest description when no README."""
    src_dir = tmp_path / "src"
    src_dir.mkdir()

    (src_dir / "main.py").write_text("class MyClass:\n    pass")

    (tmp_path / "pyproject.toml").write_text("""
[project]
name = "test-package"
version = "1.0.0"
description = "Manifest description fallback"
    """)

    result = analyze_repository_code(tmp_path, {}, "TestPackage")

    # Should use manifest description as fallback
    assert result["positioning"]["short_description"] == "Manifest description fallback"


def test_analyze_repository_code_handles_no_source_files(tmp_path):
    """Test repository analysis with no source files."""
    result = analyze_repository_code(tmp_path, {}, "EmptyRepo")

    # Should return empty but valid structure
    assert result["api_surface"]["classes"] == []
    assert result["api_surface"]["functions"] == []
    assert result["metadata"]["files_analyzed"] == 0


def test_performance_budget(tmp_path):
    """Test that analysis completes within performance budget (< 3 seconds for 100 files)."""
    # Create 100 small Python files
    src_dir = tmp_path / "src"
    src_dir.mkdir()

    for i in range(100):
        file_path = src_dir / f"module_{i}.py"
        file_path.write_text(f"""
class Class{i}:
    pass

def function_{i}():
    pass

CONSTANT_{i} = {i}
        """)

    start_time = time.time()
    result = analyze_repository_code(tmp_path, {}, "PerfTest", max_files=100)
    duration = time.time() - start_time

    # Should complete in < 3 seconds
    assert duration < 3.0, f"Analysis took {duration:.2f}s, expected < 3.0s"

    # Should have analyzed all 100 files
    assert result["metadata"]["files_analyzed"] == 100


def test_analyze_repository_code_with_multiple_languages(tmp_path):
    """Test repository with Python, JavaScript, and C# files."""
    (tmp_path / "src").mkdir()

    (tmp_path / "src" / "main.py").write_text("class PythonClass:\n    pass")
    (tmp_path / "src" / "app.js").write_text("class JsClass {}")
    (tmp_path / "src" / "lib.cs").write_text("public class CsClass {}")

    result = analyze_repository_code(tmp_path, {}, "MultiLang")

    # Should extract from all languages
    all_classes = result["api_surface"]["classes"]
    assert "CsClass" in all_classes
    assert "JsClass" in all_classes
    assert "PythonClass" in all_classes


def test_extract_modules_from_init_with_all(tmp_path):
    """Test module extraction from __all__ assignment."""
    init_file = tmp_path / "__init__.py"
    init_file.write_text("__all__ = ['module_a', 'module_b', 'module_c']")

    from src.launch.workers.w2_facts_builder.code_analyzer import _extract_modules_from_init
    result = _extract_modules_from_init(init_file)

    assert result == ['module_a', 'module_b', 'module_c']


def test_extract_modules_from_imports(tmp_path):
    """Test module extraction from import statements."""
    init_file = tmp_path / "__init__.py"
    init_file.write_text("""
import module_x
from module_y import something
from module_z.submodule import other
""")

    from src.launch.workers.w2_facts_builder.code_analyzer import _extract_modules_from_init
    result = _extract_modules_from_init(init_file)

    assert set(result) == {'module_x', 'module_y', 'module_z'}


def test_detect_public_entrypoints_main_py(tmp_path):
    """Test entrypoint detection with __main__.py."""
    source_root = tmp_path / "src"
    source_root.mkdir()
    (source_root / "__init__.py").touch()
    (source_root / "__main__.py").touch()

    from src.launch.workers.w2_facts_builder.code_analyzer import _detect_public_entrypoints
    result = _detect_public_entrypoints(tmp_path, ["src/"])

    assert '__init__.py' in result
    assert '__main__.py' in result
