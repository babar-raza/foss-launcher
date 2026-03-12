# AH-00 — agents.md Healing Sprint: Gap Index

Generated from self-review of the initial `agents.md` authoring session (2026-03-08).
All gaps identified during the dimension-by-dimension self-review are listed here.
Each gap maps to ≥1 taskcard that closes it.

---

## Gap Table

| Gap ID | Dimension(s) affected | Severity | Description | Taskcard(s) |
|--------|-----------------------|----------|-------------|-------------|
| G-01 | Integration & arch fit, Thoroughness | HIGH | `WorkerContract` abstract interface not documented — agents implementing new workers have no reference | AH-01 |
| G-02 | Integration & arch fit, Thoroughness | HIGH | `PipelineGraphState` TypedDict fields not listed — agents don't know what's in the state bag | AH-01 |
| G-03 | Integration & arch fit, Thoroughness | HIGH | `WorkerContext` runtime context not documented — agents don't know what's injected into every worker | AH-01 |
| G-04 | Robustness & failure modes, Observability | HIGH | No "diagnosing a failed run" workflow — agents have no playbook when the pipeline crashes or returns NO-GO | AH-02 |
| G-05 | Observability & telemetry, Thoroughness | MEDIUM | `TELEMETRY_API_URL` env var not documented; event types table missing; `snapshot.json` purpose unexplained | AH-03 |
| G-06 | Thoroughness, Integration | MEDIUM | `deploy/` directory and `promoter.promote_run()` auto-promotion logic not adequately described | AH-03 |
| G-07 | Testability & coverage, Thoroughness | MEDIUM | Test section thin: no `tests/` directory layout, no mock worker pattern, no regression test recipe (required by AG-016) | AH-04 |
| G-08 | Performance & efficiency, Thoroughness | MEDIUM | No performance/cost guidance — when to use `--stop-after`, what `content_budget_used` means, token budget per call | AH-04 |
| G-09 | Correctness & spec alignment | HIGH | `max_re_runs=2` described as "configurable" — it is hardcoded in `PipelineGraphState` initialization, not a config key | AH-05 |
| G-10 | Correctness & spec alignment | HIGH | `--run-id` + `--resume-from` mutual requirement not documented — agents will hit a cryptic `ValueError` | AH-05 |
| G-11 | Thoroughness, Correctness | LOW | `launch intake` sub-commands (scan, classify) not detailed — no flags or usage examples | AH-05 |
| G-12 | Scope & constraints adherence | MEDIUM | No "read before overwrite" process check documented — agents may silently overwrite pre-existing untracked files | AH-06 |

---

## Taskcard Summary

| Taskcard | Gaps Closed | Priority | Status |
|----------|-------------|----------|--------|
| AH-01 | G-01, G-02, G-03 | HIGH | Not Started |
| AH-02 | G-04 | HIGH | Not Started |
| AH-03 | G-05, G-06 | MEDIUM | Not Started |
| AH-04 | G-07, G-08 | MEDIUM | Not Started |
| AH-05 | G-09, G-10, G-11 | HIGH | Not Started |
| AH-06 | G-12 | MEDIUM | Not Started |

---

## Plan Files

| File | Taskcards |
|------|-----------|
| `plans/healing/AH-01-architecture-internals.md` | AH-01 |
| `plans/healing/AH-02-failure-diagnosis.md` | AH-02 |
| `plans/healing/AH-03-observability-and-deploy.md` | AH-03 |
| `plans/healing/AH-04-test-and-performance.md` | AH-04 |
| `plans/healing/AH-05-correctness-and-intake.md` | AH-05 |
| `plans/healing/AH-06-process-safeguard.md` | AH-06 |
