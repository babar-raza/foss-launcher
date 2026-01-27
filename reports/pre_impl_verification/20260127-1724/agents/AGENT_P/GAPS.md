# Plans/Taskcards Gaps Report

**Generated**: 2026-01-27
**Auditor**: AGENT_P (Plans/Taskcards & Swarm Readiness Auditor)
**Purpose**: Document all planning and taskcard gaps requiring attention

---

## Gap Summary

**Total Gaps Identified**: 3
**Severity Breakdown**:
- BLOCKER: 0
- WARNING: 0
- INFO: 3 (all expected in pre-implementation phase)

**Overall Assessment**: ✅ **NO BLOCKING GAPS**

All identified gaps are **INFO-level** and reflect the expected state of pre-implementation readiness. No plan deficiencies detected.

---

## P-GAP-001 | INFO | Orchestrator Implementation Not Started (Expected)

**Taskcard**: TC-300 (Orchestrator graph wiring and run loop)
**Spec Authority**:
- `specs/state-graph.md:1-end` (LangGraph state machine transitions)
- `specs/state-management.md:1-end` (state persistence, snapshots, event sourcing)
- `specs/28_coordination_and_handoffs.md:1-end` (orchestrator-to-worker handoff contracts)
- `specs/11_state_and_events.md:1-end` (event log structure)
- `specs/21_worker_contracts.md:1-end` (W1-W9 IO contracts)

**Issue**: Critical orchestrator spec has no implementation artifacts yet

**Evidence**:
- `plans/traceability_matrix.md:22-36`:
  ```markdown
  - specs/state-graph.md
    - **Purpose**: Defines LangGraph state machine transitions for orchestrator
    - **Implement**: TC-300 (Orchestrator graph definition, node transitions, edge conditions)
    - **Validate**: TC-300 (graph smoke tests, transition determinism tests)
    - **Status**: Spec complete, TC-300 not started

  - specs/state-management.md
    - **Purpose**: Defines state persistence, snapshot updates, event log structure
    - **Implement**: TC-300 (state serialization, snapshot creation, event sourcing)
    - **Validate**: TC-300 (determinism tests for state serialization)
    - **Status**: Spec complete, TC-300 not started

  - specs/28_coordination_and_handoffs.md
    - **Purpose**: Defines orchestrator-to-worker handoff contracts and coordination patterns
    - **Implement**: TC-300 (worker orchestration, handoff logic, state transitions)
    - **Validate**: TC-300 (orchestrator integration tests)
    - **Status**: Spec complete, TC-300 not started
  ```

- `plans/taskcards/STATUS_BOARD.md:25`:
  ```markdown
  | TC-300 | Orchestrator graph wiring and run loop | Ready | unassigned | TC-200 | 5 paths | ... |
  ```

- `plans/taskcards/TC-300_orchestrator_langgraph.md:1-21` (YAML frontmatter):
  ```yaml
  id: TC-300
  title: "Orchestrator graph wiring and run loop"
  status: Ready
  owner: "unassigned"
  depends_on:
    - TC-200
  allowed_paths:
    - src/launch/orchestrator/**
    - src/launch/state/**
    - tests/unit/orchestrator/test_tc_300_graph.py
    - tests/integration/test_tc_300_run_loop.py
    - reports/agents/**/TC-300/**
  ```

**Impact**:
- **Cannot execute full pipeline** without orchestrator
- **All workers (W1-W9) depend on TC-300** for state machine integration
- **Critical path blocker** for implementation

**Why This Is INFO (Not BLOCKER)**:
- This is **pre-implementation phase** — taskcards being "Ready" is the **correct state**
- TC-300 has **comprehensive taskcard** with:
  - Clear objective (orchestrator graph + run loop)
  - 6 spec references (binding authority)
  - Implementation steps (graph definition, run lifecycle, worker invocation, stop-the-line)
  - E2E verification commands
  - Acceptance checks (transitions match spec, events/snapshot produced, stop-the-line works)
  - Version locks (spec_ref, ruleset_version, templates_version)
