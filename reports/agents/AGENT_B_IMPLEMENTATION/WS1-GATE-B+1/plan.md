# Implementation Plan: WS1-GATE-B+1 - Taskcard Readiness Validation Gate

## Incident Context

**Problem**: TC-700-703 were worked on WITHOUT taskcards existing (SOP violation)
**Root Cause**: No gate validates "taskcard exists before work"
**Solution**: Create Gate B+1 to block unauthorized work

## Assumptions (Verified)

Based on reading existing reference files:

1. **Gate Pattern** (`tools/validate_swarm_ready.py`):
   - Gates are Python scripts that return exit code 0 (pass) or 1 (fail)
   - Run via `GateRunner.run_gate()` method
   - Gate B currently runs at line 235-240
   - Integration point: Add Gate B+1 immediately after Gate B

2. **Frontmatter Parsing** (`tools/validate_taskcards.py`):
   - Function `extract_frontmatter()` can be reused (lines 62-83)
   - Returns (frontmatter_dict, body_content, error_message)
   - Handles YAML parsing and basic validation

3. **Taskcard Schema** (`plans/taskcards/TC-100_bootstrap_repo.md`):
   - Frontmatter has required fields: id, title, status, depends_on, etc.
   - Status values: "Draft", "Ready", "In-Progress", "Blocked", "Done"
   - Valid statuses for work: "Ready", "Done" (NOT "Draft" or "Blocked")
   - Dependencies specified in `depends_on` list

4. **Pilot Config Schema** (`specs/pilots/*/run_config.pinned.yaml`):
   - Currently NO `taskcard_id` field exists in pilot configs
   - This is a NEW field that MUST be added for Gate B+1 to work
   - Gate B+1 must be OPTIONAL if field missing (backward compatible)

## Implementation Steps

### Step 1: Create `tools/validate_taskcard_readiness.py`

**Purpose**: Standalone gate script that validates taskcard readiness

**Logic**:
1. Scan `specs/pilots/*/run_config.pinned.yaml` for pilot configs
2. Load each YAML file and check for `taskcard_id` field
3. If `taskcard_id` missing: Skip validation (backward compatible)
4. If `taskcard_id` present:
   - Find taskcard file: `plans/taskcards/TC-{id}_*.md`
   - Parse YAML frontmatter
   - Validate status in ["Ready", "Done"]
   - Recursively validate `depends_on` taskcards
   - Detect circular dependencies
5. Return exit code 0 (all valid) or 1 (errors found)

**Key Functions**:
- `find_pilot_configs(repo_root)`: Glob for pilot configs
- `extract_taskcard_id(config_data)`: Get taskcard_id from YAML
- `find_taskcard_file(tc_id, repo_root)`: Locate TC-{id}_*.md
- `extract_frontmatter(content)`: Reuse from validate_taskcards.py
- `validate_taskcard_status(frontmatter)`: Check status in ["Ready", "Done"]
- `validate_dependency_chain(tc_id, repo_root, visited)`: Recursive dependency check
- `main()`: Orchestrate validation

### Step 2: Integrate into `tools/validate_swarm_ready.py`

**Location**: After Gate B (line 240)

**Code to add**:
```python
# Gate B+1: Taskcard readiness validation
runner.run_gate(
    "B+1",
    "Taskcard readiness validation",
    "tools/validate_taskcard_readiness.py",
    check_warnings=False
)
```

**Header update**: Add Gate B+1 to docstring (line 13):
```python
#  B+1 - validate_taskcard_readiness.py (taskcard exists + ready before work)
```

### Step 3: Create `tests/unit/tools/test_validate_taskcard_readiness.py`

**Test Coverage** (100% required):
1. `test_no_pilot_configs()`: Empty pilots directory
2. `test_no_taskcard_id_field()`: Pilot config without taskcard_id (skip validation)
3. `test_taskcard_exists_pass()`: Valid taskcard with status "Ready"
4. `test_taskcard_done_status_pass()`: Valid taskcard with status "Done"
5. `test_taskcard_missing_fail()`: Taskcard file doesn't exist
6. `test_taskcard_draft_status_blocked()`: Status is "Draft"
7. `test_taskcard_blocked_status_fail()`: Status is "Blocked"
8. `test_dependency_chain_satisfied()`: All deps are Ready/Done
9. `test_dependency_missing_fail()`: Dependency taskcard missing
10. `test_circular_dependency_fail()`: TC-A depends on TC-B, TC-B depends on TC-A
11. `test_invalid_frontmatter()`: Malformed YAML
12. `test_multiple_pilots_mixed()`: Some pass, some fail

