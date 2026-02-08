---
id: TC-530
title: "CLI entrypoints and runbooks"
status: Done
owner: "CLI_AGENT"
updated: "2026-01-28"
depends_on:
  - TC-300
  - TC-460
allowed_paths:
  - src/launch/cli.py
  - src/launch/mcp/server.py
  - docs/cli_usage.md
  - README.md
  - tests/unit/test_tc_530_entrypoints.py
  - reports/agents/**/TC-530/**
evidence_required:
  - reports/agents/<agent>/TC-530/report.md
  - reports/agents/<agent>/TC-530/self_review.md
spec_ref: f48fc5dbb12c5513f42aabc2a90e2b08c6170323
ruleset_version: ruleset.v1
templates_version: templates.v1
---

# Taskcard TC-530 — CLI entrypoints and runbooks

## Objective
Provide CLI entrypoints and operational runbooks so the system can be run locally and in CI with reproducible commands and clear failure handling.

## Required spec references
- specs/19_toolchain_and_ci.md
- specs/29_project_repo_structure.md
- specs/11_state_and_events.md
- specs/12_pr_and_release.md
- plans/acceptance_test_matrix.md

## Scope
### In scope
- CLI commands for:
  - launch run
  - validate run
  - run pilots
  - start MCP server
- Operator runbooks: setup, common failures, escalation steps
- Exit code mapping aligned with `specs/01_system_contract.md`

### Out of scope
- GUI/interactive interface
- Full release automation beyond docs

## Inputs
- A validated run_config file
- Required env vars (telemetry token, github token, etc.) as documented
- Local toolchain installed per `specs/19_toolchain_and_ci.md`

## Outputs
- CLI modules or console scripts callable in CI
- Documentation:
  - README updates and/or `docs/runbooks/*.md`
- Example command lines and expected outputs

## Allowed paths
- src/launch/cli.py
- src/launch/mcp/server.py
- docs/cli_usage.md
- README.md
- tests/unit/test_tc_530_entrypoints.py
- reports/agents/**/TC-530/**

Note: Console scripts in pyproject.toml are already defined by TC-100. TC-530 enhances existing CLI implementations but does not modify entrypoint declarations. The `launch_validate` command implementation is owned by TC-570.
## Implementation steps
1) Define CLI interface (argparse/typer) and document command surface.
2) Implement CLI wrappers that call orchestrator runner (TC-300) and validator runner.
3) Ensure CLIs:
   - create RUN_DIR as needed
   - print run_id and key paths
   - return correct exit codes
4) Write runbooks covering:
   - setup
   - running a pilot
   - interpreting validation failures
   - known failure modes (network, commit service, telemetry)
5) Add smoke tests for CLI help and minimal invocation (mocked where needed).

## E2E verification
**Concrete command(s) to run:**
```bash
# After pip install -e .
launch_run --help
launch_validate --help
launch_mcp --help

# Or directly via Python
python -c "from launch.cli import main; main()" --help
python -c "from launch.validators.cli import main; main()" --help
python -c "from launch.mcp.server import main; main()" --help
```

**Expected artifacts:**
- src/launch/cli.py
- src/launch/validators/cli.py
- src/launch/mcp/server.py

**Success criteria:**
- [ ] All three CLI help commands display correctly
- [ ] Console scripts are registered in pyproject.toml
- [ ] Commands accept documented flags

> If E2E harness not yet implemented, this defines the stub contract for TC-520/522/523.

## Integration boundary proven
What upstream/downstream wiring was validated:
- Upstream: TC-300 (orchestrator)
- Downstream: Human operators, CI pipelines
- Contracts: CLI argument spec in docs/

## Failure modes

### Failure mode 1: CLI exits with wrong exit code breaking CI pipeline integration
**Detection:** Validation fails but launch_validate exits with 0; CI pipeline passes when it should fail; validation_report.json shows ok=false but exit code doesn't reflect failure
**Resolution:** Review exit code mapping in launch_validate CLI; ensure exit 2 on validation failure per specs/01_system_contract.md; verify exit 1 on runtime error/crash; check exit 0 only when ok=true; test with failing validation gate to confirm non-zero exit; document exit code contract in CLI help text
**Spec/Gate:** specs/01_system_contract.md (exit code contract), specs/19_toolchain_and_ci.md (CI integration)

### Failure mode 2: CLI help text missing or incomplete causing operator confusion
**Detection:** launch_run --help doesn't show required arguments; unclear which flags are mandatory; no examples provided; operators can't determine correct usage
**Resolution:** Review CLI argument parser definition; ensure --help shows all required and optional flags with descriptions; add usage examples in help text; document default values for optional args; verify help text matches documented behavior in docs/cli_usage.md; test help output readability
**Spec/Gate:** specs/19_toolchain_and_ci.md (CLI documentation), docs/cli_usage.md (usage reference)

### Failure mode 3: CLI creates RUN_DIR without validating write permissions causing late failure
**Detection:** RUN_DIR creation succeeds but later writes fail with permission denied; partial artifacts left in read-only directory; unclear error message; run aborts after significant work
**Resolution:** Add write permission check before creating RUN_DIR; test write access by creating test file in parent directory; emit clear error if insufficient permissions; suggest alternative RUN_DIR location in error message; fail fast with actionable message; document RUN_DIR requirements in runbook
**Spec/Gate:** specs/11_state_and_events.md (RUN_DIR structure), docs/runbooks/setup.md (environment requirements)

### Failure mode 4: CLI doesn't validate run_config before starting expensive operations
**Detection:** Orchestrator runs for minutes then fails due to invalid run_config; required fields missing; schema validation error after clone operation; wasted time and resources
**Resolution:** Add run_config schema validation at CLI entry point before invoking orchestrator; use jsonschema to validate against specs/schemas/run_config.schema.json; emit BLOCKER issue if validation fails with field-level error details; fail fast with config validation errors; document run_config structure in CLI help; suggest example config path
**Spec/Gate:** specs/schemas/run_config.schema.json (config contract), Gate C (schema validation), specs/01_system_contract.md (fail-fast principle)

## Task-specific review checklist
Beyond the standard acceptance checks, verify:
- [ ] All outputs are written atomically per specs/10_determinism_and_caching.md
- [ ] No manual content edits made (compliance with no_manual_content_edits policy)
- [ ] Determinism verified by running task twice and comparing artifacts byte-for-byte
- [ ] All spec references listed in taskcard were consulted during implementation
- [ ] Evidence files (report.md, self_review.md) include all required sections and command outputs
- [ ] No placeholder values (PIN_ME, TODO, FIXME, etc.) remain in production code paths

## Deliverables
- Code:
  - CLI entrypoints
- Docs:
  - runbooks + README updates
- Tests:
  - CLI smoke tests
- Reports (required):
  - reports/agents/<agent>/TC-530/report.md
  - reports/agents/<agent>/TC-530/self_review.md

## Acceptance checks
- [ ] `launch_run --help` (after install) displays help
- [ ] `launch_validate --help` (after install) displays help
- [ ] `launch_mcp --help` (after install) displays help
- [ ] Exit codes match documented mapping
- [ ] Runbooks exist and reference actual commands
- [ ] Tests passing

## Self-review
Use `reports/templates/self_review_12d.md`. Any dimension <4 must include a concrete fix plan.
