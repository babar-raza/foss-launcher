---
id: TC-3831
title: "heal_event_types"
status: Done
priority: Normal
owner: "agent"
updated: "2026-03-08"
tags: [models, events, heal]
depends_on: [TC-3829]
allowed_paths:
  - src/launcher/models/event.py
  - plans/taskcards/TC-3831_heal_event_types.md
evidence_required:
  - reports/TC-3831/evidence.md
---

# Taskcard TC-3831 — heal_event_types

## Objective

Extend the `EventType` enum in `src/launcher/models/event.py` with 4 new heal
lifecycle event types so the event log can record heal session boundaries.

## Required spec references

- `specs/11_state_and_events.md` (event types, pipeline events)

## Scope

### In scope
- Add `HEAL_SESSION_STARTED`, `HEAL_STEP_STARTED`, `HEAL_STEP_COMPLETED`,
  `HEAL_SESSION_COMPLETED` to `EventType`

### Out of scope
- Emitting these events (heal worker, separate TC)
- Event schema JSON files

## Inputs

- `src/launcher/models/event.py` (existing file)

## Outputs

- `src/launcher/models/event.py` with 4 new enum members

## Allowed paths

- src/launcher/models/event.py
- plans/taskcards/TC-3831_heal_event_types.md

### Allowed paths rationale

`event.py` is the canonical home for all pipeline event types. The taskcard file
satisfies AG-002.

## Implementation steps

### Step 1: Append enum values

Add 4 new values to the `EventType` enum after `intake_onboard_complete`:

```python
HEAL_SESSION_STARTED = "heal_session_started"
HEAL_STEP_STARTED = "heal_step_started"
HEAL_STEP_COMPLETED = "heal_step_completed"
HEAL_SESSION_COMPLETED = "heal_session_completed"
```

### Step 2: Run tests

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q 2>&1 | tail -5
```

### Step 3: Verify import

```bash
.venv/Scripts/python.exe -c "from launcher.models.event import EventType; EventType.HEAL_SESSION_STARTED; print('OK')"
```

## Failure modes

### Failure mode 1: Enum frozen — write fails

**Detection**: `AttributeError` when adding to enum at runtime (not applicable — we edit the source file)
**Resolution**: Edit is to source code, not runtime mutation. Not an issue.
**Gate**: Python import

### Failure mode 2: Value collision with existing enum member

**Detection**: `ValueError: duplicate values found in Enum` at import time
**Resolution**: Verify none of the 4 new string values duplicate existing ones
**Gate**: Python import

### Failure mode 3: Downstream code that iterates EventType breaks

**Detection**: Test failure in event_log or snapshot_manager tests
**Resolution**: The new values are additive; no existing consumer exhaustively matches all enum values
**Gate**: pytest

## Task-specific review checklist

1. [x] All 4 new enum members added
2. [x] No existing enum member modified or removed
3. [x] String values use `heal_` prefix, distinct from all existing values
4. [x] Enum uses UPPER_CASE names as specified
5. [x] No import changes required (enum already defined in file)
6. [x] All tests pass with PYTHONHASHSEED=0

## Deliverables

1. `src/launcher/models/event.py` with 4 new `EventType` members
2. This taskcard at `plans/taskcards/TC-3831_heal_event_types.md`

## Acceptance checks

1. [x] `from launcher.models.event import EventType; EventType.HEAL_SESSION_STARTED` succeeds
2. [x] `pytest tests/ -x -q` passes
3. [x] No existing enum value removed or changed

## Self-review

### Verification results
- [x] Tests: 2392/2392 PASS (PYTHONHASHSEED=0, run 2026-03-08)
- [x] Import smoke test: All 4 new EventType values accessible
- [x] Evidence file: `reports/TC-3831/evidence.md`

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

**Actual results** (run 2026-03-08):
```
2392 passed in 53.28s
```

Import verification:
```
EventType.HEAL_SESSION_STARTED: EventType.HEAL_SESSION_STARTED
EventType.HEAL_STEP_STARTED: EventType.HEAL_STEP_STARTED
EventType.HEAL_STEP_COMPLETED: EventType.HEAL_STEP_COMPLETED
EventType.HEAL_SESSION_COMPLETED: EventType.HEAL_SESSION_COMPLETED
value HEAL_SESSION_STARTED: heal_session_started
```

## Integration boundary proven

**Upstream**: Heal worker emits events with these types
**Downstream**: `event_log.py` and `snapshot_manager.py` record events; event type is stored as string
**Contract**: `EventType` enum values used as string keys in `events.ndjson`
