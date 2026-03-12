---
id: TC-3827
title: "SEO FM Contract — template_loader two-tuple + worker sentinel fill"
status: Done
priority: High
owner: "agent"
updated: "2026-03-08"
tags: [seo, frontmatter, template, pipeline]
depends_on: [TC-3824]
allowed_paths:
  - plans/taskcards/TC-3827_seo_fm_contract.md
  - src/launcher/content/template_loader.py
  - src/launcher/workers/generate/worker.py
  - tests/unit/content/test_template_loader.py
  - tests/unit/workers/test_generate.py
evidence_required:
  - reports/TC-3827/evidence.md
---

# Taskcard TC-3827 — SEO FM Contract

## Objective

Two compounding failures cause missing SEO frontmatter: (1) `extract_template_frontmatter()`
silently drops placeholder keys so the generate worker has no knowledge of required fields, and
(2) the worker has no mechanism to insert sentinels for unfilled keys, so they are simply absent
when the evaluate gate checks them. This TC introduces a two-tuple return value and a sentinel
fill pass to make the FM contract explicit and observable.

## Required spec references

- `specs/seo.md` (SEO frontmatter requirements)

## Scope

### In scope
- `extract_template_frontmatter()` returns `(dict, frozenset)` instead of plain `dict`
- Generate worker inserts `""` sentinels for required placeholder keys missing from merged FM
- Update all callers to destructure the two-tuple

### Out of scope
- SEO exception handling — already implemented in TC-3824
- Canonical deterministic fallback — already implemented in TC-3824
- `robots` deterministic fill at plan time — already implemented in TC-3824

## Inputs

- Hugo template files with `__PLACEHOLDER__` values
- Page-plan frontmatter (from planner, includes `robots` per TC-3824)

## Outputs

- Explicit `frozenset[str]` of required-key names; sentinel `""` in merged FM for missing ones
- Evaluate `seo` gate catches empty sentinels — pages with missing SEO FM are detectable

## Allowed paths

- plans/taskcards/TC-3827_seo_fm_contract.md
- src/launcher/content/template_loader.py
- src/launcher/workers/generate/worker.py
- tests/unit/content/test_template_loader.py
- tests/unit/workers/test_generate.py

### Allowed paths rationale

Only `template_loader.py`, the generate worker, and their test files need changes.

## Implementation steps

### Step 1: Change `extract_template_frontmatter` return type

Return `tuple[dict[str, Any], frozenset[str]]`:
- First element: concrete values (same as before)
- Second element: frozenset of keys that had placeholder values — caller MUST populate these

Collect placeholder keys in a `set[str]` and convert to `frozenset` at return.

### Step 2: Update generate worker

At line 424: change default to `required_placeholder_keys: frozenset[str] = frozenset()`.
At line 431: destructure `template_fm, required_placeholder_keys = extract_template_frontmatter(...)`.
After `merged_fm` construction (~line 451): insert `""` sentinels:
```python
for key in required_placeholder_keys:
    if key not in merged_fm:
        merged_fm[key] = ""
```

### Step 3: Update tests

`tests/unit/content/test_template_loader.py`:
- Existing test `test_extract_template_frontmatter_strips_all_placeholders`: update to unpack
  two-tuple `fm, required_keys = extract_template_frontmatter(content)`
- Add new tests: placeholder → in `required_keys`, real value → in `fm`, no overlap

`tests/unit/workers/test_generate.py`:
- Existing test `test_extract_template_frontmatter_strips_placeholders`: update to unpack

## Failure modes

### Failure mode 1: Callers that unpack into a plain dict receive a tuple instead

**Detection**: `TypeError: too many values to unpack` or `AttributeError` at runtime
**Resolution**: All callers updated in this TC (worker.py + both test files)
**Gate**: Full regression suite

### Failure mode 2: Sentinel `""` passes FM None-check in ir_renderer but evaluate SEO gate misses it

**Detection**: `seoTitle: ""` in YAML is an empty string, not `null` — Hugo treats as empty
**Resolution**: The evaluate `seo.py` check already tests for empty/missing strings; `""` is
correctly caught. No ir_renderer FrontmatterError (None is rejected, empty string is not).
**Gate**: evaluate seo check

### Failure mode 3: `required_placeholder_keys` is non-empty when no template is found

**Detection**: `required_placeholder_keys = frozenset()` when `template_content` is None
**Resolution**: Default initialisation `frozenset()` is kept; the sentinel fill loop is a no-op
**Gate**: Unit tests (no-template path)

## Task-specific review checklist

1. [x] `extract_template_frontmatter` returns `(dict, frozenset)` not `dict`
2. [x] Placeholder key appears in `frozenset`, not in `dict` (no overlap)
3. [x] Real-value key appears in `dict`, not in `frozenset`
4. [x] Worker inserts `""` sentinel for missing required keys after `merged_fm`
5. [x] All existing tests updated to unpack two-tuple
6. [x] Full regression passes (worker integration tests still pass)

## Deliverables

1. `src/launcher/content/template_loader.py` — two-tuple return type
2. `src/launcher/workers/generate/worker.py` — sentinel fill pass
3. Updated test files

## Acceptance checks

1. [x] `pytest tests/unit/content/test_template_loader.py -v` — 0 failures
2. [x] `pytest tests/unit/workers/test_generate.py -v` — 0 failures
3. [x] `extract_template_frontmatter("---\ndesc: __DESC__\n---")` returns `({}, frozenset({"desc"}))`
4. [x] Full regression: `pytest tests/ -x -q` — 0 failures

## Self-review

### Verification results
- [x] Tests: 466/466 PASS (targeted), 2392/2392 PASS (full suite, run 2026-03-08)
- [x] Two-tuple verified: `extract_template_frontmatter("---\ndesc: __DESC__\n---")` → `({}, frozenset({'desc'}))`
- [x] Sentinel fill verified: generate worker inserts `""` for missing required keys
- [x] Evidence file: `reports/TC-3827/evidence.md`

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/content/test_template_loader.py tests/unit/workers/test_generate.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

**Actual results** (run 2026-03-08):
```
466 passed in 1.24s (targeted suite)
2392 passed in 53.28s (full suite)
```

Two-tuple verification:
```
extract_template_frontmatter("---\ndesc: __DESC__\n---") → ({}, frozenset({'desc'}))
```

## Integration boundary proven

**Upstream**: Hugo template files with placeholder FM fields
**Downstream**: Generate worker merges template FM with page-plan FM; SEO phase fills seoTitle/keywords
**Contract**: Every key declared in template FM is either present with a real value, or the
caller knows it is required (via `frozenset`) and inserts a `""` sentinel
