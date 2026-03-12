# Healing Plan: SQP Missing Test Coverage

**Source gap index**: `plans/healing/SQP-00-gap-index.md`
**Covers gaps**: SQP-G04

---

## Taskcard SQP-H4 — Write missing test coverage for TC-4032, TC-4030, TC-4031

**Status**: Not Started
**Gap linkage**: SQP-G04
**Role**: Senior engineer. Drop-in, production-ready.

### Problem

All three implementation taskcards (TC-4032, TC-4030, TC-4031) explicitly required new
test files in their Acceptance checks and Deliverables sections. None were written.
The current state:

| Code path | Coverage |
|-----------|----------|
| TC-4032 OSError guard (primary path) | 0 new tests |
| TC-4032 OSError guard (fallback path) | 0 new tests |
| TC-4032 non-OSError still propagates | 0 new tests |
| TC-4030 SharedFacts 4 new fields populated | 0 new tests |
| TC-4030 `extract_install_recipe` cache bypass | 0 new tests |
| TC-4030 worker.py uses shared_facts (SQP-H1) | 0 new tests |
| TC-4031 Go struct field extraction | 0 new tests |
| TC-4031 Go typed function parameters | 0 new tests |
| TC-4031 Go iota enum synthesis | 0 new tests |
| TC-4031 C++ tree-sitter primary path | 0 new tests |
| TC-4031 C++ fallback when tree-sitter empty | 0 new tests |

This means every new code path is untested. A future refactor that silently breaks
Go struct field extraction would pass CI.

### Scope

**Fix**: Write the following new test files and extend the named existing files.
Zero code changes — tests only.

**Allowed paths**:
- `tests/unit/workers/understand/test_snippets_io.py` *(new)*
- `tests/unit/workers/test_scout_facts_extended.py` *(new)*
- `tests/unit/workers/understand/test_go_extraction.py` *(new)*
- `tests/unit/workers/understand/test_cpp_extraction.py` *(new)*
- `tests/unit/shared/test_ts_analyzer.py` *(extend existing — add Go/C++ cases)*
- `tests/unit/workers/test_understand_product_evidence.py` *(extend existing — assert shared_facts forwarded)*

**Forbidden**: any `src/` file or any other path.

---

### Sub-task A — TC-4032 OSError tests

**File**: `tests/unit/workers/understand/test_snippets_io.py` *(new)*

```python
"""Tests for _build_embedding_index() disk-error resilience (TC-4032)."""
from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


def _make_context(tmp_path: Path, with_store: bool = True):
    ctx = MagicMock()
    ctx.llm_config = None
    ctx.run_dir = tmp_path
    if with_store:
        store = MagicMock()
        store.artifacts_dir = tmp_path / "artifacts"
        ctx.store = store
    else:
        ctx.store = None
    return ctx


def _make_claims():
    from launcher.models.claims import Claim
    return [Claim(
        claim_id="c1",
        text="test claim",
        kind="feature",
        evidence=[],
        visibility="public",
        tier_relevance="all",
    )]


class TestBuildEmbeddingIndexOSError:
    """TC-4032: disk-write failures must not crash the understand worker."""

    def test_primary_path_oserror_does_not_propagate(self, tmp_path):
        """OSError on primary artifacts_dir write is swallowed; function returns."""
        from launcher.workers.understand.extract._snippets import _build_embedding_index
        from launcher.shared.embeddings import EmbeddingIndex

        ctx = _make_context(tmp_path)
        with patch.object(EmbeddingIndex, "save", side_effect=OSError("disk full")):
            # Must not raise
            _build_embedding_index(_make_claims(), [], ctx)

    def test_fallback_path_mkdir_oserror_does_not_propagate(self, tmp_path):
        """OSError on run_dir mkdir is swallowed; function returns."""
        from launcher.workers.understand.extract._snippets import _build_embedding_index
        from launcher.shared.embeddings import EmbeddingIndex

        ctx = _make_context(tmp_path, with_store=False)
        with patch("pathlib.Path.mkdir", side_effect=OSError("read-only filesystem")):
            _build_embedding_index(_make_claims(), [], ctx)

    def test_fallback_path_save_oserror_does_not_propagate(self, tmp_path):
        """OSError on run_dir save is swallowed; function returns."""
        from launcher.workers.understand.extract._snippets import _build_embedding_index
        from launcher.shared.embeddings import EmbeddingIndex

        ctx = _make_context(tmp_path, with_store=False)
        with patch.object(EmbeddingIndex, "save", side_effect=OSError("permission denied")):
            _build_embedding_index(_make_claims(), [], ctx)

    def test_non_oserror_still_propagates(self, tmp_path):
        """ValueError (programming error) must not be silently swallowed."""
        from launcher.workers.understand.extract._snippets import _build_embedding_index
        from launcher.shared.embeddings import EmbeddingIndex

        ctx = _make_context(tmp_path)
        with patch.object(EmbeddingIndex, "save", side_effect=ValueError("bad data")):
            with pytest.raises(ValueError, match="bad data"):
                _build_embedding_index(_make_claims(), [], ctx)

    def test_success_path_writes_artifact(self, tmp_path):
        """Happy path: artifact is written when disk is available."""
        from launcher.workers.understand.extract._snippets import _build_embedding_index

        ctx = _make_context(tmp_path)
        ctx.store.artifacts_dir = tmp_path
        _build_embedding_index(_make_claims(), [], ctx)
        assert (tmp_path / "embedding_index.json").exists()
```

