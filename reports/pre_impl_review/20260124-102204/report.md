# Pre-Implementation Hardening Report

## Run Metadata

- **Run Timestamp**: 2026-01-24 10:22:04
- **Host OS**: Windows (win32)
- **Python Version**: 3.13.2 (exceeds >=3.12 requirement)
- **Git Branch**: chore/pre_impl_readiness_sweep
- **Git Commit**: f48fc5d (chore(gitignore): ignore local archive)

## Repo Rules Discovered

### Write-Fence / Allowed Paths Policy
**Source**: [plans/taskcards/00_TASKCARD_CONTRACT.md](../../../plans/taskcards/00_TASKCARD_CONTRACT.md)

**Core Rule** (line 8-9):
> **Write fence:** the taskcard MUST enumerate Allowed paths. Agents MAY ONLY modify files under Allowed paths.

**Critical Clarifications** (line 16-20):
- `allowed_paths` lists define which files may be **MODIFIED or CREATED**
- Reading, importing, and using existing code is **ALWAYS allowed** for all taskcards
- Do NOT include shared libraries in `allowed_paths` just because you need to import/use them

**Shared Library Boundaries** (lines 22-31, ZERO TOLERANCE):
- `src/launch/io/**` → TC-200 (owner only)
- `src/launch/util/**` → TC-200 (owner only)
- `src/launch/models/**` → TC-250 (owner only)
- `src/launch/clients/**` → TC-500 (owner only)
- Validation tooling (`validate_taskcards.py`, `validate_swarm_ready.py`) rejects violations
- No "acceptable overlap" exceptions permitted

### RUN_DIR Isolation
**Source**: [specs/29_project_repo_structure.md](../../../specs/29_project_repo_structure.md)

**Binding Rules** (lines 130-136):
1. **Isolation**: Workers MUST NOT read or write outside `RUN_DIR` (except for reading installed tools and env vars)
2. **Atomic writes**: JSON artifacts are written to temp file and atomically renamed
3. **Worktree safety**:
   - Only LinkerAndPatcher (W6) and Fixer (W8) may write to `RUN_DIR/work/site/`
   - All writes MUST be refused if outside `run_config.allowed_paths`

### Strict Compliance Guarantees (A-L)
**Source**: [specs/34_strict_compliance_guarantees.md](../../../specs/34_strict_compliance_guarantees.md)

**12 Binding Guarantees** (lines 36-357):
- **A** Input immutability (pinned commit SHAs)
- **B** Hermetic execution boundaries
- **C** Supply-chain pinning
- **D** Network egress allowlist
- **E** Secret hygiene/redaction
- **F** Budget limits/circuit breakers
- **G** Change-budget/minimal-diff
- **H** CI parity/single entrypoint
- **I** Non-flaky tests
- **J** No execution of untrusted code
- **K** Spec/taskcard version locking
- **L** Rollback/recovery contract

### Validation Gates
**Source**: [specs/09_validation_gates.md](../../../specs/09_validation_gates.md)

**Strict Compliance Gates** (lines 193-211):
- **Gate J**: Pinned refs policy (Guarantee A)
- **Gate K**: Frozen deps / lock integrity (Guarantee C)
- **Gate L**: Secrets scan (Guarantee E) - **MARKED AS STUB in validate_swarm_ready.py**
- **Gate M**: No placeholders in production paths
- **Gate N**: Network allowlist contract (Guarantee D)
- **Gate O**: Budget config contract (Guarantees F, G) - **MARKED AS STUB in validate_swarm_ready.py**
- **Gate P**: Taskcard version-lock compliance (Guarantee K)
- **Gate Q**: CI parity (Guarantee H)
- **Gate R**: Untrusted-code non-execution policy (Guarantee J) - **MARKED AS STUB in validate_swarm_ready.py**

### Preflight Mandatory
**Source**: [plans/taskcards/00_TASKCARD_CONTRACT.md](../../../plans/taskcards/00_TASKCARD_CONTRACT.md) (lines 40-45)

Before starting ANY implementation work:
1. Run: `make install` (or pip editable install)
2. Run: `python tools/validate_swarm_ready.py`
3. All gates must pass before proceeding (no exceptions)

### Gate Execution Order (Discovered)
**Source**: [tools/validate_swarm_ready.py](../../../tools/validate_swarm_ready.py)

Complete gate sequence (lines 213-359):
- Gate 0: Virtual environment policy (.venv enforcement)
- Gate A1: Spec pack validation
- Gate A2: Plans validation (zero warnings)
- Gate B: Taskcard validation + path enforcement
- Gate C: Status board generation
- Gate D: Markdown link integrity
- Gate E: Allowed paths audit (zero violations + zero critical overlaps)
- Gate F: Platform layout consistency (V2)
- Gate G: Pilots contract validation
- Gate H: MCP contract validation
- Gate I: Phase report integrity
- Gate J: Pinned refs policy (Guarantee A)
- Gate K: Supply chain pinning (Guarantee C)
- Gate L: Secrets hygiene (Guarantee E) - **STUB**
- Gate M: No placeholders in production
- Gate N: Network allowlist (Guarantee D)
- Gate O: Budget config (Guarantees F/G) - **STUB**
- Gate P: Taskcard version locks (Guarantee K)
- Gate Q: CI parity (Guarantee H)
- Gate R: Untrusted code policy (Guarantee J) - **STUB**
- Gate S: Windows reserved names prevention

### For Pre-Implementation Hardening Agent
**Agent-Specific Constraints**:
- This agent operates in `reports/pre_impl_review/<TS>/` folder
- No write-fence restrictions for report generation (reports are evidence, not production code)
- MUST respect write-fence for any production code/spec changes
- MUST create CHANGE_REQUEST.md if required changes are outside allowed area

## Gate Execution Summary

| Gate | Name | Status | Evidence File |
|------|------|--------|---------------|
| (to be populated after gate discovery) ||||

## Work Items Completed

(To be filled as work progresses)

## Changes Made

(To be filled with links to requirements, tests, and evidence)

## Final Status

(To be determined: GO / NO-GO)
