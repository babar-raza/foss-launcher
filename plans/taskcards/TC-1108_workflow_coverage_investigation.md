---
id: TC-1108
title: "Workflow Coverage Investigation (developer-guide.md)"
status: Done
priority: LOW
owner: agent_d
agent: agent_d
track: track3_content_reviewer_final_tuning
created: "2026-02-10"
updated: "2026-02-10"
depends_on: [TC-1105]
blocks: []
allowed_paths:
  - src/launch/workers/w4_ia_planner/worker.py
  - src/launch/workers/w5_5_content_reviewer/checks/technical_accuracy.py
  - tests/unit/workers/w4_ia_planner/test_worker.py
  - tests/unit/workers/w5_5_content_reviewer/test_technical_accuracy.py
  - plans/taskcards/TC-1108_workflow_coverage_investigation.md
  - reports/agents/agent_d/TC-1108_workflow_coverage_investigation/**
evidence_required:
  - investigation.md with findings from 5-step investigation
  - decision.md with option chosen (A/B/C) and rationale
  - changes.md with implementation details (if fix chosen)
  - evidence.md with test results (if fix chosen)
  - self_review.md with 12D scoring
spec_ref: "60acd31b02cb92674179b7582af6810a1eb33ac1"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# TC-1108: Workflow Coverage Investigation (developer-guide.md)

## Objective
Investigate whether the "Workflow not covered: Installation" error for developer-guide.md is a false positive (incorrect page_role assignment), legitimate content gap (W5 generation quality issue), or check too strict (reviewer logic needs refinement).

## Required spec references
- `specs/04_w4_ia_planner.md` - Page role assignment logic
- `specs/17_w5_5_content_reviewer.md` - Workflow coverage check specification
- `specs/schemas/page_plan.schema.json` - Page plan structure and page_role values
- `specs/schemas/product_facts.schema.json` - Workflow definitions

## Scope

### In scope
1. Analyze product_facts.json to identify all workflows
2. Analyze page_plan.json to understand developer-guide's page_role and purpose
3. Analyze developer-guide.md content to identify mentioned workflows
4. Review W4 page_role assignment logic for developer-guide
5. Review W5.5 workflow coverage check trigger conditions
6. Determine root cause (Option A, B, or C)
7. Implement fix if needed (Option A or C)
8. Document as legitimate if Option B

### Out of scope
- Fixing W5 content generation quality (Option B scenario)
- Modifying workflow definitions in product_facts
- Changing page plan structure
- Refactoring unrelated checks in W5.5

## Inputs
- `runs/track2_final_validation/artifacts/product_facts.json` - Workflow definitions
- `runs/track2_final_validation/artifacts/page_plan.json` - Page role assignments
- `runs/track2_final_validation/drafts/docs/developer-guide.md` - Actual content
- `src/launch/workers/w4_ia_planner/worker.py` - Page role assignment logic
- `src/launch/workers/w5_5_content_reviewer/checks/technical_accuracy.py` - Coverage check logic

## Outputs
- `reports/agents/agent_d/TC-1108_workflow_coverage_investigation/investigation.md` - Detailed findings
- `reports/agents/agent_d/TC-1108_workflow_coverage_investigation/decision.md` - Option chosen with rationale
- `reports/agents/agent_d/TC-1108_workflow_coverage_investigation/changes.md` - Implementation (if fix)
- `reports/agents/agent_d/TC-1108_workflow_coverage_investigation/evidence.md` - Test results (if fix)
- `reports/agents/agent_d/TC-1108_workflow_coverage_investigation/self_review.md` - 12D scoring
- Updated source files (if fix needed)
- Updated test files (if fix needed)

## Allowed paths
- src/launch/workers/w4_ia_planner/worker.py
- src/launch/workers/w5_5_content_reviewer/checks/technical_accuracy.py
- tests/unit/workers/w4_ia_planner/test_worker.py
- tests/unit/workers/w5_5_content_reviewer/test_technical_accuracy.py
- plans/taskcards/TC-1108_workflow_coverage_investigation.md
- reports/agents/agent_d/TC-1108_workflow_coverage_investigation/**

## Preconditions / dependencies
- TC-1105 completed (Track 2 final validation with errors identified)
- Track 2 validation artifacts available in `runs/track2_final_validation/`
- W5.5 ContentReviewer implementation complete
- Test suite passing baseline

## Implementation steps

### Step 1: Investigation Phase
1. Read `runs/track2_final_validation/artifacts/product_facts.json`
   - Extract all workflow definitions
   - Note workflow IDs, names, and types
2. Read `runs/track2_final_validation/artifacts/page_plan.json`
   - Find developer-guide entry
   - Document page_role, purpose, target_workflows
3. Read `runs/track2_final_validation/drafts/docs/developer-guide.md`
   - List all workflows mentioned in content
   - Check for Installation workflow presence
4. Read `src/launch/workers/w4_ia_planner/worker.py`
   - Locate `_assign_page_role()` function
   - Document logic for assigning comprehensive_guide role
   - Identify conditions for developer-guide classification
5. Read `src/launch/workers/w5_5_content_reviewer/checks/technical_accuracy.py`
   - Locate workflow coverage check (T-003)
   - Document trigger conditions (which page_roles)
   - Document coverage requirement logic

### Step 2: Analysis Phase
1. Compare workflows in product_facts vs developer-guide content
2. Evaluate if developer-guide SHOULD be comprehensive_guide
3. Evaluate if comprehensive_guide SHOULD cover ALL workflows
4. Evaluate if Installation is appropriate for developer-guide context

### Step 3: Decision Phase
Select one option:

**Option A - False Positive (page_role incorrect)**:
- Condition: developer-guide should NOT be comprehensive_guide
- Root cause: W4 page_role assignment logic too broad
- Fix target: `src/launch/workers/w4_ia_planner/worker.py`
- Action: Refine `_assign_page_role()` logic

**Option B - Legitimate Gap (content missing)**:
- Condition: developer-guide SHOULD be comprehensive AND SHOULD cover Installation
- Root cause: W5 generation quality issue (not reviewer bug)
- Fix target: None (W5.5 working as designed)
- Action: Document as legitimate content quality issue

**Option C - Check Too Strict**:
- Condition: comprehensive_guide shouldn't require ALL workflows
- Root cause: Workflow coverage check too rigid
- Fix target: `src/launch/workers/w5_5_content_reviewer/checks/technical_accuracy.py`
- Action: Add exemptions or scoring refinement

### Step 4: Implementation Phase (if Option A or C)
1. Implement code changes in target file
2. Add/update corresponding test cases
3. Run test suite: `python -m pytest tests/ -x`
4. Verify 1 error eliminated in validation rerun
5. Document changes in changes.md

### Step 5: Evidence Phase
1. Write investigation.md with all findings
2. Write decision.md with option chosen and rationale
3. Write changes.md (if fix implemented)
4. Write evidence.md with test results (if fix implemented)
5. Write self_review.md with 12D scoring

## Failure modes

### FM-1: Misdiagnosis of root cause
**Detection signal**: Fix implemented but error persists or new errors introduced
**Resolution steps**:
1. Revert changes
2. Re-read spec sections with focus on page_role definitions
3. Trace execution path in debugger
4. Consult `specs/04_w4_ia_planner.md` and `specs/17_w5_5_content_reviewer.md`
**Spec/gate link**: Specs 04, 17; Gate T-003

### FM-2: Invalid test coverage
**Detection signal**: Tests pass but validation still shows error
**Resolution steps**:
1. Add integration test with real artifacts
2. Verify test uses same logic as production code
3. Check for mocking that hides real behavior
**Spec/gate link**: Guarantee I (non-flaky tests)

### FM-3: Breaking change to page_role assignment
**Detection signal**: Other pages misclassified after fix
**Resolution steps**:
1. Review all page_role assignments in page_plan.json
2. Add regression tests for other page types
3. Refine logic to be more specific (avoid broad changes)
**Spec/gate link**: Spec 04 (W4 page role definitions)

### FM-4: Workflow coverage logic too lenient
**Detection signal**: After Option C fix, real gaps not detected
**Resolution steps**:
1. Review exemption conditions carefully
2. Add test cases for legitimate workflow gaps
3. Ensure fix doesn't disable check entirely
**Spec/gate link**: Spec 17 (Technical Accuracy dimension)

### FM-5: Evidence incomplete
**Detection signal**: Self-review dimension <4 due to missing analysis
**Resolution steps**:
1. Re-read all 5 input files with detailed notes
2. Document every decision point
3. Include code snippets and line numbers in investigation.md
**Spec/gate link**: Taskcard contract (evidence-driven decisions)

### FM-6: Version lock fields invalid
**Detection signal**: Gate B validation fails on taskcard
**Resolution steps**:
1. Run `git rev-parse HEAD` to get correct commit SHA
2. Verify spec_ref, ruleset_version, templates_version match contract
3. Re-validate with `python tools/validate_taskcards.py`
**Spec/gate link**: Guarantee K (version locking)

## Task-specific review checklist
1. [ ] All 5 investigation steps completed with documented findings
2. [ ] Decision rationale clearly links findings to chosen option (A/B/C)
3. [ ] If Option B: Evidence shows developer-guide SHOULD be comprehensive AND SHOULD cover Installation
4. [ ] If Option A or C: Code changes target root cause identified in investigation
5. [ ] If Option A or C: Test coverage includes both unit and integration tests
6. [ ] If Option A or C: Validation rerun shows 1 error eliminated (or documented why not)
7. [ ] investigation.md includes code snippets and line numbers for all findings
8. [ ] decision.md explicitly rules out non-chosen options with evidence
9. [ ] No changes to unrelated checks or page types
10. [ ] Evidence package complete (all 5 files) before self-review

## Test plan
If Option A or C chosen:
1. Unit tests for modified function in isolation
2. Integration test with real track2 artifacts
3. Regression test for other page types (Option A)
4. Negative test for legitimate workflow gaps (Option C)
5. Full test suite: `python -m pytest tests/ -x`
6. Validation rerun: Check error count reduction

If Option B chosen:
1. No test changes needed (documenting legitimate issue)
2. Evidence shows check working as designed

## Deliverables
1. Updated taskcard (this file) with status: Done
2. Evidence package in `reports/agents/agent_d/TC-1108_workflow_coverage_investigation/`:
   - investigation.md
   - decision.md
   - changes.md (if fix)
   - evidence.md (if fix)
   - self_review.md
3. Updated source files (if Option A or C)
4. Updated test files (if Option A or C)
5. Git commit with Co-Authored-By (if fix)

## Acceptance checks
- [ ] Taskcard registered in `plans/taskcards/INDEX.md`
- [ ] Taskcard validates: `python tools/validate_taskcards.py`
- [ ] Investigation phase: All 5 steps completed with findings documented
- [ ] Analysis phase: Workflows compared, page_role evaluated, coverage logic evaluated
- [ ] Decision phase: Option A, B, or C chosen with clear rationale
- [ ] Decision rationale references specific spec sections or code lines
- [ ] If Option A or C: Implementation complete with tests
- [ ] If Option A or C: Test suite passes (0 failures)
- [ ] If Option A or C: Validation shows 1 error eliminated OR explanation why not
- [ ] If Option B: Evidence shows legitimate issue (not reviewer bug)
- [ ] Evidence package complete (all required files present)
- [ ] Self-review ≥48/60 (≥4 per dimension)
- [ ] No shared-library violations in allowed_paths
- [ ] Changes respect determinism-first principle

## E2E verification
If fix implemented (Option A or C):
```bash
# Run full validation
python src/launch/orchestrator/graph.py --config specs/pilots/pilot-aspose-3d-foss-python/run_config.pinned.yaml --review-enabled
```

**Expected artifacts**:
- `runs/track2_final_validation/validation_report.json` with 1 fewer error
- developer-guide.md passes workflow coverage check (no T-003 error)
- Other comprehensive guides still validated appropriately

If Option B (legitimate issue):
```bash
# No code changes - verify check behavior matches spec
cat runs/track2_final_validation/review_results/docs/developer-guide.md.review.json
```

**Expected artifacts**:
- Review result showing T-003 error is legitimate per spec 17
- Documentation in decision.md explaining why this is expected behavior

## Integration boundary proven

**Upstream integration**:
- Input: product_facts.json with workflows, page_plan.json with page_role assignments, draft_sections from W5
- Contract: JSON schemas per specs/schemas/product_facts.schema.json, page_plan.schema.json, draft_section.schema.json

**Downstream integration**:
- Output: (Option A) Updated page_plan.json with refined page_role assignments
- Output: (Option C) Review results with refined workflow coverage checks
- Output: (Option B) Documentation of legitimate issue
- Contract: Same schemas maintained, no breaking changes

**Verification**:
If fix implemented (Option A or C):
- Integration tests pass with new/updated test cases
- Pilot validation shows expected error reduction (1 fewer error)
- No new errors introduced in validation_report.json
- Other page types not affected (regression test confirms)
- Contract compliance verified via test suite
- Backward compatible: no schema changes

If Option B (legitimate issue):
- Investigation evidence confirms check behavior matches spec 17
- No code changes needed (working as designed)
- Documentation complete in evidence package

## Self-review
(To be completed after implementation)
- See `reports/agents/agent_d/TC-1108_workflow_coverage_investigation/self_review.md`
