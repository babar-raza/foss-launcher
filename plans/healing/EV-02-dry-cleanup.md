# EV-02 — DRY Cleanup: Deduplicate Shared Helpers

**Status:** Done (pre-existing)
**Gap linkage:** G-EV-03, G-EV-04
**Role:** Senior engineer. Drop-in, production-ready.

## Context

Three new check files define local `_strip_frontmatter` and `_strip_code_blocks` helpers identical to those already in `src/launcher/shared/jaccard.py`. Additionally, `repetition.py` defines a local `_jaccard()` function duplicating `jaccard_similarity()` from the same shared module. `artifacts.py` imports `collections.Counter` inside the function body instead of at module level.

## Scope

### Fix
1. In `repetition.py`: Remove local `_strip_frontmatter`, `_strip_code_blocks`, `_jaccard`. Import from `launcher.shared.jaccard` instead. Rename call sites from `_jaccard` → `jaccard_similarity`.
2. In `product_names.py`: Remove local `_strip_code_blocks`. Import from `launcher.shared.jaccard` (note: function is named `_strip_code_blocks` — it's private. If not importable, extract to a shared `launcher.shared.text_utils` or make it public in jaccard.py as `strip_code_blocks`).
3. In `artifacts.py`: Move `from collections import Counter` to module-level imports.
4. Verify no behavior change by running existing tests.

### Allowed paths
- `src/launcher/workers/evaluate/checks/repetition.py`
- `src/launcher/workers/evaluate/checks/product_names.py`
- `src/launcher/workers/evaluate/checks/artifacts.py`
- `src/launcher/shared/jaccard.py` (only if making helpers public)
- `tests/unit/workers/test_evaluate.py`

### Forbidden
- Any other file/path

## Acceptance checks

- **CLI:** `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_evaluate.py -v` — all 78 tests pass
- **Tests:** No new tests needed — this is pure refactoring; existing tests validate behavior
- **Config respected end-to-end:** N/A
- **No mock data in production paths:** N/A

## Deliverables

- Modified `repetition.py` — local helpers removed, shared imports added
- Modified `product_names.py` — local helper removed, shared import added
- Modified `artifacts.py` — Counter import moved to module level
- Optionally modified `jaccard.py` — if helpers need to be made public (rename `_strip_*` → `strip_*`)
- Verified all 78 evaluate tests still pass

## Hard rules

- Keep public signatures unchanged
- No network in offline tests
- No behavior change — pure refactoring
- No new deps
- If making jaccard helpers public, add `__all__` entries

## Review dimensions — what 5/5 means

| Dimension | 5/5 Criteria |
|-----------|-------------|
| Maintainability | Single source of truth for frontmatter/code-block stripping across all check files |
| Minimality | Only remove duplicates; don't refactor anything else |
| Correctness | All 78 tests pass unchanged — zero behavior delta |
| Integration | Imports resolve correctly; no circular dependencies |
| Performance | No perf change — same functions, different import path |

## Now (runbook)

```bash
# 1. Check if jaccard.py helpers are importable (underscore = private convention)
grep -n "^def _strip_" src/launcher/shared/jaccard.py

# 2. Decision: rename _strip_frontmatter → strip_frontmatter in jaccard.py
#    OR import with leading underscore (acceptable within same package)

# 3. Edit repetition.py — remove local defs, add imports
# 4. Edit product_names.py — remove local _strip_code_blocks, add import
# 5. Edit artifacts.py — move Counter import to top

# 6. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_evaluate.py -v

# 7. Run full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest --tb=short -q
```
