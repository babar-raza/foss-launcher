---
id: TC-1050-T1
title: "Complete code_analyzer.py TODOs"
status: In-Progress
priority: Normal
owner: "Agent-B"
updated: "2026-02-08"
tags: ["w2", "code-analysis", "intelligence", "todos"]
depends_on: ["TC-1041"]
allowed_paths:
  - plans/taskcards/TC-1050-T1_code_analyzer_todos.md
  - plans/taskcards/INDEX.md
  - src/launch/workers/w2_facts_builder/code_analyzer.py
  - tests/unit/workers/test_w2_code_analyzer.py
  - reports/agents/agent_b/TC-1050-T1/evidence.md
  - reports/agents/agent_b/TC-1050-T1/self_review.md
evidence_required:
  - reports/agents/agent_b/TC-1050-T1/evidence.md
  - reports/agents/agent_b/TC-1050-T1/self_review.md
spec_ref: "784056663bbe919578900c517d5e03abe1720734"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# Taskcard TC-1050-T1 — Complete code_analyzer.py TODOs

## Objective
Implement `_extract_modules_from_init()` and `_detect_public_entrypoints()` functions in code_analyzer.py to replace TODO placeholders and improve API surface understanding.

## Problem Statement
Two TODOs exist in code_analyzer.py at lines 303 and 307:
- Line 303: Module extraction from `__init__.py` returns empty array instead of actual module names
- Line 307: Public entrypoint detection is hardcoded to `["__init__.py"]` instead of dynamically discovering entrypoints

This prevents accurate representation of package structure and API surface area in product_facts.json.

## Required spec references
- specs/07_code_analysis_and_enrichment.md (Code analyzer implementation requirements)
- plans/taskcards/00_TASKCARD_CONTRACT.md (Taskcard format requirements)
- plans/taskcards/TC-1041_implement_code_analyzer.md (Parent taskcard for code analyzer implementation)

## Scope

### In scope
- Implement `_extract_modules_from_init()` to parse `__all__` assignment and import statements
- Implement `_detect_public_entrypoints()` to discover `__init__.py`, `__main__.py`, and setup.py entry_points
- Remove TODO comments at lines 303 and 307
- Add 3 new unit tests covering both functions
- Verify all existing tests pass

### Out of scope
- Modifying other parts of code_analyzer.py beyond the two TODO functions
- Adding support for additional language manifests (setup.cfg, etc.)
- Performance optimization (handled separately in TC-1050-T2)
- Integration testing beyond unit tests

## Inputs
- Existing code_analyzer.py with TODOs at lines 303 and 307
- Existing test suite in test_w2_code_analyzer.py with 498 tests
- Python AST and stdlib modules for parsing

## Outputs
- Implemented `_extract_modules_from_init()` function with __all__ and import fallback strategies
- Implemented `_detect_public_entrypoints()` function checking __init__.py, __main__.py, setup.py
- 3 new unit tests added to test_w2_code_analyzer.py
- Evidence bundle at reports/agents/agent_b/TC-1050-T1/evidence.md
- 12D self-review at reports/agents/agent_b/TC-1050-T1/self_review.md

## Allowed paths
- plans/taskcards/TC-1050-T1_code_analyzer_todos.md
- plans/taskcards/INDEX.md
- src/launch/workers/w2_facts_builder/code_analyzer.py
- tests/unit/workers/test_w2_code_analyzer.py
- reports/agents/agent_b/TC-1050-T1/evidence.md
- reports/agents/agent_b/TC-1050-T1/self_review.md

### Allowed paths rationale
TC-1050-T1 modifies code_analyzer.py to complete TODO implementations (lines 303, 307) and adds corresponding unit tests. Evidence and self-review are stored in reports/agents/agent_b/TC-1050-T1/.

## Implementation steps

### Step 1: Register taskcard in INDEX.md
Add TC-1050-T1 to the W2 Intelligence Refinements section in INDEX.md after TC-1050:

```markdown
- TC-1050-T1 — Complete code_analyzer.py TODOs — Agent-B, depends: TC-1041
```

### Step 2: Implement `_extract_modules_from_init()` function
Replace TODO at line 303 with:

```python
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
        logger.debug("extract_modules_failed", path=str(init_path), error=str(e))
        return []
```

