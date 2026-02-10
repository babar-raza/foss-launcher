---
id: TC-1101
task_id: TC-1101
title: "W5/W5.5 Contract Alignment: Frontmatter Field Name Resolution"
owner: Agent-B
status: Done
assignee: Agent-B
priority: P1
created: "2026-02-10"
updated: "2026-02-10"
spec_ref: 08ba89c5d5e624e0d2c29f5b561c2c5ce8308c5a
ruleset_version: ruleset.v1
templates_version: templates.v1
tags:
  - W5.5
  - ContentReviewer
  - frontmatter
  - contract-alignment
depends_on: []
blocks: []
evidence_required:
  - reports/agents/agent_b/TC-CREV-B-TRACK2/investigation.md
  - reports/agents/agent_b/TC-CREV-B-TRACK2/decision.md
  - reports/agents/agent_b/TC-CREV-B-TRACK2/changes.md
  - reports/agents/agent_b/TC-CREV-B-TRACK2/evidence.md
  - reports/agents/agent_b/TC-CREV-B-TRACK2/self_review.md
allowed_paths:
  - src/launch/workers/w5_5_content_reviewer/checks/content_quality.py
  - tests/unit/workers/w5_5_content_reviewer/test_checks.py
  - specs/schemas/frontmatter_contract.schema.json
  - reports/agents/agent_b/TC-CREV-B-TRACK2/**
---

# TC-CREV-B-TRACK2: W5/W5.5 Contract Alignment: Frontmatter Field Name Resolution

## Objective
Resolve the contract mismatch between W5 (which generates `permalink:` field) and W5.5 (which expects `url_path:` field) that causes 16 ERROR issues on all non-index pages during content review.

## Required spec references
- `specs/10_requirements.md` - Content generation requirements
- `specs/20_tech_platform_and_architecture.md` - Hugo frontmatter conventions
- `specs/schemas/frontmatter.schema.json` - Canonical frontmatter field definitions
- Hugo documentation - Standard frontmatter fields

## Scope

### In scope
- Investigation of field naming across W4, W5, W5.5, and Hugo standards
- Decision on canonical field name (permalink vs url_path)
- Implementation to accept both field names in W5.5 check logic
- Test coverage for both field formats
- Documentation update in frontmatter schema

### Out of scope
- Changing W5 output format (maintain backward compatibility)
- Modifying W4 page_plan artifact structure
- Changes to other W5.5 checks beyond frontmatter completeness

## Preconditions / dependencies
- W5.5 ContentReviewer implementation (TC-1100) completed
- Access to recent pilot run artifacts for investigation
- Hugo documentation for standard field names

## Inputs
- W5 generated frontmatter with `permalink` field
- W5.5 check expecting `url_path` field
- Hugo documentation on standard frontmatter fields
- `specs/schemas/frontmatter.schema.json`
- W4 page_plan artifacts

## Outputs
- Updated `_check_7_frontmatter_completeness()` to accept both `permalink` and `url_path`
- Test coverage for both field formats
- Updated `frontmatter.schema.json` documentation
- Evidence package in `reports/agents/agent_b/TC-CREV-B-TRACK2/`

## Allowed paths
- src/launch/workers/w5_5_content_reviewer/checks/content_quality.py
- tests/unit/workers/w5_5_content_reviewer/test_checks.py
- specs/schemas/frontmatter_contract.schema.json
- reports/agents/agent_b/TC-CREV-B-TRACK2/**

## Implementation steps

### Step 1: Investigation (B-101-1)
1. Check Hugo documentation for standard frontmatter field names
2. Read `specs/schemas/frontmatter.schema.json` for canonical field definition
3. Check W4 page_plan artifact for field specification
4. Check W5 source code for frontmatter generation logic
5. Check W5.5 check logic for field validation
6. Document findings in `investigation.md`

### Step 2: Decision (B-101-2)
1. Analyze investigation findings
2. Choose approach: Accept both fields (Option A - recommended)
3. Document decision rationale in `decision.md`
4. Justify based on Hugo standards and backward compatibility

### Step 3: Implementation (B-101-3)
1. Update `_check_7_frontmatter_completeness()` in `content_quality.py`
2. Modify logic to accept both `permalink` and `url_path` as valid
3. Ensure at least one field is present (not both required)
4. Document code changes in `changes.md`

### Step 4: Test Coverage (B-101-4)
1. Add test case: frontmatter with `url_path` only → PASS
2. Add test case: frontmatter with `permalink` only → PASS
3. Add test case: frontmatter with both fields → PASS
4. Add test case: frontmatter with neither field → ERROR
5. Ensure all existing tests still pass

### Step 5: Schema Documentation (B-101-5)
1. Update `frontmatter.schema.json` to document both fields
2. Add clarification that either field is acceptable
3. Reference Hugo standard for `permalink`

### Step 6: Verification (B-101-6)
1. Run full test suite: `.venv/Scripts/python.exe -m pytest tests/ -x`
2. Verify no regressions in test_checks.py
3. Document test results in `evidence.md`

## Failure modes

### FM-1: Tests fail after implementation
**Detection**: pytest exit code non-zero
**Resolution**:
1. Review test output for specific failures
2. Check if test fixtures need updating
3. Verify check logic handles all edge cases
4. Revert changes and re-analyze if critical failure
**Spec/Gate**: Gate T (test determinism)

### FM-2: Schema change breaks validation elsewhere
**Detection**: Schema validation errors in other components
**Resolution**:
1. Search codebase for frontmatter.schema.json usage
2. Check if other validators depend on strict field names
3. Update dependent validators if needed
4. Document cross-component impact
**Spec/Gate**: Gate B (schema validation)

### FM-3: Hugo build fails due to field mismatch
**Detection**: Gate 13 (Hugo Build) failure
**Resolution**:
1. Verify Hugo actually accepts both field names
2. Check Hugo version compatibility
3. Test with minimal Hugo site
4. Fall back to single canonical field if needed
**Spec/Gate**: Gate 13 (Hugo Build)

### FM-4: W4 page_plan uses third field name
**Detection**: Investigation reveals W4 uses different field
**Resolution**:
1. Document all three field names
2. Expand check to accept all variants
3. File blocker issue for field standardization
4. Ensure backward compatibility maintained
**Spec/Gate**: Spec 20 (architecture)

### FM-5: Existing content has mixed field usage
**Detection**: Pilot runs show inconsistent field names
**Resolution**:
1. Accept both fields as valid (planned solution)
2. Do not require migration of existing content
3. Document field name evolution
4. Ensure new content follows convention
**Spec/Gate**: Spec 10 (requirements)

### FM-6: Performance impact from dual field check
**Detection**: Measurable slowdown in W5.5 execution
**Resolution**:
1. Measure baseline vs modified performance
2. Optimize check logic if needed (early return)
3. Document any performance trade-offs
4. Acceptable if impact <5% overall runtime
**Spec/Gate**: Spec 30 (AI governance - performance budgets)

## Task-specific review checklist
1. Investigation covers all 5 data sources (Hugo docs, schema, W4, W5, W5.5)
2. Decision document includes clear rationale with evidence citations
3. Implementation accepts both `permalink` and `url_path` without breaking existing behavior
4. Test coverage includes all 4 scenarios (url_path only, permalink only, both, neither)
5. Schema documentation clarifies both fields are valid with Hugo standard reference
6. Full test suite passes with no regressions
7. Evidence package includes before/after comparison of check behavior
8. Changes maintain backward compatibility with existing content
9. No manual content edits required (policy compliance)
10. Git commit includes Co-Authored-By tag

## Test plan
1. Unit tests for check logic with all 4 field scenarios
2. Integration test: W5 → W5.5 with real frontmatter
3. Regression test: Ensure existing tests pass
4. Manual verification: Check pilot run artifacts show PASS for frontmatter check

## E2E verification

**Commands**:
```bash
# Run new test suite
.venv/Scripts/python.exe -m pytest tests/unit/workers/w5_5_content_reviewer/test_checks.py::TestBugFixB101FrontmatterUrlField -xvs

# Run full W5.5 test suite
.venv/Scripts/python.exe -m pytest tests/unit/workers/w5_5_content_reviewer/ -x
```

**Expected artifacts**:
- Test results: 5/5 new tests pass, 121/121 existing tests pass
- No test failures or regressions
- Evidence package in `reports/agents/agent_b/TC-CREV-B-TRACK2/`

**Future verification** (orchestrator task):
- Run pilot with W5.5 enabled
- Verify review_report.json shows 0 frontmatter URL field errors

## Integration boundary proven

**Upstream**: W5 SectionWriter
- W5 generates `permalink:` field in frontmatter (Hugo standard)
- Confirmed in: `src/launch/workers/w5_section_writer/worker.py` lines 299, 435, 607, 901, 1097
- No changes needed: W5 output format is correct

**Downstream**: W6 LinkerPatcher, W7 Validator
- W6 consumes markdown content, not specific frontmatter field names
- W7 validation gates do not check frontmatter field names
- No changes needed: downstream workers unaffected

**Artifact contracts**:
- W4 page_plan.json: Uses `url_path` field (internal model) - unchanged
- W5 draft markdown: Generates `permalink` field (Hugo standard) - unchanged
- W5.5 review_report.json: Now accepts both field names - fixed

## Deliverables
1. Updated check logic in `content_quality.py`
2. New test cases in `test_checks.py`
3. Updated schema documentation in `frontmatter.schema.json`
4. Evidence package:
   - `investigation.md` - Findings from 5 data sources
   - `decision.md` - Option chosen with rationale
   - `changes.md` - File-by-file change documentation
   - `evidence.md` - Test results and before/after comparison
   - `self_review.md` - 12D self-review scoring

## Acceptance checks
- [ ] Taskcard created and registered in INDEX.md
- [ ] Investigation complete with all 5 sources documented
- [ ] Decision documented with evidence-based rationale
- [ ] Check logic updated to accept both field names
- [ ] Test coverage complete for all 4 scenarios
- [ ] Schema documentation updated
- [ ] Full test suite passes (no regressions)
- [ ] Evidence package generated in reports/agents/agent_b/TC-CREV-B-TRACK2/
- [ ] 12D self-review completed with ≥4/5 on all dimensions
- [ ] Git commit created with Co-Authored-By tag

## Self-review
Will be completed in `reports/agents/agent_b/TC-CREV-B-TRACK2/self_review.md` using the 12D template.
