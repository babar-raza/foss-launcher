# Test Verification Plan
**Agent**: Agent C (Tests & Verification)
**Task**: TASK-HEAL-TESTS
**Date**: 2026-02-03
**Run ID**: run_20260203_220940

---

## Objective

Verify comprehensive test coverage for all healing fixes (HEAL-BUG1, HEAL-BUG3, HEAL-BUG4) and ensure no regressions were introduced.

---

## Healing Fixes Under Test

### HEAL-BUG1: URL Path Generation Fix
- **File**: `src/launch/workers/w4_ia_planner/worker.py`
- **Function**: `compute_url_path()`
- **Fix**: Removed section name from URL path per subdomain architecture
- **Tests**: `tests/unit/workers/test_tc_430_ia_planner.py` (Tests 12, 12a, 12b, 12c)

### HEAL-BUG3: Cross-Section Link Transformation
- **File**: `src/launch/workers/w5_section_writer/link_transformer.py`
- **Function**: `transform_cross_section_links()`
- **Fix**: Integrated TC-938 link transformation into W5 pipeline
- **Tests**: `tests/unit/workers/test_w5_link_transformer.py` (15 tests)

### HEAL-BUG4: Template Discovery Filtering
- **File**: `src/launch/workers/w4_ia_planner/worker.py`
- **Function**: `enumerate_templates()`
- **Fix**: Filter out obsolete `__LOCALE__` templates from blog section
- **Tests**: `tests/unit/workers/test_w4_template_discovery.py` (6 tests)

### TC-938 Regression Tests
- **File**: `tests/unit/workers/test_tc_938_absolute_links.py`
- **Tests**: 19 tests for absolute URL generation (HEAL-BUG3 foundation)

---

## Test Execution Plan

### Phase 1: Review Existing Test Coverage
- [x] Read test_w4_template_discovery.py (Bug #4)
- [x] Read test_tc_430_ia_planner.py (Bug #1)
- [x] Read test_w5_link_transformer.py (Bug #3)
- [x] Read test_tc_938_absolute_links.py (TC-938 foundation)

### Phase 2: Execute Test Suite
- [x] Run W4 template discovery tests (6 tests)
- [x] Run TC-430 IA planner tests (33 tests)
- [x] Run W5 link transformer tests (15 tests)
- [x] Run TC-938 absolute links tests (19 tests)
- [x] Run full worker test suite for regressions

### Phase 3: Coverage Analysis
- [x] Generate coverage report for healing-related modules
- [x] Analyze coverage metrics
- [x] Identify coverage gaps

### Phase 4: Regression Analysis
- [x] Identify failing tests
- [x] Categorize failures (expected vs unexpected)
- [x] Document test updates needed

### Phase 5: Test Quality Assessment
- [x] Evaluate test quality dimensions
- [x] Score tests on 12-dimension framework
- [x] Document gaps and recommendations

---

## Success Criteria

1. All healing-specific tests pass (54 tests: 6+33+15)
2. TC-938 regression tests pass (19 tests)
3. Coverage ≥90% for W4 template discovery
4. Coverage ≥95% for W4 URL generation
5. Coverage ≥90% for W5 link transformation
6. No unexpected regressions in worker test suite
7. Test quality scores ≥4/5 on all dimensions

---

## Deliverables

1. **plan.md** - This document
2. **evidence.md** - Test execution results
3. **test_quality_report.md** - Quality assessment
4. **changes.md** - New tests added (if any)
5. **self_review.md** - 12-dimension self-review
6. **commands.ps1** - All commands executed

---

## Risk Assessment

| Risk | Mitigation |
|------|-----------|
| Test failures reveal regressions | Categorize expected vs unexpected failures |
| Coverage gaps found | Document gaps, create additional tests if critical |
| Performance issues | Run with timeout, monitor test execution time |
| Platform compatibility | Tests run on Windows (current), document Linux compatibility |

---

## Timeline

- Test review: 15 minutes
- Test execution: 10 minutes
- Coverage analysis: 10 minutes
- Regression analysis: 15 minutes
- Report writing: 30 minutes
- Self-review: 10 minutes

**Total**: ~90 minutes
