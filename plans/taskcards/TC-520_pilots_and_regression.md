---
id: TC-520
title: "Pilots and regression harness"
status: Ready
owner: "unassigned"
updated: "2026-01-23"
depends_on:
  - TC-300
  - TC-460
allowed_paths:
  - specs/pilots/**
  - configs/pilots/**
  - scripts/run_pilot.py
  - scripts/regression_harness.py
  - tests/pilots/**
  - reports/agents/**/TC-520/**
evidence_required:
  - reports/agents/<agent>/TC-520/report.md
  - reports/agents/<agent>/TC-520/self_review.md
---

# Taskcard TC-520 — Pilots and regression harness

## Objective
Create a reproducible pilot/regression harness so the system can be validated on known repos with deterministic outcomes, with failures captured as issues and evidence artifacts.

## Required spec references
- specs/13_pilots.md
- specs/pilot-blueprint.md
- specs/10_determinism_and_caching.md
- specs/09_validation_gates.md
- specs/schemas/issue.schema.json

## Scope
### In scope
- Canonical pilot artifacts under `specs/pilots/<pilot_id>/`:
  - `run_config.pinned.yaml` — pinned inputs (repo SHAs, versions, allowed_paths)
  - `expected_page_plan.json` — expected PagePlan output
  - `expected_validation_report.json` — expected ValidationReport (ok=true)
  - `notes.md` — repo structure notes and known quirks
- A runner that executes pilots and records results consistently
- Regression assertions (golden artifacts or checksums) for determinism
- Template maintenance under `configs/pilots/**` (non-binding authoring helpers)

### Out of scope
- Full production release process (TC-480/TC-12)
- Building a large pilot library (start with minimum viable set)

## Inputs
- **Canonical pilot configs**: `specs/pilots/<pilot_id>/run_config.pinned.yaml`
- **Expected artifacts**: `specs/pilots/<pilot_id>/expected_*.json`
- Templates (non-binding): `configs/pilots/_template.*.yaml`
- The orchestrator runner (TC-300)
- Network access (optional) depending on pilots; must support offline-safe behavior where possible

## Outputs
- Pilot runner script/CLI (e.g., `python -m launch_pilots` or `scripts/run_pilots.py`)
- Pilot result summary artifact(s):
  - per-pilot status
  - run_id + resolved SHAs
  - determinism check outputs
- Captured issue artifacts for failures

## Allowed paths
- specs/pilots/** (canonical pilot configs and expected artifacts)
- configs/pilots/** (non-binding templates only)
- scripts/run_pilot.py
- scripts/regression_harness.py
- tests/pilots/**
- reports/agents/**/TC-520/**
## Implementation steps
1) Define pilot config schema/contract (YAML) and document required fields.
2) Implement pilot runner:
   - enumerates pilots deterministically (sorted)
   - runs each pilot in isolated RUN_DIR
   - collects validation_report and key artifacts
3) Implement determinism regression:
   - rerun a pilot twice and compare stable artifacts (bytes)
   - record diffs on mismatch
4) Add tests for pilot discovery ordering and result aggregation.

## E2E verification
**Concrete command(s) to run:**
```bash
python scripts/run_pilot.py --pilot pilot-aspose-3d-foss-python --dry-run
```

**Expected artifacts:**
- artifacts/pilot_run_report.json
- Compare: expected_page_plan.json vs actual page_plan.json

**Success criteria:**
- [ ] Pilot completes
- [ ] Output matches expected artifacts

> If E2E harness not yet implemented, this defines the stub contract for TC-520/522/523.

## Integration boundary proven
What upstream/downstream wiring was validated:
- Upstream: TC-300 (full pipeline)
- Downstream: Regression harness (CI)
- Contracts: specs/13_pilots.md determinism requirements

## Deliverables
- Code:
  - pilot runner + config contract docs
- Tests:
  - ordering and aggregation tests
- Reports (required):
  - reports/agents/<agent>/TC-520/report.md
  - reports/agents/<agent>/TC-520/self_review.md

## Acceptance checks
- [ ] At least one pilot can be executed end-to-end
- [ ] Pilot enumeration is deterministic
- [ ] Determinism regression emits clear failure evidence
- [ ] Tests passing

## Self-review
Use `reports/templates/self_review_12d.md`. Any dimension <4 must include a concrete fix plan.
