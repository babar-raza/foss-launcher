# SEO-14: Gemini Model Deprecation Fallback Chain

## Status: Done

## Gap Linkage
- **G-SR6**: When Google deprecated `gemini-2.0-flash` (quota=0), the client
  returned empty results with no actionable guidance. There is no model fallback
  chain — if `gemini-2.5-flash` is deprecated tomorrow, the same silent
  degradation occurs. The client should try a fallback model before giving up.

## Role
Senior engineer. Drop-in, production-ready.

## Scope

### Fix
In `gemini_client.py`:

1. Add a `_FALLBACK_MODELS` list: `["gemini-2.5-flash", "gemini-2.0-flash-lite"]`
   (ordered by preference after the primary model)

2. In `_call_api()`, when a 429 response body contains `"limit: 0"` or
   `"quota exceeded"` (case-insensitive), this indicates model deprecation
   rather than transient rate limiting. In this case:
   - Log a WARNING: `"[Gemini] Model {model} appears deprecated (quota=0),
     trying fallback"`
   - Try the next model in `_FALLBACK_MODELS`
   - If all models exhausted, return empty string (existing behavior)

3. Cache the working model for the session so subsequent calls skip deprecated
   models.

### Allowed paths
- `src/launcher/clients/gemini_client.py`
- `tests/unit/clients/test_gemini_client.py`
- `plans/healing/SEO-14-gemini-model-fallback.md`

### Forbidden
Any other file.

## Acceptance Checks

### CLI
- `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/clients/test_gemini_client.py -x -v` — all pass

### Tests
- `test_model_fallback_on_quota_zero` — 429 with "limit: 0" body triggers
  fallback to next model
- `test_model_fallback_caches_working_model` — second call skips deprecated model
- `test_all_models_deprecated_returns_empty` — all models return quota=0,
  final result is empty string
- No existing tests broken

## Deliverables
- `gemini_client.py`: fallback chain logic (~20 lines)
- `test_gemini_client.py`: 3 new tests

## Hard Rules
- No new dependencies
- Fallback is session-scoped, not persisted to disk
- Existing behavior unchanged when primary model works

## Review Dimensions

| Dimension | 5/5 Definition |
|-----------|----------------|
| Resilience | Deprecation doesn't silently kill SEO features |
| Correctness | Only quota=0 triggers fallback, not transient 429s |
| Testability | All 3 scenarios tested with mocked HTTP |
| Minimality | Focused change, no over-engineering |

## Runbook

```bash
# 1. Add _FALLBACK_MODELS and fallback logic to _call_api
# 2. Add 3 tests
# 3. Run targeted tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/clients/test_gemini_client.py -x -v
# 4. Full regression
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
# 5. Mark Done
```

```yaml
# machine-readable
taskcard_id: SEO-14
title: Gemini Model Deprecation Fallback Chain
status: Not Started
priority: P1
gaps: [G-SR6]
allowed_paths:
  - src/launcher/clients/gemini_client.py
  - tests/unit/clients/test_gemini_client.py
depends_on: []
```
