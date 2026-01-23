---
id: TC-460
title: "W7 Validator (all gates → validation_report.json)"
status: Ready
owner: "unassigned"
updated: "2026-01-22"
depends_on:
  - TC-450
allowed_paths:
  - src/launch/workers/w7_validator.py
  - src/launch/validators/**
  - tests/unit/workers/test_tc_460_validator.py
  - reports/agents/**/TC-460/**
evidence_required:
  - reports/agents/<agent>/TC-460/report.md
  - reports/agents/<agent>/TC-460/self_review.md
---

# Taskcard TC-460 — W7 Validator (all gates → validation_report.json)

## Objective
Implement **W7: Validator** to run all required validation gates, normalize outputs into stable issues, and produce a single deterministic `validation_report.json`.

## Required spec references
- specs/21_worker_contracts.md (W7)
- specs/09_validation_gates.md
- specs/04_claims_compiler_truth_lock.md
- specs/19_toolchain_and_ci.md
- specs/31_hugo_config_awareness.md
- specs/schemas/validation_report.schema.json
- specs/schemas/issue.schema.json

## Scope
### In scope
- Gate runner orchestration (schema, markdown lint, Hugo config compatibility, Hugo build, links, snippet checks, TruthLock, consistency, universality gates)
- Tool execution with pinned configs (from `config/` and toolchain lock)
- Stable issue normalization:
  - stable issue IDs and ordering
  - stable fields per schema
- Validator is read-only (must not modify site)

### Out of scope
- Fixing issues (W8)

## Inputs
- site worktree (`RUN_DIR/work/site/`)
- `RUN_DIR/artifacts/page_plan.json`
- `RUN_DIR/artifacts/product_facts.json`
- `RUN_DIR/artifacts/evidence_map.json`
- `RUN_DIR/artifacts/patch_bundle.json` (if present)

## Outputs
- `RUN_DIR/artifacts/validation_report.json`
- Raw tool logs under `RUN_DIR/logs/` (one subfile per gate)

## Allowed paths
- src/launch/workers/w7_validator.py
- src/launch/validators/**
- tests/unit/workers/test_tc_460_validator.py
- reports/agents/**/TC-460/**
## Implementation steps
1) Implement per-gate functions under `src/launch/validators/`.
2) For each gate:
   - run tool or internal check
   - capture raw logs to `RUN_DIR/logs/<gate_id>.*`
   - convert findings to `issue.schema.json` objects
3) Apply stable normalization:
   - stable issue_id derivation (per spec)
   - stable ordering (sort by severity then id)
4) Produce `validation_report.json`:
   - `ok` true only when all required gates pass
   - include per-gate status + issue counts
5) Write artifacts atomically and emit events.

## E2E verification
**Concrete command(s) to run:**
```bash
python -m launch.workers.w7_validator --site-dir workdir/site --config specs/pilots/pilot-aspose-3d-foss-python/run_config.pinned.yaml
```

**Expected artifacts:**
- artifacts/validation_report.json (schema: validation_report.schema.json)

**Success criteria:**
- [ ] All gates run
- [ ] Report validates against schema

> If E2E harness not yet implemented, this defines the stub contract for TC-520/522/523.

## Integration boundary proven
What upstream/downstream wiring was validated:
- Upstream: TC-450 (patched site)
- Downstream: TC-470 (Fixer), TC-480 (PRManager)
- Contracts: validation_report.schema.json, specs/09_validation_gates.md

## Deliverables
- Code:
  - gate implementations and validator orchestrator
- Tests:
  - unit tests for issue normalization and ordering
  - integration test: run validator on fixture site tree and assert stable validation_report bytes
- Reports:
  - reports/agents/<agent>/TC-460/report.md
  - reports/agents/<agent>/TC-460/self_review.md

## Acceptance checks
- [ ] `validation_report.json` validates against schema
- [ ] Stable ordering: same inputs => identical report bytes
- [ ] All gates listed in specs are represented (even if some are conditionally skipped by config)
- [ ] Validator does not modify site worktree

## Self-review
Use `reports/templates/self_review_12d.md`.
