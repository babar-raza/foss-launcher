# RID-04: Run Directory Observability

## Status: Done

## Gap Linkage
- G-RID-05: Run directory names lost product-family context (`pilot_cells_` → `r_260307_xxxx`)

## Role
Senior engineer. Drop-in, production-ready.

## Scope

### Fix
Add a `run_manifest.json` file written at run creation time that provides
human-readable context for each run directory. This preserves observability
without lengthening the directory name.

Contents:
```json
{
  "run_id": "r_260307_a1b2c3",
  "family": "cells",
  "platform": "python",
  "created_utc": "2026-03-07T08:15:33Z",
  "config_path": "configs/pilots/aspose-cells-foss-python.yaml"
}
```

This file is written by both `run_loop.py` (already writes `run_config.json`)
and `run_pilot.py` (already writes `run_config.json`). The manifest is a
lightweight summary — `run_config.json` remains the full config snapshot.

Alternative (simpler): skip a new file entirely, just ensure `run_config.json`
is written early enough that `ls runs/ && cat runs/*/run_config.json | jq .family`
gives the answer. **This is already the case** — both entrypoints write
`run_config.json` immediately. The gap may be sufficiently addressed by
documenting the lookup command.

### Decision needed
This taskcard may be **Won't Fix** if the team decides that
`run_config.json` already provides sufficient observability. The cost of an
additional manifest file may not justify itself. Flag for team review.

### Allowed paths
- `src/launcher/orchestrator/run_loop.py` (add manifest write after line ~303)
- `scripts/run_pilot.py` (add manifest write after line ~87)
- OR: `plans/healing/RID-04-observability-context.md` updated to "Won't Fix"

### Forbidden
- Any other file/path

## Acceptance Checks

### CLI
- After a pipeline run: `cat runs/<run_id>/run_config.json | python -c "import json,sys; d=json.load(sys.stdin); print(d['family'])"` prints the family name
- OR if manifest added: `cat runs/<run_id>/run_manifest.json` shows family+platform

### Tests
- If manifest added: test in `test_run_layout.py` that `create_run_skeleton` path includes manifest

### No mock data in production paths
- Manifest values come from RunConfig, not hardcoded

## Deliverables
- Either: 2 file patches adding manifest write, plus 1 test
- Or: this file updated to "Won't Fix" with rationale

## Hard Rules
- No new deps
- Keep entrypoints in parity
- Code/docs/tests in sync

## Review Dimensions — what 5/5 means for this taskcard

| Dimension | 5/5 Criteria |
|-----------|-------------|
| Observability | `runs/` directory browsable with family context in <1 command |
| Minimality | No unnecessary files if `run_config.json` suffices |
| Integration fit | Manifest uses same `ArtifactStore.write_json` pattern |

## Now (Runbook)

```bash
# 1. Decide: manifest vs won't-fix
# 2. If manifest:
#    a. Add write_json("run_manifest.json", ...) in run_loop.py after run_config write
#    b. Add same in run_pilot.py
#    c. Add test
# 3. If won't-fix: update this file status
# 4. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```
