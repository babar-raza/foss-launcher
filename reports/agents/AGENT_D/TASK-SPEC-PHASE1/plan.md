# TASK-SPEC-PHASE1: Add 4 Missing Error Codes

**Agent:** Agent D (Docs & Specs)
**Phase:** Phase 1 of Pre-Implementation Hardening
**Date:** 2026-01-27
**Workspace:** reports/agents/AGENT_D/TASK-SPEC-PHASE1/

---

## Objective

Add 4 missing error codes to specs/01_system_contract.md to resolve BLOCKER gaps identified in verification run 20260127-1724.

---

## Assumptions

1. Error codes should be added to the "Examples" section (lines 124-131 in specs/01_system_contract.md)
2. Error codes should maintain alphabetical order within their component categories
3. Format should match existing error codes: `- \`CODE_NAME\` - Description`
4. All error codes follow the pattern: `{COMPONENT}_{ERROR_TYPE}_{SPECIFIC}`

---

## Tasks

### TASK-SPEC-1A: Add SECTION_WRITER_UNFILLED_TOKENS
**Gap ID:** S-GAP-001
**Location:** specs/01_system_contract.md (Examples section, line ~124-131)
**Format:**
```markdown
- `SECTION_WRITER_UNFILLED_TOKENS` - LLM output contains unfilled template tokens like {{PRODUCT_NAME}}
```

### TASK-SPEC-1B: Add SPEC_REF_INVALID and SPEC_REF_MISSING
**Gap ID:** S-GAP-003
**Location:** specs/01_system_contract.md (Examples section, line ~124-131)
**Format:**
```markdown
- `SPEC_REF_INVALID` - spec_ref field is not a valid 40-character Git SHA
- `SPEC_REF_MISSING` - spec_ref field is required but not present in run_config/page_plan/pr
```

### TASK-SPEC-1C: Add REPO_EMPTY
**Gap ID:** S-GAP-010 (partial)
**Location:** specs/01_system_contract.md (Examples section, line ~124-131)
**Format:**
```markdown
- `REPO_EMPTY` - Repository has zero files after clone (excluding .git/ directory)
```

### TASK-SPEC-1D: Add GATE_DETERMINISM_VARIANCE
**Gap ID:** S-GAP-013
**Location:** specs/01_system_contract.md (Examples section, line ~124-131)
**Format:**
```markdown
- `GATE_DETERMINISM_VARIANCE` - Re-running with identical inputs produces different outputs
```

---

## Implementation Steps

1. Read specs/01_system_contract.md to locate exact line numbers
2. Add error codes to Examples section in alphabetical order:
   - GATE_DETERMINISM_VARIANCE (after COMMIT_SERVICE_AUTH_FAILED, before GATE_TIMEOUT)
   - REPO_EMPTY (after REPO_SCOUT_CLONE_FAILED)
   - SECTION_WRITER_UNFILLED_TOKENS (after SCHEMA_VALIDATION_FAILED)
   - SPEC_REF_INVALID (after SECTION_WRITER_UNFILLED_TOKENS)
   - SPEC_REF_MISSING (after SPEC_REF_INVALID)
3. Save changes
4. Validate with grep command
5. Run validation gates

---

## Validation Commands

```bash
# Verify error codes exist
grep -n "SECTION_WRITER_UNFILLED_TOKENS\|SPEC_REF_\|REPO_EMPTY\|GATE_DETERMINISM_VARIANCE" specs/01_system_contract.md

# Validate specs
python tools/validate_swarm_ready.py

# Validate spec pack
python scripts/validate_spec_pack.py
```

---

## Rollback Plan

If validation fails:
1. Revert changes: `git checkout -- specs/01_system_contract.md`
2. Review error messages
3. Fix issues
4. Re-apply changes

---

## Acceptance Criteria

- [ ] SECTION_WRITER_UNFILLED_TOKENS added to error code examples
- [ ] SPEC_REF_INVALID added to error code examples
- [ ] SPEC_REF_MISSING added to error code examples
- [ ] REPO_EMPTY added to error code examples
- [ ] GATE_DETERMINISM_VARIANCE added to error code examples
- [ ] All error codes follow existing format
- [ ] All error codes in alphabetical order
- [ ] grep command finds all 4 error codes
- [ ] python tools/validate_swarm_ready.py exits 0
- [ ] python scripts/validate_spec_pack.py exits 0
- [ ] specs/21:223 can reference SECTION_WRITER_UNFILLED_TOKENS
- [ ] specs/34:377-385 can reference SPEC_REF_ codes
- [ ] specs/02 can reference REPO_EMPTY
- [ ] specs/09:471-495 can reference GATE_DETERMINISM_VARIANCE

---

## Evidence Requirements

1. File path and line citations for all changes
2. Command outputs showing successful validation
3. grep output showing all 4 error codes exist
4. Self-review with 12-dimension scoring

---

## Notes

- The error codes in the mission brief include detailed specifications (Severity, When, Action, Debug), but the existing format in specs/01 is simpler (just `- \`CODE\` - Description`)
- I will match the existing format in specs/01 rather than adding the extended format
- The extended format details are provided in the mission brief for context but are not part of the specs/01 error code registry
