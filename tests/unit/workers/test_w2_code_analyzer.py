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
    parse_setup_py,
    extract_positioning_from_readme,
    analyze_repository_code,
    discover_source_files,
    discover_manifests,
    find_readme,
    detect_source_roots,
    analyze_file_safe,
    extract_code_limitations,
)


def _class_names(classes):
    """Helper to extract class names from class dicts or strings."""
    return [c["name"] if isinstance(c, dict) else c for c in classes]


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
    names = _class_names(result["classes"])
    assert "AnotherPublic" in names
    assert "PublicClass" in names
    assert "_PrivateClass" not in names
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
    names = _class_names(result["classes"])
    assert "MyClass" in names


def test_analyze_file_safe_javascript(tmp_path):
    """Test safe file analysis for JavaScript."""
    file_path = tmp_path / "test.js"
    file_path.write_text("class MyClass {}")

    result = analyze_file_safe(file_path)
    assert "MyClass" in result["classes"]  # JS returns strings


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
    class_names = _class_names(result["api_surface"]["classes"])
    assert "Scene" in class_names
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
    all_class_names = _class_names(result["api_surface"]["classes"])
    assert "CsClass" in all_class_names
    assert "JsClass" in all_class_names
    assert "PythonClass" in all_class_names


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


def test_analyze_python_file_extracts_class_methods(tmp_path):
    """Test that public methods within classes are extracted (Phase 3B5)."""
    file_path = tmp_path / "test.py"
    file_path.write_text("""
class Document:
    def load(self):
        pass

    def save(self):
        pass

    def _private_method(self):
        pass
    """)

    result = analyze_python_file(file_path)
    names = _class_names(result["classes"])
    assert "Document" in names
    assert "Document.load" in result["functions"]
    assert "Document.save" in result["functions"]
    # Private method excluded from public API
    assert "Document._private_method" not in result["functions"]


def test_analyze_python_file_private_only_methods(tmp_path):
    """Test classes with only private methods still get dunder methods extracted."""
    file_path = tmp_path / "test.py"
    file_path.write_text("""
class AutoBinding:
    def __init__(self):
        pass

    def _get_property(self):
        pass

    def _set_property(self, value):
        pass
    """)

    result = analyze_python_file(file_path)
    names = _class_names(result["classes"])
    assert "AutoBinding" in names
    # Should include __init__ as fallback since no public methods exist
    assert "AutoBinding.__init__" in result["functions"]


class TestEnrichedASTExtraction:
    """TC-1501: Tests for enriched AST extraction with docstrings, signatures, inheritance."""

    def test_extracts_docstrings(self, tmp_path):
        """Verify class docstrings are extracted."""
        file_path = tmp_path / "test.py"
        file_path.write_text(
            'class DataProcessor:\n'
            '    """Processes input data and produces results."""\n'
            '    pass\n'
        )
        result = analyze_python_file(file_path)
        assert len(result["classes"]) == 1
        cls = result["classes"][0]
        assert isinstance(cls, dict)
        assert cls["docstring"] == "Processes input data and produces results."

    def test_extracts_base_classes(self, tmp_path):
        """Verify base class names are extracted."""
        file_path = tmp_path / "test.py"
        file_path.write_text(
            'class BaseNode:\n'
            '    pass\n'
            '\n'
            'class DocumentNode(BaseNode):\n'
            '    pass\n'
        )
        result = analyze_python_file(file_path)
        doc_cls = next(c for c in result["classes"] if c["name"] == "DocumentNode")
        assert "BaseNode" in doc_cls["bases"]

    def test_extracts_method_signatures(self, tmp_path):
        """Verify method parameter names and types are extracted."""
        file_path = tmp_path / "test.py"
        file_path.write_text(
            'class Converter:\n'
            '    def convert(self, input_path: str, output_path: str) -> bool:\n'
            '        pass\n'
        )
        result = analyze_python_file(file_path)
        cls = result["classes"][0]
        assert len(cls["method_details"]) == 1
        m = cls["method_details"][0]
        assert m["name"] == "convert"
        assert "input_path" in m["signature"]
        assert "output_path" in m["signature"]

    def test_extracts_return_types(self, tmp_path):
        """Verify return type annotations are extracted."""
        file_path = tmp_path / "test.py"
        file_path.write_text(
            'class Reader:\n'
            '    def read(self, path: str) -> str:\n'
            '        pass\n'
        )
        result = analyze_python_file(file_path)
        m = result["classes"][0]["method_details"][0]
        assert m["return_type"] == "str"

    def test_class_format_is_dict(self, tmp_path):
        """Verify Python classes are returned as dicts with all fields."""
        file_path = tmp_path / "test.py"
        file_path.write_text('class MyClass:\n    pass\n')
        result = analyze_python_file(file_path)
        cls = result["classes"][0]
        assert isinstance(cls, dict)
        assert "name" in cls
        assert "docstring" in cls
        assert "bases" in cls
        assert "module" in cls
        assert "methods" in cls
        assert "method_details" in cls

    def test_method_docstrings(self, tmp_path):
        """Verify method docstrings are extracted."""
        file_path = tmp_path / "test.py"
        file_path.write_text(
            'class Writer:\n'
            '    def save(self, path: str):\n'
            '        """Save data to a file."""\n'
            '        pass\n'
        )
        result = analyze_python_file(file_path)
        m = result["classes"][0]["method_details"][0]
        assert m["docstring"] == "Save data to a file."

    def test_backward_compat_functions_still_strings(self, tmp_path):
        """Verify functions list remains flat strings for backward compat."""
        file_path = tmp_path / "test.py"
        file_path.write_text(
            'class Obj:\n'
            '    def method(self):\n'
            '        pass\n'
            'def standalone():\n'
            '    pass\n'
        )
        result = analyze_python_file(file_path)
        assert "Obj.method" in result["functions"]
        assert "standalone" in result["functions"]
        for f in result["functions"]:
            assert isinstance(f, str)


