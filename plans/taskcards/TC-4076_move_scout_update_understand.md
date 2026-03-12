---
id: TC-4076
title: "Move scout.py to scout worker; update UnderstandWorker to accept ScoutBundle"
status: Done
retroactive: true
priority: High
owner: agent
updated: "2026-03-11"
tags: [phase2, scout, understand, refactor]
depends_on: [TC-4075]
allowed_paths:
  - plans/taskcards/TC-4076_move_scout_update_understand.md
  - src/launcher/workers/scout/scout.py
  - src/launcher/workers/understand/scout.py
  - src/launcher/workers/understand/worker.py
evidence_required:
  - reports/TC-4076/evidence.md
---

# Taskcard TC-4076 — Move scout.py + Update UnderstandWorker

> **Retroactive taskcard** (THS-01). Implementation was completed without this
> taskcard file.

## Objective

Move Scout logic (`scout.py`) from `workers/understand/` to `workers/scout/`.
Leave a re-export shim at the old path for backward compatibility.
Update `UnderstandWorker` to accept `ScoutBundle` as input instead of
`IntakeBundle`, removing the internal Phase A Scout call.

## Allowed paths

- plans/taskcards/TC-4076_move_scout_update_understand.md
- src/launcher/workers/scout/scout.py
- src/launcher/workers/understand/scout.py
- src/launcher/workers/understand/worker.py

## Implementation (as built)

1. `src/launcher/workers/scout/scout.py` — Scout logic relocated here.
   Contains `run_scout()`, `_walk_file_tree()`, `_read_repo_content()`,
   `_extract_shared_facts()`, and all budget/category constants.

2. `src/launcher/workers/understand/scout.py` — Re-export shim:
   ```python
   """Re-export shim — scout logic has moved to launcher.workers.scout.scout."""
   from launcher.workers.scout.scout import (
       _BUDGET_LOG_MAX, _CATEGORY_PRIORITY, _DEFAULT_BUDGET_BYTES, ...
   )  # noqa: F401
   ```
   Shim exists to preserve backward compatibility for any code using
   `from launcher.workers.understand.scout import ...`.
   Removal is tracked in THS-10.

3. `src/launcher/workers/understand/worker.py` — Updated:
   - Input type changed from `IntakeBundle` to `ScoutBundle`
   - Phase A Scout call removed (lines 74–93 removed)
   - Content access: `repo_content = context.repo_content` (from ScoutWorker)
   - Resume fallback: when `context.repo_content is None`, files re-read
     from disk using ScoutBundle's file_index

## Failure modes

1. Re-export shim import path wrong → `ImportError` at startup
2. `context.repo_content is None` on non-resume run → resume fallback
   incorrectly triggered (mitigated by ScoutWorker always setting it)
3. UnderstandWorker receives IntakeBundle instead of ScoutBundle → Pydantic
   validation error with clear message

## Acceptance checks

- [x] `from launcher.workers.scout.scout import run_scout` succeeds
- [x] `from launcher.workers.understand.scout import run_scout` succeeds (shim works)
- [x] `UnderstandWorker.run()` accepts ScoutBundle (not IntakeBundle)
- [x] `test_run_scout_importable_from_understand_scout` passes in test_scout.py
- [x] Scout Phase A code no longer present in `workers/understand/worker.py`

## Evidence

See `reports/TC-4076/evidence.md`.
