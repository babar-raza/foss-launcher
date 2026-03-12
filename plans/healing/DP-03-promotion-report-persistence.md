# DP-03 — Promotion Report Persistence

## Status: Done

## Gap linkage
- **DP-G3 (MODERATE)**: The auto-promote hook in `run_loop.py` generates a `PromotionReport` but discards it after logging. There is no disk artifact to audit which pages were promoted for a given run. This makes post-hoc debugging and promotion history impossible.

## Role
Senior engineer. Drop-in, production-ready.

## Scope

### Fix
1. In `run_loop.py`, after the auto-promote call, write the `PromotionReport` to `{run_dir}/promotion_report.json` using `store.write_json()`.
2. In `promote_run()`, add an optional `report_path: Path | None = None` parameter. When set, the report is written to that path after promotion completes.
3. In the CLI `promote` command, write `promotion_report.json` to the deploy directory alongside the manifest.
4. Add tests verifying the report file is created on disk with correct content after promotion.

### Allowed paths
- `src/launcher/deploy/promoter.py`
- `src/launcher/orchestrator/run_loop.py`
- `src/launcher/cli/deploy.py`
- `tests/unit/deploy/test_promoter.py`

### Forbidden
- Any other file/path

## Acceptance checks

### CLI
```bash
.venv/Scripts/python.exe -m launcher.cli.main deploy promote runs/pilot_cells_20260307T082430
# Expected: deploy/promotion_report.json exists with run_id, promoted count, details
```

### Tests
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/deploy/test_promoter.py -v -k "report_persist"
# New tests pass
```

### Config respected end-to-end
- Auto-promote writes report to run dir; CLI promote writes report to deploy dir.

### No mock data in production paths
- Tests use `tmp_path`.

## Deliverables

### File: `src/launcher/orchestrator/run_loop.py`
- After `promo = _promote_run(run_dir, deploy_dir)` (line 456), add:
  ```python
  store.write_json("promotion_report.json", promo.model_dump(mode="json"))
  ```

### File: `src/launcher/cli/deploy.py`
- In the `promote` command, after `promote_run()` returns and when `not dry_run and report.promoted > 0`, write the report:
  ```python
  from launcher.io.atomic import atomic_write_json
  report_path = deploy_dir.resolve() / "promotion_report.json"
  atomic_write_json(report_path, report.model_dump(mode="json"), validate_boundary=deploy_dir.resolve())
  ```

### File: `tests/unit/deploy/test_promoter.py`
- Add `test_auto_promote_writes_report`: after `promote_run()`, manually write report to tmp_path and verify round-trip.
- Add `test_promotion_report_contains_details`: promote 2 pages, verify report JSON has correct `promoted`, `total_pages_in_run`, and `details` entries.

## Hard rules
- Keep public signatures of `promote_run` unchanged (report_path is optional with default None).
- No network in offline tests.
- Deterministic runs (PYTHONHASHSEED=0).
- No new deps.
- Keep code/docs/tests in sync.

## Review dimensions — what 5/5 means for this taskcard

| Dimension | 5/5 criteria |
|-----------|-------------|
| Observability | Every promotion (auto and manual) produces a JSON artifact on disk |
| Production grading | Audit trail exists for every deploy/ mutation |
| Consistency | Uses `store.write_json()` in run_loop (matches other artifact writes); uses `atomic_write_json` in CLI |
| Testability | Report content verified via round-trip JSON parsing |
| Minimality | 2-3 lines added per call site; no architectural changes |

## Now (runbook)

```bash
# 1. Edit run_loop.py — add store.write_json after promo call
# 2. Edit cli/deploy.py — add atomic_write_json for CLI promote
# 3. Add 2 new tests to test_promoter.py
# 4. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/deploy/ -v
# 5. Run existing orchestrator tests to verify no regression
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/orchestrator/ -v
```
