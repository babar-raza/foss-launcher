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

- `src/launch/validators/policy_gate.py`
- `tests/unit/validators/test_tc_571_policy_gate.py`
- `reports/agents/**/TC-571/**`## Implementation steps
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

### Failure mode 1: Policy gate allows manual edits when allow_manual_edits=false
**Detection:** Gate PASS despite unexplained content changes; git diff shows manual edits to content/ not linked to W4-W6 operations; validation_report.json missing policy violation issue
**Resolution:** Review policy gate implementation in execute_policy_gate(); verify run_config.allow_manual_edits flag checked correctly; ensure git diff --name-only content/ executed to detect changes; cross-reference changed files against operations_log.json to confirm pipeline provenance; emit BLOCKER issue for unexplained edits with file list
**Spec/Gate:** plans/policies/no_manual_content_edits.md (policy definition), specs/09_validation_gates.md (policy gate contract)

### Failure mode 2: Emergency mode (allow_manual_edits=true) doesn't record manual edits in validation report
**Detection:** Manual edits made but not documented; validation_report.json missing manual_edits_metadata field; audit trail incomplete; unclear which files were manually edited
**Resolution:** Review emergency mode logic in policy gate; ensure manual edits detected via git diff even when allow_manual_edits=true; verify manual_edits_metadata field added to validation_report with file list, edit rationale, and timestamp; check that emergency mode flag logged to telemetry; document emergency override in validation report summary
**Spec/Gate:** plans/policies/no_manual_content_edits.md (emergency mode metadata), specs/11_state_and_events.md (validation_report schema)

### Failure mode 3: Policy gate produces non-deterministic file ordering in issue list
**Detection:** Gate H (determinism) fails; validation_report.json has different ordering of policy violation files across runs; SHA256 mismatch on identical violations
**Resolution:** Apply sorted() to file lists before writing to validation_report; ensure operations_log.json entries processed in sorted order; verify issue.location.path uses stable sorting when multiple files violate policy; review json.dumps(sort_keys=True) applied to final report
**Spec/Gate:** specs/10_determinism_and_caching.md (stable serialization), Gate H (determinism validation)

### Failure mode 4: Policy gate false positive on W6 patch operations with complex diffs
**Detection:** Gate fails on legitimate W6 patches; false positive for unexplained edits; operations_log.json shows patch applied but gate doesn't recognize it as explained
**Resolution:** Review provenance matching logic; ensure operations_log.json includes patch_applied events with target file paths; verify policy gate cross-references git diff output with operations_log events by file path; check for path normalization issues (absolute vs relative, backslash vs forward slash); add test case with W6 patch operation
**Spec/Gate:** plans/policies/no_manual_content_edits.md (provenance requirements), specs/21_worker_contracts.md (W6 patch events)

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
