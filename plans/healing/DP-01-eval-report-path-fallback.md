# DP-01 — Eval Report Path Fallback

## Status: Done

## Checklist
- [x] Add `_find_eval_report()` helper
- [x] Update `is_run_complete()` to use it
- [x] Update `promote_run()` to use it
- [x] Add `eval_location` param to `_create_run` test helper
- [x] Add 5 new tests (summary-only completeness, root-preferred, none-case, promote-from-summary, backfill-with-summary)
- [x] All 34 tests pass
- [x] Real run verified: pilot_cells_20260307T082430 → Pages in run: 26, Promoted: 5

## Gap linkage
- **DP-G1 (CRITICAL)**: `is_run_complete()` and `promote_run()` only check `evaluation_report.json` at run root. Real-world data shows ~87% of completed runs (13 of 15) only have `evaluation/evaluation_summary.json`. This makes `promote` and `backfill` non-functional for existing runs.

## Role
Senior engineer. Drop-in, production-ready.

## Scope

### Fix
1. Extract a `_find_eval_report(run_dir) -> Path | None` helper that checks both locations:
   - `{run_dir}/evaluation_report.json` (preferred — written by `run_loop.py` line 444)
   - `{run_dir}/evaluation/evaluation_summary.json` (fallback — written by evaluate worker)
2. Update `is_run_complete()` to use `_find_eval_report()` instead of hardcoded path.
3. Update `promote_run()` to use `_find_eval_report()` instead of hardcoded `eval_path`.
4. Add tests that exercise the fallback path (run with only `evaluation/evaluation_summary.json`).
5. Add a test that exercises `promote_run` against a real-format run structure with the summary path.

### Allowed paths
- `src/launcher/deploy/promoter.py`
- `tests/unit/deploy/test_promoter.py`

### Forbidden
- Any other file/path

## Acceptance checks

### CLI
```bash
# Must find and promote pages from a run that only has evaluation/evaluation_summary.json
.venv/Scripts/python.exe -m launcher.cli.main deploy promote runs/pilot_cells_20260307T082430 --dry-run
# Expected: Pages in run: 26 (not 0)
```

### Tests
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/deploy/test_promoter.py -v -k "eval_report"
# All new tests pass
```

### Config respected end-to-end
- Both eval report locations are checked in priority order (root first, then evaluation/ subdir).

### No mock data in production paths
- Tests use `tmp_path` fixtures, no mock data written to real `runs/` or `deploy/`.

## Deliverables

### File: `src/launcher/deploy/promoter.py`
- Add `_find_eval_report(run_dir: Path) -> Path | None` before `is_run_complete()`.
- Replace `eval_report = run_dir / "evaluation_report.json"` in `is_run_complete()` with `if not _find_eval_report(run_dir): return False`.
- Replace `eval_path = run_dir / "evaluation_report.json"` in `promote_run()` with `eval_path = _find_eval_report(run_dir)` and handle `None`.

### File: `tests/unit/deploy/test_promoter.py`
- Add `test_complete_run_with_summary_only`: run has `evaluation/evaluation_summary.json` but no root `evaluation_report.json` — must be detected as complete.
- Add `test_promote_from_summary_only`: same structure — `promote_run` must read and promote from the summary path.
- Add `test_root_report_preferred_over_summary`: run has both — root file is used.
- Update `_create_run` helper to accept an `eval_location` parameter (`"root"` | `"subdir"` | `"both"`, default `"root"` for backward compat).

## Hard rules
- Keep public signatures unless justified; update all call sites.
- No network in offline tests.
- Keep entrypoints in parity (CLI, auto-promote in run_loop all benefit from same fix).
- Deterministic runs (PYTHONHASHSEED=0).
- No new deps.
- Keep code/docs/tests in sync.

## Review dimensions — what 5/5 means for this taskcard

| Dimension | 5/5 criteria |
|-----------|-------------|
| Thoroughness | Both paths tested; root-preferred-over-summary tested; None case tested |
| Consistency | Uses same `EvaluationReport.model_validate()` for both paths |
| Production grading | Works on all 15 existing runs, not just the 2 with root reports |
| Correctness | `_find_eval_report` returns root path when both exist |
| Robustness | Graceful `None` return when neither exists |
| Testability | At least 3 new test cases covering fallback, preference, and absence |
| Minimality | Only `promoter.py` and its test file change; no other files touched |

## Now (runbook)

```bash
# 1. Edit promoter.py — add _find_eval_report, update is_run_complete and promote_run
# 2. Edit test_promoter.py — add _create_run eval_location param, add 3 new tests
# 3. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/deploy/ -v
# 4. Verify against real run
.venv/Scripts/python.exe -m launcher.cli.main deploy promote runs/pilot_cells_20260307T082430 --dry-run
# 5. Expected: "Pages in run: 26", non-zero promoted count
```
