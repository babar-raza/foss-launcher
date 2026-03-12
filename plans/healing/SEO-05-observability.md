# SEO-05: Observability — Event Emission + Description Chain Logging

## Status: Done

## Gap Linkage
- **G-08**: No structured event emission for Phase 1.5 — breaks observability pattern
- **G-09**: No debug logging for description priority chain selection

## Role
Senior engineer. Drop-in, production-ready.

## Scope

### Fix
1. **Add `context.emit_event("seo_optimized", {...})` after Phase 1.5 loop** in
   `worker.py`. Event payload:
   ```python
   {
       "pages_processed": len(page_results),
       "seo_failures": seo_failures,  # from SEO-01 try/except counter
   }
   ```
   This matches the existing pattern where every phase emits a structured event.

2. **Add debug logging to `_generate_description` priority chain** in
   `seo_metadata.py`. At each fallback level, log which source was selected:
   ```python
   logger.debug("[SEO] %s: description source=gemini|purpose|content|claim|template", page_ir.page_id)
   ```
   This enables diagnosis of why a particular page got a template description
   vs a Gemini-generated one.

3. **Add per-page info logging to `optimize_seo_metadata`** showing which
   fields were added/modified:
   ```python
   logger.debug("[SEO] %s: fields set: %s", page_ir.page_id, ", ".join(changed_fields))
   ```

### Allowed paths
- `src/launcher/workers/generate/worker.py` (event emission)
- `src/launcher/workers/generate/seo_metadata.py` (debug logging)
- `plans/healing/SEO-05-observability.md`

### Forbidden
Any other file/path.

## Acceptance Checks

### CLI
- `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q` — all pass

### Tests
- Existing tests pass (logging doesn't affect behavior)
- No new tests required (observability is verified by log inspection, not assertions)

### Config respected end-to-end
- Debug logging controlled by standard Python logging level (no new config)

### No mock data in production paths
- N/A

## Deliverables
- Event emission line in `worker.py` Phase 1.5
- Debug log lines in `_generate_description` and `optimize_seo_metadata`

## Hard Rules
- No behavioral changes
- Event schema matches existing `emit_event` patterns
- Logging at DEBUG level (not INFO) for per-page detail
- No new deps
- Code/tests in sync

## Review Dimensions — What 5/5 Means

| Dimension | 5/5 Definition |
|-----------|----------------|
| Observability | Every description source decision is traceable in debug logs |
| Consistency | Event emission matches worker_started/worker_completed pattern |
| Minimality | Only log/event additions, zero behavioral change |
| Production grading | Operators can diagnose "why did this page get a template description" from logs |

## Runbook

```bash
# 1. Add emit_event("seo_optimized") in worker.py
# 2. Add logger.debug lines in seo_metadata.py
# 3. Run tests to verify no regressions
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
# 4. Manual verification: run a pilot with DEBUG logging, confirm SEO log lines appear
# 5. Mark Done
```
