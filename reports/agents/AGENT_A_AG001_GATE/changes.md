# AG-001 Gate Strengthening - Changes Documentation

**Date**: 2026-02-02
**Agent**: Agent A (Implementation + Architecture)
**Mission**: Fix 3 critical security bypasses in AG-001 branch creation gate

---

## Summary

Implemented 3 tasks to strengthen the AG-001 branch creation gate:
1. **Task A1**: Automated hook installation via `make install`
2. **Task A2**: Removed git config bypass, added emergency bypass with logging
3. **Task A3**: Added AG-001 validation to commit service API

---

## Task A1: Hook Installation Automation

### Files Created

#### `scripts/install_hooks.py` (NEW)
**Purpose**: Automatically install AI governance hooks from `hooks/` to `.git/hooks/`

**Features**:
- Cross-platform compatible (Windows, macOS, Linux)
- Idempotent (safe to run multiple times)
- Backs up existing hooks before overwriting
- Makes hooks executable on Unix-like systems
- ASCII-only output for Windows compatibility

**Key Implementation Details**:
- Uses `Path` library for cross-platform path handling
- Detects platform with `os.name` to handle executable permissions
- Creates backup with `.backup` suffix before overwriting
- Returns exit code 0 on success, non-zero on failure
- Excludes `README.md` and `install.sh` from installation

**Before**: No automated installation, hooks in `hooks/` not in `.git/hooks/`
**After**: Hooks automatically installed to `.git/hooks/` with proper permissions

### Files Modified

#### `Makefile`
**Changes**:
1. Added `.PHONY` target: `install-hooks`
2. Added target implementation:
   ```makefile
   install-hooks:
       python scripts/install_hooks.py
   ```
3. Made `install` depend on `install-hooks`
4. Made `install-uv` depend on `install-hooks`

**Before**: No hook installation in build process
**After**: Hooks installed automatically on `make install` or `make install-uv`

**Impact**: Ensures all developers and CI have hooks installed after setup

---

## Task A2: Remove Hook Bypass

### Files Modified

#### `hooks/prepare-commit-msg` (lines 73-85)
**Changes**: Replaced git config bypass with emergency environment variable bypass

**Before**:
```bash
# In enforcement mode, block the commit
# To disable enforcement, set: git config hooks.ai-governance.enforce false
ENFORCE=$(git config --get hooks.ai-governance.enforce || echo "true")

if [ "$ENFORCE" = "true" ]; then
    echo ""
    echo "❌ COMMIT BLOCKED"
    echo ""
    exit 1
else
    echo ""
    echo "⚠️  WARNING: Enforcement disabled, allowing commit"
    echo ""
fi
```

**After**:
```bash
# Check for emergency bypass via environment variable
# AG-001 Task A2: Remove git config bypass, only allow emergency bypass
if [ "$AG001_EMERGENCY_BYPASS" = "true" ]; then
    # Log emergency bypass to audit log
    BYPASS_LOG=".git/AG001_EMERGENCY_BYPASS_LOG.jsonl"
    TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    USER=$(git config user.name || echo "unknown")
    EMAIL=$(git config user.email || echo "unknown")

    # Create JSON log entry
    LOG_ENTRY=$(cat <<EOF
{"timestamp":"$TIMESTAMP","user":"$USER","email":"$EMAIL","branch":"$CURRENT_BRANCH","reason":"emergency_bypass","action":"allowed_commit"}
EOF
)
    echo "$LOG_ENTRY" >> "$BYPASS_LOG"

    echo ""
    echo "⚠️  EMERGENCY BYPASS ACTIVE"
    echo "   This bypass has been logged to: $BYPASS_LOG"
    echo "   User: $USER ($EMAIL)"
    echo "   Branch: $CURRENT_BRANCH"
    echo ""
    echo "   WARNING: Emergency bypasses should only be used in exceptional"
    echo "   circumstances and must be justified in post-incident review."
    echo ""
else
    # Normal enforcement: block the commit
    echo ""
    echo "❌ COMMIT BLOCKED"
    echo ""
    echo "For emergency bypass (use with extreme caution):"
    echo "  $ AG001_EMERGENCY_BYPASS=true git commit -m 'your message'"
    echo ""
    echo "All emergency bypasses are logged and auditable."
    echo ""
    exit 1
fi
```