**Test Fixtures**:
- Use `tmp_path` pytest fixture for isolated filesystem
- Create mock pilot configs and taskcards
- Test both success and failure paths

### Step 4: Update Documentation

**Files to update**:
- `tools/validate_swarm_ready.py`: Docstring header (Gate B+1 entry)

## Rollback Plan

If Gate B+1 causes issues:

1. **Remove integration**: Comment out Gate B+1 call in `validate_swarm_ready.py`
2. **Preserve script**: Keep `tools/validate_taskcard_readiness.py` for future use
3. **Preserve tests**: Keep tests for regression prevention
4. **Git revert**: If needed, revert commit with: `git revert <commit-sha>`

**Safe because**:
- Gate B+1 is ADDITIVE (doesn't modify existing gates)
- Backward compatible (skips if taskcard_id missing)
- Can be disabled by removing 4 lines from validate_swarm_ready.py

## Test Plan

### Unit Tests
```bash
python -m pytest tests/unit/tools/test_validate_taskcard_readiness.py -v
```

**Expected**: All 12 tests pass (100% coverage)

### Integration Tests
```bash
# Test Gate B+1 in isolation
python tools/validate_taskcard_readiness.py

# Test full gate suite
python tools/validate_swarm_ready.py
```

**Expected**:
- Gate B+1 passes (no pilots have taskcard_id yet)
- All other gates unchanged

### Manual Tests

1. **Test backward compatibility**:
   - Run with current pilots (no taskcard_id) → PASS

2. **Test validation logic** (future):
   - Add `taskcard_id: TC-100` to a pilot config
   - Verify Gate B+1 validates TC-100 exists and is Ready

### Regression Tests

Verify existing gates still work:
```bash
python tools/validate_taskcards.py  # Gate B
python tools/validate_swarm_ready.py  # All gates
```

## Acceptance Checklist

- [ ] `tools/validate_taskcard_readiness.py` created (~200 lines)
- [ ] `tests/unit/tools/test_validate_taskcard_readiness.py` created (~150 lines)
- [ ] `tools/validate_swarm_ready.py` modified (Gate B+1 integration)
- [ ] Gate B+1 fails if taskcard doesn't exist
- [ ] Gate B+1 fails if status is "Draft" or "Blocked"
- [ ] Gate B+1 fails if dependency chain broken
- [ ] Gate B+1 passes for all existing pilots (backward compatible)
- [ ] All unit tests pass (100% coverage)
- [ ] All existing gates still pass
- [ ] Circular dependency detection works
- [ ] Self-review completed (all dimensions ≥4/5)
- [ ] All deliverables created (changes.md, evidence.md, commands.sh, self_review.md)

## Risk Mitigation

**Risk 1**: Breaking existing workflows
- **Mitigation**: Backward compatible design (skip if taskcard_id missing)
- **Validation**: Test with current pilot configs

**Risk 2**: False positives/negatives
- **Mitigation**: Comprehensive unit tests (12 test cases)
- **Validation**: Test both success and failure paths

**Risk 3**: Circular dependency detection fails
- **Mitigation**: Track visited set, detect revisits
- **Validation**: Explicit test case for circular deps

**Risk 4**: Performance impact
- **Mitigation**: Gate only scans 2 pilots currently, O(n) complexity
- **Validation**: Measure gate runtime (<1 second expected)

## Success Metrics

1. **Correctness**: All tests pass (100% coverage)
2. **Backward Compatibility**: Existing gates unchanged
3. **Effectiveness**: Gate blocks work when taskcard missing/not ready
4. **Performance**: Gate runs in <1 second
5. **Code Quality**: Self-review ≥4/5 on all dimensions
