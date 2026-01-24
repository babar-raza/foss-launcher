# BLOCKER Artifacts

**Created**: 2026-01-23
**Agent**: hardening-agent
**Run**: run_20260123_strict_compliance

---

## Purpose

These BLOCKER artifacts document incomplete guarantees that prevent marking the mission as "complete" per the binding contract:

> "If any guarantee is partial/stub/deferred:
> - Create BLOCKER artifacts (per repo issue schema) and mark status BLOCKED."

---

## BLOCKER Summary

| Issue ID | Guarantee | Severity | Status |
|----------|-----------|----------|--------|
| BLOCKER-D-network-runtime-enforcement | D (Network Egress) | blocker | OPEN |
| BLOCKER-E-secrets-scanner | E (Secret Hygiene) | blocker | OPEN |
| BLOCKER-F-budget-config | F (Budget/Circuit Breakers) | blocker | OPEN |
| BLOCKER-G-change-budget | G (Change Budget) | blocker | OPEN |
| BLOCKER-J-subprocess-wrapper | J (No Untrusted Exec) | blocker | OPEN |
| BLOCKER-L-rollback-contract | L (Rollback/Recovery) | blocker | OPEN |

**Total**: 6 BLOCKERS

---

## Guarantee Implementation Status

### ✅ Fully Implemented (7/12)
- **A**: Input Immutability (Pinned SHAs) - Gate J PASS
- **B**: Hermetic Execution - Path validation + 23 tests
- **C**: Supply-Chain Pinning - Gate K PASS
- **H**: CI Parity - Gate Q FAIL (fixable: CI missing `make install-uv`)
- **I**: Non-Flaky Tests - pytest-env + determinism tests
- **K**: Version Locking - Gate P PASS (all 39 taskcards)
- **E** (partial): False pass prevention implemented

### ⚠️ Partially Implemented (3/12)
- **D**: Network allowlist file exists (Gate N PASS) but no runtime enforcement
- **E**: False pass prevention + placeholder gate done, secrets scanner stub
- **J**: No eval/exec verified, but subprocess wrapper not implemented

### ❌ Not Implemented (2/12)
- **F**: Budget/circuit breakers - Gate O stub
- **G**: Change budget - No gate or implementation
- **L**: Rollback contract - No gate or implementation

---

## BLOCKER Details

### BLOCKER-D-network-runtime-enforcement

**Guarantee**: D (Network Egress Allowlist)
**Status**: PARTIAL

**What exists**:
- ✅ config/network_allowlist.yaml
- ✅ Gate N (validate_network_allowlist.py) validates file exists
- ✅ Spec defines requirement

**What's missing**:
- ❌ Runtime enforcement in network clients
- ❌ validate_host() called before all network requests
- ❌ PolicyViolationError raised for unauthorized hosts

**Suggested fix**:
1. Create src/launch/util/network_policy.py
2. Update all clients (telemetry, commit service, LLM, GitHub)
3. Add comprehensive tests

---

### BLOCKER-E-secrets-scanner

**Guarantee**: E (Secret Hygiene / No False Passes)
**Status**: PARTIAL

**What exists**:
- ✅ False pass prevention in cli.py (NOT_IMPLEMENTED gates marked failed)
- ✅ Gate M (placeholder detection) implemented
- ✅ Spec defines requirement

**What's missing**:
- ❌ Full secrets scanner (Gate L is stub)
- ❌ Pattern detection for API keys, tokens, passwords
- ❌ Scanning of runs/**/logs/, runs/**/reports/, runs/**/artifacts/

**Suggested fix**:
1. Implement full secrets scanner in tools/validate_secrets_hygiene.py
2. Define patterns (ghp_*, Bearer tokens, API keys, env vars)
3. Add comprehensive tests

---

### BLOCKER-F-budget-config

**Guarantee**: F (Budget / Circuit Breakers)
**Status**: NOT IMPLEMENTED

**What exists**:
- ✅ Gate O stub (explicitly fails)
- ✅ Spec defines requirement

**What's missing**:
- ❌ Budget fields in run_config.schema.json
- ❌ Gate O validation of budget fields
- ❌ Runtime budget tracking (max_runtime_s, max_llm_calls, etc.)
- ❌ Budget enforcement (raise BudgetExceededError)
- ❌ Circuit breakers for external services

