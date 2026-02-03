---
id: TC-702
title: "Validation Report Deterministic Generation"
status: Done
owner: "VALIDATOR_AGENT"
updated: "2026-01-30"
depends_on:
  - TC-460
  - TC-570
allowed_paths:
  - tests/unit/workers/test_tc_702_validation_report.py
  - reports/agents/**/TC-702/**
  # Note: src/launch/workers/w7_validator/worker.py moved to TC-935 (superseded)
evidence_required:
  - reports/agents/<agent>/TC-702/report.md
  - reports/agents/<agent>/TC-702/self_review.md
spec_ref: f48fc5dbb12c5513f42aabc2a90e2b08c6170323
ruleset_version: ruleset.v1
templates_version: templates.v1
---

# Taskcard TC-702 — Validation Report Deterministic Generation

## Objective
Ensure validation_report.json is deterministic across runs by normalizing paths and removing timestamps, enabling bit-for-bit reproducible validation artifacts for the golden process and VFV harness.

## Required spec references
- specs/10_determinism_and_caching.md
- specs/21_worker_contracts.md (W7)
- specs/09_validation_gates.md
- specs/schemas/validation_report.schema.json

## Scope
### In scope
- Add `normalize_validation_report()` function to W7 worker
- Replace absolute run_dir paths with `<RUN_DIR>` token
- Replace absolute repo root paths with `<REPO_ROOT>` token
- Remove timestamps from report body
- Stable sort gates by name
- Stable sort issues by (path, line, message)
- Add `compute_canonical_hash()` function for VFV use
- Create comprehensive unit tests proving determinism

### Out of scope
- Gate implementation changes (only validator normalization)
- Schema changes (work within existing schema)
- Full pilot execution (only unit tests)

## Inputs
- Validation report from gate execution (before normalization)
- run_dir path for token replacement

## Outputs
- Normalized validation_report.json with deterministic content
- Canonical hash for VFV comparison

## Allowed paths
- tests/unit/workers/test_tc_702_validation_report.py
- reports/agents/**/TC-702/**

**Note**: Implementation moved to TC-935 (superseded this taskcard's worker.py changes)

## Implementation steps
1) **Implement normalize_validation_report() function**:
   - Handle multiple path variants (resolved, unresolved, Windows, Unix)
   - Recursively replace run_dir paths with `<RUN_DIR>` token
   - Recursively replace repo root paths with `<REPO_ROOT>` token
   - Remove timestamps (generated_at, timestamp fields)
   - Stable sort gates by name
   - Stable sort issues by (path, line, message)
   - Deep recursive normalization of nested structures

2) **Implement compute_canonical_hash() function**:
   - Compute SHA256 hash of canonical JSON representation
   - Use sort_keys=True for deterministic serialization
   - Return hex digest for VFV harness comparison

3) **Modify execute_validator() function**:
   - Apply normalization before writing validation_report.json
   - Ensure normalization preserves schema compliance

4) **Create unit tests**:
   - Test basic normalization preserves structure
   - Test run_dir path replacement
   - Test repo root path replacement
   - Test path separator normalization (Windows → Unix)
   - Test timestamp removal
   - Test stable sorting (gates and issues)
   - **Critical test**: Two-run determinism proof (different paths → identical hashes)
   - Test canonical hash computation stability
   - Test deep nested path normalization
   - Test schema compliance preservation

## Failure modes

1. **Failure**: Path normalization misses some absolute paths
   - **Detection**: Unit test with multiple path variants finds unnormalized paths
   - **Fix**: Expand path variant handling to cover resolved/unresolved/Windows/Unix paths
   - **Spec/Gate**: specs/10_determinism_and_caching.md (determinism requirement)

2. **Failure**: Timestamps still present after normalization
   - **Detection**: Unit test checks for timestamp fields in normalized report
   - **Fix**: Add timestamp removal logic for all timestamp fields
   - **Spec/Gate**: specs/10_determinism_and_caching.md (stable artifacts)

3. **Failure**: Issue ordering non-deterministic
   - **Detection**: Two runs with same inputs produce different issue order
   - **Fix**: Implement stable sort by (path, line, message) tuple
   - **Spec/Gate**: specs/10_determinism_and_caching.md (reproducibility)

4) **Failure**: Normalization breaks schema compliance
   - **Detection**: Normalized report fails validation against validation_report.schema.json
   - **Fix**: Ensure normalization only modifies values, not structure; preserve all required fields
   - **Spec/Gate**: specs/schemas/validation_report.schema.json

## Task-specific review checklist

Beyond the standard acceptance checks, verify:
- [ ] All absolute paths replaced with tokens (`<RUN_DIR>`, `<REPO_ROOT>`)
- [ ] No timestamps in normalized report body
- [ ] Gates sorted alphabetically by name
- [ ] Issues sorted by (path, line, message)
- [ ] Two-run determinism test passes (identical hashes)
- [ ] Normalized report validates against schema
- [ ] Path separator normalization (Windows backslashes → forward slashes)
- [ ] Deep nested structures handled correctly

## E2E verification
**Concrete command(s) to run:**
```bash
# Run unit tests
python -m pytest tests/unit/workers/test_tc_702_validation_report.py -v

# Expected: 11/11 tests pass
```

**Expected artifacts:**
- Modified src/launch/workers/w7_validator/worker.py
- New tests/unit/workers/test_tc_702_validation_report.py

**Success criteria:**
- [ ] All 11 unit tests pass
- [ ] Two-run determinism test proves identical hashes
- [ ] Normalized report validates against schema

## Integration boundary proven
What upstream/downstream wiring was validated:
- Upstream: TC-460/TC-570 (gates) → TC-702 (normalization)
- Downstream: TC-702 → TC-703 (VFV harness uses canonical hash)
- Contracts: validation_report.schema.json, determinism guarantees

## Deliverables
- Code:
  - Modified src/launch/workers/w7_validator/worker.py with normalize_validation_report() and compute_canonical_hash()
  - New tests/unit/workers/test_tc_702_validation_report.py (11 tests)
- Reports:
  - reports/agents/<agent>/TC-702/report.md
  - reports/agents/<agent>/TC-702/self_review.md

## Acceptance checks
- [ ] normalize_validation_report() function implemented
- [ ] compute_canonical_hash() function implemented
- [ ] Absolute paths replaced with tokens
- [ ] Timestamps removed from report body
- [ ] Gates sorted by name
- [ ] Issues sorted by (path, line, message)
- [ ] All 11 unit tests pass
- [ ] Two-run determinism test proves identical hashes
- [ ] Normalized report validates against schema

## Self-review
Use `reports/templates/self_review_12d.md`. Any dimension <4 must include a concrete fix plan.
