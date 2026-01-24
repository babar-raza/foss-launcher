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
spec_ref: f48fc5dbb12c5513f42aabc2a90e2b08c6170323
ruleset_version: ruleset.v1
templates_version: templates.v1
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
- [ ] All schema files validate as proper JSON Schema Draft 7
- [ ] Schema validation helpers cover all required artifact types
- [ ] All outputs are written atomically per specs/10_determinism_and_caching.md
- [ ] No manual content edits made (compliance with no_manual_content_edits policy)
- [ ] Determinism verified by running task twice and comparing artifacts byte-for-byte
- [ ] All spec references listed in taskcard were consulted during implementation
- [ ] Evidence files (report.md, self_review.md) include all required sections and command outputs
- [ ] No placeholder values (PIN_ME, TODO, FIXME, etc.) remain in production code paths

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
