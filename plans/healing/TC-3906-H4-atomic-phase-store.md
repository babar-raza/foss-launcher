---
id: TC-3906-H4
title: "Make phase_store writes atomic; derive filenames from RunLayout"
status: Done
priority: P1 / High
owner: unassigned
updated: "2026-03-09"
tags: [snapshot, robustness, atomic-writes]
depends_on: [TC-3906-H3]
allowed_paths:
  - plans/healing/TC-3906-H4-atomic-phase-store.md
  - src/launcher/deploy/phase_promoter.py
---

# TC-3906-H4 — Atomic phase_store writes + RunLayout-derived filenames

## Status: Not Started

## Gap linkage

- **G-3906-04a**: `_update_phase_store()` uses `shutil.copy2(src, dst)` — a non-atomic
  operation. If the process is interrupted mid-copy, the destination file is a partial write.
  Phase store files (understand.json, plan.json, etc.) are consumed by downstream pipeline
  resume logic; a corrupt partial file there silently produces wrong behaviour.

- **G-3906-04b**: `_PHASE_FILES` hardcodes run-directory filenames as a dict:
  ```python
  _PHASE_FILES = {
      "understand": "understanding_bundle.json",
      "plan": "planner_checkpoint.json",
      "generate": "generate_checkpoint.json",
      "evaluate": "evaluate_checkpoint.json",
  }
  ```
  These filenames are authoritative in `RunLayout` (e.g., `layout.understanding_bundle`).
  The dict is a second source of truth that can silently diverge.

## Role

Senior engineer. Drop-in, production-ready.

## Scope

### Fix:

**`src/launcher/deploy/phase_promoter.py`** only.

**Remove `_PHASE_FILES` dict.** Replace `_update_phase_store` with a version that:
1. Instantiates `RunLayout(run_dir=run_dir)` to get canonical paths.
2. Builds the source list from `RunLayout` properties.
3. Copies each file atomically: write to `<dest>.tmp`, then `os.replace(<dest>.tmp, <dest>)`.

```python
import os
from launcher.io.run_layout import RunLayout

def _update_phase_store(
    run_dir: Path,
    phase_store_dir: Path,
    family: str,
    platform: str,
) -> None:
    """Copy run-level phase JSONs to phase_store/{family}/{platform}/ atomically."""
    layout = RunLayout(run_dir=run_dir)

    # Canonical source → destination name mapping derived from RunLayout
    phase_sources: dict[str, Path] = {
        "understand.json": layout.understanding_bundle,
        "plan.json": run_dir / "planner_checkpoint.json",
        "generate.json": run_dir / "generate_checkpoint.json",
        "evaluate.json": run_dir / "evaluate_checkpoint.json",
    }

    dest_dir = phase_store_dir / family / platform
    dest_dir.mkdir(parents=True, exist_ok=True)

    for dest_name, src in phase_sources.items():
        if not src.exists():
            logger.debug("Phase file not found, skipping: %s", src.name)
            continue
        dest = dest_dir / dest_name
        tmp = dest.with_suffix(".tmp")
        try:
            import shutil
            shutil.copy2(src, tmp)
            os.replace(tmp, dest)
            logger.debug("Updated phase_store %s from %s", dest_name, src.name)
        except Exception:
            # Clean up temp file if present
            if tmp.exists():
                tmp.unlink(missing_ok=True)
            logger.warning("Failed to copy %s to phase_store", src.name, exc_info=True)
```

Note: `RunLayout` validates that `run_dir` is inside a `runs/` parent. If `run_dir` is not
under `runs/`, `RunLayout` raises `ValueError`. Catch this in `promote_phase_snapshots` and
log a warning rather than crashing.

Also add the `ValueError` guard in `promote_phase_snapshots` before calling
`_update_phase_store`:
```python
try:
    _update_phase_store(run_dir, phase_store_dir, family, platform)
except ValueError as e:
    logger.warning("Cannot update phase_store (RunLayout validation): %s", e)
```

### Allowed paths:
- `plans/healing/TC-3906-H4-atomic-phase-store.md`
- `src/launcher/deploy/phase_promoter.py`

### Forbidden: any other file/path

## Acceptance checks

### CLI:
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
    tests/unit/deploy/test_phase_promoter.py -v --tb=short
```
`test_phase_jsons_written_when_majority_won` passes. No `.tmp` files left in phase_store after test.

### UI/Web/API:
N/A.

### Tests:
1. `test_phase_store_no_partial_files_on_interrupt` — Patch `shutil.copy2` to raise `OSError`
   mid-copy. Assert: destination `.json` file not created; `.tmp` file not left behind; no crash.
2. Existing `test_phase_jsons_written_when_majority_won` still passes with RunLayout-derived paths.
3. `test_run_dir_outside_runs_does_not_crash` — Pass a `run_dir` not under `runs/`. Assert
   `phase_store` is not written, warning is logged, no exception propagated.

### Config respected end-to-end:
Phase store filenames (`understand.json`, `plan.json`, `generate.json`, `evaluate.json`) match
what downstream resume logic expects.

### No mock data in production paths:
`RunLayout` used with real `tmp_path` dirs in tests.

## Deliverables

1. **`src/launcher/deploy/phase_promoter.py`** — Full file replacement. Remove `_PHASE_FILES`.
   Replace `_update_phase_store` with atomic version using `RunLayout`. Add `ValueError` guard.
   No other behavioural changes.

Full file replacement — no stubs, no TODOs.

## Hard rules

- `promote_phase_snapshots()` public signature unchanged.
- Import `RunLayout` inside `_update_phase_store` body (not at module level) to avoid circular
  import risk if `run_layout.py` ever imports from `deploy`.
- No new deps beyond stdlib `os` and existing `launcher.io.run_layout`.
- Deterministic: `PYTHONHASHSEED=0`.

## Review dimensions

| Dimension | 5/5 target for this TC |
|-----------|------------------------|
| Robustness | Interrupted copy leaves no partial files; ValueError from RunLayout is caught |
| Correctness | Filenames derived from RunLayout — single source of truth |
| Maintainability | `_PHASE_FILES` dict removed; no second source of truth for filenames |
| Minimality | Only `phase_promoter.py` changes; ≤30 lines net change |

## Now (runbook)

```bash
# 1. Read RunLayout to confirm property names
grep -n "understanding_bundle\|planner_checkpoint\|generate_checkpoint\|evaluate_checkpoint" \
    src/launcher/io/run_layout.py

# 2. Verify RunLayout._validate_run_dir raises ValueError for non-runs/ paths
python -c "
from launcher.io.run_layout import RunLayout
from pathlib import Path
try:
    RunLayout(run_dir=Path('/tmp/bad_dir'))
    print('No error — check _validate_run_dir')
except Exception as e:
    print(f'Got expected error: {e}')
"

# 3. Rewrite _update_phase_store in phase_promoter.py

# 4. Remove _PHASE_FILES

# 5. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
    tests/unit/deploy/test_phase_promoter.py -v --tb=short

# 6. Full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=no | tail -3
```
