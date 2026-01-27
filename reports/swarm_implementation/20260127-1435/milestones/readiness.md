# Swarm Implementation Readiness Decision

**Date**: 2026-01-27
**Run**: 20260127-1435
**Supervisor**: SUPERVISOR
**Branch**: gpt-reviewed
**HEAD**: c8dab0cc1845996f5618a8f0f65489e1b462f06c

---

## Summary

**DECISION**: READY TO PROCEED with explicit batch execution blockers

All preflight gates pass. 41 taskcards are ready for implementation. One open question (OQ-BATCH-001) blocks batch execution semantics but does not prevent implementing single-run execution paths.

---

## Preflight Status

### ✅ All Gates Passed

Ran `python tools/validate_swarm_ready.py` - all 21 gates passed:

- Gate 0: Virtual environment policy (.venv enforcement)
- Gate A1: Spec pack validation
- Gate A2: Plans validation (zero warnings)
- Gate B: Taskcard validation + path enforcement
- Gate C: Status board generation
- Gate D: Markdown link integrity
- Gate E: Allowed paths audit (zero violations + zero critical overlaps)
- Gate F: Platform layout consistency (V2)
- Gate G: Pilots contract (canonical path consistency)
- Gate H: MCP contract (quickstart tools in specs)
- Gate I: Phase report integrity (gate outputs + change logs)
- Gate J: Pinned refs policy (Guarantee A: no floating branches/tags)
- Gate K: Supply chain pinning (Guarantee C: frozen deps)
- Gate L: Secrets hygiene (Guarantee E: secrets scan)
- Gate M: No placeholders in production (Guarantee E)
- Gate N: Network allowlist (Guarantee D: allowlist exists)
- Gate O: Budget config (Guarantees F/G: budget config)
- Gate P: Taskcard version locks (Guarantee K)
- Gate Q: CI parity (Guarantee H: canonical commands)
- Gate R: Untrusted code policy (Guarantee J: parse-only)
- Gate S: Windows reserved names prevention

Full output: `reports/swarm_implementation/20260127-1435/milestones/preflight.md`

### ✅ Taskcards Ready

- **Total**: 41 taskcards
- **Status**: 39 Ready, 2 Done (TC-601, TC-602)
- **Contract**: All taskcards validated against `plans/taskcards/00_TASKCARD_CONTRACT.md`
- **Dependencies**: All `depends_on` relationships are valid
- **Allowed paths**: All paths exist and have no critical overlaps (single-writer areas protected)

### ✅ Infrastructure Ready

- **Specs**: All specs in `specs/**` validated
- **Templates**: Agent report and self-review templates exist in `reports/templates/`
- **Validators**: All validation scripts operational
- **Forensics**: Repo snapshot captured in `reports/forensics/`
- **Environment**: `.venv` compliant with specs/00_environment_policy.md

---

## Known Blocker: OQ-BATCH-001 (Batch Execution Semantics)

### Issue

From `OPEN_QUESTIONS.md`:

> **OQ-BATCH-001**: Batch execution (queue many runs) semantics
> **Question**: `specs/00_overview.md` requires batch execution (queue many runs) with bounded concurrency, but what is the exact batch input shape and execution contract?
> **Status**: OPEN

### Impact

Blocks deterministic implementation of:
- Batch input formats (directory of run_configs, batch manifest, CLI args)
- Scheduling/ordering rules for deterministic batch execution
- Resume/checkpoint artifacts for batch runs
- CLI + MCP endpoints for batch execution

### Affected Taskcards

- **TC-300** (Orchestrator graph wiring and run loop) - single-run execution path is implementable; batch orchestration requires OQ-BATCH-001 resolution
- **TC-530** (CLI entrypoints and runbooks) - single-run CLI is implementable; batch CLI commands require OQ-BATCH-001
- **TC-510/TC-511/TC-512** (MCP endpoints) - single-run MCP tools are implementable; batch MCP endpoints require OQ-BATCH-001

### Safe Implementation Strategy

**We will proceed with the following constraints**:

1. **Implement single-run execution paths** in TC-300, TC-530, TC-510/TC-511/TC-512
   - Focus on `launch_run` (single run_config)
   - Defer batch queue management, bounded concurrency, batch resume

2. **Mark batch surfaces with blockers** when encountered
   - If a taskcard requires guessing batch semantics, STOP and file blocker issue
   - Document batch surfaces as "NOT IMPLEMENTED - BLOCKED BY OQ-BATCH-001"

