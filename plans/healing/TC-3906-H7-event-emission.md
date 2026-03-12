---
id: TC-3906-H7
title: "Emit snapshot_promoted / phase_store_updated events to events.ndjson"
status: Done
priority: P3 / Low
owner: unassigned
updated: "2026-03-09"
tags: [snapshot, events, audit-trail, observability]
depends_on: [TC-3906-H1, TC-3906-H4]
allowed_paths:
  - plans/healing/TC-3906-H7-event-emission.md
  - src/launcher/deploy/phase_promoter.py
  - src/launcher/state/event_log.py
---

# TC-3906-H7 — Emit snapshot events to events.ndjson

## Status: Done

## Gap linkage

- **G-3906-07**: `promote_phase_snapshots()` performs IR promotion and phase_store updates
  but emits nothing to `events.ndjson`. This means the audit trail has no record of:
  - Which IRs were promoted to `snapshots/` and from which run
  - Which run became the majority run and updated `phase_store/`
  - Grade transitions in `snapshots/`

  Every other promotion path (`promote_run()` in `promoter.py`) has a corresponding
  audit record. Snapshot promotion is invisible to the event log, breaking the
  "all mutations are observable" invariant.

## Role

Senior engineer. Drop-in, production-ready.

## Scope

### Events to emit

**1. `snapshot_ir_promoted`** — emitted once per IR file successfully written to `snapshots/`:
```json
{
  "event_type": "snapshot_ir_promoted",
  "run_id": "<source_run_id>",
  "content_path": "kb.aspose.org/cells/python/developer-guide/slug",
  "old_grade": "C",
  "new_grade": "B",
  "sha256": "<64-char hex>",
  "snapshot_file": "kb.aspose.org/cells/python/developer-guide/slug.ir.json",
  "ts": "<ISO-8601 UTC>"
}
```
`old_grade` is `null` if this is the first promotion for the slug.

**2. `phase_store_updated`** — emitted once when the majority run wins and phase JSONs are written:
```json
{
  "event_type": "phase_store_updated",
  "run_id": "<majority_run_id>",
  "family": "cells",
  "platform": "python",
  "ir_won_count": 42,
  "phase_files_written": ["understand.json", "plan.json", "generate.json", "evaluate.json"],
  "ts": "<ISO-8601 UTC>"
}
```

### Where to write

Events are appended to `events.ndjson` in the **project root** (same file used by all
other pipeline stages). Use `event_log.append_event()` from `src/launcher/state/event_log.py`.

The events file path should be resolved as:
```python
events_path = snapshots_dir.parent.parent / "events.ndjson"
```
(snapshots_dir is a top-level dir like `project_root/snapshots/`, so `.parent` is project root.)

Alternatively, accept an optional `events_path: Path | None = None` parameter in
`promote_phase_snapshots()` and default to `None` (no events) if not provided — this
preserves backward compatibility with callers that don't have a project root context.

**Recommended**: accept `events_path: Path | None = None` as an optional kwarg. Emit only
when not None. The hook in `promoter.py` (`_auto_promote_phase_snapshots`) passes
`deploy_dir.parent / "events.ndjson"`.

### Dry-run guard

When `dry_run=True`, do **not** write events. Log at DEBUG level what would have been emitted.

### Allowed paths:
- `plans/healing/TC-3906-H7-event-emission.md`
- `src/launcher/deploy/phase_promoter.py`
- `src/launcher/state/event_log.py`

### Forbidden: any other file/path

## Acceptance checks

### CLI:
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=no | tail -3
```
≥ 3183 passing (no regressions).

### Functional:
After a call to `promote_phase_snapshots()` with a real `events_path`:
```bash
grep "snapshot_ir_promoted" events.ndjson | wc -l
# Should equal the number of IR files promoted
grep "phase_store_updated" events.ndjson | wc -l
# Should equal 1 if majority run changed, 0 otherwise
```

### Schema:
Each emitted line is valid NDJSON with at minimum: `event_type`, `run_id`, `ts` fields.

### UI/Web/API:
N/A.

### Tests:
1. `test_snapshot_events_emitted` — call `promote_phase_snapshots()` with a tmp `events_path`;
   assert `snapshot_ir_promoted` lines match promoted IR count.
2. `test_snapshot_events_dry_run` — `dry_run=True` emits no events to `events_path`.
3. `test_phase_store_event_emitted` — when majority run wins, `phase_store_updated` event present.
4. `test_no_events_when_events_path_none` — `events_path=None` (default) does not raise and
   does not create any file.

## Deliverables

1. **`src/launcher/deploy/phase_promoter.py`** — Add `events_path: Path | None = None` kwarg
   to `promote_phase_snapshots()`; emit `snapshot_ir_promoted` per promoted IR and
   `phase_store_updated` when phase_store is written; skip when `dry_run=True`.
2. **`src/launcher/state/event_log.py`** — Verify `append_event()` exists and handles
   concurrent appends safely (should already be the case; read before assuming changes needed).

## Hard rules

- Do not emit events in dry_run mode.
- `events_path=None` is valid and silently skips emission — no crash.
- Event `ts` must be UTC ISO-8601 (use `datetime.now(UTC).isoformat()`).
- No new mandatory parameters to `promote_phase_snapshots()` — `events_path` must be optional.

## Review dimensions

| Dimension | 5/5 target for this TC |
|-----------|------------------------|
| Observability | Both event types emitted; audit trail complete |
| Backward compat | `events_path=None` default — no existing callers break |
| Correctness | Events match actual mutations; dry_run never emits |
| Minimality | Two event types, no over-engineering |

## Now (runbook)

```bash
# 1. Read event_log.py to confirm append_event() signature
cat src/launcher/state/event_log.py

# 2. Add events_path param and emission logic to phase_promoter.py

# 3. Update _auto_promote_phase_snapshots in promoter.py to pass events_path

# 4. Run full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=no | tail -3

# 5. Manual smoke-test
grep "snapshot_ir_promoted" events.ndjson && echo "OK" || echo "NO EVENTS"
```