### Step 3: Implement `_detect_public_entrypoints()` function
Replace TODO at line 307 with:

```python
def _detect_public_entrypoints(source_roots: List[Path]) -> List[str]:
    """
    Detect public entrypoints from directory structure.

    Checks for:
    - __init__.py (package entrypoint)
    - __main__.py (direct execution entrypoint)
    - setup.py with entry_points section

    Args:
        source_roots: List of source root directories

    Returns:
        List of entrypoint identifiers (defaults to ["__init__.py"] if none found)
    """
    entrypoints = []

    for root in source_roots:
        # Check for __init__.py
        if (root / '__init__.py').exists():
            if '__init__.py' not in entrypoints:
                entrypoints.append('__init__.py')

        # Check for __main__.py
        if (root / '__main__.py').exists():
            if '__main__.py' not in entrypoints:
                entrypoints.append('__main__.py')

        # Check for setup.py with entry_points
        setup_py = root.parent / 'setup.py'
        if setup_py.exists():
            try:
                content = setup_py.read_text(encoding='utf-8')
                if 'entry_points' in content:
                    if 'setup.py (entry_points)' not in entrypoints:
                        entrypoints.append('setup.py (entry_points)')
            except Exception:
                pass

    return entrypoints if entrypoints else ['__init__.py']  # Default fallback
```

### Step 4: Add unit tests
Add 3 new tests to test_w2_code_analyzer.py after the existing tests:

```python
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
    result = _detect_public_entrypoints([source_root])

    assert '__init__.py' in result
    assert '__main__.py' in result
```

### Step 5: Run new tests
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_w2_code_analyzer.py::test_extract_modules_from_init_with_all tests/unit/workers/test_w2_code_analyzer.py::test_extract_modules_from_imports tests/unit/workers/test_w2_code_analyzer.py::test_detect_public_entrypoints_main_py -xvs
```

Expected: 3/3 tests PASS

### Step 6: Run full test suite
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_w2_code_analyzer.py -x
```

Expected: All existing tests continue to pass (>=498 tests)

### Step 7: Create evidence bundle
Create reports/agents/agent_b/TC-1050-T1/evidence.md documenting:
- Code diffs for both functions
- New test code
- Test execution results
- Example module extractions from pilot repos

### Step 8: Complete 12D self-review
Create reports/agents/agent_b/TC-1050-T1/self_review.md scoring all 12 dimensions with evidence.

## Failure modes

### Failure mode 1: Functions are not visible to tests (import error)
**Detection:** ImportError when tests try to import `_extract_modules_from_init` or `_detect_public_entrypoints`
**Resolution:** Functions are currently at module level in code_analyzer.py. Ensure they are defined before `analyze_repository_code()` function. Check function names match exactly (including leading underscore).
**Spec/Gate:** Test execution requirements

### Failure mode 2: AST parsing fails on malformed __init__.py
**Detection:** Test failures showing unexpected empty lists or parse errors
**Resolution:** Both functions include try/except blocks with logging. Verify exception handling catches SyntaxError and other parse failures. Ensure fallback strategies execute correctly.
**Spec/Gate:** specs/07_code_analysis_and_enrichment.md error handling requirements

### Failure mode 3: Module extraction returns duplicates
**Detection:** Test assertions fail because result contains duplicate module names
**Resolution:** Use `set()` for intermediate storage in `_extract_modules_from_init()`. Apply `sorted()` to final result for determinism and deduplication.
**Spec/Gate:** Determinism requirements from pyproject.toml PYTHONHASHSEED=0

### Failure mode 4: Entrypoint detection misses __main__.py
**Detection:** test_detect_public_entrypoints_main_py fails with AssertionError
**Resolution:** Verify path construction uses `root / '__main__.py'` not `root.parent / '__main__.py'`. Check file existence with `.exists()` method before adding to list.
**Spec/Gate:** Unit test acceptance criteria

### Failure mode 5: setup.py detection false positive
**Detection:** Test adds 'setup.py (entry_points)' when setup.py has no entry_points
**Resolution:** String check `'entry_points' in content` is too broad. Consider regex pattern `r'entry_points\s*='` for more accurate detection. For now, simple string match is acceptable (documented limitation).
**Spec/Gate:** Code structure discovery requirements

