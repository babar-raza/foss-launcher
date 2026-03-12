---
id: TC-3906
title: "snapshots/ IR Store + phase_store/ + ir_regenerate"
status: Done
priority: High
owner: "claude-agent"
updated: "2026-03-09"
tags: [deploy, snapshots, ir, regeneration]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3906_snapshot-ir-store.md
  - src/launcher/deploy/snapshot_manifest.py
  - src/launcher/deploy/phase_promoter.py
  - src/launcher/deploy/promoter.py
  - src/launcher/shared/ir_regenerate.py
  - src/launcher/cli/deploy.py
  - src/launcher/deploy/__init__.py
  - src/launcher/shared/__init__.py
  - specs/schemas/snapshot_manifest.schema.json
evidence_required:
  - reports/TC-3906/evidence.md
---

# Taskcard TC-3906 — snapshots/ IR Store + phase_store/ + ir_regenerate

## Objective

Create a durable, grade-based IR store (`snapshots/`) that mirrors `deploy/` path-for-path with `.ir.json` instead of `.md`, enabling zero-LLM `.md` regeneration. Also create `phase_store/` for run-level phase JSONs (understand, plan, generate, evaluate) from the dominant run. Hook both into the existing `promote_run()` flow.

## Required spec references

- `specs/11_state_and_events.md` (artifact provenance)
- `specs/schemas/deploy_manifest.schema.json` (pattern for snapshot_manifest)

## Scope

### In scope
- `src/launcher/deploy/snapshot_manifest.py` — `SnapshotManifest` model + load/save
- `src/launcher/deploy/phase_promoter.py` — grade-based IR promotion + phase_store update
- `src/launcher/shared/ir_regenerate.py` — rglob-based .md regeneration from snapshots/
- `src/launcher/deploy/promoter.py` — call `promote_phase_snapshots()` after `promote_run()`
- `src/launcher/cli/deploy.py` — `snapshot promote` subcommand
- `specs/schemas/snapshot_manifest.schema.json` — schema for snapshot_manifest.json

### Out of scope
- Changes to run_loop.py, workers, or pipeline config
- Modifying the existing `deploy/` promotion logic beyond the hook
- UI or reporting beyond CLI subcommand

## Inputs

- `runs/{run_id}/evaluation_report.json` — page grades + content_paths
- `runs/{run_id}/content_bundle/pages/**/*.ir.json` — PageIR files
- `runs/{run_id}/understanding_bundle.json`, `planner_checkpoint.json`, `generate_checkpoint.json`, `evaluate_checkpoint.json` — run-level phase data
- `snapshots/snapshot_manifest.json` — incumbent IR grades (loaded if exists)

## Outputs

- `snapshots/{content_path}.ir.json` — best-grade IR per slug
- `snapshots/snapshot_manifest.json` — provenance ledger
- `phase_store/{family}/{platform}/understand.json` + plan + generate + evaluate — from dominant run
- `{output_dir}/{content_path}.md` — regenerated markdown (from ir_regenerate)

## Allowed paths

- plans/taskcards/TC-3906_snapshot-ir-store.md
- src/launcher/deploy/snapshot_manifest.py
- src/launcher/deploy/phase_promoter.py
- src/launcher/deploy/promoter.py
- src/launcher/shared/ir_regenerate.py
- src/launcher/cli/deploy.py
- src/launcher/deploy/__init__.py
- src/launcher/shared/__init__.py
- specs/schemas/snapshot_manifest.schema.json

### Allowed paths rationale
- `snapshot_manifest.py` — new model file in deploy package
- `phase_promoter.py` — new promoter in deploy package
- `promoter.py` — add hook call only
- `ir_regenerate.py` — new utility in shared package
- `cli/deploy.py` — add subcommand
- `__init__.py` files — may need export updates
- `snapshot_manifest.schema.json` — new schema in specs/schemas

## Implementation steps

### Step 1: Create snapshot_manifest.py
Create `src/launcher/deploy/snapshot_manifest.py` with:
- `SnapshotIREntry` model: `content_path`, `snapshot_file`, `source_run_id`, `grade`, `sha256`, `promoted_at`
- `SnapshotManifest` model: `schema_version="1.0"`, `pages: dict[str, SnapshotIREntry]`, `majority_run_id=""`, `majority_run_ir_count=0`, `last_promotion=""`, `promotion_count=0`
- `load_snapshot_manifest(path: Path) -> SnapshotManifest`
- `save_snapshot_manifest(path: Path, manifest: SnapshotManifest) -> None` using `atomic_write_json`

### Step 2: Create phase_promoter.py
Create `src/launcher/deploy/phase_promoter.py` with:
- `PhasePromotionAction` enum: PROMOTED, SKIPPED_GRADE_LOW, SKIPPED_NO_IMPROVEMENT, SKIPPED_SAME_HASH, SKIPPED_MISSING_IR
- `IRPromotionResult` model: `content_path`, `action`, `old_grade`, `new_grade`, `source_run_id`
- `PhasePromotionReport` model: `run_id`, `ir_promoted`, `ir_skipped_*`, `phase_jsons_updated: bool`, `details`
- `promote_phase_snapshots(run_dir, snapshots_dir, phase_store_dir, family, platform, *, min_grade=Grade.C, dry_run=False)` implementing:
  1. Load evaluation_report.json
  2. Load or init snapshot_manifest.json
  3. For each page_eval: IR source = `run_dir/"content_bundle"/"pages"/(content_path+".ir.json")`, snapshot dest = `snapshots_dir/(content_path+".ir.json")`; grade-compare; if better → atomic write
  4. Count slots won; if > majority_run_ir_count → update phase_store
  5. Save snapshot_manifest.json

