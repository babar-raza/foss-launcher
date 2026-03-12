---
id: TC-3836
title: "content_freshness_signals"
status: Done
priority: Normal
owner: "agent"
updated: "2026-03-08"
tags: [generate, seo, freshness, frontmatter]
depends_on: [TC-3810]
allowed_paths:
  - src/launcher/workers/generate/seo_metadata.py
  - tests/unit/workers/test_seo_metadata.py
  - plans/taskcards/TC-3836_content_freshness_signals.md
evidence_required:
  - reports/TC-3836/evidence.md
---

# Taskcard TC-3836 — content_freshness_signals

## Objective

Inject ISO 8601 freshness date fields (date, lastmod, datePublished, dateModified) into frontmatter during SEO metadata optimization so that Hugo and search engines have accurate publication signals.

## Required spec references

- `specs/seo_metadata.md` (Section: frontmatter fields)

## Scope

### In scope
- New `_inject_freshness_dates()` helper in `seo_metadata.py`
- Call from `optimize_seo_metadata()` after quality enforcement
- 5 new tests in `TestFreshnessDates` class

### Out of scope
- Hugo template changes
- Publish worker changes
- Run config schema changes

## Inputs

- `src/launcher/workers/generate/seo_metadata.py` (existing SEO module)

## Outputs

- Modified `src/launcher/workers/generate/seo_metadata.py` with freshness injection
- 5 new tests in `tests/unit/workers/test_seo_metadata.py`

## Allowed paths

- src/launcher/workers/generate/seo_metadata.py
- tests/unit/workers/test_seo_metadata.py
- plans/taskcards/TC-3836_content_freshness_signals.md

### Allowed paths rationale
Source file contains `optimize_seo_metadata`. Test file already exists with related tests. Taskcard documents the work.

## Implementation steps

### Step 1: Add `datetime` import

Add `from datetime import datetime, timezone` to seo_metadata.py imports.

### Step 2: Add `_inject_freshness_dates()` helper

Place before `optimize_seo_metadata()`. Sets date (once), lastmod (always), datePublished = date, dateModified = lastmod. All in UTC ISO 8601 format.

### Step 3: Wire into `optimize_seo_metadata()`

Call `fm = _inject_freshness_dates(fm)` as step 8, after `_enforce_metadata_quality`.

### Step 4: Add tests

Add `TestFreshnessDates` class with 5 tests: injection, date preservation, lastmod always updated, ISO 8601 format validation, empty date replaced.

### Step 5: Verify

Run freshness tests then full suite.

## Failure modes

### Failure mode 1: datetime mock not intercepting `strftime`

**Detection**: `test_lastmod_always_updated` fails because mock doesn't match call chain
**Resolution**: Patch `launcher.workers.generate.seo_metadata.datetime` and mock `.now().strftime()` return value
**Gate**: test isolation

### Failure mode 2: `_enforce_metadata_quality` strips new date fields

**Detection**: date/lastmod absent from output frontmatter
**Resolution**: Inject freshness AFTER quality enforcement (step 8); quality enforcement only touches title/seoTitle/description
**Gate**: freshness injection order

### Failure mode 3: date overwritten on re-run (idempotency violation)

**Detection**: `test_date_preserved_on_rerun` fails
**Resolution**: Guard: `if "date" not in fm or not fm["date"]:` before setting date
**Gate**: date preservation logic

## Task-specific review checklist

1. [x] `date` is only set if absent or empty (never overwritten when present)
2. [x] `lastmod` is always set to current UTC time
3. [x] `datePublished` mirrors `date`, `dateModified` mirrors `lastmod`
4. [x] All values use `strftime("%Y-%m-%dT%H:%M:%SZ")` with UTC timezone
5. [x] Freshness injection occurs AFTER `_enforce_metadata_quality` (step 8)
6. [x] 5 new tests all pass; full suite 2381 passed

## Deliverables

1. `src/launcher/workers/generate/seo_metadata.py` — freshness injection added
2. 5 new tests in `tests/unit/workers/test_seo_metadata.py` under `TestFreshnessDates`

## Acceptance checks

1. [x] 5/5 `TestFreshnessDates` tests pass
2. [x] Full suite: 2381 passed, 0 failed
3. [x] `optimize_seo_metadata()` output contains date/lastmod/datePublished/dateModified

## Self-review

### Verification results
- [x] Tests: 5/5 PASS (freshness), 63/63 PASS (full seo_metadata file), 2392/2392 PASS (full suite, run 2026-03-08)
- [x] date_preserved_on_rerun PASS: existing `date` not overwritten on re-run
- [x] lastmod_always_updated PASS: `lastmod` always set to current UTC
- [x] Evidence file: `reports/TC-3836/evidence.md`

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_seo_metadata.py -v -k "Freshness"
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

**Actual results** (run 2026-03-08):
```
TestFreshnessDates::test_freshness_dates_injected PASSED
TestFreshnessDates::test_date_preserved_on_rerun PASSED
TestFreshnessDates::test_lastmod_always_updated PASSED
TestFreshnessDates::test_iso8601_format PASSED
TestFreshnessDates::test_empty_date_replaced PASSED
5 passed, 58 deselected in 0.31s

2392 passed in 53.28s
```

## Integration boundary proven

**Upstream**: `optimize_seo_metadata()` receives PageIR from generate worker
**Downstream**: Hugo rendering consumes frontmatter with date/lastmod for sitemap and schema.org
**Contract**: Returns new PageIR via `model_copy`; input not mutated
