# SS-02: Dual Event Writer Consolidation

- **Status:** Done
- **Gap linkage:** G-SS-02 (two parallel event writers produce inconsistent ndjson records)
- **Role:** Senior engineer. Drop-in, production-ready.

## Context

Two independent systems write to `events.ndjson`:

1. **`ArtifactStore.emit_event()`** — used by orchestrator and workers. Writes raw dicts with keys: `event_id`, `event_type`, `run_id`, `timestamp`, `worker`, `data`. No chain hashing.
2. **`event_log.append_event()`** — used by `llm_telemetry.py`. Writes `Event` model objects via `event.to_dict()`. Supports chain hashing (`event_hash`, `prev_hash`).

`replay_events()` calls `read_events()` which calls `Event.from_dict()` on each line. Thanks to the alias validator and `extra="ignore"`, both formats parse. But the duality causes:
- No chain hashing on ArtifactStore-emitted events (validation skips them)
- Different field ordering in ndjson (cosmetic but confusing for debugging)
- `event_type` values from ArtifactStore are free-form strings; `event_log` uses `Event` model which accepts any string

This taskcard unifies both writers behind a single code path.

## Scope

- **Fix:** Make `ArtifactStore.emit_event()` construct an `Event` model and delegate to `event_log.append_event()`.
- **Allowed paths:**
  - `src/launcher/io/artifact_store.py`
  - `tests/unit/io/test_artifact_store.py` (extend)
- **Forbidden:** any other file/path

## Acceptance Checks

- **Tests:**
  - `ArtifactStore.emit_event()` produces ndjson lines parseable by `Event.from_dict()`
  - `read_events()` on an events file written by both `emit_event()` and `append_event()` returns valid Event objects for all lines
  - `emit_event()` records include `event_id` field (non-empty UUID)
  - Existing ArtifactStore tests still pass unchanged
- **CLI:** `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/io/test_artifact_store.py -v` passes
- **Config respected end-to-end:** Events written by workers are replayable by `replay_events()`
- **No mock data in production paths:** N/A

## Deliverables

- Updated `ArtifactStore.emit_event()` to use `Event` model + `append_event()`
- 2+ new tests verifying format consistency
- All existing tests pass

## Hard Rules

- Keep `emit_event()` public signature unchanged: `(event_type, payload, *, run_id, worker)`
- No new deps
- `append_event()` must remain the single serialization path
- Do NOT add chain hashing to `emit_event()` (separate concern for a future card)

## Review Dimensions (5/5 targets)

| Dimension | What 5/5 means |
|-----------|----------------|
| Correctness | All ndjson lines use identical field set after unification |
| Minimality | Only ArtifactStore changes; no callers affected |
| Robustness | emit_event still catches and logs exceptions (no crash on telemetry failure) |
| Testability | Round-trip test: emit → read_events → verify fields |
| Consistency | Single serialization path for all events |

## Runbook

```bash
# 1. Read src/launcher/io/artifact_store.py
# 2. Replace raw dict construction in emit_event() with Event model construction
# 3. Replace manual file append with append_event() call
# 4. Add round-trip tests
# 5. Run:
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/io/test_artifact_store.py -v
# 6. Full suite:
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```
