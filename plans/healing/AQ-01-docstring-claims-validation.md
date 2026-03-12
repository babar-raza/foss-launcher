# AQ-01 — Route Docstring Claims Through Validation Pipeline

**Status**: Done
**Gap linkage**: GAP-01 (Critical — sandwich model violation)
**Role**: Senior engineer. Drop-in, production-ready.

## Context

`_harvest_docstring_claims()` creates `Claim` objects and appends them directly to the claims list AFTER `_validate_and_normalize_claims()`, `filter_claims()`, and `_filter_contaminated_claims()` have already run. This means docstring claims:
- Skip visibility filtering (off-topic detection)
- Skip deduplication against LLM-extracted claims
- Skip claim text normalization
- Skip contamination filtering

This is a **sandwich model violation** — engineering validation must wrap all claim sources.

## Scope

### Fix

Move docstring claim harvesting to BEFORE the validation pipeline. Transform `_harvest_docstring_claims()` to return raw dicts matching the format expected by `_validate_and_normalize_claims()`, then inject them into `raw_claims` before validation.

### Allowed paths
- `src/launcher/workers/understand/extract.py`
- `tests/unit/workers/understand/test_extract.py`
- `tests/unit/workers/test_understand.py`

### Forbidden
- Any other file/path

## Acceptance checks

- **CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/ tests/unit/workers/test_understand.py -q --tb=short` — all pass
- **Tests**: New test proving docstring claims go through visibility filtering (a docstring containing off-topic content is filtered out)
- **Tests**: New test proving docstring claims are deduplicated against LLM claims with identical text
- **Config respected end-to-end**: `max_claims=50` cap still enforced after validation
- **No mock data in production paths**: Claims use real `_validate_and_normalize_claims` pipeline, not a bypass

## Deliverables

1. Modified `_harvest_docstring_claims()` → renamed to `_harvest_docstring_claims_raw()`, returns `list[dict]` instead of `list[Claim]`
2. Modified `run_extract()`: calls `_harvest_docstring_claims_raw()` BEFORE `_validate_and_normalize_claims()`, extends `raw_claims`
3. Updated tests in `test_extract.py` for the new return type
4. New test: docstring claim with off-topic content → filtered by `_validate_and_normalize_claims`
5. New test: duplicate docstring claim text → deduplicated

## Hard rules

- Keep public signatures unless justified; update all call sites
- No network in offline tests
- Deterministic runs (seed/stable ordering) where needed
- No new deps without explicit justification
- Keep code/docs/tests in sync

## Review dimensions — what 5/5 means

| Dimension | 5/5 target |
|-----------|-----------|
| Thoroughness | All claim sources pass through identical validation pipeline |
| Consistency | `_harvest_docstring_claims_raw` returns same dict format as LLM extraction |
| Production grading | No claim can enter the pipeline without visibility/dedup/contamination checks |
| Correctness & spec alignment | Matches sandwich model: Engineering > LLM > Engineering |
| Robustness | Empty class_briefs → no crash, no claims; huge docstrings → truncated |
| Testability | Both happy path and filtering/dedup paths tested |
| Minimality | Only changes claim injection point + return type; no other refactoring |

## Now (runbook)

```bash
# 1. Rename function and change return type
#    _harvest_docstring_claims → _harvest_docstring_claims_raw
#    Return list[dict] with keys: text, kind, evidence (matching LLM format)

# 2. In run_extract(), move the call:
#    FROM: after _filter_contaminated_claims (line ~186)
#    TO:   after raw_claims = await _extract_claims_llm() (line ~167)
#    Change: raw_claims.extend(_harvest_docstring_claims_raw(api_surface, product))

# 3. Remove the old injection point (lines 186-190)

# 4. Update test_extract.py:
#    - Change TestDocstringClaims to test raw dict output
#    - Add test_docstring_claims_filtered_by_validation
#    - Add test_docstring_claims_deduplicated

# 5. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/ tests/unit/workers/test_understand.py -q --tb=short

# 6. Run full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=short
```