---

### Sub-task B — TC-4030 SharedFacts + extract_install_recipe cache tests

**File**: `tests/unit/workers/test_scout_facts_extended.py` *(new)*

```python
"""Tests for TC-4030: SharedFacts 4 new fields and install-recipe cache bypass."""
from __future__ import annotations

import pathlib
import pytest


class TestSharedFactsNewFields:
    """SharedFacts is populated with description, python_requires, deps, entrypoints."""

    def test_pyproject_standard_pep518(self, tmp_path):
        """Standard [project] section populates all 4 new fields."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_bytes(
            b"""
[project]
name = "mypackage"
version = "1.0.0"
description = "A test package"
requires-python = ">=3.9"
dependencies = ["requests>=2.0", "click"]

[project.scripts]
mycli = "mypackage.cli:main"
"""
        )
        import sys; sys.path.insert(0, "src")  # noqa: E702
        from launcher.workers.understand.scout import _parse_pyproject

        name, ver, lic, desc, py_req, deps, entrypoints = _parse_pyproject(pyproject)
        assert name == "mypackage"
        assert desc == "A test package"
        assert py_req == ">=3.9"
        assert "requests>=2.0" in deps or "requests" in deps
        assert "click" in deps
        assert "mycli" in entrypoints

    def test_poetry_deps_python_key_excluded(self, tmp_path):
        """Poetry [tool.poetry.dependencies] must not include 'python' in SharedFacts.dependencies."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_bytes(
            b"""
[tool.poetry]
name = "poetrypkg"
version = "0.1.0"

[tool.poetry.dependencies]
python = "^3.9"
requests = "^2.28"
"""
        )
        from launcher.workers.understand.scout import _parse_pyproject

        _, _, _, _, _, deps, _ = _parse_pyproject(pyproject)
        assert "python" not in deps, f"'python' must not appear in deps: {deps}"
        assert "requests" in deps

    def test_missing_pyproject_returns_empty_fields(self, tmp_path):
        """Non-existent file returns all-empty 7-tuple."""
        from launcher.workers.understand.scout import _parse_pyproject

        result = _parse_pyproject(tmp_path / "nonexistent.toml")
        assert result == ("", "", "", "", "", [], [])

    def test_shared_facts_built_with_new_fields(self, tmp_path):
        """_extract_shared_facts() correctly populates description/deps/etc. in SharedFacts."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_bytes(
            b"""
[project]
name = "testpkg"
version = "2.0.0"
description = "Integration test package"
requires-python = ">=3.10"
dependencies = ["httpx"]
"""
        )
        from launcher.workers.understand.scout import _extract_shared_facts

        sf = _extract_shared_facts(tmp_path, [], {})
        assert sf.package_name == "testpkg"
        assert sf.description == "Integration test package"
        assert sf.python_requires == ">=3.10"
        assert "httpx" in sf.dependencies


class TestExtractInstallRecipeCacheBypass:
    """extract_install_recipe() must not open pyproject.toml when shared_facts is populated."""

    def test_shared_facts_bypasses_disk_read(self, tmp_path):
        """When shared_facts.package_name is set, pyproject.toml is never opened."""
        from unittest.mock import patch
        from launcher.workers.understand.extract._deterministic import extract_install_recipe
        from launcher.models.understanding import SharedFacts
        from launcher.models.product import ProductIdentity

        sf = SharedFacts(package_name="mypkg", version="1.2.3")
        product = ProductIdentity(
            display_name="MyPkg", canonical_import="mypkg",
            platform="python", family="test",
        )

        opened_paths = []

        real_open = open  # keep reference

        def tracking_open(path, *args, **kwargs):
            opened_paths.append(str(path))
            return real_open(path, *args, **kwargs)

        with patch("builtins.open", side_effect=tracking_open):
            recipe = extract_install_recipe(tmp_path, product, shared_facts=sf)

        pyproject_opens = [p for p in opened_paths if "pyproject.toml" in p]
        assert pyproject_opens == [], (
            f"pyproject.toml should not be opened when shared_facts is set, "
            f"but got: {pyproject_opens}"
        )
        assert recipe is not None
        assert recipe.package_name == "mypkg"
        assert "1.2.3" in recipe.pip_command

    def test_no_shared_facts_falls_through_to_disk(self, tmp_path):
        """Without shared_facts, pyproject.toml Strategy 1 is attempted."""
        from launcher.workers.understand.extract._deterministic import extract_install_recipe
        from launcher.models.product import ProductIdentity

        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_bytes(b'[project]\nname = "diskpkg"\nversion = "0.5"\n')

        product = ProductIdentity(
            display_name="DiskPkg", canonical_import="diskpkg",
            platform="python", family="test",
        )
        recipe = extract_install_recipe(tmp_path, product, shared_facts=None)
        assert recipe is not None
        assert recipe.package_name == "diskpkg"
        assert recipe.source_file == "pyproject.toml"
```