3. **Safe architecture**
   - Design orchestrator, CLI, and MCP to be batch-extensible (but don't implement batch logic)
   - Use TODOs or BLOCKED markers where batch code would go

4. **Resume without batch implemented**
   - Single-run determinism, checkpointing, and resume are fully implementable
   - Batch resume requires OQ-BATCH-001

---

## What Is Fully Ready (No Blockers)

The following areas are **fully specified and ready for implementation**:

### Wave 1: Foundation (Sequential)
- **TC-100**: Bootstrap repo ✅
- **TC-200**: Schemas and IO foundations ✅
- **TC-201**: Emergency mode flag ✅
- **TC-250**: Shared libraries governance ✅
- **TC-300**: Orchestrator (single-run path) ✅ (batch deferred)
- **TC-500**: Clients & Services ✅

### Wave 2: Workers (Parallel after Wave 1)
- **W1 (TC-400–404)**: RepoScout ✅
- **W2 (TC-410–413)**: FactsBuilder ✅
- **W3 (TC-420–422)**: SnippetCurator ✅
- **W4–W6 (TC-430/440/450)**: IAPlanner → SectionWriter → Patcher ✅

### Wave 3: Validation + Fix + PR
- **TC-460**: Validator ✅
- **TC-570/TC-571**: Validation gates ✅
- **TC-470**: Fixer ✅
- **TC-480**: PRManager ✅

### Wave 4: MCP + CLI + Pilots + Harnesses
- **TC-510/TC-511/TC-512**: MCP (single-run tools) ✅ (batch deferred)
- **TC-530**: CLI (single-run commands) ✅ (batch deferred)
- **TC-520/TC-522/TC-523**: Pilots ✅
- **TC-540/TC-550**: Hugo config awareness ✅
- **TC-560**: Determinism harness ✅
- **TC-580**: Observability ✅
- **TC-590**: Security ✅
- **TC-600**: Failure recovery ✅

---

## Execution Plan

### Phase 1: Wave 1 (Foundation)
Execute taskcards **sequentially**:
1. TC-100 (Bootstrap)
2. TC-200 (Schemas/IO)
3. TC-201 (Emergency mode)
4. TC-250 (Models governance)
5. TC-300 (Orchestrator - single-run path only)
6. TC-500 (Clients)

Checkpoint after Wave 1 completion.

### Phase 2: Wave 2 (Workers)
Execute worker integrators + subtasks in **parallel groups** (respecting dependencies):
- W1 (TC-401→402→403→404 → TC-400)
- W2 (TC-411→412→413 → TC-410)
- W3 (TC-421→422 → TC-420)
- W4–W6 (TC-430 → TC-440 → TC-450)

Checkpoint after Wave 2 completion.

### Phase 3: Wave 3 (Validation + Fix + PR)
Execute **sequentially**:
1. TC-460 (Validator)
2. TC-570 + TC-571 (Validation gates)
3. TC-470 (Fixer)
4. TC-480 (PRManager)

Checkpoint after Wave 3 completion.

### Phase 4: Wave 4 (MCP + CLI + Pilots)
Execute in **parallel groups**:
- MCP: TC-510 → TC-511 + TC-512 (single-run tools only)
- CLI: TC-530 (single-run commands only)
- Pilots: TC-520 → TC-522 + TC-523
- Hugo: TC-540 + TC-550
- Harnesses: TC-560 + TC-580 + TC-590 + TC-600

Checkpoint after Wave 4 completion.

---

## Evidence Requirements

Every taskcard MUST produce:
- `reports/agents/<agent>/<TC-ID>/report.md`
- `reports/agents/<agent>/<TC-ID>/self_review.md` (using `reports/templates/self_review_12d.md`)

Acceptance checks (per taskcard) MUST be run and outputs recorded in report.md.

---

## Blocker Policy

If ambiguity forces guessing:
1. STOP that path immediately
2. Write blocker issue JSON: `reports/agents/<agent>/<TC-ID>/blockers/<timestamp>_<slug>.issue.json`
3. Validate against `specs/schemas/issue.schema.json`
4. Update `OPEN_QUESTIONS.md` and `reports/swarm_implementation/20260127-1435/blockers_index.md`
5. Mark taskcard as Blocked in `swarm_state.json`
6. Continue with other taskcards

---

## Conclusion

**READY TO PROCEED** with:
- All 41 taskcards validated and dependency-sorted
- All preflight gates passing
- Explicit strategy for OQ-BATCH-001 (defer batch surfaces, implement single-run paths)
- Clear blocker policy for future ambiguities

**Next Step**: Build queue.md and start Wave 1 with TC-100.

---

**Approved**: SUPERVISOR
**Timestamp**: 2026-01-27 (Asia/Karachi)
