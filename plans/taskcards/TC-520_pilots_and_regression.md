---
id: TC-520
title: "Pilots and regression harness"
status: Ready
owner: "unassigned"
updated: "2026-01-22"
depends_on:
  - TC-300
  - TC-460
allowed_paths:
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
- Pilot configuration format and folder layout under `configs/pilots/`
- A runner that executes pilots and records results consistently
- Regression assertions (golden artifacts or checksums) for determinism

### Out of scope
- Full production release process (TC-480/TC-12)
- Building a large pilot library (start with minimum viable set)

## Inputs
- Pilot configs in `configs/pilots/**`
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
- configs/pilots/**
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