---

### Sub-task C — TC-4031 Go extraction tests

**File**: `tests/unit/workers/understand/test_go_extraction.py` *(new)*

```python
"""Tests for TC-4031 Go extraction depth: struct fields, typed params, iota enums."""
from __future__ import annotations

import pathlib
import pytest

pytestmark = pytest.mark.skipif(
    pytest.importorskip("tree_sitter", reason="tree-sitter not installed") is None,
    reason="tree-sitter not installed",
)


def _go_file(tmp_path: pathlib.Path, content: str) -> pathlib.Path:
    p = tmp_path / "example.go"
    p.write_text(content, encoding="utf-8")
    return p


def _has_go_grammar() -> bool:
    try:
        import sys; sys.path.insert(0, "src")  # noqa: E702
        from launcher.shared.ts_analyzer import _get_parser
        return _get_parser("go") is not None
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _has_go_grammar(),
    reason="tree-sitter Go grammar not available",
)


class TestGoStructFieldExtraction:
    """TC-4031: Go struct exported fields appear in property_details."""

    def test_exported_struct_fields_extracted(self, tmp_path):
        p = _go_file(tmp_path, """
package example

type Point struct {
    X float64
    Y float64
    z int  // unexported — must be excluded
}
""")
        import sys; sys.path.insert(0, "src")  # noqa: E702
        from launcher.shared.ts_analyzer import analyzer

        result = analyzer.analyze_file(p, language="go")
        structs = {c["name"]: c for c in result.classes}
        assert "Point" in structs, f"Point not found in {list(structs.keys())}"
        props = {p["name"] for p in structs["Point"]["property_details"]}
        assert "X" in props
        assert "Y" in props
        assert "z" not in props, "unexported field 'z' must be excluded"

    def test_struct_field_type_annotations(self, tmp_path):
        p = _go_file(tmp_path, """
package example

type Node struct {
    Value int
    Next  *Node
    Tags  []string
}
""")
        from launcher.shared.ts_analyzer import analyzer

        result = analyzer.analyze_file(p, language="go")
        structs = {c["name"]: c for c in result.classes}
        prop_types = {
            pd["name"]: pd["type_annotation"]
            for pd in structs["Node"]["property_details"]
        }
        assert prop_types.get("Value") == "int"
        # Pointer and slice types are extracted as-is
        assert "Next" in prop_types
        assert "Tags" in prop_types


class TestGoTypedParameters:
    """TC-4031: Go function parameters include type annotations."""

    def test_function_typed_params(self, tmp_path):
        p = _go_file(tmp_path, """
package example

func Add(a int, b int) int {
    return a + b
}
""")
        from launcher.shared.ts_analyzer import analyzer

        result = analyzer.analyze_file(p, language="go")
        funcs = {f["name"]: f for f in result.functions}
        assert "Add" in funcs
        params = funcs["Add"].get("parameters", [])
        param_map = {pm["name"]: pm["type_annotation"] for pm in params}
        assert param_map.get("a") == "int"
        assert param_map.get("b") == "int"


class TestGoIotaEnumSynthesis:
    """TC-4031: Go const blocks with iota produce synthetic enum class entries."""

    def test_standard_iota_enum(self, tmp_path):
        p = _go_file(tmp_path, """
package example

type Direction int

const (
    North Direction = iota
    South
    East
    West
)
""")
        from launcher.shared.ts_analyzer import analyzer

        result = analyzer.analyze_file(p, language="go")
        enums = [c for c in result.classes if c.get("is_enum")]
        assert len(enums) == 1, f"Expected 1 enum, got {len(enums)}: {enums}"
        assert enums[0]["name"] == "Direction"
        member_names = {m["name"] for m in enums[0]["enum_members"]}
        assert "North" in member_names
        assert "South" in member_names
        assert "East" in member_names
        assert "West" in member_names

    def test_mixed_type_iota_not_emitted(self, tmp_path):
        """A const block with iota but mixed types should not produce a synthetic enum."""
        p = _go_file(tmp_path, """
package example

const (
    A Foo = iota
    B Bar  // different type — mixed
)
""")
        from launcher.shared.ts_analyzer import analyzer

        result = analyzer.analyze_file(p, language="go")
        enums = [c for c in result.classes if c.get("is_enum")]
        assert len(enums) == 0, f"Mixed-type iota should not produce enum: {enums}"

    def test_const_without_iota_not_emitted(self, tmp_path):
        """A const block without iota must not produce a synthetic enum."""
        p = _go_file(tmp_path, """
package example

const (
    MaxSize = 100
    MinSize = 1
)
""")
        from launcher.shared.ts_analyzer import analyzer

        result = analyzer.analyze_file(p, language="go")
        enums = [c for c in result.classes if c.get("is_enum")]
        assert len(enums) == 0
```

