---
id: TC-522
title: "Pilot E2E CLI execution and determinism verification"
status: Done
owner: "TELEMETRY_AGENT"
updated: "2026-01-28"
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

- `scripts/run_pilot_e2e.py`
- `tests/e2e/test_tc_522_pilot_cli.py`
- `reports/agents/**/TC-522/**`## Implementation steps
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

### Failure mode 1: CLI pilot execution exits with 0 despite validation failure
**Detection:** Pilot run fails validation but script exits successfully (exit code 0); CI pipeline passes when it should fail; validation_report.json shows ok=false but no error propagated
**Resolution:** Review exit code logic in run_pilot_e2e.py; ensure script exits with code 2 when validation fails per specs/01_system_contract.md; verify validation_report.json.ok field checked before exit; check that CLI propagates orchestrator exit code; test with failing pilot to confirm non-zero exit
**Spec/Gate:** specs/01_system_contract.md (exit code contract), specs/19_toolchain_and_ci.md (CI integration)

### Failure mode 2: Expected-vs-actual comparison fails on whitespace differences despite semantic equivalence
**Detection:** Artifact comparison reports diff for page_plan.json but only whitespace/formatting differs; semantically identical JSON reported as mismatch; pilot marked as failed incorrectly
**Resolution:** Review comparison logic in run_pilot_e2e.py; ensure JSON parsed and re-serialized with canonical formatting before SHA256 comparison; apply json.dumps(sort_keys=True, indent=2) to both expected and actual; verify comparison uses normalized bytes not raw file bytes; document canonical JSON requirement
**Spec/Gate:** specs/10_determinism_and_caching.md (canonical JSON writer), Gate H (byte-level determinism)

### Failure mode 3: Determinism check passes on first comparison but fails on subsequent runs
**Detection:** First two runs produce matching checksums but third run differs; SHA256 comparison succeeds initially but regression detected later; unstable determinism
**Resolution:** Review artifact generation for hidden sources of non-determinism (e.g., dict iteration, set ordering, filesystem traversal); ensure all lists sorted before serialization; check for timestamp fields that should be normalized; verify no random UUIDs or temp file names in outputs; run determinism check 3+ times to confirm stability
**Spec/Gate:** specs/10_determinism_and_caching.md (determinism requirements), Gate H (determinism validation), TC-560 (determinism harness)

### Failure mode 4: CLI pilot script doesn't clean up temp RUN_DIR causing disk space issues
**Detection:** Multiple pilot E2E runs accumulate temp directories; disk space fills up; old RUN_DIR directories not removed; cleanup not triggered on failure
**Resolution:** Add cleanup logic to run_pilot_e2e.py; ensure RUN_DIR removed after successful comparison unless --keep-artifacts flag set; implement try/finally block for cleanup on exception; document cleanup behavior in script help; add --cleanup flag for explicit control; log cleanup operations
**Spec/Gate:** specs/11_state_and_events.md (RUN_DIR lifecycle), specs/19_toolchain_and_ci.md (CI resource management)

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
