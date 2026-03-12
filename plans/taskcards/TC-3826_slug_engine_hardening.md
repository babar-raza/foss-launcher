---
id: TC-3826
title: "Slug Engine Edge Case Hardening"
status: Done
priority: High
owner: "agent"
updated: "2026-03-08"
tags: [slug, quality, pipeline]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3826_slug_engine_hardening.md
  - src/launcher/shared/slug_engine.py
  - tests/unit/shared/test_slug_engine.py
evidence_required:
  - reports/TC-3826/evidence.md
---

# Taskcard TC-3826 — Slug Engine Edge Case Hardening

## Objective

Close two remaining gaps in `slug_engine.py` left after TC-3800: (1) HTML entities from LLM output
survive into slugs because `strip_html_entities()` is never called in `refine_slugs_batch()`, and
(2) `_VALID_REFINED_SLUG_RE` accepts double-hyphen slugs like `convert--pdf` because it only
enforces start/end character class, not interior structure.

## Required spec references

- `specs/slug_engine.md` (slug normalisation and safety rules)

## Scope

### In scope
- `refine_slugs_batch()`: add entity stripping + `validate_slug_safety()` post-normalisation
- `_VALID_REFINED_SLUG_RE`: tighten pattern to reject consecutive hyphens
- Warning log for every LLM slug that falls back to the original

### Out of scope
- `_refine_page_slugs()` in plan.py — covered by TC-3800 (Done)
- SEO or frontmatter — covered by TC-3827

## Inputs

- `src/launcher/shared/slug_engine.py` (current implementation)
- LLM refinement output (raw strings from `refine_slugs_batch`)

## Outputs

- Hardened `slug_engine.py` — entity artifacts and double-hyphen slugs rejected at source

## Allowed paths

- plans/taskcards/TC-3826_slug_engine_hardening.md
- src/launcher/shared/slug_engine.py
- tests/unit/shared/test_slug_engine.py

### Allowed paths rationale

Only the slug engine and its test file need changes.

## Implementation steps

### Step 1: Tighten `_VALID_REFINED_SLUG_RE`

Change pattern from `^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$` to:

```
^[a-z0-9]([a-z0-9]|-(?!-))*[a-z0-9]$|^[a-z0-9]$
```

The negative lookahead `(?!-)` after each `-` prevents `--` sequences.

### Step 2: Update `refine_slugs_batch()` normalisation pipeline

Inside the LLM branch, after `raw.strip().lower()`, insert:

```
new_slug = strip_html_entities(new_slug)   # decode &reg; → "", &#xNN; → "", etc.
```

Then after `validate_slug_safety()`, if issues are found, fall back to `original` and log a
warning.

### Step 3: Add tests

Add to `tests/unit/shared/test_slug_engine.py`:
- `excelreg` entity artifact in LLM output → fallback to original
- `excel&reg;` decoded before normalisation → slug is `excel` (entity stripped)
- LLM output `convert--pdf` rejected by `_VALID_REFINED_SLUG_RE` → fallback to original
- `convert-pdf` accepted (regression)
- Single char `"a"` valid per new regex
- `"ab"` valid per new regex

## Failure modes

### Failure mode 1: `strip_html_entities` not idempotent

**Detection**: `strip_html_entities(strip_html_entities(s)) != strip_html_entities(s)` would
loop; inspect function signature
**Resolution**: The function only removes entities — applying it twice is safe (no entities left)
**Gate**: slug_safety evaluate check

### Failure mode 2: Valid single-char or two-char slug rejected by new regex

**Detection**: test `^[a-z0-9]$` branch; `"a"`, `"ab"` must pass
**Resolution**: New regex has `|^[a-z0-9]$` branch for single-char; two-char matches
main branch as `start + one (char|hyphen-no-lookahead) + end`
**Gate**: Unit tests

### Failure mode 3: validate_slug_safety adds more overhead per slug in batch

**Detection**: Benchmark `refine_slugs_batch` with 100 slugs
**Resolution**: `validate_slug_safety` is pure regex — negligible overhead; acceptable
**Gate**: Performance (no gate, informational only)

## Task-specific review checklist

1. [x] `_VALID_REFINED_SLUG_RE` rejects `"convert--pdf"` and `"a--b"`
2. [x] `_VALID_REFINED_SLUG_RE` accepts `"a"`, `"ab"`, `"convert-pdf"`, `"excel-files"`
3. [x] `refine_slugs_batch` calls `strip_html_entities` before normalisation
4. [x] `refine_slugs_batch` calls `validate_slug_safety` and falls back with warning on failure
5. [x] All existing slug_engine tests still pass (regression)
6. [x] New tests cover entity artifact, double-hyphen, and single/two-char valid slugs

## Deliverables

1. `src/launcher/shared/slug_engine.py` — hardened normalisation pipeline
2. `tests/unit/shared/test_slug_engine.py` — new test cases

## Acceptance checks

1. [x] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/test_slug_engine.py -v` — 114/114 PASS
2. [x] `_VALID_REFINED_SLUG_RE.match("convert--pdf")` returns `None`
3. [x] `_VALID_REFINED_SLUG_RE.match("convert-pdf")` returns a match
4. [x] `refine_slugs_batch(["excelreg"], llm_client=mock)` returns `["excelreg"]` (fallback)
5. [x] Full regression: `pytest tests/ -x -q` — 2359 passed, 0 failures

## Self-review

### Verification results
- [x] Tests: 114/114 PASS (slug engine suite), 2392/2392 PASS (full suite, run 2026-03-08)
- [x] VALID_REFINED_SLUG_RE: `"convert--pdf"` → None (rejected); `"convert-pdf"` → match (accepted)
- [x] Entity artifact rejection: `"excelreg"` (entity artifact) → falls back to original
- [x] Evidence file: `reports/TC-3826/evidence.md`

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/test_slug_engine.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

**Actual results** (run 2026-03-08):
```
TestRefineSlugsBatchHardening::test_double_hyphen_llm_falls_back_to_original PASSED
TestRefineSlugsBatchHardening::test_entity_artifact_falls_back_to_original PASSED
TestRefineSlugsBatchHardening::test_entity_stripped_before_normalisation PASSED
TestRefineSlugsBatchHardening::test_valid_llm_slug_accepted PASSED
TestRefineSlugsBatchHardening::test_mismatched_count_falls_back PASSED
114 passed in 0.41s

2392 passed in 53.28s
```

## Integration boundary proven

**Upstream**: LLM batch refinement output (raw strings from `refine_slugs_batch`)
**Downstream**: `_refine_page_slugs()` in plan.py which receives the refined list
**Contract**: Every returned slug passes `validate_slug_safety()` with no issues
