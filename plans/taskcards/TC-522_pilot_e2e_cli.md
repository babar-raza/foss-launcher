---
id: TC-522
title: "Pilot E2E CLI execution and determinism verification"
status: Done
owner: "TELEMETRY_AGENT"
updated: "2026-01-29"
depends_on:
  - TC-520
  - TC-530
  - TC-560
allowed_paths:
  - scripts/run_pilot_e2e.py
  - tests/e2e/test_tc_522_pilot_cli.py
  - reports/agents/**/TC-522/**
evidence_required:
  - reports/agents/<agent>/TC-522/report.md
  - reports/agents/<agent>/TC-522/self_review.md
  - artifacts/pilot_e2e_cli_report.json
spec_ref: f48fc5dbb12c5513f42aabc2a90e2b08c6170323
ruleset_version: ruleset.v1
templates_version: templates.v1
---

# Taskcard TC-522 — Pilot E2E CLI execution and determinism verification

## Objective
Implement and execute a complete end-to-end pilot run via CLI, comparing outputs to expected artifacts and verifying determinism through repeated execution.

## Required spec references
- specs/13_pilots.md
- specs/10_determinism_and_caching.md
- specs/pilots/README.md

## Scope
### In scope
- CLI-based pilot execution script
- Expected artifact comparison (page_plan, validation_report)
- Determinism verification (run twice, compare checksums)
- Report generation with pass/fail status

### Out of scope
- MCP-based execution (see TC-523)
- New pilot creation (uses existing pilots)
- Modifying pilot expected artifacts

## Non-negotiables (binding for this task)
- **No improvisation:** if anything is unclear, write a blocker issue and stop.
- **Write fence:** MAY ONLY change files under Allowed paths.
- **Determinism:** pilot outputs MUST be bitwise identical across runs.
- **Evidence:** comparison results must be recorded with checksums.

## Preconditions / dependencies
- TC-520: Pilot infrastructure exists
- TC-530: CLI entrypoints work
- TC-560: Determinism harness available
- Pinned pilot configs exist: `specs/pilots/pilot-aspose-3d-foss-python/run_config.pinned.yaml`

## Inputs
- `specs/pilots/pilot-aspose-3d-foss-python/run_config.pinned.yaml` — pinned config
- `specs/pilots/pilot-aspose-3d-foss-python/expected_page_plan.json` — expected output
- `specs/pilots/pilot-aspose-3d-foss-python/expected_validation_report.json` — expected output

## Outputs
- `scripts/run_pilot_e2e.py` — CLI pilot execution script
- `tests/e2e/test_tc_522_pilot_cli.py` — E2E test
- `artifacts/pilot_e2e_cli_report.json` — execution report

## Allowed paths
- scripts/run_pilot_e2e.py
- tests/e2e/test_tc_522_pilot_cli.py
- reports/agents/**/TC-522/**

## Implementation steps
1) Create `scripts/run_pilot_e2e.py`:
   - Accept `--pilot` argument (pilot directory name)
   - Load `run_config.pinned.yaml` from `specs/pilots/{pilot}/`
   - Execute full pipeline via CLI: `python -m launch.cli run --config <config>`
   - Compare outputs to `expected_page_plan.json` and `expected_validation_report.json`
   - Run twice and compare checksums for determinism proof
   - Generate JSON report with pass/fail, checksums, diffs

2) Create E2E test `tests/e2e/test_tc_522_pilot_cli.py`:
   - Call `run_pilot_e2e.py` with `pilot-aspose-3d-foss-python`
   - Assert report shows pass for artifact comparison
   - Assert report shows pass for determinism (two runs match)

3) Document in agent report:
   - Exact commands run
   - Checksums of expected vs actual
   - Determinism proof (two run checksums)

## Test plan
- Unit tests: N/A (this is an E2E test taskcard)
- Integration tests: `tests/e2e/test_tc_522_pilot_cli.py`
- Determinism proof: Run pilot twice, compare SHA256 of `page_plan.json`

## E2E verification
**Concrete command(s) to run:**
```bash
python scripts/run_pilot_e2e.py --pilot pilot-aspose-3d-foss-python --output artifacts/pilot_e2e_cli_report.json
python -m pytest tests/e2e/test_tc_522_pilot_cli.py -v
```

**Expected artifacts:**
- artifacts/pilot_e2e_cli_report.json (pass/fail status, checksums)
- artifacts/page_plan.json (matches expected_page_plan.json)
- artifacts/validation_report.json (matches expected_validation_report.json)

**Success criteria:**
- [ ] Pilot runs to completion
- [ ] Actual page_plan.json matches expected_page_plan.json
- [ ] Actual validation_report.json matches expected_validation_report.json
- [ ] Two consecutive runs produce identical outputs (determinism)

> This taskcard IS the E2E harness for CLI execution.

## Integration boundary proven
What upstream/downstream wiring was validated:
- Upstream: TC-530 (CLI entrypoints invoke orchestrator)
- Downstream: Validation proves full pipeline works E2E
- Contracts: page_plan.schema.json, validation_report.schema.json, determinism per specs/10

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
- [ ] Tests include positive and negative cases
- [ ] E2E verification command documented and tested
- [ ] All outputs are written atomically per specs/10_determinism_and_caching.md
- [ ] No manual content edits made (compliance with no_manual_content_edits policy)
- [ ] Determinism verified by running task twice and comparing artifacts byte-for-byte
- [ ] All spec references listed in taskcard were consulted during implementation
- [ ] Evidence files (report.md, self_review.md) include all required sections and command outputs
- [ ] No placeholder values (PIN_ME, TODO, FIXME, etc.) remain in production code paths

## Deliverables
- Code: `scripts/run_pilot_e2e.py`
- Tests: `tests/e2e/test_tc_522_pilot_cli.py`
- Docs/specs/plans: None
- Reports (required):
  - reports/agents/__AGENT__/TC-522/report.md
  - reports/agents/__AGENT__/TC-522/self_review.md

## Acceptance checks
- [ ] Pilot E2E script exists and is executable
- [ ] Script compares actual vs expected artifacts
- [ ] Script verifies determinism (two runs)
- [ ] E2E test passes
- [ ] Reports written with checksums and commands

## Self-review
Use `reports/templates/self_review_12d.md`.
