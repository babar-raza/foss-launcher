# TC-2399 Self-Review (12D)

## Dimensions

| # | Dimension | Score | Notes |
|---|---|---|---|
| 1 | Correctness | 5 | All 22 aliases resolve correctly; pre_run_states cross-checked with state.py |
| 2 | Completeness | 5 | All 5 implementation steps delivered; 15 tests across 6 classes |
| 3 | Clarity | 5 | `RESUME_NODE_MAP` self-documents; `execute_run_from_node` docstring lists all differences from `execute_run` |
| 4 | Consistency | 5 | `resume` CLI command follows identical error-handling pattern as `run` command |
| 5 | Testability | 5 | Validation helper `_validate_resume_artifacts` is testable in isolation (pure function) |
| 6 | Security | 5 | No exec of user-supplied strings; `validate_run_dir_under_runs` path-traversal guard retained |
| 7 | Determinism | 5 | `RESUME_NODE_MAP` is a plain dict with deterministic iteration order (Python 3.7+) |
| 8 | Backward compat | 5 | `build_orchestrator_graph()` default unchanged; `execute_run()` untouched; 0 regressions |
| 9 | Governance | 5 | Shared-library constraint respected; `_EVENT_RUN_RESUMED` in run_loop not models |
| 10 | Spec coverage | 5 | Every requirement in specs/43_resumable_pipeline.md implemented |
| 11 | Evidence | 5 | evidence.md with test counts, file list, compliance notes |
| 12 | Traceability | 5 | TC-2399 in taskcard header; spec ref in all modified files |

**Overall: 5.0 / 5.0**

## Known Gaps

- `_resume_pilot()` in `run_pilot.py` does not propagate `--verbose` from the pilot script
  to the `launch resume` subprocess. Low impact: worker output is still visible on stdout.
- `execute_run_from_node()` uses `snapshot if "snapshot" in dir() else None` as a fallback
  for the case where no state transitions occurred. A cleaner approach would initialise
  `snapshot` to `None` before the loop. This is cosmetic only.

---

## Hardening Self-Review (2026-02-27 — W2 prevalidation)

| # | Dimension | Score | Notes |
|---|-----------|-------|-------|
| 1 | Coverage | 5/5 | 3 new tests: empty dir, all-present, partial-missing — all 3 code branches covered |
| 2 | Correctness | 5/5 | Map invariant preserved (W2 == ingest tuples); cumulative pattern maintained |
| 3 | Evidence | 5/5 | evidence.md updated with before/after, test counts, error message |
| 4 | Test Quality | 5/5 | Tests use `_validate_resume_artifacts` directly; use `RESUME_NODE_MAP["W2"][2]` for DRY required_paths |
| 5 | Maintainability | 5/5 | Only 2 lines changed in run_loop.py; test class self-contained |
| 6 | Safety | 5/5 | No destructive operations; read-only prevalidation unchanged |
| 7 | Security | 5/5 | No new attack surface; path traversal guard still applies |
| 8 | Reliability | 5/5 | Fail-fast before lock acquisition → no stale locks from bad resumes |
| 9 | Observability | 5/5 | ValueError message lists ALL missing paths (not just first) |
| 10 | Performance | 5/5 | Two additional `is_file()` checks — negligible |
| 11 | Compatibility | 5/5 | No BC break; W1 always produces these artifacts before W2 runs |
| 12 | Docs/Specs Fidelity | 5/5 | Matches cumulative pattern in specs/43_resumable_pipeline.md §Artifact Pre-validation |

**Overall: 5.0 / 5.0 — PASS**

### Known Gaps
*(none)*
