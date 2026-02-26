"""TC-2870: Tests for shared code_fence_validator library.

Covers:
- build_symbol_lookups: imports, classes, methods, functions, properties
- build_type_bindings: aliases, constructor assignments, reassignment
- validate_code_fence: imports, methods, constructors, builtins, pseudocode
- extract_python_code_fences: extraction from markdown
"""

from __future__ import annotations

import ast
import pytest

from src.launch.workers._shared.code_fence_validator import (
    build_symbol_lookups,
    build_type_bindings,
    validate_code_fence,
    extract_python_code_fences,
    CodeFenceIssue,
    STDLIB_IMPORT_ALLOWLIST,
    BUILTIN_CLASSES,
    PYTHON_FENCE_RE,
)


def _sample_inventory() -> dict:
    return {
        "package_name": "aspose-3d",
        "import_roots": ["aspose"],
        "classes": [
            {
                "name": "Scene",
                "import_path": "aspose.threed.Scene",
                "module": "scene",
                "methods": ["open", "save", "merge_scene"],
                "properties": ["root_node", "library"],
                "bases": [],
            },
            {
                "name": "Mesh",
                "import_path": "aspose.threed.entities.Mesh",
                "module": "mesh",
                "methods": ["create_polygon", "to_mesh"],
                "properties": [],
                "bases": [],
            },
        ],
        "functions": ["configure_logging"],
        "modules": ["aspose", "aspose.threed", "aspose.threed.entities"],
    }


class TestBuildSymbolLookups:
    def test_returns_4_tuple(self):
        result = build_symbol_lookups(_sample_inventory())
        assert len(result) == 4

    def test_package_variants(self):
        ki, _, _, _ = build_symbol_lookups(_sample_inventory())
        assert "aspose-3d" in ki
        assert "aspose.3d" in ki
        assert "aspose_3d" in ki

    def test_classes_and_methods(self):
        _, kc, cm, _ = build_symbol_lookups(_sample_inventory())
        assert "Scene" in kc
        assert "open" in cm["Scene"]
        assert "save" in cm["Scene"]

    def test_properties_folded(self):
        _, _, cm, _ = build_symbol_lookups(_sample_inventory())
        assert "root_node" in cm["Scene"]
        assert "library" in cm["Scene"]

    def test_functions(self):
        _, _, _, kf = build_symbol_lookups(_sample_inventory())
        assert "configure_logging" in kf

    def test_empty_inventory(self):
        _, kc, cm, kf = build_symbol_lookups({})
        assert len(kc) == 0
        assert len(cm) == 0
        assert len(kf) == 0


class TestBuildTypeBindings:
    def setup_method(self):
        inv = _sample_inventory()
        self.ki, self.kc, self.cm, _ = build_symbol_lookups(inv)

    def _bindings(self, code: str):
        tree = ast.parse(code)
        return build_type_bindings(tree, self.kc, self.cm, self.ki)

    def test_import_alias(self):
        vt, ia = self._bindings("import aspose.threed as a3d")
        assert ia["a3d"] == "aspose.threed"

    def test_from_import_class_alias(self):
        vt, ia = self._bindings("from aspose.threed import Scene as S")
        assert ia["S"] == "Scene"

    def test_constructor_binding(self):
        vt, _ = self._bindings("s = Scene()")
        assert vt["s"] == "Scene"

    def test_qualified_constructor(self):
        vt, _ = self._bindings("import aspose.threed\ns = aspose.threed.Scene()")
        assert vt["s"] == "Scene"

    def test_reassignment_clears(self):
        vt, _ = self._bindings("s = Scene()\ns = 42")
        assert "s" not in vt

    def test_unknown_class_not_bound(self):
        vt, _ = self._bindings("x = FakeClass()")
        assert "x" not in vt


