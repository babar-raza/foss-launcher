# WS2-SCHEMA-UPDATE: Add Optional taskcard_id Field to run_config Schema

## Objective
Update `specs/schemas/run_config.schema.json` to add optional `taskcard_id` and `related_taskcards` fields for tracking which taskcard(s) a run implements.

## Requirements
- **Backward Compatibility**: New fields MUST be optional (NOT added to required array)
- **Format Validation**: taskcard_id and related_taskcards MUST match pattern `^TC-\d+$`
- **Existing Configs**: All existing pilot configs must continue to validate
- **Self-Review**: All 12 dimensions must score ≥4/5

## Implementation Plan

### Phase 1: Schema Update (30 min)
1. Read current schema from `specs/schemas/run_config.schema.json`
2. Add two new properties to the "properties" object:
   - `taskcard_id`: string with pattern `^TC-\d+$`
   - `related_taskcards`: array of strings with pattern `^TC-\d+$`
3. Do NOT modify the "required" array (backward compatibility)
4. Validate JSON syntax

### Phase 2: Validation Testing (30 min)
1. Test existing configs WITHOUT taskcard_id (should pass)
   - `pilot-aspose-3d-foss-python/run_config.pinned.yaml`
   - `pilot-aspose-note-foss-python/run_config.pinned.yaml`
2. Test WITH taskcard_id (should pass)
   - Create test config with valid TC-### format
   - Validate against schema
3. Test invalid formats (should fail)
   - Invalid pattern (e.g., "TC-abc", "INVALID", "123")

### Phase 3: Documentation (20 min)
1. Create `changes.md` documenting schema modifications
2. Create `evidence.md` with validation test results
3. Create `commands.sh` with all commands executed

### Phase 4: Self-Review (20 min)
Complete 12-dimension review in `self_review.md`:
1. Correctness
2. Completeness
3. Backward Compatibility
4. Pattern Validation
5. Documentation
6. Testing Coverage
7. Edge Cases
8. Performance
9. Security
10. Maintainability
11. Clarity
12. Risk Assessment

## Timeline
- Total estimated: 100 minutes
- Checkpoints: After schema update, after validation, after documentation

## Success Criteria
- Schema file is valid JSON
- All existing configs pass validation
- New optional fields work correctly
- Pattern validation enforces TC-### format
- All 12 self-review dimensions ≥4/5
- All deliverables present and complete
