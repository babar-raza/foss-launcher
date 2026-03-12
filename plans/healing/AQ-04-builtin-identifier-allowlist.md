# AQ-04 — Builtin Identifier Allowlist in Method Validation

**Status**: Done
**Gap linkage**: GAP-04 (High — Python builtins get their backticks stripped)
**Role**: Senior engineer. Drop-in, production-ready.

## Context

`_validate_identifiers()` in `worker.py` strips backticks from any identifier not in `api_identifiers`. This incorrectly strips backticks from Python builtins (`str`, `int`, `list`, `dict`, `Path`, `None`, `True`, `False`, `bytes`) and common type annotations (`Optional`, `Any`, `Union`) that are legitimately backticked in technical prose.

Example: `` Use `str` to convert the value `` → becomes `Use str to convert the value` which looks inconsistent with surrounding backticked API names.

## Scope

### Fix

Add a `_BUILTIN_IDENTIFIERS` frozenset containing Python builtins and common type names. In `_replacer()`, skip stripping if the identifier is in this set.

### Allowed paths
- `src/launcher/workers/generate/worker.py`
- `tests/unit/workers/generate/test_method_validation.py`

### Forbidden
- Any other file/path

## Acceptance checks

- **CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/generate/test_method_validation.py -v --tb=short` — all pass
- **Tests**: `` `str` `` in paragraph → backticks preserved
- **Tests**: `` `Path` `` in paragraph → backticks preserved
- **Tests**: `` `None` `` in paragraph → backticks preserved
- **Tests**: `` `FakeMethod()` `` not in api_identifiers and not a builtin → backticks stripped
- **No mock data in production paths**: Uses real BlockIR objects

## Deliverables

1. `_BUILTIN_IDENTIFIERS` frozenset in `worker.py`
2. Modified `_replacer()` to check builtins
3. New tests for builtin preservation
4. Updated existing test expectations if needed

## Hard rules

- Keep public signatures unless justified; update all call sites
- No network in offline tests
- No new deps without explicit justification
- Keep code/docs/tests in sync

## Review dimensions — what 5/5 means

| Dimension | 5/5 target |
|-----------|-----------|
| Correctness | No legitimate Python identifier gets its backticks stripped |
| Robustness | Builtin set is comprehensive: primitives, containers, singletons, typing |
| Minimality | One frozenset + one `or` condition + tests |
| Maintainability | Frozenset is a clear, named constant — easy to extend |

## Now (runbook)

```bash
# 1. Add before _BACKTICK_RE in worker.py:
#    _BUILTIN_IDENTIFIERS = frozenset({
#        "str", "int", "float", "bool", "list", "dict", "set", "tuple",
#        "bytes", "bytearray", "None", "True", "False", "type", "object",
#        "Path", "Optional", "Any", "Union", "Callable", "Iterator",
#        "Generator", "Sequence", "Mapping", "Iterable",
#    })

# 2. In _replacer(), change:
#    if ident in api_identifiers:
#    to:
#    if ident in api_identifiers or ident in _BUILTIN_IDENTIFIERS:

# 3. Add tests to test_method_validation.py

# 4. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/generate/test_method_validation.py -v --tb=short

# 5. Run full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=short
```