### Step 3: Create ir_regenerate.py
Create `src/launcher/shared/ir_regenerate.py` with:
- `regenerate_from_snapshots(snapshots_dir: Path, output_dir: Path) -> list[Path]`
  - `rglob("*.ir.json")` — skip snapshot_manifest.json
  - `rel.with_suffix(".md")` → dest
  - `render_page(PageIR.model_validate(json.loads(...)))` → md
  - `atomic_write_text(dest, md, validate_boundary=output_dir)`

### Step 4: Modify promoter.py
Add after the `save_manifest()` call in `promote_run()` (when `report.promoted > 0`):
```python
# Auto-promote phase snapshots
from launcher.deploy.phase_promoter import promote_phase_snapshots as _promote_snapshots
# snapshots_dir and phase_store_dir resolved relative to deploy_dir's parent
...
```
Read run_config.json for family/platform. Resolve snapshots_dir and phase_store_dir from deploy_dir.parent.

### Step 5: Add CLI subcommand to deploy.py
Add `snapshot` group with `promote` subcommand:
- Args: `--run-dir`, `--snapshots-dir`, `--phase-store-dir`, `--family`, `--platform`, `--min-grade`, `--dry-run`
- Calls `promote_phase_snapshots()` directly

### Step 6: Create schema
Create `specs/schemas/snapshot_manifest.schema.json` modelled on `deploy_manifest.schema.json`.

## Failure modes

### Failure mode 1: IR file missing for promoted page
**Detection**: `_resolve_ir_file()` returns None; logged as WARNING
**Resolution**: Skip with `SKIPPED_MISSING_IR` action; do not abort; report count at end
**Gate**: Phase promoter must not crash on missing IR — evaluate checkpoint may exist without IR

### Failure mode 2: snapshot_manifest.json corrupt
**Detection**: `model_validate` raises ValidationError on load
**Resolution**: Same pattern as `load_manifest()` in manifest.py — backup to `.json.bak`, start fresh
**Gate**: Corrupt manifest must not block promotion of new pages

### Failure mode 3: atomic_write boundary violation
**Detection**: `atomic_write_text` raises `ValueError` (validate_boundary check)
**Resolution**: Pass `validate_boundary=snapshots_dir` to all snapshot writes; check path construction
**Gate**: Must not write outside `snapshots_dir` or `output_dir`

### Failure mode 4: render_page raises FrontmatterError
**Detection**: `FrontmatterError` from `ir_regenerate.py`
**Resolution**: Log per-page error, skip page, continue; return only successfully written paths
**Gate**: One bad IR must not abort full regeneration

## Task-specific review checklist

1. [ ] `snapshot_path = snapshots_dir / (content_path + ".ir.json")` — no other path construction used
2. [ ] `dest = output_dir / rel.with_suffix(".md")` in ir_regenerate — no assumptions about depth
3. [ ] `dest.parent.mkdir(parents=True, exist_ok=True)` called before every write
4. [ ] Grade-compare uses reused `GRADE_RANK` + `_grade_ge()` from promoter.py
5. [ ] SHA-256 dedup: skip if `existing.sha256 == sha256_file(ir_source)`
6. [ ] `snapshot_manifest.json` saved atomically via `atomic_write_json`
7. [ ] Phase JSONs only overwritten when `ir_won_count > manifest.majority_run_ir_count`
8. [ ] `ir_regenerate` skips files named `snapshot_manifest.json` in rglob
9. [ ] Docstrings on all public functions
10. [ ] Schema `"description"` fields present in snapshot_manifest.schema.json
11. [ ] Checked `docs/README.md` ownership map — no guide trigger applies
11. [ ] `promoter.py` hook: reads `run_config.json` for family/platform before calling phase_promoter

## Deliverables

1. `src/launcher/deploy/snapshot_manifest.py`
2. `src/launcher/deploy/phase_promoter.py`
3. `src/launcher/shared/ir_regenerate.py`
4. Modified `src/launcher/deploy/promoter.py` (hook only)
5. Modified `src/launcher/cli/deploy.py` (snapshot subcommand)
6. `specs/schemas/snapshot_manifest.schema.json`

## Acceptance checks

1. [ ] `snapshots/snapshot_manifest.json` created after `promote_phase_snapshots()` with correct grade/sha256 entries
2. [ ] `snapshots/{content_path}.ir.json` paths match `deploy/{content_path}.md` paths (same relative path, different extension)
3. [ ] Lower-grade IR does not overwrite higher-grade incumbent in snapshots/
4. [ ] `regenerate_from_snapshots(snapshots/, deploy/)` recreates all .md files with SHA-256 matching originals
5. [ ] `phase_store/{family}/{platform}/understand.json` written when run wins majority IR slots
6. [ ] Tests pass: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q`

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Evidence captured: reports/TC-3906/evidence.md
- [ ] Doc freshness: confirmed no spec drift

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

**Expected results**:
- All existing tests pass
- New tests for snapshot_manifest, phase_promoter, ir_regenerate pass

## Integration boundary proven

**Upstream**: `promote_run()` in `promoter.py` → provides `run_dir`, `deploy_dir`; `evaluation_report.json` provides grades + content_paths
**Downstream**: `ir_regenerate.regenerate_from_snapshots()` reads `snapshots/` → writes to `output_dir`; `phase_store/` read by future pipeline resume logic
**Contract**: `content_path` is the canonical key; `snapshots_dir / (content_path + ".ir.json")` is the only valid snapshot path construction
