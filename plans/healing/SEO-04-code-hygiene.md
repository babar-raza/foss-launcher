# SEO-04: Code Hygiene — Regex Hoisting, Stop-Word Dedup, Contract Clarity

## Status: Done

## Gap Linkage
- **G-06**: `_entity_re` compiled inside function body on every call — perf waste
- **G-07**: Duplicate stop-word lists in `seo_metadata.py` and `plan.py`
- **G-11**: `_enforce_metadata_quality` mutates dict in-place AND returns it — unclear contract

## Role
Senior engineer. Drop-in, production-ready.

## Scope

### Fix
1. **Hoist regex to module level** in `seo.py`:
   Move `_entity_re = re.compile(...)` from inside `check_seo()` to module-level
   constant `_HTML_ENTITY_RE`. Update the reference inside the function.

2. **Deduplicate stop-word set**: Create a shared constant `_SEO_STOP_WORDS` in
   `seo_metadata.py` and import it in `plan.py` (or define in a shared location).
   Both `_enhance_keywords()` in `seo_metadata.py` and `_generate_seo_keywords()`
   in `plan.py` currently define their own stop-word sets. Unify to one source.

3. **Clarify `_enforce_metadata_quality` contract**: The function currently
   mutates the input dict in-place AND returns it. Change to return a new dict
   (shallow copy at entry), making the contract clear: input is not mutated.
   Update the caller in `optimize_seo_metadata` to use the return value (it
   already does, so this is a safety improvement).

### Allowed paths
- `src/launcher/workers/evaluate/checks/seo.py` (regex hoist)
- `src/launcher/workers/generate/seo_metadata.py` (stop words, enforce contract)
- `src/launcher/workers/planner/plan.py` (import shared stop words)
- `tests/unit/workers/test_seo_metadata.py` (verify contract)
- `plans/healing/SEO-04-code-hygiene.md`

### Forbidden
Any other file/path.

## Acceptance Checks

### CLI
- `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q` — all pass

### Tests
- Existing tests pass without changes (behavioral parity)
- New test: `test_enforce_metadata_quality_does_not_mutate_input` — pass a dict,
  call `_enforce_metadata_quality`, verify original dict is unchanged

### Config respected end-to-end
- N/A

### No mock data in production paths
- N/A

## Deliverables
- Module-level `_HTML_ENTITY_RE` in `seo.py`
- Shared `_SEO_STOP_WORDS` set accessible to both `seo_metadata.py` and `plan.py`
- Non-mutating `_enforce_metadata_quality`
- 1 new test

## Hard Rules
- No behavioral changes — output must be identical
- No network in tests
- No new deps
- Code/tests in sync

## Review Dimensions — What 5/5 Means

| Dimension | 5/5 Definition |
|-----------|----------------|
| Performance | Regex compiled once at import, not per-call |
| Maintainability | Single stop-word source, clear mutation contract |
| Consistency | Pattern matches rest of codebase (module-level compiled regex) |
| Minimality | Only the 3 targeted hygiene fixes, no scope creep |

## Runbook

```bash
# 1. Hoist _HTML_ENTITY_RE in seo.py
# 2. Extract _SEO_STOP_WORDS, update both files
# 3. Fix _enforce_metadata_quality to copy-then-mutate
# 4. Add test_enforce_metadata_quality_does_not_mutate_input
# 5. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
# 6. Mark Done
```
