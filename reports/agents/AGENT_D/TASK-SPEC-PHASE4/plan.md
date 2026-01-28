# Phase 4 Execution Plan - Agent D (Docs & Specs)

**Agent**: Agent D (Docs & Specs)
**Phase**: 4 of 4 (Final Phase)
**Date**: 2026-01-27
**Workspace**: `reports/agents/AGENT_D/TASK-SPEC-PHASE4/`

---

## Context

This is the final phase of the Pre-Implementation Hardening plan to resolve spec-level BLOCKER gaps identified in verification run 20260127-1724. Phase 4 adds new endpoints, requirements, and specifications to resolve the final 3 spec-level gaps (S-GAP-020, R-GAP-004, S-GAP-023, R-GAP-001, R-GAP-002).

**Previous Phases**:
- Phase 1 (Error Codes): 4 error codes added - COMPLETED with 5/5 scores
- Phase 2 (Algorithms): 3 algorithms added - COMPLETED with 5/5 scores
- Phase 3 (Field Definitions): 2 field definitions added - COMPLETED with 5/5 scores

---

## Objectives

1. Add telemetry GET endpoint specification (S-GAP-020)
2. Add template resolution order algorithm (R-GAP-004)
3. Create test harness contract spec (S-GAP-023)
4. Add empty input handling requirement (R-GAP-001)
5. Add floating ref detection requirement (R-GAP-002)

---

## Task Breakdown

### TASK-SPEC-4A: Add Telemetry GET Endpoint (S-GAP-020)

**Gap**: Missing spec for telemetry GET endpoint referenced in MCP tool schemas

**Target Files**:
- `specs/16_local_telemetry_api.md` (add GET endpoint after line 73)
- `specs/24_mcp_tool_schemas.md` (add MCP tool schema after line 145)

**Changes**:
1. Add GET /telemetry/{run_id} endpoint specification to specs/16
2. Add get_run_telemetry MCP tool schema to specs/24
3. Add cross-references between both specs

**Acceptance Criteria**:
- GET endpoint documented with request/response formats
- MCP tool schema documented with input/output schemas
- Cross-references validate (grep verification)
- All validations pass

---

### TASK-SPEC-4B: Add Template Resolution Order (R-GAP-004)

**Gap**: Missing algorithm for deterministic template resolution when multiple templates match

**Target File**: `specs/20_rulesets_and_templates_registry.md` (after line 89)

**Changes**:
1. Add Template Resolution Order Algorithm section
2. Document 6-step resolution algorithm
3. Define specificity score calculation
4. Include determinism guarantee
5. Document error cases

**Acceptance Criteria**:
- Algorithm documented with 6 clear steps
- Specificity scoring defined with examples
- Determinism guarantee explicit
- Error cases documented
- All validations pass

---

### TASK-SPEC-4C: Create Test Harness Contract Spec (S-GAP-023)

**Gap**: Missing spec for test harness contract referenced in validation gates

**Target File**: `specs/35_test_harness_contract.md` (NEW FILE)

**Changes**:
1. Create new spec file with complete contract
2. Document CLI interface (REQ-TH-001)
3. Document preflight gates execution (REQ-TH-002)
4. Document runtime gates execution (REQ-TH-003)
5. Document test isolation (REQ-TH-004)
6. Document test report schema (REQ-TH-005)
7. Document pilot test execution (REQ-TH-006)
8. Add cross-references to specs/09, specs/11, specs/13, specs/34

**Acceptance Criteria**:
- New spec file created at specs/35_test_harness_contract.md
- All 6 requirements documented (REQ-TH-001 through REQ-TH-006)
- Cross-references to other specs included
- File validates and is findable via grep
- All validations pass

---

### TASK-SPEC-4D: Add Empty Input Handling Requirement (R-GAP-001)

**Gap**: Missing edge case handling for empty/insufficient input in ProductFacts

**Target File**: `specs/03_product_facts_and_evidence.md` (after line 45)

**Changes**:
1. Add "Edge Case: Empty Input Handling" section
2. Document detection criteria
3. Document behavior (emit REPO_EMPTY error)
4. Add cross-reference to specs/01 error code (REPO_EMPTY from Phase 1)
5. Add cross-reference to specs/02 empty repo edge case (from Phase 2)

**Acceptance Criteria**:
- Edge case section added after line 45
- Detection and behavior documented
- Cross-references to specs/01 and specs/02 included
- All validations pass

---

### TASK-SPEC-4E: Add Floating Ref Detection Requirement (R-GAP-002)

