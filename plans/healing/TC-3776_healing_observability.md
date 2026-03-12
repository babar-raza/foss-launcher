# TC-3776 Healing: Observability & Telemetry

## Context

TC-3776 moved cloning to Intake but did not emit a dedicated clone event.
The Intake worker logs clone results, but there is no structured event in
the event log (events.ndjson) for clone completion. Additionally, the
`WorkerContext.repo_dir` property docstring is stale — it still says
"set by Understand worker" when it should say "set from IntakeBundle".

## Gap Table

| Gap ID | Description | Taskcard |
|--------|-------------|----------|
| G-03 | No clone_completed event emitted at Intake | TM-01 |
| G-07 | WorkerContext.repo_dir docstring stale | TM-01 |

---

## Taskcard TM-01: Emit clone_completed event + fix stale docstring

**Status:** Not Started
**Gap linkage:** G-03, G-07
**Role:** Senior engineer. Drop-in, production-ready.

### Scope

**Fix:**
1. In `IntakeWorker.run()`, after a successful clone, emit a
   `clone_completed` event via `context.emit_event()` with payload:
   `{"repo_sha": repo_sha, "fresh": is_fresh_clone, "repo_dir": str(repo_dir)}`.
2. Update the docstring on `WorkerContext.repo_dir` property (line 107
   of `worker_contract.py`) from "set by Understand worker" to
   "set from IntakeBundle by Understand worker".

**Allowed paths:**
- `src/launcher/workers/intake/worker.py`
- `src/launcher/orchestrator/worker_contract.py`
- `tests/unit/workers/test_intake.py`

**Forbidden:** any other file/path

### Acceptance checks

- **CLI:** `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_intake.py -v` — all pass
- **Tests:**
  - Existing intake tests still pass
  - (Optional) A test can verify that `context.emit_event` was called with
    `"clone_completed"` after a successful run
- **Config respected end-to-end:** Event payload matches existing event patterns
- **No mock data in production paths:** Only in tests

### Deliverables

- Updated `src/launcher/workers/intake/worker.py` (emit event)
- Updated `src/launcher/orchestrator/worker_contract.py` (docstring only)
- Optionally updated `tests/unit/workers/test_intake.py` (verify event emission)

### Hard rules

- Keep public signatures unchanged
- No network in offline tests
- No new deps
- Event schema must match existing event patterns (type, data dict, worker kwarg)
- Keep code/docs/tests in sync

### Review dimensions — what 5/5 means for TM-01

| Dimension | 5/5 criteria |
|-----------|-------------|
| Thoroughness | Event emitted on success; docstring corrected |
| Consistency | Event follows same pattern as existing `worker_started`/`worker_completed` |
| Production grading | Clone telemetry visible in events.ndjson |
| Observability | `clone_completed` event enables pipeline analytics for clone cache hit rate |
| Minimality | ~5 lines total — 3 for emit_event, 2 for docstring fix |

### Now (runbook)

```bash
# 1. Edit intake/worker.py — add context.emit_event after clone call
# 2. Edit worker_contract.py — fix repo_dir docstring
# 3. Optionally add test verifying emit_event call
# 4. Run targeted tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_intake.py -v
# 5. Run full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -v
```
