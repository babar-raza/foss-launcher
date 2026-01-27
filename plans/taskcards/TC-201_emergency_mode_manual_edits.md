---
id: TC-201
title: "Emergency mode flag (allow_manual_edits) and policy plumbing"
status: In-Progress
owner: "FOUNDATION_AGENT"
updated: "2026-01-27"
depends_on:
  - TC-200
allowed_paths:
  - src/launch/state/emergency_mode.py
  - src/launch/orchestrator/policy_enforcement.py
  - src/launch/workers/_shared/policy_check.py
  - tests/unit/state/test_tc_201_emergency_mode.py
  - reports/agents/**/TC-201/**
evidence_required:
  - reports/agents/<agent>/TC-201/report.md
  - reports/agents/<agent>/TC-201/self_review.md
spec_ref: f48fc5dbb12c5513f42aabc2a90e2b08c6170323
ruleset_version: ruleset.v1
templates_version: templates.v1
---

# Taskcard TC-201 — Emergency mode flag (allow_manual_edits) and policy plumbing

## Objective
Implement the `run_config.allow_manual_edits` escape hatch **end-to-end** (config load → validator gate output → orchestrator reporting) while keeping **default behavior strict** (manual edits forbidden).

## Required spec references
- specs/01_system_contract.md
- specs/09_validation_gates.md
- plans/policies/no_manual_content_edits.md
- specs/schemas/run_config.schema.json
- specs/schemas/validation_report.schema.json
- specs/schemas/issue.schema.json
- specs/10_determinism_and_caching.md

## Scope
### In scope
- Read and propagate `allow_manual_edits` from run_config
- Validation policy gate behavior:
  - if false (default): unexplained diffs are a BLOCKER
  - if true: validator records `manual_edits=true` + enumerates files
- Orchestrator master review requirement enforcement (must list files and rationale when manual edits were used)

### Out of scope
- Any expansion of what “manual edit” means beyond the policy definition
- Content-writing behavior changes (W4–W6)

## Inputs
- `RUN_DIR/run_config.yaml` including optional `allow_manual_edits`
- Git diff of `RUN_DIR/work/site` against base ref (or a defined baseline) for “changed files” enumeration
- Patch/evidence index for explained files (see W6/W7 specs)

## Outputs
- Code paths that:
  - expose `allow_manual_edits` to workers/validator/orchestrator
  - produce validation_report fields:
    - `manual_edits` (bool)
    - `manual_edited_files` (list[str]) when manual_edits is true
  - produce an Issue (`severity=BLOCKER`, component=policy) when manual edits occur while flag is false

## Allowed paths
- src/launch/state/emergency_mode.py
- src/launch/orchestrator/policy_enforcement.py
- src/launch/workers/_shared/policy_check.py
- tests/unit/state/test_tc_201_emergency_mode.py
- reports/agents/**/TC-201/**
## Implementation steps
1) Extend run_config loading (TC-200 utilities) to surface `allow_manual_edits` with default false.
2) Implement/extend the policy gate:
   - enumerate changed content files deterministically
   - for each changed file, confirm it appears in patch/evidence index
   - if any file is unexplained and `allow_manual_edits=false`: emit BLOCKER Issue and fail gate
   - if `allow_manual_edits=true`: set `validation_report.manual_edits=true` and record `manual_edited_files`
3) Orchestrator enforcement:
   - if validation_report.manual_edits=true, require the orchestrator master review to list the files and rationale
   - if missing, mark run BLOCKED and emit Issue
4) Tests:
   - when allow_manual_edits=false, unexplained diff => BLOCKER
   - when true, unexplained diff => manual_edits=true and files listed

## E2E verification
**Concrete command(s) to run:**
```bash
python -c "from launch.io.run_config import load_and_validate_run_config; cfg = {'allow_manual_edits': True}; print('OK')"
```

**Expected artifacts:**
- src/launch/io/run_config.py (allow_manual_edits field)

**Success criteria:**
- [ ] allow_manual_edits flag recognized
- [ ] Policy gate respects flag

> If E2E harness not yet implemented, this defines the stub contract for TC-520/522/523.

## Integration boundary proven
What upstream/downstream wiring was validated:
- Upstream: TC-200 (run_config schema)
- Downstream: TC-571 (policy gate), TC-450 (patcher)
- Contracts: run_config.schema.json includes allow_manual_edits boolean

## Failure modes
1. **Failure**: Schema validation fails for output artifacts
   - **Detection**: `validate_swarm_ready.py` or pytest fails with JSON schema errors
   - **Fix**: Review artifact structure against schema files in `specs/schemas/`; ensure all required fields are present and types match
   - **Spec/Gate**: specs/11_state_and_events.md, specs/09_validation_gates.md (Gate C)

2. **Failure**: Nondeterministic output detected
   - **Detection**: Running task twice produces different artifact bytes or ordering
   - **Fix**: Review specs/10_determinism_and_caching.md; ensure stable JSON serialization, stable sorting of lists, no timestamps/UUIDs in outputs
   - **Spec/Gate**: specs/10_determinism_and_caching.md, tools/validate_swarm_ready.py (Gate H)

3. **Failure**: Write fence violation (modified files outside allowed_paths)
   - **Detection**: `git status` shows changes outside allowed_paths, or Gate E fails
   - **Fix**: Revert unauthorized changes; if shared library modification needed, escalate to owning taskcard
   - **Spec/Gate**: plans/taskcards/00_TASKCARD_CONTRACT.md (Write fence rule), tools/validate_taskcards.py

## Task-specific review checklist
Beyond the standard acceptance checks, verify:
- [ ] All outputs are written atomically per specs/10_determinism_and_caching.md
- [ ] No manual content edits made (compliance with no_manual_content_edits policy)
- [ ] Determinism verified by running task twice and comparing artifacts byte-for-byte
- [ ] All spec references listed in taskcard were consulted during implementation
- [ ] Evidence files (report.md, self_review.md) include all required sections and command outputs
- [ ] No placeholder values (PIN_ME, TODO, FIXME, etc.) remain in production code paths

## Deliverables
- Code:
  - run_config propagation + policy gate + orchestrator checks
- Tests:
  - two-path tests (flag false/true)
- Reports (required):
  - reports/agents/<agent>/TC-201/report.md
  - reports/agents/<agent>/TC-201/self_review.md

## Acceptance checks
- [ ] Default behavior forbids manual edits and fails with a policy BLOCKER
- [ ] Emergency mode records `manual_edits=true` and enumerates files in validation_report
- [ ] Deterministic enumeration ordering (stable sort)
- [ ] Tests passing

## Self-review
Use `reports/templates/self_review_12d.md`. Any dimension <4 must include a concrete fix plan.
