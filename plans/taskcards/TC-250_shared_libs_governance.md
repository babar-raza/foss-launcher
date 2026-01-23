---
id: TC-250
title: "Shared libraries governance and single-writer enforcement"
status: Ready
owner: "unassigned"
updated: "2026-01-22"
depends_on:
  - TC-200
allowed_paths:
  - src/launch/models/**
  - tests/unit/models/**
  - reports/agents/**/TC-250/**
evidence_required:
  - reports/agents/<agent>/TC-250/report.md
  - reports/agents/<agent>/TC-250/self_review.md
  - "Test output: model validation tests"
---

# Taskcard TC-250 — Shared libraries governance and single-writer enforcement

## Objective
Establish **single-writer governance** for shared library directories and implement foundational data models to prevent merge conflicts in swarm execution.

## Required spec references
- specs/11_state_and_events.md
- specs/10_determinism_and_caching.md
- plans/swarm_coordination_playbook.md

## Scope
### In scope
- Define shared data models in `src/launch/models/**`
- Document single-writer ownership rules
- Minimal shared model interfaces (State, Event, Artifact base classes)
- Tests proving model stability

### Out of scope
- Worker-specific implementations (handled by TC-400+)
- Full state management logic (handled by TC-300)

## Non-negotiables (binding for this task)
- **Single-writer enforcement**: This taskcard is the ONLY taskcard allowed to create new files in `src/launch/models/**`
- **No improvisation**: All models must map to spec-defined schemas
- **Determinism**: Models must support stable serialization
- **Evidence**: Any model design decision must cite spec reference

## Preconditions / dependencies
- TC-200 must be complete (IO/schema validation available)
- Swarm coordination playbook defines shared lib rules

## Inputs
- `specs/schemas/*.schema.json` - Schema definitions for artifacts
- `specs/11_state_and_events.md` - Event and state structure
- `specs/21_worker_contracts.md` - Worker input/output contracts

## Outputs
- `src/launch/models/__init__.py` - Model exports
- Base model classes:
  - `State` - Represents orchestrator state
  - `Event` - Represents state transition events
  - `Artifact` - Base for all artifact types
- Schema-mapped models as needed

## Allowed paths
- src/launch/models/**
- tests/unit/models/**
- reports/agents/**/TC-250/**
## Implementation steps
1) **Define base model interfaces**:
   - Create base classes that map to schema definitions
   - Support stable serialization (to/from dict)
   - Validation hooks using TC-200 schema validation
2) **State model**:
   - Represent current orchestrator state per `specs/state-graph.md`
   - Support snapshot serialization
3) **Event model**:
   - Represent state transitions and worker events
   - Support ndjson serialization per `specs/11_state_and_events.md`
4) **Artifact models** (minimal):
   - Base Artifact class with common metadata
   - Can be extended by worker-specific taskcards later
5) **Tests**:
   - Model serialization is stable (same object => identical bytes)
   - Schema validation integration works

## Test plan
- Unit tests:
  - Model construction and validation
  - Serialization stability (deterministic output)
  - Schema compliance (using TC-200 validators)
- No integration tests required (models are passive data containers)

## E2E verification
**Concrete command(s) to run:**
```bash
python -m pytest tests/unit/models/ -v
```

**Expected artifacts:**
- src/launch/models/product_facts.py
- src/launch/models/evidence_map.py

**Success criteria:**
- [ ] Model validation tests pass
- [ ] Single-writer violations detected by linter

> If E2E harness not yet implemented, this defines the stub contract for TC-520/522/523.

## Integration boundary proven
What upstream/downstream wiring was validated:
- Upstream: TC-200 (base schemas)
- Downstream: TC-411..TC-413 (facts workers), TC-430..TC-440 (planning workers)
- Contracts: ProductFacts, EvidenceMap, TruthLock model schemas

## Deliverables
- Code:
  - `src/launch/models/` module with base classes
- Tests:
  - `tests/unit/models/` test suite
- Reports (required):
  - reports/agents/<agent>/TC-250/report.md
  - reports/agents/<agent>/TC-250/self_review.md

## Acceptance checks
- [ ] Models support stable serialization
- [ ] Models validate against corresponding schemas
- [ ] Tests pass and prove determinism
- [ ] No other taskcards modify `src/launch/models/**` (verified via allowed_paths audit)
- [ ] Agent reports are written

## Self-review
Use `reports/templates/self_review_12d.md`. Any dimension <4 must include a concrete fix plan.

## Shared Library Ownership Registry

This section documents the **single-writer ownership** for shared libraries:

| Directory | Owner Taskcard | Change Protocol |
|---|---|---|
| `src/launch/io/**` | TC-200 | Blocker issue + coordination required |
| `src/launch/util/**` | TC-200 | Blocker issue + coordination required |
| `src/launch/models/**` | TC-250 (this taskcard) | Blocker issue + coordination required |
| `src/launch/clients/**` | TC-500 | Blocker issue + coordination required |

**Rule**: No other taskcard may add or modify files in these directories without explicit coordination and dependency declaration.

**Exception process**:
1. Write blocker issue documenting required change
2. Either:
   - Update this taskcard's scope and allowed_paths, OR
   - Create a micro-taskcard with explicit permission
3. Add dependency in requesting taskcard
