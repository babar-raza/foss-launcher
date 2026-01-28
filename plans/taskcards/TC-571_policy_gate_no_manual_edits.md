---
id: TC-571
title: "W7.x Policy gate: No manual content edits"
status: Done
owner: "W7_AGENT"
updated: "2026-01-28"
depends_on:
  - TC-460
  - TC-201
allowed_paths:
  - src/launch/validators/policy_gate.py
  - tests/unit/validators/test_tc_571_policy_gate.py
  - reports/agents/**/TC-571/**
evidence_required:
  - reports/agents/<agent>/TC-571/report.md
  - reports/agents/<agent>/TC-571/self_review.md
spec_ref: f48fc5dbb12c5513f42aabc2a90e2b08c6170323
ruleset_version: ruleset.v1
templates_version: templates.v1
---

# Taskcard TC-571 — W7.x Policy gate: No manual content edits

## Objective
Implement the explicit W7 policy gate that enforces `plans/policies/no_manual_content_edits.md` and integrates with `validation_report.json`.

## Required spec references
- plans/policies/no_manual_content_edits.md
- specs/09_validation_gates.md
- specs/11_state_and_events.md
- specs/10_determinism_and_caching.md
- specs/schemas/validation_report.schema.json
- specs/schemas/issue.schema.json
- specs/08_patch_engine.md

## Scope
### In scope
- Deterministic enumeration of changed content files (site worktree)
- Patch/evidence index lookup for each changed file
- Policy decisions based on `run_config.allow_manual_edits`
- Writing gate result into validation_report (gate name: `policy_no_manual_edits`)

### Out of scope
- Other gates (schema, hugo build, links, etc.) covered by TC-460/TC-570
- Fixer behavior (TC-470)

## Inputs
- `RUN_DIR/work/site` (working copy)
- Patch/evidence index produced by patch engine (W6)
- run_config.allow_manual_edits flag

## Outputs
- validation_report gate entry:
  - name: policy_no_manual_edits
  - ok: boolean
  - log_path: optional
- Issues when policy violated (BLOCKER)

## Allowed paths
- src/launch/validators/policy_gate.py
- tests/unit/validators/test_tc_571_policy_gate.py
- reports/agents/**/TC-571/**
## Implementation steps
1) Enumerate changed content files deterministically (stable sort).
2) For each file, confirm it has a patch/evidence record.
3) If unexplained changes exist:
   - if allow_manual_edits=false: fail gate and emit BLOCKER Issue
   - if true: mark validation_report.manual_edits=true and record manual_edited_files
4) Add tests for both modes.

## E2E verification
**Concrete command(s) to run:**
```bash
python -m launch.validators.policy_gate --site-dir workdir/site --config specs/pilots/pilot-aspose-3d-foss-python/run_config.pinned.yaml
```

**Expected artifacts:**
- artifacts/policy_gate_result.json

**Success criteria:**
- [ ] Manual edit detection works
- [ ] allow_manual_edits flag respected

> If E2E harness not yet implemented, this defines the stub contract for TC-520/522/523.

## Integration boundary proven
What upstream/downstream wiring was validated:
- Upstream: TC-460 (validator), TC-201 (emergency mode flag)
- Downstream: TC-470 (fixer cannot fix policy violations)
- Contracts: plans/policies/no_manual_content_edits.md

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
- [ ] Worker emits required events per specs/21_worker_contracts.md
- [ ] Worker outputs validate against declared schemas
- [ ] Worker handles missing/malformed inputs gracefully with blocker artifacts
- [ ] All outputs are written atomically per specs/10_determinism_and_caching.md
- [ ] No manual content edits made (compliance with no_manual_content_edits policy)
- [ ] Determinism verified by running task twice and comparing artifacts byte-for-byte
- [ ] All spec references listed in taskcard were consulted during implementation
- [ ] Evidence files (report.md, self_review.md) include all required sections and command outputs
- [ ] No placeholder values (PIN_ME, TODO, FIXME, etc.) remain in production code paths

## Deliverables
- Code:
  - policy gate implementation
- Tests:
  - enforcement tests for flag true/false
- Reports (required):
  - reports/agents/<agent>/TC-571/report.md
  - reports/agents/<agent>/TC-571/self_review.md

## Acceptance checks
- [ ] Gate fails on unexplained changes when allow_manual_edits is false
- [ ] Emergency mode records manual edits fields in validation_report
- [ ] Deterministic ordering proven in tests
- [ ] Tests passing

## Self-review
Use `reports/templates/self_review_12d.md`. Any dimension <4 must include a concrete fix plan.