- **No plan gap** — only **missing implementation** (expected)

**Proposed Fix**:
1. Assign TC-300 to implementation agent (prerequisite for all workers)
2. Implement per taskcard spec:
   - Graph definition per `specs/state-graph.md`
   - RUN_DIR creation + snapshot/event log initialization
   - Worker invocation with (RUN_DIR, run_config, snapshot) contract
   - Stop-the-line on BLOCKER/FAILED condition
3. Run tests: `tests/unit/orchestrator/test_tc_300_graph.py`, `tests/integration/test_tc_300_run_loop.py`
4. Verify determinism: same inputs → identical event bytes
5. Write evidence: `reports/agents/<agent>/TC-300/report.md`, `reports/agents/<agent>/TC-300/self_review.md`

**Dependencies**:
- **Upstream**: TC-200 (schemas + IO foundations) must be Done
- **Downstream**: All workers (TC-400..480) blocked until TC-300 Done

**Acceptance Criteria** (from taskcard):
- [ ] Orchestrator transitions match `specs/state-graph.md`
- [ ] `events.ndjson` and `snapshot.json` produced and update over time
- [ ] Stop-the-line behavior triggers correctly on BLOCKER/FAILED
- [ ] Tests pass and show deterministic ordering
- [ ] Agent reports written

**Severity**: INFO
**Action Required**: Implement TC-300 (assign to agent, follow taskcard contract)

---

## P-GAP-002 | INFO | Runtime Validation Gates Not Started (Expected)

**Taskcard**: TC-460 (W7 Validator), TC-570 (Validation gates extensions)
**Spec Authority**:
- `specs/09_validation_gates.md:1-end` (all runtime gates 1-10, universality gates)
- `specs/04_claims_compiler_truth_lock.md:1-end` (TruthLock gate)
- `specs/19_toolchain_and_ci.md:172` (TemplateTokenLint gate)
- `specs/31_hugo_config_awareness.md:1-end` (Hugo config gate)
- `specs/32_platform_aware_content_layout.md:1-end` (platform layout gate)

**Issue**: Runtime validation gates not implemented (all gates listed as "NOT YET IMPLEMENTED")

**Evidence**:
- `plans/traceability_matrix.md:322-430` (Runtime Gates section):
  ```markdown
  **Runtime Gates** (run during validation phase):

  - **Gate 1**: Schema validation
    - Status: NOT YET IMPLEMENTED (See TC-460)

  - **Gate 2**: Markdown lint + frontmatter validation
    - Status: NOT YET IMPLEMENTED (See TC-460)

  - **Gate 3**: Hugo config compatibility
    - Status: NOT YET IMPLEMENTED (See TC-550)

  - **Gate 4**: Platform layout compliance (content_layout_platform)
    - Status: ✅ IMPLEMENTED (preflight tool exists; runtime gate integration PENDING - See TC-570)

  - **Gate 5**: Hugo build
    - Status: NOT YET IMPLEMENTED (See TC-460)

  - **Gate 6**: Internal links
    - Status: NOT YET IMPLEMENTED (See TC-460)

  - **Gate 7**: External links (optional by config)
    - Status: NOT YET IMPLEMENTED (See TC-460)

  - **Gate 8**: Snippet checks
    - Status: NOT YET IMPLEMENTED (See TC-460)

  - **Gate 9**: TruthLock
    - Status: NOT YET IMPLEMENTED (See TC-413, TC-460)

  - **Gate 10**: Consistency
    - Status: NOT YET IMPLEMENTED (See TC-460)

  - **Gate: TemplateTokenLint** (required per specs/19_toolchain_and_ci.md)
    - Status: NOT YET IMPLEMENTED (See TC-570)

  - **Gate: Tier compliance** (universality gate)
    - Status: NOT YET IMPLEMENTED (See TC-460)

  - **Gate: Limitations honesty** (universality gate)
    - Status: NOT YET IMPLEMENTED (See TC-460)

  - **Gate: Distribution correctness** (universality gate)
    - Status: NOT YET IMPLEMENTED (See TC-460)

  - **Gate: No hidden inference** (universality gate)
    - Status: NOT YET IMPLEMENTED (See TC-413)
  ```

