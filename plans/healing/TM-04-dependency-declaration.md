---
id: TM-04
title: "Telemetry API: Declare fastapi/uvicorn in pyproject.toml optional deps"
status: Done
priority: High
owner: unassigned
updated: "2026-03-07"
tags: [healing, telemetry-api, packaging]
depends_on: []
allowed_paths:
  - plans/healing/TM-04-dependency-declaration.md
  - pyproject.toml
evidence_required:
  - reports/healing/TM-04/evidence.md
---

# Taskcard TM-04 — Declare FastAPI/Uvicorn in pyproject.toml

## Status: Done

## Gap linkage
- **G-TM-13**: `fastapi` and `uvicorn` installed manually via pip but not declared in `pyproject.toml`. Any clean install will fail to import `launcher.telemetry_api`.

## Role
Senior engineer. Drop-in, production-ready.

## Scope

### Fix:
Add a `telemetry-api` optional dependency group to `pyproject.toml`:
```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21",
    "ruff>=0.1",
]
telemetry-api = [
    "fastapi>=0.100",
    "uvicorn[standard]>=0.20",
]
```

Note: `httpx` is already in main dependencies (line 18 of pyproject.toml). No need to add it.

### Allowed paths:
- `plans/healing/TM-04-dependency-declaration.md`
- `pyproject.toml`

### Forbidden: any other file/path

## Acceptance checks

### CLI:
- `pip install -e ".[telemetry-api]"` succeeds and `python -c "from launcher.telemetry_api import create_app; print('OK')"` works
- `pip install -e .` (without extra) does NOT pull in fastapi — telemetry-api remains optional

### UI/Web/API:
- N/A

### Tests:
- `tests/unit/telemetry_api/test_server.py` already uses `pytest.importorskip("fastapi")` — tests skip gracefully without the extra
- With the extra installed, all 22+ tests pass

### Config respected end-to-end:
- Optional group name `telemetry-api` matches the package name pattern

### No mock data in production paths:
- N/A

## Deliverables
- Modified `pyproject.toml` with `telemetry-api` optional dependency group
- Full file replacement (no stubs, no TODOs)

## Hard rules
- No new mandatory deps (fastapi/uvicorn MUST be optional)
- Keep existing `dev` group unchanged
- `httpx` already in main deps — do NOT duplicate
- No new deps without explicit justification: fastapi and uvicorn are required by the telemetry API server code already committed; this just declares what's already used

## Review dimensions — what 5/5 means for this taskcard

| Dimension | 5/5 criteria |
|-----------|-------------|
| Thoroughness | All undeclared deps captured in optional group |
| Consistency | Optional group naming follows Python packaging conventions |
| Production grading | Clean install works; CI can install with/without extra |
| Systematic approach | Verify current deps list, add only missing ones |
| Correctness & spec alignment | Dep versions match what was installed/tested |
| Scope & constraints | Only pyproject.toml touched |
| Maintainability | Optional group clearly named; easy to find |
| Testability | Tests already skip gracefully without extra |
| Robustness | Version pins are floor-only (>=), not ceiling-pinned |
| Performance | N/A |
| Integration | `pip install -e ".[telemetry-api,dev]"` works for developers |
| Observability | N/A |
| Minimality | 4 lines added to pyproject.toml |

## Now (runbook)

```bash
# 1. Read current pyproject.toml
cat pyproject.toml

# 2. Add telemetry-api optional group after dev group

# 3. Verify install works
.venv/Scripts/pip.exe install -e ".[telemetry-api]"

# 4. Verify import works
.venv/Scripts/python.exe -c "from launcher.telemetry_api import create_app; print('OK')"

# 5. Run telemetry tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/telemetry_api/ -v

# 6. Run full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x --tb=short -q
```