# ========== TC-1601: parse_setup_py tests ==========


def test_parse_setup_py_basic(tmp_path):
    """TC-1601: Parse a real setup.py with name, version, python_requires, install_requires=[]."""
    file_path = tmp_path / "setup.py"
    file_path.write_text("""
from setuptools import setup

setup(
    name="aspose-3d",
    version="26.1.0",
    python_requires=">=3.7",
    install_requires=[],
    description="Aspose.3D for Python via .NET",
)
    """)

    result = parse_setup_py(file_path)
    assert result["name"] == "aspose-3d"
    assert result["version"] == "26.1.0"
    assert result["python_requires"] == ">=3.7"
    assert result["install_requires"] == []
    assert result["description"] == "Aspose.3D for Python via .NET"


def test_parse_setup_py_no_file(tmp_path):
    """TC-1601: Non-existent file returns empty dict."""
    file_path = tmp_path / "nonexistent_setup.py"
    result = parse_setup_py(file_path)
    assert result == {}


def test_parse_setup_py_with_deps(tmp_path):
    """TC-1601: Parse setup.py with install_requires containing dependencies."""
    file_path = tmp_path / "setup.py"
    file_path.write_text("""
from setuptools import setup

setup(
    name="my-package",
    version="1.0.0",
    install_requires=["numpy>=1.20", "pandas"],
    extras_require={
        "dev": ["pytest", "flake8"],
        "docs": ["sphinx"],
    },
)
    """)

    result = parse_setup_py(file_path)
    assert result["name"] == "my-package"
    assert result["version"] == "1.0.0"
    assert "numpy>=1.20" in result["install_requires"]
    assert "pandas" in result["install_requires"]
    assert len(result["install_requires"]) == 2
    # extras_require
    assert "dev" in result["extras_require"]
    assert "pytest" in result["extras_require"]["dev"]
    assert "docs" in result["extras_require"]
    assert "sphinx" in result["extras_require"]["docs"]


def test_parse_setup_py_syntax_error(tmp_path):
    """TC-1601: Malformed file returns empty dict without crashing."""
    file_path = tmp_path / "setup.py"
    file_path.write_text("this is not valid python @@@ !!!")

    result = parse_setup_py(file_path)
    assert result == {}


def test_parse_setup_py_no_setup_call(tmp_path):
    """TC-1601: File without setup() call returns empty dict."""
    file_path = tmp_path / "setup.py"
    file_path.write_text("""
# This file doesn't call setup()
x = 42
print("hello")
    """)

    result = parse_setup_py(file_path)
    assert result == {}


def test_parse_setup_py_setuptools_style(tmp_path):
    """TC-1601: Parse setuptools.setup() call (dotted attribute)."""
    file_path = tmp_path / "setup.py"
    file_path.write_text("""
import setuptools

setuptools.setup(
    name="dotted-package",
    version="2.0.0",
    python_requires=">=3.8",
)
    """)

    result = parse_setup_py(file_path)
    assert result["name"] == "dotted-package"
    assert result["version"] == "2.0.0"
    assert result["python_requires"] == ">=3.8"


# ========== TC-1605: extract_code_limitations tests ==========


