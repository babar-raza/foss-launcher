---
id: TC-A01
title: "Map current Phase 1 architecture and responsibility split"
status: In-Progress
priority: High
owner: "Repo Analyst"
updated: "2026-03-13"
tags: [phase1, intake, architecture, analysis]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-A01_phase1_architecture_map.md
  - reports/TC-A01/evidence.md
evidence_required:
  - reports/TC-A01/evidence.md
---

# Taskcard TC-A01 - Map current Phase 1 architecture and responsibility split

## Objective

Produce the true current-state map of Phase 1 by documenting what the pipeline `IntakeWorker` does, what the broader `src/launcher/intake/` subsystem does, where they connect, and where the boundary is structurally weak.

## Required spec references

- `CLAUDE.md` (Section: AG-002 taskcard-first workflow)
- `agents.md` (Section 1: protected-path discipline, Section 2: pipeline architecture)
- `plans/twinkly-puzzling-minsky.md` (Rule 4, Rule 7, Rule 9, Phase 1/2 architecture)

## Scope

### In scope
- Current file-path inventory for Phase 1 code and CLI entrypoints
- Symbol map for the pipeline worker and the intake subsystem
- Actual call-path map for pipeline execution and CLI discovery/onboarding execution
- Responsibility overlap, gaps, and mismatch summary

### Out of scope
- Code changes to `src/launcher/**`
- Phase 2 Understand redesign
- Final architecture decisions for Phase 1 refactor

## Inputs

- `src/launcher/workers/intake/worker.py`
- `src/launcher/workers/intake/clone.py`
- `src/launcher/intake/__init__.py`
- `src/launcher/intake/config_loader.py`
- `src/launcher/intake/org_scanner.py`
- `src/launcher/intake/repo_classifier.py`
- `src/launcher/intake/config_generator.py`
- `src/launcher/intake/scheduler.py`
- `src/launcher/shared/identity.py`
- `src/launcher/models/intake.py`
- `src/launcher/cli/intake.py`
- `src/launcher/orchestrator/run_loop.py`
- `src/launcher/orchestrator/graph_builder.py`
- intake-related unit/integration tests

## Outputs

- This taskcard with analysis scope and gates
- `reports/TC-A01/evidence.md` containing the architecture map and mismatch summary

## Allowed paths

- plans/taskcards/TC-A01_phase1_architecture_map.md
- reports/TC-A01/evidence.md

### Allowed paths rationale

TC-A01 is analysis-only. It authorizes the taskcard itself and a written evidence pack, but no source edits.

## Implementation steps

### Step 1: Build the file-path and symbol inventory

Read the Phase 1 worker, shared identity module, intake subsystem modules, CLI entrypoints, and intake-related tests. Capture the file list and exported/important symbols.

### Step 2: Map the actual call paths

Trace how the pipeline reaches `IntakeWorker`, how CLI `launch intake ...` commands reach `org_scanner`, `repo_classifier`, `config_generator`, and `scheduler`, and where the two flows intersect.

### Step 3: Document mismatches and structural weakness

Write the before-state report with overlap, disconnection points, test coupling, duplicated heuristics, and failure semantics that matter for downstream trust.

## Failure modes

### Failure mode 1: Analysis omits a relevant Phase 1 entrypoint

**Detection**: The evidence report lacks either the pipeline worker path or CLI/subsystem path.
**Resolution**: Re-run the symbol search across `src/launcher/workers/intake`, `src/launcher/intake`, `src/launcher/cli`, and orchestrator references; update the map.
**Gate**: TC-A01 exit criteria; user Phase 1 evidence requirement.

### Failure mode 2: Analysis confuses design intent with actual runtime behavior

**Detection**: Claims rely on comments/docstrings without confirming imports or call sites.
**Resolution**: Add direct call-path evidence from `run_loop.py`, `graph_builder.py`, and `cli/intake.py`.
**Gate**: Evidence-first requirement; no architecture decision without actual call-path proof.

### Failure mode 3: Analysis jumps into refactor recommendations without a stable before-state

**Detection**: Proposed fixes appear before the current split, overlap, and gaps are explicitly written.
**Resolution**: Separate TC-A01 before-state mapping from TC-A02 target-architecture decision.
**Gate**: Sequencing rule; Phase 1 must progress taskcard-by-taskcard.

## Task-specific review checklist

1. [x] File-path list includes both `src/launcher/workers/intake/**` and `src/launcher/intake/**`
2. [x] Symbol map identifies major public and decision-making functions
3. [x] Pipeline call path is traced from orchestrator discovery to `IntakeWorker.run()`
4. [x] CLI call path is traced from `launch intake` commands to scanner/classifier/generator/scheduler
5. [x] Mismatch summary distinguishes overlap, gaps, and coupling
6. [x] No source edits were made under protected paths during TC-A01
7. [x] Docstrings updated for all new/changed public functions
8. [x] Spec file updated if worker behavior changed (or confirmed no spec drift)
9. [x] Schema `"description"` fields present for all new/changed properties
10. [x] Checked `docs/README.md` ownership map - no trigger event applies
11. [x] If a new `docs/guides/` file was added: `docs/README.md` index updated

## Deliverables

1. `plans/taskcards/TC-A01_phase1_architecture_map.md`
2. `reports/TC-A01/evidence.md`

## Acceptance checks

1. [x] Clear architecture map exists with file-path list and symbol map
2. [x] Actual call-path map exists for pipeline and CLI intake flows
3. [x] Responsibility overlap and gaps are documented with file-path evidence

## Self-review

### Verification results
- [x] Tests: not applicable for analysis-only taskcard
- [x] Validation: evidence report cross-checked against source files
- [x] Evidence captured: `reports/TC-A01/evidence.md`
- [x] Doc freshness: not applicable; no `src/launcher/**`, `specs/**`, or protected config/schema edits

## E2E verification

```bash
rg -n "create_worker|intake_app|scan_orgs|classify_repo|generate_config|schedule|clone_repo_cached" src/launcher
```

**Expected results**:
- The pipeline worker and CLI subsystem entrypoints are both discoverable
- The evidence report cites the same call graph shown by the source tree

## Integration boundary proven

**Upstream**: `RunConfig` and CLI arguments initiate Phase 1 flows.
**Downstream**: `IntakeBundle`, generated pilot configs, and intake reports feed later operator or pipeline work.
**Contract**: TC-A01 proves the current Phase 1 boundary as implemented, not as intended.
