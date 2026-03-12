---
id: TC-B01
title: "Map current Understand flow and artifact model"
status: In-Progress
priority: High
owner: "Repo Analyst"
updated: "2026-03-13"
tags: [phase2, understand, analysis]
depends_on:
  - TC-A08
allowed_paths:
  - plans/taskcards/TC-B01_understand_flow_map.md
  - reports/TC-B01/evidence.md
evidence_required:
  - reports/TC-B01/evidence.md
---

# Taskcard TC-B01 - Map current Understand flow and artifact model

## Objective

Produce a clear current-state map of the Understand phase, including the scout-to-understand handoff, extraction flow, artifact model, and self-review gates.

## Required spec references

- `src/launcher/workers/understand/worker.py`
- `src/launcher/workers/scout/worker.py`
- `src/launcher/workers/scout/scout.py`
- `src/launcher/models/understanding.py`

## Scope

### In scope
- file-path map
- symbol map
- data-flow map
- artifact inventory
- mismatch summary

### Out of scope
- refactoring
- Phase 2 contract redesign

## Inputs

- Understand worker implementation
- Scout worker implementation
- extraction modules
- understanding models

## Outputs

- current-state evidence report

## Allowed paths

- plans/taskcards/TC-B01_understand_flow_map.md
- reports/TC-B01/evidence.md

### Allowed paths rationale

TC-B01 is analysis-only and establishes the evidence base for all later Phase 2 decisions.

## Implementation steps

### Step 1: Map entrypoints and major symbols

### Step 2: Trace scout bundle input to understanding bundle output

### Step 3: Record artifact inventory and architectural mismatches

## Failure modes

### Failure mode 1: artifact model is described only from schemas, not code

**Detection**: no concrete symbol/file references.
**Resolution**: cite worker and model files directly.
**Gate**: evidence-first analysis requirement.

### Failure mode 2: self-review logic is omitted from the map

**Detection**: report ends at extraction assembly.
**Resolution**: include semantic checks and failure categories.
**Gate**: Phase 2 trust requirement.

### Failure mode 3: scout/understand boundary is assumed rather than traced

**Detection**: no explicit handoff path from `ScoutBundle` to `UnderstandingBundle`.
**Resolution**: record the actual call/data path.
**Gate**: architecture clarity requirement.

## Task-specific review checklist

1. [ ] file path map recorded
2. [ ] symbol map recorded
3. [ ] data flow map recorded
4. [ ] artifact inventory recorded
5. [ ] mismatch summary recorded

## Deliverables

1. `reports/TC-B01/evidence.md`

## Acceptance checks

1. [ ] current state documented clearly
2. [ ] evidence cites exact files
3. [ ] downstream redesign can use this map without re-discovery

## Self-review

### Verification results
- [ ] Evidence captured

## E2E verification

```bash
rg -n "def |class |self_review|run\\(" src/launcher/workers/understand src/launcher/workers/scout src/launcher/models/understanding.py
```

**Expected results**:
- core Understand and Scout control flow is mapped from code, not recalled from memory

## Integration boundary proven

**Upstream**: Phase 1 GO.
**Downstream**: TC-B02 target contract decision.
**Contract**: TC-B01 defines the real current state before any Understand redesign is attempted.
