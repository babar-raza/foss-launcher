# P7A-01 — Missing Test Coverage for Phase 7a Fixes

## Status: Done

## Gap Linkage: G-01

Three new behaviors were implemented with zero dedicated tests. Existing tests were
only updated where they broke. This leaves the new code paths unprotected against
regression.

## Role

Senior engineer. Drop-in, production-ready test suite covering all Phase 7a behaviors.

## Scope

### Fix

Write dedicated unit tests for:

1. **Claim citation stripping in code blocks (section_validator)**
   - Code block with `[CLM-12345]` in content → stripped after `_validate_block`
   - Code block with `# Claims: CLM-12345` comment → stripped (existing behavior, confirm)
   - Code block with both citation and comment → both stripped
   - Code block with NO citations → content unchanged
   - Code block with citation mid-line → line content preserved, citation removed

2. **Page role validation in frontmatter.py**
   - Frontmatter with valid `page_role: "workflow_page"` → no role-related findings
   - Frontmatter with unknown `page_role: "invented_role"` → high-severity finding
   - Frontmatter with missing `page_role` → high-severity finding
   - Frontmatter with each of the 17 known roles → no role-related findings
   - Verify `_VALID_ROLES` equals `PAGE_ROLE_SKELETONS.keys()`

3. **Page role validation in planner self_review**
   - PlanBundle with valid roles → self_review passes
   - PlanBundle with one invalid role → self_review finding with category "invalid_role"
   - PlanBundle with invalid role → `passed=False` (severity is high)

4. **Canonical import config validation**
   - Config with `canonical_import: "aspose.cells"`, platform=python → raises ConfigError
   - Config with `canonical_import: "aspose_cells_foss"`, platform=python → passes
   - Config with `canonical_import: "com.aspose.cells"`, platform=java → passes (no validation for non-python)
   - Config with no canonical_import → passes (field is optional)
   - Config with no platform → passes (skips validation)

### Allowed paths

- `tests/unit/test_section_validator_claim_strip.py` (new)
- `tests/unit/workers/test_frontmatter_role_validation.py` (new)
- `tests/unit/test_planner_role_validation.py` (new)
- `tests/unit/test_run_config_validation.py` (new)

### Forbidden

Any path not listed above.

## Acceptance Checks

- CLI: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/test_section_validator_claim_strip.py tests/unit/workers/test_frontmatter_role_validation.py tests/unit/test_planner_role_validation.py tests/unit/test_run_config_validation.py -v` — all pass
- Tests: ≥15 test cases across the 4 files
- Tests: each file covers ≥1 happy path + ≥1 failure/edge case
- Config respected end-to-end: tests use real `PAGE_ROLE_SKELETONS.keys()`, not hardcoded sets
- No mock data in production paths: tests create test data inline, no fixtures polluting src/

## Deliverables

- `tests/unit/test_section_validator_claim_strip.py` — 5+ test cases
- `tests/unit/workers/test_frontmatter_role_validation.py` — 5+ test cases
- `tests/unit/test_planner_role_validation.py` — 3+ test cases
- `tests/unit/test_run_config_validation.py` — 5+ test cases

## Hard Rules

- No network in tests
- Deterministic: PYTHONHASHSEED=0 required
- Tests must import from `launcher.*` (production code), not copy implementations
- No new dependencies
- Use `pytest` conventions (class-based or function-based, consistent with existing test files)

## Review Dimensions — What 5/5 Means

| Dimension | 5/5 Criteria |
|-----------|-------------|
| Thoroughness | Every new code path has ≥1 positive and ≥1 negative test |
| Consistency | Test style matches existing `tests/unit/` conventions |
| Production grading | Tests would catch any regression to the 3 fixed behaviors |
| Systematic approach | Tests organized by behavior, not by implementation detail |
| Correctness | Assertions match the actual contract (e.g., `_VALID_ROLES == PAGE_ROLE_SKELETONS.keys()`) |
| Scope adherence | Only test files created, no source changes |
| Maintainability | Clear test names, minimal setup, no test interdependencies |
| Testability | Tests are themselves fast (<2s total), no I/O |
| Robustness | Edge cases covered (empty input, None, boundary values) |
| Performance | No slow fixtures, no unnecessary file I/O |
| Integration fit | Tests runnable via `pytest` with no extra config |
| Observability | Assertion messages are descriptive on failure |
| Minimality | No unnecessary test helpers or abstractions |

## Now (Runbook)

```bash
# 1. Create test files
# (write each file per deliverables above)

# 2. Run new tests in isolation
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/test_section_validator_claim_strip.py tests/unit/workers/test_frontmatter_role_validation.py tests/unit/test_planner_role_validation.py tests/unit/test_run_config_validation.py -v

# 3. Run full suite to confirm no regressions
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --ignore=tests/test_planner_per_module.py

# 4. Verify count: expect ≥2159 + 15 new = ≥2174 passed
```
