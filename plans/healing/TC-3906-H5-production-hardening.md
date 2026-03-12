---
id: TC-3906-H5
title: "Harden project_root resolution and schema_path in snapshot modules"
status: Done
priority: P1 / High
owner: unassigned
updated: "2026-03-09"
tags: [snapshot, production, schema-path, project-root]
depends_on: []
allowed_paths:
  - plans/healing/TC-3906-H5-production-hardening.md
  - src/launcher/deploy/snapshot_manifest.py
  - src/launcher/deploy/promoter.py
---

# TC-3906-H5 — Harden `project_root` resolution and `schema_path`

## Status: Not Started

## Gap linkage

- **G-3906-05a**: `_auto_promote_phase_snapshots()` in `promoter.py` computes:
  ```python
  project_root = deploy_dir.parent
  snapshots_dir = project_root / "snapshots"
  phase_store_dir = project_root / "phase_store"
  ```
  This assumes `deploy/` is exactly one level below the project root. If a caller passes
  `deploy_dir = Path("/some/nested/path/to/deploy")`, `project_root` resolves incorrectly
  and both `snapshots/` and `phase_store/` land in the wrong location — silently.

- **G-3906-05b**: `save_snapshot_manifest()` calls `atomic_write_json` with:
  ```python
  schema_path="specs/schemas/snapshot_manifest.schema.json"
  ```
  This is a CWD-relative path. If the process is launched from any directory other than the
  project root (e.g., from a CI script, from `runs/`, or from a test's `tmp_path`),
  `atomic_write_json` will fail to find the schema file and raise `FileNotFoundError`.
  Existing `save_manifest()` in `manifest.py` has the same issue — this TC does not fix
  that (out of scope), but should align with whatever pattern is chosen here.

## Role

Senior engineer. Drop-in, production-ready.

## Scope

### Fix A — `project_root` in `promoter.py`:

Add explicit `snapshots_dir` and `phase_store_dir` optional parameters to `promote_run()`.
When provided, use them directly; when absent, fall back to the current `deploy_dir.parent`
heuristic with an INFO log warning.

```python
def promote_run(
    run_dir: Path,
    deploy_dir: Path,
    *,
    min_grade: Grade = Grade.C,
    dry_run: bool = False,
    snapshots_dir: Path | None = None,      # NEW optional param
    phase_store_dir: Path | None = None,    # NEW optional param
) -> PromotionReport:
```

Inside `_auto_promote_phase_snapshots`, change:
```python
# BEFORE:
project_root = deploy_dir.parent
snapshots_dir = project_root / "snapshots"
phase_store_dir = project_root / "phase_store"

# AFTER:
if snapshots_dir is None:
    snapshots_dir = deploy_dir.parent / "snapshots"
    logger.info(
        "snapshots_dir not specified — defaulting to %s (deploy_dir.parent heuristic)",
        snapshots_dir,
    )
if phase_store_dir is None:
    phase_store_dir = deploy_dir.parent / "phase_store"
    logger.info(
        "phase_store_dir not specified — defaulting to %s (deploy_dir.parent heuristic)",
        phase_store_dir,
    )
```

Propagate `snapshots_dir` and `phase_store_dir` into `_auto_promote_phase_snapshots` signature.

Update `backfill_runs()` to accept and forward the same two optional params.

Update `cli/deploy.py`'s `promote` and `backfill` subcommands to expose `--snapshots-dir`
and `--phase-store-dir` options.

**Note**: `cli/deploy.py` is NOT in the allowed paths for this TC. Limit allowed paths to only
`promoter.py` and `snapshot_manifest.py`. The CLI wiring for the new parameters is a follow-on
in TC-3906-H6 or left for the implementer to handle under a separate TC if needed.
Actually: add `cli/deploy.py` to allowed paths to wire the params through cleanly.

### Fix B — `schema_path` in `snapshot_manifest.py`:

Resolve `schema_path` relative to the module's `__file__` rather than CWD:

```python
import os as _os

_SCHEMA_PATH: str = _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)),   # src/launcher/deploy/
    "..", "..", "..", "..",                           # → project root
    "specs", "schemas", "snapshot_manifest.schema.json",
)

def save_snapshot_manifest(path: Path, manifest: SnapshotManifest) -> None:
    """Atomically write snapshot manifest to disk."""
    data = manifest.model_dump(mode="json")
    atomic_write_json(
        path,
        data,
        validate_boundary=path.parent,
        schema_path=_SCHEMA_PATH,
    )
```

Verify the relative `..` count: `src/launcher/deploy/` → `src/launcher/` → `src/` →
project root → `specs/schemas/`. That is 3 levels up from `deploy/`, so path should be
`"../../../specs/schemas/snapshot_manifest.schema.json"` from `__file__`'s directory,
or use `Path(__file__).resolve().parents[3] / "specs/schemas/snapshot_manifest.schema.json"`.

Use `Path` for clarity:
```python
_SCHEMA_PATH: Path = (
    Path(__file__).resolve().parents[3]
    / "specs" / "schemas" / "snapshot_manifest.schema.json"
)
```

Pass as `str` to `atomic_write_json(schema_path=str(_SCHEMA_PATH))` since that function
accepts `Optional[str]`.

### Allowed paths:
- `plans/healing/TC-3906-H5-production-hardening.md`
- `src/launcher/deploy/snapshot_manifest.py`
- `src/launcher/deploy/promoter.py`
- `src/launcher/orchestrator/run_loop.py`

### Forbidden: any other file/path (cli/deploy.py wiring is follow-on)

## Acceptance checks

### CLI:
```bash
# From a non-project-root CWD:
cd /tmp && python -c "
from pathlib import Path
from launcher.deploy.snapshot_manifest import save_snapshot_manifest, SnapshotManifest
import tempfile
with tempfile.TemporaryDirectory() as d:
    save_snapshot_manifest(Path(d) / 'manifest.json', SnapshotManifest())
    print('Schema resolved OK')
"
```
Prints `Schema resolved OK` regardless of CWD.

### UI/Web/API:
N/A.

### Tests:
1. `test_save_snapshot_manifest_works_from_any_cwd` — `monkeypatch.chdir(tmp_path)` (a dir
   with no `specs/` subdirectory), then call `save_snapshot_manifest()`. Assert no
   `FileNotFoundError`.
2. `test_promote_run_accepts_explicit_snapshots_dir` — Pass `snapshots_dir=tmp_path/"snap"` to
   `promote_run()`. Assert IR lands in `tmp_path/"snap/..."` not `deploy_dir.parent/"snapshots"`.
3. `test_promote_run_logs_heuristic_when_snapshots_dir_none` — `snapshots_dir=None`, capture
   logs. Assert INFO message containing `"defaulting to"` is emitted.

### Config respected end-to-end:
When `snapshots_dir` and `phase_store_dir` are explicit, they override the heuristic
completely. Default behaviour (both `None`) is unchanged from TC-3906 original.

### No mock data in production paths:
Real `tmp_path` fixtures; schema loaded from filesystem via absolute `__file__`-relative path.

## Deliverables

1. **`src/launcher/deploy/snapshot_manifest.py`** — Full file replacement. Add `_SCHEMA_PATH`
   constant using `Path(__file__).resolve().parents[3]`. Update `save_snapshot_manifest` to
   use it. No other changes.
2. **`src/launcher/deploy/promoter.py`** — Full file replacement. Add `snapshots_dir` and
   `phase_store_dir` optional params to `promote_run()` and `backfill_runs()`. Update
   `_auto_promote_phase_snapshots` to accept and use them. Add INFO log when defaulting.

Full file replacements — no stubs, no TODOs.

## Hard rules

- `promote_run()` remains backward-compatible: existing callers with no `snapshots_dir` arg
  continue to work (heuristic applies with INFO log).
- `backfill_runs()` similarly backward-compatible.
- No new deps.
- `_SCHEMA_PATH` computation must be verified with `assert _SCHEMA_PATH.exists()` in a dev
  sanity check (not in production code path).

## Review dimensions

| Dimension | 5/5 target for this TC |
|-----------|------------------------|
| Robustness | `save_snapshot_manifest` works when CWD is `/tmp`, CI `/workspace`, or test `tmp_path` |
| Production grading | Explicit `snapshots_dir` param prevents silent mis-routing in non-standard deployments |
| Correctness | `_SCHEMA_PATH` resolves to correct absolute path from any CWD |
| Maintainability | Heuristic vs explicit param documented in `promote_run` docstring |

## Now (runbook)

```bash
# 1. Verify parent depth from snapshot_manifest.py
python -c "
from pathlib import Path
p = Path('src/launcher/deploy/snapshot_manifest.py').resolve()
print(p.parents[0])  # deploy/
print(p.parents[1])  # launcher/
print(p.parents[2])  # src/
print(p.parents[3])  # project root
"

# 2. Fix snapshot_manifest.py: add _SCHEMA_PATH constant

# 3. Fix promoter.py: add optional params + INFO log

# 4. Test from /tmp
cd /tmp && python -c "
import sys; sys.path.insert(0, 'C:/Users/prora/OneDrive/Documents/GitHub/foss-launcher-v2/src')
from launcher.deploy.snapshot_manifest import save_snapshot_manifest, SnapshotManifest
import tempfile; from pathlib import Path
with tempfile.TemporaryDirectory() as d:
    save_snapshot_manifest(Path(d) / 'x.json', SnapshotManifest())
    print('OK')
"

# 5. Full suite
cd "C:/Users/prora/OneDrive/Documents/GitHub/foss-launcher-v2"
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=no | tail -3
```
