"""TC-2811 / TC-2870: Tests for Gate 15b — Code Fence API Validation.

Covers:
- Valid code fences with known imports → pass
- Unknown imports → error (blocker in prod)
- Unknown method on known class → error in ci/prod, warn in local (TC-2870)
- Unparseable code fence (pseudocode) → graceful skip (no error)
- No api_inventory.json → error in ci/prod, info in local (TC-2870)
- Severity escalation by profile (local/ci/prod)
- STDLIB_IMPORT_ALLOWLIST bypass for stdlib/common third-party
- TC-2870: Type inference — import aliases, constructor bindings, variable method calls
"""

from __future__ import annotations

import json
import pytest
from pathlib import Path

from src.launch.workers.w9_validator.gates.gate_15b_code_fence_api import (
    execute_gate,
    _build_symbol_lookups,
    _build_type_bindings,
    _resolve_call_class,
    _extract_python_code_fences,
    _validate_code_fence,
    _escalate_severity,
    _BUILTIN_CLASSES,
    STDLIB_IMPORT_ALLOWLIST,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_api_inventory(run_dir: Path, inventory: dict) -> None:
    """Write api_inventory.json into run_dir/artifacts/."""
    arts = run_dir / "artifacts"
    arts.mkdir(parents=True, exist_ok=True)
    (arts / "api_inventory.json").write_text(
        json.dumps(inventory), encoding="utf-8"
    )


def _write_md(run_dir: Path, rel_path: str, content: str) -> Path:
    """Write a markdown file under run_dir/work/site/ and return its Path."""
    md_file = run_dir / "work" / "site" / rel_path
    md_file.parent.mkdir(parents=True, exist_ok=True)
    md_file.write_text(content, encoding="utf-8")
    return md_file


def _sample_inventory() -> dict:
    """Standard test inventory for aspose.threed."""
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


# ---------------------------------------------------------------------------
# _build_symbol_lookups
# ---------------------------------------------------------------------------

class TestBuildSymbolLookups:
    """Test symbol lookup construction from API inventory."""

    def test_known_imports_include_package_variants(self):
        inv = _sample_inventory()
        known_imports, _, _, _ = _build_symbol_lookups(inv)
        assert "aspose-3d" in known_imports
        assert "aspose.3d" in known_imports
        assert "aspose_3d" in known_imports

    def test_known_imports_include_module_paths(self):
        inv = _sample_inventory()
        known_imports, _, _, _ = _build_symbol_lookups(inv)
        assert "aspose" in known_imports
        assert "aspose.threed" in known_imports
        assert "aspose.threed.entities" in known_imports

    def test_known_classes_populated(self):
        inv = _sample_inventory()
        _, known_classes, _, _ = _build_symbol_lookups(inv)
        assert "Scene" in known_classes
        assert "Mesh" in known_classes

    def test_class_methods_populated(self):
        inv = _sample_inventory()
        _, _, class_methods, _ = _build_symbol_lookups(inv)
        assert "open" in class_methods["Scene"]
        assert "save" in class_methods["Scene"]
        assert "create_polygon" in class_methods["Mesh"]

    def test_properties_folded_into_class_methods(self):
        """TC-2870: Properties included in class_methods for attribute validation."""
        inv = _sample_inventory()
        _, _, class_methods, _ = _build_symbol_lookups(inv)
        assert "root_node" in class_methods["Scene"]
        assert "library" in class_methods["Scene"]

    def test_known_functions_populated(self):
        """TC-2870: Functions extracted from inventory."""
        inv = _sample_inventory()
        _, _, _, known_functions = _build_symbol_lookups(inv)
        assert "configure_logging" in known_functions

    def test_empty_inventory(self):
        known_imports, known_classes, class_methods, known_functions = _build_symbol_lookups({})
        assert len(known_classes) == 0
        assert len(class_methods) == 0
        assert len(known_functions) == 0

    def test_string_only_classes(self):
        inv = {"classes": ["Foo", "Bar"]}
        _, known_classes, class_methods, _ = _build_symbol_lookups(inv)
        assert "Foo" in known_classes
        assert "Bar" in known_classes
        assert "Foo" not in class_methods


# ---------------------------------------------------------------------------
# _extract_python_code_fences
# ---------------------------------------------------------------------------

class TestExtractPythonCodeFences:
    """Test Python code fence extraction from markdown."""

    def test_single_python_fence(self):
        content = "Some text\n```python\nimport os\nprint('hi')\n```\nMore text"
        fences = _extract_python_code_fences(content)
        assert len(fences) == 1
        code, offset = fences[0]
        assert "import os" in code
        assert offset == 2  # fence starts at line 2 (1 newline before it + 1)

    def test_py_shorthand(self):
        content = "```py\nx = 1\n```"
        fences = _extract_python_code_fences(content)
        assert len(fences) == 1

    def test_non_python_fence_ignored(self):
        content = "```javascript\nvar x = 1;\n```"
        fences = _extract_python_code_fences(content)
        assert len(fences) == 0

    def test_multiple_fences(self):
        content = "```python\na = 1\n```\ntext\n```python\nb = 2\n```"
        fences = _extract_python_code_fences(content)
        assert len(fences) == 2

    def test_no_fences(self):
        content = "Just regular markdown text with no code."
        fences = _extract_python_code_fences(content)
        assert len(fences) == 0


# ---------------------------------------------------------------------------
# _escalate_severity
# ---------------------------------------------------------------------------

class TestEscalateSeverity:
    """Test profile-based severity escalation."""

    def test_prod_escalates_error_to_blocker(self):
        assert _escalate_severity("error", "prod") == "blocker"

    def test_ci_keeps_error(self):
        assert _escalate_severity("error", "ci") == "error"

    def test_local_demotes_error_to_warn(self):
        assert _escalate_severity("error", "local") == "warn"

    def test_warn_unchanged_all_profiles(self):
        assert _escalate_severity("warn", "prod") == "warn"
        assert _escalate_severity("warn", "ci") == "warn"
        assert _escalate_severity("warn", "local") == "warn"


# ---------------------------------------------------------------------------
# _validate_code_fence
# ---------------------------------------------------------------------------

class TestValidateCodeFence:
    """Test individual code fence validation."""

    def setup_method(self):
        inv = _sample_inventory()
        self.known_imports, self.known_classes, self.class_methods, self.known_functions = (
            _build_symbol_lookups(inv)
        )

    def _validate(self, code: str, profile: str = "ci"):
        return _validate_code_fence(
            code, 1, Path("test.md"),
            self.known_imports, self.known_classes, self.class_methods,
            self.known_functions, profile,
        )

    def test_valid_import_passes(self):
        code = "import aspose.threed\nscene = aspose.threed.Scene()"
        issues = self._validate(code)
        error_issues = [i for i in issues if i["severity"] in ("error", "blocker")]
        assert len(error_issues) == 0

    def test_unknown_import_raises_error(self):
        code = "import fake_library\nfake_library.do_stuff()"
        issues = self._validate(code)
        error_issues = [i for i in issues if i["severity"] in ("error", "blocker")]
        assert len(error_issues) >= 1
        assert error_issues[0]["error_code"] == "GATE15B_UNKNOWN_IMPORT"

    def test_unknown_from_import_raises_error(self):
        code = "from nonexistent.module import Something"
        issues = self._validate(code)
        error_issues = [i for i in issues if i["severity"] in ("error", "blocker")]
        assert len(error_issues) >= 1
        assert error_issues[0]["error_code"] == "GATE15B_UNKNOWN_IMPORT"

    def test_stdlib_import_allowed(self):
        code = "import os\nimport json\nimport pathlib"
        issues = self._validate(code)
        assert len(issues) == 0

    def test_common_third_party_allowed(self):
        code = "import numpy as np\nimport pandas as pd"
        issues = self._validate(code)
        assert len(issues) == 0

    def test_known_method_passes(self):
        code = "scene = Scene()\nscene_result = Scene.open('file.3ds')"
        issues = self._validate(code)
        method_issues = [i for i in issues if i["error_code"] == "GATE15B_UNKNOWN_METHOD"]
        assert len(method_issues) == 0

    def test_unknown_method_error_in_ci(self):
        """TC-2870: Unknown methods are error in CI (was: warn)."""
        code = "result = Scene.nonexistent_method()"
        issues = self._validate(code, profile="ci")
        method_issues = [i for i in issues if i["error_code"] == "GATE15B_UNKNOWN_METHOD"]
        assert len(method_issues) == 1
        assert method_issues[0]["severity"] == "error"

    def test_unknown_method_blocker_in_prod(self):
        """TC-2870: Unknown methods are blocker in prod."""
        code = "result = Scene.nonexistent_method()"
        issues = self._validate(code, profile="prod")
        method_issues = [i for i in issues if i["error_code"] == "GATE15B_UNKNOWN_METHOD"]
        assert len(method_issues) == 1
        assert method_issues[0]["severity"] == "blocker"

    def test_unknown_method_warn_in_local(self):
        """TC-2870: Unknown methods are warn in local."""
        code = "result = Scene.nonexistent_method()"
        issues = self._validate(code, profile="local")
        method_issues = [i for i in issues if i["error_code"] == "GATE15B_UNKNOWN_METHOD"]
        assert len(method_issues) == 1
        assert method_issues[0]["severity"] == "warn"

    def test_syntax_error_graceful(self):
        code = "this is not valid python: {{{}}}"
        issues = self._validate(code)
        assert len(issues) == 0  # pseudocode → no errors

    def test_prod_profile_escalates_import_to_blocker(self):
        code = "import hallucinated_pkg"
        issues = self._validate(code, profile="prod")
        blocker_issues = [i for i in issues if i["severity"] == "blocker"]
        assert len(blocker_issues) >= 1

    def test_local_profile_demotes_import_to_warn(self):
        code = "import hallucinated_pkg"
        issues = self._validate(code, profile="local")
        warn_issues = [i for i in issues if i["severity"] == "warn"]
        assert len(warn_issues) >= 1
        error_issues = [i for i in issues if i["severity"] in ("error", "blocker")]
        assert len(error_issues) == 0

    def test_property_access_passes(self):
        """TC-2870: Property access validated via class_methods (includes properties)."""
        code = "s = Scene()\nnode = s.root_node"
        issues = self._validate(code, profile="local")
        method_issues = [i for i in issues if i["error_code"] == "GATE15B_UNKNOWN_METHOD"]
        assert len(method_issues) == 0


# ---------------------------------------------------------------------------
# TC-2870: Type inference
# ---------------------------------------------------------------------------

class TestTypeInference:
    """TC-2870: Test type inference for import aliases and constructor bindings."""

    def setup_method(self):
        inv = _sample_inventory()
        self.known_imports, self.known_classes, self.class_methods, self.known_functions = (
            _build_symbol_lookups(inv)
        )

    def _validate(self, code: str, profile: str = "ci"):
        return _validate_code_fence(
            code, 1, Path("test.md"),
            self.known_imports, self.known_classes, self.class_methods,
            self.known_functions, profile,
        )

    def test_import_alias_tracked(self):
        """import aspose.threed as a3d; a3d.Scene() → no import error."""
        code = "import aspose.threed as a3d\ns = a3d.Scene()\ns.open('file.fbx')"
        issues = self._validate(code)
        import_issues = [i for i in issues if i["error_code"] == "GATE15B_UNKNOWN_IMPORT"]
        assert len(import_issues) == 0

    def test_from_import_alias_tracked(self):
        """from aspose.threed import Scene as S; S.open() → valid."""
        code = "from aspose.threed import Scene as S\nresult = S.open('file.fbx')"
        issues = self._validate(code)
        method_issues = [i for i in issues if i["error_code"] == "GATE15B_UNKNOWN_METHOD"]
        assert len(method_issues) == 0

    def test_from_import_alias_unknown_method(self):
        """from aspose.threed import Scene as S; S.fake() → flagged."""
        code = "from aspose.threed import Scene as S\nresult = S.fake()"
        issues = self._validate(code, profile="ci")
        method_issues = [i for i in issues if i["error_code"] == "GATE15B_UNKNOWN_METHOD"]
        assert len(method_issues) == 1
        assert method_issues[0]["severity"] == "error"

    def test_constructor_binding(self):
        """s = Scene(); s.open() → valid; s.nonexistent() → flagged."""
        code = "s = Scene()\ns.open('file.fbx')"
        issues = self._validate(code)
        assert len([i for i in issues if i["error_code"] == "GATE15B_UNKNOWN_METHOD"]) == 0

        code2 = "s = Scene()\ns.nonexistent()"
        issues2 = self._validate(code2, profile="ci")
        method_issues = [i for i in issues2 if i["error_code"] == "GATE15B_UNKNOWN_METHOD"]
        assert len(method_issues) == 1
        assert method_issues[0]["severity"] == "error"

    def test_module_qualified_constructor(self):
        """s = aspose.threed.Scene(); s.save() → valid."""
        code = "import aspose.threed\ns = aspose.threed.Scene()\ns.save('out.fbx')"
        issues = self._validate(code)
        method_issues = [i for i in issues if i["error_code"] == "GATE15B_UNKNOWN_METHOD"]
        assert len(method_issues) == 0

    def test_reassignment_clears_binding(self):
        """s = Scene(); s = 42; s.open() → NOT flagged (conservative)."""
        code = "s = Scene()\ns = 42\ns.open('file.fbx')"
        issues = self._validate(code)
        # After reassignment to non-class, binding is removed.
        # s.open() is no longer resolved to Scene → no issue flagged.
        method_issues = [i for i in issues if i["error_code"] == "GATE15B_UNKNOWN_METHOD"]
        assert len(method_issues) == 0

    def test_builtin_class_not_flagged(self):
        """ValueError("msg") should never be flagged as unknown class."""
        assert "ValueError" in _BUILTIN_CLASSES
        assert "dict" in _BUILTIN_CLASSES
        assert "Path" in _BUILTIN_CLASSES

    def test_property_access_validated(self):
        """scene.root_node → valid (property in inventory)."""
        code = "s = Scene()\nnode = s.root_node"
        issues = self._validate(code)
        method_issues = [i for i in issues if i["error_code"] == "GATE15B_UNKNOWN_METHOD"]
        assert len(method_issues) == 0

    def test_unknown_property_flagged(self):
        """scene.fake_prop → flagged as unknown method/property."""
        code = "s = Scene()\nval = s.fake_prop"
        issues = self._validate(code, profile="ci")
        method_issues = [i for i in issues if i["error_code"] == "GATE15B_UNKNOWN_METHOD"]
        assert len(method_issues) == 1


# ---------------------------------------------------------------------------
# TC-2870: _build_type_bindings unit tests
# ---------------------------------------------------------------------------

class TestBuildTypeBindings:
    """TC-2870: Unit tests for _build_type_bindings."""

    def setup_method(self):
        inv = _sample_inventory()
        self.known_imports, self.known_classes, self.class_methods, _ = (
            _build_symbol_lookups(inv)
        )

    def _bindings(self, code: str):
        import ast
        tree = ast.parse(code)
        return _build_type_bindings(
            tree, self.known_classes, self.class_methods, self.known_imports,
        )

    def test_import_alias(self):
        var_types, import_aliases = self._bindings("import aspose.threed as a3d")
        assert import_aliases["a3d"] == "aspose.threed"

    def test_from_import_class_alias(self):
        var_types, import_aliases = self._bindings(
            "from aspose.threed import Scene as S"
        )
        assert import_aliases["S"] == "Scene"

    def test_constructor_assignment(self):
        var_types, _ = self._bindings("s = Scene()")
        assert var_types["s"] == "Scene"

    def test_qualified_constructor(self):
        var_types, _ = self._bindings(
            "import aspose.threed\ns = aspose.threed.Scene()"
        )
        assert var_types["s"] == "Scene"

    def test_reassignment_removes_binding(self):
        var_types, _ = self._bindings("s = Scene()\ns = 42")
        assert "s" not in var_types

    def test_unknown_class_not_bound(self):
        var_types, _ = self._bindings("x = FakeClass()")
        assert "x" not in var_types


# ---------------------------------------------------------------------------
# execute_gate (integration)
# ---------------------------------------------------------------------------

class TestExecuteGate:
    """Integration tests for the full gate execution."""

    def test_no_api_inventory_graceful_skip_local(self, tmp_path):
        """Gate passes gracefully when api_inventory.json is absent in local."""
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        passed, issues = execute_gate(run_dir, "local")
        assert passed is True
        assert len(issues) == 1
        assert issues[0]["error_code"] == "GATE15B_INVENTORY_MISSING"
        assert issues[0]["severity"] == "info"

    def test_missing_inventory_error_in_ci(self, tmp_path):
        """TC-2870: Missing inventory fails gate in CI."""
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is False
        assert issues[0]["severity"] == "error"
        assert issues[0]["error_code"] == "GATE15B_INVENTORY_MISSING"

    def test_missing_inventory_blocker_in_prod(self, tmp_path):
        """TC-2870: Missing inventory is blocker in prod."""
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        passed, issues = execute_gate(run_dir, "prod")
        assert passed is False
        assert issues[0]["severity"] == "blocker"

    def test_no_site_dir_passes(self, tmp_path):
        """Gate passes when work/site directory doesn't exist."""
        run_dir = tmp_path / "run"
        _write_api_inventory(run_dir, _sample_inventory())
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is True

    def test_valid_code_fence_passes(self, tmp_path):
        """Gate passes with valid imports in code fences."""
        run_dir = tmp_path / "run"
        _write_api_inventory(run_dir, _sample_inventory())
        _write_md(run_dir, "page.md", (
            "# Example\n\n"
            "```python\n"
            "import aspose.threed\n"
            "scene = aspose.threed.Scene()\n"
            "scene.open('model.fbx')\n"
            "```\n"
        ))
        passed, issues = execute_gate(run_dir, "ci")
        error_issues = [i for i in issues if i["severity"] in ("error", "blocker")]
        assert len(error_issues) == 0
        assert passed is True

    def test_unknown_import_fails_gate(self, tmp_path):
        """Gate fails when code fence has unknown imports."""
        run_dir = tmp_path / "run"
        _write_api_inventory(run_dir, _sample_inventory())
        _write_md(run_dir, "page.md", (
            "# Bad Example\n\n"
            "```python\n"
            "import totally_fake_library\n"
            "totally_fake_library.do_things()\n"
            "```\n"
        ))
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is False
        error_issues = [i for i in issues if i["severity"] in ("error", "blocker")]
        assert len(error_issues) >= 1

    def test_unknown_method_fails_gate_in_ci(self, tmp_path):
        """TC-2870: Unknown methods fail gate in CI (was: pass with warn)."""
        run_dir = tmp_path / "run"
        _write_api_inventory(run_dir, _sample_inventory())
        _write_md(run_dir, "page.md", (
            "```python\n"
            "result = Scene.hallucinated_method()\n"
            "```\n"
        ))
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is False
        error_issues = [i for i in issues if i["severity"] == "error"]
        assert len(error_issues) >= 1

    def test_unknown_method_passes_gate_in_local(self, tmp_path):
        """TC-2870: Unknown methods are warn-only in local, gate still passes."""
        run_dir = tmp_path / "run"
        _write_api_inventory(run_dir, _sample_inventory())
        _write_md(run_dir, "page.md", (
            "```python\n"
            "result = Scene.hallucinated_method()\n"
            "```\n"
        ))
        passed, issues = execute_gate(run_dir, "local")
        assert passed is True
        warn_issues = [i for i in issues if i["severity"] == "warn"]
        assert len(warn_issues) >= 1

    def test_variable_method_call_detected(self, tmp_path):
        """TC-2870: s = Scene(); s.fake() detected via type inference."""
        run_dir = tmp_path / "run"
        _write_api_inventory(run_dir, _sample_inventory())
        _write_md(run_dir, "page.md", (
            "```python\n"
            "from aspose.threed import Scene\n"
            "s = Scene()\n"
            "s.hallucinated_api()\n"
            "```\n"
        ))
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is False
        method_issues = [i for i in issues if i["error_code"] == "GATE15B_UNKNOWN_METHOD"]
        assert len(method_issues) >= 1

    def test_variable_method_call_valid_passes(self, tmp_path):
        """TC-2870: s = Scene(); s.open() passes — real method."""
        run_dir = tmp_path / "run"
        _write_api_inventory(run_dir, _sample_inventory())
        _write_md(run_dir, "page.md", (
            "```python\n"
            "from aspose.threed import Scene\n"
            "s = Scene()\n"
            "s.open('model.fbx')\n"
            "s.save('output.fbx')\n"
            "```\n"
        ))
        passed, issues = execute_gate(run_dir, "ci")
        method_issues = [i for i in issues if i["error_code"] == "GATE15B_UNKNOWN_METHOD"]
        assert len(method_issues) == 0
        assert passed is True

    def test_mixed_valid_and_invalid(self, tmp_path):
        """Gate fails if any code fence has unknown imports, even if others are valid."""
        run_dir = tmp_path / "run"
        _write_api_inventory(run_dir, _sample_inventory())
        _write_md(run_dir, "good.md", (
            "```python\nimport os\nprint('ok')\n```\n"
        ))
        _write_md(run_dir, "bad.md", (
            "```python\nimport hallucinated_api\n```\n"
        ))
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is False

    def test_pseudocode_does_not_fail(self, tmp_path):
        """Unparseable code fences (pseudocode) don't cause errors."""
        run_dir = tmp_path / "run"
        _write_api_inventory(run_dir, _sample_inventory())
        _write_md(run_dir, "page.md", (
            "```python\n"
            "# Step 1: Load the file\n"
            "scene = load file 'model.fbx'  # not real Python\n"
            "```\n"
        ))
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is True

    def test_corrupted_inventory_graceful_local(self, tmp_path):
        """Gate passes gracefully with corrupted api_inventory.json in local."""
        run_dir = tmp_path / "run"
        arts = run_dir / "artifacts"
        arts.mkdir(parents=True)
        (arts / "api_inventory.json").write_text("NOT JSON", encoding="utf-8")
        passed, issues = execute_gate(run_dir, "local")
        assert passed is True
        assert issues[0]["error_code"] == "GATE15B_INVENTORY_ERROR"
        assert issues[0]["severity"] == "info"

    def test_corrupted_inventory_error_in_ci(self, tmp_path):
        """TC-2870: Corrupted inventory fails gate in CI."""
        run_dir = tmp_path / "run"
        arts = run_dir / "artifacts"
        arts.mkdir(parents=True)
        (arts / "api_inventory.json").write_text("NOT JSON", encoding="utf-8")
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is False
        assert issues[0]["severity"] == "error"

    def test_empty_classes_still_validates_imports(self, tmp_path):
        """Gate validates imports even when inventory has no classes."""
        run_dir = tmp_path / "run"
        _write_api_inventory(run_dir, {
            "package_name": "empty-pkg",
            "classes": [],
            "functions": [],
            "modules": ["mypkg"],
        })
        _write_md(run_dir, "page.md", (
            "```python\nimport something_unknown\n```\n"
        ))
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is False
        assert any(i["error_code"] == "GATE15B_UNKNOWN_IMPORT" for i in issues)

    def test_function_only_inventory_known_import_passes(self, tmp_path):
        """Inventory with modules + functions but no classes — known import passes."""
        run_dir = tmp_path / "run"
        _write_api_inventory(run_dir, {
            "package_name": "func-only-pkg",
            "classes": [],
            "functions": ["do_work"],
            "modules": ["funcpkg", "funcpkg.utils"],
        })
        _write_md(run_dir, "page.md", (
            "```python\nimport funcpkg\n```\n"
        ))
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is True
        assert not any(i["error_code"] == "GATE15B_UNKNOWN_IMPORT" for i in issues)

    def test_function_only_inventory_unknown_import_fails(self, tmp_path):
        """Inventory with modules + functions but no classes — unknown import fails."""
        run_dir = tmp_path / "run"
        _write_api_inventory(run_dir, {
            "package_name": "func-only-pkg",
            "classes": [],
            "functions": ["do_work"],
            "modules": ["funcpkg"],
        })
        _write_md(run_dir, "page.md", (
            "```python\nimport bogus_lib\n```\n"
        ))
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is False
        assert any(i["error_code"] == "GATE15B_UNKNOWN_IMPORT" for i in issues)

    def test_max_issues_per_file_capped(self, tmp_path):
        """No more than MAX_ISSUES_PER_FILE issues per markdown file."""
        run_dir = tmp_path / "run"
        _write_api_inventory(run_dir, _sample_inventory())
        # Create a file with many bad imports
        bad_imports = "\n".join(
            f"import fake_lib_{i}" for i in range(30)
        )
        _write_md(run_dir, "many_errors.md", (
            f"```python\n{bad_imports}\n```\n"
        ))
        passed, issues = execute_gate(run_dir, "ci")
        # Should be capped at 15
        file_issues = [
            i for i in issues
            if "many_errors" in i.get("issue_id", "")
        ]
        assert len(file_issues) <= 15


# ---------------------------------------------------------------------------
# STDLIB_IMPORT_ALLOWLIST coverage
# ---------------------------------------------------------------------------

class TestStdlibAllowlist:
    """Verify key stdlib/third-party modules are in the allowlist."""

    @pytest.mark.parametrize("module", [
        "os", "sys", "json", "re", "pathlib", "io", "math",
        "datetime", "collections", "typing", "logging",
    ])
    def test_stdlib_in_allowlist(self, module):
        assert module in STDLIB_IMPORT_ALLOWLIST

    @pytest.mark.parametrize("module", [
        "numpy", "pandas", "requests", "pytest", "yaml",
    ])
    def test_third_party_in_allowlist(self, module):
        assert module in STDLIB_IMPORT_ALLOWLIST