- `plans/taskcards/STATUS_BOARD.md:41,55`:
  ```markdown
  | TC-460 | W7 Validator (all gates → validation_report.json) | Ready | unassigned | TC-450 | 4 paths | ... |
  | TC-570 | Validation Gates (schema, links, Hugo smoke, policy) | Ready | unassigned | TC-460, TC-550 | 8 paths | ... |
  ```

**Impact**:
- **Cannot validate artifacts** until TC-460/TC-570 implemented
- **Cannot produce validation_report.json** (required by W8/W9)
- **Cannot run gates 1-10** (schema, lint, hugo, links, snippets, truthlock, consistency)
- **Cannot enforce platform layout** (V2 path validation pending TC-570 integration)

**Why This Is INFO (Not BLOCKER)**:
- This is **pre-implementation phase** — runtime gates being "not started" is **expected**
- **ALL PREFLIGHT GATES ARE IMPLEMENTED** (per `plans/traceability_matrix.md:242-315`):
  - Gate 0, A1, B, E, J, K, L, M, N, O, P, Q, R — ✅ ALL IMPLEMENTED
  - Preflight validation is **complete** and **ready to use**
- TC-460 and TC-570 have **comprehensive taskcards** with:
  - Clear objectives (gate runner orchestration, stable issue normalization)
  - Spec references (09_validation_gates, schemas, etc.)
  - Implementation steps (per-gate functions, stable normalization, timeout enforcement, platform gate)
  - E2E verification (canonical interface: `launch_validate --run_dir --profile`)
  - Acceptance checks (validation_report validates against schema, stable ordering, gates run)
  - Version locks (spec_ref, ruleset_version, templates_version)
- **No plan gap** — only **missing implementation** (expected)

**Proposed Fix**:
1. **TC-460** (W7 Validator):
   - Implement gate runner orchestration
   - Implement per-gate functions (schema, lint, hugo, links, snippets, truthlock, consistency)
   - Produce `validation_report.json` (schema: specs/schemas/validation_report.schema.json)
   - Ensure stable issue normalization (deterministic issue_id, stable ordering)
   - Validator is read-only (must not modify site)

2. **TC-570** (Validation gates extensions):
   - Implement `launch_validate` CLI with all gates
   - Implement **content_layout_platform gate** (V2 path validation per specs/32)
   - Implement **TemplateTokenLint gate** (unresolved token detection per specs/19:172)
   - Implement **gate timeout enforcement** (per specs/09:84-120)
   - Exit non-zero on required gate failure

3. Write evidence: `reports/agents/<agent>/TC-460/report.md`, `reports/agents/<agent>/TC-570/report.md`

**Dependencies**:
- **TC-460 depends on**: TC-450 (patched site available)
- **TC-570 depends on**: TC-460 (validator orchestration), TC-550 (Hugo awareness)
- **Downstream**: TC-470 (fixer), TC-480 (PRManager) depend on TC-460 output (validation_report.json)

**Acceptance Criteria** (from taskcards):
- [ ] `validation_report.json` validates against schema
- [ ] Stable ordering: same inputs → identical report bytes
- [ ] All gates listed in specs are represented
- [ ] Validator does not modify site worktree
- [ ] Exits non-zero on required gate failure
- [ ] Platform layout gate enforces V2 path structure
- [ ] TemplateTokenLint detects unresolved tokens
- [ ] Gate timeouts enforced per specs/09

**Severity**: INFO
**Action Required**: Implement TC-460, TC-570 (assign to agents, follow taskcard contracts)

---

## P-GAP-003 | INFO | PRManager Rollback Metadata Not Implemented (Expected)

