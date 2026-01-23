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

## Deliverables
- Code + tests
- Report and self review under repo-root reports/

## Acceptance checks
- [ ] Evidence zip produced with deterministic ordering
- [ ] INDEX.md contains direct relative links to top artifacts/reports
- [ ] No secrets included (TC-590)

## Self-review
Use `reports/templates/self_review_12d.md`. Any dimension <4 must include a concrete fix plan.
