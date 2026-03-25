# TC-PLAT-205 Evidence — Platform Adapter for TypeScript

**Date**: 2026-03-14
**Agent**: Agent-G
**Status**: Done

## Changes Made

### 1. `src/launcher/workers/generate/_identifier_repair.py`

- Added `_TYPESCRIPT_BUILTINS` frozenset with 50+ JS/TS runtime builtins (Promise, Array, Map, Set, WeakMap, WeakSet, Buffer, Error types, typed arrays, streams, web APIs, etc.)
- Added `_get_exempt_builtins(platform: str) -> frozenset[str]` dispatch function:
  - `"typescript"` / `"javascript"` -> returns `_PYTHON_BUILTINS | _TYPESCRIPT_BUILTINS`
  - `"dotnet"` / `"csharp"` -> returns `_PYTHON_BUILTINS` (stub for future)
  - Default -> returns `_PYTHON_BUILTINS`
- Updated `_build_exempt_set()` to accept `platform` parameter and use `_get_exempt_builtins(platform)` instead of hardcoded `_PYTHON_BUILTINS`
- Updated `repair_identifiers()` to accept optional `platform: str = "python"` parameter (backward compatible)

### 2. `src/launcher/workers/generate/fallback.py`

- Updated `_render_prerequisites_blocks()` to be platform-aware:
  - TypeScript/JavaScript: emits `npm install` and ES import syntax
  - .NET/C#: emits `dotnet add package` and `using` syntax
  - Python (default): unchanged `pip install` and `import` syntax
- Updated `_render_code_example_blocks()` with same platform dispatch
- Updated `render_minimal_stub()` import example with platform-aware import syntax

### 3. `src/launcher/workers/generate/worker.py`

- Updated `_normalize_code_languages()` to accept `platform: str = "python"` parameter
- Default language tag is now platform-aware via `get_lang_tag(platform)` instead of hardcoded `"python"`
- Updated both call sites (section-by-section path ~line 1588 and whole-page path ~line 1950) to pass `product.platform`
- Updated all 4 `repair_identifiers` call sites to pass `platform=product.platform or "python"`

## Tests Added

### `test_identifier_repair.py` — 8 new tests (class `TestPlatformAwareExemptions`)

| Test | Description | Result |
|------|-------------|--------|
| `test_typescript_builtins_exempt` | Promise NOT repaired for TS platform | PASS |
| `test_python_builtins_exempt_still_works` | Path NOT repaired for Python platform | PASS |
| `test_get_exempt_builtins_typescript` | Returns set containing Promise, Array, etc. | PASS |
| `test_get_exempt_builtins_python_default` | Returns set NOT containing Promise | PASS |
| `test_get_exempt_builtins_javascript_alias` | JS alias behaves same as TS | PASS |
| `test_default_platform_is_python` | Default platform omits TS builtins | PASS |
| `test_typescript_platform_exempts_abort_controller` | AbortController exempt for TS, not Python | PASS |

### `test_generate.py` — 7 new tests (classes `TestPlatformAwareFallback`, `TestNormalizeCodeLanguagesPlatformAware`)

| Test | Description | Result |
|------|-------------|--------|
| `test_fallback_typescript_npm_install` | TS fallback emits `npm install` | PASS |
| `test_fallback_python_pip_install` | Python fallback still emits `pip install` | PASS |
| `test_fallback_typescript_import_syntax` | TS fallback uses ES import syntax | PASS |
| `test_normalize_code_languages_typescript_default` | Default lang is `typescript` for TS | PASS |
| `test_normalize_code_languages_python_default` | Default lang is `python` for Python | PASS |
| `test_normalize_code_languages_shell_override` | Shell cmds still get `bash` tag | PASS |
| `test_normalize_code_languages_backward_compat` | No platform param defaults to `python` | PASS |

## Test Results

### Targeted tests
```
tests/unit/workers/generate/test_identifier_repair.py: 40 passed
tests/unit/workers/test_generate.py (platform tests): 7 passed
```

### Full suite
```
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=no
4500 passed, 65 skipped, 3 xfailed, 2 xpassed in 85.96s
```

## Backward Compatibility

All new parameters have defaults that preserve Python behavior:
- `repair_identifiers(..., platform="python")` — default
- `_build_exempt_set(..., platform="python")` — default
- `_normalize_code_languages(..., platform="python")` — default

All 4486+ existing tests pass unchanged with 0 failures.

## Acceptance Checks

- [x] TypeScript builtins not repaired when platform="typescript"
- [x] Python builtins still not repaired when platform="python"
- [x] Fallback emits platform-appropriate install commands
- [x] Default language tag is platform-aware
- [x] Full test suite: 4500 passed, 0 failed (exceeds 4486 threshold)
- [x] New tests: 15 (exceeds 6 minimum)