**Gap**: Missing requirement for floating reference detection at runtime

**Target File**: `specs/34_strict_compliance_guarantees.md` (after line 385)

**Changes**:
1. Add "Guarantee L: Floating Reference Detection" section
2. Document definition of floating references
3. Document enforcement rules (5 validation checks)
4. Document error cases
5. Add cross-references to specs/01 field definition (from Phase 3) and error codes (from Phase 1)
6. Add cross-references to specs/09 gates

**Acceptance Criteria**:
- Guarantee L documented after line 385
- 5 enforcement checks documented
- Error cases with error codes included
- Cross-references to specs/01 and specs/09 validate
- All validations pass

---

## Execution Order

1. TASK-SPEC-4A (telemetry endpoint) - independent
2. TASK-SPEC-4B (template resolution) - independent
3. TASK-SPEC-4C (test harness spec) - independent
4. TASK-SPEC-4D (empty input handling) - independent
5. TASK-SPEC-4E (floating ref detection) - independent

All tasks are independent and can be executed in parallel if needed.

---

## Validation Protocol

After completing all changes, run these validation commands:

```bash
# Spec pack validation
python scripts/validate_spec_pack.py

# Preflight gates validation
python tools/validate_swarm_ready.py

# Verify all additions present
grep -n "GET /telemetry" specs/16_local_telemetry_api.md
grep -n "get_run_telemetry" specs/24_mcp_tool_schemas.md
grep -n "Template Resolution Order" specs/20_rulesets_and_templates_registry.md
test -f specs/35_test_harness_contract.md && echo "specs/35 exists" || echo "specs/35 missing"
grep -n "35. Test Harness Contract" specs/35_test_harness_contract.md
grep -n "Empty Input Handling" specs/03_product_facts_and_evidence.md
grep -n "Floating Reference Detection" specs/34_strict_compliance_guarantees.md

# Verify cross-references
grep -n "specs/24" specs/16_local_telemetry_api.md
grep -n "specs/16" specs/24_mcp_tool_schemas.md
grep -n "REPO_EMPTY" specs/03_product_facts_and_evidence.md
grep -n "specs/01:180-195" specs/34_strict_compliance_guarantees.md
```

All commands must exit 0 (success).

---

## Hard Rules

1. NEVER delete or modify existing content (append-only changes)
2. NEVER work outside designated workspace folder
3. NEVER skip validation steps
4. NEVER claim completion without evidence
5. Preserve all existing formatting, line breaks, section structure
6. All changes must match HEALING_PROMPT.md proposed fixes exactly

---

## Rollback Plan

If any validation fails:
1. Identify the failing change via git diff
2. Revert that specific change using git checkout
3. Review the error message and fix the issue
4. Re-run validation

Full rollback:
```bash
git checkout -- specs/16_local_telemetry_api.md
git checkout -- specs/24_mcp_tool_schemas.md
git checkout -- specs/20_rulesets_and_templates_registry.md
git checkout -- specs/35_test_harness_contract.md
git checkout -- specs/03_product_facts_and_evidence.md
git checkout -- specs/34_strict_compliance_guarantees.md
```

---

## Success Criteria

- All 5 tasks completed
- All 3 gaps resolved (S-GAP-020, R-GAP-004, S-GAP-023, R-GAP-001, R-GAP-002)
- All validation commands exit 0
- Self-review scores ≥4/5 on all applicable dimensions
- All deliverables created in workspace folder

---

## Assumptions

1. HEALING_PROMPT.md proposed fixes are accurate and complete
2. Previous phases (1-3) completed successfully and their changes are available
3. All target spec files exist and are writable
4. Validation scripts are functional and up-to-date

---

## Risks

1. **Cross-reference validation failures**: Mitigate by verifying all cross-references after changes
2. **Spec pack validation errors**: Mitigate by running validation after each task
3. **Line number drift**: Mitigate by using content-based insertion points rather than exact line numbers
4. **Content drift from proposed fixes**: Mitigate by copying proposed fixes exactly from HEALING_PROMPT.md

---

## Deliverables

1. `plan.md` - This execution plan
2. `changes.md` - All changes with file:line citations
3. `evidence.md` - Validation results (grep outputs, spec pack validation, etc.)
4. `commands.sh` - All validation commands (executable)
5. `self_review.md` - 12-dimension self-review with scores

All deliverables will be created in `reports/agents/AGENT_D/TASK-SPEC-PHASE4/`.
