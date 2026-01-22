---
id: TC-300
title: "Orchestrator graph wiring and run loop"
status: Ready
owner: "unassigned"
updated: "2026-01-22"
depends_on:
  - TC-200
allowed_paths:
  - src/launch/orchestrator/**
  - src/launch/state/**
  - tests/unit/orchestrator/test_tc_300_graph.py
  - tests/integration/test_tc_300_run_loop.py
  - reports/agents/**/TC-300/**
evidence_required:
  - reports/agents/<agent>/TC-300/report.md
  - reports/agents/<agent>/TC-300/self_review.md
---

# Taskcard TC-300 — Orchestrator graph wiring and run loop

## Objective
Implement the orchestrator’s **state-graph wiring** and run loop so that workers W1–W9 can be executed deterministically with correct state transitions, event logging, and stop-the-line gate semantics.

## Required spec references
- specs/state-graph.md
- specs/state-management.md
- specs/11_state_and_events.md
- specs/21_worker_contracts.md
- specs/09_validation_gates.md
- plans/00_orchestrator_master_prompt.md
- plans/acceptance_test_matrix.md

## Scope
### In scope
- Orchestrator graph definition and transitions (stub workers acceptable; full worker behavior is in TC-400+)
- RUN_DIR creation + canonical layout
- Event log append (ndjson) and snapshot updates
- Stop-the-line behavior when a worker emits a BLOCKER/FAILED condition

### Out of scope
- Worker internals (RepoScout/FactsBuilder/etc.)
- Commit/PR logic (TC-480 / TC-500 / commit service)

## Inputs
- Validated run_config (from TC-200 utilities)
- `specs/21_worker_contracts.md` describing required worker IO contracts
- Optional: resume-from-snapshot inputs (if specified by state mgmt spec)

## Outputs
- `RUN_DIR/events.ndjson` and `RUN_DIR/snapshot.json` updated throughout
- Structured runner output indicating final state and exit code
- Deterministic worker invocation ordering and retry semantics per specs

## Allowed paths
- src/launch/orchestrator/**
- src/launch/state/**
- tests/unit/orchestrator/test_tc_300_graph.py
- tests/integration/test_tc_300_run_loop.py
- reports/agents/**/TC-300/**
## Implementation steps
1) **Graph definition**:
   - define states and transitions exactly per `specs/state-graph.md`
   - ensure transitions are explicit (no implicit fallthrough)
2) **Run lifecycle**:
   - create RUN_DIR structure (see `specs/29_project_repo_structure.md`)
   - initialize snapshot with run metadata (resolved SHAs when available)
   - append events for each transition
3) **Worker invocation contract**:
   - call each worker with (RUN_DIR, run_config, snapshot)
   - enforce that workers write only within allowed paths (write fence) via IO layer checks
4) **Stop-the-line**:
   - if validation gate fails or BLOCKER emitted: stop and mark snapshot accordingly
   - if fix loop allowed: transition to FIXING with bounded attempts
5) **Tests**:
   - a graph “smoke” test with stub workers proving correct ordering, events, and stop behavior
   - determinism test: same stub inputs => identical event bytes (except explicitly allowed fields)

## Deliverables
- Code:
  - orchestrator graph + runner
- Tests:
  - ordering + stop-the-line test
  - determinism test for events/snapshot serialization
- Reports (required):
  - reports/agents/<agent>/TC-300/report.md
  - reports/agents/<agent>/TC-300/self_review.md

## Acceptance checks
- [ ] Orchestrator transitions match `specs/state-graph.md`
- [ ] events.ndjson and snapshot.json produced and update over time
- [ ] stop-the-line behavior triggers correctly on BLOCKER/FAILED
- [ ] tests pass and show deterministic ordering
- [ ] Agent reports are written

## Self-review
Use `reports/templates/self_review_12d.md`. Any dimension <4 must include a concrete fix plan.
