---
id: TC-3906-H1
title: "Fix majority-run IR-count accumulation across multiple promote calls"
status: Done
priority: P0 / Critical
owner: unassigned
updated: "2026-03-09"
tags: [snapshot, correctness, majority-tracking]
depends_on: []
allowed_paths:
  - plans/healing/TC-3906-H1-majority-tracking-fix.md
  - src/launcher/deploy/snapshot_manifest.py
  - src/launcher/deploy/phase_promoter.py
  - specs/schemas/snapshot_manifest.schema.json
---

# TC-3906-H1 — Fix majority-run IR-count accumulation

## Status: Not Started

## Gap linkage

- **G-3906-01**: `promote_phase_snapshots()` computes `ir_won_this_run` as the count of IR slots
  won in *this single call*. It then compares `ir_won_this_run > manifest.majority_run_ir_count`.
  `manifest.majority_run_ir_count` is a cumulative total across all previous calls. In a
  `backfill_runs()` scenario processing 10 runs oldest-first:
  - Run A wins 5 slots (stored: majority_run="A", count=5)
  - Run B wins 3 slots this call (3 > 5 is False → B never wins even if B is genuinely better)
  - Correct behaviour: accumulate per `run_id` across calls, then compare totals.

## Role

Senior engineer. Drop-in, production-ready.

## Scope

### Fix:

**`snapshot_manifest.py`** — Add `run_ir_counts: Dict[str, int]` field to `SnapshotManifest`.
This accumulates per-run IR slot counts across all promotion calls. Do not remove
`majority_run_ir_count` (it remains the stored maximum for fast comparison).

```python
run_ir_counts: Dict[str, int] = Field(default_factory=dict)
```

**`phase_promoter.py`** — Replace the majority-update block (currently lines ~202-213):

```python
# BEFORE (broken):
if ir_won_this_run > manifest.majority_run_ir_count:
    manifest.majority_run_id = run_id
    manifest.majority_run_ir_count = ir_won_this_run
    ...

# AFTER (correct — accumulate per run_id):
manifest.run_ir_counts[run_id] = manifest.run_ir_counts.get(run_id, 0) + ir_won_this_run
run_total = manifest.run_ir_counts[run_id]
if run_total > manifest.majority_run_ir_count:
    manifest.majority_run_id = run_id
    manifest.majority_run_ir_count = run_total
    if not dry_run:
        _update_phase_store(run_dir, phase_store_dir, family, platform)
        report.phase_jsons_updated = True
```

**`snapshot_manifest.schema.json`** — Add `run_ir_counts` property:

```json
"run_ir_counts": {
  "type": "object",
  "description": "Cumulative IR slot count per run_id across all promotion calls.",
  "additionalProperties": { "type": "integer", "minimum": 0 }
}
```

No other files need changes. `load_snapshot_manifest` uses `model_validate` so existing
manifests without `run_ir_counts` deserialise cleanly (Field default = `{}`).

### Allowed paths:
- `plans/healing/TC-3906-H1-majority-tracking-fix.md`
- `src/launcher/deploy/snapshot_manifest.py`
- `src/launcher/deploy/phase_promoter.py`
- `specs/schemas/snapshot_manifest.schema.json`

### Forbidden: any other file/path

## Acceptance checks

### CLI:
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
    tests/unit/deploy/test_phase_promoter.py \
    tests/unit/deploy/test_snapshot_manifest.py \
    -v --tb=short
```
All new tests pass; existing suite ≥ 3183 passed.

### UI/Web/API:
N/A — no web layer.

### Tests:
1. `test_majority_accumulates_across_calls` — Call `promote_phase_snapshots()` twice for
   `run_id="A"` (3 slots first call, 3 slots second call). Assert
   `manifest.run_ir_counts["A"] == 6` and `manifest.majority_run_id == "A"` and
   `manifest.majority_run_ir_count == 6`.
2. `test_majority_correct_winner_in_backfill` — Call for run A (5 slots), then run B (3 slots
   each in 3 calls = 9 total). Assert after all calls: `majority_run_id == "B"`,
   `majority_run_ir_count == 9`.
3. `test_existing_manifest_without_run_ir_counts_deserialises` — Load a manifest JSON that has
   no `run_ir_counts` key. Assert `manifest.run_ir_counts == {}` (backward compat).
4. `test_dry_run_does_not_update_manifest_counts` — dry_run=True: assert `run_ir_counts` is
   not written to disk.

### Config respected end-to-end:
Backfill scenario (multiple runs, oldest-first) must produce correct `majority_run_id` in
`snapshots/snapshot_manifest.json` after all runs processed.

### No mock data in production paths:
`_update_phase_store` only mocked in tests; live path uses real `shutil` operations.

## Deliverables

1. **`src/launcher/deploy/snapshot_manifest.py`** — Full file replacement. Add
   `run_ir_counts: Dict[str, int] = Field(default_factory=dict)` to `SnapshotManifest`.
2. **`src/launcher/deploy/phase_promoter.py`** — Full file replacement. Replace majority-update
   block with accumulation logic shown in Scope section.
3. **`specs/schemas/snapshot_manifest.schema.json`** — Full file replacement. Add
   `run_ir_counts` property.
4. **`tests/unit/deploy/test_phase_promoter.py`** — New test file with 4 tests above covering
   happy path + regression paths.

Full file replacements — no stubs, no TODOs.

## Hard rules

- `SnapshotManifest` backward compat: existing manifests (missing `run_ir_counts`) must
  deserialise without error via `model_validate` default.
- `promote_phase_snapshots()` signature unchanged.
- `PYTHONHASHSEED=0` in all test invocations.
- No new deps.
- Update docstring on `promote_phase_snapshots()` to document accumulation contract.

## Review dimensions

| Dimension | 5/5 target for this TC |
|-----------|------------------------|
| Correctness | `manifest.run_ir_counts[run_id]` equals sum of all per-call wins for that run |
| Thoroughness | Multi-call, multi-run, backfill, and backward-compat paths all tested |
| Robustness | Old manifests (no `run_ir_counts`) load cleanly; dry_run doesn't mutate |
| Minimality | ≤20 lines changed; no unrelated modifications |
| Testability | All tests use `tmp_path`, offline, deterministic |

## Now (runbook)

```bash
# 1. Confirm the bug location
grep -n "ir_won_this_run\|majority_run_ir_count" src/launcher/deploy/phase_promoter.py

# 2. Apply fix to snapshot_manifest.py (add run_ir_counts field)

# 3. Apply fix to phase_promoter.py (replace majority-update block)

# 4. Update snapshot_manifest.schema.json (add run_ir_counts property)

# 5. Write tests/unit/deploy/test_phase_promoter.py

# 6. Run targeted tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
    tests/unit/deploy/test_phase_promoter.py -v --tb=short

# 7. Run full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=no | tail -3
```
