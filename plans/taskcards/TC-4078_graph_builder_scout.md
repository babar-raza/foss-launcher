---
id: TC-4078
title: "Register ScoutWorker in orchestrator graph builder"
status: Done
retroactive: true
priority: High
owner: agent
updated: "2026-03-11"
tags: [phase2, scout, orchestrator, graph]
depends_on: [TC-4075, TC-4077]
allowed_paths:
  - plans/taskcards/TC-4078_graph_builder_scout.md
  - src/launcher/orchestrator/graph_builder.py
evidence_required:
  - reports/TC-4078/evidence.md
---

# Taskcard TC-4078 — Graph Builder Scout Registration

> **Retroactive taskcard** (THS-01). Implementation was completed without this
> taskcard file.

## Objective

Add `ScoutWorker` to the orchestrator's graph builder so that the pipeline
executes Scout between Intake and Understand. Update heal-loop bypass logic
to include Scout in the set of workers that can be skipped when heal targets
a downstream phase.

## Allowed paths

- plans/taskcards/TC-4078_graph_builder_scout.md
- src/launcher/orchestrator/graph_builder.py

## Implementation (as built)

`src/launcher/orchestrator/graph_builder.py` changes:
1. `"scout"` worker name added to the worker dispatch block:
   ```python
   elif worker_name == "scout":
       # TC-4078: Scout takes IntakeBundle as input
       # (ScoutBundle input type resolved at runtime via graph)
   ```
2. `ScoutBundle` import added for type handling in the Understand dispatch:
   ```python
   from launcher.models.scout import ScoutBundle
   model = ScoutBundle
   ```
3. Heal loop bypass logic updated: `"scout"` added to `bypass_candidates`
   alongside `"understand"` and `"planner"`. When `heal_metadata.responsible_worker
   == "generate"`, Scout checkpoint is also preserved (Scout is slow — full
   file I/O — so it should not be re-triggered by a generate heal).

## Failure modes

1. ScoutWorker not registered → pipeline stops at intake with no next step
2. Scout not in bypass_candidates → heal loop re-triggers Scout on every
   generate fix (performance regression)
3. ScoutBundle import fails → understand dispatch crashes at graph build time

## Acceptance checks

- [x] `graph_builder.py` handles `worker_name == "scout"`
- [x] `"scout"` added to heal-loop bypass candidates
- [x] `ScoutBundle` imported in graph_builder for understand dispatch
- [x] Pipeline runs end-to-end (scout → understand → planner → generate → evaluate → publish)
- [x] Tests in `tests/unit/orchestrator/test_graph_builder.py` pass

## Evidence

See `reports/TC-4078/evidence.md`.
