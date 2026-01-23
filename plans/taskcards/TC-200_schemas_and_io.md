---
id: TC-200
title: "Schemas and IO foundations"
status: Ready
owner: "unassigned"
updated: "2026-01-22"
depends_on:
  - TC-100
allowed_paths:
  - src/launch/io/**
  - src/launch/util/**
  - scripts/validate_schemas.py
  - tests/unit/io/**
  - tests/unit/util/**
  - reports/agents/**/TC-200/**
evidence_required:
  - reports/agents/<agent>/TC-200/report.md
  - reports/agents/<agent>/TC-200/self_review.md
  - "Test output: stable JSON bytes test"
  - "Test output: run_config validation tests"
---

# Taskcard TC-200 — Schemas and IO foundations

## Objective
Make the system’s **artifact IO** enforceable and deterministic by completing/validating schema usage and implementing stable JSON read/write helpers that all workers must use.

## Required spec references
- specs/11_state_and_events.md
- specs/10_determinism_and_caching.md
- specs/19_toolchain_and_ci.md
- specs/schemas/run_config.schema.json
- specs/schemas/issue.schema.json
- specs/schemas/validation_report.schema.json

## Scope
### In scope
- Stable JSON serialization rules (ordering, newline, UTF-8, no BOM)
- Atomic write helper(s) used by all artifact writers
- Schema validation helper(s) (for run_config + artifacts)
- Minimal tests proving byte-for-byte stable outputs

### Out of scope
- Worker-specific artifact generation (handled by TC-400+)
- Patch engine logic (handled by TC-450/TC-540)

## Inputs
- `specs/schemas/*.schema.json`
- Run configs under `configs/**` and/or `RUN_DIR/run_config.yaml` (when running)
- Determinism rules in `specs/10_determinism_and_caching.md`

## Outputs
- Library module(s) providing:
  - `read_yaml_run_config()`
  - `validate_json_against_schema()`
  - `write_json_stable_atomic()`
- Tests verifying:
  - stable JSON bytes (same dict => identical bytes)
  - atomic write behavior (temp file + rename)

## Allowed paths
- src/launch/io/**
- src/launch/util/**
- scripts/validate_schemas.py
- tests/unit/io/**
- tests/unit/util/**
- reports/agents/**/TC-200/**
## Implementation steps
1) **Define stable JSON format** (as code constants): sorted keys, 2-space indent, trailing newline, UTF-8.
2) **Atomic write**:
   - write to `.<name>.tmp` in same directory
   - fsync (where available) and rename
   - never leave partial files on crash path
3) **Schema validation**:
   - use jsonschema (pinned per toolchain)
   - provide helpers to validate dicts and raise a stable error shape (mapped to Issue schema fields where relevant)
4) **Run config loader**:
   - load YAML (safe loader)
   - validate against `run_config.schema.json`
   - expose a normalized internal object (e.g., ensure locales vs locale rules enforced)
5) **Tests**:
   - unit tests for stable JSON bytes (golden snapshot or direct byte comparison)
   - unit tests that validate a known-good example config and reject an invalid one

## E2E verification
**Concrete command(s) to run:**
```bash
python -m pytest tests/unit/io/ -v
python -c "from launch.io.run_config import load_and_validate_run_config; print('OK')"
```

**Expected artifacts:**
- specs/schemas/run_config.schema.json (validates against JSON Schema draft)
- specs/schemas/page_plan.schema.json

**Success criteria:**
- [ ] All schema files compile
- [ ] Example configs validate

> If E2E harness not yet implemented, this defines the stub contract for TC-520/522/523.

## Integration boundary proven
What upstream/downstream wiring was validated:
- Upstream: TC-100 (package structure)
- Downstream: All workers consume schemas via TC-200 I/O layer
- Contracts: run_config.schema.json, page_plan.schema.json, validation_report.schema.json

## Deliverables
- Code:
  - stable IO + schema validation helpers
- Tests:
  - stable JSON bytes test
  - run_config validation tests
- Reports (required):
  - reports/agents/<agent>/TC-200/report.md
  - reports/agents/<agent>/TC-200/self_review.md

## Acceptance checks
- [ ] Stable JSON writer produces byte-identical outputs across runs
- [ ] Atomic write helper passes tests and never writes partial artifacts
- [ ] run_config validation enforces locales/locale rule (per schema)
- [ ] Agent reports are written

## Self-review
Use `reports/templates/self_review_12d.md`. Any dimension <4 must include a concrete fix plan.