**Taskcard**: TC-480 (W9 PRManager)
**Spec Authority**:
- `specs/12_pr_and_release.md:1-end` (PR creation, rollback requirements)
- `specs/34_strict_compliance_guarantees.md` (Guarantee L: rollback + recovery)
- `specs/17_github_commit_service.md:1-end` (commit service client)
- `specs/schemas/pr.schema.json:1-end` (PR artifact schema with rollback fields)

**Issue**: TC-480 not started, so no PR artifacts with rollback metadata yet

**Evidence**:
- `plans/traceability_matrix.md:487-493`:
  ```markdown
  - **Rollback metadata validation (runtime)**
    - Enforcer: Integrated into launch_validate
    - Spec: specs/34_strict_compliance_guarantees.md (Guarantee L), specs/12_pr_and_release.md
    - Enforces: PR artifacts include rollback metadata in prod profile (base_ref, run_id, rollback_steps, affected_paths)
    - Taskcards: TC-480 (PRManager)
    - Status: PENDING IMPLEMENTATION (See TC-480 - TC not started)
  ```

- `plans/taskcards/TC-480_pr_manager_w9.md:36-41`:
  ```markdown
  ### In scope
  - W9 worker implementation
  - Deterministic branch name and PR title/body templates
  - Commit service client calls in production mode
  - Persist **REQUIRED** `RUN_DIR/artifacts/pr.json` in prod profile (optional in local/ci) with:
    - PR URL and commit SHA
    - Rollback metadata per Guarantee L (base_ref, run_id, rollback_steps, affected_paths)
  - Associate commit SHA to telemetry outbox/client
  ```

- `plans/taskcards/TC-480_pr_manager_w9.md:135-138` (Acceptance checks):
  ```markdown
  ## Acceptance checks
  - [ ] PR payload is deterministic given same run_dir artifacts
  - [ ] `pr.json` validates against specs/schemas/pr.schema.json
  - [ ] pr.json includes rollback fields: base_ref, run_id, rollback_steps, affected_paths (Guarantee L)
  - [ ] Telemetry association of commit SHA recorded
  - [ ] Prod profile validation fails if pr.json missing rollback metadata
  ```

- `plans/taskcards/STATUS_BOARD.md:43`:
  ```markdown
  | TC-480 | W9 PRManager (commit service → PR) | Ready | unassigned | TC-470 | 3 paths | ... |
  ```

**Impact**:
- **Cannot create PRs** with rollback metadata until TC-480 implemented
- **Cannot satisfy Guarantee L** (rollback + recovery) in prod profile
- **Prod profile validation will fail** if pr.json missing rollback metadata

**Why This Is INFO (Not BLOCKER)**:
- This is **pre-implementation phase** — TC-480 being "Ready" is **expected**
- TC-480 **already includes rollback requirements** in taskcard spec:
  - Lines 36-41: "Persist **REQUIRED** pr.json with rollback metadata per Guarantee L"
  - Lines 135-138: Acceptance check for rollback fields present
- **No plan gap** — rollback fields are **already designed** in taskcard
- Only **missing implementation** (expected in pre-implementation phase)

**Proposed Fix**:
1. Implement TC-480 per taskcard spec:
   - Deterministic branch name from run_id + product_slug
   - Build PR body (gates summary, pages created/updated, TruthLock summary, resolved SHAs)
   - Call commit service (create branch, commit changes, open PR)
   - Write `pr.json` with **REQUIRED** rollback fields:
     - `base_ref` (branch PR targets)
     - `run_id` (link to run artifacts)
     - `rollback_steps` (instructions to revert)
     - `affected_paths` (files changed by run)
   - Emit telemetry association event

2. Validate pr.json against `specs/schemas/pr.schema.json`

3. Write evidence: `reports/agents/<agent>/TC-480/report.md`, `reports/agents/<agent>/TC-480/self_review.md`

**Dependencies**:
- **Upstream**: TC-470 (W8 Fixer) must be Done (validation_report.ok=true)
- **Downstream**: PRs can be created (final step of pipeline)