### Failure mode 6: Missing logger import
**Detection:** NameError: name 'logger' is not defined when functions execute
**Resolution:** Verify `import logging` and `logger = logging.getLogger(__name__)` exist at module top. Both functions use logger.debug() which requires logger to be defined.
**Spec/Gate:** Python module structure requirements

## Task-specific review checklist
1. [ ] `_extract_modules_from_init()` handles `__all__` assignment with ast.literal_eval
2. [ ] `_extract_modules_from_init()` falls back to import statement extraction
3. [ ] `_extract_modules_from_init()` returns sorted list for determinism
4. [ ] `_detect_public_entrypoints()` checks for `__init__.py` existence
5. [ ] `_detect_public_entrypoints()` checks for `__main__.py` existence
6. [ ] `_detect_public_entrypoints()` checks setup.py for entry_points string
7. [ ] `_detect_public_entrypoints()` avoids duplicates in result list
8. [ ] `_detect_public_entrypoints()` returns default `['__init__.py']` if nothing found
9. [ ] TODO comments removed from lines 303 and 307
10. [ ] 3 new unit tests added to test_w2_code_analyzer.py
11. [ ] Test names follow convention `test_<function>_<scenario>`
12. [ ] All tests use tmp_path fixture for file system isolation
13. [ ] Tests verify exact expected behavior (sorted lists, set membership)
14. [ ] Existing test suite passes (>=498 tests)
15. [ ] Functions include docstrings with Args and Returns sections
16. [ ] Exception handling logs debug messages (not warnings/errors)

## Deliverables
- Modified src/launch/workers/w2_facts_builder/code_analyzer.py with implemented functions (lines 303, 307)
- Modified tests/unit/workers/test_w2_code_analyzer.py with 3 new tests
- Test execution results showing all tests pass (>=501 tests)
- Evidence bundle at reports/agents/agent_b/TC-1050-T1/evidence.md
- 12D self-review at reports/agents/agent_b/TC-1050-T1/self_review.md
- Updated plans/taskcards/INDEX.md with TC-1050-T1 entry

## Acceptance checks
1. [ ] `_extract_modules_from_init()` implemented and TODO removed (line 303)
2. [ ] `_detect_public_entrypoints()` implemented and TODO removed (line 307)
3. [ ] 3 new unit tests added (test_extract_modules_from_init_with_all, test_extract_modules_from_imports, test_detect_public_entrypoints_main_py)
4. [ ] New tests pass: 3/3 PASS
5. [ ] Full test suite passes: >=501/501 PASS (existing 498 + new 3)
6. [ ] Evidence bundle created with code diffs and test results
7. [ ] 12D self-review completed with all dimensions >= 4/5
8. [ ] TC-1050-T1 registered in INDEX.md

## Preconditions / dependencies
- TC-1041 complete (code_analyzer.py exists with TODO placeholders)
- Python virtual environment activated (.venv)
- All dependencies installed
- PYTHONHASHSEED=0 set for deterministic test execution

## Test plan
1. **Test case 1:** Extract modules from `__all__` assignment
   - Create `__init__.py` with `__all__ = ['mod_a', 'mod_b']`
   - Call `_extract_modules_from_init(path)`
   - Expected: `['mod_a', 'mod_b']` (sorted)

2. **Test case 2:** Extract modules from import statements
   - Create `__init__.py` with `import x`, `from y import z`
   - Call `_extract_modules_from_init(path)`
   - Expected: `['x', 'y']` (sorted, top-level modules only)

3. **Test case 3:** Detect entrypoints with __main__.py
   - Create src/ directory with `__init__.py` and `__main__.py`
   - Call `_detect_public_entrypoints([src_path])`
   - Expected: `['__init__.py', '__main__.py']`

4. **Test case 4:** Verify TODO comments removed
   - Open code_analyzer.py
   - Search for "TODO" at lines 303 and 307
   - Expected: No TODO comments found

5. **Test case 5:** Regression test existing functionality
   - Run full test suite
   - Expected: All 498+ existing tests continue to pass

## Self-review

### 12D Checklist

1. **Determinism:** Both functions return sorted lists. `_extract_modules_from_init()` uses `sorted()` on final result. `_detect_public_entrypoints()` maintains insertion order but avoids duplicates deterministically.

