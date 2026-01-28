# Phase 3 Changes: Field Definitions

**Date:** 2026-01-27
**Agent:** AGENT_D (Docs & Specs)
**Phase:** 3 of 4 (Pre-Implementation Hardening)

---

## Summary

Added 2 missing field definitions to specs/01_system_contract.md to resolve BLOCKER gaps S-GAP-003 and S-GAP-006.

---

## Changes by File

### specs/01_system_contract.md

**Change 1: Added Field Definitions section header**
- **Location:** After line 175 (after Acceptance criteria section)
- **Lines:** 176-178
- **Content:**
  ```markdown
  ## Field Definitions

  This section defines critical fields used across configuration and artifact schemas.
  ```
- **Purpose:** Create new section to house field definitions

**Change 2: Added spec_ref field definition**
- **Location:** Lines 180-195
- **Gap Resolved:** S-GAP-003
- **Content:** Complete field definition including:
  - Type: string (required in run_config.json, page_plan.json, pr.json)
  - Definition: Git commit SHA (40-character hex) of foss-launcher repository
  - Validation rules: exactly 40 hex chars, must resolve to actual commit
  - Error codes: SPEC_REF_MISSING, SPEC_REF_INVALID (cross-referenced from line 134-135)
  - Purpose: Version locking for reproducibility (Guarantee K per specs/34:377-385)
  - Example: Full 40-char SHA example
  - Schema enforcement: run_config.schema.json, page_plan.schema.json, pr.schema.json

**Change 3: Added validation_profile field definition**
- **Location:** Lines 197-216
- **Gap Resolved:** S-GAP-006
- **Content:** Complete field definition including:
  - Type: string enum (strict/standard/permissive), optional, default: "standard"
  - Definition: Controls gate enforcement strength per specs/09:14-18
  - Values: All 3 enum values with descriptions
  - Validation rule: Must be one of 3 enum values
  - Purpose: Flexible enforcement for different contexts (CI vs local dev)
  - Example: "strict" value
  - Schema enforcement: run_config.schema.json:458 (already implemented)

---

## Cross-References Validated

### spec_ref Field
- [x] Error codes SPEC_REF_MISSING, SPEC_REF_INVALID exist at lines 134-135
- [x] References Guarantee K (specs/34:377-385)
- [x] References schemas: run_config.schema.json, page_plan.schema.json, pr.schema.json

### validation_profile Field
- [x] References gate enforcement (specs/09:14-18)
- [x] References schema definition (run_config.schema.json:458)

---

## Line Citations

| Change | File | Lines | Description |
|--------|------|-------|-------------|
| Field Definitions Section | specs/01_system_contract.md | 176-178 | New section header |
| spec_ref Field | specs/01_system_contract.md | 180-195 | Complete field definition (S-GAP-003) |
| validation_profile Field | specs/01_system_contract.md | 197-216 | Complete field definition (S-GAP-006) |

---

## Impact Analysis

### Files Modified
- specs/01_system_contract.md (1 file)

### Files Added
- None

### Files Deleted
- None

### Sections Modified
- specs/01_system_contract.md: Added new "Field Definitions" section after "Acceptance criteria"

### Cross-References Updated
- spec_ref field now references error codes from error registry (lines 134-135)
- spec_ref field now references Guarantee K (specs/34:377-385)
- validation_profile field now references gate enforcement (specs/09:14-18)
- validation_profile field now references schema (run_config.schema.json:458)

---

## Verification

### Grep Tests (All Passed)
```bash
# Test 1: Field definitions findable
grep -n "### spec_ref Field|### validation_profile Field" specs/01_system_contract.md
# Result: Lines 180, 197 (PASS)

# Test 2: Error code cross-references exist
grep -n "SPEC_REF_MISSING|SPEC_REF_INVALID" specs/01_system_contract.md
# Result: Lines 134, 135, 189 (PASS)
```

### Validation Gates
- [x] python scripts/validate_spec_pack.py - PASSED (exit 0)
- [x] Gate A1 (Spec pack validation) - PASSED
- [x] Both field definitions findable via grep
- [x] All cross-references valid

---

## Backward Compatibility

**Impact:** NONE - Additive changes only

- Added new section, did not modify existing sections
- Added new field definitions, did not change existing definitions
- All cross-references point to existing content (error codes added in Phase 1)
- No breaking changes to schemas (field definitions document existing schema fields)

---

## Testing

### Manual Testing
1. Read specs/01_system_contract.md - field definitions present
2. Grep for field definitions - both found
3. Grep for error codes - cross-references valid
4. Run spec pack validation - PASSED

### Automated Testing
- python scripts/validate_spec_pack.py - PASSED
- Gate A1 (Spec pack validation) - PASSED

---

## Completion Status

- [x] S-GAP-003: spec_ref field definition added
- [x] S-GAP-006: validation_profile field definition added
- [x] Both definitions findable via grep
- [x] Cross-references validated
- [x] Spec pack validation passed
- [x] No backward compatibility issues
