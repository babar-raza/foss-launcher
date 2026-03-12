# SEO-01: Exception Safety for Phase 1.5 + Gemini Calls

## Status: Done

## Gap Linkage
- **G-01**: No exception safety in Phase 1.5 — one bad page crashes entire run
- **G-02**: Gemini call in `_generate_description` has no exception handling

## Role
Senior engineer. Drop-in, production-ready.

## Scope

### Fix
1. Wrap the Phase 1.5 per-page loop in `worker.py` with try/except so a single
   page failure logs a warning and continues with the original (un-optimized)
   PageIR rather than crashing the entire generation run.
2. Wrap the Gemini `generate_description()` call in `seo_metadata.py`
   `_generate_description()` with try/except, falling through to the next
   priority in the chain on any exception.
3. Add a counter for SEO failures and include it in the Phase 1.5 log line.

### Allowed paths
- `src/launcher/workers/generate/worker.py` (Phase 1.5 loop)
- `src/launcher/workers/generate/seo_metadata.py` (`_generate_description`)
- `tests/unit/workers/test_seo_metadata.py` (new failure-path tests)
- `plans/healing/SEO-01-exception-safety.md`

### Forbidden
Any other file/path.

## Acceptance Checks

### CLI
- `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q` — all pass

### Tests
- New test: `test_optimize_seo_metadata_survives_bad_frontmatter` — pass a PageIR
  with frontmatter containing non-string `title` (e.g., `None`, `123`). Verify
  result is returned without exception, with original or cleaned frontmatter.
- New test: `test_gemini_exception_falls_through` — mock Gemini client that raises
  `RuntimeError` on `generate_description`. Verify description falls through to
  next priority level (purpose/content/claim/template).
- New test: `test_phase15_bad_page_continues` — (integration-style) verify that
  if `optimize_seo_metadata` raises for one page, remaining pages are still processed.

### Config respected end-to-end
- N/A (no config changes)

### No mock data in production paths
- Mocks only in test files

## Deliverables
- Full replacement for the Phase 1.5 loop in `worker.py` with try/except
- Updated `_generate_description` with Gemini exception handling
- 3 new tests in `test_seo_metadata.py`

## Hard Rules
- Keep public signatures unchanged
- No network in offline tests
- Deterministic runs (no randomness)
- No new deps
- Code/tests in sync

## Review Dimensions — What 5/5 Means

| Dimension | 5/5 Definition |
|-----------|----------------|
| Thoroughness | Every exception path in Phase 1.5 and Gemini call is guarded |
| Consistency | Exception handling pattern matches existing worker error handling |
| Production grading | Zero chance of Phase 1.5 crashing the run |
| Correctness | Failed pages get original PageIR, not partially-mutated state |
| Robustness | Tested with None title, Gemini RuntimeError, arbitrary Exception |
| Testability | Each failure mode has a dedicated test |
| Observability | Failures logged with page_id, exception type, and traceback |
| Minimality | Only the try/except wrappers and tests added, nothing else |

## Runbook

```bash
# 1. Apply the Phase 1.5 exception wrapper in worker.py
# 2. Apply the Gemini exception wrapper in seo_metadata.py
# 3. Add 3 new tests to test_seo_metadata.py
# 4. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_seo_metadata.py -x -v
# 5. Full regression
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
# 6. Mark Done
```
