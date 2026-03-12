---
id: TM-07
title: "Telemetry API: SQLite performance improvements"
status: Not Started
priority: Low
owner: unassigned
updated: "2026-03-07"
tags: [healing, telemetry-api, performance]
depends_on: [TM-02]
allowed_paths:
  - plans/healing/TM-07-sqlite-performance.md
  - src/launcher/telemetry_api/routes/database.py
  - tests/unit/telemetry_api/test_database.py
evidence_required:
  - reports/healing/TM-07/evidence.md
---

# Taskcard TM-07 — SQLite Performance Improvements

## Status: Not Started

## Gap linkage
- **G-TM-17**: New SQLite connection opened/closed per operation. Under concurrent requests this means constant file handle churn.
- **G-TM-18**: `batch_upload` calls `get_run_by_event_id()` + `create_run()` per run = 2N queries for N runs. Could use single INSERT OR IGNORE pattern.
- **G-TM-19**: No WAL mode configuration. Default journal mode blocks concurrent reads during writes.

## Role
Senior engineer. Drop-in, production-ready.

## Scope

### Fix:
1. Enable WAL mode on database init: `PRAGMA journal_mode=WAL` in `_init_db()`
2. Add a persistent connection option: `TelemetryDatabase.__init__` accepts optional `pool_size` param; when >0, maintains a connection pool (or single reusable connection with threading lock for SQLite)
3. Optimize `batch_upload` path: add `bulk_create_runs(run_data_list)` method that uses a single transaction with INSERT OR IGNORE for idempotency, avoiding per-run SELECT
4. Add a benchmark test in `test_database.py` that creates 100 runs and verifies it completes in <1 second

### Allowed paths:
- `plans/healing/TM-07-sqlite-performance.md`
- `src/launcher/telemetry_api/routes/database.py`
- `tests/unit/telemetry_api/test_database.py`

### Forbidden: any other file/path

## Acceptance checks

### CLI:
- `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/telemetry_api/test_database.py -v` passes

### UI/Web/API:
- GET /metrics shows `journal_mode: wal` in performance dict

### Tests:
- New test: WAL mode is active after init
- New test: bulk_create_runs creates N runs in single transaction
- New test: 100 run batch completes in <1 second
- All existing tests still pass

### Config respected end-to-end:
- WAL mode is set automatically; no config needed

### No mock data in production paths:
- Benchmark uses realistic run payloads

## Deliverables
- Modified `src/launcher/telemetry_api/routes/database.py` with WAL mode and optimized batch
- New `tests/unit/telemetry_api/test_database.py` with performance tests
- Full file replacements (no stubs, no TODOs)

## Hard rules
- Keep backward compatibility: existing callers of create_run() unchanged
- Single-writer SQLite constraint respected (no concurrent write attempts)
- No network in offline tests
- No new deps
- Deterministic — PYTHONHASHSEED=0 (benchmark uses wall-clock threshold, not exact timing)

## Review dimensions — what 5/5 means for this taskcard

| Dimension | 5/5 criteria |
|-----------|-------------|
| Thoroughness | All 3 perf gaps addressed |
| Consistency | WAL mode matches SQLite best practices for read-heavy workloads |
| Production grading | 100-run batch under 1 second on CI hardware |
| Systematic approach | Measure before optimizing; WAL first (free win), then batch |
| Correctness & spec alignment | Idempotency preserved with INSERT OR IGNORE |
| Scope & constraints | Only database.py and test file touched |
| Maintainability | bulk_create_runs has clear docstring explaining when to use it |
| Testability | Benchmark test has generous threshold (1s) to avoid CI flakiness |
| Robustness | WAL mode degrades gracefully if PRAGMA fails (log warning, continue) |
| Performance | Measurable improvement: N queries → 1 transaction for batch |
| Integration | batch.py can optionally call bulk_create_runs in future |
| Observability | journal_mode visible in /metrics endpoint |
| Minimality | ~30 lines in database.py; ~20 lines in test |

## Now (runbook)

```bash
# 1. Read database.py _init_db
grep -n "PRAGMA\|journal" src/launcher/telemetry_api/routes/database.py

# 2. Add PRAGMA journal_mode=WAL to _init_db after table creation

# 3. Add bulk_create_runs method using executemany or INSERT OR IGNORE loop

# 4. Create test_database.py with:
#    - test_wal_mode_active
#    - test_bulk_create
#    - test_batch_performance

# 5. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/telemetry_api/ -v

# 6. Run full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x --tb=short -q
```
