# Agent C: Repository Cloning Gate Verification & Documentation Plan

## Mission
Complete Tasks GOVGATE-C1 (verification) and C2 (docs/telemetry) to verify and enhance the existing repository cloning validation implementation.

## Task C1: Repository Cloning Verification (READ-ONLY)

### Verification Steps

1. **Read and analyze validator implementation**
   - Read `src/launch/workers/_git/repo_url_validator.py` (expected ~616 lines)
   - Confirm structure includes:
     - URL validation logic
     - Pattern matching for allowed repo types
     - Legacy FOSS pattern support
     - Error handling

2. **Verify integration with clone operations**
   - Read `src/launch/workers/w1_repo_scout/clone.py`
   - Confirm `validate_repo_url()` is called before all clone operations
   - Identify all clone entry points

3. **Search for bypass paths**
   - Search entire codebase for direct `git clone` calls
   - Verify no unprotected clone operations exist
   - Check for subprocess calls that might bypass validation

4. **Verify test coverage**
   - Read `tests/unit/workers/_git/test_repo_url_validator.py`
   - Confirm 50+ test cases exist
   - Verify test quality and edge case coverage

5. **Run existing tests**
   - Execute validator tests
   - Confirm all tests pass
   - Document test results

### Expected Findings
- Implementation is complete and secure
- All clone paths protected by validation
- Comprehensive test coverage exists
- No security bypasses found

## Task C2: Documentation and Telemetry Fixes

### Exact Locations for Changes

#### 2.1 Documentation Addition
**File**: `specs/36_repository_url_policy.md`

**Action**: Add Legacy FOSS Pattern section
- Read file to understand structure
- Identify "Legacy Patterns" section location
- Add FOSS pattern documentation with examples:
  - Standard legacy pattern
  - FOSS legacy pattern
  - Example URLs

#### 2.2 Telemetry Addition
**File**: `src/launch/workers/w1_repo_scout/clone.py`

**Action**: Emit REPO_URL_VALIDATED events
- Read file to understand event emission patterns
- Identify all `validate_repo_url()` call sites
- Add telemetry event emission after each successful validation
- Event payload must include: url, repo_type
- Follow existing event emission pattern in codebase

### Test Commands

```bash
# C1 Verification
# ---------------

# 1. Check validator file exists and size
ls -lh "src/launch/workers/_git/repo_url_validator.py"

# 2. Search for git clone calls
grep -r "git clone" src/ --include="*.py" || echo "No direct git clone calls found"

# 3. Run validator tests
python -m pytest tests/unit/workers/_git/test_repo_url_validator.py -v

# 4. Check test coverage
python -m pytest tests/unit/workers/_git/test_repo_url_validator.py --cov=src/launch/workers/_git/repo_url_validator --cov-report=term-missing

# C2 Implementation
# -----------------

# 1. Verify specs file exists
ls -lh "specs/36_repository_url_policy.md"

# 2. After modifications, verify telemetry events
# Run a test clone operation and check events.ndjson
grep "REPO_URL_VALIDATED" <test_run_dir>/events.ndjson

# 3. Verify documentation renders correctly
cat "specs/36_repository_url_policy.md" | grep -A 10 "Legacy Patterns"
```

## Deliverables

1. `verification_report.md` - C1 findings and security assessment
2. `changes.md` - List of modified files (specs/36, clone.py)
3. `evidence.md` - Test results and event samples
4. `commands.sh` - All verification and test commands
5. `self_review.md` - 12-dimension quality assessment

## Critical Rules

- C1 is READ-ONLY - no code modifications
- C2 is minor additions only - no refactoring
- Verify tests pass before any changes
- Follow existing patterns for telemetry
- Maintain consistency with codebase style

## Success Criteria

- [ ] Verification report confirms security
- [ ] Documentation updated with FOSS pattern
- [ ] Telemetry events emitted correctly
- [ ] All tests passing
- [ ] Self-review >= 4/5 on all dimensions
