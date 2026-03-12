# TC-3800 Healing Plan — _refine_page_slugs safety check hardening

## Context

TC-3800 added `validate_slug_safety()` to `_refine_page_slugs()`, closing the
last unguarded slug entry point. The production code change (6 lines) is correct
and tested for the primary case (`reg` artifact rejection + safe slug acceptance).

However, self-review identified 7 gaps spanning governance, test coverage,
maintainability, and robustness. This healing plan addresses all of them in
two focused taskcards.

## Gap Table

| Gap ID | Description | Taskcard |
|--------|-------------|----------|
| G1 | TC-3800 acceptance checks unchecked despite status=Done | SR-13 |
| G2 | Missing `reports/TC-3800/evidence.md` per `evidence_required` | SR-13 |
| G3 | Inline `_BadLLM`/`_GoodLLM` diverge from `_MockLLMClient` pattern | SR-14 |
| G4 | No test coverage for `trade`/`copy` entity artifact variants | SR-14 |
| G5 | No E2E test through `run_plan()` for LLM safety rejection | SR-14 |
| G6 | No test verifying URL field preservation on rejection | SR-14 |
| G7 | No test for edge case where ALL refined slugs are unsafe | SR-14 |

---

## Taskcard SR-13 — TC-3800 Governance Completion

**Status:** Done
**Gap linkage:** G1, G2
**Role:** Senior engineer. Drop-in, production-ready.

### Scope

**Fix:**
- Mark all 4 acceptance checks in TC-3800 taskcard as `[x]` with evidence references
- Create `reports/TC-3800/evidence.md` documenting test results, the code diff, and verification commands

**Allowed paths:**
- `plans/taskcards/TC-3800_refine_slugs_safety_check.md`
- `reports/TC-3800/evidence.md`

**Forbidden:** any other file/path

### Acceptance checks

- **CLI:** `cat plans/taskcards/TC-3800_refine_slugs_safety_check.md | grep '\[x\]'` returns 4 lines under Acceptance checks
- **Tests:** N/A (governance-only change)
- **Config respected end-to-end:** `evidence_required` field in TC-3800 frontmatter matches the created file path
- **No mock data in production paths:** Evidence file contains real test output, not fabricated data

### Deliverables

1. Updated `plans/taskcards/TC-3800_refine_slugs_safety_check.md` with all acceptance checks marked `[x]` and annotated with test names
2. New `reports/TC-3800/evidence.md` containing:
   - The 6-line production diff
   - `pytest` output for the 3 new tests (copy-paste from terminal)
   - Full suite summary line (`N passed, M failed`)
   - Statement linking each acceptance check to its evidence

### Hard rules

- Keep public signatures unless justified; update all call sites: N/A
- No network in offline tests: N/A
- Deterministic runs: N/A
- No new deps: N/A
- Keep code/docs/tests in sync: taskcard acceptance checks must match actual test results

### Review dimensions — what 5/5 means

| Dimension | 5/5 definition |
|-----------|----------------|
| Thoroughness | All 4 acceptance checks marked, evidence file covers every check |
| Consistency | Frontmatter `evidence_required` matches actual file path |
| Production grading | Evidence is from actual test runs, not fabricated |
| Correctness | Check annotations reference actual test function names |
| Minimality | Only the two files are touched |

### Now (runbook)

```bash
# 1. Run the tests to capture fresh evidence
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_plan_slug_integration.py::TestRefinePageSlugsSafety -v 2>&1 | tee /tmp/tc3800_tests.txt

# 2. Run full suite for summary line
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ --tb=short -q 2>&1 | tail -5 | tee /tmp/tc3800_suite.txt

# 3. Create reports directory
mkdir -p reports/TC-3800

# 4. Write evidence.md with captured output
# (compose from /tmp/tc3800_tests.txt and /tmp/tc3800_suite.txt)

# 5. Update TC-3800 acceptance checks to [x] with test references

# 6. Verify
grep '\[x\]' plans/taskcards/TC-3800_refine_slugs_safety_check.md | wc -l
# Expected: at least 4 lines under Acceptance checks
test -f reports/TC-3800/evidence.md && echo "Evidence exists" || echo "MISSING"
```

---

## Taskcard SR-14 — TC-3800 Test Coverage Hardening