class TestValidateCodeFence:
    def test_valid_imports_pass(self):
        issues = validate_code_fence(
            "import aspose.threed\nfrom aspose.threed import Scene",
            _sample_inventory(),
        )
        assert len(issues) == 0

    def test_unknown_import_flagged(self):
        issues = validate_code_fence(
            "import fake_library",
            _sample_inventory(),
        )
        assert len(issues) == 1
        assert issues[0].error_type == "unknown_import"
        assert issues[0].symbol == "fake_library"

    def test_stdlib_allowed(self):
        issues = validate_code_fence(
            "import os\nimport json\nimport pathlib",
            _sample_inventory(),
        )
        assert len(issues) == 0

    def test_known_method_passes(self):
        issues = validate_code_fence(
            "s = Scene()\ns.open('file.fbx')",
            _sample_inventory(),
        )
        method_issues = [i for i in issues if i.error_type == "unknown_method"]
        assert len(method_issues) == 0

    def test_unknown_method_flagged(self):
        issues = validate_code_fence(
            "s = Scene()\ns.hallucinated()",
            _sample_inventory(),
        )
        method_issues = [i for i in issues if i.error_type == "unknown_method"]
        assert len(method_issues) == 1
        assert method_issues[0].class_name == "Scene"
        assert method_issues[0].symbol == "hallucinated"

    def test_property_access_passes(self):
        issues = validate_code_fence(
            "s = Scene()\nnode = s.root_node",
            _sample_inventory(),
        )
        method_issues = [i for i in issues if i.error_type == "unknown_method"]
        assert len(method_issues) == 0

    def test_check_methods_false_skips_methods(self):
        issues = validate_code_fence(
            "s = Scene()\ns.hallucinated()",
            _sample_inventory(),
            check_methods=False,
        )
        method_issues = [i for i in issues if i.error_type == "unknown_method"]
        assert len(method_issues) == 0

    def test_pseudocode_returns_empty(self):
        issues = validate_code_fence(
            "this is not python {{{",
            _sample_inventory(),
        )
        assert len(issues) == 0

    def test_empty_inventory_returns_empty(self):
        issues = validate_code_fence("import anything", {})
        assert len(issues) == 0

    def test_alias_method_validation(self):
        issues = validate_code_fence(
            "from aspose.threed import Scene as S\nS.open('f.fbx')",
            _sample_inventory(),
        )
        method_issues = [i for i in issues if i.error_type == "unknown_method"]
        assert len(method_issues) == 0

    def test_alias_unknown_method_flagged(self):
        issues = validate_code_fence(
            "from aspose.threed import Scene as S\nS.fake()",
            _sample_inventory(),
        )
        method_issues = [i for i in issues if i.error_type == "unknown_method"]
        assert len(method_issues) == 1

    def test_no_classes_still_validates_imports(self):
        """Even with no classes, unknown imports are flagged."""
        inventory = {
            "package_name": "func-only-pkg",
            "classes": [],
            "functions": ["do_work"],
            "modules": ["funcpkg", "funcpkg.utils"],
        }
        issues = validate_code_fence(
            "import bogus_lib",
            inventory,
        )
        import_issues = [i for i in issues if i.error_type == "unknown_import"]
        assert len(import_issues) == 1
        assert import_issues[0].symbol == "bogus_lib"

    def test_no_classes_known_import_passes(self):
        """With no classes, known module imports pass cleanly."""
        inventory = {
            "package_name": "func-only-pkg",
            "classes": [],
            "functions": ["do_work"],
            "modules": ["funcpkg"],
        }
        issues = validate_code_fence(
            "import funcpkg",
            inventory,
        )
        import_issues = [i for i in issues if i.error_type == "unknown_import"]
        assert len(import_issues) == 0


class TestExtractPythonCodeFences:
    def test_single_fence(self):
        content = "text\n```python\nimport os\n```\nmore"
        fences = extract_python_code_fences(content)
        assert len(fences) == 1
        assert "import os" in fences[0][0]

    def test_py_shorthand(self):
        fences = extract_python_code_fences("```py\nx=1\n```")
        assert len(fences) == 1

    def test_non_python_ignored(self):
        fences = extract_python_code_fences("```javascript\nvar x;\n```")
        assert len(fences) == 0

    def test_multiple(self):
        content = "```python\na=1\n```\n\n```python\nb=2\n```"
        fences = extract_python_code_fences(content)
        assert len(fences) == 2


class TestBuiltinClasses:
    @pytest.mark.parametrize("name", [
        "ValueError", "dict", "list", "Path", "Exception",
        "Counter", "StringIO", "Thread",
    ])
    def test_builtin_in_set(self, name):
        assert name in BUILTIN_CLASSES
