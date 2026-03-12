# SRI-04: Integration Test — Generated Config to RunConfig Validation

**Status:** Not Started
**Gap linkage:** Intake port self-review, Dimension 5 (Test Quality)
**Role:** Testing
**Scope:** End-to-end test proving generated configs load into v2 pipeline

---

## Problem

No test currently proves the full path: `generate_config()` → write YAML → `load_and_validate_run_config()` → success. Unit tests check field values but never validate the generated YAML actually loads as a valid RunConfig. This is the critical integration boundary.

## Acceptance Checks

- [ ] Test exists at `tests/integration/intake/test_config_roundtrip.py`
- [ ] Test calls `generate_config()` with mock repo metadata
- [ ] Test writes output to temp file
- [ ] Test loads via `load_and_validate_run_config()` (or RunConfig pydantic parse)
- [ ] Test asserts no validation errors
- [ ] Test asserts key fields (family, platform, repo_url) survive roundtrip
- [ ] Test passes with `PYTHONHASHSEED=0`

## Deliverables

1. `tests/integration/intake/test_config_roundtrip.py`

## Hard Rules

- Must use actual RunConfig loader, not hand-rolled YAML parsing
- Must not mock the validator — this is an integration test

## Review Dimensions

- Boundary coverage
- Realistic test data
- No false passes (test must fail if schema breaks)

## Runbook

1. Create test file
2. Build mock repo dict matching GitHub API shape
3. Call `generate_config(repo)`
4. Write to tmpdir YAML file
5. Load via `load_and_validate_run_config(path)`
6. Assert fields match
7. Run test