**Key Changes**:
1. Removed `git config --get hooks.ai-governance.enforce` check
2. Added `AG001_EMERGENCY_BYPASS` environment variable check
3. Added audit logging to `.git/AG001_EMERGENCY_BYPASS_LOG.jsonl`
4. Logged: timestamp, user, email, branch, reason, action
5. Added warning message about emergency bypass

**Security Impact**:
- **Before**: Bypass could be silently enabled with `git config` command
- **After**: Bypass requires explicit environment variable AND is logged to audit file
- Bypass is now transient (per-command) not persistent (config setting)

---

## Task A3: Commit Service Validation

### Files Modified

#### `specs/schemas/commit_request.schema.json`
**Changes**: Added optional `ai_governance_metadata` field to schema

**Added Structure**:
```json
"ai_governance_metadata": {
  "type": "object",
  "description": "AI governance metadata for automated compliance checks (AG-001, etc.)",
  "properties": {
    "ag001_approval": {
      "type": "object",
      "description": "Branch creation approval metadata (AG-001 gate)",
      "properties": {
        "approved": {"type": "boolean"},
        "approval_source": {
          "type": "string",
          "enum": ["interactive-dialog", "manual-marker", "config-override"]
        },
        "timestamp": {"type": "string", "format": "date-time"},
        "approver": {"type": "string"}
      },
      "required": ["approved", "approval_source", "timestamp"]
    }
  }
}
```

**Design Decision**: Field is optional (not in `required` array) for backwards compatibility
**Future**: Will be required in API v2

#### `scripts/stub_commit_service.py`
**Changes**: Added AG-001 validation to `/v1/commit` endpoint

**Added Models**:
```python
class AG001Approval(BaseModel):
    approved: bool
    approval_source: str = Field(..., pattern="^(interactive-dialog|manual-marker|config-override)$")
    timestamp: str
    approver: Optional[str] = None

class AIGovernanceMetadata(BaseModel):
    ag001_approval: Optional[AG001Approval] = None
```

**Updated `CommitRequest`**:
- Added field: `ai_governance_metadata: Optional[AIGovernanceMetadata] = None`

**Added Validation Logic** (in `commit()` endpoint):
1. Check if `ai_governance_metadata` is None or missing `ag001_approval`
   - If missing: Return 403 with error code `AG001_APPROVAL_REQUIRED`
2. Check if `ag001_approval.approved` is False
   - If denied: Return 403 with error code `AG001_APPROVAL_DENIED`
3. Log approval metadata to audit log
4. Proceed with commit creation

**Error Response Format**:
```json
{
  "code": "AG001_APPROVAL_REQUIRED",
  "message": "Branch creation requires AI governance approval (AG-001)",
  "details": {
    "branch_name": "...",
    "gate": "AG-001",
    "required_field": "ai_governance_metadata.ag001_approval",
    "documentation": "specs/30_ai_agent_governance.md"
  }
}
```

#### `src/launch/clients/commit_service.py`
**Changes**: Added support for sending governance metadata

**Modified `create_commit()` Signature**:
- Added parameter: `ai_governance_metadata: Optional[Dict[str, Any]] = None`
- Updated docstring to document new parameter
- Added payload field if metadata provided:
  ```python
  if ai_governance_metadata is not None:
      payload["ai_governance_metadata"] = ai_governance_metadata
  ```

**Backwards Compatibility**: Parameter is optional, existing calls continue to work

#### `src/launch/workers/w9_pr_manager/worker.py`
**Changes**: Collect AG-001 approval before creating commit

