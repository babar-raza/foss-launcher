# SEO-11: Hoist _FAMILY_TREND_TERMS to Module Level

## Status: Done

## Gap Linkage
- **G-SR3**: `_FAMILY_TREND_TERMS` dict is defined inside the function body of
  `_fetch_trends_keywords()`. This means a new dict is allocated on every call,
  is invisible to importers/tests, and violates the module-level constant
  convention used everywhere else in the codebase (e.g. `_STOP_WORDS`,
  `_USE_CASE_VERBS`, `_PAGE_KEYWORD_MAP`).

## Role
Senior engineer. Drop-in, production-ready.

## Scope

### Fix
Move `_FAMILY_TREND_TERMS` from inside `_fetch_trends_keywords()` to
module-level constant in `keyword_research.py`, alongside the other
module-level dicts.

1. Cut the dict definition from inside `_fetch_trends_keywords()` (~L259-267)
2. Paste at module level, between `_PAGE_KEYWORD_MAP` and the function
3. No logic change — just a relocation

### Allowed paths
- `src/launcher/shared/keyword_research.py`
- `plans/healing/SEO-11-trends-constant-hoist.md`

### Forbidden
Any other file.

## Acceptance Checks

### CLI
- `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q` — all pass

### Tests
- No existing tests broken
- `_FAMILY_TREND_TERMS` accessible at module level (importable in tests)

### Code quality
- Constant follows same pattern as `_STOP_WORDS`, `_USE_CASE_VERBS`, etc.

## Deliverables
- 1 file modified: `keyword_research.py` (move, not rewrite)

## Hard Rules
- Zero logic change
- Zero new code
- Just a relocation

## Review Dimensions

| Dimension | 5/5 Definition |
|-----------|----------------|
| Correctness | Exact same dict, exact same behavior |
| Convention | Matches all other module-level constants |
| Minimality | Only the move, nothing else |

## Runbook

```bash
# 1. Move _FAMILY_TREND_TERMS to module level
# 2. Full regression
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
# 3. Mark Done
```

```yaml
# machine-readable
taskcard_id: SEO-11
title: Hoist _FAMILY_TREND_TERMS to Module Level
status: Not Started
priority: P2
gaps: [G-SR3]
allowed_paths:
  - src/launcher/shared/keyword_research.py
depends_on: []
```
