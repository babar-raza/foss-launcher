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
  - src/launch/cli/**
  - src/launch/__main__.py
  - scripts/cli_runner.py
  - docs/cli_usage.md
  - README.md
  - tests/unit/cli/test_tc_530_entrypoints.py
  - reports/agents/**/TC-530/**
evidence_required:
  - reports/agents/<agent>/TC-530/report.md
  - reports/agents/<agent>/TC-530/self_review.md
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
- src/launch/cli/**
- src/launch/__main__.py
- scripts/cli_runner.py
- docs/cli_usage.md
- README.md
- tests/unit/cli/test_tc_530_entrypoints.py
- reports/agents/**/TC-530/**
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
- [ ] `python -m launch_run --help` and related commands work
- [ ] Exit codes match documented mapping
- [ ] Runbooks exist and reference actual commands
- [ ] Tests passing

## Self-review
Use `reports/templates/self_review_12d.md`. Any dimension <4 must include a concrete fix plan.
