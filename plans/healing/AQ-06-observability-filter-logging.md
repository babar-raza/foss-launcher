# AQ-06 — Observability: Filter Stage Logging + Pipeline Events

**Status**: Done
**Gap linkage**: GAP-08 (no logging in _extract_api_surface for filter stages), GAP-10 (no context.emit_event for new stages)
**Role**: Senior engineer. Drop-in, production-ready.

## Context

The contamination filter in `_extract_api_surface()` silently filters files and classes. In production, when debugging why a class is missing from the API surface, there is no log trail showing:
- How many files were found vs how many passed the package-root filter
- How many files passed the canonical-import filter
- How many classes were removed by the internal-class heuristic
- How many ClassBriefs were generated

Additionally, the new pipeline stages (docstring harvesting, synthetic snippets, density pruning) don't emit `context.emit_event()` calls, making them invisible to the telemetry system.

## Scope

### Fix

1. Add `logger.info()` calls at each filter stage in `_extract_api_surface()`
2. Add `context.emit_event()` calls in `run_extract()` for docstring harvesting and synthetic snippet generation
3. Add `logger.info()` in `_prune_thin_pages()` listing which pages were pruned and why

### Allowed paths
- `src/launcher/workers/understand/extract.py`
- `src/launcher/workers/planner/plan.py`
- `tests/unit/workers/understand/test_extract.py`

### Forbidden
- Any other file/path

## Acceptance checks

- **CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=short` — all pass
- **Tests**: Verify log messages are emitted (using `caplog` fixture) for filter stages
- **Config respected end-to-end**: Logging does not change any return values or behavior
- **No mock data in production paths**: Real file structures in tests

## Deliverables

1. Filter stage logging in `_extract_api_surface()`:
   - `logger.info("api_surface_filter: total_files=%d, package_root_files=%d, import_filtered=%d", ...)`
   - `logger.info("api_surface_classes: total=%d, internal_filtered=%d, public=%d, briefs=%d", ...)`
2. Pipeline events in `run_extract()`:
   - `context.emit_event("docstring_claims_harvested", {"count": len(docstring_claims)}, worker="understand")`
   - `context.emit_event("synthetic_snippets_generated", {"count": len(synthetic)}, worker="understand")`
3. Pruning logging in `_prune_thin_pages()`:
   - `logger.info("density_pruning: page=%s role=%s density=%.1f -> pruned", page.page_id, page.page_role, density)` for each pruned page
4. caplog-based tests verifying key log messages appear

## Hard rules

- Keep public signatures unless justified; update all call sites
- No network in offline tests
- No new deps without explicit justification
- Keep code/docs/tests in sync
- Logging must not alter behavior or return values

## Review dimensions — what 5/5 means

| Dimension | 5/5 target |
|-----------|-----------|
| Observability | Every filter stage has a quantified log line; telemetry consumers see new stages |
| Minimality | Only logger.info/emit_event additions; no logic changes |
| Production grading | A support engineer can trace "why is class X missing?" from logs alone |
| Testability | caplog tests confirm message format and presence |

## Now (runbook)

```bash
# 1. Add filter stage counters in _extract_api_surface:
#    - Count files at each stage (total, package_root, import_filtered)
#    - Count classes (raw, internal_filtered, public, with_briefs)
#    - Add logger.info at end with all counts

# 2. Add emit_event in run_extract for docstring + synthetic stages

# 3. Add per-page pruning log in _prune_thin_pages

# 4. Add caplog tests

# 5. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=short
```
