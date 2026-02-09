---
id: "TC-934"
title: "Fix Gate R: Replace unsafe subprocess call with approved wrapper"
owner: "supervisor-agent"
status: "In-Progress"
created: "2026-02-03"
updated: "2026-02-03"
spec_ref: "35fb9356c1e277ff05be2fbf60d59111ca2dece6"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
evidence_required:
  - reports/agents/<agent>/TC-934/report.md
  - reports/agents/<agent>/TC-934/self_review.md
  - "validate_swarm_ready.py Gate R PASS after subprocess wrapper fix"
depends_on: []
allowed_paths:
  - "plans/taskcards/TC-934_fix_gate_r_subprocess.md"
  - "src/launch/workers/w7_validator/gates/gate_u_taskcard_authorization.py"
  - "plans/taskcards/INDEX.md"
  - "plans/taskcards/STATUS_BOARD.md"
  - "reports/agents/**/TC-934/**"
---

# Taskcard TC-934 — Fix Gate R: Replace unsafe subprocess call with approved wrapper

## Objective
Replace direct subprocess.run() call in gate_u_taskcard_authorization.py with the approved subprocess wrapper (src/launch/util/subprocess.py) to pass Gate R (Untrusted code policy).

## Context
Gate R reports:
```
WARN: Direct subprocess calls detected (should use wrapper):
  src\launch\workers\w7_validator\gates\gate_u_taskcard_authorization.py
    Line 31: result = subprocess.run(
```

The repository already has an approved subprocess wrapper at src/launch/util/subprocess.py. All subprocess operations must use this wrapper to enforce cwd validation and security policies per specs/09_validation_gates.md Gate R.

## Scope

### In scope
- Replace direct subprocess.run() call at line 31 of gate_u_taskcard_authorization.py
- Import and use the approved wrapper from src/launch/util/subprocess.py
- Verify Gate R passes after fix

### Out of scope
- Modifying the subprocess wrapper implementation
- Changing other gate implementations
- Refactoring gate logic beyond subprocess replacement

## Inputs
1. Current gate_u_taskcard_authorization.py with unsafe subprocess call (line 31)
2. Approved subprocess wrapper: src/launch/util/subprocess.py
3. Gate R validation output showing the violation

## Outputs
1. Updated gate_u_taskcard_authorization.py using approved wrapper
2. Gate R validation passing

## Required spec references
- specs/09_validation_gates.md (Gate R: Untrusted code policy)
- src/launch/util/subprocess.py (approved wrapper implementation)

## Allowed paths

- `plans/taskcards/TC-934_fix_gate_r_subprocess.md`
- `src/launch/workers/w7_validator/gates/gate_u_taskcard_authorization.py`
- `plans/taskcards/INDEX.md`
- `plans/taskcards/STATUS_BOARD.md`
- `reports/agents/**/TC-934/**`## Implementation steps

### Step 1: Read current gate implementation
Read gate_u_taskcard_authorization.py to understand the context of the subprocess call at line 31.

### Step 2: Read subprocess wrapper
Read src/launch/util/subprocess.py to understand the approved wrapper API.

### Step 3: Replace subprocess call
Update gate_u_taskcard_authorization.py:
- Import the approved wrapper function from src.launch.util.subprocess
- Replace subprocess.run() call with the wrapper equivalent
- Preserve all existing functionality (command, arguments, error handling)

### Step 4: Verify Gate R passes
Run validation:
```bash
.venv\Scripts\python.exe tools\validate_swarm_ready.py
```

Save output to: runs/tc931_a2bc_then_er_then_vfv_20260203_000521/logs/validate_after_tc934.txt

Expected:
- Gate R: PASS (no unsafe subprocess calls)
- 21/21 gates PASS

## Deliverables
1. Updated gate_u_taskcard_authorization.py using approved wrapper
2. Validation log showing Gate R PASS
3. All 21 gates passing

## Acceptance checks
- [ ] gate_u_taskcard_authorization.py does NOT use direct subprocess.run()
- [ ] gate_u_taskcard_authorization.py imports approved wrapper
- [ ] gate_u_taskcard_authorization.py uses wrapper for subprocess operations
- [ ] Gate R PASS (zero unsafe subprocess calls)
- [ ] 21/21 gates PASS
- [ ] No regressions in pytest suite

## E2E verification
After implementing the fix, run:
```bash
.venv\Scripts\python.exe tools\validate_swarm_ready.py
```

Expected artifacts:
- Updated gate_u_taskcard_authorization.py
- Validation log showing Gate R PASS

Expected outcome:
- Gate R transitions from FAIL → PASS
- All 21 gates PASS
- No unsafe subprocess calls detected

## Integration boundary proven
**Upstream:** TC-932 (overlap resolution) → TC-934 (subprocess policy)
**Downstream:** TC-934 → Full validation PASS → VFV runs enabled
**Proven by:** validate_swarm_ready showing 21/21 gates PASS after TC-934 implementation

## Risk Assessment
- **Low risk:** Minimal code change, replacing one function call with another
- **Validation:** Gate R checks for unsafe calls, pytest ensures no regressions
- **Rollback:** Git revert TC-934 commit if issues arise

## Failure modes

### Failure mode 1: Approved wrapper has different API signature than subprocess.run()
**Detection:** ImportError or TypeError when calling wrapper function; Gate U test failures
**Resolution:** Read wrapper implementation to understand correct API; adjust call signature (args, kwargs) to match wrapper; test with sample command
**Spec/Gate:** src/launch/util/subprocess.py (wrapper API documentation)

### Failure mode 2: Wrapper enforces stricter security policies that break gate logic
**Detection:** Gate U fails to execute git commands; validation errors in taskcard authorization checks
**Resolution:** Review wrapper's cwd validation and allowed command policies; adjust gate logic if needed to comply with security requirements; consider relaxing wrapper policy if too strict for validation context
**Spec/Gate:** specs/09_validation_gates.md Gate R (subprocess security policy)

### Failure mode 3: Other files still use direct subprocess calls, Gate R still fails
**Detection:** Gate R validation still reports unsafe subprocess calls after fix
**Resolution:** Use grep to find all remaining subprocess.run/call/Popen usages; create follow-up taskcards to fix remaining violations; update TC-934 scope if multiple files need fixing
**Spec/Gate:** specs/09_validation_gates.md Gate R (comprehensive subprocess wrapper enforcement)

## Task-specific review checklist
1. [ ] subprocess.run() call removed from line 31 of gate_u_taskcard_authorization.py
2. [ ] Approved wrapper imported from src.launch.util.subprocess
3. [ ] Wrapper function call preserves all original functionality (command execution, output capture, error handling)
4. [ ] Gate U tests still pass with wrapper implementation
5. [ ] Gate R validation shows zero unsafe subprocess calls
6. [ ] pytest suite passes with no regressions in validation gates
7. [ ] Wrapper call includes proper error handling and logging
8. [ ] No other direct subprocess calls introduced during refactoring

## Self-review
- [ ] Taskcard follows required structure (all required sections present)
- [ ] allowed_paths covers all files to be modified
- [ ] Acceptance criteria are concrete and testable
- [ ] E2E verification includes specific command and expected outcome
- [ ] YAML frontmatter complete (all required keys present, spec_ref is commit SHA)
- [ ] Spec references accurate and exist in repo
- [ ] Integration boundary specifies upstream/downstream dependencies explicitly
- [ ] Implementation steps are concrete and executable
- [ ] Deliverables list tangible outputs
