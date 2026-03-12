---
id: TC-4075
title: "Create ScoutWorker — extract Scout phase into standalone pipeline worker"
status: Done
retroactive: true
priority: High
owner: agent
updated: "2026-03-11"
tags: [phase2, scout, worker, refactor]
depends_on: [TC-4074]
allowed_paths:
  - plans/taskcards/TC-4075_scout_worker_implementation.md
  - src/launcher/workers/scout/__init__.py
  - src/launcher/workers/scout/worker.py
evidence_required:
  - reports/TC-4075/evidence.md
---

# Taskcard TC-4075 — Create ScoutWorker

> **Retroactive taskcard** (THS-01). Implementation was completed without this
> taskcard file. This document retroactively describes what was built and
> verifies the acceptance checks against the current codebase.

## Objective

Create `ScoutWorker` as a standalone pipeline worker that takes `IntakeBundle`
as input and produces `ScoutBundle` as output. Scout was previously embedded
inside `UnderstandWorker` as a private Phase A — extracting it enables
independent verification, targeted heal-loop re-runs, and clean resume
semantics for the Understand phase.

## Required spec references

- `specs/system_contract.md` (WorkerContract interface)
- `specs/worker_understand.md` (Scout phase responsibility)
- tender-hugging-shamir.md Phase 2, TC-4075

## Scope

### In scope
- `src/launcher/workers/scout/__init__.py` (package init)
- `src/launcher/workers/scout/worker.py` (ScoutWorker implementation)

### Out of scope
- Moving scout.py (TC-4076)
- pipeline.yaml changes (TC-4077)
- Graph builder changes (TC-4078)

## Inputs

- `src/launcher/workers/scout/scout.py` — Scout logic (moved from understand/)
- `src/launcher/models/scout.py` — ScoutBundle model (TC-4074)
- `src/launcher/models/intake.py` — IntakeBundle (input type)

## Outputs

- `src/launcher/workers/scout/__init__.py`
- `src/launcher/workers/scout/worker.py`

## Allowed paths

- plans/taskcards/TC-4075_scout_worker_implementation.md
- src/launcher/workers/scout/__init__.py
- src/launcher/workers/scout/worker.py

## Implementation (as built)

`ScoutWorker` implements `WorkerContract`:
- `name` property returns `"scout"`
- `run(input_data, context)` accepts IntakeBundle, calls `run_scout()` from
  `scout.scout`, sets `context.repo_content`, writes scout artifact, returns ScoutBundle
- `self_review(output)` checks files_enumerated > 0 and content_files_read > 0
  (severity=high), package_name present (severity=medium)

## Failure modes

1. `repo_dir` does not exist → `ValueError` raised immediately in `run()`
2. Scout returns 0 files (empty repo) → self_review fails with high severity
3. context.repo_content not set → UnderstandWorker resume path must handle None

## Acceptance checks

- [x] `from launcher.workers.scout.worker import ScoutWorker` succeeds
- [x] `ScoutWorker().name == "scout"`
- [x] `ScoutWorker` implements `WorkerContract` interface
- [x] `run()` sets `context.repo_content` after successful scout
- [x] `self_review()` fails with high severity when files_enumerated == 0
- [x] Tests in `tests/unit/workers/test_scout.py` cover all above paths

## Evidence

See `reports/TC-4075/evidence.md`.
