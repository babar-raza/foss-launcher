---
id: TC-3796
title: "Telemetry API Server Port"
status: Done
priority: Low
owner: "agent-E"
updated: "2026-03-07"
tags: [telemetry, api-server, observability]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3796_telemetry_api_server.md
  - src/launcher/telemetry_api/__init__.py
  - src/launcher/telemetry_api/server.py
  - src/launcher/telemetry_api/routes/__init__.py
  - src/launcher/telemetry_api/routes/database.py
  - src/launcher/telemetry_api/routes/runs.py
  - src/launcher/telemetry_api/routes/batch.py
  - src/launcher/telemetry_api/routes/metadata.py
  - src/launcher/telemetry_api/routes/models.py
  - tests/unit/telemetry_api/test_server.py
evidence_required:
  - reports/agents/telemetry/TC-3796/evidence.md
---

# Taskcard TC-3796 — Telemetry API Server Port

## Objective

Port the v1 FastAPI telemetry API server from `src/launch/telemetry_api/` to `src/launcher/telemetry_api/`, providing a local HTTP server for querying telemetry data stored in SQLite.

## Required spec references

- `specs/16_local_telemetry_api.md` (Section: Full API specification — if it exists in v2; otherwise v1 spec)
- `specs/toolchain_ci_telemetry.md` (Section: Telemetry Events)

## Scope

### In scope
- Port 7 files from v1: server.py, routes/{database,runs,batch,metadata,models}.py, __init__.py
- Rename all imports from `launch.` to `launcher.`
- Update version string to match v2 engine version
- Write basic endpoint tests

### Out of scope
- Adding new endpoints
- Changing database schema
- Modifying TelemetryClient (already ported)
- Making server mandatory (it's optional infrastructure)

## Inputs

- v1 source: `git show main:src/launch/telemetry_api/` (7 files, ~1,500 lines)

## Outputs

- `src/launcher/telemetry_api/` package (7 files)
- Unit tests

## Allowed paths

- plans/taskcards/TC-3796_telemetry_api_server.md
- src/launcher/telemetry_api/__init__.py
- src/launcher/telemetry_api/server.py
- src/launcher/telemetry_api/routes/__init__.py
- src/launcher/telemetry_api/routes/database.py
- src/launcher/telemetry_api/routes/runs.py
- src/launcher/telemetry_api/routes/batch.py
- src/launcher/telemetry_api/routes/metadata.py
- src/launcher/telemetry_api/routes/models.py
- tests/unit/telemetry_api/test_server.py

### Allowed paths rationale
- All files in new telemetry_api package: mechanical port from v1
- Test file: verification

## Implementation steps

### Step 1: Read all v1 source files

```bash
git show main:src/launch/telemetry_api/server.py
git show main:src/launch/telemetry_api/__init__.py
git show main:src/launch/telemetry_api/routes/database.py
git show main:src/launch/telemetry_api/routes/runs.py
git show main:src/launch/telemetry_api/routes/batch.py
git show main:src/launch/telemetry_api/routes/metadata.py
git show main:src/launch/telemetry_api/routes/models.py
```

### Step 2: Port files with import renaming

For each file: copy content, replace `launch.` with `launcher.`, `launch.telemetry_api` with `launcher.telemetry_api`.

### Step 3: Write endpoint tests

Using FastAPI TestClient, test:
- GET /health returns 200
- POST /api/v1/runs creates a run
- GET /api/v1/runs lists runs
- PATCH /api/v1/runs/{event_id} updates

## Failure modes

### Failure mode 1: Missing FastAPI dependency
**Detection**: ImportError for fastapi/uvicorn
**Resolution**: Add to pyproject.toml optional dependencies
**Gate**: Import test

### Failure mode 2: SQLite schema incompatibility
**Detection**: Database creation fails
**Resolution**: Schema is self-contained in database.py, no external deps
**Gate**: Database init test

### Failure mode 3: Import path mismatch
**Detection**: ImportError on launch.* references
**Resolution**: Search-and-replace all launch.* to launcher.*
**Gate**: Full import test

## Task-specific review checklist

1. [x] All 7 files ported
2. [x] All launch.* imports renamed to launcher.*
3. [x] Version string updated
4. [x] Health endpoint works
5. [x] CRUD endpoints work
6. [x] SQLite database creates correctly

## Deliverables

1. `src/launcher/telemetry_api/` package (7 files)
2. `tests/unit/telemetry_api/test_server.py`

## Acceptance checks

1. [x] Server starts without errors
2. [x] Health endpoint returns 200
3. [x] CRUD operations work
4. [x] All existing tests pass (PYTHONHASHSEED=0)

## Self-review

### Verification results
- [x] Tests: 22/22 PASS
- [x] All endpoints verified
- [x] Evidence captured

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/telemetry_api/test_server.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x --tb=short -q
```

**Expected results**:
- Server endpoint tests pass
- No regressions

## Integration boundary proven

**Upstream**: TelemetryClient POSTs to this server's endpoints
**Downstream**: SQLite database stores telemetry for querying
**Contract**: REST API: POST/GET/PATCH /api/v1/runs, GET /health, GET /metrics
