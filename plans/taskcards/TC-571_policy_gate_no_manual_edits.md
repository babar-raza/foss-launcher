---
id: TC-571
title: "W7.x Policy gate: No manual content edits"
status: Ready
owner: "unassigned"
updated: "2026-01-22"
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
