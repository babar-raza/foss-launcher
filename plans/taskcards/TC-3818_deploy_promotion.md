---
id: TC-3818
title: "Deploy promotion system (golden snapshot)"
status: In-Progress
priority: High
owner: agent
updated: "2026-03-07"
tags: [deploy, promotion, golden-snapshot]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3818_deploy_promotion.md
  - src/launcher/deploy/__init__.py
  - src/launcher/deploy/manifest.py
  - src/launcher/deploy/promoter.py
  - src/launcher/cli/deploy.py
  - src/launcher/cli/main.py
  - src/launcher/orchestrator/run_loop.py
  - specs/schemas/deploy_manifest.schema.json
  - tests/unit/deploy/__init__.py
  - tests/unit/deploy/test_manifest.py
  - tests/unit/deploy/test_promoter.py
evidence_required:
  - tests/unit/deploy/test_manifest.py
  - tests/unit/deploy/test_promoter.py
---

# Taskcard TC-3818 — Deploy promotion system (golden snapshot)

## Objective

Create a deploy/ directory that accumulates the best version of each page across all pipeline runs, using per-page evaluation grades to decide promotions. This enables deployment from a single, curated content store.

## Required spec references

- `specs/state_events_checkpoints.md` (Section: snapshot model and event log)
- `specs/schemas/` (Section: evaluation report schema)

## Scope

### In scope
- DeployManifest and DeployedPage models
- promote_run() — per-page grade comparison and file copy
- is_run_complete() — validates run has evaluation_report.json + content files
- backfill_runs() — scans all runs for family/platform and promotes best
- Auto-promote hook in run_loop.py (non-fatal)
- CLI subcommands: promote, backfill, status, diff
- deploy_manifest.schema.json
- Unit tests for manifest and promoter

### Out of scope
- Hugo build or site generation from deploy/
- Cross-family deploy merging
- CI/CD integration or deployment scripts

## Inputs

- `runs/{any}/evaluation_report.json` — per-page grades
- `runs/{any}/content_bundle/pages/` — markdown content files
- `runs/{any}/run_config.json` — family/platform for backfill filtering

## Outputs

- `deploy/{content_path}.md` — best version of each page
- `deploy/manifest.json` — provenance ledger

## Allowed paths

- plans/taskcards/TC-3818_deploy_promotion.md
- src/launcher/deploy/__init__.py
- src/launcher/deploy/manifest.py
- src/launcher/deploy/promoter.py
- src/launcher/cli/deploy.py
- src/launcher/cli/main.py
- src/launcher/orchestrator/run_loop.py
- specs/schemas/deploy_manifest.schema.json
- tests/unit/deploy/__init__.py
- tests/unit/deploy/test_manifest.py
- tests/unit/deploy/test_promoter.py

### Allowed paths rationale
- deploy/ module: new package for promotion logic
- cli/deploy.py: CLI subcommands
- cli/main.py: wire deploy_app into main typer app
- run_loop.py: auto-promote hook after pipeline completion
- schema: manifest validation
- tests: verify all logic

## Implementation steps

### Step 1: Create deploy package and manifest models
Create `src/launcher/deploy/__init__.py` and `manifest.py` with DeployedPage and DeployManifest pydantic models, plus load/save functions.

### Step 2: Create promoter logic
Create `promoter.py` with GRADE_RANK, is_run_complete(), promote_run(), backfill_runs(), and PromotionReport model.

### Step 3: Create CLI subcommands
Create `cli/deploy.py` with promote, backfill, status, diff commands using typer.

### Step 4: Wire CLI and auto-promote
Add deploy_app to main.py. Add non-fatal auto-promote call in run_loop.py after _write_final_snapshot.

### Step 5: Create schema and tests
Create deploy_manifest.schema.json and unit tests for manifest round-trip and promoter logic.

## Failure modes

### Failure mode 1: Run has no evaluation_report.json
**Detection**: is_run_complete() returns False
**Resolution**: Skip with log message; do not promote incomplete runs
**Gate**: Completeness check in promote_run()

### Failure mode 2: content_path in eval doesn't match file on disk
**Detection**: FileNotFoundError when reading source .md
**Resolution**: Skip that page, log warning, continue with remaining pages
**Gate**: Per-page error handling in promote_run()

### Failure mode 3: Auto-promote crashes during pipeline run
**Detection**: Exception caught in run_loop.py try/except
**Resolution**: Log warning, continue pipeline — promotion is non-fatal
**Gate**: try/except wrapper in run_loop.py

### Failure mode 4: Corrupt manifest.json
**Detection**: JSON parse error in load_manifest()
**Resolution**: Back up corrupt file, create fresh manifest, log warning
**Gate**: Schema validation on load

## Task-specific review checklist

1. [ ] Grade comparison is correct (A>B>C>D>F, never downgrades)
2. [ ] is_run_complete() checks both evaluation_report.json and content files
3. [ ] Atomic writes used for all deploy/ file operations
4. [ ] Auto-promote in run_loop.py is wrapped in try/except (non-fatal)
5. [ ] Backfill processes runs oldest-first so newer wins on ties
6. [ ] Manifest tracks provenance (run_id, grade, sha256, timestamp)
7. [ ] CLI --min-grade defaults to C
8. [ ] Idempotent: same run promoted twice produces no changes

## Deliverables

1. `src/launcher/deploy/` package (3 files)
2. `src/launcher/cli/deploy.py`
3. Modified `src/launcher/cli/main.py`
4. Modified `src/launcher/orchestrator/run_loop.py`
5. `specs/schemas/deploy_manifest.schema.json`
6. `tests/unit/deploy/` (2 test files)

## Acceptance checks

1. [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/deploy/ -v` passes
2. [ ] `launch deploy promote runs/pilot_cells_20260307T082430 --dry-run` lists pages
3. [ ] `launch deploy status` shows grade distribution after promotion
4. [ ] Auto-promote fires after pipeline run without errors
5. [ ] Backfill scans all matching runs and promotes best pages

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Evidence captured: tests/unit/deploy/

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/deploy/ -v
```

**Expected results**:
- All manifest round-trip tests pass
- All promoter logic tests pass (upgrade, no-downgrade, completeness, backfill)

## Integration boundary proven

**Upstream**: Pipeline run_loop.py produces evaluation_report.json + content_bundle/
**Downstream**: deploy/ directory consumed by deployment tooling
**Contract**: deploy/manifest.json validated against deploy_manifest.schema.json
