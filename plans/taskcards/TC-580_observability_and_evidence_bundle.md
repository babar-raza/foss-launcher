---
id: TC-580
title: "Observability and Evidence Packaging (reports index + evidence zip)"
status: Ready
owner: "unassigned"
updated: "2026-01-22"
depends_on:
  - TC-300
  - TC-460
allowed_paths:
  - src/launch/tools/evidence_bundle.py
  - src/launch/tools/report_index.py
  - tests/unit/tools/test_tc_580_evidence_bundle.py
  - reports/agents/**/TC-580/**
evidence_required:
  - reports/agents/<agent>/TC-580/report.md
  - reports/agents/<agent>/TC-580/self_review.md
spec_ref: f48fc5dbb12c5513f42aabc2a90e2b08c6170323
ruleset_version: ruleset.v1
templates_version: templates.v1
---

# Taskcard TC-580 — Observability and Evidence Packaging (reports index + evidence zip)

## Objective
Standardize run-time reporting and create an evidence bundle that reviewers can inspect without rerunning the system.

## Required spec references
- specs/11_state_and_events.md
- specs/16_local_telemetry_api.md
- specs/09_validation_gates.md
- specs/28_coordination_and_handoffs.md

## Scope
### In scope
- Standardize `RUN_DIR/reports/`:
  - `RUN_DIR/reports/INDEX.md`
  - `RUN_DIR/reports/summary.json`
- Implement evidence bundler:
  - `RUN_DIR/evidence_bundle.zip`
  - deterministic zip ordering
  - excludes secrets and caches
- Integrate helper into orchestrator end-of-run

### Out of scope
- _None._

## Inputs
- `RUN_DIR` with artifacts/logs/reports

## Outputs
- `RUN_DIR/reports/INDEX.md`
- `RUN_DIR/evidence_bundle.zip`
- Event: `EVIDENCE_BUNDLE_WRITTEN`

## Allowed paths
- src/launch/tools/evidence_bundle.py
- src/launch/tools/report_index.py
- tests/unit/tools/test_tc_580_evidence_bundle.py
- reports/agents/**/TC-580/**
## Implementation steps
1) Define index format and required links to artifacts and gate reports.
2) Implement `build_report_index(RUN_DIR)`.
3) Build evidence zip with deterministic ordering and allowlist selection.
4) Add tests for deterministic content list and secret exclusion.

## E2E verification
**Concrete command(s) to run:**
```bash
python -m launch.observability.package --run-id test_run --output evidence_bundle.zip
```

**Expected artifacts:**
- evidence_bundle.zip (contains all run artifacts)
- artifacts/reports_index.json

**Success criteria:**
- [ ] Bundle created
- [ ] All artifacts included

> If E2E harness not yet implemented, this defines the stub contract for TC-520/522/523.

## Integration boundary proven
What upstream/downstream wiring was validated:
- Upstream: TC-300 (run completion)
- Downstream: Audit trail, debugging
- Contracts: specs/11_state_and_events.md evidence requirements

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
- Code + tests
- Report and self review under repo-root reports/

## Acceptance checks
- [ ] Evidence zip produced with deterministic ordering
- [ ] INDEX.md contains direct relative links to top artifacts/reports
- [ ] No secrets included (TC-590)

## Self-review
Use `reports/templates/self_review_12d.md`. Any dimension <4 must include a concrete fix plan.