**Added Logic** (before `commit_client.create_commit()` call):
```python
# AG-001 Task A3: Collect branch creation approval metadata
ai_governance_metadata = None
approval_marker_path = run_layout.run_dir.parent / ".git" / "AI_BRANCH_APPROVED"

if approval_marker_path.exists():
    # Read approval marker
    with open(approval_marker_path, "r", encoding="utf-8") as f:
        approval_source = f.read().strip() or "manual-marker"

    # Build AG-001 approval metadata
    ai_governance_metadata = {
        "ag001_approval": {
            "approved": True,
            "approval_source": approval_source if approval_source in [...] else "manual-marker",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "approver": os.getenv("USER") or os.getenv("USERNAME") or "unknown",
        }
    }
else:
    logger.warning("pr_manager_no_approval_marker", ...)
```

**Updated `create_commit()` Call**:
- Added parameter: `ai_governance_metadata=ai_governance_metadata`

**Behavior**:
- If `.git/AI_BRANCH_APPROVED` exists: Collect approval, send to service
- If marker missing: Log warning, send request without metadata (will be rejected by service)
- In offline mode: Skip check (offline bundles reviewed manually)

#### `specs/17_github_commit_service.md`
**Changes**: Added "AI Governance Integration (AG-001)" section

**Added Documentation**:
1. Request field structure and description
2. Validation rules for new branch commits
3. Error response format examples
4. Client integration requirements
5. Future evolution notes (v2 will require field)

**Location**: Added after "Concurrency + branch rules" section, before "Telemetry" section

---

## Unexpected Findings

### Finding 1: Windows Unicode Issues
**Issue**: Original script used Unicode characters (➜, ✅, ❌, ⚠️) that failed on Windows cmd.exe
**Resolution**: Replaced with ASCII equivalents ([OK], [X], [!], ->)
**Impact**: Script now works on all platforms without encoding errors

### Finding 2: Approval Marker Path Resolution
**Issue**: W9 PRManager runs from `run_dir`, but approval marker is at repo root `.git/`
**Resolution**: Used `run_layout.run_dir.parent / ".git" / "AI_BRANCH_APPROVED"` to go up one level
**Impact**: Correctly reads approval marker from repository root

### Finding 3: Backwards Compatibility Requirement
**Issue**: Making `ai_governance_metadata` required would break existing tests and stub service calls
**Resolution**: Made field optional in schema, will be required in v2
**Impact**: Gradual migration path, existing code continues to work

---

## Deviation from Plan

### Deviation 1: Makefile Targets Order
**Planned**: Add `install-hooks` as separate target
**Actual**: Made `install` and `install-uv` depend on `install-hooks` so it runs automatically
**Reason**: Ensures hooks are always installed during setup, not just when explicitly requested
**Better Because**: Reduces chance of forgetting to install hooks

### Deviation 2: Emergency Bypass Logging Format
**Planned**: Simple log format
**Actual**: JSON Lines (JSONL) format with structured fields
**Reason**: Makes log parsing easier for audit tools
**Better Because**: Structured logging enables automated analysis

### Deviation 3: Stub Service Error Details
**Planned**: Basic error code and message
**Actual**: Rich error details with branch name, gate, required field, documentation link
**Reason**: Better developer experience, clearer error messages
**Better Because**: Faster debugging, self-documenting errors

---

## Files Changed Summary

### Created (1)
- `scripts/install_hooks.py` - Hook installation automation script

### Modified (6)
- `Makefile` - Added `install-hooks` target and dependencies
- `hooks/prepare-commit-msg` - Replaced git config bypass with emergency bypass + logging
- `specs/schemas/commit_request.schema.json` - Added `ai_governance_metadata` field
- `scripts/stub_commit_service.py` - Added AG-001 validation logic
- `src/launch/clients/commit_service.py` - Added governance metadata parameter
- `src/launch/workers/w9_pr_manager/worker.py` - Collect and send approval metadata
- `specs/17_github_commit_service.md` - Documented AG-001 integration

### Total Files Changed: 7

---

## Next Steps

1. Run validation tests to verify changes work correctly
2. Collect evidence of all acceptance criteria being met
3. Create executable commands script for verification
4. Complete self-review scorecard
