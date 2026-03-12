---
id: TM-01
title: "Telemetry API: Fix version string and verify spec alignment"
status: Done
priority: High
owner: unassigned
updated: "2026-03-07"
tags: [healing, telemetry-api, correctness]
depends_on: []
allowed_paths:
  - plans/healing/TM-01-version-and-spec-alignment.md
  - src/launcher/telemetry_api/server.py
  - tests/unit/telemetry_api/test_server.py
evidence_required:
  - reports/healing/TM-01/evidence.md
---

# Taskcard TM-01 — Fix Version String and Verify Spec Alignment

## Status: Done

## Gap linkage
- **G-TM-01**: Version string `2.2.0` carried verbatim from v1; v2 ENGINE_VERSION is `2.0.0` and project version is `2.0.0-alpha`
- **G-TM-02**: API contract never verified against `specs/toolchain_ci_telemetry.md` or the original v1 spec

## Role
Senior engineer. Drop-in, production-ready.

## Scope

### Fix:
1. Replace hardcoded `"2.2.0"` in `server.py` (lines 50 and 82) with a version derived from `ENGINE_VERSION` or the project version constant
2. Audit all endpoints against `specs/toolchain_ci_telemetry.md` (Section: Telemetry Events, Pipeline-Level Metrics) to confirm the API server's contract matches what the spec defines
3. Document any spec divergence in the evidence file

### Allowed paths:
- `plans/healing/TM-01-version-and-spec-alignment.md`
- `src/launcher/telemetry_api/server.py`
- `tests/unit/telemetry_api/test_server.py`

### Forbidden: any other file/path

## Acceptance checks

### CLI:
- `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/telemetry_api/test_server.py -v` passes

### UI/Web/API:
- `GET /health` returns version matching ENGINE_VERSION (currently `2.0.0`)
- Version string appears in OpenAPI schema (`/openapi.json`)

### Tests:
- Existing 22 tests still pass
- Health endpoint test asserts the correct version value (not `2.2.0`)

### Config respected end-to-end:
- Version is sourced from a single constant, not hardcoded in two places

### No mock data in production paths:
- N/A

## Deliverables
- Modified `src/launcher/telemetry_api/server.py` with correct version sourcing
- Updated `tests/unit/telemetry_api/test_server.py` asserting correct version
- Full file replacements (no stubs, no TODOs)

## Hard rules
- Keep public signatures unchanged (`create_app`, `ServerConfig`, etc.)
- Update all call sites if the version source changes
- No network in offline tests
- No new deps without explicit justification
- Keep code/docs/tests in sync
- Deterministic — PYTHONHASHSEED=0

## Review dimensions — what 5/5 means for this taskcard

| Dimension | 5/5 criteria |
|-----------|-------------|
| Thoroughness | Both version occurrences fixed; spec audit documented |
| Consistency | Version sourced from single constant used everywhere |
| Production grading | No hardcoded version strings remain |
| Systematic approach | Read spec first, audit endpoints, fix version, test |
| Correctness & spec alignment | Every endpoint matches spec contract |
| Scope & constraints | Only allowed files touched |
| Maintainability | Version is DRY — single source of truth |
| Testability | Test asserts actual version value, not just presence |
| Robustness | N/A for this card |
| Performance | N/A for this card |
| Integration | Version matches ENGINE_VERSION used by provenance |
| Observability | Version visible in /health and /openapi.json |
| Minimality | Exactly 2-3 line changes in server.py + 1 test update |

## Now (runbook)

```bash
# 1. Read current ENGINE_VERSION
grep -n "ENGINE_VERSION" src/launcher/provenance/provenance.py

# 2. Read server.py to find both version strings
grep -n "2.2.0" src/launcher/telemetry_api/server.py

# 3. Import ENGINE_VERSION and use it in server.py
#    Replace: version="2.2.0"  →  version=_API_VERSION
#    Add at top: from launcher.provenance import ENGINE_VERSION
#    Add: _API_VERSION = ENGINE_VERSION

# 4. Update HealthResponse to use same constant

# 5. Update test to assert version matches ENGINE_VERSION
grep -n "version" tests/unit/telemetry_api/test_server.py

# 6. Read specs/toolchain_ci_telemetry.md and audit endpoints
#    Document findings in evidence file

# 7. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/telemetry_api/test_server.py -v

# 8. Run full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x --tb=short -q
```
