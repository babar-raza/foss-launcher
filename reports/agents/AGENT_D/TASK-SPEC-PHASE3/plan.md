# Phase 3 Execution Plan: Field Definitions

**Agent:** AGENT_D (Docs & Specs)
**Phase:** 3 of 4 (Pre-Implementation Hardening)
**Date:** 2026-01-27
**Status:** IN PROGRESS

---

## Objective

Add 2 missing field definitions to specs/01_system_contract.md to resolve BLOCKER gaps S-GAP-003 and S-GAP-006.

---

## Approach

1. **Read specs/01_system_contract.md** to identify structure
   - Locate field definitions section (if exists)
   - If no section exists, create one after error codes section (after line 175)

2. **Add spec_ref field definition** (S-GAP-003)
   - Complete definition with type, validation, purpose, example
   - Cross-reference error codes SPEC_REF_MISSING, SPEC_REF_INVALID from Phase 1
   - Cross-reference Guarantee K (specs/34:377-385)
   - Cross-reference schemas (run_config.schema.json, page_plan.schema.json, pr.schema.json)

3. **Add validation_profile field definition** (S-GAP-006)
   - Complete definition with type, enum values, purpose, example
   - Cross-reference specs/09:14-18 (gate enforcement)
   - Cross-reference run_config.schema.json:458

4. **Validate changes**
   - Run python tools/validate_swarm_ready.py
   - Run python scripts/validate_spec_pack.py
   - Grep for field definitions to verify findability
   - Grep for cross-references to verify validity

---

## Assumptions

1. specs/01_system_contract.md exists and is readable (VERIFIED in git status)
2. Error codes SPEC_REF_MISSING, SPEC_REF_INVALID exist in specs/01 (added in Phase 1)
3. Field definitions section does not currently exist (will create if needed)
4. Both field definitions follow consistent format from HEALING_PROMPT.md
5. Validation gates will pass after adding field definitions (spec-only changes)

---

## Steps

### STEP 1: Read specs/01_system_contract.md
- **Action:** Read entire file to identify structure
- **Output:** Understanding of where to add field definitions section

### STEP 2: Add spec_ref field definition
- **Location:** After error codes section (after line 175) or in existing field definitions
- **Content:** Full definition from HEALING_PROMPT.md (lines 241-257)
- **Cross-references:**
  - Error codes: SPEC_REF_MISSING, SPEC_REF_INVALID
  - Guarantee K: specs/34:377-385
  - Schemas: run_config.schema.json, page_plan.schema.json, pr.schema.json

### STEP 3: Add validation_profile field definition
- **Location:** After spec_ref field definition
- **Content:** Full definition from HEALING_PROMPT.md (lines 269-289)
- **Cross-references:**
  - Gate enforcement: specs/09:14-18
  - Schema: run_config.schema.json:458

### STEP 4: Validate changes
- **Command:** python tools/validate_swarm_ready.py
- **Expected:** Exit 0
- **Command:** python scripts/validate_spec_pack.py
- **Expected:** Exit 0
- **Command:** grep -n "### spec_ref Field|### validation_profile Field" specs/01_system_contract.md
- **Expected:** Both field definitions found
- **Command:** grep -n "SPEC_REF_MISSING|SPEC_REF_INVALID" specs/01_system_contract.md
- **Expected:** Cross-references found

---

## Risks

1. **Risk:** Field definitions section already exists with different format
   - **Mitigation:** Adapt to existing format if found
   - **Likelihood:** Low (no evidence of field definitions in current specs/01)

2. **Risk:** Cross-references to specs/34:377-385 or specs/09:14-18 are invalid
   - **Mitigation:** Verify line numbers after adding definitions
   - **Likelihood:** Low (line numbers from HEALING_PROMPT.md)

3. **Risk:** Validation gates fail after changes
   - **Mitigation:** Spec-only changes should not break validation
   - **Likelihood:** Very low

---

## Evidence Trail

All commands and outputs will be recorded in:
- commands.sh (append-only log of all commands)
- evidence.md (commands + outputs + analysis)

---

## Success Criteria

- [ ] spec_ref field definition added to specs/01
- [ ] validation_profile field definition added to specs/01
- [ ] Both definitions findable via grep
- [ ] spec_ref references SPEC_REF_MISSING, SPEC_REF_INVALID error codes
- [ ] spec_ref references Guarantee K (specs/34:377-385)
- [ ] validation_profile references run_config.schema.json:458
- [ ] python tools/validate_swarm_ready.py exits 0
- [ ] python scripts/validate_spec_pack.py exits 0
- [ ] Self-review score ≥4/5 on all 12 dimensions

---

## Execution Timeline

1. Read specs/01 (COMPLETED)
2. Add spec_ref field (NEXT)
3. Add validation_profile field (PENDING)
4. Validate changes (PENDING)
5. Write evidence (PENDING)
6. Self-review (PENDING)
