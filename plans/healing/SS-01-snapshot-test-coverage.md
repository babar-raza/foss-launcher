# SS-01: Snapshot System Test Coverage

- **Status:** Done
- **Gap linkage:** G-SS-01 (snapshot models, wiring, and alias validator have zero test coverage)
- **Role:** Senior engineer. Drop-in, production-ready.

## Context

The snapshot system was fully dead code until this session's fix (missing models, wrong Event field names, no orchestrator wiring). The fix added:
- `Snapshot`, `WorkItem`, `ArtifactIndexEntry` models in `models/state.py`
- Event `model_validator` alias normalization in `models/event.py`
- `_write_final_snapshot()` + `create_initial_snapshot()` wiring in `run_loop.py`

None of this has test coverage. Without tests, regressions will silently re-break snapshots.

## Scope

- **Fix:** Add unit tests covering the snapshot lifecycle end-to-end.
- **Allowed paths:**
  - `tests/unit/state/test_snapshot_manager.py` (new)
  - `tests/unit/models/test_event.py` (new or extend)
  - `tests/unit/models/test_state.py` (new or extend)
- **Forbidden:** any other file/path

## Acceptance Checks

- **Tests:**
  - `Snapshot()` default construction produces valid model with `run_state="CREATED"`
  - `Snapshot.to_dict()` → `Snapshot.from_dict()` round-trip is identity
  - `Snapshot.from_dict({})` returns default Snapshot (not crash)
  - `WorkItem` status defaults to `WORK_ITEM_STATUS_QUEUED`
  - `ArtifactIndexEntry` serializes/deserializes all 6 fields
  - `Event(ts=..., type=..., payload=...)` normalizes to `timestamp`, `event_type`, `data`
  - `Event(timestamp=..., event_type=..., data=...)` works directly (no double-map)
  - `Event.from_dict(raw_ndjson_dict)` parses ArtifactStore-emitted events correctly
  - `create_initial_snapshot(run_id)` returns Snapshot with matching run_id and state "CREATED"
  - `write_snapshot()` then `read_snapshot()` round-trip produces identical Snapshot
  - `replay_events()` on an events.ndjson with `run_created` + `worker_started` events produces non-empty snapshot
  - `apply_event_reducer()` for `EVENT_ARTIFACT_WRITTEN` populates `artifacts_index`
  - `apply_event_reducer()` for `EVENT_WORK_ITEM_QUEUED` appends to `work_items`
  - `apply_event_reducer()` for `EVENT_RUN_STATE_CHANGED` updates `run_state`
- **CLI:** `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/state/ tests/unit/models/ -v` passes
- **Config respected end-to-end:** N/A
- **No mock data in production paths:** Tests use tmp_path fixtures only

## Deliverables

- Full `tests/unit/state/test_snapshot_manager.py` with 10+ test methods
- Event alias tests in `tests/unit/models/test_event.py` with 4+ test methods
- State model tests in `tests/unit/models/test_state.py` with 5+ test methods
- All tests self-contained (no network, no LLM)

## Hard Rules

- Keep public signatures unchanged
- No network in offline tests
- Deterministic (PYTHONHASHSEED=0)
- No new deps
- Tests must use real `replay_events()` → `write_snapshot()` → `read_snapshot()` chain, not mocked internals

## Review Dimensions (5/5 targets)

| Dimension | What 5/5 means |
|-----------|----------------|
| Thoroughness | Every public function in snapshot_manager.py has happy + error path |
| Correctness | Assert on actual field values, not just "no exception" |
| Isolation | Each test is independent; tmp_path for all disk I/O |
| Coverage | All 9 event types in apply_event_reducer have a test |
| Determinism | Tests pass with PYTHONHASHSEED=0 |

## Runbook

```bash
# 1. Create test files
# 2. Write snapshot model tests (Snapshot, WorkItem, ArtifactIndexEntry)
# 3. Write Event alias normalization tests
# 4. Write snapshot_manager function tests (write, read, replay, reduce)
# 5. Run:
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/state/test_snapshot_manager.py tests/unit/models/ -v
# 6. Full suite:
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```
