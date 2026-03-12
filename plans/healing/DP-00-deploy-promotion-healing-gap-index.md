# Deploy Promotion Healing — Gap Index

## Context

TC-3818 implemented the deploy promotion system (golden snapshot). A self-review
identified 7 gaps ranging from a critical blocker (wrong eval report path) to
moderate robustness and test-quality issues. This index maps every gap to a
healing taskcard.

## Gap Table

| Gap ID | Severity | Description | Taskcard |
|--------|----------|-------------|----------|
| DP-G1 | CRITICAL | `is_run_complete()` and `promote_run()` only check `evaluation_report.json` at run root; ~87% of real runs only have `evaluation/evaluation_summary.json` | DP-01 |
| DP-G2 | MODERATE | `shutil.copy2` for content deployment is non-atomic; interrupted copy leaves partial `.md` files in `deploy/` | DP-02 |
| DP-G3 | MODERATE | Promotion report not persisted to disk; no audit trail for auto-promote operations | DP-03 |
| DP-G4 | MODERATE | `test_backfill_multiple_runs` has weak assertion (`"New" in content or "Old" in content`); does not deterministically verify the A-graded version wins | DP-04 |
| DP-G5 | LOW | `save_manifest()` does not use JSON schema validation despite schema file existing at `specs/schemas/deploy_manifest.schema.json` | DP-02 |
| DP-G6 | LOW | SHA256 computed before grade check — unnecessary I/O for pages that will be rejected on grade | DP-05 |
| DP-G7 | LOW | `action` field on `PagePromotionResult` uses magic strings instead of enum; dead `_index.md` fallback code in `_resolve_content_file`; unused `import pytest` in test_manifest.py | DP-05 |

## Taskcard Summary

| ID | Title | Gaps Fixed | Files Changed |
|----|-------|------------|---------------|
| DP-01 | Eval report path fallback | DP-G1 | `src/launcher/deploy/promoter.py`, `tests/unit/deploy/test_promoter.py` |
| DP-02 | Atomic writes + schema validation | DP-G2, DP-G5 | `src/launcher/deploy/promoter.py`, `src/launcher/deploy/manifest.py`, `tests/unit/deploy/test_promoter.py` |
| DP-03 | Promotion report persistence | DP-G3 | `src/launcher/deploy/promoter.py`, `src/launcher/orchestrator/run_loop.py`, `tests/unit/deploy/test_promoter.py` |
| DP-04 | Test determinism + coverage expansion | DP-G4 | `tests/unit/deploy/test_promoter.py`, `tests/unit/deploy/test_manifest.py` |
| DP-05 | Code hygiene + perf short-circuit | DP-G6, DP-G7 | `src/launcher/deploy/promoter.py`, `tests/unit/deploy/test_promoter.py` |
