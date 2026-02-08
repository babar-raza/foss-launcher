# Agent A (Implementation + Architecture) Work Plan
## Mission: AG-001 Branch Creation Gate Strengthening

**Date**: 2026-02-02
**Agent**: Agent A (Implementation + Architecture)
**Mission**: Fix 3 critical security bypasses in AG-001 branch creation gate

---

## Executive Summary

The AG-001 gate is designed to block branch creation without user approval but has 3 critical weaknesses:
1. Hook not installed in `.git/hooks/` (only exists in `hooks/` directory)
2. Can be bypassed via `git config hooks.ai-governance.enforce false`
3. Commit service API has no AG-001 validation (W9 PRManager bypasses local hooks)

This plan addresses all 3 vulnerabilities through Tasks A1, A2, and A3.

---

## Assumptions (Verified)

### VERIFIED Assumptions
1. **Hook exists but not installed**: `hooks/prepare-commit-msg` exists but NOT in `.git/hooks/` ✓
   - Verified: Hook file exists at `c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\hooks\prepare-commit-msg`
   - Verified: `.git/hooks/prepare-commit-msg` does NOT exist

2. **Install script exists**: `hooks/install.sh` exists and can be used as reference ✓
   - Verified: File exists at `c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\hooks\install.sh`
   - Contains manual installation logic that can be automated

3. **Makefile exists**: `Makefile` exists and can be modified ✓
   - Verified: File exists at `c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\Makefile`
   - Currently has `install`, `install-uv`, `lint`, `format`, `validate`, `test` targets

4. **Git config bypass exists**: Lines 73-85 in `hooks/prepare-commit-msg` allow bypass ✓
   - Verified: Line 74 has `ENFORCE=$(git config --get hooks.ai-governance.enforce || echo "true")`
   - Verified: Lines 76-85 implement the bypass logic

5. **Commit service schema exists**: `specs/schemas/commit_request.schema.json` exists ✓
   - Verified: File exists with current schema version 1.0
   - Does NOT have `ai_governance_metadata` field (needs to be added)

6. **Commit service stub exists**: `scripts/stub_commit_service.py` exists ✓
   - Verified: File exists and implements `/v1/commit` endpoint
   - Does NOT have AG-001 validation (needs to be added)

7. **Commit service client exists**: `src/launch/clients/commit_service.py` exists ✓
   - Verified: File exists with `create_commit()` method
   - Does NOT send governance metadata (needs to be added)

8. **W9 PRManager exists**: `src/launch/workers/w9_pr_manager/worker.py` exists ✓
   - Verified: File exists with `execute_pr_manager()` function
   - Does NOT collect AG-001 approval (needs to be added)

9. **Commit service spec exists**: `specs/17_github_commit_service.md` exists ✓
   - Verified: File exists and documents API contract
   - Does NOT mention AG-001 requirement (needs to be added)

---

## Task Breakdown

### Task A1: Hook Installation Automation (2 days)

**Objective**: Ensure hooks are always installed in `.git/hooks/` after `make install`

**Files to Create/Modify**:
- CREATE: `scripts/install_hooks.py` - Automated installation script
- MODIFY: `Makefile` - Add `install-hooks` target and dependency

**Implementation Steps**:

1. **Create `scripts/install_hooks.py`**:
   - Read hook files from `hooks/` directory
   - Copy to `.git/hooks/` with proper permissions
   - Make executable (chmod +x on Unix, no-op on Windows Git Bash)
   - Idempotent: Safe to run multiple times (overwrite existing)
   - Backup existing hooks before overwriting
   - Return exit code 0 on success, non-zero on failure
   - Log installation actions to stdout

2. **Modify `Makefile`**:
   - Add new target: `install-hooks`
   - Call: `$(VENV_PY) scripts/install_hooks.py`
   - Modify `install` target to depend on `install-hooks`
   - Modify `install-uv` target to depend on `install-hooks`
   - Ensure hooks are installed AFTER venv setup

**Acceptance Criteria**:
- After `make install`, `.git/hooks/prepare-commit-msg` exists with executable permissions
- After `make install-uv`, `.git/hooks/prepare-commit-msg` exists with executable permissions
- Running `make install-hooks` multiple times is safe (idempotent)
- Existing hooks are backed up before overwriting
- Script works on both Windows and Unix-like systems

**Test Commands**:
```bash
# Clean state
rm -f .git/hooks/prepare-commit-msg

# Test installation
make install-hooks

# Verify hook installed
test -f .git/hooks/prepare-commit-msg && echo "✓ Hook installed"
test -x .git/hooks/prepare-commit-msg && echo "✓ Hook executable"

# Test idempotency
make install-hooks
make install-hooks
test -f .git/hooks/prepare-commit-msg && echo "✓ Still installed"

# Test full install flow
rm -f .git/hooks/prepare-commit-msg
make install
test -f .git/hooks/prepare-commit-msg && echo "✓ Hook installed via make install"
```