---

### Sub-task D — TC-4031 C++ extraction tests

**File**: `tests/unit/workers/understand/test_cpp_extraction.py` *(new)*

```python
"""Tests for TC-4031 C++ tree-sitter extraction depth."""
from __future__ import annotations

import pathlib
import pytest


def _has_cpp_grammar() -> bool:
    try:
        import sys; sys.path.insert(0, "src")  # noqa: E702
        from launcher.shared.ts_analyzer import _get_parser
        return _get_parser("cpp") is not None
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _has_cpp_grammar(),
    reason="tree-sitter C++ grammar not available",
)


def _cpp_file(tmp_path: pathlib.Path, content: str) -> pathlib.Path:
    p = tmp_path / "example.cpp"
    p.write_text(content, encoding="utf-8")
    return p


class TestCppClassExtraction:
    """TC-4031: C++ class/struct extraction via tree-sitter."""

    def test_class_name_extracted(self, tmp_path):
        p = _cpp_file(tmp_path, """
class MyClass {
public:
    void doSomething();
};
""")
        import sys; sys.path.insert(0, "src")  # noqa: E702
        from launcher.shared.ts_analyzer import analyzer

        result = analyzer.analyze_file(p, language="cpp")
        names = {c["name"] for c in result.classes}
        assert "MyClass" in names

    def test_public_method_extracted(self, tmp_path):
        p = _cpp_file(tmp_path, """
class Foo {
public:
    int compute(int x, int y);
private:
    int secret();
};
""")
        from launcher.shared.ts_analyzer import analyzer

        result = analyzer.analyze_file(p, language="cpp")
        classes = {c["name"]: c for c in result.classes}
        assert "Foo" in classes
        method_names = {m["name"] for m in classes["Foo"]["method_details"]}
        assert "compute" in method_names
        assert "secret" not in method_names, "private method must be excluded"

    def test_struct_public_by_default(self, tmp_path):
        """C++ struct members are public by default — must be extracted."""
        p = _cpp_file(tmp_path, """
struct Vec2 {
    float x;
    float y;
};
""")
        from launcher.shared.ts_analyzer import analyzer

        result = analyzer.analyze_file(p, language="cpp")
        classes = {c["name"]: c for c in result.classes}
        assert "Vec2" in classes
        prop_names = {pd["name"] for pd in classes["Vec2"]["property_details"]}
        assert "x" in prop_names
        assert "y" in prop_names


class TestCppAdapterFallback:
    """TC-4031: CppExtractor falls back to code_analyzer when tree-sitter returns empty."""

    def test_fallback_invoked_when_ts_returns_empty(self, tmp_path):
        """If ts_analyzer returns no classes, code_analyzer is called."""
        from unittest.mock import patch, MagicMock
        from launcher.workers.understand.adapters._cpp import CppExtractor
        from launcher.models.product import ProductIdentity

        p = tmp_path / "empty.cpp"
        p.write_text("// no classes here\n", encoding="utf-8")

        product = ProductIdentity(
            display_name="Test", canonical_import="test",
            platform="cpp", family="test",
        )
        extractor = CppExtractor()

        mock_ts_result = MagicMock()
        mock_ts_result.classes = []  # empty — triggers fallback

        with patch(
            "launcher.shared.ts_analyzer.TreeSitterAnalyzer.analyze_file",
            return_value=mock_ts_result,
        ):
            with patch(
                "launcher.shared.code_analyzer.analyze_file_safe",
                return_value={"classes": [{"name": "FallbackClass"}]},
            ) as mock_fallback:
                result = extractor.extract_class_details(p, tmp_path, product)

        mock_fallback.assert_called_once()
        assert result == [{"name": "FallbackClass"}]
```

