# Agent A / GOV-1 — Plan

## Summary

GOV-1 commits the 152 tracked modified files (` M` in `git status`) accumulated across sessions 13–20 into 10 logical batches, creating a clear audit trail.

## Taskcard

TC-5200 (`plans/taskcards/TC-5200_gov1-commit-working-tree.md`) — In-Progress

## Batches

| Batch | Component | Files |
|-------|-----------|-------|
| A | src/launcher/models/ | 6 files |
| B | src/launcher/workers/understand/ | 10 files |
| C | src/launcher/workers/evaluate/ | 10 files |
| D | src/launcher/workers/generate/ + prompts/ | 5 files |
| E | src/launcher/workers/planner/ | 2 files |
| F | src/launcher/orchestrator/ + cli/ + shared/ | 10 files |
| G | workers/scout/ + intake/ + publish/ | 6 files |
| H | tests/ | 18 files |
| I | configs/ + specs/ + deploy/ + snapshots/ + intake/ + phase_store/ | ~75 files |
| J | agents.md + .claude/ | 2 files |

## Secondary deliverables (same session)

- GOV-2: `agents.md` __pycache__ cleanup section
- GOV-3: `scripts/check_tc_evidence.py`
- Governance files: PLAN_SOURCES.md, PLAN_INDEX.md, TASK_BACKLOG.md, from_chat plan