class TestExtractCodeLimitations:
    """TC-1605: Tests for limitation extraction from source code patterns."""

    def test_extract_not_implemented_error(self, tmp_path):
        """NotImplementedError with message string becomes a limitation claim."""
        src = tmp_path / "module.py"
        src.write_text(
            'class Foo:\n'
            '    def bar(self):\n'
            '        raise NotImplementedError("animation export")\n'
        )
        claims = extract_code_limitations(tmp_path, "TestProduct")
        assert len(claims) >= 1
        assert any("animation export" in c["claim_text"] for c in claims)
        assert all(c["claim_kind"] == "limitation" for c in claims)
        # NotImplementedError is a fact (code proves it)
        nie_claims = [c for c in claims if "animation export" in c["claim_text"]]
        assert nie_claims[0]["truth_status"] == "fact"

    def test_extract_todo_comment(self, tmp_path):
        """TODO comments become inference limitation claims."""
        src = tmp_path / "module.py"
        src.write_text(
            '# TODO: implement FBX binary export\n'
            'def placeholder():\n'
            '    pass\n'
        )
        claims = extract_code_limitations(tmp_path, "TestProduct")
        assert len(claims) >= 1
        assert any("FBX binary export" in c["claim_text"] for c in claims)
        todo_claims = [c for c in claims if "FBX binary export" in c["claim_text"]]
        assert todo_claims[0]["truth_status"] == "inference"

    def test_extract_fixme_comment(self, tmp_path):
        """FIXME comments also become limitation claims."""
        src = tmp_path / "module.py"
        src.write_text(
            '# FIXME: handle unicode filenames properly\n'
            'def read_file(path):\n'
            '    pass\n'
        )
        claims = extract_code_limitations(tmp_path, "TestProduct")
        assert len(claims) >= 1
        assert any("unicode filenames" in c["claim_text"] for c in claims)

    def test_dedup_similar_limitations(self, tmp_path):
        """Duplicate limitation messages are deduplicated."""
        src1 = tmp_path / "a.py"
        src1.write_text('raise NotImplementedError("feature X")\n')
        src2 = tmp_path / "b.py"
        src2.write_text('raise NotImplementedError("feature X")\n')
        claims = extract_code_limitations(tmp_path, "TestProduct")
        texts = [c["claim_text"] for c in claims]
        # Should be deduplicated to 1
        assert len([t for t in texts if "feature X" in t]) == 1

    def test_no_source_files(self, tmp_path):
        """Empty directory returns empty list."""
        claims = extract_code_limitations(tmp_path, "TestProduct")
        assert claims == []

    def test_skips_test_directories(self, tmp_path):
        """Files under test/ or tests/ directories are skipped."""
        test_dir = tmp_path / "tests"
        test_dir.mkdir()
        src = test_dir / "test_module.py"
        src.write_text(
            '# TODO: add more test cases\n'
            'raise NotImplementedError("test stub")\n'
        )
        claims = extract_code_limitations(tmp_path, "TestProduct")
        assert claims == []

    def test_skips_pycache(self, tmp_path):
        """Files under __pycache__ are skipped."""
        cache_dir = tmp_path / "__pycache__"
        cache_dir.mkdir()
        src = cache_dir / "module.py"
        src.write_text('raise NotImplementedError("cached")\n')
        claims = extract_code_limitations(tmp_path, "TestProduct")
        assert claims == []

    def test_claim_structure(self, tmp_path):
        """Each claim has all required fields with correct types."""
        src = tmp_path / "module.py"
        src.write_text('raise NotImplementedError("streaming mode")\n')
        claims = extract_code_limitations(tmp_path, "TestProduct")
        assert len(claims) == 1
        claim = claims[0]
        assert "claim_id" in claim and isinstance(claim["claim_id"], str)
        assert claim["claim_kind"] == "limitation"
        assert claim["confidence"] == "medium"
        assert claim["source_type"] == "source_code"
        assert claim["source_priority"] == 2
        assert claim["source_relevance"] == 70
        assert isinstance(claim["citations"], list)
        assert len(claim["citations"]) == 1
        citation = claim["citations"][0]
        assert "path" in citation
        assert "start_line" in citation
        assert "end_line" in citation
        assert citation["source_type"] == "source_code"

    def test_handles_syntax_errors_gracefully(self, tmp_path):
        """Files with syntax errors don't crash; TODO comments still extracted."""
        src = tmp_path / "broken.py"
        src.write_text(
            '# TODO: fix this broken syntax\n'
            'def incomplete(\n'
        )
        claims = extract_code_limitations(tmp_path, "TestProduct")
        # The TODO comment should still be extracted via regex even though AST fails
        assert len(claims) >= 1
        assert any("fix this broken syntax" in c["claim_text"] for c in claims)

    def test_not_implemented_error_without_message_ignored(self, tmp_path):
        """NotImplementedError without a string message is ignored."""
        src = tmp_path / "module.py"
        src.write_text(
            'raise NotImplementedError\n'
            'raise NotImplementedError()\n'
        )
        claims = extract_code_limitations(tmp_path, "TestProduct")
        # Neither bare raise nor empty-args should produce claims
        assert claims == []

    def test_mixed_sources(self, tmp_path):
        """File with both NotImplementedError and TODO produces multiple claims."""
        src = tmp_path / "module.py"
        src.write_text(
            '# TODO: optimize batch processing\n'
            'class Exporter:\n'
            '    def export_glb(self):\n'
            '        raise NotImplementedError("GLB binary export")\n'
        )
        claims = extract_code_limitations(tmp_path, "TestProduct")
        assert len(claims) == 2
        texts = [c["claim_text"] for c in claims]
        assert any("optimize batch processing" in t for t in texts)
        assert any("GLB binary export" in t for t in texts)