**Suggested fix**:
1. Extend run_config schema with budgets object
2. Implement Gate O validation
3. Create budget_tracker.py in orchestrator
4. Add runtime enforcement
5. Add comprehensive tests

---

### BLOCKER-G-change-budget

**Guarantee**: G (Change Budget / Minimal-Diff Discipline)
**Status**: NOT IMPLEMENTED

**What exists**:
- ✅ Spec defines requirement

**What's missing**:
- ❌ max_files_changed field in config
- ❌ max_lines_per_file field in config
- ❌ Gate to validate config has these fields
- ❌ Runtime change tracking
- ❌ Change budget enforcement

**Suggested fix**:
1. Extend budget config with change limits
2. Create Gate S (validate_change_budget.py)
3. Create change_tracker.py in orchestrator
4. Add runtime enforcement
5. Add comprehensive tests

---

### BLOCKER-J-subprocess-wrapper

**Guarantee**: J (No Execution of Untrusted Repo Code)
**Status**: PARTIAL

**What exists**:
- ✅ Gate R stub (explicitly fails)
- ✅ No eval/exec in src/launch/** (verified)
- ✅ Spec defines requirement

**What's missing**:
- ❌ Subprocess wrapper with cwd validation
- ❌ Runtime check: cwd never in RUN_DIR/work/repo/
- ❌ PolicyViolationError for cwd violations
- ❌ Gate R validation of subprocess usage

**Suggested fix**:
1. Create src/launch/util/subprocess.py with safe_subprocess()
2. Implement cwd boundary validation
3. Update Gate R to scan for direct subprocess usage
4. Add comprehensive tests

---

### BLOCKER-L-rollback-contract

**Guarantee**: L (Rollback / Recovery Contract)
**Status**: NOT IMPLEMENTED

**What exists**:
- ✅ Spec defines requirement

**What's missing**:
- ❌ Pre-run snapshot mechanism
- ❌ Rollback API (restore previous state)
- ❌ Gate to validate rollback capability
- ❌ CLI --rollback flag
- ❌ Integration with orchestrator

**Suggested fix**:
1. Create src/launch/util/snapshot.py
2. Create Gate T (validate_rollback_capability.py)
3. Update orchestrator to create snapshots before writes
4. Add CLI rollback command
5. Add comprehensive tests

---

## Impact on Mission Status

**Previous claim**: "Mission Complete ✅" and "production-ready"

**Actual status**: **BLOCKED**

**Reason**: 6 BLOCKERS prevent claiming mission complete per binding contract

**Contract requirement**:
> "You MUST NOT call the mission 'complete' unless:
> - ALL required guarantees are binding+enforced+tested, AND
> - validate_swarm_ready.py passes with exit code 0."

**Current state**:
- ❌ validate_swarm_ready.py: exit code 1 (6/20 gates failed)
- ❌ 5 guarantees incomplete (D partial, E partial, F, G, J partial, L)

**Required action**: Resolve all BLOCKERs OR accept partial implementation status

---

## Resolution Paths

### Option 1: Complete all BLOCKERs (recommended)
- Implement all 6 missing features
- Re-run validate_swarm_ready.py
- Verify exit code 0
- Then claim "Mission Complete"

### Option 2: Accept partial status (alternative)
- Document 7/12 guarantees fully implemented
- Mark mission as "BLOCKED" not "COMPLETE"
- Provide clear implementation roadmap in BLOCKERs
- Claim "Substantial progress" not "production-ready"

### Option 3: Prioritize critical BLOCKERs (pragmatic)
- Fix high-priority security BLOCKERs (E, J)
- Fix resource limit BLOCKERs (F, G)
- Defer nice-to-have features (D runtime, L rollback)
- Re-evaluate mission status

---

## Files Reference

All BLOCKER artifacts conform to `specs/schemas/issue.schema.json`:

```
BLOCKERS/
├── README.md (this file)
├── BLOCKER-D-network-runtime-enforcement.json
├── BLOCKER-E-secrets-scanner.json
├── BLOCKER-F-budget-config.json
├── BLOCKER-G-change-budget.json
├── BLOCKER-J-subprocess-wrapper.json
└── BLOCKER-L-rollback-contract.json
```

Each JSON file includes:
- issue_id: Unique identifier
- gate: Associated gate name
- severity: "blocker"
- message: Detailed description
- files: Related files
- suggested_fix: Implementation guidance
- status: "OPEN"