2. **Dependencies:** No new dependencies. Uses stdlib `ast`, `pathlib`, `logging`. Functions integrate with existing code_analyzer.py module structure.

3. **Documentation:** Both functions include complete docstrings with description, strategy/approach, Args, and Returns sections. Inline comments explain fallback strategies.

4. **Data preservation:** Functions do not modify input files. Read-only operations on __init__.py and directory structures. Exception handling prevents data corruption on parse failures.

5. **Deliberate design:**
   - `_extract_modules_from_init()`: Three-tier fallback (__all__ → imports → empty) provides maximum coverage
   - `_detect_public_entrypoints()`: Checks common entrypoint patterns with sensible default

6. **Detection:** Both functions log parse failures at debug level. Return empty/default values on errors. Callers can detect issues through empty module lists or default entrypoints.

7. **Diagnostics:** Functions log exceptions with file paths and error messages. Debug-level logging avoids noise while providing troubleshooting information.

8. **Defensive coding:**
   - Try/except blocks wrap file I/O and AST parsing
   - ast.literal_eval() safely evaluates __all__ values
   - Path existence checks before reading files
   - Fallback to empty list/default value on all error paths

9. **Direct testing:** 3 new unit tests directly verify function behavior. Tests use tmp_path for isolation. Assertions check exact expected outputs.

10. **Deployment safety:** Changes only affect unused TODO placeholders. Functions are called from `analyze_repository_code()` which is already tested. No API contract changes.

11. **Delta tracking:** Two function implementations replace TODOs. Three new tests added. Total diff: ~80 lines added. No breaking changes.

12. **Downstream impact:**
    - Enables accurate module and entrypoint discovery in product_facts.json
    - Improves api_surface and code_structure metadata quality
    - No breaking changes to existing code_analyzer API

### Verification results
- [ ] Tests: 3/3 new tests PASS (to be verified)
- [ ] Regression: >=498 existing tests PASS (to be verified)
- [ ] Evidence: reports/agents/agent_b/TC-1050-T1/evidence.md (to be created)

## E2E verification
```bash
# Run new tests only
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_w2_code_analyzer.py::test_extract_modules_from_init_with_all tests/unit/workers/test_w2_code_analyzer.py::test_extract_modules_from_imports tests/unit/workers/test_w2_code_analyzer.py::test_detect_public_entrypoints_main_py -xvs

# Run full code_analyzer test suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_w2_code_analyzer.py -x

# Verify TODOs removed
grep -n "TODO" src/launch/workers/w2_facts_builder/code_analyzer.py | grep -E "(303|307)"
```

**Expected artifacts:**
- **src/launch/workers/w2_facts_builder/code_analyzer.py** - Lines 303 and 307 have implemented functions instead of TODOs
- **tests/unit/workers/test_w2_code_analyzer.py** - Contains 3 new test functions at end of file
- **reports/agents/agent_b/TC-1050-T1/evidence.md** - Evidence bundle with diffs and results
- **reports/agents/agent_b/TC-1050-T1/self_review.md** - 12D review with scores

**Expected results:**
- New tests: 3/3 PASS
- Full suite: >=501 PASS, 0 FAIL
- No TODO comments at lines 303 or 307
- Functions return non-empty results on pilot repos

## Integration boundary proven
**Upstream:** `analyze_repository_code()` function calls both TODO functions at lines 303 and 307 during repository analysis. It passes `Path` objects and expects `List[str]` returns.

**Downstream:** Function results populate `product_facts.json`:
- `_extract_modules_from_init()` → `api_surface.modules`
- `_detect_public_entrypoints()` → `code_structure.public_entrypoints`

**Contract:**
- Input: `_extract_modules_from_init(Path)` receives __init__.py file path
- Input: `_detect_public_entrypoints(List[Path])` receives source root directories
- Output: Both return `List[str]` with sorted, deduplicated identifiers
- Error handling: Both return empty list/default on failures (never raise exceptions)
- Determinism: Both produce deterministic sorted outputs for same inputs

## Evidence Location
`reports/agents/agent_b/TC-1050-T1/evidence.md`
`reports/agents/agent_b/TC-1050-T1/self_review.md`
