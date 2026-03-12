---
id: TC-3906-H6
title: "Remove dead _NON_IR_NAMES; slim _auto_promote_phase_snapshots in promoter.py"
status: In Progress
priority: P2 / Medium
owner: unassigned
updated: "2026-03-09"
tags: [snapshot, code-hygiene, minimality]
depends_on: [TC-3906-H3, TC-3906-H5]
allowed_paths:
  - plans/healing/TC-3906-H6-dead-code-refactor.md
  - src/launcher/shared/ir_regenerate.py
  - src/launcher/deploy/promoter.py
---

# TC-3906-H6 — Remove dead code; slim auto-hook in `promoter.py`

## Status: Not Started

## Gap linkage

- **G-3906-06a**: `ir_regenerate.py` defines:
  ```python
  _NON_IR_NAMES: frozenset[str] = frozenset({"snapshot_manifest.json"})
  ```
  and uses it as:
  ```python
  if ir_file.name in _NON_IR_NAMES:
      continue
  ```
  This is dead code. The glob pattern `rglob("*.ir.json")` will never match
  `snapshot_manifest.json` (which has `.json` extension, not `.ir.json`). The check is
  unreachable and misleads readers into thinking `.ir.json`-named manifests are possible.

- **G-3906-06b**: `_auto_promote_phase_snapshots()` in `promoter.py` is a 50-line private
  function that reads `run_config.json`, resolves paths, and calls into `phase_promoter.py`.
  This logic bloats `promoter.py` and creates a hidden cross-module dependency. The function
  should be slimmed to its essential purpose: a thin dispatch that leaves path resolution and
  config reading to the caller or to a dedicated integration helper.

## Role

Senior engineer. Drop-in, production-ready.

## Scope

### Fix A — Remove `_NON_IR_NAMES` from `ir_regenerate.py`:

Delete the constant and the associated `if ir_file.name in _NON_IR_NAMES: continue` check.
Update the module docstring to remove any reference to this filter. The glob `rglob("*.ir.json")`
is the sole filter; no additional name exclusion is needed.

### Fix B — Slim `_auto_promote_phase_snapshots` in `promoter.py`:

The function currently:
1. Reads `run_config.json` from `run_dir`
2. Extracts `family` / `platform`
3. Resolves `snapshots_dir` and `phase_store_dir` from `deploy_dir.parent`
4. Calls `promote_phase_snapshots()`

After TC-3906-H5 lands, `promote_run()` accepts explicit `snapshots_dir` / `phase_store_dir`.
Slim `_auto_promote_phase_snapshots` to:
- Read `run_config.json` for `family` / `platform` only
- Use whatever `snapshots_dir` / `phase_store_dir` was passed to `promote_run()` (already
  resolved by H5 fix)
- Call `promote_phase_snapshots()` with those resolved values

Target: reduce `_auto_promote_phase_snapshots` from ~50 lines to ~20 lines.

Concrete slimming — replace the path-resolution block with a direct delegation:

```python
def _auto_promote_phase_snapshots(
    run_dir: Path,
    snapshots_dir: Path,     # already resolved by promote_run
    phase_store_dir: Path,   # already resolved by promote_run
    min_grade: Grade,
) -> None:
    """Dispatch to phase_promoter after a successful promote_run."""
    from launcher.deploy.phase_promoter import promote_phase_snapshots

    run_config_path = run_dir / "run_config.json"
    if not run_config_path.exists():
        logger.debug("No run_config.json — skipping phase snapshot promotion")
        return

    try:
        rc = json.loads(run_config_path.read_text(encoding="utf-8"))
        family = rc.get("family", "")
        platform = rc.get("platform", "")
    except Exception:
        logger.warning("Cannot parse run_config.json in %s", run_dir, exc_info=True)
        return

    if not family or not platform:
        logger.warning("Missing family/platform in run_config.json for %s", run_dir)
        return

    try:
        phase_report = promote_phase_snapshots(
            run_dir=run_dir,
            snapshots_dir=snapshots_dir,
            phase_store_dir=phase_store_dir,
            family=family,
            platform=platform,
            min_grade=min_grade,
        )
        logger.info("Phase snapshots: promoted=%d updated=%s",
                    phase_report.ir_promoted, phase_report.phase_jsons_updated)
    except Exception:
        logger.error("Phase snapshot promotion failed for %s", run_dir, exc_info=True)
```

Call site in `promote_run()` becomes:
```python
if not dry_run and report.promoted > 0:
    _auto_promote_phase_snapshots(run_dir, snapshots_dir, phase_store_dir, min_grade)
```

### Allowed paths:
- `plans/healing/TC-3906-H6-dead-code-refactor.md`
- `src/launcher/shared/ir_regenerate.py`
- `src/launcher/deploy/promoter.py`

### Forbidden: any other file/path

## Acceptance checks

### CLI:
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=no | tail -3
```
≥ 3183 passing (no regressions).

```bash
grep "_NON_IR_NAMES" src/launcher/shared/ir_regenerate.py
```
Returns nothing (constant removed).

### UI/Web/API:
N/A.

### Tests:
1. No new tests required — dead code removal is verified by absence of the symbol.
2. `test_snapshot_manifest_json_not_processed` in TC-3906-H2 confirms `snapshot_manifest.json`
   is never emitted as a `.md` file (proves the dead guard wasn't needed).
3. Confirm `_auto_promote_phase_snapshots` accepts the slimmed signature by running any
   existing phase-promoter integration path.

### Config respected end-to-end:
Slimmed `_auto_promote_phase_snapshots` must still correctly dispatch to `promote_phase_snapshots`
with correct `family`/`platform`/`snapshots_dir`/`phase_store_dir`.

### No mock data in production paths:
N/A for dead code removal.

## Deliverables

1. **`src/launcher/shared/ir_regenerate.py`** — Full file replacement. Remove `_NON_IR_NAMES`
   constant, remove associated `if ir_file.name in _NON_IR_NAMES: continue` check, update
   docstring. No other changes.
2. **`src/launcher/deploy/promoter.py`** — Full file replacement. Slim
   `_auto_promote_phase_snapshots` to ~20 lines per the spec above. Update call site signature.

Full file replacements — no stubs, no TODOs.

## Hard rules

- `promote_run()` public signature: adding `snapshots_dir`/`phase_store_dir` is done in
  TC-3906-H5; TC-3906-H6 only slims the internal helper.
- `_auto_promote_phase_snapshots` remains private (leading underscore).
- No new deps.

## Review dimensions

| Dimension | 5/5 target for this TC |
|-----------|------------------------|
| Minimality | `_NON_IR_NAMES` gone; `_auto_promote_phase_snapshots` ≤20 lines |
| Maintainability | No dead code; helper function has single clear responsibility |
| Correctness | Behaviour unchanged after slimming |
| Readability | `promoter.py` no longer contains 50-line phase-promotion logic |

## Now (runbook)

```bash
# 1. Confirm _NON_IR_NAMES is unreachable
python -c "
import re
pat = re.compile(r'\.ir\.json$')
print(pat.search('snapshot_manifest.json'))  # Should print None
"

# 2. Remove _NON_IR_NAMES from ir_regenerate.py

# 3. Slim _auto_promote_phase_snapshots in promoter.py
#    (depends on TC-3906-H5 having added snapshots_dir/phase_store_dir params)

# 4. Run full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=no | tail -3

# 5. Confirm dead symbol gone
grep "_NON_IR_NAMES" src/launcher/shared/ir_regenerate.py && echo "FAIL" || echo "OK"
```
