# HG-03 — Add `extract_install_recipe()` to Adapter Interface

**Status**: Not Started
**Gap linkage**: G3 (`extract_install_recipe()` not in adapter interface)
**Role**: Senior engineer. Drop-in, production-ready.
**Priority**: High

## Context

The humming-greeting-kay plan spec (Platform Adapter Interface section) explicitly
defines `extract_install_recipe()` as an abstract method on `PlatformExtractor`:

```python
@abstractmethod
def extract_install_recipe(
    self, repo_dir: Path, product: ProductIdentity,
) -> InstallRecipe | None:
    """Extract deterministic install command from manifest files."""
```

The current `_base.py` does NOT include this method. As a result:
- The Python adapter cannot provide `dotnet add package` or `go get` commands
- The install recipe extraction in `_entry.py` is Python-only (calls `extract_install_recipe`
  from `_deterministic.py` unconditionally, regardless of platform)
- Non-Python platforms get `InstallRecipe(pip_command="")` — silent wrong answer

## Scope

### Fix

1. Add `extract_install_recipe()` as a non-abstract default method on `_base.py`
   (default returns None — fail-open, not abstract, to preserve backwards compat)
2. Implement in `_python.py`: delegate to existing `_deterministic.extract_install_recipe()`
3. Implement in `_dotnet.py`: parse `*.csproj` for `<PackageReference>` to get package ID;
   emit `dotnet add package {package_id}`
4. Implement in `_java.py`: parse `pom.xml` for `<groupId>/<artifactId>` to get Maven coords;
   emit `mvn dependency:get -Dartifact={groupId}:{artifactId}:{version}`
5. Update `_entry.py` to call `_adapter.extract_install_recipe(repo_dir, product)` when
   adapter is available, falling back to `_deterministic.extract_install_recipe()` only
   for Python
6. Write tests for each adapter's install recipe extraction

### Allowed paths

```
src/launcher/workers/understand/adapters/_base.py
src/launcher/workers/understand/adapters/_python.py
src/launcher/workers/understand/adapters/_dotnet.py
src/launcher/workers/understand/adapters/_java.py
src/launcher/workers/understand/adapters/_cpp.py
src/launcher/workers/understand/adapters/_generic.py
src/launcher/workers/understand/extract/_entry.py
tests/unit/workers/test_understand.py
plans/taskcards/TC-4009_adapter_install_recipe.md
```

### Forbidden

All other paths. `_deterministic.py` is read-only (its `extract_install_recipe()`
is still called by Python adapter; not replaced).

## Acceptance checks

### CLI
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand.py -k "install_recipe" -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest --tb=no -q
```
Zero new failures.

### Tests
- `test_python_adapter_install_recipe_pyproject`: fixture with pyproject.toml → correct pip command
- `test_dotnet_adapter_install_recipe_csproj`: fixture with .csproj → `dotnet add package X`
- `test_java_adapter_install_recipe_pom`: fixture with pom.xml → Maven coords
- `test_generic_adapter_install_recipe_returns_none`: unknown platform → None
- `test_entry_uses_adapter_install_recipe`: mock adapter with known install → recipe in ProductEvidence
- Failure path: malformed pom.xml → None, no exception

### Config respected end-to-end
- `_entry.py` uses adapter's install recipe when adapter is not None
- Falls back to `_deterministic.extract_install_recipe()` only for Python with no adapter

### No mock data in production paths
- Tests use `tmp_path` fixture with real file content (pyproject.toml, .csproj, pom.xml snippets)

## Deliverables

1. Updated `_base.py` with default `extract_install_recipe()` method
2. Updated `_python.py`, `_dotnet.py`, `_java.py` implementations
3. Updated `_entry.py` dispatch logic
4. 6+ new tests in `test_understand.py`
5. `plans/taskcards/TC-4009_adapter_install_recipe.md`

## Hard rules

- `extract_install_recipe()` on `_base.py` MUST be non-abstract (default returns None)
  to preserve backwards compatibility with existing adapters
- Keep public signatures of all adapter methods unchanged except adding new method
- `_cpp.py` and `_generic.py` inherit default (return None) — no changes needed unless
  package managers are added
- No new dependencies (use `xml.etree.ElementTree` for pom.xml, stdlib only)

## Review dimensions (5/5 targets)

| Dimension | 5/5 means |
|-----------|-----------|
| Correctness | Each platform produces correct install command from real manifest |
| Robustness | Malformed manifests → None, no exception; MissingInfoEntry recorded |
| Testability | Each adapter install recipe has unit test with tmp_path fixture |
| Consistency | All adapters implement same interface; _base.py is authoritative spec |
| Minimality | Only 6 files changed; no unrelated refactoring |

## Now (runbook)

```
1. Read src/launcher/workers/understand/adapters/_base.py (current interface)
2. Read src/launcher/workers/understand/extract/_deterministic.py (existing Python recipe logic)
3. Add default method to _base.py:
   def extract_install_recipe(self, repo_dir, product) -> InstallRecipe | None:
       return None
4. In _python.py: import and delegate to _deterministic.extract_install_recipe()
5. In _dotnet.py: parse first .csproj found; emit "dotnet add package {name}"
6. In _java.py: parse pom.xml groupId/artifactId; emit maven/gradle coords
7. In _entry.py: replace unconditional _deterministic call with:
   if _adapter: install_recipe = _adapter.extract_install_recipe(repo_dir, product)
   else: install_recipe = extract_install_recipe(repo_dir, product)
8. Write 6 tests
9. Run: PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand.py -v
10. Run full suite
```
