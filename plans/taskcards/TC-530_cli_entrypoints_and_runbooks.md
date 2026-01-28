---
id: TC-530
title: "CLI entrypoints and runbooks"
status: Ready
owner: "unassigned"
updated: "2026-01-22"
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
