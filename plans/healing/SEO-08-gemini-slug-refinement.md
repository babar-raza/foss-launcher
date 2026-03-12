# SEO-08: Gemini Slug Refinement Wiring

## Status: Done

## Gap Linkage
- **G-14**: Gemini slug refinement in `_refine_page_slugs()` not implemented (plan spec)

## Role
Senior engineer. Drop-in, production-ready.

## Scope

### Fix
1. **Update `_refine_page_slugs()` in `plan.py`** to accept a `GeminiSEOClient`
   (or `GeminiClientLike` protocol from SEO-03) instead of the pipeline
   `llm_client`. When Gemini is available, use `gemini_client.refine_slugs()`
   for slug refinement. When Gemini is unavailable, fall back to the existing
   `strip_leading_stop_words()` algorithmic approach.

2. **Thread Gemini client through `run_plan()`**: Add a `gemini_client`
   parameter to `run_plan()`. The Planner worker instantiates the Gemini
   client from `GEMINI_API_KEY` env var and the SEO cache, then passes it.

3. **Remove or deprecate the `llm_client` parameter** for slug refinement
   in `run_plan()`. The pipeline LLM should not be used for slug refinement
   (Gemini handles it on the free tier, saving pipeline LLM quota).

### Allowed paths
- `src/launcher/workers/planner/plan.py` (`_refine_page_slugs`, `run_plan`)
- `src/launcher/workers/planner/worker.py` (instantiate Gemini client)
- `tests/unit/workers/test_plan_slugs.py` (verify Gemini slug integration)
- `plans/healing/SEO-08-gemini-slug-refinement.md`

### Forbidden
Any other file/path.

## Acceptance Checks

### CLI
- `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q` — all pass

### Tests
- New test: `test_refine_slugs_with_gemini` — mock `GeminiSEOClient.refine_slugs`
  returning cleaned slugs. Verify pages get Gemini-refined slugs.
- New test: `test_refine_slugs_gemini_unavailable_falls_back` — Gemini client
  with `available=False`. Verify algorithmic fallback used.
- New test: `test_refine_slugs_gemini_error_falls_back` — Gemini raises
  exception. Verify algorithmic fallback used.
- Existing slug tests must pass unchanged.

### Config respected end-to-end
- When `GEMINI_API_KEY` is not set, slug refinement uses algorithmic fallback
- When `seo.slug_rewrite: false` (from SEO-07), slug refinement is skipped entirely

### No mock data in production paths
- Gemini is mocked in tests

## Deliverables
- Updated `_refine_page_slugs()` with Gemini-first logic
- Updated `run_plan()` signature with `gemini_client` parameter
- Updated Planner worker to instantiate and pass Gemini client
- 3 new tests

## Hard Rules
- Keep backward compat: `gemini_client=None` falls back to algorithmic
- No network in tests (mock Gemini)
- Deterministic: Gemini responses cached, algorithmic fallback is deterministic
- No new deps (Gemini client already exists from TC-3807)
- Code/tests in sync

## Review Dimensions — What 5/5 Means

| Dimension | 5/5 Definition |
|-----------|----------------|
| Spec alignment | Matches plan: "Use Gemini instead of pipeline LLM for slug refinement" |
| Robustness | Gemini down → algorithmic fallback, never crash |
| Performance | Gemini responses cached per slug batch hash (existing cache in TC-3807) |
| Integration | Gemini client instantiation reuses SEOCache from understand worker |
| Testability | Happy path + unavailable + error all tested |

## Runbook

```bash
# 1. Update _refine_page_slugs() to accept gemini_client
# 2. Add gemini_client param to run_plan()
# 3. Update PlannerWorker.run() to instantiate GeminiSEOClient
# 4. Add 3 tests to test_plan_slugs.py
# 5. Run targeted tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_plan_slugs.py -x -v
# 6. Full regression
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
# 7. Mark Done
```
