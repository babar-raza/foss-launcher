---
id: TC-INTAKE-PORT
title: "Retroactive taskcard: Port intake discovery module from v1 to v2"
status: Done
priority: Normal
owner: "agent"
updated: "2026-03-07"
tags: [intake, port, retroactive, SRI-01]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-INTAKE-PORT.md
  - src/launcher/intake/org_scanner.py
  - src/launcher/intake/repo_classifier.py
  - src/launcher/intake/config_generator.py
  - src/launcher/intake/scheduler.py
  - src/launcher/intake/config_loader.py
  - src/launcher/intake/__init__.py
  - src/launcher/cli/main.py
  - specs/schemas/intake_config.schema.json
  - configs/intake_config.yaml
  - configs/families.yaml
  - tests/unit/intake/test_org_scanner.py
  - tests/unit/intake/test_classifier.py
  - tests/unit/intake/test_config_generator.py
  - tests/unit/intake/test_config_loader.py
  - tests/unit/intake/test_scheduler.py
  - tests/unit/intake/test_intake_cli.py
  - tests/unit/intake/__init__.py
evidence_required:
  - tests/unit/intake/ (6 test files passing)
---

# Taskcard TC-INTAKE-PORT — Retroactive: Port intake discovery module from v1 to v2

## Objective

**RETROACTIVE TASKCARD (SRI-01):** This taskcard documents work that was already completed without a prior AG-002 taskcard. The intake discovery module (GitHub org scanning, repo classification, pilot config generation, and scheduling) was ported from the v1 main branch to the v2 orphan branch. This retroactive taskcard is created to satisfy AG-002 governance requirements and provide an auditable record of the changes.

## Required spec references

- `specs/schemas/intake_config.schema.json` (Section: defines the schema for intake configuration files)
- `specs/02_intake_worker.md` (Section: intake pipeline worker contract — note: the discovery module is a pre-pipeline CLI tool, separate from the intake pipeline worker at `src/launcher/workers/intake/`)

## Scope

### In scope
- Port 5 intake discovery modules from v1: org_scanner.py, repo_classifier.py, config_generator.py, scheduler.py, config_loader.py
- Create `src/launcher/intake/__init__.py` with public API exports (scan_org, scan_orgs, classify_repo, classify_repos, generate_config, write_config, schedule, load_intake_config)
- Add 4 CLI subcommands (scan, classify, generate, onboard) to `src/launcher/cli/main.py`
- Update `specs/schemas/intake_config.schema.json` with full v1 schema
- Update `configs/intake_config.yaml` with 25 organizations
- Expand `configs/families.yaml` from 6 to 26 families
- Port 6 test files to `tests/unit/intake/`

### Out of scope
- Intake pipeline worker (`src/launcher/workers/intake/`) — separate module, not part of this port
- New feature development on top of the ported code — this is a faithful port only
- Integration tests with live GitHub API — unit tests with mocks only

## Inputs

- v1 main branch: intake discovery module source files
- v1 main branch: intake test files
- `specs/schemas/intake_config.schema.json` (existing v2 stub)
- `configs/families.yaml` (existing v2 file with 6 families)
- `configs/intake_config.yaml` (existing v2 stub)

## Outputs

- `src/launcher/intake/org_scanner.py` — GitHub org scanning via API
- `src/launcher/intake/repo_classifier.py` — repo classification by product family
- `src/launcher/intake/config_generator.py` — pilot config YAML generation
- `src/launcher/intake/scheduler.py` — scheduling logic for intake runs
- `src/launcher/intake/config_loader.py` — intake config file loader with schema validation
- `src/launcher/intake/__init__.py` — public API exports
- `src/launcher/cli/main.py` — updated with 4 intake CLI subcommands
- `specs/schemas/intake_config.schema.json` — full v1-compatible schema
- `configs/intake_config.yaml` — 25 organizations configured
- `configs/families.yaml` — expanded to 26 families
- 6 test files in `tests/unit/intake/`

## Allowed paths

- `plans/taskcards/TC-INTAKE-PORT.md`
- `src/launcher/intake/*.py`
- `src/launcher/cli/main.py`
- `specs/schemas/intake_config.schema.json`
- `configs/intake_config.yaml`
- `configs/families.yaml`
- `tests/unit/intake/*.py`

### Allowed paths rationale
- `src/launcher/intake/` — target location for the ported discovery module
- `src/launcher/cli/main.py` — CLI entry point needs new subcommands for intake operations
- `specs/schemas/` — schema must match v1 intake config structure
- `configs/` — intake config and families config need v1-parity data
- `tests/unit/intake/` — unit tests validate the ported code behaves correctly

## Implementation steps

### Step 1: Port core modules

Copy and adapt 5 modules from v1 main branch to `src/launcher/intake/`: org_scanner.py, repo_classifier.py, config_generator.py, scheduler.py, config_loader.py. Adjust imports to use v2 package paths (`launcher.*` instead of `launch.*`).