**Rollback Procedure**:
- Delete `scripts/install_hooks.py`
- Restore original `Makefile` from git
- Remove `.git/hooks/prepare-commit-msg` if needed

---

### Task A2: Remove Hook Bypass (1 day)

**Objective**: Remove git config bypass, only allow emergency bypass via environment variable

**Files to Modify**:
- MODIFY: `hooks/prepare-commit-msg` (lines 73-85)

**Implementation Steps**:

1. **Replace git config bypass (lines 73-85)**:
   - Remove line 74: `ENFORCE=$(git config --get hooks.ai-governance.enforce || echo "true")`
   - Replace with environment variable check: `AG001_EMERGENCY_BYPASS`
   - Only bypass if `AG001_EMERGENCY_BYPASS=true`
   - Log all bypasses to `.git/AG001_EMERGENCY_BYPASS_LOG.jsonl`

2. **Add bypass logging**:
   - Log format: JSON lines with timestamp, user, reason, branch
   - Fields: `{"timestamp": "ISO8601", "user": "git config user.name", "branch": "branch-name", "reason": "emergency bypass"}`
   - Append to `.git/AG001_EMERGENCY_BYPASS_LOG.jsonl`
   - Warn user that bypass is being used

**Acceptance Criteria**:
- Git config bypass no longer works: `git config hooks.ai-governance.enforce false` has no effect
- Environment variable bypass works: `AG001_EMERGENCY_BYPASS=true` allows commits
- All bypasses are logged to `.git/AG001_EMERGENCY_BYPASS_LOG.jsonl` with timestamp
- Normal (non-bypass) flow still blocks unapproved branches
- Approved branches still work normally

**Test Commands**:
```bash
# Test 1: Git config bypass no longer works
git checkout main
git checkout -b test-bypass-config
git config hooks.ai-governance.enforce false
touch test.txt
git add test.txt
git commit -m "Test commit"
# Expected: BLOCKED (git config has no effect)

# Clean up
git checkout main
git branch -D test-bypass-config
git config --unset hooks.ai-governance.enforce

# Test 2: Environment variable bypass works and logs
rm -f .git/AG001_EMERGENCY_BYPASS_LOG.jsonl
git checkout -b test-bypass-env
touch test.txt
git add test.txt
AG001_EMERGENCY_BYPASS=true git commit -m "Emergency commit"
# Expected: ALLOWED with warning
test -f .git/AG001_EMERGENCY_BYPASS_LOG.jsonl && echo "✓ Bypass logged"
cat .git/AG001_EMERGENCY_BYPASS_LOG.jsonl

# Clean up
git checkout main
git branch -D test-bypass-env

# Test 3: Normal flow still blocks
git checkout -b test-normal-block
touch test.txt
git add test.txt
git commit -m "Test commit"
# Expected: BLOCKED

# Clean up
git checkout main
git branch -D test-normal-block

# Test 4: Approved flow still works
touch .git/AI_BRANCH_APPROVED
echo "manual-test" > .git/AI_BRANCH_APPROVED
git checkout -b test-approved
touch test.txt
git add test.txt
git commit -m "Test commit"
# Expected: ALLOWED with governance metadata

# Clean up
git checkout main
git branch -D test-approved
```

**Rollback Procedure**:
- Restore `hooks/prepare-commit-msg` from git
- Re-run `make install-hooks` to reinstall original hook

---

### Task A3: Commit Service Validation (4 days)

**Objective**: Add AG-001 validation to commit service API

**Files to Create/Modify**:
- MODIFY: `specs/schemas/commit_request.schema.json` - Add `ai_governance_metadata` field
- MODIFY: `scripts/stub_commit_service.py` - Add validation logic
- MODIFY: `src/launch/clients/commit_service.py` - Send governance metadata
- MODIFY: `src/launch/workers/w9_pr_manager/worker.py` - Collect approval
- MODIFY: `specs/17_github_commit_service.md` - Document requirement

**Implementation Steps**:

1. **Update commit_request.schema.json**:
   - Add optional field: `ai_governance_metadata`
   - Structure:
     ```json
     "ai_governance_metadata": {
       "type": "object",
       "properties": {
         "ag001_approval": {
           "type": "object",
           "properties": {
             "approved": {"type": "boolean"},
             "approval_source": {"type": "string", "enum": ["interactive-dialog", "manual-marker", "config-override"]},
             "timestamp": {"type": "string"},
             "approver": {"type": "string"}
           },
           "required": ["approved", "approval_source", "timestamp"]
         }
       }
     }
     ```
   - NOT required initially (for backwards compatibility)
   - Will be required in future version

