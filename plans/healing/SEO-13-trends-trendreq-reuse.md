# SEO-13: Reuse TrendReq Instance Across Queries

## Status: Done

## Gap Linkage
- **G-SR5**: `TrendReq` is instantiated inside the per-query loop in
  `_fetch_trends_keywords()`. Each instantiation creates a new `requests.Session`,
  performs cookie setup, and negotiates tokens. For 3 queries this means 3
  sessions instead of 1. Performance waste + unnecessary network round-trips.

## Role
Senior engineer. Drop-in, production-ready.

## Scope

### Fix
In `_fetch_trends_keywords()` in `keyword_research.py`:

1. Move `pytrends = TrendReq(hl="en-US", tz=360)` BEFORE the `for query` loop
2. Reuse the same `pytrends` instance for all 3 queries
3. If a query fails, continue with same instance (session is still valid)

### Allowed paths
- `src/launcher/shared/keyword_research.py`
- `plans/healing/SEO-13-trends-trendreq-reuse.md`

### Forbidden
Any other file.

## Acceptance Checks

### CLI
- `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q` — all pass

### Code quality
- `TrendReq` instantiated exactly once per `_fetch_trends_keywords()` call

## Deliverables
- 1 file modified: `keyword_research.py` (2-line move)

## Hard Rules
- Zero behavior change beyond performance
- No new deps

## Review Dimensions

| Dimension | 5/5 Definition |
|-----------|----------------|
| Correctness | Same results, fewer sessions |
| Minimality | Just the move |

## Runbook

```bash
# 1. Move TrendReq instantiation before loop
# 2. Full regression
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
# 3. Mark Done
```

```yaml
# machine-readable
taskcard_id: SEO-13
title: Reuse TrendReq Instance Across Queries
status: Not Started
priority: P3
gaps: [G-SR5]
allowed_paths:
  - src/launcher/shared/keyword_research.py
depends_on: []
```