**Acceptance Criteria** (from taskcard):
- [ ] PR payload is deterministic given same run_dir artifacts
- [ ] `pr.json` validates against specs/schemas/pr.schema.json
- [ ] **pr.json includes rollback fields**: base_ref, run_id, rollback_steps, affected_paths (Guarantee L)
- [ ] Telemetry association of commit SHA recorded
- [ ] **Prod profile validation fails** if pr.json missing rollback metadata

**Severity**: INFO
**Action Required**: Implement TC-480 (assign to agent, follow taskcard contract with rollback fields)

---

## Additional Observations (No Gaps)

### ✅ All Preflight Gates Implemented

**Evidence**: `plans/traceability_matrix.md:242-315`

All preflight gates are ✅ **IMPLEMENTED** and **ready to use**:
- Gate 0: .venv policy validation (`tools/validate_dotvenv_policy.py`)
- Gate A1: Spec pack validation (`scripts/validate_spec_pack.py`)
- Gate B: Taskcard contract validation (`tools/validate_taskcards.py`)
- Gate E: Allowed paths overlap detection (`tools/audit_allowed_paths.py`)
- Gate J: Pinned refs policy (`tools/validate_pinned_refs.py`)
- Gate K: Supply chain pinning (`tools/validate_supply_chain_pinning.py`)
- Gate L: Secrets hygiene (`tools/validate_secrets_hygiene.py`)
- Gate M: No placeholders in production paths (`tools/validate_no_placeholders_production.py`)
- Gate N: Network allowlist validation (`tools/validate_network_allowlist.py`)
- Gate O: Budget validation (`tools/validate_budgets_config.py`)
- Gate P: Taskcard version locks (`tools/validate_taskcard_version_locks.py`)
- Gate Q: CI parity (`tools/validate_ci_parity.py`)
- Gate R: Untrusted code non-execution (`tools/validate_untrusted_code_policy.py`)

**Impact**: Swarm readiness can be validated **immediately** with:
```bash
python tools/validate_swarm_ready.py
```

No blocking issues for starting implementation.

### ✅ All Runtime Enforcers Implemented

**Evidence**: `plans/traceability_matrix.md:432-493`

All runtime enforcers are ✅ **IMPLEMENTED** and **ready for integration**:
- Path validation runtime enforcer (`src/launch/util/path_validation.py`) + tests
- Budget tracking runtime enforcer (`src/launch/util/budget_tracker.py`) + tests
- Diff analyzer runtime enforcer (`src/launch/util/diff_analyzer.py`) + tests
- Network allowlist runtime enforcer (`src/launch/clients/http.py`) + tests
- Subprocess execution blocker (`src/launch/util/subprocess.py`) + tests

**Pending**:
- Secret redaction runtime enforcer (TC-590, status: Ready)
- Floating ref rejection (runtime) — integration into TC-300 orchestrator + TC-460 validator
- Rollback metadata validation (runtime) — integration into TC-480 PRManager

**Impact**: Core compliance guarantees (B, D, F, G, J) are **already enforced** at runtime.

### ✅ Comprehensive Spec-to-Taskcard Mapping

**Evidence**: `plans/traceability_matrix.md:7-543`

All 35+ binding specs mapped to implementing taskcards:
- Core contracts: 6 specs → 5 taskcards (TC-100, TC-200, TC-300, etc.)
- Worker contracts: 1 spec → 9 taskcards (TC-400..480)
- Schemas: 20+ schemas → mapped to governing specs + validating gates
- Gates: 13 preflight + 14+ runtime → all mapped to validators/enforcers

**No orphaned specs detected.**

### ✅ Zero Write Fence Violations (By Design)

**Evidence**: `plans/swarm_coordination_playbook.md:54-76`, `plans/taskcards/00_TASKCARD_CONTRACT.md:22-31`

Shared library ownership enforced:
- `src/launch/io/**` → TC-200 (exclusive owner)
- `src/launch/util/**` → TC-200 (exclusive owner)
- `src/launch/models/**` → TC-250 (exclusive owner)
- `src/launch/clients/**` → TC-500 (exclusive owner)

