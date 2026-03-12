---
id: TC-4077
title: "Add scout step to configs/pipeline.yaml; create scout_bundle.schema.json"
status: Done
retroactive: true
priority: High
owner: agent
updated: "2026-03-11"
tags: [phase2, scout, pipeline, config, schema]
depends_on: [TC-4074, TC-4075]
allowed_paths:
  - plans/taskcards/TC-4077_pipeline_yaml_scout_step.md
  - configs/pipeline.yaml
  - specs/schemas/scout_bundle.schema.json
evidence_required:
  - reports/TC-4077/evidence.md
---

# Taskcard TC-4077 — pipeline.yaml Scout Step

> **Retroactive taskcard** (THS-01). Implementation was partially completed
> without this taskcard file. `configs/pipeline.yaml` was updated. However,
> `specs/schemas/scout_bundle.schema.json` was NOT created — this is an
> open gap tracked in THS-06 (BudgetLogEntry schema) and requires a
> follow-up taskcard.

## Objective

Register the `scout` worker step in `configs/pipeline.yaml` between `intake`
and `understand`. Create the JSON Schema for ScoutBundle.

## Allowed paths

- plans/taskcards/TC-4077_pipeline_yaml_scout_step.md
- configs/pipeline.yaml
- specs/schemas/scout_bundle.schema.json

## Implementation (as built)

`configs/pipeline.yaml` updated with scout step:
```yaml
- worker: scout
  input_schema: intake_bundle.schema.json
  output_schema: scout_bundle.schema.json
  checkpoint: true
```

The `understand` step's `input_schema` was updated from
`intake_bundle.schema.json` to `scout_bundle.schema.json`.

**Known gap**: `specs/schemas/scout_bundle.schema.json` was NOT created.
The pipeline references it but the file does not exist. This means JSON
schema validation at the scout→understand boundary cannot run.
Tracked in THS-06 (which also adds BudgetLogEntry typing).

## Failure modes

1. `scout_bundle.schema.json` missing → schema validation skipped/fails silently
   for scout output (current state — open gap)
2. pipeline.yaml malformed → orchestrator fails to load pipeline at startup
3. understand step still references intake_bundle.schema.json →
   UnderstandWorker receives wrong schema for validation

## Acceptance checks

- [x] `configs/pipeline.yaml` contains `worker: scout` step
- [x] Scout step has `input_schema: intake_bundle.schema.json`
- [x] Scout step has `output_schema: scout_bundle.schema.json`
- [x] Scout step has `checkpoint: true`
- [x] Understand step has `input_schema: scout_bundle.schema.json`
- [ ] `specs/schemas/scout_bundle.schema.json` exists — **OPEN GAP** (THS-06)

## Evidence

See `reports/TC-4077/evidence.md`.