2. **Update stub_commit_service.py**:
   - Add validation in `/v1/commit` endpoint
   - Check for `ai_governance_metadata.ag001_approval`
   - If branch is new (not in idempotency store) AND no approval:
     - Return 403 with error code `AG001_APPROVAL_REQUIRED`
     - Error message: "Branch creation requires AI governance approval (AG-001)"
   - Log approval status in audit log
   - Add configuration flag to enable/disable check (default: enabled)

3. **Update commit_service.py client**:
   - Modify `create_commit()` method signature
   - Add parameter: `ai_governance_metadata: Optional[Dict[str, Any]] = None`
   - Include in payload if provided
   - Backward compatible (parameter is optional)

4. **Update W9 PRManager worker**:
   - Before calling `commit_client.create_commit()`:
     - Check for approval marker: `.git/AI_BRANCH_APPROVED`
     - If exists, read approval source and timestamp
     - Build `ai_governance_metadata` object
   - Pass metadata to `create_commit()` call
   - If approval marker missing and not offline mode:
     - Log warning
     - Proceed without metadata (will be rejected by service)
   - In offline mode: skip check (offline bundles are reviewed manually)

5. **Update spec document**:
   - Add section: "AI Governance Integration (AG-001)"
   - Document `ai_governance_metadata` field
   - Document error code `AG001_APPROVAL_REQUIRED`
   - Document that field will be required in v2 API

**Acceptance Criteria**:
- Schema validates with new `ai_governance_metadata` field (optional)
- Stub service rejects commits without approval metadata (403 + AG001_APPROVAL_REQUIRED)
- Stub service accepts commits with valid approval metadata
- Client sends metadata when provided
- W9 PRManager collects approval from marker file
- Spec document updated with requirement

**Test Commands**:
```bash
# Test 1: Schema validation
python scripts/validate_schemas.py
# Expected: All schemas pass validation

# Test 2: Stub service rejects missing approval
# Start stub service in terminal 1:
python scripts/stub_commit_service.py --port 4320

# In terminal 2:
curl -X POST http://localhost:4320/v1/commit \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test-token" \
  -H "Idempotency-Key: test-key-123" \
  -d '{
    "schema_version": "1.0",
    "run_id": "test-run",
    "idempotency_key": "test-key-123",
    "repo_url": "https://github.com/test/repo",
    "base_ref": "main",
    "branch_name": "test-branch",
    "allowed_paths": ["/test"],
    "commit_message": "Test",
    "commit_body": "Test body",
    "patch_bundle": {"schema_version": "1.0", "files": []}
  }'
# Expected: 403 with error code AG001_APPROVAL_REQUIRED

# Test 3: Stub service accepts with approval
curl -X POST http://localhost:4320/v1/commit \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test-token" \
  -H "Idempotency-Key: test-key-456" \
  -d '{
    "schema_version": "1.0",
    "run_id": "test-run",
    "idempotency_key": "test-key-456",
    "repo_url": "https://github.com/test/repo",
    "base_ref": "main",
    "branch_name": "test-branch",
    "allowed_paths": ["/test"],
    "commit_message": "Test",
    "commit_body": "Test body",
    "patch_bundle": {"schema_version": "1.0", "files": []},
    "ai_governance_metadata": {
      "ag001_approval": {
        "approved": true,
        "approval_source": "interactive-dialog",
        "timestamp": "2026-02-02T12:00:00Z",
        "approver": "test-user"
      }
    }
  }'
# Expected: 200 with commit SHA

# Test 4: Client integration test
# Create test script that uses CommitServiceClient
# Verify metadata is sent correctly

# Test 5: W9 integration test
# Run W9 PRManager in test mode
# Verify it collects approval from marker file
```

**Rollback Procedure**:
- Restore all modified files from git
- Re-run schema validation
- Restart stub service with original code

---

## Risk Mitigation

### Risk 1: Hook installation breaks on Windows
**Mitigation**: Test on Windows Git Bash, use `Path` library for cross-platform paths

### Risk 2: Schema change breaks existing tests
**Mitigation**: Make field optional initially, run full test suite after change

### Risk 3: Stub service change breaks W9 tests
**Mitigation**: Update W9 tests to send approval metadata, add configuration flag to disable check

### Risk 4: Bypass logging fills disk
**Mitigation**: Log to `.git/` directory (excluded from commits), document cleanup procedure

---

## Success Criteria

All tasks (A1, A2, A3) must meet:
1. Acceptance criteria met and verified
2. Test commands run successfully with expected output
3. No regressions in existing functionality
4. Code follows repository style (ruff format passes)
5. Evidence collected for all changes

---

## Timeline

- Task A1: 2 hours (hook installation automation)
- Task A2: 1 hour (remove bypass)
- Task A3: 4 hours (commit service validation)
- Testing & Evidence: 1 hour
- Documentation & Self-Review: 1 hour

**Total Estimated Time**: 9 hours
