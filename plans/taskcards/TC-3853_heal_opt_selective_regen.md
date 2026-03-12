---
id: TC-3853
title: "Heal Opt — Selective Page Regeneration (H5.1+H5.2)"
status: Done
priority: Medium
owner: "agent"
updated: "2026-03-08"
tags: [heal, optimization, generate]
depends_on: [TC-3851, TC-3852a, TC-3852b, TC-3852c]
allowed_paths:
  - plans/taskcards/TC-3853_heal_opt_selective_regen.md
  - src/launcher/orchestrator/worker_contract.py
  - src/launcher/workers/generate/worker.py
  - tests/unit/workers/test_selective_regen.py
  - reports/TC-3853/evidence.md
evidence_required:
  - reports/TC-3853/evidence.md
---

# Taskcard TC-3853 — Heal Opt: Selective Page Regeneration (H5.1+H5.2)

## Objective

H5.1: Add `heal_target_pages` to WorkerContext so generate worker can skip pages
not targeted for healing, reducing unnecessary LLM calls.

H5.2: Generate worker reads `heal_target_pages` and skips non-targeted pages
by reusing their existing content (rather than re-calling LLM for all pages).

NOTE: Graph builder worker-skip logic (routing past Understand+Planner) is
deferred — it requires deeper orchestrator surgery not justified by current scope.
The selective page skip inside generate/worker.py delivers most of the benefit.

## Scope

### In scope
- `heal_target_pages: list[str] | None` field in WorkerContext (worker_contract.py)
- `heal_target_pages` property returning the list or None
- In `generate/worker.py` page loop: if `heal_target_pages` is set AND non-empty,
  skip pages whose `page_id` is NOT in `heal_target_pages`
- Log a warning when skipping a page
- Emit `generate_page_skipped` event for each skipped page
- Tests: 4 test cases

### Out of scope
- Graph builder routing logic (deferred)
- Modifying run_loop or graph_builder for worker-level skipping

## Allowed paths

- plans/taskcards/TC-3853_heal_opt_selective_regen.md
- src/launcher/orchestrator/worker_contract.py
- src/launcher/workers/generate/worker.py
- tests/unit/workers/test_selective_regen.py
- reports/TC-3853/evidence.md

## Acceptance checks

1. [x] `heal_target_pages=None` → all pages processed (normal mode)
2. [x] `heal_target_pages=["pg-1"]` → only pg-1 processed, others skipped
3. [x] `generate_page_skipped` event emitted for each skipped page
4. [x] `pytest tests/unit/workers/test_selective_regen.py -v` — 24/24 PASS
5. [x] `pytest tests/ -q` — 2936 passed, 0 failures

## Self-review

### Verification results
- [x] Evidence file: `reports/TC-3853/evidence.md`

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_selective_regen.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

## Integration boundary proven

**Upstream**: `heal.py` sets `heal_target_pages` from `HealDecision.action.target_pages`
**Downstream**: Generate worker skips non-targeted pages, reducing LLM calls by ~(1 - |target|/|total|)
**Contract**: pages with `page_id not in heal_target_pages` are skipped silently with event
