# TC-3820 Healing Plan: Slug Quality Gate Production Hardening

## Context

TC-3820 added a semantic quality gate (`validate_slug_quality`, `_extract_slug_core`, noise filtering) to catch garbled slugs. Self-review identified 7 concrete gaps that prevent the implementation from being production-safe. This plan converts each gap into an executable taskcard.

## Gap Table

| Gap ID | Description | Severity | Taskcard |
|--------|-------------|----------|----------|
| G-01 | No re-disambiguation after quality gate replaces slugs -- collision risk | Critical | SR-01 |
| G-02 | Circular title recovery: `_generate_title(bad_slug)` feeds bad text to `_extract_slug_core` | Critical | SR-02 |
| G-03 | Singular/plural not handled in redundancy check (`spreadsheet` vs `spreadsheets`) | Medium | SR-03 |
| G-04 | `_extract_slug_core` exported with leading underscore across module boundary | Low | SR-04 |
| G-05 | `from collections import Counter` imported inside function body, not at module level | Low | SR-04 |
| G-06 | No integration tests for `_quality_check_slugs` or `_slug_fallback` in plan.py | High | SR-05 |
| G-07 | `_slug_fallback("feature_blog", ...)` always returns same slug -- guaranteed collision for multiple bad feature_blog pages | High | SR-01 |

---

## SR-01: Re-disambiguate after quality gate + unique fallback slugs

**Status:** Done
**Gap linkage:** G-01, G-07
**Role:** Senior engineer. Drop-in, production-ready.

### Scope

**Fix:**
1. In `plan.py`, call `_disambiguate_slugs(pages)` again immediately after `_quality_check_slugs(pages, product)` to resolve any collisions introduced by slug replacement.
2. Modify `_slug_fallback` to accept an `index` parameter so that multiple pages with the same role produce distinct fallback slugs (e.g., `spreadsheets-features-python` vs `spreadsheets-features-python-2`). Alternatively, rely solely on the existing `_disambiguate_slugs` pass to append `-2`, `-3` suffixes.
3. Add a DEBUG log when re-disambiguation changes any slug.

**Allowed paths:**
- `src/launcher/workers/planner/plan.py`
- `tests/unit/workers/test_plan_slug_integration.py`
- `plans/healing/TC-3820_healing_plan.md`

**Forbidden:** any other file/path

### Acceptance checks

- **CLI:** `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x` passes with 0 failures.
- **Tests:** New test in `test_plan_slug_integration.py` constructs a page list with 2 different bad slugs that both map to the same `_slug_fallback` output, verifies that after `_quality_check_slugs` + `_disambiguate_slugs`, no two pages share the same `page_id`.
- **Config respected end-to-end:** No config changes needed.
- **No mock data in production paths:** No mock data introduced.

### Deliverables

1. Updated `src/launcher/workers/planner/plan.py` with re-disambiguation call and (optionally) `_slug_fallback` accepting index.
2. New test case in `test_plan_slug_integration.py` proving collision resolution.

### Hard rules

- Keep public signatures of `run_plan` unchanged.
- No network in offline tests.
- Deterministic runs: re-disambiguation must be stable (same input -> same output) under `PYTHONHASHSEED=0`.
- No new deps.
- Code/tests in sync.

### Review dimensions (5/5 targets)

| Dimension | 5/5 means |
|-----------|-----------|
| Correctness | Zero permalink collisions possible after step 3c+3d |
| Robustness | Even if quality gate replaces ALL slugs to identical fallbacks, disambiguation resolves them |
| Testability | Explicit test with 2+ colliding fallbacks proving uniqueness |
| Minimality | Exactly 1 new line in pipeline (`pages = _disambiguate_slugs(pages)`) + optional `_slug_fallback` tweak |

### Runbook

```bash
# 1. Edit plan.py: add _disambiguate_slugs call after _quality_check_slugs
# 2. Add integration test
# 3. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_plan_slug_integration.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x
```

---

## SR-02: Fix circular title recovery in `_quality_check_slugs`

**Status:** Done
**Gap linkage:** G-02
**Role:** Senior engineer. Drop-in, production-ready.

### Scope

