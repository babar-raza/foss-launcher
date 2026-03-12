# Healing Plan — Telemetry API Server Port (TC-3796) Self-Review Gaps

**Date:** 2026-03-07
**Source:** Self-review of TC-3796 (Telemetry API Server Port)
**Scope:** All blockers, gaps, and production-readiness issues identified in the 13-dimension self-review

---

## Gap Table

| Gap ID | Description | Severity | Taskcard | Status |
|--------|-------------|----------|----------|--------|
| **Correctness & Spec Alignment** |||||
| G-TM-01 | Version string `2.2.0` carried from v1; should match v2 ENGINE_VERSION `2.0.0` | High | TM-01 | **Done** |
| G-TM-02 | Never verified API contract against `specs/toolchain_ci_telemetry.md` or v1 spec `specs/16_local_telemetry_api.md` (not ported) | Medium | TM-01 | **Done** |
| **Security & Robustness** |||||
| G-TM-03 | `update_run()` builds SQL column names via f-string; no allowlist validation | High | TM-02 | **Done** |
| G-TM-04 | `batch-transactional` endpoint calls `db._get_connection()` (private API) | Medium | TM-02 | **Done** |
| G-TM-05 | No input length validation on string fields (agent_name, product, etc.) | Low | TM-02 | **Deferred** (low severity) |
| **Test Coverage** |||||
| G-TM-06 | No test for `batch-transactional` endpoint | High | TM-03 | **Done** (added in TM-02 pass) |
| G-TM-07 | No test for `list_runs` filter params (status, job_type, product, parent_run_id) | High | TM-03 | Not Started |
| G-TM-08 | No test for pagination (limit/offset) | Medium | TM-03 | Not Started |
| G-TM-09 | No test for event storage/retrieval roundtrip via database | Medium | TM-03 | Not Started |
| G-TM-10 | No test for metadata cache invalidation behavior | Low | TM-03 | Not Started |
| G-TM-11 | No negative tests for malformed JSON bodies or missing required fields | Medium | TM-03 | Not Started |
| G-TM-12 | No test for `get_server_config_from_env()` | Low | TM-03 | Not Started |
| **Dependency & Packaging** |||||
| G-TM-13 | `fastapi` and `uvicorn` not declared in `pyproject.toml` optional deps | High | TM-04 | **Done** |
| **Governance & Evidence** |||||
| G-TM-14 | Evidence file `reports/agents/telemetry/TC-3796/evidence.md` never created (required by taskcard frontmatter) | Medium | TM-05 | Not Started |
| **Integration & Wiring** |||||
| G-TM-15 | No CLI command to start telemetry server (`launcher telemetry-server` not wired) | Medium | TM-06 | Not Started |
| G-TM-16 | No documentation of TelemetryClient -> API Server -> SQLite data flow | Low | TM-06 | Not Started |
| **Performance** |||||
| G-TM-17 | New SQLite connection per operation; no connection pooling | Low | TM-07 | Not Started |
| G-TM-18 | `batch_upload` does 2 queries per run (get_by_event_id + create_run); O(2N) | Low | TM-07 | Not Started |
| G-TM-19 | No WAL mode configuration for concurrent read performance | Low | TM-07 | Not Started |
| **Observability** |||||
| G-TM-20 | No request-level logging middleware (request ID, duration, status code) | Low | TM-08 | Not Started |
| G-TM-21 | Error logs use `str(e)` without stack traces | Low | TM-08 | Not Started |

---

## Summary

| Category | Total | Taskcard |
|----------|-------|----------|
| Correctness & Spec | 2 | TM-01 |
| Security & Robustness | 3 | TM-02 |
| Test Coverage | 7 | TM-03 |
| Dependency & Packaging | 1 | TM-04 |
| Governance & Evidence | 1 | TM-05 |
| Integration & Wiring | 2 | TM-06 |
| Performance | 3 | TM-07 |
| Observability | 2 | TM-08 |
| **TOTAL** | **21** | **8 taskcards** |

---

## Taskcard File Inventory

| Taskcard | File |
|----------|------|
| TM-01 | `plans/healing/TM-01-version-and-spec-alignment.md` |
| TM-02 | `plans/healing/TM-02-sql-safety-and-robustness.md` |
| TM-03 | `plans/healing/TM-03-test-coverage-expansion.md` |
| TM-04 | `plans/healing/TM-04-dependency-declaration.md` |
| TM-05 | `plans/healing/TM-05-evidence-and-governance.md` |
| TM-06 | `plans/healing/TM-06-cli-wiring-and-integration.md` |
| TM-07 | `plans/healing/TM-07-sqlite-performance.md` |
| TM-08 | `plans/healing/TM-08-request-observability.md` |

## Priority Order (recommended execution)

1. **TM-01** (version fix) — trivial, high impact, no deps
2. **TM-02** (SQL safety) — security blocker, no deps
3. **TM-04** (pyproject.toml) — packaging correctness, no deps
4. **TM-03** (test coverage) — depends on TM-01 + TM-02 being merged
5. **TM-05** (evidence) — governance compliance, no deps
6. **TM-06** (CLI wiring) — integration, depends on TM-04
7. **TM-07** (performance) — non-blocking optimization
8. **TM-08** (observability) — non-blocking enhancement