Worker isolation guaranteed:
- Each worker (W1-W9) has exclusive ownership of implementation directory
- No path overlaps by design
- Validated by Gate E (`tools/audit_allowed_paths.py`)

**Impact**: Parallel agent swarms can execute without merge conflicts.

### ✅ All Taskcards Include Version Locks

**Evidence**: All sampled taskcards (TC-100, TC-200, TC-300, TC-400, TC-460, TC-480, TC-530, TC-570)

All taskcards include version lock fields:
```yaml
spec_ref: f48fc5dbb12c5513f42aabc2a90e2b08c6170323  # Commit SHA
ruleset_version: ruleset.v1
templates_version: templates.v1
```

**Validated by**: Gate B (`tools/validate_taskcards.py`), Gate P (`tools/validate_taskcard_version_locks.py`)

**Impact**: Reproducible builds, version traceability, compliance with Guarantee K.

---

## Gap Remediation Plan

### Phase 1: Foundation (No Gaps)
- ✅ All planning documents complete
- ✅ All taskcards have comprehensive specs
- ✅ All preflight gates implemented
- ✅ All runtime enforcers implemented (core guarantees)

### Phase 2: Implementation (Address INFO Gaps)

**P-GAP-001**: Implement TC-300 (Orchestrator)
- **Priority**: CRITICAL (prerequisite for all workers)
- **Assignee**: Implementation agent
- **Timeline**: Phase 1 implementation
- **Evidence**: `reports/agents/<agent>/TC-300/report.md`, `reports/agents/<agent>/TC-300/self_review.md`

**P-GAP-002**: Implement TC-460 (Validator) + TC-570 (Gates)
- **Priority**: HIGH (required for validation pipeline)
- **Assignee**: Implementation agent
- **Timeline**: Phase 5 implementation (after workers)
- **Evidence**: `reports/agents/<agent>/TC-460/report.md`, `reports/agents/<agent>/TC-570/report.md`

**P-GAP-003**: Implement TC-480 (PRManager with rollback)
- **Priority**: HIGH (required for PR creation)
- **Assignee**: Implementation agent
- **Timeline**: Phase 6 implementation (after validator)
- **Evidence**: `reports/agents/<agent>/TC-480/report.md` with rollback fields verification

### Phase 3: Validation (No Gaps Expected)

After all taskcards implemented:
- Run E2E pilots (TC-522 CLI, TC-523 MCP)
- Verify determinism (golden runs)
- Orchestrator master review (GO/NO-GO decision)

---

## Conclusion

**Total Gaps**: 3 (all INFO-level, non-blocking)

**Gap Assessment**:
- **P-GAP-001**: Orchestrator not started (expected, taskcard Ready)
- **P-GAP-002**: Runtime gates not started (expected, preflight gates all implemented)
- **P-GAP-003**: PRManager not started (expected, rollback fields already designed)

**Root Cause**: All gaps are due to **pre-implementation phase** (taskcards Ready, waiting for assignment), NOT plan deficiencies.

**Blocking Issues**: **ZERO**

**Action Required**:
1. Run preflight validation: `python tools/validate_swarm_ready.py`
2. Assign taskcards to agents (update YAML frontmatter: `owner`, `status: In-Progress`)
3. Regenerate STATUS_BOARD: `python tools/generate_status_board.py`
4. Begin implementation following Taskcards Contract

**Readiness**: ✅ **PLANS AND TASKCARDS ARE READY FOR IMPLEMENTATION**

No plan modifications required. All gaps will be resolved through taskcard execution.

---

**Gaps Report Generated**: 2026-01-27
**Auditor**: AGENT_P (Plans/Taskcards & Swarm Readiness Auditor)
**Gaps Identified**: 3 INFO-level (0 blocking)
**Remediation Plan**: Execute taskcards per contract (no plan changes needed)