**Fix:**
1. In `_quality_check_slugs`, replace `_generate_title(slug, page_role)` with a source that does not derive from the bad slug. Use `page.get("topic_category", "")` or the page's `page_role` as input to `_extract_slug_core`.
2. If neither `topic_category` nor `page_role` yields a usable core, go directly to `_slug_fallback` (skip the dead `_extract_slug_core` path).
3. Add a unit test that constructs a page with a bad slug lacking any high-intent verb, verifies that `_quality_check_slugs` falls through to `_slug_fallback` cleanly rather than producing garbage.

**Allowed paths:**
- `src/launcher/workers/planner/plan.py`
- `tests/unit/workers/test_plan_slug_integration.py`
- `plans/healing/TC-3820_healing_plan.md`

**Forbidden:** any other file/path

### Acceptance checks

- **CLI:** Full test suite passes.
- **Tests:** New test proves that a page with slug `microsoft-windows-windows-desktop-spreadsheets` and `page_role=feature_blog` gets a readable replacement (not one derived from the bad slug's title-case form).
- **No mock data in production paths.**

### Deliverables

1. Updated `_quality_check_slugs` in `plan.py` with non-circular title source.
2. New test case proving recovery path is not circular.

### Hard rules

- Keep `_quality_check_slugs` signature unchanged.
- No network in tests.
- Deterministic output.
- No new deps.

### Review dimensions (5/5 targets)

| Dimension | 5/5 means |
|-----------|-----------|
| Correctness | `_extract_slug_core` receives meaningful text, not title-cased garbage |
| Robustness | Every code path through `_quality_check_slugs` produces a valid slug |
| Testability | Test exercises the exact bad slug from production deploy |

### Runbook

```bash
# 1. Edit _quality_check_slugs: replace _generate_title(slug, page_role) with topic_category or role
# 2. Add test
# 3. Run
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_plan_slug_integration.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x
```

---

## SR-03: Plural-aware redundancy detection in `validate_slug_quality`

**Status:** Done
**Gap linkage:** G-03
**Role:** Senior engineer. Drop-in, production-ready.

### Scope

**Fix:**
1. In `validate_slug_quality`, normalize slug parts before counting by stripping a trailing `s` from words longer than 3 characters. This catches `spreadsheet` vs `spreadsheets` as redundant.
2. Update the existing `test_redundant_words` test to verify `spreadsheet-generation-spreadsheets` is caught (currently only `spreadsheets-generation-spreadsheets` is tested).
3. Add a negative test: `files-to-formats` should NOT flag (`file` vs `files` after stemming -- `file` is 4 chars, trailing `s` stripped, both become `file` -- but these are in the `("to", "for")` exemption... actually no). We need a test confirming that common patterns like `convert-files-to-formats` do not false-positive.

**Allowed paths:**
- `src/launcher/shared/slug_engine.py`
- `tests/unit/shared/test_slug_engine.py`
- `plans/healing/TC-3820_healing_plan.md`

**Forbidden:** any other file/path

### Acceptance checks

- **CLI:** Full test suite passes.
- **Tests:** `spreadsheet-generation-spreadsheets` now caught. `convert-files-to-formats` still passes. `how-to-load-spreadsheets-python` still passes.
- **No mock data in production paths.**

### Deliverables

1. Updated `validate_slug_quality` in `slug_engine.py` with plural-aware counting.
2. Updated + new tests in `test_slug_engine.py`.

### Hard rules

- Keep `validate_slug_quality` signature unchanged.
- The stemming must be trivial (rstrip `s` for words > 3 chars) -- no NLP dependency.
- No new deps.
- Deterministic.

### Review dimensions (5/5 targets)

| Dimension | 5/5 means |
|-----------|-----------|
| Correctness | All 5 known bad deploy slugs caught by quality + safety checks combined |
| Robustness | No false positives on the existing 99 test slugs |
| Testability | Both positive and negative cases with singular/plural variants |
| Minimality | ~3 lines changed in the Counter logic |

### Runbook

```bash
# 1. Edit validate_slug_quality: stem parts before Counter
# 2. Update/add tests
# 3. Run
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/test_slug_engine.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x
```

---

## SR-04: Code hygiene -- public API naming + import placement

**Status:** Done
**Gap linkage:** G-04, G-05
**Role:** Senior engineer. Drop-in, production-ready.

### Scope

**Fix:**
1. Rename `_extract_slug_core` to `extract_slug_core` (drop leading underscore) since it is exported and imported across module boundaries.
2. Update all import sites: `plan.py` and `test_slug_engine.py`.
3. Move `from collections import Counter` from inside `validate_slug_quality` body to the top-level imports in `slug_engine.py`.

**Allowed paths:**
- `src/launcher/shared/slug_engine.py`
- `src/launcher/workers/planner/plan.py`
- `tests/unit/shared/test_slug_engine.py`
- `plans/healing/TC-3820_healing_plan.md`

**Forbidden:** any other file/path

### Acceptance checks

- **CLI:** Full test suite passes.
- **Tests:** Existing 99 slug engine tests pass. No import errors.
- **No mock data in production paths.**

### Deliverables

1. Renamed function in `slug_engine.py` + moved import.
2. Updated imports in `plan.py` and `test_slug_engine.py`.

### Hard rules

- Update ALL call sites (grep for `_extract_slug_core`).
- No functional change -- pure rename + import move.
- No new deps.

### Review dimensions (5/5 targets)

| Dimension | 5/5 means |
|-----------|-----------|
| Consistency | No underscore-prefixed functions exported across modules |
| Maintainability | All imports at top of file per PEP 8 |
| Minimality | Rename + import move only, zero logic changes |

### Runbook

```bash
# 1. Rename function in slug_engine.py, move Counter import
# 2. Update imports in plan.py and test_slug_engine.py
# 3. Grep to verify no stale references remain
grep -r "_extract_slug_core" src/ tests/
# 4. Run
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x
```

---

## SR-05: Integration tests for `_quality_check_slugs` and `_slug_fallback`

**Status:** Done
**Gap linkage:** G-06
**Role:** Senior engineer. Drop-in, production-ready.

### Scope

**Fix:**
1. Add a new test class `TestQualityCheckSlugs` in `test_plan_slug_integration.py` (or a new file `test_plan_slug_quality.py`) covering:
   - A page with a garbled slug gets replaced by a readable slug.
   - A page with a good slug is left unchanged.
   - `_slug_fallback` returns distinct slugs per page_role (`feature_blog`, `howto_article`, `blog_announcement`, generic).
   - The hardened `_derive_optional_slug` skips bad claims and tries the next one.
2. Each test constructs minimal `ProductIdentity` and page dicts, calls the functions directly, and asserts on output slug values.

**Allowed paths:**
- `tests/unit/workers/test_plan_slug_integration.py` (or `tests/unit/workers/test_plan_slug_quality.py`)
- `plans/healing/TC-3820_healing_plan.md`

**Forbidden:** any other file/path

### Acceptance checks

- **CLI:** Full test suite passes.
- **Tests:** At least 6 new test cases covering: quality gate replacement, passthrough, fallback per role, optional slug retry, collision after replacement, noise word in optional slug.
- **No mock data in production paths:** Tests use minimal in-memory fixtures.
- **No network in tests.**

### Deliverables

1. New test file or class with >= 6 test cases.
2. All tests passing under `PYTHONHASHSEED=0`.

### Hard rules

- No network calls.
- Deterministic under `PYTHONHASHSEED=0`.
- No new deps beyond pytest.
- Tests must not import private functions via fragile paths -- if functions need to be tested, they should be importable (see SR-04 for the rename).

### Review dimensions (5/5 targets)

| Dimension | 5/5 means |
|-----------|-----------|
| Testability | Every code path through quality gate and fallback is exercised |
| Coverage | Both happy path (good slug untouched) and failure path (bad slug replaced) |
| Robustness | Edge cases: empty slug, `_index`, slug with only noise words |
| Correctness | Assertions check exact slug values, not just "contains" |

### Runbook

```bash
# 1. Create/update test file
# 2. Run focused
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_plan_slug_integration.py -v
# 3. Run full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x
```

---

## Execution Order

Recommended sequence (respects dependencies):

1. **SR-04** (rename + import hygiene) -- no functional change, unblocks clean imports for SR-05
2. **SR-03** (plural-aware redundancy) -- isolated to slug_engine, no plan.py dependency
3. **SR-02** (fix circular recovery) -- changes `_quality_check_slugs` logic
4. **SR-01** (re-disambiguation + unique fallback) -- depends on SR-02 being in place
5. **SR-05** (integration tests) -- should run last to test the final state of all fixes
