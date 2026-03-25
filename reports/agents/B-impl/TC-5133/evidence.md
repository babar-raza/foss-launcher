# TC-5133 Evidence — LLM Cache Default-On + Fallback Caching + Bust Mode

## Changes Made

### `src/launcher/clients/llm_cache.py`
- Changed `cache_enabled()` default from `"0"` to `"1"` (cache enabled by default)
- Added `cache_bust_enabled()` function reading `FOSS_LAUNCHER_LLM_CACHE_BUST` env var
- Updated module docstring to reflect two-pass algorithm

### `src/launcher/clients/llm_provider.py`
- Integrated bust mode: when `cache_bust_enabled()`, skip `llm_cache.load()` but keep `llm_cache.save()`
- Changed `FOSS_LAUNCHER_LLM_CACHE_FALLBACK` default from `"0"` to `"1"`
- Bust mode emits telemetry event for observability

### `tests/unit/clients/test_llm_cache.py`
- Updated `test_enabled_by_default` to assert `True` (was `False`)
- Added `TestCacheBust` class with 3 tests
- Added `FOSS_LAUNCHER_LLM_CACHE_BUST` to `clean_env` fixture

### `tests/unit/cli/test_heal_cli.py`
- Updated `test_cache_env_not_set_when_heal_not_active` to match new default-on behavior

## Test Results

```
tests/unit/clients/test_llm_cache.py: 14/14 PASS
tests/unit/cli/test_heal_cli.py: all PASS (after test update)
Full suite: 5096 passed, 0 failed
```

## Acceptance Checks

- [x] `cache_enabled()` defaults to True (no env var)
- [x] `FOSS_LAUNCHER_LLM_CACHE=0` disables cache
- [x] Bust mode: reads skipped, writes preserved
- [x] All existing tests pass
- [x] New unit tests pass