**Status:** Done
**Gap linkage:** G3, G4, G5, G6, G7
**Role:** Senior engineer. Drop-in, production-ready.

### Scope

**Fix:**
1. Refactor `TestRefinePageSlugsSafety` to reuse existing `_MockLLMClient` instead of inline classes (G3)
2. Add parameterized test covering `trade` and `copy` artifact variants alongside `reg` (G4)
3. Add E2E test through `run_plan()` with mock LLM returning entity-artifact slugs (G5)
4. Add test verifying URL field is unchanged when slug is rejected (G6)
5. Add test for edge case where ALL LLM-refined slugs are unsafe — all originals preserved (G7)

**Allowed paths:**
- `tests/unit/workers/test_plan_slug_integration.py`

**Forbidden:** any other file/path (no production code changes — the fix is already correct)

### Acceptance checks

- **CLI:** `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_plan_slug_integration.py::TestRefinePageSlugsSafety -v` — all tests pass
- **Tests:**
  - `test_entity_artifact_slug_rejected` — uses `_MockLLMClient` (not inline class)
  - `test_windowsreg_artifact_slug_rejected` — uses `_MockLLMClient`
  - `test_safe_refined_slug_accepted` — uses `_MockLLMClient`
  - `test_entity_variants_rejected[trade]` — parameterized, `exceltrade` rejected
  - `test_entity_variants_rejected[copy]` — parameterized, `microsoftcopy` rejected
  - `test_e2e_entity_artifact_rejected_through_run_plan` — full pipeline test
  - `test_url_preserved_on_rejection` — URL field unchanged when slug rejected
  - `test_all_slugs_unsafe_all_preserved` — every slug rejected, all originals kept
- **Config respected end-to-end:** Tests use `PYTHONHASHSEED=0`
- **No mock data in production paths:** All mocks are test-only; `_MockLLMClient` is defined in test module

### Deliverables

1. Updated `TestRefinePageSlugsSafety` class in `tests/unit/workers/test_plan_slug_integration.py`:
   - Inline `_BadLLM`/`_GoodLLM` classes replaced with `_MockLLMClient` from line 494
   - 5 new test methods added (parameterized variants, E2E, URL preservation, all-unsafe)
   - Existing 3 tests preserved (behavior unchanged, only mock class swapped)
2. Full test suite passes with zero regressions

### Hard rules

- Keep public signatures unless justified; update all call sites: No signature changes
- No network in offline tests: All tests use `_MockLLMClient`, no network
- Deterministic runs: `PYTHONHASHSEED=0` required for all runs
- No new deps: No new imports beyond `pytest.mark.parametrize` (already available)
- Keep code/docs/tests in sync: New tests match the production code path exactly

### Review dimensions — what 5/5 means

| Dimension | 5/5 definition |
|-----------|----------------|
| Thoroughness | All 3 entity variant types (`reg`, `trade`, `copy`) tested; E2E path tested; edge cases covered |
| Consistency | All mock LLM usage goes through `_MockLLMClient`; no inline classes |
| Testability | 8 total tests covering happy path, 3 artifact types, E2E, URL preservation, all-unsafe edge |
| Robustness | Edge case (all slugs unsafe) proves no crash, no partial state |
| Minimality | Only the test file changes; no production code touched |
| Maintainability | Single mock class pattern; parameterized tests reduce duplication |
| Correctness | Each test asserts specific slug values, not just "no crash" |
| Integration fit | E2E test uses `run_plan()` which exercises the full planner pipeline |

### Now (runbook)

```bash
# 1. Edit test file: replace inline classes with _MockLLMClient
# 2. Add parameterized test for trade/copy variants
# 3. Add E2E test through run_plan()
# 4. Add URL preservation test
# 5. Add all-slugs-unsafe test

# 6. Run TC-3800 tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_plan_slug_integration.py::TestRefinePageSlugsSafety -v

# 7. Run full planner integration suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_plan_slug_integration.py -v

# 8. Run full test suite for regression check
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ --tb=short -q

# 9. Verify no inline LLM classes remain in TestRefinePageSlugsSafety
grep -c "class _Bad\|class _Good" tests/unit/workers/test_plan_slug_integration.py
# Expected: 0

# 10. Verify parameterized variants exist
grep "entity_variants_rejected" tests/unit/workers/test_plan_slug_integration.py
# Expected: test function + parametrize decorator
```