### Step 2: Create __init__.py with public API

Create `src/launcher/intake/__init__.py` exporting: scan_org, scan_orgs, classify_repo, classify_repos, generate_config, write_config, schedule, load_intake_config.

### Step 3: Add CLI subcommands

Add 4 subcommands to `src/launcher/cli/main.py`: scan (org scanning), classify (repo classification), generate (config generation), onboard (full pipeline: scan + classify + generate).

### Step 4: Update schema

Update `specs/schemas/intake_config.schema.json` with the full v1 intake config schema, covering organizations, families, scheduling, and classification rules.

### Step 5: Expand configuration files

Update `configs/intake_config.yaml` with 25 organizations. Expand `configs/families.yaml` from 6 to 26 product families.

### Step 6: Port tests

Port 6 test files to `tests/unit/intake/`: test_org_scanner.py, test_classifier.py, test_config_generator.py, test_config_loader.py, test_scheduler.py, test_intake_cli.py. Add `__init__.py`.

## Failure modes

### Failure mode 1: Import path mismatch after port

**Detection**: `ImportError` or `ModuleNotFoundError` when running tests or CLI commands referencing `launch.*` instead of `launcher.*`.
**Resolution**: Search all ported files for `from launch.` or `import launch.` and replace with `from launcher.` / `import launcher.`.
**Gate**: Unit test suite — any import failure causes test failure.

### Failure mode 2: Schema validation rejects valid v1 configs

**Detection**: `jsonschema.ValidationError` when loading `configs/intake_config.yaml` against the updated schema.
**Resolution**: Compare v1 schema against actual config structure; add missing properties or relax constraints to match v1 data.
**Gate**: `intake_config.schema.json` validation in config_loader.py.

### Failure mode 3: CLI subcommand conflicts with existing commands

**Detection**: `argparse` or `click` error on startup due to duplicate subcommand names or parameter collisions.
**Resolution**: Audit existing CLI commands in `main.py` and rename conflicting intake subcommands.
**Gate**: `test_intake_cli.py` exercises all 4 subcommands.

### Failure mode 4: families.yaml expansion breaks downstream consumers

**Detection**: Existing tests or pipeline workers fail after families.yaml grows from 6 to 26 entries.
**Resolution**: Verify all consumers of families.yaml iterate dynamically and do not hard-code family counts or names.
**Gate**: Full test suite regression (`pytest tests/`).

## Task-specific review checklist

1. [x] All 5 intake modules exist in `src/launcher/intake/` and are importable
2. [x] `__init__.py` exports match the 8 documented public API symbols
3. [x] All imports use `launcher.*` (v2), not `launch.*` (v1)
4. [x] 4 CLI subcommands (scan, classify, generate, onboard) are registered and callable
5. [x] `intake_config.schema.json` validates `configs/intake_config.yaml` without errors
6. [x] `configs/families.yaml` contains 26 families
7. [x] `configs/intake_config.yaml` contains 25 organizations
8. [x] All 6 test files in `tests/unit/intake/` pass

## Deliverables

1. 5 ported modules at `src/launcher/intake/{org_scanner,repo_classifier,config_generator,scheduler,config_loader}.py`
2. Public API init at `src/launcher/intake/__init__.py`
3. CLI subcommands in `src/launcher/cli/main.py`
4. Updated schema at `specs/schemas/intake_config.schema.json`
5. Updated configs at `configs/intake_config.yaml` and `configs/families.yaml`
6. 6 test files at `tests/unit/intake/`

## Acceptance checks

1. [x] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/intake/ -v` — all tests pass
2. [x] `python -c "from launcher.intake import scan_org, classify_repo, generate_config, schedule, load_intake_config"` — no import errors
3. [x] `configs/intake_config.yaml` validates against `specs/schemas/intake_config.schema.json`
4. [x] Full test suite shows no regressions from expanded families.yaml

## Self-review

### Verification results
- [x] Tests: 6/6 intake test files PASS
- [x] Validation: intake_config schema validation PASS
- [x] Evidence captured: tests/unit/intake/ (test output)

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/intake/ -v
```

**Expected results**:
- All tests in `tests/unit/intake/` pass
- No import errors from ported modules
- No regressions in broader test suite

## Integration boundary proven

**Upstream**: v1 main branch intake discovery module (source of the port); GitHub API (consumed by org_scanner at runtime)
**Downstream**: `configs/intake_config.yaml` consumed by config_loader; `configs/families.yaml` consumed by pipeline workers and config_generator; CLI subcommands consumed by operators
**Contract**: `specs/schemas/intake_config.schema.json` defines the data contract for intake configuration; `src/launcher/intake/__init__.py` defines the public API contract (8 exported symbols)