---

### Acceptance checks (SQP-H4 overall)

**CLI**:
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/understand/test_snippets_io.py \
  tests/unit/workers/test_scout_facts_extended.py \
  tests/unit/workers/understand/test_go_extraction.py \
  tests/unit/workers/understand/test_cpp_extraction.py \
  -v
```
All tests collected must pass. Grammar-dependent tests are skipped (not failed)
when the grammar is unavailable.

**UI/Web/API**: N/A.

**Tests**: See sub-tasks A–D above. Key coverage:
- OSError guard: primary, fallback, non-OSError propagation, success path
- SharedFacts: PEP 518 list, Poetry dict, absent field, `_extract_shared_facts` integration
- Install recipe: cache bypass confirmed by `builtins.open` tracking
- Go: struct fields (exported/unexported), typed params, iota enum (standard/mixed/no-iota)
- C++: class name, public/private filtering, fallback trigger

**Config respected end-to-end**: No configuration changes introduced by tests.
Grammar-dependent tests use `pytest.mark.skipif` — they don't fail CI when grammars
are absent.

**No mock data in production paths**: tests use `tmp_path` with real TOML/Go/C++ content;
no fixtures that bypass the actual parsing code paths.

### Deliverables

1. **`tests/unit/workers/understand/test_snippets_io.py`** — new, full content as above
2. **`tests/unit/workers/test_scout_facts_extended.py`** — new, full content as above
3. **`tests/unit/workers/understand/test_go_extraction.py`** — new, full content as above
4. **`tests/unit/workers/understand/test_cpp_extraction.py`** — new, full content as above

All files are complete (no stubs, no `pass` placeholders).

### Hard rules

- No network in offline tests — all tests use `tmp_path`; no LLM calls.
- No new deps beyond `pytest` (already installed).
- Grammar tests use `pytest.mark.skipif` so they don't block CI when grammars are absent.
- All tests must be `PYTHONHASHSEED=0` deterministic.
- Keep `tests/unit/workers/understand/__init__.py` — it must exist for pytest collection.

### Review dimensions — what "5/5" means for this taskcard

| Dimension | 5/5 criterion |
|-----------|---------------|
| Coverage | Every new code path (TC-4032/4030/4031) has ≥1 test for happy path + ≥1 failure/regression path |
| Correctness | Tests actually call the production code (no mocking of the function under test itself) |
| Robustness | Grammar-absent environments are handled via `skipif`, not `xfail` or bare `import` |
| No mock data in production paths | `tmp_path` + real TOML/Go/C++ source used throughout |
| Determinism | `PYTHONHASHSEED=0` produces identical results on repeated runs |

### Now (runbook)

```bash
# 1. Create the four test files (content above)

# 2. Ensure __init__.py exists for the understand test subdirectory
touch tests/unit/workers/understand/__init__.py  # usually exists

# 3. Run them in isolation first
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/understand/test_snippets_io.py -v

PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/test_scout_facts_extended.py -v

# Grammar tests — may skip if grammar not installed
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/understand/test_go_extraction.py \
  tests/unit/workers/understand/test_cpp_extraction.py -v

# 4. Confirm no interference with existing suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/understand/ tests/unit/workers/test_scout_facts.py \
  tests/unit/shared/test_ts_analyzer.py -x -q
```
