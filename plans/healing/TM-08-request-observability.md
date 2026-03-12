---
id: TM-08
title: "Telemetry API: Add request-level logging middleware"
status: Not Started
priority: Low
owner: unassigned
updated: "2026-03-07"
tags: [healing, telemetry-api, observability]
depends_on: []
allowed_paths:
  - plans/healing/TM-08-request-observability.md
  - src/launcher/telemetry_api/server.py
  - tests/unit/telemetry_api/test_server.py
evidence_required:
  - reports/healing/TM-08/evidence.md
---

# Taskcard TM-08 — Add Request-Level Logging Middleware

## Status: Not Started

## Gap linkage
- **G-TM-20**: No request-level logging middleware. Individual endpoint handlers log, but there's no unified request/response logging with request ID, duration, status code, and method+path.
- **G-TM-21**: Error logs use `str(e)` without stack traces, making production debugging difficult.

## Role
Senior engineer. Drop-in, production-ready.

## Scope

### Fix:
1. Add a Starlette `BaseHTTPMiddleware` subclass in `server.py` that:
   - Generates a request ID (UUIDv4) per request
   - Logs `method path status_code duration_ms request_id` at INFO level on completion
   - Logs exceptions at ERROR level with `logger.exception()` (includes traceback)
   - Adds `X-Request-ID` response header
2. Register the middleware in `create_app()`
3. Add test that response includes `X-Request-ID` header
4. Update error handlers in route files to use `logger.exception()` instead of `logger.error(f"... {e}")`

### Allowed paths:
- `plans/healing/TM-08-request-observability.md`
- `src/launcher/telemetry_api/server.py`
- `tests/unit/telemetry_api/test_server.py`

### Forbidden: any other file/path

## Acceptance checks

### CLI:
- `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/telemetry_api/test_server.py -v` passes

### UI/Web/API:
- Every HTTP response includes `X-Request-ID` header
- Request logs show `GET /health 200 2ms req_id=...` format

### Tests:
- New test: `X-Request-ID` header present in response
- New test: request ID is valid UUID format
- All existing 22+ tests still pass

### Config respected end-to-end:
- N/A (middleware is always active)

### No mock data in production paths:
- N/A

## Deliverables
- Modified `src/launcher/telemetry_api/server.py` with logging middleware
- Updated `tests/unit/telemetry_api/test_server.py` with middleware tests
- Full file replacements (no stubs, no TODOs)

## Hard rules
- Keep public signatures unchanged
- Middleware must not catch/swallow exceptions (only log them, then re-raise)
- No network in offline tests
- No new deps (uuid and time are stdlib)
- Deterministic — PYTHONHASHSEED=0
- Request ID generation uses `uuid.uuid4()` (standard, no custom schemes)

## Review dimensions — what 5/5 means for this taskcard

| Dimension | 5/5 criteria |
|-----------|-------------|
| Thoroughness | Both gaps closed; request logging + stack traces |
| Consistency | Log format matches structlog patterns used elsewhere in launcher |
| Production grading | Request ID enables correlation across logs |
| Systematic approach | Middleware → single logging point; no per-handler duplication |
| Correctness & spec alignment | N/A |
| Scope & constraints | Only server.py and test file touched |
| Maintainability | Middleware is self-contained; easy to extend |
| Testability | X-Request-ID header is easy to assert |
| Robustness | Middleware never swallows exceptions |
| Performance | UUID generation + time.time() overhead is negligible (<0.1ms) |
| Integration | X-Request-ID can be forwarded to TelemetryClient for tracing |
| Observability | This IS the observability improvement |
| Minimality | ~25 lines for middleware class + registration |

## Now (runbook)

```bash
# 1. Read server.py to find middleware registration point
grep -n "middleware\|add_middleware" src/launcher/telemetry_api/server.py

# 2. Add RequestLoggingMiddleware class after imports
# 3. Register middleware in create_app() after CORS middleware

# 4. Add tests for X-Request-ID header

# 5. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/telemetry_api/test_server.py -v

# 6. Run full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x --tb=short -q
```
