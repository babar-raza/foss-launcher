# BT-02: Cache Compiled Regex Pattern for API Identifiers

**Status**: Done
**Gap linkage**: BT-00 → BT-02
**Role**: Engineer
**Severity**: MEDIUM — performance regression, ~200 recompilations per pilot run

## Problem

`_backtick_api_names()` in `section_validator.py` builds and compiles a regex pattern from up to 500 API identifiers on every call. This function is called once per block, ~200 times per pilot run. The pattern is identical across all calls within a single page generation (same `api_identifiers` set).

## Scope

**In scope**: Cache the compiled regex pattern so it's built once per identifier set.
**Out of scope**: Caching across different pages/runs, global state.

## Fix

Use `functools.lru_cache` on a helper that compiles the pattern from a frozen identifier tuple:

```python
@functools.lru_cache(maxsize=4)
def _compile_api_pattern(identifiers: tuple[str, ...]) -> re.Pattern[str]:
    sorted_ids = sorted(identifiers, key=len, reverse=True)
    escaped = [re.escape(ident) for ident in sorted_ids]
    return re.compile(r"\b(" + "|".join(escaped) + r")\b")
```

Call site in `_backtick_api_names()`:
```python
pattern = _compile_api_pattern(tuple(sorted(api_identifiers)))
```

## Acceptance Checks

- [ ] Pattern compiled once per unique identifier set (verified via `_compile_api_pattern.cache_info()` in test)
- [ ] Behavior identical to uncached version — same backtick output
- [ ] Existing tests pass
- [ ] No global mutable state introduced

## Deliverables

- Modified: `src/launcher/workers/generate/section_validator.py`
- Test in: `tests/test_section_validator.py`

## Hard Rules

- Cache key must be a frozen/hashable type (tuple, not set)
- `maxsize` >= 2 (at least two pages could be in-flight)
- No module-level mutable state

## Review Dimensions

1. Cache hit rate: second call with same identifiers reuses compiled pattern
2. Cache miss: different identifier set compiles new pattern
3. Thread safety: `lru_cache` is thread-safe by default
4. Memory: maxsize=4 bounds memory usage

## Now (Runbook)

1. Read `section_validator.py:_backtick_api_names()` (lines 313-363)
2. Extract pattern compilation into `_compile_api_pattern()` with `@lru_cache`
3. Update `_backtick_api_names()` to call the cached helper
4. Write test verifying cache hit on repeated calls
5. Run full test suite
